# -*- coding: utf-8 -*-
"""刷题主观题判分路由

提供 POST /api/quiz/grade_subjective 接口：
  - grading_mode=auto_full → 有作答即满分
  - grading_mode=ai        → 调用 AI 判分
  - grading_mode=manual    → 返回 pending，前端展示自评按钮
"""

import logging
from typing import Optional

from flask import request, jsonify, current_app

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.cache_utils import bump_user_quiz_version
from app.core.services.quiz_data_service import QuizDataService
from app.models.subject import Question
from app.core.utils.subject_permissions import can_user_access_subject

from ..api_bp import quiz_api_bp

logger = logging.getLogger(__name__)

_SUBJECTIVE_TYPES = frozenset(['简答题', '计算题', '论述题', '问答题'])
_VALID_GRADING_MODES = frozenset(['auto_full', 'ai', 'manual'])


def _grade_auto_full(user_answer: str) -> dict:
    """有作答即满分"""
    is_correct = bool(user_answer and user_answer.strip())
    return {'is_correct': is_correct, 'grading': 'auto_full'}


def _grade_ai(
    question_content: str,
    standard_answer: str,
    user_answer: str,
) -> dict:
    """AI 判分，失败时降级为 auto_full"""
    try:
        from app.modules.exam.services.ai_grading_service import grade_essay_answer
        result = grade_essay_answer(question_content, standard_answer, user_answer)
        if result is not None:
            return {'is_correct': bool(result), 'grading': 'ai'}
        # AI 返回 None → 降级
        logger.info("AI 判分返回 None，降级为 auto_full")
    except Exception as e:
        logger.warning("AI 判分异常，降级为 auto_full: %s", e)
    return _grade_auto_full(user_answer)


def _grade_manual() -> dict:
    """人工/自评模式 — 返回 pending，前端展示自评按钮"""
    return {'is_correct': None, 'grading': 'manual', 'pending': True}


@quiz_api_bp.route('/grade_subjective', methods=['POST'])
@auth_required
@limiter.limit("30/minute")
def api_grade_subjective():
    """主观题判分接口

    请求体:
        question_id: int
        user_answer: str
        grading_mode: str  (auto_full | ai | manual)
    """
    data = request.get_json(silent=True) or {}
    q_id = data.get('question_id')
    user_answer = str(data.get('user_answer', '') or '').strip()
    grading_mode = str(data.get('grading_mode', 'auto_full') or 'auto_full').strip().lower()
    uid = current_user_id()

    # 参数校验
    try:
        q_id_int = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400

    if grading_mode not in _VALID_GRADING_MODES:
        grading_mode = 'auto_full'

    # 题目存在性 + 权限
    question = Question.query.get(q_id_int)
    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404
    if question.subject_id and not can_user_access_subject(int(uid), int(question.subject_id)):
        return jsonify({'status': 'error', 'message': '无权访问该题目'}), 403

    # 题型校验（仅主观题走此接口）
    q_type = str(getattr(question, 'q_type', '') or '')
    if q_type not in _SUBJECTIVE_TYPES:
        return jsonify({'status': 'error', 'message': '该题型不支持此判分接口'}), 400

    # 获取题目内容和标准答案
    question_content = str(getattr(question, 'content', '') or '')
    standard_answer = str(getattr(question, 'answer', '') or '')

    # 按模式判分
    if grading_mode == 'manual':
        result = _grade_manual()
    elif grading_mode == 'ai':
        result = _grade_ai(question_content, standard_answer, user_answer)
    else:
        result = _grade_auto_full(user_answer)

    # 非 pending 时记录答题结果
    is_correct = result.get('is_correct')
    if is_correct is not None:
        try:
            if not is_correct:
                QuizDataService.record_mistake(
                    user_id=uid, question_id=q_id_int, source='public',
                )
            else:
                QuizDataService.remove_mistake(
                    user_id=uid, question_id=q_id_int, source='public',
                )
            QuizDataService.record_answer(
                user_id=uid, question_id=q_id_int,
                is_correct=bool(is_correct), source='public',
            )
            db.session.commit()
            try:
                bump_user_quiz_version(int(uid))
            except Exception:
                pass
        except Exception as e:
            db.session.rollback()
            logger.error("记录主观题结果失败: %s", e, exc_info=True)

    return jsonify({
        'status': 'success',
        'data': {
            'is_correct': is_correct,
            'grading': result.get('grading', grading_mode),
            'pending': result.get('pending', False),
            'standard_answer': standard_answer if grading_mode == 'manual' else None,
        },
    })
