# -*- coding: utf-8 -*-
"""互动通知 API — 挂载到 chat_api_bp"""
from flask import jsonify, request, session

from .api import chat_api_bp
from app.modules.forum.services import interaction_service


@chat_api_bp.route('/chat/interactions')
def api_interactions():
    """互动通知列表"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session['user_id'])
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    data = interaction_service.get_notifications(uid, page, per_page)
    return jsonify({'status': 'success', 'data': data})


@chat_api_bp.route('/chat/interactions/read', methods=['POST'])
def api_interactions_read():
    """标记互动通知已读"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session['user_id'])
    data = request.get_json(silent=True) or {}
    ids = data.get('ids')

    if ids and isinstance(ids, list):
        ids = [int(i) for i in ids if i]
    else:
        ids = None

    count = interaction_service.mark_read(uid, ids)
    return jsonify({'status': 'success', 'data': {'marked': count}})


@chat_api_bp.route('/chat/interactions/unread_count')
def api_interactions_unread_count():
    """未读互动通知数"""
    if not session.get('user_id'):
        return jsonify({'status': 'success', 'data': {'count': 0}})

    uid = int(session['user_id'])
    count = interaction_service.get_unread_count(uid)
    return jsonify({'status': 'success', 'data': {'count': count}})
