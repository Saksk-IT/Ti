# -*- coding: utf-8 -*-
"""教务课表查询功能测试。"""

import json
import threading
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text


def _sample_schedule_payload(xnm="2025", xqm="12"):
    return {
        "xsxx": {
            "XM": "王为硕",
            "XH": "stu_demo_2026",
            "BJMC": "计算机科学与技术23-5班",
            "ZYMC": "计算机科学与技术",
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


def _sample_all_grade_payload():
    first_term = _sample_grade_payload(xnm="2024", xqm="12")["items"]
    second_term = _sample_grade_payload(xnm="2025", xqm="3")["items"]
    return {"items": [*first_term, *second_term], "totalResult": 4}


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


def test_grade_payload_splits_all_grades_by_returned_term():
    from app.modules.edu_schedule.services.grade_parser import split_grade_payload_by_term

    payloads = split_grade_payload_by_term(_sample_all_grade_payload())

    assert len(payloads) == 2
    assert [(item["items"][0]["xnm"], item["items"][0]["xqm"]) for item in payloads] == [
        ("2024", "12"),
        ("2025", "3"),
    ]
    assert [item["totalResult"] for item in payloads] == [2, 2]


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
    assert post_call["data"]["queryModel.showCount"] == "1000"
    assert post_call["data"]["time"] == "8"
    assert post_call["headers"]["Origin"] == "https://jwxt.webvpn.synu.edu.cn"
    assert post_call["headers"]["Referer"].endswith(
        "/jwglxt/cjcx/cjcx_cxDgXscj.html?gnmkdm=N305005&layout=default"
    )


def test_grade_query_can_request_all_grades_without_term_filters():
    from app.modules.edu_schedule.services.client import JWXTClient

    class FakeResponse:
        def json(self):
            return {"items": [], "totalResult": 0}

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
    calls = []

    def fake_request(session, method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse()

    client._request = fake_request

    client._query_grades(object(), "", "")

    post_call = calls[0]
    assert "cjcx_cxXsgrcj" in post_call["url"]
    assert post_call["data"]["xnm"] == ""
    assert post_call["data"]["xqm"] == ""
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
        assert "/api/edu-schedule/query-tasks/" in html
        assert "pollEduQueryTask" in html
        assert "教务系统繁忙" in html


def test_campus_pages_expose_persistent_query_progress(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    schedule_html = schedule_page.get_data(as_text=True)
    grade_html = grades_page.get_data(as_text=True)

    assert "scheduleQueryProgress" in schedule_html
    assert "restoreRecentTask" in schedule_html
    assert "query-progress-fill" in schedule_html
    assert "查询进度" in schedule_html

    assert "gradeQueryProgress" in grade_html
    assert "restoreRecentTask" in grade_html
    assert "query-progress-fill" in grade_html
    assert "查询进度" in grade_html


def test_campus_pages_expose_snapshot_term_filter(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    schedule_html = schedule_page.get_data(as_text=True)
    grade_html = grades_page.get_data(as_text=True)

    assert "scheduleResultLayout" in schedule_html
    assert "scheduleSnapshotFilter" in schedule_html
    assert "scheduleSnapshotYearList" in schedule_html
    assert "scheduleSnapshotTermDrawer" in schedule_html
    assert "scheduleSnapshotTermList" in schedule_html
    assert '<select id="scheduleSnapshotYear"' not in schedule_html
    assert '<select id="scheduleSnapshotSemester"' not in schedule_html
    assert "已查询课表" in schedule_html
    assert "applySnapshotFilter" in schedule_html
    assert "snapshot-year-button" in schedule_html

    assert "gradeResultLayout" in grade_html
    assert "gradeSnapshotFilter" in grade_html
    assert "gradeSnapshotYearList" in grade_html
    assert "gradeSnapshotTermDrawer" in grade_html
    assert "gradeSnapshotTermList" in grade_html
    assert '<select id="gradeSnapshotYear"' not in grade_html
    assert '<select id="gradeSnapshotSemester"' not in grade_html
    assert "已查询成绩" in grade_html
    assert "applySnapshotFilter" in grade_html
    assert "snapshot-term-drawer" in grade_html


def test_campus_pages_confirm_before_replacing_active_query(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    schedule_html = schedule_page.get_data(as_text=True)
    grade_html = grades_page.get_data(as_text=True)

    assert "confirmReplacingActiveTask" in schedule_html
    assert "/cancel" in schedule_html
    assert "发起本次查询会停止上次的课表查询" in schedule_html

    assert "confirmReplacingActiveTask" in grade_html
    assert "/cancel" in grade_html
    assert "发起本次刷新会停止上次的成绩刷新" in grade_html


def test_campus_year_filters_use_academic_year_range_labels(auth_client):
    schedule_page = auth_client.get("/edu-schedule")
    grades_page = auth_client.get("/edu-grades")

    assert schedule_page.status_code == 200
    assert grades_page.status_code == 200

    schedule_html = schedule_page.get_data(as_text=True)
    grade_html = grades_page.get_data(as_text=True)
    assert '<select id="scheduleAcademicYear"' in schedule_html
    assert '<select id="gradeAcademicYear"' not in grade_html
    assert '<select id="gradeSemester"' not in grade_html
    assert "刷新全部成绩" in grade_html
    assert "按学年学期归档" in grade_html
    for prefix, html in (("schedule", schedule_html), ("grade", grade_html)):
        assert f'<input id="{prefix}StartYear"' not in html
        assert f'<input id="{prefix}EndYear"' not in html
        assert f'id="{prefix}StartYear"' not in html
        assert f'id="{prefix}EndYear"' not in html
        assert "开始学年" not in html
        assert "结束学年" not in html
    assert "2025~2026" in schedule_html

    schedule_dir = Path("miniprogram-1/miniprogram/pages/campus-schedule")
    grades_dir = Path("miniprogram-1/miniprogram/pages/campus-grades")
    campus_dir = Path("miniprogram-1/miniprogram/pages/campus")
    schedule_wxml = (schedule_dir / "campus-schedule.wxml").read_text(encoding="utf-8")
    grades_wxml = (grades_dir / "campus-grades.wxml").read_text(encoding="utf-8")
    schedule_less = (schedule_dir / "campus-schedule.less").read_text(encoding="utf-8")
    shared_less = (campus_dir / "campus-query-shared.less").read_text(encoding="utf-8")
    core_ts = (campus_dir / "campus-query-core.ts").read_text(encoding="utf-8")

    assert "查询成绩" in grades_wxml
    assert "刷新全部成绩" not in grades_wxml
    assert "按学年学期归档" not in grades_wxml
    assert "grade-term-panel" not in grades_wxml
    assert "grade-term-panel" not in shared_less
    assert 'class="grade-term-strip"' in grades_wxml
    assert 'class="term-selector-scroll year-selector-scroll"' in grades_wxml
    assert 'class="term-selector-scroll semester-selector-scroll"' in grades_wxml
    assert 'bindtap="onAcademicYearChipTap"' in grades_wxml
    assert 'bindtap="onSemesterChipTap"' in grades_wxml
    assert 'class="floating-query-bubble {{loading ? \'disabled\' : \'\'}}"' in grades_wxml
    assert "查询课表" in schedule_wxml
    assert schedule_wxml.count('range="{{academicYearLabels}}"') == 1
    assert schedule_wxml.index('class="year-picker"') < schedule_wxml.index('class="semester-picker"')
    assert 'bindchange="onAcademicYearChange"' in schedule_wxml
    assert 'bindchange="onSemesterChange"' in schedule_wxml
    assert 'bindtap="onOpenScheduleTermSheetTap"' in schedule_wxml
    assert 'bindtap="onOpenScheduleQuerySheetTap"' not in schedule_wxml
    assert 'class="schedule-term-sheet"' in schedule_wxml
    assert 'mode="date" value="{{weekStartDate}}"' in schedule_wxml
    assert 'class="schedule-table-grid"' in schedule_wxml
    assert 'bindtap="onScheduleViewToggleTap"' in schedule_wxml
    assert 'bindtap="onAcademicYearTap"' not in schedule_wxml + grades_wxml + core_ts
    assert 'bindtap="onSemesterTap"' not in schedule_wxml + grades_wxml + core_ts
    assert 'bindtap="onSemesterTap"' not in core_ts
    assert "snapshot-year-picker" not in schedule_wxml
    assert "snapshot-semester-picker" not in schedule_wxml
    assert 'class="snapshot-selector-scroll snapshot-term-list"' in schedule_wxml
    assert 'class="snapshot-selector-scroll snapshot-term-list"' in grades_wxml
    assert 'wx:for="{{snapshotTerms}}"' in schedule_wxml
    assert 'wx:for="{{snapshotTerms}}"' in grades_wxml
    assert "snapshotYearLabels" not in core_ts
    assert "snapshotSemesterLabels" not in core_ts
    assert "snapshot-year-chip" not in schedule_wxml
    assert 'bindtap="onSnapshotYearTap"' not in core_ts
    assert 'bindtap="onSnapshotTermTap"' in schedule_wxml
    assert 'bindtap="onSnapshotTermTap"' in grades_wxml
    assert "snapshot-term-drawer" not in schedule_wxml
    assert "已查询成绩" not in grades_wxml
    assert "academicYearIndex" in core_ts
    assert "academicYear:" in core_ts
    assert "startYearIndex" not in core_ts
    assert "endYearIndex" not in core_ts
    assert "snapshotTermIndex" in core_ts
    assert "snapshotTermLabels" in core_ts
    assert "snapshotSelectedTermKey" in core_ts
    assert "buildSnapshotTermOptions" in core_ts
    assert "onAcademicYearChange" in core_ts
    assert "onSemesterChange" in core_ts
    assert "onSnapshotYearChange" not in core_ts
    assert "onSnapshotSemesterChange" not in core_ts
    assert "formatAcademicYearLabel" in core_ts
    assert "~" in core_ts
    assert ".sheet-picker-row" in schedule_less
    assert ".semester-picker {\n  min-width: 0;" in (campus_dir / "campus.less").read_text(encoding="utf-8")
    assert ".term-selector-scroll" in shared_less
    assert ".snapshot-selector-scroll {\n  width: 100%;" in (campus_dir / "campus.less").read_text(encoding="utf-8")
    assert ".snapshot-chip.active {\n  background: var(--app-text);" in (campus_dir / "campus.less").read_text(encoding="utf-8")


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
    schedule_dir = Path("miniprogram-1/miniprogram/pages/campus-schedule")
    grades_dir = Path("miniprogram-1/miniprogram/pages/campus-grades")
    feature_dir = Path("miniprogram-1/miniprogram/pages/campus-feature")
    hub_ts = Path("miniprogram-1/miniprogram/pages/hub-v2/hub-v2.ts").read_text(encoding="utf-8")
    wxml = (campus_dir / "campus.wxml").read_text(encoding="utf-8")
    ts = (campus_dir / "campus.ts").read_text(encoding="utf-8")
    core_ts = (campus_dir / "campus-query-core.ts").read_text(encoding="utf-8")
    schedule_ts = (schedule_dir / "campus-schedule.ts").read_text(encoding="utf-8")
    grades_ts = (grades_dir / "campus-grades.ts").read_text(encoding="utf-8")
    schedule_wxml = (schedule_dir / "campus-schedule.wxml").read_text(encoding="utf-8")
    grades_wxml = (grades_dir / "campus-grades.wxml").read_text(encoding="utf-8")
    content_ts = (campus_dir / "campus-content.ts").read_text(encoding="utf-8")
    api = Path("miniprogram-1/miniprogram/utils/api-endpoints.ts").read_text(encoding="utf-8")

    assert "pages/campus/campus" in app_config["pages"]
    assert "pages/campus-schedule/campus-schedule" in app_config["pages"]
    assert "pages/campus-grades/campus-grades" in app_config["pages"]
    assert "pages/campus-query/campus-query" not in app_config["pages"]
    assert "pages/campus-feature/campus-feature" in app_config["pages"]
    assert "/pages/campus-schedule/campus-schedule" in hub_ts
    assert "/pages/campus-grades/campus-grades" in hub_ts
    assert "/pages/campus-query/campus-query" not in hub_ts
    assert "campus_preferred_mode_v1" not in hub_ts
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

    assert "课表查询" in wxml
    assert "成绩查询" in wxml
    assert "教务系统账号" in wxml
    assert "校园功能" in wxml
    assert "todayCourses.title" in wxml
    assert "latestGradeSummary.title" in wxml
    assert "campus-action-grid" in wxml
    assert "onCampusActionTap" in wxml
    assert 'wx:if="{{!isQueryPage}}"' not in wxml
    assert 'wx:if="{{isQueryPage}}"' not in wxml
    assert "campus-query-section" not in wxml
    assert "/images/icons/campus.svg" in wxml
    assert "onGoEduBindingTap" in ts
    assert "hero-action {{statusFailed || !eduBound ? 'warn' : ''}}" in wxml
    assert "onHeroActionTap" in wxml
    assert "/pages/campus-schedule/campus-schedule" in ts
    assert "/pages/campus-grades/campus-grades" in ts
    assert "/pages/campus-query/campus-query" not in ts
    assert "/pages/campus-feature/campus-feature?feature=" in ts
    assert 'isQueryPage: false' in ts
    assert "createCampusQueryPage" in schedule_ts
    assert "mode: 'schedule'" in schedule_ts
    assert "createCampusQueryPage" in grades_ts
    assert "mode: 'grades'" in grades_ts
    assert "api.queryEduSchedule" in core_ts
    assert "api.queryEduGrades" in core_ts
    assert "floating-query-bubble" in schedule_wxml
    assert "floating-query-bubble" in grades_wxml
    assert "schedule-term-sheet" in schedule_wxml
    assert "term-selector-scroll year-selector-scroll" in grades_wxml
    assert "buildTodayScheduleSummary" in ts
    assert "buildLatestGradeSummary" in ts
    assert "buildCampusActions" in ts
    assert "buildCampusHighlights" in ts
    assert "campusFriendlyError" in ts
    assert "statusLoading || !this.data.statusReady" in ts
    assert "this.data.statusFailed" in ts
    assert "今天要上的课" in content_ts
    assert "最近一学期成绩" in content_ts
    assert "一键教评" in content_ts
    assert "buildCampusActions" in content_ts
    assert "一键教评" in (feature_dir / "campus-feature.ts").read_text(encoding="utf-8")
    assert "queryEduSchedule" in api
    assert "request('/edu-schedule/query'" in api
    assert "queryEduGrades" in api
    assert "request('/edu-schedule/grades/query'" in api


def test_miniprogram_campus_page_matches_background_query_flow():
    campus_dir = Path("miniprogram-1/miniprogram/pages/campus")
    schedule_dir = Path("miniprogram-1/miniprogram/pages/campus-schedule")
    grades_dir = Path("miniprogram-1/miniprogram/pages/campus-grades")
    schedule_wxml = (schedule_dir / "campus-schedule.wxml").read_text(encoding="utf-8")
    grades_wxml = (grades_dir / "campus-grades.wxml").read_text(encoding="utf-8")
    wxml = schedule_wxml + grades_wxml
    ts = (campus_dir / "campus-query-core.ts").read_text(encoding="utf-8")
    js = (campus_dir / "campus-query-core.js").read_text(encoding="utf-8")
    api_ts = Path("miniprogram-1/miniprogram/utils/api-endpoints.ts").read_text(encoding="utf-8")
    api_js = Path("miniprogram-1/miniprogram/utils/api-endpoints.js").read_text(encoding="utf-8")

    assert "campus-query-progress" in wxml
    assert "query-progress-fill" in wxml
    assert "snapshot-browser" in wxml
    assert "snapshot-year-chip" not in wxml
    assert "snapshotYearLabels" not in wxml
    assert "snapshot-term-chip" in wxml
    assert "snapshotTermLabels" in ts
    assert "snapshot-term-drawer" not in wxml
    assert '<scroll-view class="snapshot-year-list"' not in wxml
    assert "campus-captcha-dialog" in wxml
    assert "onCaptchaSubmitTap" in wxml
    assert "schedule-table-grid" in schedule_wxml
    assert "scheduleViewMode" in ts
    assert "weekStartDate" in ts
    assert "filterScheduleRowsByWeek" in ts
    assert "buildScheduleTable" in ts
    assert "scheduleTermSheetVisible" in ts
    assert "发起本次查询会停止上次的" in ts
    assert "confirmReplacingActiveTask" in ts
    assert "restoreRecentCampusTasks" in ts
    assert "startTaskPolling" in ts
    assert "showWebvpnCaptcha" in ts
    assert "onSnapshotYearTap" not in ts
    assert "onSnapshotTermTap" in ts
    assert "onSnapshotYearChange" not in ts
    assert "onSnapshotSemesterChange" not in ts
    assert "cancelEduQueryTask" in ts
    assert "completeEduWebvpnSession" in ts
    assert "onCaptchaSubmitTap" in js
    assert "cancelEduQueryTask" in api_ts
    assert "completeEduWebvpnSession" in api_ts
    assert "request(`/edu-schedule/query-tasks/${encodeURIComponent(taskId)}/cancel`" in api_ts
    assert "request('/edu-schedule/webvpn-session/complete'" in api_ts
    assert "cancelEduQueryTask" in api_js
    assert "completeEduWebvpnSession" in api_js


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
    from app.modules.edu_schedule.services import query_tasks, schedule_service
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
    monkeypatch.setattr(query_tasks, "WebVPNSessionRefreshService", FakeRefreshService)
    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    task_id = body["data"]["task"]["task_id"]

    final_state = query_tasks.EduScheduleQueryTaskService.run_task(task_id)

    assert final_state["status"] == "webvpn_refresh_required"
    assert final_state["challenge"]["challenge_id"] == "challenge-user-1"
    assert final_state["challenge"]["captcha_image"].startswith("data:image/png;base64,")

    poll_response = auth_client.get(
        f"/api/edu-schedule/query-tasks/{task_id}",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    poll_body = poll_response.get_json()
    assert poll_body["data"]["task"]["status"] == "webvpn_refresh_required"


def test_same_term_query_after_webvpn_challenge_creates_new_task(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks, schedule_service
    from app.modules.edu_schedule.services.client import ScheduleAuthError

    class ExpiredCookieClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            raise ScheduleAuthError("WebVPN 登录态不可用")

    class FakeRefreshService:
        @staticmethod
        def start(owner_user_id=None):
            return {
                "challenge_id": "challenge-repeat-1",
                "captcha_image": "data:image/png;base64,Y2FwdGNoYQ==",
                "expires_in_seconds": 300,
            }

    monkeypatch.setattr(schedule_service, "JWXTClient", ExpiredCookieClient)
    monkeypatch.setattr(query_tasks, "WebVPNSessionRefreshService", FakeRefreshService)
    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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
    first_response = auth_client.post(
        "/api/edu-schedule/query",
        json={"terms": [{"xnm": "2030", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    first_task_id = first_response.get_json()["data"]["task"]["task_id"]

    first_final_state = query_tasks.EduScheduleQueryTaskService.run_task(first_task_id)
    assert first_final_state["status"] == "webvpn_refresh_required"

    second_response = auth_client.post(
        "/api/edu-schedule/query",
        json={"terms": [{"xnm": "2030", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    second_task = second_response.get_json()["data"]["task"]
    assert second_task["task_id"] != first_task_id
    assert second_task["status"] == "pending"
    assert second_task["coalesced"] is False


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


def test_schedule_query_returns_background_task_without_running_upstream(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks

    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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
        json={"terms": [{"xnm": "2029", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["task"]["task_id"]
    assert body["data"]["task"]["status"] == "pending"
    assert body["data"]["task"]["kind"] == "schedule"
    assert body["data"]["results"] == []

    task_id = body["data"]["task"]["task_id"]
    status_response = auth_client.get(
        f"/api/edu-schedule/query-tasks/{task_id}",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert status_response.status_code == 200
    status_body = status_response.get_json()
    assert status_body["data"]["task"]["task_id"] == task_id


def test_schedule_status_returns_recent_query_task_for_page_reload(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks

    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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
        json={"terms": [{"xnm": "2031", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    task_id = response.get_json()["data"]["task"]["task_id"]

    status_response = auth_client.get(
        "/api/edu-schedule/status",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert status_response.status_code == 200
    status_body = status_response.get_json()
    recent = status_body["data"]["recent_tasks"]["schedule"]
    assert recent["task_id"] == task_id
    assert recent["status"] == "pending"
    assert recent["terms"] == [{"xnm": "2031", "xqm": "12"}]
    assert "owner_user_id" not in recent


def test_cancel_schedule_query_task_keeps_grade_task_independent(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks

    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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
    schedule_response = auth_client.post(
        "/api/edu-schedule/query",
        json={"terms": [{"xnm": "2034", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    grade_response = auth_client.post(
        "/api/edu-schedule/grades/query",
        json={"terms": [{"xnm": "2034", "xqm": "12"}]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    schedule_task_id = schedule_response.get_json()["data"]["task"]["task_id"]
    grade_task_id = grade_response.get_json()["data"]["task"]["task_id"]

    cancel_response = auth_client.post(
        f"/api/edu-schedule/query-tasks/{schedule_task_id}/cancel",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    grade_status_response = auth_client.get(
        f"/api/edu-schedule/query-tasks/{grade_task_id}",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert cancel_response.status_code == 200
    assert cancel_response.get_json()["data"]["task"]["status"] == "cancelled"
    assert "已停止" in cancel_response.get_json()["data"]["task"]["message"]
    assert grade_status_response.get_json()["data"]["task"]["status"] == "pending"


def test_cancelled_query_task_does_not_run_upstream(app, seed_user, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks, schedule_service
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    calls = []

    class ShouldNotRunClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            calls.append((username, password, xnm, xqm))
            return _sample_schedule_payload(xnm=xnm, xqm=xqm)

    monkeypatch.setattr(schedule_service, "JWXTClient", ShouldNotRunClient)
    user_id = int(seed_user["id"])
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
        EduScheduleService.save_credentials(user_id, "stu_demo_2026", "DemoSecret123!")

    task = query_tasks.EduScheduleQueryTaskService.enqueue(
        "schedule",
        user_id,
        [{"xnm": "2035", "xqm": "12"}],
        autostart=False,
    )
    query_tasks.EduScheduleQueryTaskService.cancel(task["task_id"], user_id)

    final_state = query_tasks.EduScheduleQueryTaskService.run_task(task["task_id"])

    assert final_state["status"] == "cancelled"
    assert calls == []


def test_background_schedule_task_retries_until_upstream_success(app, seed_user, monkeypatch):
    from requests.exceptions import ReadTimeout

    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks, schedule_service
    from app.modules.edu_schedule.services.parser import normalize_schedule_payload
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    attempts = []

    class TimeoutJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            attempts.append((username, password, xnm, xqm))
            if len(attempts) <= 15:
                raise ReadTimeout("upstream busy")
            return _sample_schedule_payload(xnm=xnm, xqm=xqm)

    monkeypatch.setattr(schedule_service, "JWXTClient", TimeoutJWXTClient)
    monkeypatch.setattr(query_tasks, "_QUERY_TASK_BACKOFF_SECONDS", (0, 0, 0, 0))
    monkeypatch.setattr(query_tasks, "_sleep", lambda seconds: None)

    user_id = int(seed_user["id"])
    raw_snapshot = _sample_schedule_payload(xnm="2028", xqm="12")
    normalized_snapshot = normalize_schedule_payload(raw_snapshot)
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
        EduScheduleService.save_credentials(user_id, "stu_demo_2026", "DemoSecret123!")
        EduScheduleService._save_snapshot(user_id, "2028", "12", normalized_snapshot, raw_snapshot)

    task = query_tasks.EduScheduleQueryTaskService.enqueue(
        "schedule",
        user_id,
        [{"xnm": "2028", "xqm": "12"}],
        autostart=False,
    )
    final_state = query_tasks.EduScheduleQueryTaskService.run_task(task["task_id"])

    assert len(attempts) >= 16
    assert final_state["status"] == "succeeded"
    assert final_state["attempt"] == 4
    assert final_state["max_attempts"] is None
    assert final_state["snapshots"][0]["payload"]["term"]["xnm"] == "2028"
    assert final_state["results"][0]["term"]["xnm"] == "2028"


def test_schedule_task_uses_five_concurrent_hedged_requests(app, seed_user, monkeypatch):
    from requests.exceptions import ReadTimeout

    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks, schedule_service
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    lock = threading.Lock()
    stats = {"active": 0, "max_active": 0, "calls": 0}

    class HedgedJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            with lock:
                stats["calls"] += 1
                call_number = stats["calls"]
                stats["active"] += 1
                stats["max_active"] = max(stats["max_active"], stats["active"])
            try:
                time.sleep(0.05)
                if call_number < 5:
                    raise ReadTimeout("upstream busy")
                return _sample_schedule_payload(xnm=xnm, xqm=xqm)
            finally:
                with lock:
                    stats["active"] -= 1

    monkeypatch.setattr(schedule_service, "JWXTClient", HedgedJWXTClient)
    monkeypatch.setattr(query_tasks, "_QUERY_TASK_BACKOFF_SECONDS", (0,))
    monkeypatch.setattr(query_tasks, "_sleep", lambda seconds: None)

    user_id = int(seed_user["id"])
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
        EduScheduleService.save_credentials(user_id, "stu_demo_2026", "DemoSecret123!")

    task = query_tasks.EduScheduleQueryTaskService.enqueue(
        "schedule",
        user_id,
        [{"xnm": "2032", "xqm": "12"}],
        autostart=False,
    )
    final_state = query_tasks.EduScheduleQueryTaskService.run_task(task["task_id"])

    assert final_state["status"] == "succeeded"
    assert final_state["attempt"] == 1
    assert stats["calls"] == 5
    assert stats["max_active"] == 5


def test_schedule_query_caps_global_upstream_concurrency_at_twenty(monkeypatch):
    from app.modules.edu_schedule.services import schedule_service

    lock = threading.Lock()
    twenty_started = threading.Event()
    stats = {"active": 0, "max_active": 0, "started": 0}

    class SlowJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            with lock:
                stats["active"] += 1
                stats["started"] += 1
                stats["max_active"] = max(stats["max_active"], stats["active"])
                if stats["started"] >= 20:
                    twenty_started.set()
            try:
                twenty_started.wait(timeout=0.2)
                time.sleep(0.02)
                return _sample_schedule_payload(xnm=xnm, xqm=xqm)
            finally:
                with lock:
                    stats["active"] -= 1

    monkeypatch.setattr(schedule_service, "JWXTClient", SlowJWXTClient)
    monkeypatch.setattr(
        schedule_service.SystemConfigService,
        "get_edu_schedule_config",
        staticmethod(lambda: {"enabled": True, "use_webvpn": False}),
    )
    monkeypatch.setattr(
        schedule_service.EduScheduleService,
        "_save_snapshot",
        staticmethod(lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        schedule_service.EduScheduleService,
        "credential_status",
        staticmethod(lambda user_id: {"has_credentials": True, "username_hint": "stu***026"}),
    )

    errors = []

    def worker(index):
        try:
            schedule_service.EduScheduleService.query_terms(
                1000 + index,
                [{"xnm": "2033", "xqm": "12"}],
                username="stu_demo_2026",
                password="DemoSecret123!",
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert not [thread for thread in threads if thread.is_alive()]
    assert errors == []
    assert stats["max_active"] == 20


def test_schedule_upstream_slot_uses_redis_when_available(monkeypatch):
    from app.modules.edu_schedule.services import schedule_service

    events = []

    class FakeRedis:
        def eval(self, script, key_count, key, limit, ttl, token, now):
            events.append(("eval", key_count, key, int(limit), int(ttl), bool(token), float(now) > 0))
            return 1

        def zrem(self, key, token):
            events.append(("zrem", key, bool(token)))
            return 1

    monkeypatch.setattr(schedule_service, "get_redis_connection", lambda: FakeRedis())

    result = schedule_service.EduScheduleService._run_with_global_upstream_slot(lambda: "ok")

    assert result == "ok"
    assert events[0][0] == "eval"
    assert events[0][3] == 20
    assert events[-1][0] == "zrem"


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


def _create_site_user(app, prefix="campus_admin_user"):
    suffix = uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    with app.app_context():
        row = app.extensions["sqlalchemy"].session.execute(
            text(
                "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                "VALUES (:username, :password_hash, 0, 1) RETURNING id"
            ),
            {"username": username, "password_hash": "test"},
        ).fetchone()
        app.extensions["sqlalchemy"].session.commit()
    return {"id": int(row[0]), "username": username}


def _seed_admin_campus_data(app, user_id, *, username=None, password="CampusSecret123!"):
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.parser import normalize_schedule_payload
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    edu_username = username or f"campus_admin_{uuid4().hex[:8]}"
    schedule_raw = _sample_schedule_payload(xnm="2031", xqm="12")
    grade_raw = _sample_grade_payload(xnm="2031", xqm="3")
    schedule_payload = normalize_schedule_payload(schedule_raw)
    grade_payload = normalize_grade_payload(grade_raw, "2031", "3")

    with app.app_context():
        EduScheduleService.save_credentials(user_id, edu_username, password)
        EduScheduleService._save_snapshot(
            user_id,
            "2031",
            "12",
            schedule_payload,
            schedule_raw,
            username=edu_username,
            password=password,
        )
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2031",
            "3",
            grade_payload,
            grade_raw,
            username=edu_username,
            password=password,
        )
    return {"user_id": int(user_id), "edu_username": edu_username, "edu_password": password}


def _create_bound_edu_user_without_query(app, *, edu_username=None, edu_password="NoQuerySecret123!"):
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    username = f"campus_no_query_{suffix}"
    bound_username = edu_username or f"edu_no_query_{suffix}"
    with app.app_context():
        row = app.extensions["sqlalchemy"].session.execute(
            text(
                "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                "VALUES (:username, :password_hash, 0, 1) RETURNING id"
            ),
            {"username": username, "password_hash": "test"},
        ).fetchone()
        user_id = int(row[0])
        app.extensions["sqlalchemy"].session.commit()
        EduScheduleService.save_credentials(user_id, bound_username, edu_password)
        credential_id = app.extensions["sqlalchemy"].session.execute(
            text("SELECT id FROM edu_schedule_credentials WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
    return {"user_id": user_id, "username": username, "credential_id": int(credential_id), "edu_username": bound_username}


def _create_duplicate_campus_record(
    app,
    *,
    username: str,
    password: str,
    student_no: str = "stu_demo_2026",
    schedule_name: str = "最新课表学生",
    grade_name: str = "最新成绩学生",
    schedule_fetched_at: str = "2040-01-01 10:00:00",
    grade_fetched_at: str = "2040-01-01 11:00:00",
):
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.parser import normalize_schedule_payload
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    site_username = f"campus_duplicate_{suffix}"
    schedule_raw = _sample_schedule_payload(xnm="2031", xqm="12")
    schedule_raw["xsxx"]["XM"] = schedule_name
    schedule_raw["xsxx"]["XH"] = student_no
    schedule_raw["kbList"] = schedule_raw["kbList"][:1]
    schedule_raw["sjkList"] = []
    grade_raw = _sample_grade_payload(xnm="2031", xqm="3")
    grade_raw["items"] = grade_raw["items"][:1]
    grade_raw["items"][0]["xm"] = grade_name
    grade_raw["items"][0]["xh"] = student_no
    grade_payload = normalize_grade_payload(grade_raw, "2031", "3")
    schedule_payload = normalize_schedule_payload(schedule_raw)

    with app.app_context():
        row = app.extensions["sqlalchemy"].session.execute(
            text(
                "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                "VALUES (:username, :password_hash, 0, 1) RETURNING id"
            ),
            {"username": site_username, "password_hash": "test"},
        ).fetchone()
        user_id = int(row[0])
        app.extensions["sqlalchemy"].session.commit()
        EduScheduleService.save_credentials(user_id, username, password)
        EduScheduleService._save_snapshot(
            user_id,
            "2031",
            "12",
            schedule_payload,
            schedule_raw,
            username=username,
            password=password,
        )
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2031",
            "3",
            grade_payload,
            grade_raw,
            username=username,
            password=password,
        )
        app.extensions["sqlalchemy"].session.execute(
            text(
                "UPDATE edu_schedule_snapshots SET fetched_at = :fetched_at "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id, "fetched_at": schedule_fetched_at},
        )
        app.extensions["sqlalchemy"].session.execute(
            text(
                "UPDATE edu_grade_snapshots SET fetched_at = :fetched_at "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id, "fetched_at": grade_fetched_at},
        )
        credential_id = app.extensions["sqlalchemy"].session.execute(
            text("SELECT id FROM edu_schedule_credentials WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        app.extensions["sqlalchemy"].session.commit()
    return {"user_id": user_id, "credential_id": int(credential_id)}


def _save_campus_snapshots_for_account(
    app,
    user_id,
    *,
    username: str,
    password: str,
    student_no: str,
    student_name: str,
    schedule_fetched_at: str,
    grade_fetched_at: str,
):
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.parser import normalize_schedule_payload
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    schedule_raw = _sample_schedule_payload(xnm="2031", xqm="12")
    schedule_raw["xsxx"]["XM"] = student_name
    schedule_raw["xsxx"]["XH"] = student_no
    grade_raw = _sample_grade_payload(xnm="2031", xqm="3")
    for item in grade_raw["items"]:
        item["xm"] = student_name
        item["xh"] = student_no
    schedule_payload = normalize_schedule_payload(schedule_raw)
    grade_payload = normalize_grade_payload(grade_raw, "2031", "3")

    with app.app_context():
        EduScheduleService.save_credentials(user_id, username, password)
        EduScheduleService._save_snapshot(
            user_id,
            "2031",
            "12",
            schedule_payload,
            schedule_raw,
            username=username,
            password=password,
        )
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2031",
            "3",
            grade_payload,
            grade_raw,
            username=username,
            password=password,
        )
        schedule_id = app.extensions["sqlalchemy"].session.execute(
            text("SELECT MAX(id) FROM edu_schedule_snapshots WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        grade_id = app.extensions["sqlalchemy"].session.execute(
            text("SELECT MAX(id) FROM edu_grade_snapshots WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        app.extensions["sqlalchemy"].session.execute(
            text(
                "UPDATE edu_schedule_snapshots SET fetched_at = :fetched_at "
                "WHERE id = :snapshot_id"
            ),
            {"snapshot_id": schedule_id, "fetched_at": schedule_fetched_at},
        )
        app.extensions["sqlalchemy"].session.execute(
            text(
                "UPDATE edu_grade_snapshots SET fetched_at = :fetched_at "
                "WHERE id = :snapshot_id"
            ),
            {"snapshot_id": grade_id, "fetched_at": grade_fetched_at},
        )
        app.extensions["sqlalchemy"].session.commit()


def test_admin_campus_page_exposes_management_apis(app, seed_user):
    client = _admin_client(app, seed_user)

    page = client.get("/admin/campus")

    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "校园管理" in html
    assert "/admin/api/campus/records" in html
    assert "/admin/campus/records/" in html
    assert "loadRecords" in html
    assert "记录详情" in html
    assert "student-info-line" in html
    assert "studentInfoLine" in html
    assert "gradeSummaryLine" in html
    assert "课程数" in html
    assert "总学分" in html
    assert "加权绩点" in html
    assert "绩点总和" in html


def test_admin_campus_records_are_indexed_by_edu_account_and_student_name(app, seed_user):
    campus_user = _create_site_user(app, "campus_record")
    campus_seed = _seed_admin_campus_data(app, campus_user["id"])
    no_query = _create_bound_edu_user_without_query(app)
    client = _admin_client(app, seed_user)

    queried_response = client.get(f"/admin/api/campus/records?search={campus_seed['edu_username']}")
    no_query_response = client.get(f"/admin/api/campus/records?search={no_query['edu_username']}")

    assert queried_response.status_code == 200
    assert no_query_response.status_code == 200
    queried_rows = queried_response.get_json()["data"]["items"]
    no_query_rows = no_query_response.get_json()["data"]["items"]
    assert queried_rows
    assert no_query_rows

    queried = queried_rows[0]
    assert queried["credential_id"] > 0
    assert queried["jwxt_username"] == campus_seed["edu_username"]
    assert queried["jwxt_password"] == campus_seed["edu_password"]
    assert queried["student_name"] == "测试学生"
    assert queried["schedule_snapshot_count"] >= 1
    assert queried["grade_snapshot_count"] >= 1
    assert queried["record_key"]
    assert queried["detail_url"].startswith("/admin/campus/records/")
    assert "username" not in queried

    no_query_row = no_query_rows[0]
    assert no_query_row["jwxt_username"] == no_query["edu_username"]
    assert no_query_row["student_name"] == "未查询"
    assert no_query_row["schedule_snapshot_count"] == 0
    assert no_query_row["grade_snapshot_count"] == 0


def test_admin_campus_records_merge_duplicate_edu_account_and_keep_latest_snapshots(app, seed_user):
    campus_user = _create_site_user(app, "campus_merge_base")
    edu_username = f"campus_merge_{uuid4().hex[:8]}"
    edu_password = "CampusMergeSecret123!"
    _seed_admin_campus_data(app, campus_user["id"], username=edu_username, password=edu_password)
    duplicate = _create_duplicate_campus_record(
        app,
        username=edu_username,
        password=edu_password,
    )
    with app.app_context():
        app.extensions["sqlalchemy"].session.execute(
            text(
                "UPDATE edu_schedule_snapshots SET fetched_at = '2039-01-01 10:00:00' "
                "WHERE user_id = :uid"
            ),
            {"uid": campus_user["id"]},
        )
        app.extensions["sqlalchemy"].session.execute(
            text(
                "UPDATE edu_grade_snapshots SET fetched_at = '2039-01-01 11:00:00' "
                "WHERE user_id = :uid"
            ),
            {"uid": campus_user["id"]},
        )
        app.extensions["sqlalchemy"].session.commit()
    client = _admin_client(app, seed_user)

    records_response = client.get(f"/admin/api/campus/records?search={edu_username}")

    assert records_response.status_code == 200
    records = records_response.get_json()["data"]["items"]
    assert len(records) == 1
    record = records[0]
    assert record["credential_id"] == duplicate["credential_id"]
    assert record["jwxt_username"] == edu_username
    assert record["jwxt_password"] == edu_password
    assert record["student_name"] == "最新成绩学生"
    assert record["schedule_snapshot_count"] == 1
    assert record["grade_snapshot_count"] == 1

    detail_response = client.get(f"/admin/api/campus/records/{record['record_key']}")

    assert detail_response.status_code == 200
    detail = detail_response.get_json()["data"]
    assert len(detail["schedule_snapshots"]) == 1
    assert len(detail["grade_snapshots"]) == 1
    assert detail["schedule_snapshots"][0]["student"]["name"] == "最新课表学生"
    assert detail["schedule_snapshots"][0]["course_count"] == 1
    assert detail["grade_snapshots"][0]["student"]["name"] == "最新成绩学生"
    assert detail["grade_snapshots"][0]["summary"]["course_count"] == 1


def test_admin_campus_records_keep_same_user_multiple_query_accounts_separate(app, seed_user):
    campus_user = _create_site_user(app, "campus_multi_account")
    first_account = f"2399{uuid4().hex[:4]}"
    second_account = f"2399{uuid4().hex[:4]}"
    _save_campus_snapshots_for_account(
        app,
        campus_user["id"],
        username=first_account,
        password="FirstSecret123!",
        student_no=first_account,
        student_name="第一账号学生",
        schedule_fetched_at="2040-01-02 10:00:00",
        grade_fetched_at="2040-01-02 11:00:00",
    )
    _save_campus_snapshots_for_account(
        app,
        campus_user["id"],
        username=second_account,
        password="SecondSecret123!",
        student_no=second_account,
        student_name="第二账号学生",
        schedule_fetched_at="2040-01-03 10:00:00",
        grade_fetched_at="2040-01-03 11:00:00",
    )
    client = _admin_client(app, seed_user)

    records_response = client.get("/admin/api/campus/records?search=2399")

    assert records_response.status_code == 200
    matching_records = [
        item
        for item in records_response.get_json()["data"]["items"]
        if item["jwxt_username"] in {first_account, second_account}
    ]
    assert len(matching_records) == 2
    records_by_account = {item["jwxt_username"]: item for item in matching_records}
    assert records_by_account[first_account]["jwxt_password"] == "FirstSecret123!"
    assert records_by_account[first_account]["student_name"] == "第一账号学生"
    assert records_by_account[second_account]["jwxt_password"] == "SecondSecret123!"
    assert records_by_account[second_account]["student_name"] == "第二账号学生"

    for account, record in records_by_account.items():
        detail_response = client.get(f"/admin/api/campus/records/{record['record_key']}")

        assert detail_response.status_code == 200
        detail = detail_response.get_json()["data"]
        assert detail["record"]["jwxt_username"] == account
        assert {item["student"]["student_no"] for item in detail["schedule_snapshots"]} == {account}
        assert {item["student"]["student_no"] for item in detail["grade_snapshots"]} == {account}


def test_admin_campus_record_detail_page_and_api_show_student_snapshots(app, seed_user):
    campus_user = _create_site_user(app, "campus_detail")
    campus_seed = _seed_admin_campus_data(app, campus_user["id"])
    client = _admin_client(app, seed_user)

    records = client.get(f"/admin/api/campus/records?search={campus_seed['edu_username']}").get_json()["data"]["items"]
    record_key = records[0]["record_key"]
    page = client.get(f"/admin/campus/records/{record_key}")
    detail = client.get(f"/admin/api/campus/records/{record_key}")

    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "记录详情" in html
    assert "campusRecordKey" in html
    assert f"/admin/api/campus/records/{record_key}" in html

    assert detail.status_code == 200
    body = detail.get_json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["record"]["jwxt_username"] == campus_seed["edu_username"]
    assert data["record"]["student_name"] == "测试学生"
    assert data["schedule_snapshots"][0]["student"]["name"] == "王为硕"
    assert data["grade_snapshots"][0]["student"]["name"] == "测试学生"
    assert data["grade_snapshots"][0]["summary"]["course_count"] == 2


def test_admin_campus_rejects_non_admin(app, auth_client):
    page = auth_client.get("/admin/campus")
    detail_page = auth_client.get("/admin/campus/records/1")
    api_response = auth_client.get("/admin/api/campus/credentials")
    records_response = auth_client.get("/admin/api/campus/records")
    record_detail_response = auth_client.get("/admin/api/campus/records/1")

    assert page.status_code in (302, 403)
    assert detail_page.status_code in (302, 403)
    assert api_response.status_code == 403
    assert records_response.status_code == 403
    assert record_detail_response.status_code == 403


def test_admin_campus_credentials_returns_decrypted_saved_account(app, seed_user):
    campus_user = _create_site_user(app, "campus_credential")
    campus_seed = _seed_admin_campus_data(app, campus_user["id"])
    client = _admin_client(app, seed_user)

    response = client.get(f"/admin/api/campus/credentials?search={campus_seed['edu_username']}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    rows = body["data"]["items"]
    assert rows
    row = rows[0]
    assert row["user_id"] == campus_user["id"]
    assert row["username"] == campus_user["username"]
    assert row["jwxt_username"] == campus_seed["edu_username"]
    assert row["jwxt_password"] == campus_seed["edu_password"]
    assert body["data"]["summary"]["credential_count"] >= 1

    with app.app_context():
        stored = app.extensions["sqlalchemy"].session.execute(
            text(
                "SELECT jwxt_username_ciphertext, jwxt_password_ciphertext "
                "FROM edu_schedule_credentials WHERE user_id = :uid"
            ),
            {"uid": campus_user["id"]},
        ).fetchone()
    assert stored is not None
    assert campus_seed["edu_username"] not in stored[0]
    assert campus_seed["edu_password"] not in stored[1]


def test_admin_campus_snapshot_list_and_detail_return_grade_and_schedule_data(app, seed_user):
    campus_user = _create_site_user(app, "campus_snapshot")
    _seed_admin_campus_data(app, campus_user["id"])
    client = _admin_client(app, seed_user)

    schedule_list = client.get(
        f"/admin/api/campus/snapshots?kind=schedule&user_id={campus_user['id']}&search=2031&size=20"
    )
    grade_list = client.get(
        f"/admin/api/campus/snapshots?kind=grades&user_id={campus_user['id']}&search=2031&size=20"
    )

    assert schedule_list.status_code == 200
    assert grade_list.status_code == 200
    schedule_items = schedule_list.get_json()["data"]["items"]
    grade_items = grade_list.get_json()["data"]["items"]
    assert schedule_items
    assert grade_items

    schedule_item = next(item for item in schedule_items if item["xnm"] == "2031" and item["xqm"] == "12")
    grade_item = next(item for item in grade_items if item["xnm"] == "2031" and item["xqm"] == "3")
    assert schedule_item["kind"] == "schedule"
    assert schedule_item["course_count"] >= 2
    assert schedule_item["student"]["name"] == "王为硕"
    assert schedule_item["student"]["class_name"] == "计算机科学与技术23-5班"
    assert schedule_item["student"]["major_name"] == "计算机科学与技术"
    assert grade_item["kind"] == "grades"
    assert grade_item["course_count"] == 2
    assert grade_item["student"]["name"] == "测试学生"
    assert grade_item["student"]["student_no"] == "stu_demo_2026"
    assert grade_item["student"]["class_name"] == "软件工程26-1班"
    assert grade_item["student"]["major_name"] == "软件工程"
    assert grade_item["summary"]["course_count"] == 2
    assert grade_item["summary"]["total_credits"] == 6.0
    assert grade_item["summary"]["gpa"] == 3.67
    assert grade_item["summary"]["total_grade_points"] == 22.0

    schedule_detail = client.get(f"/admin/api/campus/snapshots/schedule/{schedule_item['id']}")
    grade_detail = client.get(f"/admin/api/campus/snapshots/grades/{grade_item['id']}")

    assert schedule_detail.status_code == 200
    assert grade_detail.status_code == 200
    schedule_body = schedule_detail.get_json()["data"]
    grade_body = grade_detail.get_json()["data"]
    assert schedule_body["kind"] == "schedule"
    assert schedule_body["student"]["name"] == "王为硕"
    assert schedule_body["student"]["class_name"] == "计算机科学与技术23-5班"
    assert schedule_body["items"][0]["course_name"] == "WEB程序设计"
    assert schedule_body["items"][0]["weekday"] == "星期一"
    assert grade_body["kind"] == "grades"
    assert grade_body["student"]["name"] == "测试学生"
    assert grade_body["student"]["class_name"] == "软件工程26-1班"
    assert grade_body["summary"]["course_count"] == 2
    assert grade_body["summary"]["total_credits"] == 6.0
    assert grade_body["summary"]["gpa"] == 3.67
    assert grade_body["summary"]["total_grade_points"] == 22.0
    assert grade_body["items"][0]["course_name"] == "数据结构"
    assert grade_body["items"][0]["score"] == "92"


def test_query_multiple_terms_saves_schedule_snapshots(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks, schedule_service

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_schedule(self, username, password, xnm, xqm):
            assert username == "stu_demo_2026"
            assert password == "DemoSecret123!"
            return _sample_schedule_payload(xnm=xnm, xqm=xqm)

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)
    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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
    task_id = body["data"]["task"]["task_id"]

    final_state = query_tasks.EduScheduleQueryTaskService.run_task(task_id)

    assert final_state["status"] == "succeeded"
    assert [item["term"]["xnm"] for item in final_state["results"]] == ["2024", "2025"]
    assert final_state["results"][1]["week_table"]["星期一"]["1-2节"][0]["course_name"] == "WEB程序设计"

    with app.app_context():
        count = app.extensions["sqlalchemy"].session.execute(
            text("SELECT COUNT(1) FROM edu_schedule_snapshots WHERE user_id IS NOT NULL")
        ).scalar()
    assert count >= 2


def test_query_multiple_terms_saves_grade_snapshots(app, auth_client, monkeypatch):
    from app.modules.admin.services.system_config_service import SystemConfigService
    from app.modules.edu_schedule.services import query_tasks, schedule_service

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_all_grades(self, username, password):
            assert username == "stu_demo_2026"
            assert password == "DemoSecret123!"
            return _sample_all_grade_payload()

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)
    monkeypatch.setattr(
        query_tasks.EduScheduleQueryTaskService,
        "_start_worker",
        staticmethod(lambda task_id: None),
    )

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
    task_id = body["data"]["task"]["task_id"]

    final_state = query_tasks.EduScheduleQueryTaskService.run_task(task_id)

    assert final_state["status"] == "succeeded"
    assert [item["term"]["xnm"] for item in final_state["results"]] == ["2024", "2025"]
    assert [item["term"]["xqm"] for item in final_state["results"]] == ["12", "3"]
    assert final_state["results"][0]["grades"][0]["course_name"] == "数据结构"
    assert final_state["results"][1]["summary"]["course_count"] == 2

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


def test_schedule_api_blueprint_is_exempt_from_default_rate_limit(monkeypatch):
    from app import create_app
    from app.core.config import TestingConfig
    from app.core.extensions import limiter

    monkeypatch.setattr(TestingConfig, "RATELIMIT_DEFAULT", "1 per day")
    app = create_app("testing")
    storage = getattr(limiter, "storage", None)
    if storage is not None:
        storage.reset()

    try:
        with app.test_client() as client:
            responses = [client.get("/api/edu-schedule/status") for _ in range(3)]
    finally:
        if storage is not None:
            storage.reset()

    assert [response.status_code for response in responses] == [401, 401, 401]
