# -*- coding: utf-8 -*-
"""帖子业务逻辑"""
import json
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db
from ..services.content_sanitizer import sanitize_html, strip_html_tags
from ..services import mention_service, ban_service
from app.core.utils.cache_utils import bump_forum_boards_version


def get_posts(
    board_id: Optional[int] = None,
    sort: str = 'latest',
    keyword: str = '',
    featured_only: bool = False,
    page: int = 1,
    per_page: int = 20,
    user_id: Optional[int] = None,
) -> dict:
    """获取帖子列表（分页）"""
    conditions = ['p.is_deleted = false']
    params: dict = {}

    if board_id:
        conditions.append('p.board_id = :board_id')
        params['board_id'] = board_id
    if keyword:
        # PostgreSQL: 使用 GIN 全文索引；SQLite: 降级 LIKE
        dialect = db.engine.dialect.name
        if dialect == 'postgresql':
            conditions.append(
                "p.search_vector @@ plainto_tsquery('simple', :kw)"
            )
            params['kw'] = keyword
        else:
            conditions.append("(p.title LIKE :kw OR p.content LIKE :kw)")
            params['kw'] = f'%{keyword}%'
    if featured_only:
        conditions.append('p.is_featured = true')

    where = ' AND '.join(conditions)

    order_map = {
        'latest': 'p.created_at DESC',
        'hot': (
            '(p.like_count * 2 + p.comment_count * 3 + p.view_count * 0.1'
            ' + p.favorite_count * 2)'
            ' / POWER(GREATEST(EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 3600, 1), 0.5)'
            ' DESC, p.created_at DESC'
        ),
        'featured': 'p.is_featured DESC, p.created_at DESC',
        'active': 'COALESCE(p.last_comment_at, p.created_at) DESC',
    }
    order = order_map.get(sort, order_map['latest'])

    # 只有最新排序才强制置顶帖优先，热门/活跃按各自算法排
    pin_prefix = 'p.is_pinned DESC, ' if sort in ('latest',) else ''

    total = db.session.execute(text(
        f'SELECT COUNT(*) FROM forum_posts p WHERE {where}'
    ), params).scalar()

    offset = (page - 1) * per_page
    params['limit'] = per_page
    params['offset'] = offset

    # 用户点赞/收藏状态子查询
    liked_sql = ''
    faved_sql = ''
    if user_id:
        params['uid'] = user_id
        liked_sql = ", EXISTS(SELECT 1 FROM forum_likes WHERE user_id=:uid AND target_type='post' AND target_id=p.id) AS liked"
        faved_sql = ", EXISTS(SELECT 1 FROM forum_favorites WHERE user_id=:uid AND post_id=p.id) AS favorited"

    rows = db.session.execute(text(f'''
        SELECT p.id, p.board_id, p.author_id, p.title,
               LEFT(p.content, 800) AS content_raw,
               p.images, p.question_refs,
               p.is_pinned, p.is_featured, p.is_locked,
               p.comment_count, p.like_count, p.favorite_count, p.view_count,
               p.created_at, p.updated_at, p.last_comment_at,
               u.username AS author_name, u.avatar AS author_avatar,
               b.name AS board_name, b.slug AS board_slug
               {liked_sql}{faved_sql}
        FROM forum_posts p
        JOIN users u ON u.id = p.author_id
        JOIN forum_boards b ON b.id = p.board_id
        WHERE {where}
        ORDER BY {pin_prefix}{order}
        LIMIT :limit OFFSET :offset
    '''), params).fetchall()

    posts = []
    for r in rows:
        d = dict(r._mapping)
        d['content_preview'] = strip_html_tags(d.pop('content_raw', ''), 200)
        posts.append(d)

    return {
        'posts': posts,
        'total': total,
        'page': page,
        'per_page': per_page,
    }


