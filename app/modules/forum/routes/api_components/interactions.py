# -*- coding: utf-8 -*-
"""点赞 / 收藏 API"""
from flask import jsonify, request, current_app

from sqlalchemy import text

from ..api import forum_api_bp
from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.modules.forum.services.content_sanitizer import strip_html_tags
from app.modules.forum.services import interaction_service


@forum_api_bp.route('/like', methods=['POST'])
@auth_required
def api_toggle_like():
    """点赞 / 取消点赞"""
    try:
        data = request.get_json(silent=True) or {}
        target_type = data.get('target_type', '')
        target_id = data.get('target_id')

        if target_type not in ('post', 'comment') or not target_id:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400

        uid = current_user_id()
        existing = db.session.execute(text(
            'SELECT id FROM forum_likes WHERE user_id=:uid AND target_type=:tt AND target_id=:tid'
        ), {'uid': uid, 'tt': target_type, 'tid': target_id}).fetchone()

        if existing:
            db.session.execute(text(
                'DELETE FROM forum_likes WHERE id=:lid'
            ), {'lid': existing._mapping['id']})
            # 减少计数
            table = 'forum_posts' if target_type == 'post' else 'forum_comments'
            db.session.execute(text(
                f'UPDATE {table} SET like_count = GREATEST(like_count - 1, 0) WHERE id=:tid'
            ), {'tid': target_id})
            db.session.commit()
            return jsonify({'status': 'success', 'data': {'liked': False}})
        else:
            db.session.execute(text(
                'INSERT INTO forum_likes (user_id, target_type, target_id) VALUES (:uid, :tt, :tid)'
            ), {'uid': uid, 'tt': target_type, 'tid': target_id})
            table = 'forum_posts' if target_type == 'post' else 'forum_comments'
            db.session.execute(text(
                f'UPDATE {table} SET like_count = like_count + 1 WHERE id=:tid'
            ), {'tid': target_id})
            db.session.commit()

            # 触发互动通知
            try:
                if target_type == 'post':
                    row_author = db.session.execute(text(
                        'SELECT author_id, title FROM forum_posts WHERE id=:tid'
                    ), {'tid': target_id}).fetchone()
                    if row_author:
                        interaction_service.create_notification(
                            user_id=row_author._mapping['author_id'], actor_id=uid,
                            action_type=interaction_service.ACTION_LIKE_POST,
                            target_type='post', target_id=target_id,
                            post_id=target_id,
                            content_preview=row_author._mapping.get('title', ''),
                        )
                elif target_type == 'comment':
                    row_author = db.session.execute(text(
                        'SELECT author_id, post_id, LEFT(content, 100) AS preview FROM forum_comments WHERE id=:tid'
                    ), {'tid': target_id}).fetchone()
                    if row_author:
                        interaction_service.create_notification(
                            user_id=row_author._mapping['author_id'], actor_id=uid,
                            action_type=interaction_service.ACTION_LIKE_COMMENT,
                            target_type='comment', target_id=target_id,
                            post_id=row_author._mapping.get('post_id'),
                            content_preview=strip_html_tags(row_author._mapping.get('preview', ''), 100),
                        )
            except Exception:
                pass

            return jsonify({'status': 'success', 'data': {'liked': True}})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"点赞操作失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '操作失败'}), 500


@forum_api_bp.route('/favorite', methods=['POST'])
@auth_required
def api_toggle_favorite():
    """收藏 / 取消收藏"""
    try:
        data = request.get_json(silent=True) or {}
        post_id = data.get('post_id')
        if not post_id:
            return jsonify({'status': 'error', 'message': '参数错误'}), 400

        uid = current_user_id()
        existing = db.session.execute(text(
            'SELECT id FROM forum_favorites WHERE user_id=:uid AND post_id=:pid'
        ), {'uid': uid, 'pid': post_id}).fetchone()

        if existing:
            db.session.execute(text(
                'DELETE FROM forum_favorites WHERE id=:fid'
            ), {'fid': existing._mapping['id']})
            db.session.execute(text(
                'UPDATE forum_posts SET favorite_count = GREATEST(favorite_count - 1, 0) WHERE id=:pid'
            ), {'pid': post_id})
            db.session.commit()
            return jsonify({'status': 'success', 'data': {'favorited': False}})
        else:
            db.session.execute(text(
                'INSERT INTO forum_favorites (user_id, post_id) VALUES (:uid, :pid)'
            ), {'uid': uid, 'pid': post_id})
            db.session.execute(text(
                'UPDATE forum_posts SET favorite_count = favorite_count + 1 WHERE id=:pid'
            ), {'pid': post_id})
            db.session.commit()
            return jsonify({'status': 'success', 'data': {'favorited': True}})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"收藏操作失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '操作失败'}), 500


@forum_api_bp.route('/my/favorites', methods=['GET'])
@auth_required
def api_my_favorites():
    """我的收藏列表"""
    try:
        uid = current_user_id()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        offset = (page - 1) * per_page

        total = db.session.execute(text(
            'SELECT COUNT(*) FROM forum_favorites WHERE user_id=:uid'
        ), {'uid': uid}).scalar()

        rows = db.session.execute(text('''
            SELECT p.id, p.title, LEFT(p.content, 800) AS content_raw,
                   p.images, p.comment_count, p.like_count, p.view_count,
                   p.created_at, u.username AS author_name, u.avatar AS author_avatar,
                   b.name AS board_name, f.created_at AS favorited_at
            FROM forum_favorites f
            JOIN forum_posts p ON p.id = f.post_id AND p.is_deleted = false
            JOIN users u ON u.id = p.author_id
            JOIN forum_boards b ON b.id = p.board_id
            WHERE f.user_id = :uid
            ORDER BY f.created_at DESC
            LIMIT :limit OFFSET :offset
        '''), {'uid': uid, 'limit': per_page, 'offset': offset}).fetchall()

        posts = []
        for r in rows:
            d = dict(r._mapping)
            d['content_preview'] = strip_html_tags(d.pop('content_raw', ''), 200)
            posts.append(d)

        return jsonify({'status': 'success', 'data': {
            'posts': posts,
            'total': total, 'page': page, 'per_page': per_page,
        }})
    except Exception as e:
        current_app.logger.error(f"获取收藏列表失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '获取收藏列表失败'}), 500


@forum_api_bp.route('/users/search', methods=['GET'])
@auth_required
def api_search_users():
    """搜索用户（用于转发、@提及等）"""
    try:
        q = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 10, type=int), 20)
        if not q:
            return jsonify({'status': 'success', 'data': []})

        uid = current_user_id()
        rows = db.session.execute(text('''
            SELECT id, username, avatar
            FROM users
            WHERE id != :uid AND username ILIKE :q
            ORDER BY username
            LIMIT :lim
        '''), {'uid': uid, 'q': f'%{q}%', 'lim': limit}).fetchall()

        return jsonify({'status': 'success', 'data': [
            {'id': r._mapping['id'], 'username': r._mapping['username'],
             'avatar': r._mapping['avatar']}
            for r in rows
        ]})
    except Exception as e:
        current_app.logger.error(f"搜索用户失败: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': '搜索失败'}), 500
