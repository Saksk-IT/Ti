# -*- coding: utf-8 -*-
"""
用户状态缓存（JWT/Web 会话校验加速）

目标：
- 小程序端每次请求都会走 JWT 校验，Web 端每次请求也需要同步锁定/权限状态；
  原实现每次都查询 users 表，在 SQLite + 单机场景下会带来不必要的读压力。
- 本缓存采用"短 TTL + 变更时主动失效"的策略，尽量做到：
  - 正常情况下减少 DB 读；
  - 用户被锁定/强制下线/解绑微信等变更能尽快生效。
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional

from .redis_utils import redis_delete, redis_get_json, redis_set_json

_CACHE_PREFIX = 'auth:user_state:'
_MISSING = object()
_WEB_SESSION_STATE_KEYS = frozenset({
    'session_version',
    'is_locked',
    'is_admin',
    'is_subject_admin',
    'is_notification_admin',
    'email',
})

_MEM_LOCK = threading.Lock()
_MEM_CACHE: Dict[str, Any] = {}


def _now() -> float:
    return time.monotonic()


def _ttl_seconds() -> int:
    try:
        from flask import current_app

        ttl = current_app.config.get('JWT_USER_STATE_CACHE_TTL_SECONDS')
        ttl = int(ttl) if ttl is not None else int(os.environ.get('JWT_USER_STATE_CACHE_TTL_SECONDS', '20') or 20)
    except Exception:
        ttl = int(os.environ.get('JWT_USER_STATE_CACHE_TTL_SECONDS', '20') or 20)
    return max(0, int(ttl))


def _mem_get(key: str):
    ttl = _ttl_seconds()
    if ttl <= 0:
        return _MISSING
    with _MEM_LOCK:
        item = _MEM_CACHE.get(key)
        if not item:
            return _MISSING
        exp_at, value = item
        if exp_at < _now():
            _MEM_CACHE.pop(key, None)
            return _MISSING
        return value


def _mem_set(key: str, value: Any):
    ttl = _ttl_seconds()
    if ttl <= 0:
        return
    with _MEM_LOCK:
        _MEM_CACHE[key] = (_now() + float(ttl), value)


def _mem_delete(key: str):
    with _MEM_LOCK:
        _MEM_CACHE.pop(key, None)


def _key(user_id: int) -> str:
    return f'{_CACHE_PREFIX}{int(user_id)}'


def get_user_state(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户状态缓存。"""
    k = _key(user_id)
    cached = redis_get_json(k)
    if isinstance(cached, dict):
        return cached

    mem = _mem_get(k)
    if mem is not _MISSING and isinstance(mem, dict):
        return mem
    return None


def set_user_state(user_id: int, state: Dict[str, Any]) -> None:
    """写入用户状态缓存（优先 Redis，失败则内存兜底）。"""
    k = _key(user_id)
    ttl = _ttl_seconds()
    ok = redis_set_json(k, state, ttl_seconds=ttl if ttl > 0 else None)
    if not ok:
        _mem_set(k, state)


def invalidate_user_state(user_id: int) -> None:
    """失效用户状态缓存（用于锁定/解绑/强制下线等变更后）。"""
    k = _key(user_id)
    redis_delete(k)
    _mem_delete(k)


def has_complete_web_session_state(state: Any) -> bool:
    """判断缓存是否包含 Web 会话同步所需的完整权限字段。"""
    return isinstance(state, dict) and _WEB_SESSION_STATE_KEYS.issubset(state.keys())


def user_state_from_model(user: Any) -> Dict[str, Any]:
    """从 User 模型构造完整用户状态缓存。"""
    return {
        'session_version': user.session_version or 0,
        'is_locked': bool(user.is_locked),
        'openid': (user.openid or '').strip(),
        'is_admin': bool(user.is_admin),
        'is_subject_admin': bool(user.is_subject_admin),
        'is_notification_admin': bool(user.is_notification_admin),
        'email': user.email or '',
    }
