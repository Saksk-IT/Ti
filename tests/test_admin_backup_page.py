# -*- coding: utf-8 -*-
"""管理员数据备份页面的入口、交互契约与前端安全回归测试。"""

from pathlib import Path

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.user_state_cache import invalidate_user_state


ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = ROOT / "app/modules/admin/routes/pages.py"
INDEX_PATH = ROOT / "app/modules/admin/templates/admin/settings/index.html"
BACKUP_PATH = ROOT / "app/modules/admin/templates/admin/settings/backup.html"


def _set_admin(app, seed_user, enabled):
    user_id = int(seed_user["id"])
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin=:enabled WHERE id=:uid"),
            {"enabled": bool(enabled), "uid": user_id},
        )
        db.session.commit()
        invalidate_user_state(user_id)


def _session_client(app, seed_user, *, admin):
    _set_admin(app, seed_user, admin)
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = int(seed_user["id"])
        session["username"] = seed_user["username"]
        session["is_admin"] = admin
        session["session_version"] = 0
    return client


def test_backup_settings_entry_and_page_require_full_admin(app, seed_user):
    index_source = INDEX_PATH.read_text(encoding="utf-8")
    pages_source = PAGES_PATH.read_text(encoding="utf-8")
    anonymous = app.test_client()

    try:
        assert 'href="/admin/settings/backup"' in index_source
        assert "数据备份" in index_source
        assert "@admin_pages_bp.route('/settings/backup')\n@admin_required" in pages_source
        assert "admin/settings/backup.html" in pages_source

        assert anonymous.get("/admin/settings/backup").status_code == 302
        assert _session_client(app, seed_user, admin=False).get(
            "/admin/settings/backup"
        ).status_code in {302, 403}

        response = _session_client(app, seed_user, admin=True).get(
            "/admin/settings/backup"
        )
        assert response.status_code == 200
        assert "Cloudflare R2 存储配置" in response.get_data(as_text=True)
    finally:
        _set_admin(app, seed_user, False)


def test_backup_page_exposes_required_fields_and_all_seven_api_calls():
    source = BACKUP_PATH.read_text(encoding="utf-8")

    for field in (
        "endpoint",
        "region",
        "bucket",
        "prefix",
        "access_key_id",
        "secret_access_key",
        "schedule_enabled",
        "cron_expression",
        "retention_days",
        "max_backups",
    ):
        assert f'id="{field}"' in source

    assert 'id="region" value="auto" readonly' in source
    assert 'value="0 2 * * *"' in source
    for endpoint in (
        "'/admin/api/settings/backup'",
        "'/admin/api/settings/backup/test'",
        "'/admin/api/backups'",
        "`/admin/api/backups/${jobId}/download`",
        "`/admin/api/backups/${jobId}`",
    ):
        assert endpoint in source

    assert "method: 'GET'" in source
    assert "method: 'POST'" in source
    assert "method: 'DELETE'" in source
    assert source.count("X-Requested-With") >= 1
    assert "XMLHttpRequest" in source
    assert "saveStorageConfig({ silent: true })" in source


def test_backup_page_contains_records_actions_tutorials_and_accessible_modals():
    source = BACKUP_PATH.read_text(encoding="utf-8")

    for text_value in (
        "备份记录",
        "状态",
        "文件名",
        "大小",
        "过期时间",
        "触发方式",
        "开始时间",
        "操作",
        "创建备份",
        "刷新",
        "下载",
        "恢复",
        "删除",
        "重试删除",
        "创建私有 Bucket",
        "Manage API Tokens",
        "Object Read &amp; Write",
        "仅指定 Bucket",
        "一次性 Secret",
        "https://developers.cloudflare.com/r2/",
        "服务器维护窗口",
        "下载到 backups",
        "校验 SHA",
        "ENV_FILE=.env.production COMPOSE_FILE=compose.prod.yml ./scripts/restore.sh",
    ):
        assert text_value in source

    assert source.count('role="dialog"') == 2
    assert source.count('aria-modal="true"') == 2
    assert 'aria-labelledby="r2TutorialTitle"' in source
    assert 'aria-labelledby="restoreTutorialTitle"' in source
    assert "event.key === 'Escape'" in source
    assert "event.target === modal" in source
    assert "document.body.style.overflow = 'hidden'" in source
    assert "previousFocus.focus()" in source
    assert "data-id" in source
    assert "recordsById" in source
    assert "record.status === 'deleting'" in source


