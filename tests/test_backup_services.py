# -*- coding: utf-8 -*-
"""R2 存储、备份归档和任务编排服务测试。"""

from __future__ import annotations

import copy
import hashlib
import logging
import tarfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.extensions import db
from app.models.backup import BackupJob
from app.models.system import SystemConfig
from app.modules.admin.services.backup_archive_service import BackupArchiveService
from app.modules.admin.services.backup_config_service import (
    BackupConfigService,
    BackupConfigValidationError,
)
from app.modules.admin.services import backup_job_service as backup_job_module
from app.modules.admin.services.backup_job_service import BackupJobService
from app.modules.admin.services.backup_storage_service import (
    BackupStorageError,
    BackupStorageService,
)
from app.modules.admin.services.system_config_service import _cache_clear


VALID_ENDPOINT = "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com"
VALID_CONFIG = {
    "endpoint": VALID_ENDPOINT,
    "region": "auto",
    "bucket": "ti-backups",
    "prefix": "backups/",
    "access_key_id": "r2-access-key-123456",
    "secret_access_key": "r2-secret-key-abcdef",
    "schedule_enabled": True,
    "cron_expression": "0 2 * * *",
    "retention_days": 14,
    "max_backups": 3,
}
BACKUP_CONFIG_KEYS = tuple(f"backup_{key}" for key in VALID_CONFIG)


class FakeS3Client:
    def __init__(self, *, content_length: int | None = None, fail_put: bool = False):
        self.content_length = content_length
        self.fail_put = fail_put
        self.calls = []

    def put_object(self, **kwargs):
        self.calls.append(("put_object", kwargs))
        if self.fail_put:
            raise RuntimeError("simulated put failure")

    def delete_object(self, **kwargs):
        self.calls.append(("delete_object", kwargs))

    def upload_file(self, filename, bucket, key, **kwargs):
        self.calls.append(("upload_file", (filename, bucket, key, kwargs)))

    def head_object(self, **kwargs):
        self.calls.append(("head_object", kwargs))
        return {"ContentLength": self.content_length}

    def generate_presigned_url(self, operation, **kwargs):
        self.calls.append(("generate_presigned_url", (operation, kwargs)))
        return "https://download.invalid/signed"


@pytest.fixture
def clean_backup_state(app):
    with app.app_context():
        BackupJob.query.delete(synchronize_session=False)
        SystemConfig.query.filter(
            SystemConfig.config_key.in_(BACKUP_CONFIG_KEYS)
        ).delete(synchronize_session=False)
        db.session.commit()
        _cache_clear()
        app.config["BACKUP_CREDENTIAL_SECRET"] = "backup-service-test-key"
        yield
        db.session.rollback()
        BackupJob.query.delete(synchronize_session=False)
        SystemConfig.query.filter(
            SystemConfig.config_key.in_(BACKUP_CONFIG_KEYS)
        ).delete(synchronize_session=False)
        db.session.commit()
        _cache_clear()


def test_runtime_config_decrypts_credentials_without_changing_public_dto(
    app, clean_backup_state
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)

        public_config = BackupConfigService.get_config()
        runtime_config = BackupConfigService.get_runtime_config()

        assert runtime_config["access_key_id"] == VALID_CONFIG["access_key_id"]
        assert runtime_config["secret_access_key"] == VALID_CONFIG["secret_access_key"]
        assert public_config["access_key_id"] != VALID_CONFIG["access_key_id"]
        assert public_config["secret_access_key"] != VALID_CONFIG["secret_access_key"]


def test_storage_connection_uses_fixed_healthcheck_prefix_and_always_deletes():
    client = FakeS3Client(fail_put=True)
    service = BackupStorageService(VALID_CONFIG, client=client)

    with pytest.raises(RuntimeError, match="simulated put failure"):
        service.test_connection()

    put = client.calls[0]
    delete = client.calls[1]
    assert put[0] == "put_object"
    assert put[1]["Bucket"] == VALID_CONFIG["bucket"]
    assert put[1]["Key"].startswith("backups/.healthcheck/")
    assert put[1]["Key"].endswith(".txt")
    assert delete == (
        "delete_object",
        {"Bucket": VALID_CONFIG["bucket"], "Key": put[1]["Key"]},
    )


