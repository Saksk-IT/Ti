# -*- coding: utf-8 -*-

"""用户题库：题目管理 API"""

import json

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id

from .api_base import user_bank_api_bp, check_bank_access
from .api_tags import _load_bank_tag_store


def _build_named_in(col: str, values: list, prefix: str = 'in') -> tuple[str, dict]:
    """构建命名参数 IN 子句，返回 (sql_fragment, params_dict)"""
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ', '.join(f':{k}' for k in params)
    return f"{col} IN ({placeholders})", params


def _table_exists(table: str) -> bool:
    try:
        row = db.session.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = :tbl LIMIT 1"),
            {'tbl': table},
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _column_exists(table: str, column: str) -> bool:
    if not _table_exists(table):
        return False
    try:
        row = db.session.execute(
            text("SELECT 1 FROM information_schema.columns WHERE table_name = :tbl AND column_name = :col LIMIT 1"),
            {'tbl': table, 'col': column},
        ).fetchone()
        return row is not None
    except Exception:
        return False


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

    tag_question_ids = None
    if tag and tag != 'all':
        try:
            conn = db.session.connection()
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
    join_params: dict = {}
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
        fav_ts_col = 'created_at' if fav_has_created else ('id' if _column_exists('user_bank_favorites', 'id') else 'ctid')

        fav_filters = []
        if fav_has_user:
            fav_filters.append('user_id = :fav_uid')
            join_params['fav_uid'] = int(user_id)
        if fav_has_bank:
            fav_filters.append('bank_id = :fav_bid')
            join_params['fav_bid'] = int(bank_id)
        fav_where = ('WHERE ' + ' AND '.join(fav_filters)) if fav_filters else ''

        # 用聚合子查询保证每题唯一，兼容 favorites 表缺少 user_id/bank_id 的情况
        joins += f' JOIN (SELECT question_id, MAX({fav_ts_col}) AS _ts FROM user_bank_favorites {fav_where} GROUP BY question_id) f ON q.id = f.question_id'
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
        if mis_has_user:
            mis_filters.append('user_id = :mis_uid')
            join_params['mis_uid'] = int(user_id)
        if mis_has_bank:
            mis_filters.append('bank_id = :mis_bid')
            join_params['mis_bid'] = int(bank_id)
        mis_where = ('WHERE ' + ' AND '.join(mis_filters)) if mis_filters else ''

        # 显示字段：尽量选日期字段；排序字段兜底用 id/ctid
        mis_updated_expr = 'MAX(updated_at) AS updated_at' if mis_has_updated else (
            'MAX(last_updated) AS updated_at' if mis_has_last_updated else (
                'MAX(created_at) AS updated_at' if mis_has_created else 'NULL AS updated_at'
            )
        )
        mis_sort_col = 'updated_at' if mis_has_updated else ('last_updated' if mis_has_last_updated else ('created_at' if mis_has_created else ('id' if mis_has_id else 'ctid')))
        mis_sort_expr = f'MAX({mis_sort_col}) AS _ts'
        mis_created_expr = 'MIN(created_at) AS created_at' if mis_has_created else 'NULL AS created_at'
        mis_wrong_expr = 'MAX(COALESCE(wrong_count, 1)) AS wrong_count' if mis_has_wrong else 'COUNT(1) AS wrong_count'

        joins += (
            ' JOIN ('
            f'SELECT question_id, {mis_wrong_expr}, {mis_created_expr}, {mis_updated_expr}, {mis_sort_expr} '
            f'FROM user_bank_mistakes {mis_where} GROUP BY question_id'
            ') m ON q.id = m.question_id'
        )
        order_by = 'm.wrong_count DESC, m._ts DESC, q.id DESC'
        select_extras.extend([
            'm.wrong_count AS mistake_wrong_count',
            'm.created_at AS mistake_created_at',
            'm.updated_at AS mistake_updated_at',
        ])
    else:
        source = 'all'

    where = ' WHERE q.bank_id = :w_bid'
    where_params: dict = {'w_bid': int(bank_id)}

    if q_type:
        from app.core.utils.portable_question_format import any_type_to_portable_type

        where += ' AND q.type = :w_qtype'
        where_params['w_qtype'] = any_type_to_portable_type(q_type)

    if keyword:
        term = f'%{keyword}%'
        where += ' AND (q.content LIKE :w_kw1 OR q.analysis LIKE :w_kw2 OR q.options LIKE :w_kw3 OR q.answer LIKE :w_kw4)'
        where_params['w_kw1'] = term
        where_params['w_kw2'] = term
        where_params['w_kw3'] = term
        where_params['w_kw4'] = term

    if tag_question_ids is not None:
        tag_question_ids = sorted(set(tag_question_ids))
        in_fragment, in_params = _build_named_in('q.id', tag_question_ids, 'tag')
        where += f' AND {in_fragment}'
        where_params.update(in_params)

    count_sql = f'SELECT COUNT(*) as cnt FROM user_bank_questions q{joins}{where}'
    total = db.session.execute(text(count_sql), {**join_params, **where_params}).fetchone()._mapping['cnt']

    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    # 为列表补齐最后一次答题状态（便于数据面板/复盘中心呈现）
    query_params: dict = dict(join_params)
    if _table_exists('user_bank_answers') and _column_exists('user_bank_answers', 'question_id') and _column_exists('user_bank_answers', 'user_id'):
        join_sql = ' LEFT JOIN user_bank_answers a ON a.question_id = q.id AND a.user_id = :ans_uid'
        query_params['ans_uid'] = int(user_id)
        if _column_exists('user_bank_answers', 'bank_id'):
            join_sql += ' AND a.bank_id = :ans_bid'
            query_params['ans_bid'] = int(bank_id)
        query_joins = joins + join_sql

        select_extras.extend([
            ('a.is_correct' if _column_exists('user_bank_answers', 'is_correct') else 'NULL') + ' AS last_is_correct',
            ('a.created_at' if _column_exists('user_bank_answers', 'created_at') else 'NULL') + ' AS last_answered_at',
            ('a.user_answer' if _column_exists('user_bank_answers', 'user_answer') else 'NULL') + ' AS last_user_answer',
        ])
    else:
        query_joins = joins
        select_extras.extend([
            'NULL AS last_is_correct',
            'NULL AS last_answered_at',
            'NULL AS last_user_answer',
        ])

    select_sql = 'q.*'
    if select_extras:
        select_sql += ', ' + ', '.join(select_extras)

    query_sql = f'SELECT {select_sql} FROM user_bank_questions q{query_joins}{where} ORDER BY {order_by} LIMIT :q_lim OFFSET :q_off'
    rows = db.session.execute(text(query_sql), {**query_params, **where_params, 'q_lim': per_page, 'q_off': offset}).fetchall()

    # 为列表补齐收藏/错题标记 + 预览字段（便于复盘中心/搜索复用）
    q_ids = [int(r._mapping['id']) for r in rows] if rows else []
    fav_set: set = set()
    mis_set: set = set()
    if q_ids:
        if _table_exists('user_bank_favorites') and _column_exists('user_bank_favorites', 'question_id'):
            fav_where_parts = []
            fav_p: dict = {}
            if _column_exists('user_bank_favorites', 'user_id'):
                fav_where_parts.append('user_id = :fset_uid')
                fav_p['fset_uid'] = int(user_id)
            if _column_exists('user_bank_favorites', 'bank_id'):
                fav_where_parts.append('bank_id = :fset_bid')
                fav_p['fset_bid'] = int(bank_id)
            in_frag, in_p = _build_named_in('question_id', q_ids, 'fqid')
            fav_where_parts.append(in_frag)
            fav_p.update(in_p)
            fav_rows = db.session.execute(
                text('SELECT question_id FROM user_bank_favorites WHERE ' + ' AND '.join(fav_where_parts)),
                fav_p,
            ).fetchall()
            fav_set = {int(r._mapping['question_id']) for r in (fav_rows or []) if r and r._mapping['question_id'] is not None}

        if _table_exists('user_bank_mistakes') and _column_exists('user_bank_mistakes', 'question_id'):
            mis_where_parts = []
            mis_p: dict = {}
            if _column_exists('user_bank_mistakes', 'user_id'):
                mis_where_parts.append('user_id = :mset_uid')
                mis_p['mset_uid'] = int(user_id)
            if _column_exists('user_bank_mistakes', 'bank_id'):
                mis_where_parts.append('bank_id = :mset_bid')
                mis_p['mset_bid'] = int(bank_id)
            in_frag, in_p = _build_named_in('question_id', q_ids, 'mqid')
            mis_where_parts.append(in_frag)
            mis_p.update(in_p)
            mis_rows = db.session.execute(
                text('SELECT question_id FROM user_bank_mistakes WHERE ' + ' AND '.join(mis_where_parts)),
                mis_p,
            ).fetchall()
            mis_set = {int(r._mapping['question_id']) for r in (mis_rows or []) if r and r._mapping['question_id'] is not None}

    def _preview(content: str) -> str:
        try:
            import re as _re
            text_str = _re.sub(r'<[^>]+>', '', content or '').replace('\n', ' ').strip()
        except Exception:
            text_str = (content or '').replace('\n', ' ').strip()
        return text_str[:80] + '...' if len(text_str) > 80 else text_str

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
            return s.strip()

        if qt == '填空题':
            return s.strip().replace('；；', ';;').replace('；', ';')

        # 简答/计算/其它：保留多行内容，仅去掉首尾空白
        return s.strip()

    user_id = current_user_id()
    from app.core.utils.portable_question_sync import build_portable_columns

    # 检查权限
    bank = db.session.execute(
        text('SELECT id, question_count FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
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

    result = db.session.execute(
        text('''
        INSERT INTO user_bank_questions
        (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
        VALUES (:bid, :uid, :typ, :content, :options, :answer, :analysis, :tags, :difficulty, 'custom',
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = :bid2))
        RETURNING id
        '''),
        {
            'bid': bank_id,
            'uid': user_id,
            'typ': pqf['type'] or 'essay',
            'content': pqf['content'] or '',
            'options': pqf['options'] or '[]',
            'answer': pqf['answer'] or '[]',
            'analysis': pqf['analysis'] or '',
            'tags': pqf['tags'] or '[]',
            'difficulty': int(pqf.get('difficulty') or 1),
            'bid2': bank_id,
        },
    )
    new_id = result.fetchone()[0]

    # 更新题目数量
    db.session.execute(
        text('UPDATE user_question_banks SET question_count = question_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = :bid'),
        {'bid': bank_id}
    )
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': new_id
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

    row = db.session.execute(
        text('SELECT * FROM user_bank_questions WHERE id = :qid AND bank_id = :bid'),
        {'qid': question_id, 'bid': bank_id},
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

    # 检查题库权限
    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 检查题目
    question = db.session.execute(
        text('SELECT id, source_type, type, content, options, answer, analysis, difficulty FROM user_bank_questions WHERE id = :qid AND bank_id = :bid'),
        {'qid': question_id, 'bid': bank_id}
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 非自建题目禁止编辑
    if question._mapping['source_type'] != 'custom':
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

    db.session.execute(
        text('''
        UPDATE user_bank_questions
        SET type = :typ,
            content = :content,
            options = :options,
            answer = :answer,
            analysis = :analysis,
            tags = :tags,
            difficulty = :difficulty,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :qid AND bank_id = :bid
        '''),
        {
            'typ': pqf['type'] or 'essay',
            'content': pqf['content'] or '',
            'options': pqf['options'] or '[]',
            'answer': pqf['answer'] or '[]',
            'analysis': pqf['analysis'] or '',
            'tags': pqf['tags'] or '[]',
            'difficulty': int(pqf.get('difficulty') or 1),
            'qid': int(question_id),
            'bid': int(bank_id),
        },
    )
    db.session.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>', methods=['DELETE'])
@auth_required
def delete_question(bank_id, question_id):
    """删除题目"""
    user_id = current_user_id()

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    question = db.session.execute(
        text('SELECT id FROM user_bank_questions WHERE id = :qid AND bank_id = :bid'),
        {'qid': question_id, 'bid': bank_id}
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    db.session.execute(text('DELETE FROM user_bank_questions WHERE id = :qid'), {'qid': question_id})
    db.session.execute(
        text('UPDATE user_question_banks SET question_count = question_count - 1, updated_at = CURRENT_TIMESTAMP WHERE id = :bid'),
        {'bid': bank_id}
    )
    db.session.commit()

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

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    in_frag, in_p = _build_named_in('id', question_ids, 'del')
    db.session.execute(
        text(f'DELETE FROM user_bank_questions WHERE {in_frag} AND bank_id = :bid'),
        {**in_p, 'bid': bank_id}
    )

    # 重新计算题目数量
    count = db.session.execute(
        text('SELECT COUNT(*) as cnt FROM user_bank_questions WHERE bank_id = :bid'),
        {'bid': bank_id}
    ).fetchone()._mapping['cnt']

    db.session.execute(
        text('UPDATE user_question_banks SET question_count = :cnt, updated_at = CURRENT_TIMESTAMP WHERE id = :bid'),
        {'cnt': count, 'bid': bank_id}
    )
    db.session.commit()

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
    seen: set = set()
    ids = [x for x in ids if not (x in seen or seen.add(x))]

    q_type = data.get('q_type', None)
    difficulty = data.get('difficulty', None)

    if q_type is None and difficulty is None:
        return jsonify({'code': 1, 'message': '没有可更新的字段'}), 400

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    in_frag, in_p = _build_named_in('id', ids, 'buid')
    rows = db.session.execute(
        text(f'SELECT id, source_type FROM user_bank_questions WHERE bank_id = :bid AND {in_frag}'),
        {'bid': bank_id, **in_p},
    ).fetchall()

    editable_ids = []
    for r in rows or []:
        try:
            if r._mapping['source_type'] == 'custom':
                editable_ids.append(int(r._mapping['id']))
        except Exception:
            editable_ids.append(int(r._mapping['id']))

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

        in_frag2, in_p2 = _build_named_in('id', editable_ids, 'edid')
        db.session.execute(
            text(f'''
            UPDATE user_bank_questions
            SET difficulty = :diff, updated_at = CURRENT_TIMESTAMP
            WHERE bank_id = :bid AND {in_frag2}
            '''),
            {'diff': diff, 'bid': bank_id, **in_p2},
        )
        db.session.commit()
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

        in_frag2, in_p2 = _build_named_in('id', editable_ids, 'edid')
        rows = db.session.execute(
            text(f'''
            SELECT id, type, content, options, answer, analysis, difficulty
            FROM user_bank_questions
            WHERE bank_id = :bid AND {in_frag2}
            '''),
            {'bid': bank_id, **in_p2},
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
            db.session.execute(
                text('''
                UPDATE user_bank_questions
                SET type = :typ,
                    content = :content,
                    options = :options,
                    answer = :answer,
                    analysis = :analysis,
                    tags = :tags,
                    difficulty = :difficulty,
                    updated_at = CURRENT_TIMESTAMP
                WHERE bank_id = :bid AND id = :qid
                '''),
                {
                    'typ': pqf['type'] or 'essay',
                    'content': pqf['content'] or '',
                    'options': pqf['options'] or '[]',
                    'answer': pqf['answer'] or '[]',
                    'analysis': pqf['analysis'] or '',
                    'tags': pqf['tags'] or '[]',
                    'difficulty': int(pqf.get('difficulty') or 1),
                    'bid': int(bank_id),
                    'qid': int(cur.get('id') or 0),
                },
            )

        db.session.commit()

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
