# -*- coding: utf-8 -*-
"""成绩刷新批次一致性回归测试。"""

import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text


def _normalized_payload(account: str, course_name: str, score: float) -> dict:
    return {
        "term": {
            "xnm": "2024",
            "xqm": "12",
            "year_name": "2024-2025",
            "label": "2024-2025 第2学期",
        },
        "student": {"student_no": account, "name": "测试学生"},
        "grades": [
            {
                "course_name": course_name,
                "credits": 2.0,
                "converted_score": score,
                "grade_point": 3.0,
            }
        ],
    }


def test_recent_grade_tasks_use_refresh_order_before_completion_time(monkeypatch):
    from app.modules.edu_schedule.services import query_tasks

    states = {
        "older": {
            "task_id": "older",
            "owner_user_id": 7,
            "kind": "grades",
            "refresh_order": 100,
            "created_at": "2026-07-15T10:00:00+00:00",
            "updated_at": "2026-07-15T10:10:00+00:00",
        },
        "newer": {
            "task_id": "newer",
            "owner_user_id": 7,
            "kind": "grades",
            "refresh_order": 200,
            "created_at": "2026-07-15T10:01:00+00:00",
            "updated_at": "2026-07-15T10:02:00+00:00",
        },
    }
    monkeypatch.setattr(query_tasks, "_load_user_task_ids", lambda _user_id: ["older", "newer"])
    monkeypatch.setattr(query_tasks, "_load_state", states.get)
    monkeypatch.setattr(query_tasks, "grade_task_matches_bound_account", lambda *_args: True)

    recent = query_tasks.EduScheduleQueryTaskService.list_recent(7, kind="grades")

    assert [item["task_id"] for item in recent] == ["newer", "older"]
    assert "refresh_order" not in recent[0]


def test_zero_order_batch_keeps_older_official_gpa_cache(app, seed_user):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot
    from app.modules.edu_schedule.services.grade_snapshot_batch import (
        summarize_grade_snapshot_batch,
    )
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account_key = EduScheduleService.account_key(f"zero_order_{suffix}")
    older_refresh = f"older-official-{suffix}"
    current_refresh = f"current-calculated-{suffix}"
    with app.app_context():
        db.session.add_all(
            [
                EduGradeOverviewSnapshot(
                    user_id=int(seed_user["id"]),
                    refresh_id=older_refresh,
                    refresh_order=0,
                    jwxt_account_key=account_key,
                    official_gpa=Decimal("3.23"),
                    calculated_gpa=Decimal("3.00"),
                    source="official",
                    fetched_at=datetime(2026, 7, 14, 10, 0, 0),
                ),
                EduGradeOverviewSnapshot(
                    user_id=int(seed_user["id"]),
                    refresh_id=current_refresh,
                    refresh_order=0,
                    jwxt_account_key=account_key,
                    calculated_gpa=Decimal("2.50"),
                    source="calculated",
                    fetched_at=datetime(2026, 7, 15, 10, 0, 0),
                ),
            ]
        )
        db.session.commit()
        snapshots = [
            {
                "id": 1,
                "refresh_id": current_refresh,
                "refresh_order": 0,
                "fetched_at": "2026-07-15T10:00:00",
                "payload": _normalized_payload("ignored", "当前课程", 80.0),
            }
        ]
        overview, _year_averages = summarize_grade_snapshot_batch(
            int(seed_user["id"]),
            account_key,
            snapshots,
        )

    assert overview["display_gpa"] == 3.23
    assert overview["calculated_gpa"] == 2.5
    assert overview["is_cached"] is True
    assert overview["latest_refresh_id"] == current_refresh