def test_storage_upload_generates_prefixed_key_and_verifies_remote_size(tmp_path):
    archive = tmp_path / "backup_20260711_020304_12345678.tar.gz"
    archive.write_bytes(b"archive-bytes")
    client = FakeS3Client(content_length=archive.stat().st_size)
    service = BackupStorageService(VALID_CONFIG, client=client)

    result = service.upload_file(archive)

    assert result.object_key == f"backups/{archive.name}"
    assert result.size_bytes == archive.stat().st_size
    upload_call = client.calls[0]
    transfer_config = upload_call[1][3]["Config"]
    assert transfer_config.max_request_concurrency == 2
    assert transfer_config.max_io_queue_size == 4
    assert transfer_config.multipart_chunksize == 8 * 1024 * 1024
    assert client.calls[-1] == (
        "head_object",
        {"Bucket": VALID_CONFIG["bucket"], "Key": result.object_key},
    )


def test_storage_upload_rejects_size_mismatch(tmp_path):
    archive = tmp_path / "backup_20260711_020304_12345678.tar.gz"
    archive.write_bytes(b"archive-bytes")
    client = FakeS3Client(content_length=archive.stat().st_size + 1)
    service = BackupStorageService(VALID_CONFIG, client=client)

    with pytest.raises(BackupStorageError, match="大小校验失败"):
        service.upload_file(archive)
    assert client.calls[-1] == (
        "delete_object",
        {"Bucket": VALID_CONFIG["bucket"], "Key": f"backups/{archive.name}"},
    )


def test_storage_download_and_delete_are_limited_to_current_prefix():
    client = FakeS3Client()
    service = BackupStorageService(VALID_CONFIG, client=client)
    key = "backups/backup_20260711_020304_12345678.tar.gz"

    assert service.generate_presigned_url(key) == "https://download.invalid/signed"
    service.delete_object(key)

    presign = client.calls[0]
    assert presign == (
        "generate_presigned_url",
        (
            "get_object",
            {
                "Params": {"Bucket": VALID_CONFIG["bucket"], "Key": key},
                "ExpiresIn": 300,
            },
        ),
    )
    assert client.calls[1] == (
        "delete_object",
        {"Bucket": VALID_CONFIG["bucket"], "Key": key},
    )
    with pytest.raises(BackupStorageError, match="当前备份前缀"):
        service.delete_object("other-prefix/archive.tar.gz")


def test_storage_copies_config_and_rejects_unvalidated_credentials():
    submitted = copy.deepcopy(VALID_CONFIG)
    service = BackupStorageService(submitted, client=FakeS3Client())
    submitted["bucket"] = "mutated-after-construction"

    assert service.bucket == VALID_CONFIG["bucket"]
    with pytest.raises(BackupStorageError, match="凭据"):
        BackupStorageService(
            {**VALID_CONFIG, "secret_access_key": ""}, client=FakeS3Client()
        )


