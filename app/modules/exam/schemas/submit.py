# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any, List

from pydantic import BaseModel, Field, field_validator, model_validator


class SubmitExamAnswerItem(BaseModel):
    question_id: int = Field(..., ge=1)
    user_answer: str = Field(default='')

    @field_validator('user_answer', mode='before')
    @classmethod
    def _coerce_user_answer(cls, v: Any) -> str:
        if v is None:
            return ''
        if isinstance(v, (list, dict)):
            # 兼容多空题：前端若直接传数组/对象，转成 JSON 字符串（后端判分可识别）
            try:
                return json.dumps(v, ensure_ascii=False)
            except Exception:
                return str(v)
        return str(v).strip()


class SubmitExamSchema(BaseModel):
    """提交考试（API 入参）"""

    exam_id: int = Field(..., ge=1)
    answers: List[SubmitExamAnswerItem] = Field(default_factory=list)

    @model_validator(mode='after')
    def _dedupe_answers(self):
        # 同一 question_id 可能重复提交：保留最后一次
        uniq = {}
        for item in self.answers:
            uniq[int(item.question_id)] = item
        self.answers = list(uniq.values())
        return self

