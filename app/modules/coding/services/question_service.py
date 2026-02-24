# -*- coding: utf-8 -*-
"""
题目服务
负责题目的CRUD、查询、筛选和统计
"""
from typing import Dict, Any, Optional
import json
import logging

from app.core.extensions import db
from app.models.coding import CodingQuestion, CodingSubject, CodeSubmission
from app.models.quiz import Favorite
from app.modules.coding.schemas.question_schemas import (
    QuestionCreateSchema,
    QuestionUpdateSchema,
)

logger = logging.getLogger(__name__)


class QuestionService:
    """题目服务"""

    @staticmethod
    def get_questions(
        subject_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取题目列表（带筛选和分页）"""

        query = (
            db.session.query(CodingQuestion, CodingSubject.name.label("subject_name"))
            .outerjoin(CodingSubject, CodingQuestion.coding_subject_id == CodingSubject.id)
        )

        if subject_id:
            query = query.filter(CodingQuestion.coding_subject_id == subject_id)
        if difficulty:
            query = query.filter(CodingQuestion.difficulty == difficulty)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                db.or_(
                    CodingQuestion.title.ilike(pattern),
                    CodingQuestion.description.ilike(pattern),
                )
            )

        total = query.count()

        query = query.order_by(CodingQuestion.id.desc())
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        questions = []
        for cq, subject_name in rows:
            question = _question_to_dict(cq, subject_name)

            try:
                stats = QuestionService.calculate_statistics(cq.id)
                question["acceptance_rate"] = stats.get("acceptance_rate", 0)
                question["total_submissions"] = stats.get("total_submissions", 0)
            except Exception:
                logger.warning("计算题目 %s 统计信息失败", cq.id, exc_info=True)
                question["acceptance_rate"] = 0
                question["total_submissions"] = 0

            if user_id:
                question["is_favorite"] = (
                    Favorite.query.filter_by(user_id=user_id, question_id=cq.id).first()
                    is not None
                )
                accepted = CodeSubmission.query.filter_by(
                    user_id=user_id, question_id=cq.id, status="accepted"
                ).first()
                if accepted:
                    question["status"] = "solved"
                else:
                    submitted = CodeSubmission.query.filter_by(
                        user_id=user_id, question_id=cq.id
                    ).first()
                    question["status"] = "solving" if submitted else "unsolved"
            else:
                question["is_favorite"] = False
                question["status"] = "unsolved"

            questions.append(question)

        if status and status != "all" and user_id:
            questions = [q for q in questions if q.get("status") == status]

        return {
            "questions": questions,
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    @staticmethod
    def get_question(
        question_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取题目详情"""

        cq = CodingQuestion.query.get(question_id)
        if not cq:
            return None

        question = _question_to_dict(cq)

        if cq.test_cases_json:
            try:
                tc = json.loads(cq.test_cases_json)
                if isinstance(tc, dict):
                    question["constraints"] = tc.get("constraints", [])
            except (json.JSONDecodeError, TypeError):
                pass

        if user_id:
            question["is_favorite"] = (
                Favorite.query.filter_by(user_id=user_id, question_id=question_id).first()
                is not None
            )
        else:
            question["is_favorite"] = False

        return question

    @staticmethod
    def create_question(data: QuestionCreateSchema) -> Dict[str, Any]:
        """创建题目"""

        test_cases_data = {"test_cases": data.examples or [], "hidden_cases": []}
        if data.test_cases_json:
            try:
                test_cases_data = json.loads(data.test_cases_json)
            except (json.JSONDecodeError, TypeError):
                pass

        cq = CodingQuestion(
            coding_subject_id=data.subject_id,
            title=data.title,
            q_type=data.q_type,
            difficulty=data.difficulty,
            description=data.description,
            code_template=data.code_template or "",
            programming_language=data.programming_language,
            time_limit=data.time_limit,
            memory_limit=data.memory_limit,
            test_cases_json=json.dumps(test_cases_data, ensure_ascii=False),
        )
        db.session.add(cq)
        db.session.commit()

        return QuestionService.get_question(cq.id)

    @staticmethod
    def update_question(
        question_id: int,
        data: QuestionUpdateSchema,
    ) -> Dict[str, Any]:
        """更新题目"""

        cq = CodingQuestion.query.get(question_id)
        if not cq:
            raise ValueError(f"题目 {question_id} 不存在")

        field_map = {
            "subject_id": "coding_subject_id",
            "title": "title",
            "description": "description",
            "q_type": "q_type",
            "difficulty": "difficulty",
            "code_template": "code_template",
            "programming_language": "programming_language",
            "time_limit": "time_limit",
            "memory_limit": "memory_limit",
            "test_cases_json": "test_cases_json",
        }

        changed = False
        for schema_field, model_attr in field_map.items():
            value = getattr(data, schema_field, None)
            if value is not None:
                setattr(cq, model_attr, value)
                changed = True

        if changed:
            db.session.commit()

        return QuestionService.get_question(question_id)

    @staticmethod
    def delete_question(question_id: int) -> bool:
        """删除题目"""
        deleted = CodingQuestion.query.filter_by(id=question_id).delete()
        db.session.commit()
        return deleted > 0

    @staticmethod
    def calculate_statistics(question_id: int) -> Dict[str, Any]:
        """计算题目统计信息（通过率、提交次数）"""

        total_submissions: int = (
            CodeSubmission.query.filter_by(question_id=question_id).count()
        )
        accepted_submissions: int = (
            CodeSubmission.query.filter_by(
                question_id=question_id, status="accepted"
            ).count()
        )
        acceptance_rate = (
            accepted_submissions / total_submissions if total_submissions > 0 else 0.0
        )

        return {
            "total_submissions": total_submissions,
            "accepted_submissions": accepted_submissions,
            "acceptance_rate": round(acceptance_rate, 2),
        }


def _question_to_dict(
    cq: CodingQuestion,
    subject_name: Optional[str] = None,
) -> Dict[str, Any]:
    """将 ORM 实例转为字典，解析 JSON 字段。"""

    question: Dict[str, Any] = {
        "id": cq.id,
        "coding_subject_id": cq.coding_subject_id,
        "subject_name": subject_name or (cq.subject.name if cq.subject else None),
        "title": cq.title,
        "q_type": cq.q_type,
        "description": cq.description,
        "difficulty": cq.difficulty,
        "code_template": cq.code_template,
        "programming_language": cq.programming_language,
        "time_limit": cq.time_limit,
        "memory_limit": cq.memory_limit,
        "test_cases_json": cq.test_cases_json,
        "hints": cq.hints,
        "is_enabled": cq.is_enabled,
        "created_at": cq.created_at.isoformat() if cq.created_at else None,
    }

    if cq.test_cases_json:
        try:
            tc = json.loads(cq.test_cases_json)
            if isinstance(tc, dict):
                question["examples"] = tc.get("test_cases", [])
            elif isinstance(tc, list):
                question["examples"] = tc
            else:
                question["examples"] = []
        except (json.JSONDecodeError, TypeError):
            question["examples"] = []
    else:
        question["examples"] = []

    return question
