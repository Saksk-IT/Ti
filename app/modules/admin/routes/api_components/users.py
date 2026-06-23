# -*- coding: utf-8 -*-
"""Admin API routes - users & permissions."""

import datetime
import io
import json
import os
import zipfile

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.core.extensions import db, limiter
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.csv_helpers import csv_escape
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp
from app.core.utils.decorators import admin_required


def _build_named_in(col: str, values: list, prefix: str = 'in') -> tuple[str, dict]:
    """构建命名参数 IN 子句，返回 (sql_fragment, params_dict)"""
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ', '.join(f':{k}' for k in params)
    return f"{col} IN ({placeholders})", params


def _parse_admin_user_time(value):
    """按 UTC 解释用户表中的无时区时间，避免 Flask jsonify 输出 RFC 日期。"""
    if not value:
        return None

    if isinstance(value, datetime.datetime):
        parsed = value
    else:
        raw_value = str(value).strip()
        if not raw_value:
            return None

        normalized = raw_value[:-1] + '+00:00' if raw_value.endswith('Z') else raw_value
        parsed = None
        try:
            parsed = datetime.datetime.fromisoformat(normalized)
        except ValueError:
            for fmt in (
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
                '%a, %d %b %Y %H:%M:%S GMT',
            ):
                try:
                    parsed = datetime.datetime.strptime(raw_value, fmt)
                    break
                except ValueError:
                    continue
        if parsed is None:
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def _format_admin_user_time(value):
    parsed = _parse_admin_user_time(value)
    if parsed is None:
        return None
    return parsed.replace(microsecond=0).isoformat() + 'Z'


def _is_user_online(last_active, now_utc=None) -> bool:
    parsed = _parse_admin_user_time(last_active)
    if parsed is None:
        return False

    now = now_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    delta = now - parsed
    return datetime.timedelta(0) <= delta < datetime.timedelta(minutes=5)


