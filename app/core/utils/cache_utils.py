# -*- coding: utf-8 -*-
"""
轻量缓存工具（Redis 优先，失败自动降级）

用途：
- 读接口短 TTL 缓存（将响应 JSON 存入 Redis）
- “版本号失效”策略：写接口只需 bump 版本号，读接口 key 自动变化
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from .redis_utils import redis_get_text, redis_incr, redis_set_text

_CACHE_KEY_PREFIX = "cache:"
_VERSION_KEY_PREFIX = "cache:ver:"


def _stable_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_cache_key(feature: str, params: Dict[str, Any]) -> str:
    """构造短且稳定的缓存 key（避免 Redis key 过长）。"""
    feature = str(feature or "").strip() or "default"
    payload = _stable_dumps(params or {})
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{_CACHE_KEY_PREFIX}{feature}:{digest}"


def _version_key(name: str) -> str:
    name = str(name or "").strip() or "default"
    return f"{_VERSION_KEY_PREFIX}{name}"


def get_version(name: str, default: int = 1) -> int:
    """获取版本号（不存在则初始化为 default）。"""
    k = _version_key(name)
    raw = redis_get_text(k)
    if raw is None:
        try:
            redis_set_text(k, str(int(default)), nx=True)
        except Exception:
            pass
        return max(0, int(default))
    try:
        return max(0, int(raw))
    except Exception:
        return max(0, int(default))


def bump_version(name: str, amount: int = 1) -> Optional[int]:
    """版本号自增；失败返回 None。"""
    return redis_incr(_version_key(name), amount=int(amount))


# === 本项目常用版本号封装 ===


def get_questions_version() -> int:
    return get_version("quiz:questions", default=1)


def bump_questions_version() -> Optional[int]:
    return bump_version("quiz:questions", amount=1)


def get_subjects_version() -> int:
    return get_version("quiz:subjects", default=1)


def bump_subjects_version() -> Optional[int]:
    return bump_version("quiz:subjects", amount=1)


def get_user_quiz_version(user_id: int) -> int:
    return get_version(f"quiz:u:{int(user_id)}", default=1)


def bump_user_quiz_version(user_id: int) -> Optional[int]:
    return bump_version(f"quiz:u:{int(user_id)}", amount=1)

