# -*- coding: utf-8 -*-
"""
Redis 工具

说明：
- 本项目既有 SQLite，也有 Web + 小程序双端。
- Redis 在这里主要用于：缓存、RQ 队列、以及 Flask-Limiter 的共享存储。
- 代码必须在未安装 redis/rq 依赖、或未配置 REDIS_URL 时可安全降级。
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional


def get_redis_url_from_env() -> Optional[str]:
    """在无 Flask 上下文（如 RQ worker）场景获取 Redis URL。"""
    url = (
        os.environ.get('REDIS_URL')
        or os.environ.get('RATELIMIT_STORAGE_URI')
        or os.environ.get('RATELIMIT_STORAGE_URL')
        or ''
    )
    url = str(url).strip()
    if not url:
        return None
    if not url.startswith(('redis://', 'rediss://')):
        return None
    return url


def get_redis_url() -> Optional[str]:
    """在 Flask 上下文中获取 Redis URL。"""
    try:
        from flask import current_app

        url = (
            current_app.config.get('REDIS_URL')
            or current_app.config.get('RATELIMIT_STORAGE_URI')
            or current_app.config.get('RATELIMIT_STORAGE_URL')
            or ''
        )
        url = str(url).strip()
        if not url:
            return None
        if not url.startswith(('redis://', 'rediss://')):
            return None
        return url
    except Exception:
        return get_redis_url_from_env()


def get_redis_connection(url: Optional[str] = None):
    """获取 Redis 连接（decode_responses=False，兼容 RQ 二进制数据）。"""
    try:
        import redis  # type: ignore
    except Exception:
        return None

    redis_url = url or get_redis_url()
    if not redis_url:
        return None

    try:
        return redis.Redis.from_url(redis_url, decode_responses=False)
    except Exception:
        return None


def _decode_bytes(raw: Any) -> Any:
    if isinstance(raw, (bytes, bytearray)):
        try:
            return raw.decode('utf-8')
        except Exception:
            return raw.decode('utf-8', errors='ignore')
    return raw


def redis_get_text(key: str) -> Optional[str]:
    conn = get_redis_connection()
    if conn is None:
        return None
    try:
        raw = conn.get(key)
    except Exception:
        return None
    if raw is None:
        return None
    val = _decode_bytes(raw)
    return str(val)


def redis_set_text(key: str, value: str, ttl_seconds: Optional[int] = None, *, nx: bool = False) -> bool:
    conn = get_redis_connection()
    if conn is None:
        return False
    try:
        if ttl_seconds is not None:
            conn.set(key, str(value), ex=int(ttl_seconds), nx=bool(nx))
        else:
            conn.set(key, str(value), nx=bool(nx))
        return True
    except Exception:
        return False


def redis_get_json(key: str) -> Optional[Any]:
    raw = redis_get_text(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def redis_set_json(key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
    try:
        payload = json.dumps(value, ensure_ascii=False)
    except Exception:
        return False
    return redis_set_text(key, payload, ttl_seconds=ttl_seconds, nx=False)


def redis_delete(key: str) -> bool:
    conn = get_redis_connection()
    if conn is None:
        return False
    try:
        conn.delete(key)
        return True
    except Exception:
        return False


def redis_incr(key: str, amount: int = 1) -> Optional[int]:
    """Redis INCR：用于缓存版本号等场景；失败返回 None。"""
    conn = get_redis_connection()
    if conn is None:
        return None
    try:
        return int(conn.incr(key, int(amount)))
    except Exception:
        return None
