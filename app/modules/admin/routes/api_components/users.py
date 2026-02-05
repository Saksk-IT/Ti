# -*- coding: utf-8 -*-
"""Admin API routes - users & permissions."""

import datetime
import io
import json
import os
import sqlite3
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
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp


@admin_api_bp.route('/users')
@limiter.exempt
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
        
        conn = get_db()
        where = 'WHERE 1=1'
        params = []
        
        if search:
            where += ' AND username LIKE ?'
            params.append(f'%{search}%')
        
        total = conn.execute(f'SELECT COUNT(1) FROM users {where}', params).fetchone()[0]
        
        # 检查 is_subject_admin 和 is_notification_admin 字段是否存在，如果不存在则自动添加
        has_subject_admin_field = False
        has_notification_admin_field = False
        try:
            user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            has_subject_admin_field = 'is_subject_admin' in user_cols
            has_notification_admin_field = 'is_notification_admin' in user_cols
            
            # 如果字段不存在，尝试添加
            if not has_subject_admin_field:
                try:
                    conn.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
                    conn.commit()
                    has_subject_admin_field = True
                    current_app.logger.info('已自动添加 is_subject_admin 字段')
                except Exception as e:
                    current_app.logger.warning(f'添加 is_subject_admin 字段失败（可能已存在）: {e}')
                    # 即使添加失败，也尝试查询，可能字段已经存在
                    try:
                        test_row = conn.execute('SELECT is_subject_admin FROM users LIMIT 1').fetchone()
                        has_subject_admin_field = True
                    except Exception:
                        has_subject_admin_field = False
            if not has_notification_admin_field:
                try:
                    conn.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
                    conn.commit()
                    has_notification_admin_field = True
                    current_app.logger.info('已自动添加 is_notification_admin 字段')
                except Exception as e:
                    current_app.logger.warning(f'添加 is_notification_admin 字段失败（可能已存在）: {e}')
                    try:
                        test_row = conn.execute('SELECT is_notification_admin FROM users LIMIT 1').fetchone()
                        has_notification_admin_field = True
                    except Exception:
                        has_notification_admin_field = False
        except Exception as e:
            current_app.logger.warning(f'检查用户字段失败: {e}')
            # 如果检查失败，尝试直接查询，如果失败则使用不包含该字段的查询
            try:
                test_row = conn.execute('SELECT is_subject_admin FROM users LIMIT 1').fetchone()
                has_subject_admin_field = True
            except Exception:
                has_subject_admin_field = False
            try:
                test_row = conn.execute('SELECT is_notification_admin FROM users LIMIT 1').fetchone()
                has_notification_admin_field = True
            except Exception:
                has_notification_admin_field = False
        
        # 根据字段是否存在构建查询（使用子查询避免GROUP BY复杂性）
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
        # 检查是否是权限管理页面的请求（通过referrer或特殊参数）
        is_permissions_page = request.referrer and '/admin/permissions' in request.referrer
        use_priority_sort = request.args.get('priority_sort', '').lower() == 'true' or is_permissions_page
        
        if use_priority_sort:
            # 权限优先级排序：管理员 > 通知管理员 > 科目管理员 > 普通用户
            # 构建排序字段
            priority_fields = ['u.is_admin DESC']
            # 通知管理员排在科目管理员之前
            if has_notification_admin_field:
                priority_fields.append('u.is_notification_admin DESC')
            if has_subject_admin_field:
                priority_fields.append('u.is_subject_admin DESC')
            priority_order = ', '.join(priority_fields)
            # 先按权限优先级，再按其他字段排序
            order_by = f'{priority_order}, u.{sort_map[sort]} {order}'
        else:
            order_by = f'u.{sort_map[sort]} {order}'
        
        rows = conn.execute(
            f'SELECT {select_with_count} FROM users u {where_for_query} ORDER BY {order_by} LIMIT ? OFFSET ?',
            params + [size, offset]
        ).fetchall()
        
        from datetime import datetime, timedelta
        from app.core.utils.time_utils import now_bj
        
        data = []
        for r in rows:
            # 判断在线状态：5分钟内有活动视为在线
            is_online = False
            last_active_val = r['last_active'] if 'last_active' in r.keys() else None
            if last_active_val:
                try:
                    # SQLite 的 CURRENT_TIMESTAMP 格式: "YYYY-MM-DD HH:MM:SS" (UTC时间)
                    last_active_str = last_active_val.replace('T', ' ').split('.')[0]
                    last_active = datetime.strptime(last_active_str, '%Y-%m-%d %H:%M:%S')
                    # SQLite CURRENT_TIMESTAMP 是 UTC，需要转换为本地时间
                    is_online = (now_bj() - last_active) < timedelta(minutes=5)
                except Exception as e:
                    current_app.logger.warning(f'解析 last_active 失败: {last_active_val}, 错误: {e}')
            
            # sqlite3.Row 对象使用字典式访问，但不是真正的字典，需要用 in 检查或直接访问
            data.append({
                'id': r['id'],
                'username': r['username'],
                'is_admin': bool(r['is_admin']) if 'is_admin' in r.keys() else False,
                'is_subject_admin': bool(r['is_subject_admin']) if has_subject_admin_field and 'is_subject_admin' in r.keys() else False,
                'is_notification_admin': bool(r['is_notification_admin']) if has_notification_admin_field and 'is_notification_admin' in r.keys() else False,
                'is_locked': bool(r['is_locked']) if 'is_locked' in r.keys() else False,
                'created_at': r['created_at'] if 'created_at' in r.keys() else '',
                'is_online': is_online,
                'last_active': last_active_val,
                'restricted_subjects_count': r['restricted_subjects_count'] or 0
            })
        
        # 统计所有用户的全局数据（不受分页和搜索影响）
        # 获取所有用户的字段用于统计，根据字段是否存在决定查询字段
        stats_fields = ['is_admin', 'is_locked', 'last_active']
        if has_subject_admin_field:
            stats_fields.append('is_subject_admin')
        if has_notification_admin_field:
            stats_fields.append('is_notification_admin')
        all_users_stats_query = f'SELECT {", ".join(stats_fields)} FROM users'
        all_users_rows = conn.execute(all_users_stats_query).fetchall()
        
        # 统计全局数据
        online_count = 0
        admin_count = 0
        subject_admin_count = 0
        notification_admin_count = 0
        locked_count = 0
        
        for user_row in all_users_rows:
            # 统计管理员
            if user_row['is_admin']:
                admin_count += 1
            # 统计科目管理员（不包括管理员）
            elif has_subject_admin_field and 'is_subject_admin' in user_row.keys() and user_row['is_subject_admin']:
                subject_admin_count += 1
            # 统计通知管理员（不包括管理员）
            if has_notification_admin_field and 'is_notification_admin' in user_row.keys() and user_row['is_notification_admin']:
                notification_admin_count += 1
            # 统计锁定用户
            if user_row['is_locked']:
                locked_count += 1
            # 统计在线用户（5分钟内有活动）
            last_active_val = user_row['last_active'] if 'last_active' in user_row.keys() else None
            if last_active_val:
                try:
                    last_active_str = last_active_val.replace('T', ' ').split('.')[0]
                    last_active = datetime.strptime(last_active_str, '%Y-%m-%d %H:%M:%S')
                    if (now_bj() - last_active) < timedelta(minutes=5):
                        online_count += 1
                except Exception:
                    pass
        
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
def toggle_admin_status(user_id):
    """切换管理员权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '管理员不能对自己进行操作'}), 400
    
    conn = get_db()
    try:
        row = conn.execute('SELECT is_admin, username FROM users WHERE id=?', (user_id,)).fetchone()
        
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        target_is_admin = bool(row['is_admin'])
        
        if target_is_admin:
            admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能取消最后一个管理员的权限'}), 400
        
        conn.execute('UPDATE users SET is_admin = NOT is_admin WHERE id = ?', (user_id,))
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=?', (user_id,))
        conn.commit()
        invalidate_user_state(int(user_id))
        
        current_app.logger.info(f'管理员权限切换 - 目标用户: {row["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_subject_admin', methods=['POST'])
def toggle_subject_admin_status(user_id):
    """切换科目管理员权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    conn = get_db()
    try:
        row = conn.execute('SELECT is_subject_admin, username FROM users WHERE id=?', (user_id,)).fetchone()
        
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        conn.execute('UPDATE users SET is_subject_admin = NOT is_subject_admin WHERE id = ?', (user_id,))
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=?', (user_id,))
        conn.commit()
        invalidate_user_state(int(user_id))
        
        current_app.logger.info(f'科目管理员权限切换 - 目标用户: {row["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '科目管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换科目管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_notification_admin', methods=['POST'])
def toggle_notification_admin_status(user_id):
    """切换通知管理员权限"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    conn = get_db()
    try:
        # 检查 is_notification_admin 字段是否存在，如果不存在则自动添加
        has_notification_admin_field = False
        try:
            user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            has_notification_admin_field = 'is_notification_admin' in user_cols
            
            # 如果字段不存在，尝试添加
            if not has_notification_admin_field:
                try:
                    conn.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
                    conn.commit()
                    has_notification_admin_field = True
                    current_app.logger.info('已自动添加 is_notification_admin 字段')
                except Exception as e:
                    current_app.logger.warning(f'添加 is_notification_admin 字段失败（可能已存在）: {e}')
                    # 即使添加失败，也尝试查询，可能字段已经存在
                    try:
                        test_row = conn.execute('SELECT is_notification_admin FROM users LIMIT 1').fetchone()
                        has_notification_admin_field = True
                    except Exception:
                        has_notification_admin_field = False
        except Exception as e:
            current_app.logger.warning(f'检查 is_notification_admin 字段失败: {e}')
            # 如果检查失败，尝试直接查询，如果失败则使用不包含该字段的查询
            try:
                test_row = conn.execute('SELECT is_notification_admin FROM users LIMIT 1').fetchone()
                has_notification_admin_field = True
            except Exception:
                has_notification_admin_field = False
        
        # 根据字段是否存在构建查询
        if has_notification_admin_field:
            row = conn.execute('SELECT is_notification_admin, username FROM users WHERE id=?', (user_id,)).fetchone()
        else:
            row = conn.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
        
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 如果字段存在，执行更新；否则先添加字段再设置
        if has_notification_admin_field:
            conn.execute('UPDATE users SET is_notification_admin = NOT is_notification_admin WHERE id = ?', (user_id,))
        else:
            # 字段不存在，先添加字段，然后设置为1（因为默认是0，所以切换后应该是1）
            conn.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
            conn.execute('UPDATE users SET is_notification_admin = 1 WHERE id = ?', (user_id,))
        
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=?', (user_id,))
        conn.commit()
        invalidate_user_state(int(user_id))
        
        current_app.logger.info(f'通知管理员权限切换 - 目标用户: {row["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '通知管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        import traceback
        current_app.logger.error(f'切换通知管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'}), 500


# ============== 权限管理 ==============


@admin_api_bp.route('/permissions/batch', methods=['POST'])
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
    
    conn = get_db()
    try:
        # 检查字段是否存在
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_subject_admin_field = 'is_subject_admin' in user_cols
        has_notification_admin_field = 'is_notification_admin' in user_cols
        
        # 如果字段不存在，尝试添加
        if permission_type == 'subject_admin' and not has_subject_admin_field:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
                conn.commit()
                has_subject_admin_field = True
            except Exception:
                pass
        
        if permission_type == 'notification_admin' and not has_notification_admin_field:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
                conn.commit()
                has_notification_admin_field = True
            except Exception:
                pass
        
        # 验证用户是否存在
        placeholders = ','.join(['?'] * len(user_ids))
        existing_users = conn.execute(
            f'SELECT id, username FROM users WHERE id IN ({placeholders})',
            user_ids
        ).fetchall()
        
        if len(existing_users) != len(user_ids):
            return jsonify({'status': 'error', 'message': '部分用户不存在'}), 400
        
        # 批量更新权限
        value = 1 if enable else 0
        if permission_type == 'subject_admin':
            conn.execute(
                f'UPDATE users SET is_subject_admin = ? WHERE id IN ({placeholders})',
                [value] + user_ids
            )
        elif permission_type == 'notification_admin':
            conn.execute(
                f'UPDATE users SET is_notification_admin = ? WHERE id IN ({placeholders})',
                [value] + user_ids
            )
        
        # 更新所有受影响用户的session_version，强制刷新会话
        conn.execute(
            f'UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id IN ({placeholders})',
            user_ids
        )
        
        conn.commit()
        for uid in user_ids:
            try:
                invalidate_user_state(int(uid))
            except Exception:
                pass
        
        # 记录操作日志
        action = '设为' if enable else '取消'
        permission_name = '科目管理员' if permission_type == 'subject_admin' else '通知管理员'
        usernames = [u['username'] for u in existing_users]
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
        import traceback
        current_app.logger.error(f'批量设置权限失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'}), 500



@admin_api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户"""
    from app.core.utils.user_state_cache import invalidate_user_state

    def _ref_counts(uid: int):
        """统计哪些表还在引用该用户，用于给管理员友好提示"""
        # 说明：这里列出的是数据库里对 users.id 有外键/逻辑关联的主要表
        checks = [
            ('favorites', 'SELECT COUNT(1) FROM favorites WHERE user_id=?'),
            ('mistakes', 'SELECT COUNT(1) FROM mistakes WHERE user_id=?'),
            ('user_answers', 'SELECT COUNT(1) FROM user_answers WHERE user_id=?'),
            ('user_progress', 'SELECT COUNT(1) FROM user_progress WHERE user_id=?'),
            ('exams', 'SELECT COUNT(1) FROM exams WHERE user_id=?'),
            ('chat_messages(发送者)', 'SELECT COUNT(1) FROM chat_messages WHERE sender_id=?'),
            ('chat_members(会话成员)', 'SELECT COUNT(1) FROM chat_members WHERE user_id=?'),
            ('user_remarks(备注-owner)', 'SELECT COUNT(1) FROM user_remarks WHERE owner_user_id=?'),
            ('user_remarks(备注-target)', 'SELECT COUNT(1) FROM user_remarks WHERE target_user_id=?'),
            ('notification_dismissals', 'SELECT COUNT(1) FROM notification_dismissals WHERE user_id=?'),
            ('notifications(创建者)', 'SELECT COUNT(1) FROM notifications WHERE created_by=?'),
            ('questions(出题人)', 'SELECT COUNT(1) FROM questions WHERE created_by=?'),
            ('code_submissions', 'SELECT COUNT(1) FROM code_submissions WHERE user_id=?'),
            ('coding_statistics', 'SELECT COUNT(1) FROM coding_statistics WHERE user_id=?'),
            ('user_coding_stats', 'SELECT COUNT(1) FROM user_coding_stats WHERE user_id=?'),
            ('code_drafts', 'SELECT COUNT(1) FROM code_drafts WHERE user_id=?'),
            ('user_subjects', 'SELECT COUNT(1) FROM user_subjects WHERE user_id=?'),
            ('user_quiz_stats', 'SELECT COUNT(1) FROM user_quiz_stats WHERE user_id=?'),
            ('email_verification_codes', 'SELECT COUNT(1) FROM email_verification_codes WHERE user_id=?'),
            ('popup_dismissals', 'SELECT COUNT(1) FROM popup_dismissals WHERE user_id=?'),
        ]
        details = []
        for name, sql in checks:
            try:
                c = conn.execute(sql, (uid,)).fetchone()[0]
                if c and int(c) > 0:
                    details.append({'table': name, 'count': int(c)})
            except Exception:
                # 兼容：有些表可能在老库不存在/字段不同，忽略即可
                pass
        return details

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能删除自己'}), 400

    conn = get_db()
    try:
        u = conn.execute('SELECT id, is_admin, username FROM users WHERE id=?', (user_id,)).fetchone()

        if not u:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        if u['is_admin']:
            admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能删除最后一个管理员'}), 400

        # 级联清理所有关联数据（按依赖顺序删除，避免外键约束错误）
        # 注意：即使某些表有 ON DELETE CASCADE，手动删除更可靠，因为可能数据库创建时外键未启用
        
        # 1. 删除考试相关数据（exams 表没有 CASCADE，必须先删除）
        conn.execute('DELETE FROM exam_questions WHERE exam_id IN (SELECT id FROM exams WHERE user_id=?)', (user_id,))
        conn.execute('DELETE FROM exams WHERE user_id=?', (user_id,))
        
        # 2. 删除用户基础数据
        conn.execute('DELETE FROM favorites WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM mistakes WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_answers WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_progress WHERE user_id=?', (user_id,))
        
        # 3. 删除聊天相关数据
        conn.execute('DELETE FROM chat_messages WHERE sender_id=?', (user_id,))
        conn.execute('DELETE FROM chat_members WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_remarks WHERE owner_user_id=? OR target_user_id=?', (user_id, user_id))
        
        # 4. 删除通知相关数据
        conn.execute('DELETE FROM notification_dismissals WHERE user_id=?', (user_id,))
        
        # 5. 删除编程相关数据
        conn.execute('DELETE FROM code_submissions WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM coding_statistics WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_coding_stats WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM code_drafts WHERE user_id=?', (user_id,))
        
        # 6. 删除其他用户数据
        conn.execute('DELETE FROM user_subjects WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_quiz_stats WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM email_verification_codes WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM popup_dismissals WHERE user_id=?', (user_id,))
        
        # 7. 更新引用该用户的字段（SET NULL 处理）
        conn.execute('UPDATE questions SET created_by=NULL WHERE created_by=?', (user_id,))
        conn.execute('UPDATE notifications SET created_by=NULL WHERE created_by=?', (user_id,))
        conn.execute('UPDATE popups SET created_by=NULL WHERE created_by=?', (user_id,))
        conn.execute('UPDATE popup_views SET user_id=NULL WHERE user_id=?', (user_id,))
        conn.execute('UPDATE system_config SET updated_by=NULL WHERE updated_by=?', (user_id,))
        conn.execute('UPDATE user_subjects SET restricted_by=NULL WHERE restricted_by=?', (user_id,))
        
        # 8. 最后删除用户本身
        conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status': 'success', 'message': '用户已删除'})

    except sqlite3.IntegrityError as e:
        conn.rollback()
        # 外键约束失败：返回“哪些表还在引用”
        msg = str(e)
        if 'FOREIGN KEY constraint failed' in msg:
            details = _ref_counts(user_id)
            if details:
                # 生成更易读的提示
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
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/users/create', methods=['POST'])
def admin_create_user():
    """创建用户"""
    payload = request.json or {}
    username = (payload.get('username') or '').strip()
    password = payload.get('password') or ''
    is_admin = 1 if payload.get('is_admin') in (1, True, '1', 'true') else 0
    
    if not username or not password:
        return jsonify({'status':'error','message':'用户名和密码不能为空'}), 400
    
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400
    
    ph = generate_password_hash(password)
    
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash, is_admin, is_locked, session_version) VALUES (?, ?, ?, 0, 0)',
            (username, ph, is_admin)
        )
        conn.commit()
        return jsonify({'status':'success','message':'用户创建成功'})
    except sqlite3.IntegrityError:
        return jsonify({'status':'error','message':'用户名已存在'}), 409



