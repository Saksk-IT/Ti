# -*- coding: utf-8 -*-
"""题库广场查询服务。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.time_utils import now_bj

from .plaza_metrics_service import ensure_plaza_metrics

VALID_TABS = {'latest', 'hot', 'active', 'featured', 'questions'}
VALID_SCOPES = {'all', 'public', 'shared'}
VALID_MY_SCOPES = {'all', 'created', 'public', 'shared'}


def list_public_banks(
    *,
    tab: str = 'latest',
    board_id: int | None = None,
    keyword: str = '',
    page: int = 1,
    per_page: int = 12,
    user_id: int | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    ensure_plaza_metrics()
    current_tab = _normalize_tab(tab)
    current_keyword = _normalize_keyword(keyword)
    current_page = max(int(page or 1), 1)
    page_size = max(1, min(int(per_page or 12), 50))
    filters, params = _build_metric_filters(board_id=board_id, keyword=current_keyword, source_type=source_type)
    if current_tab == 'featured':
        filters.append('COALESCE(m.is_featured, false) = true')

    where_sql = _join_filters(filters)
    search_enabled = bool(current_keyword)
    total = db.session.execute(
        text(f'SELECT COUNT(*) AS total FROM public_bank_plaza_metrics m {where_sql}'),
        params,
    ).scalar() or 0

    params.update({'limit': page_size, 'offset': (current_page - 1) * page_size})
    query = text(
        f"""
        SELECT
            m.source_type,
            m.source_id,
            m.name,
            m.description,
            m.cover_image,
            m.owner_label,
            m.question_count_total,
            m.plaza_board_id,
            m.is_featured,
            m.featured_weight,
            m.published_at,
            m.last_activity_at,
            m.join_count_total,
            m.join_users_7d,
            m.join_users_30d,
            m.answer_count_7d,
            m.answer_count_30d,
            m.answer_users_7d,
            m.answer_users_30d,
            m.hot_score,
            m.active_score,
            m.recommended_score,
            {_keyword_rank_sql(search_enabled)} AS search_rank,
            b.slug AS board_slug,
            b.name AS board_name
        FROM public_bank_plaza_metrics m
        LEFT JOIN plaza_boards b ON b.id = m.plaza_board_id
        {where_sql}
        ORDER BY {_search_order_sql(current_tab, search_enabled)}
        LIMIT :limit OFFSET :offset
        """
    )
    rows = db.session.execute(query, params).mappings().all()
    relation_map = _get_public_relation_map(
        user_id,
        [int(row['source_id']) for row in rows if row.get('source_type') == 'user_public'],
    )

    items = [_serialize_metric_item(row, relation_map.get(int(row['source_id']))) for row in rows]
    return {
        'items': items,
        'total': int(total),
        'page': current_page,
        'per_page': page_size,
        'tab': current_tab,
        'keyword': current_keyword,
        'board_id': int(board_id) if board_id else None,
        'available_tabs': ['latest', 'hot', 'active', 'featured'],
    }


def get_plaza_summary(*, board_id: int | None = None, keyword: str = '') -> dict[str, Any]:
    ensure_plaza_metrics()
    filters, params = _build_metric_filters(board_id=board_id, keyword=keyword)
    where_sql = _join_filters(filters)
    summary = db.session.execute(
        text(
            f"""
            SELECT
                COUNT(*) AS total_banks,
                COALESCE(SUM(m.question_count_total), 0) AS total_questions,
                COUNT(DISTINCT m.plaza_board_id) AS total_boards,
                COUNT(CASE WHEN m.published_at >= :cutoff_7 THEN 1 END) AS new_banks_7d,
                SUM(CASE WHEN m.source_type = 'system' THEN 1 ELSE 0 END) AS system_count,
                SUM(CASE WHEN m.source_type = 'user_public' THEN 1 ELSE 0 END) AS user_public_count
            FROM public_bank_plaza_metrics m
            {where_sql}
            """
        ),
        {**params, 'cutoff_7': now_bj().replace(hour=0, minute=0, second=0, microsecond=0)},
    ).mappings().first() or {}

    active_users_7d = _count_active_users_7d(filters, params)
    return {
        'total_banks': int(summary.get('total_banks') or 0),
        'total_questions': int(summary.get('total_questions') or 0),
        'total_boards': int(summary.get('total_boards') or 0),
        'new_banks_7d': int(summary.get('new_banks_7d') or 0),
        'active_users_7d': int(active_users_7d),
        'source_breakdown': {
            'system': int(summary.get('system_count') or 0),
            'user_public': int(summary.get('user_public_count') or 0),
        },
    }


def list_plaza_boards(*, keyword: str = '') -> list[dict[str, Any]]:
    ensure_plaza_metrics()
    filters, params = _build_metric_filters(keyword=keyword)
    where_sql = _join_filters(filters)
    rows = db.session.execute(
        text(
            f"""
            SELECT
                b.id,
                b.slug,
                b.name,
                COALESCE(b.description, '') AS description,
                COUNT(m.id) AS bank_count
            FROM plaza_boards b
            LEFT JOIN public_bank_plaza_metrics m ON m.plaza_board_id = b.id
            {'WHERE b.is_active = true' if not where_sql else 'WHERE b.is_active = true AND ' + where_sql.replace('WHERE ', '', 1)}
            GROUP BY b.id, b.slug, b.name, b.description, b.sort_order
            ORDER BY b.sort_order ASC, bank_count DESC, b.id ASC
            """
        ),
        params,
    ).mappings().all()
    return [
        {
            'id': int(row['id']),
            'slug': row['slug'],
            'name': row['name'],
            'description': row['description'],
            'bank_count': int(row['bank_count'] or 0),
        }
        for row in rows
    ]


def list_hot_public_banks(*, board_id: int | None = None, keyword: str = '', limit: int = 5) -> list[dict[str, Any]]:
    data = list_public_banks(
        tab='hot',
        board_id=board_id,
        keyword=keyword,
        page=1,
        per_page=max(1, min(int(limit or 5), 10)),
    )
    return data['items']


def list_joined_banks(
    *,
    user_id: int,
    scope: str = 'all',
    keyword: str = '',
    page: int = 1,
    per_page: int = 12,
) -> dict[str, Any]:
    ensure_plaza_metrics()
    current_scope = _normalize_scope(scope)
    current_page = max(int(page or 1), 1)
    page_size = max(1, min(int(per_page or 12), 50))
    filters = [
        'b.status = 1',
        '(joined.has_public = 1 OR joined.has_shared = 1)',
    ]
    params: dict[str, Any] = {'uid': int(user_id), 'now_bj': now_bj()}
    if current_scope == 'public':
        filters.append('joined.has_public = 1')
    elif current_scope == 'shared':
        filters.append('joined.has_shared = 1')
    keyword_like = _keyword_like(keyword)
    if keyword_like:
        params['keyword'] = keyword_like
        filters.append('(LOWER(b.name) LIKE :keyword OR LOWER(COALESCE(NULLIF(b.public_description, \'\'), b.description, \'\')) LIKE :keyword)')

    where_sql = ' WHERE ' + ' AND '.join(filters)
    base_cte = _joined_cte_sql()
    total = db.session.execute(
        text(
            f"""
            {base_cte}
            SELECT COUNT(*) AS total
            FROM joined
            JOIN user_question_banks b ON b.id = joined.bank_id
            {where_sql}
            """
        ),
        params,
    ).scalar() or 0
    params.update({'limit': page_size, 'offset': (current_page - 1) * page_size})
    rows = db.session.execute(
        text(
            f"""
            {base_cte}
            SELECT
                b.id AS bank_id,
                b.name,
                COALESCE(NULLIF(b.public_description, ''), b.description, '') AS description,
                b.cover_image,
                b.question_count,
                COALESCE(u.username, '匿名用户') AS owner_label,
                b.plaza_board_id,
                pb.slug AS board_slug,
                pb.name AS board_name,
                joined.last_joined_at,
                joined.has_public,
                joined.has_shared,
                m.last_activity_at,
                m.join_count_total,
                m.answer_users_7d,
                m.is_featured
            FROM joined
            JOIN user_question_banks b ON b.id = joined.bank_id
            JOIN users u ON u.id = b.user_id
            LEFT JOIN plaza_boards pb ON pb.id = b.plaza_board_id
            LEFT JOIN public_bank_plaza_metrics m
              ON m.source_type = 'user_public' AND m.source_id = b.id
            {where_sql}
            ORDER BY joined.last_joined_at DESC, b.id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    relation_counts = _get_joined_relation_counts(user_id)
    items = [_serialize_joined_item(row) for row in rows]
    return {
        'items': items,
        'total': int(total),
        'page': current_page,
        'per_page': page_size,
        'scope': current_scope,
        'relation_counts': relation_counts,
    }


