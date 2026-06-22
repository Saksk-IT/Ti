# -*- coding: utf-8 -*-
"""个人题库题目查重测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db


def _create_user(app, prefix: str = "duplicate_owner") -> int:
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


def _delete_user(app, user_id: int | None) -> None:
    if user_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": int(user_id)})
        db.session.commit()


def _create_bank(app, user_id: int, name: str = "查重测试题库") -> int:
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status, question_count)
                VALUES (:user_id, :name, 1, 0)
                RETURNING id
                """
            ),
            {"user_id": int(user_id), "name": f"{name}-{uuid.uuid4().hex[:6]}"},
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _delete_bank(app, bank_id: int | None) -> None:
    if bank_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM user_progress WHERE p_key = :p_key"), {"p_key": f"user_bank_duplicate_check:{int(bank_id)}"})
        db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def _insert_question(app, bank_id: int, user_id: int, content: str, sort_order: int) -> int:
    with app.app_context():
        question_id = db.session.execute(
            text(
                """
                INSERT INTO user_bank_questions (
                    bank_id, user_id, type, content, options, answer,
                    analysis, tags, difficulty, source_type, sort_order
                )
                VALUES (
                    :bank_id, :user_id, 'single_choice', :content,
                    '["A","B"]', '["A"]', '解析', '[]', 1, 'custom', :sort_order
                )
                RETURNING id
                """
            ),
            {
                "bank_id": int(bank_id),
                "user_id": int(user_id),
                "content": content,
                "sort_order": int(sort_order),
            },
        ).scalar_one()
        count = db.session.execute(
            text("SELECT COUNT(*) FROM user_bank_questions WHERE bank_id = :bank_id"),
            {"bank_id": int(bank_id)},
        ).scalar_one()
        db.session.execute(
            text("UPDATE user_question_banks SET question_count = :count WHERE id = :bank_id"),
            {"count": int(count), "bank_id": int(bank_id)},
        )
        db.session.commit()
        return int(question_id)


def test_user_bank_duplicate_check_post_saves_and_get_keeps_result(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"])
    try:
        first_id = _insert_question(app, bank_id, seed_user["id"], "数据库事务的四个特性包括原子性、一致性、隔离性和持久性。", 1)
        second_id = _insert_question(app, bank_id, seed_user["id"], "数据库事务的四个特性包括原子性、一致性、隔离性和持久性。", 2)
        _insert_question(app, bank_id, seed_user["id"], "完全不同的网络协议分层模型题目。", 3)

        empty_response = auth_client.get(f"/user/banks/api/{bank_id}/questions/duplicate-check")
        empty_payload = empty_response.get_json()

        assert empty_response.status_code == 200
        assert empty_payload["status"] == "success"
        assert empty_payload["data"]["has_result"] is False
        assert empty_payload["data"]["total_pairs"] == 0

        response = auth_client.post(
            f"/user/banks/api/{bank_id}/questions/duplicate-check",
            json={"similarity_threshold": 0.9},
        )
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        data = payload["data"]
        assert data["has_result"] is True
        assert data["checked_at"]
        assert data["total_questions"] == 3
        assert data["total_pairs"] == 1
        assert data["similarity_threshold"] == 0.9
        assert data["duplicates"][0]["similarity"] == 1.0
        assert {
            data["duplicates"][0]["question1"]["id"],
            data["duplicates"][0]["question2"]["id"],
        } == {first_id, second_id}

        fourth_id = _insert_question(app, bank_id, seed_user["id"], "数据库事务的四个特性包括原子性、一致性、隔离性和持久性。", 4)
        saved_response = auth_client.get(f"/user/banks/api/{bank_id}/questions/duplicate-check")
        saved_data = saved_response.get_json()["data"]

        assert saved_response.status_code == 200
        assert saved_data["has_result"] is True
        assert saved_data["total_questions"] == 3
        assert saved_data["total_pairs"] == 1

        rerun_response = auth_client.post(
            f"/user/banks/api/{bank_id}/questions/duplicate-check",
            json={"similarity_threshold": 0.9},
        )
        rerun_data = rerun_response.get_json()["data"]

        assert rerun_response.status_code == 200
        assert rerun_data["total_questions"] == 4
        assert rerun_data["total_pairs"] == 3

        delete_response = auth_client.delete(f"/user/banks/api/{bank_id}/questions/{second_id}")
        pruned_response = auth_client.get(f"/user/banks/api/{bank_id}/questions/duplicate-check")
        pruned_data = pruned_response.get_json()["data"]
        remaining_ids = {
            question["id"]
            for pair in pruned_data["duplicates"]
            for question in (pair["question1"], pair["question2"])
        }

        assert delete_response.status_code == 200
        assert pruned_response.status_code == 200
        assert pruned_data["has_result"] is True
        assert pruned_data["total_questions"] == 3
        assert pruned_data["total_pairs"] == 1
        assert second_id not in remaining_ids
        assert {first_id, fourth_id}.issubset(remaining_ids)
    finally:
        _delete_bank(app, bank_id)


def test_user_bank_duplicate_check_requires_owner(app, auth_client):
    owner_id = _create_user(app)
    bank_id = _create_bank(app, owner_id, name="非本人查重测试题库")
    try:
        _insert_question(app, bank_id, owner_id, "重复题目 A", 1)
        _insert_question(app, bank_id, owner_id, "重复题目 A", 2)

        get_response = auth_client.get(f"/user/banks/api/{bank_id}/questions/duplicate-check")
        post_response = auth_client.post(f"/user/banks/api/{bank_id}/questions/duplicate-check", json={})

        assert get_response.status_code == 404
        assert get_response.get_json()["status"] == "error"
        assert post_response.status_code == 404
        assert post_response.get_json()["status"] == "error"
    finally:
        _delete_bank(app, bank_id)
        _delete_user(app, owner_id)


def test_user_bank_questions_page_links_to_dedicated_duplicate_check_page(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], name="查重页面入口测试题库")
    try:
        response = auth_client.get(f"/user/banks/{bank_id}")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'id="ubmDuplicateCheckBtn"' in html
        assert f'href="/user/banks/{bank_id}/duplicate-check"' in html
        assert 'id="ubmDuplicateOverlay"' not in html
        assert 'id="ubmDuplicateThreshold"' not in html
        assert "查重去重" in html
    finally:
        _delete_bank(app, bank_id)


def test_user_bank_duplicate_check_page_renders_dedicated_controls(app, auth_client, seed_user):
    bank_id = _create_bank(app, seed_user["id"], name="独立查重页面测试题库")
    try:
        response = auth_client.get(f"/user/banks/{bank_id}/duplicate-check")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'id="ubdRunBtn"' in html
        assert 'id="ubdThreshold"' in html
        assert 'id="ubdList"' in html
        assert 'id="ubdDetailOverlay"' in html
        assert 'id="ubdModalBody1"' in html
        assert 'id="ubdModalBody2"' in html
        assert "再次查重" in html
        assert "返回题目管理" in html
    finally:
        _delete_bank(app, bank_id)
