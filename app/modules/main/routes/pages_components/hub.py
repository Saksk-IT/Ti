# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

from flask import current_app, redirect, render_template, request, session
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.time_utils import today_bj
from app.models.user import User

from .bp import main_pages_bp
from .common import _get_accessible_subject_rows


def _build_named_in(col: str, values: list, prefix: str = "in") -> tuple[str, dict]:
    """Build a named-parameter IN clause for SQLAlchemy text() queries."""
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ", ".join(f":{k}" for k in params)
    return f"{col} IN ({placeholders})", params


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return int(default)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return float(default)


def _build_spark_points(values: list[int]) -> str:
    try:
        safe_values = values or [0] * 7
        width = 96
        height = 28
        pad = 2
        max_v = max(safe_values) if safe_values else 0
        min_v = min(safe_values) if safe_values else 0
        span = (max_v - min_v) or 1
        step = (width - pad * 2) / (len(safe_values) - 1 or 1)
        pts = []
        for idx, value in enumerate(safe_values):
            x = pad + step * idx
            y = pad + (height - pad * 2) * (1 - ((value - min_v) / span))
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)
    except Exception:
        return ""


@main_pages_bp.route("/hub")
def hub():
    """介绍页"""
    uid = session.get("user_id")

    subject_total = 0
    question_total = 0
    my_bank_total = 0

    recent_subject = None
    mistakes_count = 0
    favorites_count = 0
    answers_7d_total = 0
    answers_7d_correct = 0
    answers_7d_accuracy = 0
    answers_7d_delta = 0
    accuracy_7d_delta = 0
    answers_7d_series = []
    answers_7d_spark_points = ""

    try:
        subjects_meta = None
        subject_ids = []
        if uid:
            subjects_meta = _get_accessible_subject_rows(uid=uid)
            subject_total = len(subjects_meta or [])

            subject_ids = [
                int(s["id"])
                for s in (subjects_meta or [])
                if s and s.get("id") is not None
            ]
            if subject_ids:
                in_clause, in_params = _build_named_in(
                    "q.subject_id", subject_ids, "sid"
                )
                question_total = (
                    db.session.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM questions q
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            WHERE {in_clause}
                              AND (s.is_locked = false OR s.is_locked IS NULL)
                            """
                        ),
                        in_params,
                    ).scalar()
                    or 0
                )
        else:
            subject_total = (
                db.session.execute(
                    text(
                        "SELECT COUNT(*) FROM subjects WHERE (is_locked = false OR is_locked IS NULL)"
                    )
                ).scalar()
                or 0
            )
            question_total = (
                db.session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM questions q
                        LEFT JOIN subjects s ON q.subject_id = s.id
                        WHERE (s.is_locked = false OR s.is_locked IS NULL)
                        """
                    )
                ).scalar()
                or 0
            )
    except Exception as e:
        current_app.logger.error(f"Error fetching hub stats: {e}")
        subject_total = 0
        question_total = 0

    if uid:
        try:
            my_bank_total = (
                db.session.execute(
                    text(
                        "SELECT COUNT(*) FROM user_question_banks WHERE user_id = :uid AND status = 1"
                    ),
                    {"uid": uid},
                ).scalar()
                or 0
            )
        except Exception:
            my_bank_total = 0

        try:
            if subject_ids:
                in_clause, in_params = _build_named_in(
                    "q.subject_id", subject_ids, "sid"
                )

                fav_params = {"uid": uid, **in_params}
                favorites_count = (
                    db.session.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM favorites f
                            JOIN questions q ON f.question_id = q.id
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            WHERE f.user_id = :uid
                              AND {in_clause}
                              AND (s.is_locked = false OR s.is_locked IS NULL)
                            """
                        ),
                        fav_params,
                    ).scalar()
                    or 0
                )

                mis_params = {"uid": uid, **in_params}
                mistakes_count = (
                    db.session.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM mistakes m
                            JOIN questions q ON m.question_id = q.id
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            WHERE m.user_id = :uid
                              AND {in_clause}
                              AND (s.is_locked = false OR s.is_locked IS NULL)
                            """
                        ),
                        mis_params,
                    ).scalar()
                    or 0
                )

                from datetime import date

                today = today_bj()
                day_keys = [
                    (today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)
                ]

                # created_at 存储 UTC，需将北京时间 00:00 边界转为 UTC（减 8 小时）
                bj_offset = timedelta(hours=8)
                start_dt = (
                    datetime.combine(today - timedelta(days=6), datetime.min.time())
                    - bj_offset
                )
                end_dt = (
                    datetime.combine(today + timedelta(days=1), datetime.min.time())
                    - bj_offset
                )
                start_s = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                end_s = end_dt.strftime("%Y-%m-%d %H:%M:%S")

                prev_start_dt = (
                    datetime.combine(today - timedelta(days=13), datetime.min.time())
                    - bj_offset
                )
                prev_end_dt = (
                    datetime.combine(today - timedelta(days=6), datetime.min.time())
                    - bj_offset
                )
                prev_start_s = prev_start_dt.strftime("%Y-%m-%d %H:%M:%S")
                prev_end_s = prev_end_dt.strftime("%Y-%m-%d %H:%M:%S")

                time_params = {
                    "uid": uid,
                    "start_s": start_s,
                    "end_s": end_s,
                    **in_params,
                }
                rows = db.session.execute(
                    text(
                        f"""
                        SELECT DATE(ua.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai') AS d,
                               COUNT(*) AS cnt
                        FROM user_answers ua
                        JOIN questions q ON ua.question_id = q.id
                        LEFT JOIN subjects s ON q.subject_id = s.id
                        WHERE ua.user_id = :uid
                          AND ua.created_at >= :start_s AND ua.created_at < :end_s
                          AND {in_clause}
                          AND (s.is_locked = false OR s.is_locked IS NULL)
                        GROUP BY d
                        ORDER BY d
                        """
                    ),
                    time_params,
                ).fetchall()

                by_day = {}
                for r in rows or []:
                    if not r:
                        continue
                    d = r._mapping["d"]
                    if not d:
                        continue
                    by_day[str(d)] = int(r._mapping["cnt"] or 0)
                answers_7d_series = [
                    int(by_day.get(k, 0) or 0) for k in day_keys
                ]
                answers_7d_total = int(sum(answers_7d_series))

                correct_params = {
                    "uid": uid,
                    "start_s": start_s,
                    "end_s": end_s,
                    **in_params,
                }
                answers_7d_correct = (
                    db.session.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM user_answers ua
                            JOIN questions q ON ua.question_id = q.id
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            WHERE ua.user_id = :uid
                              AND ua.is_correct = true
                              AND ua.created_at >= :start_s AND ua.created_at < :end_s
                              AND {in_clause}
                              AND (s.is_locked = false OR s.is_locked IS NULL)
                            """
                        ),
                        correct_params,
                    ).scalar()
                    or 0
                )
                answers_7d_correct = int(answers_7d_correct)
                answers_7d_accuracy = (
                    round(answers_7d_correct / answers_7d_total * 100, 1)
                    if answers_7d_total > 0
                    else 0
                )

                prev_params = {
                    "uid": uid,
                    "start_s": prev_start_s,
                    "end_s": prev_end_s,
                    **in_params,
                }
                prev_total = (
                    db.session.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM user_answers ua
                            JOIN questions q ON ua.question_id = q.id
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            WHERE ua.user_id = :uid
                              AND ua.created_at >= :start_s AND ua.created_at < :end_s
                              AND {in_clause}
                              AND (s.is_locked = false OR s.is_locked IS NULL)
                            """
                        ),
                        prev_params,
                    ).scalar()
                    or 0
                )
                prev_total = int(prev_total)

                prev_correct_params = {
                    "uid": uid,
                    "start_s": prev_start_s,
                    "end_s": prev_end_s,
                    **in_params,
                }
                prev_correct = (
                    db.session.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM user_answers ua
                            JOIN questions q ON ua.question_id = q.id
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            WHERE ua.user_id = :uid
                              AND ua.is_correct = true
                              AND ua.created_at >= :start_s AND ua.created_at < :end_s
                              AND {in_clause}
                              AND (s.is_locked = false OR s.is_locked IS NULL)
                            """
                        ),
                        prev_correct_params,
                    ).scalar()
                    or 0
                )
                prev_correct = int(prev_correct)

                prev_accuracy = (
                    round(prev_correct / prev_total * 100, 1) if prev_total > 0 else 0
                )

                answers_7d_delta = int(answers_7d_total - prev_total)
                accuracy_7d_delta = round(
                    float(answers_7d_accuracy - prev_accuracy), 1
                )

                recent_params = {"uid": uid, **in_params}
                recent = db.session.execute(
                    text(
                        f"""
                        SELECT q.subject_id as subject_id, s.name as subject_name,
                               MAX(ua.created_at) as last_answer_at
                        FROM user_answers ua
                        JOIN questions q ON ua.question_id = q.id
                        LEFT JOIN subjects s ON q.subject_id = s.id
                        WHERE ua.user_id = :uid
                          AND {in_clause}
                          AND (s.is_locked = false OR s.is_locked IS NULL)
                        GROUP BY q.subject_id, s.name
                        ORDER BY MAX(ua.created_at) DESC
                        LIMIT 1
                        """
                    ),
                    recent_params,
                ).fetchone()
                if (
                    recent
                    and recent._mapping["subject_id"] is not None
                    and recent._mapping["subject_name"]
                ):
                    recent_subject = {
                        "id": int(recent._mapping["subject_id"]),
                        "name": str(recent._mapping["subject_name"]),
                        "last_answer_at": str(
                            recent._mapping.get("last_answer_at", "") or ""
                        ),
                    }

                # Sparkline points (7 days)
                try:
                    values = answers_7d_series or [0] * 7
                    width = 96
                    height = 28
                    pad = 2
                    max_v = max(values) if values else 0
                    min_v = min(values) if values else 0
                    span = (max_v - min_v) or 1
                    step = (width - pad * 2) / (len(values) - 1 or 1)
                    pts = []
                    for idx, v in enumerate(values):
                        x = pad + step * idx
                        y = pad + (height - pad * 2) * (
                            1 - ((v - min_v) / span)
                        )
                        pts.append(f"{x:.1f},{y:.1f}")
                    answers_7d_spark_points = " ".join(pts)
                except Exception:
                    answers_7d_spark_points = ""
        except Exception as e:
            current_app.logger.error(f"Error fetching hub user metrics: {e}")
            recent_subject = None
            mistakes_count = 0
            favorites_count = 0
            answers_7d_total = 0
            answers_7d_correct = 0
            answers_7d_accuracy = 0
            answers_7d_delta = 0
            accuracy_7d_delta = 0
            answers_7d_series = []
            answers_7d_spark_points = ""

        try:
            from .data_center import _compute_data_center_context

            data_center_ctx = _compute_data_center_context(int(uid), 30)
            all_summary = data_center_ctx.get("all_summary") or {}
            bank_summary = data_center_ctx.get("bank_summary") or {}
            all_daily = data_center_ctx.get("all_daily") or []

            if all_summary:
                question_total = _safe_int(all_summary.get("total_questions"))
                favorites_count = _safe_int(all_summary.get("favorites"))
                mistakes_count = _safe_int(all_summary.get("mistakes"))

            if bank_summary:
                my_bank_total = _safe_int(bank_summary.get("bank_total"), my_bank_total)

            if all_daily:
                recent_days = list(all_daily)[-7:]
                previous_days = list(all_daily)[-14:-7]
                answers_7d_series = [
                    _safe_int((row or {}).get("total")) for row in recent_days
                ]
                answers_7d_total = sum(answers_7d_series)
                answers_7d_correct = sum(
                    _safe_int((row or {}).get("correct")) for row in recent_days
                )
                answers_7d_accuracy = (
                    round(answers_7d_correct / answers_7d_total * 100, 1)
                    if answers_7d_total > 0
                    else 0
                )

                prev_total = sum(
                    _safe_int((row or {}).get("total")) for row in previous_days
                )
                prev_correct = sum(
                    _safe_int((row or {}).get("correct")) for row in previous_days
                )
                prev_accuracy = (
                    round(prev_correct / prev_total * 100, 1) if prev_total > 0 else 0
                )
                answers_7d_delta = int(answers_7d_total - prev_total)
                accuracy_7d_delta = round(
                    _safe_float(answers_7d_accuracy) - _safe_float(prev_accuracy), 1
                )
                answers_7d_spark_points = _build_spark_points(answers_7d_series)
        except Exception as e:
            current_app.logger.warning(f"Error applying global hub stats: {e}")

    # 获取用户头像
    avatar = None
    if uid:
        try:
            user = User.query.get(uid)
            if user:
                avatar = user.avatar
        except Exception:
            avatar = None

    return render_template(
        "main/hub/hub.html",
        subject_total=subject_total,
        question_total=question_total,
        my_bank_total=my_bank_total,
        recent_subject=recent_subject,
        mistakes_count=mistakes_count,
        favorites_count=favorites_count,
        answers_7d_total=answers_7d_total,
        answers_7d_correct=answers_7d_correct,
        answers_7d_accuracy=answers_7d_accuracy,
        answers_7d_delta=answers_7d_delta,
        accuracy_7d_delta=accuracy_7d_delta,
        answers_7d_series=answers_7d_series,
        answers_7d_spark_points=answers_7d_spark_points,
        logged_in=bool(uid),
        username=session.get("username"),
        avatar=avatar,
        is_admin=session.get("is_admin", False),
        is_subject_admin=session.get("is_subject_admin", False),
        is_notification_admin=session.get("is_notification_admin", False),
        user_id=uid or 0,
    )


@main_pages_bp.route("/")
def index():
    """首页 -> Hub"""
    return redirect("/hub")
