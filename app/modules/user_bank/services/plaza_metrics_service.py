# -*- coding: utf-8 -*-
"""题库广场读模型刷新服务。"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from datetime import timedelta
from typing import Any

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.redis_utils import get_redis_connection
from app.core.utils.time_utils import now_bj

METRICS_TTL_SECONDS = 300
METRICS_MIN_TTL_SECONDS = 60
METRICS_REFRESH_LOCK_KEY = 'plaza:metrics:refresh:lock'
METRICS_REFRESH_LOCK_TTL_SECONDS = 30
METRICS_REFRESH_WAIT_SECONDS = 8.0
METRICS_REFRESH_POLL_SECONDS = 0.2

_LOCAL_REFRESH_LOCK = threading.Lock()
_logger = logging.getLogger(__name__)


def ensure_plaza_metrics(force: bool = False, ttl_seconds: int = METRICS_TTL_SECONDS) -> None:
    ttl = max(int(ttl_seconds or 0), METRICS_MIN_TTL_SECONDS)
    if not force and not _is_metrics_stale(ttl):
        return

    release = _try_acquire_refresh_lock()
    if release is None:
        if _wait_for_metrics_refresh(ttl_seconds=ttl):
            return
        _logger.warning('题库广场指标刷新锁繁忙，跳过本次同步刷新（force=%s）', force)
        return

    try:
        if not force and not _is_metrics_stale(ttl):
            return
        _refresh_plaza_metrics()
    finally:
        release()


def _is_metrics_stale(ttl_seconds: int) -> bool:
    row = db.session.execute(
        text("SELECT MAX(updated_at) AS updated_at FROM public_bank_plaza_metrics")
    ).mappings().first()
    updated_at = row.get('updated_at') if row else None
    if not updated_at:
        return True
    return (now_bj() - updated_at).total_seconds() >= max(int(ttl_seconds or 0), METRICS_MIN_TTL_SECONDS)


def _try_acquire_refresh_lock():
    conn = get_redis_connection()
    if conn is not None:
        token = secrets.token_urlsafe(12)
        try:
            locked = bool(conn.set(
                METRICS_REFRESH_LOCK_KEY,
                token,
                ex=METRICS_REFRESH_LOCK_TTL_SECONDS,
                nx=True,
            ))
        except Exception:
            locked = False
        if locked:
            token_bytes = token.encode('utf-8')

            def _release() -> None:
                try:
                    current = conn.get(METRICS_REFRESH_LOCK_KEY)
                    if current == token_bytes:
                        conn.delete(METRICS_REFRESH_LOCK_KEY)
                except Exception:
                    pass

            return _release

    if not _LOCAL_REFRESH_LOCK.acquire(blocking=False):
        return None

    def _release_local() -> None:
        if _LOCAL_REFRESH_LOCK.locked():
            _LOCAL_REFRESH_LOCK.release()

    return _release_local


def _wait_for_metrics_refresh(ttl_seconds: int) -> bool:
    deadline = time.monotonic() + METRICS_REFRESH_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(METRICS_REFRESH_POLL_SECONDS)
        try:
            if not _is_metrics_stale(ttl_seconds):
                return True
        except Exception:
            return False
    try:
        return not _is_metrics_stale(ttl_seconds)
    except Exception:
        return False


def _refresh_plaza_metrics() -> None:
    now = now_bj()
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)
    try:
        rows = _build_system_rows(cutoff_7, cutoff_30) + _build_user_rows(cutoff_7, cutoff_30)

        db.session.execute(text('DELETE FROM public_bank_plaza_metrics'))
        if rows:
            db.session.execute(
                text(
                    """
                    INSERT INTO public_bank_plaza_metrics (
                        source_type, source_id, name, description, cover_image, owner_label,
                        question_count_total, plaza_board_id, is_featured, featured_weight,
                        published_at, last_activity_at, join_count_total, join_users_7d,
                        join_users_30d, answer_count_7d, answer_count_30d, answer_users_7d,
                        answer_users_30d, hot_score, active_score, recommended_score, updated_at
                    ) VALUES (
                        :source_type, :source_id, :name, :description, :cover_image, :owner_label,
                        :question_count_total, :plaza_board_id, :is_featured, :featured_weight,
                        :published_at, :last_activity_at, :join_count_total, :join_users_7d,
                        :join_users_30d, :answer_count_7d, :answer_count_30d, :answer_users_7d,
                        :answer_users_30d, :hot_score, :active_score, :recommended_score, :updated_at
                    )
                    """
                ),
                rows,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _build_system_rows(cutoff_7, cutoff_30) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            s.id AS source_id,
            s.name AS name,
            COALESCE(s.description, '') AS description,
            NULL AS cover_image,
            '系统题库' AS owner_label,
            COALESCE(qs.question_count_total, 0) AS question_count_total,
            s.plaza_board_id AS plaza_board_id,
            COALESCE(s.is_plaza_featured, false) AS is_featured,
            COALESCE(s.plaza_featured_weight, 0) AS featured_weight,
            s.created_at AS published_at,
            COALESCE(usage.last_activity_at, s.created_at) AS last_activity_at,
            COALESCE(usage.participant_count_total, 0) AS join_count_total,
            COALESCE(usage.answer_users_7d, 0) AS join_users_7d,
            COALESCE(usage.answer_users_30d, 0) AS join_users_30d,
            COALESCE(usage.answer_count_7d, 0) AS answer_count_7d,
            COALESCE(usage.answer_count_30d, 0) AS answer_count_30d,
            COALESCE(usage.answer_users_7d, 0) AS answer_users_7d,
            COALESCE(usage.answer_users_30d, 0) AS answer_users_30d
        FROM subjects s
        LEFT JOIN (
            SELECT subject_id, COUNT(*) AS question_count_total
            FROM questions
            GROUP BY subject_id
        ) qs ON qs.subject_id = s.id
        LEFT JOIN (
            SELECT
                ev.subject_id AS subject_id,
                MAX(ev.event_at) AS last_activity_at,
                COUNT(DISTINCT ev.user_id) AS participant_count_total,
                COUNT(DISTINCT CASE WHEN ev.is_answer = 1 AND ev.event_at >= :cutoff_7 THEN ev.user_id END) AS answer_users_7d,
                COUNT(DISTINCT CASE WHEN ev.is_answer = 1 AND ev.event_at >= :cutoff_30 THEN ev.user_id END) AS answer_users_30d,
                COUNT(CASE WHEN ev.is_answer = 1 AND ev.event_at >= :cutoff_7 THEN 1 END) AS answer_count_7d,
                COUNT(CASE WHEN ev.is_answer = 1 AND ev.event_at >= :cutoff_30 THEN 1 END) AS answer_count_30d
            FROM (
                SELECT q.subject_id AS subject_id, ua.user_id AS user_id, ua.created_at AS event_at, 1 AS is_answer
                FROM questions q
                JOIN user_answers ua ON ua.question_id = q.id
                UNION ALL
                SELECT psu.subject_id AS subject_id, psu.user_id AS user_id, COALESCE(psu.last_access_at, psu.created_at) AS event_at, 0 AS is_answer
                FROM public_subject_users psu
            ) ev
            GROUP BY ev.subject_id
        ) usage ON usage.subject_id = s.id
        WHERE COALESCE(s.is_locked, false) = false
        """
    )
    rows = db.session.execute(query, {'cutoff_7': cutoff_7, 'cutoff_30': cutoff_30}).mappings().all()
    return [_hydrate_metric_row('system', row, now_bj()) for row in rows]


