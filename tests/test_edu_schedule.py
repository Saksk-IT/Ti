# -*- coding: utf-8 -*-
"""教务课表查询功能测试。"""

import json
from pathlib import Path

from sqlalchemy import text


def _sample_schedule_payload(xnm="2025", xqm="12"):
    return {
        "xsxx": {
            "XM": "王为硕",
            "BJMC": "计算机科学与技术23-5班",
            "XNMC": "2025-2026",
            "XNM": xnm,
            "XQM": xqm,
            "XQMMC": "2",
        },
        "kbList": [
            {
                "xqj": "1",
                "xqjmc": "星期一",
                "jc": "1-2节",
                "jcor": "1-2",
                "kcmc": "WEB程序设计",
                "xm": "尹伟静",
                "zcd": "1-15周",
                "lh": "软件楼",
                "cdmc": "软件122",
                "xf": "3.0",
                "khfsmc": "考试",
            },
            {
                "xqj": "2",
                "xqjmc": "星期二",
                "jc": "5-8节",
                "jcor": "5-8",
                "kcmc": "大数据技术原理与应用",
                "xm": "刘燚",
                "zcd": "14周",
                "lh": "软件楼",
                "cdmc": "软件121（合）",
                "xf": "2.5",
                "khfsmc": "考查",
            },
        ],
        "sjkList": [
            {
                "kcmc": "专业技术综合实践",
                "jsxm": "刘会燕",
                "qsjsz": "16-18周",
                "xf": "2.0",
                "khfsmc": "考试",
                "xqmc": "主校区",
            }
        ],
    }


def _sample_grade_payload(xnm="2025", xqm="3"):
    return {
        "items": [
            {
                "row_id": "1",
                "xm": "测试学生",
                "xh": "stu_demo_2026",
                "bj": "软件工程26-1班",
                "zymc": "软件工程",
                "jgmc": "信息学院",
                "xnm": xnm,
                "xnmmc": f"{xnm}-{int(xnm) + 1}",
                "xqm": xqm,
                "xqmmc": "1" if xqm == "3" else "2",
                "kch": "CS1001",
                "kcmc": "数据结构",
                "kcxzmc": "专业必修",
                "kcbj": "主修",
                "jsxm": "任课教师A",
                "xf": "4.0",
                "zxs": "64",
                "cj": "92",
                "bfzcj": "92",
                "jd": "4.00",
                "xfjd": "16.00",
                "khfsmc": "考试",
                "ksxz": "正常考试",
                "kkbmmc": "信息学院",
            },
            {
                "row_id": "2",
                "xm": "测试学生",
                "xh": "stu_demo_2026",
                "bj": "软件工程26-1班",
                "zymc": "软件工程",
                "jgmc": "信息学院",
                "xnm": xnm,
                "xnmmc": f"{xnm}-{int(xnm) + 1}",
                "xqm": xqm,
                "xqmmc": "1" if xqm == "3" else "2",
                "kch": "CS1002",
                "kcmc": "创新实践",
                "kcxzmc": "通识选修",
                "kcbj": "主修",
                "jsxm": "任课教师B",
                "xf": "2.0",
                "zxs": "32",
                "cj": "良好",
                "bfzcj": "85",
                "jd": "3.00",
                "xfjd": "6.00",
                "khfsmc": "考查",
                "ksxz": "正常考试",
                "kkbmmc": "创新学院",
            },
        ],
        "totalResult": 2,
    }


def _admin_client(app, seed_user):
    c = app.test_client()
    with app.app_context():
        from app.core.extensions import db

        row = db.session.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": "edu_schedule_admin"},
        ).fetchone()
        if row is None:
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:u, :p, 1, 1)"
                ),
                {"u": "edu_schedule_admin", "p": "test"},
            )
            db.session.commit()
            row = db.session.execute(
                text("SELECT id FROM users WHERE username = :u"),
                {"u": "edu_schedule_admin"},
            ).fetchone()
        admin_id = int(row[0])
        db.session.execute(
            text("UPDATE users SET is_admin = 1 WHERE id = :uid"),
            {"uid": admin_id},
        )
        db.session.commit()
    with c.session_transaction() as sess:
        sess["user_id"] = admin_id
        sess["username"] = "edu_schedule_admin"
        sess["is_admin"] = True
        sess["session_version"] = 0
    return c