def test_archive_contains_only_restore_compatible_business_data(tmp_path):
    uploads = tmp_path / "uploads"
    instance = tmp_path / "instance"
    uploads.mkdir()
    instance.mkdir()
    (uploads / "question.png").write_bytes(b"image")
    (instance / "local.sqlite").write_bytes(b"sqlite")
    (uploads / ".env").write_text("SECRET=excluded", encoding="utf-8")
    (instance / "compose.prod.yml").write_text("services: {}", encoding="utf-8")
    (uploads / "logs").mkdir()
    (uploads / "logs" / "application.log").write_text("excluded", encoding="utf-8")
    (uploads / "log").mkdir()
    (uploads / "log" / "worker.log").write_text("excluded", encoding="utf-8")
    (uploads / "scattered.log").write_text("excluded", encoding="utf-8")
    (instance / "redis").mkdir()
    (instance / "redis" / "dump.rdb").write_bytes(b"excluded")
    password = "db-password-never-on-command-line"
    runner_calls = []

    def fake_runner(command, **kwargs):
        runner_calls.append((command, kwargs))
        kwargs["stdout"].write(b"-- postgres dump --\n")
        return SimpleNamespace(returncode=0)

    service = BackupArchiveService(
        database_url=f"postgresql://studyuser:{password}@db.internal:5432/ti_db",
        uploads_dir=uploads,
        instance_dir=instance,
        temp_root=tmp_path / "private",
        runner=fake_runner,
        now=lambda: datetime(2026, 7, 11, 2, 3, 4),
    )

    result = service.create_archive("12345678-1234-1234-1234-123456789abc")

    assert result.filename == "backup_20260711_020304_12345678.tar.gz"
    assert result.size_bytes == result.path.stat().st_size
    assert result.sha256 == hashlib.sha256(result.path.read_bytes()).hexdigest()
    assert result.path.stat().st_mode & 0o777 == 0o600
    with tarfile.open(result.path, "r:gz") as archive:
        names = set(archive.getnames())
        root = "backup_20260711_020304_12345678"
        assert f"{root}/database.sql" in names
        assert f"{root}/uploads/question.png" in names
        assert f"{root}/instance/local.sqlite" in names
        assert f"{root}/MANIFEST.txt" in names
        assert not any(
            excluded in name
            for name in names
            for excluded in ("redis", "/log/", "/logs/", ".log", ".env", "compose")
        )

    command, kwargs = runner_calls[0]
    assert isinstance(command, list)
    assert password not in command
    assert kwargs["shell"] is False
    assert kwargs["check"] is True
    assert kwargs["timeout"] > 0
    assert kwargs["env"]["PGPASSWORD"] == password
    assert "DATABASE_URL" not in kwargs["env"]
    service.cleanup_archive(result.path)
    assert not result.path.exists()


