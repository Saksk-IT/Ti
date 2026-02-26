# -*- coding: utf-8 -*-
"""评论 API"""
from flask import jsonify, request, current_app, session

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from app.modules.forum.services import comment_service


@forum_api_bp.route('/posts/<int:post_id>/comments', methods=['GET'])
@auth_required
def api_get_comments(post_id: int):
    """获取评论列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 30, type=int), 50)
        result = comment_service.get_comments(
            post_id, page=page, per_page=per_page,
            user_id=current_user_id(),
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        current_app.logger.error(f"获取评论失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取评论失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>/comments', methods=['POST'])
@auth_required
def api_create_comment(post_id: int):
    """发表评论"""
    try:
        data = request.get_json(silent=True) or {}
        content = (data.get('content') or '').strip()
        if not content:
            return jsonify({'status': 'error', 'message': '评论内容不能为空'}), 400
        if len(content) > 2000:
            return jsonify({'status': 'error', 'message': '评论不能超过2000字'}), 400

        parent_id = data.get('parent_id')
        reply_to_user_id = data.get('reply_to_user_id')

        comment = comment_service.create_comment(
            post_id=post_id, author_id=current_user_id(),
            content=content, parent_id=parent_id,
            reply_to_user_id=reply_to_user_id,
        )
        if 'error' in comment:
            return jsonify({'status': 'error', 'message': comment['error']}), 403
        return jsonify({'status': 'success', 'data': comment})
    except Exception as e:
        current_app.logger.error(f"发表评论失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '发表评论失败'}), 500


@forum_api_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@auth_required
def api_delete_comment(comment_id: int):
    """删除评论"""
    try:
        is_admin = bool(session.get('is_admin'))
        ok = comment_service.delete_comment(
            comment_id, user_id=current_user_id(), is_admin=is_admin,
        )
        if not ok:
            return jsonify({'status': 'error', 'message': '无权删除或评论不存在'}), 403
        return jsonify({'status': 'success', 'message': '删除成功'})
    except Exception as e:
        current_app.logger.error(f"删除评论失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '删除评论失败'}), 500
