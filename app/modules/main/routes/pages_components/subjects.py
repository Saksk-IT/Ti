# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from flask import redirect, render_template, request, session

from app.core.utils.database import get_db
from app.core.utils.decorators import login_required

from .bp import main_pages_bp


@main_pages_bp.route('/subjects/<int:subject_id>')
def subject_detail_page(subject_id: int):
    """科目详情页：练习设置 / 题库数据（含范围/题型/标签与统计）。"""
    uid = session.get('user_id')
    conn = get_db()

    subject = conn.execute(
        "SELECT id, name, is_locked FROM subjects WHERE id = ?",
        (subject_id,),
    ).fetchone()

    if not subject or int(subject['is_locked'] or 0) == 1:
        return "科目不存在或已锁定", 404

    # 已登录用户：校验科目权限
    if uid:
        from app.core.utils.subject_permissions import can_user_access_subject

        if not can_user_access_subject(uid, int(subject_id)):
            return "无权限访问该科目", 403

    # 题型列表
    try:
        from app.core.utils.portable_question_format import portable_type_to_q_type

        types = [
            portable_type_to_q_type((r[0] or ""))
            for r in conn.execute(
                "SELECT DISTINCT type FROM questions WHERE subject_id = ? ORDER BY type",
                (subject_id,),
            ).fetchall()
            if r and r[0]
        ]
        types = [t for t in types if t]
    except Exception:
        types = []

    # 科目题量
    total_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE q.subject_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """,
        (subject_id,),
    ).fetchone()[0]

    fav_count = 0
    mistake_count = 0
    user_tags = []
    my_stats = None
    if uid:
        try:
            fav_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                WHERE f.user_id = ? AND q.subject_id = ?
                """,
                (uid, subject_id),
            ).fetchone()[0]
        except Exception:
            fav_count = 0

        try:
            mistake_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                WHERE m.user_id = ? AND q.subject_id = ?
                """,
                (uid, subject_id),
            ).fetchone()[0]
        except Exception:
            mistake_count = 0

        try:
            from app.modules.quiz.services.question_tags_service import list_user_tags

            user_tags = list_user_tags(conn, uid, int(subject_id))
        except Exception:
            user_tags = []

        try:
            row = conn.execute(
                """
                WITH latest AS (
                  SELECT question_id, MAX(id) AS last_id
                  FROM user_answers
                  WHERE user_id = ?
                  GROUP BY question_id
                )
                SELECT
                  COUNT(1) AS answered,
                  SUM(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) AS correct
                FROM latest
                JOIN user_answers ua ON ua.id = latest.last_id
                JOIN questions q ON q.id = latest.question_id
                WHERE q.subject_id = ?
                """,
                (uid, int(subject_id)),
            ).fetchone()
            answered = int(row["answered"] or 0) if row else 0
            correct = int(row["correct"] or 0) if row else 0
            my_stats = {
                "total_answered": answered,
                "correct_count": correct,
                "accuracy": round((correct * 100.0 / answered), 1) if answered else 0.0,
            }
        except Exception:
            my_stats = {
                "total_answered": 0,
                "correct_count": 0,
                "accuracy": 0.0,
            }

    return render_template(
        'main/subject/subject_detail.html',
        subject_id=int(subject['id']),
        subject_name=subject['name'],
        types=types,
        total_count=total_count,
        fav_count=fav_count,
        mistake_count=mistake_count,
        user_tags=user_tags,
        my_stats=my_stats,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/subjects/<int:subject_id>/data')
def subject_data_redirect_page(subject_id: int):
    """公共题库数据：默认跳转到全局子页。"""
    try:
        sp = request.args.to_dict(flat=True)
        qs = ('?' + urlencode(sp)) if sp else ''
    except Exception:
        qs = ''
    return redirect(f'/subjects/{int(subject_id)}/data/global{qs}')


@main_pages_bp.route('/subjects/<int:subject_id>/data/<subtab>')
@login_required
def subject_data_page(subject_id: int, subtab: str):
    """公共题库数据子页（全局/错题/收藏）"""
    uid = session.get('user_id')
    conn = get_db()

    tab = (subtab or '').strip().lower()
    if tab not in ('global', 'mistakes', 'favorites'):
        tab = 'global'

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 30

    subject = conn.execute(
        "SELECT id, name, is_locked FROM subjects WHERE id = ?",
        (int(subject_id),),
    ).fetchone()

    if not subject or int(subject['is_locked'] or 0) == 1:
        return "科目不存在或已锁定", 404

    # 已登录用户：校验科目权限（数据页属于个人数据，不开放匿名访问）
    from app.core.utils.subject_permissions import can_user_access_subject

    if not can_user_access_subject(int(uid), int(subject_id)):
        return "无权限访问该科目", 403

    total_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE q.subject_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """,
        (int(subject_id),),
    ).fetchone()[0]

    fav_count = 0
    mistake_count = 0
    try:
        fav_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            WHERE f.user_id = ? AND q.subject_id = ?
            """,
            (int(uid), int(subject_id)),
        ).fetchone()[0]
    except Exception:
        fav_count = 0

    try:
        mistake_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            WHERE m.user_id = ? AND q.subject_id = ?
            """,
            (int(uid), int(subject_id)),
        ).fetchone()[0]
    except Exception:
        mistake_count = 0

    return render_template(
        'main/subject/subject_data.html',
        subject_id=int(subject['id']),
        subject_name=subject['name'],
        total_count=total_count,
        fav_count=fav_count,
        mistake_count=mistake_count,
        subtab=tab,
        window_days=window_days,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=int(uid or 0),
    )
