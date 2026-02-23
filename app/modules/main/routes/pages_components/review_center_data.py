# -*- coding: utf-8 -*-
"""复盘中心 — 数据 tab 统计逻辑。"""

from __future__ import annotations

from datetime import timedelta

from flask import current_app

from app.core.utils.database import safe_in_clause
from app.core.utils.time_utils import today_bj

from .review_center_helpers import _build_preview, _url_with_params


# ── 通用工具 ──────────────────────────────────────────────


def _pct(n: int, d: int) -> float:
    try:
        return round((float(n) * 100.0 / float(d)) if d else 0.0, 1)
    except Exception:
        return 0.0


def _column_exists(conn, table: str, col: str) -> bool:
    try:
        cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return col in set(cols)
    except Exception:
        return False


def _append_tag_clause(sql: str, params: list, tag_ids, col: str = 'q.id') -> tuple[str, list]:
    if isinstance(tag_ids, list):
        sql, params = safe_in_clause(col, tag_ids, sql, params)
    return sql, params


def _append_type_clause(sql: str, params: list, q_type: str, col: str = 'q.type') -> tuple[str, list]:
    if q_type and q_type != 'all':
        from app.core.utils.portable_question_format import any_type_to_portable_type
        portable_type = any_type_to_portable_type(q_type)
        col = str(col or 'q.type').replace('.q_type', '.type')
        sql += f" AND {col} = ?"
        params.append(portable_type)
    return sql, params


# ── 题型分布 ──────────────────────────────────────────────