def test_archive_skips_symlinks_and_cleans_private_directory_on_failure(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    secret = tmp_path / ".env.production"
    secret.write_text("SECRET=must-not-archive", encoding="utf-8")
    (uploads / "linked-secret").symlink_to(secret)
    private_root = tmp_path / "private"

    def failing_runner(command, **kwargs):
        raise RuntimeError("pg_dump failed")

    service = BackupArchiveService(
        database_url="postgresql://studyuser:pw@db.internal:5432/ti_db",
        uploads_dir=uploads,
        instance_dir=None,
        temp_root=private_root,
        runner=failing_runner,
    )

    with pytest.raises(RuntimeError, match="pg_dump failed"):
        service.create_archive("12345678-1234-1234-1234-123456789abc")

    assert list(private_root.iterdir()) == []


def test_archive_creates_empty_restore_directories_when_sources_do_not_exist(tmp_path):
    def fake_runner(command, **kwargs):
        kwargs["stdout"].write(b"-- postgres dump --\n")
        return SimpleNamespace(returncode=0)

    service = BackupArchiveService(
        database_url="postgresql://studyuser:pw@db.internal:5432/ti_db",
        uploads_dir=tmp_path / "missing-uploads",
        instance_dir=tmp_path / "missing-instance",
        temp_root=tmp_path / "private",
        runner=fake_runner,
        now=lambda: datetime(2026, 7, 11, 2, 3, 4),
    )

    result = service.create_archive("12345678-1234-1234-1234-123456789abc")

    with tarfile.open(result.path, "r:gz") as archive:
        names = set(archive.getnames())
    root = "backup_20260711_020304_12345678"
    assert f"{root}/uploads" in names
    assert f"{root}/instance" in names


def test_archive_never_changes_configured_temp_parent_permissions(tmp_path):
    temp_root = tmp_path / "shared-backup-temp"
    temp_root.mkdir(mode=0o755)
    temp_root.chmod(0o755)

    def fake_runner(command, **kwargs):
        kwargs["stdout"].write(b"-- postgres dump --\n")
        return SimpleNamespace(returncode=0)

    service = BackupArchiveService(
        database_url="postgresql://studyuser:pw@db.internal:5432/ti_db",
        uploads_dir=None,
        instance_dir=None,
        temp_root=temp_root,
        runner=fake_runner,
    )

    result = service.create_archive("12345678-1234-1234-1234-123456789abc")

    assert temp_root.stat().st_mode & 0o777 == 0o755
    assert result.path.parent.stat().st_mode & 0o777 == 0o700


class FakeArchiveService:
    def __init__(self, tmp_path: Path, *, fail: bool = False):
        self.tmp_path = tmp_path
        self.fail = fail
        self.cleaned = []
        self.create_calls = []

    def create_archive(self, job_id):
        self.create_calls.append(job_id)
        path = self.tmp_path / f"backup_20260711_020304_{str(job_id)[:8]}.tar.gz"
        path.write_bytes(b"job archive")
        if self.fail:
            raise RuntimeError("archive failure includes internal detail")
        return SimpleNamespace(
            path=path,
            filename=path.name,
            size_bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )

    def cleanup_archive(self, path):
        self.cleaned.append(Path(path))
        Path(path).unlink(missing_ok=True)


class FakeStorageService:
    def __init__(
        self,
        *,
        fail_upload: bool = False,
        fail_delete_count: int = 0,
        on_upload=None,
    ):
        self.fail_upload = fail_upload
        self.fail_delete_count = fail_delete_count
        self.on_upload = on_upload
        self.uploaded = []
        self.deleted = []
        self.presigned = []

    def upload_file(self, path):
        self.uploaded.append(Path(path))
        if self.fail_upload:
            raise RuntimeError("storage failure with provider detail")
        if self.on_upload is not None:
            self.on_upload()
        return SimpleNamespace(
            object_key=f"backups/{Path(path).name}",
            size_bytes=Path(path).stat().st_size,
        )

    def generate_presigned_url(self, object_key):
        self.presigned.append(object_key)
        return "https://download.invalid/job-signed"

    def delete_object(self, object_key):
        self.deleted.append(object_key)
        if self.fail_delete_count > 0:
            self.fail_delete_count -= 1
            raise RuntimeError("simulated remote delete failure")


def _completed_job(index: int, completed_at: datetime, *, prefix: str = "backups/"):
    return BackupJob(
        id=f"00000000-0000-0000-0000-{index:012d}",
        status="completed",
        trigger="manual",
        filename=f"backup_202607{index:02d}_020304_{index:08d}.tar.gz",
        object_key=f"{prefix}backup_202607{index:02d}_020304_{index:08d}.tar.gz",
        size_bytes=100 + index,
        sha256=f"{index:064x}",
        started_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        created_at=completed_at - timedelta(minutes=2),
    )


def test_manual_job_reuses_existing_queued_or_running_job(app, clean_backup_state):
    with app.app_context():
        service = BackupJobService()
        first = service.create_manual_job(created_by=7)
        second = service.create_manual_job(created_by=8)

        assert second.id == first.id
        assert BackupJob.query.count() == 1
        assert first.created_by == 7


def test_active_slot_unique_constraint_and_integrity_conflict_reuse(
    app, clean_backup_state, monkeypatch
):
    with app.app_context():
        existing = BackupJob(
            status="running",
            trigger="manual",
            active_slot="global",
            created_by=7,
        )
        db.session.add(existing)
        db.session.commit()
        duplicate = BackupJob(
            status="queued",
            trigger="manual",
            active_slot="global",
            created_by=8,
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        original_commit = db.session.commit
        commit_calls = 0

        def tracked_commit():
            nonlocal commit_calls
            commit_calls += 1
            return original_commit()

        monkeypatch.setattr(db.session, "commit", tracked_commit)
        reused = BackupJobService().create_manual_job(created_by=9)

        assert reused.id == existing.id
        assert reused.active_slot == "global"
        assert commit_calls == 1
        assert BackupJob.query.filter_by(active_slot="global").count() == 1


def test_atomic_claim_only_transitions_queued_job_once(app, clean_backup_state):
    with app.app_context():
        now = datetime(2026, 7, 11, 2, 3, 4)
        service = BackupJobService(now=lambda: now, lease_seconds=120)
        job = service.create_manual_job(created_by=7)

        claimed = service.atomic_claim(job.id)
        second_claim = service.atomic_claim(job.id)

        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.started_at == datetime(2026, 7, 11, 2, 3, 4)
        assert claimed.lease_expires_at == now + timedelta(seconds=120)
        assert str(uuid.UUID(claimed.worker_token)) == claimed.worker_token
        assert second_claim is None


def test_stale_running_lease_is_recovered_before_new_manual_job(
    app, clean_backup_state
):
    now = datetime(2026, 7, 11, 2, 3, 4)
    with app.app_context():
        stale = BackupJob(
            status="running",
            trigger="scheduled",
            active_slot="global",
            lease_expires_at=now - timedelta(seconds=1),
            worker_token="expired-worker-token",
            started_at=now - timedelta(hours=2),
        )
        db.session.add(stale)
        db.session.commit()
        service = BackupJobService(now=lambda: now, lease_seconds=120)

        replacement = service.create_manual_job(created_by=7)

        db.session.refresh(stale)
        assert stale.status == "failed"
        assert stale.active_slot is None
        assert stale.lease_expires_at is None
        assert stale.worker_token is None
        assert stale.completed_at == now
        assert replacement.id != stale.id
        assert replacement.active_slot == "global"


def test_atomic_claim_recovers_stale_jobs_even_when_target_is_missing(
    app, clean_backup_state
):
    now = datetime(2026, 7, 11, 2, 3, 4)
    with app.app_context():
        stale = BackupJob(
            status="running",
            trigger="scheduled",
            active_slot="global",
            lease_expires_at=now - timedelta(minutes=1),
            worker_token="expired-worker-token",
        )
        db.session.add(stale)
        db.session.commit()
        service = BackupJobService(now=lambda: now)

        assert service.atomic_claim("missing-job-id") is None
        db.session.refresh(stale)
        assert stale.status == "failed"
        assert stale.active_slot is None
        assert stale.worker_token is None


def test_execute_job_archives_uploads_completes_and_cleans_local_file(
    app, clean_backup_state, tmp_path
):
    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService()
    now = datetime(2026, 7, 11, 2, 3, 4)
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            now=lambda: now,
        )
        job = service.create_manual_job(created_by=7)

        completed = service.execute_job(job.id)

        assert completed.status == "completed"
        assert completed.object_key.startswith("backups/backup_")
        assert completed.filename.endswith(".tar.gz")
        assert completed.size_bytes == len(b"job archive")
        assert completed.sha256 == hashlib.sha256(b"job archive").hexdigest()
        assert completed.completed_at == now
        assert completed.expires_at == now + timedelta(days=14)
        assert completed.active_slot is None
        assert completed.lease_expires_at is None
        assert completed.worker_token is None
        assert len(archive.cleaned) == 1
        assert not archive.cleaned[0].exists()


def test_execute_job_marks_safe_failure_and_cleans_temporary_file(
    app, clean_backup_state, tmp_path
):
    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService(fail_upload=True)
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            now=lambda: datetime(2026, 7, 11, 2, 3, 4),
        )
        job = service.create_manual_job(created_by=7)

        failed = service.execute_job(job.id)

        assert failed.status == "failed"
        assert failed.error_message == "备份执行失败，请查看服务器日志"
        assert failed.active_slot is None
        assert failed.lease_expires_at is None
        assert failed.worker_token is None
        assert "provider detail" not in failed.error_message
        assert len(archive.cleaned) == 1
        assert not archive.cleaned[0].exists()


