# -*- coding: utf-8 -*-
"""教务服务的公共错误与展示辅助。"""

from __future__ import annotations

from .client import (
    ScheduleAuthError,
    ScheduleClientError,
    WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE,
)


class EduScheduleError(RuntimeError):
    """教务业务错误。"""


def mask_account(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 4:
        return "***"
    return f"{text[:4]}****{text[-4:]}"


def user_safe_error(exc: Exception) -> str:
    if isinstance(exc, ScheduleAuthError):
        auth_message = str(exc).strip()
        if auth_message == WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE:
            return WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE
        if auth_message == "教务系统账号或密码错误":
            return "教务系统账号或密码错误，请检查绑定信息后重试"
        if auth_message == "WebVPN 登录态不可用":
            return "WebVPN 登录态不可用，请联系管理员在后台刷新 WebVPN 登录态"
        if auth_message == "WebVPN 未配置可用登录态":
            return "WebVPN 未配置可用登录态，请在后台配置有效 Cookie 或登录信息"
        return "上游登录失败，请检查授权信息后重试"
    if isinstance(exc, ScheduleClientError):
        return "教务查询失败，请稍后重试"
    if isinstance(exc, EduScheduleError):
        return str(exc)
    return "教务查询失败，请稍后重试"