def load_type_distribution(
    *, conn, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, tag_ids, tag: str,
    q_type: str, base_url: str, ctx: dict,
) -> tuple[list[dict], int]:
    """返回 (type_dist, data_type_count)。"""
    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
        return [], 0

    if source_type == 'public':
        base = """
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
              AND q.subject_id = ?
        """
        params: list = [int(uid), int(uid), int(subject_id)]
        if kind == 'favorites':
            base += " AND f.id IS NOT NULL"
        elif kind == 'mistakes':
            base += " AND m.id IS NOT NULL"
        if isinstance(tag_ids, list):
            base, params = safe_in_clause('q.id', tag_ids, base, params)
        base += " GROUP BY q.type ORDER BY cnt DESC"
        rows = conn.execute(base, params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        dist = [
            {'q_type': portable_type_to_q_type((r['p_type'] or '')), 'count': int(r['cnt'] or 0)}
            for r in (rows or []) if r and r['p_type']
        ]
    else:
        base = """
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM user_bank_questions q
            LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE q.bank_id = ?
        """
        params = [int(uid), int(uid), int(bank_id)]
        if kind == 'favorites':
            base += " AND f.id IS NOT NULL"
        elif kind == 'mistakes':
            base += " AND m.id IS NOT NULL"
        if isinstance(tag_ids, list):
            base, params = safe_in_clause('q.id', tag_ids, base, params)
        base += " GROUP BY q.type ORDER BY cnt DESC"
        rows = conn.execute(base, params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        dist = [
            {'q_type': portable_type_to_q_type((r['p_type'] or ''), essay_q_type="简答题"), 'count': int(r['cnt'] or 0)}
            for r in (rows or []) if r and r['p_type']
        ]

    max_n = max([d['count'] for d in dist], default=0)
    type_dist = []
    for d in dist[:10]:
        d['pct'] = int(round((d['count'] * 100.0 / max_n), 0)) if max_n else 0
        d['practice_url'] = _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': d['q_type'], 'tag': tag})
        type_dist.append(d)
    return type_dist, len(dist)


# ── 答题统计 + 活跃度 ─────────────────────────────────────


def _answer_stats_public(conn, uid: int, subject_id: int, kind: str, q_type: str, tag_ids, days: int = 0) -> tuple[int, int]:
    sql = """
        SELECT COUNT(1) as answered,
               SUM(CASE WHEN t.correct=1 THEN 1 ELSE 0 END) as correct
        FROM (
          SELECT ua.question_id as qid,
                 MAX(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
          FROM user_answers ua
          JOIN questions q ON q.id = ua.question_id
          LEFT JOIN subjects s ON q.subject_id = s.id
          LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
          LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
          WHERE ua.user_id = ?
            AND (s.is_locked=0 OR s.is_locked IS NULL)
            AND q.subject_id = ?
    """
    params: list = [int(uid), int(uid), int(uid), int(subject_id)]
    if kind == 'favorites':
        sql += " AND f.id IS NOT NULL"
    elif kind == 'mistakes':
        sql += " AND m.id IS NOT NULL"
    sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
    sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
    if days > 0:
        sql += " AND ua.created_at >= datetime('now', '+8 hours', ?)"
        params.append(f'-{int(days)} day')
    sql += " GROUP BY ua.question_id ) t"
    row = conn.execute(sql, params).fetchone()
    answered = int(row['answered'] or 0) if row else 0
    correct = int(row['correct'] or 0) if row else 0
    return answered, correct


def _answer_stats_bank(conn, uid: int, bank_id: int, kind: str, q_type: str, tag_ids, days: int = 0) -> tuple[int, int]:
    sql = """
        SELECT COUNT(1) as answered,
               SUM(CASE WHEN t.correct=1 THEN 1 ELSE 0 END) as correct
        FROM (
          SELECT ua.question_id as qid,
                 MAX(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
          FROM user_bank_answers ua
          JOIN user_bank_questions q ON q.id = ua.question_id
          LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
          LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
          WHERE ua.user_id = ?
            AND ua.bank_id = ?
            AND q.bank_id = ?
    """
    params: list = [int(uid), int(uid), int(uid), int(bank_id), int(bank_id)]
    if kind == 'favorites':
        sql += " AND f.id IS NOT NULL"
    elif kind == 'mistakes':
        sql += " AND m.id IS NOT NULL"
    sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
    sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
    if days > 0:
        sql += " AND ua.created_at >= datetime('now', '+8 hours', ?)"
        params.append(f'-{int(days)} day')
    sql += " GROUP BY ua.question_id ) t"
    row = conn.execute(sql, params).fetchone()
    answered = int(row['answered'] or 0) if row else 0
    correct = int(row['correct'] or 0) if row else 0
    return answered, correct


def _build_activity_series(conn, *, uid: int, source_type: str, subject_id: int | None,
                           bank_id: int, kind: str, q_type: str, tag_ids,
                           window_days: int = 14) -> list[dict]:
    day_offset = max(0, window_days - 1)
    since_arg = f'-{day_offset} day'

    if source_type == 'public':
        act_sql = """
            SELECT DATE(ua.created_at) as day,
                   COUNT(1) as total,
                   SUM(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
            FROM user_answers ua
            JOIN questions q ON q.id = ua.question_id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE ua.user_id = ?
              AND (s.is_locked=0 OR s.is_locked IS NULL)
              AND q.subject_id = ?
              AND ua.created_at >= datetime('now', '+8 hours', ?)
        """
        act_params: list = [int(uid), int(uid), int(uid), int(subject_id), since_arg]
        if kind == 'favorites':
            act_sql += " AND f.id IS NOT NULL"
        elif kind == 'mistakes':
            act_sql += " AND m.id IS NOT NULL"
        act_sql, act_params = _append_type_clause(act_sql, act_params, q_type, 'q.q_type')
        act_sql, act_params = _append_tag_clause(act_sql, act_params, tag_ids, 'q.id')
    else:
        act_sql = """
            SELECT DATE(ua.created_at) as day,
                   COUNT(1) as total,
                   SUM(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
            FROM user_bank_answers ua
            JOIN user_bank_questions q ON q.id = ua.question_id
            LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE ua.user_id = ?
              AND ua.bank_id = ?
              AND q.bank_id = ?
              AND ua.created_at >= datetime('now', '+8 hours', ?)
        """
        act_params = [int(uid), int(uid), int(uid), int(bank_id), int(bank_id), since_arg]
        if kind == 'favorites':
            act_sql += " AND f.id IS NOT NULL"
        elif kind == 'mistakes':
            act_sql += " AND m.id IS NOT NULL"
        act_sql, act_params = _append_type_clause(act_sql, act_params, q_type, 'q.q_type')
        act_sql, act_params = _append_tag_clause(act_sql, act_params, tag_ids, 'q.id')

    act_sql += " GROUP BY day ORDER BY day ASC"
    rows = conn.execute(act_sql, act_params).fetchall()
    day_map = {
        str(r['day']): {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)}
        for r in (rows or []) if r and r['day']
    }

    today = today_bj()
    series = []
    max_total = 0
    for i in range(window_days - 1, -1, -1):
        d = today - timedelta(days=i)
        key = d.strftime('%Y-%m-%d')
        item = day_map.get(key, {'total': 0, 'correct': 0})
        total_n = int(item.get('total') or 0)
        correct_n = int(item.get('correct') or 0)
        max_total = max(max_total, total_n)
        series.append({'day': d.strftime('%m-%d'), 'total': total_n, 'correct': correct_n})

    for it in series:
        total_n = int(it.get('total') or 0)
        correct_n = int(it.get('correct') or 0)
        it['pct'] = int(round((total_n * 100.0 / max_total), 0)) if max_total else 0
        it['acc'] = _pct(correct_n, total_n)

    return series


# ── 收藏 / 错题统计 ───────────────────────────────────────


def _load_fav_stats(conn, *, uid: int, source_type: str, subject_id: int | None,
                    bank_id: int, q_type: str, tag_ids) -> dict:
    data_fav = {'count': 0, 'new_7d': 0, 'new_30d': 0}

    if source_type == 'public':
        fav_sql = """
            SELECT COUNT(1) as cnt
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
              AND q.subject_id = ?
        """
        fav_params: list = [int(uid), int(subject_id)]
    else:
        fav_sql = """
            SELECT COUNT(1) as cnt
            FROM user_bank_questions q
            JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
            WHERE q.bank_id = ?
        """
        fav_params = [int(uid), int(bank_id)]

    fav_sql, fav_params = _append_type_clause(fav_sql, fav_params, q_type, 'q.q_type')
    fav_sql, fav_params = _append_tag_clause(fav_sql, fav_params, tag_ids, 'q.id')
    row = conn.execute(fav_sql, fav_params).fetchone()
    data_fav['count'] = int(row['cnt'] or 0) if row else 0

    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
        sql = fav_sql + " AND f.created_at >= datetime('now', '+8 hours', ?)"
        params = list(fav_params) + [f'-{int(days)} day']
        row = conn.execute(sql, params).fetchone()
        data_fav[key] = int(row['cnt'] or 0) if row else 0

    return data_fav


def _load_mis_stats_public(conn, *, uid: int, subject_id: int, q_type: str, tag_ids) -> dict:
    data_mis = {'count': 0, 'times': 0, 'new_7d': 0, 'new_30d': 0, 'active_7d': 0}

    mis_has_wrong = _column_exists(conn, 'mistakes', 'wrong_count')
    mis_created_col = None
    if _column_exists(conn, 'mistakes', 'created_at'):
        mis_created_col = 'm.created_at'
    elif _column_exists(conn, 'mistakes', 'last_updated'):
        mis_created_col = 'm.last_updated'
    elif _column_exists(conn, 'mistakes', 'updated_at'):
        mis_created_col = 'm.updated_at'

    mis_updated_col = None
    if _column_exists(conn, 'mistakes', 'updated_at'):
        mis_updated_col = 'm.updated_at'
    elif _column_exists(conn, 'mistakes', 'last_updated'):
        mis_updated_col = 'm.last_updated'
    elif _column_exists(conn, 'mistakes', 'created_at'):
        mis_updated_col = 'm.created_at'

    mis_times_expr = (
        "SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) as times"
        if mis_has_wrong
        else "COUNT(1) as times"
    )
    mis_sql = f"""
        SELECT COUNT(1) as cnt, {mis_times_expr}
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
          AND q.subject_id = ?
    """
    mis_params: list = [int(uid), int(subject_id)]
    mis_sql, mis_params = _append_type_clause(mis_sql, mis_params, q_type, 'q.q_type')
    mis_sql, mis_params = _append_tag_clause(mis_sql, mis_params, tag_ids, 'q.id')
    row = conn.execute(mis_sql, mis_params).fetchone()
    data_mis['count'] = int(row['cnt'] or 0) if row else 0
    data_mis['times'] = int(row['times'] or 0) if row else 0

    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
        if not mis_created_col:
            data_mis[key] = 0
            continue
        sql = mis_sql + f" AND {mis_created_col} >= datetime('now', '+8 hours', ?)"
        params = list(mis_params) + [f'-{int(days)} day']
        row = conn.execute(sql, params).fetchone()
        data_mis[key] = int(row['cnt'] or 0) if row else 0

    if mis_updated_col:
        sql = mis_sql + f" AND {mis_updated_col} >= datetime('now', '+8 hours', ?)"
        params = list(mis_params) + ['-7 day']
        row = conn.execute(sql, params).fetchone()
        data_mis['active_7d'] = int(row['cnt'] or 0) if row else 0

    return data_mis


def _load_mis_stats_bank(conn, *, uid: int, bank_id: int, q_type: str, tag_ids) -> dict:
    data_mis = {'count': 0, 'times': 0, 'new_7d': 0, 'new_30d': 0, 'active_7d': 0}

    mis_sql = """
        SELECT COUNT(1) as cnt,
               SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) as times
        FROM user_bank_questions q
        JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
        WHERE q.bank_id = ?
    """
    mis_params: list = [int(uid), int(bank_id)]
    mis_sql, mis_params = _append_type_clause(mis_sql, mis_params, q_type, 'q.q_type')
    mis_sql, mis_params = _append_tag_clause(mis_sql, mis_params, tag_ids, 'q.id')
    row = conn.execute(mis_sql, mis_params).fetchone()
    data_mis['count'] = int(row['cnt'] or 0) if row else 0
    data_mis['times'] = int(row['times'] or 0) if row else 0

    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
        sql = mis_sql + " AND m.created_at >= datetime('now', '+8 hours', ?)"
        params = list(mis_params) + [f'-{int(days)} day']
        row = conn.execute(sql, params).fetchone()
        data_mis[key] = int(row['cnt'] or 0) if row else 0

    sql = mis_sql + " AND m.updated_at >= datetime('now', '+8 hours', ?)"
    params = list(mis_params) + ['-7 day']
    row = conn.execute(sql, params).fetchone()
    data_mis['active_7d'] = int(row['cnt'] or 0) if row else 0

    return data_mis


# ── 标签分布 ──────────────────────────────────────────────


def _load_tag_distribution(
    conn, *, uid: int, source_type: str, bank_id: int,
    kind: str, tag: str, q_type: str, scope_qids: set,
    base_url: str, ctx: dict,
) -> tuple[list[dict], bool]:
    """返回 (tag_dist, has_tagged)。"""
    tag_counter: dict[str, int] = {}
    tagged_count = 0

    if not scope_qids:
        return [], False

    if source_type == 'public':
        from app.modules.quiz.services.question_tags_service import load_store
        store = load_store(conn, int(uid))
        bindings = store.get('bindings') or {}
        if isinstance(bindings, dict):
            for qid in scope_qids:
                tlist = bindings.get(str(qid))
                if not isinstance(tlist, list) or not tlist:
                    continue
                tagged_count += 1
                for t in tlist:
                    name = (t or '').strip()
                    if not name or name.lower() == 'all':
                        continue
                    if kind == 'tags' and tag and name == tag:
                        continue
                    tag_counter[name] = tag_counter.get(name, 0) + 1
    else:
        from app.modules.user_bank.routes.api import _load_bank_tag_store
        store = _load_bank_tag_store(conn, int(bank_id), int(uid))
        qtags = store.get('question_tags') or {}
        if isinstance(qtags, dict):
            for qid in scope_qids:
                tlist = qtags.get(str(qid)) or qtags.get(int(qid))
                if not isinstance(tlist, list) or not tlist:
                    continue
                tagged_count += 1
                for t in tlist:
                    name = (t or '').strip()
                    if not name or name.lower() == 'all':
                        continue
                    if kind == 'tags' and tag and name == tag:
                        continue
                    tag_counter[name] = tag_counter.get(name, 0) + 1

    ranked = sorted(tag_counter.items(), key=lambda kv: int(kv[1] or 0), reverse=True)[:10]
    max_c = max([int(v) for _, v in ranked], default=0)
    tag_dist = []
    for name, cnt in ranked:
        tag_dist.append({
            'name': name,
            'count': int(cnt or 0),
            'pct': int(round((float(cnt) * 100.0 / float(max_c)) if max_c else 0.0, 0)),
            'switch_url': _url_with_params(base_url, {**ctx, 'tab': 'data', 'type': q_type, 'tag': name}),
        })

    return tag_dist, tagged_count > 0


# ── 错题次数分布 ──────────────────────────────────────────


def _load_mistake_buckets(
    conn, *, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, q_type: str, tag_ids,
) -> list[dict]:
    buckets = {'1': 0, '2': 0, '3': 0, '4+': 0}

    if source_type == 'public':
        sql = """
            SELECT CASE
                     WHEN m.wrong_count IS NULL OR m.wrong_count <= 1 THEN '1'
                     WHEN m.wrong_count = 2 THEN '2'
                     WHEN m.wrong_count = 3 THEN '3'
                     ELSE '4+'
                   END as bucket,
                   COUNT(1) as cnt
            FROM mistakes m
            JOIN questions q ON q.id = m.question_id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
              AND m.user_id = ?
              AND q.subject_id = ?
        """
        params: list = [int(uid), int(subject_id)]
    else:
        sql = """
            SELECT CASE
                     WHEN m.wrong_count IS NULL OR m.wrong_count <= 1 THEN '1'
                     WHEN m.wrong_count = 2 THEN '2'
                     WHEN m.wrong_count = 3 THEN '3'
                     ELSE '4+'
                   END as bucket,
                   COUNT(1) as cnt
            FROM user_bank_mistakes m
            JOIN user_bank_questions q ON q.id = m.question_id
            WHERE m.user_id = ?
              AND q.bank_id = ?
        """
        params = [int(uid), int(bank_id)]

    sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
    sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
    sql += " GROUP BY bucket"
    rows = conn.execute(sql, params).fetchall()

    for r in rows or []:
        b = str(r['bucket'] or '').strip()
        if b in buckets:
            buckets[b] = int(r['cnt'] or 0)

    max_b = max(buckets.values()) if buckets else 0
    result = []
    for key in ('1', '2', '3', '4+'):
        cnt = int(buckets.get(key) or 0)
        result.append({
            'label': f'错 {key} 次' if key != '4+' else '错 4+ 次',
            'count': cnt,
            'pct': int(round((float(cnt) * 100.0 / float(max_b)) if max_b else 0.0, 0)),
        })
    return result


# ── scope qids 加载 ──────────────────────────────────────


def _load_scope_qids(
    conn, *, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, q_type: str, tag_ids, tag: str,
    limit: int | None = None,
) -> list[int]:
    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
        return []

    if source_type == 'public':
        sql = """
            SELECT q.id as id
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
              AND q.subject_id = ?
        """
        params: list = [int(uid), int(uid), int(subject_id)]
    else:
        sql = """
            SELECT q.id as id
            FROM user_bank_questions q
            LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE q.bank_id = ?
        """
        params = [int(uid), int(uid), int(bank_id)]

    if kind == 'favorites':
        sql += " AND f.id IS NOT NULL"
    elif kind == 'mistakes':
        sql += " AND m.id IS NOT NULL"
    sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
    sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
    sql += " ORDER BY q.id DESC"
    if isinstance(limit, int) and limit > 0:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    return [int(r['id']) for r in (rows or []) if r and r['id'] is not None]


# ── 快捷清单 ──────────────────────────────────────────────


def _load_data_items(
    conn, *, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, q_type: str, tag_ids, tag: str,
    base_url: str, ctx: dict,
) -> list[dict]:
    data_items: list[dict] = []

    if kind == 'favorites':
        if source_type == 'public':
            sql = """
                SELECT q.id, q.type as p_type, q.content, f.created_at as ts
                FROM favorites f
                JOIN questions q ON q.id = f.question_id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                  AND f.user_id = ?
                  AND q.subject_id = ?
            """
            params: list = [int(uid), int(subject_id)]
        else:
            sql = """
                SELECT q.id, q.type as p_type, q.content, f.created_at as ts
                FROM user_bank_favorites f
                JOIN user_bank_questions q ON q.id = f.question_id
                WHERE f.user_id = ?
                  AND q.bank_id = ?
            """
            params = [int(uid), int(bank_id)]

        sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
        sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
        sql += " ORDER BY f.created_at DESC LIMIT 8"
        rows = conn.execute(sql, params).fetchall()

        from app.core.utils.portable_question_format import portable_type_to_q_type
        for r in rows or []:
            qt = portable_type_to_q_type((r['p_type'] or ''))
            data_items.append({
                'title': _build_preview(r['content'] or ''),
                'q_type': qt or '未知题型',
                'meta': f"收藏于 {r['ts']}",
                'practice_url': _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': qt or 'all', 'tag': tag}),
            })

    elif kind == 'mistakes':
        if source_type == 'public':
            order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.last_updated, m.created_at) DESC"
            sql = f"""
                SELECT q.id, q.type as p_type, q.content,
                       m.wrong_count as wrong_count,
                       COALESCE(m.updated_at, m.last_updated, m.created_at) as ts
                FROM mistakes m
                JOIN questions q ON q.id = m.question_id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                  AND m.user_id = ?
                  AND q.subject_id = ?
            """
            params = [int(uid), int(subject_id)]
            sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
            sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
            sql += f" ORDER BY {order_by} LIMIT 8"
        else:
            sql = """
                SELECT q.id, q.type as p_type, q.content,
                       m.wrong_count as wrong_count,
                       COALESCE(m.updated_at, m.created_at) as ts
                FROM user_bank_mistakes m
                JOIN user_bank_questions q ON q.id = m.question_id
                WHERE m.user_id = ?
                  AND q.bank_id = ?
            """
            params = [int(uid), int(bank_id)]
            sql, params = _append_type_clause(sql, params, q_type, 'q.q_type')
            sql, params = _append_tag_clause(sql, params, tag_ids, 'q.id')
            sql += " ORDER BY m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC LIMIT 8"

        rows = conn.execute(sql, params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        for r in rows or []:
            qt = portable_type_to_q_type((r['p_type'] or ''))
            wc = int(r['wrong_count'] or 0)
            data_items.append({
                'title': _build_preview(r['content'] or ''),
                'q_type': qt or '未知题型',
                'meta': f"错 {wc} 次 · 最近 {r['ts']}",
                'practice_url': _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': qt or 'all', 'tag': tag}),
            })

    return data_items


# ── 自动建议 ──────────────────────────────────────────────


def _build_tips(
    *, kind: str, tag: str, tags: list,
    q_type: str, data_total: int, available_count: int,
    data_answer: dict, data_fav: dict, data_mis: dict,
    type_dist: list, scope_total: int, has_tagged: bool,
) -> list[str]:
    tips: list[str] = []
    total_q = int(available_count or 0) if (q_type and q_type != 'all') else int(data_total or 0)
    answered_q = int(data_answer.get('answered') or 0)
    acc = float(data_answer.get('accuracy') or 0.0)

    if total_q <= 0:
        tips.append('当前范围下暂无题目数据：可切换题型/标签，或先去刷题产生数据。')
    elif answered_q <= 0:
        tips.append('当前范围下你还没做过题：先去「开始刷题」跑一遍，本页会给出更精准的分析。')
    else:
        if acc < 60:
            tips.append('正确率偏低：建议先用「背题模式」把概念/公式过一遍，再回到刷题巩固。')
        elif acc < 80:
            tips.append('正确率不错：建议开启「打乱题目」，并将范围拆到 1 个题型/1 个标签逐步推进。')
        else:
            tips.append('正确率很高：可以尝试混合题型练习；选择/多选题再打开「打乱选项」增强抗干扰。')

    if kind == 'mistakes':
        mis_cnt = int(data_mis.get('count') or 0)
        mis_times = int(data_mis.get('times') or 0)
        if mis_cnt > 0 and mis_times >= int(mis_cnt * 2):
            tips.append('错题重复出现较多：建议把错题按标签细分，并优先复盘「高频错题型」。')
        if type_dist:
            top = type_dist[0]
            tips.append(f"优先攻克题型：{top.get('q_type')}（{top.get('count')} 题）。")
    elif kind == 'favorites':
        fav_cnt = int(data_fav.get('count') or 0)
        if fav_cnt >= 120:
            tips.append('收藏量较大：建议按标签整理（例如：易错/易忘/高频），并定期清理已掌握题目。')
        if type_dist:
            top = type_dist[0]
            tips.append(f"收藏最多的题型：{top.get('q_type')}（{top.get('count')} 题）。")
    elif kind == 'tags':
        if tag and tag.lower() != 'all':
            if int(data_total or 0) < 10:
                tips.append('该标签题目较少：可以继续补充题目，或与相近标签合并以提升统计稳定性。')
            if type_dist:
                top = type_dist[0]
                tips.append(f"该标签下最多的题型：{top.get('q_type')}（{top.get('count')} 题）。")

    if tag and tag.lower() == 'all' and (tags or []):
        tips.append('试试选择一个标签，把范围拆小后再看数据页，会更清晰。')

    if kind != 'tags' and scope_total > 0 and not has_tagged:
        tips.append('当前范围内还没有使用标签：给题目打标签能帮助你更快做复盘与专项训练。')

    return tips


# ── 主入口：加载 data tab 全部数据 ────────────────────────


def load_data_tab(
    *, conn, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, q_type: str, tag: str, tag_ids,
    tags: list, available_count: int, data_total: int,
    base_url: str, ctx: dict,
) -> dict:
    """返回 data tab 所需的全部数据字典。"""
    data_answer = {
        'answered': 0, 'correct': 0, 'accuracy': 0.0,
        'answered_7d': 0, 'correct_7d': 0, 'accuracy_7d': 0.0,
        'answered_30d': 0, 'correct_30d': 0, 'accuracy_30d': 0.0,
    }
    data_activity: list[dict] = []
    data_fav = {'count': 0, 'new_7d': 0, 'new_30d': 0}
    data_mis = {'count': 0, 'times': 0, 'new_7d': 0, 'new_30d': 0, 'active_7d': 0}
    data_tips: list = []
    data_state = {
        'total': 0, 'answered': 0, 'correct': 0, 'wrong': 0, 'unanswered': 0,
        'pct_correct': 0.0, 'pct_wrong': 0.0, 'pct_unanswered': 0.0,
    }
    mistake_buckets: list[dict] = []
    tag_dist: list[dict] = []
    data_items: list[dict] = []

    is_tag_empty = (isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all')

    if is_tag_empty:
        data_tips.append('当前标签下暂无题目：先在刷题页给题目打上该标签，再回到这里复盘。')
        return {
            'data_answer': data_answer, 'data_activity': data_activity,
            'data_fav': data_fav, 'data_mis': data_mis, 'data_tips': data_tips,
            'data_state': data_state, 'mistake_buckets': mistake_buckets,
            'tag_dist': tag_dist, 'data_items': data_items,
        }

    try:
        # 答题统计
        common_kw = dict(kind=kind, q_type=q_type, tag_ids=tag_ids)
        if source_type == 'public':
            ans_total, cor_total = _answer_stats_public(conn, uid=uid, subject_id=int(subject_id), **common_kw, days=0)
            ans_7d, cor_7d = _answer_stats_public(conn, uid=uid, subject_id=int(subject_id), **common_kw, days=7)
            ans_30d, cor_30d = _answer_stats_public(conn, uid=uid, subject_id=int(subject_id), **common_kw, days=30)
        else:
            ans_total, cor_total = _answer_stats_bank(conn, uid=uid, bank_id=bank_id, **common_kw, days=0)
            ans_7d, cor_7d = _answer_stats_bank(conn, uid=uid, bank_id=bank_id, **common_kw, days=7)
            ans_30d, cor_30d = _answer_stats_bank(conn, uid=uid, bank_id=bank_id, **common_kw, days=30)

        data_answer.update({
            'answered': ans_total, 'correct': cor_total, 'accuracy': _pct(cor_total, ans_total),
            'answered_7d': ans_7d, 'correct_7d': cor_7d, 'accuracy_7d': _pct(cor_7d, ans_7d),
            'answered_30d': ans_30d, 'correct_30d': cor_30d, 'accuracy_30d': _pct(cor_30d, ans_30d),
        })

        # 活跃度
        data_activity = _build_activity_series(
            conn, uid=uid, source_type=source_type, subject_id=subject_id,
            bank_id=bank_id, **common_kw,
        )

        # 收藏统计
        data_fav = _load_fav_stats(
            conn, uid=uid, source_type=source_type, subject_id=subject_id,
            bank_id=bank_id, q_type=q_type, tag_ids=tag_ids,
        )

        # 错题统计
        if source_type == 'public':
            data_mis = _load_mis_stats_public(conn, uid=uid, subject_id=int(subject_id), q_type=q_type, tag_ids=tag_ids)
        else:
            data_mis = _load_mis_stats_bank(conn, uid=uid, bank_id=bank_id, q_type=q_type, tag_ids=tag_ids)

        # 状态分布
        scope_total = int(available_count or 0)
        answered_q = int(data_answer.get('answered') or 0)
        correct_q = int(data_answer.get('correct') or 0)
        wrong_q = max(0, answered_q - correct_q)
        unanswered_q = max(0, scope_total - answered_q)
        data_state = {
            'total': scope_total, 'answered': answered_q,
            'correct': correct_q, 'wrong': wrong_q, 'unanswered': unanswered_q,
            'pct_correct': _pct(correct_q, scope_total),
            'pct_wrong': _pct(wrong_q, scope_total),
            'pct_unanswered': _pct(unanswered_q, scope_total),
        }

        # scope qids
        try:
            scope_qids = set(_load_scope_qids(
                conn, uid=uid, source_type=source_type, subject_id=subject_id,
                bank_id=bank_id, kind=kind, q_type=q_type, tag_ids=tag_ids, tag=tag,
            ))
        except Exception:
            scope_qids = set()

        # 标签分布
        try:
            tag_dist, has_tagged = _load_tag_distribution(
                conn, uid=uid, source_type=source_type, bank_id=bank_id,
                kind=kind, tag=tag, q_type=q_type, scope_qids=scope_qids,
                base_url=base_url, ctx=ctx,
            )
        except Exception:
            tag_dist = []
            has_tagged = False

        # 错题次数分布
        if kind == 'mistakes':
            try:
                mistake_buckets = _load_mistake_buckets(
                    conn, uid=uid, source_type=source_type, subject_id=subject_id,
                    bank_id=bank_id, q_type=q_type, tag_ids=tag_ids,
                )
            except Exception:
                mistake_buckets = []

        # 快捷清单
        try:
            data_items = _load_data_items(
                conn, uid=uid, source_type=source_type, subject_id=subject_id,
                bank_id=bank_id, kind=kind, q_type=q_type, tag_ids=tag_ids, tag=tag,
                base_url=base_url, ctx=ctx,
            )
        except Exception:
            data_items = []

        # 自动建议
        data_tips = _build_tips(
            kind=kind, tag=tag, tags=tags,
            q_type=q_type, data_total=data_total, available_count=available_count,
            data_answer=data_answer, data_fav=data_fav, data_mis=data_mis,
            type_dist=type_dist, scope_total=scope_total, has_tagged=has_tagged,
        )
    except Exception as e:
        current_app.logger.warning(f"review center data stats failed: {e}")
        data_tips = data_tips or ['数据统计加载失败：请稍后刷新重试。']

    return {
        'data_answer': data_answer, 'data_activity': data_activity,
        'data_fav': data_fav, 'data_mis': data_mis, 'data_tips': data_tips,
        'data_state': data_state, 'mistake_buckets': mistake_buckets,
        'tag_dist': tag_dist, 'data_items': data_items,
    }
