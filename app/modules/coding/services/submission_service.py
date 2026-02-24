# -*- coding: utf-8 -*-
"""
提交服务
负责提交记录的CRUD和统计
"""
from typing import Dict, Any, Optional
import logging

from sqlalchemy import func

from app.core.extensions import db
from app.core.utils.time_utils import now_bj
from app.models.coding import (
    CodeSubmission,
    CodingQuestion,
    CodingStatistics,
    UserCodingStats,
)

logger = logging.getLogger(__name__)


class SubmissionService:
    """提交服务"""

    @staticmethod
    def create_submission(
        user_id: int,
        question_id: int,
        code: str,
        language: str,
        judge_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建提交记录并更新统计信息"""

        passed_cases = judge_result.get("passed_cases", 0)
        total_cases = judge_result.get("total_cases", 1)
        score = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0

        submission = CodeSubmission(
            user_id=user_id,
            question_id=question_id,
            code=code,
            language=language,
            status=judge_result["status"],
            passed_cases=passed_cases,
            total_cases=total_cases,
            execution_time=judge_result.get("execution_time"),
            error_message=judge_result.get("error_message"),
            score=score,
        )
        db.session.add(submission)
        db.session.flush()

        SubmissionService._update_question_statistics(
            user_id, question_id, judge_result, score
        )
        SubmissionService._update_user_statistics(user_id)

        db.session.commit()

        return {
            "id": submission.id,
            "user_id": submission.user_id,
            "question_id": submission.question_id,
            "code": submission.code,
            "language": submission.language,
            "status": submission.status,
            "passed_cases": submission.passed_cases,
            "total_cases": submission.total_cases,
            "execution_time": submission.execution_time,
            "error_message": submission.error_message,
            "score": submission.score,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        }

    @staticmethod
    def _update_question_statistics(
        user_id: int,
        question_id: int,
        judge_result: Dict[str, Any],
        score: float,
    ) -> None:
        """更新用户对特定题目的统计信息"""
        status = judge_result["status"]
        is_accepted = (status == "accepted")
        execution_time = judge_result.get("execution_time")
        submitted_at = now_bj()

        existing = CodingStatistics.query.filter_by(
            user_id=user_id, question_id=question_id
        ).first()

        if existing:
            existing.total_submissions += 1
            existing.last_submitted_at = submitted_at
            existing.updated_at = submitted_at
            if is_accepted:
                existing.accepted_submissions += 1
                if not existing.first_accepted_at:
                    existing.first_accepted_at = submitted_at
                if execution_time and (not existing.best_time or execution_time < existing.best_time):
                    existing.best_time = execution_time
                if score > (existing.best_score or 0):
                    existing.best_score = score
        else:
            stat = CodingStatistics(
                user_id=user_id,
                question_id=question_id,
                total_submissions=1,
                accepted_submissions=1 if is_accepted else 0,
                best_time=execution_time if is_accepted else None,
                best_score=score if is_accepted else 0.0,
                first_accepted_at=submitted_at if is_accepted else None,
                last_submitted_at=submitted_at,
                updated_at=submitted_at,
            )
            db.session.add(stat)

    @staticmethod
    def _update_user_statistics(user_id: int) -> None:
        """更新用户总统计信息"""

        total_submissions = CodeSubmission.query.filter_by(user_id=user_id).count()

        accepted_submissions = CodeSubmission.query.filter_by(
            user_id=user_id, status="accepted"
        ).count()

        solved_questions = (
            db.session.query(func.count(func.distinct(CodeSubmission.question_id)))
            .filter(CodeSubmission.user_id == user_id, CodeSubmission.status == "accepted")
            .scalar() or 0
        )

        total_score = (
            db.session.query(func.sum(CodeSubmission.score))
            .filter(CodeSubmission.user_id == user_id)
            .scalar() or 0.0
        )

        average_score = (total_score / total_submissions) if total_submissions > 0 else 0.0
        acceptance_rate = (accepted_submissions / total_submissions) if total_submissions > 0 else 0.0

        existing = UserCodingStats.query.filter_by(user_id=user_id).first()
        if existing:
            existing.total_submissions = total_submissions
            existing.accepted_submissions = accepted_submissions
            existing.solved_questions = solved_questions
            existing.total_score = total_score
            existing.average_score = average_score
            existing.acceptance_rate = acceptance_rate
            existing.updated_at = now_bj()
        else:
            stats = UserCodingStats(
                user_id=user_id,
                total_submissions=total_submissions,
                accepted_submissions=accepted_submissions,
                solved_questions=solved_questions,
                total_score=total_score,
                average_score=average_score,
                acceptance_rate=acceptance_rate,
            )
            db.session.add(stats)

    @staticmethod
    def get_submissions(
        user_id: Optional[int] = None,
        question_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """获取提交历史（分页、筛选）"""

        query = (
            db.session.query(CodeSubmission, CodingQuestion.title.label("question_title"))
            .outerjoin(CodingQuestion, CodeSubmission.question_id == CodingQuestion.id)
        )

        if user_id:
            query = query.filter(CodeSubmission.user_id == user_id)
        if question_id:
            query = query.filter(CodeSubmission.question_id == question_id)
        if status:
            query = query.filter(CodeSubmission.status == status)

        total = query.count()

        rows = (
            query.order_by(CodeSubmission.submitted_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        submissions = []
        for sub, question_title in rows:
            submissions.append({
                "id": sub.id,
                "user_id": sub.user_id,
                "question_id": sub.question_id,
                "question_title": question_title,
                "code": sub.code,
                "language": sub.language,
                "status": sub.status,
                "passed_cases": sub.passed_cases,
                "total_cases": sub.total_cases,
                "execution_time": sub.execution_time,
                "error_message": sub.error_message,
                "score": sub.score,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            })

        return {
            "submissions": submissions,
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    @staticmethod
    def get_submission(
        submission_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取提交详情"""

        sub = CodeSubmission.query.get(submission_id)
        if not sub:
            return None

        if user_id and sub.user_id != user_id:
            return None

        return {
            "id": sub.id,
            "user_id": sub.user_id,
            "question_id": sub.question_id,
            "code": sub.code,
            "language": sub.language,
            "status": sub.status,
            "passed_cases": sub.passed_cases,
            "total_cases": sub.total_cases,
            "execution_time": sub.execution_time,
            "error_message": sub.error_message,
            "score": sub.score,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }

    @staticmethod
    def get_best_submission(
        user_id: int,
        question_id: int,
    ) -> Optional[Dict[str, Any]]:
        """获取最佳提交记录（首次通过）"""

        sub = (
            CodeSubmission.query
            .filter_by(user_id=user_id, question_id=question_id, status="accepted")
            .order_by(CodeSubmission.submitted_at.asc())
            .first()
        )
        if not sub:
            return None

        return {
            "id": sub.id,
            "user_id": sub.user_id,
            "question_id": sub.question_id,
            "code": sub.code,
            "language": sub.language,
            "status": sub.status,
            "passed_cases": sub.passed_cases,
            "total_cases": sub.total_cases,
            "execution_time": sub.execution_time,
            "error_message": sub.error_message,
            "score": sub.score,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }

    @staticmethod
    def get_user_statistics(user_id: int) -> Dict[str, Any]:
        """获取用户统计信息"""

        total_submissions = CodeSubmission.query.filter_by(user_id=user_id).count()

        accepted_submissions = CodeSubmission.query.filter_by(
            user_id=user_id, status="accepted"
        ).count()

        solved_questions = (
            db.session.query(func.count(func.distinct(CodeSubmission.question_id)))
            .filter(CodeSubmission.user_id == user_id, CodeSubmission.status == "accepted")
            .scalar() or 0
        )

        total_questions = CodingQuestion.query.count()

        acceptance_rate = (
            accepted_submissions / total_submissions if total_submissions > 0 else 0.0
        )

        return {
            "total_submissions": total_submissions,
            "accepted_submissions": accepted_submissions,
            "total_questions": total_questions,
            "solved_questions": solved_questions,
            "acceptance_rate": round(acceptance_rate, 2),
        }
