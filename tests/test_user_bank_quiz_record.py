# -*- coding: utf-8 -*-
"""个人题库刷题记录接口回归测试。"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
import pytest
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.core.utils.jwt_utils import generate_jwt_token
from app.core.utils.user_state_cache import invalidate_user_state
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
            "essay": (json.dumps([], ensure_ascii=False), json.dumps(["参考答案"], ensure_ascii=False)),
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


def _create_public_subject_with_questions(app, question_count: int) -> tuple[int, str]:
    subject_name = "全量加载回归科目"
    with app.app_context():
        db.session.execute(text("DELETE FROM questions WHERE subject_id IN (SELECT id FROM subjects WHERE name = :name)"), {"name": subject_name})
        db.session.execute(text("DELETE FROM subjects WHERE name = :name"), {"name": subject_name})
        subject_id = db.session.execute(
            text(
                """
                INSERT INTO subjects (name, description, is_locked)
                VALUES (:name, 'full load regression', 0)
                RETURNING id
                """
            ),
            {"name": subject_name},
        ).scalar_one()
        for index in range(1, question_count + 1):
            db.session.execute(
                text(
                    """
                    INSERT INTO questions
                    (subject_id, type, content, options, answer, analysis, tags, difficulty)
                    VALUES
                    (:subject_id, 'single_choice', :content, :options, :answer, '', '[]', 1)
                    """
                ),
                {
                    "subject_id": int(subject_id),
                    "content": f"公共题目 {index}",
                    "options": json.dumps(["错误 A", "正确 B", "错误 C"], ensure_ascii=False),
                    "answer": json.dumps([1], ensure_ascii=False),
                },
            )
        db.session.commit()
        return int(subject_id), subject_name


def _create_jwt_test_user(app) -> tuple[int, dict[str, str]]:
    suffix = uuid.uuid4().hex[:8]
    username = f"full_load_user_{suffix}"
    openid = f"openid_{username}"
    with app.app_context():
        user_id = db.session.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, is_admin, has_password_set, openid, session_version)
                VALUES (:username, :email, :password_hash, 0, 1, :openid, 0)
                RETURNING id
                """
            ),
            {
                "username": username,
                "email": f"{username}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
                "openid": openid,
            },
        ).scalar_one()
        db.session.commit()
        invalidate_user_state(int(user_id))
        token = generate_jwt_token(user_id=int(user_id), openid=openid, session_version=0)
    return int(user_id), {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


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
                text("DELETE FROM user_bank_questions WHERE bank_id IN (:choice_bank_id, :mixed_bank_id)"),
                {"choice_bank_id": choice_bank_id, "mixed_bank_id": mixed_bank_id},
            )
            db.session.execute(
                text("DELETE FROM user_question_banks WHERE id IN (:choice_bank_id, :mixed_bank_id)"),
                {"choice_bank_id": choice_bank_id, "mixed_bank_id": mixed_bank_id},
            )
            db.session.commit()


def test_bank_quiz_questions_full_load_returns_all_questions(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], ["single_choice"] * 55)

    try:
        response = auth_client.get(f"/user/banks/api/{bank_id}/quiz?full_load=1")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["total"] == 55
        assert data["page"] == 1
        assert data["per_page"] == 55
        assert len(data["questions"]) == 55
        assert data["questions"][0]["content"] == "题目 1"
        assert data["questions"][-1]["content"] == "题目 55"
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.commit()


def test_public_quiz_questions_full_load_returns_all_questions(app):
    subject_id, subject_name = _create_public_subject_with_questions(app, 55)
    user_id, headers = _create_jwt_test_user(app)
    api_client = app.test_client()

    try:
        response = api_client.get(
            f"/api/quiz/questions?subject={subject_name}&full_load=1",
            headers=headers,
        )
        assert response.status_code == 200, response.get_json()
        data = response.get_json()["data"]
        assert data["total"] == 55
        assert data["page"] == 1
        assert data["per_page"] == 55
        assert len(data["questions"]) == 55
        assert data["questions"][0]["content"] == "公共题目 1"
        assert data["questions"][-1]["content"] == "公共题目 55"
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM questions WHERE subject_id = :subject_id"), {"subject_id": int(subject_id)})
            db.session.execute(text("DELETE FROM subjects WHERE id = :subject_id"), {"subject_id": int(subject_id)})
            invalidate_user_state(int(user_id))
            db.session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": int(user_id)})
            db.session.commit()


def test_bank_quiz_questions_supports_page_per_page_pagination(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], ["single_choice"] * 55)

    try:
        first_resp = auth_client.get(f"/user/banks/api/{bank_id}/quiz?page=1&per_page=50")
        assert first_resp.status_code == 200
        first_data = first_resp.get_json()["data"]
        assert first_data["total"] == 55
        assert len(first_data["questions"]) == 50
        assert first_data["questions"][0]["content"] == "题目 1"
        assert first_data["questions"][-1]["content"] == "题目 50"

        second_resp = auth_client.get(f"/user/banks/api/{bank_id}/quiz?page=2&per_page=50")
        assert second_resp.status_code == 200
        second_data = second_resp.get_json()["data"]
        assert second_data["total"] == 55
        assert len(second_data["questions"]) == 5
        assert [q["content"] for q in second_data["questions"]] == [
            "题目 51",
            "题目 52",
            "题目 53",
            "题目 54",
            "题目 55",
        ]
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.commit()


