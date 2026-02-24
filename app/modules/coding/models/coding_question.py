# -*- coding: utf-8 -*-
"""
编程题数据模型 — ORM 版本
"""
import json
import logging
from typing import Any, Dict, Optional

from app.models.coding import CodingQuestion as CodingQuestionModel

logger = logging.getLogger(__name__)


class CodingQuestion:
    """编程题模型（静态方法包装，返回 dict 以保持向后兼容）"""

    @staticmethod
    def get_by_id(question_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取题目

        Args:
            question_id: 题目ID

        Returns:
            题目字典，如果不存在返回None
        """
        q = CodingQuestionModel.query.get(question_id)
        if q is None:
            return None

        result: Dict[str, Any] = {
            "id": q.id,
            "coding_subject_id": q.coding_subject_id,
            "title": q.title,
            "q_type": q.q_type,
            "description": q.description,
            "difficulty": q.difficulty,
            "code_template": q.code_template,
            "programming_language": q.programming_language,
            "time_limit": q.time_limit,
            "memory_limit": q.memory_limit,
            "test_cases_json": q.test_cases_json,
            "examples": q.examples,
            "constraints": q.constraints,
            "hints": q.hints,
            "is_enabled": q.is_enabled,
            "created_at": q.created_at,
            "subject_name": q.subject.name if q.subject else None,
        }
        return result

    @staticmethod
    def get_test_cases(question_id: int) -> Dict[str, Any]:
        """
        获取题目的测试用例

        Args:
            question_id: 题目ID

        Returns:
            测试用例字典（包含test_cases和hidden_cases）
        """
        q = CodingQuestionModel.query.get(question_id)
        if q is None or not q.test_cases_json:
            return {"test_cases": [], "hidden_cases": []}

        try:
            return json.loads(q.test_cases_json)
        except (json.JSONDecodeError, TypeError):
            return {"test_cases": [], "hidden_cases": []}
