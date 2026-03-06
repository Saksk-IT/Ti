# -*- coding: utf-8 -*-
"""论坛阅读页侧栏数据服务"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from app.core.extensions import db
from app.modules.forum.services import post_service


def _json_read_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


def _normalize_title(value: Any) -> str:
    title = str(value or '').strip()
    return title or '无标题'


def _serialize_post_row(row: Any) -> dict[str, Any]:
    data = dict(row._mapping)
    data['title'] = _normalize_title(data.get('title'))
    data['is_hidden'] = bool(data.get('is_hidden'))
    return data


def _build_hidden_condition(alias: str, *, viewer_id: int | None, is_admin: bool) -> tuple[str, dict[str, Any]]:
    if not post_service.supports_post_hidden() or is_admin:
        return '1=1', {}
    if viewer_id:
        return f'(COALESCE({alias}.is_hidden, false) = false OR {alias}.author_id = :viewer_id)', {'viewer_id': viewer_id}
    return f'COALESCE({alias}.is_hidden, false) = false', {}


def _merge_unique_rows(rows: list[Any], *, excluded_ids: set[int], limit: int) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen = set(excluded_ids)
    for row in rows:
        item = _serialize_post_row(row)
        pid = int(item.get('id') or 0)
        if not pid or pid in seen:
            continue
        seen.add(pid)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def get_reader_sidebar(
    post_id: int,
    *,
    viewer_id: int | None = None,
    is_admin: bool = False,
    limit: int = 4,
) -> dict[str, Any] | None:
    has_tags = post_service._has_forum_posts_column('tags')
    has_hidden = post_service.supports_post_hidden()
    params: dict[str, Any] = {'pid': post_id}
    post_hidden_condition, post_hidden_params = _build_hidden_condition('p', viewer_id=viewer_id, is_admin=is_admin)
    params.update(post_hidden_params)
    tags_select = 'p.tags AS tags' if has_tags else "'[]' AS tags"

    base_row = db.session.execute(text(f'''
        SELECT p.id, p.author_id, p.board_id, {tags_select}
        FROM forum_posts p
        WHERE p.id = :pid AND p.is_deleted = false AND {post_hidden_condition}
    '''), params).fetchone()

    if not base_row:
        return None

    base = dict(base_row._mapping)
    author_id = int(base['author_id'])
    board_id = int(base['board_id'])
    current_tags = [str(tag).strip() for tag in _json_read_list(base.get('tags')) if str(tag).strip()]

    author_params: dict[str, Any] = {
        'author_id': author_id,
        'viewer_id': int(viewer_id or 0),
    }
    author_hidden_condition, author_hidden_params = _build_hidden_condition('p', viewer_id=viewer_id, is_admin=is_admin)
    author_params.update(author_hidden_params)

    author_row = db.session.execute(text(f'''
        SELECT
            u.id,
            u.username,
            u.avatar,
            u.college,
            u.created_at,
            COALESCE((
                SELECT up.data
                FROM user_progress up
                WHERE up.user_id = u.id AND up.p_key = 'user_profile_extra_v1'
                LIMIT 1
            ), '') AS extra_json,
            (SELECT COUNT(*) FROM user_follows WHERE following_id = u.id) AS follower_count,
            (SELECT COUNT(*) FROM user_follows WHERE follower_id = u.id) AS following_count,
            COALESCE((
                SELECT SUM(fp.like_count)
                FROM forum_posts fp
                WHERE fp.author_id = u.id AND fp.is_deleted = false
            ), 0) AS total_likes_received,
            (
                SELECT COUNT(*)
                FROM forum_posts p
                WHERE p.author_id = u.id AND p.is_deleted = false AND {author_hidden_condition}
            ) AS post_count,
            CASE
                WHEN :viewer_id > 0 AND :viewer_id != u.id THEN EXISTS(
                    SELECT 1 FROM user_follows uf WHERE uf.follower_id = :viewer_id AND uf.following_id = u.id
                )
                ELSE false
            END AS i_follow,
            CASE
                WHEN :viewer_id > 0 AND :viewer_id != u.id THEN EXISTS(
                    SELECT 1 FROM user_follows uf WHERE uf.follower_id = u.id AND uf.following_id = :viewer_id
                )
                ELSE false
            END AS follows_me
        FROM users u
        WHERE u.id = :author_id
    '''), author_params).fetchone()

    author = None
    if author_row:
        author = dict(author_row._mapping)
        extra_json = author.pop('extra_json', '') or ''
        signature = ''
        if extra_json:
            try:
                extra = json.loads(extra_json)
                if isinstance(extra, dict):
                    signature = str(extra.get('signature') or '').strip()
            except Exception:
                signature = ''
        author['signature'] = signature
        author['i_follow'] = bool(author.get('i_follow'))
        author['follows_me'] = bool(author.get('follows_me'))
        author['mutual'] = bool(author['i_follow'] and author['follows_me'])

    list_hidden_condition, list_hidden_params = _build_hidden_condition('p', viewer_id=viewer_id, is_admin=is_admin)
    hot_order = (
        '(p.like_count * 2 + p.comment_count * 3 + p.view_count * 0.1 + p.favorite_count * 2) '
        '/ POWER(GREATEST(EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 3600, 1), 0.5) DESC, p.created_at DESC'
        if db.engine.dialect.name == 'postgresql'
        else 'p.like_count DESC, p.comment_count DESC, p.view_count DESC, p.created_at DESC'
    )
    hidden_select = 'COALESCE(p.is_hidden, false) AS is_hidden' if has_hidden else 'false AS is_hidden'

    author_posts_params = {
        'author_id': author_id,
        'current_post_id': post_id,
        'limit': max(limit, 4),
        **list_hidden_params,
    }
    author_posts_rows = db.session.execute(text(f'''
        SELECT p.id, p.title, p.created_at, p.like_count, p.comment_count, p.view_count,
               b.name AS board_name,
               {hidden_select}
        FROM forum_posts p
        JOIN forum_boards b ON b.id = p.board_id
        WHERE p.author_id = :author_id
          AND p.id != :current_post_id
          AND p.is_deleted = false
          AND {list_hidden_condition}
        ORDER BY p.created_at DESC
        LIMIT :limit
    '''), author_posts_params).fetchall()

    related_rows_all: list[Any] = []
    related_params = {
        'board_id': board_id,
        'current_post_id': post_id,
        'limit': max(limit * 2, 8),
        **list_hidden_params,
    }
    related_rows_all.extend(db.session.execute(text(f'''
        SELECT p.id, p.title, p.created_at, p.like_count, p.comment_count, p.view_count,
               b.name AS board_name,
               {hidden_select}
        FROM forum_posts p
        JOIN forum_boards b ON b.id = p.board_id
        WHERE p.board_id = :board_id
          AND p.id != :current_post_id
          AND p.is_deleted = false
          AND {list_hidden_condition}
        ORDER BY {hot_order}
        LIMIT :limit
    '''), related_params).fetchall())

    if current_tags and has_tags:
        tag_conditions = []
        tag_params = dict(related_params)
        for index, tag in enumerate(current_tags[:3]):
            key = f'tag_{index}'
            tag_conditions.append(f'CAST(p.tags AS TEXT) LIKE :{key}')
            tag_params[key] = f'%{tag}%'
        if tag_conditions:
            related_rows_all.extend(db.session.execute(text(f'''
                SELECT p.id, p.title, p.created_at, p.like_count, p.comment_count, p.view_count,
                       b.name AS board_name,
                       {hidden_select}
                FROM forum_posts p
                JOIN forum_boards b ON b.id = p.board_id
                WHERE p.id != :current_post_id
                  AND p.is_deleted = false
                  AND {list_hidden_condition}
                  AND ({' OR '.join(tag_conditions)})
                ORDER BY {hot_order}
                LIMIT :limit
            '''), tag_params).fetchall())

    hot_params = {
        'current_post_id': post_id,
        'limit': max(limit * 2, 8),
        **list_hidden_params,
    }
    hot_rows = db.session.execute(text(f'''
        SELECT p.id, p.title, p.created_at, p.like_count, p.comment_count, p.view_count,
               b.name AS board_name,
               {hidden_select}
        FROM forum_posts p
        JOIN forum_boards b ON b.id = p.board_id
        WHERE p.id != :current_post_id
          AND p.is_deleted = false
          AND {list_hidden_condition}
        ORDER BY {hot_order}
        LIMIT :limit
    '''), hot_params).fetchall()

    author_posts = _merge_unique_rows(author_posts_rows, excluded_ids={post_id}, limit=limit)
    author_post_ids = {int(item['id']) for item in author_posts}

    related_posts = _merge_unique_rows(
        related_rows_all,
        excluded_ids={post_id, *author_post_ids},
        limit=limit,
    )
    related_post_ids = {int(item['id']) for item in related_posts}

    hot_posts = _merge_unique_rows(
        hot_rows,
        excluded_ids={post_id, *author_post_ids, *related_post_ids},
        limit=limit,
    )

    return {
        'author': author,
        'author_posts': author_posts,
        'related_posts': related_posts,
        'hot_posts': hot_posts,
    }