def test_web_user_bank_subjective_grade_records_bank_answer(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], ["essay"])

    try:
        with app.app_context():
            question_id = int(
                db.session.execute(
                    text("SELECT id FROM user_bank_questions WHERE bank_id = :bank_id"),
                    {"bank_id": int(bank_id)},
                ).scalar_one()
            )

        response = auth_client.post(
            "/api/grade_subjective",
            json={
                "question_id": question_id,
                "user_answer": "我的答案",
                "grading_mode": "auto_full",
                "source": "user_bank",
                "bank_id": bank_id,
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200, response.get_json()
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["data"]["is_correct"] is True

        with app.app_context():
            recorded = db.session.execute(
                text(
                    """
                    SELECT user_answer, is_correct
                    FROM user_bank_answers
                    WHERE user_id = :user_id AND bank_id = :bank_id AND question_id = :question_id
                    """
                ),
                {
                    "user_id": int(seed_user["id"]),
                    "bank_id": int(bank_id),
                    "question_id": int(question_id),
                },
            ).fetchone()
            assert recorded is not None
            assert recorded._mapping["user_answer"] == "我的答案"
            assert bool(recorded._mapping["is_correct"]) is True
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_bank_answers WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_mistakes WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.commit()


def test_quiz_subjective_grade_falls_back_to_user_bank_question(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], ["essay"])

    try:
        with app.app_context():
            question_id = int(
                db.session.execute(
                    text("SELECT id FROM user_bank_questions WHERE bank_id = :bank_id"),
                    {"bank_id": int(bank_id)},
                ).scalar_one()
            )

        response = auth_client.post(
            "/api/quiz/grade_subjective",
            json={
                "question_id": question_id,
                "user_answer": "小程序旧请求",
                "grading_mode": "auto_full",
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200, response.get_json()
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["data"]["is_correct"] is True

        with app.app_context():
            recorded = db.session.execute(
                text(
                    """
                    SELECT user_answer, is_correct
                    FROM user_bank_answers
                    WHERE user_id = :user_id AND bank_id = :bank_id AND question_id = :question_id
                    """
                ),
                {
                    "user_id": int(seed_user["id"]),
                    "bank_id": int(bank_id),
                    "question_id": int(question_id),
                },
            ).fetchone()
            assert recorded is not None
            assert recorded._mapping["user_answer"] == "小程序旧请求"
            assert bool(recorded._mapping["is_correct"]) is True
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_bank_answers WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_mistakes WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.commit()


def test_user_bank_subjective_manual_mode_returns_pending_without_recording(app, auth_client, seed_user):
    bank_id = _create_bank_with_questions(app, seed_user["id"], ["essay"])

    try:
        with app.app_context():
            question_id = int(
                db.session.execute(
                    text("SELECT id FROM user_bank_questions WHERE bank_id = :bank_id"),
                    {"bank_id": int(bank_id)},
                ).scalar_one()
            )

        response = auth_client.post(
            "/api/grade_subjective",
            json={
                "question_id": question_id,
                "user_answer": "我先看参考答案再自评",
                "grading_mode": "manual",
                "source": "user_bank",
                "bank_id": bank_id,
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200, response.get_json()
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["code"] == 0
        assert payload["data"]["pending"] is True
        assert payload["data"]["is_correct"] is None
        assert payload["data"]["standard_answer"] == "参考答案"

        with app.app_context():
            recorded = db.session.execute(
                text(
                    """
                    SELECT 1
                    FROM user_bank_answers
                    WHERE user_id = :user_id AND bank_id = :bank_id AND question_id = :question_id
                    """
                ),
                {
                    "user_id": int(seed_user["id"]),
                    "bank_id": int(bank_id),
                    "question_id": int(question_id),
                },
            ).fetchone()
            assert recorded is None
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_bank_answers WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_mistakes WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.commit()


def test_user_bank_subjective_ai_mode_returns_feedback_and_records_result(app, auth_client, seed_user, monkeypatch):
    from app.modules.exam.services import ai_grading_service

    bank_id = _create_bank_with_questions(app, seed_user["id"], ["essay"])

    def fake_grade_essay_answer(question_content, standard_answer, user_answer):
        assert question_content == "题目 1"
        assert standard_answer == "参考答案"
        assert user_answer == "遗漏关键点"
        return SimpleNamespace(score=42, is_correct=False, feedback="缺少核心要点")

    monkeypatch.setattr(ai_grading_service, "grade_essay_answer", fake_grade_essay_answer)

    try:
        with app.app_context():
            question_id = int(
                db.session.execute(
                    text("SELECT id FROM user_bank_questions WHERE bank_id = :bank_id"),
                    {"bank_id": int(bank_id)},
                ).scalar_one()
            )

        response = auth_client.post(
            "/api/quiz/grade_subjective",
            json={
                "question_id": question_id,
                "user_answer": "遗漏关键点",
                "grading_mode": "ai",
                "source": "user_bank",
                "bank_id": bank_id,
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        assert response.status_code == 200, response.get_json()
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["code"] == 0
        assert payload["data"]["grading"] == "ai"
        assert payload["data"]["is_correct"] is False
        assert payload["data"]["score"] == 42
        assert payload["data"]["feedback"] == "缺少核心要点"

        with app.app_context():
            recorded = db.session.execute(
                text(
                    """
                    SELECT user_answer, is_correct
                    FROM user_bank_answers
                    WHERE user_id = :user_id AND bank_id = :bank_id AND question_id = :question_id
                    """
                ),
                {
                    "user_id": int(seed_user["id"]),
                    "bank_id": int(bank_id),
                    "question_id": int(question_id),
                },
            ).fetchone()
            assert recorded is not None
            assert recorded._mapping["user_answer"] == "遗漏关键点"
            assert bool(recorded._mapping["is_correct"]) is False
    finally:
        with app.app_context():
            db.session.execute(text("DELETE FROM user_bank_answers WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_mistakes WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
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
            db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(
                text("DELETE FROM user_progress WHERE user_id = :user_id AND p_key = :p_key"),
                {"user_id": int(seed_user["id"]), "p_key": progress_key},
            )
            db.session.commit()
