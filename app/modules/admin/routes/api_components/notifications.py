# -*- coding: utf-8 -*-
"""Admin API routes - notifications."""

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


@admin_api_bp.route('/notifications', methods=['GET'])
def admin_api_notifications_list():
    """获取所有通知列表"""
    conn = get_db()
    rows = conn.execute('''
        SELECT n.id, n.title, n.content, n.n_type, n.priority, n.is_active,
               n.start_at, n.end_at, n.created_at, n.updated_at,
               u.username as created_by_name
        FROM notifications n
        LEFT JOIN users u ON n.created_by = u.id
        ORDER BY n.priority DESC, n.created_at DESC
    ''').fetchall()

    return jsonify({
        'status': 'success',
        'notifications': [dict(row) for row in rows]
    })



@admin_api_bp.route('/notifications', methods=['POST'])
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

    conn = get_db()
    try:
        cursor = conn.execute('''
            INSERT INTO notifications (title, content, n_type, priority, is_active, start_at, end_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, n_type, priority, is_active, start_at, end_at, uid))
        new_id = cursor.lastrowid
        conn.commit()

        return jsonify({'status': 'success', 'message': '通知创建成功', 'id': new_id})
    except Exception as e:
        import traceback
        current_app.logger.error(f'创建通知失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/notifications/<int:nid>', methods=['GET'])
def admin_api_notifications_get(nid):
    """获取单个通知"""
    conn = get_db()
    row = conn.execute('SELECT * FROM notifications WHERE id = ?', (nid,)).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '通知不存在'}), 404

    return jsonify({'status': 'success', 'notification': dict(row)})



@admin_api_bp.route('/notifications/<int:nid>', methods=['PUT'])
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

    conn = get_db()
    try:
        conn.execute('''
            UPDATE notifications SET
                title = ?, content = ?, n_type = ?, priority = ?,
                is_active = ?, start_at = ?, end_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, content, n_type, priority, is_active, start_at, end_at, nid))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        conn.commit()
        return jsonify({'status': 'success', 'message': '通知更新成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/notifications/<int:nid>', methods=['DELETE'])
def admin_api_notifications_delete(nid):
    """删除通知"""
    conn = get_db()
    try:
        # 先删除关联的关闭记录
        conn.execute('DELETE FROM notification_dismissals WHERE notification_id = ?', (nid,))
        conn.execute('DELETE FROM notifications WHERE id = ?', (nid,))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        conn.commit()
        return jsonify({'status': 'success', 'message': '通知删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_api_bp.route('/notifications/<int:nid>/toggle', methods=['POST'])
def admin_api_notifications_toggle(nid):
    """切换通知启用状态"""
    conn = get_db()
    try:
        conn.execute('''
            UPDATE notifications SET
                is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (nid,))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        conn.commit()

        row = conn.execute('SELECT is_active FROM notifications WHERE id = ?', (nid,)).fetchone()
        new_status = '启用' if row['is_active'] else '禁用'

        return jsonify({'status': 'success', 'message': f'通知已{new_status}', 'is_active': bool(row['is_active'])})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


