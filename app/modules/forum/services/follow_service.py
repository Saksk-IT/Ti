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
    """获取关注状态 + 计数（单条 SQL 合并 4 个子查询）"""
    row = db.session.execute(text('''
        SELECT
            EXISTS(SELECT 1 FROM user_follows WHERE follower_id=:uid AND following_id=:tid) AS i_follow,
            EXISTS(SELECT 1 FROM user_follows WHERE follower_id=:tid AND following_id=:uid) AS follows_me,
            (SELECT COUNT(*) FROM user_follows WHERE following_id=:tid) AS follower_count,
            (SELECT COUNT(*) FROM user_follows WHERE follower_id=:tid) AS following_count
    '''), {'uid': user_id, 'tid': target_id}).fetchone()
    m = row._mapping
    i_follow = bool(m['i_follow'])
    follows_me = bool(m['follows_me'])
    return {
        'i_follow': i_follow,
        'follows_me': follows_me,
        'mutual': i_follow and follows_me,
        'follower_count': m['follower_count'] or 0,
        'following_count': m['following_count'] or 0,
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
