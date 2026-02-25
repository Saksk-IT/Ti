# -*- coding: utf-8 -*-
"""帖子转发到私聊 API"""
from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from ...services import forward_service


@forum_api_bp.route('/forward', methods=['POST'])
@auth_required
def api_forward_post():
    """转发帖子到私聊"""
    try:
        data = request.get_json(silent=True) or {}
        post_id = data.get('post_id')
        receiver_id = data.get('receiver_id')

        if not post_id or not receiver_id:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400

        uid = current_user_id()
        if uid == receiver_id:
            return jsonify({'status': 'error', 'message': '不能转发给自己'}), 400

        result = forward_service.forward_post_to_chat(post_id, uid, receiver_id)
        if 'error' in result:
            return jsonify({'status': 'error', 'message': result['error']}), 400
        return jsonify({'status': 'success', 'message': '转发成功',
                        'data': {'conversation_id': result['conversation_id']}})
    except Exception as e:
        current_app.logger.error(f"转发帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '转发失败'}), 500
