# -*- coding: utf-8 -*-
"""WebVPN 登录态刷新服务。"""

from __future__ import annotations

import base64
import re
import secrets
import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests

from app.core.utils.credential_crypto import decrypt_secret, encrypt_secret
from app.core.utils.redis_utils import redis_delete, redis_get_json, redis_set_json
from app.modules.admin.services.system_config_service import SystemConfigService

from .client import (
    JWXTClient,
    ScheduleAuthError,
    ScheduleClientError,
    WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE,
    _extract_input_value,
    _load_cookie_header,
    _looks_webvpn_logged_in,
    _requires_webvpn_interactive_challenge,
)


WEBVPN_REFRESH_REQUIRED_ERROR_CODE = "WEBVPN_REFRESH_REQUIRED"
WEBVPN_REFRESH_REQUIRED_MESSAGE = "WebVPN 登录态已失效，请输入验证码后继续查询"
_WEBVPN_CHALLENGE_TTL_SECONDS = 300
_WEBVPN_CHALLENGE_KEY_PREFIX = "edu_schedule:webvpn_challenge:"
_WEBVPN_CHALLENGE_LOCK = threading.Lock()
_WEBVPN_CHALLENGES: Dict[str, Dict[str, Any]] = {}


def should_start_webvpn_refresh(exc: Exception) -> bool:
    if not isinstance(exc, ScheduleAuthError):
        return False
    message = str(exc).strip()
    return message in {
        "WebVPN 登录态不可用",
        WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE,
    }


def _challenge_key(challenge_id: str) -> str:
    return f"{_WEBVPN_CHALLENGE_KEY_PREFIX}{challenge_id}"


def _cleanup_memory_challenges(now: float) -> None:
    expired_ids = [
        challenge_id
        for challenge_id, challenge in _WEBVPN_CHALLENGES.items()
        if float(challenge.get("expires_at") or 0) <= now
    ]
    for challenge_id in expired_ids:
        _WEBVPN_CHALLENGES.pop(challenge_id, None)


def _store_challenge(challenge: Dict[str, Any]) -> str:
    challenge_id = secrets.token_urlsafe(24)
    now = time.time()
    stored = {
        **challenge,
        "challenge_id": challenge_id,
        "expires_at": now + _WEBVPN_CHALLENGE_TTL_SECONDS,
    }
    redis_set_json(_challenge_key(challenge_id), stored, ttl_seconds=_WEBVPN_CHALLENGE_TTL_SECONDS)
    with _WEBVPN_CHALLENGE_LOCK:
        _cleanup_memory_challenges(now)
        _WEBVPN_CHALLENGES[challenge_id] = stored
    return challenge_id


def _pop_challenge(challenge_id: str) -> Dict[str, Any]:
    now = time.time()
    redis_challenge = redis_get_json(_challenge_key(challenge_id))
    redis_delete(_challenge_key(challenge_id))

    with _WEBVPN_CHALLENGE_LOCK:
        _cleanup_memory_challenges(now)
        memory_challenge = _WEBVPN_CHALLENGES.pop(challenge_id, None)

    challenge = redis_challenge or memory_challenge

    if not isinstance(challenge, dict):
        raise ValueError("验证码会话已过期，请重新刷新")
    if float(challenge.get("expires_at") or 0) <= now:
        raise ValueError("验证码会话已过期，请重新刷新")
    return challenge


def _session_cookie_header(request_session: requests.Session) -> str:
    pairs: Dict[str, str] = {}
    for cookie in request_session.cookies:
        name = str(getattr(cookie, "name", "") or "").strip()
        value = str(getattr(cookie, "value", "") or "")
        if name:
            pairs[name] = value
    return "; ".join(f"{name}={value}" for name, value in pairs.items())


def _captcha_data_url(response: Any) -> str:
    content = bytes(getattr(response, "content", b"") or b"")
    if not content and getattr(response, "text", ""):
        content = str(response.text).encode("utf-8")
    if not content:
        raise ValueError("验证码图片获取失败")

    content_type = str(getattr(response, "headers", {}).get("Content-Type") or "image/png").split(";", 1)[0]
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _webvpn_login_url(cfg: Dict[str, Any]) -> str:
    base_url = str(cfg.get("webvpn_base_url") or "").strip().rstrip("/")
    login_path = str(cfg.get("webvpn_login_path") or "/users/sign_in").strip()
    return urljoin(base_url + "/", login_path.lstrip("/"))


def _captcha_url(cfg: Dict[str, Any]) -> str:
    base_url = str(cfg.get("webvpn_base_url") or "").strip().rstrip("/")
    return urljoin(base_url + "/", "rucaptcha/")