def _build_user_rows(cutoff_7, cutoff_30) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            b.id AS source_id,
            b.name AS name,
            COALESCE(NULLIF(b.public_description, ''), b.description, '') AS description,
            b.cover_image AS cover_image,
            COALESCE(u.username, '匿名用户') AS owner_label,
            COALESCE(b.question_count, 0) AS question_count_total,
            b.plaza_board_id AS plaza_board_id,
            COALESCE(b.is_plaza_featured, false) AS is_featured,
            COALESCE(b.plaza_featured_weight, 0) AS featured_weight,
            COALESCE(b.public_at, b.created_at) AS published_at,
            COALESCE(participants.last_activity_at, COALESCE(b.public_at, b.created_at)) AS last_activity_at,
            COALESCE(participants.participant_count_total, 0) AS join_count_total,
            COALESCE(participants.participant_users_7d, 0) AS join_users_7d,
            COALESCE(participants.participant_users_30d, 0) AS join_users_30d,
            COALESCE(answers.answer_count_7d, 0) AS answer_count_7d,
            COALESCE(answers.answer_count_30d, 0) AS answer_count_30d,
            COALESCE(answers.answer_users_7d, 0) AS answer_users_7d,
            COALESCE(answers.answer_users_30d, 0) AS answer_users_30d
        FROM user_question_banks b
        JOIN users u ON u.id = b.user_id
        LEFT JOIN (
            SELECT
                ev.bank_id AS bank_id,
                MAX(ev.event_at) AS last_activity_at,
                COUNT(DISTINCT ev.user_id) AS participant_count_total,
                COUNT(DISTINCT CASE WHEN ev.event_at >= :cutoff_7 THEN ev.user_id END) AS participant_users_7d,
                COUNT(DISTINCT CASE WHEN ev.event_at >= :cutoff_30 THEN ev.user_id END) AS participant_users_30d
            FROM (
                SELECT bank_id, user_id, COALESCE(last_access_at, created_at) AS event_at
                FROM public_bank_users
                UNION ALL
                SELECT bank_id, user_id, COALESCE(last_access_at, created_at) AS event_at
                FROM bank_share_records
                WHERE status = 1
                UNION ALL
                SELECT bank_id, user_id, created_at AS event_at
                FROM user_bank_answers
            ) ev
            GROUP BY ev.bank_id
        ) participants ON participants.bank_id = b.id
        LEFT JOIN (
            SELECT
                bank_id,
                COUNT(DISTINCT CASE WHEN created_at >= :cutoff_7 THEN user_id END) AS answer_users_7d,
                COUNT(DISTINCT CASE WHEN created_at >= :cutoff_30 THEN user_id END) AS answer_users_30d,
                COUNT(CASE WHEN created_at >= :cutoff_7 THEN 1 END) AS answer_count_7d,
                COUNT(CASE WHEN created_at >= :cutoff_30 THEN 1 END) AS answer_count_30d
            FROM user_bank_answers
            GROUP BY bank_id
        ) answers ON answers.bank_id = b.id
        WHERE b.is_public = true AND b.status = 1
        """
    )
    rows = db.session.execute(query, {'cutoff_7': cutoff_7, 'cutoff_30': cutoff_30}).mappings().all()
    return [_hydrate_metric_row('user_public', row, now_bj()) for row in rows]


def _hydrate_metric_row(source_type: str, row: dict[str, Any], updated_at) -> dict[str, Any]:
    question_count = int(row.get('question_count_total') or 0)
    join_count = int(row.get('join_count_total') or 0)
    join_users_7d = int(row.get('join_users_7d') or 0)
    join_users_30d = int(row.get('join_users_30d') or 0)
    answer_users_7d = int(row.get('answer_users_7d') or 0)
    answer_users_30d = int(row.get('answer_users_30d') or 0)
    answer_count_7d = int(row.get('answer_count_7d') or 0)
    answer_count_30d = int(row.get('answer_count_30d') or 0)
    featured_weight = int(row.get('featured_weight') or 0)
    is_featured = bool(row.get('is_featured'))

    hot_score = round(
        (join_count * 1.2) +
        (join_users_7d * 2.4) +
        (answer_users_7d * 3.0) +
        (answer_count_7d * 0.15) +
        (question_count * 0.02),
        3,
    )
    active_score = round(
        (join_users_7d * 2.0) +
        (answer_users_7d * 3.0) +
        (answer_count_7d * 0.15),
        3,
    )
    recommended_score = round(
        hot_score +
        (join_users_30d * 0.35) +
        (answer_users_30d * 0.5) +
        (featured_weight * 0.2) +
        (1000 if is_featured else 0),
        3,
    )

    return {
        'source_type': source_type,
        'source_id': int(row.get('source_id') or 0),
        'name': str(row.get('name') or '').strip(),
        'description': str(row.get('description') or '').strip(),
        'cover_image': row.get('cover_image') or None,
        'owner_label': str(row.get('owner_label') or '').strip(),
        'question_count_total': question_count,
        'plaza_board_id': row.get('plaza_board_id'),
        'is_featured': is_featured,
        'featured_weight': featured_weight,
        'published_at': row.get('published_at'),
        'last_activity_at': row.get('last_activity_at') or row.get('published_at'),
        'join_count_total': join_count,
        'join_users_7d': join_users_7d,
        'join_users_30d': join_users_30d,
        'answer_count_7d': answer_count_7d,
        'answer_count_30d': answer_count_30d,
        'answer_users_7d': answer_users_7d,
        'answer_users_30d': answer_users_30d,
        'hot_score': hot_score,
        'active_score': active_score,
        'recommended_score': recommended_score,
        'updated_at': updated_at,
    }
