# -*- coding: utf-8 -*-
"""累计学分绩点总览测试。"""

from decimal import Decimal
from uuid import uuid4

import pytest
import requests
from sqlalchemy import text


def _all_grade_payload(*, student_no: str = "stu_demo_2026", grade_point: str = "4.00"):
    return {
        "items": [
            {
                "xh": student_no,
                "xm": "测试学生",
                "xnm": "2024",
                "xqm": "12",
                "xnmmc": "2024-2025",
                "xqmmc": "2",
                "kch": "CS1001",
                "kcmc": "数据结构",
                "xf": "4.0",
                "cj": "95",
                "bfzcj": "95",
                "jd": grade_point,
                "xfjd": str(Decimal("4.0") * Decimal(grade_point)),
            },
            {
                "xh": student_no,
                "xm": "测试学生",
                "xnm": "2025",
                "xqm": "3",
                "xnmmc": "2025-2026",
                "xqmmc": "1",
                "kch": "CS1002",
                "kcmc": "创新实践",
                "xf": "2.0",
                "cj": "85",
                "bfzcj": "85",
                "jd": "3.00",
                "xfjd": "6.00",
            },
        ],
        "totalResult": 2,
    }


def _client_config(cookie: str = ""):
    return {
        "enabled": True,
        "use_webvpn": bool(cookie),
        "webvpn_base_url": "https://webvpn.synu.edu.cn",
        "webvpn_login_path": "/users/sign_in",
        "webvpn_cookie": cookie,
        "jwxt_base_url": "https://jwxt.webvpn.synu.edu.cn/jwglxt",
        "jwxt_login_path": "/xtgl/login_slogin.html",
        "grade_path": "/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005",
        "request_timeout": 20,
        "verify_tls": True,
        "allowed_hosts": ("webvpn.synu.edu.cn", "jwxt.webvpn.synu.edu.cn"),
    }


@pytest.fixture
def grade_task_redis(monkeypatch):
    from app.core.utils.redis_utils import get_redis_connection
    from app.modules.edu_schedule.services import query_tasks

    connection = get_redis_connection("redis://redis:6379/15")
    if connection is None:
        pytest.skip("Redis 测试连接不可用")
    try:
        connection.ping()
    except Exception:
        pytest.skip("Redis 测试服务不可用")
    connection.flushdb()
    monkeypatch.setattr(query_tasks, "get_redis_connection", lambda: connection)
    yield connection
    connection.flushdb()


def test_official_gpa_parser_anchors_label_and_ignores_other_numbers():
    from app.modules.edu_schedule.services.grade_overview import parse_official_gpa_html

    html = """
    <html><body>
      <div>已修学分：128.5</div>
      <div>当前所有课程 <strong>平均学分绩点（GPA）</strong>： <span>3.23</span></div>
      <script>window.fakeGpa = 4.99;</script>
    </body></html>
    """

    assert parse_official_gpa_html(html) == Decimal("3.23")


@pytest.mark.parametrize(
    "html",
    [
        "<html><body>登录 教务管理系统</body></html>",
        "<html><body>当前所有课程 平均学分绩点（GPA）：9.99</body></html>",
        "<html><body>总学分：128.5</body></html>",
    ],
)
def test_official_gpa_parser_rejects_invalid_pages(html):
    from app.modules.edu_schedule.services.grade_overview import GradeOverviewParseError, parse_official_gpa_html

    with pytest.raises(GradeOverviewParseError):
        parse_official_gpa_html(html)


def test_calculated_cumulative_gpa_uses_decimal_half_up_and_skips_invalid_rows():
    from app.modules.edu_schedule.services.grade_overview import calculate_cumulative_gpa

    payload = {
        "items": [
            {"xnm": "2024", "xqm": "12", "xf": "1", "jd": "2.345", "xfjd": "2.345"},
            {"xnm": "2024", "xqm": "12", "xf": "1", "jd": "2.344"},
            {"xnm": "2024", "xqm": "12", "xf": "2", "jd": "", "xfjd": "8"},
            {"xnm": "2024", "xqm": "12", "xf": "0", "jd": "5", "xfjd": "0"},
            {"xnm": "2024", "xqm": "12", "xf": "bad", "jd": "4", "xfjd": "4"},
        ]
    }

    assert calculate_cumulative_gpa(payload) == Decimal("2.34")


