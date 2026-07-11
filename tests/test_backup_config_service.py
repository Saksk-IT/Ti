# -*- coding: utf-8 -*-
"""备份任务模型与 Cloudflare R2 配置服务测试。"""

from copy import deepcopy
from datetime import datetime

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.extensions import db
from app.models.backup import BackupJob
from app.models.system import SystemConfig
from app.modules.admin.services.backup_config_service import (
    BackupConfigService,
    BackupConfigValidationError,
)
from app.modules.admin.services.system_config_service import SystemConfigService, _cache_clear


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


@pytest.fixture
def clean_backup_config(app):
    """隔离 system_config 中的备份配置。"""
    with app.app_context():
        BackupJob.query.delete(synchronize_session=False)
        SystemConfig.query.filter(SystemConfig.config_key.in_(BACKUP_CONFIG_KEYS)).delete(
            synchronize_session=False
        )
        db.session.commit()
        _cache_clear()
        app.config["BACKUP_CREDENTIAL_SECRET"] = "backup-test-encryption-key"
        yield
        BackupJob.query.delete(synchronize_session=False)
        SystemConfig.query.filter(SystemConfig.config_key.in_(BACKUP_CONFIG_KEYS)).delete(
            synchronize_session=False
        )
        db.session.commit()
        _cache_clear()


def test_backup_job_uses_uuid_defaults_and_allowlisted_serialization(app):
    with app.app_context():
        job = BackupJob(
            object_key="backups/backup.sql.gz",
            filename="backup.sql.gz",
            size_bytes=128,
            sha256="a" * 64,
            created_by=None,
        )
        db.session.add(job)
        db.session.flush()

        payload = job.to_dict()

        assert len(job.id) == 36
        assert job.status == "queued"
        assert job.trigger == "manual"
        assert payload == {
            "id": job.id,
            "status": "queued",
            "trigger": "manual",
            "object_key": "backups/backup.sql.gz",
            "filename": "backup.sql.gz",
            "size_bytes": 128,
            "sha256": "a" * 64,
            "error_message": None,
            "created_by": None,
            "started_at": None,
            "completed_at": None,
            "expires_at": None,
            "created_at": f"{job.created_at.isoformat()}Z" if job.created_at else None,
        }
        assert not any("secret" in key or "credential" in key for key in payload)
        assert "active_slot" not in payload
        assert "lease_expires_at" not in payload
    assert "worker_token" not in payload


def test_storage_identity_cannot_change_while_historical_backups_exist(
    app, clean_backup_config
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        db.session.add(
            BackupJob(
                status="completed",
                trigger="manual",
                active_slot=None,
                object_key="backups/backup_20260711_020304_12345678.tar.gz",
                filename="backup_20260711_020304_12345678.tar.gz",
            )
        )
        db.session.commit()

        for update in (
            {
                "endpoint": "https://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.fedramp.r2.cloudflarestorage.com"
            },
            {"bucket": "new-ti-backups"},
            {"prefix": "archives/"},
        ):
            with pytest.raises(
                BackupConfigValidationError,
                match="删除现有备份记录",
            ):
                BackupConfigService.save_config(update)

        rotated = BackupConfigService.save_config(
            {
                "access_key_id": "rotated-access-key",
                "secret_access_key": "rotated-secret-key",
            }
        )

        assert rotated["bucket"] == VALID_CONFIG["bucket"]


@pytest.mark.parametrize("status", ["queued", "running"])
def test_storage_identity_cannot_change_while_backup_is_active(
    app, clean_backup_config, status
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        db.session.add(
            BackupJob(
                status=status,
                trigger="manual",
                active_slot="global",
            )
        )
        db.session.commit()

        with pytest.raises(
            BackupConfigValidationError,
            match="删除现有备份记录",
        ):
            BackupConfigService.save_config({"prefix": "archives/"})


def test_storage_identity_check_bypasses_stale_system_config_cache(
    app, clean_backup_config
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        SystemConfigService.get_all_configs()
        db.session.add(
            BackupJob(
                status="completed",
                trigger="manual",
                active_slot=None,
                object_key="archives/backup_20260711_020304_12345678.tar.gz",
                filename="backup_20260711_020304_12345678.tar.gz",
            )
        )
        db.session.commit()
        stale_prefix_row = SystemConfig.query.filter_by(
            config_key="backup_prefix"
        ).one()
        assert stale_prefix_row.config_value == "backups/"
        other_session = sessionmaker(bind=db.engine)()
        try:
            other_session.query(SystemConfig).filter_by(
                config_key="backup_prefix"
            ).update({SystemConfig.config_value: "archives/"})
            other_session.commit()
        finally:
            other_session.close()

        assert stale_prefix_row.config_value == "backups/"

        with pytest.raises(
            BackupConfigValidationError,
            match="删除现有备份记录",
        ):
            BackupConfigService.save_config({"prefix": "backups/"})
        db.session.rollback()


@pytest.mark.parametrize(
    "endpoint",
    [
        VALID_ENDPOINT,
        "https://0123456789abcdef0123456789abcdef.eu.r2.cloudflarestorage.com",
        "https://0123456789abcdef0123456789abcdef.fedramp.r2.cloudflarestorage.com",
    ],
)
def test_r2_endpoint_accepts_only_supported_cloudflare_hosts(
    app, clean_backup_config, endpoint
):
    with app.app_context():
        result = BackupConfigService.save_config({**VALID_CONFIG, "endpoint": endpoint})
        assert result["endpoint"] == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com",
        "https://example.com",
        "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com:443",
        "https://user@0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com",
        f"{VALID_ENDPOINT}/bucket",
        f"{VALID_ENDPOINT}?x=1",
        f"{VALID_ENDPOINT}:",
        f"{VALID_ENDPOINT}?",
        f"{VALID_ENDPOINT}#",
        "https://0123456789ABCDEF0123456789ABCDEF.r2.cloudflarestorage.com",
        "https://short.r2.cloudflarestorage.com",
    ],
)
def test_r2_endpoint_rejects_noncanonical_or_unsafe_urls(
    app, clean_backup_config, endpoint
):
    with app.app_context(), pytest.raises(BackupConfigValidationError, match="endpoint"):
        BackupConfigService.save_config({**VALID_CONFIG, "endpoint": endpoint})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("region", "us-east-1"),
        ("bucket", "UPPER_CASE"),
        ("bucket", "ab"),
        ("bucket", "-invalid"),
        ("prefix", "/absolute/"),
        ("prefix", "../escape/"),
        ("prefix", "safe..but-invalid/"),
        ("prefix", "safe/almost../invalid"),
        ("prefix", "double//slash/"),
        ("prefix", "bad\\path"),
        ("retention_days", -1),
        ("retention_days", 3651),
        ("max_backups", 0),
        ("max_backups", 101),
    ],
)
def test_backup_config_rejects_invalid_fields(app, clean_backup_config, field, value):
    with app.app_context(), pytest.raises(BackupConfigValidationError, match=field):
        BackupConfigService.save_config({**VALID_CONFIG, field: value})


