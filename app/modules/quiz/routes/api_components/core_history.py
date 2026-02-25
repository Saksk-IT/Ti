# -*- coding: utf-8 -*-
"""学习统计历史路由 — /history 接口

从 core.py 拆分，提供学习统计（答题历史、连续天数、科目/题型/难度维度、薄弱点等）。
"""

from datetime import datetime, timedelta

from flask import request, jsonify, current_app
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import (
    get_questions_version,
    get_subjects_version,
    get_user_quiz_version,
    make_cache_key,
)
from app.core.utils.time_utils import today_bj

from ..api_bp import quiz_api_bp


def _build_named_in(prefix: str, values: list) -> tuple[str, dict]:
    """构建命名参数 IN 子句，返回 (placeholder_str, params_dict)"""
    params = {}
    names = []
    for i, v in enumerate(values):
        key = f"{prefix}_{i}"
        params[key] = v
        names.append(f":{key}")
    return ", ".join(names), params


@quiz_api_bp.route("/history", methods=["GET"])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_history_stats():
    """学习统计（与 Web /history 同语义，供小程序 v2 页面使用）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.core.utils.portable_question_format import portable_type_to_q_type

    uid = current_user_id()
    if not uid:
        return jsonify({"status": "unauthorized", "message": "请先登录"}), 401

    cache_key = None
    cache_ttl = 0
    if bool(current_app.config.get("QUIZ_API_CACHE_ENABLED", True)):
        try:
            cache_ttl = int(current_app.config.get("QUIZ_CACHE_TTL_HISTORY_SECONDS", 30) or 30)
        except Exception:
            cache_ttl = 30
        if cache_ttl > 0:
            try:
                cache_key = make_cache_key(
                    "quiz:history",
                    {
                        "uid": int(uid),
                        "uv": get_user_quiz_version(int(uid)),
                        "qv": get_questions_version(),
                        "sv": get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get("status") == "success" and "data" in cached:
                    return jsonify(cached)
            except Exception:
                cache_key = None

    # 可访问科目（并过滤锁定）
    subject_ids, subjects_meta = _load_subjects_meta(uid)

    # 公共题库总题数（按权限与锁定过滤）
    total_questions = _count_total_questions(subject_ids)

    # 复用 join + 权限过滤（公共题库）
    ua_from, ua_params_base = _build_ua_from(uid, subject_ids)

    # 全局汇总（公共题库）
    answered_count, correct_count, last_activity = _summary_stats(ua_from, ua_params_base)

    accuracy = round(correct_count * 100 / answered_count, 1) if answered_count > 0 else 0.0
    completion = round(answered_count * 100 / total_questions, 1) if total_questions > 0 else 0.0

    # 收藏/错题（公共题库）
    favorites_count = _count_favorites(uid, subject_ids)
    mistakes_count, mistakes_times = _count_mistakes(uid, subject_ids)

    # 连续学习天数
    streak_days = _calc_streak(ua_from, ua_params_base)

    # 近期统计
    answered_7d, correct_7d = _count_since(ua_from, ua_params_base, 7, answered_count, correct_count)
    answered_30d, correct_30d = _count_since(ua_from, ua_params_base, 30, answered_count, correct_count)

    # 趋势窗口
    window_days = request.args.get("days", 30, type=int)
    if window_days not in (7, 30, 90):
        window_days = 30
    daily, daily_max, window_answered, window_correct, window_accuracy = _build_daily_trend(
        ua_from, ua_params_base, window_days,
    )

    # 科目维度
    subject_rows = _build_subject_rows(uid, subject_ids, subjects_meta)

    # 题型维度
    type_rows = _build_type_rows(ua_from, ua_params_base, portable_type_to_q_type)

    # 难度维度
    difficulty_rows = _build_difficulty_rows(ua_from, ua_params_base)

    # 薄弱点
    weakness_rows = _build_weakness_rows(uid, subject_ids, ua_from, ua_params_base, portable_type_to_q_type)

    # 最近错题
    recent_mistakes = _build_recent_mistakes(uid, subject_ids, portable_type_to_q_type)

    # 下一步建议
    next_actions = []
    try:
        for w in (weakness_rows or [])[:3]:
            next_actions.append({
                "title": _fmt_weakness_title(w),
                "meta": f"正确率 {w['accuracy']}%（已做 {w['answered']}）",
                "subject": w["subject"],
                "q_type": w["q_type"],
            })
    except Exception:
        next_actions = []

    payload = {
        "status": "success",
        "data": {
            "subjects_meta": subjects_meta,
            "total_questions": total_questions,
            "answered_count": answered_count,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "completion": completion,
            "favorites_count": favorites_count,
            "mistakes_count": mistakes_count,
            "mistakes_times": mistakes_times,
            "streak_days": streak_days,
            "last_activity": last_activity,
            "answered_7d": answered_7d,
            "correct_7d": correct_7d,
            "answered_30d": answered_30d,
            "correct_30d": correct_30d,
            "window_days": window_days,
            "daily": daily,
            "daily_max": daily_max or 1,
            "window_answered": window_answered,
            "window_correct": window_correct,
            "window_accuracy": window_accuracy,
            "subject_rows": subject_rows,
            "type_rows": type_rows,
            "difficulty_rows": difficulty_rows,
            "weakness_rows": weakness_rows,
            "recent_mistakes": recent_mistakes,
            "next_actions": next_actions,
        },
    }

    if cache_key and cache_ttl > 0 and bool(current_app.config.get("QUIZ_API_CACHE_ENABLED", True)):
        try:
            redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
        except Exception:
            pass

    return jsonify(payload)



# ---------------------------------------------------------------------------
# 以下为 api_history_stats 的辅助函数
# ---------------------------------------------------------------------------

def _fmt_weakness_title(w: dict) -> str:
    """格式化薄弱点标题"""
    return f"{w['subject']} · {w['q_type']}"


def _load_subjects_meta(uid) -> tuple[list[int], list[dict]]:
    """加载用户可访问的科目元数据"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subject_ids: list[int] = []
    subjects_meta: list[dict] = []
    try:
        accessible_ids = get_user_accessible_subjects(uid) or []
        if accessible_ids:
            in_str, in_params = _build_named_in("sid", accessible_ids)
            rows = db.session.execute(
                text(f"""
                SELECT id, name
                FROM subjects
                WHERE (is_locked=false OR is_locked IS NULL)
                  AND id IN ({in_str})
                ORDER BY id
                """),
                in_params,
            ).fetchall()
            subjects_meta = [{"id": int(r[0]), "name": r[1]} for r in (rows or []) if r and r[0] is not None]
            subject_ids = [int(r[0]) for r in (rows or []) if r and r[0] is not None]
    except Exception as e:
        current_app.logger.warning(f"history subjects meta failed: {e}")
        subject_ids = []
        subjects_meta = []
    return subject_ids, subjects_meta