def test_calculated_cumulative_gpa_keeps_numeric_zero_grade_points():
    from app.modules.edu_schedule.services.grade_overview import calculate_cumulative_gpa

    payload = {
        "items": [
            {"xnm": "2024", "xqm": "12", "xf": 2, "jd": 0, "xfjd": 0},
            {"xnm": "2024", "xqm": "12", "xf": 2, "jd": 4, "xfjd": 8},
        ]
    }

    assert calculate_cumulative_gpa(payload) == Decimal("2.00")


def test_calculated_cumulative_gpa_rejects_truncated_grade_payload():
    from app.modules.edu_schedule.services.grade_overview import calculate_cumulative_gpa

    payload = _all_grade_payload()
    payload["totalResult"] = len(payload["items"]) + 1

    assert calculate_cumulative_gpa(payload) is None

    payload["totalResult"] = len(payload["items"]) - 1

    assert calculate_cumulative_gpa(payload) is None


def test_calculated_cumulative_gpa_skips_out_of_range_grade_rows():
    from app.modules.edu_schedule.services.grade_overview import calculate_cumulative_gpa

    payload = {
        "items": [
            {"xnm": "2024", "xqm": "12", "xf": "2", "jd": "4", "xfjd": "8"},
            {"xnm": "2024", "xqm": "12", "xf": "2", "jd": "6", "xfjd": "12"},
            {"xnm": "2024", "xqm": "12", "xf": "2", "jd": "4", "xfjd": "10.01"},
        ],
        "totalResult": 3,
    }

    assert calculate_cumulative_gpa(payload) == Decimal("4.00")


def test_academic_year_weighted_averages_match_school_published_values():
    from app.modules.edu_schedule.services.grade_overview import (
        calculate_academic_year_weighted_averages,
    )

    def snapshot(xnm, xqm, included_rows, excluded_credits=()):
        grades = [
            {
                "credits": str(credits),
                "converted_score": str(converted_score),
                "grade_point": "1",
            }
            for credits, converted_score in included_rows
        ]
        grades.extend(
            {
                "credits": str(credits),
                "converted_score": "85",
                "grade_point": "",
            }
            for credits in excluded_credits
        )
        return {
            "payload": {
                "term": {
                    "xnm": xnm,
                    "xqm": xqm,
                    "year_name": f"{xnm}-{int(xnm) + 1}",
                },
                "grades": grades,
            }
        }

    snapshots = [
        snapshot(
            "2023",
            "3",
            [(4, 100), (3, 87), (1, 74), (3, 65), (4, 87), (3, 90), (3, 95), (4, 94)],
            excluded_credits=(2, 2, 1),
        ),
        snapshot(
            "2023",
            "12",
            [(1, 95), (1, 77), (4, 81), (2, 95), (0.5, 75), (3.5, 92), (4, 98), (3, 83), (4, 84)],
            excluded_credits=(1, 1, 2),
        ),
        snapshot(
            "2024",
            "3",
            [(4, 97), (1, 90), (2, 75), (3.5, 86), (4, 92), (3, 83), (2, 95)],
            excluded_credits=(2, 1, 1),
        ),
        snapshot(
            "2024",
            "12",
            [(2, 85), (1, 85), (3, 76), (1, 80), (2, 76), (0.5, 85), (4, 85), (4, 98), (3, 95), (3, 85), (3, 91), (4, 90)],
            excluded_credits=(1, 2, 2),
        ),
    ]

    result = calculate_academic_year_weighted_averages(snapshots)
    by_year = {item["xnm"]: item for item in result}

    assert by_year["2023"] == {
        "xnm": "2023",
        "year_name": "2023-2024",
        "year_number": 1,
        "weighted_average": 88.16,
        "included_credits": 48.0,
        "included_course_count": 17,
    }
    assert by_year["2024"] == {
        "xnm": "2024",
        "year_name": "2024-2025",
        "year_number": 2,
        "weighted_average": 87.97,
        "included_credits": 50.0,
        "included_course_count": 19,
    }


