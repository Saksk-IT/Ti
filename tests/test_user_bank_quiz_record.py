# -*- coding: utf-8 -*-
"""个人题库刷题记录接口回归测试。"""

from __future__ import annotations

import json
import pytest
from sqlalchemy import text

from app.core.extensions import db
from app.modules.quiz.routes.pages_helpers import (
    apply_question_shuffle,
    shuffle_choice_options,
)
from app.modules.user_bank.routes.api_quiz import _normalize_quiz_record_is_correct


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
        ("yes", True),
        ("no", False),
    ],
)
def test_normalize_quiz_record_is_correct_accepts_common_client_values(raw_value, expected):
    assert _normalize_quiz_record_is_correct(raw_value) is expected


@pytest.mark.parametrize("raw_value", [None, "", "maybe", 2, [], {}])
def test_normalize_quiz_record_is_correct_rejects_invalid_values(raw_value):
    with pytest.raises(ValueError):
        _normalize_quiz_record_is_correct(raw_value)


def test_shuffle_choice_options_remaps_single_choice_answer():
    question = {
        "id": 1,
        "q_type": "选择题",
        "options": [
            {"key": "A", "value": "错误项 A"},
            {"key": "B", "value": "正确项"},
            {"key": "C", "value": "错误项 C"},
        ],
        "answer": "B",
    }

    class ReverseRng:
        def shuffle(self, items):
            items.reverse()

    shuffled = shuffle_choice_options(question, rng=ReverseRng())

    assert [x["value"] for x in shuffled["options"]] == ["错误项 C", "正确项", "错误项 A"]
    assert [x["key"] for x in shuffled["options"]] == ["A", "B", "C"]
    assert shuffled["answer"] == "B"


def test_shuffle_choice_options_remaps_multi_choice_answer():
    question = {
        "id": 1,
        "q_type": "多选题",
        "options": [
            {"key": "A", "value": "正确项 A"},
            {"key": "B", "value": "错误项 B"},
            {"key": "C", "value": "正确项 C"},
        ],
        "answer": "AC",
    }

    class ReverseRng:
        def shuffle(self, items):
            items.reverse()

    shuffled = shuffle_choice_options(question, rng=ReverseRng())

    assert [x["value"] for x in shuffled["options"]] == ["正确项 C", "错误项 B", "正确项 A"]
    assert shuffled["answer"] == "AC"


def test_shuffle_choice_options_tracks_duplicate_option_identity():
    question = {
        "id": 1,
        "q_type": "选择题",
        "options": [
            {"key": "A", "value": "相同文本"},
            {"key": "B", "value": "相同文本"},
            {"key": "C", "value": "其他文本"},
        ],
        "answer": "B",
    }

    class ReverseRng:
        def shuffle(self, items):
            items.reverse()

    shuffled = shuffle_choice_options(question, rng=ReverseRng())

    assert [x["value"] for x in shuffled["options"]] == ["其他文本", "相同文本", "相同文本"]
    assert shuffled["answer"] == "B"


def test_apply_question_shuffle_reorders_without_in_place_mutation():
    questions = [{"id": 1}, {"id": 2}, {"id": 3}]
    shuffled, order = apply_question_shuffle(questions, saved_order=[3, 1, 2])

    assert [q["id"] for q in shuffled] == [3, 1, 2]
    assert order == [3, 1, 2]
    assert [q["id"] for q in questions] == [1, 2, 3]


