# -*- coding: utf-8 -*-
"""个人题库 portable JSON 导入测试。"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import text

from app.core.extensions import db


def _create_empty_bank(app, user_id: int) -> int:
    bank_name = f"portable-json-import-{uuid.uuid4().hex[:8]}"
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status, question_count)
                VALUES (:user_id, :name, 1, 0)
                RETURNING id
                """
            ),
            {"user_id": int(user_id), "name": bank_name},
        ).scalar_one()
        db.session.commit()
        return int(bank_id)


def _delete_bank(app, bank_id: int | None) -> None:
    if bank_id is None:
        return
    with app.app_context():
        db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def test_import_questions_json_accepts_extension_portable_payload(app, auth_client, seed_user):
    bank_id = _create_empty_bank(app, seed_user["id"])
    payload = {
        "questions": [
            {
                "type": "single_choice",
                "content": "扩展导入测试题干",
                "options": ["选项 A", "选项 B"],
                "answer": [1],
                "analysis": "扩展导入解析",
                "tags": ["浏览器扩展"],
                "difficulty": 3,
            }
        ]
    }

    try:
        response = auth_client.post(
            f"/user/banks/api/{bank_id}/questions/import/json",
            json=payload,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["code"] == 0
        assert body["data"]["imported"] == 1

        with app.app_context():
            row = db.session.execute(
                text(
                    """
                    SELECT q.type, q.content, q.options, q.answer, q.analysis, q.tags, b.question_count
                    FROM user_bank_questions q
                    JOIN user_question_banks b ON b.id = q.bank_id
                    WHERE q.bank_id = :bank_id
                    """
                ),
                {"bank_id": int(bank_id)},
            ).mappings().one()

        assert row["type"] == "single_choice"
        assert row["content"] == "扩展导入测试题干"
        assert json.loads(row["options"]) == ["选项 A", "选项 B"]
        assert json.loads(row["answer"]) == [1]
        assert row["analysis"] == "扩展导入解析"
        assert json.loads(row["tags"]) == ["浏览器扩展"]
        assert row["question_count"] == 1
    finally:
        _delete_bank(app, bank_id)