def test_load_grade_refresh_batch_excludes_newer_batch(app, seed_user):
    from app.core.extensions import db
    from app.models.edu_schedule import EduGradeOverviewSnapshot, EduGradeSnapshot
    from app.modules.edu_schedule.services.grade_snapshot_batch import load_grade_refresh_batch
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"batch_exact_{suffix}"
    account_key = EduScheduleService.account_key(account)
    older_refresh = f"batch-a-{suffix}"
    newer_refresh = f"batch-b-{suffix}"
    with app.app_context():
        for refresh_id, refresh_order, course_name, score, gpa in (
            (older_refresh, 100, "批次 A 课程", 80.0, Decimal("3.10")),
            (newer_refresh, 200, "批次 B 课程", 99.0, Decimal("4.10")),
        ):
            payload = _normalized_payload(account, course_name, score)
            db.session.add(
                EduGradeSnapshot(
                    user_id=int(seed_user["id"]),
                    xnm="2024",
                    xqm="12",
                    refresh_id=refresh_id,
                    refresh_order=refresh_order,
                    jwxt_account_key=account_key,
                    term_label="2024-2025 第2学期",
                    payload_json=json.dumps(payload, ensure_ascii=False),
                    raw_payload_json="{}",
                )
            )
            db.session.add(
                EduGradeOverviewSnapshot(
                    user_id=int(seed_user["id"]),
                    refresh_id=refresh_id,
                    refresh_order=refresh_order,
                    jwxt_account_key=account_key,
                    official_gpa=gpa,
                    calculated_gpa=gpa,
                    source="official",
                )
            )
        db.session.commit()
        snapshots, overview, year_averages = load_grade_refresh_batch(
            int(seed_user["id"]),
            account_key,
            older_refresh,
        )

    assert {item["refresh_id"] for item in snapshots} == {older_refresh}
    assert snapshots[0]["payload"]["grades"][0]["course_name"] == "批次 A 课程"
    assert overview["display_gpa"] == 3.1
    assert overview["latest_refresh_id"] == older_refresh
    assert year_averages[0]["weighted_average"] == 80.0


def test_successful_grade_task_keeps_published_batch_together(app, monkeypatch):
    from app.core.extensions import db
    from app.modules.edu_schedule.services import query_tasks
    from app.modules.edu_schedule.services.schedule_service import EduScheduleService

    suffix = uuid4().hex[:8]
    account = f"task_batch_{suffix}"
    with app.app_context():
        user_id = int(
            db.session.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_admin, has_password_set) "
                    "VALUES (:username, 'test', 1, 1) RETURNING id"
                ),
                {"username": f"task_batch_user_{suffix}"},
            ).scalar()
        )
        db.session.commit()
        EduScheduleService.save_credentials(user_id, account, "BatchSecret123!")
        monkeypatch.setattr(query_tasks, "get_redis_connection", lambda: None)
        task = query_tasks.EduScheduleQueryTaskService.enqueue(
            "grades",
            user_id,
            [],
            autostart=False,
        )

        payload_a = _normalized_payload(account, "批次 A 课程", 80.0)
        snapshot_a = [{"refresh_id": task["task_id"], "payload": payload_a}]
        overview_a = {"display_gpa": 3.1, "latest_refresh_id": task["task_id"]}
        year_a = [{"xnm": "2024", "weighted_average": 80.0}]
        snapshot_b = [{"refresh_id": "newer-batch", "payload": {"grades": []}}]
        overview_b = {"display_gpa": 4.1, "latest_refresh_id": "newer-batch"}
        year_b = [{"xnm": "2024", "weighted_average": 99.0}]

        monkeypatch.setattr(
            EduScheduleService,
            "query_grade_terms",
            staticmethod(
                lambda *_args, **_kwargs: {
                    "results": [payload_a],
                    "snapshots": snapshot_a,
                    "grade_overview": overview_a,
                    "academic_year_averages": year_a,
                    "credential": {},
                }
            ),
        )
        monkeypatch.setattr(
            query_tasks,
            "_task_cached_data",
            lambda *_args, **_kwargs: (snapshot_b, overview_b, year_b),
        )
        result = query_tasks.EduScheduleQueryTaskService.run_task(task["task_id"])

    assert result["status"] == "succeeded"
    assert result["snapshots"] == snapshot_a
    assert result["grade_overview"] == overview_a
    assert result["academic_year_averages"] == year_a
    assert result["results"] == [payload_a]
