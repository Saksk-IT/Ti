# -*- coding: utf-8 -*-
"""个人题库分享加入链路回归测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.core.utils.jwt_utils import generate_jwt_token
from app.core.utils.user_state_cache import invalidate_user_state


def _create_user(app, prefix: str) -> int:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    with app.app_context():
        user_id = db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, is_admin, has_password_set,
                    session_version, openid
                )
                VALUES (
                    :username, :email, :password_hash, 0, 1,
                    0, :openid
                )
                RETURNING id
                """
            ),
            {
                "username": username,
                "email": f"{username}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
                "openid": f"openid_{username}",
            },
        ).scalar_one()
        db.session.commit()
        return int(user_id)


def _jwt_headers(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        row = db.session.execute(
            text("SELECT openid FROM users WHERE id = :uid"),
            {"uid": int(user_id)},
        ).mappings().first()
        token = generate_jwt_token(
            user_id=int(user_id),
            openid=str((row or {}).get("openid") or f"openid_{user_id}"),
            session_version=0,
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _create_bank(app, owner_id: int, name: str) -> int:
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (
                    user_id, name, description, status, is_public, question_count
                )
                VALUES (:owner_id, :name, 'share fixture', 1, false, 3)
                RETURNING id
                """
            ),
            {"owner_id": int(owner_id), "name": name},
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _cleanup(app, *user_ids: int) -> None:
    with app.app_context():
        for user_id in user_ids:
            if not user_id:
                continue
            invalidate_user_state(int(user_id))
            db.session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": int(user_id)})
        db.session.commit()


def test_user_bank_share_code_and_token_join_show_in_shared_list(app, client):
    """用户通过分享码/微信 token 加入后，应出现在收到的分享题库列表。"""
    owner_id = _create_user(app, "share_owner")
    receiver_code_id = _create_user(app, "share_code_receiver")
    receiver_token_id = _create_user(app, "share_token_receiver")
    bank_id = _create_bank(app, owner_id, f"分享链路题库-{uuid.uuid4().hex[:8]}")

    owner_headers = _jwt_headers(app, owner_id)
    code_headers = _jwt_headers(app, receiver_code_id)
    token_headers = _jwt_headers(app, receiver_token_id)

    try:
        code_resp = client.post(
            f"/api/user/banks/api/{bank_id}/shares",
            json={"type": "code", "permission": "read", "expires_in": None},
            headers=owner_headers,
        )
        assert code_resp.status_code == 200
        code_payload = code_resp.get_json()
        assert code_payload["status"] == "success"
        share_code = code_payload["data"]["share_code"]

        code_join_resp = client.post(
            "/api/user/banks/api/join",
            json={"share_code": share_code},
            headers=code_headers,
        )
        assert code_join_resp.status_code == 200
        assert code_join_resp.get_json()["data"]["bank_id"] == bank_id

        code_shared_resp = client.get(
            "/api/user/banks/api/shared",
            headers=code_headers,
        )
        assert code_shared_resp.status_code == 200
        code_banks = code_shared_resp.get_json()["data"]["banks"]
        assert any(int(item["bank_id"]) == bank_id for item in code_banks)

        token_resp = client.post(
            f"/api/user/banks/api/{bank_id}/shares",
            json={"type": "link", "permission": "read", "expires_in": None},
            headers=owner_headers,
        )
        assert token_resp.status_code == 200
        token_payload = token_resp.get_json()
        assert token_payload["status"] == "success"
        share_token = token_payload["data"]["share_token"]

        token_join_resp = client.post(
            "/api/user/banks/api/join",
            json={"token": share_token},
            headers=token_headers,
        )
        assert token_join_resp.status_code == 200
        assert token_join_resp.get_json()["data"]["bank_id"] == bank_id

        token_shared_resp = client.get(
            "/api/user/banks/api/shared",
            headers=token_headers,
        )
        assert token_shared_resp.status_code == 200
        token_banks = token_shared_resp.get_json()["data"]["banks"]
        assert any(int(item["bank_id"]) == bank_id for item in token_banks)
    finally:
        _cleanup(app, owner_id, receiver_code_id, receiver_token_id)


def test_revoked_user_bank_share_removes_access(app, client):
    """撤销分享后，已加入用户不应继续通过该分享访问题库。"""
    owner_id = _create_user(app, "revoke_owner")
    receiver_id = _create_user(app, "revoke_receiver")
    bank_id = _create_bank(app, owner_id, f"撤销分享题库-{uuid.uuid4().hex[:8]}")

    owner_headers = _jwt_headers(app, owner_id)
    receiver_headers = _jwt_headers(app, receiver_id)

    try:
        share_resp = client.post(
            f"/api/user/banks/api/{bank_id}/shares",
            json={"type": "code", "permission": "read", "expires_in": None},
            headers=owner_headers,
        )
        assert share_resp.status_code == 200
        share_data = share_resp.get_json()["data"]
        share_id = int(share_data["share_id"])

        join_resp = client.post(
            "/api/user/banks/api/join",
            json={"share_code": share_data["share_code"]},
            headers=receiver_headers,
        )
        assert join_resp.status_code == 200

        detail_before = client.get(
            f"/api/user/banks/api/{bank_id}",
            headers=receiver_headers,
        )
        assert detail_before.status_code == 200

        revoke_resp = client.delete(
            f"/api/user/banks/api/{bank_id}/shares/{share_id}",
            headers=owner_headers,
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.get_json()["status"] == "success"

        detail_after = client.get(
            f"/api/user/banks/api/{bank_id}",
            headers=receiver_headers,
        )
        assert detail_after.status_code == 403

        shared_resp = client.get(
            "/api/user/banks/api/shared",
            headers=receiver_headers,
        )
        assert shared_resp.status_code == 200
        banks = shared_resp.get_json()["data"]["banks"]
        assert not any(int(item["bank_id"]) == bank_id for item in banks)
    finally:
        _cleanup(app, owner_id, receiver_id)
