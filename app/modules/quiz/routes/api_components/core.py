# -*- coding: utf-8 -*-
"""刷题核心路由 — 收藏切换 + 答题结果记录

原 core.py 已按功能域拆分为：
  - core_reinforce.py  — 强化训练（/reinforce）
  - core_counts.py     — 题目/用户计数（/questions/count, /questions/user_counts）
  - core_history.py    — 学习统计（/history）

本文件保留收藏与答题记录路由，并 re-export 所有被外部引用的符号以确保向后兼容。
"""

from flask import request, jsonify

from app.core.utils.database import get_db
from app.core.extensions import limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.cache_utils import bump_user_quiz_version

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
@limiter.exempt  # 收藏接口不限流
def toggle_favorite():
    """切换收藏状态"""
    data = request.get_json(silent=True) or {}
    q_id = data.get('question_id')
    uid = current_user_id()

    try:
        q_id = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400

    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND question_id = ?",
        (uid, q_id)
    ).fetchone()

    if exists:
        conn.execute("DELETE FROM favorites WHERE user_id = ? AND question_id = ?", (uid, q_id))
        is_favorite = False
    else:
        try:
            conn.execute("INSERT INTO favorites (user_id, question_id) VALUES (?, ?)", (uid, q_id))
        except Exception:
            # 兜底处理：题目不存在 / 外键约束失败 / 并发插入等
            conn.rollback()
            return jsonify({'status': 'error', 'message': '收藏失败：题目不存在或不可收藏'}), 400
        is_favorite = True

    conn.commit()
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
@limiter.exempt  # 答题记录接口不限流
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

    conn = get_db()
    try:
        # 更新错题本（只记录错误题目）
        if not is_correct:
            try:
                conn.execute(
                    """
                    INSERT INTO mistakes (user_id, question_id, wrong_count, created_at, updated_at, last_updated)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, question_id) DO UPDATE SET
                      wrong_count = wrong_count + 1,
                      updated_at = CURRENT_TIMESTAMP,
                      last_updated = CURRENT_TIMESTAMP
                    """,
                    (uid, q_id),
                )
            except Exception:
                # 兼容旧库：缺少 created_at/updated_at/last_updated 字段
                conn.execute(
                    "INSERT INTO mistakes (user_id, question_id, wrong_count) VALUES (?, ?, 1) ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1",
                    (uid, q_id),
                )
            action = "added_mistake"
        else:
            if clear_mistake_on_correct:
                # 答对了，从错题本中移除（默认行为）
                conn.execute("DELETE FROM mistakes WHERE user_id = ? AND question_id = ?", (uid, q_id))
                action = "removed_mistake"
            else:
                # 答对但不清除：保留在错题本
                action = "kept_mistake"

        # 记录答题历史（每次答题都记录，用于统计）
        # 先删除旧记录，再插入新记录，确保每个用户对每道题只保留最新的一条记录
        conn.execute(
            'DELETE FROM user_answers WHERE user_id = ? AND question_id = ?',
            (uid, q_id)
        )
        conn.execute(
            """INSERT INTO user_answers
               (user_id, question_id, is_correct, created_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (uid, q_id, 1 if is_correct else 0)
        )

        # 增加刷题数（如果功能开启）
        increment_user_quiz_count(uid)

        conn.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        return jsonify({"status": "success", "action": action})
    except Exception as e:
        conn.rollback()
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
