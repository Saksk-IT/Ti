# -*- coding: utf-8 -*-
"""复盘中心 — 核心页面函数 _review_center_page。"""

from __future__ import annotations

from flask import redirect, render_template, request, session

from app.core.utils.database import get_db, safe_in_clause
from app.core.utils.decorators import login_required

from .bp import main_pages_bp
from .common import _get_accessible_subject_rows
from .review_center_helpers import (
    _build_preview,
    _load_bank_tag_ids,
    _load_public_tag_ids,
    _review_center_meta,
    _url_with_params,
)


def _count_available(
    conn, *, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, type_filter: str, tag_ids,
) -> int:
    tf = (type_filter or 'all').strip()
    if isinstance(tag_ids, list) and len(tag_ids) == 0:
        return 0
    from app.core.utils.portable_question_format import any_type_to_portable_type

    if source_type == 'public':
        base = """
            SELECT COUNT(1) as cnt
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
              AND q.subject_id = ?
        """
        params: list = [int(uid), int(uid), int(subject_id)]
    else:
        base = """
            SELECT COUNT(1) as cnt
            FROM user_bank_questions q
            LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
            LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
            WHERE q.bank_id = ?
        """
        params = [int(uid), int(uid), int(bank_id)]

    if kind == 'favorites':
        base += " AND f.id IS NOT NULL"
    elif kind == 'mistakes':
        base += " AND m.id IS NOT NULL"
    if tf != 'all':
        base += " AND q.type = ?"
        params.append(any_type_to_portable_type(tf))
    if isinstance(tag_ids, list):
        base, params = safe_in_clause('q.id', tag_ids, base, params)

    row = conn.execute(base, params).fetchone()
    return int(row['cnt'] or 0) if row else 0


