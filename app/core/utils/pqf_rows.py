# -*- coding: utf-8 -*-
"""PQF（Portable Question Format）行数据转换工具。

用于把数据库中使用 PQF 同名列（type/content/options/answer/analysis/tags/difficulty）
存储的记录，转换为旧页面/旧接口仍在使用的字段：
- q_type（中文题型）
- explanation（解析）
- answer（字符串：选择题字母/填空 ';;' 等）
- options（列表）
并同时附带 portable_* 字段，便于前端逐步过渡到 PQF。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

from app.core.utils.portable_question_format import portable_question_to_internal


def safe_json_load(raw: Any, default: Any):
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


def pqf_row_to_internal(
    row: Mapping[str, Any],
    *,
    scope: str,
    override_tags: Optional[Any] = None,
) -> Dict[str, Any]:
    """把一条 PQF 行转换为旧字段可用的 dict。

    scope:
      - "question_center"
      - "user_bank"
    override_tags:
      - 若提供，则覆盖 PQF 行中的 tags（用于"按用户维度标签"）
    """
    r = dict(row or {})
    portable = {
        "id": r.get("id"),
        "type": r.get("type") or "",
        "content": r.get("content") or "",
        "options": safe_json_load(r.get("options"), []),
        "answer": safe_json_load(r.get("answer"), []),
        "analysis": r.get("analysis") or "",
        "tags": safe_json_load(r.get("tags"), []),
        "difficulty": r.get("difficulty") if r.get("difficulty") is not None else 1,
    }
    if override_tags is not None:
        portable["tags"] = override_tags

    internal, _errors = portable_question_to_internal(portable, scope=scope)

    # portable_*：方便逐步迁移
    r["portable_type"] = portable.get("type") or ""
    r["portable_content"] = portable.get("content") or ""
    r["portable_options"] = portable.get("options") or []
    r["portable_answer"] = portable.get("answer") if portable.get("answer") is not None else []
    r["portable_tags"] = portable.get("tags") or []

    # 旧字段：兼容现有页面/JS
    r["q_type"] = internal.get("q_type") or ""
    r["content"] = internal.get("content") or ""
    r["options"] = internal.get("options") or []
    r["answer"] = internal.get("answer") or ""
    r["explanation"] = internal.get("explanation") or ""
    r["difficulty"] = (
        internal.get("difficulty")
        if internal.get("difficulty") is not None
        else int(portable.get("difficulty") or 1)
    )

    # tags：默认输出列表（旧页面一般忽略，不会破坏）
    r["tags"] = portable.get("tags") or []

    return r

