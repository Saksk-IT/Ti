# -*- coding: utf-8 -*-
"""个人题库题目图片上传与分类存储测试。"""

from __future__ import annotations

import base64
import json
from io import BytesIO
import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db


_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XnX8AAAAASUVORK5CYII="
)


def _create_user(app) -> int:
    username = f"question_image_owner_{uuid.uuid4().hex[:8]}"
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


def _create_bank(app, user_id: int, name: str = "题目图片测试题库") -> int:
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status)
                VALUES (:user_id, :name, 1)
                RETURNING id
                """
            ),
            {"user_id": int(user_id), "name": name},
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _delete_bank(app, bank_id: int | None) -> None:
    if bank_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def _create_question(app, bank_id: int, user_id: int, *, image_path=None) -> int:
    with app.app_context():
        question_id = db.session.execute(
            text(
                """
                INSERT INTO user_bank_questions
                (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, image_path, source_type, sort_order)
                VALUES (
                    :bank_id, :user_id, 'single_choice', :content, '[]', '[\"A\"]', '旧解析', '[]', 2, :image_path, 'custom', 1
                )
                RETURNING id
                """
            ),
            {
                "bank_id": int(bank_id),
                "user_id": int(user_id),
                "content": "原题干",
                "image_path": image_path,
            },
        ).scalar_one()
        db.session.commit()
        return int(question_id)


def test_upload_question_image_saves_file(app, auth_client, seed_user, monkeypatch, tmp_path):
    bank_id = _create_bank(app, seed_user["id"])
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))

    try:
        response = auth_client.post(
            f"/user/banks/api/{bank_id}/question-images/upload",
            data={"file": (BytesIO(_PNG_BYTES), "question.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["data"]["path"].startswith("user_bank_question_images/")
        assert payload["data"]["url"].startswith("/uploads/user_bank_question_images/")
        assert (tmp_path / payload["data"]["path"]).exists()

        public_response = auth_client.get(payload["data"]["url"])
        assert public_response.status_code == 200
    finally:
        _delete_bank(app, bank_id)


def test_update_question_saves_grouped_images(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"])
    question_id = _create_question(app, bank_id, seed_user["id"])

    payload = {
        "q_type": "选择题",
        "content": "新题干",
        "options": ["选项 A", "选项 B"],
        "answer": "A",
        "explanation": "新解析",
        "difficulty": 3,
        "image_groups": {
            "content": ["user_bank_question_images/content-a.png"],
            "answer": ["user_bank_question_images/answer-a.png"],
            "explanation": ["user_bank_question_images/explain-a.png"],
        },
    }

    try:
        response = auth_client.put(
            f"/user/banks/api/{bank_id}/questions/{question_id}",
            json=payload,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        assert response.get_json()["status"] == "success"

        with app.app_context():
            raw = db.session.execute(
                text("SELECT image_path FROM user_bank_questions WHERE id = :qid"),
                {"qid": int(question_id)},
            ).scalar_one()

        stored = json.loads(raw)
        assert stored["content"] == ["user_bank_question_images/content-a.png"]
        assert stored["answer"] == ["user_bank_question_images/answer-a.png"]
        assert stored["explanation"] == ["user_bank_question_images/explain-a.png"]

        detail_response = auth_client.get(f"/user/banks/api/{bank_id}/questions/{question_id}")
        assert detail_response.status_code == 200
        detail = detail_response.get_json()["data"]
        assert detail["content_images"] == ["user_bank_question_images/content-a.png"]
        assert detail["answer_images"] == ["user_bank_question_images/answer-a.png"]
        assert detail["explanation_images"] == ["user_bank_question_images/explain-a.png"]
        assert detail["image_path"] == "user_bank_question_images/content-a.png"
    finally:
        _delete_bank(app, bank_id)


def test_question_detail_normalizes_legacy_upload_prefix(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"])
    question_id = _create_question(
        app,
        bank_id,
        seed_user["id"],
        image_path='["/uploads/questions/legacy-a.png"]',
    )

    try:
        response = auth_client.get(f"/user/banks/api/{bank_id}/questions/{question_id}")
        assert response.status_code == 200
        detail = response.get_json()["data"]
        assert detail["content_images"] == ["questions/legacy-a.png"]
        assert detail["image_path"] == "questions/legacy-a.png"
        assert json.loads(detail["image_path_json"]) == ["questions/legacy-a.png"]
    finally:
        _delete_bank(app, bank_id)


def test_upload_question_image_requires_owner(app, auth_client, seed_user):
    owner_id = _create_user(app)
    bank_id = _create_bank(app, owner_id, name="非本人题目图片题库")

    try:
        response = auth_client.post(
            f"/user/banks/api/{bank_id}/question-images/upload",
            data={"file": (BytesIO(_PNG_BYTES), "question.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 404
        assert response.get_json()["status"] == "error"
    finally:
        _delete_bank(app, bank_id)
        _delete_user(app, owner_id)
