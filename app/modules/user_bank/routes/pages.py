# -*- coding: utf-8 -*-
"""用户题库页面路由"""
import json

from flask import Blueprint, render_template, redirect, url_for, request, session
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import login_required

user_bank_pages_bp = Blueprint('user_bank_pages', __name__)


@user_bank_pages_bp.route('/')
@login_required
def banks_list():
    """我的题库首页（复用题库广场模板）"""
    return render_template(
        'user_bank/my/my_banks.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=session.get('user_id') or 0,
    )


@user_bank_pages_bp.route('/manage')
@login_required
def banks_manage():
    """（已下线）旧的题库后台入口：重定向到我的题库列表。"""
    return redirect('/user/banks')


@user_bank_pages_bp.route('/manage/shares')
@login_required
def manage_shares():
    """创建者后台：分享管理（已下线）"""
    return "页面已下线", 404


@user_bank_pages_bp.route('/<int:bank_id>')
@login_required
def bank_detail(bank_id):
    """题库详情/题目管理页面"""
    uid = session.get('user_id')
    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access or access_type != 'owner':
        return "题库不存在或无权限访问", 404

    bank = db.session.execute(
        text("""
        SELECT id, name, is_public, question_count, share_count
        FROM user_question_banks
        WHERE id = :bid AND status = 1
        """),
        {'bid': int(bank_id)},
    ).fetchone()
    if not bank:
        return "题库不存在或无权限访问", 404

    from app.core.utils.portable_question_format import portable_type_to_q_type

    types = [
        portable_type_to_q_type((r._mapping['p_type'] or ''), essay_q_type='简答题')
        for r in db.session.execute(
            text("""
            SELECT DISTINCT type as p_type
            FROM user_bank_questions
            WHERE bank_id = :bid AND type IS NOT NULL AND TRIM(type) != ''
            ORDER BY type
            """),
            {'bid': int(bank_id)},
        ).fetchall()
        if r and r._mapping['p_type']
    ]

    return render_template(
        'user_bank/manage/bank_manage_questions.html',
        bank_id=int(bank._mapping['id']),
        bank_name=bank._mapping['name'],
        is_public=bool(bank._mapping['is_public']),
        question_count=int(bank._mapping['question_count'] or 0),
        share_count=int(bank._mapping['share_count'] or 0),
        types=types,
    )


