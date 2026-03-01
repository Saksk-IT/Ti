# -*- coding: utf-8 -*-
"""限流键工具：统一按用户优先、IP 兜底。"""

from __future__ import annotations

from flask import g, request, session
from flask_limiter.util import get_remote_address


def _safe_user_id() -> int | None:
    """提取当前请求用户 ID（优先 g，再回退 session）。"""
    cached_uid = getattr(g, "_limiter_uid_cache", None)
    if cached_uid is not None:
        return int(cached_uid) if cached_uid else None

    try:
        uid = getattr(g, "current_user_id", None)
        if uid:
            g._limiter_uid_cache = int(uid)
            return int(uid)
    except Exception:
        pass

    try:
        uid = session.get("user_id")
        if uid:
            g._limiter_uid_cache = int(uid)
            return int(uid)
    except Exception:
        pass

    # 可选 JWT（用于无需 @auth_required 但可携带 token 的接口）
    try:
        token = request.headers.get("Authorization") or request.headers.get("authorization") or ""
        raw = str(token).strip()
        if raw.startswith("Bearer "):
            raw = raw[7:].strip()
        if raw:
            from app.core.utils.jwt_utils import decode_jwt_token
            payload = decode_jwt_token(raw)
            if payload and payload.get("user_id"):
                g._limiter_uid_cache = int(payload.get("user_id"))
                return int(payload.get("user_id"))
    except Exception:
        pass
    g._limiter_uid_cache = 0
    return None


def _safe_client_ip() -> str:
    """提取客户端 IP。"""
    try:
        ip = get_remote_address()
        if ip:
            return str(ip)
    except Exception:
        pass
    try:
        ip = request.remote_addr
        if ip:
            return str(ip)
    except Exception:
        pass
    return "unknown"


def user_or_ip_rate_key() -> str:
    """统一限流键：uid 优先，IP 兜底。"""
    uid = _safe_user_id()
    if uid:
        return f"uid:{uid}"
    return f"ip:{_safe_client_ip()}"