def test_job_execution_logs_never_include_exception_credentials(
    app, clean_backup_state, tmp_path, caplog
):
    class CredentialArchive(FakeArchiveService):
        def cleanup_archive(self, path):
            super().cleanup_archive(path)
            raise RuntimeError("cleanup credential=cleanup-secret-value")

    class CredentialStorage(FakeStorageService):
        def upload_file(self, path):
            raise RuntimeError("provider password=upload-secret-value")

    with app.app_context(), caplog.at_level(logging.ERROR):
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=CredentialArchive(tmp_path),
            storage_service=CredentialStorage(),
            now=lambda: datetime(2026, 7, 11, 2, 3, 4),
        )
        job = service.create_manual_job(created_by=7)

        failed = service.execute_job(job.id)

    assert failed.status == "failed"
    assert "event=job_execution_failed" in caplog.text
    assert "event=archive_cleanup_failed" in caplog.text
    assert "exception_type=RuntimeError" in caplog.text
    assert str(job.id) in caplog.text
    assert "upload-secret-value" not in caplog.text
    assert "cleanup-secret-value" not in caplog.text
    assert "Traceback" not in caplog.text


def test_job_service_source_has_no_traceback_exception_logging():
    source = Path(backup_job_module.__file__).read_text(encoding="utf-8")

    assert "logger.exception" not in source
    assert "str(exc)" not in source


