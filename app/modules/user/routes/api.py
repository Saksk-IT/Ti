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
from html import unescape
import json
import os
import re
import uuid

user_api_bp = Blueprint('user_api', __name__)


# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'\s+')

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _strip_html_text(raw: str) -> str:
    """将富文本内容转换为可读纯文本，避免把 HTML 标签展示到卡片摘要。"""
    text = unescape(str(raw or ''))
    text = _HTML_TAG_RE.sub(' ', text)
    return _WHITESPACE_RE.sub(' ', text).strip()


def _post_preview(raw: str, limit: int = 80) -> str:
    text = _strip_html_text(raw)
    return text[:limit] if text else ''


def _extract_first_image(images) -> str:
    """兼容字符串 JSON / 列表 / 对象列表，提取帖子首图 URL。"""
    if not images:
        return ''
    try:
        parsed = images if isinstance(images, list) else json.loads(images)
    except Exception:
        parsed = images if isinstance(images, list) else None

    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                for key in ('url', 'src', 'image', 'path'):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
    if isinstance(parsed, str) and parsed.strip():
        return parsed.strip()
    return ''


def validate_profile_nickname(username: str):
    """校验昵称：2-20 位，禁止控制字符"""
    v = (username or '').strip()
    if not v:
        return False, '昵称不能为空'
    if len(v) < 2:
        return False, '昵称至少2个字符'
    if len(v) > 20:
        return False, '昵称最多20个字符'
    if any((ord(ch) < 32 or ord(ch) == 127) for ch in v):
        return False, '昵称包含非法字符'
    return True, ''


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
    """检查昵称是否可用"""
    uid = int(current_user_id() or 0)
    data = request.json or {}
    username = data.get('username', '').strip()

    ok, err = validate_profile_nickname(username)
    if not ok:
        return jsonify({'status': 'error', 'message': err}), 400

    existing = db.session.query(UserModel.id).filter(
        UserModel.username == username, UserModel.id != uid
    ).first()

    if existing:
        return jsonify({'status': 'error', 'available': False, 'message': '该昵称已被使用'})

    return jsonify({'status': 'success', 'available': True, 'message': '昵称可用'})


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
                return jsonify({'status': 'error', 'message': '昵称格式不正确'}), 400
            username_clean = username.strip()
            ok, err = validate_profile_nickname(username_clean)
            if not ok:
                return jsonify({'status': 'error', 'message': err}), 400
            # 检查唯一性
            existing = db.session.query(UserModel.id).filter(
                UserModel.username == username_clean, UserModel.id != uid
            ).first()
            if existing:
                return jsonify({'status': 'error', 'message': '该昵称已被使用，请换一个'}), 400

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

        # Web 端：昵称更新后同步会话，确保首页/侧边栏即时显示自定义昵称
        if username_clean is not None:
            try:
                if int(session.get('user_id') or 0) == int(uid):
                    session['username'] = username_clean
            except Exception:
                pass
        
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
            'phone': user_obj.phone,
            'phone_verified': user_obj.phone_verified,
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
                'phone': user.get('phone') or '',
                'phone_verified': bool(user.get('phone_verified', 0)),
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
    is_set_password = bool(data.get('is_set_password', False))  # 前端传参，仅用于兼容

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

        # 以后端真实状态为准，不信任前端传入 is_set_password，防止绕过当前密码校验
        needs_set_password = not has_password
        if is_set_password != needs_set_password:
            current_app.logger.info(
                'password mode mismatch: uid=%s client_is_set=%s server_needs_set=%s',
                uid, is_set_password, needs_set_password
            )

        # 用户未设置过密码：无需校验当前密码，直接设置
        if needs_set_password:
            # 设置密码
            LegacyUser.update_password(uid, new_password, set_password=True)
            return jsonify({'status': 'success', 'message': '密码设置成功'})

        # 用户已设置过密码：必须校验当前密码
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
    # S1: 聊天文件访问鉴权
    from app.core.utils.chat_file_auth import check_chat_file_access
    check_chat_file_access(filename)
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


# ─────────────────────────────────────────────────────────────
# Profile V2 — 抖音风格个人主页 API
# ─────────────────────────────────────────────────────────────

def _get_user_extra(user_id: int) -> dict:
    """读取 user_profile_extra_v1 JSON"""
    import json as _json
    row = (
        db.session.query(UserProgress.data)
        .filter(UserProgress.user_id == user_id, UserProgress.p_key == 'user_profile_extra_v1')
        .first()
    )
    if row and row.data:
        try:
            extra = _json.loads(row.data)
            if isinstance(extra, dict):
                return extra
        except Exception:
            pass
    return {}


def _format_count(n: int) -> str:
    """格式化数字：>=10000 显示为 x.xw"""
    if n >= 10000:
        return f'{n / 10000:.1f}w'
    return str(n)


