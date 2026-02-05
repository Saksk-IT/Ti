# -*- coding: utf-8 -*-

import json
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, current_app

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import today_bj

from ..api_bp import user_bank_api_bp
from ..api_shared import (
    check_bank_access,
    generate_share_code,
    get_bank_category_name,
    _parse_question_ids_from_request_args,
    _get_bank_tag_store_key,
    _load_bank_tag_store,
    _save_bank_tag_store,
)


@user_bank_api_bp.route('/<int:bank_id>/quiz', methods=['GET'])
@auth_required
def get_quiz_questions(bank_id):
    """获取刷题题目"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    mode = request.args.get('mode', 'all')
    limit = request.args.get('limit', 20, type=int)
    q_type = (request.args.get('q_type') or '').strip()
    tag = (request.args.get('tag') or '').strip()

    conn = get_db()

    tag_question_ids = None
    if tag and tag != 'all':
        try:
            store = _load_bank_tag_store(conn, bank_id, user_id)
            question_tags = store.get('question_tags', {}) or {}
            tag_question_ids = []
            for q_id, tags in question_tags.items():
                if not isinstance(tags, list):
                    continue
                if tag in tags:
                    try:
                        tag_question_ids.append(int(q_id))
                    except Exception:
                        continue
        except Exception:
            tag_question_ids = []

        if not tag_question_ids:
            return jsonify({'code': 0, 'data': {'questions': [], 'total': 0}})

    type_condition = ' AND q.q_type = ?' if q_type else ''
    type_params = [q_type] if q_type else []

    tag_condition = ''
    tag_params = []
    if tag_question_ids is not None:
        # 去重，避免无意义的 SQL 变量膨胀
        tag_question_ids = sorted(set(tag_question_ids))
        # SQLite 默认变量上限约 999；超过时改为安全的整数拼接（已强制 int 转换）
        if len(tag_question_ids) <= 900:
            tag_condition = ' AND q.id IN ({})'.format(','.join('?' * len(tag_question_ids)))
            tag_params = tag_question_ids
        else:
            tag_condition = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_question_ids))
            tag_params = []

    if mode == 'wrong':
        # 错题模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY m.wrong_count DESC, m.updated_at DESC
            LIMIT ?
        ''', [bank_id, user_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    elif mode == 'favorites':
        # 收藏模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY f.created_at DESC
            LIMIT ?
        ''', [bank_id, user_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    elif mode == 'random':
        # 随机模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY RANDOM() LIMIT ?
        ''', [bank_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition, [bank_id] + type_params + tag_params).fetchone()['cnt']
    else:
        # 顺序模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY q.sort_order ASC, q.id ASC LIMIT ?
        ''', [bank_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition, [bank_id] + type_params + tag_params).fetchone()['cnt']

    # 更新访问记录
    if access_type == 'shared':
        conn.execute('''
            UPDATE bank_share_records
            SET last_access_at = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE user_id = ? AND bank_id = ?
        ''', (user_id, bank_id))
    elif access_type == 'public':
        # 更新公开题库使用记录
        existing = conn.execute(
            'SELECT id FROM public_bank_users WHERE bank_id = ? AND user_id = ?',
            (bank_id, user_id)
        ).fetchone()

        if existing:
            conn.execute('''
                UPDATE public_bank_users
                SET last_access_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE bank_id = ? AND user_id = ?
            ''', (bank_id, user_id))
        else:
            conn.execute('''
                INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1)
            ''', (bank_id, user_id))
            # 更新公开使用人数
            conn.execute(
                'UPDATE user_question_banks SET public_use_count = public_use_count + 1 WHERE id = ?',
                (bank_id,)
            )

    conn.commit()

    # 获取用户的收藏和错题状态
    question_ids = [q['id'] for q in questions]

    if question_ids:
        # 获取收藏状态
        fav_query = 'SELECT question_id FROM user_bank_favorites WHERE user_id = ? AND question_id IN ({})'.format(
            ','.join('?' * len(question_ids))
        )
        fav_rows = conn.execute(fav_query, [user_id] + question_ids).fetchall()
        fav_set = {r['question_id'] for r in fav_rows}

        # 获取错题状态
        mistake_query = 'SELECT question_id FROM user_bank_mistakes WHERE user_id = ? AND question_id IN ({})'.format(
            ','.join('?' * len(question_ids))
        )
        mistake_rows = conn.execute(mistake_query, [user_id] + question_ids).fetchall()
        mistake_set = {r['question_id'] for r in mistake_rows}
    else:
        fav_set = set()
        mistake_set = set()

    # 构建返回数据，添加收藏和错题状态
    result_questions = []
    for q in questions:
        q_dict = dict(q)
        q_dict['is_fav'] = 1 if q_dict['id'] in fav_set else 0
        q_dict['is_mistake'] = 1 if q_dict['id'] in mistake_set else 0
        result_questions.append(q_dict)

    return jsonify({
        'code': 0,
        'data': {
            'questions': result_questions,
            'total': total
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/quiz/record', methods=['POST'])
@auth_required
def record_quiz_result(bank_id):
    """记录答题结果"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    data = request.get_json() or {}
    question_id = data.get('question_id')
    user_answer = data.get('user_answer')
    is_correct = data.get('is_correct')

    if not question_id:
        return jsonify({'code': 1, 'message': '缺少题目ID'}), 400

    conn = get_db()

    # 验证题目属于该题库
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 记录或更新答题记录
    conn.execute('''
        INSERT INTO user_bank_answers (user_id, bank_id, question_id, user_answer, is_correct)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            user_answer = excluded.user_answer,
            is_correct = excluded.is_correct,
            created_at = CURRENT_TIMESTAMP
    ''', (user_id, bank_id, question_id, user_answer, 1 if is_correct else 0))

    # 处理错题记录
    if not is_correct:
        conn.execute('''
            INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, question_id) DO UPDATE SET
                wrong_count = wrong_count + 1,
                updated_at = CURRENT_TIMESTAMP
        ''', (user_id, bank_id, question_id))
    else:
        # 答对了，从错题中移除
        conn.execute(
            'DELETE FROM user_bank_mistakes WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )

    conn.commit()

    return jsonify({'code': 0, 'message': '记录成功'})


@user_bank_api_bp.route('/<int:bank_id>/my-stats', methods=['GET'])
@auth_required
def get_my_stats(bank_id):
    """获取我的答题统计"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    stats = conn.execute('''
        SELECT
            COUNT(*) as total_answered,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
            SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as wrong_count
        FROM user_bank_answers
        WHERE user_id = ? AND bank_id = ?
    ''', (user_id, bank_id)).fetchone()

    total = stats['total_answered'] or 0
    correct = stats['correct_count'] or 0
    wrong = stats['wrong_count'] or 0
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    return jsonify({
        'code': 0,
        'data': {
            'total_answered': total,
            'correct_count': correct,
            'wrong_count': wrong,
            'accuracy': accuracy
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/stats', methods=['GET'])
@auth_required
def get_bank_stats_detail(bank_id):
    """题库统计详情（用于题库详情页-统计子页面）"""
    from datetime import datetime, timedelta

    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)
    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    def _column_exists(table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    window_days = request.args.get('days', 14, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 14

    # 可选筛选：用于“错题/收藏/标签中心”的数据子页面（不传则按全题库统计）
    source = (request.args.get('source') or 'all').strip().lower()  # all/favorites/mistakes
    if source not in ('all', 'favorites', 'mistakes'):
        source = 'all'

    q_type_filter = (request.args.get('q_type') or '').strip()
    if q_type_filter.lower() == 'all':
        q_type_filter = ''

    tag = (request.args.get('tag') or '').strip()
    if tag and str(tag).lower() == 'all':
        tag = ''

    tag_cond = ''
    tag_params: list = []
    if tag:
        try:
            store = _load_bank_tag_store(conn, bank_id, user_id)
            question_tags = store.get('question_tags', {}) or {}
            tag_question_ids = []
            for q_id, tags in question_tags.items():
                if not isinstance(tags, list):
                    continue
                if tag in tags:
                    try:
                        tag_question_ids.append(int(q_id))
                    except Exception:
                        continue
        except Exception:
            tag_question_ids = []

        if not tag_question_ids:
            return jsonify({
                'code': 0,
                'data': {
                    'bank_id': int(bank_id),
                    'total_count': 0,
                    'answered': 0,
                    'correct': 0,
                    'wrong': 0,
                    'favorites': 0,
                    'mistakes': 0,
                    'mistakes_times': 0,
                    'accuracy': 0.0,
                    'completion': 0.0,
                    'streak_days': 0,
                    'last_activity': None,
                    'trend_days': window_days,
                    'trend': [],
                    'by_type': [],
                    'by_difficulty': [],
                    'advice': [],
                }
            })

        tag_question_ids = sorted(set(tag_question_ids))
        if len(tag_question_ids) <= 900:
            placeholders = ','.join('?' * len(tag_question_ids))
            tag_cond = f' AND q.id IN ({placeholders})'
            tag_params = tag_question_ids
        else:
            # 避免 SQLite 参数上限（tag_question_ids 已强制 int 转换）
            tag_cond = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_question_ids))
            tag_params = []

    def _join_bank_table(table: str, alias: str):
        # 兼容旧库：favorites/mistakes 表可能缺少 user_id/bank_id 字段
        if not _column_exists(table, 'question_id'):
            return f"LEFT JOIN (SELECT NULL AS question_id) {alias} ON 1=0", []
        join_sql = f"LEFT JOIN {table} {alias} ON {alias}.question_id = q.id"
        params = []
        if _column_exists(table, 'user_id'):
            join_sql += f" AND {alias}.user_id = ?"
            params.append(int(user_id))
        if _column_exists(table, 'bank_id'):
            join_sql += f" AND {alias}.bank_id = ?"
            params.append(int(bank_id))
        return join_sql, params

    fav_join, fav_params = _join_bank_table('user_bank_favorites', 'f')
    mis_join, mis_params = _join_bank_table('user_bank_mistakes', 'm')

    base_from = f"""
    FROM user_bank_questions q
    {fav_join}
    {mis_join}
    WHERE q.bank_id = ?
    """
    base_params: list = fav_params + mis_params + [int(bank_id)]
    if q_type_filter:
        base_from += " AND q.q_type = ?"
        base_params.append(q_type_filter)
    if tag_cond:
        base_from += tag_cond
        base_params.extend(tag_params)
    if source == 'favorites':
        base_from += " AND f.question_id IS NOT NULL"
    elif source == 'mistakes':
        base_from += " AND m.question_id IS NOT NULL"

    total_count = int(conn.execute("SELECT COUNT(1) AS cnt " + base_from, base_params).fetchone()['cnt'] or 0)

    row = conn.execute(
        f"""
        SELECT
          COUNT(*) AS answered,
          SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          MAX(a.created_at) AS last_activity
        FROM user_bank_answers a
        JOIN user_bank_questions q ON a.question_id = q.id
        {fav_join}
        {mis_join}
        WHERE a.user_id = ? AND a.bank_id = ?
        """
        + (" AND q.q_type = ?" if q_type_filter else "")
        + tag_cond
        + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
        + (" AND m.question_id IS NOT NULL" if source == "mistakes" else ""),
        (fav_params + mis_params + [int(user_id), int(bank_id)] + ([q_type_filter] if q_type_filter else []) + tag_params),
    ).fetchone()

    answered = int(row['answered'] or 0) if row else 0
    correct = int(row['correct'] or 0) if row else 0
    wrong = max(0, answered - correct)
    last_activity = (row['last_activity'] if row else None) or None

    favorites = int(conn.execute("SELECT COUNT(1) AS cnt " + base_from + " AND f.question_id IS NOT NULL", base_params).fetchone()['cnt'] or 0)

    mistakes_has_wrong_count = _column_exists('user_bank_mistakes', 'wrong_count')
    try:
        if mistakes_has_wrong_count:
            m_row = conn.execute(
                "SELECT COUNT(1) AS cnt, SUM(COALESCE(m.wrong_count, 1)) AS times " + base_from + " AND m.question_id IS NOT NULL",
                base_params,
            ).fetchone()
            mistakes = int(m_row['cnt'] or 0) if m_row else 0
            mistakes_times = int(m_row['times'] or 0) if m_row else 0
        else:
            mistakes = int(conn.execute("SELECT COUNT(1) AS cnt " + base_from + " AND m.question_id IS NOT NULL", base_params).fetchone()['cnt'] or 0)
            mistakes_times = mistakes
    except Exception:
        mistakes = 0
        mistakes_times = 0

    accuracy = round(correct * 100 / answered, 1) if answered > 0 else 0.0
    completion = round(answered * 100 / total_count, 1) if total_count > 0 else 0.0

    # streak（注：基于 user_bank_answers 的最新记录，属于“近似活跃”）
    streak_days = 0
    try:
        rows = conn.execute(
            f"""
            SELECT DISTINCT DATE(a.created_at) AS day
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = ? AND a.bank_id = ?
            """
            + (" AND q.q_type = ?" if q_type_filter else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + """
            ORDER BY day DESC
            LIMIT 120
            """,
            (fav_params + mis_params + [int(user_id), int(bank_id)] + ([q_type_filter] if q_type_filter else []) + tag_params),
        ).fetchall()

        dates = []
        for r in rows or []:
            day = (r['day'] if r else None) or None
            if not day:
                continue
            try:
                dates.append(datetime.strptime(day, '%Y-%m-%d').date())
            except Exception:
                continue

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

    # trend：最近 N 天（基于 user_bank_answers 的最新记录）
    trend = []
    try:
        days_back = max(1, window_days) - 1
        rows = conn.execute(
            f"""
            SELECT
              DATE(a.created_at) AS day,
              COUNT(*) AS answered,
              SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = ? AND a.bank_id = ?
              AND a.created_at >= datetime('now', '+8 hours', ?)
            """
            + (" AND q.q_type = ?" if q_type_filter else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + """
            GROUP BY day
            ORDER BY day ASC
            """,
            (fav_params + mis_params + [int(user_id), int(bank_id), f'-{days_back} days'] + ([q_type_filter] if q_type_filter else []) + tag_params),
        ).fetchall()

        by_day = {}
        for r in rows or []:
            day = (r['day'] if r else None) or None
            if not day:
                continue
            by_day[str(day)] = {
                'answered': int(r['answered'] or 0),
                'correct': int(r['correct'] or 0),
            }

        start_day = today_bj() - timedelta(days=days_back)
        for i in range(0, days_back + 1):
            d = (start_day + timedelta(days=i)).strftime('%Y-%m-%d')
            item = by_day.get(d) or {'answered': 0, 'correct': 0}
            a = int(item.get('answered') or 0)
            c = int(item.get('correct') or 0)
            trend.append({'day': d, 'answered': a, 'correct': c, 'wrong': max(0, a - c)})
    except Exception:
        trend = []

    # by_type：总题/已做/正确率/覆盖率 + 收藏/错题
    by_type = []
    try:
        total_rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(q.q_type), ''), '未知') AS q_type, COUNT(*) AS total
            """
            + base_from
            + """
            GROUP BY q_type
            ORDER BY total DESC
            """,
            base_params,
        ).fetchall()
        total_map = {str(r['q_type']): int(r['total'] or 0) for r in (total_rows or []) if r}

        answered_rows = conn.execute(
            f"""
            SELECT COALESCE(NULLIF(TRIM(q.q_type), ''), '未知') AS q_type,
                   COUNT(*) AS answered,
                   SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = ? AND a.bank_id = ?
            """
            + (" AND q.q_type = ?" if q_type_filter else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + """
            GROUP BY q.q_type
            """,
            (fav_params + mis_params + [int(user_id), int(bank_id)] + ([q_type_filter] if q_type_filter else []) + tag_params),
        ).fetchall()
        answered_map = {
            str(r['q_type']): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
            for r in (answered_rows or [])
            if r
        }

        fav_rows = conn.execute(
            "SELECT COALESCE(NULLIF(TRIM(q.q_type), ''), '未知') AS q_type, COUNT(*) AS cnt " + base_from + " AND f.question_id IS NOT NULL GROUP BY q_type",
            base_params,
        ).fetchall()
        fav_map = {str(r['q_type']): int(r['cnt'] or 0) for r in (fav_rows or []) if r}

        mis_rows = conn.execute(
            "SELECT COALESCE(NULLIF(TRIM(q.q_type), ''), '未知') AS q_type, COUNT(*) AS cnt " + base_from + " AND m.question_id IS NOT NULL GROUP BY q_type",
            base_params,
        ).fetchall()
        mis_map = {str(r['q_type']): int(r['cnt'] or 0) for r in (mis_rows or []) if r}

        keys = set(total_map.keys()) | set(answered_map.keys()) | set(fav_map.keys()) | set(mis_map.keys())
        for k in keys:
            total = int(total_map.get(k, 0))
            a = int((answered_map.get(k) or {}).get('answered', 0))
            c = int((answered_map.get(k) or {}).get('correct', 0))
            w = max(0, a - c)
            by_type.append({
                'q_type': k,
                'total': total,
                'answered': a,
                'correct': c,
                'wrong': w,
                'accuracy': round(c * 100 / a, 1) if a > 0 else 0.0,
                'completion': round(a * 100 / total, 1) if total > 0 else 0.0,
                'favorites': int(fav_map.get(k, 0)),
                'mistakes': int(mis_map.get(k, 0)),
            })

        by_type.sort(key=lambda x: (-int(x.get('answered') or 0), str(x.get('q_type') or '')))
    except Exception:
        by_type = []

    # by_difficulty（个人题库题目有 difficulty 字段）
    by_difficulty = []
    if _column_exists('user_bank_questions', 'difficulty'):
        try:
            total_rows = conn.execute(
                "SELECT COALESCE(q.difficulty, 1) AS difficulty, COUNT(*) AS total " + base_from + " GROUP BY difficulty ORDER BY difficulty ASC",
                base_params,
            ).fetchall()
            total_map = {int(r['difficulty'] or 1): int(r['total'] or 0) for r in (total_rows or []) if r}

            ans_rows = conn.execute(
                f"""
                SELECT COALESCE(q.difficulty, 1) AS difficulty,
                       COUNT(*) AS answered,
                       SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                FROM user_bank_answers a
                JOIN user_bank_questions q ON a.question_id = q.id
                {fav_join}
                {mis_join}
                WHERE a.user_id = ? AND a.bank_id = ?
                """
                + (" AND q.q_type = ?" if q_type_filter else "")
                + tag_cond
                + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
                + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
                + """
                GROUP BY q.difficulty
                ORDER BY difficulty ASC
                """,
                (fav_params + mis_params + [int(user_id), int(bank_id)] + ([q_type_filter] if q_type_filter else []) + tag_params),
            ).fetchall()
            ans_map = {
                int(r['difficulty'] or 1): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
                for r in (ans_rows or [])
                if r
            }

            def _diff_label(d: int) -> str:
                return {1: '简单', 2: '中等', 3: '困难'}.get(d, f'难度{d}')

            keys = sorted(set(total_map.keys()) | set(ans_map.keys()))
            for d in keys:
                total = int(total_map.get(d, 0))
                a = int((ans_map.get(d) or {}).get('answered', 0))
                c = int((ans_map.get(d) or {}).get('correct', 0))
                by_difficulty.append({
                    'difficulty': int(d),
                    'label': _diff_label(int(d)),
                    'total': total,
                    'answered': a,
                    'correct': c,
                    'wrong': max(0, a - c),
                    'accuracy': round(c * 100 / a, 1) if a > 0 else 0.0,
                    'completion': round(a * 100 / total, 1) if total > 0 else 0.0,
                })
        except Exception:
            by_difficulty = []

    advice = []
    try:
        if total_count <= 0:
            advice = [{'title': '暂无题目', 'content': '该题库目前没有可练习的题目。'}]
        else:
            if answered < 10:
                advice.append({'title': '先建立手感', 'content': '建议先从“练习-全题库”开始，连续做 20~30 题快速熟悉题型与知识点。'})
            if completion < 35:
                advice.append({'title': '提高完成度', 'content': '当前覆盖率偏低，建议每天固定一段时间刷题，优先把“未做”题补齐。'})
            if accuracy < 65 and answered >= 10:
                advice.append({'title': '聚焦薄弱点', 'content': '正确率偏低，建议先做“错题”复盘，再回到练习巩固。'})
            if mistakes_times >= 20:
                advice.append({'title': '错题要闭环', 'content': '错题次数较多，建议用“背题”模式强化记忆，并在错因处做一次总结。'})

            weak = [r for r in (by_type or []) if int(r.get('answered') or 0) >= 5]
            weak.sort(key=lambda x: (float(x.get('accuracy') or 0.0), -int(x.get('answered') or 0)))
            if weak[:2]:
                names = '、'.join([str(x.get('q_type')) for x in weak[:2]])
                advice.append({'title': '优先攻克题型', 'content': f'你在「{names}」上的正确率相对更低，建议优先针对性练习并复盘。'})
    except Exception:
        advice = []

    return jsonify({
        'code': 0,
        'data': {
            'bank_id': int(bank_id),
            'total_count': total_count,
            'answered': answered,
            'correct': correct,
            'wrong': wrong,
            'favorites': favorites,
            'mistakes': mistakes,
            'mistakes_times': mistakes_times,
            'accuracy': accuracy,
            'completion': completion,
            'streak_days': streak_days,
            'last_activity': last_activity,
            'trend_days': window_days,
            'trend': trend,
            'by_type': by_type,
            'by_difficulty': by_difficulty,
            'advice': advice,
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/user-counts', methods=['GET'])
@auth_required
def get_user_counts(bank_id):
    """获取题库的用户统计（总数、收藏数、错题数，支持题型和来源筛选）"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    q_type = request.args.get('q_type', '').strip()
    source = request.args.get('source', 'all').strip()
    tag = (request.args.get('tag') or '').strip()

    conn = get_db()

    tag_question_ids = None
    if tag and tag != 'all':
        try:
            store = _load_bank_tag_store(conn, bank_id, user_id)
            question_tags = store.get('question_tags', {}) or {}
            tag_question_ids = []
            for q_id, tags in question_tags.items():
                if not isinstance(tags, list):
                    continue
                if tag in tags:
                    try:
                        tag_question_ids.append(int(q_id))
                    except Exception:
                        continue
        except Exception:
            tag_question_ids = []

        if not tag_question_ids:
            return jsonify({'code': 0, 'data': {'total': 0, 'favorites': 0, 'mistakes': 0}})

    # 构建基础查询条件
    type_condition = ' AND q.q_type = ?' if q_type else ''
    type_params = [q_type] if q_type else []

    tag_condition = ''
    tag_params = []
    if tag_question_ids is not None:
        tag_question_ids = sorted(set(tag_question_ids))
        if len(tag_question_ids) <= 900:
            tag_condition = ' AND q.id IN ({})'.format(','.join('?' * len(tag_question_ids)))
            tag_params = tag_question_ids
        else:
            tag_condition = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_question_ids))
            tag_params = []

    # 根据 source 筛选
    if source == 'favorites':
        # 获取收藏题目数
        total_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition
        total = conn.execute(total_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    elif source == 'mistakes':
        # 获取用户错题
        total_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition
        total = conn.execute(total_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    else:
        # 获取全部题目
        total_query = 'SELECT COUNT(*) as cnt FROM user_bank_questions q WHERE q.bank_id = ?' + type_condition + tag_condition
        total = conn.execute(total_query, [bank_id] + type_params + tag_params).fetchone()['cnt']

    # 获取收藏数（基于当前题型筛选）
    try:
        favorites_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition
        favorites = conn.execute(favorites_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    except Exception:
        favorites = 0

    # 获取错题数（基于当前题型筛选）
    try:
        mistakes_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition
        mistakes = conn.execute(mistakes_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    except Exception:
        mistakes = 0

    return jsonify({
        'code': 0,
        'data': {
            'total': total,
            'favorites': favorites,
            'mistakes': mistakes
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>/favorite', methods=['POST'])
@auth_required
def toggle_favorite(bank_id, question_id):
    """切换题目收藏状态"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    # 检查题目是否存在
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 检查是否已收藏
    existing = conn.execute(
        'SELECT id FROM user_bank_favorites WHERE user_id = ? AND question_id = ?',
        (user_id, question_id)
    ).fetchone()

    if existing:
        # 取消收藏
        conn.execute(
            'DELETE FROM user_bank_favorites WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )
        conn.commit()
        return jsonify({
            'code': 0,
            'message': '已取消收藏',
            'is_favorite': False
        })
    else:
        # 添加收藏
        conn.execute(
            '''INSERT INTO user_bank_favorites (user_id, bank_id, question_id)
               VALUES (?, ?, ?)''',
            (user_id, bank_id, question_id)
        )
        conn.commit()
        return jsonify({
            'code': 0,
            'message': '已收藏',
            'is_favorite': True
        })
