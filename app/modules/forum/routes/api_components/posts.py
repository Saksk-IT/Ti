# -*- coding: utf-8 -*-
"""帖子 CRUD API"""
from flask import jsonify, request, current_app

from ..api import forum_api_bp
from app.core.utils.decorators import auth_required, current_user_id
from app.modules.forum.services import post_service


@forum_api_bp.route('/posts', methods=['GET'])
@auth_required
def api_get_posts():
    """帖子列表"""
    try:
        board_id = request.args.get('board_id', type=int)
        sort = request.args.get('sort', 'latest')
        keyword = request.args.get('keyword', '').strip()
        featured = request.args.get('featured', '').lower() in ('true', '1')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)

        result = post_service.get_posts(
            board_id=board_id, sort=sort, keyword=keyword,
            featured_only=featured, page=page, per_page=per_page,
            user_id=current_user_id(),
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        current_app.logger.error(f"获取帖子列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取帖子列表失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>', methods=['GET'])
@auth_required
def api_get_post(post_id: int):
    """帖子详情"""
    try:
        post = post_service.get_post_detail(post_id, user_id=current_user_id())
        if not post:
            return jsonify({'status': 'error', 'message': '帖子不存在'}), 404
        return jsonify({'status': 'success', 'data': post})
    except Exception as e:
        current_app.logger.error(f"获取帖子详情失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取帖子详情失败'}), 500


@forum_api_bp.route('/posts', methods=['POST'])
@auth_required
def api_create_post():
    """创建帖子"""
    try:
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        board_id = data.get('board_id')
        images = data.get('images') or []
        question_refs = data.get('question_refs') or []

        if not title or not board_id:
            return jsonify({'status': 'error', 'message': '标题和版块不能为空'}), 400
        if len(title) > 200:
            return jsonify({'status': 'error', 'message': '标题不能超过200字'}), 400

        post = post_service.create_post(
            author_id=current_user_id(), board_id=board_id,
            title=title, content=content,
            images=images, question_refs=question_refs,
            poll=data.get('poll'),
        )
        if 'error' in post:
            return jsonify({'status': 'error', 'message': post['error']}), 403
        return jsonify({'status': 'success', 'data': post})
    except Exception as e:
        current_app.logger.error(f"创建帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '创建帖子失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>', methods=['PUT'])
@auth_required
def api_update_post(post_id: int):
    """编辑帖子"""
    try:
        data = request.get_json(silent=True) or {}
        ok = post_service.update_post(post_id, author_id=current_user_id(), **data)
        if not ok:
            return jsonify({'status': 'error', 'message': '无权编辑或帖子不存在'}), 403
        return jsonify({'status': 'success', 'message': '更新成功'})
    except Exception as e:
        current_app.logger.error(f"编辑帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '编辑帖子失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@auth_required
def api_delete_post(post_id: int):
    """删除帖子"""
    try:
        from flask import session
        is_admin = bool(session.get('is_admin'))
        ok = post_service.delete_post(post_id, user_id=current_user_id(), is_admin=is_admin)
        if not ok:
            return jsonify({'status': 'error', 'message': '无权删除或帖子不存在'}), 403
        return jsonify({'status': 'success', 'message': '删除成功'})
    except Exception as e:
        current_app.logger.error(f"删除帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '删除帖子失败'}), 500
