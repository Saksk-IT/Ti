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