def test_academic_year_weighted_average_keeps_zero_grade_point_and_rejects_bad_rows():
    from app.modules.edu_schedule.services.grade_overview import (
        calculate_academic_year_weighted_averages,
    )

    snapshots = [
        {
            "payload": {
                "term": {"xnm": "2025", "xqm": "3", "year_name": "2025-2026"},
                "grades": [
                    {"credits": "2", "converted_score": "0", "grade_point": "0"},
                    {"credits": "2", "converted_score": "100", "grade_point": "4"},
                    {"credits": "2", "converted_score": "101", "grade_point": "4"},
                    {"credits": "2", "converted_score": "85", "grade_point": ""},
                ],
            }
        }
    ]

    result = calculate_academic_year_weighted_averages(snapshots)

    assert result[0]["weighted_average"] == 50.0
    assert result[0]["included_course_count"] == 2


def test_academic_year_average_handles_third_term_holes_rounding_and_duplicates():
    from app.modules.edu_schedule.services.grade_overview import (
        calculate_academic_year_weighted_averages,
    )

    def snapshot(xnm, xqm, grades):
        return {
            "payload": {
                "term": {
                    "xnm": xnm,
                    "xqm": xqm,
                    "year_name": f"{xnm}-{int(xnm) + 1}",
                },
                "grades": grades,
            }
        }

    snapshots = [
        snapshot(
            "2023",
            "3",
            [{"credits": "2", "converted_score": "85", "grade_point": ""}],
        ),
        snapshot(
            "2024",
            "3",
            [
                {
                    "score": "中等",
                    "credits": "1",
                    "converted_score": "74",
                    "grade_point": "2",
                }
            ],
        ),
        snapshot(
            "2024",
            "16",
            [{"credits": "1", "converted_score": "74.01", "grade_point": "2"}],
        ),
        snapshot(
            "2024",
            "16",
            [{"credits": "1", "converted_score": "100", "grade_point": "4"}],
        ),
    ]

    result = calculate_academic_year_weighted_averages(snapshots)

    assert result == [
        {
            "xnm": "2024",
            "year_name": "2024-2025",
            "year_number": 2,
            "weighted_average": 74.01,
            "included_credits": 2.0,
            "included_course_count": 2,
        }
    ]


def test_shared_webvpn_cookie_never_seeds_jwxt_session_cookie():
    from app.modules.edu_schedule.services.client import JWXTClient

    client = JWXTClient(
        _client_config(
            "JSESSIONID=student-session; route=sticky; _webvpn_key=vpn-key; "
            "webvpn_username=vpn-user; SERVERID=edge"
        )
    )
    session = requests.Session()

    client._prepare_webvpn(session)

    cookies = {(item.domain, item.name): item.value for item in session.cookies}
    jwxt_domain = "jwxt.webvpn.synu.edu.cn"
    assert (jwxt_domain, "JSESSIONID") not in cookies
    assert (jwxt_domain, "route") not in cookies
    assert cookies[(jwxt_domain, "_webvpn_key")] == "vpn-key"
    assert cookies[(jwxt_domain, "webvpn_username")] == "vpn-user"


def test_jwxt_login_clears_parent_domain_session_cookies():
    from app.modules.edu_schedule.services.client import JWXTClient

    client = JWXTClient(_client_config())
    session = requests.Session()
    session.cookies.set("JSESSIONID", "parent-session", domain=".synu.edu.cn", path="/")
    session.cookies.set("route", "parent-route", domain=".webvpn.synu.edu.cn", path="/")
    session.cookies.set("unrelated", "keep", domain=".synu.edu.cn", path="/")

    client._clear_jwxt_session_cookies(session)

    remaining_names = {cookie.name for cookie in session.cookies}
    assert "JSESSIONID" not in remaining_names
    assert "route" not in remaining_names
    assert "unrelated" in remaining_names


