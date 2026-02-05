# -*- coding: utf-8 -*-
from __future__ import annotations

from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.core.models.exam import Exam
from app.core.utils.database import get_db
from app.core.utils.subject_permissions import can_user_access_subject
from app.modules.exam.schemas.create import CreateExamSchema


class ExamCreateService:
    @staticmethod
    def create(*, user_id: int, payload: CreateExamSchema) -> int:
        uid = int(user_id)
        source = payload.source
        subject = payload.subject
        duration = int(payload.duration)
        types_cfg = payload.types or {}
        scores_cfg = payload.scores or {}
        bank_id_int = int(payload.bank_id) if payload.bank_id is not None else None

        if source == 'user_bank':
            if not bank_id_int or bank_id_int <= 0:
                raise BadRequestError(message='请选择个人题库')

            from app.modules.user_bank.routes.api import check_bank_access

            has_access, _permission, _access_type = check_bank_access(uid, bank_id_int)
            if not has_access:
                raise ForbiddenError(message='题库不存在或无权限')

            conn = get_db()
            bank = conn.execute(
                "SELECT id, name FROM user_question_banks WHERE id=? AND status=1",
                (bank_id_int,),
            ).fetchone()
            if not bank:
                raise NotFoundError(message='题库不存在或无权限')

            # 兼容 exams.subject 字段：用于列表展示（公共/个人统一一个“范围”列）
            subject = bank['name'] or f'题库#{bank_id_int}'

        # 如果指定了科目，检查用户是否有权限访问该科目
        if source != 'user_bank' and subject != 'all':
            conn = get_db()
            subject_row = conn.execute(
                'SELECT id FROM subjects WHERE name = ?',
                (subject,),
            ).fetchone()

            if subject_row:
                subject_id = subject_row['id']
                if not can_user_access_subject(uid, subject_id):
                    raise ForbiddenError(message='您没有权限访问该科目')

        try:
            exam_id = Exam.create(
                uid,
                subject,
                duration,
                types_cfg,
                scores_cfg,
                source=source,
                bank_id=bank_id_int,
            )
        except ValueError:
            raise BadRequestError(message='创建考试失败：参数不合法')

        return int(exam_id or 0)