def list_my_bank_collections(
    *,
    user_id: int,
    scope: str = 'all',
    keyword: str = '',
    page: int = 1,
    per_page: int = 12,
) -> dict[str, Any]:
    ensure_plaza_metrics()
    current_scope = _normalize_my_scope(scope)
    current_keyword = _normalize_keyword(keyword)
    current_page = max(int(page or 1), 1)
    page_size = max(1, min(int(per_page or 12), 50))

    created_items = _list_created_bank_items(int(user_id), current_keyword)
    joined_items = _list_joined_bank_collection_items(int(user_id), current_keyword)
    counts = {
        'created': _count_created_banks(int(user_id)),
        **_get_joined_relation_counts(int(user_id)),
    }
    counts['all'] = int(counts.get('created') or 0) + int(counts.get('all') or 0)

    if current_scope == 'created':
        merged = created_items
    elif current_scope == 'public':
        merged = [item for item in joined_items if item.get('relation') in {'public', 'both'}]
    elif current_scope == 'shared':
        merged = [item for item in joined_items if item.get('relation') in {'shared', 'both'}]
    else:
        merged = created_items + joined_items

    merged.sort(
        key=lambda item: (
            1 if item.get('kind') == 'created' else 0,
            item.get('_sort_at') or '',
            int(item.get('id') or 0),
        ),
        reverse=True,
    )
    total = len(merged)
    start = (current_page - 1) * page_size
    end = start + page_size
    items = []
    for item in merged[start:end]:
        d = dict(item)
        d.pop('_sort_at', None)
        items.append(d)

    return {
        'items': items,
        'total': int(total),
        'page': current_page,
        'per_page': page_size,
        'scope': current_scope,
        'counts': counts,
    }


