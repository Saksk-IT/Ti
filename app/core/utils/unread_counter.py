# -*- coding: utf-8 -*-
"""Redis 未读计数缓存

用 Redis Hash ``chat:unread:{user_id}`` 维护每个会话的未读数，
避免每次都做 CTE+ROW_NUMBER+COUNT 全量查库。

无 Redis 时所有函数安全降级（返回 None / 静默忽略）。
"""
from __future__ import annotations

from typing import Optional


def _get_conn():
    """获取 decode_responses=False 的 Redis 连接"""
    from app.core.utils.redis_utils import get_redis_connection
    return get_redis_connection()


def incr_unread(user_id: int, conversation_id: int) -> None:
    """某会话有新消息时，对目标用户的未读数 +1"""
    conn = _get_conn()
    if conn is None:
        return
    try:
        conn.hincrby(f"chat:unread:{user_id}", str(conversation_id), 1)
    except Exception:
        pass


def reset_unread(user_id: int, conversation_id: int) -> None:
    """用户已读某会话后，清除该会话的未读计数"""
    conn = _get_conn()
    if conn is None:
        return
    try:
        conn.hdel(f"chat:unread:{user_id}", str(conversation_id))
    except Exception:
        pass


def get_total_unread(user_id: int) -> Optional[int]:
    """获取用户所有会话的未读总数。

    Returns:
        int: 未读总数
        None: Redis 不可用，调用方应降级查库
    """
    conn = _get_conn()
    if conn is None:
        return None
    try:
        vals = conn.hvals(f"chat:unread:{user_id}")
        if not vals:
            return 0
        return sum(int(v) for v in vals)
    except Exception:
        return None
