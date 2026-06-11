# -*- coding: utf-8 -*-
"""个人题库设置页测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db


def _create_user(app, prefix: str = "settings_user") -> int:
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    with app.app_context():
        user_id = db.session.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, is_admin, has_password_set)
                VALUES (:username, :email, :password_hash, 0, 1)
                RETURNING id
                """
            ),
            {
                "username": username,
                "email": f"{username}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
            },
        ).scalar_one()
        db.session.commit()
        return int(user_id)


def _create_bank(app, user_id: int, name: str = "设置页测试题库", **extra) -> int:
    data = {
        "user_id": int(user_id),
        "name": f"{name}-{uuid.uuid4().hex[:6]}",
        "is_public": bool(extra.get("is_public", False)),
        "join_mode": extra.get("join_mode", "free"),
        "public_description": extra.get("public_description", "公开简介保留测试"),
    }
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (
                    user_id, name, is_public, join_mode, public_description, status, question_count, share_count
                )
                VALUES (
                    :user_id, :name, :is_public, :join_mode, :public_description, 1, 3, 0
                )
                RETURNING id
                """
            ),
            data,
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _delete_bank(app, bank_id: int | None) -> None:
    if bank_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def _delete_user(app, user_id: int | None) -> None:
    if user_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": int(user_id)})
        db.session.commit()


def _fetch_bank(app, bank_id: int) -> dict:
    with app.app_context():
        row = db.session.execute(
            text(
                """
                SELECT is_public, join_mode, status, public_description
                FROM user_question_banks
                WHERE id = :bank_id
                """
            ),
            {"bank_id": int(bank_id)},
        ).fetchone()
        assert row is not None
        return dict(row._mapping)


def test_bank_settings_page_uses_manage_tab_layout(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], is_public=True, join_mode="approval")

    try:
        response = auth_client.get(f"/user/banks/{bank_id}/edit")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'href="/user/banks/{}/edit"'.format(bank_id) in html
        assert 'aria-label="题库公开状态"' in html
        assert "加入方式选择" in html
        assert "删除题库" in html
        assert "题库名称" not in html
        assert "封面图" not in html
        assert "公开简介" not in html
        assert "下一步" not in html
        assert "bank_profile_wizard.js" not in html
        assert 'data-current-join-mode="approval"' in html
    finally:
        _delete_bank(app, bank_id)


def test_bank_settings_page_requires_owner(app, auth_client):
    owner_id = _create_user(app, "settings_owner")
    bank_id = _create_bank(app, owner_id)

    try:
        response = auth_client.get(f"/user/banks/{bank_id}/edit")
        assert response.status_code == 404
    finally:
        _delete_bank(app, bank_id)
        _delete_user(app, owner_id)


def test_bank_settings_existing_apis_support_public_join_and_delete(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], is_public=False, join_mode="free")

    public_resp = auth_client.post(
        f"/user/banks/api/{bank_id}/public",
        json={"is_public": True},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert public_resp.status_code == 200
    assert public_resp.get_json()["status"] == "success"
    after_public = _fetch_bank(app, bank_id)
    assert bool(after_public["is_public"]) is True
    assert after_public["public_description"] == "公开简介保留测试"

    join_resp = auth_client.put(
        f"/user/banks/api/{bank_id}",
        json={"join_mode": "member"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert join_resp.status_code == 200
    assert join_resp.get_json()["status"] == "success"
    assert _fetch_bank(app, bank_id)["join_mode"] == "member"

    delete_resp = auth_client.delete(
        f"/user/banks/api/{bank_id}",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["status"] == "success"
    assert int(_fetch_bank(app, bank_id)["status"]) == 0

    _delete_bank(app, bank_id)
