# -*- coding: utf-8 -*-
"""刷题主观题判分路由

提供 POST /api/quiz/grade_subjective 接口：
  - grading_mode=auto_full → 有作答即满分
  - grading_mode=ai        → 调用 AI 判分
  - grading_mode=manual    → 返回 pending，前端展示自评按钮
"""

import json
import logging
from typing import Optional

from flask import request, jsonify, current_app
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.cache_utils import bump_user_quiz_version
from app.core.services.quiz_data_service import QuizDataService
from app.models.subject import Question
from app.models.user_bank import UserBankQuestion
from app.core.utils.subject_permissions import can_user_access_subject

from ..api_bp import quiz_api_bp

logger = logging.getLogger(__name__)

# DB 存储的是 portable type（英文），前端通过 portable_type_to_q_type 转中文显示
_SUBJECTIVE_TYPES = frozenset(['essay'])
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
            return {
                'is_correct': result.is_correct,
                'grading': 'ai',
                'score': result.score,
                'feedback': result.feedback,
            }
        # AI 返回 None → 降级
        logger.info("AI 判分返回 None，降级为 auto_full")
    except Exception as e:
        logger.warning("AI 判分异常，降级为 auto_full: %s", e)
    return _grade_auto_full(user_answer)


def _grade_manual() -> dict:
    """人工/自评模式 — 返回 pending，前端展示自评按钮"""
    return {'is_correct': None, 'grading': 'manual', 'pending': True}


def _parse_optional_int(value) -> Optional[int]:
    try:
        if value in (None, ''):
            return None
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _wants_user_bank_scope(data: dict) -> bool:
    source = str(data.get('source') or '').strip().lower()
    return source in {'user_bank', 'bank'} or _parse_optional_int(data.get('bank_id')) is not None


def _standard_answer_text(raw_answer) -> str:
    raw = '' if raw_answer is None else str(raw_answer)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return '；'.join(str(item) for item in parsed)
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=False)
        return str(parsed)
    except Exception:
        return raw


def _load_user_bank_question(uid: int, q_id: int, bank_id: Optional[int]):
    from app.modules.user_bank.routes.api_base import check_bank_access

    query = UserBankQuestion.query.filter(UserBankQuestion.id == int(q_id))
    if bank_id is not None:
        has_access, _permission, _access_type = check_bank_access(int(uid), int(bank_id))
        if not has_access:
            return None, jsonify({'status': 'error', 'message': '无权访问该题目'}), 403
        query = query.filter(UserBankQuestion.bank_id == int(bank_id))

    question = query.first()
    if not question:
        return None, jsonify({'status': 'error', 'message': '题目不存在'}), 404

    resolved_bank_id = int(question.bank_id)
    if bank_id is None:
        has_access, _permission, _access_type = check_bank_access(int(uid), resolved_bank_id)
        if not has_access:
            return None, jsonify({'status': 'error', 'message': '无权访问该题目'}), 403

    return question, None, None


def _record_user_bank_subjective_result(
    *,
    uid: int,
    bank_id: int,
    question_id: int,
    user_answer: str,
    is_correct: bool,
) -> None:
    db.session.execute(text('''
        INSERT INTO user_bank_answers (user_id, bank_id, question_id, user_answer, is_correct)
        VALUES (:uid, :bank_id, :qid, :user_answer, :is_correct)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            bank_id = EXCLUDED.bank_id,
            user_answer = EXCLUDED.user_answer,
            is_correct = EXCLUDED.is_correct,
            created_at = CURRENT_TIMESTAMP
    '''), {
        'uid': int(uid),
        'bank_id': int(bank_id),
        'qid': int(question_id),
        'user_answer': user_answer,
        'is_correct': bool(is_correct),
    })

    if is_correct:
        db.session.execute(
            text('DELETE FROM user_bank_mistakes WHERE user_id = :uid AND question_id = :qid'),
            {'uid': int(uid), 'qid': int(question_id)},
        )
    else:
        db.session.execute(text('''
            INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count)
            VALUES (:uid, :bank_id, :qid, 1)
            ON CONFLICT(user_id, question_id) DO UPDATE SET
                bank_id = EXCLUDED.bank_id,
                wrong_count = user_bank_mistakes.wrong_count + 1,
                updated_at = CURRENT_TIMESTAMP
        '''), {
            'uid': int(uid),
            'bank_id': int(bank_id),
            'qid': int(question_id),
        })


def _handle_user_bank_subjective(
    *,
    q_id_int: int,
    bank_id: Optional[int],
    user_answer: str,
    grading_mode: str,
    uid: int,
):
    question, error_response, status_code = _load_user_bank_question(uid, q_id_int, bank_id)
    if error_response is not None:
        return error_response, status_code

    q_type = str(getattr(question, 'type', '') or '')
    if q_type not in _SUBJECTIVE_TYPES:
        return jsonify({'status': 'error', 'message': '该题型不支持此判分接口'}), 400

    question_content = str(getattr(question, 'content', '') or '')
    standard_answer = _standard_answer_text(getattr(question, 'answer', '') or '')

    if grading_mode == 'manual':
        result = _grade_manual()
    elif grading_mode == 'ai':
        result = _grade_ai(question_content, standard_answer, user_answer)
    else:
        result = _grade_auto_full(user_answer)

    is_correct = result.get('is_correct')
    if is_correct is not None:
        try:
            _record_user_bank_subjective_result(
                uid=int(uid),
                bank_id=int(question.bank_id),
                question_id=int(q_id_int),
                user_answer=user_answer,
                is_correct=bool(is_correct),
            )
            db.session.commit()
            try:
                bump_user_quiz_version(int(uid))
            except Exception:
                pass
        except Exception as e:
            db.session.rollback()
            logger.error("记录个人题库主观题结果失败: %s", e, exc_info=True)

    return jsonify({
        'status': 'success',
        'data': {
            'is_correct': is_correct,
            'grading': result.get('grading', grading_mode),
            'pending': result.get('pending', False),
            'score': result.get('score'),
            'feedback': result.get('feedback'),
            'standard_answer': standard_answer if grading_mode == 'manual' else None,
        },
    })


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

    bank_id = _parse_optional_int(data.get('bank_id'))
    if _wants_user_bank_scope(data):
        return _handle_user_bank_subjective(
            q_id_int=q_id_int,
            bank_id=bank_id,
            user_answer=user_answer,
            grading_mode=grading_mode,
            uid=int(uid),
        )

    # 题目存在性 + 权限
    question = Question.query.get(q_id_int)
    if not question:
        fallback = _handle_user_bank_subjective(
            q_id_int=q_id_int,
            bank_id=None,
            user_answer=user_answer,
            grading_mode=grading_mode,
            uid=int(uid),
        )
        fallback_status = fallback[1] if isinstance(fallback, tuple) else getattr(fallback, 'status_code', 200)
        if fallback_status != 404:
            return fallback
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404
    if question.subject_id and not can_user_access_subject(int(uid), int(question.subject_id)):
        return jsonify({'status': 'error', 'message': '无权访问该题目'}), 403

    # 题型校验（仅主观题走此接口）
    q_type = str(getattr(question, 'type', '') or '')
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
            'score': result.get('score'),
            'feedback': result.get('feedback'),
            'standard_answer': standard_answer if grading_mode == 'manual' else None,
        },
    })