def _create_bank_with_questions(app, user_id: int, question_types: list[str]) -> int:
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status, question_count)
                VALUES (:user_id, '打乱回归题库', 1, :question_count)
                RETURNING id
                """
            ),
            {"user_id": int(user_id), "question_count": len(question_types)},
        ).scalar_one()
        type_to_payload = {
            "single_choice": (json.dumps(["错误 A", "正确 B", "错误 C"], ensure_ascii=False), json.dumps([1])),
            "multi_choice": (json.dumps(["正确 A", "错误 B", "正确 C"], ensure_ascii=False), json.dumps([0, 2])),
            "boolean": (json.dumps([], ensure_ascii=False), json.dumps([True])),
        }
        for index, q_type in enumerate(question_types, start=1):
            options, answer = type_to_payload[q_type]
            db.session.execute(
                text(
                    """
                    INSERT INTO user_bank_questions
                    (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
                    VALUES
                    (:bank_id, :user_id, :type, :content, :options, :answer, '', '[]', 1, 'custom', :sort_order)
                    """
                ),
                {
                    "bank_id": int(bank_id),
                    "user_id": int(user_id),
                    "type": q_type,
                    "content": f"题目 {index}",
                    "options": options,
                    "answer": answer,
                    "sort_order": index,
                },
            )
        db.session.commit()
        return int(bank_id)


def test_bank_user_counts_reports_shuffle_options_availability(app, auth_client, seed_user):
    choice_bank_id = _create_bank_with_questions(app, seed_user["id"], ["single_choice", "multi_choice"])
    mixed_bank_id = _create_bank_with_questions(app, seed_user["id"], ["single_choice", "boolean"])

    try:
        choice_resp = auth_client.get(f"/user/banks/api/{choice_bank_id}/user-counts")
        assert choice_resp.status_code == 200
        choice_data = choice_resp.get_json()["data"]
        assert choice_data["types"] == ["多选题", "选择题"]
        assert choice_data["shuffle_options_available"] is True

        mixed_resp = auth_client.get(f"/user/banks/api/{mixed_bank_id}/user-counts")
        assert mixed_resp.status_code == 200
        mixed_data = mixed_resp.get_json()["data"]
        assert set(mixed_data["types"]) == {"判断题", "选择题"}
        assert mixed_data["shuffle_options_available"] is False
    finally:
        with app.app_context():
            db.session.execute(
                text("DELETE FROM user_question_banks WHERE id IN (:choice_bank_id, :mixed_bank_id)"),
                {"choice_bank_id": choice_bank_id, "mixed_bank_id": mixed_bank_id},
            )
            db.session.commit()


def test_web_user_bank_quiz_applies_saved_shuffle_order(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(
        app,
        seed_user["id"],
        ["single_choice", "single_choice", "single_choice"],
    )
    progress_key = f"quiz_progress_{seed_user['id']}_quiz_bank_{bank_id}_all_all_q1_o0"

    try:
        with app.app_context():
            db.session.execute(
                text(
                    """
                    INSERT INTO user_progress (user_id, p_key, data)
                    VALUES (:user_id, :p_key, :data)
                    """
                ),
                {
                    "user_id": int(seed_user["id"]),
                    "p_key": progress_key,
                    "data": json.dumps({"order": []}, ensure_ascii=False),
                },
            )
            ids = [
                int(row[0])
                for row in db.session.execute(
                    text("SELECT id FROM user_bank_questions WHERE bank_id = :bank_id ORDER BY sort_order"),
                    {"bank_id": int(bank_id)},
                ).fetchall()
            ]
            saved_order = [ids[2], ids[0], ids[1]]
            db.session.execute(
                text("UPDATE user_progress SET data = :data WHERE user_id = :user_id AND p_key = :p_key"),
                {
                    "user_id": int(seed_user["id"]),
                    "p_key": progress_key,
                    "data": json.dumps({"order": saved_order}, ensure_ascii=False),
                },
            )
            db.session.commit()

        response = auth_client.get(f"/quiz?bank_id={bank_id}&mode=quiz&shuffle_questions=1")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        positions = [html.index(f'data-id="{qid}"') for qid in saved_order]
        assert positions == sorted(positions)
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(
                text("DELETE FROM user_progress WHERE user_id = :user_id AND p_key = :p_key"),
                {"user_id": int(seed_user["id"]), "p_key": progress_key},
            )
            db.session.commit()
