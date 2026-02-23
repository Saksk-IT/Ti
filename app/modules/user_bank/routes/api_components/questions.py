# -*- coding: utf-8 -*-

import json
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, current_app

from app.core.utils.database import get_db, safe_in_clause
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


@user_bank_api_bp.route('/<int:bank_id>/questions', methods=['GET'])
@auth_required
def get_bank_questions(bank_id):
    """获取题库题目列表"""
    user_id = current_user_id()
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({'code': 401, 'message': '请先登录'}), 401
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    q_type = request.args.get('q_type', '')
    keyword = request.args.get('keyword', '').strip()
    source = (request.args.get('source') or 'all').strip().lower()  # all/favorites/mistakes
    tag = (request.args.get('tag') or '').strip()

    conn = get_db()

    def _table_exists(table: str) -> bool:
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            return bool(row and (row['name'] or '').lower() == table.lower())
        except Exception:
            return False

    def _column_exists(table: str, column: str) -> bool:
        if not _table_exists(table):
            return False
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

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
            return jsonify({
                'code': 0,
                'data': {
                    'questions': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                    'permission': permission,
                    'access_type': access_type
                }
            })

    joins = ''
    join_params = []
    order_by = 'q.id ASC'
    if _column_exists('user_bank_questions', 'sort_order'):
        order_by = 'q.sort_order ASC, q.id ASC'
    select_extras = []

    if source == 'favorites':
        if not _table_exists('user_bank_favorites') or not _column_exists('user_bank_favorites', 'question_id'):
            return jsonify({
                'code': 0,
                'data': {
                    'questions': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                    'permission': permission,
                    'access_type': access_type
                }
            })

        fav_has_user = _column_exists('user_bank_favorites', 'user_id')
        fav_has_bank = _column_exists('user_bank_favorites', 'bank_id')
        fav_has_created = _column_exists('user_bank_favorites', 'created_at')
        fav_ts_col = 'created_at' if fav_has_created else ('id' if _column_exists('user_bank_favorites', 'id') else 'rowid')

        fav_filters = []
        fav_params = []
        if fav_has_user:
            fav_filters.append('user_id = ?')
            fav_params.append(int(user_id))
        if fav_has_bank:
            fav_filters.append('bank_id = ?')
            fav_params.append(int(bank_id))
        fav_where = ('WHERE ' + ' AND '.join(fav_filters)) if fav_filters else ''

        # 用聚合子查询保证每题唯一，兼容 favorites 表缺少 user_id/bank_id 的情况
        joins += f' JOIN (SELECT question_id, MAX({fav_ts_col}) AS _ts FROM user_bank_favorites {fav_where} GROUP BY question_id) f ON q.id = f.question_id'
        join_params.extend(fav_params)
        order_by = 'f._ts DESC, q.id DESC'
        select_extras.append('f._ts AS favorite_created_at' if fav_has_created else 'NULL AS favorite_created_at')
    elif source == 'mistakes':
        if not _table_exists('user_bank_mistakes') or not _column_exists('user_bank_mistakes', 'question_id'):
            return jsonify({
                'code': 0,
                'data': {
                    'questions': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                    'permission': permission,
                    'access_type': access_type
                }
            })

        mis_has_user = _column_exists('user_bank_mistakes', 'user_id')
        mis_has_bank = _column_exists('user_bank_mistakes', 'bank_id')
        mis_has_wrong = _column_exists('user_bank_mistakes', 'wrong_count')
        mis_has_created = _column_exists('user_bank_mistakes', 'created_at')
        mis_has_updated = _column_exists('user_bank_mistakes', 'updated_at')
        mis_has_last_updated = _column_exists('user_bank_mistakes', 'last_updated')
        mis_has_id = _column_exists('user_bank_mistakes', 'id')

        mis_filters = []
        mis_params = []
        if mis_has_user:
            mis_filters.append('user_id = ?')
            mis_params.append(int(user_id))
        if mis_has_bank:
            mis_filters.append('bank_id = ?')
            mis_params.append(int(bank_id))
        mis_where = ('WHERE ' + ' AND '.join(mis_filters)) if mis_filters else ''

        # 显示字段：尽量选日期字段；排序字段兜底用 id/rowid
        mis_updated_expr = 'MAX(updated_at) AS updated_at' if mis_has_updated else (
            'MAX(last_updated) AS updated_at' if mis_has_last_updated else (
                'MAX(created_at) AS updated_at' if mis_has_created else 'NULL AS updated_at'
            )
        )
        mis_sort_col = 'updated_at' if mis_has_updated else ('last_updated' if mis_has_last_updated else ('created_at' if mis_has_created else ('id' if mis_has_id else 'rowid')))
        mis_sort_expr = f'MAX({mis_sort_col}) AS _ts'
        mis_created_expr = 'MIN(created_at) AS created_at' if mis_has_created else 'NULL AS created_at'
        mis_wrong_expr = 'MAX(COALESCE(wrong_count, 1)) AS wrong_count' if mis_has_wrong else 'COUNT(1) AS wrong_count'

        joins += (
            ' JOIN ('
            f'SELECT question_id, {mis_wrong_expr}, {mis_created_expr}, {mis_updated_expr}, {mis_sort_expr} '
            f'FROM user_bank_mistakes {mis_where} GROUP BY question_id'
            ') m ON q.id = m.question_id'
        )
        join_params.extend(mis_params)
        order_by = 'm.wrong_count DESC, m._ts DESC, q.id DESC'
        select_extras.extend([
            'm.wrong_count AS mistake_wrong_count',
            'm.created_at AS mistake_created_at',
            'm.updated_at AS mistake_updated_at',
        ])
    else:
        source = 'all'

    where = ' WHERE q.bank_id = ?'
    where_params = [int(bank_id)]

    if q_type:
        where += ' AND q.q_type = ?'
        where_params.append(q_type)

    if keyword:
        term = f'%{keyword}%'
        where += ' AND (q.content LIKE ? OR q.explanation LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)'
        where_params.extend([term, term, term, term])

    if tag_question_ids is not None:
        tag_question_ids = sorted(set(tag_question_ids))
        where, where_params = safe_in_clause('q.id', tag_question_ids, where, where_params)

    count_sql = f'SELECT COUNT(*) as cnt FROM user_bank_questions q{joins}{where}'
    total = conn.execute(count_sql, join_params + where_params).fetchone()['cnt']

    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    # 为列表补齐最后一次答题状态（便于数据面板/复盘中心呈现）
    if _table_exists('user_bank_answers') and _column_exists('user_bank_answers', 'question_id') and _column_exists('user_bank_answers', 'user_id'):
        join_sql = ' LEFT JOIN user_bank_answers a ON a.question_id = q.id AND a.user_id = ?'
        query_params = join_params + [int(user_id)]
        if _column_exists('user_bank_answers', 'bank_id'):
            join_sql += ' AND a.bank_id = ?'
            query_params.append(int(bank_id))
        query_joins = joins + join_sql

        select_extras.extend([
            ('a.is_correct' if _column_exists('user_bank_answers', 'is_correct') else 'NULL') + ' AS last_is_correct',
            ('a.created_at' if _column_exists('user_bank_answers', 'created_at') else 'NULL') + ' AS last_answered_at',
            ('a.user_answer' if _column_exists('user_bank_answers', 'user_answer') else 'NULL') + ' AS last_user_answer',
        ])
    else:
        query_joins = joins
        query_params = join_params
        select_extras.extend([
            'NULL AS last_is_correct',
            'NULL AS last_answered_at',
            'NULL AS last_user_answer',
        ])

    select_sql = 'q.*'
    if select_extras:
        select_sql += ', ' + ', '.join(select_extras)

    query_sql = f'SELECT {select_sql} FROM user_bank_questions q{query_joins}{where} ORDER BY {order_by} LIMIT ? OFFSET ?'
    rows = conn.execute(query_sql, query_params + where_params + [per_page, offset]).fetchall()

    # 为列表补齐收藏/错题标记 + 预览字段（便于复盘中心/搜索复用）
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if q_ids:
        placeholders = ','.join('?' * len(q_ids))
        if _table_exists('user_bank_favorites') and _column_exists('user_bank_favorites', 'question_id'):
            fav_where = []
            fav_params = []
            if _column_exists('user_bank_favorites', 'user_id'):
                fav_where.append('user_id = ?')
                fav_params.append(int(user_id))
            if _column_exists('user_bank_favorites', 'bank_id'):
                fav_where.append('bank_id = ?')
                fav_params.append(int(bank_id))
            fav_where.append(f'question_id IN ({placeholders})')
            fav_rows = conn.execute(
                'SELECT question_id FROM user_bank_favorites WHERE ' + ' AND '.join(fav_where),
                fav_params + q_ids,
            ).fetchall()
            fav_set = {int(r['question_id']) for r in (fav_rows or []) if r and r['question_id'] is not None}

        if _table_exists('user_bank_mistakes') and _column_exists('user_bank_mistakes', 'question_id'):
            mis_where = []
            mis_params = []
            if _column_exists('user_bank_mistakes', 'user_id'):
                mis_where.append('user_id = ?')
                mis_params.append(int(user_id))
            if _column_exists('user_bank_mistakes', 'bank_id'):
                mis_where.append('bank_id = ?')
                mis_params.append(int(bank_id))
            mis_where.append(f'question_id IN ({placeholders})')
            mis_rows = conn.execute(
                'SELECT question_id FROM user_bank_mistakes WHERE ' + ' AND '.join(mis_where),
                mis_params + q_ids,
            ).fetchall()
            mis_set = {int(r['question_id']) for r in (mis_rows or []) if r and r['question_id'] is not None}

    def _preview(content: str) -> str:
        try:
            import re as _re
            text = _re.sub(r'<[^>]+>', '', content or '').replace('\n', ' ').strip()
        except Exception:
            text = (content or '').replace('\n', ' ').strip()
        return text[:80] + '...' if len(text) > 80 else text

    questions = []
    for r in rows or []:
        q = dict(r)
        qid = int(q.get('id') or 0)
        q['is_fav'] = 1 if qid in fav_set else 0
        q['is_mistake'] = 1 if qid in mis_set else 0
        q['content_preview'] = _preview(str(q.get('content') or ''))
        questions.append(q)

    return jsonify({
        'code': 0,
        'data': {
            'questions': questions,
            'total': total,
            'page': page,
            'per_page': per_page,
            'permission': permission,
            'access_type': access_type
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/favorites/trend', methods=['GET'])
@auth_required
def get_bank_favorites_trend(bank_id: int):
    """收藏趋势：按收藏创建时间聚合（用于收藏数据面板）。"""
    from datetime import datetime, timedelta

    user_id = current_user_id()
    has_access, _permission, _access_type = check_bank_access(user_id, bank_id)
    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 30

    days_back = max(1, int(window_days)) - 1

    conn = get_db()

    def _table_exists(table: str) -> bool:
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            return bool(row and (row['name'] or '').lower() == table.lower())
        except Exception:
            return False

    def _column_exists(table: str, column: str) -> bool:
        if not _table_exists(table):
            return False
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    total = 0
    rows = []
    if _table_exists('user_bank_favorites') and _column_exists('user_bank_favorites', 'question_id') and _column_exists('user_bank_favorites', 'created_at'):
        fav_has_user = _column_exists('user_bank_favorites', 'user_id')
        fav_has_bank = _column_exists('user_bank_favorites', 'bank_id')
        try:
            if fav_has_bank:
                where_parts = ['bank_id = ?']
                params = [int(bank_id)]
                if fav_has_user:
                    where_parts.insert(0, 'user_id = ?')
                    params.insert(0, int(user_id))

                total = int(
                    conn.execute(
                        "SELECT COUNT(1) AS cnt FROM user_bank_favorites WHERE " + " AND ".join(where_parts),
                        params,
                    ).fetchone()['cnt']
                    or 0
                )

                rows = conn.execute(
                    """
                    SELECT DATE(created_at) AS day, COUNT(*) AS added
                    FROM user_bank_favorites
                    WHERE """
                    + " AND ".join(where_parts)
                    + """
                      AND created_at >= datetime('now', '+8 hours', ?)
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params + [f'-{days_back} days'],
                ).fetchall()
            else:
                where_parts = ['q.bank_id = ?']
                params = [int(bank_id)]
                if fav_has_user:
                    where_parts.append('f.user_id = ?')
                    params.append(int(user_id))

                total = int(
                    conn.execute(
                        """
                        SELECT COUNT(1) AS cnt
                        FROM user_bank_favorites f
                        JOIN user_bank_questions q ON q.id = f.question_id
                        WHERE """
                        + " AND ".join(where_parts),
                        params,
                    ).fetchone()['cnt']
                    or 0
                )

                rows = conn.execute(
                    """
                    SELECT DATE(f.created_at) AS day, COUNT(*) AS added
                    FROM user_bank_favorites f
                    JOIN user_bank_questions q ON q.id = f.question_id
                    WHERE """
                    + " AND ".join(where_parts)
                    + """
                      AND f.created_at >= datetime('now', '+8 hours', ?)
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params + [f'-{days_back} days'],
                ).fetchall()
        except Exception:
            total = 0
            rows = []

    by_day = {}
    for r in rows or []:
        day = (r['day'] if r else None) or None
        if not day:
            continue
        by_day[str(day)] = int((r['added'] if r else 0) or 0)

    start_day = today_bj() - timedelta(days=days_back)
    trend = []
    total_added = 0
    for i in range(0, days_back + 1):
        d = (start_day + timedelta(days=i)).strftime('%Y-%m-%d')
        added = int(by_day.get(d) or 0)
        total_added += added
        trend.append({'day': d, 'added': added})

    return jsonify({
        'code': 0,
        'data': {
            'bank_id': int(bank_id),
            'days': int(window_days),
            'favorites_total': total,
            'total_added': total_added,
            'trend': trend,
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/questions', methods=['POST'])
@auth_required
def add_question(bank_id):
    """添加题目（自建）"""
    def _normalize_answer_for_storage(q_type: str, answer) -> str:
        qt = (q_type or '').strip()
        s = '' if answer is None else str(answer)
        s = s.replace('\r\n', '\n').replace('\r', '\n')

        if qt in ('选择题', '多选题'):
            letters = ''.join([c for c in s if c.isalpha()]).upper()
            if qt == '选择题':
                return (letters[:1] or '').strip()
            # 多选题：去重并排序，确保跨端一致（小程序/网页/考试均使用 AB… 格式）
            return ''.join(sorted(set(letters)))

        if qt == '判断题':
            v = s.strip().lower()
            if v in ('对', '正确', 'true', 't', '1', 'yes', 'y', '是', 'a'):
                return '正确'
            if v in ('错', '错误', 'false', 'f', '0', 'no', 'n', '否', 'b'):
                return '错误'
            # 兜底：保留原值（避免误伤非标准存量数据）
            return s.strip()

        if qt == '填空题':
            return s.strip().replace('；；', ';;').replace('；', ';')

        # 简答/计算/其它：保留多行内容，仅去掉首尾空白
        return s.strip()

    user_id = current_user_id()
    conn = get_db()

    # 检查权限
    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    q_type = (data.get('q_type') or '').strip()
    options = data.get('options')
    answer = _normalize_answer_for_storage(q_type, data.get('answer'))
    explanation = (data.get('explanation') or '').strip()
    difficulty = data.get('difficulty', 1)

    if not content:
        return jsonify({'code': 1, 'message': '题干不能为空'}), 400
    if not q_type:
        return jsonify({'code': 1, 'message': '题型不能为空'}), 400

    # 处理选项
    import json
    options_str = json.dumps(options, ensure_ascii=False) if options else None

    cursor = conn.execute('''
        INSERT INTO user_bank_questions
        (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, source_type, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
    ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, bank_id))

    # 更新题目数量
    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': cursor.lastrowid
        },
        'message': '添加成功'
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>', methods=['GET'])
@auth_required
def get_question_detail(bank_id, question_id):
    """获取题目详情（单题）"""
    user_id = current_user_id()
    try:
        user_id = int(user_id)
    except Exception:
        return jsonify({'code': 401, 'message': '请先登录'}), 401

    has_access, _permission, _access_type = check_bank_access(user_id, bank_id)
    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()
    row = conn.execute(
        'SELECT * FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id),
    ).fetchone()

    if not row:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    return jsonify({'code': 0, 'data': dict(row)})


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>', methods=['PUT'])
@auth_required
def update_question(bank_id, question_id):
    """编辑题目"""
    def _normalize_answer_for_storage(q_type: str, answer) -> str:
        qt = (q_type or '').strip()
        s = '' if answer is None else str(answer)
        s = s.replace('\r\n', '\n').replace('\r', '\n')

        if qt in ('选择题', '多选题'):
            letters = ''.join([c for c in s if c.isalpha()]).upper()
            if qt == '选择题':
                return (letters[:1] or '').strip()
            return ''.join(sorted(set(letters)))

        if qt == '判断题':
            v = s.strip().lower()
            if v in ('对', '正确', 'true', 't', '1', 'yes', 'y', '是', 'a'):
                return '正确'
            if v in ('错', '错误', 'false', 'f', '0', 'no', 'n', '否', 'b'):
                return '错误'
            return s.strip()

        if qt == '填空题':
            return s.strip().replace('；；', ';;').replace('；', ';')

        return s.strip()

    user_id = current_user_id()
    conn = get_db()

    # 检查题库权限
    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 检查题目
    question = conn.execute(
        'SELECT id, source_type, q_type FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 非自建题目禁止编辑
    if question['source_type'] != 'custom':
        return jsonify({'code': 1, 'message': '非自建题目不能编辑，请删除后重新添加'}), 400

    data = request.get_json() or {}
    effective_q_type = (data.get('q_type') or (question['q_type'] if question and 'q_type' in question.keys() else '') or '').strip()
    updates = []
    params = []

    if 'content' in data:
        content = (data['content'] or '').strip()
        if not content:
            return jsonify({'code': 1, 'message': '题干不能为空'}), 400
        updates.append('content = ?')
        params.append(content)

    if 'q_type' in data:
        updates.append('q_type = ?')
        params.append((data['q_type'] or '').strip())

    if 'options' in data:
        import json
        updates.append('options = ?')
        params.append(json.dumps(data['options'], ensure_ascii=False) if data['options'] else None)

    if 'answer' in data:
        updates.append('answer = ?')
        params.append(_normalize_answer_for_storage(effective_q_type, data['answer']))

    if 'explanation' in data:
        updates.append('explanation = ?')
        params.append((data['explanation'] or '').strip())

    if 'difficulty' in data:
        updates.append('difficulty = ?')
        params.append(data['difficulty'])

    if not updates:
        return jsonify({'code': 1, 'message': '没有要更新的内容'}), 400

    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(question_id)

    conn.execute(
        f'UPDATE user_bank_questions SET {", ".join(updates)} WHERE id = ?',
        params
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>', methods=['DELETE'])
@auth_required
def delete_question(bank_id, question_id):
    """删除题目"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    conn.execute('DELETE FROM user_bank_questions WHERE id = ?', (question_id,))
    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count - 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '删除成功'})


@user_bank_api_bp.route('/<int:bank_id>/questions/batch_delete', methods=['POST'])
@auth_required
def batch_delete_questions(bank_id):
    """批量删除题目"""
    user_id = current_user_id()
    data = request.get_json() or {}
    question_ids = data.get('question_ids', [])

    if not question_ids:
        return jsonify({'code': 1, 'message': '请选择要删除的题目'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    placeholders = ','.join(['?'] * len(question_ids))
    conn.execute(
        f'DELETE FROM user_bank_questions WHERE id IN ({placeholders}) AND bank_id = ?',
        question_ids + [bank_id]
    )

    # 重新计算题目数量
    count = conn.execute(
        'SELECT COUNT(*) as cnt FROM user_bank_questions WHERE bank_id = ?',
        (bank_id,)
    ).fetchone()['cnt']

    conn.execute(
        'UPDATE user_question_banks SET question_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (count, bank_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': f'成功删除{len(question_ids)}道题目'})


@user_bank_api_bp.route('/<int:bank_id>/questions/batch_update', methods=['POST'])
@auth_required
def batch_update_questions(bank_id):
    """批量更新题目（题型/难度）"""
    user_id = current_user_id()
    data = request.get_json() or {}
    question_ids = data.get('question_ids', [])

    if not question_ids or not isinstance(question_ids, list):
        return jsonify({'code': 1, 'message': '请选择要操作的题目'}), 400

    ids = []
    for v in question_ids:
        try:
            ids.append(int(v))
        except Exception:
            continue
    if not ids:
        return jsonify({'code': 1, 'message': '请选择要操作的题目'}), 400

    # 去重但保留顺序
    seen = set()
    ids = [x for x in ids if not (x in seen or seen.add(x))]

    q_type = data.get('q_type', None)
    difficulty = data.get('difficulty', None)

    if q_type is None and difficulty is None:
        return jsonify({'code': 1, 'message': '没有可更新的字段'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    placeholders = ','.join(['?'] * len(ids))
    rows = conn.execute(
        f'SELECT id, source_type FROM user_bank_questions WHERE bank_id = ? AND id IN ({placeholders})',
        [bank_id, *ids],
    ).fetchall()

    editable_ids = []
    for r in rows or []:
        try:
            if r['source_type'] == 'custom':
                editable_ids.append(int(r['id']))
        except Exception:
            editable_ids.append(int(r['id']))

    editable_ids = [x for x in editable_ids if x in set(ids)]
    if not editable_ids:
        return jsonify({'code': 1, 'message': '选中的题目均不可编辑（仅自建题目允许修改）'}), 400

    updates = []
    params = []

    if q_type is not None:
        qt = str(q_type or '').strip()
        if not qt:
            return jsonify({'code': 1, 'message': '题型不能为空'}), 400
        updates.append('q_type = ?')
        params.append(qt)

    if difficulty is not None:
        try:
            diff = int(difficulty)
        except Exception:
            diff = 1
        if diff < 1:
            diff = 1
        updates.append('difficulty = ?')
        params.append(diff)

    updates.append('updated_at = CURRENT_TIMESTAMP')

    placeholders2 = ','.join(['?'] * len(editable_ids))
    conn.execute(
        f'UPDATE user_bank_questions SET {", ".join(updates)} WHERE bank_id = ? AND id IN ({placeholders2})',
        params + [bank_id, *editable_ids],
    )
    conn.commit()

    skipped = len(ids) - len(editable_ids)
    msg = f'已更新{len(editable_ids)}道题目' + (f'，已跳过{skipped}道非自建题目' if skipped > 0 else '')
    return jsonify({
        'code': 0,
        'data': {'updated': len(editable_ids), 'skipped': skipped},
        'message': msg,
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/copy', methods=['POST'])
@auth_required
def copy_questions(bank_id):
    """复制题目功能已移除"""
    return jsonify({'code': 1, 'message': '题目复制功能已停用'}), 410


@user_bank_api_bp.route('/<int:bank_id>/questions/import', methods=['POST'])
@auth_required
def import_questions(bank_id):
    """从错题本/收藏夹导入题目"""
    user_id = current_user_id()
    data = request.get_json() or {}
    source = data.get('source')  # 'mistakes' or 'favorites'
    subject_id = data.get('subject_id')
    question_ids = data.get('question_ids', [])

    if source not in ('mistakes', 'favorites'):
        return jsonify({'code': 1, 'message': '无效的来源'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 构建查询
    if source == 'mistakes':
        query = '''
            SELECT q.id, q.content, q.q_type, q.options, q.answer, q.explanation, q.difficulty, q.image_path
            FROM questions q
            JOIN mistakes m ON q.id = m.question_id
            WHERE m.user_id = ?
        '''
        source_type = 'mistake'
    else:
        query = '''
            SELECT q.id, q.content, q.q_type, q.options, q.answer, q.explanation, q.difficulty, q.image_path
            FROM questions q
            JOIN favorites f ON q.id = f.question_id
            WHERE f.user_id = ?
        '''
        source_type = 'favorite'

    params = [user_id]

    if subject_id:
        query += ' AND q.subject_id = ?'
        params.append(subject_id)

    if question_ids:
        placeholders = ','.join(['?'] * len(question_ids))
        query += f' AND q.id IN ({placeholders})'
        params.extend(question_ids)

    questions = conn.execute(query, params).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '未找到可导入的题目'}), 404

    imported_count = 0
    for q in questions:
        conn.execute('''
            INSERT INTO user_bank_questions
            (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, image_path,
             source_type, source_question_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
        ''', (bank_id, user_id, q['content'], q['q_type'], q['options'], q['answer'],
              q['explanation'], q['difficulty'], q['image_path'], source_type, q['id'], bank_id))
        imported_count += 1

    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (imported_count, bank_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': f'成功导入{imported_count}道题目'})


@user_bank_api_bp.route('/<int:bank_id>/questions/import/json', methods=['POST'])
@auth_required
def import_questions_json(bank_id):
    """直接导入题目数据（JSON格式）"""
    user_id = current_user_id()
    data = request.get_json() or {}
    questions = data.get('questions', [])

    if not questions or not isinstance(questions, list):
        return jsonify({'code': 1, 'message': '请提供有效的题目数据'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    imported_count = 0
    errors = []

    for idx, q in enumerate(questions):
        q_type = (q.get('题型') or q.get('q_type') or '').strip()
        content = q.get('题干') or q.get('content') or ''
        answer = q.get('答案') or q.get('answer') or ''
        explanation = q.get('解析') or q.get('explanation') or ''
        difficulty = q.get('难度') or q.get('difficulty') or 1

        # 保留题干/答案/解析的缩进与换行；仅用于校验时做 strip 判断。
        content = str(content or '').replace('\r\n', '\n').replace('\r', '\n')
        answer = str(answer or '').replace('\r\n', '\n').replace('\r', '\n')
        explanation = str(explanation or '').replace('\r\n', '\n').replace('\r', '\n')

        try:
            difficulty = int(difficulty or 1)
        except Exception:
            difficulty = 1
        difficulty = max(1, min(5, difficulty))

        if not q_type or not content.strip():
            errors.append(f'第{idx+1}题: 题型或题干为空')
            continue

        # 处理选项
        options = q.get('选项') or q.get('options') or []
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except:
                options = []
        if isinstance(options, list):
            options = [str(o) for o in options]

        options_str = json.dumps(options, ensure_ascii=False) if options else None

        try:
            conn.execute('''
                INSERT INTO user_bank_questions
                (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, source_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
            ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, bank_id))
            imported_count += 1
        except Exception as e:
            errors.append(f'第{idx+1}题: 导入失败 - {str(e)}')

    # 更新题目数量
    if imported_count > 0:
        conn.execute(
            'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (imported_count, bank_id)
        )
        conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'imported': imported_count,
            'errors': errors[:10]
        },
        'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/import/word/extract', methods=['POST'])
@auth_required
def extract_questions_word_docx(bank_id: int):
    """从 Word(.docx) 提取原始文本（供前端解析/预览使用）。"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id),
    ).fetchone()
    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    filename = file.filename or ''
    if not filename or not filename.lower().endswith('.docx'):
        return jsonify({'code': 1, 'message': '请上传.docx格式的文件'}), 400

    try:
        from app.core.utils.docx_text_extractor import extract_docx_text

        raw = file.read()
        text = extract_docx_text(raw)
        return jsonify({
            'code': 0,
            'data': {
                'filename': filename,
                'text': text,
            }
        })
    except Exception as e:
        try:
            current_app.logger.exception('extract_questions_word_docx failed: %s', str(e))
        except Exception:
            pass
        return jsonify({'code': 1, 'message': f'解析失败: {str(e)}'}), 500