def test_schedule_payload_normalizes_week_table():
    from app.modules.edu_schedule.services.parser import normalize_schedule_payload

    data = normalize_schedule_payload(_sample_schedule_payload())

    assert data["student"]["name"] == "王为硕"
    assert data["term"]["xnm"] == "2025"
    assert data["week_table"]["星期一"]["1-2节"][0]["course_name"] == "WEB程序设计"
    assert data["week_table"]["星期二"]["5-8节"][0]["weeks"] == "14周"
    assert data["practice_courses"][0]["course_name"] == "专业技术综合实践"


def test_grade_payload_normalizes_summary():
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload

    data = normalize_grade_payload(_sample_grade_payload())

    assert data["student"]["name"] == "测试学生"
    assert data["term"]["xnm"] == "2025"
    assert data["term"]["label"] == "2025-2026 第1学期"
    assert data["grades"][0]["course_name"] == "数据结构"
    assert data["grades"][0]["score"] == "92"
    assert data["grades"][1]["grade_point"] == "3.00"
    assert data["summary"]["course_count"] == 2
    assert data["summary"]["total_credits"] == 6.0
    assert data["summary"]["gpa"] == 3.67


def test_grade_query_falls_back_when_primary_endpoint_returns_html():
    from app.modules.edu_schedule.services.client import JWXTClient

    class FakeResponse:
        def __init__(self, payload=None, json_error=False):
            self.payload = payload
            self.json_error = json_error

        def json(self):
            if self.json_error:
                raise json.JSONDecodeError("Expecting value", "<html>", 0)
            return self.payload

    client = JWXTClient(
        {
            "enabled": True,
            "use_webvpn": False,
            "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
            "grade_path": "/cjcx/cjcx_cxXsgrcj.html?doType=query&gnmkdm=N305005",
            "request_timeout": 20,
            "verify_tls": True,
            "allowed_hosts": ("jwxt.webvpn.synu.edu.cn",),
        }
    )
    called_urls = []

    def fake_request(session, method, url, **kwargs):
        called_urls.append(url)
        if "cjcx_cxXsgrcj" in url:
            return FakeResponse(json_error=True)
        return FakeResponse({"items": [], "totalResult": 0})

    client._request = fake_request

    payload = client._query_grades(object(), "2025", "3")

    assert payload["items"] == []
    assert "cjcx_cxXsgrcj" in called_urls[0]
    assert "cjcx_cxDgXscj" in called_urls[1]