def test_execute_job_does_not_run_when_queued_claim_was_already_taken(
    app, clean_backup_state, tmp_path
):
    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService()
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            now=lambda: datetime(2026, 7, 11, 2, 3, 4),
        )
        job = service.create_manual_job(created_by=7)
        claimed = service.atomic_claim(job.id)

        result = service.execute_job(job.id)

        assert claimed is not None
        assert result.status == "running"
        assert archive.create_calls == []
        assert storage.uploaded == []


def test_execute_job_removes_uploaded_object_when_completion_commit_fails(
    app, clean_backup_state, tmp_path, monkeypatch
):
    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService()
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            now=lambda: datetime(2026, 7, 11, 2, 3, 4),
        )
        job = service.create_manual_job(created_by=7)
        original_commit = db.session.commit
        commit_calls = 0

        def fail_completion_commit_once():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 2:
                raise RuntimeError("simulated completion commit failure")
            return original_commit()

        monkeypatch.setattr(db.session, "commit", fail_completion_commit_once)

        failed = service.execute_job(job.id)

        assert failed.status == "failed"
        assert len(storage.uploaded) == 1
        assert storage.deleted == [f"backups/{storage.uploaded[0].name}"]


class FakeHeartbeat:
    def __init__(self, factory, kwargs):
        self.factory = factory
        self.kwargs = kwargs

    def __enter__(self):
        self.factory.started += 1
        if self.factory.renew_seconds is not None:
            renewed_until = self.factory.clock() + timedelta(
                seconds=self.factory.renew_seconds
            )
            updated = (
                BackupJob.query.filter_by(
                    id=self.kwargs["job_id"],
                    status="running",
                    worker_token=self.kwargs["worker_token"],
                )
                .update(
                    {BackupJob.lease_expires_at: renewed_until},
                    synchronize_session=False,
                )
            )
            db.session.commit()
            self.factory.renewed += updated
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.factory.stopped += 1
        return False


class FakeHeartbeatFactory:
    def __init__(self, clock, *, renew_seconds=None):
        self.clock = clock
        self.renew_seconds = renew_seconds
        self.started = 0
        self.renewed = 0
        self.stopped = 0

    def __call__(self, **kwargs):
        return FakeHeartbeat(self, kwargs)


def test_long_running_job_heartbeat_renews_lease_and_stops(
    app, clean_backup_state, tmp_path
):
    clock = [datetime(2026, 7, 11, 2, 3, 4)]
    heartbeat_factory = FakeHeartbeatFactory(lambda: clock[0], renew_seconds=90)
    recovery_counts = []

    def pass_original_lease_then_recover():
        clock[0] += timedelta(seconds=20)
        recovery_counts.append(
            BackupJobService(now=lambda: clock[0]).recover_stale_jobs()
        )

    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService(on_upload=pass_original_lease_then_recover)
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            heartbeat_factory=heartbeat_factory,
            lease_seconds=10,
            now=lambda: clock[0],
        )
        job = service.create_manual_job(created_by=7)

        result = service.execute_job(job.id)

        assert result.status == "completed"
        assert recovery_counts == [0]
        assert heartbeat_factory.started == 1
        assert heartbeat_factory.renewed == 1
        assert heartbeat_factory.stopped == 1


