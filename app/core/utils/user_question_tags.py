# -*- coding: utf-8 -*-
"""按用户维度的题目标签存储（跨题库统一）。

设计目标：
- 同一题目在不同用户下可有不同 tags（系统题库/个人题库/共享题库均适用）。
- tags 采用“规范化明细表”存储：一行一个 tag，便于按 tag 过滤与统计。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.core.utils.portable_question_format import normalize_tags


SCOPE_QUESTION_CENTER = "question_center"
SCOPE_USER_BANK = "user_bank"
TAG_DEF_QUESTION_ID = 0
DEFAULT_SCOPE_ID = 0


def _normalize_scope_id(scope_id: Optional[int]) -> int:
    """SQLite UNIQUE/PRIMARY KEY 对 NULL 的处理会导致去重失效；因此 scope_id 统一落为非 NULL。"""
    try:
        return int(DEFAULT_SCOPE_ID if scope_id is None else scope_id)
    except Exception:
        return int(DEFAULT_SCOPE_ID)


def _clean_tag_list(tags: Any, *, max_len: int = 20) -> List[str]:
    out = []
    for t in normalize_tags(tags):
        t = str(t).strip()
        if not t:
            continue
        if len(t) > max_len:
            t = t[:max_len]
        if t and t not in out:
            out.append(t)
    return out


def ensure_tag_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_question_tag_items (
            user_id INTEGER NOT NULL,
            scope TEXT NOT NULL,
            scope_id INTEGER NOT NULL DEFAULT 0,
            question_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, scope, scope_id, question_id, tag),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_uqti_user_scope_scopeid_tag ON user_question_tag_items(user_id, scope, scope_id, tag)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_uqti_user_scope_scopeid_qid ON user_question_tag_items(user_id, scope, scope_id, question_id)"
    )


def set_question_tags(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
    question_id: int,
    tags: Any,
) -> List[str]:
    """覆盖设置某题 tags（返回清洗后的 tags 列表）。"""
    ensure_tag_tables(conn)
    cleaned = _clean_tag_list(tags)
    sid = _normalize_scope_id(scope_id)

    conn.execute(
        """
        DELETE FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id = ? AND question_id = ?
        """,
        (int(user_id), str(scope), int(sid), int(question_id)),
    )

    if cleaned:
        conn.executemany(
            """
            INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(int(user_id), str(scope), int(sid), int(question_id), t) for t in cleaned],
        )
        conn.execute(
            """
            UPDATE user_question_tag_items
            SET updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND scope = ? AND scope_id = ? AND question_id = ?
            """,
            (int(user_id), str(scope), int(sid), int(question_id)),
        )
    return cleaned


def get_question_tags(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
    question_id: int,
) -> List[str]:
    ensure_tag_tables(conn)
    sid = _normalize_scope_id(scope_id)
    rows = conn.execute(
        """
        SELECT tag
        FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id = ? AND question_id = ?
        ORDER BY tag ASC
        """,
        (int(user_id), str(scope), int(sid), int(question_id)),
    ).fetchall()
    return [str(r["tag"]) for r in rows or [] if r and r["tag"] is not None]


def get_questions_tags_map(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
    question_ids: Sequence[int],
) -> Dict[int, List[str]]:
    ensure_tag_tables(conn)
    sid = _normalize_scope_id(scope_id)
    ids = []
    for v in question_ids or []:
        try:
            ids.append(int(v))
        except Exception:
            continue
    if not ids:
        return {}

    placeholders = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"""
        SELECT question_id, tag
        FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id = ? AND question_id IN ({placeholders})
        ORDER BY question_id ASC, tag ASC
        """,
        [int(user_id), str(scope), int(sid), *ids],
    ).fetchall()

    out: Dict[int, List[str]] = {}
    for r in rows or []:
        try:
            qid = int(r["question_id"])
        except Exception:
            continue
        t = str(r["tag"] or "").strip()
        if not t:
            continue
        out.setdefault(qid, []).append(t)
    return out


def list_tags_with_counts(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
) -> List[Dict[str, Any]]:
    ensure_tag_tables(conn)
    sid = _normalize_scope_id(scope_id)
    rows = conn.execute(
        """
        SELECT tag, SUM(CASE WHEN question_id > 0 THEN 1 ELSE 0 END) as cnt
        FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id = ?
        GROUP BY tag
        ORDER BY cnt DESC, tag ASC
        """,
        (int(user_id), str(scope), int(sid)),
    ).fetchall()
    return [{"name": str(r["tag"]), "count": int(r["cnt"])} for r in rows or [] if r and r["tag"] is not None]


def get_question_ids_by_tag(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
    tag: str,
) -> List[int]:
    """按 tag 过滤题目 ID（供 quiz/tag 筛选使用）。"""
    ensure_tag_tables(conn)
    sid = _normalize_scope_id(scope_id)
    t = str(tag or "").strip()
    if not t:
        return []
    rows = conn.execute(
        """
        SELECT DISTINCT question_id
        FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id = ? AND tag = ?
          AND question_id > 0
        ORDER BY question_id ASC
        """,
        (int(user_id), str(scope), int(sid), t),
    ).fetchall()
    out = []
    for r in rows or []:
        try:
            out.append(int(r["question_id"]))
        except Exception:
            continue
    return out


def ensure_user_tag_exists(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
    tag: Any,
) -> str:
    """确保某个 tag 在当前 scope 下“已存在”，允许 0 绑定（通过写入 question_id=0 的占位行）。"""
    ensure_tag_tables(conn)
    sid = _normalize_scope_id(scope_id)
    cleaned = _clean_tag_list([tag])
    if not cleaned:
        return ""
    t = cleaned[0]
    if t.lower() == "all":
        return ""
    conn.execute(
        """
        INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(user_id), str(scope), int(sid), int(TAG_DEF_QUESTION_ID), t),
    )
    return t


def delete_user_tag(
    conn,
    *,
    user_id: int,
    scope: str,
    scope_id: Optional[int],
    tag: Any,
) -> str:
    """删除某个 tag（包含占位行与所有题目绑定）。"""
    ensure_tag_tables(conn)
    sid = _normalize_scope_id(scope_id)
    cleaned = _clean_tag_list([tag])
    if not cleaned:
        return ""
    t = cleaned[0]
    conn.execute(
        """
        DELETE FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id = ? AND tag = ?
        """,
        (int(user_id), str(scope), int(sid), t),
    )
    return t
