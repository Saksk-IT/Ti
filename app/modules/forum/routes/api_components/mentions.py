# -*- coding: utf-8 -*-
"""@提及 + 未读数 API"""
from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from ...services import mention_service


@forum_api_bp.route('/mentions', methods=['GET'])
@auth_required
def api_get_mentions():
    """获取我的提及列表"""
    try:
        uid = current_user_id()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        data = mention_service.get_unread_mentions(uid, page, per_page)
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error(f"获取提及列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取失败'}), 500


@forum_api_bp.route('/mentions/read', methods=['POST'])
@auth_required
def api_mark_mentions_read():
    """标记提及为已读"""
    try:
        uid = current_user_id()
        data = request.get_json(silent=True) or {}
        mention_ids = data.get('mention_ids')  # None = 全部已读
        count = mention_service.mark_mentions_read(uid, mention_ids)
        return jsonify({'status': 'success', 'data': {'updated': count}})
    except Exception as e:
        current_app.logger.error(f"标记已读失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '操作失败'}), 500


@forum_api_bp.route('/unread', methods=['GET'])
@auth_required
def api_get_unread_count():
    """获取论坛未读数（提及）"""
    try:
        uid = current_user_id()
        count = mention_service.get_unread_count(uid)
        return jsonify({'status': 'success', 'data': {'unread_count': count}})
    except Exception as e:
        current_app.logger.error(f"获取未读数失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取失败'}), 500