@pytest.mark.parametrize(
    "cron_expression",
    [
        "* * * * *",
        "0,30 * * * *",
        "*/15 * * * *",
        "0 * * *",
        "0 25 * * *",
        "0 2 * JAN *",
    ],
)
def test_cron_must_be_numeric_five_field_and_at_least_hourly(
    app, clean_backup_config, cron_expression
):
    with app.app_context(), pytest.raises(
        BackupConfigValidationError, match="cron_expression"
    ):
        BackupConfigService.save_config(
            {**VALID_CONFIG, "cron_expression": cron_expression}
        )


def test_save_encrypts_both_credentials_and_returns_only_masks(
    app, clean_backup_config
):
    with app.app_context():
        result = BackupConfigService.save_config(VALID_CONFIG, admin_id=7)
        access_row = SystemConfig.query.filter_by(
            config_key="backup_access_key_id"
        ).one()
        secret_row = SystemConfig.query.filter_by(
            config_key="backup_secret_access_key"
        ).one()

        assert access_row.config_value.startswith("enc:backup:v1:")
        assert secret_row.config_value.startswith("enc:backup:v1:")
        assert VALID_CONFIG["access_key_id"] not in access_row.config_value
        assert VALID_CONFIG["secret_access_key"] not in secret_row.config_value
        assert result["access_key_id"] != VALID_CONFIG["access_key_id"]
        assert result["secret_access_key"] != VALID_CONFIG["secret_access_key"]
        assert "*" in result["access_key_id"]
        assert "*" in result["secret_access_key"]
        assert result["access_key_id_configured"] is True
        assert result["secret_access_key_configured"] is True
        assert "provider" not in result
        assert "secret_configured" not in result


