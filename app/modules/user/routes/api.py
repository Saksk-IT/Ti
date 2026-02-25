# -*- coding: utf-8 -*-
"""用户API路由"""
from flask import Blueprint, request, jsonify, session, current_app, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from app.core.extensions import db
from app.models.user import User as UserModel
from app.models.quiz import Favorite, Mistake, UserAnswer, UserProgress, UserCheckin
from app.models.subject import Subject, Question
from app.models.exam import Exam
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import now_bj, today_bj
from datetime import datetime, timedelta
import os
import uuid

user_api_bp = Blueprint('user_api', __name__)


# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_streak_days(user_id):
    """计算连续学习天数"""
    try:
        rows = (
            db.session.query(db.func.distinct(db.func.date(UserAnswer.created_at)).label('date'))
            .filter(UserAnswer.user_id == user_id)
            .order_by(db.text('date DESC'))
            .limit(100)
            .all()
        )
        if not rows:
            return 0
        
        dates = [datetime.strptime(str(r.date), '%Y-%m-%d').date() for r in rows]
        today = today_bj()
        
        # 如果最近一次答题不是今天或昨天，连续天数为0
        if dates[0] < today - timedelta(days=1):
            return 0
        
        streak = 1
        for i in range(1, len(dates)):
            if dates[i-1] - dates[i] == timedelta(days=1):
                streak += 1
            else:
                break
        
        return streak
    except Exception:
        return 0


def calculate_checkin_streak_days(user_id):
    """计算连续签到天数（截至最近一次签到，最近一次需为今天或昨天，否则为0）"""
    try:
        rows = (
            db.session.query(db.func.distinct(UserCheckin.checkin_date).label('date'))
            .filter(UserCheckin.user_id == user_id)
            .order_by(db.text('date DESC'))
            .limit(100)
            .all()
        )

        if not rows:
            return 0

        dates = [datetime.strptime(str(r.date), '%Y-%m-%d').date() for r in rows if r and r.date]
        if not dates:
            return 0

        today = today_bj()

        if dates[0] < today - timedelta(days=1):
            return 0

        streak = 1
        for i in range(1, len(dates)):
            if dates[i - 1] - dates[i] == timedelta(days=1):
                streak += 1
            else:
                break

        return streak
    except Exception:
        return 0


@user_api_bp.route('/user/checkin/status')
@auth_required  # 支持 session / JWT（小程序）
def user_checkin_status():
    """获取今日签到状态"""
    uid = int(current_user_id() or 0)

    today = today_bj()
    today_s = today.isoformat()

    # 获取本月第一天和最后一天
    month_start = today.replace(day=1).isoformat()
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1).isoformat()
    else:
        month_end = today.replace(month=today.month + 1, day=1).isoformat()

    try:
        row_today = (
            db.session.query(UserCheckin.id, UserCheckin.created_at)
            .filter(UserCheckin.user_id == uid, UserCheckin.checkin_date == today_s)
            .first()
        )

        checked_in_today = row_today is not None
        checked_in_at = (row_today.created_at if row_today else None)

        total_days = db.session.query(db.func.count(UserCheckin.id)).filter(UserCheckin.user_id == uid).scalar() or 0
        total_days = int(total_days)

        streak_days = int(calculate_checkin_streak_days(uid) or 0)

        # 获取本月已签到日期列表
        month_rows = (
            db.session.query(UserCheckin.checkin_date)
            .filter(UserCheckin.user_id == uid, UserCheckin.checkin_date >= month_start, UserCheckin.checkin_date < month_end)
            .order_by(UserCheckin.checkin_date)
            .all()
        )
        checked_dates = [str(r.checkin_date) for r in (month_rows or [])]

        return jsonify({
            'status': 'success',
            'data': {
                'today': today_s,
                'checked_in_today': checked_in_today,
                'checked_in_at': checked_in_at,
                'streak_days': streak_days,
                'total_days': total_days,
                'checked_dates': checked_dates,
            }
        })
    except Exception as e:
        current_app.logger.error(f'[checkin] status failed: {e}')
        return jsonify({'status': 'error', 'message': '获取签到状态失败'}), 500


