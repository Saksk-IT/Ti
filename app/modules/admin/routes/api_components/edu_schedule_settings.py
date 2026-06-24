# -*- coding: utf-8 -*-
"""Admin API routes - edu schedule settings."""

from __future__ import annotations

import base64
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict
from urllib.parse import urljoin, urlparse

from flask import current_app, request, session
import requests

from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import admin_required
from app.modules.admin.services.system_config_service import SystemConfigService
from app.modules.edu_schedule.services.client import (
    JWXTClient,
    ScheduleAuthError,
    ScheduleClientError,
    _extract_input_value,
    _looks_webvpn_logged_in,
    _requires_webvpn_interactive_challenge,
)

from ..api_bp import admin_api_bp


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _validate_hosted_url(value: str, field_name: str) -> str:
    text = (value or "").strip().rstrip("/")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field_name} 必须是 http:// 或 https:// 开头的完整地址")
    return text


def _normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    timeout = int(data.get("request_timeout") or 20)
    if timeout < 5 or timeout > 120:
        raise ValueError("请求超时必须在 5-120 秒之间")

    webvpn_base = _validate_hosted_url(str(data.get("webvpn_base_url") or "https://webvpn.synu.edu.cn"), "WebVPN 地址")
    jwxt_base = _validate_hosted_url(str(data.get("jwxt_base_url") or "https://jwxt.webvpn.synu.edu.cn/jwglxt"), "教务系统地址")

    allowed_hosts_text = str(data.get("allowed_hosts_text") or data.get("allowed_hosts") or "").strip()
    if not allowed_hosts_text:
        allowed_hosts = sorted({urlparse(webvpn_base).hostname or "", urlparse(jwxt_base).hostname or ""})
        allowed_hosts_text = ",".join(host for host in allowed_hosts if host)

    return {
        "enabled": _as_bool(data.get("enabled"), False),
        "use_webvpn": _as_bool(data.get("use_webvpn"), True),
        "webvpn_base_url": webvpn_base,
        "webvpn_login_path": str(data.get("webvpn_login_path") or "/users/sign_in").strip(),
        "webvpn_username": str(data.get("webvpn_username") or "").strip(),
        "webvpn_password": str(data.get("webvpn_password") or ""),
        "webvpn_cookie": str(data.get("webvpn_cookie") or ""),
        "jwxt_base_url": jwxt_base,
        "jwxt_login_path": str(data.get("jwxt_login_path") or "/xtgl/login_slogin.html").strip(),
        "schedule_path": str(data.get("schedule_path") or "/kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N253508").strip(),
        "grade_path": str(data.get("grade_path") or "/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005").strip(),
        "request_timeout": timeout,
        "verify_tls": _as_bool(data.get("verify_tls"), True),
        "store_user_credentials": _as_bool(data.get("store_user_credentials"), True),
        "allowed_hosts_text": allowed_hosts_text,
    }


_WEBVPN_CHALLENGE_TTL_SECONDS = 300


@dataclass(frozen=True)
class _WebVPNChallenge:
    client: Any
    session: requests.Session
    login_url: str
    token: str
    username: str
    password: str
    expires_at: float


_WEBVPN_CHALLENGES: Dict[str, _WebVPNChallenge] = {}
_WEBVPN_CHALLENGE_LOCK = threading.Lock()


def _cleanup_webvpn_challenges(now: float) -> None:
    expired_ids = [
        challenge_id
        for challenge_id, challenge in _WEBVPN_CHALLENGES.items()
        if challenge.expires_at <= now
    ]
    for challenge_id in expired_ids:
        _WEBVPN_CHALLENGES.pop(challenge_id, None)


def _store_webvpn_challenge(challenge: _WebVPNChallenge) -> str:
    challenge_id = secrets.token_urlsafe(24)
    now = time.time()
    with _WEBVPN_CHALLENGE_LOCK:
        _cleanup_webvpn_challenges(now)
        _WEBVPN_CHALLENGES[challenge_id] = challenge
    return challenge_id


def _pop_webvpn_challenge(challenge_id: str) -> _WebVPNChallenge:
    now = time.time()
    with _WEBVPN_CHALLENGE_LOCK:
        _cleanup_webvpn_challenges(now)
        challenge = _WEBVPN_CHALLENGES.pop(challenge_id, None)
    if not challenge:
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
    if not _as_bool(cfg.get("use_webvpn"), True):
        raise ValueError("当前未启用 WebVPN")
    if not str(cfg.get("webvpn_username") or "").strip() or not str(cfg.get("webvpn_password") or ""):
        raise ValueError("请先保存 WebVPN 账号和密码")


