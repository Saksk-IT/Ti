# -*- coding: utf-8 -*-
"""版块 API"""
from flask import jsonify, request

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from app.modules.forum.services import board_service


@forum_api_bp.route('/boards', methods=['GET'])
@auth_required
def api_get_boards():
    """获取版块列表"""
    try:
        boards = board_service.get_boards()
        return jsonify({'status': 'success', 'data': {'boards': boards}})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"获取版块列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取版块列表失败'}), 500


@forum_api_bp.route('/boards/sync', methods=['POST'])
@auth_required
def api_sync_boards():
    """手动同步科目版块"""
    try:
        created = board_service.sync_subject_boards()
        return jsonify({'status': 'success', 'data': {'created': created}})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"同步版块失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '同步版块失败'}), 500
