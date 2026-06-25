# -*- coding: utf-8 -*-
"""Admin API routes - edu schedule settings."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

from flask import current_app, request, session

from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import admin_required
from app.modules.admin.services.system_config_service import SystemConfigService
from app.modules.edu_schedule.services.client import ScheduleAuthError, ScheduleClientError
from app.modules.edu_schedule.services.webvpn_refresh import WebVPNSessionRefreshService

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
        "grade_path": str(data.get("grade_path") or "/cjcx/cjcx_cxXsgrcj.html?doType=query&gnmkdm=N305005").strip(),
        "request_timeout": timeout,
        "verify_tls": _as_bool(data.get("verify_tls"), True),
        "store_user_credentials": _as_bool(data.get("store_user_credentials"), True),
        "allowed_hosts_text": allowed_hosts_text,
    }


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
        data = WebVPNSessionRefreshService.start(admin_id=session.get("user_id"))
        message = "WebVPN 登录态已刷新" if data.get("refreshed") else "请输入 WebVPN 验证码"
        return success_response(data=data, message=message)
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
        data = WebVPNSessionRefreshService.complete(
            str(payload.get("challenge_id") or ""),
            str(payload.get("captcha_code") or ""),
            admin_id=session.get("user_id"),
        )
        return success_response(data=data, message="WebVPN 登录态已刷新")
    except (ValueError, ScheduleAuthError, ScheduleClientError) as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("提交 WebVPN 验证码失败: %s", type(exc).__name__, exc_info=True)
        return error_response("提交 WebVPN 验证码失败，请稍后重试", status_code=500)
