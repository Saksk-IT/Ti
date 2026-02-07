# -*- coding: utf-8 -*-
"""用户API路由"""
from flask import Blueprint, request, jsonify, session, current_app, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from app.core.utils.database import get_db
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


def calculate_streak_days(conn, user_id):
    """计算连续学习天数"""
    try:
        # 获取最近的答题日期
        rows = conn.execute(
            '''SELECT DISTINCT DATE(created_at) as date
               FROM user_answers
               WHERE user_id = ?
               ORDER BY date DESC
               LIMIT 100''',
            (user_id,)
        ).fetchall()
        
        if not rows:
            return 0
        
        dates = [datetime.strptime(r['date'], '%Y-%m-%d').date() for r in rows]
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
    except:
        return 0


def calculate_checkin_streak_days(conn, user_id):
    """计算连续签到天数（截至最近一次签到，最近一次需为今天或昨天，否则为0）"""
    try:
        rows = conn.execute(
            '''SELECT DISTINCT checkin_date as date
               FROM user_checkins
               WHERE user_id = ?
               ORDER BY date DESC
               LIMIT 100''',
            (user_id,)
        ).fetchall()

        if not rows:
            return 0

        dates = [datetime.strptime(str(r['date']), '%Y-%m-%d').date() for r in rows if r and r['date']]
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
    conn = get_db()

    today = today_bj()
    today_s = today.isoformat()

    # 获取本月第一天和最后一天
    month_start = today.replace(day=1).isoformat()
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1).isoformat()
    else:
        month_end = today.replace(month=today.month + 1, day=1).isoformat()

    try:
        row_today = conn.execute(
            'SELECT id, created_at FROM user_checkins WHERE user_id = ? AND checkin_date = ? LIMIT 1',
            (uid, today_s),
        ).fetchone()

        checked_in_today = row_today is not None
        checked_in_at = (row_today['created_at'] if row_today else None)

        total_days = conn.execute(
            'SELECT COUNT(*) FROM user_checkins WHERE user_id = ?',
            (uid,),
        ).fetchone()[0]
        total_days = int(total_days or 0)

        streak_days = int(calculate_checkin_streak_days(conn, uid) or 0)

        # 获取本月已签到日期列表
        month_rows = conn.execute(
            'SELECT checkin_date FROM user_checkins WHERE user_id = ? AND checkin_date >= ? AND checkin_date < ? ORDER BY checkin_date',
            (uid, month_start, month_end),
        ).fetchall()
        checked_dates = [str(r['checkin_date']) for r in (month_rows or [])]

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
    conn = get_db()

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
        cur = conn.execute(
            'INSERT OR IGNORE INTO user_checkins (user_id, checkin_date, created_at) VALUES (?, ?, ?)',
            (uid, today_s, now_s),
        )
        conn.commit()

        just_checked_in = bool(getattr(cur, 'rowcount', 0) == 1)

        row_today = conn.execute(
            'SELECT created_at FROM user_checkins WHERE user_id = ? AND checkin_date = ? LIMIT 1',
            (uid, today_s),
        ).fetchone()
        checked_in_at = (row_today['created_at'] if row_today else now_s)

        total_days = conn.execute(
            'SELECT COUNT(*) FROM user_checkins WHERE user_id = ?',
            (uid,),
        ).fetchone()[0]
        total_days = int(total_days or 0)

        streak_days = int(calculate_checkin_streak_days(conn, uid) or 0)

        # 获取本月已签到日期列表
        month_rows = conn.execute(
            'SELECT checkin_date FROM user_checkins WHERE user_id = ? AND checkin_date >= ? AND checkin_date < ? ORDER BY checkin_date',
            (uid, month_start, month_end),
        ).fetchall()
        checked_dates = [str(r['checkin_date']) for r in (month_rows or [])]

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
            conn.rollback()
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
    conn = get_db()
    
    try:
        # 获取用户基本信息
        user = conn.execute(
            'SELECT id, username, email, created_at FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        
        # 统计数据
        total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        
        favorites_count = conn.execute(
            'SELECT COUNT(*) FROM favorites WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        mistakes_count = conn.execute(
            'SELECT COUNT(*) FROM mistakes WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        # 答题统计
        answered_count = conn.execute(
            'SELECT COUNT(DISTINCT question_id) FROM user_answers WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        correct_count = conn.execute(
            'SELECT COUNT(DISTINCT question_id) FROM user_answers WHERE user_id = ? AND is_correct = 1',
            (uid,)
        ).fetchone()[0]
        
        # 考试统计
        exam_count = conn.execute(
            'SELECT COUNT(*) FROM exams WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        finished_exam_count = conn.execute(
            'SELECT COUNT(*) FROM exams WHERE user_id = ? AND status = "finished"',
            (uid,)
        ).fetchone()[0]
        
        return jsonify({
            'status': 'success',
            'data': {
                'user': dict(user) if user else None,
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

    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM users WHERE username = ? AND id != ?',
        (username, uid)
    ).fetchone()

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

    conn = get_db()

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
            existing = conn.execute(
                'SELECT id FROM users WHERE username = ? AND id != ?',
                (username_clean, uid)
            ).fetchone()
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

        # 构建更新SQL
        updates = []
        params = []

        if username_clean is not None:
            updates.append('username = ?')
            params.append(username_clean)
        if avatar is not None:
            updates.append('avatar = ?')
            params.append(avatar)
        if contact is not None:
            updates.append('contact = ?')
            params.append(contact)
        if college is not None:
            updates.append('college = ?')
            params.append(college)

        if not updates and signature_clean is None:
            return jsonify({'status': 'error', 'message': '没有需要更新的内容'}), 400
        
        if updates:
            params.append(uid)
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            conn.execute(sql, params)

        if signature_clean is not None:
            import json
            key = 'user_profile_extra_v1'
            existing = conn.execute(
                'SELECT id, data FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key),
            ).fetchone()

            if existing:
                try:
                    extra = json.loads(existing['data'] or '{}')
                except Exception:
                    extra = {}
                if not isinstance(extra, dict):
                    extra = {}
                extra['signature'] = signature_clean
                data_json = json.dumps(extra, ensure_ascii=False)
                conn.execute(
                    'UPDATE user_progress SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (data_json, existing['id']),
                )
            else:
                data_json = json.dumps({'signature': signature_clean}, ensure_ascii=False)
                try:
                    conn.execute(
                        """INSERT INTO user_progress (user_id, p_key, data, updated_at, created_at)
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                        (uid, key, data_json),
                    )
                except Exception:
                    conn.execute(
                        """INSERT INTO user_progress (user_id, p_key, data, updated_at)
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                        (uid, key, data_json),
                    )

        conn.commit()
        
        return jsonify({'status': 'success', 'message': '更新成功'})
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        current_app.logger.error('更新失败: %s', e, exc_info=True)
        return jsonify({'status': 'error', 'message': '更新失败，请稍后重试'}), 500


@user_api_bp.route('/profile')
@auth_required  # 支持 session 和 JWT（小程序）
def api_profile():
    """获取用户个人资料"""
    uid = int(current_user_id() or 0)
    conn = get_db()
    
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_openid = 'openid' in user_cols
        # 获取用户基本信息
        if has_openid:
            user_row = conn.execute(
                'SELECT id, username, created_at, is_admin, avatar, contact, college, email, email_verified, openid FROM users WHERE id = ?',
                (uid,)
            ).fetchone()
        else:
            user_row = conn.execute(
                'SELECT id, username, created_at, is_admin, avatar, contact, college, email, email_verified FROM users WHERE id = ?',
                (uid,)
            ).fetchone()
        
        if not user_row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 将Row对象转换为字典
        user = dict(user_row)
        
        # 检查用户是否设置了密码
        from app.core.models.user import User
        has_password_set = User.has_password_set(uid)
        
        # 统计数据
        favorites_count = conn.execute(
            'SELECT COUNT(*) FROM favorites WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        mistakes_count = conn.execute(
            'SELECT COUNT(*) FROM mistakes WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        # 答题统计
        total_answered = conn.execute(
            'SELECT COUNT(*) FROM user_answers WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        correct_answered = conn.execute(
            'SELECT COUNT(*) FROM user_answers WHERE user_id = ? AND is_correct = 1',
            (uid,)
        ).fetchone()[0]
        
        accuracy = round(correct_answered / total_answered * 100, 1) if total_answered > 0 else 0
        
        # 计算连续学习天数
        streak_days = calculate_streak_days(conn, uid)

        # 用户扩展资料（不改DB结构：存储在 user_progress）
        signature = ''
        try:
            import json
            extra_row = conn.execute(
                'SELECT data FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, 'user_profile_extra_v1'),
            ).fetchone()
            if extra_row and extra_row['data']:
                extra = json.loads(extra_row['data'])
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
                'wechat_bound': bool(user.get('openid')) if has_openid else False,
                'created_at': user['created_at'][:10] if user['created_at'] else '-',
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
    
    conn = get_db()
    
    try:
        # 检查用户是否存在
        user = conn.execute(
            'SELECT password_hash FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        
        if not user:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 检查用户是否设置了密码
        from app.core.models.user import User
        has_password = User.has_password_set(uid)
        
        # 如果是设置密码（用户还没有设置密码），不需要验证当前密码
        if is_set_password or not has_password:
            # 设置密码
            User.update_password(uid, new_password, set_password=True)
            return jsonify({'status': 'success', 'message': '密码设置成功'})
        else:
            # 修改密码，需要验证当前密码
            if not current_password:
                return jsonify({'status': 'error', 'message': '请填写当前密码'}), 400
            
            # 验证当前密码
            if not check_password_hash(user['password_hash'], current_password):
                return jsonify({'status': 'error', 'message': '当前密码错误'}), 400
            
            # 更新密码
            User.update_password(uid, new_password, set_password=False)
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
    conn = get_db()
    
    try:
        # 获取最近N天的答题记录
        rows = conn.execute(
            '''SELECT DATE(created_at) as date, 
                      COUNT(*) as total,
                      SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers 
               WHERE user_id = ? AND created_at >= DATE('now', ?)
               GROUP BY DATE(created_at)
               ORDER BY date''',
            (uid, f'-{days} days')
        ).fetchall()
        
        data = [{'date': r['date'], 'total': r['total'], 'correct': r['correct']} for r in rows]
        
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
    conn = get_db()
    
    try:
        rows = conn.execute(
            '''SELECT s.name as subject,
                      COUNT(*) as total,
                      SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers ua
               JOIN questions q ON ua.question_id = q.id
               LEFT JOIN subjects s ON q.subject_id = s.id
               WHERE ua.user_id = ?
               GROUP BY s.name
               ORDER BY total DESC''',
            (uid,)
        ).fetchall()
        
        data = [{'subject': r['subject'] or '未分类', 'total': r['total'], 'correct': r['correct']} for r in rows]
        
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
    conn = get_db()
    
    try:
        rows = conn.execute(
            '''SELECT q.type as p_type,
                      COUNT(*) as total,
                      SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers ua
               JOIN questions q ON ua.question_id = q.id
               WHERE ua.user_id = ?
               GROUP BY q.type
               ORDER BY total DESC''',
            (uid,)
        ).fetchall()

        from app.core.utils.portable_question_format import portable_type_to_q_type

        data = [
            {
                'q_type': (portable_type_to_q_type(r['p_type']) if r and r['p_type'] else '未知'),
                'total': r['total'],
                'correct': r['correct']
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
        conn = get_db()
        
        # 删除旧头像文件（如果存在）
        old_avatar = conn.execute(
            'SELECT avatar FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        
        if old_avatar and old_avatar['avatar']:
            old_path = old_avatar['avatar'].replace('/uploads/', '')
            old_file = os.path.join(upload_folder, old_path)
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except:
                    pass
        
        # 保存新头像路径
        conn.execute(
            'UPDATE users SET avatar = ? WHERE id = ?',
            (avatar_url, uid)
        )
        conn.commit()
        
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
    conn = get_db()

    try:
        # 获取最近一次答题记录（公共题库）
        row = conn.execute(
            '''
            SELECT
              ua.question_id,
              ua.created_at,
              q.subject_id,
              COALESCE(s.name, '未分类') AS subject_name
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE ua.user_id = ?
              AND (s.is_locked = 0 OR s.is_locked IS NULL)
            ORDER BY ua.created_at DESC
            LIMIT 1
            ''',
            (uid,),
        ).fetchone()

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

        subject_id = int(row['subject_id'] or 0)
        subject_name = row['subject_name'] or '未分类'
        question_id = int(row['question_id'] or 0)
        last_at = row['created_at']

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
    conn = get_db()

    # 当前用户是否为管理员（JWT 模式下 session 可能为空，因此查询 DB）
    is_admin_user = False
    try:
        row = conn.execute('SELECT is_admin FROM users WHERE id = ? LIMIT 1', (uid,)).fetchone()
        if row and ('is_admin' in row.keys()):
            is_admin_user = bool(row['is_admin'])
    except Exception:
        is_admin_user = bool(session.get('is_admin'))

    admin = None
    try:
        # 优先使用带 last_active 的排序（若列不存在会抛异常）
        admin = conn.execute(
            """
            SELECT id, username, email, contact
            FROM users
            WHERE is_admin = 1
            ORDER BY (last_active IS NULL) ASC, last_active DESC, id ASC
            LIMIT 1
            """
        ).fetchone()
    except Exception:
        try:
            admin = conn.execute(
                """
                SELECT id, username, email, contact
                FROM users
                WHERE is_admin = 1
                ORDER BY id ASC
                LIMIT 1
                """
            ).fetchone()
        except Exception:
            admin = None

    admin_available = bool(admin)
    admin_username = ''
    admin_email = ''
    admin_wechat = ''
    if admin:
        try:
            admin_username = (admin['username'] or '').strip()
        except Exception:
            admin_username = ''
        try:
            admin_email = (admin['email'] or '').strip()
        except Exception:
            admin_email = ''
        try:
            admin_wechat = (admin['contact'] or '').strip()
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