@pytest.mark.parametrize("replacement", ["", "   ", "****masked****"])
def test_empty_or_masked_credentials_preserve_existing_ciphertext(
    app, clean_backup_config, replacement
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        before = {
            row.config_key: row.config_value
            for row in SystemConfig.query.filter(
                SystemConfig.config_key.in_(
                    ("backup_access_key_id", "backup_secret_access_key")
                )
            ).all()
        }
        update = {
            **VALID_CONFIG,
            "access_key_id": replacement,
            "secret_access_key": replacement,
            "max_backups": 4,
        }
        result = BackupConfigService.save_config(update)
        after = {
            row.config_key: row.config_value
            for row in SystemConfig.query.filter(
                SystemConfig.config_key.in_(
                    ("backup_access_key_id", "backup_secret_access_key")
                )
            ).all()
        }

        assert after == before
        assert result["max_backups"] == 4


def test_empty_prefix_is_normalized_to_documented_default(app, clean_backup_config):
    with app.app_context():
        result = BackupConfigService.save_config({**VALID_CONFIG, "prefix": ""})
        stored = SystemConfig.query.filter_by(config_key="backup_prefix").one()

        assert stored.config_value == "backups/"
        assert result["prefix"] == "backups/"


def test_save_does_not_mutate_input_and_get_uses_documented_defaults(
    app, clean_backup_config
):
    with app.app_context():
        defaults = BackupConfigService.get_config()
        assert defaults == {
            "endpoint": "",
            "region": "auto",
            "bucket": "",
            "prefix": "backups/",
            "access_key_id": "",
            "secret_access_key": "",
            "access_key_id_configured": False,
            "secret_access_key_configured": False,
            "schedule_enabled": False,
            "cron_expression": "0 2 * * *",
            "retention_days": 14,
            "max_backups": 3,
        }

        submitted = deepcopy(VALID_CONFIG)
        snapshot = deepcopy(submitted)
        BackupConfigService.save_config(submitted)
        assert submitted == snapshot


def test_independent_partial_saves_only_update_submitted_plain_fields(
    app, clean_backup_config
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG, admin_id=7)
        storage_update = {"prefix": "archives/"}
        storage_snapshot = deepcopy(storage_update)
        storage_result = BackupConfigService.save_config(storage_update, admin_id=8)

        schedule_row = SystemConfig.query.filter_by(
            config_key="backup_cron_expression"
        ).one()
        storage_row = SystemConfig.query.filter_by(config_key="backup_prefix").one()
        assert schedule_row.updated_by == 7
        assert storage_row.updated_by == 8
        assert storage_update == storage_snapshot
        assert storage_result["prefix"] == "archives/"
        assert storage_result["cron_expression"] == VALID_CONFIG["cron_expression"]

        schedule_update = {"cron_expression": "15 3 * * *"}
        schedule_snapshot = deepcopy(schedule_update)
        schedule_result = BackupConfigService.save_config(schedule_update, admin_id=9)

        db.session.refresh(storage_row)
        db.session.refresh(schedule_row)
        assert storage_row.updated_by == 8
        assert schedule_row.updated_by == 9
        assert storage_row.config_value == "archives/"
        assert schedule_row.config_value == "15 3 * * *"
        assert schedule_update == schedule_snapshot
        assert schedule_result["prefix"] == "archives/"
        assert schedule_result["cron_expression"] == "15 3 * * *"


def test_generic_config_listing_never_exposes_backup_credentials(
    app, clean_backup_config
):
    with app.app_context():
        BackupConfigService.save_config(VALID_CONFIG)
        rows = {
            row["config_key"]: row["config_value"]
            for row in SystemConfigService.get_all_configs()
            if row["config_key"] in {
                "backup_access_key_id",
                "backup_secret_access_key",
            }
        }

        assert rows == {
            "backup_access_key_id": "***",
            "backup_secret_access_key": "***",
        }
        assert not any(value.startswith("enc:backup:v1:") for value in rows.values())


@pytest.mark.parametrize(
    "config_key", ["backup_access_key_id", "backup_secret_access_key"]
)
def test_generic_config_update_rejects_backup_credentials(
    app, clean_backup_config, config_key
):
    with app.app_context(), pytest.raises(ValueError, match="备份凭据"):
        SystemConfigService.update_config(config_key, "plaintext-must-not-be-stored")

    with app.app_context():
        assert SystemConfig.query.filter_by(config_key=config_key).first() is None


def test_backup_config_save_rolls_back_all_fields_and_keeps_cache_on_midway_failure(
    app, clean_backup_config, monkeypatch
):
    with app.app_context():
        before = {
            row["config_key"]: row["config_value"]
            for row in SystemConfigService.get_all_configs()
            if row["config_key"].startswith("backup_")
        }
        original_add = db.session.add
        backup_add_count = 0

        def fail_on_fourth_backup_row(instance):
            nonlocal backup_add_count
            if isinstance(instance, SystemConfig) and instance.config_key.startswith(
                "backup_"
            ):
                backup_add_count += 1
                if backup_add_count == 4:
                    raise RuntimeError("simulated midway write failure")
            return original_add(instance)

        monkeypatch.setattr(db.session, "add", fail_on_fourth_backup_row)

        with pytest.raises(RuntimeError, match="simulated midway write failure"):
            BackupConfigService.save_config(VALID_CONFIG)

        stored = {
            row.config_key: row.config_value
            for row in SystemConfig.query.filter(
                SystemConfig.config_key.like("backup_%")
            ).all()
        }
        cached = {
            row["config_key"]: row["config_value"]
            for row in SystemConfigService.get_all_configs()
            if row["config_key"].startswith("backup_")
        }

        assert backup_add_count == 4
        assert stored == before == cached


def test_backup_job_serializes_datetimes_as_iso_strings():
    moment = datetime(2026, 7, 11, 2, 3, 4)
    job = BackupJob(
        id="12345678-1234-1234-1234-123456789abc",
        status="completed",
        trigger="scheduled",
        started_at=moment,
        completed_at=moment,
        expires_at=moment,
        created_at=moment,
    )

    payload = job.to_dict()

    assert payload["started_at"] == "2026-07-11T02:03:04Z"
    assert payload["completed_at"] == "2026-07-11T02:03:04Z"
    assert payload["expires_at"] == "2026-07-11T02:03:04Z"
    assert payload["created_at"] == "2026-07-11T02:03:04Z"