@user_api_bp.route('/user/<int:uid>/profile')
def api_user_profile(uid: int):
    """公开主页数据"""
    from sqlalchemy import text as sa_text
    from app.modules.forum.services.follow_service import get_follow_status, get_follow_counts

    target = db.session.get(UserModel, uid)
    if not target:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404

    # 当前登录用户
    me_id = int(current_user_id() or session.get('user_id') or 0)
    is_self = (me_id == uid) if me_id else False

    # 关注状态
    follow_info = get_follow_status(me_id, uid) if me_id and not is_self else {
        'i_follow': False, 'follows_me': False, 'mutual': False,
        'follower_count': 0, 'following_count': 0,
    }
    if is_self:
        counts = get_follow_counts(uid)
        follow_info['follower_count'] = counts['follower_count']
        follow_info['following_count'] = counts['following_count']

    # 获赞总数 = 所有帖子 like_count 之和
    total_likes = db.session.execute(sa_text(
        'SELECT COALESCE(SUM(like_count),0) FROM forum_posts WHERE author_id=:uid AND is_deleted=false'
    ), {'uid': uid}).scalar() or 0

    # 作品数 = 公开题库 + 帖子
    banks_count = db.session.execute(sa_text(
        'SELECT COUNT(*) FROM user_question_banks WHERE user_id=:uid AND is_public=true AND status=1'
    ), {'uid': uid}).scalar() or 0
    posts_count = db.session.execute(sa_text(
        'SELECT COUNT(*) FROM forum_posts WHERE author_id=:uid AND is_deleted=false'
    ), {'uid': uid}).scalar() or 0
    works_count = banks_count + posts_count

    # 收藏数 / 喜欢数
    favorites_count = db.session.execute(sa_text(
        'SELECT COUNT(*) FROM forum_favorites WHERE user_id=:uid'
    ), {'uid': uid}).scalar() or 0
    likes_count = db.session.execute(sa_text(
        "SELECT COUNT(*) FROM forum_likes WHERE user_id=:uid AND target_type='post'"
    ), {'uid': uid}).scalar() or 0

    # 隐私设置
    extra = _get_user_extra(uid)
    signature = extra.get('signature', '')
    privacy_favorites = extra.get('privacy_favorites', 'public')
    privacy_likes = extra.get('privacy_likes', 'public')

    # 非本人 + 私密 → count 返回 null
    resp_favorites_count = favorites_count if (is_self or privacy_favorites == 'public') else None
    resp_likes_count = likes_count if (is_self or privacy_likes == 'public') else None

    return jsonify({
        'status': 'success',
        'data': {
            'id': target.id,
            'username': target.username,
            'avatar': target.avatar,
            'signature': signature,
            'college': target.college or '',
            'created_at': target.created_at.strftime('%Y-%m-%d') if target.created_at else '',
            'following_count': follow_info['following_count'],
            'follower_count': follow_info['follower_count'],
            'total_likes_received': total_likes,
            'is_self': is_self,
            'i_follow': follow_info['i_follow'],
            'follows_me': follow_info['follows_me'],
            'mutual': follow_info['mutual'],
            'privacy': {
                'favorites': privacy_favorites,
                'likes': privacy_likes,
            },
            'works_count': works_count,
            'favorites_count': resp_favorites_count,
            'likes_count': resp_likes_count,
        }
    })


