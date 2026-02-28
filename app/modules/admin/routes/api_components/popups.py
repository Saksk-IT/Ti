# -*- coding: utf-8 -*-
"""Admin API routes - popups."""

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


@admin_api_bp.route('/popups', methods=['GET'])
@notification_admin_required
def admin_api_popups_list():
    """获取所有弹窗列表"""
    rows = db.session.execute(text('''
        SELECT p.id, p.title, p.content, p.popup_type, p.priority, p.is_active,
               p.start_at, p.end_at, p.created_at, p.updated_at,
               u.username as created_by_name
        FROM popups p
        LEFT JOIN users u ON p.created_by = u.id
        ORDER BY p.priority DESC, p.created_at DESC
    ''')).fetchall()

    return jsonify({
        'status': 'success',
        'popups': [dict(row._mapping) for row in rows]
    })



@admin_api_bp.route('/popups', methods=['POST'])
@notification_admin_required
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
        
        result = db.session.execute(text('''
            INSERT INTO popups (title, content, popup_type, priority, is_active, start_at, end_at, created_by)
            VALUES (:title, :content, :popup_type, :priority, :is_active, :start_at, :end_at, :created_by)
            RETURNING id
        '''), {
            'title': schema.title,
            'content': schema.content,
            'popup_type': schema.popup_type,
            'priority': schema.priority,
            'is_active': schema.is_active,
            'start_at': schema.start_at.isoformat() if schema.start_at else None,
            'end_at': schema.end_at.isoformat() if schema.end_at else None,
            'created_by': session.get('user_id')
        })
        new_id = result.scalar()
        db.session.commit()

        return jsonify({'status': 'success', 'message': '弹窗创建成功', 'id': new_id})
    except Exception as e:
        current_app.logger.error('创建弹窗失败', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/<int:pid>', methods=['GET'])
@notification_admin_required
def admin_api_popups_get(pid):
    """获取单个弹窗"""
    row = db.session.execute(text('''
        SELECT p.id, p.title, p.content, p.popup_type, p.priority, p.is_active,
               p.start_at, p.end_at, p.created_at, p.updated_at, p.created_by,
               u.username as created_by_name
        FROM popups p
        LEFT JOIN users u ON p.created_by = u.id
        WHERE p.id = :pid
    '''), {'pid': pid}).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404

    return jsonify({'status': 'success', 'popup': dict(row._mapping)})



@admin_api_bp.route('/popups/<int:pid>', methods=['PUT'])
@notification_admin_required
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
        
        # 构建更新字段
        updates = []
        params = {}

        if schema.title is not None:
            updates.append('title = :title')
            params['title'] = schema.title
        if schema.content is not None:
            updates.append('content = :content')
            params['content'] = schema.content
        if schema.popup_type is not None:
            updates.append('popup_type = :popup_type')
            params['popup_type'] = schema.popup_type
        if schema.is_active is not None:
            updates.append('is_active = :is_active')
            params['is_active'] = schema.is_active
        if schema.priority is not None:
            updates.append('priority = :priority')
            params['priority'] = schema.priority
        if schema.start_at is not None:
            updates.append('start_at = :start_at')
            params['start_at'] = schema.start_at.isoformat() if schema.start_at else None
        if schema.end_at is not None:
            updates.append('end_at = :end_at')
            params['end_at'] = schema.end_at.isoformat() if schema.end_at else None

        if not updates:
            return jsonify({'status': 'error', 'message': '没有要更新的字段'}), 400

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params['pid'] = pid

        sql = f'UPDATE popups SET {", ".join(updates)} WHERE id = :pid'
        result = db.session.execute(text(sql), params)

        if result.rowcount == 0:
            return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404

        db.session.commit()
        return jsonify({'status': 'success', 'message': '弹窗更新成功'})
    except Exception as e:
        current_app.logger.error('更新弹窗失败', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/<int:pid>', methods=['DELETE'])
@notification_admin_required
def admin_api_popups_delete(pid):
    """删除弹窗"""
    # 允许管理员和通知管理员删除弹窗
    is_admin_user = session.get('is_admin')
    is_notification_admin_user = session.get('is_notification_admin')
    if not (is_admin_user or is_notification_admin_user):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        # 先删除关联的记录
        db.session.execute(text('DELETE FROM popup_views WHERE popup_id = :pid'), {'pid': pid})
        db.session.execute(text('DELETE FROM popup_dismissals WHERE popup_id = :pid'), {'pid': pid})
        result = db.session.execute(text('DELETE FROM popups WHERE id = :pid'), {'pid': pid})

        if result.rowcount == 0:
            return jsonify({'status': 'error', 'message': '弹窗不存在'}), 404

        db.session.commit()
        return jsonify({'status': 'success', 'message': '弹窗删除成功'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error('删除弹窗失败', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/stats', methods=['GET'])
@notification_admin_required
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
        current_app.logger.error('获取弹窗统计失败', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/popups/<int:pid>/stats', methods=['GET'])
@notification_admin_required
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
        current_app.logger.error('获取弹窗统计失败', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