def get_public_bank_detail(*, bank_id: int, bank_type: str = 'user') -> dict[str, Any] | None:
    ensure_plaza_metrics()
    source_type = 'system' if str(bank_type).strip() == 'system' else 'user_public'
    row = db.session.execute(
        text(
            """
            SELECT
                source_type,
                source_id,
                name,
                description,
                cover_image,
                owner_label,
                question_count_total,
                published_at,
                last_activity_at,
                join_count_total,
                answer_users_7d,
                is_featured
            FROM public_bank_plaza_metrics
            WHERE source_type = :source_type AND source_id = :source_id
            """
        ),
        {'source_type': source_type, 'source_id': int(bank_id)},
    ).mappings().first()
    if not row:
        return None
    item = _serialize_metric_item(row, relation=None)
    item['bank_type'] = 'system' if source_type == 'system' else 'user'
    return item


def build_legacy_bank_list(
    *,
    sort: str = 'newest',
    bank_type: str = '',
    keyword: str = '',
    page: int = 1,
    per_page: int = 20,
    user_id: int | None = None,
) -> dict[str, Any]:
    source_type = None
    if bank_type == 'system':
        source_type = 'system'
    elif bank_type == 'user':
        source_type = 'user_public'
    tab = {
        'newest': 'latest',
        'popular': 'hot',
        'questions': 'questions',
    }.get(str(sort).strip(), 'latest')
    data = list_public_banks(
        tab=tab,
        keyword=keyword,
        page=page,
        per_page=per_page,
        user_id=user_id,
        source_type=source_type,
    )
    banks = []
    for item in data['items']:
        banks.append({
            'id': item['id'],
            'name': item['name'],
            'description': item['description'],
            'question_count': item['question_count'],
            'use_count': item['participants_total'],
            'allow_copy': 0,
            'public_at': item['published_at'],
            'created_at': item['published_at'],
            'owner_nickname': item['owner_label'],
            'owner_avatar': None,
            'bank_type': 'system' if item['source_type'] == 'system' else 'user',
            'is_shared': 0,
        })
    return {
        'banks': banks,
        'total': data['total'],
        'page': data['page'],
    }


