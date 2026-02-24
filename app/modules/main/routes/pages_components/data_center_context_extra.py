# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

from flask import current_app

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.time_utils import today_bj

def compute_data_center_context_extra(conn, uid: int, window_days: int, subject_ids: list, base_ctx: dict) -> dict:
    uid = int(uid or 0)
    base_ctx = base_ctx or {}
    from app.core.utils.portable_question_format import portable_type_to_q_type

    def _pt_to_qt(pt: str) -> str:
        pt = str(pt or '').strip()
        if not pt or pt == 'unknown':
            return '未知'
        return portable_type_to_q_type(pt) or '未知'

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

    def _column_exists(table: str, column: str) -> bool:
        return True

    mistakes_has_wrong_count = _column_exists('mistakes', 'wrong_count')

    # ===== Extra: v2 数据页（错题/收藏/标签）所需聚合（仅新增字段，不改变既有语义）=====
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

    def _window_start(window_days: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(days=int(window_days))).strftime('%Y-%m-%d %H:%M:%S')

    bank_ids_active = []
    try:
        bank_ids_active = sorted({int(r.get('bank_id') or 0) for r in (bank_rows or []) if int(r.get('bank_id') or 0) > 0})
    except Exception:
        bank_ids_active = []

    # 聚合结果（供模板/Javascript 使用）
    mistakes_daily = []
    favorites_daily = []
    mistakes_by_type = []
    mistakes_by_difficulty = []
    favorites_by_type = []
    favorites_by_difficulty = []
    mistakes_top_items = []
    favorites_top_items = []
    recent_mistakes_bank = []
    recent_favorites_bank = []
    recent_favorites_public = []
    tags_public = []
    tags_banks = []
    tags_all = []
    tags_graph = {'nodes': [], 'links': []}
    tags_kpis = {
        'public_tag_count': 0,
        'banks_tag_count': 0,
        'all_tag_count': 0,
        'public_tagged_questions': 0,
        'banks_tagged_questions': 0,
        'all_tagged_questions': 0,
        'tagged_answered_coverage': 0.0,
    }
    global_insights = []
    pub_tagged_answered = 0
    banks_tagged_answered = 0

    # 健康分（全局大局观）：覆盖×正确×连续×错题治理（0-100）
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

    # ---------- 趋势：错题/收藏新增 ----------
    try:
        day_keys = _date_keys(window_days)

        pub_mis = {}
        pub_fav = {}
        bank_mis = {}
        bank_fav = {}

        # 公共：错题新增
        try:
            params = {'uid': int(uid), 'win_start': _window_start(window_days)}
            sql = """
                SELECT date(m.created_at) AS day, COUNT(*) AS cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
                  AND m.created_at >= :win_start
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            sql += " GROUP BY day ORDER BY day"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                d = (r._mapping['day'] or '')
                if d:
                    pub_mis[str(d)] = _safe_int(r._mapping['cnt'])
        except Exception:
            pub_mis = {}

        # 公共：收藏新增
        try:
            params = {'uid': int(uid), 'win_start': _window_start(window_days)}
            sql = """
                SELECT date(f.created_at) AS day, COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
                  AND f.created_at >= :win_start
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            sql += " GROUP BY day ORDER BY day"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                d = (r._mapping['day'] or '')
                if d:
                    pub_fav[str(d)] = _safe_int(r._mapping['cnt'])
        except Exception:
            pub_fav = {}

        # 个人题库：错题新增
        try:
            params = {'uid': int(uid), 'win_start': _window_start(window_days)}
            sql = """
                SELECT date(created_at) AS day, COUNT(*) AS cnt
                FROM user_bank_mistakes
                WHERE user_id = :uid
                  AND created_at >= :win_start
            """
            if bank_ids_active:
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                sql += f" AND bank_id IN ({','.join(f':bid_{i}' for i in range(len(bank_ids_active)))})"
                params.update(bid_params)
            sql += " GROUP BY day ORDER BY day"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                d = (r._mapping['day'] or '')
                if d:
                    bank_mis[str(d)] = _safe_int(r._mapping['cnt'])
        except Exception:
            bank_mis = {}

        # 个人题库：收藏新增
        try:
            params = {'uid': int(uid), 'win_start': _window_start(window_days)}
            sql = """
                SELECT date(created_at) AS day, COUNT(*) AS cnt
                FROM user_bank_favorites
                WHERE user_id = :uid
                  AND created_at >= :win_start
            """
            if bank_ids_active:
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                sql += f" AND bank_id IN ({','.join(f':bid_{i}' for i in range(len(bank_ids_active)))})"
                params.update(bid_params)
            sql += " GROUP BY day ORDER BY day"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                d = (r._mapping['day'] or '')
                if d:
                    bank_fav[str(d)] = _safe_int(r._mapping['cnt'])
        except Exception:
            bank_fav = {}

        mistakes_daily = []
        favorites_daily = []
        for d in day_keys:
            pm = _safe_int(pub_mis.get(d))
            bm = _safe_int(bank_mis.get(d))
            pf = _safe_int(pub_fav.get(d))
            bf = _safe_int(bank_fav.get(d))
            mistakes_daily.append({'day': d, 'public': pm, 'banks': bm, 'all': pm + bm})
            favorites_daily.append({'day': d, 'public': pf, 'banks': bf, 'all': pf + bf})
    except Exception as e:
        current_app.logger.warning(f"data portal trend failed: {e}")
        mistakes_daily = []
        favorites_daily = []

    # ---------- 维度：错题/收藏 题型&难度 ----------
    try:
        diff_label = {1: '简单', 2: '中等', 3: '困难'}
        ubm_has_wrong_count = _column_exists('user_bank_mistakes', 'wrong_count')

        # 公共错题：按题型
        pub_mis_type = {}
        pub_mis_type_times = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.type, 'unknown') AS p_type,
                       COUNT(*) AS cnt,
                       SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            if not mistakes_has_wrong_count:
                sql = sql.replace("m.wrong_count", "NULL")
            sql += " GROUP BY p_type ORDER BY cnt DESC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _pt_to_qt(r._mapping['p_type'])
                pub_mis_type[str(k)] = _safe_int(r._mapping['cnt'])
                pub_mis_type_times[str(k)] = (
                    _safe_int(r._mapping['times']) if mistakes_has_wrong_count else _safe_int(r._mapping['cnt'])
                )
        except Exception:
            pub_mis_type = {}
            pub_mis_type_times = {}

        # 个人题库错题：按题型
        bank_mis_type = {}
        bank_mis_type_times = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.type, 'unknown') AS p_type,
                       COUNT(*) AS cnt,
                       SUM(COALESCE(m.wrong_count, 1)) AS times
                FROM user_bank_mistakes m
                JOIN user_bank_questions q ON m.question_id = q.id
                WHERE m.user_id = :uid
            """
            if bank_ids_active:
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                sql += f" AND m.bank_id IN ({','.join(f':bid_{i}' for i in range(len(bank_ids_active)))})"
                params.update(bid_params)
            if not ubm_has_wrong_count:
                sql = sql.replace("m.wrong_count", "NULL")
            sql += " GROUP BY p_type ORDER BY cnt DESC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _pt_to_qt(r._mapping['p_type'])
                bank_mis_type[str(k)] = _safe_int(r._mapping['cnt'])
                bank_mis_type_times[str(k)] = _safe_int(r._mapping['times']) if ubm_has_wrong_count else _safe_int(r._mapping['cnt'])
        except Exception:
            bank_mis_type = {}
            bank_mis_type_times = {}

        # 公共收藏：按题型
        pub_fav_type = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.type, 'unknown') AS p_type,
                       COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            sql += " GROUP BY p_type ORDER BY cnt DESC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _pt_to_qt(r._mapping['p_type'])
                pub_fav_type[str(k)] = _safe_int(r._mapping['cnt'])
        except Exception:
            pub_fav_type = {}

        # 个人题库收藏：按题型
        bank_fav_type = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.type, 'unknown') AS p_type,
                       COUNT(*) AS cnt
                FROM user_bank_favorites f
                JOIN user_bank_questions q ON f.question_id = q.id
                WHERE f.user_id = :uid
            """
            if bank_ids_active:
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                sql += f" AND f.bank_id IN ({','.join(f':bid_{i}' for i in range(len(bank_ids_active)))})"
                params.update(bid_params)
            sql += " GROUP BY p_type ORDER BY cnt DESC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _pt_to_qt(r._mapping['p_type'])
                bank_fav_type[str(k)] = _safe_int(r._mapping['cnt'])
        except Exception:
            bank_fav_type = {}

        # 公共错题：按难度
        pub_mis_diff = {}
        pub_mis_diff_times = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.difficulty, 1) AS difficulty,
                       COUNT(*) AS cnt,
                       SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            if not mistakes_has_wrong_count:
                sql = sql.replace("m.wrong_count", "NULL")
            sql += " GROUP BY difficulty ORDER BY difficulty ASC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _safe_int(r._mapping['difficulty'], 1)
                pub_mis_diff[k] = _safe_int(r._mapping['cnt'])
                pub_mis_diff_times[k] = _safe_int(r._mapping['times']) if mistakes_has_wrong_count else _safe_int(r._mapping['cnt'])
        except Exception:
            pub_mis_diff = {}
            pub_mis_diff_times = {}

        # 个人题库错题：按难度
        bank_mis_diff = {}
        bank_mis_diff_times = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.difficulty, 1) AS difficulty,
                       COUNT(*) AS cnt,
                       SUM(COALESCE(m.wrong_count, 1)) AS times
                FROM user_bank_mistakes m
                JOIN user_bank_questions q ON m.question_id = q.id
                WHERE m.user_id = :uid
            """
            if bank_ids_active:
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                sql += f" AND m.bank_id IN ({','.join(f':bid_{i}' for i in range(len(bank_ids_active)))})"
                params.update(bid_params)
            if not ubm_has_wrong_count:
                sql = sql.replace("m.wrong_count", "NULL")
            sql += " GROUP BY difficulty ORDER BY difficulty ASC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _safe_int(r._mapping['difficulty'], 1)
                bank_mis_diff[k] = _safe_int(r._mapping['cnt'])
                bank_mis_diff_times[k] = _safe_int(r._mapping['times']) if ubm_has_wrong_count else _safe_int(r._mapping['cnt'])
        except Exception:
            bank_mis_diff = {}
            bank_mis_diff_times = {}

        # 公共收藏：按难度
        pub_fav_diff = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.difficulty, 1) AS difficulty,
                       COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            sql += " GROUP BY difficulty ORDER BY difficulty ASC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _safe_int(r._mapping['difficulty'], 1)
                pub_fav_diff[k] = _safe_int(r._mapping['cnt'])
        except Exception:
            pub_fav_diff = {}

        # 个人题库收藏：按难度
        bank_fav_diff = {}
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(q.difficulty, 1) AS difficulty,
                       COUNT(*) AS cnt
                FROM user_bank_favorites f
                JOIN user_bank_questions q ON f.question_id = q.id
                WHERE f.user_id = :uid
            """
            if bank_ids_active:
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                sql += f" AND f.bank_id IN ({','.join(f':bid_{i}' for i in range(len(bank_ids_active)))})"
                params.update(bid_params)
            sql += " GROUP BY difficulty ORDER BY difficulty ASC"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                k = _safe_int(r._mapping['difficulty'], 1)
                bank_fav_diff[k] = _safe_int(r._mapping['cnt'])
        except Exception:
            bank_fav_diff = {}

        # 汇总输出（适配 ECharts）
        type_keys = sorted(
            set(list(pub_mis_type.keys()) + list(bank_mis_type.keys()) + list(pub_fav_type.keys()) + list(bank_fav_type.keys())),
            key=lambda x: str(x),
        )
        mistakes_by_type = [
            {
                'q_type': k,
                'public': _safe_int(pub_mis_type.get(k)),
                'banks': _safe_int(bank_mis_type.get(k)),
                'all': _safe_int(pub_mis_type.get(k)) + _safe_int(bank_mis_type.get(k)),
                'times_public': _safe_int(pub_mis_type_times.get(k)),
                'times_banks': _safe_int(bank_mis_type_times.get(k)),
                'times_all': _safe_int(pub_mis_type_times.get(k)) + _safe_int(bank_mis_type_times.get(k)),
            }
            for k in type_keys
            if (_safe_int(pub_mis_type.get(k)) + _safe_int(bank_mis_type.get(k))) > 0
        ]
        favorites_by_type = [
            {
                'q_type': k,
                'public': _safe_int(pub_fav_type.get(k)),
                'banks': _safe_int(bank_fav_type.get(k)),
                'all': _safe_int(pub_fav_type.get(k)) + _safe_int(bank_fav_type.get(k)),
            }
            for k in type_keys
            if (_safe_int(pub_fav_type.get(k)) + _safe_int(bank_fav_type.get(k))) > 0
        ]

        diff_keys = sorted(set(list(pub_mis_diff.keys()) + list(bank_mis_diff.keys()) + list(pub_fav_diff.keys()) + list(bank_fav_diff.keys())))
        mistakes_by_difficulty = [
            {
                'difficulty': int(k),
                'label': diff_label.get(int(k), f'难度{int(k)}'),
                'public': _safe_int(pub_mis_diff.get(k)),
                'banks': _safe_int(bank_mis_diff.get(k)),
                'all': _safe_int(pub_mis_diff.get(k)) + _safe_int(bank_mis_diff.get(k)),
                'times_public': _safe_int(pub_mis_diff_times.get(k)),
                'times_banks': _safe_int(bank_mis_diff_times.get(k)),
                'times_all': _safe_int(pub_mis_diff_times.get(k)) + _safe_int(bank_mis_diff_times.get(k)),
            }
            for k in diff_keys
            if (_safe_int(pub_mis_diff.get(k)) + _safe_int(bank_mis_diff.get(k))) > 0
        ]
        favorites_by_difficulty = [
            {
                'difficulty': int(k),
                'label': diff_label.get(int(k), f'难度{int(k)}'),
                'public': _safe_int(pub_fav_diff.get(k)),
                'banks': _safe_int(bank_fav_diff.get(k)),
                'all': _safe_int(pub_fav_diff.get(k)) + _safe_int(bank_fav_diff.get(k)),
            }
            for k in diff_keys
            if (_safe_int(pub_fav_diff.get(k)) + _safe_int(bank_fav_diff.get(k))) > 0
        ]
    except Exception as e:
        current_app.logger.warning(f"data portal breakdown failed: {e}")
        mistakes_by_type = []
        mistakes_by_difficulty = []
        favorites_by_type = []
        favorites_by_difficulty = []

    # ---------- 排行：错题/收藏 Top 领域（公共按科目，个人按题库） ----------
    try:
        pub_mis_subject = []
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(s.name, '未分类') AS name,
                       COUNT(*) AS cnt,
                       SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            if not mistakes_has_wrong_count:
                sql = sql.replace("m.wrong_count", "NULL")
            sql += " GROUP BY name ORDER BY times DESC, cnt DESC LIMIT 10"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                pub_mis_subject.append({'name': r._mapping['name'] or '未分类', 'count': _safe_int(r._mapping['cnt']), 'times': _safe_int(r._mapping['times'])})
        except Exception:
            pub_mis_subject = []

        pub_fav_subject = []
        try:
            params = {'uid': int(uid)}
            sql = """
                SELECT COALESCE(s.name, '未分类') AS name,
                       COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = :uid
                  AND (s.is_locked=false OR s.is_locked IS NULL)
            """
            if subject_ids:
                sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                params.update(sid_params)
            sql += " GROUP BY name ORDER BY cnt DESC LIMIT 10"
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                pub_fav_subject.append({'name': r._mapping['name'] or '未分类', 'count': _safe_int(r._mapping['cnt'])})
        except Exception:
            pub_fav_subject = []

        bank_mis_rank = []
        bank_fav_rank = []
        try:
            for b in (bank_rows or []):
                name = (b.get('name') or '').strip()
                if not name:
                    continue
                bank_mis_rank.append({
                    'name': name,
                    'count': _safe_int(b.get('mistakes')),
                    'times': _safe_int(b.get('mistakes_times')),
                    'bank_id': _safe_int(b.get('bank_id')),
                })
                bank_fav_rank.append({
                    'name': name,
                    'count': _safe_int(b.get('favorites')),
                    'bank_id': _safe_int(b.get('bank_id')),
                })
            bank_mis_rank.sort(key=lambda x: (int(x.get('times') or 0), int(x.get('count') or 0)), reverse=True)
            bank_fav_rank.sort(key=lambda x: int(x.get('count') or 0), reverse=True)
        except Exception:
            bank_mis_rank = []
            bank_fav_rank = []

        mistakes_top_items = []
        for r in pub_mis_subject:
            mistakes_top_items.append({'name': r._mapping['name'], 'source': 'public', 'count': int(r.get('count') or 0), 'times': int(r.get('times') or 0)})
        for r in (bank_mis_rank or [])[:12]:
            if int(r.get('times') or 0) <= 0 and int(r.get('count') or 0) <= 0:
                continue
            mistakes_top_items.append({
                'name': r._mapping['name'],
                'source': 'banks',
                'count': int(r.get('count') or 0),
                'times': int(r.get('times') or 0),
                'bank_id': int(r.get('bank_id') or 0),
            })
        mistakes_top_items.sort(key=lambda x: (int(x.get('times') or 0), int(x.get('count') or 0)), reverse=True)
        mistakes_top_items = mistakes_top_items[:12]

        favorites_top_items = []
        for r in pub_fav_subject:
            favorites_top_items.append({'name': r._mapping['name'], 'source': 'public', 'count': int(r.get('count') or 0)})
        for r in (bank_fav_rank or [])[:12]:
            if int(r.get('count') or 0) <= 0:
                continue
            favorites_top_items.append({
                'name': r._mapping['name'],
                'source': 'banks',
                'count': int(r.get('count') or 0),
                'bank_id': int(r.get('bank_id') or 0),
            })
        favorites_top_items.sort(key=lambda x: int(x.get('count') or 0), reverse=True)
        favorites_top_items = favorites_top_items[:12]
    except Exception as e:
        current_app.logger.warning(f"data portal rank failed: {e}")
        mistakes_top_items = []
        favorites_top_items = []

    # ---------- 列表：个人题库错题/收藏（用于页面“最新/高频”展示） ----------
    try:
        if bank_ids_active:
            # 错题：按错题次数/最近更新
            try:
                ubm_has_wrong_count = _column_exists('user_bank_mistakes', 'wrong_count')
                ubm_has_updated_at = _column_exists('user_bank_mistakes', 'updated_at')
                order_by = "m.created_at DESC"
                if ubm_has_wrong_count:
                    order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC" if ubm_has_updated_at else "m.wrong_count DESC, m.created_at DESC"

                bid_in = ','.join(f':bid_{i}' for i in range(len(bank_ids_active)))
                sql = f"""
                     SELECT
                       b.id AS bank_id,
                       b.name AS bank_name,
                      COALESCE(q.type, 'unknown') AS p_type,
                       q.id AS question_id,
                       q.content AS content,
                       q.difficulty AS difficulty,
                       m.created_at AS created_at
                       {', m.wrong_count AS wrong_count' if ubm_has_wrong_count else ''}
                    FROM user_bank_mistakes m
                    JOIN user_bank_questions q ON m.question_id = q.id
                    JOIN user_question_banks b ON m.bank_id = b.id
                    WHERE m.user_id = :uid
                      AND b.id IN ({bid_in})
                      AND b.status = 1
                    ORDER BY {order_by}
                    LIMIT 8
                """
                bid_params = {f'bid_{i}': v for i, v in enumerate(bank_ids_active)}
                bid_params['uid'] = int(uid)
                rows = db.session.execute(text(sql), bid_params).fetchall()
                recent_mistakes_bank = []
                for r in rows or []:
                     content = (r._mapping['content'] or '').strip().replace('\r', ' ').replace('\n', ' ')
                     snippet = content[:80] + ('...' if len(content) > 80 else '')
                     recent_mistakes_bank.append({
                         'bank_id': int(r._mapping['bank_id'] or 0),
                         'bank_name': r._mapping['bank_name'] or '',
                        'q_type': _pt_to_qt(r._mapping['p_type']),
                         'question_id': int(r._mapping['question_id'] or 0),
                         'snippet': snippet,
                         'difficulty': int(r._mapping['difficulty'] or 1),
                         'wrong_count': int(r._mapping['wrong_count'] or 1) if ubm_has_wrong_count else None,
                     })
            except Exception:
                recent_mistakes_bank = []

            # 收藏：按最新收藏
            try:
                bid_in = ','.join(f':bid_{i}' for i in range(len(bank_ids_active)))
                sql = f"""
                     SELECT
                       b.id AS bank_id,
                       b.name AS bank_name,
                      COALESCE(q.type, 'unknown') AS p_type,
                       q.id AS question_id,
                       q.content AS content,
                       q.difficulty AS difficulty,
                       f.created_at AS created_at
                    FROM user_bank_favorites f
                    JOIN user_bank_questions q ON f.question_id = q.id
                    JOIN user_question_banks b ON f.bank_id = b.id
                    WHERE f.user_id = :uid
                      AND b.id IN ({bid_in})
                      AND b.status = 1
                    ORDER BY f.created_at DESC
                    LIMIT 8
                """
                bid_params = {f'bid_{i}': v for i, v in enumerate(bank_ids_active)}
                bid_params['uid'] = int(uid)
                rows = db.session.execute(text(sql), bid_params).fetchall()
                recent_favorites_bank = []
                for r in rows or []:
                     content = (r._mapping['content'] or '').strip().replace('\r', ' ').replace('\n', ' ')
                     snippet = content[:80] + ('...' if len(content) > 80 else '')
                     recent_favorites_bank.append({
                         'bank_id': int(r._mapping['bank_id'] or 0),
                         'bank_name': r._mapping['bank_name'] or '',
                        'q_type': _pt_to_qt(r._mapping['p_type']),
                         'question_id': int(r._mapping['question_id'] or 0),
                         'snippet': snippet,
                         'difficulty': int(r._mapping['difficulty'] or 1),
                     })
            except Exception:
                recent_favorites_bank = []
    except Exception as e:
        current_app.logger.warning(f"data portal recent list failed: {e}")
        recent_mistakes_bank = []
        recent_favorites_bank = []

    # 公共收藏：最新
    try:
        fav_sql = """
             SELECT
               COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.type, 'unknown') AS p_type,
               q.id AS question_id,
               q.content AS content,
               q.difficulty AS difficulty,
               f.created_at AS created_at
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = :uid AND (s.is_locked=false OR s.is_locked IS NULL)
        """
        fav_params = {'uid': int(uid)}
        if subject_ids:
            sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
            fav_sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
            fav_params.update(sid_params)
        fav_sql += " ORDER BY f.created_at DESC LIMIT 8"
        rows = db.session.execute(text(fav_sql), fav_params).fetchall()
        recent_favorites_public = []
        for r in rows or []:
            content = (r._mapping['content'] or '').strip().replace('\r', ' ').replace('\n', ' ')
            snippet = content[:80] + ('...' if len(content) > 80 else '')
            recent_favorites_public.append({
                'subject': r._mapping['subject'] or '未分类',
                'q_type': _pt_to_qt(r._mapping['p_type']),
                'question_id': int(r._mapping['question_id'] or 0),
                'snippet': snippet,
                'difficulty': int(r._mapping['difficulty'] or 1),
            })
    except Exception:
        recent_favorites_public = []

    # ---------- 标签：公共题库（用户私有标签系统） ----------
    try:
        from app.modules.quiz.services import question_tags_service as _qts

        store = _qts.load_store(db.session, int(uid))
        bindings = store.get('bindings') if isinstance(store.get('bindings'), dict) else {}

        qid_to_tags = {}
        raw_qids = []
        for qid, tag_list in (bindings or {}).items():
            if not isinstance(tag_list, list) or not tag_list:
                continue
            try:
                qid_i = int(qid)
            except Exception:
                continue
            tags = []
            for t in tag_list:
                name = (t or '').strip()
                if not name or name.lower() == 'all':
                    continue
                if name not in tags:
                    tags.append(name)
            if not tags:
                continue
            qid_to_tags[qid_i] = tags
            raw_qids.append(qid_i)

        raw_qids = sorted(set(raw_qids))

        # 过滤锁定/无权限科目
        pub_qids = []
        if raw_qids:
            for chunk in _chunks(raw_qids):
                chunk_params = {f"qid_{i}": v for i, v in enumerate(chunk)}
                sql = f"""
                    SELECT q.id AS id
                    FROM questions q
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE q.id IN ({','.join(f':qid_{i}' for i in range(len(chunk)))})
                      AND (s.is_locked=false OR s.is_locked IS NULL)
                """
                params = dict(chunk_params)
                if subject_ids:
                    sid_params = {f"sid_{i}": v for i, v in enumerate(subject_ids)}
                    sql += f" AND q.subject_id IN ({','.join(f':sid_{i}' for i in range(len(subject_ids)))})"
                    params.update(sid_params)
                rows = db.session.execute(text(sql), params).fetchall()
                for r in rows or []:
                    if r and r._mapping['id'] is not None:
                        pub_qids.append(int(r._mapping['id']))

        pub_qids = sorted(set(pub_qids))
        pub_qid_set = set(pub_qids)

        # 预加载：答题/收藏/错题（按 question_id）
        ua_map = {}
        fav_set = set()
        mis_times = {}

        if pub_qids:
            for chunk in _chunks(pub_qids):
                chunk_params = {f"p_{i}": v for i, v in enumerate(chunk)}
                chunk_params["uid"] = int(uid)
                chunk_in = ",".join(f":p_{i}" for i in range(len(chunk)))

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid, is_correct AS is_correct FROM user_answers WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        ua_map[int(r._mapping["qid"])] = 1 if int(r._mapping["is_correct"] or 0) == 1 else 0

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid FROM favorites WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        fav_set.add(int(r._mapping["qid"]))

                if mistakes_has_wrong_count:
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid, wrong_count AS wrong_count FROM mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                mis_times[int(r._mapping["qid"])] = _safe_int(r._mapping["wrong_count"], 1)
                else:
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid FROM mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                mis_times[int(r._mapping["qid"])] = 1

        # 聚合标签
        pub_stats = {}
        pub_tagged_questions = 0
        pub_tagged_answered = 0
        for qid, tags in qid_to_tags.items():
            if qid not in pub_qid_set:
                continue
            pub_tagged_questions += 1
            answered = qid in ua_map
            if answered:
                pub_tagged_answered += 1
            is_correct = ua_map.get(qid)
            is_fav = qid in fav_set
            wrong_times = int(mis_times.get(qid) or 0)

            for t in tags:
                it = pub_stats.get(t)
                if not it:
                    it = {'tag': t, 'count': 0, 'answered': 0, 'correct': 0, 'favorites': 0, 'mistakes': 0, 'mistakes_times': 0}
                    pub_stats[t] = it
                it['count'] += 1
                if answered:
                    it['answered'] += 1
                    if int(is_correct or 0) == 1:
                        it['correct'] += 1
                if is_fav:
                    it['favorites'] += 1
                if wrong_times:
                    it['mistakes'] += 1
                    it['mistakes_times'] += wrong_times

        tags_public = []
        for it in pub_stats.values():
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            it['accuracy'] = round(cor * 100.0 / ans, 1) if ans > 0 else 0.0
            tags_public.append(it)
        tags_public.sort(key=lambda x: (int(x.get('count') or 0), int(x.get('answered') or 0)), reverse=True)

        tags_kpis['public_tag_count'] = int(len([t for t in tags_public if int(t.get('count') or 0) > 0]))
        tags_kpis['public_tagged_questions'] = int(pub_tagged_questions)
        answered_total = int(all_summary.get('answered') or 0)
        tags_kpis['tagged_answered_coverage'] = round(int(pub_tagged_answered) * 100.0 / answered_total, 1) if answered_total > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"data portal public tags failed: {e}")
        tags_public = []

    # ---------- 标签：个人题库（bank_<id>_tags）+ 合并 ----------
    try:
        bank_qid_to_tags = {}
        bank_raw_qids = set()

        if bank_ids_active:
            from app.modules.user_bank.routes.api import _load_bank_tag_store as _load_bank_store

            for bid in bank_ids_active:
                try:
                    store2 = _load_bank_store(db.session, int(bid), int(uid)) or {}
                except Exception:
                    store2 = {}
                qtags = store2.get('question_tags') if isinstance(store2.get('question_tags'), dict) else {}
                for qid, tag_list in (qtags or {}).items():
                    if not isinstance(tag_list, list) or not tag_list:
                        continue
                    try:
                        qid_i = int(qid)
                    except Exception:
                        continue
                    tags = []
                    for t in tag_list:
                        name = (t or '').strip()
                        if not name or name.lower() == 'all':
                            continue
                        if name not in tags:
                            tags.append(name)
                    if not tags:
                        continue
                    bank_qid_to_tags[qid_i] = tags
                    bank_raw_qids.add(qid_i)

        bank_raw_qids = sorted(bank_raw_qids)
        bank_qids = []
        if bank_raw_qids and bank_ids_active:
            for chunk in _chunks(bank_raw_qids):
                chunk_params = {f"p_{i}": v for i, v in enumerate(chunk)}
                bid_params = {f"bid_{i}": v for i, v in enumerate(bank_ids_active)}
                chunk_params.update(bid_params)
                chunk_in = ",".join(f":p_{i}" for i in range(len(chunk)))
                bid_in = ",".join(f":bid_{i}" for i in range(len(bank_ids_active)))
                sql = f"SELECT id FROM user_bank_questions WHERE id IN ({chunk_in}) AND bank_id IN ({bid_in})"
                rows = db.session.execute(text(sql), chunk_params).fetchall()
                for r in rows or []:
                    if r and r._mapping['id'] is not None:
                        bank_qids.append(int(r._mapping['id']))

        bank_qids = sorted(set(bank_qids))
        bank_qid_set = set(bank_qids)

        ub_ans_map = {}
        ub_fav_set = set()
        ub_mis_times = {}

        if bank_qids:
            for chunk in _chunks(bank_qids):
                chunk_params = {f"p_{i}": v for i, v in enumerate(chunk)}
                chunk_params["uid"] = int(uid)
                chunk_in = ",".join(f":p_{i}" for i in range(len(chunk)))

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid, is_correct AS is_correct FROM user_bank_answers WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        ub_ans_map[int(r._mapping["qid"])] = 1 if int(r._mapping["is_correct"] or 0) == 1 else 0

                rows = db.session.execute(
                    text(f"SELECT question_id AS qid FROM user_bank_favorites WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                    chunk_params,
                ).fetchall()
                for r in rows or []:
                    if r and r._mapping["qid"] is not None:
                        ub_fav_set.add(int(r._mapping["qid"]))

                if _column_exists("user_bank_mistakes", "wrong_count"):
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid, wrong_count AS wrong_count FROM user_bank_mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                ub_mis_times[int(r._mapping["qid"])] = _safe_int(r._mapping["wrong_count"], 1)
                else:
                    rows = db.session.execute(
                            text(f"SELECT question_id AS qid FROM user_bank_mistakes WHERE user_id=:uid AND question_id IN ({chunk_in})"),
                            chunk_params,
                    ).fetchall()
                    for r in rows or []:
                            if r and r._mapping["qid"] is not None:
                                ub_mis_times[int(r._mapping["qid"])] = 1

        bank_stats = {}
        banks_tagged_questions = 0
        banks_tagged_answered = 0
        for qid, tags in bank_qid_to_tags.items():
            if qid not in bank_qid_set:
                continue
            banks_tagged_questions += 1
            answered = qid in ub_ans_map
            if answered:
                banks_tagged_answered += 1
            is_correct = ub_ans_map.get(qid)
            is_fav = qid in ub_fav_set
            wrong_times = int(ub_mis_times.get(qid) or 0)

            for t in tags:
                it = bank_stats.get(t)
                if not it:
                    it = {'tag': t, 'count': 0, 'answered': 0, 'correct': 0, 'favorites': 0, 'mistakes': 0, 'mistakes_times': 0}
                    bank_stats[t] = it
                it['count'] += 1
                if answered:
                    it['answered'] += 1
                    if int(is_correct or 0) == 1:
                        it['correct'] += 1
                if is_fav:
                    it['favorites'] += 1
                if wrong_times:
                    it['mistakes'] += 1
                    it['mistakes_times'] += wrong_times

        tags_banks = []
        for it in bank_stats.values():
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            it['accuracy'] = round(cor * 100.0 / ans, 1) if ans > 0 else 0.0
            tags_banks.append(it)
        tags_banks.sort(key=lambda x: (int(x.get('count') or 0), int(x.get('answered') or 0)), reverse=True)

        # 合并公共+个人
        all_stats = {}
        for src in (tags_public or []):
            t = src.get('tag')
            if t:
                all_stats[t] = dict(src)
        for src in (tags_banks or []):
            t = src.get('tag')
            if not t:
                continue
            it = all_stats.get(t)
            if not it:
                all_stats[t] = dict(src)
                continue
            for k in ('count', 'answered', 'correct', 'favorites', 'mistakes', 'mistakes_times'):
                it[k] = int(it.get(k) or 0) + int(src.get(k) or 0)
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            it['accuracy'] = round(cor * 100.0 / ans, 1) if ans > 0 else 0.0
        tags_all = list(all_stats.values())
        tags_all.sort(key=lambda x: (int(x.get('count') or 0), int(x.get('answered') or 0)), reverse=True)

        # KPI
        tags_kpis['banks_tag_count'] = int(len([t for t in tags_banks if int(t.get('count') or 0) > 0]))
        tags_kpis['all_tag_count'] = int(len([t for t in tags_all if int(t.get('count') or 0) > 0]))
        tags_kpis['banks_tagged_questions'] = int(banks_tagged_questions)
        tags_kpis['all_tagged_questions'] = int(tags_kpis.get('public_tagged_questions') or 0) + int(banks_tagged_questions)

        answered_total = int(all_summary.get('answered') or 0)
        tags_kpis['tagged_answered_coverage'] = round((int(pub_tagged_answered) + int(banks_tagged_answered)) * 100.0 / answered_total, 1) if answered_total > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"data portal bank tags failed: {e}")
        tags_banks = []
        tags_all = []

    # ---------- 标签图：共现网络（高端可视化） ----------
    try:
        _qid_to_tags = locals().get('qid_to_tags') if isinstance(locals().get('qid_to_tags'), dict) else {}
        _pub_qid_set = locals().get('pub_qid_set') if isinstance(locals().get('pub_qid_set'), set) else set()
        _bank_qid_to_tags = locals().get('bank_qid_to_tags') if isinstance(locals().get('bank_qid_to_tags'), dict) else {}
        _bank_qid_set = locals().get('bank_qid_set') if isinstance(locals().get('bank_qid_set'), set) else set()

        cooc_map = {}
        for qid, tl in (_qid_to_tags or {}).items():
            if _pub_qid_set and qid not in _pub_qid_set:
                continue
            if isinstance(tl, list) and tl:
                cooc_map[f'p{qid}'] = tl
        for qid, tl in (_bank_qid_to_tags or {}).items():
            if _bank_qid_set and qid not in _bank_qid_set:
                continue
            if isinstance(tl, list) and tl:
                cooc_map[f'b{qid}'] = tl

        pair = {}
        for _k, tl in (cooc_map or {}).items():
            if not isinstance(tl, list):
                continue
            uniq = []
            for t in tl:
                if t and t not in uniq:
                    uniq.append(t)
            if len(uniq) < 2:
                continue
            uniq = sorted(uniq)[:12]
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    kk = (uniq[i], uniq[j])
                    pair[kk] = pair.get(kk, 0) + 1

        links = [{'source': a, 'target': b, 'value': int(v)} for (a, b), v in pair.items() if int(v) > 0]
        links.sort(key=lambda x: int(x.get('value') or 0), reverse=True)
        links = links[:56]

        node_names = set()
        for l in links:
            node_names.add(l['source'])
            node_names.add(l['target'])

        count_map = {t.get('tag'): int(t.get('count') or 0) for t in (tags_all or []) if t.get('tag')}
        nodes = [{'name': name, 'value': int(count_map.get(name) or 1)} for name in node_names]
        nodes.sort(key=lambda x: int(x.get('value') or 0), reverse=True)
        tags_graph = {'nodes': nodes[:40], 'links': links}
    except Exception as e:
        current_app.logger.warning(f"data portal tag graph failed: {e}")
        tags_graph = {'nodes': [], 'links': []}

    # ---------- 全局洞察：大局观摘要（用于全局子页面） ----------
    try:
        insights = []

        # 近窗最活跃小时
        try:
            best = None
            for it in (hourly.get('all') or []):
                if not it:
                    continue
                if best is None or int(it.get('total') or 0) > int(best.get('total') or 0):
                    best = it
            if best and int(best.get('total') or 0) > 0:
                h = int(best.get('hour') or 0)
                insights.append({'title': '最活跃时段', 'value': f'{h:02d}:00', 'hint': f"近 {window_days} 天答题 {int(best.get('total') or 0)}"})
        except Exception:
            pass

        # 近窗最活跃周几
        try:
            wk = [0] * 7
            for cell in (heatmap.get('all') or []):
                if not cell or len(cell) < 3:
                    continue
                wd = int(cell[0] or 0)
                wk[wd] += int(cell[2] or 0)
            max_wd = max(range(7), key=lambda i: wk[i])
            if wk[max_wd] > 0:
                names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
                insights.append({'title': '高频日', 'value': names[max_wd], 'hint': f"近 {window_days} 天答题 {wk[max_wd]}"})
        except Exception:
            pass

        # 最大风险点
        try:
            w0 = (weakness_rows or [None])[0]
            if w0:
                insights.append({'title': '优先补短板', 'value': f"{w0.get('subject')}·{w0.get('q_type')}", 'hint': f"正确率 {w0.get('accuracy')}% · 错题 {w0.get('mistakes')}"})
        except Exception:
            pass

        # 进度 / 健康
        insights.append({'title': '学习健康分', 'value': f'{health_score} / 100', 'hint': '覆盖×正确×连续×错题治理'})

        global_insights = insights[:4]
    except Exception:
        global_insights = []

    return {
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
        'global_insights': global_insights,
        'mistakes_daily': mistakes_daily,
        'favorites_daily': favorites_daily,
        'mistakes_by_type': mistakes_by_type,
        'mistakes_by_difficulty': mistakes_by_difficulty,
        'favorites_by_type': favorites_by_type,
        'favorites_by_difficulty': favorites_by_difficulty,
        'mistakes_top_items': mistakes_top_items,
        'favorites_top_items': favorites_top_items,
        'recent_mistakes_bank': recent_mistakes_bank,
        'recent_favorites_bank': recent_favorites_bank,
        'recent_favorites_public': recent_favorites_public,
        'tags_public': tags_public,
        'tags_banks': tags_banks,
        'tags_all': tags_all,
        'tags_graph': tags_graph,
        'tags_kpis': tags_kpis,
    }