def test_empty_grade_payload_cannot_establish_student_identity():
    from app.modules.edu_schedule.services.client import ScheduleAuthError
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    with pytest.raises(ScheduleAuthError):
        EduScheduleService._validate_grade_identity({"items": []}, "stu_demo_2026")

    with pytest.raises(ScheduleAuthError):
        EduScheduleService._validate_grade_identity(
            {"items": [{"xh": "stu_demo_2026"}, {"xh": ""}]},
            "stu_demo_2026",
        )


def test_official_gpa_request_reuses_session_and_exact_endpoint():
    from app.modules.edu_schedule.services.client import JWXTClient

    client = JWXTClient(_client_config())
    authenticated_session = object()
    calls = []

    class Response:
        status_code = 200
        url = "https://jwxt.webvpn.synu.edu.cn/jwglxt/xsxy/xsxyqk_cxXsxyqkIndex.html"
        text = "<div>当前所有课程 平均学分绩点（GPA）：3.23</div>"
        headers = {"Content-Type": "text/html; charset=UTF-8"}

    def fake_request(session, method, url, **kwargs):
        calls.append((session, method, url, kwargs))
        return Response()

    client._request = fake_request

    assert client._query_grade_overview(authenticated_session) == Decimal("3.23")
    assert calls[0][0] is authenticated_session
    assert calls[0][1] == "GET"
    assert calls[0][2].endswith(
        "/jwglxt/xsxy/xsxyqk_cxXsxyqkIndex.html?gnmkdm=N105515&layout=default"
    )
    assert calls[0][3]["allow_redirects"] is True


def test_grade_refresh_persists_official_overview_and_exposes_status(
    app,
    auth_client,
    seed_user,
    monkeypatch,
):
    from app.modules.edu_schedule.services import schedule_service
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    counters = {"official": 0, "closed": 0}

    class FakeFetchResult:
        payload = _all_grade_payload()

        def fetch_official_gpa(self):
            counters["official"] += 1
            return Decimal("3.23")

        def close(self):
            counters["closed"] += 1

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_all_grades_authenticated(self, username, password):
            assert username == "stu_demo_2026"
            return FakeFetchResult()

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)
    monkeypatch.setattr(schedule_service, "_EDU_UPSTREAM_TASK_CONCURRENCY", 3)
    monkeypatch.setattr(
        schedule_service.SystemConfigService,
        "get_edu_schedule_config",
        staticmethod(lambda: {"enabled": True, "store_user_credentials": True}),
    )

    refresh_id = "overview-official-refresh"
    with app.app_context():
        result = EduScheduleService.query_grade_terms(
            int(seed_user["id"]),
            [],
            username="stu_demo_2026",
            password="DemoSecret123!",
            remember=True,
            refresh_id=refresh_id,
        )

    assert counters["official"] == 1
    assert result["grade_overview"]["display_gpa"] == 3.23
    assert result["grade_overview"]["source"] == "official"
    assert result["grade_overview"]["is_cached"] is False
    assert result["academic_year_averages"] == [
        {
            "xnm": "2025",
            "year_name": "2025-2026",
            "year_number": 2,
            "weighted_average": 85.0,
            "included_credits": 2.0,
            "included_course_count": 1,
        },
        {
            "xnm": "2024",
            "year_name": "2024-2025",
            "year_number": 1,
            "weighted_average": 95.0,
            "included_credits": 4.0,
            "included_course_count": 1,
        },
    ]

    with app.app_context():
        from app.core.extensions import db
        from app.models.edu_schedule import EduGradeOverviewSnapshot

        current = EduGradeOverviewSnapshot.query.filter_by(
            user_id=int(seed_user["id"]),
            refresh_id=refresh_id,
        ).one()
        db.session.add(
            EduGradeOverviewSnapshot(
                user_id=int(seed_user["id"]),
                refresh_id="future-overview-without-grade-batch",
                refresh_order=int(current.refresh_order or 0) + 1,
                jwxt_account_key=current.jwxt_account_key,
                official_gpa=Decimal("4.99"),
                calculated_gpa=Decimal("4.99"),
                source="official",
            )
        )
        db.session.commit()

    status = auth_client.get("/api/edu-schedule/status").get_json()["data"]
    assert counters["official"] == 1
    assert status["grade_overview"]["display_gpa"] == 3.23
    assert status["grade_overview"]["refresh_id"] == refresh_id
    assert status["academic_year_averages"] == result["academic_year_averages"]


