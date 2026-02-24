# -*- coding: utf-8 -*-

"""用户题库：刷题/统计 API"""

import random
from datetime import datetime, timedelta

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import today_bj, now_bj

from .api_base import user_bank_api_bp, check_bank_access
from .api_tags import _load_bank_tag_store


def _build_named_in(col: str, values: list, prefix: str = 'in') -> tuple[str, dict]:
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ', '.join(f':{k}' for k in params)
    return f"{col} IN ({placeholders})", params


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
    custom_ids_raw = (request.args.get('ids') or request.args.get('question_ids') or '').strip()

    def _parse_id_list(val: str, max_len: int = 200):
        out = []
        if not val:
            return out
        parts = str(val).replace('\uff0c', ',').split(',')
        for p in parts:
            if len(out) >= max_len:
                break
            s = str(p or '').strip()
            if not s:
                continue
            try:
                n = int(s)
            except Exception:
                continue
            if n > 0:
                out.append(n)
        # 去重（保持顺序）
        seen = set()
        uniq = []
        for n in out:
            if n in seen:
                continue
            seen.add(n)
            uniq.append(n)
        return uniq

    custom_ids = _parse_id_list(custom_ids_raw)

    if custom_ids:
        in_clause, in_params = _build_named_in('q.id', custom_ids, 'cid')
        rows = db.session.execute(
            text(f"SELECT q.* FROM user_bank_questions q WHERE q.bank_id = :bank_id AND {in_clause}"),
            {'bank_id': bank_id, **in_params},
        ).fetchall()
        q_map = {int(r._mapping['id']): r for r in (rows or []) if r and r._mapping['id'] is not None}
        questions = [q_map[i] for i in custom_ids if i in q_map]
        total = len(questions)
    else:
        raw_conn = db.session.connection()
        tag_question_ids = None
        if tag and tag != 'all':
            try:
                store = _load_bank_tag_store(raw_conn, bank_id, user_id)
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

        from app.core.utils.portable_question_format import any_type_to_portable_type

        type_condition = ' AND q.type = :q_type_filter' if q_type else ''
        type_params = {'q_type_filter': any_type_to_portable_type(q_type)} if q_type else {}

        tag_condition = ''
        tag_params = {}
        if tag_question_ids is not None:
            tag_question_ids = sorted(set(tag_question_ids))
            tag_condition, tag_params = _build_named_in('q.id', tag_question_ids, 'tq')
            tag_condition = ' AND ' + tag_condition

        base_params = {'bank_id': bank_id, 'uid': user_id, 'lim': limit, **type_params, **tag_params}

        if mode == 'wrong':
            questions = db.session.execute(text('''
                SELECT q.* FROM user_bank_questions q
                JOIN user_bank_mistakes m ON q.id = m.question_id
                WHERE q.bank_id = :bank_id AND m.user_id = :uid
            ''' + type_condition + tag_condition + '''
                ORDER BY m.wrong_count DESC, m.updated_at DESC
                LIMIT :lim
            '''), base_params).fetchall()

            total = db.session.execute(text('''
                SELECT COUNT(*) as cnt FROM user_bank_questions q
                JOIN user_bank_mistakes m ON q.id = m.question_id
                WHERE q.bank_id = :bank_id AND m.user_id = :uid
            ''' + type_condition + tag_condition), base_params).fetchone()._mapping['cnt']
        elif mode == 'favorites':
            questions = db.session.execute(text('''
                SELECT q.* FROM user_bank_questions q
                JOIN user_bank_favorites f ON q.id = f.question_id
                WHERE q.bank_id = :bank_id AND f.user_id = :uid
            ''' + type_condition + tag_condition + '''
                ORDER BY f.created_at DESC
                LIMIT :lim
            '''), base_params).fetchall()

            total = db.session.execute(text('''
                SELECT COUNT(*) as cnt FROM user_bank_questions q
                JOIN user_bank_favorites f ON q.id = f.question_id
                WHERE q.bank_id = :bank_id AND f.user_id = :uid
            ''' + type_condition + tag_condition), base_params).fetchone()._mapping['cnt']
        elif mode == 'random':
            questions = db.session.execute(text('''
                SELECT q.* FROM user_bank_questions q
                WHERE q.bank_id = :bank_id
            ''' + type_condition + tag_condition + '''
                ORDER BY RANDOM() LIMIT :lim
            '''), base_params).fetchall()

            total = db.session.execute(text('''
                SELECT COUNT(*) as cnt FROM user_bank_questions q
                WHERE q.bank_id = :bank_id
            ''' + type_condition + tag_condition), base_params).fetchone()._mapping['cnt']
        else:
            questions = db.session.execute(text('''
                SELECT q.* FROM user_bank_questions q
                WHERE q.bank_id = :bank_id
            ''' + type_condition + tag_condition + '''
                ORDER BY q.sort_order ASC, q.id ASC LIMIT :lim
            '''), base_params).fetchall()

            total = db.session.execute(text('''
                SELECT COUNT(*) as cnt FROM user_bank_questions q
                WHERE q.bank_id = :bank_id
            ''' + type_condition + tag_condition), base_params).fetchone()._mapping['cnt']

    # 更新访问记录
    if access_type == 'shared':
        db.session.execute(text('''
            UPDATE bank_share_records
            SET last_access_at = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE user_id = :uid AND bank_id = :bank_id
        '''), {'uid': user_id, 'bank_id': bank_id})
    elif access_type == 'public':
        existing = db.session.execute(
            text('SELECT id FROM public_bank_users WHERE bank_id = :bank_id AND user_id = :uid'),
            {'bank_id': bank_id, 'uid': user_id}
        ).fetchone()

        if existing:
            db.session.execute(text('''
                UPDATE public_bank_users
                SET last_access_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE bank_id = :bank_id AND user_id = :uid
            '''), {'bank_id': bank_id, 'uid': user_id})
        else:
            db.session.execute(text('''
                INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
                VALUES (:bank_id, :uid, CURRENT_TIMESTAMP, 1)
            '''), {'bank_id': bank_id, 'uid': user_id})
            db.session.execute(
                text('UPDATE user_question_banks SET public_use_count = public_use_count + 1 WHERE id = :bank_id'),
                {'bank_id': bank_id}
            )

    db.session.commit()

    # 获取用户的收藏和错题状态
    question_ids = [q._mapping['id'] for q in questions]

    if question_ids:
        in_clause, in_params = _build_named_in('question_id', question_ids, 'qid')
        fav_rows = db.session.execute(
            text(f'SELECT question_id FROM user_bank_favorites WHERE user_id = :uid AND {in_clause}'),
            {'uid': user_id, **in_params}
        ).fetchall()
        fav_set = {r._mapping['question_id'] for r in fav_rows}

        mistake_rows = db.session.execute(
            text(f'SELECT question_id FROM user_bank_mistakes WHERE user_id = :uid AND {in_clause}'),
            {'uid': user_id, **in_params}
        ).fetchall()
        mistake_set = {r._mapping['question_id'] for r in mistake_rows}
    else:
        fav_set = set()
        mistake_set = set()

    # 构建返回数据，添加收藏和错题状态
    from app.core.utils.pqf_rows import pqf_row_to_internal

    result_questions = []
    for q in questions:
        q_dict = pqf_row_to_internal(q, scope='user_bank')
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

    question = db.session.execute(
        text('SELECT id FROM user_bank_questions WHERE id = :qid AND bank_id = :bank_id'),
        {'qid': question_id, 'bank_id': bank_id}
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    db.session.execute(text('''
        INSERT INTO user_bank_answers (user_id, bank_id, question_id, user_answer, is_correct)
        VALUES (:uid, :bank_id, :qid, :user_answer, :is_correct)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            user_answer = EXCLUDED.user_answer,
            is_correct = EXCLUDED.is_correct,
            created_at = CURRENT_TIMESTAMP
    '''), {'uid': user_id, 'bank_id': bank_id, 'qid': question_id,
           'user_answer': user_answer, 'is_correct': 1 if is_correct else 0})

    if not is_correct:
        db.session.execute(text('''
            INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count)
            VALUES (:uid, :bank_id, :qid, 1)
            ON CONFLICT(user_id, question_id) DO UPDATE SET
                wrong_count = user_bank_mistakes.wrong_count + 1,
                updated_at = CURRENT_TIMESTAMP
        '''), {'uid': user_id, 'bank_id': bank_id, 'qid': question_id})
    else:
        db.session.execute(
            text('DELETE FROM user_bank_mistakes WHERE user_id = :uid AND question_id = :qid'),
            {'uid': user_id, 'qid': question_id}
        )

    db.session.commit()

    return jsonify({'code': 0, 'message': '记录成功'})


@user_bank_api_bp.route('/<int:bank_id>/my-stats', methods=['GET'])
@auth_required
def get_my_stats(bank_id):
    """获取我的答题统计"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    stats = db.session.execute(text('''
        SELECT
            COUNT(*) as total_answered,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
            SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as wrong_count
        FROM user_bank_answers
        WHERE user_id = :uid AND bank_id = :bank_id
    '''), {'uid': user_id, 'bank_id': bank_id}).fetchone()

    total = stats._mapping['total_answered'] or 0
    correct = stats._mapping['correct_count'] or 0
    wrong = stats._mapping['wrong_count'] or 0
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

    window_days = request.args.get('days', 14, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 14

    source = (request.args.get('source') or 'all').strip().lower()
    if source not in ('all', 'favorites', 'mistakes'):
        source = 'all'

    q_type_filter = (request.args.get('q_type') or '').strip()
    if q_type_filter.lower() == 'all':
        q_type_filter = ''
    from app.core.utils.portable_question_format import any_type_to_portable_type, portable_type_to_q_type
    q_type_filter_pt = any_type_to_portable_type(q_type_filter) if q_type_filter else ''

    tag = (request.args.get('tag') or '').strip()
    if tag and str(tag).lower() == 'all':
        tag = ''

    tag_cond = ''
    tag_params: dict = {}
    if tag:
        raw_conn = db.session.connection()
        try:
            store = _load_bank_tag_store(raw_conn, bank_id, user_id)
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
                    'total_count': 0, 'answered': 0, 'correct': 0, 'wrong': 0,
                    'favorites': 0, 'mistakes': 0, 'mistakes_times': 0,
                    'accuracy': 0.0, 'completion': 0.0, 'streak_days': 0,
                    'last_activity': None, 'trend_days': window_days,
                    'trend': [], 'by_type': [], 'by_difficulty': [], 'advice': [],
                }
            })

        tag_question_ids = sorted(set(tag_question_ids))
        in_sql, tag_params = _build_named_in('q.id', tag_question_ids, 'tq')
        tag_cond = ' AND ' + in_sql

    # PostgreSQL: all columns guaranteed to exist — no dynamic column checks needed
    fav_join = "LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = :fav_uid AND f.bank_id = :fav_bid"
    mis_join = "LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = :mis_uid AND m.bank_id = :mis_bid"
    join_params = {'fav_uid': int(user_id), 'fav_bid': int(bank_id), 'mis_uid': int(user_id), 'mis_bid': int(bank_id)}

    base_from = f"""
    FROM user_bank_questions q
    {fav_join}
    {mis_join}
    WHERE q.bank_id = :base_bank_id
    """
    base_params: dict = {**join_params, 'base_bank_id': int(bank_id)}
    if q_type_filter_pt:
        base_from += " AND q.type = :q_type_f"
        base_params['q_type_f'] = q_type_filter_pt
    if tag_cond:
        base_from += tag_cond
        base_params.update(tag_params)
    if source == 'favorites':
        base_from += " AND f.question_id IS NOT NULL"
    elif source == 'mistakes':
        base_from += " AND m.question_id IS NOT NULL"

    total_count = int(db.session.execute(text("SELECT COUNT(1) AS cnt " + base_from), base_params).fetchone()._mapping['cnt'] or 0)

    ans_extra_params = {**base_params, 'ans_uid': int(user_id), 'ans_bid': int(bank_id)}
    row = db.session.execute(
        text(f"""
        SELECT
          COUNT(*) AS answered,
          SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
          MAX(a.created_at) AS last_activity
        FROM user_bank_answers a
        JOIN user_bank_questions q ON a.question_id = q.id
        {fav_join}
        {mis_join}
        WHERE a.user_id = :ans_uid AND a.bank_id = :ans_bid
        """
        + (" AND q.type = :q_type_f" if q_type_filter_pt else "")
        + tag_cond
        + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
        + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")),
        ans_extra_params,
    ).fetchone()

    answered = int(row._mapping['answered'] or 0) if row else 0
    correct = int(row._mapping['correct'] or 0) if row else 0
    wrong = max(0, answered - correct)
    last_activity = (row._mapping['last_activity'] if row else None) or None

    favorites = int(db.session.execute(
        text("SELECT COUNT(1) AS cnt " + base_from + " AND f.question_id IS NOT NULL"), base_params
    ).fetchone()._mapping['cnt'] or 0)

    try:
        m_row = db.session.execute(
            text("SELECT COUNT(1) AS cnt, SUM(COALESCE(m.wrong_count, 1)) AS times " + base_from + " AND m.question_id IS NOT NULL"),
            base_params,
        ).fetchone()
        mistakes = int(m_row._mapping['cnt'] or 0) if m_row else 0
        mistakes_times = int(m_row._mapping['times'] or 0) if m_row else 0
    except Exception:
        mistakes = 0
        mistakes_times = 0

    accuracy = round(correct * 100 / answered, 1) if answered > 0 else 0.0
    completion = round(answered * 100 / total_count, 1) if total_count > 0 else 0.0

    # streak
    streak_days = 0
    try:
        rows = db.session.execute(
            text(f"""
            SELECT DISTINCT DATE(a.created_at) AS day
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = :ans_uid AND a.bank_id = :ans_bid
            """
            + (" AND q.type = :q_type_f" if q_type_filter_pt else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + """
            ORDER BY day DESC
            LIMIT 120
            """),
            ans_extra_params,
        ).fetchall()

        dates = []
        for r in rows or []:
            day = (r._mapping['day'] if r else None) or None
            if not day:
                continue
            try:
                if isinstance(day, str):
                    dates.append(datetime.strptime(day, '%Y-%m-%d').date())
                else:
                    dates.append(day)
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

    # trend：最近 N 天
    trend = []
    try:
        days_back = max(1, window_days) - 1
        trend_start = (now_bj() - timedelta(days=days_back)).strftime('%Y-%m-%d 00:00:00')
        trend_params = {**ans_extra_params, 'trend_start': trend_start}
        rows = db.session.execute(
            text(f"""
            SELECT
              DATE(a.created_at) AS day,
              COUNT(*) AS answered,
              SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = :ans_uid AND a.bank_id = :ans_bid
              AND a.created_at >= :trend_start
            """
            + (" AND q.type = :q_type_f" if q_type_filter_pt else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + """
            GROUP BY day
            ORDER BY day ASC
            """),
            trend_params,
        ).fetchall()

        by_day = {}
        for r in rows or []:
            day = (r._mapping['day'] if r else None) or None
            if not day:
                continue
            by_day[str(day)] = {
                'answered': int(r._mapping['answered'] or 0),
                'correct': int(r._mapping['correct'] or 0),
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

    # by_type
    by_type = []
    try:
        total_rows = db.session.execute(
            text("SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'essay') AS type, COUNT(*) AS total "
                 + base_from + " GROUP BY type ORDER BY total DESC"),
            base_params,
        ).fetchall()
        total_map = {str(r._mapping['type']): int(r._mapping['total'] or 0) for r in (total_rows or []) if r}

        answered_rows = db.session.execute(
            text(f"""
            SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'essay') AS type,
                   COUNT(*) AS answered,
                   SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = :ans_uid AND a.bank_id = :ans_bid
            """
            + (" AND q.type = :q_type_f" if q_type_filter_pt else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + " GROUP BY q.type"),
            ans_extra_params,
        ).fetchall()
        answered_map = {
            str(r._mapping['type']): {'answered': int(r._mapping['answered'] or 0), 'correct': int(r._mapping['correct'] or 0)}
            for r in (answered_rows or []) if r
        }

        fav_rows = db.session.execute(
            text("SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'essay') AS type, COUNT(*) AS cnt "
                 + base_from + " AND f.question_id IS NOT NULL GROUP BY type"),
            base_params,
        ).fetchall()
        fav_map = {str(r._mapping['type']): int(r._mapping['cnt'] or 0) for r in (fav_rows or []) if r}

        mis_rows = db.session.execute(
            text("SELECT COALESCE(NULLIF(TRIM(q.type), ''), 'essay') AS type, COUNT(*) AS cnt "
                 + base_from + " AND m.question_id IS NOT NULL GROUP BY type"),
            base_params,
        ).fetchall()
        mis_map = {str(r._mapping['type']): int(r._mapping['cnt'] or 0) for r in (mis_rows or []) if r}

        keys = set(total_map.keys()) | set(answered_map.keys()) | set(fav_map.keys()) | set(mis_map.keys())
        for k in keys:
            total = int(total_map.get(k, 0))
            a = int((answered_map.get(k) or {}).get('answered', 0))
            c = int((answered_map.get(k) or {}).get('correct', 0))
            w = max(0, a - c)
            by_type.append({
                'q_type': portable_type_to_q_type(k, essay_q_type='简答题'),
                'portable_type': k,
                'total': total, 'answered': a, 'correct': c, 'wrong': w,
                'accuracy': round(c * 100 / a, 1) if a > 0 else 0.0,
                'completion': round(a * 100 / total, 1) if total > 0 else 0.0,
                'favorites': int(fav_map.get(k, 0)),
                'mistakes': int(mis_map.get(k, 0)),
            })

        by_type.sort(key=lambda x: (-int(x.get('answered') or 0), str(x.get('q_type') or '')))
    except Exception:
        by_type = []

    # by_difficulty
    by_difficulty = []
    try:
        total_rows = db.session.execute(
            text("SELECT COALESCE(q.difficulty, 1) AS difficulty, COUNT(*) AS total "
                 + base_from + " GROUP BY difficulty ORDER BY difficulty ASC"),
            base_params,
        ).fetchall()
        total_map = {int(r._mapping['difficulty'] or 1): int(r._mapping['total'] or 0) for r in (total_rows or []) if r}

        ans_rows = db.session.execute(
            text(f"""
            SELECT COALESCE(q.difficulty, 1) AS difficulty,
                   COUNT(*) AS answered,
                   SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM user_bank_answers a
            JOIN user_bank_questions q ON a.question_id = q.id
            {fav_join}
            {mis_join}
            WHERE a.user_id = :ans_uid AND a.bank_id = :ans_bid
            """
            + (" AND q.type = :q_type_f" if q_type_filter_pt else "")
            + tag_cond
            + (" AND f.question_id IS NOT NULL" if source == "favorites" else "")
            + (" AND m.question_id IS NOT NULL" if source == "mistakes" else "")
            + " GROUP BY q.difficulty ORDER BY difficulty ASC"),
            ans_extra_params,
        ).fetchall()
        ans_map = {
            int(r._mapping['difficulty'] or 1): {'answered': int(r._mapping['answered'] or 0), 'correct': int(r._mapping['correct'] or 0)}
            for r in (ans_rows or []) if r
        }

        def _diff_label(d: int) -> str:
            return {1: '简单', 2: '中等', 3: '困难'}.get(d, f'难度{d}')

        keys = sorted(set(total_map.keys()) | set(ans_map.keys()))
        for d in keys:
            total = int(total_map.get(d, 0))
            a = int((ans_map.get(d) or {}).get('answered', 0))
            c = int((ans_map.get(d) or {}).get('correct', 0))
            by_difficulty.append({
                'difficulty': int(d), 'label': _diff_label(int(d)),
                'total': total, 'answered': a, 'correct': c,
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
                advice.append({'title': '先建立手感', 'content': '建议先从"练习-全题库"开始，连续做 20~30 题快速熟悉题型与知识点。'})
            if completion < 35:
                advice.append({'title': '提高完成度', 'content': '当前覆盖率偏低，建议每天固定一段时间刷题，优先把"未做"题补齐。'})
            if accuracy < 65 and answered >= 10:
                advice.append({'title': '聚焦薄弱点', 'content': '正确率偏低，建议先做"错题"复盘，再回到练习巩固。'})
            if mistakes_times >= 20:
                advice.append({'title': '错题要闭环', 'content': '错题次数较多，建议用"背题"模式强化记忆，并在错因处做一次总结。'})

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

    tag_question_ids = None
    if tag and tag != 'all':
        raw_conn = db.session.connection()
        try:
            store = _load_bank_tag_store(raw_conn, bank_id, user_id)
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

    from app.core.utils.portable_question_format import any_type_to_portable_type

    type_condition = ' AND q.type = :q_type_f' if q_type else ''
    type_params = {'q_type_f': any_type_to_portable_type(q_type)} if q_type else {}

    tag_condition = ''
    tag_params = {}
    if tag_question_ids is not None:
        tag_question_ids = sorted(set(tag_question_ids))
        in_sql, tag_params = _build_named_in('q.id', tag_question_ids, 'tq')
        tag_condition = ' AND ' + in_sql

    base = {'bank_id': bank_id, 'uid': user_id, **type_params, **tag_params}

    if source == 'favorites':
        total = db.session.execute(text('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = :bank_id AND f.user_id = :uid
        ''' + type_condition + tag_condition), base).fetchone()._mapping['cnt']
    elif source == 'mistakes':
        total = db.session.execute(text('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = :bank_id AND m.user_id = :uid
        ''' + type_condition + tag_condition), base).fetchone()._mapping['cnt']
    else:
        total = db.session.execute(text(
            'SELECT COUNT(*) as cnt FROM user_bank_questions q WHERE q.bank_id = :bank_id'
            + type_condition + tag_condition), base).fetchone()._mapping['cnt']

    try:
        favorites = db.session.execute(text('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = :bank_id AND f.user_id = :uid
        ''' + type_condition + tag_condition), base).fetchone()._mapping['cnt']
    except Exception:
        favorites = 0

    try:
        mistakes = db.session.execute(text('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = :bank_id AND m.user_id = :uid
        ''' + type_condition + tag_condition), base).fetchone()._mapping['cnt']
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
