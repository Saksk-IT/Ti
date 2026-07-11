# -*- coding: utf-8 -*-
"""独立数据库备份 sidecar 调度器。"""

from __future__ import annotations

import logging
import os
import signal
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from croniter import croniter

from app import create_app
from app.core.extensions import db
from app.modules.admin.services.backup_config_service import BackupConfigService
from app.modules.admin.services.backup_job_service import BackupJobService


logger = logging.getLogger(__name__)
_DEFAULT_TIMEZONE = "Asia/Shanghai"
_DEFAULT_POLL_SECONDS = 60
_MIN_POLL_SECONDS = 5
_MAX_POLL_SECONDS = 3600


def _safe_log_error(stage: str, error: Exception) -> None:
    logger.error("备份调度失败 stage=%s error_type=%s", stage, type(error).__name__)


def latest_due_schedule_slot(
    cron_expression: str,
    timezone_name: str,
    now: datetime,
) -> str:
    """计算不晚于 now 的最新 cron 时间槽，并规范化为 UTC 分钟字符串。"""
    zone = ZoneInfo(str(timezone_name))
    instant = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    local_minute = instant.astimezone(zone).replace(second=0, microsecond=0)
    expression = str(cron_expression or "").strip()
    if not croniter.is_valid(expression):
        raise ValueError("cron_expression 格式无效")
    if croniter.match(expression, local_minute):
        due = local_minute
    else:
        due = croniter(expression, local_minute).get_prev(datetime)
    utc_due = due.astimezone(timezone.utc).replace(second=0, microsecond=0)
    return utc_due.isoformat(timespec="seconds").replace("+00:00", "Z")


def _poll_seconds(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = _DEFAULT_POLL_SECONDS
    return max(_MIN_POLL_SECONDS, min(parsed, _MAX_POLL_SECONDS))


class BackupScheduler:
    """串行恢复、创建到期任务并执行最旧队列任务。"""

    def __init__(
        self,
        *,
        job_service: Optional[Any] = None,
        config_service: Any = BackupConfigService,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        timezone_name: Optional[str] = None,
        poll_seconds: Optional[int] = None,
    ):
        self._job_service = job_service or BackupJobService()
        self._config_service = config_service
        self._clock = clock
        self._timezone_name = timezone_name
        self._configured_poll_seconds = poll_seconds

    def _timezone(self) -> str:
        return str(
            self._timezone_name
            or os.environ.get("TZ")
            or _DEFAULT_TIMEZONE
        )

    def _poll_interval(self) -> int:
        value = (
            self._configured_poll_seconds
            if self._configured_poll_seconds is not None
            else os.environ.get(
                "BACKUP_SCHEDULER_POLL_SECONDS", _DEFAULT_POLL_SECONDS
            )
        )
        return _poll_seconds(value)

    def _schedule_due_job(self) -> None:
        try:
            config = dict(self._config_service.get_config())
            if not config.get("schedule_enabled"):
                return
            slot = latest_due_schedule_slot(
                str(config.get("cron_expression") or ""),
                self._timezone(),
                self._clock(),
            )
            self._job_service.create_scheduled_job(slot)
        except Exception as exc:
            _safe_log_error("schedule", exc)

    def run_once(self) -> None:
        self._job_service.recover_stale_jobs()
        try:
            self._job_service.retry_deleting_jobs()
        except Exception as exc:
            _safe_log_error("retry_deleting", exc)
        self._schedule_due_job()
        queued_id = self._job_service.oldest_queued_job_id()
        if queued_id is not None:
            self._job_service.execute_job(str(queued_id))

    def run(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                self.run_once()
            except Exception as exc:
                _safe_log_error("run_once", exc)
            finally:
                db.session.remove()
            if stop_event.wait(self._poll_interval()):
                break


def _install_signal_handlers(stop_event: threading.Event) -> None:
    def request_stop(_signum: int, _frame: Any) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)


def main() -> None:
    stop_event = threading.Event()
    _install_signal_handlers(stop_event)
    app = create_app()
    with app.app_context():
        BackupScheduler().run(stop_event)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _safe_log_error("startup", exc)
        raise SystemExit(1)