@user_api_bp.route('/user/checkin', methods=['POST'])
@auth_required  # 支持 session / JWT（小程序）
def user_checkin():
    """执行今日签到（幂等）"""
    uid = int(current_user_id() or 0)

    today = today_bj()
    today_s = today.isoformat()
    now_s = now_bj().strftime('%Y-%m-%d %H:%M:%S')

    # 获取本月第一天和最后一天
    month_start = today.replace(day=1).isoformat()
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1).isoformat()
    else:
        month_end = today.replace(month=today.month + 1, day=1).isoformat()

    try:
        # Check if already checked in today
        existing = (
            db.session.query(UserCheckin)
            .filter(UserCheckin.user_id == uid, UserCheckin.checkin_date == today_s)
            .first()
        )
        just_checked_in = False
        if not existing:
            new_checkin = UserCheckin(user_id=uid, checkin_date=today_s, created_at=now_s)
            db.session.add(new_checkin)
            db.session.commit()
            just_checked_in = True

        row_today = (
            db.session.query(UserCheckin.created_at)
            .filter(UserCheckin.user_id == uid, UserCheckin.checkin_date == today_s)
            .first()
        )
        checked_in_at = (row_today.created_at if row_today else now_s)

        total_days = db.session.query(db.func.count(UserCheckin.id)).filter(UserCheckin.user_id == uid).scalar() or 0
        total_days = int(total_days)

        streak_days = int(calculate_checkin_streak_days(uid) or 0)

        # 获取本月已签到日期列表
        month_rows = (
            db.session.query(UserCheckin.checkin_date)
            .filter(UserCheckin.user_id == uid, UserCheckin.checkin_date >= month_start, UserCheckin.checkin_date < month_end)
            .order_by(UserCheckin.checkin_date)
            .all()
        )
        checked_dates = [str(r.checkin_date) for r in (month_rows or [])]

        return jsonify({
            'status': 'success',
            'data': {
                'today': today_s,
                'checked_in_today': True,
                'checked_in_at': checked_in_at,
                'streak_days': streak_days,
                'total_days': total_days,
                'just_checked_in': just_checked_in,
                'checked_dates': checked_dates,
            }
        })
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        current_app.logger.error(f'[checkin] checkin failed: {e}')
        return jsonify({'status': 'error', 'message': '签到失败，请稍后重试'}), 500


@user_api_bp.route('/user/stats')
def user_stats():
    """获取用户统计数据"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    
    try:
        # 获取用户基本信息
        user = db.session.query(
            UserModel.id, UserModel.username, UserModel.email, UserModel.created_at
        ).filter(UserModel.id == uid).first()
        
        # 统计数据
        total_questions = db.session.query(db.func.count(Question.id)).scalar() or 0
        
        favorites_count = db.session.query(db.func.count(Favorite.id)).filter(Favorite.user_id == uid).scalar() or 0
        
        mistakes_count = db.session.query(db.func.count(Mistake.id)).filter(Mistake.user_id == uid).scalar() or 0
        
        # 答题统计
        answered_count = db.session.query(db.func.count(db.func.distinct(UserAnswer.question_id))).filter(UserAnswer.user_id == uid).scalar() or 0
        
        correct_count = db.session.query(db.func.count(db.func.distinct(UserAnswer.question_id))).filter(UserAnswer.user_id == uid, UserAnswer.is_correct == True).scalar() or 0
        
        # 考试统计
        exam_count = db.session.query(db.func.count(Exam.id)).filter(Exam.user_id == uid).scalar() or 0
        
        finished_exam_count = db.session.query(db.func.count(Exam.id)).filter(Exam.user_id == uid, Exam.status == 'finished').scalar() or 0
        
        user_dict = None
        if user:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at,
            }
        
        return jsonify({
            'status': 'success',
            'data': {
                'user': user_dict,
                'total_questions': total_questions,
                'favorites_count': favorites_count,
                'mistakes_count': mistakes_count,
                'answered_count': answered_count,
                'correct_count': correct_count,
                'accuracy': round(correct_count / answered_count * 100, 1) if answered_count > 0 else 0,
                'exam_count': exam_count,
                'finished_exam_count': finished_exam_count
            }
        })
    except Exception as e:
        current_app.logger.error('请求处理异常: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500


@user_api_bp.route('/user/update', methods=['POST'])
def update_user():
    """更新用户信息"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    data = request.json
    
    # 这里可以添加更新用户信息的逻辑
    # 例如：更新邮箱、密码等
    
    return jsonify({'status': 'success', 'message': '更新成功'})