@admin_api_bp.route('/users')
@admin_required
@limiter.limit("30 per minute;300 per hour")
def admin_api_users():
    """用户列表API"""
    try:
        search = (request.args.get('search') or '').strip()
        page = parse_int(request.args.get('page'), 1, 1)
        size = parse_int(request.args.get('size'), 10, 5, 100)
        sort = (request.args.get('sort') or 'created_at').lower()
        order = (request.args.get('order') or 'desc').lower()

        sort_map = {'created_at':'created_at', 'username':'username', 'id':'id'}
        if sort not in sort_map:
            sort = 'created_at'
        if order not in ('asc','desc'):
            order = 'desc'

        offset = (page-1)*size

        where = 'WHERE 1=1'
        params: dict = {}

        if search:
            where += ' AND username LIKE :search'
            params['search'] = f'%{search}%'

        total = db.session.execute(text(f'SELECT COUNT(1) FROM users {where}'), params).scalar()

        # ORM 模型已定义所有字段，无需 PRAGMA 检查
        has_subject_admin_field = True
        has_notification_admin_field = True

        # 根据字段构建查询（使用子查询避免GROUP BY复杂性）
        select_fields = ['u.id', 'u.username', 'u.is_admin', 'u.is_locked', 'u.created_at', 'u.last_active']
        if has_subject_admin_field:
            select_fields.append('u.is_subject_admin')
        if has_notification_admin_field:
            select_fields.append('u.is_notification_admin')
        select_fields.append('COALESCE((SELECT COUNT(DISTINCT subject_id) FROM user_subjects WHERE user_id = u.id), 0) as restricted_subjects_count')
        select_with_count = ', '.join(select_fields)

        # 处理where子句：将条件中的字段引用改为u.前缀
        where_for_query = where.replace('username', 'u.username')

        # 权限管理页面：按权限优先级排序
        is_permissions_page = request.referrer and '/admin/permissions' in request.referrer
        use_priority_sort = request.args.get('priority_sort', '').lower() == 'true' or is_permissions_page

        if use_priority_sort:
            priority_fields = ['u.is_admin DESC']
            if has_notification_admin_field:
                priority_fields.append('u.is_notification_admin DESC')
            if has_subject_admin_field:
                priority_fields.append('u.is_subject_admin DESC')
            priority_order = ', '.join(priority_fields)
            order_by = f'{priority_order}, u.{sort_map[sort]} {order}'
        else:
            order_by = f'u.{sort_map[sort]} {order}'

        query_params = {**params, 'limit': size, 'offset': offset}
        rows = db.session.execute(
            text(f'SELECT {select_with_count} FROM users u {where_for_query} ORDER BY {order_by} LIMIT :limit OFFSET :offset'),
            query_params
        ).fetchall()
        
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        data = []
        for r in rows:
            m = r._mapping
            last_active_val = m.get('last_active')

            data.append({
                'id': m['id'],
                'username': m['username'],
                'is_admin': bool(m.get('is_admin', False)),
                'is_subject_admin': bool(m.get('is_subject_admin', False)),
                'is_notification_admin': bool(m.get('is_notification_admin', False)),
                'is_locked': bool(m.get('is_locked', False)),
                'created_at': _format_admin_user_time(m.get('created_at')),
                'is_online': _is_user_online(last_active_val, now_utc),
                'last_active': _format_admin_user_time(last_active_val),
                'restricted_subjects_count': m.get('restricted_subjects_count') or 0
            })
        
        # 统计所有用户的全局数据（不受分页和搜索影响）
        stats_fields = ['is_admin', 'is_locked', 'last_active', 'is_subject_admin', 'is_notification_admin']
        all_users_rows = db.session.execute(text(f'SELECT {", ".join(stats_fields)} FROM users')).fetchall()

        # 统计全局数据
        online_count = 0
        admin_count = 0
        subject_admin_count = 0
        notification_admin_count = 0
        locked_count = 0

        for user_row in all_users_rows:
            um = user_row._mapping
            # 统计管理员
            if um['is_admin']:
                admin_count += 1
            # 统计科目管理员（不包括管理员）
            elif um.get('is_subject_admin'):
                subject_admin_count += 1
            # 统计通知管理员（不包括管理员）
            if um.get('is_notification_admin'):
                notification_admin_count += 1
            # 统计锁定用户
            if um['is_locked']:
                locked_count += 1
            # 统计在线用户（5分钟内有活动）
            if _is_user_online(um.get('last_active'), now_utc):
                online_count += 1
        
        # 返回数据，包含全局统计数据
        return jsonify({
            'status': 'success',
            'data': data,
            'total': total,
            'stats': {
                'online': online_count,
                'admin': admin_count,
                'subject_admin': subject_admin_count,
                'notification_admin': notification_admin_count,
                'locked': locked_count
            }
        })
    except Exception as e:
        current_app.logger.error(f'用户列表API错误: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': f'加载用户列表失败: {str(e)}'}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@admin_required
