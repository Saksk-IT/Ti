# -*- coding: utf-8 -*-
"""成绩查询任务隔离与并发协调测试。"""

import threading
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
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


def test_same_account_password_change_invalidates_pending_grade_task(app, monkeypatch):
    from app.core.extensions import db
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"grade_password_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_password_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "FirstSecret123!")
        first_task = EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )

        EduScheduleService.save_credentials(user_id, account, "SecondSecret123!")
        second_task = EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )

        monkeypatch.setattr(
            EduScheduleService,
            "query_grade_terms",
            staticmethod(lambda *args, **kwargs: pytest.fail("失效任务不应访问教务系统")),
        )
        first_state = EduScheduleQueryTaskService.run_task(first_task["task_id"])

        assert first_task["task_id"] != second_task["task_id"]
        assert first_state["status"] == "cancelled"
        assert EduScheduleQueryTaskService.list_recent(user_id, kind="grades")[0]["task_id"] == second_task["task_id"]


def test_temporary_grade_task_does_not_expose_cache_before_authentication(app):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"grade_temporary_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_temporary_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "CorrectSecret123!")
        raw_payload = _all_grade_payload(student_no=account)
        normalized = normalize_grade_payload(raw_payload)
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2024",
            "12",
            normalized,
            raw_payload,
            username=account,
            password="CorrectSecret123!",
            refresh_id="temporary-cache-refresh",
        )
        db.session.add(
            EduGradeOverviewSnapshot(
                user_id=user_id,
                refresh_id="temporary-cache-refresh",
                jwxt_account_key=EduScheduleService.account_key(account),
                official_gpa=Decimal("3.80"),
                calculated_gpa=Decimal("3.70"),
                source="official",
            )
        )
        db.session.commit()

        task = EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            username=account,
            password="WrongSecret123!",
            remember=False,
            autostart=False,
        )

    assert task["results"] == []
    assert task["snapshots"] == []
    assert task["grade_overview"] is None
    assert task["academic_year_averages"] == []