def _count_total_questions(subject_ids: list[int]) -> int:
    """公共题库总题数（按权限与锁定过滤）"""
    try:
        base_sql = """
            SELECT COUNT(*)
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE (s.is_locked=false OR s.is_locked IS NULL)
        """
        params: dict = {}
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            base_sql += f" AND q.subject_id IN ({in_str})"
            params.update(in_params)
        return int(db.session.execute(text(base_sql), params).scalar() or 0)
    except Exception as e:
        current_app.logger.warning(f"history total_questions failed: {e}")
        return 0


def _build_ua_from(uid, subject_ids: list[int]) -> tuple[str, dict]:
    """构建 user_answers 的 FROM + WHERE 子句和参数"""
    ua_from = """
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE ua.user_id = :uid
          AND (s.is_locked=false OR s.is_locked IS NULL)
    """
    ua_params_base: dict = {"uid": uid}
    if subject_ids:
        in_str, in_params = _build_named_in("sid", subject_ids)
        ua_from += f" AND q.subject_id IN ({in_str})"
        ua_params_base.update(in_params)
    return ua_from, ua_params_base


def _summary_stats(ua_from: str, ua_params_base: dict) -> tuple[int, int, str | None]:
    """全局汇总：已答题数、正确数、最后活动时间"""
    try:
        row = db.session.execute(
            text(f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct,
              MAX(ua.created_at) AS last_activity
            {ua_from}
            """),
            ua_params_base,
        ).fetchone()
        answered = int(row[0] or 0) if row else 0
        correct = int(row[1] or 0) if row else 0
        last_act = (str(row[2]) if row and row[2] else None)
        return answered, correct, last_act
    except Exception as e:
        current_app.logger.warning(f"history summary failed: {e}")
        return 0, 0, None


def _count_favorites(uid, subject_ids: list[int]) -> int:
    """收藏数（公共题库）"""
    try:
        fav_sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
        """
        fav_params: dict = {"uid": uid}
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            fav_sql += f" AND q.subject_id IN ({in_str})"
            fav_params.update(in_params)
        return int(db.session.execute(text(fav_sql), fav_params).scalar() or 0)
    except Exception as e:
        current_app.logger.warning(f"history favorites_count failed: {e}")
        return 0


def _count_mistakes(uid, subject_ids: list[int]) -> tuple[int, int]:
    """错题数和累计错误次数（公共题库）"""
    try:
        mis_sql = """
            SELECT
              COUNT(*) AS cnt,
              SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
        """
        mis_params: dict = {"uid": uid}
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            mis_sql += f" AND q.subject_id IN ({in_str})"
            mis_params.update(in_params)
        row = db.session.execute(text(mis_sql), mis_params).fetchone()
        cnt = int(row[0] or 0) if row else 0
        times = int(row[1] or 0) if row else 0
        return cnt, times
    except Exception as e:
        current_app.logger.warning(f"history mistakes_count failed: {e}")
        return 0, 0



def _calc_streak(ua_from: str, ua_params_base: dict) -> int:
    """连续学习天数（基于 user_answers 的 DATE(created_at)）"""
    try:
        rows = db.session.execute(
            text(f"SELECT DISTINCT DATE(ua.created_at) AS day {ua_from} ORDER BY day DESC LIMIT 120"),
            ua_params_base,
        ).fetchall()
        dates = []
        for r in rows or []:
            if r and r[0]:
                try:
                    d = r[0]
                    if isinstance(d, str):
                        dates.append(datetime.strptime(d, "%Y-%m-%d").date())
                    else:
                        dates.append(d)
                except Exception:
                    continue
        today = today_bj()
        if dates and dates[0] >= (today - timedelta(days=1)):
            streak = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    streak += 1
                else:
                    break
            return streak
        return 0
    except Exception as e:
        current_app.logger.warning(f"history streak failed: {e}")
        return 0


def _count_since(
    ua_from: str, ua_params_base: dict,
    days: int, total_answered: int, total_correct: int,
) -> tuple[int, int]:
    """统计最近 N 天的答题数和正确数"""
    if days <= 0:
        return total_answered, total_correct
    try:
        cutoff = datetime.utcnow() + timedelta(hours=8) - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        params = dict(ua_params_base)
        params["cutoff"] = cutoff_str
        row = db.session.execute(
            text(f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
            {ua_from}
              AND ua.created_at >= :cutoff
            """),
            params,
        ).fetchone()
        return int(row[0] or 0), int(row[1] or 0)
    except Exception:
        return 0, 0


def _build_daily_trend(
    ua_from: str, ua_params_base: dict, window_days: int,
) -> tuple[list[dict], int, int, int, float]:
    """构建每日趋势数据"""
    daily: list[dict] = []
    daily_max = 0
    window_answered = 0
    window_correct = 0
    window_accuracy = 0.0
    try:
        cutoff = datetime.utcnow() + timedelta(hours=8) - timedelta(days=window_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        params = dict(ua_params_base)
        params["cutoff"] = cutoff_str
        rows = db.session.execute(
            text(f"""
            SELECT
              DATE(ua.created_at) AS day,
              COUNT(*) AS total,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
            {ua_from}
              AND ua.created_at >= :cutoff
            GROUP BY DATE(ua.created_at)
            ORDER BY day
            """),
            params,
        ).fetchall()
        data_map = {}
        for r in (rows or []):
            if r and r[0]:
                day_key = str(r[0])
                data_map[day_key] = {"total": int(r[1] or 0), "correct": int(r[2] or 0)}

        today = today_bj()
        start = today - timedelta(days=window_days - 1)
        for i in range(window_days):
            d = start + timedelta(days=i)
            key = d.strftime("%Y-%m-%d")
            total = int((data_map.get(key) or {}).get("total", 0))
            correct = int((data_map.get(key) or {}).get("correct", 0))
            acc = round(correct * 100 / total, 1) if total > 0 else 0.0
            daily_max = max(daily_max, total)
            daily.append({"day": key, "total": total, "correct": correct, "accuracy": acc})

        window_answered = sum(int(x.get("total", 0) or 0) for x in daily)
        window_correct = sum(int(x.get("correct", 0) or 0) for x in daily)
        window_accuracy = round(window_correct * 100 / window_answered, 1) if window_answered > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"history daily failed: {e}")

    return daily, daily_max, window_answered, window_correct, window_accuracy



def _build_subject_rows(uid, subject_ids: list[int], subjects_meta: list[dict]) -> list[dict]:
    """科目维度统计（公共题库）"""
    subject_rows: list[dict] = []
    try:
        total_map: dict = {}
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            rows = db.session.execute(
                text(f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS total
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=false OR s.is_locked IS NULL)
                  AND q.subject_id IN ({in_str})
                GROUP BY q.subject_id
                """),
                in_params,
            ).fetchall()
            total_map = {int(r[0]): int(r[1] or 0) for r in (rows or []) if r and r[0] is not None}

        ans_map: dict = {}
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            in_params["uid"] = uid
            rows = db.session.execute(
                text(f"""
                SELECT q.subject_id AS subject_id,
                       COUNT(*) AS answered,
                       SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE ua.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
                  AND q.subject_id IN ({in_str})
                GROUP BY q.subject_id
                """),
                in_params,
            ).fetchall()
            ans_map = {
                int(r[0]): {"answered": int(r[1] or 0), "correct": int(r[2] or 0)}
                for r in (rows or [])
                if r and r[0] is not None
            }

        mis_map: dict = {}
        fav_map: dict = {}
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            in_params["uid"] = uid
            rows = db.session.execute(
                text(f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
                  AND q.subject_id IN ({in_str})
                GROUP BY q.subject_id
                """),
                in_params,
            ).fetchall()
            mis_map = {int(r[0]): int(r[1] or 0) for r in (rows or []) if r and r[0] is not None}

            in_str2, in_params2 = _build_named_in("sid", subject_ids)
            in_params2["uid"] = uid
            rows = db.session.execute(
                text(f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
                  AND q.subject_id IN ({in_str2})
                GROUP BY q.subject_id
                """),
                in_params2,
            ).fetchall()
            fav_map = {int(r[0]): int(r[1] or 0) for r in (rows or []) if r and r[0] is not None}

        for s in subjects_meta or []:
            sid = int(s["id"])
            total = int(total_map.get(sid, 0))
            answered = int((ans_map.get(sid) or {}).get("answered", 0))
            correct = int((ans_map.get(sid) or {}).get("correct", 0))
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            comp = round(answered * 100 / total, 1) if total > 0 else 0.0
            subject_rows.append({
                "subject_id": sid,
                "subject": s["name"],
                "total": total,
                "answered": answered,
                "correct": correct,
                "accuracy": acc,
                "completion": comp,
                "mistakes": int(mis_map.get(sid, 0)),
                "favorites": int(fav_map.get(sid, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history subject rows failed: {e}")
        subject_rows = []
    return subject_rows



def _build_type_rows(ua_from: str, ua_params_base: dict, portable_type_to_q_type) -> list[dict]:
    """题型维度统计（公共题库）"""
    type_rows: list[dict] = []
    try:
        rows = db.session.execute(
            text(f"""
            SELECT
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            ORDER BY answered DESC
            """),
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            p_type = str(r[0] or "unknown")
            answered = int(r[1] or 0)
            correct = int(r[2] or 0)
            type_rows.append({
                "q_type": ("未知" if p_type == "unknown" else portable_type_to_q_type(p_type)),
                "answered": answered,
                "correct": correct,
                "accuracy": round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history type rows failed: {e}")
    return type_rows


def _build_difficulty_rows(ua_from: str, ua_params_base: dict) -> list[dict]:
    """难度维度统计（公共题库）"""
    difficulty_rows: list[dict] = []
    try:
        rows = db.session.execute(
            text(f"""
            SELECT
              COALESCE(q.difficulty, 1) AS difficulty,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.difficulty
            ORDER BY difficulty ASC
            """),
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            diff = int(r[0] or 1)
            answered = int(r[1] or 0)
            correct = int(r[2] or 0)
            label = {1: "简单", 2: "中等", 3: "困难"}.get(diff, f"难度{diff}")
            difficulty_rows.append({
                "difficulty": diff,
                "label": label,
                "answered": answered,
                "correct": correct,
                "accuracy": round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history difficulty rows failed: {e}")
    return difficulty_rows


def _build_weakness_rows(
    uid, subject_ids: list[int],
    ua_from: str, ua_params_base: dict,
    portable_type_to_q_type,
) -> list[dict]:
    """薄弱点：科目 x 题型（公共题库）"""
    weakness_rows: list[dict] = []
    try:
        rows = db.session.execute(
            text(f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY s.name, COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            HAVING COUNT(*) >= 5
            ORDER BY (SUM(CASE WHEN ua.is_correct = true THEN 1 ELSE 0 END) * 1.0 / COUNT(*)) ASC, COUNT(*) DESC
            LIMIT 8
            """),
            ua_params_base,
        ).fetchall()

        mis_params: dict = {"uid": uid}
        mis_sid_clause = ""
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            mis_sid_clause = f" AND q.subject_id IN ({in_str})"
            mis_params.update(in_params)

        mis_rows = db.session.execute(
            text(f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              COUNT(*) AS mistakes
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
            {mis_sid_clause}
            GROUP BY s.name, COALESCE(NULLIF(TRIM(q.type), ''), 'unknown')
            """),
            mis_params,
        ).fetchall()

        mis_map: dict = {}
        for r in mis_rows or []:
            if not r:
                continue
            subject_name = r[0] or "未分类"
            p_type = str(r[1] or "unknown")
            q_type_disp = "未知" if p_type == "unknown" else portable_type_to_q_type(p_type)
            mis_map[(subject_name, q_type_disp)] = int(r[2] or 0)

        for r in rows or []:
            p_type = str(r[1] or "unknown")
            q_type_disp = "未知" if p_type == "unknown" else portable_type_to_q_type(p_type)
            answered = int(r[2] or 0)
            correct = int(r[3] or 0)
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            key = (r[0] or "未分类", q_type_disp)
            weakness_rows.append({
                "subject": r[0] or "未分类",
                "q_type": q_type_disp,
                "answered": answered,
                "correct": correct,
                "accuracy": acc,
                "mistakes": int(mis_map.get(key, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history weakness rows failed: {e}")
    return weakness_rows



def _build_recent_mistakes(
    uid, subject_ids: list[int],
    portable_type_to_q_type,
) -> list[dict]:
    """最近错题（公共题库）"""
    recent_mistakes: list[dict] = []
    try:
        order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC"

        params: dict = {"uid": uid}
        sid_clause = ""
        if subject_ids:
            in_str, in_params = _build_named_in("sid", subject_ids)
            sid_clause = f" AND q.subject_id IN ({in_str})"
            params.update(in_params)

        sql = f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(NULLIF(TRIM(q.type), ''), 'unknown') AS p_type,
              q.id AS question_id,
              q.content AS content,
              q.difficulty AS difficulty,
              m.created_at AS created_at,
              m.wrong_count AS wrong_count
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
            {sid_clause}
            ORDER BY {order_by}
            LIMIT 8
        """
        rows = db.session.execute(text(sql), params).fetchall()
        for r in rows or []:
            raw_content = (str(r[3]) if r[3] else "").strip()
            raw_content = raw_content.replace('\r', ' ').replace('\n', ' ')
            snippet = raw_content[:80] + ("…" if len(raw_content) > 80 else "")
            p_type = str(r[1] or "unknown")
            q_type_disp = "未知" if p_type == "unknown" else portable_type_to_q_type(p_type)
            recent_mistakes.append({
                "subject": r[0] or "未分类",
                "q_type": q_type_disp,
                "question_id": int(r[2]),
                "snippet": snippet,
                "difficulty": int(r[4] or 1),
                "wrong_count": int(r[6] or 1) if r[6] is not None else None,
            })
    except Exception as e:
        current_app.logger.warning(f"history recent mistakes failed: {e}")
    return recent_mistakes