def test_grade_query_uses_browser_form_encoding_for_empty_sort_name():
    from app.modules.edu_schedule.services.client import JWXTClient

    class FakeResponse:
        def json(self):
            return {"items": [], "totalResult": 0}

    client = JWXTClient(
        {
            "enabled": True,
            "use_webvpn": False,
            "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
            "grade_path": "/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005",
            "request_timeout": 20,
            "verify_tls": True,
            "allowed_hosts": ("jwxt.webvpn.synu.edu.cn",),
        }
    )
    calls = []

    def fake_request(session, method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse()

    client._request = fake_request

    client._query_grades(object(), "2025", "12")

    post_call = calls[0]
    assert post_call["data"]["queryModel.sortName"] == " "
    assert post_call["headers"]["Origin"] == "https://jwxt.webvpn.synu.edu.cn"
    assert post_call["headers"]["Referer"].endswith(
        "/jwglxt/cjcx/cjcx_cxDgXscj.html?gnmkdm=N305005&layout=default"
    )


def test_user_can_save_encrypted_jwxt_credentials(app, auth_client):
    response = auth_client.post(
        "/api/edu-schedule/credentials",
        json={
            "username": "stu_demo_2026",
            "password": "DemoSecret123!",
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["has_credentials"] is True
    assert body["data"]["username_hint"] == "stu_****2026"

    with app.app_context():
        row = app.extensions["sqlalchemy"].session.execute(
            text(
                "SELECT jwxt_username_ciphertext, jwxt_password_ciphertext "
                "FROM edu_schedule_credentials "
                "ORDER BY id DESC LIMIT 1"
            )
        ).fetchone()

    assert row is not None
    assert "stu_demo_2026" not in row[0]
    assert "DemoSecret123!" not in row[1]


def test_account_bindings_page_exposes_edu_credential_binding(auth_client):
    page = auth_client.get("/settings/account/bindings")

    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "教务系统" in html
    assert "eduBindForm" in html
    assert "/api/edu-schedule/credentials" in html
    assert "/api/edu-schedule/status" in html


def test_campus_pages_only_keep_term_filters_and_bind_prompt(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    schedule_html = schedule_page.get_data(as_text=True)
    grade_html = grades_page.get_data(as_text=True)

    assert "scheduleUsername" not in schedule_html
    assert "schedulePassword" not in schedule_html
    assert "scheduleRemember" not in schedule_html
    assert "scheduleClearCredential" not in schedule_html
    assert "未绑定教务系统账号" in schedule_html
    assert "/settings/account/bindings" in schedule_html

    assert "gradeUsername" not in grade_html
    assert "gradePassword" not in grade_html
    assert "gradeRemember" not in grade_html
    assert "gradeClearCredential" not in grade_html
    assert "未绑定教务系统账号" in grade_html
    assert "/settings/account/bindings" in grade_html


def test_campus_pages_expose_user_webvpn_captcha_refresh(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    for html in (schedule_page.get_data(as_text=True), grades_page.get_data(as_text=True)):
        assert "webvpnCaptchaDialog" in html
        assert "webvpnCaptchaImage" in html
        assert "submitWebvpnCaptcha" in html
        assert "WEBVPN_REFRESH_REQUIRED" in html
        assert "/api/edu-schedule/webvpn-session/complete" in html
        assert "submitQueryAfterWebvpnRefresh" in html


def test_campus_year_filters_use_academic_year_range_labels(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    schedule_html = schedule_page.get_data(as_text=True)
    grade_html = grades_page.get_data(as_text=True)
    for prefix, html in (("schedule", schedule_html), ("grade", grade_html)):
        assert f'<select id="{prefix}AcademicYear"' in html
        assert f'<input id="{prefix}StartYear"' not in html
        assert f'<input id="{prefix}EndYear"' not in html
        assert f'id="{prefix}StartYear"' not in html
        assert f'id="{prefix}EndYear"' not in html
        assert "开始学年" not in html
        assert "结束学年" not in html
        assert "2025~2026" in html

    campus_dir = Path("miniprogram-1/miniprogram/pages/campus")
    wxml = (campus_dir / "campus.wxml").read_text(encoding="utf-8")
    ts = (campus_dir / "campus.ts").read_text(encoding="utf-8")

    assert wxml.count('range="{{academicYearLabels}}"') == 1
    assert 'range="{{academicYearLabels}}"' in wxml
    assert "onAcademicYearChange" in wxml
    assert "onStartYearChange" not in wxml
    assert "onEndYearChange" not in wxml
    assert "onStartYearInput" not in wxml
    assert "onEndYearInput" not in wxml
    assert "开始学年" not in wxml
    assert "结束学年" not in wxml
    assert "academicYearIndex" in ts
    assert "academicYear:" in ts
    assert "startYearIndex" not in ts
    assert "endYearIndex" not in ts
    assert "formatAcademicYearLabel" in ts
    assert "~" in ts


def test_miniprogram_account_bindings_page_exposes_edu_credential_binding():
    page_dir = Path("miniprogram-1/miniprogram/pages/settings-account-bindings-v2")
    wxml = (page_dir / "settings-account-bindings-v2.wxml").read_text(encoding="utf-8")
    ts = (page_dir / "settings-account-bindings-v2.ts").read_text(encoding="utf-8")
    api = Path("miniprogram-1/miniprogram/utils/api-endpoints.ts").read_text(encoding="utf-8")

    assert "教务系统" in wxml
    assert "bindEduUsername" in wxml
    assert "onEduActionTap" in wxml
    assert "loadEduCredentialStatus" in ts
    assert "saveEduCredentials" in api
    assert "getEduScheduleStatus" in api


def test_miniprogram_campus_tab_exposes_schedule_and_grade_queries():
    app_config = json.loads(Path("miniprogram-1/miniprogram/app.json").read_text(encoding="utf-8"))
    campus_dir = Path("miniprogram-1/miniprogram/pages/campus")
    wxml = (campus_dir / "campus.wxml").read_text(encoding="utf-8")
    ts = (campus_dir / "campus.ts").read_text(encoding="utf-8")
    api = Path("miniprogram-1/miniprogram/utils/api-endpoints.ts").read_text(encoding="utf-8")

    assert "pages/campus/campus" in app_config["pages"]
    campus_tab = next(
        item for item in app_config["tabBar"]["list"]
        if item["pagePath"] == "pages/campus/campus"
    )
    assert campus_tab["text"] == "校园"
    assert campus_tab["iconPath"] == "images/tabbar/campus.png"
    assert campus_tab["selectedIconPath"] == "images/tabbar/campus-active.png"
    assert Path("miniprogram-1/miniprogram/images/tabbar/campus.png").exists()
    assert Path("miniprogram-1/miniprogram/images/tabbar/campus-active.png").exists()
    assert Path("miniprogram-1/miniprogram/images/icons/campus.svg").exists()

    assert "查询课表" in wxml
    assert "查询成绩" in wxml
    assert "教务系统账号" in wxml
    assert "/images/icons/campus.svg" in wxml
    assert "mode-icon-wrap" in wxml
    assert "query-icon" in wxml
    assert "onGoEduBindingTap" in wxml
    assert "statusReady && !statusFailed && !eduBound" in wxml
    assert "onHeroActionTap" in wxml
    assert "api.queryEduSchedule" in ts
    assert "api.queryEduGrades" in ts
    assert "campusFriendlyError" in ts
    assert "statusLoading || !this.data.statusReady" in ts
    assert "this.data.statusFailed" in ts
    assert "queryEduSchedule" in api
    assert "request('/edu-schedule/query'" in api
    assert "queryEduGrades" in api
    assert "request('/edu-schedule/grades/query'" in api


def test_admin_can_save_webvpn_schedule_config_masked(app, seed_user):
    client = _admin_client(app, seed_user)

    response = client.post(
        "/admin/api/settings/edu-schedule",
        json={
            "enabled": True,
            "use_webvpn": True,
            "webvpn_base_url": "https://webvpn.synu.edu.cn",
            "webvpn_username": "vpn-admin",
            "webvpn_password": "VpnSecret123!",
            "webvpn_cookie": "JSESSIONID=abc; route=def",
            "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
            "request_timeout": 20,
            "verify_tls": True,
            "store_user_credentials": True,
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["webvpn_password"] == "Vpn****23!"
    assert body["data"]["webvpn_cookie"] == "JSE****def"

    page = client.get("/admin/settings/edu-schedule")
    assert page.status_code == 200
    assert b"VpnSecret123!" not in page.data
    assert b"JSESSIONID=abc" not in page.data


def test_admin_can_refresh_webvpn_cookie_with_manual_captcha(app, seed_user, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import webvpn_refresh

    client = _admin_client(app, seed_user)

    class FakeResponse:
        def __init__(self, *, text="", content=b"", content_type="text/html", url="https://webvpn.synu.edu.cn/users/sign_in"):
            self.text = text
            self.content = content
            self.headers = {"Content-Type": content_type}
            self.url = url

    class FakeClient:
        def __init__(self, config):
            self.config = config

        def _request(self, session, method, url, **kwargs):
            if method == "GET" and url.endswith("/users/sign_in"):
                assert kwargs["headers"]["Accept"].startswith("text/html")
                return FakeResponse(
                    text="""
                    <form id="login-form">
                      <input name="authenticity_token" value="token-123">
                      <input name="_rucaptcha">
                    </form>
                    """
                )
            if method == "GET" and url.endswith("/rucaptcha/"):
                assert kwargs["headers"]["Referer"].endswith("/users/sign_in")
                assert kwargs["headers"]["Accept"].startswith("image/")
                return FakeResponse(content=b"captcha-png", content_type="image/png")
            if method == "POST" and url.endswith("/users/sign_in"):
                assert kwargs["headers"]["Origin"] == "https://webvpn.synu.edu.cn"
                assert kwargs["headers"]["Referer"].endswith("/users/sign_in")
                assert kwargs["data"]["authenticity_token"] == "token-123"
                assert kwargs["data"]["_rucaptcha"] == "vxpj"
                assert kwargs["data"]["user[login]"] == "vpn-admin"
                assert kwargs["data"]["user[password]"] == "VpnSecret123!"
                session.cookies.set("SERVERID", "Server1", domain="webvpn.synu.edu.cn", path="/")
                session.cookies.set("_astraeus_session", "logged-session", domain="webvpn.synu.edu.cn", path="/")
                session.cookies.set("_webvpn_key", "webvpn-key-value", domain=".synu.edu.cn", path="/")
                return FakeResponse(
                    text='<body class="vpn"><a href="/users/sign_out">退出登录</a></body>',
                    url="https://webvpn.synu.edu.cn/",
                )
            raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr(webvpn_refresh, "JWXTClient", FakeClient)

    with app.app_context():
        SystemConfigService.save_edu_schedule_config(
            {
                "enabled": True,
                "use_webvpn": True,
                "webvpn_base_url": "https://webvpn.synu.edu.cn",
                "webvpn_login_path": "/users/sign_in",
                "webvpn_username": "vpn-admin",
                "webvpn_password": "VpnSecret123!",
                "webvpn_cookie": "",
                "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
                "request_timeout": 20,
                "verify_tls": True,
                "store_user_credentials": True,
            },
            admin_id=1,
        )

    start_response = client.post(
        "/admin/api/settings/edu-schedule/webvpn-session/start",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert start_response.status_code == 200
    start_body = start_response.get_json()
    assert start_body["status"] == "success"
    assert start_body["data"]["challenge_id"]
    assert start_body["data"]["captcha_image"].startswith("data:image/png;base64,")

    submit_response = client.post(
        "/admin/api/settings/edu-schedule/webvpn-session/complete",
        json={
            "challenge_id": start_body["data"]["challenge_id"],
            "captcha_code": "vxpj",
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert submit_response.status_code == 200
    submit_body = submit_response.get_json()
    assert submit_body["status"] == "success"
    assert submit_body["data"]["webvpn_cookie"].startswith("SER")
    assert "logged-session" not in submit_body["data"]["webvpn_cookie"]

    with app.app_context():
        saved = SystemConfigService.get_edu_schedule_config()["webvpn_cookie"]
    assert "SERVERID=Server1" in saved
    assert "_astraeus_session=logged-session" in saved
    assert "_webvpn_key=webvpn-key-value" in saved


def test_user_query_returns_webvpn_refresh_challenge_when_cookie_expired(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.routes import api as edu_schedule_api
    from app.modules.edu_schedule.services import schedule_service
    from app.modules.edu_schedule.services.client import ScheduleAuthError

    class ExpiredCookieClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            raise ScheduleAuthError("WebVPN 登录态不可用")

    class FakeRefreshService:
        @staticmethod
        def start(owner_user_id=None):
            assert owner_user_id
            return {
                "challenge_id": "challenge-user-1",
                "captcha_image": "data:image/png;base64,Y2FwdGNoYQ==",
                "expires_in_seconds": 300,
            }

    monkeypatch.setattr(schedule_service, "JWXTClient", ExpiredCookieClient)
    monkeypatch.setattr(edu_schedule_api, "WebVPNSessionRefreshService", FakeRefreshService)

    with app.app_context():
        SystemConfigService.save_edu_schedule_config(
            {
                "enabled": True,
                "use_webvpn": True,
                "webvpn_base_url": "https://webvpn.synu.edu.cn",
                "webvpn_login_path": "/users/sign_in",
                "webvpn_username": "vpn-admin",
                "webvpn_password": "VpnSecret123!",
                "webvpn_cookie": "SERVERID=expired",
                "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
                "request_timeout": 20,
                "verify_tls": True,
                "store_user_credentials": True,
            },
            admin_id=1,
        )

    auth_client.post(
        "/api/edu-schedule/credentials",
        json={"username": "stu_demo_2026", "password": "DemoSecret123!"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    response = auth_client.post(
        "/api/edu-schedule/query",
        json={"terms": [{"xnm": "2025", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 409
    body = response.get_json()
    assert body["status"] == "error"
    assert body["error_code"] == "WEBVPN_REFRESH_REQUIRED"
    assert body["data"]["challenge_id"] == "challenge-user-1"
    assert body["data"]["captcha_image"].startswith("data:image/png;base64,")


def test_user_can_complete_webvpn_refresh_challenge(app, auth_client, monkeypatch):
    from app.modules.edu_schedule.routes import api as edu_schedule_api

    captured = {}

    class FakeRefreshService:
        @staticmethod
        def complete(challenge_id, captcha_code, owner_user_id=None):
            captured["challenge_id"] = challenge_id
            captured["captcha_code"] = captcha_code
            captured["owner_user_id"] = owner_user_id
            return {"webvpn_cookie": "SER****key"}

    monkeypatch.setattr(edu_schedule_api, "WebVPNSessionRefreshService", FakeRefreshService)

    response = auth_client.post(
        "/api/edu-schedule/webvpn-session/complete",
        json={"challenge_id": "challenge-user-1", "captcha_code": "vxpj"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["webvpn_cookie"] == "SER****key"
    assert captured["challenge_id"] == "challenge-user-1"
    assert captured["captcha_code"] == "vxpj"
    assert captured["owner_user_id"]


def test_webvpn_refresh_service_uses_temp_cookie_and_saves_refreshed_cookie(app, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import webvpn_refresh

    class FakeResponse:
        def __init__(self, *, text="", content=b"", content_type="text/html", url="https://webvpn.synu.edu.cn/users/sign_in"):
            self.text = text
            self.content = content
            self.headers = {"Content-Type": content_type}
            self.url = url

    class FakeClient:
        def __init__(self, config):
            self.config = config

        def _request(self, session, method, url, **kwargs):
            if method == "GET" and url.endswith("/users/sign_in"):
                session.cookies.set("SERVERID", "Server1", domain="webvpn.synu.edu.cn", path="/")
                session.cookies.set("_astraeus_session", "temporary-session", domain="webvpn.synu.edu.cn", path="/")
                return FakeResponse(
                    text='<input name="authenticity_token" value="token-456"><input name="_rucaptcha">'
                )
            if method == "GET" and url.endswith("/rucaptcha/"):
                assert "SERVERID=Server1" in webvpn_refresh._session_cookie_header(session)
                return FakeResponse(content=b"captcha-png", content_type="image/png")
            if method == "POST" and url.endswith("/users/sign_in"):
                assert "SERVERID=Server1" in webvpn_refresh._session_cookie_header(session)
                assert "_astraeus_session=temporary-session" in webvpn_refresh._session_cookie_header(session)
                assert kwargs["data"]["authenticity_token"] == "token-456"
                assert kwargs["data"]["_rucaptcha"] == "vxpj"
                session.cookies.set("_astraeus_session", "refreshed-session", domain="webvpn.synu.edu.cn", path="/")
                session.cookies.set("_webvpn_key", "refreshed-key", domain=".synu.edu.cn", path="/")
                return FakeResponse(
                    text='<body class="vpn"><a href="/users/sign_out">退出登录</a></body>',
                    url="https://webvpn.synu.edu.cn/",
                )
            raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr(webvpn_refresh, "JWXTClient", FakeClient)

    with app.app_context():
        SystemConfigService.save_edu_schedule_config(
            {
                "enabled": True,
                "use_webvpn": True,
                "webvpn_base_url": "https://webvpn.synu.edu.cn",
                "webvpn_login_path": "/users/sign_in",
                "webvpn_username": "vpn-admin",
                "webvpn_password": "VpnSecret123!",
                "webvpn_cookie": "SERVERID=expired",
                "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
                "request_timeout": 20,
                "verify_tls": True,
                "store_user_credentials": True,
            },
            admin_id=1,
        )

        challenge = webvpn_refresh.WebVPNSessionRefreshService.start(owner_user_id=42)
        assert challenge["captcha_image"].startswith("data:image/png;base64,")

        result = webvpn_refresh.WebVPNSessionRefreshService.complete(
            challenge["challenge_id"],
            "vxpj",
            owner_user_id=42,
        )

        assert result["webvpn_cookie"].startswith("SER")
        saved = SystemConfigService.get_edu_schedule_config()["webvpn_cookie"]
        assert "SERVERID=Server1" in saved
        assert "_astraeus_session=refreshed-session" in saved
        assert "_webvpn_key=refreshed-key" in saved


def test_admin_edu_schedule_page_exposes_webvpn_refresh_controls(app, seed_user):
    client = _admin_client(app, seed_user)

    page = client.get("/admin/settings/edu-schedule")

    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "刷新 WebVPN 登录态" in html
    assert "webvpnCaptchaImage" in html
    assert "/admin/api/settings/edu-schedule/webvpn-session/start" in html
    assert "/admin/api/settings/edu-schedule/webvpn-session/complete" in html


def test_query_multiple_terms_saves_schedule_snapshots(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import schedule_service

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            assert username == "stu_demo_2026"
            assert password == "DemoSecret123!"
            return _sample_schedule_payload(xnm=xnm, xqm=xqm)

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)

    with app.app_context():
        SystemConfigService.save_edu_schedule_config(
            {
                "enabled": True,
                "use_webvpn": False,
                "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
                "request_timeout": 20,
                "verify_tls": True,
                "store_user_credentials": True,
            },
            admin_id=1,
        )

    auth_client.post(
        "/api/edu-schedule/credentials",
        json={"username": "stu_demo_2026", "password": "DemoSecret123!"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    response = auth_client.post(
        "/api/edu-schedule/query",
        json={
            "terms": [
                {"xnm": "2024", "xqm": "3"},
                {"xnm": "2025", "xqm": "12"},
            ]
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert [item["term"]["xnm"] for item in body["data"]["results"]] == ["2024", "2025"]
    assert body["data"]["results"][1]["week_table"]["星期一"]["1-2节"][0]["course_name"] == "WEB程序设计"

    with app.app_context():
        count = app.extensions["sqlalchemy"].session.execute(
            text("SELECT COUNT(1) FROM edu_schedule_snapshots WHERE user_id IS NOT NULL")
        ).scalar()
    assert count >= 2


def test_query_multiple_terms_saves_grade_snapshots(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import schedule_service

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_grades(self, username, password, xnm, xqm):
            assert username == "stu_demo_2026"
            assert password == "DemoSecret123!"
            return _sample_grade_payload(xnm=xnm, xqm=xqm)

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)

    with app.app_context():
        SystemConfigService.save_edu_schedule_config(
            {
                "enabled": True,
                "use_webvpn": False,
                "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
                "request_timeout": 20,
                "verify_tls": True,
                "store_user_credentials": True,
            },
            admin_id=1,
        )

    auth_client.post(
        "/api/edu-schedule/credentials",
        json={"username": "stu_demo_2026", "password": "DemoSecret123!"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    response = auth_client.post(
        "/api/edu-schedule/grades/query",
        json={
            "terms": [
                {"xnm": "2024", "xqm": "3"},
                {"xnm": "2025", "xqm": "12"},
            ]
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert [item["term"]["xnm"] for item in body["data"]["results"]] == ["2024", "2025"]
    assert body["data"]["results"][0]["grades"][0]["course_name"] == "数据结构"
    assert body["data"]["results"][1]["summary"]["course_count"] == 2

    with app.app_context():
        count = app.extensions["sqlalchemy"].session.execute(
            text("SELECT COUNT(1) FROM edu_grade_snapshots WHERE user_id IS NOT NULL")
        ).scalar()
    assert count >= 2


def test_query_rejects_partial_inline_credentials(auth_client):
    response = auth_client.post(
        "/api/edu-schedule/query",
        json={
            "username": "stu_demo_2026",
            "terms": [{"xnm": "2025", "xqm": "12"}],
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "输入参数不正确"


def test_webvpn_cookie_table_normalizes_to_header():
    from app.modules.edu_schedule.services.client import _normalize_cookie_header

    cookie_table = "\n".join(
        [
            "_astraeus_session\tabc%3D%3D--sig\twebvpn.synu.edu.cn\t/\t会话",
            "_webvpn_key\tjwt.token.value\t.synu.edu.cn\t/\t会话",
            "SERVERID\tServer1\twebvpn.synu.edu.cn\t/\t会话",
            "webvpn_username\tuser%7Ctime%7Csig\t.synu.edu.cn\t/\t会话",
        ]
    )

    assert _normalize_cookie_header(cookie_table) == (
        "_astraeus_session=abc%3D%3D--sig; "
        "_webvpn_key=jwt.token.value; "
        "SERVERID=Server1; "
        "webvpn_username=user%7Ctime%7Csig"
    )
    assert _normalize_cookie_header("SERVERID=Server1; route=webvpn") == "SERVERID=Server1; route=webvpn"


def test_schedule_api_routes_do_not_have_rate_limits():
    route_source = Path("app/modules/edu_schedule/routes/api.py").read_text(encoding="utf-8")

    assert "per hour" not in route_source
    assert "limiter.limit" not in route_source
