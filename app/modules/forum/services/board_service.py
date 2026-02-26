# -*- coding: utf-8 -*-
"""版块管理服务"""
import re
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.cache_utils import (
    get_forum_boards_version, bump_forum_boards_version, make_cache_key,
)
from app.core.utils.redis_utils import redis_get_json, redis_set_json


def _slugify(name: str) -> str:
    """将中文名转为 slug（拼音首字母或直接用名称 hash）"""
    slug = re.sub(r'[^\w\u4e00-\u9fff-]', '', name).strip().lower()
    if not slug:
        import hashlib
        slug = hashlib.md5(name.encode()).hexdigest()[:8]
    return slug


def sync_subject_boards() -> int:
    """将 subjects 表同步为论坛版块（仅新增，不删除）"""
    rows = db.session.execute(text(
        'SELECT id, name FROM subjects ORDER BY id'
    )).fetchall()

    created = 0
    for row in rows:
        sid = row._mapping['id']
        sname = row._mapping['name']
        exists = db.session.execute(text(
            'SELECT 1 FROM forum_boards WHERE board_type = :bt AND subject_id = :sid'
        ), {'bt': 'subject', 'sid': sid}).fetchone()
        if exists:
            continue

        slug = f'subject-{sid}'
        db.session.execute(text('''
            INSERT INTO forum_boards (name, slug, description, board_type, subject_id, sort_order, is_active)
            VALUES (:name, :slug, :desc, 'subject', :sid, :sort, true)
        '''), {
            'name': sname,
            'slug': slug,
            'desc': f'{sname} 学习交流',
            'sid': sid,
            'sort': sid,
        })
        created += 1

    if created:
        db.session.commit()
    return created


def get_boards(include_inactive: bool = False) -> list[dict]:
    """获取版块列表（含帖子数）— Redis 缓存 300s"""
    ver = get_forum_boards_version()
    cache_key = make_cache_key("forum:boards", {"inc": include_inactive, "ver": ver})
    cached = redis_get_json(cache_key)
    if cached is not None:
        return cached

    where = '' if include_inactive else 'WHERE b.is_active = true'
    rows = db.session.execute(text(f'''
        SELECT b.*,
               COALESCE(pc.cnt, 0) AS post_count
        FROM forum_boards b
        LEFT JOIN (
            SELECT board_id, COUNT(*) AS cnt
            FROM forum_posts WHERE is_deleted = false
            GROUP BY board_id
        ) pc ON pc.board_id = b.id
        {where}
        ORDER BY b.sort_order, b.id
    ''')).fetchall()
    result = [dict(r._mapping) for r in rows]

    redis_set_json(cache_key, result, ttl_seconds=300)
    return result


def get_board_by_id(board_id: int) -> Optional[dict]:
    row = db.session.execute(text(
        'SELECT * FROM forum_boards WHERE id = :bid'
    ), {'bid': board_id}).fetchone()
    return dict(row._mapping) if row else None


def create_board(name: str, slug: str, description: str, icon: str,
                 sort_order: int, created_by: int) -> dict:
    db.session.execute(text('''
        INSERT INTO forum_boards (name, slug, description, board_type, icon, sort_order, is_active, created_by)
        VALUES (:name, :slug, :desc, 'custom', :icon, :sort, true, :uid)
    '''), {
        'name': name, 'slug': slug, 'desc': description,
        'icon': icon, 'sort': sort_order, 'uid': created_by,
    })
    db.session.commit()
    bump_forum_boards_version()
    row = db.session.execute(text(
        'SELECT * FROM forum_boards WHERE slug = :slug'
    ), {'slug': slug}).fetchone()
    return dict(row._mapping)


def update_board(board_id: int, **fields) -> bool:
    allowed = {'name', 'slug', 'description', 'icon', 'sort_order', 'is_active'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    set_clause = ', '.join(f'{k} = :{k}' for k in updates)
    updates['bid'] = board_id
    db.session.execute(text(
        f'UPDATE forum_boards SET {set_clause}, updated_at = NOW() WHERE id = :bid'
    ), updates)
    db.session.commit()
    bump_forum_boards_version()
    return True


def delete_board(board_id: int) -> bool:
    """删除自定义版块（科目版块不可删除）"""
    row = db.session.execute(text(
        'SELECT board_type FROM forum_boards WHERE id = :bid'
    ), {'bid': board_id}).fetchone()
    if not row or row._mapping['board_type'] == 'subject':
        return False
    db.session.execute(text('DELETE FROM forum_boards WHERE id = :bid'), {'bid': board_id})
    db.session.commit()
    bump_forum_boards_version()
    return True
