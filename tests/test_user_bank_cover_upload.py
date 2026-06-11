# -*- coding: utf-8 -*-
"""用户题库封面上传接口测试。"""

from __future__ import annotations

import base64
from io import BytesIO
import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db


_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XnX8AAAAASUVORK5CYII="
)


def _create_bank(
    app,
    user_id: int,
    name: str = "封面上传测试题库",
    cover_image: str | None = None,
) -> int:
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, cover_image, status)
                VALUES (:user_id, :name, :cover_image, 1)
                RETURNING id
                """
            ),
            {"user_id": int(user_id), "name": name, "cover_image": cover_image},
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _create_user(app) -> int:
    username = f"cover_owner_{uuid.uuid4().hex[:8]}"
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


def _delete_user(app, user_id: int | None) -> None:
    if user_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": int(user_id)})
        db.session.commit()


def _delete_bank(app, bank_id: int | None) -> None:
    if bank_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def _fetch_cover_image(app, bank_id: int) -> str | None:
    with app.app_context():
        row = db.session.execute(
            text("SELECT cover_image FROM user_question_banks WHERE id = :bank_id"),
            {"bank_id": int(bank_id)},
        ).fetchone()
        assert row is not None
        return row._mapping["cover_image"]


def test_manage_page_renders_cover_upload_controls(app, auth_client, seed_user):
    cover_url = "/uploads/bank_covers/bank_cover_manage_existing.png"
    bank_id = _create_bank(app, seed_user["id"], name="管理页封面测试题库", cover_image=cover_url)

    try:
        response = auth_client.get(f"/user/banks/{bank_id}/manage")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'id="ubmCoverImage"' in html
        assert 'id="ubmCoverFile"' in html
        assert 'id="ubmChooseCoverBtn"' in html
        assert 'id="ubmSaveCoverBtn"' in html
        assert 'accept="image/png,image/jpeg,image/gif,image/webp"' in html
        assert f'value="{cover_url}"' in html
        assert "/cover/upload" in html
    finally:
        _delete_bank(app, bank_id)


def test_manage_cover_save_updates_cover_image(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], name="管理页封面保存测试题库")
    cover_url = "/uploads/bank_covers/bank_cover_manage_saved.png"

    try:
        response = auth_client.put(
            f"/user/banks/api/{bank_id}",
            json={"cover_image": cover_url},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        assert response.get_json()["status"] == "success"
        assert _fetch_cover_image(app, bank_id) == cover_url
    finally:
        _delete_bank(app, bank_id)


def test_upload_existing_bank_cover_saves_file(app, auth_client, seed_user, monkeypatch, tmp_path):
    bank_id = _create_bank(app, seed_user["id"])
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))

    try:
        response = auth_client.post(
            f"/user/banks/api/{bank_id}/cover/upload",
            data={"file": (BytesIO(_PNG_BYTES), "cover.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["code"] == 0
        assert payload["data"]["url"].startswith("/uploads/bank_covers/bank_cover_")
        assert payload["data"]["path"].startswith("bank_covers/")
        assert (tmp_path / payload["data"]["path"]).exists()

        public_response = auth_client.get(payload["data"]["url"])
        assert public_response.status_code == 200
    finally:
        _delete_bank(app, bank_id)


def test_upload_existing_bank_cover_requires_owner(app, auth_client, seed_user):
    owner_id = _create_user(app)
    bank_id = _create_bank(app, owner_id, name="非本人封面测试题库")

    try:
        response = auth_client.post(
            f"/user/banks/api/{bank_id}/cover/upload",
            data={"file": (BytesIO(_PNG_BYTES), "cover.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 404
        assert response.get_json()["status"] == "error"
    finally:
        _delete_bank(app, bank_id)
        _delete_user(app, owner_id)


def test_upload_bank_cover_rejects_fake_image(auth_client):
    response = auth_client.post(
        "/user/banks/api/cover/upload",
        data={"file": (BytesIO(b"not an image"), "cover.png")},
        content_type="multipart/form-data",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "error"
    assert "图片" in payload["message"]
