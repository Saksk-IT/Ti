# -*- coding: utf-8 -*-
"""刷题核心路由 — 收藏切换 + 答题结果记录

原 core.py 已按功能域拆分为：
  - core_reinforce.py  — 强化训练（/reinforce）
  - core_counts.py     — 题目/用户计数（/questions/count, /questions/user_counts）
  - core_history.py    — 学习统计（/history）

本文件保留收藏与答题记录路由，并 re-export 所有被外部引用的符号以确保向后兼容。
"""

from flask import request, jsonify, current_app

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.cache_utils import bump_user_quiz_version
from app.models.quiz import Favorite, Mistake, UserAnswer
from app.models.subject import Question
from app.core.utils.subject_permissions import can_user_access_subject
from app.core.services.quiz_data_service import QuizDataService

from ..api_bp import quiz_api_bp

# ---------------------------------------------------------------------------
# 导入拆分模块以完成路由注册（副作用导入）
# ---------------------------------------------------------------------------
from . import core_reinforce as _core_reinforce  # noqa: F401
from . import core_counts as _core_counts  # noqa: F401
from . import core_history as _core_history  # noqa: F401

# ---------------------------------------------------------------------------
# Re-export：外部通过 from ...core import xxx 引用的符号必须仍可导入
# ---------------------------------------------------------------------------
from .core_counts import api_questions_count, api_user_counts  # noqa: F401
from .core_reinforce import api_reinforce  # noqa: F401
from .core_history import api_history_stats  # noqa: F401


# ---------------------------------------------------------------------------
# 收藏切换
# ---------------------------------------------------------------------------

@quiz_api_bp.route('/favorite', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.limit("30/minute")
def toggle_favorite():
    """切换收藏状态"""
    data = request.get_json(silent=True) or {}
    q_id = data.get('question_id')
    uid = current_user_id()

    try:
        q_id = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400

    # 权限校验：题目存在性 + 科目访问权限
    question = Question.query.get(q_id)
    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404
    if question.subject_id and not can_user_access_subject(int(uid), int(question.subject_id)):
        return jsonify({'status': 'error', 'message': '无权访问该题目'}), 403

    try:
        is_favorite = QuizDataService.toggle_favorite(
            user_id=uid, question_id=q_id, source='public',
        )
    except Exception as e:
        current_app.logger.warning(f'收藏失败 user_id={uid} question_id={q_id}: {e}')
        db.session.rollback()
        return jsonify({'status': 'error', 'message': '收藏失败：题目不存在或不可收藏'}), 400

    db.session.commit()
    try:
        bump_user_quiz_version(int(uid))
    except Exception:
        pass
    return jsonify({"status": "success", "data": {"is_favorite": is_favorite}})


# ---------------------------------------------------------------------------
# 答题结果记录
# ---------------------------------------------------------------------------

@quiz_api_bp.route('/record_result', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.limit("60/minute")
def record_result():
    """记录做题结果（添加刷题限制检查）"""
    from app.core.utils.subject_permissions import (
        check_quiz_limit,
        increment_user_quiz_count,
        get_user_quiz_count,
        get_quiz_limit_count
    )

    data = request.json or {}
    q_id = data.get('question_id')
    is_correct = data.get('is_correct')
    clear_mistake_on_correct = data.get('clear_mistake_on_correct', True)
    uid = current_user_id()

    if not q_id or is_correct is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400

    # 权限校验：题目存在性 + 科目访问权限
    try:
        q_id_int = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400
    question = Question.query.get(q_id_int)
    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404
    if question.subject_id and not can_user_access_subject(int(uid), int(question.subject_id)):
        return jsonify({'status': 'error', 'message': '无权访问该题目'}), 403

    # 兼容 clear_mistake_on_correct 可能为 string/int/bool；默认 True（保持旧行为）
    clear_mistake_on_correct = _parse_bool(clear_mistake_on_correct, default=True)

    # 检查刷题限制
    is_limited, limit_message = check_quiz_limit(uid)
    if is_limited:
        return jsonify({
            'status': 'error',
            'message': limit_message,
            'code': 'QUIZ_LIMIT_REACHED',
            'data': {
                'current_count': get_user_quiz_count(uid),
                'limit_count': get_quiz_limit_count(),
            }
        }), 403

    try:
        # 更新错题本（只记录错误题目）
        if not is_correct:
            QuizDataService.record_mistake(user_id=uid, question_id=q_id, source='public')
            action = "added_mistake"
        else:
            if clear_mistake_on_correct:
                # 答对了，从错题本中移除（默认行为）
                QuizDataService.remove_mistake(user_id=uid, question_id=q_id, source='public')
                action = "removed_mistake"
            else:
                # 答对但不清除：保留在错题本
                action = "kept_mistake"

        # 记录答题历史（每次答题都记录，用于统计）
        QuizDataService.record_answer(user_id=uid, question_id=q_id, is_correct=bool(is_correct), source='public')

        # 增加刷题数（如果功能开启）
        increment_user_quiz_count(uid)

        db.session.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        return jsonify({"status": "success", "action": action})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'记录答题结果失败 user_id={uid} question_id={q_id}: {e}', exc_info=True)
        return jsonify({"status": "error", "msg": str(e)}), 500


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _parse_bool(value, *, default: bool = True) -> bool:
    """将 string/int/bool 统一解析为 bool"""
    try:
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ('0', 'false', 'no', 'off'):
                return False
            if v in ('1', 'true', 'yes', 'on'):
                return True
            return default
        if isinstance(value, (int, float)):
            return bool(value)
        return bool(value)
    except Exception:
        return default