def test_bound_grade_task_keeps_legacy_null_account_key_cache(app):
    from app.core.extensions import db
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"grade_legacy_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_legacy_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "LegacySecret123!")
        raw_payload = _all_grade_payload(student_no=account)
        raw_payload["items"] = raw_payload["items"][:1]
        raw_payload["items"][0]["kcmc"] = "历史成绩课程"
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2024",
            "12",
            normalize_grade_payload(raw_payload),
            raw_payload,
            username=account,
            password="LegacySecret123!",
            refresh_id=None,
        )
        db.session.execute(
            text(
                "UPDATE edu_grade_snapshots SET jwxt_account_key = NULL, "
                "jwxt_username_ciphertext = NULL, jwxt_password_ciphertext = NULL "
                "WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        )
        db.session.commit()

        task = EduScheduleQueryTaskService.enqueue("grades", user_id, [], autostart=False)

    assert task["snapshots"][0]["payload"]["grades"][0]["course_name"] == "历史成绩课程"
    assert task["academic_year_averages"][0]["weighted_average"] == 95.0


@pytest.mark.parametrize("payload_kind", ["mixed", "other_account"])
def test_legacy_null_account_snapshot_rejects_unverified_payload(app, payload_kind):
    from app.core.extensions import db
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"grade_legacy_safe_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_legacy_safe_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "LegacySafeSecret123!")
        raw_payload = _all_grade_payload(
            student_no="another_student" if payload_kind == "other_account" else account
        )
        normalized = normalize_grade_payload(raw_payload)
        if payload_kind == "mixed":
            raw_payload["items"][1]["xh"] = "another_student"
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2024",
            "12",
            normalized,
            raw_payload,
            username=account,
            password="LegacySafeSecret123!",
            refresh_id=None,
        )
        db.session.execute(
            text("UPDATE edu_grade_snapshots SET jwxt_account_key = NULL WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        db.session.commit()
        snapshots = EduScheduleService.list_grade_snapshots(user_id)

    assert snapshots == []


def test_remembered_inline_grade_credentials_are_not_bound_before_authentication(app, monkeypatch):
    from app.core.extensions import db
    from app.modules.edu_schedule.services.client import ScheduleAuthError
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account_a = f"grade_remember_a_{suffix}"
    account_b = f"grade_remember_b_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_remember_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account_a, "AccountASecret123!")
        task = EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            username=account_b,
            password="WrongSecret123!",
            remember=True,
            autostart=False,
        )
        assert EduScheduleService._bound_account(user_id) == account_a
        assert task["snapshots"] == []

        monkeypatch.setattr(
            EduScheduleService,
            "query_grade_terms",
            staticmethod(lambda *args, **kwargs: (_ for _ in ()).throw(ScheduleAuthError("账号或密码错误"))),
        )
        final_state = EduScheduleQueryTaskService.run_task(task["task_id"])

        assert final_state["status"] == "failed"
        assert final_state["snapshots"] == []
        assert EduScheduleService._bound_account(user_id) == account_a


def test_rebinding_task_state_never_attaches_new_account_cache(app):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account_a = f"grade_state_a_{suffix}"
    account_b = f"grade_state_b_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_state_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account_a, "AccountASecret123!")
        task = EduScheduleQueryTaskService.enqueue("grades", user_id, [], autostart=False)

        EduScheduleService.save_credentials(user_id, account_b, "AccountBSecret123!")
        raw_payload = _all_grade_payload(student_no=account_b)
        raw_payload["items"] = raw_payload["items"][:1]
        raw_payload["items"][0]["kcmc"] = "账号 B 私有课程"
        EduScheduleService._save_grade_snapshot(
            user_id,
            "2024",
            "12",
            normalize_grade_payload(raw_payload),
            raw_payload,
            username=account_b,
            password="AccountBSecret123!",
            refresh_id="account-b-refresh",
        )
        db.session.add(
            EduGradeOverviewSnapshot(
                user_id=user_id,
                refresh_id="account-b-refresh",
                jwxt_account_key=EduScheduleService.account_key(account_b),
                official_gpa=Decimal("4.50"),
                calculated_gpa=Decimal("4.40"),
                source="official",
            )
        )
        db.session.commit()

        cancelled = EduScheduleQueryTaskService.run_task(task["task_id"])
        assert cancelled["status"] == "cancelled"
        assert cancelled["snapshots"] == []
        assert cancelled["grade_overview"] is None

        EduScheduleService.save_credentials(user_id, account_a, "AccountASecret123!")
        restored = EduScheduleQueryTaskService.get(task["task_id"], user_id)

    assert restored["snapshots"] == []
    assert restored["grade_overview"] is None
    assert "账号 B 私有课程" not in str(restored)


def test_cancelled_slow_grade_task_cannot_overwrite_newer_refresh(app, monkeypatch):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.query_tasks import EduScheduleQueryTaskService
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"grade_race_{suffix}"
    first_started = threading.Event()
    release_first = threading.Event()
    first_task_id = {"value": ""}

    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_race_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "RaceSecret123!")

    def fake_query_grade_terms(query_user_id, terms, *, refresh_id=None, **kwargs):
        if refresh_id == first_task_id["value"]:
            first_started.set()
            assert release_first.wait(timeout=3)
            course_name = "已取消的旧刷新"
            official_gpa = Decimal("1.11")
        else:
            course_name = "最新刷新"
            official_gpa = Decimal("4.22")
        raw_payload = _all_grade_payload(student_no=account)
        raw_payload["items"] = raw_payload["items"][:1]
        raw_payload["items"][0]["kcmc"] = course_name
        normalized = normalize_grade_payload(raw_payload)
        EduScheduleService._save_grade_snapshot(
            query_user_id,
            "2024",
            "12",
            normalized,
            raw_payload,
            username=account,
            password="RaceSecret123!",
            refresh_id=refresh_id,
            commit=False,
        )
        db.session.add(
            EduGradeOverviewSnapshot(
                user_id=query_user_id,
                refresh_id=refresh_id,
                jwxt_account_key=EduScheduleService.account_key(account),
                official_gpa=official_gpa,
                calculated_gpa=official_gpa,
                source="official",
            )
        )
        db.session.commit()
        return {
            "results": [normalized],
            "credential": EduScheduleService.credential_status(query_user_id),
            "grade_overview": EduScheduleService.get_grade_overview(query_user_id),
        }

    monkeypatch.setattr(
        EduScheduleService,
        "query_grade_terms",
        staticmethod(fake_query_grade_terms),
    )

    with app.app_context():
        first_task = EduScheduleQueryTaskService.enqueue("grades", user_id, [], autostart=False)
        first_task_id["value"] = first_task["task_id"]

    first_result = {}

    def run_first_task():
        with app.app_context():
            first_result.update(EduScheduleQueryTaskService.run_task(first_task["task_id"]))

    worker = threading.Thread(target=run_first_task)
    worker.start()
    assert first_started.wait(timeout=3)

    with app.app_context():
        EduScheduleQueryTaskService.cancel(first_task["task_id"], user_id)
        second_task = EduScheduleQueryTaskService.enqueue("grades", user_id, [], autostart=False)
        second_result = EduScheduleQueryTaskService.run_task(second_task["task_id"])
    release_first.set()
    worker.join(timeout=3)

    assert not worker.is_alive()
    assert first_result["status"] == "cancelled"
    assert second_result["status"] == "succeeded"
    with app.app_context():
        old_grade_count = db.session.execute(
            text("SELECT COUNT(1) FROM edu_grade_snapshots WHERE refresh_id = :refresh_id"),
            {"refresh_id": first_task["task_id"]},
        ).scalar()
        old_overview_count = db.session.execute(
            text("SELECT COUNT(1) FROM edu_grade_overview_snapshots WHERE refresh_id = :refresh_id"),
            {"refresh_id": first_task["task_id"]},
        ).scalar()
        snapshots = EduScheduleService.list_grade_snapshots(user_id)
        overview = EduScheduleService.get_grade_overview(user_id)

    assert old_grade_count == 0
    assert old_overview_count == 0
    assert snapshots[0]["payload"]["grades"][0]["course_name"] == "最新刷新"
    assert overview["display_gpa"] == 4.22


def test_grade_task_dedupe_uses_redis_across_worker_local_caches(
    app,
    monkeypatch,
    grade_task_redis,
):
    from app.core.extensions import db
    from app.modules.edu_schedule.services import query_tasks
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_dedupe_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(
            user_id,
            f"grade_dedupe_{suffix}",
            "DedupeSecret123!",
        )
        first = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )

        monkeypatch.setattr(query_tasks, "_QUERY_TASKS", {})
        monkeypatch.setattr(query_tasks, "_QUERY_TASK_DEDUPES", {})
        monkeypatch.setattr(query_tasks, "_QUERY_TASK_USER_TASKS", {})
        second = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )

    assert second["task_id"] == first["task_id"]
    assert second["coalesced"] is True


