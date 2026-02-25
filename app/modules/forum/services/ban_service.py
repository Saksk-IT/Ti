# -*- coding: utf-8 -*-
"""用户封禁服务"""
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db


def is_banned(user_id: int) -> bool:
    """检查用户是否被封禁（含过期检查）"""
    row = db.session.execute(text('''
        SELECT id FROM forum_user_bans
        WHERE user_id=:uid AND is_active=true
          AND (expires_at IS NULL OR expires_at > NOW())
        LIMIT 1
    '''), {'uid': user_id}).fetchone()
    return row is not None


def ban_user(user_id: int, banned_by: int, reason: str,
             expires_at: Optional[str] = None) -> dict:
    """封禁用户"""
    if is_banned(user_id):
        return {'error': '该用户已被封禁'}

    params: dict = {'uid': user_id, 'by': banned_by, 'reason': reason}
    expires_sql = 'NULL'
    if expires_at:
        expires_sql = ':expires'
        params['expires'] = expires_at

    db.session.execute(text(f'''
        INSERT INTO forum_user_bans (user_id, banned_by, reason, expires_at)
        VALUES (:uid, :by, :reason, {expires_sql})
    '''), params)
    db.session.commit()
    return {'success': True}


def unban_user(user_id: int) -> bool:
    """解除封禁"""
    result = db.session.execute(text(
        'UPDATE forum_user_bans SET is_active=false WHERE user_id=:uid AND is_active=true'
    ), {'uid': user_id})
    db.session.commit()
    return result.rowcount > 0


def get_bans(page: int = 1, per_page: int = 20, active_only: bool = True) -> dict:
    """获取封禁列表"""
    offset = (page - 1) * per_page
    condition = 'WHERE b.is_active=true' if active_only else ''

    total = db.session.execute(text(
        f'SELECT COUNT(*) FROM forum_user_bans b {condition}'
    )).scalar()

    rows = db.session.execute(text(f'''
        SELECT b.*, u.username AS user_name, u.avatar AS user_avatar,
               a.username AS banned_by_name
        FROM forum_user_bans b
        JOIN users u ON u.id = b.user_id
        LEFT JOIN users a ON a.id = b.banned_by
        {condition}
        ORDER BY b.created_at DESC
        LIMIT :limit OFFSET :offset
    '''), {'limit': per_page, 'offset': offset}).fetchall()

    return {
        'bans': [dict(r._mapping) for r in rows],
        'total': total, 'page': page, 'per_page': per_page,
    }
