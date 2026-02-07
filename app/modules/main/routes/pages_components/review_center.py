# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import current_app, redirect, render_template, request, session

from app.core.utils.database import get_db, safe_in_clause
from app.core.utils.decorators import login_required
from app.core.utils.time_utils import today_bj

from .bp import main_pages_bp
from .common import _get_accessible_subject_rows

@main_pages_bp.route('/favorites')
@login_required
def favorites_detail_page():
    """收藏：先选题库（公共题库 / 个人题库），再进入题库详情页。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='favorites',
        entry_title='收藏',
        entry_subtitle='先选择题库，再进入收藏中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/review')
@login_required
def review_entry_page():
    """复盘：错题 / 收藏 / 标签统一入口，先选题库再进入对应中心。"""
    uid = session.get('user_id')
    conn = get_db()

    kind = (request.args.get('kind') or 'mistakes').strip().lower()
    if kind not in ('mistakes', 'favorites', 'tags'):
        kind = 'mistakes'
    kind_label_map = {'mistakes': '错题', 'favorites': '收藏', 'tags': '标签'}
    kind_label = kind_label_map.get(kind, '错题')

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='review',
        entry_title='复盘',
        entry_subtitle='错题 / 收藏 / 标签 统一入口：先选择题库，再开始复盘。',
        review_kind=kind,
        review_kind_label=kind_label,
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/mistakes')
@login_required
def mistakes_detail_page():
    """错题：先选题库（公共题库 / 个人题库），再进入题库详情页。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='mistakes',
        entry_title='错题',
        entry_subtitle='先选择题库，再进入错题中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/tags')
