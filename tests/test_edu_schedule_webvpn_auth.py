# -*- coding: utf-8 -*-
"""WebVPN authentication edge-case tests."""

import pytest

from app.modules.edu_schedule.routes import api as edu_schedule_api
from app.modules.edu_schedule.services.client import JWXTClient, ScheduleAuthError
from app.modules.edu_schedule.services import query_tasks
from app.modules.edu_schedule.services.schedule_service import user_safe_error


def _webvpn_config():
    return {
        "enabled": True,
        "use_webvpn": True,
        "webvpn_base_url": "https://webvpn.synu.edu.cn",
        "webvpn_login_path": "/users/sign_in",
        "webvpn_username": "vpn-admin",
        "webvpn_password": "placeholder-password",
        "webvpn_cookie": "",
        "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
        "jwxt_login_path": "/xtgl/login_slogin.html",
        "schedule_path": "/kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N253508",
        "grade_path": "/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005",
        "request_timeout": 20,
        "verify_tls": True,
        "allowed_hosts": ("webvpn.synu.edu.cn", "jwxt.webvpn.synu.edu.cn"),
    }


class _Response:
    def __init__(self, text, url="https://webvpn.synu.edu.cn/users/sign_in"):
        self.text = text
        self.url = url


class _CaptchaWebVPNClient(JWXTClient):
    def __init__(self):
        super().__init__(_webvpn_config())
        self.methods = []

    def _request(self, session, method, url, **kwargs):
        self.methods.append(method)
        return _Response(
            """
            <form id="login-form">
              <input name="authenticity_token" value="token">
              <input name="user[login]">
              <input name="user[password]" type="password">
              <input name="_rucaptcha" placeholder="请输入验证码">
              <input name="user[otp_with_capcha]" value="false">
            </form>
            """
        )


class _LoggedInWebVPNClient(JWXTClient):
    def __init__(self):
        super().__init__(_webvpn_config())
        self.methods = []

    def _request(self, session, method, url, **kwargs):
        self.methods.append(method)
        return _Response(
            """
            <body class="vpn">
              <a rel="nofollow" data-method="delete" href="/users/sign_out">退出登录</a>
              <a href="https://jwxt.webvpn.synu.edu.cn:443/jwglxt">教务管理系统一</a>
            </body>
            """,
            url="https://webvpn.synu.edu.cn/",
        )


def test_webvpn_captcha_page_stops_before_password_post():
    client = _CaptchaWebVPNClient()

    with pytest.raises(ScheduleAuthError) as exc_info:
        client._prepare_webvpn(object())

    assert "仅凭账号密码自动登录" in str(exc_info.value)
    assert client.methods == ["GET"]


def test_webvpn_logged_in_home_page_is_accepted_without_password_post():
    client = _LoggedInWebVPNClient()

    client._prepare_webvpn(object())

    assert client.methods == ["GET"]


def test_grade_query_returns_actionable_webvpn_challenge_message(auth_client, monkeypatch):
    challenge_message = "WebVPN 登录需要验证码或二次验证，无法仅凭账号密码自动登录"

    def raise_challenge(*args, **kwargs):
        raise ScheduleAuthError(challenge_message)

    monkeypatch.setattr(edu_schedule_api.EduScheduleService, "query_grade_terms", raise_challenge)
    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

    response = auth_client.post(
        "/api/edu-schedule/grades/query",
        json={
            "terms": [{"xnm": "2025", "xqm": "3"}],
            "username": "stu_demo_2026",
            "password": "DemoSecret123!",
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"

    final_state = query_tasks.EduScheduleQueryTaskService.run_task(body["data"]["task"]["task_id"])

    assert final_state["status"] == "failed"
    assert final_state["message"] == challenge_message


def test_user_safe_error_tells_admin_to_refresh_expired_webvpn_cookie():
    message = user_safe_error(ScheduleAuthError("WebVPN 登录态不可用"))

    assert message == "WebVPN 登录态不可用，请联系管理员在后台刷新 WebVPN 登录态"
