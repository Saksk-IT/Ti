# -*- coding: utf-8 -*-
"""个人题库题目删除接口测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db


def _create_bank(app, user_id: int, *, question_count: int = 0) -> int:
    name = f"删除题目测试题库-{uuid.uuid4().hex[:8]}"
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status, question_count)
                VALUES (:user_id, :name, 1, :question_count)
                RETURNING id
                """
            ),
            {"user_id": int(user_id), "name": name, "question_count": int(question_count)},
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _insert_question(app, bank_id: int, user_id: int, content: str) -> int:
    with app.app_context():
        question_id = db.session.execute(
            text(
                """
                INSERT INTO user_bank_questions (
                    bank_id, user_id, type, content, options, answer,
                    analysis, tags, difficulty, source_type, sort_order
                )
                VALUES (
                    :bank_id, :user_id, 'single_choice', :content, '["A","B"]',
                    '["A"]', '解析', '[]', 1, 'custom', 1
                )
                RETURNING id
                """
            ),
            {"bank_id": int(bank_id), "user_id": int(user_id), "content": content},
        ).scalar_one()
        db.session.commit()
        return int(question_id)


def _create_user(app, suffix: str) -> int:
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
                "username": f"delete_question_{suffix}",
                "email": f"delete_question_{suffix}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
            },
        ).scalar_one()
        db.session.commit()
        return int(user_id)


def _client_for_user(app, user_id: int):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = int(user_id)
        sess["username"] = f"user_{user_id}"
    return client


def _cleanup(app, *, bank_id: int | None = None, user_id: int | None = None) -> None:
    with app.app_context():
        if bank_id is not None:
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        if user_id is not None:
            db.session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": int(user_id)})
        db.session.commit()


def test_delete_bank_question_removes_question_and_recomputes_count(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], question_count=99)
    first_id = _insert_question(app, bank_id, seed_user["id"], "删除测试题目 1")
    second_id = _insert_question(app, bank_id, seed_user["id"], "删除测试题目 2")

    try:
        response = auth_client.delete(f"/user/banks/api/{bank_id}/questions/{first_id}")
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["code"] == 0
        assert payload["message"] == "删除成功"

        with app.app_context():
            deleted = db.session.execute(
                text("SELECT id FROM user_bank_questions WHERE id = :qid"),
                {"qid": int(first_id)},
            ).fetchone()
            remaining = db.session.execute(
                text("SELECT id FROM user_bank_questions WHERE id = :qid"),
                {"qid": int(second_id)},
            ).fetchone()
            count = db.session.execute(
                text("SELECT question_count FROM user_question_banks WHERE id = :bank_id"),
                {"bank_id": int(bank_id)},
            ).scalar_one()

        assert deleted is None
        assert remaining is not None
        assert count == 1
    finally:
        _cleanup(app, bank_id=bank_id)


def test_delete_bank_question_requires_owner(app, seed_user):
    bank_id = _create_bank(app, seed_user["id"], question_count=1)
    question_id = _insert_question(app, bank_id, seed_user["id"], "非 owner 删除测试题目")
    other_user_id = _create_user(app, uuid.uuid4().hex[:8])
    other_client = _client_for_user(app, other_user_id)

    try:
        response = other_client.delete(f"/user/banks/api/{bank_id}/questions/{question_id}")
        payload = response.get_json()

        assert response.status_code == 404
        assert payload["status"] == "error"
        assert payload["message"] == "题库不存在或无权操作"

        with app.app_context():
            question = db.session.execute(
                text("SELECT id FROM user_bank_questions WHERE id = :qid"),
                {"qid": int(question_id)},
            ).fetchone()
            count = db.session.execute(
                text("SELECT question_count FROM user_question_banks WHERE id = :bank_id"),
                {"bank_id": int(bank_id)},
            ).scalar_one()

        assert question is not None
        assert count == 1
    finally:
        _cleanup(app, bank_id=bank_id, user_id=other_user_id)


def test_delete_bank_question_returns_not_found_for_missing_question(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], question_count=0)

    try:
        response = auth_client.delete(f"/user/banks/api/{bank_id}/questions/99999999")
        payload = response.get_json()

        assert response.status_code == 404
        assert payload["status"] == "error"
        assert payload["message"] == "题目不存在"
    finally:
        _cleanup(app, bank_id=bank_id)
