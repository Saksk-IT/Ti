# -*- coding: utf-8 -*-
"""举报 API"""
from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required, current_user_id
from ...services import report_service


VALID_REASONS = ('spam', 'abuse', 'inappropriate', 'plagiarism', 'other')


@forum_api_bp.route('/report', methods=['POST'])
@auth_required
@limiter.limit("20 per minute;100 per day")
def api_create_report():
    """举报内容"""
    try:
        data = request.get_json(silent=True) or {}
        target_type = data.get('target_type', '')
        target_id = data.get('target_id')
        reason = data.get('reason', '')
        detail = (data.get('detail') or '').strip()

        if target_type not in ('post', 'comment') or not target_id:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400
        if reason not in VALID_REASONS:
            return jsonify({'status': 'error', 'message': '举报原因无效'}), 400

        uid = current_user_id()
        result = report_service.create_report(uid, target_type, target_id, reason, detail)
        if 'error' in result:
            return jsonify({'status': 'error', 'message': result['error']}), 400
        return jsonify({'status': 'success', 'message': '举报已提交'})
    except Exception as e:
        current_app.logger.error(f"举报失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '举报失败'}), 500
