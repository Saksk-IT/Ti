# -*- coding: utf-8 -*-
"""数据库备份 sidecar 调度器测试。"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

import pytest
from flask import Flask

import app as app_module
from app.core.extensions import db
from app.models.backup import BackupJob
from app.modules.admin.services.backup_config_service import BackupConfigError
from app.modules.admin.services.backup_job_service import BackupJobService
from app.tasks.backup_scheduler import BackupScheduler, latest_due_schedule_slot


class _ConfigService:
    def __init__(self, config=None, error=None):
        self._config = dict(config or {})
        self._error = error

    def get_config(self):
        if self._error is not None:
            raise self._error
        return dict(self._config)


class _JobService:
    def __init__(self, queued_id=None):
        self.calls = []
        self.queued_id = queued_id

    def recover_stale_jobs(self):
        self.calls.append(("recover", None))
        return 0

    def retry_deleting_jobs(self):
        self.calls.append(("retry_deleting", None))
        return []

    def create_scheduled_job(self, schedule_slot):
        self.calls.append(("create", schedule_slot))
        return object()

    def oldest_queued_job_id(self):
        self.calls.append(("oldest", None))
        return self.queued_id

    def execute_job(self, job_id):
        self.calls.append(("execute", job_id))
        return object()


@pytest.fixture
def clean_scheduler_jobs(app):
    with app.app_context():
        BackupJob.query.delete(synchronize_session=False)
        db.session.commit()
        yield
        db.session.rollback()
        BackupJob.query.delete(synchronize_session=False)
        db.session.commit()


def test_latest_due_schedule_slot_is_stable_for_same_cron_minute():
    at_slot = datetime(2026, 7, 10, 18, 0, 0, tzinfo=timezone.utc)
    later_in_slot = datetime(2026, 7, 10, 18, 0, 59, tzinfo=timezone.utc)

    first = latest_due_schedule_slot("0 2 * * *", "Asia/Shanghai", at_slot)
    second = latest_due_schedule_slot(
        "0 2 * * *", "Asia/Shanghai", later_in_slot
    )

    assert first == "2026-07-10T18:00:00Z"
    assert second == first


def test_scheduled_job_creation_is_idempotent_across_service_instances(
    app, clean_scheduler_jobs
):
    with app.app_context():
        first = BackupJobService().create_scheduled_job(
            "2026-07-10T18:00:00Z"
        )
        second = BackupJobService().create_scheduled_job(
            "2026-07-10T18:00:00Z"
        )

        assert first is not None
        assert second is not None
        assert second.id == first.id
        assert first.trigger == "scheduled"
        assert first.active_slot == "global"
        assert BackupJob.query.filter_by(
            schedule_slot="2026-07-10T18:00:00Z"
        ).count() == 1


def test_scheduled_slot_retries_after_active_manual_job_finishes(
    app, clean_scheduler_jobs
):
    with app.app_context():
        service = BackupJobService()
        manual = service.create_manual_job(created_by=7)

        skipped = service.create_scheduled_job("2026-07-10T18:00:00Z")

        assert skipped is None
        assert BackupJob.query.filter_by(trigger="scheduled").count() == 0

        manual.status = "completed"
        manual.active_slot = None
        db.session.commit()

        retried = service.create_scheduled_job("2026-07-10T18:00:00Z")

        assert retried is not None
        assert retried.trigger == "scheduled"
        assert retried.schedule_slot == "2026-07-10T18:00:00Z"


def test_run_once_recovers_schedules_then_executes_oldest_queue():
    service = _JobService(queued_id="manual-oldest")
    config = _ConfigService(
        {
            "schedule_enabled": True,
            "cron_expression": "0 2 * * *",
        }
    )
    scheduler = BackupScheduler(
        job_service=service,
        config_service=config,
        clock=lambda: datetime(2026, 7, 10, 18, 3, tzinfo=timezone.utc),
        timezone_name="Asia/Shanghai",
    )

    scheduler.run_once()

    assert service.calls == [
        ("recover", None),
        ("retry_deleting", None),
        ("create", "2026-07-10T18:00:00Z"),
        ("oldest", None),
        ("execute", "manual-oldest"),
    ]


def test_run_once_executes_manual_queue_when_schedule_is_disabled():
    service = _JobService(queued_id="manual-job")
    scheduler = BackupScheduler(
        job_service=service,
        config_service=_ConfigService({"schedule_enabled": False}),
    )

    scheduler.run_once()

    assert service.calls == [
        ("recover", None),
        ("retry_deleting", None),
        ("oldest", None),
        ("execute", "manual-job"),
    ]


def test_incomplete_schedule_config_is_logged_without_secret_and_queue_continues(
    caplog,
):
    service = _JobService(queued_id="manual-job")
    scheduler = BackupScheduler(
        job_service=service,
        config_service=_ConfigService(
            error=BackupConfigError("credential secret-value is incomplete")
        ),
    )

    with caplog.at_level(logging.ERROR):
        scheduler.run_once()

    assert service.calls == [
        ("recover", None),
        ("retry_deleting", None),
        ("oldest", None),
        ("execute", "manual-job"),
    ]
    assert "BackupConfigError" in caplog.text
    assert "secret-value" not in caplog.text


def test_run_clamps_poll_interval_and_stops_when_event_requests_it(monkeypatch):
    service = _JobService()
    scheduler = BackupScheduler(
        job_service=service,
        config_service=_ConfigService({"schedule_enabled": False}),
    )
    waits = []

    class _StopEvent:
        def is_set(self):
            return False

        def wait(self, seconds):
            waits.append(seconds)
            return True

    monkeypatch.setenv("BACKUP_SCHEDULER_POLL_SECONDS", "1")

    scheduler.run(_StopEvent())

    assert waits == [5]
    assert service.calls == [
        ("recover", None),
        ("retry_deleting", None),
        ("oldest", None),
    ]


def test_run_logs_only_error_type_and_continues_to_stop(caplog):
    class _FailingJobService(_JobService):
        def recover_stale_jobs(self):
            raise RuntimeError("database-password=secret-value")

    scheduler = BackupScheduler(
        job_service=_FailingJobService(),
        config_service=_ConfigService({"schedule_enabled": False}),
        poll_seconds=3601,
    )

    class _StopEvent:
        def is_set(self):
            return False

        def wait(self, seconds):
            assert seconds == 3600
            return True

    with caplog.at_level(logging.ERROR):
        scheduler.run(_StopEvent())

    assert "RuntimeError" in caplog.text
    assert "secret-value" not in caplog.text


def test_run_finishes_inflight_backup_after_stop_is_requested(app):
    stop_event = threading.Event()

    class _StoppingJobService(_JobService):
        def execute_job(self, job_id):
            result = super().execute_job(job_id)
            stop_event.set()
            return result

    service = _StoppingJobService(queued_id="inflight-job")
    scheduler = BackupScheduler(
        job_service=service,
        config_service=_ConfigService({"schedule_enabled": False}),
        poll_seconds=60,
    )

    with app.app_context():
        scheduler.run(stop_event)

    assert stop_event.is_set()
    assert service.calls == [
        ("recover", None),
        ("retry_deleting", None),
        ("oldest", None),
        ("execute", "inflight-job"),
    ]


def test_backup_sidecar_mode_skips_writable_runtime_dirs_and_file_logger(
    tmp_path, monkeypatch
):
    application = Flask("backup-sidecar-test")
    application.config.update(
        DEBUG=False,
        TESTING=False,
        LOG_DIR=str(tmp_path / "logs"),
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
        DATABASE_PATH=str(tmp_path / "instance" / "database.db"),
        LOG_LEVEL=logging.INFO,
        LOG_MAX_BYTES=1024,
        LOG_BACKUP_COUNT=1,
    )
    monkeypatch.setenv("TI_BACKUP_SCHEDULER", "1")

    def reject_file_logger(*_args, **_kwargs):
        raise AssertionError("backup sidecar must not create a file logger")

    monkeypatch.setattr(app_module, "RotatingFileHandler", reject_file_logger)

    app_module._ensure_directories(application)
    app_module._setup_logging(application)

    assert not (tmp_path / "logs").exists()
    assert not (tmp_path / "uploads").exists()


def test_backup_sidecar_does_not_start_web_background_threads(monkeypatch):
    from app.core import tasks as task_module

    calls = []
    monkeypatch.setattr(
        task_module, "start_background_tasks", lambda app: calls.append(app)
    )
    application = object()

    monkeypatch.setenv("TI_BACKUP_SCHEDULER", "1")
    app_module._start_background_tasks(application)
    assert calls == []

    monkeypatch.delenv("TI_BACKUP_SCHEDULER")
    app_module._start_background_tasks(application)
    assert calls == [application]


def test_create_app_uses_minimal_runtime_in_backup_sidecar_mode(
    tmp_path, monkeypatch
):
    readonly_data = tmp_path / "readonly-data"
    readonly_data.mkdir()
    readonly_data.chmod(0o555)
    testing_config = app_module.config["testing"]
    monkeypatch.setattr(testing_config, "DATA_DIR", str(readonly_data))
    monkeypatch.setattr(
        testing_config, "UPLOAD_FOLDER", str(readonly_data / "uploads")
    )
    monkeypatch.setattr(testing_config, "LOG_DIR", str(readonly_data / "logs"))
    monkeypatch.setattr(
        testing_config,
        "DATABASE_PATH",
        str(readonly_data / "instance" / "test.db"),
    )
    monkeypatch.setattr(
        testing_config,
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///:memory:",
    )
    monkeypatch.setenv("TI_BACKUP_SCHEDULER", "1")

    try:
        application = app_module.create_app("testing")
    finally:
        readonly_data.chmod(0o755)

    assert not any(
        rule.rule.startswith("/admin")
        for rule in application.url_map.iter_rules()
    )


def test_run_once_retries_deleting_jobs_before_scheduling():
    service = _JobService()
    scheduler = BackupScheduler(
        job_service=service,
        config_service=_ConfigService({"schedule_enabled": False}),
    )

    scheduler.run_once()

    assert service.calls == [
        ("recover", None),
        ("retry_deleting", None),
        ("oldest", None),
    ]
