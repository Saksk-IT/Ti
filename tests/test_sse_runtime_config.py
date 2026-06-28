# -*- coding: utf-8 -*-

from app.core.utils.user_state_cache import invalidate_user_state


def test_sse_preflight_returns_fast_disabled_response(app, auth_client, seed_user):
    previous_enabled = app.config.get("SSE_ENABLED")
    previous_retry_after = app.config.get("SSE_RETRY_AFTER_SECONDS")
    app.config["SSE_ENABLED"] = False
    app.config["SSE_RETRY_AFTER_SECONDS"] = 300

    try:
        response = auth_client.get("/api/sse/preflight")
    finally:
        app.config["SSE_ENABLED"] = previous_enabled
        app.config["SSE_RETRY_AFTER_SECONDS"] = previous_retry_after
        invalidate_user_state(seed_user["id"])

    payload = response.get_json()
    retry_after_header = int(response.headers["Retry-After"])
    assert response.status_code == 503
    assert 299 <= retry_after_header <= 300
    assert payload["status"] == "error"
    assert payload["reason"] == "disabled"
    assert payload["retry_after"] == 300


def test_sse_stream_returns_json_when_disabled(app, auth_client, seed_user):
    previous_enabled = app.config.get("SSE_ENABLED")
    app.config["SSE_ENABLED"] = False

    try:
        response = auth_client.get("/api/sse/stream")
    finally:
        app.config["SSE_ENABLED"] = previous_enabled
        invalidate_user_state(seed_user["id"])

    assert response.status_code == 503
    assert response.mimetype == "application/json"
    assert response.get_json()["reason"] == "disabled"
