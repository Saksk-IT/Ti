# -*- coding: utf-8 -*-
"""Portable Question Format 与数据库结构化列同步工具。

说明（2026-01 起）：
- 数据库已切换为 PQF 同名列：type/content/options/answer/analysis/tags/difficulty
- 历史调用点可能仍传入旧字段（q_type/explanation/答案字符串等）
- 本模块负责把“旧入参”转换为 PQF 并写回新列，尽量降低改造面
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.core.utils.portable_question_format import internal_question_to_portable


def build_portable_columns(
    *,
    q_id: Optional[int],
    q_type: Any,
    content: Any,
    options: Any,
    answer: Any,
    explanation: Any,
    difficulty: Any,
    tags: Any = None,
) -> Dict[str, Any]:
    portable = internal_question_to_portable(
        q_id=q_id,
        q_type=q_type,
        content=content,
        options=options,
        answer=answer,
        explanation=explanation,
        difficulty=difficulty,
        tags=tags,
    )
    return {
        # PQF 同名列
        "type": portable.get("type") or "",
        "content": portable.get("content") or "",
        "options": json.dumps(portable.get("options") or [], ensure_ascii=False),
        "answer": json.dumps(
            portable.get("answer") if portable.get("answer") is not None else [],
            ensure_ascii=False,
        ),
        "analysis": portable.get("analysis") or "",
        "tags": json.dumps(portable.get("tags") or [], ensure_ascii=False),
        "difficulty": int(portable.get("difficulty") or 1),
    }


def try_sync_questions_portable_columns(
    conn,
    *,
    question_id: int,
    q_type: Any,
    content: Any,
    options: Any,
    answer: Any,
    explanation: Any,
    difficulty: Any,
    tags: Any = None,
) -> None:
    try:
        v = build_portable_columns(
            q_id=int(question_id),
            q_type=q_type,
            content=content,
            options=options,
            answer=answer,
            explanation=explanation,
            difficulty=difficulty,
            tags=tags,
        )
        conn.execute(
            """
            UPDATE questions
            SET type=?,
                content=?,
                options=?,
                answer=?,
                analysis=?,
                tags=?,
                difficulty=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                v["type"],
                v["content"],
                v["options"],
                v["answer"],
                v["analysis"],
                v["tags"],
                v["difficulty"],
                int(question_id),
            ),
        )
    except Exception:
        return


def try_sync_user_bank_questions_portable_columns(
    conn,
    *,
    question_id: int,
    q_type: Any,
    content: Any,
    options: Any,
    answer: Any,
    explanation: Any,
    difficulty: Any,
) -> None:
    try:
        v = build_portable_columns(
            q_id=int(question_id),
            q_type=q_type,
            content=content,
            options=options,
            answer=answer,
            explanation=explanation,
            difficulty=difficulty,
            tags=None,
        )
        conn.execute(
            """
            UPDATE user_bank_questions
            SET type=?,
                content=?,
                options=?,
                answer=?,
                analysis=?,
                tags=?,
                difficulty=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                v["type"],
                v["content"],
                v["options"],
                v["answer"],
                v["analysis"],
                v["tags"],
                v["difficulty"],
                int(question_id),
            ),
        )
    except Exception:
        return