def _count_created_banks(user_id: int) -> int:
    row = db.session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM user_question_banks
            WHERE user_id = :uid AND status = 1
            """
        ),
        {'uid': int(user_id)},
    ).mappings().first() or {}
    return int(row.get('total') or 0)



def _list_created_bank_items(user_id: int, keyword: str = '') -> list[dict[str, Any]]:
    params: dict[str, Any] = {'uid': int(user_id)}
    filters = ['b.user_id = :uid', 'b.status = 1']
    keyword_params = _keyword_search_params(keyword)
    if keyword_params:
        params.update(keyword_params)
        filters.append(
            "("             "LOWER(b.name) LIKE :keyword OR "             "LOWER(COALESCE(b.description, '')) LIKE :keyword OR "             "LOWER(COALESCE(b.public_description, '')) LIKE :keyword OR "             "LOWER(COALESCE(c.name, '')) LIKE :keyword"             ")"
        )
    where_sql = ' WHERE ' + ' AND '.join(filters)
    rows = db.session.execute(
        text(
            f"""
            SELECT
                b.id,
                b.name,
                COALESCE(NULLIF(b.description, ''), NULLIF(b.public_description, ''), '') AS description,
                b.question_count,
                b.is_public,
                b.public_use_count,
                b.share_count,
                b.updated_at,
                b.created_at,
                c.name AS category_name,
                COALESCE(m.answer_users_7d, 0) AS answer_users_7d,
                COALESCE(m.join_count_total, 0) AS participants_total,
                COALESCE(m.last_activity_at, b.updated_at, b.created_at) AS last_activity_at,
                COALESCE(m.is_featured, false) AS is_featured,
                pb.name AS board_name
            FROM user_question_banks b
            LEFT JOIN user_bank_categories c ON c.id = b.category_id
            LEFT JOIN public_bank_plaza_metrics m
              ON m.source_type = 'user_public' AND m.source_id = b.id
            LEFT JOIN plaza_boards pb ON pb.id = b.plaza_board_id
            {where_sql}
            ORDER BY COALESCE(b.updated_at, b.created_at) DESC, b.id DESC
            """
        ),
        params,
    ).mappings().all()
    return [_serialize_created_bank_item(row) for row in rows]



def _list_joined_bank_collection_items(user_id: int, keyword: str = '') -> list[dict[str, Any]]:
    params: dict[str, Any] = {'uid': int(user_id), 'now_bj': now_bj()}
    filters = [
        'b.status = 1',
        '(joined.has_public = 1 OR joined.has_shared = 1)',
    ]
    keyword_params = _keyword_search_params(keyword)
    if keyword_params:
        params.update(keyword_params)
        filters.append(
            "("             "LOWER(b.name) LIKE :keyword OR "             "LOWER(COALESCE(NULLIF(b.public_description, ''), b.description, '')) LIKE :keyword OR "             "LOWER(COALESCE(u.username, '')) LIKE :keyword"             ")"
        )
    where_sql = ' WHERE ' + ' AND '.join(filters)
    rows = db.session.execute(
        text(
            f"""
            {_joined_cte_sql()}
            SELECT
                b.id AS bank_id,
                b.name,
                COALESCE(NULLIF(b.public_description, ''), b.description, '') AS description,
                b.cover_image,
                b.question_count,
                COALESCE(u.username, '匿名用户') AS owner_label,
                b.plaza_board_id,
                pb.slug AS board_slug,
                pb.name AS board_name,
                joined.last_joined_at,
                joined.has_public,
                joined.has_shared,
                m.last_activity_at,
                m.join_count_total,
                m.answer_users_7d,
                m.is_featured
            FROM joined
            JOIN user_question_banks b ON b.id = joined.bank_id
            JOIN users u ON u.id = b.user_id
            LEFT JOIN plaza_boards pb ON pb.id = b.plaza_board_id
            LEFT JOIN public_bank_plaza_metrics m
              ON m.source_type = 'user_public' AND m.source_id = b.id
            {where_sql}
            ORDER BY joined.last_joined_at DESC, b.id DESC
            """
        ),
        params,
    ).mappings().all()
    return [_serialize_joined_bank_collection_item(row) for row in rows]



def _serialize_created_bank_item(row: dict[str, Any]) -> dict[str, Any]:
    bank_id = int(row.get('id') or 0)
    updated_at = row.get('updated_at') or row.get('created_at') or row.get('last_activity_at')
    is_public = bool(row.get('is_public'))
    return {
        'id': bank_id,
        'kind': 'created',
        'relation': 'created',
        'name': str(row.get('name') or '').strip(),
        'description': str(row.get('description') or '').strip(),
        'owner_label': '我创建的题库',
        'question_count': int(row.get('question_count') or 0),
        'participants_total': int(row.get('participants_total') or 0),
        'answer_users_7d': int(row.get('answer_users_7d') or 0),
        'is_featured': bool(row.get('is_featured')),
        'visibility_label': '公开' if is_public else '私密',
        'board': {
            'name': str(row.get('category_name') or row.get('board_name') or '未分类'),
        },
        'detail_url': f'/user/banks/{bank_id}/practice',
        'question_manage_url': f'/user/banks/{bank_id}',
        'manage_url': f'/user/banks/{bank_id}/manage',
        'updated_at': _datetime_text(updated_at),
        'last_activity_at': _datetime_text(row.get('last_activity_at') or updated_at),
        '_sort_at': _datetime_text(updated_at) or '',
    }



def _serialize_joined_bank_collection_item(row: dict[str, Any]) -> dict[str, Any]:
    data = _serialize_joined_item(row)
    relation = str(data.get('relation') or 'public')
    data['kind'] = 'joined'
    data['source_label'] = '公开 + 分享加入' if relation == 'both' else '分享加入' if relation == 'shared' else '公开加入'
    data['_sort_at'] = data.get('last_joined_at') or data.get('last_activity_at') or ''
    return data



def _normalize_my_scope(scope: str) -> str:
    current = str(scope or 'all').strip().lower()
    return current if current in VALID_MY_SCOPES else 'all'


def _build_metric_filters(*, board_id: int | None = None, keyword: str = '', source_type: str | None = None) -> tuple[list[str], dict[str, Any]]:
    filters: list[str] = []
    params: dict[str, Any] = {}
    if board_id:
        filters.append('m.plaza_board_id = :board_id')
        params['board_id'] = int(board_id)
    keyword_params = _keyword_search_params(keyword)
    if keyword_params:
        params.update(keyword_params)
        filters.append(
            "("             "LOWER(m.name) LIKE :keyword OR "             "LOWER(COALESCE(m.description, '')) LIKE :keyword OR "             "LOWER(COALESCE(m.owner_label, '')) LIKE :keyword"             ")"
        )
    if source_type in {'system', 'user_public'}:
        filters.append('m.source_type = :source_type')
        params['source_type'] = source_type
    return filters, params


def _count_active_users_7d(filters: list[str], params: dict[str, Any]) -> int:
    cutoff_7 = now_bj().replace(hour=0, minute=0, second=0, microsecond=0)
    where_sql = _join_filters(filters)
    row = db.session.execute(
        text(
            f"""
            WITH filtered AS (
                SELECT m.source_type, m.source_id
                FROM public_bank_plaza_metrics m
                {where_sql}
            ),
            events AS (
                SELECT 'system' AS source_type, q.subject_id AS source_id, ua.user_id AS user_id
                FROM questions q
                JOIN user_answers ua ON ua.question_id = q.id
                WHERE ua.created_at >= :cutoff_7
                UNION ALL
                SELECT 'user_public' AS source_type, p.bank_id AS source_id, p.user_id AS user_id
                FROM public_bank_users p
                WHERE COALESCE(p.last_access_at, p.created_at) >= :cutoff_7
                UNION ALL
                SELECT 'user_public' AS source_type, r.bank_id AS source_id, r.user_id AS user_id
                FROM bank_share_records r
                JOIN bank_shares bs ON bs.id = r.share_id
                WHERE r.status = 1
                  AND bs.is_active = true
                  AND (bs.expires_at IS NULL OR bs.expires_at > :now_bj)
                  AND COALESCE(r.last_access_at, r.created_at) >= :cutoff_7
                UNION ALL
                SELECT 'user_public' AS source_type, a.bank_id AS source_id, a.user_id AS user_id
                FROM user_bank_answers a
                WHERE a.created_at >= :cutoff_7
            )
            SELECT COUNT(DISTINCT events.user_id) AS active_users_7d
            FROM events
            JOIN filtered f
              ON f.source_type = events.source_type AND f.source_id = events.source_id
            """
        ),
        {**params, 'cutoff_7': cutoff_7, 'now_bj': now_bj()},
    ).mappings().first() or {}
    return int(row.get('active_users_7d') or 0)


def _get_public_relation_map(user_id: int | None, bank_ids: list[int]) -> dict[int, str]:
    if not user_id or not bank_ids:
        return {}
    ids = sorted({int(bank_id) for bank_id in bank_ids if int(bank_id) > 0})
    if not ids:
        return {}
    now = now_bj()
    in_clause, in_params = _build_named_in('bank_id', ids)
    params = {'uid': int(user_id), 'now_bj': now, **in_params}
    public_rows = db.session.execute(
        text(
            f"""
            SELECT bank_id
            FROM public_bank_users
            WHERE user_id = :uid AND bank_id IN ({in_clause})
            """
        ),
        params,
    ).mappings().all()
    shared_rows = db.session.execute(
        text(
            f"""
            SELECT DISTINCT bsr.bank_id
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bs.id = bsr.share_id
            WHERE bsr.user_id = :uid
              AND bsr.status = 1
              AND bs.is_active = true
              AND (bs.expires_at IS NULL OR bs.expires_at > :now_bj)
              AND bsr.bank_id IN ({in_clause})
            """
        ),
        params,
    ).mappings().all()
    public_ids = {int(row['bank_id']) for row in public_rows}
    shared_ids = {int(row['bank_id']) for row in shared_rows}
    relation_map: dict[int, str] = {}
    for bank_id in set(public_ids) | set(shared_ids):
        if bank_id in public_ids and bank_id in shared_ids:
            relation_map[bank_id] = 'both'
        elif bank_id in public_ids:
            relation_map[bank_id] = 'public'
        else:
            relation_map[bank_id] = 'shared'
    return relation_map


def _get_joined_relation_counts(user_id: int) -> dict[str, int]:
    row = db.session.execute(
        text(
            f"""
            {_joined_cte_sql()}
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN joined.has_public = 1 THEN 1 ELSE 0 END) AS public_count,
                SUM(CASE WHEN joined.has_shared = 1 THEN 1 ELSE 0 END) AS shared_count
            FROM joined
            """
        ),
        {'uid': int(user_id), 'now_bj': now_bj()},
    ).mappings().first() or {}
    return {
        'all': int(row.get('total') or 0),
        'public': int(row.get('public_count') or 0),
        'shared': int(row.get('shared_count') or 0),
    }


def _joined_cte_sql() -> str:
    return """
        WITH rel AS (
            SELECT bank_id, 'public' AS rel_type, COALESCE(last_access_at, created_at) AS joined_at
            FROM public_bank_users
            WHERE user_id = :uid
            UNION ALL
            SELECT bsr.bank_id, 'shared' AS rel_type, COALESCE(bsr.last_access_at, bsr.created_at) AS joined_at
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bs.id = bsr.share_id
            WHERE bsr.user_id = :uid
              AND bsr.status = 1
              AND bs.is_active = true
              AND (bs.expires_at IS NULL OR bs.expires_at > :now_bj)
        ),
        joined AS (
            SELECT
                bank_id,
                MAX(joined_at) AS last_joined_at,
                MAX(CASE WHEN rel_type = 'public' THEN 1 ELSE 0 END) AS has_public,
                MAX(CASE WHEN rel_type = 'shared' THEN 1 ELSE 0 END) AS has_shared
            FROM rel
            GROUP BY bank_id
        )
    """


def _serialize_metric_item(row: dict[str, Any], relation: str | None) -> dict[str, Any]:
    source_type = str(row.get('source_type') or 'user_public')
    source_id = int(row.get('source_id') or 0)
    detail_url = f'/subjects/{source_id}' if source_type == 'system' else f'/user/banks/{source_id}/practice'
    return {
        'id': source_id,
        'source_type': source_type,
        'name': str(row.get('name') or '').strip(),
        'description': str(row.get('description') or '').strip(),
        'cover_image': row.get('cover_image') or None,
        'owner_label': str(row.get('owner_label') or '').strip(),
        'question_count': int(row.get('question_count_total') or 0),
        'participants_total': int(row.get('join_count_total') or 0),
        'join_users_7d': int(row.get('join_users_7d') or 0),
        'answer_users_7d': int(row.get('answer_users_7d') or 0),
        'answer_count_7d': int(row.get('answer_count_7d') or 0),
        'hot_score': float(row.get('hot_score') or 0),
        'active_score': float(row.get('active_score') or 0),
        'recommended_score': float(row.get('recommended_score') or 0),
        'published_at': _datetime_text(row.get('published_at') or row.get('last_activity_at')),
        'last_activity_at': _datetime_text(row.get('last_activity_at')),
        'is_featured': bool(row.get('is_featured')),
        'featured_weight': int(row.get('featured_weight') or 0),
        'board': {
            'id': int(row['plaza_board_id']) if row.get('plaza_board_id') else None,
            'slug': row.get('board_slug') or None,
            'name': row.get('board_name') or '未分板块',
        },
        'detail_url': detail_url,
        'source_label': '系统题库' if source_type == 'system' else '用户公开',
        'relation': {
            'joined_via': relation or 'none',
            'is_joined': relation in {'public', 'shared', 'both'},
        },
    }


def _serialize_joined_item(row: dict[str, Any]) -> dict[str, Any]:
    relation = 'both' if int(row.get('has_public') or 0) and int(row.get('has_shared') or 0) else 'public' if int(row.get('has_public') or 0) else 'shared'
    return {
        'id': int(row.get('bank_id') or 0),
        'name': str(row.get('name') or '').strip(),
        'description': str(row.get('description') or '').strip(),
        'cover_image': row.get('cover_image') or None,
        'owner_label': str(row.get('owner_label') or '').strip(),
        'question_count': int(row.get('question_count') or 0),
        'participants_total': int(row.get('join_count_total') or 0),
        'answer_users_7d': int(row.get('answer_users_7d') or 0),
        'last_joined_at': _datetime_text(row.get('last_joined_at')),
        'last_activity_at': _datetime_text(row.get('last_activity_at')),
        'is_featured': bool(row.get('is_featured')),
        'board': {
            'id': int(row['plaza_board_id']) if row.get('plaza_board_id') else None,
            'slug': row.get('board_slug') or None,
            'name': row.get('board_name') or '未分板块',
        },
        'detail_url': f"/user/banks/{int(row.get('bank_id') or 0)}/practice",
        'relation': relation,
    }


def _datetime_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return value.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(value)


def _normalize_tab(tab: str) -> str:
    current = str(tab or 'latest').strip().lower()
    return current if current in VALID_TABS else 'latest'


def _normalize_scope(scope: str) -> str:
    current = str(scope or 'all').strip().lower()
    return current if current in VALID_SCOPES else 'all'


def _normalize_keyword(keyword: str) -> str:
    return ' '.join(str(keyword or '').strip().lower().split())


def _keyword_search_params(keyword: str) -> dict[str, str]:
    current = _normalize_keyword(keyword)
    if not current:
        return {}
    return {
        'keyword': f'%{current}%',
        'keyword_exact': current,
        'keyword_prefix': f'{current}%'
    }


def _join_filters(filters: list[str]) -> str:
    return f"WHERE {' AND '.join(filters)}" if filters else ''


def _order_sql(tab: str) -> str:
    if tab == 'hot':
        return 'm.hot_score DESC, m.published_at DESC, m.source_id DESC'
    if tab == 'active':
        return 'm.active_score DESC, m.last_activity_at DESC, m.source_id DESC'
    if tab == 'featured':
        return 'm.featured_weight DESC, m.recommended_score DESC, m.published_at DESC, m.source_id DESC'
    if tab == 'questions':
        return 'm.question_count_total DESC, m.published_at DESC, m.source_id DESC'
    return 'm.published_at DESC, m.source_id DESC'


def _keyword_rank_sql(search_enabled: bool) -> str:
    if not search_enabled:
        return '0'
    return (
        "("         "CASE "         "WHEN LOWER(m.name) = :keyword_exact THEN 120 "         "WHEN LOWER(m.name) LIKE :keyword_prefix THEN 90 "         "WHEN LOWER(m.name) LIKE :keyword THEN 70 "         "ELSE 0 END + "         "CASE "         "WHEN LOWER(COALESCE(m.description, '')) LIKE :keyword_prefix THEN 35 "         "WHEN LOWER(COALESCE(m.description, '')) LIKE :keyword THEN 20 "         "ELSE 0 END + "         "CASE WHEN LOWER(COALESCE(m.owner_label, '')) LIKE :keyword THEN 10 ELSE 0 END"         ")"
    )


def _search_order_sql(tab: str, search_enabled: bool) -> str:
    base = _order_sql(tab)
    if not search_enabled:
        return base
    return f'search_rank DESC, {base}'


def _build_named_in(prefix: str, values: list[int]) -> tuple[str, dict[str, int]]:
    params: dict[str, int] = {}
    names: list[str] = []
    for index, value in enumerate(values):
        key = f'{prefix}_{index}'
        params[key] = int(value)
        names.append(f':{key}')
    if not names:
        return 'NULL', {}
    return ', '.join(names), params
