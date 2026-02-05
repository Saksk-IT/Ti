# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

from flask import current_app, redirect, render_template, request, session

from app.core.utils.database import get_db

from .bp import main_pages_bp
from .common import _get_accessible_subject_rows


@main_pages_bp.route('/hub')
def hub():
    """介绍页"""
    uid = session.get('user_id')
    conn = get_db()

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
            subjects_meta = _get_accessible_subject_rows(conn, uid)
            subject_total = len(subjects_meta or [])

            subject_ids = [int(s['id']) for s in (subjects_meta or []) if s and s.get('id') is not None]
            if subject_ids:
                placeholders = ','.join(['?'] * len(subject_ids))
                question_total = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM questions q
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    subject_ids,
                ).fetchone()[0]
        else:
            subject_total = conn.execute(
                "SELECT COUNT(*) FROM subjects WHERE (is_locked=0 OR is_locked IS NULL)"
            ).fetchone()[0]
            question_total = conn.execute(
                """
                SELECT COUNT(*)
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                """
            ).fetchone()[0]
    except Exception as e:
        current_app.logger.error(f"Error fetching hub stats: {e}")
        subject_total = 0
        question_total = 0

    if uid:
        try:
            my_bank_total = conn.execute(
                "SELECT COUNT(*) FROM user_question_banks WHERE user_id = ? AND status = 1",
                (uid,),
            ).fetchone()[0]
        except Exception:
            my_bank_total = 0

        try:
            if subject_ids:
                placeholders = ','.join(['?'] * len(subject_ids))

                favorites_count = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM favorites f
                    JOIN questions q ON f.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE f.user_id = ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    [uid, *subject_ids],
                ).fetchone()[0]

                mistakes_count = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM mistakes m
                    JOIN questions q ON m.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE m.user_id = ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    [uid, *subject_ids],
                ).fetchone()[0]

                from datetime import date

                today = date.today()
                day_keys = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

                start_dt = datetime.combine(today - timedelta(days=6), datetime.min.time())
                end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
                start_s = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                end_s = end_dt.strftime('%Y-%m-%d %H:%M:%S')

                prev_start_dt = datetime.combine(today - timedelta(days=13), datetime.min.time())
                prev_end_dt = datetime.combine(today - timedelta(days=6), datetime.min.time())
                prev_start_s = prev_start_dt.strftime('%Y-%m-%d %H:%M:%S')
                prev_end_s = prev_end_dt.strftime('%Y-%m-%d %H:%M:%S')

                rows = conn.execute(
                    f"""
                    SELECT DATE(ua.created_at) AS d, COUNT(*) AS cnt
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE ua.user_id = ?
                      AND ua.created_at >= ? AND ua.created_at < ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    GROUP BY d
                    ORDER BY d
                    """,
                    [uid, start_s, end_s, *subject_ids],
                ).fetchall()

                by_day = {}
                for r in (rows or []):
                    if not r:
                        continue
                    d = r['d']
                    if not d:
                        continue
                    by_day[str(d)] = int(r['cnt'] or 0)
                answers_7d_series = [int(by_day.get(k, 0) or 0) for k in day_keys]
                answers_7d_total = int(sum(answers_7d_series))

                answers_7d_correct = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE ua.user_id = ?
                      AND ua.is_correct = 1
                      AND ua.created_at >= ? AND ua.created_at < ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    [uid, start_s, end_s, *subject_ids],
                ).fetchone()[0]
                answers_7d_correct = int(answers_7d_correct or 0)
                answers_7d_accuracy = round(answers_7d_correct / answers_7d_total * 100, 1) if answers_7d_total > 0 else 0

                prev_total = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE ua.user_id = ?
                      AND ua.created_at >= ? AND ua.created_at < ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    [uid, prev_start_s, prev_end_s, *subject_ids],
                ).fetchone()[0]
                prev_total = int(prev_total or 0)

                prev_correct = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE ua.user_id = ?
                      AND ua.is_correct = 1
                      AND ua.created_at >= ? AND ua.created_at < ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    [uid, prev_start_s, prev_end_s, *subject_ids],
                ).fetchone()[0]
                prev_correct = int(prev_correct or 0)

                prev_accuracy = round(prev_correct / prev_total * 100, 1) if prev_total > 0 else 0

                answers_7d_delta = int(answers_7d_total - prev_total)
                accuracy_7d_delta = round(float(answers_7d_accuracy - prev_accuracy), 1)

                recent = conn.execute(
                    f"""
                    SELECT q.subject_id as subject_id, s.name as subject_name, MAX(ua.created_at) as last_answer_at
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE ua.user_id = ?
                      AND q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    GROUP BY q.subject_id
                    ORDER BY ua.created_at DESC
                    LIMIT 1
                    """,
                    [uid, *subject_ids],
                ).fetchone()
                if recent and recent['subject_id'] is not None and recent['subject_name']:
                    recent_subject = {
                        'id': int(recent['subject_id']),
                        'name': str(recent['subject_name']),
                        'last_answer_at': (recent['last_answer_at'] or '') if 'last_answer_at' in recent.keys() else '',
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
                        y = pad + (height - pad * 2) * (1 - ((v - min_v) / span))
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

    return render_template(
        'main/hub/hub.html',
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
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/')
def index():
    """首页（题库广场）"""
    return redirect('/public/banks')

