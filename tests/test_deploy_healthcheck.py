# -*- coding: utf-8 -*-
import sys
import types
import os
import re
import subprocess
import tarfile
import textwrap
from pathlib import Path

import pytest


def _compose_service_section(compose_text, service_name):
    marker = f"\n  {service_name}:"
    start = compose_text.index(marker)
    next_service = re.search(
        r"\n  [A-Za-z0-9_-]+:", compose_text[start + len(marker):]
    )
    end = (
        len(compose_text)
        if next_service is None
        else start + len(marker) + next_service.start()
    )
    return compose_text[start:end]


def _shell_function_section(script_text, function_name):
    marker = f"\n{function_name}() {{"
    start = script_text.index(marker)
    next_function = re.search(
        r"\n[a-zA-Z_][a-zA-Z0-9_]*\(\) \{",
        script_text[start + len(marker):],
    )
    end = (
        len(script_text)
        if next_function is None
        else start + len(marker) + next_function.start()
    )
    return script_text[start:end]


def test_default_admin_cli_is_registered(app):
    assert "ensure-default-admin" in app.cli.commands


def test_redis_connection_uses_bounded_connect_timeout(monkeypatch):
    captured = {}

    class FakeRedis:
        @staticmethod
        def from_url(url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return object()

    fake_redis_module = types.SimpleNamespace(Redis=FakeRedis)
    monkeypatch.setitem(sys.modules, "redis", fake_redis_module)
    monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", "1.5")

    from app.core.utils.redis_utils import get_redis_connection

    conn = get_redis_connection("redis://redis:6379/0")

    assert conn is not None
    assert captured["url"] == "redis://redis:6379/0"
    assert captured["kwargs"]["decode_responses"] is False
    assert captured["kwargs"]["socket_connect_timeout"] == 1.5
    assert captured["kwargs"]["socket_timeout"] is None


def test_deep_ping_uses_short_redis_timeouts(client, monkeypatch):
    captured = {}

    class FakeRedis:
        def ping(self):
            return True

    def fake_get_redis_connection(**kwargs):
        captured.update(kwargs)
        return FakeRedis()

    from app.core.utils import redis_utils

    monkeypatch.setattr(redis_utils, "get_redis_connection", fake_get_redis_connection)
    monkeypatch.setenv("HEALTHCHECK_REDIS_TIMEOUT_SECONDS", "0.75")

    resp = client.get("/api/ping?deep=1")

    assert resp.status_code == 200
    assert captured["socket_connect_timeout"] == 0.75
    assert captured["socket_timeout"] == 0.75


def test_ping_is_exempt_from_default_rate_limit(app, monkeypatch):
    app.config["RATELIMIT_DEFAULT"] = "1 per day"

    with app.test_client() as client:
        first = client.get("/api/ping")
        second = client.get("/api/ping")
        third = client.get("/api/ping")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200


def test_production_web_healthcheck_uses_tcp_probe():
    compose_text = Path("compose.prod.yml").read_text(encoding="utf-8")

    assert "socket.create_connection" in compose_text
    assert "urllib.request.urlopen('http://localhost:8000/api/ping')" not in compose_text


def test_production_compose_relaxes_rate_limit_defaults():
    compose_text = Path("compose.prod.yml").read_text(encoding="utf-8")

    assert "RATELIMIT_LIMIT_MULTIPLIER: ${RATELIMIT_LIMIT_MULTIPLIER:-100}" in compose_text
    assert 'RATELIMIT_DEFAULT: "${RATELIMIT_DEFAULT:-500000/day;50000/hour;1000/second}"' in compose_text
    assert "RATELIMIT_DEFAULT: ${RATELIMIT_DEFAULT:-}" not in compose_text


def test_production_compose_disables_sse_by_default():
    compose_text = Path("compose.prod.yml").read_text(encoding="utf-8")

    assert "SSE_ENABLED: ${SSE_ENABLED:-false}" in compose_text
    assert "SSE_RETRY_AFTER_SECONDS: ${SSE_RETRY_AFTER_SECONDS:-300}" in compose_text


def test_production_compose_waits_for_redis_health():
    compose_text = Path("compose.prod.yml").read_text(encoding="utf-8")

    assert 'test: ["CMD", "redis-cli", "ping"]' in compose_text

    for service_name in ("web", "worker", "backup"):
        marker = f"\n  {service_name}:"
        start = compose_text.index(marker)
        next_service = re.search(r"\n  [A-Za-z0-9_-]+:", compose_text[start + len(marker):])
        end = len(compose_text) if next_service is None else start + len(marker) + next_service.start()
        section = compose_text[start:end]
        assert "redis:" in section
        assert "condition: service_healthy" in section


@pytest.mark.parametrize("compose_path", ["compose.dev.yml", "compose.prod.yml"])
def test_backup_sidecar_uses_ti_image_and_safe_mounts(compose_path):
    compose_text = Path(compose_path).read_text(encoding="utf-8")
    section = _compose_service_section(compose_text, "backup")

    assert "image: ${TI_IMAGE:-ghcr.io/saksk-it/ti:latest}" in section
    assert "python -m app.tasks.backup_scheduler" in section
    assert "stop_grace_period: ${BACKUP_STOP_GRACE_PERIOD:-1h}" in section
    assert "memory: 512M" in section
    assert "./var:/data:ro" in section
    assert ".env.production" not in section
    assert "compose.prod.yml:/" not in section
    assert "docker.sock" not in section
    assert "backup-cron.sh" not in section
    assert "postgres:" in section
    assert "condition: service_healthy" in section


@pytest.mark.parametrize(
    ("compose_path", "expected_expression"),
    [
        (
            "compose.dev.yml",
            "BACKUP_CREDENTIAL_SECRET: ${BACKUP_CREDENTIAL_SECRET:-dev-backup-credential-secret}",
        ),
        (
            "compose.prod.yml",
            "BACKUP_CREDENTIAL_SECRET: ${BACKUP_CREDENTIAL_SECRET:?BACKUP_CREDENTIAL_SECRET is required}",
        ),
    ],
)
def test_web_and_backup_sidecar_share_backup_credential_secret(
    compose_path, expected_expression
):
    compose_text = Path(compose_path).read_text(encoding="utf-8")

    assert expected_expression in _compose_service_section(compose_text, "web")
    assert expected_expression in _compose_service_section(compose_text, "backup")


def test_development_backup_sidecar_mounts_application_source():
    compose_text = Path("compose.dev.yml").read_text(encoding="utf-8")
    section = _compose_service_section(compose_text, "backup")

    assert "./app:/app/app" in section


def test_production_backup_sidecar_has_restart_and_runtime_environment():
    compose_text = Path("compose.prod.yml").read_text(encoding="utf-8")
    section = _compose_service_section(compose_text, "backup")

    assert "restart: unless-stopped" in section
    for variable in (
        "DATABASE_URL:",
        "DATA_DIR:",
        "SECRET_KEY:",
        "BACKUP_CREDENTIAL_SECRET:",
        "TZ:",
        "BACKUP_SCHEDULER_POLL_SECONDS:",
        "BACKUP_JOB_LEASE_SECONDS:",
        "BACKUP_PG_DUMP_TIMEOUT:",
        "TI_BACKUP_SCHEDULER:",
    ):
        assert variable in section


def test_runtime_image_installs_postgresql_client():
    dockerfile = Path("docker/Dockerfile").read_text(encoding="utf-8")

    assert "postgresql-client" in dockerfile
    assert "rm -rf /var/lib/apt/lists/*" in dockerfile


def test_production_doc_env_template_matches_backup_sidecar_runtime():
    doc = Path("docs/PRODUCTION.md").read_text(encoding="utf-8")
    template = doc.split("cat > .env.production <<EOF", 1)[1].split("\nEOF", 1)[0]

    assert "BACKUP_CREDENTIAL_SECRET=$(python3 -c" in template
    assert "TZ=Asia/Shanghai" in template
    assert "BACKUP_SCHEDULER_POLL_SECONDS=60" in template
    assert "BACKUP_JOB_LEASE_SECONDS=3600" in template
    assert "BACKUP_PG_DUMP_TIMEOUT=900" in template
    assert "BACKUP_STOP_GRACE_PERIOD=1h" in template
    for obsolete in (
        "BACKUP_TZ=",
        "BACKUP_ANCHOR_TIME=",
        "BACKUP_INTERVAL=",
        "BACKUP_CHECK_INTERVAL=",
        "BACKUP_RETENTION_DAYS=",
    ):
        assert obsolete not in template
    assert 'if ! grep -q \'^BACKUP_CREDENTIAL_SECRET=\' .env.production; then' in doc
    assert "printf 'BACKUP_CREDENTIAL_SECRET=%s\\n'" in doc
    assert '>> .env.production' in doc


def test_deploy_script_writes_production_backup_sidecar_environment():
    script = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")
    section = _shell_function_section(script, "write_production_env")

    assert 'backup_credential_secret="${BACKUP_CREDENTIAL_SECRET:-$(random_secret)}"' in section
    assert "BACKUP_CREDENTIAL_SECRET=${backup_credential_secret}" in section
    assert "TZ=${TZ:-Asia/Shanghai}" in section
    assert "BACKUP_SCHEDULER_POLL_SECONDS=${BACKUP_SCHEDULER_POLL_SECONDS:-60}" in section
    assert "BACKUP_JOB_LEASE_SECONDS=${BACKUP_JOB_LEASE_SECONDS:-3600}" in section
    assert "BACKUP_PG_DUMP_TIMEOUT=${BACKUP_PG_DUMP_TIMEOUT:-900}" in section
    assert "BACKUP_STOP_GRACE_PERIOD=${BACKUP_STOP_GRACE_PERIOD:-1h}" in section
    for obsolete in (
        "BACKUP_TZ=",
        "BACKUP_ANCHOR_TIME=",
        "BACKUP_INTERVAL=",
        "BACKUP_CHECK_INTERVAL=",
        "BACKUP_RETENTION_DAYS=",
    ):
        assert obsolete not in section


def test_deploy_script_writes_development_backup_sidecar_environment():
    script = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")
    section = _shell_function_section(script, "write_development_env")

    assert "BACKUP_CREDENTIAL_SECRET=${BACKUP_CREDENTIAL_SECRET:-dev-backup-credential-secret}" in section
    assert "TZ=${TZ:-Asia/Shanghai}" in section
    assert "BACKUP_SCHEDULER_POLL_SECONDS=${BACKUP_SCHEDULER_POLL_SECONDS:-60}" in section
    assert "BACKUP_JOB_LEASE_SECONDS=${BACKUP_JOB_LEASE_SECONDS:-3600}" in section
    assert "BACKUP_PG_DUMP_TIMEOUT=${BACKUP_PG_DUMP_TIMEOUT:-900}" in section
    assert "BACKUP_STOP_GRACE_PERIOD=${BACKUP_STOP_GRACE_PERIOD:-1h}" in section
    for obsolete in (
        "BACKUP_TZ=",
        "BACKUP_ANCHOR_TIME=",
        "BACKUP_INTERVAL=",
        "BACKUP_CHECK_INTERVAL=",
        "BACKUP_RETENTION_DAYS=",
    ):
        assert obsolete not in section


@pytest.mark.parametrize(
    "legacy_backup_line",
    ["", "BACKUP_CREDENTIAL_SECRET=\n"],
    ids=["missing", "empty"],
)
def test_deploy_script_upgrades_legacy_production_env_without_logging_secret(
    tmp_path, legacy_backup_line
):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        "FLASK_ENV=production\n"
        "SECRET_KEY=legacy-app-secret\n"
        f"{legacy_backup_line}",
        encoding="utf-8",
    )
    command = textwrap.dedent(
        f"""
        set -euo pipefail
        export DEPLOY_UBUNTU24_TEST_HELPERS=1
        export DEPLOY_ENV=production
        export ENV_FILE='{env_file}'
        source scripts/deploy_ubuntu24.sh
        random_secret() {{ printf '%s\\n' 'generated-backup-secret'; }}
        ensure_backup_credential_secret
        """
    )

    result = subprocess.run(
        ["bash", "-c", command],
        cwd=Path.cwd(),
        check=True,
        text=True,
        capture_output=True,
    )

    env_text = env_file.read_text(encoding="utf-8")
    assert env_text.count("BACKUP_CREDENTIAL_SECRET=") == 1
    assert "BACKUP_CREDENTIAL_SECRET=generated-backup-secret" in env_text
    assert env_file.stat().st_mode & 0o777 == 0o600
    assert "generated-backup-secret" not in result.stdout
    assert "generated-backup-secret" not in result.stderr


