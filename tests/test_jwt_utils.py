# -*- coding: utf-8 -*-
from app.core.utils.jwt_utils import decode_jwt_token, generate_jwt_token


def test_generate_jwt_token_uses_configured_default_expiry(app):
    with app.app_context():
        token = generate_jwt_token(user_id=1, openid="openid_1")
        payload = decode_jwt_token(token)

    assert payload is not None
    assert int(payload["exp"]) - int(payload["iat"]) == 15 * 24 * 60 * 60


def test_generate_jwt_token_allows_explicit_expiry_override(app):
    with app.app_context():
        token = generate_jwt_token(user_id=1, openid="openid_1", expires_in=60)
        payload = decode_jwt_token(token)

    assert payload is not None
    assert int(payload["exp"]) - int(payload["iat"]) == 60


def test_generate_jwt_token_keeps_openid_and_session_version(app):
    with app.app_context():
        token = generate_jwt_token(user_id=1, openid="openid_1", session_version=7)
        payload = decode_jwt_token(token)

    assert payload is not None
    assert payload["openid"] == "openid_1"
    assert payload["session_version"] == 7
