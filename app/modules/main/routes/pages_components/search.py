# -*- coding: utf-8 -*-

from flask import current_app, render_template, request, session

from app.core.extensions import db
from sqlalchemy import text

from .bp import main_pages_bp

SEARCH_TABS = {"all", "questions", "forum"}
QUESTION_PER_PAGE = 20
FORUM_PER_PAGE = 10


@main_pages_bp.route('/search')
def search_page():
    """搜索页面 - 支持高级搜索选项"""
    keyword = request.args.get('keyword', '').strip()
    subject_filter = request.args.get('subject', '').strip()
    type_filter = request.args.get('type', '').strip()
    active_tab = (request.args.get('tab', 'all') or 'all').strip().lower()
    if active_tab not in SEARCH_TABS:
        active_tab = 'all'

    legacy_page = request.args.get('page', type=int)
    raw_question_page = request.args.get('question_page', type=int)
    raw_forum_page = request.args.get('forum_page', type=int)
    question_page = raw_question_page or 1
    forum_page = raw_forum_page or 1
    if legacy_page and legacy_page > 0:
        if active_tab == 'forum' and raw_forum_page is None:
            forum_page = legacy_page
        elif active_tab == 'questions' and raw_question_page is None:
            question_page = legacy_page
        elif active_tab == 'all' and raw_question_page is None:
            question_page = legacy_page

    uid = session.get('user_id') or -1
    user_id = session.get('user_id')
    question_page = max(question_page, 1)
    forum_page = max(forum_page, 1)

    # 获取所有科目和题型用于筛选下拉框（添加权限过滤）
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.core.utils.portable_question_format import portable_type_to_q_type, q_type_to_portable_type

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
            forum_posts=[],
            subjects=subjects,
            q_types=q_types,
            subject=subject_filter,
            q_type=type_filter,
            active_tab=active_tab,
            question_page=1,
            forum_page=1,
            question_total=0,
            question_total_pages=0,
            forum_total=0,
            forum_total_pages=0,
            all_total=0,
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
    question_total = db.session.execute(text(count_sql), params).fetchone()[0]
    question_total_pages = (
        (question_total + QUESTION_PER_PAGE - 1) // QUESTION_PER_PAGE
        if question_total > 0 else 0
    )

    # 确保页码有效
    if question_total_pages > 0 and question_page > question_total_pages:
        question_page = question_total_pages

    # 添加排序和分页
    sql = sql_base + " ORDER BY q.id DESC LIMIT :limit OFFSET :offset"
    params['limit'] = QUESTION_PER_PAGE
    params['offset'] = (question_page - 1) * QUESTION_PER_PAGE

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

    forum_posts = []
    forum_total = 0
    forum_total_pages = 0
    if user_id:
        try:
            from app.modules.forum.services import post_service

            forum_result = post_service.get_posts(
                sort='hot',
                keyword=keyword,
                page=forum_page,
                per_page=FORUM_PER_PAGE,
                user_id=user_id,
            )
            forum_posts = list(forum_result.get('posts') or [])
            forum_total = int(forum_result.get('total') or 0)
            forum_per_page = int(forum_result.get('per_page') or FORUM_PER_PAGE) or FORUM_PER_PAGE
            forum_total_pages = (forum_total + forum_per_page - 1) // forum_per_page if forum_total > 0 else 0

            if forum_total_pages > 0 and forum_page > forum_total_pages:
                forum_page = forum_total_pages
                forum_result = post_service.get_posts(
                    sort='hot',
                    keyword=keyword,
                    page=forum_page,
                    per_page=FORUM_PER_PAGE,
                    user_id=user_id,
                )
                forum_posts = list(forum_result.get('posts') or [])
        except Exception:
            current_app.logger.error('全局搜索读取论坛结果失败', exc_info=True)
            forum_posts = []
            forum_total = 0
            forum_total_pages = 0

    all_total = question_total + forum_total

    return render_template(
        'main/search/search.html',
        keyword=keyword,
        questions=questions,
        forum_posts=forum_posts,
        subjects=subjects,
        q_types=q_types,
        subject=subject_filter,
        q_type=type_filter,
        active_tab=active_tab,
        question_page=question_page,
        forum_page=forum_page,
        question_total=question_total,
        question_total_pages=question_total_pages,
        forum_total=forum_total,
        forum_total_pages=forum_total_pages,
        all_total=all_total,
        search_history=[],
        logged_in=bool(session.get('user_id')),
        username=session.get('username'),
    )