def test_deploy_script_preserves_existing_backup_credential_secret(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        "FLASK_ENV=production\n"
        "BACKUP_CREDENTIAL_SECRET=preserved-backup-secret\n",
        encoding="utf-8",
    )
    command = textwrap.dedent(
        f"""
        set -euo pipefail
        export DEPLOY_UBUNTU24_TEST_HELPERS=1
        export DEPLOY_ENV=production
        export ENV_FILE='{env_file}'
        source scripts/deploy_ubuntu24.sh
        random_secret() {{ printf '%s\\n' 'replacement-secret'; }}
        ensure_backup_credential_secret
        """
    )

    result = subprocess.run(
        ["bash", "-c", command],
        cwd=Path.cwd(),
        check=True,
        text=True,
        capture_output=True,
    )

    env_text = env_file.read_text(encoding="utf-8")
    assert env_text.count("BACKUP_CREDENTIAL_SECRET=") == 1
    assert "BACKUP_CREDENTIAL_SECRET=preserved-backup-secret" in env_text
    assert "replacement-secret" not in env_text
    assert env_file.stat().st_mode & 0o777 == 0o600
    assert result.stdout == ""
    assert result.stderr == ""


def test_restore_script_handles_empty_upload_and_instance_directories(tmp_path):
    archive_name = "backup_20260711_020304_12345678.tar.gz"
    archive_root = archive_name.removesuffix(".tar.gz")
    source_root = tmp_path / "archive" / archive_root
    (source_root / "uploads").mkdir(parents=True)
    (source_root / "instance").mkdir()
    (source_root / "database.sql").write_text("-- empty test dump\n", encoding="utf-8")
    (source_root / "MANIFEST.txt").write_text("test backup\n", encoding="utf-8")
    backups = tmp_path / "backups"
    backups.mkdir()
    with tarfile.open(backups / archive_name, "w:gz") as archive:
        archive.add(source_root, arcname=archive_root)

    (tmp_path / "var" / "uploads").mkdir(parents=True)
    (tmp_path / "var" / "instance").mkdir()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$FAKE_DOCKER_LOG\"\ncat >/dev/null || true\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    env_file = tmp_path / ".env.production"
    env_file.write_text("POSTGRES_USER=tester\nPOSTGRES_DB=testdb\n", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "FAKE_DOCKER_LOG": str(docker_log),
        "ENV_FILE": str(env_file),
        "COMPOSE_FILE": "compose.prod.yml",
    }

    result = subprocess.run(
        ["bash", str(Path.cwd() / "scripts" / "restore.sh"), archive_name],
        cwd=tmp_path,
        input="yes\n",
        text=True,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "var" / "uploads").is_dir()
    assert (tmp_path / "var" / "instance").is_dir()
    assert "=== 恢复完成 ===" in result.stdout
    assert "stop web worker" in docker_log.read_text(encoding="utf-8")
    assert "stop web worker backup" in docker_log.read_text(encoding="utf-8")
    assert "start web worker backup" in docker_log.read_text(encoding="utf-8")


