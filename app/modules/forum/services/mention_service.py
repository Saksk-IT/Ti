# -*- coding: utf-8 -*-
"""@提及服务"""
import re
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db


def extract_mentions(content: str) -> list[str]:
    """从内容中提取 @用户名 列表"""
    return re.findall(r'@(\w+)', content)


def create_mentions(source_type: str, source_id: int, mentioner_id: int,
                    content: str) -> int:
    """解析内容中的 @提及并创建记录，返回创建数量"""
    usernames = extract_mentions(content)
    if not usernames:
        return 0

    # 批量查找用户
    placeholders = ', '.join(f':u{i}' for i in range(len(usernames)))
    params = {f'u{i}': name for i, name in enumerate(usernames)}
    rows = db.session.execute(text(
        f'SELECT id, username FROM users WHERE username IN ({placeholders})'
    ), params).fetchall()

    created = 0
    for row in rows:
        uid = row._mapping['id']
        if uid == mentioner_id:
            continue  # 不提及自己
        db.session.execute(text('''
            INSERT INTO forum_mentions (source_type, source_id, mentioned_user_id, mentioner_id)
            VALUES (:st, :sid, :muid, :mid)
            ON CONFLICT DO NOTHING
        '''), {'st': source_type, 'sid': source_id, 'muid': uid, 'mid': mentioner_id})
        created += 1

    if created:
        db.session.commit()
    return created


def get_unread_mentions(user_id: int, page: int = 1, per_page: int = 20) -> dict:
    """获取用户的未读提及"""
    offset = (page - 1) * per_page
    total = db.session.execute(text(
        'SELECT COUNT(*) FROM forum_mentions WHERE mentioned_user_id=:uid AND is_read=false'
    ), {'uid': user_id}).scalar()

    rows = db.session.execute(text('''
        SELECT m.*, u.username AS mentioner_name, u.avatar AS mentioner_avatar,
               CASE m.source_type
                   WHEN 'post' THEN (SELECT title FROM forum_posts WHERE id=m.source_id)
                   WHEN 'comment' THEN (SELECT LEFT(content, 100) FROM forum_comments WHERE id=m.source_id)
               END AS source_preview,
               CASE m.source_type
                   WHEN 'post' THEN m.source_id
                   WHEN 'comment' THEN (SELECT post_id FROM forum_comments WHERE id=m.source_id)
               END AS post_id
        FROM forum_mentions m
        JOIN users u ON u.id = m.mentioner_id
        WHERE m.mentioned_user_id = :uid
        ORDER BY m.is_read ASC, m.created_at DESC
        LIMIT :limit OFFSET :offset
    '''), {'uid': user_id, 'limit': per_page, 'offset': offset}).fetchall()

    return {
        'mentions': [dict(r._mapping) for r in rows],
        'total': total, 'page': page, 'per_page': per_page,
    }


def mark_mentions_read(user_id: int, mention_ids: Optional[list[int]] = None) -> int:
    """标记提及为已读，返回更新数量"""
    if mention_ids:
        placeholders = ', '.join(f':id{i}' for i in range(len(mention_ids)))
        params = {f'id{i}': mid for i, mid in enumerate(mention_ids)}
        params['uid'] = user_id
        result = db.session.execute(text(
            f'UPDATE forum_mentions SET is_read=true WHERE mentioned_user_id=:uid AND id IN ({placeholders})'
        ), params)
    else:
        result = db.session.execute(text(
            'UPDATE forum_mentions SET is_read=true WHERE mentioned_user_id=:uid AND is_read=false'
        ), {'uid': user_id})
    db.session.commit()
    return result.rowcount


def get_unread_count(user_id: int) -> int:
    """获取未读提及数"""
    return db.session.execute(text(
        'SELECT COUNT(*) FROM forum_mentions WHERE mentioned_user_id=:uid AND is_read=false'
    ), {'uid': user_id}).scalar() or 0
