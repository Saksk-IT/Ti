# -*- coding: utf-8 -*-
"""个人题库题目查重服务。"""

from __future__ import annotations

import difflib
import json
import re
from typing import Any

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.time_utils import now_bj
from app.core.utils.pqf_rows import pqf_row_to_internal


DEFAULT_SIMILARITY_THRESHOLD = 0.8
DUPLICATE_CHECK_KEY_PREFIX = "user_bank_duplicate_check"


def normalize_text(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_similarity_threshold(value: float | int | str | None) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        threshold = DEFAULT_SIMILARITY_THRESHOLD
    return max(0.0, min(threshold, 1.0))


def calculate_similarity(text_a: str, text_b: str) -> float:
    normalized_a = normalize_text(text_a)
    normalized_b = normalize_text(text_b)
    if not normalized_a or not normalized_b:
        return 0.0
    if normalized_a == normalized_b:
        return 1.0
    return round(difflib.SequenceMatcher(None, normalized_a, normalized_b).ratio(), 4)


def check_bank_duplicates(bank_id: int, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> dict[str, Any]:
    threshold = normalize_similarity_threshold(similarity_threshold)
    questions = _load_bank_questions(bank_id)
    duplicates: list[dict[str, Any]] = []

    for left_index in range(len(questions)):
        for right_index in range(left_index + 1, len(questions)):
            left = questions[left_index]
            right = questions[right_index]
            left_text = normalize_text(left.get("content") or "")
            right_text = normalize_text(right.get("content") or "")
            if not left_text or not right_text:
                continue
            if max(len(left_text), len(right_text)) > 2 * min(len(left_text), len(right_text)):
                continue

            similarity = calculate_similarity(left_text, right_text)
            if similarity < threshold:
                continue

            duplicates.append({
                "question1": _serialize_question(left),
                "question2": _serialize_question(right),
                "similarity": similarity,
                "similarity_percent": int(round(similarity * 100)),
            })

    duplicates.sort(key=lambda item: item["similarity"], reverse=True)
    return {
        "bank_id": int(bank_id),
        "has_result": True,
        "total_questions": len(questions),
        "total_pairs": len(duplicates),
        "similarity_threshold": threshold,
        "duplicates": duplicates,
    }


def build_duplicate_check_key(bank_id: int) -> str:
    return f"{DUPLICATE_CHECK_KEY_PREFIX}:{int(bank_id)}"


def empty_duplicate_check_result(bank_id: int) -> dict[str, Any]:
    return {
        "bank_id": int(bank_id),
        "has_result": False,
        "checked_at": None,
        "total_questions": 0,
        "total_pairs": 0,
        "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD,
        "duplicates": [],
    }


def load_saved_duplicate_check(user_id: int, bank_id: int) -> dict[str, Any]:
    row = db.session.execute(
        text(
            """
            SELECT data
            FROM user_progress
            WHERE user_id = :user_id AND p_key = :p_key
            """
        ),
        {"user_id": int(user_id), "p_key": build_duplicate_check_key(bank_id)},
    ).fetchone()
    if not row:
        return empty_duplicate_check_result(bank_id)

    try:
        data = json.loads(row._mapping.get("data") or "{}")
    except Exception:
        return empty_duplicate_check_result(bank_id)
    if not isinstance(data, dict):
        return empty_duplicate_check_result(bank_id)

    saved = dict(data)
    saved["bank_id"] = int(bank_id)
    saved["has_result"] = True
    saved["duplicates"] = saved.get("duplicates") if isinstance(saved.get("duplicates"), list) else []
    saved["total_pairs"] = int(saved.get("total_pairs") or len(saved["duplicates"]))
    saved["total_questions"] = int(saved.get("total_questions") or 0)
    saved["similarity_threshold"] = normalize_similarity_threshold(saved.get("similarity_threshold"))
    return saved


def save_duplicate_check_result(user_id: int, bank_id: int, result: dict[str, Any]) -> dict[str, Any]:
    payload = {
        **(result or {}),
        "bank_id": int(bank_id),
        "has_result": True,
        "checked_at": now_bj().isoformat(timespec="seconds"),
    }
    payload["duplicates"] = payload.get("duplicates") if isinstance(payload.get("duplicates"), list) else []
    payload["total_pairs"] = int(payload.get("total_pairs") or len(payload["duplicates"]))
    payload["total_questions"] = int(payload.get("total_questions") or 0)
    payload["similarity_threshold"] = normalize_similarity_threshold(payload.get("similarity_threshold"))
    data_json = json.dumps(payload, ensure_ascii=False)
    key = build_duplicate_check_key(bank_id)

    existing = db.session.execute(
        text("SELECT id FROM user_progress WHERE user_id = :user_id AND p_key = :p_key"),
        {"user_id": int(user_id), "p_key": key},
    ).fetchone()
    if existing:
        db.session.execute(
            text(
                """
                UPDATE user_progress
                SET data = :data, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND p_key = :p_key
                """
            ),
            {"data": data_json, "user_id": int(user_id), "p_key": key},
        )
    else:
        db.session.execute(
            text(
                """
                INSERT INTO user_progress (user_id, p_key, data)
                VALUES (:user_id, :p_key, :data)
                """
            ),
            {"user_id": int(user_id), "p_key": key, "data": data_json},
        )
    db.session.commit()
    return payload


def prune_saved_duplicate_check_questions(user_id: int, bank_id: int, question_ids: list[int] | set[int]) -> dict[str, Any] | None:
    """从已保存查重快照里移除包含已删除题目的重复组，不触发重新查重。"""
    ids = {int(qid) for qid in question_ids if _to_int(qid) is not None}
    if not ids:
        return None

    saved = load_saved_duplicate_check(int(user_id), int(bank_id))
    if not saved.get("has_result"):
        return None

    pairs = saved.get("duplicates") if isinstance(saved.get("duplicates"), list) else []
    matched_ids = {
        qid
        for pair in pairs
        for qid in (_pair_question_id(pair, "question1"), _pair_question_id(pair, "question2"))
        if qid in ids
    }
    kept_pairs = [
        pair for pair in pairs
        if _pair_question_id(pair, "question1") not in ids and _pair_question_id(pair, "question2") not in ids
    ]
    saved["duplicates"] = kept_pairs
    saved["total_pairs"] = len(kept_pairs)
    total_questions = _to_int(saved.get("total_questions")) or 0
    if matched_ids and total_questions:
        saved["total_questions"] = max(0, total_questions - len(matched_ids))
    saved["similarity_threshold"] = normalize_similarity_threshold(saved.get("similarity_threshold"))

    db.session.execute(
        text(
            """
            UPDATE user_progress
            SET data = :data, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id AND p_key = :p_key
            """
        ),
        {
            "data": json.dumps(saved, ensure_ascii=False),
            "user_id": int(user_id),
            "p_key": build_duplicate_check_key(bank_id),
        },
    )
    return saved


def run_and_save_duplicate_check(
    user_id: int,
    bank_id: int,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict[str, Any]:
    result = check_bank_duplicates(int(bank_id), similarity_threshold)
    return save_duplicate_check_result(int(user_id), int(bank_id), result)


def _load_bank_questions(bank_id: int) -> list[dict[str, Any]]:
    rows = db.session.execute(
        text(
            """
            SELECT id, bank_id, user_id, type, content, options, answer, analysis,
                   tags, difficulty, image_path, source_type, source_question_id,
                   sort_order, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = :bank_id
            ORDER BY sort_order ASC, id ASC
            """
        ),
        {"bank_id": int(bank_id)},
    ).fetchall()

    questions: list[dict[str, Any]] = []
    for row in rows or []:
        question = pqf_row_to_internal(row, scope="user_bank")
        question["sort_order"] = row._mapping.get("sort_order")
        questions.append(question)
    return questions


def _serialize_question(question: dict[str, Any]) -> dict[str, Any]:
    content = str(question.get("content") or "")
    answer = question.get("answer")
    return {
        "id": int(question.get("id") or 0),
        "q_type": question.get("q_type") or "",
        "content": content,
        "content_preview": _preview(content),
        "options": question.get("options") if isinstance(question.get("options"), list) else [],
        "answer": "" if answer is None else str(answer),
        "explanation": question.get("explanation") or "",
        "tags": question.get("tags") if isinstance(question.get("tags"), list) else [],
        "difficulty": int(question.get("difficulty") or 1),
        "sort_order": question.get("sort_order"),
        "content_images": question.get("content_images") if isinstance(question.get("content_images"), list) else [],
        "answer_images": question.get("answer_images") if isinstance(question.get("answer_images"), list) else [],
        "explanation_images": question.get("explanation_images") if isinstance(question.get("explanation_images"), list) else [],
    }


def _pair_question_id(pair: dict[str, Any], key: str) -> int | None:
    if not isinstance(pair, dict):
        return None
    question = pair.get(key)
    if not isinstance(question, dict):
        return None
    return _to_int(question.get("id"))


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _preview(value: str, limit: int = 120) -> str:
    text_value = re.sub(r"<[^>]+>", "", str(value or "")).replace("\n", " ").strip()
    return text_value[:limit] + "..." if len(text_value) > limit else text_value
