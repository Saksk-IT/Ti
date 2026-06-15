# -*- coding: utf-8 -*-
import sys
import types
import re
import subprocess
import textwrap
from pathlib import Path


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
