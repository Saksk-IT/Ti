# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class CreateExamSchema(BaseModel):
    """创建考试（API 入参）"""

    source: str = Field(default='public', description='public | user_bank')
    subject: str = Field(default='all')
    duration: int = Field(default=60, ge=1, le=24 * 60)
    types: Dict[str, int] = Field(default_factory=dict)
    scores: Dict[str, float] = Field(default_factory=dict)
    bank_id: Optional[int] = Field(default=None, description='source=user_bank 时必填')
    grading_mode: str = Field(default='auto_full', description='auto_full | ai | manual')

    @field_validator('grading_mode', mode='before')
    @classmethod
    def _normalize_grading_mode(cls, v: Any) -> str:
        s = str(v or 'auto_full').strip().lower()
        return s if s in ('auto_full', 'ai', 'manual') else 'auto_full'

    @field_validator('source', mode='before')
    @classmethod
    def _normalize_source(cls, v: Any) -> str:
        s = str(v or 'public').strip().lower()
        return s if s in ('public', 'user_bank') else 'public'

    @field_validator('subject', mode='before')
    @classmethod
    def _normalize_subject(cls, v: Any) -> str:
        s = str(v or 'all').strip()
        return s if s else 'all'

    @field_validator('types', mode='before')
    @classmethod
    def _normalize_types(cls, v: Any) -> Dict[str, int]:
        if v is None:
            return {}
        if isinstance(v, dict):
            out: Dict[str, int] = {}
            for k, raw in v.items():
                key = str(k or '').strip()
                if not key:
                    continue
                try:
                    out[key] = int(raw)
                except Exception:
                    out[key] = 0
            return out
        raise TypeError('types 必须为 object')

    @field_validator('scores', mode='before')
    @classmethod
    def _normalize_scores(cls, v: Any) -> Dict[str, float]:
        if v is None:
            return {}
        if isinstance(v, dict):
            out: Dict[str, float] = {}
            for k, raw in v.items():
                key = str(k or '').strip()
                if not key:
                    continue
                try:
                    out[key] = float(raw)
                except Exception:
                    out[key] = 0.0
            return out
        raise TypeError('scores 必须为 object')

