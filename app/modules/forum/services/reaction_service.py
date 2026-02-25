# -*- coding: utf-8 -*-
"""表情回应服务"""
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db


def get_reactions(target_type: str, target_id: int) -> list[dict]:
    """获取目标的所有表情回应（按 emoji 分组统计）"""
    rows = db.session.execute(text('''
        SELECT emoji, COUNT(*) AS count,
               ARRAY_AGG(u.username ORDER BY r.created_at) AS usernames
        FROM forum_reactions r
        JOIN users u ON u.id = r.user_id
        WHERE r.target_type = :tt AND r.target_id = :tid
        GROUP BY emoji
        ORDER BY count DESC
    '''), {'tt': target_type, 'tid': target_id}).fetchall()
    return [dict(r._mapping) for r in rows]


def get_user_reactions(target_type: str, target_id: int, user_id: int) -> list[str]:
    """获取用户对目标的表情列表"""
    rows = db.session.execute(text(
        'SELECT emoji FROM forum_reactions WHERE user_id=:uid AND target_type=:tt AND target_id=:tid'
    ), {'uid': user_id, 'tt': target_type, 'tid': target_id}).fetchall()
    return [r._mapping['emoji'] for r in rows]


def toggle_reaction(user_id: int, target_type: str, target_id: int, emoji: str) -> bool:
    """切换表情回应，返回 True=添加, False=移除"""
    existing = db.session.execute(text(
        'SELECT id FROM forum_reactions WHERE user_id=:uid AND target_type=:tt AND target_id=:tid AND emoji=:emoji'
    ), {'uid': user_id, 'tt': target_type, 'tid': target_id, 'emoji': emoji}).fetchone()

    if existing:
        db.session.execute(text('DELETE FROM forum_reactions WHERE id=:rid'), {'rid': existing._mapping['id']})
        db.session.commit()
        return False
    else:
        db.session.execute(text(
            'INSERT INTO forum_reactions (user_id, target_type, target_id, emoji) VALUES (:uid, :tt, :tid, :emoji)'
        ), {'uid': user_id, 'tt': target_type, 'tid': target_id, 'emoji': emoji})
        db.session.commit()
        return True