@user_api_bp.route('/user/<int:uid>/works')
def api_user_works(uid: int):
    """作品列表（公开题库 + 帖子），支持 ?type=all|bank|post 筛选"""
    from sqlalchemy import text as sa_text

    target = db.session.get(UserModel, uid)
    if not target:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 50)
    item_type = request.args.get('type', 'all')  # all | bank | post
    offset = (page - 1) * per_page

    items = []
    total = 0

    if item_type in ('all', 'bank'):
        bank_total = db.session.execute(sa_text(
            'SELECT COUNT(*) FROM user_question_banks WHERE user_id=:uid AND is_public=true AND status=1'
        ), {'uid': uid}).scalar() or 0
    else:
        bank_total = 0

    if item_type in ('all', 'post'):
        post_total = db.session.execute(sa_text(
            'SELECT COUNT(*) FROM forum_posts WHERE author_id=:uid AND is_deleted=false'
        ), {'uid': uid}).scalar() or 0
    else:
        post_total = 0

    if item_type == 'bank':
        total = bank_total
        rows = db.session.execute(sa_text('''
            SELECT id, name, description, cover_image, question_count, public_use_count, created_at,
                   'bank' AS item_type
            FROM user_question_banks
            WHERE user_id=:uid AND is_public=true AND status=1
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
        '''), {'uid': uid, 'lim': per_page, 'off': offset}).fetchall()
        for r in rows:
            m = r._mapping
            items.append({
                'id': m['id'], 'item_type': 'bank',
                'name': m['name'], 'description': m['description'] or '',
                'cover_image': m['cover_image'] or '',
                'stat1': m['question_count'] or 0, 'stat1_label': '题',
                'stat2': m['public_use_count'] or 0, 'stat2_label': '使用',
                'created_at': str(m['created_at'] or ''),
            })
    elif item_type == 'post':
        total = post_total
        rows = db.session.execute(sa_text('''
            SELECT id, title, content, images, like_count, comment_count, created_at,
                   'post' AS item_type
            FROM forum_posts
            WHERE author_id=:uid AND is_deleted=false
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
        '''), {'uid': uid, 'lim': per_page, 'off': offset}).fetchall()
        for r in rows:
            m = r._mapping
            preview = _post_preview(m['content'], 80)
            cover = _extract_first_image(m['images'])
            items.append({
                'id': m['id'], 'item_type': 'post',
                'name': m['title'] or '', 'description': preview,
                'cover_image': cover,
                'stat1': m['like_count'] or 0, 'stat1_label': '赞',
                'stat2': m['comment_count'] or 0, 'stat2_label': '评论',
                'created_at': str(m['created_at'] or ''),
            })
    else:
        # all: UNION 查询
        total = bank_total + post_total
        rows = db.session.execute(sa_text('''
            SELECT * FROM (
                SELECT id, name, description, cover_image,
                       question_count AS stat1, '题' AS stat1_label,
                       public_use_count AS stat2, '使用' AS stat2_label,
                       created_at, 'bank' AS item_type, NULL AS images
                FROM user_question_banks
                WHERE user_id=:uid AND is_public=true AND status=1
                UNION ALL
                SELECT id, title AS name, content AS description,
                       NULL AS cover_image,
                       like_count AS stat1, '赞' AS stat1_label,
                       comment_count AS stat2, '评论' AS stat2_label,
                       created_at, 'post' AS item_type, images
                FROM forum_posts
                WHERE author_id=:uid AND is_deleted=false
            ) combined
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
        '''), {'uid': uid, 'lim': per_page, 'off': offset}).fetchall()
        for r in rows:
            m = r._mapping
            card_type = m['item_type']
            is_post = card_type == 'post'
            cover = m['cover_image'] or ''
            if is_post and not cover:
                cover = _extract_first_image(m['images'])
            items.append({
                'id': m['id'], 'item_type': card_type,
                'name': m['name'] or '',
                'description': _post_preview(m['description'], 80) if is_post else (m['description'] or ''),
                'cover_image': cover,
                'stat1': m['stat1'] or 0, 'stat1_label': m['stat1_label'],
                'stat2': m['stat2'] or 0, 'stat2_label': m['stat2_label'],
                'created_at': str(m['created_at'] or ''),
            })

    has_more = (page * per_page) < total
    return jsonify({
        'status': 'success',
        'data': {
            'items': items, 'total': total,
            'page': page, 'per_page': per_page, 'has_more': has_more,
        }
    })


@user_api_bp.route('/user/<int:uid>/favorites')
def api_user_favorites(uid: int):
    """收藏帖子列表（隐私检查）"""
    from sqlalchemy import text as sa_text

    target = db.session.get(UserModel, uid)
    if not target:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404

    me_id = int(current_user_id() or session.get('user_id') or 0)
    is_self = (me_id == uid) if me_id else False

    # 隐私检查
    if not is_self:
        extra = _get_user_extra(uid)
        if extra.get('privacy_favorites', 'public') == 'private':
            return jsonify({'status': 'error', 'code': 'PRIVATE', 'message': '该用户已将收藏设为私密'})

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 50)
    offset = (page - 1) * per_page

    total = db.session.execute(sa_text(
        'SELECT COUNT(*) FROM forum_favorites ff JOIN forum_posts fp ON fp.id=ff.post_id '
        'WHERE ff.user_id=:uid AND fp.is_deleted=false'
    ), {'uid': uid}).scalar() or 0

    rows = db.session.execute(sa_text('''
        SELECT fp.id, fp.title, fp.content, fp.images, fp.like_count, fp.comment_count, ff.created_at
        FROM forum_favorites ff
        JOIN forum_posts fp ON fp.id = ff.post_id
        WHERE ff.user_id = :uid AND fp.is_deleted = false
        ORDER BY ff.created_at DESC
        LIMIT :lim OFFSET :off
    '''), {'uid': uid, 'lim': per_page, 'off': offset}).fetchall()

    items = []
    for r in rows:
        m = r._mapping
        preview = _post_preview(m['content'], 80)
        cover = _extract_first_image(m['images'])
        items.append({
            'id': m['id'], 'item_type': 'post',
            'name': m['title'] or '', 'description': preview,
            'cover_image': cover,
            'stat1': m['like_count'] or 0, 'stat1_label': '赞',
            'stat2': m['comment_count'] or 0, 'stat2_label': '评论',
            'created_at': str(m['created_at'] or ''),
        })

    has_more = (page * per_page) < total
    return jsonify({
        'status': 'success',
        'data': {
            'items': items, 'total': total,
            'page': page, 'per_page': per_page, 'has_more': has_more,
        }
    })