def test_cancelled_redis_task_cannot_be_revived_by_stale_worker_state(
    app,
    monkeypatch,
    grade_task_redis,
):
    from app.core.extensions import db
    from app.modules.edu_schedule.services import query_tasks
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_cas_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(
            user_id,
            f"grade_cas_{suffix}",
            "CasSecret123!",
        )
        task = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )
        stale_state = query_tasks._load_state(task["task_id"])
        query_tasks.EduScheduleQueryTaskService.cancel(task["task_id"], user_id)

        monkeypatch.setattr(
            query_tasks,
            "_QUERY_TASKS",
            {task["task_id"]: stale_state},
        )
        attempted = query_tasks._save_state(
            {
                **stale_state,
                "status": "succeeded",
                "message": "陈旧 worker 不应复活任务",
            }
        )
        persisted = query_tasks._load_state(task["task_id"])

    assert attempted["status"] == "cancelled"
    assert persisted["status"] == "cancelled"


def test_redis_publish_claim_releases_dedupe_for_new_refresh(app, grade_task_redis):
    from app.core.extensions import db
    from app.modules.edu_schedule.services import query_tasks
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_claim_redis_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(
            user_id,
            f"grade_claim_redis_{suffix}",
            "ClaimRedisSecret123!",
        )
        first = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades", user_id, [], autostart=False
        )
        query_tasks._save_state(
            {**query_tasks._load_state(first["task_id"]), "status": "running"}
        )
        assert query_tasks._claim_task_publish(first["task_id"]) is True
        second = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades", user_id, [], autostart=False
        )

    assert second["task_id"] != first["task_id"]
    assert second["coalesced"] is False


