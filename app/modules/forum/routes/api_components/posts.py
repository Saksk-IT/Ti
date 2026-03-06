# -*- coding: utf-8 -*-
"""帖子 CRUD API"""
from flask import jsonify, request, current_app, session

from ..api import forum_api_bp
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.modules.forum.services import post_service, reader_service

MAX_TAGS = 8
MAX_TAG_LENGTH = 20
MAX_SUMMARY_LENGTH = 300
SUPPORTED_CONTENT_FORMATS = {'html', 'markdown'}


def _validate_meta_payload(data: dict) -> tuple[bool, str]:
    content_format = (data.get('content_format') or 'html').strip().lower()
    if content_format not in SUPPORTED_CONTENT_FORMATS:
        return False, '不支持的内容格式'

    if content_format == 'markdown' and not str(data.get('markdown_source') or '').strip():
        return False, 'Markdown 模式下内容不能为空'

    tags = data.get('tags')
    if tags is not None:
        if not isinstance(tags, list):
            return False, '标签格式错误'
        if len(tags) > MAX_TAGS:
            return False, f'标签最多 {MAX_TAGS} 个'
        for item in tags:
            if len(str(item or '').strip()) > MAX_TAG_LENGTH:
                return False, f'标签长度不能超过 {MAX_TAG_LENGTH} 字'

    summary = data.get('summary')
    if summary is not None and len(str(summary).strip()) > MAX_SUMMARY_LENGTH:
        return False, f'摘要不能超过 {MAX_SUMMARY_LENGTH} 字'

    cover_image = data.get('cover_image')
    if cover_image is not None and len(str(cover_image).strip()) > 1024:
        return False, '封面地址过长'

    return True, ''


@forum_api_bp.route('/posts', methods=['GET'])
@auth_required
@limiter.limit("60 per minute;600 per hour")
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
@limiter.limit("120 per minute;1200 per hour")
def api_get_post(post_id: int):
    """帖子详情"""
    try:
        post = post_service.get_post_detail(
            post_id,
            user_id=current_user_id(),
            is_admin=bool(session.get('is_admin')),
        )
        if not post:
            return jsonify({'status': 'error', 'message': '帖子不存在'}), 404
        return jsonify({'status': 'success', 'data': post})
    except Exception as e:
        current_app.logger.error(f"获取帖子详情失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取帖子详情失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>/sidebar', methods=['GET'])
@auth_required
@limiter.limit("120 per minute;1200 per hour")
def api_get_post_sidebar(post_id: int):
    """帖子阅读页侧栏数据"""
    try:
        result = reader_service.get_reader_sidebar(
            post_id,
            viewer_id=current_user_id(),
            is_admin=bool(session.get('is_admin')),
            limit=min(request.args.get('limit', 4, type=int), 6),
        )
        if not result:
            return jsonify({'status': 'error', 'message': '帖子不存在'}), 404
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        current_app.logger.error(f"获取帖子侧栏数据失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取帖子侧栏数据失败'}), 500


@forum_api_bp.route('/posts', methods=['POST'])
@auth_required
@limiter.limit("20 per minute;200 per day")
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
        valid, message = _validate_meta_payload(data)
        if not valid:
            return jsonify({'status': 'error', 'message': message}), 400

        post = post_service.create_post(
            author_id=current_user_id(), board_id=board_id,
            title=title, content=content,
            images=images, question_refs=question_refs,
            poll=data.get('poll'),
            content_format=data.get('content_format'),
            markdown_source=data.get('markdown_source'),
            cover_image=data.get('cover_image'),
            tags=data.get('tags'),
            summary=data.get('summary'),
        )
        if 'error' in post:
            return jsonify({'status': 'error', 'message': post['error']}), 403
        return jsonify({'status': 'success', 'data': post})
    except Exception as e:
        current_app.logger.error(f"创建帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '创建帖子失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>', methods=['PUT'])
@auth_required
@limiter.limit("30 per minute;300 per day")
def api_update_post(post_id: int):
    """编辑帖子"""
    try:
        data = request.get_json(silent=True) or {}
        if 'title' in data:
            title = str(data.get('title') or '').strip()
            if not title:
                return jsonify({'status': 'error', 'message': '标题不能为空'}), 400
            if len(title) > 200:
                return jsonify({'status': 'error', 'message': '标题不能超过200字'}), 400
            data['title'] = title
        valid, message = _validate_meta_payload(data)
        if not valid:
            return jsonify({'status': 'error', 'message': message}), 400

        ok = post_service.update_post(post_id, author_id=current_user_id(), **data)
        if not ok:
            return jsonify({'status': 'error', 'message': '无权编辑或帖子不存在'}), 403
        return jsonify({'status': 'success', 'message': '更新成功'})
    except Exception as e:
        current_app.logger.error(f"编辑帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '编辑帖子失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@auth_required
@limiter.limit("20 per minute;200 per day")
def api_delete_post(post_id: int):
    """删除帖子"""
    try:
        is_admin = bool(session.get('is_admin'))
        ok = post_service.delete_post(post_id, user_id=current_user_id(), is_admin=is_admin)
        if not ok:
            return jsonify({'status': 'error', 'message': '无权删除或帖子不存在'}), 403
        return jsonify({'status': 'success', 'message': '删除成功'})
    except Exception as e:
        current_app.logger.error(f"删除帖子失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '删除帖子失败'}), 500


@forum_api_bp.route('/posts/<int:post_id>/hidden', methods=['POST'])
@auth_required
@limiter.limit("30 per minute;300 per day")
def api_set_post_hidden(post_id: int):
    """设置帖子隐藏状态（作者/管理员）"""
    try:
        data = request.get_json(silent=True) or {}
        raw_hidden = data.get('hidden')
        if isinstance(raw_hidden, bool):
            hidden = raw_hidden
        elif isinstance(raw_hidden, (int, float)) and raw_hidden in (0, 1):
            hidden = bool(raw_hidden)
        elif isinstance(raw_hidden, str):
            normalized = raw_hidden.strip().lower()
            if normalized in ('true', '1', 'yes', 'on'):
                hidden = True
            elif normalized in ('false', '0', 'no', 'off'):
                hidden = False
            else:
                return jsonify({'status': 'error', 'message': '参数 hidden 非法'}), 400
        else:
            return jsonify({'status': 'error', 'message': '参数 hidden 必填'}), 400

        ok, reason = post_service.set_post_hidden(
            post_id=post_id,
            user_id=current_user_id(),
            hidden=hidden,
            is_admin=bool(session.get('is_admin')),
        )
        if not ok:
            if reason == 'unsupported':
                return jsonify({'status': 'error', 'message': '当前版本不支持隐藏帖子'}), 400
            if reason == 'not_found':
                return jsonify({'status': 'error', 'message': '帖子不存在'}), 404
            return jsonify({'status': 'error', 'message': '无权操作该帖子'}), 403

        return jsonify({'status': 'success', 'data': {'post_id': post_id, 'is_hidden': hidden}})
    except Exception as e:
        current_app.logger.error(f"设置帖子隐藏状态失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '设置帖子隐藏状态失败'}), 500