def test_restore_script_restarts_all_services_after_database_failure(tmp_path):
    archive_name = "backup_20260711_020304_12345678.tar.gz"
    archive_root = archive_name.removesuffix(".tar.gz")
    source_root = tmp_path / "archive" / archive_root
    (source_root / "uploads").mkdir(parents=True)
    (source_root / "instance").mkdir()
    (source_root / "database.sql").write_text("-- test dump\n", encoding="utf-8")
    backups = tmp_path / "backups"
    backups.mkdir()
    with tarfile.open(backups / archive_name, "w:gz") as archive:
        archive.add(source_root, arcname=archive_root)
    (tmp_path / "var" / "uploads").mkdir(parents=True)
    (tmp_path / "var" / "instance").mkdir()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$FAKE_DOCKER_LOG\"\n"
        "case \"$*\" in *'exec -T postgres psql'*) exit 7;; esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    env_file = tmp_path / ".env.production"
    env_file.write_text("POSTGRES_USER=tester\nPOSTGRES_DB=testdb\n", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "FAKE_DOCKER_LOG": str(docker_log),
        "ENV_FILE": str(env_file),
        "COMPOSE_FILE": "compose.prod.yml",
    }

    result = subprocess.run(
        ["bash", str(Path.cwd() / "scripts" / "restore.sh"), archive_name],
        cwd=tmp_path,
        input="yes\n",
        text=True,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 7
    calls = docker_log.read_text(encoding="utf-8")
    assert "stop web worker backup" in calls
    assert "start web worker backup" in calls


def test_legacy_backup_secret_upgrade_runs_before_env_load_and_compose():
    script = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")
    prepare = _shell_function_section(script, "prepare_runtime_files")

    assert prepare.index("ensure_backup_credential_secret") < prepare.index(
        "load_env_file"
    )
    main = script.rsplit(
        'if [[ "${DEPLOY_UBUNTU24_TEST_HELPERS:-0}" == "1" ]]', 1
    )[1]
    assert main.index("prepare_runtime_files") < main.index("deploy_stack")


def test_production_deploy_runs_migrations_before_full_stack_up():
    script_text = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")

    base_up = 'up -d postgres redis'
    migration = 'run_web_flask db upgrade'
    full_up = 'up -d --remove-orphans'

    assert base_up in script_text
    assert migration in script_text
    assert full_up in script_text
    assert script_text.index(base_up) < script_text.index(migration) < script_text.index(full_up)
    assert 'exec -T web flask db upgrade' not in script_text
    assert 'logs --tail=200 web' in script_text


def test_production_deploy_persists_rate_limit_multiplier():
    script_text = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")

    assert 'RATELIMIT_LIMIT_MULTIPLIER="${RATELIMIT_LIMIT_MULTIPLIER:-100}"' in script_text
    assert 'RATELIMIT_LIMIT_MULTIPLIER=${RATELIMIT_LIMIT_MULTIPLIER}' in script_text
    assert 'upsert_env_value "RATELIMIT_LIMIT_MULTIPLIER" "$RATELIMIT_LIMIT_MULTIPLIER"' in script_text


def test_production_deploy_persists_sse_disabled_default():
    script_text = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")

    assert 'SSE_ENABLED="${SSE_ENABLED:-$DEFAULT_SSE_ENABLED}"' in script_text
    assert 'SSE_ENABLED=${SSE_ENABLED}' in script_text
    assert 'SSE_RETRY_AFTER_SECONDS=${SSE_RETRY_AFTER_SECONDS}' in script_text
    assert 'upsert_env_value "SSE_ENABLED" "$SSE_ENABLED"' in script_text
    assert 'upsert_env_value "SSE_RETRY_AFTER_SECONDS" "$SSE_RETRY_AFTER_SECONDS"' in script_text


def test_production_deploy_supports_extra_https_domains():
    script_text = Path("scripts/deploy_ubuntu24.sh").read_text(encoding="utf-8")

    assert 'EXTRA_DOMAINS="${EXTRA_DOMAINS:-}"' in script_text
    assert 'raw_extra_domains="${EXTRA_DOMAINS//,/ }"' in script_text
    assert 'upsert_env_value "EXTRA_DOMAINS" "$EXTRA_DOMAINS"' in script_text
    assert 'server_names="$APP_DOMAINS"' in script_text
    assert 'server_name ${server_names};' in script_text
    assert 'for domain in $APP_DOMAINS; do' in script_text
    assert 'if [[ -z "$CERTBOT_EMAIL" ]] && ! certificate_covers_all_domains; then' in script_text
    assert 'certbot_domain_args+=(-d "$domain")' in script_text
    assert 'certbot_common_args+=(--expand)' in script_text
    assert 'for domain in $APP_DOMAINS; do' in script_text
    assert '"https://${domain}/api/ping"' in script_text


def test_update_production_preserves_extra_https_domains():
    script_text = Path("scripts/update_production.sh").read_text(encoding="utf-8")

    assert "saved_extra_domains" in script_text
    assert "saved_extra_domains=\"$(read_env_value EXTRA_DOMAINS)\"" in script_text
    assert 'EXTRA_DOMAINS="${EXTRA_DOMAINS:-$saved_extra_domains}"' in script_text
    assert "export DOMAIN EXTRA_DOMAINS CERTBOT_EMAIL" in script_text


def test_deploy_helper_generates_multi_domain_nginx_and_certbot_args(tmp_path):
    nginx_conf = tmp_path / "ti.conf"
    enabled_conf = tmp_path / "enabled-ti.conf"

    command = textwrap.dedent(
        f"""
        set -euo pipefail
        export DEPLOY_UBUNTU24_TEST_HELPERS=1
        export DOMAIN=saksk.top
        export EXTRA_DOMAINS='ti.saksk.top,api.saksk.top'
        export HOST_NGINX_CONFIG_PATH='{nginx_conf}'
        export HOST_NGINX_ENABLED_PATH='{enabled_conf}'
        source scripts/deploy_ubuntu24.sh
        SUDO=
        APP_DOMAIN=saksk.top
        EXTRA_DOMAINS='ti.saksk.top,api.saksk.top'
        HTTP_PORT=8080
        APP_DOMAINS=
        build_app_domains
        certificate_files_exist() {{ return 0; }}
        reload_host_nginx() {{ :; }}
        write_host_nginx_config
        echo "DOMAINS:$APP_DOMAINS"
        cat '{nginx_conf}'
        """
    )

    result = subprocess.run(
        ["bash", "-c", command],
        cwd=Path.cwd(),
        check=True,
        text=True,
        capture_output=True,
    )

    assert "DOMAINS:saksk.top ti.saksk.top api.saksk.top" in result.stdout
    assert "server_name saksk.top ti.saksk.top api.saksk.top;" in result.stdout
    assert "ssl_certificate /etc/letsencrypt/live/saksk.top/fullchain.pem;" in result.stdout
    assert "proxy_pass http://127.0.0.1:8080;" in result.stdout
