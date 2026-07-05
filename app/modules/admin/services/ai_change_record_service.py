# -*- coding: utf-8 -*-
"""AI 改动记录服务。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import or_

from app.core.extensions import db
from app.models.ai_change_record import AIChangeRecord


SUMMARY_LIMIT = 120
SOURCE_LIMIT = 32
EXTERNAL_ID_LIMIT = 128

_CATEGORY_ALIASES = {
    "bug": "bug",
    "fix": "bug",
    "bugfix": "bug",
    "defect": "bug",
    "修复": "bug",
    "缺陷": "bug",
    "问题": "bug",
    "功能": "feature",
    "feature": "feature",
    "feat": "feature",
    "enhancement": "feature",
    "新增": "feature",
    "优化": "feature",
}

_BUG_HINTS = ("bug", "fix", "修复", "异常", "错误", "失败", "报错", "缺陷", "回归", "崩溃")


def _compact_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip()


def _compact_list(values: Iterable[Any], *, item_limit: int = 160, max_items: int = 20) -> list[str]:
    return [
        item
        for item in (_compact_text(value, item_limit) for value in list(values or [])[:max_items])
        if item
    ]


def _normalize_category(category: Optional[str], haystacks: Iterable[Any]) -> str:
    raw = _compact_text(category, 32).lower()
    if raw:
        normalized = _CATEGORY_ALIASES.get(raw)
        if not normalized:
            raise ValueError("分类必须是 bug 或 feature")
        return normalized

    text = " ".join(_compact_text(item, 200).lower() for item in haystacks)
    if any(hint in text for hint in _BUG_HINTS):
        return "bug"
    return "feature"


def _build_summary(payload: Dict[str, Any]) -> str:
    for key in ("summary", "title"):
        value = _compact_text(payload.get(key), SUMMARY_LIMIT)
        if value:
            return value

    changes = _compact_list(payload.get("changes", []), item_limit=SUMMARY_LIMIT, max_items=1)
    if changes:
        return changes[0]

    return "记录一次 AI 改动"


def _build_detail_json(payload: Dict[str, Any]) -> str:
    detail = payload.get("detail")
    metadata = payload.get("metadata")
    detail_payload = {
        "title": _compact_text(payload.get("title"), 200),
        "changes": _compact_list(payload.get("changes", [])),
        "files": _compact_list(payload.get("files", []), item_limit=240, max_items=50),
        "detail": detail if isinstance(detail, dict) else {},
        "metadata": metadata if isinstance(metadata, dict) else {},
    }
    return json.dumps(detail_payload, ensure_ascii=False, sort_keys=True)


def _record_to_dict(record: AIChangeRecord) -> Dict[str, Any]:
    return {
        "id": record.id,
        "category": record.category,
        "summary": record.summary,
        "source": record.source,
        "external_id": record.external_id,
        "created_by": record.created_by,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


class AIChangeRecordService:
    """AI 改动记录写入与查询。"""

    @staticmethod
    def create_record(payload: Dict[str, Any], created_by: Optional[int] = None) -> Dict[str, Any]:
        summary = _build_summary(payload)
        category = _normalize_category(
            payload.get("category"),
            (
                payload.get("title"),
                payload.get("summary"),
                *list(payload.get("changes") or []),
            ),
        )
        source = _compact_text(payload.get("source") or "codex", SOURCE_LIMIT) or "codex"
        external_id = _compact_text(payload.get("external_id"), EXTERNAL_ID_LIMIT) or None
        if external_id:
            existing = AIChangeRecord.query.filter_by(external_id=external_id).first()
            if existing:
                return _record_to_dict(existing)

        record = AIChangeRecord(
            category=category,
            summary=summary,
            detail_json=_build_detail_json(payload),
            source=source,
            external_id=external_id,
            created_by=created_by,
        )
        db.session.add(record)
        db.session.commit()
        return _record_to_dict(record)

    @staticmethod
    def list_records(
        *,
        category: str = "",
        q: str = "",
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        query = AIChangeRecord.query
        normalized_category = _normalize_category(category, ()) if category else ""
        if normalized_category:
            query = query.filter(AIChangeRecord.category == normalized_category)

        keyword = _compact_text(q, 120)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    AIChangeRecord.summary.ilike(like),
                    AIChangeRecord.source.ilike(like),
                    AIChangeRecord.external_id.ilike(like),
                )
            )

        total = query.count()
        items = (
            query.order_by(AIChangeRecord.created_at.desc(), AIChangeRecord.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return {
            "items": [_record_to_dict(item) for item in items],
            "total": total,
            "page": page,
            "size": size,
        }
