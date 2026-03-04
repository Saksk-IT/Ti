# -*- coding: utf-8 -*-
"""帖子业务逻辑"""
import json
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db
from ..services.content_sanitizer import sanitize_html, strip_html_tags
from ..services.markdown_renderer import render_markdown_to_safe_html
from ..services import mention_service, ban_service
from app.core.utils.cache_utils import bump_forum_boards_version

MAX_TAGS = 8
MAX_TAG_LENGTH = 20
MAX_SUMMARY_LENGTH = 300
DEFAULT_PREVIEW_LENGTH = 200
SUPPORTED_CONTENT_FORMATS = {'html', 'markdown'}


def _is_postgresql() -> bool:
    return db.engine.dialect.name == 'postgresql'


def _to_json_str(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _safe_tags(tags) -> list[str]:
    if not isinstance(tags, list):
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw_tag in tags:
        tag = str(raw_tag or '').strip()
        if not tag:
            continue
        tag = tag[:MAX_TAG_LENGTH]
        if tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
        if len(normalized) >= MAX_TAGS:
            break
    return normalized


def _safe_cover_image(cover_image: str | None) -> str | None:
    if cover_image is None:
        return None
    cover = str(cover_image).strip()
    if not cover:
        return None
    if cover.startswith('/uploads/forum/') or cover.startswith('https://') or cover.startswith('http://'):
        return cover
    return None


def _safe_summary(summary: str | None, html_content: str) -> str:
    raw = (summary or '').strip()
    if raw:
        return raw[:MAX_SUMMARY_LENGTH]
    return strip_html_tags(html_content, 160)


def _normalize_post_content(
    content: str,
    content_format: str | None = None,
    markdown_source: str | None = None,
) -> tuple[str, str, str | None]:
    fmt = (content_format or 'html').strip().lower()
    if fmt not in SUPPORTED_CONTENT_FORMATS:
        fmt = 'html'

    if fmt == 'markdown':
        md_source = (markdown_source if markdown_source is not None else content or '').strip()
        rendered_html = render_markdown_to_safe_html(md_source)
        return rendered_html, 'markdown', md_source

    safe_html = sanitize_html(content or '')
    return safe_html, 'html', None


def _json_read(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if parsed is not None else default
        except Exception:
            return default
    return default


def _json_read_list(value) -> list:
    parsed = _json_read(value, [])
    return parsed if isinstance(parsed, list) else []


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
    dialect = db.engine.dialect.name
    is_pg = dialect == 'postgresql'
    is_sqlite = dialect == 'sqlite'

    if board_id:
        conditions.append('p.board_id = :board_id')
        params['board_id'] = board_id
    if keyword:
        # PostgreSQL: 使用 GIN 全文索引；SQLite: 降级 LIKE
        if is_pg:
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

    if is_pg:
        hot_order = (
            '(p.like_count * 2 + p.comment_count * 3 + p.view_count * 0.1'
            ' + p.favorite_count * 2)'
            ' / POWER(GREATEST(EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 3600, 1), 0.5)'
            ' DESC, p.created_at DESC'
        )
        content_raw_expr = 'LEFT(p.content, 800)'
    elif is_sqlite:
        # SQLite 不支持 NOW/EXTRACT/LEFT，使用兼容表达式。
        hot_order = (
            '(p.like_count * 2 + p.comment_count * 3 + p.view_count * 0.1'
            ' + p.favorite_count * 2)'
            " / CASE WHEN ((strftime('%s','now') - strftime('%s', p.created_at)) / 3600.0) > 1"
            " THEN ((strftime('%s','now') - strftime('%s', p.created_at)) / 3600.0)"
            ' ELSE 1 END'
            ' DESC, p.created_at DESC'
        )
        content_raw_expr = 'SUBSTR(p.content, 1, 800)'
    else:
        hot_order = (
            '(p.like_count * 2 + p.comment_count * 3 + p.view_count * 0.1'
            ' + p.favorite_count * 2)'
            ' DESC, p.created_at DESC'
        )
        content_raw_expr = 'SUBSTRING(p.content, 1, 800)'

    order_map = {
        'latest': 'p.created_at DESC',
        'hot': hot_order,
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
               {content_raw_expr} AS content_raw,
               p.images, p.question_refs, p.cover_image, p.tags, p.summary,
               p.content_format,
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
        summary = str(d.get('summary') or '').strip()
        content_raw = d.pop('content_raw', '')
        d['tags'] = _json_read_list(d.get('tags'))
        d['images'] = _json_read_list(d.get('images'))
        d['question_refs'] = _json_read_list(d.get('question_refs'))
        d['content_preview'] = summary or strip_html_tags(content_raw, DEFAULT_PREVIEW_LENGTH)
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

    data = dict(row._mapping)
    data['tags'] = _json_read_list(data.get('tags'))
    data['images'] = _json_read_list(data.get('images'))
    data['question_refs'] = _json_read_list(data.get('question_refs'))
    return data


def create_post(author_id: int, board_id: int, title: str, content: str,
                images: list | None = None, question_refs: list | None = None,
                poll: dict | None = None, content_format: str | None = None,
                markdown_source: str | None = None, cover_image: str | None = None,
                tags: list | None = None, summary: str | None = None) -> dict:
    """创建帖子"""
    if ban_service.is_banned(author_id):
        return {'error': '您已被禁言，无法发帖'}

    safe_content, normalized_format, normalized_markdown = _normalize_post_content(
        content=content,
        content_format=content_format,
        markdown_source=markdown_source,
    )
    normalized_tags = _safe_tags(tags or [])
    normalized_cover = _safe_cover_image(cover_image)
    normalized_summary = _safe_summary(summary, safe_content)

    images_json = _to_json_str(images or [])
    refs_json = _to_json_str(question_refs or [])
    tags_json = _to_json_str(normalized_tags)
    poll_json = _to_json_str(poll) if poll else None
    is_pg = _is_postgresql()
    images_expr = 'CAST(:images AS jsonb)' if is_pg else ':images'
    refs_expr = 'CAST(:refs AS jsonb)' if is_pg else ':refs'
    tags_expr = 'CAST(:tags AS jsonb)' if is_pg else ':tags'
    poll_expr = (
        'CASE WHEN :poll IS NOT NULL THEN CAST(:poll AS jsonb) ELSE NULL END'
        if is_pg else ':poll'
    )
    insert_sql = f'''
        INSERT INTO forum_posts
            (board_id, author_id, title, content, content_format, markdown_source,
             cover_image, tags, summary, images, question_refs, poll)
        VALUES (:bid, :uid, :title, :content, :content_format, :markdown_source,
                :cover_image, {tags_expr}, :summary, {images_expr}, {refs_expr}, {poll_expr})
        RETURNING id
    '''

    result = db.session.execute(text(insert_sql), {
        'bid': board_id, 'uid': author_id, 'title': title,
        'content': safe_content, 'content_format': normalized_format,
        'markdown_source': normalized_markdown, 'cover_image': normalized_cover,
        'tags': tags_json, 'summary': normalized_summary,
        'images': images_json, 'refs': refs_json,
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
    mention_base = normalized_markdown if normalized_format == 'markdown' else safe_content
    mention_service.create_mentions('post', post['id'], author_id, mention_base)

    return post


def update_post(post_id: int, author_id: int, **fields) -> bool:
    """编辑帖子（仅作者）"""
    row = db.session.execute(text(
        'SELECT author_id, content, content_format, markdown_source '
        'FROM forum_posts WHERE id = :pid AND is_deleted = false'
    ), {'pid': post_id}).fetchone()
    if not row or row._mapping['author_id'] != author_id:
        return False

    old_content = str(row._mapping.get('content') or '')
    old_format = str(row._mapping.get('content_format') or 'html')
    old_markdown = row._mapping.get('markdown_source')

    allowed = {
        'title', 'content', 'images', 'question_refs', 'poll',
        'content_format', 'markdown_source', 'cover_image', 'tags', 'summary',
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    content_updated = (
        'content' in updates or 'content_format' in updates or 'markdown_source' in updates
    )
    if content_updated:
        safe_content, normalized_format, normalized_markdown = _normalize_post_content(
            content=str(updates.get('content', old_content) or ''),
            content_format=updates.get('content_format', old_format),
            markdown_source=updates.get('markdown_source', old_markdown),
        )
        updates['content'] = safe_content
        updates['content_format'] = normalized_format
        updates['markdown_source'] = normalized_markdown

    if 'images' in updates:
        updates['images'] = _to_json_str(updates['images'] or [])
    if 'question_refs' in updates:
        updates['question_refs'] = _to_json_str(updates['question_refs'] or [])
    if 'poll' in updates:
        updates['poll'] = _to_json_str(updates['poll']) if updates['poll'] else None
    if 'cover_image' in updates:
        updates['cover_image'] = _safe_cover_image(updates.get('cover_image'))
    if 'tags' in updates:
        updates['tags'] = _to_json_str(_safe_tags(updates.get('tags') or []))
    if 'summary' in updates:
        summary_source = str(updates.get('content', old_content) or '')
        updates['summary'] = _safe_summary(updates.get('summary'), summary_source)
    elif content_updated and 'content' in updates:
        # 内容有更新但前端未传摘要时，不自动覆盖既有摘要。
        pass

    is_pg = _is_postgresql()
    set_parts = []
    for k in updates:
        if k in ('images', 'question_refs', 'tags'):
            if is_pg:
                set_parts.append(f'{k} = CAST(:{k} AS jsonb)')
            else:
                set_parts.append(f'{k} = :{k}')
        elif k == 'poll':
            if is_pg:
                set_parts.append(f'{k} = CASE WHEN :{k} IS NOT NULL THEN CAST(:{k} AS jsonb) ELSE NULL END')
            else:
                set_parts.append(f'{k} = :{k}')
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
