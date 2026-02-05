# -*- coding: utf-8 -*-
"""Admin API routes - popups."""

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


@admin_api_bp.route('/popups', methods=['GET'])
def admin_api_popups_list():
    """获取所有弹窗列表"""
    conn = get_db()
    rows = conn.execute('''
        SELECT p.id, p.title, p.content, p.popup_type, p.priority, p.is_active,
               p.start_at, p.end_at, p.created_at, p.updated_at,
               u.username as created_by_name
        FROM popups p
        LEFT JOIN users u ON p.created_by = u.id
        ORDER BY p.priority DESC, p.created_at DESC
    ''').fetchall()

    return jsonify({
        'status': 'success',
        'popups': [dict(row) for row in rows]
    })



@admin_api_bp.route('/popups', methods=['POST'])
def admin_api_popups_create():
    """创建弹窗"""
    from app.modules.popups.schemas import PopupCreateSchema
    from datetime import datetime
    
    # 允许管理员和通知管理员创建弹窗
    is_admin_user = session.get('is_admin')
    is_notification_admin_user = session.get('is_notification_admin')
    if not (is_admin_user or is_notification_admin_user):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        data = request.json or {}
        # 使用Pydantic验证
        schema = PopupCreateSchema(**data)
        
        conn = get_db()
        cursor = conn.execute('''
            INSERT INTO popups (title, content, popup_type, priority, is_active, start_at, end_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            schema.title,
            schema.content,
            schema.popup_type,
            schema.priority,
            1 if schema.is_active else 0,
            schema.start_at.isoformat() if schema.start_at else None,
            schema.end_at.isoformat() if schema.end_at else None,
            session.get('user_id')
        ))
        new_id = cursor.lastrowid
        conn.commit()

        return jsonify({'status': 'success', 'message': '弹窗创建成功', 'id': new_id})
    except Exception as e:
        import traceback
        current_app.logger.error(f'创建弹窗失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/<int:pid>', methods=['GET'])
def admin_api_popups_get(pid):
    """获取单个弹窗"""
    conn = get_db()
    row = conn.execute('''
        SELECT p.id, p.title, p.content, p.popup_type, p.priority, p.is_active,
               p.start_at, p.end_at, p.created_at, p.updated_at, p.created_by,
               u.username as created_by_name
        FROM popups p
        LEFT JOIN users u ON p.created_by = u.id
        WHERE p.id = ?
    ''', (pid,)).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404

    return jsonify({'status': 'success', 'popup': dict(row)})



@admin_api_bp.route('/popups/<int:pid>', methods=['PUT'])
def admin_api_popups_update(pid):
    """更新弹窗"""
    from app.modules.popups.schemas import PopupUpdateSchema
    
    # 允许管理员和通知管理员更新弹窗
    is_admin_user = session.get('is_admin')
    is_notification_admin_user = session.get('is_notification_admin')
    if not (is_admin_user or is_notification_admin_user):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        data = request.json or {}
        schema = PopupUpdateSchema(**data)
        
        conn = get_db()
        
        # 构建更新字段
        updates = []
        values = []
        
        if schema.title is not None:
            updates.append('title = ?')
            values.append(schema.title)
        if schema.content is not None:
            updates.append('content = ?')
            values.append(schema.content)
        if schema.popup_type is not None:
            updates.append('popup_type = ?')
            values.append(schema.popup_type)
        if schema.is_active is not None:
            updates.append('is_active = ?')
            values.append(1 if schema.is_active else 0)
        if schema.priority is not None:
            updates.append('priority = ?')
            values.append(schema.priority)
        if schema.start_at is not None:
            updates.append('start_at = ?')
            values.append(schema.start_at.isoformat() if schema.start_at else None)
        if schema.end_at is not None:
            updates.append('end_at = ?')
            values.append(schema.end_at.isoformat() if schema.end_at else None)
        
        if not updates:
            return jsonify({'status': 'error', 'message': '没有要更新的字段'}), 400
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        values.append(pid)
        
        sql = f'UPDATE popups SET {", ".join(updates)} WHERE id = ?'
        conn.execute(sql, values)
        
        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404

        conn.commit()
        return jsonify({'status': 'success', 'message': '弹窗更新成功'})
    except Exception as e:
        import traceback
        current_app.logger.error(f'更新弹窗失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/<int:pid>', methods=['DELETE'])
def admin_api_popups_delete(pid):
    """删除弹窗"""
    # 允许管理员和通知管理员删除弹窗
    is_admin_user = session.get('is_admin')
    is_notification_admin_user = session.get('is_notification_admin')
    if not (is_admin_user or is_notification_admin_user):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    conn = get_db()
    try:
        # 先删除关联的记录
        conn.execute('DELETE FROM popup_views WHERE popup_id = ?', (pid,))
        conn.execute('DELETE FROM popup_dismissals WHERE popup_id = ?', (pid,))
        conn.execute('DELETE FROM popups WHERE id = ?', (pid,))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404

        conn.commit()
        return jsonify({'status': 'success', 'message': '弹窗删除成功'})
    except Exception as e:
        import traceback
        current_app.logger.error(f'删除弹窗失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/stats', methods=['GET'])
def admin_api_popups_stats():
    """获取所有弹窗的统计信息"""
    from app.modules.popups.services.popup_service import PopupService
    
    # 允许管理员和通知管理员查看统计信息
    is_admin_user = session.get('is_admin')
    is_notification_admin_user = session.get('is_notification_admin')
    if not (is_admin_user or is_notification_admin_user):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        stats_list = PopupService.get_all_popups_stats()
        return jsonify({
            'status': 'success',
            'stats': stats_list
        })
    except Exception as e:
        import traceback
        current_app.logger.error(f'获取弹窗统计失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/<int:pid>/stats', methods=['GET'])
def admin_api_popup_stats(pid):
    """获取单个弹窗的统计信息"""
    from app.modules.popups.services.popup_service import PopupService
    
    # 允许管理员和通知管理员查看统计信息
    is_admin_user = session.get('is_admin')
    is_notification_admin_user = session.get('is_notification_admin')
    if not (is_admin_user or is_notification_admin_user):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        stats = PopupService.get_popup_stats(pid)
        if not stats:
            return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        import traceback
        current_app.logger.error(f'获取弹窗统计失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