@user_api_bp.route('/profile/check-username', methods=['POST'])
@auth_required
def check_username():
    """检查用户名是否可用"""
    uid = int(current_user_id() or 0)
    data = request.json or {}
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'status': 'error', 'message': '用户名不能为空'}), 400

    if len(username) < 2:
        return jsonify({'status': 'error', 'message': '用户名至少2个字符'}), 400

    if len(username) > 20:
        return jsonify({'status': 'error', 'message': '用户名最多20个字符'}), 400

    existing = db.session.query(UserModel.id).filter(
        UserModel.username == username, UserModel.id != uid
    ).first()

    if existing:
        return jsonify({'status': 'error', 'available': False, 'message': '该用户名已被使用'})

    return jsonify({'status': 'success', 'available': True, 'message': '用户名可用'})


@user_api_bp.route('/profile/update', methods=['POST'])
@auth_required  # 支持 session 和 JWT（小程序）
def update_profile():
    """更新用户个人资料"""
    uid = int(current_user_id() or 0)
    data = request.json or {}

    avatar = data.get('avatar')
    contact = data.get('contact')
    college = data.get('college')
    signature = data.get('signature')
    username = data.get('username')


    try:
        # 用户名校验
        username_clean = None
        if username is not None:
            if not isinstance(username, str):
                return jsonify({'status': 'error', 'message': '用户名格式不正确'}), 400
            username_clean = username.strip()
            if len(username_clean) < 2:
                return jsonify({'status': 'error', 'message': '用户名至少2个字符'}), 400
            if len(username_clean) > 20:
                return jsonify({'status': 'error', 'message': '用户名最多20个字符'}), 400
            # 检查唯一性
            existing = db.session.query(UserModel.id).filter(
                UserModel.username == username_clean, UserModel.id != uid
            ).first()
            if existing:
                return jsonify({'status': 'error', 'message': '该用户名已被使用，请换一个'}), 400

        # 签名（不改DB结构，存到 user_progress）
        signature_clean = None
        if signature is not None:
            if not isinstance(signature, str):
                return jsonify({'status': 'error', 'message': '签名格式不正确'}), 400
            signature_clean = signature.strip()
            if len(signature_clean) > 80:
                return jsonify({'status': 'error', 'message': '签名最多80个字符'}), 400

        # 构建更新字段
        user_obj = db.session.get(UserModel, uid)
        if not user_obj:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        has_updates = False
        if username_clean is not None:
            user_obj.username = username_clean
            has_updates = True
        if avatar is not None:
            user_obj.avatar = avatar
            has_updates = True
        if contact is not None:
            user_obj.contact = contact
            has_updates = True
        if college is not None:
            user_obj.college = college
            has_updates = True

        if not has_updates and signature_clean is None:
            return jsonify({'status': 'error', 'message': '没有需要更新的内容'}), 400

        if signature_clean is not None:
            import json
            key = 'user_profile_extra_v1'
            progress_row = (
                db.session.query(UserProgress)
                .filter(UserProgress.user_id == uid, UserProgress.p_key == key)
                .first()
            )

            if progress_row:
                try:
                    extra = json.loads(progress_row.data or '{}')
                except Exception:
                    extra = {}
                if not isinstance(extra, dict):
                    extra = {}
                extra['signature'] = signature_clean
                progress_row.data = json.dumps(extra, ensure_ascii=False)
                progress_row.updated_at = now_bj().strftime('%Y-%m-%d %H:%M:%S')
            else:
                data_json = json.dumps({'signature': signature_clean}, ensure_ascii=False)
                now_s = now_bj().strftime('%Y-%m-%d %H:%M:%S')
                new_progress = UserProgress(
                    user_id=uid, p_key=key, data=data_json,
                    updated_at=now_s, created_at=now_s,
                )
                db.session.add(new_progress)

        db.session.commit()
        
        return jsonify({'status': 'success', 'message': '更新成功'})
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        current_app.logger.error('更新失败: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '更新失败，请稍后重试'}), 500


@user_api_bp.route('/profile')
@auth_required  # 支持 session 和 JWT（小程序）
def api_profile():
    """获取用户个人资料"""
    uid = int(current_user_id() or 0)
    
    try:
        # 获取用户基本信息
        user_obj = db.session.get(UserModel, uid)
        
        if not user_obj:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        user = {
            'id': user_obj.id,
            'username': user_obj.username,
            'created_at': user_obj.created_at,
            'is_admin': user_obj.is_admin,
            'avatar': user_obj.avatar,
            'contact': user_obj.contact,
            'college': user_obj.college,
            'email': user_obj.email,
            'email_verified': user_obj.email_verified,
            'openid': user_obj.openid,
        }
        
        # 检查用户是否设置了密码
        from app.core.models.user import User as LegacyUser
        has_password_set = LegacyUser.has_password_set(uid)
        
        # 统计数据
        favorites_count = db.session.query(db.func.count(Favorite.id)).filter(Favorite.user_id == uid).scalar() or 0
        
        mistakes_count = db.session.query(db.func.count(Mistake.id)).filter(Mistake.user_id == uid).scalar() or 0
        
        # 答题统计
        total_answered = db.session.query(db.func.count(UserAnswer.id)).filter(UserAnswer.user_id == uid).scalar() or 0
        
        correct_answered = db.session.query(db.func.count(UserAnswer.id)).filter(UserAnswer.user_id == uid, UserAnswer.is_correct == True).scalar() or 0
        
        accuracy = round(correct_answered / total_answered * 100, 1) if total_answered > 0 else 0
        
        # 计算连续学习天数
        streak_days = calculate_streak_days(uid)

        # 用户扩展资料（不改DB结构：存储在 user_progress）
        signature = ''
        try:
            import json
            extra_row = (
                db.session.query(UserProgress.data)
                .filter(UserProgress.user_id == uid, UserProgress.p_key == 'user_profile_extra_v1')
                .first()
            )
            if extra_row and extra_row.data:
                extra = json.loads(extra_row.data)
                if isinstance(extra, dict) and isinstance(extra.get('signature'), str):
                    signature = extra.get('signature', '').strip()
        except Exception:
            signature = ''
        
        return jsonify({
            'status': 'success',
            'data': {
                'username': user['username'],
                'avatar': user['avatar'],
                'contact': user['contact'],
                'college': user['college'],
                'signature': signature,
                'email': user.get('email'),
                'email_verified': bool(user.get('email_verified', 0)),
                'wechat_bound': bool(user.get('openid')),
                'created_at': user['created_at'].strftime('%Y-%m-%d') if user['created_at'] else '-',
                'is_admin': bool(user['is_admin']),
                'has_password_set': has_password_set,
                'streak_days': streak_days,
                'total_answered': total_answered,
                'correct_answered': correct_answered,
                'accuracy': accuracy,
                'favorites_count': favorites_count,
                'mistakes_count': mistakes_count
            }
        })
    except Exception as e:
        current_app.logger.error('加载失败: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '加载失败，请稍后重试'}), 500


@user_api_bp.route('/profile/password', methods=['POST'])
@auth_required  # 支持 session 和 JWT（小程序）
def change_password():
    """修改密码或设置密码"""
    uid = int(current_user_id() or 0)
    data = request.json or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    is_set_password = data.get('is_set_password', False)  # 是否为设置密码

    if not new_password:
        return jsonify({'status': 'error', 'message': '请填写新密码'}), 400

    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': '密码至少8位'}), 400

    # 检查密码格式：必须包含字母和数字
    import re
    has_letter = bool(re.search(r'[a-zA-Z]', new_password))
    has_digit = bool(re.search(r'\d', new_password))
    if not has_letter or not has_digit:
        return jsonify({'status': 'error', 'message': '密码必须包含字母和数字'}), 400
    
    try:
        # 检查用户是否存在
        user_obj = db.session.get(UserModel, uid)
        
        if not user_obj:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 检查用户是否设置了密码（使用 LegacyUser 的复杂迁移逻辑）
        from app.core.models.user import User as LegacyUser
        has_password = LegacyUser.has_password_set(uid)
        
        # 如果是设置密码（用户还没有设置密码），不需要验证当前密码
        if is_set_password or not has_password:
            # 设置密码
            LegacyUser.update_password(uid, new_password, set_password=True)
            return jsonify({'status': 'success', 'message': '密码设置成功'})
        else:
            # 修改密码，需要验证当前密码
            if not current_password:
                return jsonify({'status': 'error', 'message': '请填写当前密码'}), 400
            
            # 验证当前密码
            if not check_password_hash(user_obj.password_hash, current_password):
                return jsonify({'status': 'error', 'message': '当前密码错误'}), 400
            
            # 更新密码
            LegacyUser.update_password(uid, new_password, set_password=False)
            return jsonify({'status': 'success', 'message': '密码修改成功'})
    except Exception as e:
        current_app.logger.error('操作失败: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '操作失败，请稍后重试'}), 500


@user_api_bp.route('/stats/daily')
def stats_daily():
    """获取每日答题统计"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    
    try:
        start_date = (today_bj() - timedelta(days=days)).isoformat()
        rows = (
            db.session.query(
                db.func.date(UserAnswer.created_at).label('date'),
                db.func.count().label('total'),
                db.func.sum(db.case((UserAnswer.is_correct == True, 1), else_=0)).label('correct'),
            )
            .filter(UserAnswer.user_id == uid)
            .filter(UserAnswer.created_at >= start_date)
            .group_by(db.func.date(UserAnswer.created_at))
            .order_by(db.text('date'))
            .all()
        )
        
        data = [{'date': str(r.date), 'total': r.total, 'correct': r.correct} for r in rows]
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error('请求处理异常: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500


@user_api_bp.route('/stats/by_subject')
def stats_by_subject():
    """按科目统计答题情况"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    
    try:
        rows = (
            db.session.query(
                Subject.name.label('subject'),
                db.func.count().label('total'),
                db.func.sum(db.case((UserAnswer.is_correct == True, 1), else_=0)).label('correct'),
            )
            .join(Question, UserAnswer.question_id == Question.id)
            .outerjoin(Subject, Question.subject_id == Subject.id)
            .filter(UserAnswer.user_id == uid)
            .group_by(Subject.name)
            .order_by(db.text('total DESC'))
            .all()
        )
        
        data = [{'subject': r.subject or '未分类', 'total': r.total, 'correct': r.correct} for r in rows]
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error('请求处理异常: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500


@user_api_bp.route('/stats/by_type')
def stats_by_type():
    """按题型统计答题情况"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    
    try:
        rows = (
            db.session.query(
                Question.type.label('p_type'),
                db.func.count().label('total'),
                db.func.sum(db.case((UserAnswer.is_correct == True, 1), else_=0)).label('correct'),
            )
            .join(Question, UserAnswer.question_id == Question.id)
            .filter(UserAnswer.user_id == uid)
            .group_by(Question.type)
            .order_by(db.text('total DESC'))
            .all()
        )

        from app.core.utils.portable_question_format import portable_type_to_q_type

        data = [
            {
                'q_type': (portable_type_to_q_type(r.p_type) if r and r.p_type else '未知'),
                'total': r.total,
                'correct': r.correct
            }
            for r in rows
        ]
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error('请求处理异常: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500


@user_api_bp.route('/profile/avatar', methods=['POST'])
@auth_required  # 支持 session 和 JWT（小程序）
def upload_avatar():
    """上传用户头像"""
    uid = int(current_user_id() or 0)
    
    # 检查是否有文件
    if 'avatar' not in request.files:
        return jsonify({'status': 'error', 'message': '没有上传文件'}), 400
    
    file = request.files['avatar']
    
    # 检查文件名
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': '不支持的文件类型，请上传图片文件（png, jpg, jpeg, gif, webp）'}), 400
    
    try:
        # 生成唯一文件名
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"avatar_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # 确保上传目录存在
        upload_folder = current_app.config['UPLOAD_FOLDER']
        avatars_folder = os.path.join(upload_folder, 'avatars')
        os.makedirs(avatars_folder, exist_ok=True)
        
        # 保存文件
        filepath = os.path.join(avatars_folder, filename)
        file.save(filepath)
        
        # 更新数据库
        avatar_url = f'/uploads/avatars/{filename}'
        
        # 删除旧头像文件（如果存在）
        user_obj = db.session.get(UserModel, uid)
        
        if user_obj and user_obj.avatar:
            old_path = user_obj.avatar.replace('/uploads/', '')
            old_file = os.path.join(upload_folder, old_path)
            # 路径遍历防护：确保文件在 upload_folder 内
            if os.path.realpath(old_file).startswith(os.path.realpath(upload_folder)) and os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

        # 保存新头像路径
        if user_obj:
            user_obj.avatar = avatar_url
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '头像上传成功',
            'avatar_url': avatar_url
        })
    except Exception as e:
        current_app.logger.error('上传失败: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '上传失败，请稍后重试'}), 500


@user_api_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """访问上传的文件"""
    # 路径遍历防护：拒绝包含 .. 的路径
    if '..' in filename or filename.startswith('/'):
        from flask import abort
        abort(400)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename)


@user_api_bp.route('/user/last-practice')
@auth_required  # 支持 session 和 JWT（小程序）
def user_last_practice():
    """获取用户最近一次练习记录，用于「继续练习」功能"""
    uid = int(current_user_id() or 0)

    try:
        # 获取最近一次答题记录（公共题库）
        row = (
            db.session.query(
                UserAnswer.question_id,
                UserAnswer.created_at,
                Question.subject_id,
                db.func.coalesce(Subject.name, '未分类').label('subject_name'),
            )
            .join(Question, UserAnswer.question_id == Question.id)
            .outerjoin(Subject, Question.subject_id == Subject.id)
            .filter(UserAnswer.user_id == uid)
            .filter(db.or_(Subject.is_locked == 0, Subject.is_locked.is_(None)))
            .order_by(UserAnswer.created_at.desc())
            .first()
        )

        if not row:
            return jsonify({
                'status': 'success',
                'data': {
                    'has_practice': False,
                    'last_at': None,
                    'subject_id': None,
                    'subject_name': None,
                    'question_id': None,
                    'path': None,
                }
            })

        subject_id = int(row.subject_id or 0)
        subject_name = row.subject_name or '未分类'
        question_id = int(row.question_id or 0)
        last_at = row.created_at

        # 构建小程序跳转路径
        path = f'/pages/quiz/quiz?subject={subject_id}' if subject_id else '/pages/public-bank-v2/public-bank-v2'

        return jsonify({
            'status': 'success',
            'data': {
                'has_practice': True,
                'last_at': last_at,
                'subject_id': subject_id,
                'subject_name': subject_name,
                'question_id': question_id,
                'path': path,
            }
        })
    except Exception as e:
        current_app.logger.error(f'[last-practice] failed: {e}')
        return jsonify({'status': 'error', 'message': '获取练习记录失败'}), 500


@user_api_bp.route('/settings/about')
@auth_required  # 支持 session 和 JWT（小程序）
def api_settings_about():
    """设置 - 关于：提供管理员联系方式等信息（与 Web /settings/about 语义对齐）"""
    uid = int(current_user_id() or 0)

    # 当前用户是否为管理员（JWT 模式下 session 可能为空，因此查询 DB）
    is_admin_user = False
    try:
        user_obj = db.session.get(UserModel, uid)
        if user_obj:
            is_admin_user = bool(user_obj.is_admin)
    except Exception:
        is_admin_user = bool(session.get('is_admin'))

    admin = None
    try:
        admin = (
            db.session.query(UserModel.id, UserModel.username, UserModel.email, UserModel.contact)
            .filter(UserModel.is_admin == True)
            .order_by(
                db.case((UserModel.last_active.is_(None), 1), else_=0),
                UserModel.last_active.desc(),
                UserModel.id.asc(),
            )
            .first()
        )
    except Exception:
        try:
            admin = (
                db.session.query(UserModel.id, UserModel.username, UserModel.email, UserModel.contact)
                .filter(UserModel.is_admin == True)
                .order_by(UserModel.id.asc())
                .first()
            )
        except Exception:
            admin = None

    admin_available = bool(admin)
    admin_username = ''
    admin_email = ''
    admin_wechat = ''
    if admin:
        try:
            admin_username = (admin.username or '').strip()
        except Exception:
            admin_username = ''
        try:
            admin_email = (admin.email or '').strip()
        except Exception:
            admin_email = ''
        try:
            admin_wechat = (admin.contact or '').strip()
        except Exception:
            admin_wechat = ''

    chat_disabled = bool(is_admin_user) or (not admin_available)
    chat_disabled_reason = ''
    if is_admin_user:
        chat_disabled_reason = '您当前已是管理员，无需发起站内聊天。'
    elif not admin_available:
        chat_disabled_reason = '系统暂未配置管理员账号，请稍后再试。'

    return jsonify({
        'status': 'success',
        'data': {
            'admin_available': admin_available,
            'admin_username': admin_username,
            'admin_email': admin_email,
            'admin_wechat': admin_wechat,
            'chat_disabled': chat_disabled,
            'chat_disabled_reason': chat_disabled_reason,
        }
    })
