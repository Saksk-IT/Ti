# -*- coding: utf-8 -*-
"""数据中心扩展上下文（协调层）

原始 1253 行单函数已拆分为：
- _extra_stats.py        趋势 / 维度 / 排行 / 列表
- _extra_tags_insights.py 标签 / 标签图 / 全局洞察
本文件负责初始化共享变量、调用子模块、合并返回。
"""
from datetime import datetime, timedelta, timezone

from app.core.utils.time_utils import today_bj

from ._extra_stats import compute_extra_stats
from ._extra_tags_insights import compute_extra_tags_insights


def compute_data_center_context_extra(conn, uid: int, window_days: int, subject_ids: list, base_ctx: dict) -> dict:
    uid = int(uid or 0)
    base_ctx = base_ctx or {}
    from app.core.utils.portable_question_format import portable_type_to_q_type

    # --- 共享辅助函数 ---
    def _pt_to_qt(pt: str) -> str:
        pt = str(pt or '').strip()
        if not pt or pt == 'unknown':
            return '未知'
        return portable_type_to_q_type(pt) or '未知'

    def _column_exists(table: str, column: str) -> bool:
        return True

    def _chunks(items: list, size: int = 900):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    def _date_keys(days: int) -> list:
        try:
            d = int(days or 0)
        except Exception:
            d = 0
        d = max(1, min(366, d))
        today = today_bj()
        start = today - timedelta(days=d - 1)
        return [(start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(d)]

    def _safe_int(x, default: int = 0) -> int:
        try:
            return int(x or 0)
        except Exception:
            return default

    def _window_start(wd: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(days=int(wd))).strftime('%Y-%m-%d %H:%M:%S')

    # --- 从 base_ctx 解包共享变量 ---
    all_summary = base_ctx.get('all_summary') or {}
    total_questions = base_ctx.get('total_questions', 0)
    answered_count = base_ctx.get('answered_count', 0)
    correct_count = base_ctx.get('correct_count', 0)
    accuracy = base_ctx.get('accuracy', 0.0)
    completion = base_ctx.get('completion', 0.0)
    favorites_count = base_ctx.get('favorites_count', 0)
    mistakes_count = base_ctx.get('mistakes_count', 0)
    mistakes_times = base_ctx.get('mistakes_times', 0)
    streak_days = base_ctx.get('streak_days', 0)
    last_activity = base_ctx.get('last_activity')

    bank_summary = base_ctx.get('bank_summary') or {}
    bank_rows = base_ctx.get('bank_rows') or []
    bank_category_rows = base_ctx.get('bank_category_rows') or []
    bank_daily = base_ctx.get('bank_daily') or []
    bank_daily_max = base_ctx.get('bank_daily_max', 0)

    all_daily = base_ctx.get('all_daily') or []
    all_daily_max = base_ctx.get('all_daily_max', 0)
    answered_7d = base_ctx.get('answered_7d', 0)
    correct_7d = base_ctx.get('correct_7d', 0)
    answered_30d = base_ctx.get('answered_30d', 0)
    correct_30d = base_ctx.get('correct_30d', 0)

    daily = base_ctx.get('daily') or []
    daily_max = base_ctx.get('daily_max', 0)
    window_answered = base_ctx.get('window_answered', 0)
    window_correct = base_ctx.get('window_correct', 0)
    window_accuracy = base_ctx.get('window_accuracy', 0.0)

    subject_rows = base_ctx.get('subject_rows') or []
    type_rows = base_ctx.get('type_rows') or []
    difficulty_rows = base_ctx.get('difficulty_rows') or []
    weakness_rows = base_ctx.get('weakness_rows') or []
    recent_mistakes = base_ctx.get('recent_mistakes') or []
    next_actions = base_ctx.get('next_actions') or []
    ai_seed_tips = base_ctx.get('ai_seed_tips') or []

    ability_radar = base_ctx.get('ability_radar') or []
    hourly = base_ctx.get('activity_hourly') or {'max': 0, 'public': [], 'banks': [], 'all': []}
    heatmap = base_ctx.get('activity_heatmap') or {'max': 0, 'public': [], 'banks': [], 'all': []}
    mistakes_rate = base_ctx.get('mistakes_rate', 0.0)

    mistakes_has_wrong_count = _column_exists('mistakes', 'wrong_count')

    bank_ids_active = []
    try:
        bank_ids_active = sorted({int(r.get('bank_id') or 0) for r in (bank_rows or []) if int(r.get('bank_id') or 0) > 0})
    except Exception:
        bank_ids_active = []

    # --- 健康分（全局大局观）---
    health_score = 0.0
    try:
        cov = float(all_summary.get('completion') or 0.0)
        acc = float(all_summary.get('accuracy') or 0.0)
        streak = float(all_summary.get('streak_days') or 0.0)
        streak_score = max(0.0, min(100.0, streak / 14.0 * 100.0))
        mistakes_guard = max(0.0, min(100.0, 100.0 - max(0.0, min(100.0, float(mistakes_rate or 0.0)))))
        health_score = round(max(0.0, min(100.0, acc * 0.34 + cov * 0.28 + streak_score * 0.18 + mistakes_guard * 0.2)), 1)
    except Exception:
        health_score = 0.0

    # --- 调用子模块：统计段 ---
    stats_result = compute_extra_stats(
        uid=uid, window_days=window_days, subject_ids=subject_ids,
        bank_ids_active=bank_ids_active, bank_rows=bank_rows,
        mistakes_has_wrong_count=mistakes_has_wrong_count,
        _pt_to_qt=_pt_to_qt, _date_keys=_date_keys,
        _window_start=_window_start, _safe_int=_safe_int,
        _column_exists=_column_exists,
    )

    # --- 调用子模块：标签与洞察段 ---
    tags_result = compute_extra_tags_insights(
        uid=uid, window_days=window_days, subject_ids=subject_ids,
        bank_ids_active=bank_ids_active,
        answered_count=answered_count, correct_count=correct_count,
        mistakes_count=mistakes_count, favorites_count=favorites_count,
        weakness_rows=weakness_rows, health_score=health_score,
        hourly=hourly, heatmap=heatmap,
        _pt_to_qt=_pt_to_qt, _safe_int=_safe_int, _chunks=_chunks,
    )

    # --- 合并返回 ---
    result = {
        'all_summary': all_summary,
        'total_questions': total_questions,
        'answered_count': answered_count,
        'correct_count': correct_count,
        'accuracy': accuracy,
        'completion': completion,
        'favorites_count': favorites_count,
        'mistakes_count': mistakes_count,
        'mistakes_times': mistakes_times,
        'streak_days': streak_days,
        'last_activity': last_activity,
        'bank_summary': bank_summary,
        'bank_rows': bank_rows,
        'bank_category_rows': bank_category_rows,
        'bank_daily': bank_daily,
        'bank_daily_max': bank_daily_max or 1,
        'all_daily': all_daily,
        'all_daily_max': all_daily_max or 1,
        'answered_7d': answered_7d,
        'correct_7d': correct_7d,
        'answered_30d': answered_30d,
        'correct_30d': correct_30d,
        'window_days': window_days,
        'daily': daily,
        'daily_max': daily_max or 1,
        'window_answered': window_answered,
        'window_correct': window_correct,
        'window_accuracy': window_accuracy,
        'subject_rows': subject_rows,
        'type_rows': type_rows,
        'difficulty_rows': difficulty_rows,
        'weakness_rows': weakness_rows,
        'recent_mistakes': recent_mistakes,
        'next_actions': next_actions,
        'ai_seed_tips': ai_seed_tips,
        'ability_radar': ability_radar,
        'activity_hourly': hourly,
        'activity_heatmap': heatmap,
        'health_score': health_score,
    }
    result.update(stats_result)
    result.update(tags_result)
    return result