def test_grade_refresh_keeps_old_official_value_when_new_official_request_fails(
    app,
    seed_user,
    monkeypatch,
):
    from app.modules.edu_schedule.services import schedule_service
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    fetch_count = {"value": 0}

    class FakeFetchResult:
        def __init__(self, payload, official_gpa=None):
            self.payload = payload
            self.official_gpa = official_gpa

        def fetch_official_gpa(self):
            if self.official_gpa is None:
                raise requests.exceptions.Timeout("官方 GPA 页面暂不可用")
            return self.official_gpa

        def close(self):
            return None

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_all_grades_authenticated(self, username, password):
            fetch_count["value"] += 1
            if fetch_count["value"] == 1:
                return FakeFetchResult(_all_grade_payload(), Decimal("3.23"))
            payload = _all_grade_payload(grade_point="2.00")
            if fetch_count["value"] == 3:
                for row in payload["items"]:
                    row["jd"] = ""
                    row["xfjd"] = ""
            return FakeFetchResult(payload)

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)
    monkeypatch.setattr(schedule_service, "_EDU_UPSTREAM_TASK_CONCURRENCY", 1)
    monkeypatch.setattr(
        schedule_service.SystemConfigService,
        "get_edu_schedule_config",
        staticmethod(lambda: {"enabled": True, "store_user_credentials": True}),
    )

    with app.app_context():
        from app.core.extensions import db
        from app.models.edu_schedule import EduGradeOverviewSnapshot

        EduGradeOverviewSnapshot.query.filter_by(user_id=int(seed_user["id"])).delete()
        db.session.commit()
        EduScheduleService.query_grade_terms(
            int(seed_user["id"]),
            [],
            username="stu_demo_2026",
            password="DemoSecret123!",
            refresh_id="overview-cache-seed-refresh",
        )
        calculated_result = EduScheduleService.query_grade_terms(
            int(seed_user["id"]),
            [],
            username="stu_demo_2026",
            password="DemoSecret123!",
            refresh_id="overview-calculated-refresh",
        )
        result = EduScheduleService.query_grade_terms(
            int(seed_user["id"]),
            [],
            username="stu_demo_2026",
            password="DemoSecret123!",
            refresh_id="overview-unavailable-refresh",
        )
        overview_count = app.extensions["sqlalchemy"].session.execute(
            text(
                "SELECT COUNT(1) FROM edu_grade_overview_snapshots "
                "WHERE user_id = :user_id AND refresh_id = :refresh_id"
            ),
            {"user_id": int(seed_user["id"]), "refresh_id": "overview-calculated-refresh"},
        ).scalar()
        unavailable_source = app.extensions["sqlalchemy"].session.execute(
            text(
                "SELECT source FROM edu_grade_overview_snapshots "
                "WHERE user_id = :user_id AND refresh_id = :refresh_id"
            ),
            {"user_id": int(seed_user["id"]), "refresh_id": "overview-unavailable-refresh"},
        ).scalar()

    assert calculated_result["grade_overview"]["calculated_gpa"] == 2.33
    assert result["grade_overview"]["display_gpa"] == 3.23
    assert result["grade_overview"]["calculated_gpa"] is None
    assert result["grade_overview"]["is_cached"] is True
    assert result["grade_overview"]["latest_refresh_id"] == "overview-unavailable-refresh"
    assert overview_count == 1
    assert unavailable_source == "unavailable"