@user_bank_pages_bp.route('/<int:bank_id>/practice')
@login_required
def bank_practice(bank_id: int):
    """题库练习详情页：练习设置 / 题库数据（含范围/题型/标签与统计）。"""
    uid = session.get('user_id')

    from app.modules.user_bank.routes.api import check_bank_access, _load_bank_tag_store

    has_access, permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access:
        return "题库不存在或无权限访问", 404

    bank = db.session.execute(
        text("""
        SELECT id, name, description, question_count, status
        FROM user_question_banks
        WHERE id = :bid AND status = 1
        """),
        {'bid': int(bank_id)},
    ).fetchone()

    if not bank:
        return "题库不存在或无权限访问", 404

    from app.core.utils.portable_question_format import portable_type_to_q_type

    types = [
        portable_type_to_q_type((r._mapping['p_type'] or ''), essay_q_type='简答题')
        for r in db.session.execute(
            text("""
            SELECT DISTINCT type as p_type
            FROM user_bank_questions
            WHERE bank_id = :bid AND type IS NOT NULL AND TRIM(type) != ''
            ORDER BY type
            """),
            {'bid': int(bank_id)},
        ).fetchall()
        if r and r._mapping['p_type']
    ]

    # 题库题量：优先用缓存字段；异常时回退实时统计
    total_count = int(bank._mapping['question_count'] or 0)
    if total_count <= 0:
        try:
            total_count = db.session.execute(
                text("SELECT COUNT(*) FROM user_bank_questions WHERE bank_id = :bid"),
                {'bid': int(bank_id)},
            ).fetchone()[0]
        except Exception:
            total_count = 0

    fav_count = 0
    mistake_count = 0
    try:
        fav_count = db.session.execute(
            text("SELECT COUNT(*) FROM user_bank_favorites WHERE user_id = :uid AND bank_id = :bid"),
            {'uid': uid, 'bid': int(bank_id)},
        ).fetchone()[0]
    except Exception:
        fav_count = 0

    try:
        mistake_count = db.session.execute(
            text("SELECT COUNT(*) FROM user_bank_mistakes WHERE user_id = :uid AND bank_id = :bid"),
            {'uid': uid, 'bid': int(bank_id)},
        ).fetchone()[0]
    except Exception:
        mistake_count = 0

    # 题库标签（来自 user_progress bank_<id>_tags）
    tags_list = []
    try:
        conn = db.session.connection()
        store = _load_bank_tag_store(conn, int(bank_id), int(uid))
        tag_counts = {t: 0 for t in (store.get('tags') or []) if isinstance(t, str) and t.strip()}
        question_tags = store.get('question_tags', {}) or {}
        for _q_id, tags in question_tags.items():
            if not isinstance(tags, list):
                continue
            for t in tags:
                if t in tag_counts:
                    tag_counts[t] += 1
        tags_list = [{'name': t, 'count': int(tag_counts.get(t, 0))} for t in (store.get('tags') or []) if t in tag_counts]
    except Exception:
        tags_list = []

    my_stats = {
        'total_answered': 0,
        'correct_count': 0,
        'accuracy': 0.0,
    }
    try:
        row = db.session.execute(
            text("""
            SELECT
              COUNT(1) as answered,
              SUM(CASE WHEN is_correct=true THEN 1 ELSE 0 END) as correct
            FROM user_bank_answers
            WHERE user_id = :uid AND bank_id = :bid
            """),
            {'uid': int(uid), 'bid': int(bank_id)},
        ).fetchone()
        answered = int(row._mapping['answered'] or 0) if row else 0
        correct = int(row._mapping['correct'] or 0) if row else 0
        my_stats = {
            'total_answered': answered,
            'correct_count': correct,
            'accuracy': round((correct * 100.0 / answered), 1) if answered else 0.0,
        }
    except Exception:
        my_stats = {
            'total_answered': 0,
            'correct_count': 0,
            'accuracy': 0.0,
        }

    return render_template(
        'user_bank/bank/bank_practice.html',
        bank_id=int(bank._mapping['id']),
        bank_name=bank._mapping['name'],
        bank_description=bank._mapping['description'] or '',
        total_count=total_count,
        fav_count=fav_count,
        mistake_count=mistake_count,
        types=types,
        user_tags=tags_list,
        my_stats=my_stats,
        permission=permission,
        access_type=access_type,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@user_bank_pages_bp.route('/<int:bank_id>/data')
@login_required
def bank_data_redirect(bank_id: int):
    """题库数据页（默认跳转到"全局"）。"""
    try:
        params = request.args.to_dict(flat=True) if request.args else {}
    except Exception:
        params = {}
    return redirect(url_for('user_bank_pages.bank_data', bank_id=int(bank_id), subtab='global', **params))


@user_bank_pages_bp.route('/<int:bank_id>/data/<string:subtab>')
@login_required
def bank_data(bank_id: int, subtab: str):
    """题库数据页：全局/错题/收藏（三个独立跳转页面）。"""
    uid = session.get('user_id')

    from app.modules.user_bank.routes.api import check_bank_access

    has_access, permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access:
        return "题库不存在或无权限访问", 404

    safe_tab = (subtab or '').strip().lower()
    if safe_tab not in ('global', 'mistakes', 'favorites'):
        safe_tab = 'global'

    window_days = request.args.get('days', 90 if safe_tab == 'global' else 30, type=int)
    if window_days not in (7, 14, 30, 90):
        window_days = 90 if safe_tab == 'global' else 30

    bank = db.session.execute(
        text("""
        SELECT id, name, description, question_count, status
        FROM user_question_banks
        WHERE id = :bid AND status = 1
        """),
        {'bid': int(bank_id)},
    ).fetchone()

    if not bank:
        return "题库不存在或无权限访问", 404

    # 题库题量：优先用缓存字段；异常时回退实时统计
    total_count = int(bank._mapping['question_count'] or 0)
    if total_count <= 0:
        try:
            total_count = db.session.execute(
                text("SELECT COUNT(*) FROM user_bank_questions WHERE bank_id = :bid"),
                {'bid': int(bank_id)},
            ).fetchone()[0]
        except Exception:
            total_count = 0

    fav_count = 0
    mistake_count = 0
    try:
        fav_count = db.session.execute(
            text("SELECT COUNT(*) FROM user_bank_favorites WHERE user_id = :uid AND bank_id = :bid"),
            {'uid': uid, 'bid': int(bank_id)},
        ).fetchone()[0]
    except Exception:
        fav_count = 0

    try:
        mistake_count = db.session.execute(
            text("SELECT COUNT(*) FROM user_bank_mistakes WHERE user_id = :uid AND bank_id = :bid"),
            {'uid': uid, 'bid': int(bank_id)},
        ).fetchone()[0]
    except Exception:
        mistake_count = 0

    return render_template(
        {
            'global': 'user_bank/bank/bank_data_global_v2.html',
            'mistakes': 'user_bank/bank/bank_data_mistakes_v2.html',
            'favorites': 'user_bank/bank/bank_data_favorites_v2.html',
        }.get(safe_tab, 'user_bank/bank/bank_data_global_v2.html'),
        bank_id=int(bank._mapping['id']),
        bank_name=bank._mapping['name'],
        bank_description=bank._mapping['description'] or '',
        total_count=total_count,
        fav_count=fav_count,
        mistake_count=mistake_count,
        subtab=safe_tab,
        window_days=window_days,
        permission=permission,
        access_type=access_type,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@user_bank_pages_bp.route('/<int:bank_id>/manage')
@login_required
def bank_manage(bank_id: int):
    """题库管理（名片页）：仅创建者可访问。"""
    uid = session.get('user_id')

    bank = db.session.execute(
        text("""
        SELECT id, user_id, name, description, public_description, cover_image, is_public, allow_copy,
               question_count, share_count
        FROM user_question_banks
        WHERE id = :bid AND status = 1
        """),
        {'bid': int(bank_id)},
    ).fetchone()

    if not bank or int(bank._mapping['user_id'] or 0) != int(uid or 0):
        return "题库不存在或无权限访问", 404

    return render_template(
        'user_bank/manage/bank_manage.html',
        bank_id=int(bank._mapping['id']),
        bank_name=bank._mapping['name'],
        bank_description=bank._mapping['description'] or '',
        public_description=bank._mapping['public_description'] or '',
        cover_image=bank._mapping['cover_image'] or '',
        is_public=bool(bank._mapping['is_public']),
        allow_copy=bool(bank._mapping['allow_copy']),
        question_count=int(bank._mapping['question_count'] or 0),
        share_count=int(bank._mapping['share_count'] or 0),
    )


@user_bank_pages_bp.route('/<int:bank_id>/search')
@login_required
def bank_search(bank_id: int):
    """题库内搜索页：搜索范围限定在当前题库。"""
    uid = session.get('user_id')
    keyword = (request.args.get('keyword') or '').strip()
    type_filter = (request.args.get('type') or 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
    if not has_access:
        return "题库不存在或无权限访问", 404

    bank = db.session.execute(
        text("SELECT id, name, status FROM user_question_banks WHERE id = :bid AND status = 1"),
        {'bid': int(bank_id)},
    ).fetchone()
    if not bank:
        return "题库不存在或无权限访问", 404

    from app.core.utils.portable_question_format import portable_type_to_q_type

    available_types = [
        portable_type_to_q_type((r._mapping['p_type'] or ''), essay_q_type='简答题')
        for r in db.session.execute(
            text("""
            SELECT DISTINCT type as p_type
            FROM user_bank_questions
            WHERE bank_id = :bid AND type IS NOT NULL AND TRIM(type) != ''
            ORDER BY type
            """),
            {'bid': int(bank_id)},
        ).fetchall()
        if r and r._mapping['p_type']
    ]

    # 无关键词：展示空搜索页
    if not keyword:
        return render_template(
            'user_bank/bank/bank_search.html',
            bank_id=int(bank._mapping['id']),
            bank_name=bank._mapping['name'],
            keyword='',
            type_filter=type_filter or 'all',
            available_types=available_types,
            questions=[],
            page=1,
            total_pages=0,
            logged_in=True,
            username=session.get('username'),
            is_admin=session.get('is_admin', False),
            is_subject_admin=session.get('is_subject_admin', False),
            is_notification_admin=session.get('is_notification_admin', False),
            user_id=uid or 0,
        )

    def _split_answer_keys(answer_text: str) -> list[str]:
        answer_text = (answer_text or '').strip()
        if not answer_text:
            return []

        # 支持 JSON 数组答案，如 ["A","C"]
        if answer_text.startswith('[') and answer_text.endswith(']'):
            try:
                decoded = json.loads(answer_text)
                if isinstance(decoded, list):
                    keys: list[str] = []
                    seen = set()
                    for item in decoded:
                        k = str(item or '').strip()
                        if not k or k in seen:
                            continue
                        keys.append(k)
                        seen.add(k)
                    if keys:
                        return keys
            except Exception:
                pass

        # 统一分隔符
        normalized = (
            answer_text.replace('，', ',')
            .replace('、', ',')
            .replace('；', ',')
            .replace(';', ',')
            .replace('|', ',')
            .replace(' ', '')
        )
        parts = [p for p in (normalized.split(',') if normalized else []) if p]
        if not parts:
            parts = [answer_text]

        keys: list[str] = []
        for p in parts:
            p = (p or '').strip()
            if not p:
                continue
            # "AC" 视为多选；仅对 A-Z 连续字母做拆分，避免误拆 True/中文
            if len(p) > 1 and all('A' <= ch <= 'Z' for ch in p):
                keys.extend(list(p))
            else:
                keys.append(p)

        # 去重且保持顺序
        uniq: list[str] = []
        seen = set()
        for k in keys:
            if k in seen:
                continue
            uniq.append(k)
            seen.add(k)
        return uniq

    def _parse_options(raw_options):
        if not raw_options:
            return [], {}

        import re

        decoded = None
        if isinstance(raw_options, str):
            try:
                decoded = json.loads(raw_options)
            except Exception:
                decoded = None
        elif isinstance(raw_options, list):
            decoded = raw_options
        else:
            decoded = None

        if not isinstance(decoded, list):
            return [], {}

        parsed = []
        options_map = {}
        for item in decoded:
            if item is None:
                continue
            if isinstance(item, dict):
                key = str(item.get('key') or item.get('label') or '').strip()
                value = str(item.get('value') or item.get('text') or '').strip()
                if key or value:
                    parsed.append({'key': key, 'value': value})
                    if key and value:
                        options_map[key] = value
                continue

            item_str = str(item).strip()
            if not item_str:
                continue

            # 兼容 "A. xxx" / "A、xxx" / "A：xxx" / "A) xxx"
            m = re.match(r'^\s*([A-Za-z])\s*[\.\uFF0E\u3001:：\)\）\-]\s*(.+)$', item_str)
            if m:
                key = m.group(1).strip().upper()
                value = (m.group(2) or '').strip()
                parsed.append({'key': key, 'value': value})
                if key and value:
                    options_map[key] = value
            else:
                parsed.append({'key': '', 'value': item_str})

        return parsed, options_map

    search_term = f'%{keyword}%'
    sql = """
        SELECT id, type, content, options, answer, analysis, image_path, updated_at
        FROM user_bank_questions
        WHERE bank_id = :bid
          AND (
            content LIKE :st1 OR analysis LIKE :st2 OR options LIKE :st3 OR answer LIKE :st4
          )
    """
    params: dict = {'bid': int(bank_id), 'st1': search_term, 'st2': search_term, 'st3': search_term, 'st4': search_term}

    if type_filter and type_filter != 'all':
        from app.core.utils.portable_question_format import any_type_to_portable_type

        sql += " AND type = :tf"
        params['tf'] = any_type_to_portable_type(type_filter)

    sql += " ORDER BY updated_at DESC, id DESC"

    # 分页
    total = db.session.execute(
        text(f"SELECT COUNT(1) FROM ({sql}) as t"),
        params,
    ).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page if total else 0
    page = max(1, min(page, max(total_pages, 1)))
    offset = (page - 1) * per_page

    rows = db.session.execute(
        text(sql + " LIMIT :lim OFFSET :off"),
        {**params, 'lim': per_page, 'off': offset},
    ).fetchall()

    from app.core.utils.pqf_rows import pqf_row_to_internal

    questions = []
    for r in rows:
        q = pqf_row_to_internal(r, scope='user_bank')
        answer_text = str(q.get('answer') or '').strip()
        q['answer'] = answer_text
        q['full_answer'] = answer_text

        options_parsed, options_map = _parse_options(q.get('options'))
        q['options'] = options_parsed

        answer_keys = _split_answer_keys(answer_text)
        if options_map and answer_keys:
            parts = []
            for key in answer_keys:
                if key in options_map:
                    parts.append(f"{key}. {options_map[key]}")
            if parts:
                q['full_answer'] = "\n".join(parts)

        questions.append(q)

    return render_template(
        'user_bank/bank/bank_search.html',
        bank_id=int(bank._mapping['id']),
        bank_name=bank._mapping['name'],
        keyword=keyword,
        type_filter=type_filter or 'all',
        available_types=available_types,
        questions=questions,
        page=page,
        total_pages=total_pages,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@user_bank_pages_bp.route('/add')
@login_required
def bank_add():
    """题库创建向导页。"""
    return render_template(
        'user_bank/manage/bank_profile_wizard.html',
        mode='add',
        bank_id=None,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=session.get('user_id') or 0,
    )


def _fetch_bank_for_owner(bank_id: int, uid) -> dict | None:
    """获取题库基本信息（仅创建者可访问的页面复用）。"""
    row = db.session.execute(
        text("""
        SELECT id, name, is_public, question_count, share_count, COALESCE(join_mode, 'free') AS join_mode
        FROM user_question_banks
        WHERE id = :bid AND status = 1
        """),
        {'bid': int(bank_id)},
    ).fetchone()
    return dict(row._mapping) if row else None


@user_bank_pages_bp.route('/<int:bank_id>/edit')
@login_required
def bank_edit(bank_id):
    """题库设置页。"""
    uid = session.get('user_id')
    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access or access_type != 'owner':
        return "题库不存在或无权限访问", 404

    bank = _fetch_bank_for_owner(bank_id, uid)
    if not bank:
        return "题库不存在或无权限访问", 404

    return render_template(
        'user_bank/manage/bank_settings.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        is_public=bool(bank['is_public']),
        join_mode=bank.get('join_mode') or 'free',
        question_count=int(bank['question_count'] or 0),
        share_count=int(bank['share_count'] or 0),
    )


@user_bank_pages_bp.route('/<int:bank_id>/questions/import/word')
@login_required
def questions_import_word(bank_id: int):
    """Word 导入页面（.docx -> 文本解析 -> JSON 导入）。"""
    uid = session.get('user_id')
    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access or access_type != 'owner':
        return "题库不存在或无权限访问", 404

    bank = _fetch_bank_for_owner(bank_id, uid)
    if not bank:
        return "题库不存在或无权限访问", 404

    return render_template(
        'user_bank/manage/bank_import_word.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        is_public=bool(bank['is_public']),
        question_count=int(bank['question_count'] or 0),
        share_count=int(bank['share_count'] or 0),
    )


@user_bank_pages_bp.route('/<int:bank_id>/questions/add')
@login_required
def question_add(bank_id):
    """添加题目页面"""
    uid = session.get('user_id')
    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access or access_type != 'owner':
        return "题库不存在或无权限访问", 404

    bank = _fetch_bank_for_owner(bank_id, uid)
    if not bank:
        return "题库不存在或无权限访问", 404

    return render_template(
        'user_bank/manage/bank_manage_question_edit.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        is_public=bool(bank['is_public']),
        question_count=int(bank['question_count'] or 0),
        share_count=int(bank['share_count'] or 0),
        question_id=None,
        mode='add',
    )


@user_bank_pages_bp.route('/<int:bank_id>/questions/<int:question_id>/edit')
@login_required
def question_edit(bank_id, question_id):
    """编辑题目页面"""
    uid = session.get('user_id')
    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access or access_type != 'owner':
        return "题库不存在或无权限访问", 404

    bank = _fetch_bank_for_owner(bank_id, uid)
    if not bank:
        return "题库不存在或无权限访问", 404

    return render_template(
        'user_bank/manage/bank_manage_question_edit.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        is_public=bool(bank['is_public']),
        question_count=int(bank['question_count'] or 0),
        share_count=int(bank['share_count'] or 0),
        question_id=int(question_id),
        mode='edit',
    )


@user_bank_pages_bp.route('/<int:bank_id>/shares')
@login_required
def shares_manage(bank_id):
    """分享管理页面"""
    uid = session.get('user_id')
    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access or access_type != 'owner':
        return "题库不存在或无权限访问", 404

    bank = _fetch_bank_for_owner(bank_id, uid)
    if not bank:
        return "题库不存在或无权限访问", 404

    return render_template(
        'user_bank/manage/bank_manage_shares.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        is_public=bool(bank['is_public']),
        question_count=int(bank['question_count'] or 0),
        share_count=int(bank['share_count'] or 0),
    )


@user_bank_pages_bp.route('/shared')
@login_required
def shared_banks():
    """收到的分享列表页面"""
    return render_template('user_bank/share/shared_banks.html')


@user_bank_pages_bp.route('/<int:bank_id>/quiz')
@login_required
def bank_quiz(bank_id):
    """题库刷题页面（复用共有题库刷题模板）"""
    bank_mode = (request.args.get('mode') or 'all').strip().lower()

    # 兼容旧的个人题库刷题参数：all/random/wrong
    params = [f'bank_id={bank_id}']
    if bank_mode == 'wrong':
        params.append('source=mistakes')
    elif bank_mode == 'favorites':
        params.append('source=favorites')
    elif bank_mode == 'random':
        params.append('shuffle_questions=1')

    return redirect('/quiz?' + '&'.join(params))
