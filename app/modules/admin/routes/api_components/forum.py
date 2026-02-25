# -*- coding: utf-8 -*-
"""管理后台 - 论坛管理 API"""
from flask import jsonify, request, current_app, session

from sqlalchemy import text

from ..api_bp import admin_api_bp
from app.core.extensions import db
from app.core.utils.decorators import admin_required
from app.modules.forum.services import board_service, report_service, ban_service


@admin_api_bp.route('/forum/stats', methods=['GET'])
@admin_required
def api_forum_stats():
    """论坛统计"""
    try:
        post_count = db.session.execute(text(
            'SELECT COUNT(*) FROM forum_posts WHERE is_deleted = false'
        )).scalar()
        comment_count = db.session.execute(text(
            'SELECT COUNT(*) FROM forum_comments WHERE is_deleted = false'
        )).scalar()
        today_posts = db.session.execute(text('''
            SELECT COUNT(*) FROM forum_posts
            WHERE is_deleted = false
              AND DATE(created_at AT TIME ZONE 'Asia/Shanghai') = DATE(NOW() AT TIME ZONE 'Asia/Shanghai')
        ''')).scalar()
        board_count = db.session.execute(text(
            'SELECT COUNT(*) FROM forum_boards WHERE is_active = true'
        )).scalar()

        return jsonify({'status': 'success', 'data': {
            'post_count': post_count,
            'comment_count': comment_count,
            'today_posts': today_posts,
            'board_count': board_count,
            'pending_reports': report_service.get_pending_count(),
        }})
    except Exception as e:
        current_app.logger.error(f"获取论坛统计失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取统计失败'}), 500


@admin_api_bp.route('/forum/posts', methods=['GET'])
@admin_required
def api_admin_forum_posts():
    """管理帖子列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        keyword = request.args.get('keyword', '').strip()
        offset = (page - 1) * per_page

        conditions = ['p.is_deleted = false']
        params: dict = {}
        if keyword:
            conditions.append("(p.title ILIKE :kw OR u.username ILIKE :kw)")
            params['kw'] = f'%{keyword}%'
        where = ' AND '.join(conditions)

        total = db.session.execute(text(f'''
            SELECT COUNT(*) FROM forum_posts p
            JOIN users u ON u.id = p.author_id
            WHERE {where}
        '''), params).scalar()

        params['limit'] = per_page
        params['offset'] = offset
        rows = db.session.execute(text(f'''
            SELECT p.id, p.title, p.is_pinned, p.is_featured, p.is_locked,
                   p.comment_count, p.like_count, p.view_count, p.created_at,
                   u.username AS author_name, b.name AS board_name
            FROM forum_posts p
            JOIN users u ON u.id = p.author_id
            JOIN forum_boards b ON b.id = p.board_id
            WHERE {where}
            ORDER BY p.created_at DESC
            LIMIT :limit OFFSET :offset
        '''), params).fetchall()

        return jsonify({'status': 'success', 'data': {
            'posts': [dict(r._mapping) for r in rows],
            'total': total, 'page': page, 'per_page': per_page,
        }})
    except Exception as e:
        current_app.logger.error(f"管理帖子列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取帖子列表失败'}), 500


@admin_api_bp.route('/forum/posts/<int:post_id>', methods=['DELETE'])
@admin_required
def api_admin_delete_post(post_id: int):
    """管理员删帖"""
    try:
        uid = session.get('user_id')
        db.session.execute(text('''
            UPDATE forum_posts SET is_deleted=true, deleted_by=:uid, deleted_at=NOW()
            WHERE id=:pid
        '''), {'pid': post_id, 'uid': uid})
        db.session.commit()
        return jsonify({'status': 'success', 'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"管理员删帖失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '删除失败'}), 500


@admin_api_bp.route('/forum/posts/<int:post_id>/toggle', methods=['POST'])
@admin_required
def api_admin_toggle_post(post_id: int):
    """置顶/精华/锁定切换"""
    try:
        data = request.get_json(silent=True) or {}
        field = data.get('field')
        if field not in ('is_pinned', 'is_featured', 'is_locked'):
            return jsonify({'status': 'error', 'message': '参数错误'}), 400
        db.session.execute(text(
            f'UPDATE forum_posts SET {field} = NOT {field} WHERE id = :pid'
        ), {'pid': post_id})
        db.session.commit()
        return jsonify({'status': 'success', 'message': '操作成功'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"切换帖子状态失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '操作失败'}), 500


@admin_api_bp.route('/forum/boards', methods=['GET'])
@admin_required
def api_admin_get_boards():
    """管理版块列表"""
    try:
        boards = board_service.get_boards(include_inactive=True)
        return jsonify({'status': 'success', 'data': {'boards': boards}})
    except Exception as e:
        current_app.logger.error(f"获取版块列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取版块列表失败'}), 500


@admin_api_bp.route('/forum/boards', methods=['POST'])
@admin_required
def api_admin_create_board():
    """创建自定义版块"""
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        slug = (data.get('slug') or '').strip()
        if not name or not slug:
            return jsonify({'status': 'error', 'message': '名称和标识不能为空'}), 400
        board = board_service.create_board(
            name=name, slug=slug,
            description=data.get('description', ''),
            icon=data.get('icon', ''),
            sort_order=data.get('sort_order', 0),
            created_by=session.get('user_id'),
        )
        return jsonify({'status': 'success', 'data': board})
    except Exception as e:
        current_app.logger.error(f"创建版块失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '创建版块失败'}), 500


@admin_api_bp.route('/forum/boards/<int:board_id>', methods=['PUT'])
@admin_required
def api_admin_update_board(board_id: int):
    """编辑版块"""
    try:
        data = request.get_json(silent=True) or {}
        ok = board_service.update_board(board_id, **data)
        if not ok:
            return jsonify({'status': 'error', 'message': '更新失败'}), 400
        return jsonify({'status': 'success', 'message': '更新成功'})
    except Exception as e:
        current_app.logger.error(f"编辑版块失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '编辑版块失败'}), 500


@admin_api_bp.route('/forum/boards/<int:board_id>', methods=['DELETE'])
@admin_required
def api_admin_delete_board(board_id: int):
    """删除版块"""
    try:
        ok = board_service.delete_board(board_id)
        if not ok:
            return jsonify({'status': 'error', 'message': '无法删除（科目版块不可删除）'}), 400
        return jsonify({'status': 'success', 'message': '删除成功'})
    except Exception as e:
        current_app.logger.error(f"删除版块失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '删除版块失败'}), 500


@admin_api_bp.route('/forum/boards/sync', methods=['POST'])
@admin_required
def api_admin_sync_boards():
    """同步科目版块"""
    try:
        created = board_service.sync_subject_boards()
        return jsonify({'status': 'success', 'data': {'created': created},
                        'message': f'同步完成，新增 {created} 个版块'})
    except Exception as e:
        current_app.logger.error(f"同步版块失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '同步失败'}), 500


# ── 举报管理 ──────────────────────────────────────────

@admin_api_bp.route('/forum/reports', methods=['GET'])
@admin_required
def api_admin_forum_reports():
    """举报列表"""
    try:
        status = request.args.get('status', 'pending')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        data = report_service.get_reports(status=status, page=page, per_page=per_page)
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error(f"获取举报列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取举报列表失败'}), 500


@admin_api_bp.route('/forum/reports/<int:report_id>/handle', methods=['POST'])
@admin_required
def api_admin_handle_report(report_id: int):
    """处理举报"""
    try:
        data = request.get_json(silent=True) or {}
        action = data.get('action', '')
        if action not in ('dismiss', 'delete_content', 'ban_user'):
            return jsonify({'status': 'error', 'message': '操作无效'}), 400
        note = (data.get('note') or '').strip()
        uid = session.get('user_id')
        ok = report_service.handle_report(report_id, uid, action, note)
        if not ok:
            return jsonify({'status': 'error', 'message': '举报不存在或已处理'}), 400
        return jsonify({'status': 'success', 'message': '处理成功'})
    except Exception as e:
        current_app.logger.error(f"处理举报失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '处理失败'}), 500


# ── 封禁管理 ──────────────────────────────────────────

@admin_api_bp.route('/forum/bans', methods=['GET'])
@admin_required
def api_admin_forum_bans():
    """封禁列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        data = ban_service.get_bans(page=page, per_page=per_page, active_only=active_only)
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        current_app.logger.error(f"获取封禁列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取封禁列表失败'}), 500


@admin_api_bp.route('/forum/bans', methods=['POST'])
@admin_required
def api_admin_ban_user():
    """封禁用户"""
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        reason = (data.get('reason') or '').strip()
        expires_at = data.get('expires_at')
        if not user_id or not reason:
            return jsonify({'status': 'error', 'message': '用户ID和原因不能为空'}), 400
        uid = session.get('user_id')
        result = ban_service.ban_user(user_id, uid, reason, expires_at)
        if 'error' in result:
            return jsonify({'status': 'error', 'message': result['error']}), 400
        return jsonify({'status': 'success', 'message': '封禁成功'})
    except Exception as e:
        current_app.logger.error(f"封禁用户失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '封禁失败'}), 500


@admin_api_bp.route('/forum/bans/<int:user_id>', methods=['DELETE'])
@admin_required
def api_admin_unban_user(user_id: int):
    """解除封禁"""
    try:
        ok = ban_service.unban_user(user_id)
        if not ok:
            return jsonify({'status': 'error', 'message': '该用户未被封禁'}), 400
        return jsonify({'status': 'success', 'message': '解封成功'})
    except Exception as e:
        current_app.logger.error(f"解封失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '解封失败'}), 500