def test_binding_change_after_publish_claim_becomes_terminal_failure():
    from app.modules.edu_schedule.services.query_task_runtime import (
        stop_for_binding_change,
    )

    saved_states = []

    def save_state(state):
        saved_states.append(dict(state))
        if len(saved_states) == 1:
            return {**state, "status": "running", "publish_claimed": True}
        return dict(state)

    result = stop_for_binding_change(
        {"task_id": "claimed-task", "status": "running"},
        message="绑定已变更",
        finished_at="2026-07-15T00:00:00+00:00",
        save_state=save_state,
    )

    assert result["status"] == "failed"
    assert result["snapshots"] == []


def test_grade_publish_claim_wins_over_late_cancel(app):
    from app.core.extensions import db
    from app.modules.edu_schedule.services import query_tasks
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_claim_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(
            user_id,
            f"grade_claim_{suffix}",
            "ClaimSecret123!",
        )
        task = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )
        running = query_tasks._save_state(
            {
                **query_tasks._load_state(task["task_id"]),
                "status": "running",
            }
        )
        assert query_tasks._claim_task_publish(task["task_id"]) is True
        replacement = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )

        cancel_result = query_tasks.EduScheduleQueryTaskService.cancel(
            task["task_id"],
            user_id,
        )
        persisted = query_tasks._load_state(task["task_id"])
        finished = query_tasks._save_state({**running, "status": "succeeded"})

    assert cancel_result["status"] == "running"
    assert replacement["task_id"] != task["task_id"]
    assert persisted["publish_claimed"] is True
    assert finished["status"] == "succeeded"


def test_newer_grade_refresh_order_wins_even_when_older_finishes_later(app):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot
    from app.modules.edu_schedule.services.grade_parser import normalize_grade_payload
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"grade_order_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"grade_order_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "OrderSecret123!")

        for refresh_id, refresh_order, course_name, official_gpa in (
            ("older-request", 100, "旧请求晚完成", Decimal("1.50")),
            ("newer-request", 200, "新请求结果", Decimal("4.50")),
        ):
            raw_payload = _all_grade_payload(student_no=account)
            raw_payload["items"] = raw_payload["items"][:1]
            raw_payload["items"][0]["kcmc"] = course_name
            EduScheduleService._save_grade_snapshot(
                user_id,
                "2024",
                "12",
                normalize_grade_payload(raw_payload),
                raw_payload,
                username=account,
                password="OrderSecret123!",
                refresh_id=refresh_id,
                refresh_order=refresh_order,
                commit=False,
            )
            db.session.add(
                EduGradeOverviewSnapshot(
                    user_id=user_id,
                    refresh_id=refresh_id,
                    refresh_order=refresh_order,
                    jwxt_account_key=EduScheduleService.account_key(account),
                    official_gpa=official_gpa,
                    calculated_gpa=official_gpa,
                    source="official",
                )
            )
        db.session.commit()
        db.session.execute(
            text(
                "UPDATE edu_grade_snapshots SET fetched_at = CASE refresh_id "
                "WHEN 'older-request' THEN '2041-01-01' ELSE '2040-01-01' END "
                "WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        )
        db.session.execute(
            text(
                "UPDATE edu_grade_overview_snapshots SET fetched_at = CASE refresh_id "
                "WHEN 'older-request' THEN '2041-01-01' ELSE '2040-01-01' END "
                "WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        )
        db.session.commit()

        snapshots = EduScheduleService.list_grade_snapshots(user_id)
        overview = EduScheduleService.get_grade_overview(user_id)

    assert snapshots[0]["refresh_id"] == "newer-request"
    assert snapshots[0]["payload"]["grades"][0]["course_name"] == "新请求结果"
    assert overview["refresh_id"] == "newer-request"
    assert overview["display_gpa"] == 4.5


def test_grades_page_contains_responsive_cumulative_gpa_card():
    html = Path("app/modules/edu_schedule/templates/edu_schedule/grades.html").read_text(encoding="utf-8")

    assert "当前所有课程平均学分绩点（GPA）" in html
    assert 'id="gradeOverviewValue"' in html
    assert 'id="gradeOverviewSource"' in html
    assert "function renderGradeOverview" in html
    assert "gradeOverviewValue.textContent" in html
    assert "每学年学分加权平均分" in html
    assert 'id="academicYearAverages"' in html
    assert "function renderAcademicYearAverages" in html
