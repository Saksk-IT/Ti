# -*- coding: utf-8 -*-
"""Admin API routes - notifications."""

from flask import (
    current_app,
    jsonify,
    request,
    session,
)

from app.core.extensions import db
from sqlalchemy import text

from ..api_bp import admin_api_bp
from app.core.utils.decorators import notification_admin_required


@admin_api_bp.route('/notifications', methods=['GET'])
@notification_admin_required
def admin_api_notifications_list():
    """获取所有通知列表"""
    rows = db.session.execute(text('''
        SELECT n.id, n.title, n.content, n.n_type, n.priority, n.is_active,
               n.start_at, n.end_at, n.created_at, n.updated_at,
               u.username as created_by_name
        FROM notifications n
        LEFT JOIN users u ON n.created_by = u.id
        ORDER BY n.priority DESC, n.created_at DESC
    ''')).fetchall()

    return jsonify({
        'status': 'success',
        'notifications': [dict(row._mapping) for row in rows]
    })



@admin_api_bp.route('/notifications', methods=['POST'])
@notification_admin_required
def admin_api_notifications_create():
    """创建通知"""
    data = request.json or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    n_type = data.get('n_type', 'info')
    priority = data.get('priority', 0)
    is_active = 1 if data.get('is_active', True) else 0
    start_at = data.get('start_at') or None
    end_at = data.get('end_at') or None
    uid = session.get('user_id')

    if not title or not content:
        return jsonify({'status': 'error', 'message': '标题和内容不能为空'}), 400

    if n_type not in ('info', 'announcement', 'reminder', 'warning'):
        n_type = 'info'

    try:
        result = db.session.execute(text('''
            INSERT INTO notifications (title, content, n_type, priority, is_active, start_at, end_at, created_by)
            VALUES (:title, :content, :n_type, :priority, :is_active, :start_at, :end_at, :uid)
            RETURNING id
        '''), {
            'title': title, 'content': content, 'n_type': n_type,
            'priority': priority, 'is_active': bool(is_active),
            'start_at': start_at, 'end_at': end_at, 'uid': uid
        })
        new_id = result.scalar()
        db.session.commit()

        # --- SSE 广播：通知所有在线用户刷新未读数 ---
        try:
            from app.core.sse.event_bus import publish
            publish('notif_unread', None, {})
        except Exception:
            pass

        return jsonify({'status': 'success', 'message': '通知创建成功', 'id': new_id})
    except Exception as e:
        db.session.rollback()
        import traceback
        current_app.logger.error(f'创建通知失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/notifications/<int:nid>', methods=['GET'])
@notification_admin_required
def admin_api_notifications_get(nid):
    """获取单个通知"""
    row = db.session.execute(
        text('SELECT * FROM notifications WHERE id = :nid'), {'nid': nid}
    ).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '通知不存在'}), 404

    return jsonify({'status': 'success', 'notification': dict(row._mapping)})



@admin_api_bp.route('/notifications/<int:nid>', methods=['PUT'])
@notification_admin_required
def admin_api_notifications_update(nid):
    """更新通知"""
    data = request.json or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    n_type = data.get('n_type', 'info')
    priority = data.get('priority', 0)
    is_active = 1 if data.get('is_active', True) else 0
    start_at = data.get('start_at') or None
    end_at = data.get('end_at') or None

    if not title or not content:
        return jsonify({'status': 'error', 'message': '标题和内容不能为空'}), 400

    if n_type not in ('info', 'announcement', 'reminder', 'warning'):
        n_type = 'info'

    try:
        result = db.session.execute(text('''
            UPDATE notifications SET
                title = :title, content = :content, n_type = :n_type, priority = :priority,
                is_active = :is_active, start_at = :start_at, end_at = :end_at, updated_at = CURRENT_TIMESTAMP
            WHERE id = :nid
        '''), {
            'title': title, 'content': content, 'n_type': n_type,
            'priority': priority, 'is_active': bool(is_active),
            'start_at': start_at, 'end_at': end_at, 'nid': nid
        })

        if result.rowcount == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        db.session.commit()

        # --- SSE 广播：通知所有在线用户刷新未读数 ---
        try:
            from app.core.sse.event_bus import publish
            publish('notif_unread', None, {})
        except Exception:
            pass

        return jsonify({'status': 'success', 'message': '通知更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/notifications/<int:nid>', methods=['DELETE'])
@notification_admin_required
def admin_api_notifications_delete(nid):
    """删除通知"""
    try:
        # 先删除关联的关闭记录
        db.session.execute(text('DELETE FROM notification_dismissals WHERE notification_id = :nid'), {'nid': nid})
        result = db.session.execute(text('DELETE FROM notifications WHERE id = :nid'), {'nid': nid})

        if result.rowcount == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        db.session.commit()
        return jsonify({'status': 'success', 'message': '通知删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_api_bp.route('/notifications/<int:nid>/toggle', methods=['POST'])
@notification_admin_required
def admin_api_notifications_toggle(nid):
    """切换通知启用状态"""
    try:
        result = db.session.execute(text('''
            UPDATE notifications SET
                is_active = NOT is_active,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :nid
        '''), {'nid': nid})

        if result.rowcount == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        db.session.commit()

        # --- SSE 广播：通知所有在线用户刷新未读数 ---
        try:
            from app.core.sse.event_bus import publish
            publish('notif_unread', None, {})
        except Exception:
            pass

        row = db.session.execute(
            text('SELECT is_active FROM notifications WHERE id = :nid'), {'nid': nid}
        ).fetchone()
        new_status = '启用' if row._mapping['is_active'] else '禁用'

        return jsonify({'status': 'success', 'message': f'通知已{new_status}', 'is_active': bool(row._mapping['is_active'])})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


