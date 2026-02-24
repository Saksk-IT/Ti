# -*- coding: utf-8 -*-
"""
代码提交数据模型 — ORM 版本
"""
import logging
from typing import Any, Dict, List, Optional

from app.core.extensions import db
from app.models.coding import (
    CodeSubmission as CodeSubmissionModel,
    CodingQuestion as CodingQuestionModel,
)

logger = logging.getLogger(__name__)


def _submission_to_dict(s: CodeSubmissionModel, question_title: Optional[str] = None) -> Dict[str, Any]:
    """将 ORM 对象转为 dict，保持向后兼容。"""
    result: Dict[str, Any] = {
        "id": s.id,
        "user_id": s.user_id,
        "question_id": s.question_id,
        "code": s.code,
        "language": s.language,
        "status": s.status,
        "passed_cases": s.passed_cases,
        "total_cases": s.total_cases,
        "execution_time": s.execution_time,
        "error_message": s.error_message,
        "score": s.score,
        "submitted_at": s.submitted_at,
    }
    if question_title is not None:
        result["question_title"] = question_title
    return result


class CodeSubmission:
    """代码提交模型（静态方法包装，返回 dict 以保持向后兼容）"""

    @staticmethod
    def create(
        user_id: int,
        question_id: int,
        code: str,
        language: str,
        status: str,
        passed_cases: int,
        total_cases: int,
        execution_time: Optional[float] = None,
        error_message: Optional[str] = None,
        score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        创建提交记录

        Args:
            user_id: 用户ID
            question_id: 题目ID
            code: 代码
            language: 编程语言
            status: 提交状态
            passed_cases: 通过的测试用例数
            total_cases: 总测试用例数
            execution_time: 执行时间（秒）
            error_message: 错误信息
            score: 得分（可选，如果不提供则自动计算）

        Returns:
            提交记录字典
        """
        if score is None:
            score = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0

        submission = CodeSubmissionModel(
            user_id=user_id,
            question_id=question_id,
            code=code,
            language=language,
            status=status,
            passed_cases=passed_cases,
            total_cases=total_cases,
            execution_time=execution_time,
            error_message=error_message,
            score=score,
        )
        db.session.add(submission)
        db.session.commit()

        return CodeSubmission.get_by_id(submission.id)

    @staticmethod
    def get_by_id(submission_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取提交记录

        Args:
            submission_id: 提交ID

        Returns:
            提交记录字典，如果不存在返回None
        """
        s = CodeSubmissionModel.query.get(submission_id)
        if s is None:
            return None

        question_title: Optional[str] = None
        q = CodingQuestionModel.query.get(s.question_id)
        if q is not None:
            question_title = q.title

        return _submission_to_dict(s, question_title=question_title)

    @staticmethod
    def get_by_user_and_question(
        user_id: int,
        question_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取用户对某题目的提交记录

        Args:
            user_id: 用户ID
            question_id: 题目ID
            limit: 返回数量限制

        Returns:
            提交记录列表
        """
        rows = (
            CodeSubmissionModel.query
            .filter_by(user_id=user_id, question_id=question_id)
            .order_by(CodeSubmissionModel.submitted_at.desc())
            .limit(limit)
            .all()
        )
        return [_submission_to_dict(r) for r in rows]
