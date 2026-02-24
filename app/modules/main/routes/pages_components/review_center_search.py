# -*- coding: utf-8 -*-
"""复盘中心 — 搜索 tab 数据加载。"""

from __future__ import annotations

from app.core.extensions import db
from sqlalchemy import text as sa_text

from .review_center_helpers import _build_preview


def _build_named_in(col: str, values: list, prefix: str = "in") -> tuple[str, dict]:
    """Build a named-parameter IN clause for SQLAlchemy text() queries."""
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ", ".join(f":{k}" for k in params)
    return f"{col} IN ({placeholders})", params


def load_search_results(
    *,
    conn,  # conn parameter kept for backward compatibility
    uid: int,
    source_type: str,
    subject_id: int | None,
    bank_id: int,
    kind: str,
    q_type: str,
    tag: str,
    tag_ids: list | None,
    keyword: str,
    page: int,
    per_page: int,
    quiz_url: str,
) -> tuple[list[dict], int]:
    """返回 (search_questions, search_total)。"""
    if not keyword:
        return [], 0

    like = f"%{keyword}%"
    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != "all":
        return [], 0

    if source_type == "public":
        return _search_public(
            uid=uid, subject_id=subject_id, kind=kind,
            q_type=q_type, tag_ids=tag_ids, like=like,
            per_page=per_page, offset=offset, quiz_url=quiz_url,
        )
    return _search_bank(
        uid=uid, bank_id=bank_id, kind=kind,
        q_type=q_type, tag_ids=tag_ids, like=like,
        per_page=per_page, offset=offset, quiz_url=quiz_url,
    )


def _search_public(
    *, uid: int, subject_id: int | None, kind: str,
    q_type: str, tag_ids: list | None, like: str,
    per_page: int, offset: int, quiz_url: str,
) -> tuple[list[dict], int]:
    base = """
        SELECT q.id, q.type as p_type, q.content,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = :uid
        LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = :uid2
        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
          AND q.subject_id = :subject_id
          AND (q.content LIKE :like1 OR q.analysis LIKE :like2 OR q.options LIKE :like3 OR q.answer LIKE :like4)
    """
    params: dict = {
        "uid": int(uid), "uid2": int(uid), "subject_id": int(subject_id),
        "like1": like, "like2": like, "like3": like, "like4": like,
    }

    if kind == "favorites":
        base += " AND f.id IS NOT NULL"
    elif kind == "mistakes":
        base += " AND m.id IS NOT NULL"

    if q_type and q_type != "all":
        from app.core.utils.portable_question_format import any_type_to_portable_type
        base += " AND q.type = :q_type"
        params["q_type"] = any_type_to_portable_type(q_type)

    if isinstance(tag_ids, list):
        in_clause, in_params = _build_named_in("q.id", tag_ids, "tag")
        base += f" AND {in_clause}"
        params.update(in_params)

    count_sql = f"SELECT COUNT(1) as cnt FROM ({base}) _sub"
    row = db.session.execute(sa_text(count_sql), params).fetchone()
    search_total = int(row._mapping["cnt"] or 0) if row else 0

    page_params = {**params, "per_page": per_page, "offset_val": offset}
    rows = db.session.execute(
        sa_text(base + " ORDER BY q.id DESC LIMIT :per_page OFFSET :offset_val"),
        page_params,
    ).fetchall()

    from app.core.utils.portable_question_format import portable_type_to_q_type
    questions = []
    for r in rows or []:
        rm = r._mapping
        questions.append({
            "id": rm["id"],
            "q_type": portable_type_to_q_type((rm["p_type"] or "")),
            "is_fav": int(rm["is_fav"] or 0),
            "is_mistake": int(rm["is_mistake"] or 0),
            "content_preview": _build_preview(rm["content"] or ""),
            "jump_url": quiz_url,
        })
    return questions, search_total


def _search_bank(
    *, uid: int, bank_id: int, kind: str,
    q_type: str, tag_ids: list | None, like: str,
    per_page: int, offset: int, quiz_url: str,
) -> tuple[list[dict], int]:
    base = """
        SELECT q.id, q.type as p_type, q.content,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM user_bank_questions q
        LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = :uid
        LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = :uid2
        WHERE q.bank_id = :bank_id
          AND (q.content LIKE :like1 OR q.analysis LIKE :like2 OR q.options LIKE :like3 OR q.answer LIKE :like4)
    """
    params: dict = {
        "uid": int(uid), "uid2": int(uid), "bank_id": int(bank_id),
        "like1": like, "like2": like, "like3": like, "like4": like,
    }

    if kind == "favorites":
        base += " AND f.id IS NOT NULL"
    elif kind == "mistakes":
        base += " AND m.id IS NOT NULL"

    if q_type and q_type != "all":
        from app.core.utils.portable_question_format import any_type_to_portable_type
        base += " AND q.type = :q_type"
        params["q_type"] = any_type_to_portable_type(q_type)

    if isinstance(tag_ids, list):
        in_clause, in_params = _build_named_in("q.id", tag_ids, "tag")
        base += f" AND {in_clause}"
        params.update(in_params)

    count_sql = f"SELECT COUNT(1) as cnt FROM ({base}) _sub"
    row = db.session.execute(sa_text(count_sql), params).fetchone()
    search_total = int(row._mapping["cnt"] or 0) if row else 0

    page_params = {**params, "per_page": per_page, "offset_val": offset}
    rows = db.session.execute(
        sa_text(base + " ORDER BY q.id DESC LIMIT :per_page OFFSET :offset_val"),
        page_params,
    ).fetchall()

    from app.core.utils.portable_question_format import portable_type_to_q_type
    questions = []
    for r in rows or []:
        rm = r._mapping
        questions.append({
            "id": rm["id"],
            "q_type": portable_type_to_q_type((rm["p_type"] or ""), essay_q_type="简答题"),
            "is_fav": int(rm["is_fav"] or 0),
            "is_mistake": int(rm["is_mistake"] or 0),
            "content_preview": _build_preview(rm["content"] or ""),
            "jump_url": quiz_url,
        })
    return questions, search_total
