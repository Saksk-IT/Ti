# -*- coding: utf-8 -*-
import sys
import types


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
