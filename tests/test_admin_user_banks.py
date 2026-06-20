# -*- coding: utf-8 -*-
"""后台题库管理接口与页面测试。"""

from __future__ import annotations

import base64
from io import BytesIO
import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.core.utils.user_state_cache import invalidate_user_state


_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XnX8AAAAASUVORK5CYII="
)


def _make_admin_client(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin = true, is_locked = false WHERE id = :uid"),
            {"uid": int(seed_user["id"])},
        )
        db.session.commit()
        invalidate_user_state(int(seed_user["id"]))

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["username"] = seed_user["username"]
        sess["is_admin"] = True
        sess["is_subject_admin"] = True
        sess["session_version"] = 0
    return client


def _make_subject_admin_client(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin = false, is_subject_admin = true WHERE id = :uid"),
            {"uid": int(seed_user["id"])},
        )
        db.session.commit()
        invalidate_user_state(int(seed_user["id"]))

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["username"] = seed_user["username"]
        sess["is_admin"] = False
        sess["is_subject_admin"] = True
        sess["session_version"] = 0
    return client


def _create_owner(app, suffix: str) -> int:
    with app.app_context():
        owner_id = db.session.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, is_admin, has_password_set)
                VALUES (:username, :email, :password_hash, false, true)
                RETURNING id
                """
            ),
            {
                "username": f"bank_owner_{suffix}",
                "email": f"bank_owner_{suffix}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
            },
        ).scalar_one()
        db.session.commit()
        return int(owner_id)


def _create_bank(app, owner_id: int, suffix: str, **overrides) -> int:
    values = {
        "user_id": int(owner_id),
        "name": f"后台题库-{suffix}",
        "description": "后台列表描述",
        "public_description": "后台公开简介",
        "cover_image": None,
        "is_public": True,
        "status": 1,
        "question_count": 3,
    }
    values.update(overrides)

    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (
                    user_id, name, description, public_description, cover_image,
                    is_public, status, question_count, public_at
                )
                VALUES (
                    :user_id, :name, :description, :public_description, :cover_image,
                    :is_public, :status, :question_count,
                    CASE WHEN :is_public THEN CURRENT_TIMESTAMP ELSE NULL END
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _cleanup(app, *, bank_ids=(), user_ids=()):
    with app.app_context():
        for bank_id in bank_ids:
            db.session.execute(
                text("DELETE FROM public_bank_plaza_metrics WHERE source_type = 'user_public' AND source_id = :bank_id"),
                {"bank_id": int(bank_id)},
            )
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        for user_id in user_ids:
            db.session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": int(user_id)})
        db.session.commit()


def test_admin_user_banks_list_returns_owner_visibility_and_count(app, seed_user):
    client = _make_admin_client(app, seed_user)
    suffix = uuid.uuid4().hex[:8]
    owner_id = _create_owner(app, suffix)
    bank_id = _create_bank(app, owner_id, suffix, name=f"后台列表题库-{suffix}", question_count=8)

    try:
        response = client.get(f"/admin/api/user-banks?keyword={suffix}")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        item = next(row for row in payload["data"]["banks"] if row["id"] == bank_id)
        assert item["name"] == f"后台列表题库-{suffix}"
        assert item["owner"]["id"] == owner_id
        assert item["owner"]["username"] == f"bank_owner_{suffix}"
        assert item["is_public"] is True
        assert item["question_count"] == 8
    finally:
        _cleanup(app, bank_ids=[bank_id], user_ids=[owner_id])


def test_admin_user_banks_rejects_non_admin(app, seed_user):
    client = _make_subject_admin_client(app, seed_user)

    response = client.get("/admin/api/user-banks")

    assert response.status_code == 403
    assert response.get_json()["status"] == "forbidden"


def test_admin_create_and_edit_user_bank_profile(app, seed_user):
    client = _make_admin_client(app, seed_user)
    suffix = uuid.uuid4().hex[:8]
    bank_id = None

    try:
        create_response = client.post(
            "/admin/api/user-banks",
            json={
                "name": f"后台创建题库-{suffix}",
                "description": "创建描述",
                "public_description": "创建简介",
                "cover_image": "/uploads/bank_covers/create.png",
                "is_public": True,
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert create_response.status_code == 200
        created = create_response.get_json()["data"]["bank"]
        bank_id = created["id"]
        assert created["owner"]["id"] == seed_user["id"]
        assert created["description"] == "创建描述"
        assert created["public_description"] == "创建简介"
        assert created["cover_image"] == "/uploads/bank_covers/create.png"
        assert created["is_public"] is True

        edit_response = client.put(
            f"/admin/api/user-banks/{bank_id}",
            json={
                "name": f"后台编辑题库-{suffix}",
                "description": "编辑描述",
                "public_description": "编辑简介",
                "cover_image": "/uploads/bank_covers/edit.png",
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert edit_response.status_code == 200
        edited = edit_response.get_json()["data"]["bank"]
        assert edited["name"] == f"后台编辑题库-{suffix}"
        assert edited["description"] == "编辑描述"
        assert edited["public_description"] == "编辑简介"
        assert edited["cover_image"] == "/uploads/bank_covers/edit.png"
    finally:
        if bank_id is not None:
            _cleanup(app, bank_ids=[bank_id])


def test_admin_user_bank_validation_rejects_long_profile(app, seed_user):
    client = _make_admin_client(app, seed_user)

    response = client.post(
        "/admin/api/user-banks",
        json={"name": "后台校验题库", "description": "x" * 201},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "error"
    assert "描述不能超过200个字符" in payload["message"]


def test_admin_can_toggle_any_user_bank_public_state(app, seed_user):
    client = _make_admin_client(app, seed_user)
    suffix = uuid.uuid4().hex[:8]
    owner_id = _create_owner(app, suffix)
    bank_id = _create_bank(app, owner_id, suffix, is_public=True, public_description="原简介")

    try:
        response = client.post(
            f"/admin/api/user-banks/{bank_id}/public",
            json={"is_public": False},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        bank = response.get_json()["data"]["bank"]
        assert bank["is_public"] is False
        assert bank["public_description"] == "原简介"

        response = client.post(
            f"/admin/api/user-banks/{bank_id}/public",
            json={"is_public": True, "public_description": "新公开简介"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        bank = response.get_json()["data"]["bank"]
        assert bank["is_public"] is True
        assert bank["public_description"] == "新公开简介"
    finally:
        _cleanup(app, bank_ids=[bank_id], user_ids=[owner_id])


def test_admin_user_bank_cover_upload_saves_file(app, seed_user, monkeypatch, tmp_path):
    client = _make_admin_client(app, seed_user)
    suffix = uuid.uuid4().hex[:8]
    owner_id = _create_owner(app, suffix)
    bank_id = _create_bank(app, owner_id, suffix, is_public=False)
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))

    try:
        response = client.post(
            f"/admin/api/user-banks/{bank_id}/cover/upload",
            data={"file": (BytesIO(_PNG_BYTES), "cover.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["data"]["url"].startswith("/uploads/bank_covers/bank_cover_admin_")
        assert (tmp_path / payload["data"]["path"]).exists()
    finally:
        _cleanup(app, bank_ids=[bank_id], user_ids=[owner_id])


def test_admin_subjects_page_renders_user_bank_management_ui(app, seed_user):
    client = _make_admin_client(app, seed_user)

    response = client.get("/admin/subjects")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "题库管理" in html
    assert "题库所有者" in html
    assert "公开状态" in html
    assert "题目数目" in html
    assert "题库封面" in html
    assert "/admin/api/user-banks" in html
    assert "旧公共科目管理" in html
