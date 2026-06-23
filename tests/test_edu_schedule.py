# -*- coding: utf-8 -*-
"""教务课表查询功能测试。"""

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
