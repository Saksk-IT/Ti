# -*- coding: utf-8 -*-
"""导出题目查询（scope/type/tag 筛选）"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.portable_question_format import any_type_to_portable_type

from .base import ExportRequest

logger = logging.getLogger(__name__)

MAX_EXPORT_QUESTIONS = 500


def _safe_load(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (list, dict, bool, int, float)):
        return raw
    s = str(raw).strip()
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def fetch_export_questions(req: ExportRequest) -> list[dict[str, Any]]:
    """根据导出请求筛选题目，返回 portable 格式的字典列表。"""
    params: dict[str, Any] = {"sid": req.subject_id}

    sql_parts = [
        "SELECT q.*, s.name AS subject_name",
        "FROM questions q",
        "JOIN subjects s ON q.subject_id = s.id",
        "WHERE q.subject_id = :sid",
    ]

    # scope 筛选
    if req.scope == "favorites" and req.user_id:
        sql_parts.append(
            "AND q.id IN (SELECT f.question_id FROM favorites f WHERE f.user_id = :uid)"
        )
        params["uid"] = req.user_id
    elif req.scope == "mistakes" and req.user_id:
        sql_parts.append(
            "AND q.id IN (SELECT m.question_id FROM mistakes m WHERE m.user_id = :uid)"
        )
        params["uid"] = req.user_id

    # 题型筛选
    if req.q_type and req.q_type != "all":
        portable_type = any_type_to_portable_type(req.q_type)
        sql_parts.append("AND q.type = :q_type")
        params["q_type"] = portable_type

    sql_parts.append("ORDER BY q.id")
    sql_parts.append(f"LIMIT {MAX_EXPORT_QUESTIONS}")

    sql = " ".join(sql_parts)
    rows = db.session.execute(text(sql), params).fetchall()

    # tag 筛选（在 Python 侧过滤）
    tag_ids: set[int] | None = None
    if req.tag and req.tag != "all" and req.user_id:
        try:
            from app.modules.quiz.services.question_tags_service import (
                get_question_ids_by_tag,
            )
            conn = db.session.connection()
            tag_ids = get_question_ids_by_tag(conn, req.user_id, req.tag)
        except Exception:
            logger.warning("获取标签题目 ID 失败", exc_info=True)
            tag_ids = set()

    questions: list[dict[str, Any]] = []
    for row in rows:
        q = dict(row._mapping)
        qid = int(q.get("id", 0))
        if tag_ids is not None and qid not in tag_ids:
            continue
        questions.append({
            "id": qid,
            "type": q.get("type") or "",
            "content": q.get("content") or "",
            "options": _safe_load(q.get("options"), []),
            "answer": _safe_load(q.get("answer"), []),
            "analysis": q.get("analysis") or q.get("explanation") or "",
            "tags": _safe_load(q.get("tags"), []),
            "difficulty": int(q.get("difficulty") or 1),
        })

    return questions