def _origin_from_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _require_webvpn_refresh_config(cfg: Dict[str, Any]) -> None:
    if not bool(cfg.get("use_webvpn", True)):
        raise ValueError("当前未启用 WebVPN")
    if not str(cfg.get("webvpn_username") or "").strip() or not str(cfg.get("webvpn_password") or ""):
        raise ValueError("请先保存 WebVPN 账号和密码")


def _new_webvpn_session() -> requests.Session:
    request_session = requests.Session()
    request_session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; TiWebVPNRefresh/1.0)",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    return request_session


def _validate_captcha_code(captcha_code: str) -> str:
    text = str(captcha_code or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9]{1,10}", text):
        raise ValueError("验证码格式不正确")
    return text


class WebVPNSessionRefreshService:
    """生成 WebVPN 验证码挑战，并用管理员配置刷新共享 Cookie。"""

    @staticmethod
    def start(owner_user_id: Optional[int] = None, admin_id: Optional[int] = None) -> Dict[str, Any]:
        cfg = SystemConfigService.get_edu_schedule_config()
        _require_webvpn_refresh_config(cfg)

        webvpn_client = JWXTClient(cfg)
        request_session = _new_webvpn_session()
        login_url = _webvpn_login_url(cfg)
        page = webvpn_client._request(
            request_session,
            "GET",
            login_url,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            allow_redirects=True,
        )
        if _looks_webvpn_logged_in(page.text):
            cookie_header = _session_cookie_header(request_session)
            if not cookie_header:
                raise ValueError("WebVPN 已登录但未获取到 Cookie")
            data = SystemConfigService.save_edu_schedule_webvpn_cookie(cookie_header, admin_id=admin_id)
            return {**data, "refreshed": True}

        token = _extract_input_value(page.text, "authenticity_token")
        if not token:
            raise ValueError("WebVPN 登录页解析失败")

        captcha_response = webvpn_client._request(
            request_session,
            "GET",
            _captcha_url(cfg),
            headers={
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": login_url,
            },
            allow_redirects=True,
        )
        temporary_cookie = _session_cookie_header(request_session)
        challenge_id = _store_challenge({
            "owner_user_id": int(owner_user_id) if owner_user_id else None,
            "login_url": login_url,
            "authenticity_token": token,
            "temporary_cookie_ciphertext": encrypt_secret(temporary_cookie) if temporary_cookie else "",
        })
        return {
            "challenge_id": challenge_id,
            "captcha_image": _captcha_data_url(captcha_response),
            "expires_in_seconds": _WEBVPN_CHALLENGE_TTL_SECONDS,
        }

    @staticmethod
    def complete(
        challenge_id: str,
        captcha_code: str,
        *,
        owner_user_id: Optional[int] = None,
        admin_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        challenge_id = str(challenge_id or "").strip()
        if not challenge_id:
            raise ValueError("缺少验证码会话")
        captcha_code = _validate_captcha_code(captcha_code)

        challenge = _pop_challenge(challenge_id)
        expected_owner = challenge.get("owner_user_id")
        if expected_owner is not None and int(expected_owner) != int(owner_user_id or 0):
            raise ValueError("验证码会话已过期，请重新刷新")

        cfg = SystemConfigService.get_edu_schedule_config()
        _require_webvpn_refresh_config(cfg)
        request_session = _new_webvpn_session()
        temporary_cookie_ciphertext = str(challenge.get("temporary_cookie_ciphertext") or "")
        if temporary_cookie_ciphertext:
            _load_cookie_header(
                request_session,
                decrypt_secret(temporary_cookie_ciphertext),
                str(cfg.get("webvpn_base_url") or ""),
            )

        login_url = str(challenge.get("login_url") or _webvpn_login_url(cfg))
        form_data = {
            "utf8": "✓",
            "authenticity_token": str(challenge.get("authenticity_token") or ""),
            "user[login]": str(cfg.get("webvpn_username") or "").strip(),
            "user[password]": str(cfg.get("webvpn_password") or ""),
            "user[dymatice_code]": "unknown",
            "user[otp_with_capcha]": "false",
            "_rucaptcha": captcha_code,
            "commit": "登录 Login",
        }
        result = JWXTClient(cfg)._request(
            request_session,
            "POST",
            login_url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": _origin_from_url(login_url),
                "Referer": login_url,
            },
            data=form_data,
            allow_redirects=True,
        )
        if _looks_webvpn_logged_in(result.text):
            cookie_header = _session_cookie_header(request_session)
            if not cookie_header:
                raise ValueError("登录成功但未获取到 WebVPN Cookie")
            return SystemConfigService.save_edu_schedule_webvpn_cookie(cookie_header, admin_id=admin_id)
        if _requires_webvpn_interactive_challenge(result.text):
            raise ValueError("验证码错误或已过期，请重新刷新验证码")
        raise ValueError("WebVPN 登录失败，请检查账号密码或验证码")