@pytest.mark.parametrize("invalid_kind", ["identity", "truncated", "missing_term"])
def test_invalid_grade_payload_does_not_persist_refresh(
    app,
    seed_user,
    monkeypatch,
    invalid_kind,
):
    from app.modules.edu_schedule.services import schedule_service
    from app.modules.edu_schedule.services.client import ScheduleAuthError, ScheduleClientError
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    payload = _all_grade_payload(
        student_no="another-student" if invalid_kind == "identity" else "stu_demo_2026"
    )
    if invalid_kind == "truncated":
        payload["totalResult"] = len(payload["items"]) + 1
    if invalid_kind == "missing_term":
        payload["items"][1]["xnm"] = ""

    class FakeFetchResult:
        def __init__(self):
            self.payload = payload

        def fetch_official_gpa(self):
            raise AssertionError("身份校验失败后不应查询官方 GPA")

        def close(self):
            return None

    class FakeJWXTClient:
        def __init__(self, config):
            self.config = config

        def fetch_all_grades_authenticated(self, username, password):
            return FakeFetchResult()

    monkeypatch.setattr(schedule_service, "JWXTClient", FakeJWXTClient)
    monkeypatch.setattr(schedule_service, "_EDU_UPSTREAM_TASK_CONCURRENCY", 1)
    monkeypatch.setattr(
        schedule_service.SystemConfigService,
        "get_edu_schedule_config",
        staticmethod(lambda: {"enabled": True, "store_user_credentials": True}),
    )

    refresh_id = f"overview-{invalid_kind}-refresh"
    expected_error = ScheduleAuthError if invalid_kind == "identity" else ScheduleClientError
    with app.app_context(), pytest.raises(expected_error):
        EduScheduleService.query_grade_terms(
            int(seed_user["id"]),
            [],
            username="stu_demo_2026",
            password="DemoSecret123!",
            refresh_id=refresh_id,
        )

    with app.app_context():
        grade_count = app.extensions["sqlalchemy"].session.execute(
            text("SELECT COUNT(1) FROM edu_grade_snapshots WHERE refresh_id = :refresh_id"),
            {"refresh_id": refresh_id},
        ).scalar()
        overview_count = app.extensions["sqlalchemy"].session.execute(
            text("SELECT COUNT(1) FROM edu_grade_overview_snapshots WHERE refresh_id = :refresh_id"),
            {"refresh_id": refresh_id},
        ).scalar()

    assert grade_count == 0
    assert overview_count == 0


def test_rebinding_account_hides_old_grade_cache_and_recent_task(app):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account_a = f"grade_a_{suffix}"
    account_b = f"grade_b_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_rebind_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account_a, "AccountASecret123!")

        raw_payload = _all_grade_payload(student_no=account_a)
        raw_payload["items"] = raw_payload["items"][:1]
        raw_payload["items"][0]["kcmc"] = "旧账号课程"
        normalized = normalize_grade_payload(raw_payload)
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2024",
            "12",
            normalized,
            raw_payload,
            username=account_a,
            password="AccountASecret123!",
            refresh_id="account-a-refresh",
        )
        db.session.add(
            EduGradeOverviewSnapshot(
                user_id=user_id,
                refresh_id="account-a-refresh",
                jwxt_account_key=EduScheduleService.account_key(account_a),
                official_gpa=Decimal("3.50"),
                calculated_gpa=Decimal("3.40"),
                source="official",
            )
        )
        db.session.commit()

        task = EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )
        EduScheduleService.save_credentials(user_id, account_b, "AccountBSecret123!")

        assert EduScheduleService.list_grade_snapshots(user_id) == []
        assert EduScheduleService.get_grade_overview(user_id) is None
        assert EduScheduleQueryTaskService.list_recent(user_id, kind="grades") == []
        with pytest.raises(ValueError):
            EduScheduleQueryTaskService.get(task["task_id"], user_id)
        with pytest.raises(ValueError):
            EduScheduleQueryTaskService.cancel(task["task_id"], user_id)

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["username"] = f"grade_rebind_{suffix}"
        session["is_admin"] = True
        session["session_version"] = 0

    status = client.get("/api/edu-schedule/status").get_json()["data"]
    assert status["grade_snapshots"] == []
    assert status["grade_overview"] is None
    assert status["recent_tasks"]["grades"] is None
    assert "旧账号课程" not in str(status)

    with app.app_context():
        EduScheduleService.delete_credentials(user_id)
        stored_credentials = db.session.execute(
            text(
                "SELECT jwxt_username_ciphertext, jwxt_password_ciphertext "
                "FROM edu_grade_snapshots WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        ).fetchone()
    assert stored_credentials == (None, None)
