# -*- coding: utf-8 -*-
"""投票 API"""
from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from ...services import poll_service


@forum_api_bp.route('/posts/<int:post_id>/poll', methods=['GET'])
@auth_required
def api_get_poll(post_id: int):
    """获取投票数据"""
    try:
        uid = current_user_id()
        data = poll_service.get_poll_data(post_id, uid)
        if not data:
            return jsonify({'status': 'error', 'message': '该帖子没有投票'}), 404
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error(f"获取投票数据失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>/poll/vote', methods=['POST'])
@auth_required
def api_cast_vote(post_id: int):
    """投票"""
    try:
        data = request.get_json(silent=True) or {}
        option_index = data.get('option_index')
        if option_index is None:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400

        uid = current_user_id()
        result = poll_service.cast_vote(post_id, uid, option_index)
        if 'error' in result:
            return jsonify({'status': 'error', 'message': result['error']}), 400
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        current_app.logger.error(f"投票失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '投票失败'}), 500
