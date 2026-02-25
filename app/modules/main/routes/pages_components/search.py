# -*- coding: utf-8 -*-
import json

from flask import render_template, request, session

from app.core.extensions import db
from sqlalchemy import text

from .bp import main_pages_bp


@main_pages_bp.route('/search')
def search_page():
    """搜索页面 - 支持高级搜索选项"""
    keyword = request.args.get('keyword', '').strip()
    subject_filter = request.args.get('subject', '').strip()
    type_filter = request.args.get('type', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示数量

    uid = session.get('user_id') or -1

    # 获取所有科目和题型用于筛选下拉框（添加权限过滤）
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.core.utils.portable_question_format import portable_type_to_q_type, q_type_to_portable_type

    user_id = session.get('user_id')
    accessible_subject_ids = []
    try:
        if user_id:
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if accessible_subject_ids:
                placeholders = ','.join([f':sid_{i}' for i in range(len(accessible_subject_ids))])
                sid_params = {f'sid_{i}': sid for i, sid in enumerate(accessible_subject_ids)}
                subjects = [
                    row[0]
                    for row in db.session.execute(
                        text(f"SELECT name FROM subjects WHERE id IN ({placeholders}) AND (is_locked=false OR is_locked IS NULL)"),
                        sid_params,
                    ).fetchall()
                ]
            else:
                subjects = []
        else:
            subjects = []  # 未登录用户返回空列表

        rows = db.session.execute(text("SELECT DISTINCT type FROM questions")).fetchall()
        q_types = [
            portable_type_to_q_type((r[0] or ''))
            for r in rows
            if r and r[0]
        ]
        q_types = sorted(list({t for t in q_types if t}))
    except Exception:
        subjects = []
        q_types = []
        accessible_subject_ids = []

    # 如果没有关键词，显示空的搜索页面
    if not keyword:
        return render_template(
            'main/search/search.html',
            keyword='',
            questions=[],
            subjects=subjects,
            q_types=q_types,
            subject=subject_filter,
            q_type=type_filter,
            page=1,
            total_pages=0,
            search_history=[],
            logged_in=bool(session.get('user_id')),
            username=session.get('username'),
        )

    # 构建搜索SQL（使用命名参数）
    sql_base = """
        SELECT q.*, s.name as subject,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = :uid
        LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = :uid
        WHERE (q.content LIKE :search_term OR q.analysis LIKE :search_term OR q.options LIKE :search_term OR q.answer LIKE :search_term)
        AND (s.is_locked=false OR s.is_locked IS NULL)
    """

    search_term = f'%{keyword}%'
    params = {'uid': uid, 'search_term': search_term}

    # 添加权限过滤：只搜索用户可访问的科目
    if user_id:
        if accessible_subject_ids:
            placeholders = ','.join([f':asid_{i}' for i in range(len(accessible_subject_ids))])
            for i, sid in enumerate(accessible_subject_ids):
                params[f'asid_{i}'] = sid
            sql_base += f" AND q.subject_id IN ({placeholders})"
        else:
            # 如果没有可访问的科目，返回空结果
            sql_base += " AND 1=0"
    else:
        # 未登录用户：返回空结果
        sql_base += " AND 1=0"

    # 添加科目筛选
    if subject_filter:
        sql_base += " AND s.name = :subject_filter"
        params['subject_filter'] = subject_filter

    # 添加题型筛选
    if type_filter:
        sql_base += " AND q.type = :type_filter"
        params['type_filter'] = q_type_to_portable_type(type_filter)

    # 先获取总数
    count_sql = f"SELECT COUNT(*) FROM ({sql_base}) AS sub"
    total_count = db.session.execute(text(count_sql), params).fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0

    # 确保页码有效
    if page < 1:
        page = 1
    if total_pages > 0 and page > total_pages:
        page = total_pages

    # 添加排序和分页
    sql = sql_base + " ORDER BY q.id DESC LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = (page - 1) * per_page

    rows = db.session.execute(text(sql), params).fetchall()

    questions = []
    for row in rows:
        from app.core.utils.pqf_rows import pqf_row_to_internal

        q = pqf_row_to_internal(row, scope="question_center")

        # 提前处理答案和选项
        correct_answer_key = str(q.get('answer', '')).strip()
        q['full_answer'] = correct_answer_key  # 默认答案为标识符

        options_list = q.get('options') or []
        if isinstance(options_list, list):
            new_options = []
            options_map = {}
            for item_str in options_list:
                item_str = str(item_str or '')
                delimiter = '、' if '、' in item_str else '.'
                parts = item_str.split(delimiter, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    new_options.append({'key': key, 'value': value})
                    options_map[key] = value
            q['options'] = new_options

            if correct_answer_key in options_map:
                q['full_answer'] = f"{correct_answer_key}. {options_map[correct_answer_key]}"
        else:
            q['options'] = []
        questions.append(q)

    return render_template(
        'main/search/search.html',
        keyword=keyword,
        questions=questions,
        subjects=subjects,
        q_types=q_types,
        subject=subject_filter,
        q_type=type_filter,
        page=page,
        total_pages=total_pages,
        search_history=[],
        logged_in=bool(session.get('user_id')),
        username=session.get('username'),
    )
