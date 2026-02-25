# -*- coding: utf-8 -*-
"""表情回应 API"""
from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from ...services import reaction_service


@forum_api_bp.route('/reactions', methods=['GET'])
@auth_required
def api_get_reactions():
    """获取目标的表情回应"""
    try:
        target_type = request.args.get('target_type', '')
        target_id = request.args.get('target_id', 0, type=int)
        if target_type not in ('post', 'comment') or not target_id:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400

        uid = current_user_id()
        reactions = reaction_service.get_reactions(target_type, target_id)
        user_emojis = reaction_service.get_user_reactions(target_type, target_id, uid)
        return jsonify({'status': 'success', 'data': {
            'reactions': reactions, 'user_emojis': user_emojis,
        }})
    except Exception as e:
        current_app.logger.error(f"获取表情回应失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取失败'}), 500


@forum_api_bp.route('/reactions', methods=['POST'])
@auth_required
def api_toggle_reaction():
    """切换表情回应"""
    try:
        data = request.get_json(silent=True) or {}
        target_type = data.get('target_type', '')
        target_id = data.get('target_id')
        emoji = (data.get('emoji') or '').strip()

        if target_type not in ('post', 'comment') or not target_id or not emoji:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400
        if len(emoji) > 20:
            return jsonify({'status': 'error', 'message': '表情无效'}), 400

        uid = current_user_id()
        added = reaction_service.toggle_reaction(uid, target_type, target_id, emoji)
        return jsonify({'status': 'success', 'data': {'added': added, 'emoji': emoji}})
    except Exception as e:
        current_app.logger.error(f"表情回应操作失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '操作失败'}), 500