def _load_bank_meta(conn, *, uid: int, bank_id: int) -> tuple[str, list, list] | None:
    """加载个人题库元数据，返回 (scope_name, types, tags) 或 None（无权限）。"""
    from app.modules.user_bank.routes.api import check_bank_access, _load_bank_tag_store

    has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
    if not has_access:
        return None

    row = conn.execute(
        "SELECT id, name FROM user_question_banks WHERE id = ? AND status = 1",
        (int(bank_id),),
    ).fetchone()
    scope_name = str(row['name'] if row else f"题库{bank_id}")

    types: list = []
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT type as p_type
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY type
            """,
            (int(bank_id),),
        ).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        types = [
            portable_type_to_q_type((r['p_type'] or ''))
            for r in (rows or []) if r and r['p_type']
        ]
        types = [t for t in types if t]
    except Exception:
        types = []

    tags: list = []
    try:
        store = _load_bank_tag_store(conn, int(bank_id), int(uid))
        tag_counts = {t: 0 for t in (store.get('tags') or [])}
        for _qid, tlist in (store.get('question_tags', {}) or {}).items():
            if not isinstance(tlist, list):
                continue
            for t in tlist:
                if t in tag_counts:
                    tag_counts[t] += 1
        tags = [{'name': t, 'count': tag_counts.get(t, 0)} for t in (store.get('tags') or [])]
    except Exception:
        tags = []

    return scope_name, types, tags


def _build_tip_items(
    *, data_tips: list, tab_urls: dict, base_url: str, ctx: dict,
    q_type: str, tag: str, shuffle_questions: bool, shuffle_options: bool,
    quiz_url: str, memo_url: str,
) -> list[dict]:
    """将纯文本 tips 转换为带行动按钮的 tip_items。"""
    try:
        tip_items = []
        for t in data_tips or []:
            text = str(t if isinstance(t, str) else (t.get('text', '') if isinstance(t, dict) else '')).strip()
            if not text:
                continue

            action_label = '去练习'
            action_url = (tab_urls or {}).get('practice') or _url_with_params(
                base_url,
                {**ctx, 'tab': 'practice', 'type': q_type, 'tag': tag,
                 'shuffle_questions': 1 if shuffle_questions else 0,
                 'shuffle_options': 1 if shuffle_options else 0},
            )

            qt = ''
            if '：' in text and '（' in text:
                try:
                    qt = text.split('：', 1)[1].split('（', 1)[0].strip()
                except Exception:
                    qt = ''

            if qt:
                action_label = '按该题型开练'
                action_url = _url_with_params(
                    base_url,
                    {**ctx, 'tab': 'practice', 'type': qt, 'tag': tag,
                     'shuffle_questions': 1 if shuffle_questions else 0,
                     'shuffle_options': 1 if shuffle_options else 0},
                )
            elif '背题模式' in text:
                action_label = '开始背题'
                action_url = memo_url
            elif '开始刷题' in text:
                action_label = '开始刷题'
                action_url = quiz_url
            elif '打乱题目' in text:
                action_label = '开启打乱题目'
                action_url = _url_with_params(
                    base_url,
                    {**ctx, 'tab': 'practice', 'type': q_type, 'tag': tag,
                     'shuffle_questions': 1, 'shuffle_options': 1 if shuffle_options else 0},
                )
            elif '打乱选项' in text:
                action_label = '开启打乱选项'
                action_url = _url_with_params(
                    base_url,
                    {**ctx, 'tab': 'practice', 'type': q_type, 'tag': tag,
                     'shuffle_questions': 1 if shuffle_questions else 0, 'shuffle_options': 1},
                )
            elif '选择一个标签' in text:
                action_label = '去选标签'
                action_url = _url_with_params(
                    base_url,
                    {**ctx, 'tab': 'practice', 'type': q_type, 'tag': 'all',
                     'shuffle_questions': 1 if shuffle_questions else 0,
                     'shuffle_options': 1 if shuffle_options else 0},
                )

            tip_items.append({'text': text, 'action_label': action_label, 'action_url': action_url})
        return tip_items
    except Exception:
        return data_tips or []


def _review_center_page(kind: str):
    uid = session.get('user_id')
    conn = get_db()

    meta = _review_center_meta(kind)
    kind = meta['kind']

    tab = (request.args.get('tab') or 'practice').strip().lower()
    if tab not in ('practice', 'search', 'data'):
        tab = 'practice'

    q_type = (request.args.get('type') or 'all').strip()
    tag = (request.args.get('tag') or 'all').strip()
    keyword = (request.args.get('keyword') or '').strip()

    shuffle_questions = str(request.args.get('shuffle_questions') or '0').strip() in ('1', 'true', 'yes', 'on')
    shuffle_options = str(request.args.get('shuffle_options') or '0').strip() in ('1', 'true', 'yes', 'on')

    bank_id = 0
    try:
        bank_id = int(request.args.get('bank_id') or 0)
    except Exception:
        bank_id = 0
    subject_name = (request.args.get('subject') or '').strip()

    source_type = 'bank' if bank_id > 0 else 'public'

    subject_id = None
    scope_name = ''
    scope_label = '个人' if source_type == 'bank' else '公共'
    warning = ''

    types: list = []
    tags: list = []

    # ── 加载题库元数据 + 题型 + 标签 ──
    if source_type == 'public':
        subjects_meta = _get_accessible_subject_rows(conn, uid)
        subject_row = next((s for s in (subjects_meta or []) if str(s.get('name') or '') == subject_name), None)
        if not subject_row:
            return redirect('/mistakes' if kind == 'mistakes' else ('/favorites' if kind == 'favorites' else '/tags'))

        subject_id = int(subject_row['id'])
        scope_name = str(subject_row.get('name') or '')

        try:
            rows = conn.execute(
                """
                SELECT DISTINCT q.type as p_type
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE q.subject_id = ?
                  AND (s.is_locked=0 OR s.is_locked IS NULL)
                ORDER BY q.type
                """,
                (subject_id,),
            ).fetchall()
            from app.core.utils.portable_question_format import portable_type_to_q_type
            types = [
                portable_type_to_q_type((r['p_type'] or ''))
                for r in (rows or []) if r and r['p_type']
            ]
            types = [t for t in types if t]
        except Exception:
            types = []

        try:
            from app.modules.quiz.services.question_tags_service import list_user_tags
            tags = list_user_tags(conn, int(uid), int(subject_id))
        except Exception:
            tags = []
    else:
        _types_tags = _load_bank_meta(conn, uid=uid, bank_id=bank_id)
        if _types_tags is None:
            return redirect('/user/banks')
        scope_name, types, tags = _types_tags

    # ── 筛选校验 ──
    if q_type != 'all' and q_type not in (types or []):
        q_type = 'all'
    if shuffle_options and q_type not in ('all', '选择题', '多选题'):
        shuffle_options = False

    tag_ids = None
    if source_type == 'public':
        tag_ids = _load_public_tag_ids(conn, int(uid), tag)
    else:
        tag_ids = _load_bank_tag_ids(conn, int(uid), int(bank_id), tag)

    if kind == 'tags' and isinstance(tag_ids, list) and len(tag_ids) == 0:
        warning = warning or '当前标签下暂无题目，请先在刷题页给题目打上该标签。'

    count_kw = dict(conn=conn, uid=uid, source_type=source_type, subject_id=subject_id,
                    bank_id=bank_id, kind=kind, tag_ids=tag_ids)
    available_count = _count_available(**count_kw, type_filter=q_type)

    # ── 构建 URL ──
    base_url = request.path
    ctx: dict = {}
    if source_type == 'public':
        ctx = {'source': 'public', 'subject': subject_name}
    else:
        ctx = {'source': 'user_bank', 'bank_id': bank_id}

    tab_urls = {
        'practice': _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': q_type, 'tag': tag, 'shuffle_questions': 1 if shuffle_questions else 0, 'shuffle_options': 1 if shuffle_options else 0}),
        'search': _url_with_params(base_url, {**ctx, 'tab': 'search', 'type': q_type, 'tag': tag, 'keyword': keyword}),
        'data': _url_with_params(base_url, {**ctx, 'tab': 'data', 'type': q_type, 'tag': tag}),
    }
    search_clear_url = _url_with_params(base_url, {**ctx, 'tab': 'search', 'type': q_type, 'tag': tag})
    reset_url = _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': 'all', 'tag': 'all', 'shuffle_questions': 0, 'shuffle_options': 0})

    def _build_quiz_url(mode: str) -> str:
        params: dict = {'mode': mode}
        if source_type == 'public':
            params['subject'] = subject_name
        else:
            params['bank_id'] = bank_id
        if q_type and q_type != 'all':
            params['type'] = q_type
        if kind in ('mistakes', 'favorites'):
            params['source'] = kind
        if tag and tag.lower() != 'all':
            params['tag'] = tag
        if shuffle_questions:
            params['shuffle_questions'] = 1
        if shuffle_options:
            params['shuffle_options'] = 1
        return _url_with_params('/quiz', params)

    quiz_url = _build_quiz_url('quiz')
    memo_url = _build_quiz_url('memo')

    # ── 搜索 tab ──
    search_questions: list = []
    search_total = 0
    if tab == 'search' and keyword:
        page = 1
        try:
            page = int(request.args.get('page') or 1)
        except Exception:
            page = 1

        from .review_center_search import load_search_results
        search_questions, search_total = load_search_results(
            conn=conn, uid=uid, source_type=source_type, subject_id=subject_id,
            bank_id=bank_id, kind=kind, q_type=q_type, tag=tag, tag_ids=tag_ids,
            keyword=keyword, page=page, per_page=20, quiz_url=quiz_url,
        )

    # ── 题型分布（所有 tab 都需要） ──
    data_total = _count_available(**count_kw, type_filter='all')
    type_dist: list = []
    data_type_count = 0
    try:
        from .review_center_data import load_type_distribution
        type_dist, data_type_count = load_type_distribution(
            conn=conn, uid=uid, source_type=source_type, subject_id=subject_id,
            bank_id=bank_id, kind=kind, tag_ids=tag_ids, tag=tag,
            q_type=q_type, base_url=base_url, ctx=ctx,
        )
    except Exception:
        type_dist = []
        data_type_count = 0

    # ── data tab ──
    data_answer = {
        'answered': 0, 'correct': 0, 'accuracy': 0.0,
        'answered_7d': 0, 'correct_7d': 0, 'accuracy_7d': 0.0,
        'answered_30d': 0, 'correct_30d': 0, 'accuracy_30d': 0.0,
    }
    data_activity: list = []
    data_fav = {'count': 0, 'new_7d': 0, 'new_30d': 0}
    data_mis = {'count': 0, 'times': 0, 'new_7d': 0, 'new_30d': 0, 'active_7d': 0}
    data_tips: list = []
    data_state = {
        'total': 0, 'answered': 0, 'correct': 0, 'wrong': 0, 'unanswered': 0,
        'pct_correct': 0.0, 'pct_wrong': 0.0, 'pct_unanswered': 0.0,
    }
    mistake_buckets: list = []
    tag_dist: list = []
    data_items: list = []

    if tab == 'data':
        from .review_center_data import load_data_tab
        result = load_data_tab(
            conn=conn, uid=uid, source_type=source_type, subject_id=subject_id,
            bank_id=bank_id, kind=kind, q_type=q_type, tag=tag, tag_ids=tag_ids,
            tags=tags, available_count=available_count, data_total=data_total,
            base_url=base_url, ctx=ctx,
        )
        data_answer = result['data_answer']
        data_activity = result['data_activity']
        data_fav = result['data_fav']
        data_mis = result['data_mis']
        data_tips = result['data_tips']
        data_state = result['data_state']
        mistake_buckets = result['mistake_buckets']
        tag_dist = result['tag_dist']
        data_items = result['data_items']

    # ── tips → 行动按钮 ──
    data_tips = _build_tip_items(
        data_tips=data_tips, tab_urls=tab_urls, base_url=base_url,
        ctx=ctx, q_type=q_type, tag=tag,
        shuffle_questions=shuffle_questions, shuffle_options=shuffle_options,
        quiz_url=quiz_url, memo_url=memo_url,
    )

    return render_template(
        'main/review/review_center.html',
        page_title=meta['title'],
        page_subtitle=meta['subtitle'],
        kind=kind,
        tab=tab,
        base_url=base_url,
        tab_urls=tab_urls,
        search_clear_url=search_clear_url,
        reset_url=reset_url,
        source_type=source_type,
        scope_label=scope_label,
        scope_name=scope_name,
        subject_name=subject_name,
        bank_id=bank_id,
        types=types or [],
        tags=tags or [],
        q_type=q_type or 'all',
        tag=tag or 'all',
        shuffle_questions=shuffle_questions,
        shuffle_options=shuffle_options,
        available_count=available_count,
        warning=warning,
        quiz_url=quiz_url,
        memo_url=memo_url,
        keyword=keyword,
        search_questions=search_questions,
        search_total=search_total,
        data_total=data_total,
        data_type_count=data_type_count,
        type_dist=type_dist,
        data_answer=data_answer,
        data_activity=data_activity,
        data_fav=data_fav,
        data_mis=data_mis,
        data_tips=data_tips,
        data_state=data_state,
        mistake_buckets=mistake_buckets,
        tag_dist=tag_dist,
        data_items=data_items,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )

