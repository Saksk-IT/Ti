# -*- coding: utf-8 -*-
"""关注服务"""
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db


def follow_user(follower_id: int, following_id: int) -> dict:
    """关注用户（幂等）"""
    if follower_id == following_id:
        return {'error': '不能关注自己'}

    db.session.execute(text('''
        INSERT INTO user_follows (follower_id, following_id)
        VALUES (:fid, :tid)
        ON CONFLICT (follower_id, following_id) DO NOTHING
    '''), {'fid': follower_id, 'tid': following_id})
    db.session.commit()
    return {'success': True}


def unfollow_user(follower_id: int, following_id: int) -> dict:
    """取消关注"""
    db.session.execute(text(
        'DELETE FROM user_follows WHERE follower_id=:fid AND following_id=:tid'
    ), {'fid': follower_id, 'tid': following_id})
    db.session.commit()
    return {'success': True}


def is_following(follower_id: int, following_id: int) -> bool:
    """检查是否已关注"""
    row = db.session.execute(text(
        'SELECT 1 FROM user_follows WHERE follower_id=:fid AND following_id=:tid'
    ), {'fid': follower_id, 'tid': following_id}).fetchone()
    return row is not None


def get_follow_status(user_id: int, target_id: int) -> dict:
    """获取关注状态 + 计数"""
    i_follow = is_following(user_id, target_id)
    follows_me = is_following(target_id, user_id)
    counts = get_follow_counts(target_id)
    return {
        'i_follow': i_follow,
        'follows_me': follows_me,
        'mutual': i_follow and follows_me,
        **counts,
    }


def get_follow_counts(user_id: int) -> dict:
    """获取粉丝数和关注数"""
    followers = db.session.execute(text(
        'SELECT COUNT(*) FROM user_follows WHERE following_id=:uid'
    ), {'uid': user_id}).scalar() or 0
    following = db.session.execute(text(
        'SELECT COUNT(*) FROM user_follows WHERE follower_id=:uid'
    ), {'uid': user_id}).scalar() or 0
    return {'follower_count': followers, 'following_count': following}


def get_followers(user_id: int, page: int = 1, per_page: int = 20) -> dict:
    """获取粉丝列表"""
    offset = (page - 1) * per_page
    total = db.session.execute(text(
        'SELECT COUNT(*) FROM user_follows WHERE following_id=:uid'
    ), {'uid': user_id}).scalar() or 0

    rows = db.session.execute(text('''
        SELECT u.id, u.username, u.avatar, uf.created_at AS followed_at
        FROM user_follows uf
        JOIN users u ON u.id = uf.follower_id
        WHERE uf.following_id = :uid
        ORDER BY uf.created_at DESC
        LIMIT :lim OFFSET :off
    '''), {'uid': user_id, 'lim': per_page, 'off': offset}).fetchall()

    return {
        'users': [dict(r._mapping) for r in rows],
        'total': total, 'page': page, 'per_page': per_page,
    }


def get_following(user_id: int, page: int = 1, per_page: int = 20) -> dict:
    """获取关注列表"""
    offset = (page - 1) * per_page
    total = db.session.execute(text(
        'SELECT COUNT(*) FROM user_follows WHERE follower_id=:uid'
    ), {'uid': user_id}).scalar() or 0

    rows = db.session.execute(text('''
        SELECT u.id, u.username, u.avatar, uf.created_at AS followed_at
        FROM user_follows uf
        JOIN users u ON u.id = uf.following_id
        WHERE uf.follower_id = :uid
        ORDER BY uf.created_at DESC
        LIMIT :lim OFFSET :off
    '''), {'uid': user_id, 'lim': per_page, 'off': offset}).fetchall()

    return {
        'users': [dict(r._mapping) for r in rows],
        'total': total, 'page': page, 'per_page': per_page,
    }
