# -*- coding: utf-8 -*-
from __future__ import annotations

from app.core.errors import BadRequestError
from app.modules.exam.services.exam_legacy_service import ExamLegacyService as Exam
from app.modules.exam.schemas.submit import SubmitExamSchema


class ExamSubmitService:
    @staticmethod
    def submit(*, user_id: int, payload: SubmitExamSchema) -> dict:
        uid = int(user_id)
        answers = [a.model_dump() for a in (payload.answers or [])]
        result = Exam.submit(int(payload.exam_id), uid, answers)
        if not result:
            raise BadRequestError(message='考试不存在/无权限/已提交')
        if isinstance(result, dict) and result.get('error') == 'exam_expired':
            raise BadRequestError(message=result.get('message', '考试已超时'))
        return {'exam_id': int(payload.exam_id), **result}

