# -*- coding: utf-8 -*-
"""数据中心扩展上下文 — 统计段：趋势/维度/排行/列表（从 data_center_context_extra.py 拆分）"""
from flask import current_app
from sqlalchemy import text

from app.core.extensions import db


def compute_extra_stats(uid: int, window_days: int, subject_ids: list,
                        bank_ids_active: list, bank_rows: list,
                        mistakes_has_wrong_count: bool,
                        _pt_to_qt, _date_keys, _window_start, _safe_int,
                        _column_exists) -> dict:
    """计算趋势/维度/排行/列表数据。"""
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
            mistakes_top_items.append({'name': r['name'], 'source': 'public', 'count': int(r.get('count') or 0), 'times': int(r.get('times') or 0)})
        for r in (bank_mis_rank or [])[:12]:
            if int(r.get('times') or 0) <= 0 and int(r.get('count') or 0) <= 0:
                continue
            mistakes_top_items.append({
                'name': r['name'],
                'source': 'banks',
                'count': int(r.get('count') or 0),
                'times': int(r.get('times') or 0),
                'bank_id': int(r.get('bank_id') or 0),
            })
        mistakes_top_items.sort(key=lambda x: (int(x.get('times') or 0), int(x.get('count') or 0)), reverse=True)
        mistakes_top_items = mistakes_top_items[:12]

        favorites_top_items = []
        for r in pub_fav_subject:
            favorites_top_items.append({'name': r['name'], 'source': 'public', 'count': int(r.get('count') or 0)})
        for r in (bank_fav_rank or [])[:12]:
            if int(r.get('count') or 0) <= 0:
                continue
            favorites_top_items.append({
                'name': r['name'],
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

    # ---------- 列表：个人题库错题/收藏（用于页面"最新/高频"展示） ----------
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

return {
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
}
