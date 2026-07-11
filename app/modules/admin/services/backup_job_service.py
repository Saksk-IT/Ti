# -*- coding: utf-8 -*-
"""备份任务创建、认领、执行与留存编排。"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.core.extensions import db
from app.models.backup import BackupJob
from app.modules.admin.services.backup_archive_service import BackupArchiveService
from app.modules.admin.services.backup_config_service import (
    BackupConfigService,
    acquire_storage_identity_lock,
)
from app.modules.admin.services.backup_storage_service import BackupStorageService


logger = logging.getLogger(__name__)
_ACTIVE_STATUSES = ("queued", "running")
_SAFE_FAILURE_SUMMARY = "备份执行失败，请查看服务器日志"
_STALE_FAILURE_SUMMARY = "备份执行租约已过期，请重新创建备份"
_DEFAULT_LEASE_SECONDS = 3600


class BackupJobError(RuntimeError):
    """备份任务状态或访问边界错误。"""


class BackupJobNotFoundError(BackupJobError):
    """备份任务不存在。"""


class BackupJobConflictError(BackupJobError):
    """备份任务存在，但当前状态不允许执行请求的操作。"""


class BackupLeaseLostError(BackupJobError):
    """当前 worker 已失去任务租约所有权。"""


def _new_worker_token() -> str:
    return str(uuid.uuid4())


def _wait_for_stop(stop_event: threading.Event, seconds: float) -> bool:
    return stop_event.wait(seconds)


def _safe_job_id(job_id: Any) -> str:
    try:
        return str(uuid.UUID(str(job_id)))
    except (AttributeError, TypeError, ValueError):
        return "invalid"


def _log_safe_error(event: str, error: Exception, job_id: Any) -> None:
    logger.error(
        "event=%s exception_type=%s job_id=%s",
        str(event),
        type(error).__name__,
        _safe_job_id(job_id),
    )


class BackupLeaseHeartbeat:
    """在独立应用上下文和会话中周期续租当前 worker 的任务。"""

    def __init__(
        self,
        *,
        app: Any,
        job_id: str,
        worker_token: str,
        lease_seconds: int,
        interval_seconds: float,
        clock: Callable[[], datetime] = datetime.utcnow,
        waiter: Callable[[threading.Event, float], bool] = _wait_for_stop,
    ):
        self._app = app
        self._job_id = str(job_id)
        self._worker_token = str(worker_token)
        self._lease_seconds = int(lease_seconds)
        self._interval_seconds = float(interval_seconds)
        self._clock = clock
        self._waiter = waiter
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def renew_once(self) -> bool:
        """仅在 token 和未过期租约仍匹配时 CAS 续租。"""
        with self._app.app_context():
            renewed_at = self._clock()
            try:
                updated = (
                    BackupJob.query.filter(
                        BackupJob.id == self._job_id,
                        BackupJob.status == "running",
                        BackupJob.worker_token == self._worker_token,
                        BackupJob.lease_expires_at > renewed_at,
                    )
                    .update(
                        {
                            BackupJob.lease_expires_at: renewed_at
                            + timedelta(seconds=self._lease_seconds)
                        },
                        synchronize_session=False,
                    )
                )
                if updated == 1:
                    db.session.commit()
                    return True
                db.session.rollback()
                return False
            except Exception as exc:
                db.session.rollback()
                _log_safe_error("heartbeat_renew_failed", exc, self._job_id)
                return False
            finally:
                db.session.remove()

    def _run(self) -> None:
        while not self._waiter(self._stop_event, self._interval_seconds):
            if not self.renew_once():
                self._stop_event.set()
                return

    def __enter__(self) -> "BackupLeaseHeartbeat":
        self._thread = threading.Thread(
            target=self._run,
            name=f"backup-lease-heartbeat-{self._job_id[:8]}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, min(self._interval_seconds, 5.0)))
            if self._thread.is_alive():
                _log_safe_error(
                    "heartbeat_stop_timeout", TimeoutError(), self._job_id
                )
        return False


class BackupJobService:
    """在数据库记录边界内编排一次备份。"""

    def __init__(
        self,
        *,
        archive_service: Optional[Any] = None,
        storage_service: Optional[Any] = None,
        storage_factory: Callable[[dict[str, Any]], Any] = BackupStorageService,
        config_service: Any = BackupConfigService,
        now: Callable[[], datetime] = datetime.utcnow,
        lease_seconds: Optional[int] = None,
        heartbeat_factory: Callable[..., Any] = BackupLeaseHeartbeat,
        heartbeat_interval_seconds: Optional[float] = None,
        heartbeat_clock: Optional[Callable[[], datetime]] = None,
        heartbeat_waiter: Callable[
            [threading.Event, float], bool
        ] = _wait_for_stop,
        worker_token_factory: Callable[[], str] = _new_worker_token,
    ):
        self._archive_service = archive_service
        self._storage_service = storage_service
        self._storage_factory = storage_factory
        self._config_service = config_service
        self._now = now
        self._heartbeat_factory = heartbeat_factory
        self._heartbeat_clock = heartbeat_clock or now
        self._heartbeat_waiter = heartbeat_waiter
        self._worker_token_factory = worker_token_factory
        configured_lease = (
            lease_seconds
            if lease_seconds is not None
            else os.environ.get("BACKUP_JOB_LEASE_SECONDS", _DEFAULT_LEASE_SECONDS)
        )
        self._lease_seconds = max(1, min(int(configured_lease), 86400))
        self._heartbeat_interval_seconds = max(
            1.0,
            float(heartbeat_interval_seconds)
            if heartbeat_interval_seconds is not None
            else self._lease_seconds / 3.0,
        )

    def _runtime_config(self) -> dict[str, Any]:
        return dict(self._config_service.get_runtime_config())

    def _storage(self, runtime_config: dict[str, Any]) -> Any:
        if self._storage_service is not None:
            return self._storage_service
        return self._storage_factory(dict(runtime_config))

    def _archive(self) -> Any:
        if self._archive_service is not None:
            return self._archive_service
        return BackupArchiveService.from_environment()

    def _heartbeat(self, job_id: str, worker_token: str) -> Any:
        return self._heartbeat_factory(
            app=current_app._get_current_object(),
            job_id=str(job_id),
            worker_token=str(worker_token),
            lease_seconds=self._lease_seconds,
            interval_seconds=self._heartbeat_interval_seconds,
            clock=self._heartbeat_clock,
            waiter=self._heartbeat_waiter,
        )

    def create_manual_job(self, created_by: Optional[int] = None) -> BackupJob:
        self.recover_stale_jobs()
        acquire_storage_identity_lock()
        job = BackupJob(
            status="queued",
            trigger="manual",
            active_slot="global",
            created_by=created_by,
        )
        try:
            db.session.add(job)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = (
                BackupJob.query.filter(
                    BackupJob.active_slot == "global",
                    BackupJob.status.in_(_ACTIVE_STATUSES),
                )
                .order_by(BackupJob.created_at.asc(), BackupJob.id.asc())
                .first()
            )
            if existing is None:
                raise
            return existing
        except Exception:
            db.session.rollback()
            raise
        return job

    def create_scheduled_job(self, schedule_slot: str) -> Optional[BackupJob]:
        """幂等创建 cron 时间槽任务；有活动任务时保留时间槽供下轮重试。"""
        slot = str(schedule_slot or "").strip()
        if not slot or len(slot) > 32:
            raise ValueError("schedule_slot 格式无效")

        for attempt in range(2):
            acquire_storage_identity_lock()
            existing = BackupJob.query.filter_by(schedule_slot=slot).first()
            if existing is not None:
                db.session.rollback()
                return existing
            active = (
                BackupJob.query.filter(
                    BackupJob.active_slot == "global",
                    BackupJob.status.in_(_ACTIVE_STATUSES),
                )
                .order_by(BackupJob.created_at.asc(), BackupJob.id.asc())
                .first()
            )
            if active is not None:
                db.session.rollback()
                return None

            job = BackupJob(
                status="queued",
                trigger="scheduled",
                active_slot="global",
                schedule_slot=slot,
            )
            try:
                db.session.add(job)
                db.session.commit()
                return job
            except IntegrityError:
                db.session.rollback()
                raced = BackupJob.query.filter_by(schedule_slot=slot).first()
                if raced is not None:
                    return raced
                if attempt == 0:
                    continue
                active = BackupJob.query.filter(
                    BackupJob.active_slot == "global",
                    BackupJob.status.in_(_ACTIVE_STATUSES),
                ).first()
                if active is not None:
                    return None
                raise
            except Exception:
                db.session.rollback()
                raise
        return None

    def oldest_queued_job_id(self) -> Optional[str]:
        """返回当前最旧排队任务 ID，实际所有权仍由 execute_job 原子认领。"""
        candidate = (
            BackupJob.query.filter_by(status="queued")
            .order_by(BackupJob.created_at.asc(), BackupJob.id.asc())
            .with_entities(BackupJob.id)
            .first()
        )
        return str(candidate[0]) if candidate else None

    def list_jobs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        jobs = (
            BackupJob.query.order_by(
                BackupJob.created_at.desc(), BackupJob.id.desc()
            )
            .limit(safe_limit)
            .all()
        )
        return [job.to_dict() for job in jobs]

    def atomic_claim(self, job_id: Optional[str] = None) -> Optional[BackupJob]:
        self.recover_stale_jobs()
        claimed_at = self._now()
        worker_token = self._worker_token_factory()
        selected_id = job_id
        if selected_id is None:
            candidate = (
                BackupJob.query.filter_by(status="queued")
                .order_by(BackupJob.created_at.asc(), BackupJob.id.asc())
                .with_entities(BackupJob.id)
                .first()
            )
            selected_id = candidate[0] if candidate else None
        if selected_id is None:
            return None
        updated = (
            BackupJob.query.filter_by(id=str(selected_id), status="queued")
            .filter(BackupJob.active_slot == "global")
            .update(
                {
                    BackupJob.status: "running",
                    BackupJob.started_at: claimed_at,
                    BackupJob.lease_expires_at: claimed_at
                    + timedelta(seconds=self._lease_seconds),
                    BackupJob.worker_token: worker_token,
                    BackupJob.error_message: None,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            db.session.rollback()
            return None
        db.session.commit()
        db.session.expire_all()
        return db.session.get(BackupJob, str(selected_id))

    def recover_stale_jobs(self) -> int:
        recovered_at = self._now()
        try:
            recovered = (
                BackupJob.query.filter(
                    BackupJob.status == "running",
                    BackupJob.lease_expires_at.isnot(None),
                    BackupJob.lease_expires_at <= recovered_at,
                )
                .update(
                    {
                        BackupJob.status: "failed",
                        BackupJob.active_slot: None,
                        BackupJob.lease_expires_at: None,
                        BackupJob.worker_token: None,
                        BackupJob.error_message: _STALE_FAILURE_SUMMARY,
                        BackupJob.completed_at: recovered_at,
                    },
                    synchronize_session=False,
                )
            )
            if recovered:
                db.session.commit()
                db.session.expire_all()
            else:
                db.session.rollback()
            return int(recovered)
        except Exception:
            db.session.rollback()
            raise

    def _mark_completed(
        self,
        job_id: str,
        worker_token: str,
        archive_result: Any,
        upload_result: Any,
        retention_days: int,
    ) -> BackupJob:
        completed_at = self._now()
        expires_at = (
            completed_at + timedelta(days=retention_days) if retention_days > 0 else None
        )
        completed = db.session.get(BackupJob, str(job_id))
        updated = (
            BackupJob.query.filter(
                BackupJob.id == str(job_id),
                BackupJob.status == "running",
                BackupJob.worker_token == str(worker_token),
                BackupJob.lease_expires_at > completed_at,
            )
            .update(
                {
                    BackupJob.status: "completed",
                    BackupJob.active_slot: None,
                    BackupJob.lease_expires_at: None,
                    BackupJob.worker_token: None,
                    BackupJob.object_key: str(upload_result.object_key),
                    BackupJob.filename: str(archive_result.filename),
                    BackupJob.size_bytes: int(upload_result.size_bytes),
                    BackupJob.sha256: str(archive_result.sha256),
                    BackupJob.error_message: None,
                    BackupJob.completed_at: completed_at,
                    BackupJob.expires_at: expires_at,
                },
                synchronize_session="fetch",
            )
        )
        if updated != 1 or completed is None:
            db.session.rollback()
            raise BackupLeaseLostError("备份任务租约所有权已失效")
        db.session.flush()
        db.session.expunge(completed)
        db.session.commit()
        return completed

    def _mark_failed(self, job_id: str, worker_token: str) -> BackupJob:
        db.session.rollback()
        failed_at = self._now()
        updated = (
            BackupJob.query.filter(
                BackupJob.id == str(job_id),
                BackupJob.status == "running",
                BackupJob.worker_token == str(worker_token),
                BackupJob.lease_expires_at > failed_at,
            )
            .update(
                {
                    BackupJob.status: "failed",
                    BackupJob.active_slot: None,
                    BackupJob.lease_expires_at: None,
                    BackupJob.worker_token: None,
                    BackupJob.error_message: _SAFE_FAILURE_SUMMARY,
                    BackupJob.completed_at: failed_at,
                    BackupJob.expires_at: None,
                },
                synchronize_session=False,
            )
        )
        if updated == 1:
            db.session.commit()
            db.session.expire_all()
        else:
            db.session.rollback()
        job = db.session.get(BackupJob, str(job_id))
        if job is None:
            raise BackupJobNotFoundError("备份任务不存在")
        return job

    def execute_job(self, job_id: str) -> BackupJob:
        job = self.atomic_claim(str(job_id))
        if job is None:
            current = db.session.get(BackupJob, str(job_id))
            if current is None:
                raise BackupJobNotFoundError("备份任务不存在")
            return current
        claimed_job_id = str(job.id)
        worker_token = str(job.worker_token or "")
        archive_result = None
        runtime_config: Optional[dict[str, Any]] = None
        storage = None
        upload_result = None
        completed: Optional[BackupJob] = None
        completed_committed = False
        try:
            if not worker_token:
                raise BackupLeaseLostError("备份任务缺少 worker 所有权令牌")
            archive_service = self._archive()
            with self._heartbeat(claimed_job_id, worker_token):
                runtime_config = self._runtime_config()
                archive_result = archive_service.create_archive(claimed_job_id)
                storage = self._storage(runtime_config)
                upload_result = storage.upload_file(archive_result.path)
                completed = self._mark_completed(
                    claimed_job_id,
                    worker_token,
                    archive_result,
                    upload_result,
                    int(runtime_config["retention_days"]),
                )
                completed_committed = True
            try:
                self.apply_retention(runtime_config=runtime_config)
            except Exception as exc:
                _log_safe_error("retention_cleanup_failed", exc, claimed_job_id)
            return completed
        except Exception as exc:
            _log_safe_error("job_execution_failed", exc, claimed_job_id)
            if (
                not completed_committed
                and storage is not None
                and upload_result is not None
            ):
                try:
                    storage.delete_object(str(upload_result.object_key))
                except Exception as cleanup_exc:
                    _log_safe_error(
                        "uploaded_object_cleanup_failed",
                        cleanup_exc,
                        claimed_job_id,
                    )
            if completed_committed and completed is not None:
                return completed
            return self._mark_failed(claimed_job_id, worker_token)
        finally:
            if archive_result is not None:
                try:
                    archive_service.cleanup_archive(archive_result.path)
                except Exception as cleanup_exc:
                    _log_safe_error(
                        "archive_cleanup_failed", cleanup_exc, claimed_job_id
                    )

    def _completed_job(self, job_id: str) -> BackupJob:
        job = db.session.get(BackupJob, str(job_id))
        if job is None:
            raise BackupJobNotFoundError("备份任务不存在")
        if job.status != "completed" or not job.object_key:
            raise BackupJobConflictError("仅已完成的备份可执行此操作")
        return job

    def _deletable_job(self, job_id: str) -> BackupJob:
        job = db.session.get(BackupJob, str(job_id))
        if job is None:
            raise BackupJobNotFoundError("备份任务不存在")
        if job.status not in {"completed", "deleting"} or not job.object_key:
            raise BackupJobConflictError(
                "仅已完成或删除中的备份可执行此操作"
            )
        return job

    def download_url(self, job_id: str) -> str:
        job = self._completed_job(job_id)
        runtime_config = self._runtime_config()
        return str(
            self._storage(runtime_config).generate_presigned_url(job.object_key)
        )

    def delete_completed_job(
        self,
        job_id: str,
        *,
        runtime_config: Optional[dict[str, Any]] = None,
        storage_service: Optional[Any] = None,
    ) -> bool:
        job = self._deletable_job(job_id)
        object_key = str(job.object_key)
        if job.status == "completed":
            job.status = "deleting"
            job.active_slot = None
            job.lease_expires_at = None
            job.worker_token = None
            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                _log_safe_error("delete_state_commit_failed", exc, job_id)
                raise
        config = (
            dict(runtime_config)
            if runtime_config is not None
            else self._runtime_config()
        )
        storage = storage_service or self._storage(config)
        try:
            storage.delete_object(object_key)
        except Exception as exc:
            db.session.rollback()
            _log_safe_error("remote_delete_failed", exc, job_id)
            raise
        try:
            job = self._deletable_job(job_id)
            db.session.delete(job)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            _log_safe_error("delete_record_failed", exc, job_id)
            raise
        return True

    def apply_retention(
        self, *, runtime_config: Optional[dict[str, Any]] = None
    ) -> list[str]:
        config = (
            dict(runtime_config)
            if runtime_config is not None
            else self._runtime_config()
        )
        deleted_ids = self.retry_deleting_jobs(runtime_config=config)
        prefix = f"{str(config['prefix']).rstrip('/')}/"
        storage = self._storage(config)
        completed = [
            job
            for job in BackupJob.query.filter_by(status="completed").all()
            if job.object_key and str(job.object_key).startswith(prefix)
        ]
        completed.sort(
            key=lambda job: (job.completed_at or job.created_at, job.id), reverse=True
        )
        if len(completed) <= 1:
            return deleted_ids

        keep_count = max(1, int(config["max_backups"]))
        by_count = {job.id for job in completed[keep_count:]}
        now = self._now()
        by_age = {
            job.id
            for job in completed[1:]
            if job.expires_at is not None and job.expires_at <= now
        }
        delete_ids = by_count | by_age
        candidates = [
            job for job in reversed(completed) if job.id in delete_ids
        ]
        if not candidates:
            return deleted_ids

        for job in candidates:
            candidate_id = job.id
            self.delete_completed_job(
                candidate_id,
                runtime_config=config,
                storage_service=storage,
            )
            deleted_ids = [*deleted_ids, candidate_id]
        return deleted_ids

    def retry_deleting_jobs(
        self, *, runtime_config: Optional[dict[str, Any]] = None
    ) -> list[str]:
        """重试因远端瞬时错误而停留在 deleting 的记录。"""
        pending = BackupJob.query.filter_by(status="deleting").all()
        if not pending:
            return []
        config = (
            dict(runtime_config)
            if runtime_config is not None
            else self._runtime_config()
        )
        prefix = f"{str(config['prefix']).rstrip('/')}/"
        storage = self._storage(config)
        deleting = [
            job
            for job in pending
            if job.object_key and str(job.object_key).startswith(prefix)
        ]
        deleted_ids: list[str] = []
        for job in deleting:
            deleting_id = job.id
            self.delete_completed_job(
                deleting_id,
                runtime_config=config,
                storage_service=storage,
            )
            deleted_ids = [*deleted_ids, deleting_id]
        return deleted_ids
