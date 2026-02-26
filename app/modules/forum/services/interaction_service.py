# -*- coding: utf-8 -*-
"""互动通知服务"""
import logging
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db

logger = logging.getLogger(__name__)

# action_type 常量
ACTION_LIKE_POST = 'like_post'
ACTION_LIKE_COMMENT = 'like_comment'
ACTION_COMMENT = 'comment'
ACTION_REPLY = 'reply'
ACTION_MENTION = 'mention'
ACTION_FOLLOW = 'follow'


def create_notification(
    user_id: int,
    actor_id: int,
    action_type: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    post_id: Optional[int] = None,
    content_preview: Optional[str] = None,
) -> bool:
    """创建互动通知（去重、不通知自己）"""
    if user_id == actor_id:
        return False

    try:
        db.session.execute(text('''
            INSERT INTO interaction_notifications
                (user_id, actor_id, action_type, target_type, target_id, post_id, content_preview)
            VALUES (:uid, :aid, :atype, :ttype, :tid, :pid, :preview)
            ON CONFLICT (user_id, actor_id, action_type, target_type, target_id) DO UPDATE
            SET is_read = false, created_at = NOW(),
                content_preview = EXCLUDED.content_preview,
                post_id = EXCLUDED.post_id
        '''), {
            'uid': user_id, 'aid': actor_id, 'atype': action_type,
            'ttype': target_type, 'tid': target_id, 'pid': post_id,
            'preview': (content_preview or '')[:200],
        })
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.warning("创建互动通知失败: %s", e)
        return False


def get_notifications(
    user_id: int, page: int = 1, per_page: int = 20
) -> dict:
    """获取互动通知列表（未读优先）"""
    offset = (page - 1) * per_page
    total = db.session.execute(text(
        'SELECT COUNT(*) FROM interaction_notifications WHERE user_id=:uid'
    ), {'uid': user_id}).scalar() or 0

    rows = db.session.execute(text('''
        SELECT n.*, u.username AS actor_name, u.avatar AS actor_avatar
        FROM interaction_notifications n
        JOIN users u ON u.id = n.actor_id
        WHERE n.user_id = :uid
        ORDER BY n.is_read ASC, n.created_at DESC
        LIMIT :lim OFFSET :off
    '''), {'uid': user_id, 'lim': per_page, 'off': offset}).fetchall()

    return {
        'notifications': [dict(r._mapping) for r in rows],
        'total': total, 'page': page, 'per_page': per_page,
    }


def mark_read(user_id: int, ids: Optional[list[int]] = None) -> int:
    """标记已读"""
    if ids:
        placeholders = ', '.join(f':id{i}' for i in range(len(ids)))
        params = {f'id{i}': nid for i, nid in enumerate(ids)}
        params['uid'] = user_id
        result = db.session.execute(text(
            f'UPDATE interaction_notifications SET is_read=true '
            f'WHERE user_id=:uid AND id IN ({placeholders})'
        ), params)
    else:
        result = db.session.execute(text(
            'UPDATE interaction_notifications SET is_read=true '
            'WHERE user_id=:uid AND is_read=false'
        ), {'uid': user_id})
    db.session.commit()
    return result.rowcount


def get_unread_count(user_id: int) -> int:
    """获取未读互动通知数"""
    return db.session.execute(text(
        'SELECT COUNT(*) FROM interaction_notifications '
        'WHERE user_id=:uid AND is_read=false'
    ), {'uid': user_id}).scalar() or 0