def get_post_detail(post_id: int, user_id: int | None = None) -> dict | None:
    """获取帖子详情"""
    params: dict = {'pid': post_id}
    liked_sql = ''
    faved_sql = ''
    if user_id:
        params['uid'] = user_id
        liked_sql = ", EXISTS(SELECT 1 FROM forum_likes WHERE user_id=:uid AND target_type='post' AND target_id=p.id) AS liked"
        faved_sql = ", EXISTS(SELECT 1 FROM forum_favorites WHERE user_id=:uid AND post_id=p.id) AS favorited"

    row = db.session.execute(text(f'''
        SELECT p.*, u.username AS author_name, u.avatar AS author_avatar,
               b.name AS board_name, b.slug AS board_slug
               {liked_sql}{faved_sql}
        FROM forum_posts p
        JOIN users u ON u.id = p.author_id
        JOIN forum_boards b ON b.id = p.board_id
        WHERE p.id = :pid AND p.is_deleted = false
    '''), params).fetchone()

    if not row:
        return None

    # 增加浏览量
    db.session.execute(text(
        'UPDATE forum_posts SET view_count = view_count + 1 WHERE id = :pid'
    ), {'pid': post_id})
    db.session.commit()

    return dict(row._mapping)


def create_post(author_id: int, board_id: int, title: str, content: str,
                images: list | None = None, question_refs: list | None = None,
                poll: dict | None = None) -> dict:
    """创建帖子"""
    if ban_service.is_banned(author_id):
        return {'error': '您已被禁言，无法发帖'}

    safe_content = sanitize_html(content)
    images_json = json.dumps(images or [])
    refs_json = json.dumps(question_refs or [])
    poll_json = json.dumps(poll) if poll else None

    result = db.session.execute(text('''
        INSERT INTO forum_posts
            (board_id, author_id, title, content, images, question_refs, poll)
        VALUES (:bid, :uid, :title, :content, CAST(:images AS jsonb), CAST(:refs AS jsonb),
                CASE WHEN :poll IS NOT NULL THEN CAST(:poll AS jsonb) ELSE NULL END)
        RETURNING id
    '''), {
        'bid': board_id, 'uid': author_id, 'title': title,
        'content': safe_content, 'images': images_json, 'refs': refs_json,
        'poll': poll_json,
    })
    new_id = result.fetchone()._mapping['id']
    db.session.commit()
    bump_forum_boards_version()

    row = db.session.execute(text(
        'SELECT * FROM forum_posts WHERE id = :pid'
    ), {'pid': new_id}).fetchone()
    post = dict(row._mapping)

    # 解析 @提及
    mention_service.create_mentions('post', post['id'], author_id, safe_content)

    return post


def update_post(post_id: int, author_id: int, **fields) -> bool:
    """编辑帖子（仅作者）"""
    row = db.session.execute(text(
        'SELECT author_id FROM forum_posts WHERE id = :pid AND is_deleted = false'
    ), {'pid': post_id}).fetchone()
    if not row or row._mapping['author_id'] != author_id:
        return False

    allowed = {'title', 'content', 'images', 'question_refs', 'poll'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    if 'content' in updates:
        updates['content'] = sanitize_html(updates['content'])
    if 'images' in updates:
        updates['images'] = json.dumps(updates['images'])
    if 'question_refs' in updates:
        updates['question_refs'] = json.dumps(updates['question_refs'])
    if 'poll' in updates:
        updates['poll'] = json.dumps(updates['poll']) if updates['poll'] else None

    set_parts = []
    for k in updates:
        if k in ('images', 'question_refs'):
            set_parts.append(f'{k} = CAST(:{k} AS jsonb)')
        elif k == 'poll':
            set_parts.append(f'{k} = CASE WHEN :{k} IS NOT NULL THEN CAST(:{k} AS jsonb) ELSE NULL END')
        else:
            set_parts.append(f'{k} = :{k}')
    set_clause = ', '.join(set_parts)
    updates['pid'] = post_id
    db.session.execute(text(
        f'UPDATE forum_posts SET {set_clause}, updated_at = NOW() WHERE id = :pid'
    ), updates)
    db.session.commit()
    return True


def delete_post(post_id: int, user_id: int, is_admin: bool = False) -> bool:
    """软删除帖子（作者或管理员）"""
    row = db.session.execute(text(
        'SELECT author_id FROM forum_posts WHERE id = :pid AND is_deleted = false'
    ), {'pid': post_id}).fetchone()
    if not row:
        return False
    if row._mapping['author_id'] != user_id and not is_admin:
        return False

    db.session.execute(text('''
        UPDATE forum_posts
        SET is_deleted = true, deleted_by = :uid, deleted_at = NOW()
        WHERE id = :pid
    '''), {'pid': post_id, 'uid': user_id})
    db.session.commit()
    return True
