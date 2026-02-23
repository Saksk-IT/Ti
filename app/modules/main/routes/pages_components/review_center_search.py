# -*- coding: utf-8 -*-
"""复盘中心 — 搜索 tab 数据加载。"""

from __future__ import annotations

from app.core.utils.database import safe_in_clause

from .review_center_helpers import _build_preview


def load_search_results(
    *,
    conn,
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

    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
        return [], 0

    if source_type == 'public':
        return _search_public(
            conn=conn, uid=uid, subject_id=subject_id, kind=kind,
            q_type=q_type, tag_ids=tag_ids, like=like,
            per_page=per_page, offset=offset, quiz_url=quiz_url,
        )
    return _search_bank(
        conn=conn, uid=uid, bank_id=bank_id, kind=kind,
        q_type=q_type, tag_ids=tag_ids, like=like,
        per_page=per_page, offset=offset, quiz_url=quiz_url,
    )


def _search_public(
    *, conn, uid: int, subject_id: int | None, kind: str,
    q_type: str, tag_ids: list | None, like: str,
    per_page: int, offset: int, quiz_url: str,
) -> tuple[list[dict], int]:
    base = """
        SELECT q.id, q.type as p_type, q.content,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
        LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
          AND q.subject_id = ?
          AND (q.content LIKE ? OR q.analysis LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
    """
    params: list = [int(uid), int(uid), int(subject_id), like, like, like, like]

    if kind == 'favorites':
        base += " AND f.id IS NOT NULL"
    elif kind == 'mistakes':
        base += " AND m.id IS NOT NULL"

    if q_type and q_type != 'all':
        from app.core.utils.portable_question_format import any_type_to_portable_type
        base += " AND q.type = ?"
        params.append(any_type_to_portable_type(q_type))

    if isinstance(tag_ids, list):
        base, params = safe_in_clause('q.id', tag_ids, base, params)

    count_sql = f"SELECT COUNT(1) FROM ({base})"
    search_total = int(conn.execute(count_sql, params).fetchone()[0] or 0)

    rows = conn.execute(
        base + " ORDER BY q.id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    from app.core.utils.portable_question_format import portable_type_to_q_type
    questions = []
    for r in rows or []:
        questions.append({
            'id': r['id'],
            'q_type': portable_type_to_q_type((r['p_type'] or '')),
            'is_fav': int(r['is_fav'] or 0),
            'is_mistake': int(r['is_mistake'] or 0),
            'content_preview': _build_preview(r['content'] or ''),
            'jump_url': quiz_url,
        })
    return questions, search_total


def _search_bank(
    *, conn, uid: int, bank_id: int, kind: str,
    q_type: str, tag_ids: list | None, like: str,
    per_page: int, offset: int, quiz_url: str,
) -> tuple[list[dict], int]:
    base = """
        SELECT q.id, q.type as p_type, q.content,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM user_bank_questions q
        LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
        LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
        WHERE q.bank_id = ?
          AND (q.content LIKE ? OR q.analysis LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
    """
    params: list = [int(uid), int(uid), int(bank_id), like, like, like, like]

    if kind == 'favorites':
        base += " AND f.id IS NOT NULL"
    elif kind == 'mistakes':
        base += " AND m.id IS NOT NULL"

    if q_type and q_type != 'all':
        from app.core.utils.portable_question_format import any_type_to_portable_type
        base += " AND q.type = ?"
        params.append(any_type_to_portable_type(q_type))

    if isinstance(tag_ids, list):
        base, params = safe_in_clause('q.id', tag_ids, base, params)

    count_sql = f"SELECT COUNT(1) FROM ({base})"
    search_total = int(conn.execute(count_sql, params).fetchone()[0] or 0)

    rows = conn.execute(
        base + " ORDER BY q.id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    from app.core.utils.portable_question_format import portable_type_to_q_type
    questions = []
    for r in rows or []:
        questions.append({
            'id': r['id'],
            'q_type': portable_type_to_q_type((r['p_type'] or ''), essay_q_type="简答题"),
            'is_fav': int(r['is_fav'] or 0),
            'is_mistake': int(r['is_mistake'] or 0),
            'content_preview': _build_preview(r['content'] or ''),
            'jump_url': quiz_url,
        })
    return questions, search_total