@user_api_bp.route('/user/<int:uid>/likes')
def api_user_likes(uid: int):
    """喜欢帖子列表（隐私检查）"""
    from sqlalchemy import text as sa_text

    target = db.session.get(UserModel, uid)
    if not target:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404

    me_id = int(current_user_id() or session.get('user_id') or 0)
    is_self = (me_id == uid) if me_id else False

    if not is_self:
        extra = _get_user_extra(uid)
        if extra.get('privacy_likes', 'public') == 'private':
            return jsonify({'status': 'error', 'code': 'PRIVATE', 'message': '该用户已将喜欢设为私密'})

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 50)
    offset = (page - 1) * per_page

    total = db.session.execute(sa_text(
        "SELECT COUNT(*) FROM forum_likes fl JOIN forum_posts fp ON fp.id=fl.target_id "
        "WHERE fl.user_id=:uid AND fl.target_type='post' AND fp.is_deleted=false"
    ), {'uid': uid}).scalar() or 0

    rows = db.session.execute(sa_text('''
        SELECT fp.id, fp.title, fp.content, fp.images, fp.like_count, fp.comment_count, fl.created_at
        FROM forum_likes fl
        JOIN forum_posts fp ON fp.id = fl.target_id
        WHERE fl.user_id = :uid AND fl.target_type = 'post' AND fp.is_deleted = false
        ORDER BY fl.created_at DESC
        LIMIT :lim OFFSET :off
    '''), {'uid': uid, 'lim': per_page, 'off': offset}).fetchall()

    items = []
    for r in rows:
        m = r._mapping
        preview = _post_preview(m['content'], 80)
        cover = _extract_first_image(m['images'])
        items.append({
            'id': m['id'], 'item_type': 'post',
            'name': m['title'] or '', 'description': preview,
            'cover_image': cover,
            'stat1': m['like_count'] or 0, 'stat1_label': '赞',
            'stat2': m['comment_count'] or 0, 'stat2_label': '评论',
            'created_at': str(m['created_at'] or ''),
        })

    has_more = (page * per_page) < total
    return jsonify({
        'status': 'success',
        'data': {
            'items': items, 'total': total,
            'page': page, 'per_page': per_page, 'has_more': has_more,
        }
    })


@user_api_bp.route('/profile/privacy', methods=['POST'])
@auth_required
def api_update_privacy():
    """更新隐私设置（仅自己）"""
    import json as _json

    uid = int(current_user_id() or 0)
    data = request.json or {}

    privacy_favorites = data.get('privacy_favorites')
    privacy_likes = data.get('privacy_likes')

    valid_values = ('public', 'private')
    if privacy_favorites and privacy_favorites not in valid_values:
        return jsonify({'status': 'error', 'message': '无效的隐私设置值'}), 400
    if privacy_likes and privacy_likes not in valid_values:
        return jsonify({'status': 'error', 'message': '无效的隐私设置值'}), 400

    if not privacy_favorites and not privacy_likes:
        return jsonify({'status': 'error', 'message': '没有需要更新的内容'}), 400

    try:
        key = 'user_profile_extra_v1'
        progress_row = (
            db.session.query(UserProgress)
            .filter(UserProgress.user_id == uid, UserProgress.p_key == key)
            .first()
        )

        if progress_row:
            try:
                extra = _json.loads(progress_row.data or '{}')
            except Exception:
                extra = {}
            if not isinstance(extra, dict):
                extra = {}
            if privacy_favorites:
                extra['privacy_favorites'] = privacy_favorites
            if privacy_likes:
                extra['privacy_likes'] = privacy_likes
            progress_row.data = _json.dumps(extra, ensure_ascii=False)
            progress_row.updated_at = now_bj().strftime('%Y-%m-%d %H:%M:%S')
        else:
            extra = {}
            if privacy_favorites:
                extra['privacy_favorites'] = privacy_favorites
            if privacy_likes:
                extra['privacy_likes'] = privacy_likes
            now_s = now_bj().strftime('%Y-%m-%d %H:%M:%S')
            new_progress = UserProgress(
                user_id=uid, p_key=key,
                data=_json.dumps(extra, ensure_ascii=False),
                updated_at=now_s, created_at=now_s,
            )
            db.session.add(new_progress)

        db.session.commit()
        return jsonify({'status': 'success', 'message': '隐私设置已更新'})
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        current_app.logger.error('隐私设置更新失败: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '更新失败，请稍后重试'}), 500