@admin_api_bp.route("/settings/edu-schedule", methods=["GET"])
@admin_required
def api_get_edu_schedule_config():
    return success_response(data=SystemConfigService.get_edu_schedule_config_masked())


@admin_api_bp.route("/settings/edu-schedule", methods=["POST"])
@admin_required
def api_save_edu_schedule_config():
    try:
        payload = _normalize_payload(request.get_json(silent=True) or {})
        data = SystemConfigService.save_edu_schedule_config(payload, admin_id=session.get("user_id"))
        return success_response(data=data, message="教务课表配置保存成功（约 15 秒内生效）")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("保存教务课表配置失败: %s", type(exc).__name__, exc_info=True)
        return error_response("保存失败，请稍后重试", status_code=500)


@admin_api_bp.route("/settings/edu-schedule/webvpn-session/start", methods=["POST"])
@admin_required
def api_start_webvpn_session_refresh():
    try:
        cfg = SystemConfigService.get_edu_schedule_config()
        _require_webvpn_refresh_config(cfg)
        webvpn_client = JWXTClient(cfg)
        request_session = requests.Session()
        request_session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; TiWebVPNRefresh/1.0)",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

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
            data = SystemConfigService.save_edu_schedule_webvpn_cookie(cookie_header, admin_id=session.get("user_id"))
            return success_response(data=data, message="WebVPN 登录态已刷新")

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
        challenge = _WebVPNChallenge(
            client=webvpn_client,
            session=request_session,
            login_url=login_url,
            token=token,
            username=str(cfg.get("webvpn_username") or "").strip(),
            password=str(cfg.get("webvpn_password") or ""),
            expires_at=time.time() + _WEBVPN_CHALLENGE_TTL_SECONDS,
        )
        challenge_id = _store_webvpn_challenge(challenge)
        return success_response(
            data={
                "challenge_id": challenge_id,
                "captcha_image": _captcha_data_url(captcha_response),
                "expires_in_seconds": _WEBVPN_CHALLENGE_TTL_SECONDS,
            },
            message="请输入 WebVPN 验证码",
        )
    except (ValueError, ScheduleAuthError, ScheduleClientError) as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("刷新 WebVPN 登录态初始化失败: %s", type(exc).__name__, exc_info=True)
        return error_response("刷新 WebVPN 登录态失败，请稍后重试", status_code=500)


@admin_api_bp.route("/settings/edu-schedule/webvpn-session/complete", methods=["POST"])
@admin_required
def api_complete_webvpn_session_refresh():
    try:
        payload = request.get_json(silent=True) or {}
        challenge_id = str(payload.get("challenge_id") or "").strip()
        captcha_code = str(payload.get("captcha_code") or "").strip()
        if not challenge_id:
            raise ValueError("缺少验证码会话")
        if not re.fullmatch(r"[A-Za-z0-9]{1,10}", captcha_code):
            raise ValueError("验证码格式不正确")

        challenge = _pop_webvpn_challenge(challenge_id)
        form_data = {
            "utf8": "✓",
            "authenticity_token": challenge.token,
            "user[login]": challenge.username,
            "user[password]": challenge.password,
            "user[dymatice_code]": "unknown",
            "user[otp_with_capcha]": "false",
            "_rucaptcha": captcha_code,
            "commit": "登录 Login",
        }
        result = challenge.client._request(
            challenge.session,
            "POST",
            challenge.login_url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": _origin_from_url(challenge.login_url),
                "Referer": challenge.login_url,
            },
            data=form_data,
            allow_redirects=True,
        )
        if _looks_webvpn_logged_in(result.text):
            cookie_header = _session_cookie_header(challenge.session)
            if not cookie_header:
                raise ValueError("登录成功但未获取到 WebVPN Cookie")
            data = SystemConfigService.save_edu_schedule_webvpn_cookie(cookie_header, admin_id=session.get("user_id"))
            return success_response(data=data, message="WebVPN 登录态已刷新")
        if _requires_webvpn_interactive_challenge(result.text):
            raise ValueError("验证码错误或已过期，请重新刷新验证码")
        raise ValueError("WebVPN 登录失败，请检查账号密码或验证码")
    except (ValueError, ScheduleAuthError, ScheduleClientError) as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("提交 WebVPN 验证码失败: %s", type(exc).__name__, exc_info=True)
        return error_response("提交 WebVPN 验证码失败，请稍后重试", status_code=500)