def test_recovered_job_fences_old_worker_completion_and_cleans_upload(
    app, clean_backup_state, tmp_path
):
    clock = [datetime(2026, 7, 11, 2, 3, 4)]
    heartbeat_factory = FakeHeartbeatFactory(lambda: clock[0])
    recovered = []

    def expire_worker_after_upload():
        clock[0] += timedelta(seconds=11)
        recovered.append(
            BackupJobService(now=lambda: clock[0]).recover_stale_jobs()
        )

    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService(on_upload=expire_worker_after_upload)
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            heartbeat_factory=heartbeat_factory,
            lease_seconds=10,
            now=lambda: clock[0],
        )
        job = service.create_manual_job(created_by=7)

        result = service.execute_job(job.id)

        assert recovered == [1]
        assert result.status == "failed"
        assert result.worker_token is None
        assert result.error_message == "备份执行租约已过期，请重新创建备份"
        assert storage.deleted == [f"backups/{storage.uploaded[0].name}"]
        assert heartbeat_factory.stopped == 1


def test_archive_factory_failure_marks_claimed_job_failed_immediately(
    app, clean_backup_state, monkeypatch
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        job = BackupJobService().create_manual_job(created_by=7)

        def fail_archive_factory():
            raise RuntimeError("bad archive config")

        monkeypatch.setattr(
            BackupArchiveService,
            "from_environment",
            fail_archive_factory,
        )
        result = BackupJobService(
            heartbeat_factory=FakeHeartbeatFactory(datetime.utcnow),
        ).execute_job(job.id)

        assert result.status == "failed"
        assert result.active_slot is None
        assert result.worker_token is None
        assert BackupJob.query.filter_by(active_slot="global").count() == 0


def test_completed_commit_is_not_followed_by_failure_cleanup_on_read_error(
    app, clean_backup_state, tmp_path, monkeypatch
):
    archive = FakeArchiveService(tmp_path)
    storage = FakeStorageService()
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        service = BackupJobService(
            archive_service=archive,
            storage_service=storage,
            heartbeat_factory=FakeHeartbeatFactory(datetime.utcnow),
        )
        job = service.create_manual_job(created_by=7)
        original_commit = db.session.commit
        original_get = db.session.get
        state = {"commit_count": 0, "completed_committed": False}

        def tracked_commit():
            original_commit()
            state["commit_count"] += 1
            if state["commit_count"] >= 2:
                state["completed_committed"] = True

        def reject_post_commit_read(*args, **kwargs):
            if state["completed_committed"]:
                raise RuntimeError("post-commit read unavailable")
            return original_get(*args, **kwargs)

        monkeypatch.setattr(db.session, "commit", tracked_commit)
        monkeypatch.setattr(db.session, "get", reject_post_commit_read)

        result = service.execute_job(job.id)

        assert result.status == "completed"
        assert storage.deleted == []


def test_list_download_and_delete_completed_job(app, clean_backup_state):
    storage = FakeStorageService()
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        completed = _completed_job(1, datetime(2026, 7, 11, 2, 3, 4))
        db.session.add(completed)
        db.session.commit()
        service = BackupJobService(storage_service=storage)

        listed = service.list_jobs()
        url = service.download_url(completed.id)
        deleted = service.delete_completed_job(completed.id)

        assert listed[0]["id"] == completed.id
        assert url == "https://download.invalid/job-signed"
        assert deleted is True
        assert storage.presigned == [completed.object_key]
        assert storage.deleted == [completed.object_key]
        assert db.session.get(BackupJob, completed.id) is None


@pytest.mark.parametrize("status", [None, "queued", "running"])
def test_job_access_uses_explicit_not_found_and_conflict_errors(
    app, clean_backup_state, status
):
    with app.app_context():
        job_id = str(uuid.uuid4())
        if status is not None:
            db.session.add(
                BackupJob(id=job_id, status=status, trigger="manual")
            )
            db.session.commit()
        service = BackupJobService(storage_service=FakeStorageService())
        expected_error = (
            backup_job_module.BackupJobNotFoundError
            if status is None
            else backup_job_module.BackupJobConflictError
        )

        with pytest.raises(expected_error):
            service.download_url(job_id)
        with pytest.raises(expected_error):
            service.delete_completed_job(job_id)


def test_delete_config_failure_preserves_deleting_state(
    app, clean_backup_state
):
    class InvalidConfig:
        @staticmethod
        def get_runtime_config():
            raise BackupConfigValidationError("secret config detail")

    with app.app_context():
        completed = _completed_job(1, datetime(2026, 7, 11, 2, 3, 4))
        db.session.add(completed)
        db.session.commit()
        service = BackupJobService(
            config_service=InvalidConfig,
            storage_service=FakeStorageService(),
        )

        with pytest.raises(BackupConfigValidationError):
            service.delete_completed_job(completed.id)

        retained = db.session.get(BackupJob, completed.id)
        assert retained is not None
        assert retained.status == "deleting"


def test_delete_completed_job_keeps_deleting_state_and_retries_after_r2_failure(
    app, clean_backup_state
):
    storage = FakeStorageService(fail_delete_count=1)
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        completed = _completed_job(1, datetime(2026, 7, 11, 2, 3, 4))
        db.session.add(completed)
        db.session.commit()
        service = BackupJobService(storage_service=storage)

        with pytest.raises(RuntimeError, match="simulated remote delete failure"):
            service.delete_completed_job(completed.id)

        retained = db.session.get(BackupJob, completed.id)
        assert retained is not None
        assert retained.status == "deleting"

        assert service.delete_completed_job(completed.id) is True
        assert storage.deleted == [completed.object_key, completed.object_key]
        assert db.session.get(BackupJob, completed.id) is None


def test_retention_zero_days_keeps_newest_and_deletes_only_current_prefix_over_limit(
    app, clean_backup_state
):
    storage = FakeStorageService()
    now = datetime(2026, 7, 11, 12, 0, 0)
    with app.app_context():
        config = {**VALID_CONFIG, "retention_days": 0, "max_backups": 2}
        BackupConfigService.save_config(config)
        jobs = [
            _completed_job(1, now - timedelta(days=30)),
            _completed_job(2, now - timedelta(days=20)),
            _completed_job(3, now - timedelta(days=10)),
            _completed_job(4, now - timedelta(days=40), prefix="legacy/"),
        ]
        db.session.add_all(jobs)
        db.session.commit()
        service = BackupJobService(storage_service=storage, now=lambda: now)

        deleted_ids = service.apply_retention()

        assert deleted_ids == [jobs[0].id]
        assert storage.deleted == [jobs[0].object_key]
        assert db.session.get(BackupJob, jobs[2].id) is not None
        assert db.session.get(BackupJob, jobs[3].id) is not None


def test_retention_age_never_deletes_the_only_successful_backup(
    app, clean_backup_state
):
    storage = FakeStorageService()
    now = datetime(2026, 7, 11, 12, 0, 0)
    with app.app_context():
        config = {**VALID_CONFIG, "retention_days": 1, "max_backups": 10}
        BackupConfigService.save_config(config)
        only = _completed_job(1, now - timedelta(days=30))
        db.session.add(only)
        db.session.commit()
        service = BackupJobService(storage_service=storage, now=lambda: now)

        deleted_ids = service.apply_retention()

        assert deleted_ids == []
        assert storage.deleted == []
        assert db.session.get(BackupJob, only.id) is not None


def test_retention_uses_persisted_expiry_instead_of_current_policy(
    app, clean_backup_state
):
    storage = FakeStorageService()
    now = datetime(2026, 7, 11, 12, 0, 0)
    with app.app_context():
        BackupConfigService.save_config(
            {**VALID_CONFIG, "retention_days": 1, "max_backups": 10}
        )
        expired = _completed_job(1, now - timedelta(days=40))
        expired.expires_at = now - timedelta(seconds=1)
        still_valid = _completed_job(2, now - timedelta(days=30))
        still_valid.expires_at = now + timedelta(days=5)
        db.session.add_all([expired, still_valid])
        db.session.commit()

        deleted_ids = BackupJobService(
            storage_service=storage,
            now=lambda: now,
        ).apply_retention()

        assert deleted_ids == [expired.id]
        assert storage.deleted == [expired.object_key]
        assert db.session.get(BackupJob, still_valid.id) is not None