@login_required
def tags_select_page():
    """标签：先选题库（公共题库 / 个人题库），再进入标签中心页。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='tags',
        entry_title='标签',
        entry_subtitle='先选择题库，再进入标签中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


def _review_center_meta(kind: str) -> dict:
    kind = (kind or '').strip().lower()
    if kind == 'favorites':
        return {
            'kind': 'favorites',
            'title': '收藏中心',
            'subtitle': '在当前题库范围内完成练习、搜索与数据复盘（与小程序保持同语义）。',
            'quiz_label': '开始刷题',
            'memo_label': '开始背题',
        }
    if kind == 'tags':
        return {
            'kind': 'tags',
            'title': '标签中心',
            'subtitle': '按你的标签体系聚类题目：练习、搜索与统计均可按标签过滤。',
            'quiz_label': '开始刷标签',
            'memo_label': '开始背标签',
        }
    return {
        'kind': 'mistakes',
        'title': '错题中心',
        'subtitle': '聚焦错题复盘：练习、搜索与统计均在错题范围内联动。',
        'quiz_label': '开始刷错题',
        'memo_label': '开始背错题',
    }


def _url_with_params(base: str, params: dict) -> str:
    clean = {k: v for k, v in (params or {}).items() if v is not None and str(v) != ''}
    if not clean:
        return base
    return f"{base}?{urlencode(clean)}"


def _build_preview(raw: str, limit: int = 80) -> str:
    try:
        import re as _re

        text = _re.sub(r'<[^>]+>', '', raw or '').replace('\n', ' ').strip()
    except Exception:
        text = (raw or '').replace('\n', ' ').strip()
    if len(text) > limit:
        return text[:limit] + '...'
    return text


def _load_public_tag_ids(conn, uid: int, tag: str):
    tag = (tag or '').strip()
    if not tag or tag.lower() == 'all':
        return None
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag

    ids = get_question_ids_by_tag(conn, uid, tag)
    return sorted({int(x) for x in ids}) if ids else []


def _load_bank_tag_ids(conn, uid: int, bank_id: int, tag: str):
    tag = (tag or '').strip()
    if not tag or tag.lower() == 'all':
        return None
    from app.modules.user_bank.routes.api import _load_bank_tag_store

    store = _load_bank_tag_store(conn, int(bank_id), int(uid))
    question_tags = store.get('question_tags', {}) or {}
    ids = []
    for q_id, tags in (question_tags or {}).items():
        if not isinstance(tags, list) or tag not in tags:
            continue
        try:
            ids.append(int(q_id))
        except Exception:
            continue
    return sorted(set(ids)) if ids else []


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

    types = []
    tags = []

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
                for r in (rows or [])
                if r and r['p_type']
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
        from app.modules.user_bank.routes.api import check_bank_access, _load_bank_tag_store

        has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
        if not has_access:
            return redirect('/user/banks')

        row = conn.execute(
            "SELECT id, name FROM user_question_banks WHERE id = ? AND status = 1",
            (int(bank_id),),
        ).fetchone()
        scope_name = str(row['name'] if row else f"题库{bank_id}")

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
                for r in (rows or [])
                if r and r['p_type']
            ]
            types = [t for t in types if t]
        except Exception:
            types = []

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

    # 题型筛选：仅允许可用题型，避免随意拼接
    if q_type != 'all' and q_type not in (types or []):
        q_type = 'all'

    # 与题库练习页保持一致：仅选择题/多选题支持“打乱选项”
    if shuffle_options and q_type not in ('all', '选择题', '多选题'):
        shuffle_options = False

    tag_ids = None
    if source_type == 'public':
        tag_ids = _load_public_tag_ids(conn, int(uid), tag)
    else:
        tag_ids = _load_bank_tag_ids(conn, int(uid), int(bank_id), tag)

    if kind == 'tags' and isinstance(tag_ids, list) and len(tag_ids) == 0:
        # 标签选择了但未绑定任何题目：直接提示
        warning = warning or '当前标签下暂无题目，请先在刷题页给题目打上该标签。'

    def _count_available(type_filter: str) -> int:
        tf = (type_filter or 'all').strip()
        if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
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
            params = [int(uid), int(uid), int(subject_id)]

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

    available_count = _count_available(q_type)

    # tab urls（保留筛选项）
    base_url = request.path
    ctx = {}
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
        params = {'mode': mode}
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

    # 搜索结果（仅用于 search tab）
    search_questions = []
    search_total = 0
    if tab == 'search' and keyword:
        like = f"%{keyword}%"
        page = 1
        try:
            page = int(request.args.get('page') or 1)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        per_page = 20
        offset = (page - 1) * per_page

        if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
            search_total = 0
            search_questions = []
        else:
            if source_type == 'public':
                base = """
                    SELECT q.id, q.type as p_type, q.content,
                           CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                           CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                    FROM questions q
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                    LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                    WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                      AND q.subject_id = ?
                      AND (q.content LIKE ? OR q.analysis LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
                """
                params = [int(uid), int(uid), int(subject_id), like, like, like, like]

                if kind == 'favorites':
                    base += " AND f.id IS NOT NULL"
                elif kind == 'mistakes':
                    base += " AND m.id IS NOT NULL"

                if q_type and q_type != 'all':
                    from app.core.utils.portable_question_format import any_type_to_portable_type

                    base += " AND q.type = ?"
                    params.append(any_type_to_portable_type(q_type))

                if isinstance(tag_ids, list):
                    base, params = safe_in_clause('q.id', tag_ids, base, params)

                count_sql = f"SELECT COUNT(1) FROM ({base})"
                search_total = int(conn.execute(count_sql, params).fetchone()[0] or 0)

                rows = conn.execute(base + " ORDER BY q.id DESC LIMIT ? OFFSET ?", params + [per_page, offset]).fetchall()
                from app.core.utils.portable_question_format import portable_type_to_q_type
                for r in rows or []:
                    search_questions.append({
                        'id': r['id'],
                        'q_type': portable_type_to_q_type((r['p_type'] or '')),
                        'is_fav': int(r['is_fav'] or 0),
                        'is_mistake': int(r['is_mistake'] or 0),
                        'content_preview': _build_preview(r['content'] or ''),
                        # 兜底：Web quiz 暂不支持 start_id，点击结果默认从当前筛选开始
                        'jump_url': quiz_url,
                    })
            else:
                base = """
                    SELECT q.id, q.type as p_type, q.content,
                           CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                           CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                    FROM user_bank_questions q
                    LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
                    LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
                    WHERE q.bank_id = ?
                      AND (q.content LIKE ? OR q.analysis LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
                """
                params = [int(uid), int(uid), int(bank_id), like, like, like, like]

                if kind == 'favorites':
                    base += " AND f.id IS NOT NULL"
                elif kind == 'mistakes':
                    base += " AND m.id IS NOT NULL"

                if q_type and q_type != 'all':
                    from app.core.utils.portable_question_format import any_type_to_portable_type

                    base += " AND q.type = ?"
                    params.append(any_type_to_portable_type(q_type))

                if isinstance(tag_ids, list):
                    base, params = safe_in_clause('q.id', tag_ids, base, params)

                count_sql = f"SELECT COUNT(1) FROM ({base})"
                search_total = int(conn.execute(count_sql, params).fetchone()[0] or 0)

                rows = conn.execute(base + " ORDER BY q.id DESC LIMIT ? OFFSET ?", params + [per_page, offset]).fetchall()
                from app.core.utils.portable_question_format import portable_type_to_q_type
                for r in rows or []:
                    search_questions.append({
                        'id': r['id'],
                        'q_type': portable_type_to_q_type((r['p_type'] or ''), essay_q_type="简答题"),
                        'is_fav': int(r['is_fav'] or 0),
                        'is_mistake': int(r['is_mistake'] or 0),
                        'content_preview': _build_preview(r['content'] or ''),
                        'jump_url': quiz_url,
                    })

    # 数据：题型分布
    data_total = _count_available('all')
    type_dist = []
    data_type_count = 0
    try:
        if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
            raise RuntimeError('tag empty')

        if source_type == 'public':
            base = """
                SELECT q.type as p_type, COUNT(1) as cnt
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id = ?
            """
            params = [int(uid), int(uid), int(subject_id)]
            if kind == 'favorites':
                base += " AND f.id IS NOT NULL"
            elif kind == 'mistakes':
                base += " AND m.id IS NOT NULL"
            if isinstance(tag_ids, list):
                base, params = safe_in_clause('q.id', tag_ids, base, params)
            base += " GROUP BY q.type ORDER BY cnt DESC"
            rows = conn.execute(base, params).fetchall()
            from app.core.utils.portable_question_format import portable_type_to_q_type

            dist = [
                {
                    'q_type': portable_type_to_q_type((r['p_type'] or '')),
                    'count': int(r['cnt'] or 0),
                }
                for r in (rows or [])
                if r and r['p_type']
            ]
        else:
            base = """
                SELECT q.type as p_type, COUNT(1) as cnt
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
            if isinstance(tag_ids, list):
                base, params = safe_in_clause('q.id', tag_ids, base, params)
            base += " GROUP BY q.type ORDER BY cnt DESC"
            rows = conn.execute(base, params).fetchall()
            from app.core.utils.portable_question_format import portable_type_to_q_type

            dist = [
                {
                    'q_type': portable_type_to_q_type((r['p_type'] or ''), essay_q_type="简答题"),
                    'count': int(r['cnt'] or 0),
                }
                for r in (rows or [])
                if r and r['p_type']
            ]

        max_n = max([d['count'] for d in dist], default=0)
        for d in dist[:10]:
            d['pct'] = int(round((d['count'] * 100.0 / max_n), 0)) if max_n else 0
            d['practice_url'] = _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': d['q_type'], 'tag': tag})
            type_dist.append(d)
        data_type_count = len(dist)
    except Exception:
        type_dist = []
        data_type_count = 0

    data_answer = {
        'answered': 0,
        'correct': 0,
        'accuracy': 0.0,
        'answered_7d': 0,
        'correct_7d': 0,
        'accuracy_7d': 0.0,
        'answered_30d': 0,
        'correct_30d': 0,
        'accuracy_30d': 0.0,
    }
    data_activity = []
    data_fav = {'count': 0, 'new_7d': 0, 'new_30d': 0}
    data_mis = {'count': 0, 'times': 0, 'new_7d': 0, 'new_30d': 0, 'active_7d': 0}
    data_tips = []
    data_state = {
        'total': 0,
        'answered': 0,
        'correct': 0,
        'wrong': 0,
        'unanswered': 0,
        'pct_correct': 0.0,
        'pct_wrong': 0.0,
        'pct_unanswered': 0.0,
    }
    mistake_buckets = []
    tag_dist = []
    data_items = []

    if tab == 'data':
        def _pct(n: int, d: int) -> float:
            try:
                return round((float(n) * 100.0 / float(d)) if d else 0.0, 1)
            except Exception:
                return 0.0

        def _column_exists(table: str, col: str) -> bool:
            try:
                cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                return col in set(cols)
            except Exception:
                return False

        def _append_tag_clause(sql: str, params: list, col: str = 'q.id') -> tuple[str, list]:
            if isinstance(tag_ids, list):
                sql, params = safe_in_clause(col, tag_ids, sql, params)
            return sql, params

        def _append_type_clause(sql: str, params: list, col: str = 'q.type') -> tuple[str, list]:
            if q_type and q_type != 'all':
                from app.core.utils.portable_question_format import any_type_to_portable_type

                portable_type = any_type_to_portable_type(q_type)
                # 兼容历史调用：若传入 q.q_type，则自动映射到 q.type
                col = str(col or 'q.type').replace('.q_type', '.type')
                sql += f" AND {col} = ?"
                params.append(portable_type)
            return sql, params

        is_tag_empty = (isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all')

        if is_tag_empty:
            data_tips.append('当前标签下暂无题目：先在刷题页给题目打上该标签，再回到这里复盘。')
        else:
            try:
                window_days = 14
                day_offset = max(0, window_days - 1)
                since_arg = f'-{day_offset} day'

                if source_type == 'public':
                    # 答题统计（基于 user_answers：每题仅保留最新一条记录）
                    def _answer_stats_public(days: int = 0) -> tuple[int, int]:
                        sql = """
                            SELECT COUNT(1) as answered,
                                   SUM(CASE WHEN t.correct=1 THEN 1 ELSE 0 END) as correct
                            FROM (
                              SELECT ua.question_id as qid,
                                     MAX(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
                              FROM user_answers ua
                              JOIN questions q ON q.id = ua.question_id
                              LEFT JOIN subjects s ON q.subject_id = s.id
                              LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                              LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                              WHERE ua.user_id = ?
                                AND (s.is_locked=0 OR s.is_locked IS NULL)
                                AND q.subject_id = ?
                        """
                        params = [int(uid), int(uid), int(uid), int(subject_id)]
                        if kind == 'favorites':
                            sql += " AND f.id IS NOT NULL"
                        elif kind == 'mistakes':
                            sql += " AND m.id IS NOT NULL"
                        sql, params = _append_type_clause(sql, params, 'q.q_type')
                        sql, params = _append_tag_clause(sql, params, 'q.id')
                        if days > 0:
                            sql += " AND ua.created_at >= datetime('now', '+8 hours', ?)"
                            params.append(f'-{int(days)} day')
                        sql += " GROUP BY ua.question_id ) t"
                        row = conn.execute(sql, params).fetchone()
                        answered = int(row['answered'] or 0) if row else 0
                        correct = int(row['correct'] or 0) if row else 0
                        return answered, correct

                    ans_total, cor_total = _answer_stats_public(0)
                    ans_7d, cor_7d = _answer_stats_public(7)
                    ans_30d, cor_30d = _answer_stats_public(30)

                    data_answer.update(
                        {
                            'answered': ans_total,
                            'correct': cor_total,
                            'accuracy': _pct(cor_total, ans_total),
                            'answered_7d': ans_7d,
                            'correct_7d': cor_7d,
                            'accuracy_7d': _pct(cor_7d, ans_7d),
                            'answered_30d': ans_30d,
                            'correct_30d': cor_30d,
                            'accuracy_30d': _pct(cor_30d, ans_30d),
                        }
                    )

                    # 近 14 天活跃（按“最后一次答题日期”聚合）
                    act_sql = """
                        SELECT DATE(ua.created_at) as day,
                               COUNT(1) as total,
                               SUM(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
                        FROM user_answers ua
                        JOIN questions q ON q.id = ua.question_id
                        LEFT JOIN subjects s ON q.subject_id = s.id
                        LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                        LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                        WHERE ua.user_id = ?
                          AND (s.is_locked=0 OR s.is_locked IS NULL)
                          AND q.subject_id = ?
                          AND ua.created_at >= datetime('now', '+8 hours', ?)
                    """
                    act_params = [int(uid), int(uid), int(uid), int(subject_id), since_arg]
                    if kind == 'favorites':
                        act_sql += " AND f.id IS NOT NULL"
                    elif kind == 'mistakes':
                        act_sql += " AND m.id IS NOT NULL"
                    act_sql, act_params = _append_type_clause(act_sql, act_params, 'q.q_type')
                    act_sql, act_params = _append_tag_clause(act_sql, act_params, 'q.id')
                    act_sql += " GROUP BY day ORDER BY day ASC"

                    rows = conn.execute(act_sql, act_params).fetchall()
                    day_map = {str(r['day']): {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in (rows or []) if r and r['day']}

                    today = today_bj()
                    series = []
                    max_total = 0
                    for i in range(window_days - 1, -1, -1):
                        d = today - timedelta(days=i)
                        key = d.strftime('%Y-%m-%d')
                        item = day_map.get(key, {'total': 0, 'correct': 0})
                        total_n = int(item.get('total') or 0)
                        correct_n = int(item.get('correct') or 0)
                        max_total = max(max_total, total_n)
                        series.append(
                            {
                                'day': d.strftime('%m-%d'),
                                'total': total_n,
                                'correct': correct_n,
                            }
                        )

                    for it in series:
                        total_n = int(it.get('total') or 0)
                        correct_n = int(it.get('correct') or 0)
                        it['pct'] = int(round((total_n * 100.0 / max_total), 0)) if max_total else 0
                        it['acc'] = _pct(correct_n, total_n)

                    data_activity = series

                    # 收藏/错题统计（在当前题库 + 当前题型/标签下）
                    fav_sql = """
                        SELECT COUNT(1) as cnt
                        FROM questions q
                        LEFT JOIN subjects s ON q.subject_id = s.id
                        JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                          AND q.subject_id = ?
                    """
                    fav_params = [int(uid), int(subject_id)]
                    fav_sql, fav_params = _append_type_clause(fav_sql, fav_params, 'q.q_type')
                    fav_sql, fav_params = _append_tag_clause(fav_sql, fav_params, 'q.id')
                    row = conn.execute(fav_sql, fav_params).fetchone()
                    data_fav['count'] = int(row['cnt'] or 0) if row else 0

                    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
                        sql = fav_sql + " AND f.created_at >= datetime('now', '+8 hours', ?)"
                        params = list(fav_params) + [f'-{int(days)} day']
                        row = conn.execute(sql, params).fetchone()
                        data_fav[key] = int(row['cnt'] or 0) if row else 0

                    mis_has_wrong = _column_exists('mistakes', 'wrong_count')
                    mis_created_col = None
                    if _column_exists('mistakes', 'created_at'):
                        mis_created_col = 'm.created_at'
                    elif _column_exists('mistakes', 'last_updated'):
                        mis_created_col = 'm.last_updated'
                    elif _column_exists('mistakes', 'updated_at'):
                        mis_created_col = 'm.updated_at'

                    mis_updated_col = None
                    if _column_exists('mistakes', 'updated_at'):
                        mis_updated_col = 'm.updated_at'
                    elif _column_exists('mistakes', 'last_updated'):
                        mis_updated_col = 'm.last_updated'
                    elif _column_exists('mistakes', 'created_at'):
                        mis_updated_col = 'm.created_at'

                    mis_times_expr = (
                        "SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) as times"
                        if mis_has_wrong
                        else "COUNT(1) as times"
                    )
                    mis_sql = f"""
                        SELECT COUNT(1) as cnt, {mis_times_expr}
                        FROM questions q
                        LEFT JOIN subjects s ON q.subject_id = s.id
                        JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                          AND q.subject_id = ?
                    """
                    mis_params = [int(uid), int(subject_id)]
                    mis_sql, mis_params = _append_type_clause(mis_sql, mis_params, 'q.q_type')
                    mis_sql, mis_params = _append_tag_clause(mis_sql, mis_params, 'q.id')
                    row = conn.execute(mis_sql, mis_params).fetchone()
                    data_mis['count'] = int(row['cnt'] or 0) if row else 0
                    data_mis['times'] = int(row['times'] or 0) if row else 0

                    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
                        if not mis_created_col:
                            data_mis[key] = 0
                            continue
                        sql = mis_sql + f" AND {mis_created_col} >= datetime('now', '+8 hours', ?)"
                        params = list(mis_params) + [f'-{int(days)} day']
                        row = conn.execute(sql, params).fetchone()
                        data_mis[key] = int(row['cnt'] or 0) if row else 0

                    # 活跃错题：优先用 updated_at，否则回退 last_updated/created_at
                    if mis_updated_col:
                        sql = mis_sql + f" AND {mis_updated_col} >= datetime('now', '+8 hours', ?)"
                        params = list(mis_params) + ['-7 day']
                        row = conn.execute(sql, params).fetchone()
                        data_mis['active_7d'] = int(row['cnt'] or 0) if row else 0
                    else:
                        data_mis['active_7d'] = 0

                else:
                    # user_bank：答题统计（user_bank_answers 仅保留最新一条记录）
                    def _answer_stats_bank(days: int = 0) -> tuple[int, int]:
                        sql = """
                            SELECT COUNT(1) as answered,
                                   SUM(CASE WHEN t.correct=1 THEN 1 ELSE 0 END) as correct
                            FROM (
                              SELECT ua.question_id as qid,
                                     MAX(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
                              FROM user_bank_answers ua
                              JOIN user_bank_questions q ON q.id = ua.question_id
                              LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
                              LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
                              WHERE ua.user_id = ?
                                AND ua.bank_id = ?
                                AND q.bank_id = ?
                        """
                        params = [int(uid), int(uid), int(uid), int(bank_id), int(bank_id)]
                        if kind == 'favorites':
                            sql += " AND f.id IS NOT NULL"
                        elif kind == 'mistakes':
                            sql += " AND m.id IS NOT NULL"
                        sql, params = _append_type_clause(sql, params, 'q.q_type')
                        sql, params = _append_tag_clause(sql, params, 'q.id')
                        if days > 0:
                            sql += " AND ua.created_at >= datetime('now', '+8 hours', ?)"
                            params.append(f'-{int(days)} day')
                        sql += " GROUP BY ua.question_id ) t"
                        row = conn.execute(sql, params).fetchone()
                        answered = int(row['answered'] or 0) if row else 0
                        correct = int(row['correct'] or 0) if row else 0
                        return answered, correct

                    ans_total, cor_total = _answer_stats_bank(0)
                    ans_7d, cor_7d = _answer_stats_bank(7)
                    ans_30d, cor_30d = _answer_stats_bank(30)

                    data_answer.update(
                        {
                            'answered': ans_total,
                            'correct': cor_total,
                            'accuracy': _pct(cor_total, ans_total),
                            'answered_7d': ans_7d,
                            'correct_7d': cor_7d,
                            'accuracy_7d': _pct(cor_7d, ans_7d),
                            'answered_30d': ans_30d,
                            'correct_30d': cor_30d,
                            'accuracy_30d': _pct(cor_30d, ans_30d),
                        }
                    )

                    # 近 14 天活跃：按 user_bank_answers.created_at（最后一次答题时间）
                    act_sql = """
                        SELECT DATE(ua.created_at) as day,
                               COUNT(1) as total,
                               SUM(CASE WHEN ua.is_correct=1 THEN 1 ELSE 0 END) as correct
                        FROM user_bank_answers ua
                        JOIN user_bank_questions q ON q.id = ua.question_id
                        LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
                        LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
                        WHERE ua.user_id = ?
                          AND ua.bank_id = ?
                          AND q.bank_id = ?
                          AND ua.created_at >= datetime('now', '+8 hours', ?)
                    """
                    act_params = [int(uid), int(uid), int(uid), int(bank_id), int(bank_id), since_arg]
                    if kind == 'favorites':
                        act_sql += " AND f.id IS NOT NULL"
                    elif kind == 'mistakes':
                        act_sql += " AND m.id IS NOT NULL"
                    act_sql, act_params = _append_type_clause(act_sql, act_params, 'q.q_type')
                    act_sql, act_params = _append_tag_clause(act_sql, act_params, 'q.id')
                    act_sql += " GROUP BY day ORDER BY day ASC"

                    rows = conn.execute(act_sql, act_params).fetchall()
                    day_map = {str(r['day']): {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in (rows or []) if r and r['day']}

                    today = today_bj()
                    series = []
                    max_total = 0
                    for i in range(window_days - 1, -1, -1):
                        d = today - timedelta(days=i)
                        key = d.strftime('%Y-%m-%d')
                        item = day_map.get(key, {'total': 0, 'correct': 0})
                        total_n = int(item.get('total') or 0)
                        correct_n = int(item.get('correct') or 0)
                        max_total = max(max_total, total_n)
                        series.append(
                            {
                                'day': d.strftime('%m-%d'),
                                'total': total_n,
                                'correct': correct_n,
                            }
                        )

                    for it in series:
                        total_n = int(it.get('total') or 0)
                        correct_n = int(it.get('correct') or 0)
                        it['pct'] = int(round((total_n * 100.0 / max_total), 0)) if max_total else 0
                        it['acc'] = _pct(correct_n, total_n)

                    data_activity = series

                    # 收藏/错题统计（当前题库 + 当前题型/标签）
                    fav_sql = """
                        SELECT COUNT(1) as cnt
                        FROM user_bank_questions q
                        JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
                        WHERE q.bank_id = ?
                    """
                    fav_params = [int(uid), int(bank_id)]
                    fav_sql, fav_params = _append_type_clause(fav_sql, fav_params, 'q.q_type')
                    fav_sql, fav_params = _append_tag_clause(fav_sql, fav_params, 'q.id')
                    row = conn.execute(fav_sql, fav_params).fetchone()
                    data_fav['count'] = int(row['cnt'] or 0) if row else 0

                    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
                        sql = fav_sql + " AND f.created_at >= datetime('now', '+8 hours', ?)"
                        params = list(fav_params) + [f'-{int(days)} day']
                        row = conn.execute(sql, params).fetchone()
                        data_fav[key] = int(row['cnt'] or 0) if row else 0

                    mis_sql = """
                        SELECT COUNT(1) as cnt,
                               SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) as times
                        FROM user_bank_questions q
                        JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
                        WHERE q.bank_id = ?
                    """
                    mis_params = [int(uid), int(bank_id)]
                    mis_sql, mis_params = _append_type_clause(mis_sql, mis_params, 'q.q_type')
                    mis_sql, mis_params = _append_tag_clause(mis_sql, mis_params, 'q.id')
                    row = conn.execute(mis_sql, mis_params).fetchone()
                    data_mis['count'] = int(row['cnt'] or 0) if row else 0
                    data_mis['times'] = int(row['times'] or 0) if row else 0

                    for days, key in ((7, 'new_7d'), (30, 'new_30d')):
                        sql = mis_sql + " AND m.created_at >= datetime('now', '+8 hours', ?)"
                        params = list(mis_params) + [f'-{int(days)} day']
                        row = conn.execute(sql, params).fetchone()
                        data_mis[key] = int(row['cnt'] or 0) if row else 0

                    sql = mis_sql + " AND m.updated_at >= datetime('now', '+8 hours', ?)"
                    params = list(mis_params) + ['-7 day']
                    row = conn.execute(sql, params).fetchone()
                    data_mis['active_7d'] = int(row['cnt'] or 0) if row else 0

                # 自动建议
                total_q = int(available_count or 0) if (q_type and q_type != 'all') else int(data_total or 0)
                answered_q = int(data_answer.get('answered') or 0)
                acc = float(data_answer.get('accuracy') or 0.0)

                if total_q <= 0:
                    data_tips.append('当前范围下暂无题目数据：可切换题型/标签，或先去刷题产生数据。')
                elif answered_q <= 0:
                    data_tips.append('当前范围下你还没做过题：先去「开始刷题」跑一遍，本页会给出更精准的分析。')
                else:
                    if acc < 60:
                        data_tips.append('正确率偏低：建议先用「背题模式」把概念/公式过一遍，再回到刷题巩固。')
                    elif acc < 80:
                        data_tips.append('正确率不错：建议开启「打乱题目」，并将范围拆到 1 个题型/1 个标签逐步推进。')
                    else:
                        data_tips.append('正确率很高：可以尝试混合题型练习；选择/多选题再打开「打乱选项」增强抗干扰。')

                if kind == 'mistakes':
                    mis_cnt = int(data_mis.get('count') or 0)
                    mis_times = int(data_mis.get('times') or 0)
                    if mis_cnt > 0 and mis_times >= int(mis_cnt * 2):
                        data_tips.append('错题重复出现较多：建议把错题按标签细分，并优先复盘「高频错题型」。')
                    if type_dist:
                        top = type_dist[0]
                        data_tips.append(f"优先攻克题型：{top.get('q_type')}（{top.get('count')} 题）。")
                elif kind == 'favorites':
                    fav_cnt = int(data_fav.get('count') or 0)
                    if fav_cnt >= 120:
                        data_tips.append('收藏量较大：建议按标签整理（例如：易错/易忘/高频），并定期清理已掌握题目。')
                    if type_dist:
                        top = type_dist[0]
                        data_tips.append(f"收藏最多的题型：{top.get('q_type')}（{top.get('count')} 题）。")
                elif kind == 'tags':
                    if tag and tag.lower() != 'all':
                        if int(data_total or 0) < 10:
                            data_tips.append('该标签题目较少：可以继续补充题目，或与相近标签合并以提升统计稳定性。')
                        if type_dist:
                            top = type_dist[0]
                            data_tips.append(f"该标签下最多的题型：{top.get('q_type')}（{top.get('count')} 题）。")

                if tag and tag.lower() == 'all' and (tags or []):
                    data_tips.append('试试选择一个标签，把范围拆小后再看数据页，会更清晰。')

                # ===== 数据增强：状态分布 / 标签分布 / 快捷清单 =====
                scope_total = int(available_count or 0)
                answered_q = int(data_answer.get('answered') or 0)
                correct_q = int(data_answer.get('correct') or 0)
                wrong_q = max(0, answered_q - correct_q)
                unanswered_q = max(0, scope_total - answered_q)
                data_state = {
                    'total': scope_total,
                    'answered': answered_q,
                    'correct': correct_q,
                    'wrong': wrong_q,
                    'unanswered': unanswered_q,
                    'pct_correct': _pct(correct_q, scope_total),
                    'pct_wrong': _pct(wrong_q, scope_total),
                    'pct_unanswered': _pct(unanswered_q, scope_total),
                }

                def _load_scope_qids(limit=None):
                    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != 'all':
                        return []

                    if source_type == 'public':
                        sql = """
                            SELECT q.id as id
                            FROM questions q
                            LEFT JOIN subjects s ON q.subject_id = s.id
                            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = ?
                            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = ?
                            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                              AND q.subject_id = ?
                        """
                        params = [int(uid), int(uid), int(subject_id)]
                        if kind == 'favorites':
                            sql += " AND f.id IS NOT NULL"
                        elif kind == 'mistakes':
                            sql += " AND m.id IS NOT NULL"
                        sql, params = _append_type_clause(sql, params, 'q.q_type')
                        sql, params = _append_tag_clause(sql, params, 'q.id')
                        sql += " ORDER BY q.id DESC"
                        if isinstance(limit, int) and limit > 0:
                            sql += " LIMIT ?"
                            params.append(int(limit))
                        rows = conn.execute(sql, params).fetchall()
                        return [int(r['id']) for r in (rows or []) if r and r['id'] is not None]

                    sql = """
                        SELECT q.id as id
                        FROM user_bank_questions q
                        LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = ?
                        LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = ?
                        WHERE q.bank_id = ?
                    """
                    params = [int(uid), int(uid), int(bank_id)]
                    if kind == 'favorites':
                        sql += " AND f.id IS NOT NULL"
                    elif kind == 'mistakes':
                        sql += " AND m.id IS NOT NULL"
                    sql, params = _append_type_clause(sql, params, 'q.q_type')
                    sql, params = _append_tag_clause(sql, params, 'q.id')
                    sql += " ORDER BY q.id DESC"
                    if isinstance(limit, int) and limit > 0:
                        sql += " LIMIT ?"
                        params.append(int(limit))
                    rows = conn.execute(sql, params).fetchall()
                    return [int(r['id']) for r in (rows or []) if r and r['id'] is not None]

                try:
                    scope_qids = set(_load_scope_qids(None))
                except Exception:
                    scope_qids = set()

                # 标签分布（限定在当前范围内）
                try:
                    tag_counter: dict[str, int] = {}
                    tagged_count = 0

                    if scope_qids:
                        if source_type == 'public':
                            from app.modules.quiz.services.question_tags_service import load_store

                            store = load_store(conn, int(uid))
                            bindings = store.get('bindings') or {}
                            if isinstance(bindings, dict):
                                for qid in scope_qids:
                                    tlist = bindings.get(str(qid))
                                    if not isinstance(tlist, list) or not tlist:
                                        continue
                                    tagged_count += 1
                                    for t in tlist:
                                        name = (t or '').strip()
                                        if not name or name.lower() == 'all':
                                            continue
                                        if kind == 'tags' and tag and name == tag:
                                            continue
                                        tag_counter[name] = tag_counter.get(name, 0) + 1
                        else:
                            from app.modules.user_bank.routes.api import _load_bank_tag_store

                            store = _load_bank_tag_store(conn, int(bank_id), int(uid))
                            qtags = store.get('question_tags') or {}
                            if isinstance(qtags, dict):
                                for qid in scope_qids:
                                    tlist = qtags.get(str(qid)) or qtags.get(int(qid))  # 兼容 key 类型
                                    if not isinstance(tlist, list) or not tlist:
                                        continue
                                    tagged_count += 1
                                    for t in tlist:
                                        name = (t or '').strip()
                                        if not name or name.lower() == 'all':
                                            continue
                                        if kind == 'tags' and tag and name == tag:
                                            continue
                                        tag_counter[name] = tag_counter.get(name, 0) + 1

                    ranked = sorted(tag_counter.items(), key=lambda kv: int(kv[1] or 0), reverse=True)[:10]
                    max_c = max([int(v) for _, v in ranked], default=0)
                    for name, cnt in ranked:
                        tag_dist.append(
                            {
                                'name': name,
                                'count': int(cnt or 0),
                                'pct': int(round((float(cnt) * 100.0 / float(max_c)) if max_c else 0.0, 0)),
                                'switch_url': _url_with_params(base_url, {**ctx, 'tab': 'data', 'type': q_type, 'tag': name}),
                            }
                        )

                    if kind != 'tags' and scope_total > 0 and tagged_count <= 0:
                        data_tips.append('当前范围内还没有使用标签：给题目打标签能帮助你更快做复盘与专项训练。')
                except Exception:
                    tag_dist = tag_dist or []

                # 错题次数分布（仅错题中心）
                if kind == 'mistakes':
                    try:
                        buckets = {'1': 0, '2': 0, '3': 0, '4+': 0}
                        if source_type == 'public':
                            sql = """
                                SELECT CASE
                                         WHEN m.wrong_count IS NULL OR m.wrong_count <= 1 THEN '1'
                                         WHEN m.wrong_count = 2 THEN '2'
                                         WHEN m.wrong_count = 3 THEN '3'
                                         ELSE '4+'
                                       END as bucket,
                                       COUNT(1) as cnt
                                FROM mistakes m
                                JOIN questions q ON q.id = m.question_id
                                LEFT JOIN subjects s ON q.subject_id = s.id
                                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                                  AND m.user_id = ?
                                  AND q.subject_id = ?
                            """
                            params = [int(uid), int(subject_id)]
                            sql, params = _append_type_clause(sql, params, 'q.q_type')
                            sql, params = _append_tag_clause(sql, params, 'q.id')
                            sql += " GROUP BY bucket"
                            rows = conn.execute(sql, params).fetchall()
                        else:
                            sql = """
                                SELECT CASE
                                         WHEN m.wrong_count IS NULL OR m.wrong_count <= 1 THEN '1'
                                         WHEN m.wrong_count = 2 THEN '2'
                                         WHEN m.wrong_count = 3 THEN '3'
                                         ELSE '4+'
                                       END as bucket,
                                       COUNT(1) as cnt
                                FROM user_bank_mistakes m
                                JOIN user_bank_questions q ON q.id = m.question_id
                                WHERE m.user_id = ?
                                  AND q.bank_id = ?
                            """
                            params = [int(uid), int(bank_id)]
                            sql, params = _append_type_clause(sql, params, 'q.q_type')
                            sql, params = _append_tag_clause(sql, params, 'q.id')
                            sql += " GROUP BY bucket"
                            rows = conn.execute(sql, params).fetchall()

                        for r in rows or []:
                            b = str(r['bucket'] or '').strip()
                            if b in buckets:
                                buckets[b] = int(r['cnt'] or 0)

                        max_b = max(buckets.values()) if buckets else 0
                        for key in ('1', '2', '3', '4+'):
                            cnt = int(buckets.get(key) or 0)
                            mistake_buckets.append(
                                {
                                    'label': f'错 {key} 次' if key != '4+' else '错 4+ 次',
                                    'count': cnt,
                                    'pct': int(round((float(cnt) * 100.0 / float(max_b)) if max_b else 0.0, 0)),
                                }
                            )
                    except Exception:
                        mistake_buckets = mistake_buckets or []

                # 快捷清单：收藏（最近）/错题（高频）
                try:
                    if kind == 'favorites':
                        if source_type == 'public':
                            sql = """
                                SELECT q.id, q.type as p_type, q.content, f.created_at as ts
                                FROM favorites f
                                JOIN questions q ON q.id = f.question_id
                                LEFT JOIN subjects s ON q.subject_id = s.id
                                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                                  AND f.user_id = ?
                                  AND q.subject_id = ?
                            """
                            params = [int(uid), int(subject_id)]
                            sql, params = _append_type_clause(sql, params, 'q.q_type')
                            sql, params = _append_tag_clause(sql, params, 'q.id')
                            sql += " ORDER BY f.created_at DESC LIMIT 8"
                            rows = conn.execute(sql, params).fetchall()
                        else:
                            sql = """
                                SELECT q.id, q.type as p_type, q.content, f.created_at as ts
                                FROM user_bank_favorites f
                                JOIN user_bank_questions q ON q.id = f.question_id
                                WHERE f.user_id = ?
                                  AND q.bank_id = ?
                            """
                            params = [int(uid), int(bank_id)]
                            sql, params = _append_type_clause(sql, params, 'q.q_type')
                            sql, params = _append_tag_clause(sql, params, 'q.id')
                            sql += " ORDER BY f.created_at DESC LIMIT 8"
                            rows = conn.execute(sql, params).fetchall()

                        for r in rows or []:
                            from app.core.utils.portable_question_format import portable_type_to_q_type

                            qt = portable_type_to_q_type(
                                (r['p_type'] or '')
                            )
                            data_items.append(
                                {
                                    'title': _build_preview(r['content'] or ''),
                                    'q_type': qt or '未知题型',
                                    'meta': f"收藏于 {r['ts']}",
                                    'practice_url': _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': qt or 'all', 'tag': tag}),
                                }
                            )
                    elif kind == 'mistakes':
                        if source_type == 'public':
                            order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.last_updated, m.created_at) DESC"
                            sql = f"""
                                SELECT q.id, q.type as p_type, q.content,
                                       m.wrong_count as wrong_count,
                                       COALESCE(m.updated_at, m.last_updated, m.created_at) as ts
                                FROM mistakes m
                                JOIN questions q ON q.id = m.question_id
                                LEFT JOIN subjects s ON q.subject_id = s.id
                                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                                  AND m.user_id = ?
                                  AND q.subject_id = ?
                            """
                            params = [int(uid), int(subject_id)]
                            sql, params = _append_type_clause(sql, params, 'q.q_type')
                            sql, params = _append_tag_clause(sql, params, 'q.id')
                            sql += f" ORDER BY {order_by} LIMIT 8"
                            rows = conn.execute(sql, params).fetchall()
                        else:
                            sql = """
                                SELECT q.id, q.type as p_type, q.content,
                                       m.wrong_count as wrong_count,
                                       COALESCE(m.updated_at, m.created_at) as ts
                                FROM user_bank_mistakes m
                                JOIN user_bank_questions q ON q.id = m.question_id
                                WHERE m.user_id = ?
                                  AND q.bank_id = ?
                            """
                            params = [int(uid), int(bank_id)]
                            sql, params = _append_type_clause(sql, params, 'q.q_type')
                            sql, params = _append_tag_clause(sql, params, 'q.id')
                            sql += " ORDER BY m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC LIMIT 8"
                            rows = conn.execute(sql, params).fetchall()

                        for r in rows or []:
                            from app.core.utils.portable_question_format import portable_type_to_q_type

                            qt = portable_type_to_q_type(
                                (r['p_type'] or '')
                            )
                            wc = int(r['wrong_count'] or 0)
                            data_items.append(
                                {
                                    'title': _build_preview(r['content'] or ''),
                                    'q_type': qt or '未知题型',
                                    'meta': f"错 {wc} 次 · 最近 {r['ts']}",
                                    'practice_url': _url_with_params(base_url, {**ctx, 'tab': 'practice', 'type': qt or 'all', 'tag': tag}),
                                }
                            )
                except Exception:
                    data_items = data_items or []
            except Exception as e:
                current_app.logger.warning(f"review center data stats failed: {e}")
                data_tips = data_tips or ['数据统计加载失败：请稍后刷新重试。']

    # Phase 1：建议 → 行动按钮（尽量不改后端语义，前端渲染为按钮）
    try:
        tip_items = []
        for t in data_tips or []:
            text = str(t or '').strip()
            if not text:
                continue

            action_label = '去练习'
            action_url = (tab_urls or {}).get('practice') or _url_with_params(
                base_url,
                {
                    **ctx,
                    'tab': 'practice',
                    'type': q_type,
                    'tag': tag,
                    'shuffle_questions': 1 if shuffle_questions else 0,
                    'shuffle_options': 1 if shuffle_options else 0,
                },
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
                    {
                        **ctx,
                        'tab': 'practice',
                        'type': qt,
                        'tag': tag,
                        'shuffle_questions': 1 if shuffle_questions else 0,
                        'shuffle_options': 1 if shuffle_options else 0,
                    },
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
                    {
                        **ctx,
                        'tab': 'practice',
                        'type': q_type,
                        'tag': tag,
                        'shuffle_questions': 1,
                        'shuffle_options': 1 if shuffle_options else 0,
                    },
                )
            elif '打乱选项' in text:
                action_label = '开启打乱选项'
                action_url = _url_with_params(
                    base_url,
                    {
                        **ctx,
                        'tab': 'practice',
                        'type': q_type,
                        'tag': tag,
                        'shuffle_questions': 1 if shuffle_questions else 0,
                        'shuffle_options': 1,
                    },
                )
            elif '选择一个标签' in text:
                action_label = '去选标签'
                action_url = _url_with_params(
                    base_url,
                    {
                        **ctx,
                        'tab': 'practice',
                        'type': q_type,
                        'tag': 'all',
                        'shuffle_questions': 1 if shuffle_questions else 0,
                        'shuffle_options': 1 if shuffle_options else 0,
                    },
                )

            tip_items.append({'text': text, 'action_label': action_label, 'action_url': action_url})

        data_tips = tip_items
    except Exception:
        pass

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


@main_pages_bp.route('/mistakes/center')
@login_required
def mistakes_center_page():
    return _review_center_page('mistakes')


@main_pages_bp.route('/favorites/center')
@login_required
def favorites_center_page():
    return _review_center_page('favorites')


@main_pages_bp.route('/tags/center')
@login_required
def tags_center_page():
    return _review_center_page('tags')