def test_backup_page_is_responsive_and_avoids_remote_html_injection():
    source = BACKUP_PATH.read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in source
    assert "@media (max-width: 768px)" in source
    assert "grid-template-columns: 1fr" in source
    assert "min-height: 44px" in source
    assert "overflow-x: hidden" in source
    assert ".backup-section" in source
    assert "textContent" in source
    assert ".innerHTML" not in source
    assert "console.log" not in source
    assert "console.error" not in source
    assert "docker.sock" not in source
    assert "/admin/api/backups/${jobId}/restore" not in source
    assert "window.location.assign(downloadUrl)" in source
    assert "queued" in source and "running" in source
    assert "setInterval" not in source
    assert "window.setTimeout" in source
    assert "confirm(" in source


def test_backup_records_ignore_stale_responses_and_cleanup_async_work():
    source = BACKUP_PATH.read_text(encoding="utf-8")

    assert "let recordsRequestSequence = 0" in source
    assert "let recordsAbortController = null" in source
    assert "new AbortController()" in source
    assert "requestSequence !== recordsRequestSequence" in source
    assert "let recordsRequestInFlight = false" in source
    assert "abortPrevious = true" in source
    assert "if (recordsRequestInFlight && !abortPrevious) return" in source
    assert "signal: requestController.signal" in source
    assert "loadRecords({ quiet: true, abortPrevious: false })" in source
    assert "scheduleNextPoll()" in source
    assert "error.name === 'AbortError'" in source
    assert "window.addEventListener('beforeunload'" in source
    assert "recordsAbortController.abort()" in source
    assert "window.clearTimeout(pollTimer)" in source


def test_backup_polling_retries_transient_errors_only_after_last_active_result():
    source = BACKUP_PATH.read_text(encoding="utf-8")
    polling_source = source.split("function clearPollTimer", 1)[1].split(
        "function backgroundElements", 1
    )[0]
    catch_source = polling_source.split("} catch (error) {", 1)[1].split(
        "} finally {", 1
    )[0]

    assert "let shouldPollRecords = false" in source
    assert "function hasActiveRecords(items)" in polling_source
    assert "item.status === 'queued' || item.status === 'running'" in polling_source
    assert "shouldPollRecords = hasActiveRecords(items)" in polling_source
    assert "if (shouldPollRecords) scheduleNextPoll()" in polling_source
    assert "scheduleNextPoll(items)" not in polling_source
    assert "shouldPollRecords = false" not in catch_source
    assert "loadRecords({ quiet: true, abortPrevious: false })" in polling_source
    assert "}, 4000);" in polling_source


def test_backup_modals_trap_focus_and_isolate_then_restore_background():
    source = BACKUP_PATH.read_text(encoding="utf-8")

    assert "getFocusableElements" in source
    assert "event.key === 'Tab'" in source
    assert "event.shiftKey" in source
    assert "firstFocusable.focus()" in source
    assert "lastFocusable.focus()" in source
    for selector in ("'.backup-page'", "'.sidebar'", "'.theme-toggle'"):
        assert selector in source
    assert "element.inert = true" in source
    assert "element.setAttribute('aria-hidden', 'true')" in source
    assert "element.inert = state.inert" in source
    assert "element.removeAttribute('aria-hidden')" in source


def test_backup_page_overrides_admin_shell_on_mobile_and_refreshes_saved_config():
    source = BACKUP_PATH.read_text(encoding="utf-8")

    assert ".backup-page, .backup-page * { box-sizing: border-box; }" in source
    assert "body { display: block; }" in source
    assert ".sidebar { position: static; width: 100%; height: auto;" in source
    assert ".sidebar::before, .sidebar::after { display: none; }" in source
    assert ".main-content { margin-left: 0; width: 100%; max-width: none; padding: 0;" in source
    assert ".sidebar-nav { display: flex; overflow-x: auto;" in source
    assert "function applyStorageConfig(config)" in source
    assert "function applyScheduleConfig(config)" in source
    assert "function applyConfig(config)" in source
    assert "access_key_id_configured" in source
    assert "secret_access_key_configured" in source
    assert "cell.setAttribute('role', 'cell')" in source

    storage_save = source.split("async function saveStorageConfig", 1)[1].split(
        "async function loadConfig", 1
    )[0]
    full_load = source.split("async function loadConfig", 1)[1].split(
        "function formatSize", 1
    )[0]
    schedule_save = source.split("scheduleForm.addEventListener", 1)[1].split(
        "testConnectionBtn.addEventListener", 1
    )[0]
    assert "applyStorageConfig(payload.data || {})" in storage_save
    assert "applyScheduleConfig" not in storage_save
    assert "applyConfig(payload.data || {})" in full_load
    assert "applyScheduleConfig(payload.data || {})" in schedule_save
    assert "applyStorageConfig" not in schedule_save
