# -*- coding: utf-8 -*-
"""个人题库题目列表分页数量测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.core.extensions import db


def _create_bank_with_questions(app, user_id: int, total: int = 205) -> int:
    bank_name = f"分页数量测试题库-{uuid.uuid4().hex[:8]}"
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status, question_count)
                VALUES (:user_id, :name, 1, :question_count)
                RETURNING id
                """
            ),
            {
                "user_id": int(user_id),
                "name": bank_name,
                "question_count": int(total),
            },
        ).scalar_one()

        db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})

        for index in range(1, total + 1):
            db.session.execute(
                text(
                    """
                    INSERT INTO user_bank_questions (
                        bank_id, user_id, type, content, options, answer,
                        analysis, tags, difficulty, source_type, sort_order
                    )
                    VALUES (
                        :bank_id, :user_id, 'single_choice', :content, '["A","B"]',
                        '["A"]', '解析', '[]', 1, 'custom', :sort_order
                    )
                    """
                ),
                {
                    "bank_id": int(bank_id),
                    "user_id": int(user_id),
                    "content": f"分页测试题目 {index}",
                    "sort_order": int(index),
                },
            )
        db.session.commit()
        return int(bank_id)


def _delete_bank(app, bank_id: int | None) -> None:
    if bank_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def test_bank_questions_page_offers_larger_page_sizes(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], total=1)

    try:
        response = auth_client.get(f"/user/banks/{bank_id}")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert '<option value="100">100</option>' in html
        assert '<option value="200">200</option>' in html
    finally:
        _delete_bank(app, bank_id)


def test_bank_questions_api_accepts_and_caps_larger_page_sizes(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], total=205)

    try:
        response = auth_client.get(f"/user/banks/api/{bank_id}/questions?page=1&per_page=200")
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["data"]["per_page"] == 200
        assert payload["data"]["total"] == 205
        assert len(payload["data"]["questions"]) == 200

        capped_response = auth_client.get(f"/user/banks/api/{bank_id}/questions?page=1&per_page=999")
        capped_payload = capped_response.get_json()

        assert capped_response.status_code == 200
        assert capped_payload["status"] == "success"
        assert capped_payload["data"]["per_page"] == 200
        assert len(capped_payload["data"]["questions"]) == 200
    finally:
        _delete_bank(app, bank_id)
