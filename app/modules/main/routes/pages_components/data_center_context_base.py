# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from flask import current_app

from app.core.utils.database import get_db
from app.core.utils.time_utils import today_bj

from .common import _get_accessible_subject_rows

def compute_data_center_context_base(uid: int, window_days: int):
    """数据中心：计算基础上下文（返回 conn, subject_ids, base_ctx）。"""
    uid = int(uid or 0)
    conn = get_db()
    from app.core.utils.portable_question_format import portable_type_to_q_type

    def _pt_to_qt(pt: str) -> str:
        pt = str(pt or '').strip()
        if not pt or pt == 'unknown':
            return '未知'
        return portable_type_to_q_type(pt) or '未知'

    def _column_exists(table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    subjects_meta = _get_accessible_subject_rows(conn, uid)
    subject_ids = [
        int(s['id'])
        for s in (subjects_meta or [])
        if s and s.get('id') is not None
    ]

    # 公共题库总题数（按权限与锁定过滤）
    total_questions = 0
    try:
        base_sql = """
            SELECT COUNT(*)
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = []
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            base_sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(subject_ids)
        total_questions = conn.execute(base_sql, params).fetchone()[0]
    except Exception:
        total_questions = 0

    # 复用 join + 权限过滤（公共题库）
    ua_from = """
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE ua.user_id = ?
          AND (s.is_locked=0 OR s.is_locked IS NULL)
    """
    ua_params_base = [uid]
    if subject_ids:
        placeholders = ','.join(['?'] * len(subject_ids))
        ua_from += f" AND q.subject_id IN ({placeholders})"
        ua_params_base.extend(subject_ids)

    # 全局汇总（公共题库）
    answered_count = 0
    correct_count = 0
    last_activity = None
    try:
        row = conn.execute(
            f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
              MAX(ua.created_at) AS last_activity
            {ua_from}
            """,
            ua_params_base,
        ).fetchone()
        answered_count = int(row['answered'] or 0) if row else 0
        correct_count = int(row['correct'] or 0) if row else 0
        last_activity = (row['last_activity'] if row else None) or None
    except Exception:
        answered_count = 0
        correct_count = 0
        last_activity = None

    accuracy = round(correct_count * 100 / answered_count, 1) if answered_count > 0 else 0.0
    completion = round(answered_count * 100 / total_questions, 1) if total_questions > 0 else 0.0

    # 收藏/错题（公共题库）
    favorites_count = 0
    mistakes_count = 0
    mistakes_times = 0  # 若存在 wrong_count 则为累计次数，否则退化为 mistakes_count
    try:
        fav_sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        fav_params = [uid]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            fav_sql += f" AND q.subject_id IN ({placeholders})"
            fav_params.extend(subject_ids)
        favorites_count = conn.execute(fav_sql, fav_params).fetchone()[0]
    except Exception:
        favorites_count = 0

    mistakes_has_wrong_count = _column_exists('mistakes', 'wrong_count')
    mistakes_has_updated_at = _column_exists('mistakes', 'updated_at')
    try:
        mis_sql = """
            SELECT
              COUNT(*) AS cnt,
              SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        mis_params = [uid]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            mis_sql += f" AND q.subject_id IN ({placeholders})"
            mis_params.extend(subject_ids)
        if not mistakes_has_wrong_count:
            mis_sql = mis_sql.replace("m.wrong_count", "NULL")
        row = conn.execute(mis_sql, mis_params).fetchone()
        mistakes_count = int(row['cnt'] or 0) if row else 0
        mistakes_times = int(row['times'] or 0) if row else 0
        if not mistakes_has_wrong_count:
            mistakes_times = mistakes_count
    except Exception:
        mistakes_count = 0
        mistakes_times = 0

    # 连续学习天数（基于 user_answers 的 DATE(created_at)）
    streak_days = 0
    public_streak_dates = []
    try:
        rows = conn.execute(
            f"SELECT DISTINCT DATE(ua.created_at) AS day {ua_from} ORDER BY day DESC LIMIT 120",
            ua_params_base,
        ).fetchall()
        dates = []
        for r in rows or []:
            if r and r['day']:
                try:
                    dates.append(datetime.strptime(r['day'], '%Y-%m-%d').date())
                except Exception:
                    continue
        public_streak_dates = dates
        today = today_bj()
        if dates and dates[0] >= (today - timedelta(days=1)):
            streak_days = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    streak_days += 1
                else:
                    break
    except Exception:
        streak_days = 0
        public_streak_dates = []

    def _count_since(days: int) -> tuple[int, int]:
        if days <= 0:
            return answered_count, correct_count
        try:
            row = conn.execute(
                f"""
                SELECT
                  COUNT(*) AS answered,
                  SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                {ua_from}
                  AND ua.created_at >= datetime('now', '+8 hours', ?)
                """,
                ua_params_base + [f'-{days} days'],
            ).fetchone()
            return int(row['answered'] or 0), int(row['correct'] or 0)
        except Exception:
            return 0, 0

    answered_7d, correct_7d = _count_since(7)
    answered_30d, correct_30d = _count_since(30)

    # 趋势窗口（只影响趋势图展示）
    try:
        window_days = int(window_days)
    except Exception:
        window_days = 30
    if window_days not in (7, 30, 90):
        window_days = 30

    daily = []
    daily_max = 0
    window_answered = 0
    window_correct = 0
    window_accuracy = 0.0
    try:
        rows = conn.execute(
            f"""
            SELECT
              DATE(ua.created_at) AS day,
              COUNT(*) AS total,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
              AND ua.created_at >= datetime('now', '+8 hours', ?)
            GROUP BY DATE(ua.created_at)
            ORDER BY day
            """,
            ua_params_base + [f'-{window_days} days'],
        ).fetchall()
        data_map = {r['day']: {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in (rows or []) if r and r['day']}

        today = today_bj()
        start = today - timedelta(days=window_days - 1)
        for i in range(window_days):
            d = start + timedelta(days=i)
            key = d.strftime('%Y-%m-%d')
            total = int((data_map.get(key) or {}).get('total', 0))
            correct = int((data_map.get(key) or {}).get('correct', 0))
            acc = round(correct * 100 / total, 1) if total > 0 else 0.0
            daily_max = max(daily_max, total)
            daily.append({'day': key, 'total': total, 'correct': correct, 'accuracy': acc})

        window_answered = sum(int(x.get('total', 0) or 0) for x in daily)
        window_correct = sum(int(x.get('correct', 0) or 0) for x in daily)
        window_accuracy = round(window_correct * 100 / window_answered, 1) if window_answered > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"history daily stats failed: {e}")
        daily = []
        daily_max = 0
        window_answered = 0
        window_correct = 0
        window_accuracy = 0.0

    # 科目维度（公共题库）
    subject_rows = []
    try:
        # 总题数（每科目）
        total_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS total
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                subject_ids,
            ).fetchall()
            total_map = {int(r['subject_id']): int(r['total'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

        # 已做/正确（每科目）
        ans_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id,
                       COUNT(*) AS answered,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE ua.user_id = ?
                  AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            ans_map = {
                int(r['subject_id']): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
                for r in (rows or [])
                if r and r['subject_id'] is not None
            }

        # 错题/收藏（每科目）
        mis_map = {}
        fav_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            mis_map = {int(r['subject_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            fav_map = {int(r['subject_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

        for s in subjects_meta or []:
            sid = int(s['id'])
            total = int(total_map.get(sid, 0))
            answered = int((ans_map.get(sid) or {}).get('answered', 0))
            correct = int((ans_map.get(sid) or {}).get('correct', 0))
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            comp = round(answered * 100 / total, 1) if total > 0 else 0.0
            subject_rows.append({
                'subject_id': sid,
                'subject': s['name'],
                'total': total,
                'answered': answered,
                'correct': correct,
                'accuracy': acc,
                'completion': comp,
                'mistakes': int(mis_map.get(sid, 0)),
                'favorites': int(fav_map.get(sid, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history subject stats failed: {e}")
        subject_rows = []

    # 题型维度（公共题库）
    type_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(q.type, 'unknown') AS p_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.type
            ORDER BY answered DESC
            """,
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            type_rows.append({
                'q_type': _pt_to_qt(r['p_type']),
                'answered': answered,
                'correct': correct,
                'accuracy': round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history type stats failed: {e}")
        type_rows = []

    # 难度维度（公共题库）
    difficulty_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(q.difficulty, 1) AS difficulty,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.difficulty
            ORDER BY difficulty ASC
            """,
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            diff = int(r['difficulty'] or 1)
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            label = {1: '简单', 2: '中等', 3: '困难'}.get(diff, f'难度{diff}')
            difficulty_rows.append({
                'difficulty': diff,
                'label': label,
                'answered': answered,
                'correct': correct,
                'accuracy': round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history difficulty stats failed: {e}")
        difficulty_rows = []

    # 薄弱点：科目 × 题型（公共题库）
    weakness_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.type, 'unknown') AS p_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY s.name, q.type
            HAVING answered >= 5
            ORDER BY (correct * 1.0 / answered) ASC, answered DESC
            LIMIT 8
            """,
            ua_params_base,
        ).fetchall()

        # 错题分布（用于提示强弱）
        mis_rows = conn.execute(
            f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.type, 'unknown') AS p_type,
              COUNT(*) AS mistakes
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            {('AND q.subject_id IN (' + ','.join(['?']*len(subject_ids)) + ')') if subject_ids else ''}
            GROUP BY s.name, q.type
            """,
            [uid] + (subject_ids if subject_ids else []),
        ).fetchall()
        mis_map = {
            (r['subject'] or '未分类', _pt_to_qt(r['p_type'])): int(r['mistakes'] or 0)
            for r in (mis_rows or [])
            if r
        }

        for r in rows or []:
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            qtype_disp = _pt_to_qt(r['p_type'])
            key = (r['subject'] or '未分类', qtype_disp)
            weakness_rows.append({
                'subject': r['subject'] or '未分类',
                'q_type': qtype_disp,
                'answered': answered,
                'correct': correct,
                'accuracy': acc,
                'mistakes': int(mis_map.get(key, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history weakness stats failed: {e}")
        weakness_rows = []

    # 最近错题（公共题库）
    recent_mistakes = []
    try:
        order_by = "m.created_at DESC"
        if mistakes_has_wrong_count:
            # 优先看错得多的题，其次最近更新
            order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC" if mistakes_has_updated_at else "m.wrong_count DESC, m.created_at DESC"
        sql = f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.type, 'unknown') AS p_type,
              q.id AS question_id,
              q.content AS content,
              q.difficulty AS difficulty,
              m.created_at AS created_at
              {', m.wrong_count AS wrong_count' if mistakes_has_wrong_count else ''}
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            {('AND q.subject_id IN (' + ','.join(['?']*len(subject_ids)) + ')') if subject_ids else ''}
            ORDER BY {order_by}
            LIMIT 8
        """
        rows = conn.execute(sql, [uid] + (subject_ids if subject_ids else [])).fetchall()
        for r in rows or []:
            content = (r['content'] or '').strip().replace('\r', ' ').replace('\n', ' ')
            snippet = content[:80] + ('…' if len(content) > 80 else '')
            recent_mistakes.append({
                'subject': r['subject'] or '未分类',
                'q_type': _pt_to_qt(r['p_type']),
                'question_id': int(r['question_id']),
                'snippet': snippet,
                'difficulty': int(r['difficulty'] or 1),
                'wrong_count': int(r['wrong_count'] or 1) if mistakes_has_wrong_count else None,
            })
    except Exception as e:
        current_app.logger.warning(f"history recent mistakes failed: {e}")
        recent_mistakes = []

    # 用于 UI 的“下一步建议”
    next_actions = []
    try:
        for w in (weakness_rows or [])[:3]:
            next_actions.append({
                'title': f"{w['subject']} · {w['q_type']}",
                'meta': f"正确率 {w['accuracy']}%（已做 {w['answered']}）",
                'subject': w['subject'],
                'q_type': w['q_type'],
            })
    except Exception:
        next_actions = []

    # ============================
    # 个人题库（我创建的题库）统计
    # ============================
    bank_rows = []
    bank_daily = []
    bank_daily_max = 0
    bank_streak_days = 0
    bank_streak_dates = []
    bank_last_activity = None
    bank_total_questions = 0
    bank_answered_count = 0
    bank_correct_count = 0
    bank_accuracy = 0.0
    bank_completion = 0.0
    bank_favorites_count = 0
    bank_mistakes_count = 0
    bank_mistakes_times = 0
    bank_total_banks = 0

    try:
        banks = conn.execute(
            """
            SELECT
              b.id AS id,
              b.name AS name,
              b.category_id AS category_id,
              COALESCE(c.name, '未分类') AS category_name
            FROM user_question_banks b
            LEFT JOIN user_bank_categories c ON b.category_id = c.id
            WHERE b.user_id = ? AND b.status = 1
            ORDER BY b.updated_at DESC, b.id DESC
            """,
            (int(uid),),
        ).fetchall()
        banks = [dict(b) for b in (banks or []) if b and b['id'] is not None]
        bank_total_banks = len(banks)
        bank_ids = [int(b['id']) for b in banks]

        if bank_ids:
            placeholders = ','.join(['?'] * len(bank_ids))

            # 题库题量（每题库）
            total_map = {}
            try:
                rows = conn.execute(
                    f"""
                    SELECT bank_id, COUNT(*) AS total
                    FROM user_bank_questions
                    WHERE bank_id IN ({placeholders})
                    GROUP BY bank_id
                    """,
                    bank_ids,
                ).fetchall()
                total_map = {int(r['bank_id']): int(r['total'] or 0) for r in (rows or []) if r and r['bank_id'] is not None}
            except Exception:
                total_map = {}

            # 已做/正确/最近活跃（每题库）
            ans_map = {}
            try:
                rows = conn.execute(
                    f"""
                    SELECT bank_id,
                           COUNT(*) AS answered,
                           SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct,
                           MAX(created_at) AS last_activity
                    FROM user_bank_answers
                    WHERE user_id = ?
                      AND bank_id IN ({placeholders})
                    GROUP BY bank_id
                    """,
                    [int(uid)] + bank_ids,
                ).fetchall()
                ans_map = {
                    int(r['bank_id']): {
                        'answered': int(r['answered'] or 0),
                        'correct': int(r['correct'] or 0),
                        'last_activity': (r['last_activity'] or None),
                    }
                    for r in (rows or [])
                    if r and r['bank_id'] is not None
                }
            except Exception:
                ans_map = {}

            # 收藏（每题库）
            fav_map = {}
            try:
                rows = conn.execute(
                    f"""
                    SELECT bank_id, COUNT(*) AS cnt
                    FROM user_bank_favorites
                    WHERE user_id = ?
                      AND bank_id IN ({placeholders})
                    GROUP BY bank_id
                    """,
                    [int(uid)] + bank_ids,
                ).fetchall()
                fav_map = {int(r['bank_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['bank_id'] is not None}
            except Exception:
                fav_map = {}

            # 错题（每题库）
            mis_map = {}
            try:
                rows = conn.execute(
                    f"""
                    SELECT bank_id,
                           COUNT(*) AS cnt,
                           SUM(COALESCE(wrong_count, 1)) AS times
                    FROM user_bank_mistakes
                    WHERE user_id = ?
                      AND bank_id IN ({placeholders})
                    GROUP BY bank_id
                    """,
                    [int(uid)] + bank_ids,
                ).fetchall()
                mis_map = {
                    int(r['bank_id']): {'cnt': int(r['cnt'] or 0), 'times': int(r['times'] or 0)}
                    for r in (rows or [])
                    if r and r['bank_id'] is not None
                }
            except Exception:
                mis_map = {}

            # 组装题库行
            for b in banks:
                bid = int(b['id'])
                total_n = int(total_map.get(bid, 0))
                ans = ans_map.get(bid) or {}
                answered_n = int(ans.get('answered', 0))
                correct_n = int(ans.get('correct', 0))
                last_n = ans.get('last_activity')
                fav_n = int(fav_map.get(bid, 0))
                mis_n = int((mis_map.get(bid) or {}).get('cnt', 0))
                mis_times_n = int((mis_map.get(bid) or {}).get('times', 0))

                acc_n = round(correct_n * 100 / answered_n, 1) if answered_n > 0 else 0.0
                comp_n = round(answered_n * 100 / total_n, 1) if total_n > 0 else 0.0

                bank_rows.append({
                    'bank_id': bid,
                    'name': (b.get('name') or '').strip() or f'题库 {bid}',
                    'category_id': int(b.get('category_id') or 0),
                    'category_name': (b.get('category_name') or '').strip() or '未分类',
                    'total': total_n,
                    'answered': answered_n,
                    'correct': correct_n,
                    'accuracy': acc_n,
                    'completion': comp_n,
                    'favorites': fav_n,
                    'mistakes': mis_n,
                    'mistakes_times': mis_times_n,
                    'last_activity': last_n,
                })

            bank_total_questions = int(sum(int(r.get('total') or 0) for r in bank_rows))
            bank_answered_count = int(sum(int(r.get('answered') or 0) for r in bank_rows))
            bank_correct_count = int(sum(int(r.get('correct') or 0) for r in bank_rows))
            bank_favorites_count = int(sum(int(r.get('favorites') or 0) for r in bank_rows))
            bank_mistakes_count = int(sum(int(r.get('mistakes') or 0) for r in bank_rows))
            bank_mistakes_times = int(sum(int(r.get('mistakes_times') or 0) for r in bank_rows))

            bank_accuracy = round(bank_correct_count * 100 / bank_answered_count, 1) if bank_answered_count > 0 else 0.0
            bank_completion = round(bank_answered_count * 100 / bank_total_questions, 1) if bank_total_questions > 0 else 0.0

            # 最近活跃（个人题库）
            try:
                bank_last_activity = max(
                    [r.get('last_activity') for r in bank_rows if r.get('last_activity')],
                    default=None,
                )
            except Exception:
                bank_last_activity = None

            # streak（个人题库）
            try:
                rows = conn.execute(
                    f"""
                    SELECT DISTINCT DATE(created_at) AS day
                    FROM user_bank_answers
                    WHERE user_id = ?
                      AND bank_id IN ({placeholders})
                    ORDER BY day DESC
                    LIMIT 120
                    """,
                    [int(uid)] + bank_ids,
                ).fetchall()
                dates = []
                for r in rows or []:
                    if r and r['day']:
                        try:
                            dates.append(datetime.strptime(r['day'], '%Y-%m-%d').date())
                        except Exception:
                            continue
                bank_streak_dates = dates
                today = today_bj()
                if dates and dates[0] >= (today - timedelta(days=1)):
                    bank_streak_days = 1
                    for i in range(1, len(dates)):
                        if dates[i - 1] - dates[i] == timedelta(days=1):
                            bank_streak_days += 1
                        else:
                            break
            except Exception:
                bank_streak_days = 0
                bank_streak_dates = []

            # 趋势（个人题库）
            try:
                rows = conn.execute(
                    f"""
                    SELECT
                      DATE(created_at) AS day,
                      COUNT(*) AS total,
                      SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct
                    FROM user_bank_answers
                    WHERE user_id = ?
                      AND bank_id IN ({placeholders})
                      AND created_at >= datetime('now', '+8 hours', ?)
                    GROUP BY DATE(created_at)
                    ORDER BY day
                    """,
                    [int(uid)] + bank_ids + [f'-{window_days} days'],
                ).fetchall()
                data_map = {r['day']: {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in (rows or []) if r and r['day']}

                today = today_bj()
                start = today - timedelta(days=window_days - 1)
                for i in range(window_days):
                    d = start + timedelta(days=i)
                    key = d.strftime('%Y-%m-%d')
                    item = data_map.get(key, {'total': 0, 'correct': 0})
                    total_n = int(item.get('total') or 0)
                    correct_n = int(item.get('correct') or 0)
                    acc_n = round(correct_n * 100 / total_n, 1) if total_n > 0 else 0.0
                    bank_daily_max = max(bank_daily_max, total_n)
                    bank_daily.append({'day': key, 'total': total_n, 'correct': correct_n, 'accuracy': acc_n})
            except Exception:
                bank_daily = []
                bank_daily_max = 0
    except Exception as e:
        current_app.logger.warning(f"data center bank stats failed: {e}")

    bank_summary = {
        'bank_total': int(bank_total_banks),
        'total_questions': int(bank_total_questions),
        'answered': int(bank_answered_count),
        'correct': int(bank_correct_count),
        'accuracy': float(bank_accuracy),
        'completion': float(bank_completion),
        'favorites': int(bank_favorites_count),
        'mistakes': int(bank_mistakes_count),
        'mistakes_times': int(bank_mistakes_times),
        'streak_days': int(bank_streak_days),
        'last_activity': bank_last_activity,
    }

    # ============================
    # 全局汇总（公共 + 个人）
    # ============================
    all_total_questions = int(total_questions or 0) + int(bank_total_questions or 0)
    all_answered_count = int(answered_count or 0) + int(bank_answered_count or 0)
    all_correct_count = int(correct_count or 0) + int(bank_correct_count or 0)
    all_favorites_count = int(favorites_count or 0) + int(bank_favorites_count or 0)
    all_mistakes_count = int(mistakes_count or 0) + int(bank_mistakes_count or 0)
    all_mistakes_times = int(mistakes_times or 0) + int(bank_mistakes_times or 0)
    all_accuracy = round(all_correct_count * 100 / all_answered_count, 1) if all_answered_count > 0 else 0.0
    all_completion = round(all_answered_count * 100 / all_total_questions, 1) if all_total_questions > 0 else 0.0

    all_last_activity = None
    try:
        candidates = [x for x in [last_activity, bank_last_activity] if x]
        all_last_activity = max(candidates) if candidates else None
    except Exception:
        all_last_activity = None

    # 全局 streak：合并公共 + 个人的活跃日期
    all_streak_days = 0
    try:
        merged_dates = sorted(set(public_streak_dates or []) | set(bank_streak_dates or []), reverse=True)
        today = today_bj()
        if merged_dates and merged_dates[0] >= (today - timedelta(days=1)):
            all_streak_days = 1
            for i in range(1, len(merged_dates)):
                if merged_dates[i - 1] - merged_dates[i] == timedelta(days=1):
                    all_streak_days += 1
                else:
                    break
    except Exception:
        all_streak_days = max(int(streak_days or 0), int(bank_streak_days or 0))

    # 全局趋势：按天叠加公共 daily + 个人 bank_daily
    all_daily = []
    all_daily_max = 0
    try:
        pub_map = {str(r.get('day')): r for r in (daily or []) if r and r.get('day')}
        bank_map = {str(r.get('day')): r for r in (bank_daily or []) if r and r.get('day')}
        keys = sorted(set(pub_map.keys()) | set(bank_map.keys()))
        for k in keys:
            p = pub_map.get(k) or {}
            b = bank_map.get(k) or {}
            total_n = int(p.get('total') or 0) + int(b.get('total') or 0)
            correct_n = int(p.get('correct') or 0) + int(b.get('correct') or 0)
            acc_n = round(correct_n * 100 / total_n, 1) if total_n > 0 else 0.0
            all_daily_max = max(all_daily_max, total_n)
            all_daily.append({'day': k, 'total': total_n, 'correct': correct_n, 'accuracy': acc_n})
    except Exception:
        all_daily = []
        all_daily_max = 0

    all_summary = {
        'total_questions': int(all_total_questions),
        'answered': int(all_answered_count),
        'correct': int(all_correct_count),
        'accuracy': float(all_accuracy),
        'completion': float(all_completion),
        'favorites': int(all_favorites_count),
        'mistakes': int(all_mistakes_count),
        'mistakes_times': int(all_mistakes_times),
        'streak_days': int(all_streak_days),
        'last_activity': all_last_activity,
    }

    # 预置建议：用于“未配置密钥/不点AI也能用”的体验兜底
    ai_seed_tips = []
    try:
        if all_total_questions <= 0:
            ai_seed_tips = [{'title': '暂无数据', 'content': '你还没有可统计的题库或答题记录，先去练习几题再回来看看。'}]
        else:
            if all_answered_count < 10:
                ai_seed_tips.append({'title': '先把“启动成本”打穿', 'content': '建议今天先连续做 20 题，先建立手感，再谈策略。'})
            if all_completion < 35:
                ai_seed_tips.append({'title': '提高覆盖率', 'content': '覆盖率偏低，优先把“未做题”补齐；每天固定 10~15 分钟更容易坚持。'})
            if all_accuracy < 65 and all_answered_count >= 10:
                ai_seed_tips.append({'title': '先错题闭环，再追速度', 'content': '正确率偏低时，先刷“错题”并总结错因，再回到全题库练习。'})
            if all_mistakes_times >= 20:
                ai_seed_tips.append({'title': '错题要复盘到“可复现”', 'content': '错题次数偏多，建议把高频错题做一次归因：概念不清/审题/计算/方法选择。'})
            if all_streak_days <= 1:
                ai_seed_tips.append({'title': '建立可持续节奏', 'content': '建议设一个“最小计划”：每天 10 题或 8 分钟，先保证不断更。'})
            if next_actions:
                ai_seed_tips.append({'title': '优先攻克薄弱点', 'content': f"先从「{next_actions[0]['title']}」开始，刷错题 + 重练 1 轮，最快见效。"})
    except Exception:
        ai_seed_tips = []

    # ===== 额外：题库分类聚合（个人题库）=====
    bank_category_rows = []
    try:
        cat_map = {}
        for r in (bank_rows or []):
            cid = int(r.get('category_id') or 0)
            cname = (r.get('category_name') or '').strip() or '未分类'
            it = cat_map.get(cid)
            if not it:
                it = {
                    'category_id': cid,
                    'category_name': cname,
                    'bank_count': 0,
                    'total': 0,
                    'answered': 0,
                    'correct': 0,
                    'accuracy': 0.0,
                    'completion': 0.0,
                    'favorites': 0,
                    'mistakes': 0,
                    'mistakes_times': 0,
                    'last_activity': None,
                }
                cat_map[cid] = it

            it['bank_count'] += 1
            it['total'] += int(r.get('total') or 0)
            it['answered'] += int(r.get('answered') or 0)
            it['correct'] += int(r.get('correct') or 0)
            it['favorites'] += int(r.get('favorites') or 0)
            it['mistakes'] += int(r.get('mistakes') or 0)
            it['mistakes_times'] += int(r.get('mistakes_times') or 0)
            la = r.get('last_activity')
            if la and (not it['last_activity'] or str(la) > str(it['last_activity'])):
                it['last_activity'] = la

        for it in cat_map.values():
            ans = int(it.get('answered') or 0)
            cor = int(it.get('correct') or 0)
            tot = int(it.get('total') or 0)
            it['accuracy'] = round(cor * 100 / ans, 1) if ans > 0 else 0.0
            it['completion'] = round(ans * 100 / tot, 1) if tot > 0 else 0.0

        bank_category_rows = sorted(list(cat_map.values()), key=lambda x: int(x.get('answered') or 0), reverse=True)
    except Exception:
        bank_category_rows = []

    # ===== 额外：活跃热力图（周×小时）与按小时分布（公共+个人）=====
    def _wk_idx(sql_w: int) -> int:
        # SQLite %w: 0=周日,1=周一,...6=周六  -> 0=周一,...6=周日
        w = int(sql_w or 0)
        return 6 if w == 0 else max(0, min(6, w - 1))

    hourly = {'max': 0, 'public': [], 'banks': [], 'all': []}
    heatmap = {'max': 0, 'public': [], 'banks': [], 'all': []}
    try:
        pub_hour = {}
        bank_hour = {}

        rows = conn.execute(
            f"""
            SELECT strftime('%H', ua.created_at) AS h,
                   COUNT(*) AS total,
                   SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
              AND ua.created_at >= datetime('now', '+8 hours', ?)
            GROUP BY h
            """,
            ua_params_base + [f'-{window_days} days'],
        ).fetchall()
        for r in rows or []:
            if not r or r.get('h') is None:
                continue
            h = int(str(r['h']))
            pub_hour[h] = {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)}

        rows = conn.execute(
            """
            SELECT strftime('%H', created_at) AS h,
                   COUNT(*) AS total,
                   SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_bank_answers
            WHERE user_id = ?
              AND created_at >= datetime('now', '+8 hours', ?)
            GROUP BY h
            """,
            [int(uid), f'-{window_days} days'],
        ).fetchall()
        for r in rows or []:
            if not r or r.get('h') is None:
                continue
            h = int(str(r['h']))
            bank_hour[h] = {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)}

        for h in range(24):
            p = pub_hour.get(h) or {}
            b = bank_hour.get(h) or {}
            pt = int(p.get('total') or 0)
            pc = int(p.get('correct') or 0)
            bt = int(b.get('total') or 0)
            bc = int(b.get('correct') or 0)
            at = pt + bt
            ac = pc + bc
            hourly['public'].append({'hour': h, 'total': pt, 'correct': pc, 'accuracy': round(pc * 100 / pt, 1) if pt > 0 else 0.0})
            hourly['banks'].append({'hour': h, 'total': bt, 'correct': bc, 'accuracy': round(bc * 100 / bt, 1) if bt > 0 else 0.0})
            hourly['all'].append({'hour': h, 'total': at, 'correct': ac, 'accuracy': round(ac * 100 / at, 1) if at > 0 else 0.0})
            hourly['max'] = max(int(hourly['max'] or 0), at)

        pub_hm = {}
        bank_hm = {}
        rows = conn.execute(
            f"""
            SELECT strftime('%w', ua.created_at) AS wd,
                   strftime('%H', ua.created_at) AS h,
                   COUNT(*) AS total
            {ua_from}
              AND ua.created_at >= datetime('now', '+8 hours', ?)
            GROUP BY wd, h
            """,
            ua_params_base + [f'-{window_days} days'],
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            wd = _wk_idx(int(r['wd'] or 0))
            h = int(str(r['h'] or 0))
            pub_hm[(wd, h)] = int(r['total'] or 0)

        rows = conn.execute(
            """
            SELECT strftime('%w', created_at) AS wd,
                   strftime('%H', created_at) AS h,
                   COUNT(*) AS total
            FROM user_bank_answers
            WHERE user_id = ?
              AND created_at >= datetime('now', '+8 hours', ?)
            GROUP BY wd, h
            """,
            [int(uid), f'-{window_days} days'],
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            wd = _wk_idx(int(r['wd'] or 0))
            h = int(str(r['h'] or 0))
            bank_hm[(wd, h)] = int(r['total'] or 0)

        for wd in range(7):
            for h in range(24):
                pv = int(pub_hm.get((wd, h), 0))
                bv = int(bank_hm.get((wd, h), 0))
                av = pv + bv
                if pv:
                    heatmap['public'].append([wd, h, pv])
                if bv:
                    heatmap['banks'].append([wd, h, bv])
                if av:
                    heatmap['all'].append([wd, h, av])
                heatmap['max'] = max(int(heatmap['max'] or 0), av)
    except Exception:
        hourly = {'max': 0, 'public': [], 'banks': [], 'all': []}
        heatmap = {'max': 0, 'public': [], 'banks': [], 'all': []}

    # ===== 额外：能力雷达（0-100）=====
    def _clamp100(x: float) -> float:
        try:
            v = float(x)
        except Exception:
            v = 0.0
        return max(0.0, min(100.0, v))

    answered_all = int(all_summary.get('answered') or 0)
    mistakes_rate = (int(all_summary.get('mistakes_times') or 0) * 100.0 / max(1, answered_all)) if answered_all > 0 else 0.0
    fav_rate = (int(all_summary.get('favorites') or 0) * 100.0 / max(1, answered_all)) if answered_all > 0 else 0.0

    ability_radar = [
        {'name': '覆盖率', 'value': _clamp100(float(all_summary.get('completion') or 0.0))},
        {'name': '正确率', 'value': _clamp100(float(all_summary.get('accuracy') or 0.0))},
        {'name': '连续性', 'value': _clamp100(float(all_summary.get('streak_days') or 0) / 14.0 * 100.0)},
        {'name': '错题治理', 'value': _clamp100(100.0 - mistakes_rate)},
        {'name': '收藏密度', 'value': _clamp100(fav_rate * 2.0)},
    ]


    base_ctx = {
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
        'bank_daily_max': bank_daily_max,
        'all_daily': all_daily,
        'all_daily_max': all_daily_max,
        'answered_7d': answered_7d,
        'correct_7d': correct_7d,
        'answered_30d': answered_30d,
        'correct_30d': correct_30d,
        'window_days': window_days,
        'daily': daily,
        'daily_max': daily_max,
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
        'mistakes_rate': mistakes_rate,
    }

    return conn, subject_ids, base_ctx