def toggle_admin_status(user_id):
    """切换管理员权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '管理员不能对自己进行操作'}), 400
    
    try:
        row = db.session.execute(text('SELECT is_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        target_is_admin = bool(row._mapping['is_admin'])

        if target_is_admin:
            admin_count = db.session.execute(text('SELECT COUNT(1) FROM users WHERE is_admin = true')).scalar()
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能取消最后一个管理员的权限'}), 400

        db.session.execute(text('UPDATE users SET is_admin = NOT is_admin WHERE id = :uid'), {'uid': user_id})
        db.session.execute(text('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'), {'uid': user_id})
        db.session.commit()
        invalidate_user_state(int(user_id))

        current_app.logger.info(f'管理员权限切换 - 目标用户: {row._mapping["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_subject_admin', methods=['POST'])
@admin_required
def toggle_subject_admin_status(user_id):
    """切换科目管理员权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    try:
        row = db.session.execute(text('SELECT is_subject_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        db.session.execute(text('UPDATE users SET is_subject_admin = NOT is_subject_admin WHERE id = :uid'), {'uid': user_id})
        db.session.execute(text('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'), {'uid': user_id})
        db.session.commit()
        invalidate_user_state(int(user_id))

        current_app.logger.info(f'科目管理员权限切换 - 目标用户: {row._mapping["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '科目管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换科目管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_notification_admin', methods=['POST'])
@admin_required
def toggle_notification_admin_status(user_id):
    """切换通知管理员权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    try:
        row = db.session.execute(text('SELECT is_notification_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        db.session.execute(text('UPDATE users SET is_notification_admin = NOT is_notification_admin WHERE id = :uid'), {'uid': user_id})
        db.session.execute(text('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'), {'uid': user_id})
        db.session.commit()
        invalidate_user_state(int(user_id))

        current_app.logger.info(f'通知管理员权限切换 - 目标用户: {row._mapping["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '通知管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error('切换通知管理员权限失败 - 用户ID: %s', user_id, exc_info=True)
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'}), 500


# ============== 权限管理 ==============


@admin_api_bp.route('/permissions/batch', methods=['POST'])
@admin_required
def batch_set_permissions():
    """批量设置用户权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    data = request.json or {}
    user_ids = data.get('user_ids', [])
    permission_type = data.get('permission_type', '').strip()
    enable = data.get('enable', True)
    
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({'status': 'error', 'message': '请选择要操作的用户'}), 400
    
    if permission_type not in ('subject_admin', 'notification_admin'):
        return jsonify({'status': 'error', 'message': '无效的权限类型'}), 400
    
    current_user_id = session.get('user_id')
    if current_user_id in user_ids:
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    try:
        # ORM 模型已定义所有字段，无需 PRAGMA 检查

        # 验证用户是否存在
        in_clause, in_params = _build_named_in('id', user_ids, 'uid')
        existing_users = db.session.execute(
            text(f'SELECT id, username FROM users WHERE {in_clause}'),
            in_params
        ).fetchall()

        if len(existing_users) != len(user_ids):
            return jsonify({'status': 'error', 'message': '部分用户不存在'}), 400

        # 批量更新权限
        value = True if enable else False
        col = 'is_subject_admin' if permission_type == 'subject_admin' else 'is_notification_admin'
        db.session.execute(
            text(f'UPDATE users SET {col} = :val WHERE {in_clause}'),
            {**in_params, 'val': value}
        )

        # 更新所有受影响用户的session_version，强制刷新会话
        db.session.execute(
            text(f'UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE {in_clause}'),
            in_params
        )

        db.session.commit()
        for uid in user_ids:
            try:
                invalidate_user_state(int(uid))
            except Exception:
                pass

        # 记录操作日志
        action = '设为' if enable else '取消'
        permission_name = '科目管理员' if permission_type == 'subject_admin' else '通知管理员'
        usernames = [u._mapping['username'] for u in existing_users]
        current_app.logger.info(
            f'批量{action}{permission_name} - 用户: {", ".join(usernames)}, '
            f'操作者: {session.get("username")}, IP: {request.remote_addr}'
        )

        return jsonify({
            'status': 'success',
            'message': f'已{action}{permission_name}（已强制刷新目标用户会话）',
            'affected_count': len(user_ids)
        })
    except Exception as e:
        current_app.logger.error('批量设置权限失败', exc_info=True)
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'}), 500



@admin_api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    from app.core.utils.user_state_cache import invalidate_user_state

    def _ref_counts(uid: int):
        """统计哪些表还在引用该用户，用于给管理员友好提示"""
        checks = [
            ('favorites', 'SELECT COUNT(1) FROM favorites WHERE user_id=:uid'),
            ('mistakes', 'SELECT COUNT(1) FROM mistakes WHERE user_id=:uid'),
            ('user_answers', 'SELECT COUNT(1) FROM user_answers WHERE user_id=:uid'),
            ('user_progress', 'SELECT COUNT(1) FROM user_progress WHERE user_id=:uid'),
            ('exams', 'SELECT COUNT(1) FROM exams WHERE user_id=:uid'),
            ('chat_messages(发送者)', 'SELECT COUNT(1) FROM chat_messages WHERE sender_id=:uid'),
            ('chat_members(会话成员)', 'SELECT COUNT(1) FROM chat_members WHERE user_id=:uid'),
            ('user_remarks(备注-owner)', 'SELECT COUNT(1) FROM user_remarks WHERE owner_user_id=:uid'),
            ('user_remarks(备注-target)', 'SELECT COUNT(1) FROM user_remarks WHERE target_user_id=:uid'),
            ('notification_dismissals', 'SELECT COUNT(1) FROM notification_dismissals WHERE user_id=:uid'),
            ('notifications(创建者)', 'SELECT COUNT(1) FROM notifications WHERE created_by=:uid'),
            ('questions(出题人)', 'SELECT COUNT(1) FROM questions WHERE created_by=:uid'),
            ('code_submissions', 'SELECT COUNT(1) FROM code_submissions WHERE user_id=:uid'),
            ('coding_statistics', 'SELECT COUNT(1) FROM coding_statistics WHERE user_id=:uid'),
            ('user_coding_stats', 'SELECT COUNT(1) FROM user_coding_stats WHERE user_id=:uid'),
            ('code_drafts', 'SELECT COUNT(1) FROM code_drafts WHERE user_id=:uid'),
            ('user_subjects', 'SELECT COUNT(1) FROM user_subjects WHERE user_id=:uid'),
            ('user_quiz_stats', 'SELECT COUNT(1) FROM user_quiz_stats WHERE user_id=:uid'),
            ('email_verification_codes', 'SELECT COUNT(1) FROM email_verification_codes WHERE user_id=:uid'),
            ('popup_dismissals', 'SELECT COUNT(1) FROM popup_dismissals WHERE user_id=:uid'),
            ('edu_schedule_credentials', 'SELECT COUNT(1) FROM edu_schedule_credentials WHERE user_id=:uid'),
            ('edu_schedule_snapshots', 'SELECT COUNT(1) FROM edu_schedule_snapshots WHERE user_id=:uid'),
            ('edu_grade_snapshots', 'SELECT COUNT(1) FROM edu_grade_snapshots WHERE user_id=:uid'),
        ]
        details = []
        for name, sql in checks:
            try:
                c = db.session.execute(text(sql), {'uid': uid}).scalar()
                if c and int(c) > 0:
                    details.append({'table': name, 'count': int(c)})
            except Exception:
                pass
        return details

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能删除自己'}), 400

    try:
        u = db.session.execute(text('SELECT id, is_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not u:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        if u._mapping['is_admin']:
            admin_count = db.session.execute(text('SELECT COUNT(1) FROM users WHERE is_admin = true')).scalar()
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能删除最后一个管理员'}), 400

        uid_p = {'uid': user_id}
        uid2_p = {'uid1': user_id, 'uid2': user_id}

        # 级联清理所有关联数据（按依赖顺序删除，避免外键约束错误）
        # 1. 删除考试相关数据
        db.session.execute(text('DELETE FROM exam_questions WHERE exam_id IN (SELECT id FROM exams WHERE user_id=:uid)'), uid_p)
        db.session.execute(text('DELETE FROM exams WHERE user_id=:uid'), uid_p)

        # 2. 删除用户基础数据
        db.session.execute(text('DELETE FROM favorites WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM mistakes WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM user_answers WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM user_progress WHERE user_id=:uid'), uid_p)

        # 3. 删除聊天相关数据
        db.session.execute(text('DELETE FROM chat_messages WHERE sender_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM chat_members WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM user_remarks WHERE owner_user_id=:uid1 OR target_user_id=:uid2'), uid2_p)

        # 4. 删除通知相关数据
        db.session.execute(text('DELETE FROM notification_dismissals WHERE user_id=:uid'), uid_p)

        # 5. 删除编程相关数据
        db.session.execute(text('DELETE FROM code_submissions WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM coding_statistics WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM user_coding_stats WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM code_drafts WHERE user_id=:uid'), uid_p)

        # 6. 删除其他用户数据
        db.session.execute(text('DELETE FROM user_subjects WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM user_quiz_stats WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM email_verification_codes WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM popup_dismissals WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM edu_schedule_credentials WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM edu_schedule_snapshots WHERE user_id=:uid'), uid_p)
        db.session.execute(text('DELETE FROM edu_grade_snapshots WHERE user_id=:uid'), uid_p)

        # 7. 更新引用该用户的字段（SET NULL 处理）
        db.session.execute(text('UPDATE questions SET created_by=NULL WHERE created_by=:uid'), uid_p)
        db.session.execute(text('UPDATE notifications SET created_by=NULL WHERE created_by=:uid'), uid_p)
        db.session.execute(text('UPDATE popups SET created_by=NULL WHERE created_by=:uid'), uid_p)
        db.session.execute(text('UPDATE popup_views SET user_id=NULL WHERE user_id=:uid'), uid_p)
        db.session.execute(text('UPDATE system_config SET updated_by=NULL WHERE updated_by=:uid'), uid_p)
        db.session.execute(text('UPDATE user_subjects SET restricted_by=NULL WHERE restricted_by=:uid'), uid_p)

        # 8. 最后删除用户本身
        db.session.execute(text('DELETE FROM users WHERE id=:uid'), uid_p)
        db.session.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status': 'success', 'message': '用户已删除'})

    except IntegrityError as e:
        db.session.rollback()
        msg = str(e)
        if 'foreign key' in msg.lower() or 'FOREIGN KEY' in msg:
            details = _ref_counts(user_id)
            if details:
                detail_str = '、'.join([f"{x['table']}({x['count']})" for x in details])
                return jsonify({
                    'status': 'error',
                    'message': f"删除失败：该用户仍有关联数据，请先处理后再删除。关联项：{detail_str}",
                    'details': details
                }), 400
            return jsonify({
                'status': 'error',
                'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。',
                'details': []
            }), 400
        return jsonify({'status': 'error', 'message': msg}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    """创建用户"""
    payload = request.json or {}
    username = (payload.get('username') or '').strip()
    password = payload.get('password') or ''
    is_admin = True if payload.get('is_admin') in (1, True, '1', 'true') else False

    if not username or not password:
        return jsonify({'status':'error','message':'用户名和密码不能为空'}), 400

    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400

    ph = generate_password_hash(password)

    try:
        db.session.execute(
            text('INSERT INTO users (username, password_hash, is_admin, is_locked, session_version) VALUES (:username, :ph, :is_admin, false, 0)'),
            {'username': username, 'ph': ph, 'is_admin': is_admin}
        )
        db.session.commit()
        return jsonify({'status':'success','message':'用户创建成功'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status':'error','message':'用户名已存在'}), 409



@admin_api_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """重置用户密码"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400
    
    payload = request.json or {}
    new = payload.get('new_password') or ''
    
    valid, msg = validate_password(new)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400
    
    ph = generate_password_hash(new)

    try:
        result = db.session.execute(
            text('UPDATE users SET password_hash=:ph, has_password_set=true, session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'),
            {'ph': ph, 'uid': user_id}
        )
        if result.rowcount == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        db.session.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'重置密码成功（已强制下线）'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error','message':str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_lock', methods=['POST'])
@admin_required
def admin_toggle_lock(user_id):
    """切换锁定状态"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    try:
        # 切换锁定状态，增加会话版本，清空 last_active 使其立即显示离线
        result = db.session.execute(
            text('UPDATE users SET is_locked = CASE WHEN COALESCE(is_locked, false) = true THEN false ELSE true END, session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=:uid'),
            {'uid': user_id}
        )
        if result.rowcount == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        db.session.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'锁定状态已切换，并已强制下线'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error','message':str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/force_logout', methods=['POST'])
@admin_required
def admin_force_logout(user_id):
    """强制用户下线"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    try:
        # 增加会话版本，清空 last_active 使其立即显示离线
        result = db.session.execute(text('UPDATE users SET session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=:uid'), {'uid': user_id})
        if result.rowcount == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        db.session.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'已强制下线该用户'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error','message':str(e)}), 500


# 页面路由
# 页面路由已迁移到pages.py



@admin_api_bp.route('/users/export')
@admin_required
def admin_export_users():
    """导出用户CSV"""
    rows = db.session.execute(
        text('SELECT id, username, is_admin, is_locked, created_at FROM users ORDER BY id')
    ).fetchall()

    out = '\ufeff' + 'id,username,is_admin,is_locked,created_at\n'
    for r in rows:
        m = r._mapping
        out += ','.join([
            str(m['id']),
            csv_escape(m['username']),
            '1' if m['is_admin'] else '0',
            '1' if (m['is_locked'] or 0) else '0',
            csv_escape(m['created_at'])
        ]) + '\n'
    
    return out, 200, {
        'Content-Type':'text/csv; charset=utf-8',
        'Content-Disposition':'attachment; filename=users.csv'
    }
