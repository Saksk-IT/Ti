# -*- coding: utf-8 -*-

"""用户题库：题目管理 API"""

import json

from flask import request, jsonify

from app.core.utils.database import get_db, safe_in_clause
from app.core.utils.decorators import auth_required, current_user_id

from .api_base import user_bank_api_bp, check_bank_access
from .api_tags import _load_bank_tag_store


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
        from app.core.utils.portable_question_format import any_type_to_portable_type

        where += ' AND q.type = ?'
        where_params.append(any_type_to_portable_type(q_type))

    if keyword:
        term = f'%{keyword}%'
        where += ' AND (q.content LIKE ? OR q.analysis LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)'
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

    from app.core.utils.pqf_rows import pqf_row_to_internal

    questions = []
    for r in rows or []:
        q = pqf_row_to_internal(r, scope='user_bank')
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
    from app.core.utils.portable_question_sync import build_portable_columns

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

    pqf = build_portable_columns(
        q_id=None,
        q_type=q_type,
        content=content,
        options=options or [],
        answer=answer,
        explanation=explanation,
        difficulty=difficulty,
        tags=None,
    )

    cursor = conn.execute(
        '''
        INSERT INTO user_bank_questions
        (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
        ''',
        (
            bank_id,
            user_id,
            pqf['type'] or 'essay',
            pqf['content'] or '',
            pqf['options'] or '[]',
            pqf['answer'] or '[]',
            pqf['analysis'] or '',
            pqf['tags'] or '[]',
            int(pqf.get('difficulty') or 1),
            bank_id,
        ),
    )

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

    from app.core.utils.pqf_rows import pqf_row_to_internal

    return jsonify({'code': 0, 'data': pqf_row_to_internal(row, scope='user_bank')})


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
        'SELECT id, source_type, type, content, options, answer, analysis, difficulty FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 非自建题目禁止编辑
    if question['source_type'] != 'custom':
        return jsonify({'code': 1, 'message': '非自建题目不能编辑，请删除后重新添加'}), 400

    data = request.get_json() or {}
    from app.core.utils.pqf_rows import pqf_row_to_internal
    from app.core.utils.portable_question_sync import build_portable_columns

    current = pqf_row_to_internal(question, scope='user_bank')

    next_q_type = str(data.get('q_type') if 'q_type' in data else current.get('q_type') or '').strip()
    next_content = str(data.get('content') if 'content' in data else current.get('content') or '').strip()
    next_options = data.get('options') if 'options' in data else (current.get('options') or [])
    next_answer_raw = data.get('answer') if 'answer' in data else (current.get('answer') or '')
    next_explanation = str(data.get('explanation') if 'explanation' in data else current.get('explanation') or '').strip()
    next_difficulty = data.get('difficulty') if 'difficulty' in data else (current.get('difficulty') or 1)

    if not next_content:
        return jsonify({'code': 1, 'message': '题干不能为空'}), 400
    if not next_q_type:
        return jsonify({'code': 1, 'message': '题型不能为空'}), 400

    next_answer = _normalize_answer_for_storage(next_q_type, next_answer_raw)
    if next_options is None:
        next_options = []

    pqf = build_portable_columns(
        q_id=int(question_id),
        q_type=next_q_type,
        content=next_content,
        options=next_options,
        answer=next_answer,
        explanation=next_explanation,
        difficulty=next_difficulty,
        tags=None,
    )

    conn.execute(
        '''
        UPDATE user_bank_questions
        SET type = ?,
            content = ?,
            options = ?,
            answer = ?,
            analysis = ?,
            tags = ?,
            difficulty = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND bank_id = ?
        ''',
        (
            pqf['type'] or 'essay',
            pqf['content'] or '',
            pqf['options'] or '[]',
            pqf['answer'] or '[]',
            pqf['analysis'] or '',
            pqf['tags'] or '[]',
            int(pqf.get('difficulty') or 1),
            int(question_id),
            int(bank_id),
        ),
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

    # 仅改难度：可走批量 SQL
    if q_type is None and difficulty is not None:
        try:
            diff = int(difficulty)
        except Exception:
            diff = 1
        diff = max(1, min(5, diff))

        placeholders2 = ','.join(['?'] * len(editable_ids))
        conn.execute(
            f'''
            UPDATE user_bank_questions
            SET difficulty = ?, updated_at = CURRENT_TIMESTAMP
            WHERE bank_id = ? AND id IN ({placeholders2})
            ''',
            [diff, bank_id, *editable_ids],
        )
        conn.commit()
    else:
        # 改题型（可能同时改难度）：逐题重算 PQF，避免 type/content/answer 不一致
        from app.core.utils.pqf_rows import pqf_row_to_internal
        from app.core.utils.portable_question_sync import build_portable_columns

        qt = None
        if q_type is not None:
            qt = str(q_type or '').strip()
            if not qt:
                return jsonify({'code': 1, 'message': '题型不能为空'}), 400

        diff = None
        if difficulty is not None:
            try:
                diff = int(difficulty)
            except Exception:
                diff = 1
            diff = max(1, min(5, diff))

        placeholders2 = ','.join(['?'] * len(editable_ids))
        rows = conn.execute(
            f'''
            SELECT id, type, content, options, answer, analysis, difficulty
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders2})
            ''',
            [bank_id, *editable_ids],
        ).fetchall()

        for r in rows or []:
            cur = pqf_row_to_internal(r, scope='user_bank')
            next_qt = qt if qt is not None else (cur.get('q_type') or '')
            next_diff = diff if diff is not None else (cur.get('difficulty') or 1)
            pqf = build_portable_columns(
                q_id=int(cur.get('id') or 0),
                q_type=next_qt,
                content=cur.get('content') or '',
                options=cur.get('options') or [],
                answer=cur.get('answer') or '',
                explanation=cur.get('explanation') or '',
                difficulty=next_diff,
                tags=None,
            )
            conn.execute(
                '''
                UPDATE user_bank_questions
                SET type = ?,
                    content = ?,
                    options = ?,
                    answer = ?,
                    analysis = ?,
                    tags = ?,
                    difficulty = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE bank_id = ? AND id = ?
                ''',
                (
                    pqf['type'] or 'essay',
                    pqf['content'] or '',
                    pqf['options'] or '[]',
                    pqf['answer'] or '[]',
                    pqf['analysis'] or '',
                    pqf['tags'] or '[]',
                    int(pqf.get('difficulty') or 1),
                    int(bank_id),
                    int(cur.get('id') or 0),
                ),
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
