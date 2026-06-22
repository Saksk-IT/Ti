# -*- coding: utf-8 -*-
"""个人题库题目查重服务。"""

from __future__ import annotations

import difflib
import re
from typing import Any

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.pqf_rows import pqf_row_to_internal


DEFAULT_SIMILARITY_THRESHOLD = 0.8


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
        "total_questions": len(questions),
        "total_pairs": len(duplicates),
        "similarity_threshold": threshold,
        "duplicates": duplicates,
    }


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
        "answer": "" if answer is None else str(answer),
        "difficulty": int(question.get("difficulty") or 1),
        "sort_order": question.get("sort_order"),
    }


def _preview(value: str, limit: int = 120) -> str:
    text_value = re.sub(r"<[^>]+>", "", str(value or "")).replace("\n", " ").strip()
    return text_value[:limit] + "..." if len(text_value) > limit else text_value