@admin_api_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
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
    
    conn = get_db()
    try:
        conn.execute(
            'UPDATE users SET password_hash=?, session_version = COALESCE(session_version,0) + 1 WHERE id=?',
            (ph, user_id)
        )
        if conn.total_changes == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        conn.commit()
        invalidate_user_state(int(user_id))
        
        return jsonify({'status':'success','message':'重置密码成功（已强制下线）'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/toggle_lock', methods=['POST'])
def admin_toggle_lock(user_id):
    """切换锁定状态"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    conn = get_db()
    try:
        # 切换锁定状态，增加会话版本，清空 last_active 使其立即显示离线
        conn.execute(
            'UPDATE users SET is_locked = CASE WHEN COALESCE(is_locked,0)=1 THEN 0 ELSE 1 END, session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=?',
            (user_id,)
        )
        if conn.total_changes == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        conn.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'锁定状态已切换，并已强制下线'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500



@admin_api_bp.route('/users/<int:user_id>/force_logout', methods=['POST'])
def admin_force_logout(user_id):
    """强制用户下线"""
    from app.core.utils.user_state_cache import invalidate_user_state

    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    conn = get_db()
    try:
        # 增加会话版本，清空 last_active 使其立即显示离线
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=?', (user_id,))
        if conn.total_changes == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        conn.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'已强制下线该用户'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


# 页面路由
# 页面路由已迁移到pages.py



@admin_api_bp.route('/users/export')
def admin_export_users():
    """导出用户CSV"""
    conn = get_db()
    rows = conn.execute(
        'SELECT id, username, is_admin, is_locked, created_at FROM users ORDER BY id'
    ).fetchall()
    
    def csv_escape(s):
        s = '' if s is None else str(s)
        if any(c in s for c in [',','"','\n','\r']):
            s = '"' + s.replace('"','""') + '"'
        return s
    
    out = '\ufeff' + 'id,username,is_admin,is_locked,created_at\n'
    for r in rows:
        out += ','.join([
            str(r['id']),
            csv_escape(r['username']),
            '1' if r['is_admin'] else '0',
            '1' if (r['is_locked'] or 0) else '0',
            csv_escape(r['created_at'])
        ]) + '\n'
    
    return out, 200, {
        'Content-Type':'text/csv; charset=utf-8',
        'Content-Disposition':'attachment; filename=users.csv'
    }


