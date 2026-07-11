# -*- coding: utf-8 -*-
"""管理员备份 API 的权限、请求边界与安全响应测试。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.jwt_utils import generate_jwt_token
from app.core.utils.user_state_cache import invalidate_user_state
from app.models.backup import BackupJob
from app.modules.admin.routes.api_components import backup_settings
from app.modules.admin.services.backup_config_service import (
    BackupConfigError,
    BackupConfigValidationError,
)
from app.modules.admin.services.backup_job_service import (
    BackupJobService,
)


VALID_CONFIG = {
    "endpoint": "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com",
    "region": "auto",
    "bucket": "ti-backups",
    "prefix": "backups/",
    "access_key_id": "saved-access-key",
    "secret_access_key": "saved-secret-key",
    "schedule_enabled": True,
    "cron_expression": "0 2 * * *",
    "retention_days": 14,
    "max_backups": 3,
}
PUBLIC_CONFIG = {
    **VALID_CONFIG,
    "access_key_id": "save****-key",
    "secret_access_key": "save****-key",
    "access_key_id_configured": True,
    "secret_access_key_configured": True,
}
XHR_HEADERS = {"X-Requested-With": "XMLHttpRequest"}
WRITE_HEADERS = {**XHR_HEADERS, "Origin": "http://localhost"}


def _assert_permission_error(response, status_code):
    assert response.status_code == status_code
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["code"] == 1


@pytest.fixture(autouse=True)
def reset_backup_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def role_client_factory(app, seed_user):
    user_id = int(seed_user["id"])

    def make(*, admin=False, subject=False, notification=False):
        with app.app_context():
            db.session.execute(
                text(
                    "UPDATE users SET is_admin=:admin, is_subject_admin=:subject, "
                    "is_notification_admin=:notification, is_locked=false WHERE id=:uid"
                ),
                {
                    "uid": user_id,
                    "admin": bool(admin),
                    "subject": bool(subject),
                    "notification": bool(notification),
                },
            )
            db.session.commit()
            invalidate_user_state(user_id)
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = seed_user["username"]
            sess["is_admin"] = bool(admin)
            sess["is_subject_admin"] = bool(subject)
            sess["is_notification_admin"] = bool(notification)
            sess["session_version"] = 0
        return client

    yield make
    with app.app_context():
        db.session.execute(
            text(
                "UPDATE users SET is_admin=false, is_subject_admin=false, "
                "is_notification_admin=false WHERE id=:uid"
            ),
            {"uid": user_id},
        )
        db.session.commit()
        invalidate_user_state(user_id)


@pytest.fixture
def admin_client(role_client_factory):
    return role_client_factory(admin=True)


class FakeConfigService:
    def __init__(self, *, runtime=None, save_error=None):
        self.runtime = dict(runtime or VALID_CONFIG)
        self.save_error = save_error
        self.saved = []

    def get_config(self):
        return dict(PUBLIC_CONFIG)

    def get_runtime_config(self):
        return dict(self.runtime)

    def save_config(self, data, admin_id=None):
        self.saved.append((dict(data), admin_id))
        if self.save_error:
            raise self.save_error
        return dict(PUBLIC_CONFIG)


@dataclass
class FakeJob:
    id: str
    status: str = "queued"

    def to_dict(self):
        return {"id": self.id, "status": self.status, "trigger": "manual"}


class FakeJobService:
    def __init__(self):
        self.created_by = None
        self.list_limit = None
        self.downloaded = None
        self.deleted = None
        self.jobs = [{"id": str(uuid4()), "status": "completed"}]
        self.url = "https://signed.invalid/secret-signature"
        self.error = None

    def create_manual_job(self, created_by=None):
        self.created_by = created_by
        return FakeJob(str(uuid4()))

    def list_jobs(self, *, limit=100):
        self.list_limit = limit
        return list(self.jobs)

    def download_url(self, job_id):
        self.downloaded = job_id
        if self.error:
            raise self.error
        return self.url

    def delete_completed_job(self, job_id):
        self.deleted = job_id
        if self.error:
            raise self.error
        return True


class FakeRealJobStorage:
    def __init__(self):
        self.deleted = []

    def generate_presigned_url(self, object_key):
        return "https://signed.invalid/real-job"

    def delete_object(self, object_key):
        self.deleted.append(object_key)


def _patch_services(monkeypatch, *, config=None, jobs=None, storage_factory=None):
    config = config or FakeConfigService()
    jobs = jobs or FakeJobService()
    monkeypatch.setattr(backup_settings, "backup_config_service_factory", lambda: config)
    monkeypatch.setattr(backup_settings, "backup_job_service_factory", lambda: jobs)
    if storage_factory is not None:
        monkeypatch.setattr(backup_settings, "backup_storage_service_factory", storage_factory)
    return config, jobs


def _patch_real_job_service(monkeypatch, *, config=None, storage=None):
    service = BackupJobService(
        config_service=config or FakeConfigService(),
        storage_service=storage or FakeRealJobStorage(),
    )
    monkeypatch.setattr(
        backup_settings, "backup_job_service_factory", lambda: service
    )
    return service


@pytest.fixture
def clean_api_backup_jobs(app):
    with app.app_context():
        BackupJob.query.delete(synchronize_session=False)
        db.session.commit()
        yield
        db.session.rollback()
        BackupJob.query.delete(synchronize_session=False)
        db.session.commit()


@pytest.fixture
def real_job_factory(app, clean_api_backup_jobs):
    def create(status):
        job_id = str(uuid4())
        with app.app_context():
            db.session.add(
                BackupJob(
                    id=job_id,
                    status=status,
                    trigger="manual",
                    object_key=(
                        f"backups/backup_20260711_020304_{job_id[:8]}.tar.gz"
                        if status == "completed"
                        else None
                    ),
                )
            )
            db.session.commit()
        return job_id

    return create


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admin/api/settings/backup"),
        ("post", "/admin/api/settings/backup"),
        ("post", "/admin/api/settings/backup/test"),
        ("get", "/admin/api/backups"),
        ("post", "/admin/api/backups"),
        ("get", f"/admin/api/backups/{uuid4()}/download"),
        ("delete", f"/admin/api/backups/{uuid4()}"),
    ],
)
def test_backup_api_requires_login(client, method, path):
    response = getattr(client, method)(path, headers=XHR_HEADERS, json={})
    _assert_permission_error(response, 401)


@pytest.mark.parametrize(
    "path",
    [
        "/admin/api/settings/backup-old",
        "/admin/api/settings/backup/test/extra",
        "/admin/api/backups-xxx",
        "/admin/api/backups/not-a-uuid",
        f"/admin/api/backups/{uuid4()}/download/extra",
    ],
)
def test_backup_path_detection_does_not_match_similar_routes(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("role", ["ordinary", "subject", "notification"])
def test_backup_api_rejects_non_full_admin(role_client_factory, role):
    client = role_client_factory(
        subject=role == "subject", notification=role == "notification"
    )
    response = client.get("/admin/api/settings/backup")
    _assert_permission_error(response, 403)


def test_backup_api_rejects_jwt_only_admin_with_json_401(
    app, seed_user, role_client_factory
):
    role_client_factory(admin=True)
    with app.app_context():
        token = generate_jwt_token(
            user_id=int(seed_user["id"]), openid="", session_version=0
        )
    response = app.test_client().get(
        "/admin/api/settings/backup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["code"] == 1
    assert payload["message"] == "请使用管理员会话登录"


def test_backup_api_rejects_jwt_only_ordinary_user_with_error_envelope(
    app, seed_user, role_client_factory
):
    role_client_factory()
    with app.app_context():
        token = generate_jwt_token(
            user_id=int(seed_user["id"]), openid="", session_version=0
        )
    response = app.test_client().get(
        "/admin/api/settings/backup",
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert_permission_error(response, 403)


def test_database_permission_revocation_takes_effect_immediately(
    app, seed_user, admin_client
):
    assert admin_client.get("/admin/api/settings/backup").status_code == 200
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin=false WHERE id=:uid"),
            {"uid": int(seed_user["id"])},
        )
        db.session.commit()
    response = admin_client.get("/admin/api/settings/backup")
    _assert_permission_error(response, 403)


def test_revoked_old_session_cannot_be_rescued_by_valid_jwt(
    app, seed_user, admin_client
):
    with app.app_context():
        token = generate_jwt_token(
            user_id=int(seed_user["id"]), openid="", session_version=0
        )
        db.session.execute(
            text("UPDATE users SET is_admin=false WHERE id=:uid"),
            {"uid": int(seed_user["id"])},
        )
        db.session.commit()

    response = admin_client.get(
        "/admin/api/settings/backup",
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert_permission_error(response, 403)


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/admin/api/settings/backup"),
        ("post", "/admin/api/settings/backup/test"),
        ("post", "/admin/api/backups"),
        ("delete", f"/admin/api/backups/{uuid4()}"),
    ],
)
def test_write_routes_require_xhr_header(admin_client, method, path):
    response = getattr(admin_client, method)(
        path, headers={"Origin": "http://localhost"}, json={}
    )
    assert response.status_code == 403
    assert response.get_json()["status"] == "error"


def test_write_routes_require_origin_or_referer(admin_client, monkeypatch):
    _patch_services(monkeypatch)
    response = admin_client.post(
        "/admin/api/backups", headers=XHR_HEADERS, json={}
    )
    _assert_permission_error(response, 403)


@pytest.mark.parametrize(
    "source_headers",
    [
        {"Origin": "https://evil.example"},
        {"Referer": "https://evil.example/admin"},
        {"Origin": "null"},
        {"Origin": "http://localhost:bad"},
        {"Origin": "http://localhost", "Referer": "https://evil.example/x"},
    ],
)
def test_write_routes_reject_cross_origin_or_malformed_sources(
    admin_client, source_headers
):
    response = admin_client.post(
        "/admin/api/backups", headers={**XHR_HEADERS, **source_headers}, json={}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "source_headers",
    [
        {"Origin": "http://localhost"},
        {"Referer": "http://localhost/admin/settings/backup"},
    ],
)
def test_same_origin_write_is_allowed(admin_client, monkeypatch, source_headers):
    _patch_services(monkeypatch)
    response = admin_client.post(
        "/admin/api/backups",
        base_url="http://localhost",
        headers={**XHR_HEADERS, **source_headers},
        json={},
    )
    assert response.status_code == 200


def test_get_config_returns_only_service_public_dto(admin_client, monkeypatch):
    _patch_services(monkeypatch)
    response = admin_client.get("/admin/api/settings/backup")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "success" and payload["code"] == 0
    assert payload["data"] == PUBLIC_CONFIG
    assert VALID_CONFIG["secret_access_key"] not in response.get_data(as_text=True)


def test_save_config_validates_object_and_unknown_fields(admin_client, monkeypatch):
    config, _ = _patch_services(monkeypatch)
    bad_shape = admin_client.post(
        "/admin/api/settings/backup", headers=WRITE_HEADERS, json=[VALID_CONFIG]
    )
    unknown = admin_client.post(
        "/admin/api/settings/backup",
        headers=WRITE_HEADERS,
        json={**VALID_CONFIG, "object_key": "attacker-controlled"},
    )
    assert bad_shape.status_code == 400
    assert unknown.status_code == 400
    assert config.saved == []


def test_save_config_returns_masked_dto_and_admin_id(
    admin_client, seed_user, monkeypatch
):
    config, _ = _patch_services(monkeypatch)
    response = admin_client.post(
        "/admin/api/settings/backup", headers=WRITE_HEADERS, json=VALID_CONFIG
    )
    assert response.status_code == 200
    assert response.get_json()["data"] == PUBLIC_CONFIG
    assert config.saved == [(VALID_CONFIG, int(seed_user["id"]))]
    assert VALID_CONFIG["secret_access_key"] not in response.get_data(as_text=True)


def test_save_validation_error_is_safe(admin_client, monkeypatch):
    config = FakeConfigService(
        save_error=BackupConfigValidationError("endpoint: 地址格式无效")
    )
    _patch_services(monkeypatch, config=config)
    response = admin_client.post(
        "/admin/api/settings/backup", headers=WRITE_HEADERS, json=VALID_CONFIG
    )
    assert response.status_code == 400
    assert response.get_json()["message"] == "endpoint: 地址格式无效"
    assert VALID_CONFIG["secret_access_key"] not in response.get_data(as_text=True)


def test_connection_uses_only_saved_runtime_config(admin_client, monkeypatch):
    seen = []

    class Storage:
        def test_connection(self):
            seen.append("tested")

    config = FakeConfigService(runtime=VALID_CONFIG)
    _patch_services(
        monkeypatch,
        config=config,
        storage_factory=lambda runtime: seen.append(runtime) or Storage(),
    )
    response = admin_client.post(
        "/admin/api/settings/backup/test",
        headers=WRITE_HEADERS,
        json={"secret_access_key": "request-secret-must-be-ignored"},
    )
    assert response.status_code == 200
    assert seen == [VALID_CONFIG, "tested"]


def test_connection_failure_returns_safe_summary(
    admin_client, monkeypatch, caplog
):
    class Storage:
        def test_connection(self):
            raise RuntimeError("upstream Authorization=credential-leak")

    _patch_services(monkeypatch, storage_factory=lambda runtime: Storage())
    with caplog.at_level("ERROR"):
        response = admin_client.post(
            "/admin/api/settings/backup/test", headers=WRITE_HEADERS, json={}
        )
    assert response.status_code == 502
    assert "credential-leak" not in response.get_data(as_text=True)
    assert "credential-leak" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_create_requires_complete_runtime_config(admin_client, monkeypatch):
    config = FakeConfigService()
    config.get_runtime_config = lambda: (_ for _ in ()).throw(
        BackupConfigError("凭据缺失 secret-value")
    )
    _patch_services(monkeypatch, config=config)
    response = admin_client.post(
        "/admin/api/backups", headers=WRITE_HEADERS, json={}
    )
    assert response.status_code == 400
    assert "secret-value" not in response.get_data(as_text=True)


def test_create_returns_job_dto_and_session_user(
    admin_client, seed_user, monkeypatch
):
    _, jobs = _patch_services(monkeypatch)
    response = admin_client.post(
        "/admin/api/backups", headers=WRITE_HEADERS, json={}
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "queued"
    assert jobs.created_by == int(seed_user["id"])


@pytest.mark.parametrize("limit", ["0", "201", "x", "1.5", ""])
def test_list_rejects_invalid_limit(admin_client, monkeypatch, limit):
    _, jobs = _patch_services(monkeypatch)
    response = admin_client.get(f"/admin/api/backups?limit={limit}")
    assert response.status_code == 400
    assert jobs.list_limit is None


def test_list_accepts_limit_1_to_200(admin_client, monkeypatch):
    _, jobs = _patch_services(monkeypatch)
    response = admin_client.get("/admin/api/backups?limit=200")
    assert response.status_code == 200
    assert response.get_json()["data"] == {"items": jobs.jobs, "limit": 200}
    assert jobs.list_limit == 200


@pytest.mark.parametrize(
    ("method", "path", "allowed_count", "payload"),
    [
        ("get", "/admin/api/settings/backup", 60, None),
        ("post", "/admin/api/settings/backup", 10, VALID_CONFIG),
        ("post", "/admin/api/settings/backup/test", 5, {}),
        ("get", "/admin/api/backups?limit=1", 60, None),
        ("post", "/admin/api/backups", 3, {}),
        ("get", f"/admin/api/backups/{uuid4()}/download", 10, None),
        ("delete", f"/admin/api/backups/{uuid4()}", 10, None),
    ],
)
def test_all_backup_rate_limits_return_json_error_envelope(
    admin_client, monkeypatch, method, path, allowed_count, payload
):
    _patch_services(
        monkeypatch,
        storage_factory=lambda runtime: type(
            "Storage", (), {"test_connection": lambda self: None}
        )(),
    )
    headers = WRITE_HEADERS if method in {"post", "delete"} else {}
    limiter.reset()
    try:
        responses = [
            getattr(admin_client, method)(path, headers=headers, json=payload)
            for _ in range(allowed_count + 1)
        ]
        assert all(
            response.status_code == 200 for response in responses[:allowed_count]
        )
        limited = responses[allowed_count]
        assert limited.status_code == 429
        assert limited.mimetype == "application/json"
        payload = limited.get_json()
        assert payload["status"] == "error"
        assert payload["code"] == 1
    finally:
        limiter.reset()


def test_download_uses_uuid_and_disables_cache(admin_client, monkeypatch):
    _, jobs = _patch_services(monkeypatch)
    job_id = uuid4()
    response = admin_client.get(f"/admin/api/backups/{job_id}/download")
    assert response.status_code == 200
    assert jobs.downloaded == str(job_id)
    assert response.get_json()["data"] == {"url": jobs.url, "expires_in": 300}
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/admin/api/backups/not-a-uuid/download"),
        ("delete", "/admin/api/backups/not-a-uuid"),
    ],
)
def test_invalid_job_uuid_returns_json_404(admin_client, method, path):
    headers = WRITE_HEADERS if method == "delete" else {}
    response = getattr(admin_client, method)(path, headers=headers)
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["code"] == 1
    assert payload["message"] == "备份任务不存在"


def test_delete_passes_only_uuid_to_service(admin_client, monkeypatch):
    _, jobs = _patch_services(monkeypatch)
    job_id = uuid4()
    response = admin_client.delete(
        f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
    )
    assert response.status_code == 200
    assert jobs.deleted == str(job_id)


def test_delete_failure_does_not_log_exception_details(
    admin_client, monkeypatch, caplog
):
    jobs = FakeJobService()
    jobs.error = RuntimeError("credential-leak-in-delete")
    _patch_services(monkeypatch, jobs=jobs)
    with caplog.at_level("ERROR"):
        response = admin_client.delete(
            f"/admin/api/backups/{uuid4()}", headers=WRITE_HEADERS
        )
    assert response.status_code == 502
    assert "credential-leak" not in response.get_data(as_text=True)
    assert "credential-leak" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_generic_route_failure_logs_only_safe_exception_type(
    admin_client, monkeypatch, caplog
):
    config = FakeConfigService()
    config.get_config = lambda: (_ for _ in ()).throw(
        RuntimeError("credential-leak-in-config")
    )
    _patch_services(monkeypatch, config=config)
    with caplog.at_level("ERROR"):
        response = admin_client.get(
            "/admin/api/settings/backup",
            headers={"X-Request-ID": "credential-leak-request-id"},
        )
    assert response.status_code == 500
    assert "credential-leak" not in caplog.text
    assert "RuntimeError" in caplog.text


@pytest.mark.parametrize("operation", ["download", "delete"])
def test_real_missing_job_returns_exact_404(
    admin_client, monkeypatch, clean_api_backup_jobs, operation
):
    _patch_real_job_service(monkeypatch)
    job_id = uuid4()
    if operation == "download":
        response = admin_client.get(f"/admin/api/backups/{job_id}/download")
    else:
        response = admin_client.delete(
            f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
        )
    assert response.status_code == 404
    _assert_permission_error(response, 404)


@pytest.mark.parametrize("operation", ["download", "delete"])
@pytest.mark.parametrize("status", ["queued", "running"])
def test_real_active_job_state_returns_exact_409(
    admin_client, monkeypatch, real_job_factory, operation, status
):
    _patch_real_job_service(monkeypatch)
    job_id = real_job_factory(status)
    if operation == "download":
        response = admin_client.get(f"/admin/api/backups/{job_id}/download")
    else:
        response = admin_client.delete(
            f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
        )
    assert response.status_code == 409
    _assert_permission_error(response, 409)


@pytest.mark.parametrize("operation", ["download", "delete"])
def test_real_completed_job_is_accepted(
    admin_client, monkeypatch, real_job_factory, operation
):
    _patch_real_job_service(monkeypatch)
    job_id = real_job_factory("completed")
    if operation == "download":
        response = admin_client.get(f"/admin/api/backups/{job_id}/download")
        assert response.get_json()["data"]["url"].startswith("https://signed.invalid/")
    else:
        response = admin_client.delete(
            f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
        )
    assert response.status_code == 200


@pytest.mark.parametrize("operation", ["download", "delete"])
def test_service_value_error_is_safe_5xx_not_404(
    admin_client, monkeypatch, caplog, operation
):
    jobs = FakeJobService()
    jobs.error = ValueError("https://signed.invalid/secret-token")
    _patch_services(monkeypatch, jobs=jobs)
    job_id = uuid4()
    with caplog.at_level("ERROR"):
        if operation == "download":
            response = admin_client.get(f"/admin/api/backups/{job_id}/download")
        else:
            response = admin_client.delete(
                f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
            )
    assert response.status_code == 502
    assert "secret-token" not in response.get_data(as_text=True)
    assert "secret-token" not in caplog.text
    assert "ValueError" in caplog.text


@pytest.mark.parametrize("operation", ["download", "delete"])
def test_database_lookup_failure_is_safe_5xx(
    app, admin_client, monkeypatch, clean_api_backup_jobs, caplog, operation
):
    _patch_real_job_service(monkeypatch)

    def fail_lookup(*args, **kwargs):
        raise RuntimeError("database query secret detail")

    monkeypatch.setattr(db.session, "get", fail_lookup)
    job_id = uuid4()
    with caplog.at_level("ERROR"):
        if operation == "download":
            response = admin_client.get(f"/admin/api/backups/{job_id}/download")
        else:
            response = admin_client.delete(
                f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
            )
    assert response.status_code == 502
    assert "secret detail" not in response.get_data(as_text=True)
    assert "secret detail" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_delete_config_error_is_safe_5xx_and_keeps_deleting(
    app, admin_client, monkeypatch, real_job_factory, caplog
):
    class InvalidConfig:
        @staticmethod
        def get_runtime_config():
            raise BackupConfigValidationError("configuration secret detail")

    _patch_real_job_service(monkeypatch, config=InvalidConfig)
    job_id = real_job_factory("completed")
    with caplog.at_level("ERROR"):
        response = admin_client.delete(
            f"/admin/api/backups/{job_id}", headers=WRITE_HEADERS
        )

    assert response.status_code == 502
    assert "secret detail" not in response.get_data(as_text=True)
    assert "secret detail" not in caplog.text
    assert "BackupConfigValidationError" in caplog.text
    with app.app_context():
        retained = db.session.get(BackupJob, job_id)
        assert retained is not None
        assert retained.status == "deleting"
