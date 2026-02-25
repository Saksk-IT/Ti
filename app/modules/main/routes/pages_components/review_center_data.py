# -*- coding: utf-8 -*-
"""复盘中心 — 数据 tab 统计逻辑。"""

from __future__ import annotations

from datetime import timedelta

from flask import current_app

from app.core.extensions import db
from sqlalchemy import text as sa_text
from app.core.utils.time_utils import today_bj

from .review_center_helpers import _build_preview, _url_with_params


# ── 通用工具 ──────────────────────────────────────────────


def _pct(n: int, d: int) -> float:
    try:
        return round((float(n) * 100.0 / float(d)) if d else 0.0, 1)
    except Exception:
        return 0.0


def _build_named_in(col: str, values: list, prefix: str = "in") -> tuple[str, dict]:
    """Build a named-parameter IN clause for SQLAlchemy text() queries."""
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ", ".join(f":{k}" for k in params)
    return f"{col} IN ({placeholders})", params


def _append_tag_clause(sql: str, params: dict, tag_ids, col: str = "q.id") -> tuple[str, dict]:
    if isinstance(tag_ids, list):
        in_clause, in_params = _build_named_in(col, tag_ids, "tag")
        sql += f" AND {in_clause}"
        params.update(in_params)
    return sql, params


def _append_type_clause(sql: str, params: dict, q_type: str, col: str = "q.type") -> tuple[str, dict]:
    if q_type and q_type != "all":
        from app.core.utils.portable_question_format import any_type_to_portable_type
        portable_type = any_type_to_portable_type(q_type)
        col = str(col or "q.type").replace(".q_type", ".type")
        sql += f" AND {col} = :type_filter"
        params["type_filter"] = portable_type
    return sql, params


# ── 题型分布 ──────────────────────────────────────────────


def load_type_distribution(
    *, conn, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, tag_ids, tag: str,
    q_type: str, base_url: str, ctx: dict,
) -> tuple[list[dict], int]:
    """返回 (type_dist, data_type_count)。conn parameter kept for backward compatibility."""
    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != "all":
        return [], 0

    if source_type == "public":
        base = """
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = :uid
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = :uid2
            WHERE (s.is_locked=false OR s.is_locked IS NULL)
              AND q.subject_id = :subject_id
        """
        params: dict = {"uid": int(uid), "uid2": int(uid), "subject_id": int(subject_id)}
        if kind == "favorites":
            base += " AND f.id IS NOT NULL"
        elif kind == "mistakes":
            base += " AND m.id IS NOT NULL"
        if isinstance(tag_ids, list):
            in_clause, in_params = _build_named_in("q.id", tag_ids, "tdist")
            base += f" AND {in_clause}"
            params.update(in_params)
        base += " GROUP BY q.type ORDER BY cnt DESC"
        rows = db.session.execute(sa_text(base), params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        dist = [
            {"q_type": portable_type_to_q_type((r._mapping["p_type"] or "")), "count": int(r._mapping["cnt"] or 0)}
            for r in (rows or []) if r and r._mapping["p_type"]
        ]
    else:
        base = """
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM user_bank_questions q
            LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = :uid
            LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = :uid2
            WHERE q.bank_id = :bank_id
        """
        params = {"uid": int(uid), "uid2": int(uid), "bank_id": int(bank_id)}
        if kind == "favorites":
            base += " AND f.id IS NOT NULL"
        elif kind == "mistakes":
            base += " AND m.id IS NOT NULL"
        if isinstance(tag_ids, list):
            in_clause, in_params = _build_named_in("q.id", tag_ids, "tdist")
            base += f" AND {in_clause}"
            params.update(in_params)
        base += " GROUP BY q.type ORDER BY cnt DESC"
        rows = db.session.execute(sa_text(base), params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        dist = [
            {"q_type": portable_type_to_q_type((r._mapping["p_type"] or ""), essay_q_type="简答题"), "count": int(r._mapping["cnt"] or 0)}
            for r in (rows or []) if r and r._mapping["p_type"]
        ]

    max_n = max([d["count"] for d in dist], default=0)
    type_dist = []
    for d in dist[:10]:
        d["pct"] = int(round((d["count"] * 100.0 / max_n), 0)) if max_n else 0
        d["practice_url"] = _url_with_params(base_url, {**ctx, "tab": "practice", "type": d["q_type"], "tag": tag})
        type_dist.append(d)
    return type_dist, len(dist)
