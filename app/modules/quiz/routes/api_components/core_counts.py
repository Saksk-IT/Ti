# -*- coding: utf-8 -*-
"""题目计数路由 — 题目数量查询 + 用户收藏/错题计数

从 core.py 拆分，提供 /questions/count 和 /questions/user_counts 接口。
"""

from flask import request, jsonify, current_app

from app.core.utils.database import get_db
from app.core.extensions import limiter
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import (
    get_questions_version,
    get_subjects_version,
    get_user_quiz_version,
    make_cache_key,
)

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request


@quiz_api_bp.route('/questions/count')
@limiter.exempt  # 题目数量查询不限流
def api_questions_count():
    """获取题目数量（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type

    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', '').lower()
    source = request.args.get('source', '').lower()  # 兼容背题模式下的来源
    tag = (request.args.get('tag') or '').strip()
    uid = _get_uid_from_request()

    cache_key = None
    cache_ttl = 0

    def _ret(payload: dict):
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify(payload)

    if bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
        try:
            cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_COUNTS_SECONDS', 60) or 60)
        except Exception:
            cache_ttl = 60
        if cache_ttl > 0:
            try:
                uv = get_user_quiz_version(int(uid)) if uid else 0
                cache_key = make_cache_key(
                    'quiz:questions_count',
                    {
                        'uid': int(uid) if uid else 0,
                        'subject': subject,
                        'type': q_type,
                        'mode': mode,
                        'source': source,
                        'tag': tag,
                        'uv': int(uv),
                        'qv': get_questions_version(),
                        'sv': get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get('status') == 'success' and 'count' in cached:
                    return jsonify(cached)
            except Exception:
                cache_key = None

    conn = get_db()

    # 获取用户可访问的科目ID列表（用于权限过滤）
    accessible_subject_ids = None
    if uid:
        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return _ret({'status': 'success', 'count': 0})

    # 兼容新的 source 参数，优先使用 source，其次 mode
    target = source if source in ('favorites', 'mistakes') else mode

    if target == 'favorites':
        if not uid:
            return _ret({'status': 'success', 'count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN favorites f ON f.question_id = q.id AND f.user_id = ? WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = [uid]
    elif target == 'mistakes':
        if not uid:
            return _ret({'status': 'success', 'count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN mistakes m ON m.question_id = q.id AND m.user_id = ? WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = [uid]
    else:
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = []

    # 添加权限过滤
    if accessible_subject_ids is not None:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        base_sql += f" AND q.subject_id IN ({placeholders})"
        params.extend(accessible_subject_ids)
    # 未登录用户：不添加权限过滤，显示所有未锁定科目的题目数（已在base_sql中过滤了is_locked）

    if subject != 'all':
        base_sql += " AND s.name = ?"
        params.append(subject)

    if q_type != 'all':
        base_sql += " AND q.type = ?"
        params.append(any_type_to_portable_type(q_type))

    # 标签筛选：无登录 / 无命中直接返回 0（标签是用户私有）
    if tag and str(tag).lower() != 'all':
        if not uid:
            return _ret({'status': 'success', 'count': 0})
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({'status': 'success', 'count': 0})

        # 变量过多时避免 IN 触发 SQLite 参数上限：回退为取ID后求交集
        if len(tag_ids) > 900:
            id_rows = conn.execute("SELECT q.id " + base_sql, params).fetchall()
            base_ids = {int(r[0]) for r in id_rows if r and r[0] is not None}
            return _ret({'status': 'success', 'count': len(base_ids & set(tag_ids))})

        placeholders = ','.join(['?'] * len(tag_ids))
        sql = "SELECT COUNT(1) " + base_sql + f" AND q.id IN ({placeholders})"
        cnt = conn.execute(sql, params + list(tag_ids)).fetchone()[0]
        return _ret({'status': 'success', 'count': cnt})

    sql = "SELECT COUNT(1) " + base_sql
    cnt = conn.execute(sql, params).fetchone()[0]
    return _ret({'status': 'success', 'count': cnt})


@quiz_api_bp.route('/questions/user_counts')
@limiter.exempt  # 用户计数查询不限流
def api_user_counts():
    """获取用户的收藏和错题数量"""
    from app.core.utils.portable_question_format import any_type_to_portable_type

    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    tag = (request.args.get('tag') or '').strip()
    uid = _get_uid_from_request()

    if not uid:
        return jsonify({'status': 'success', 'favorites': 0, 'mistakes': 0})

    cache_key = None
    cache_ttl = 0

    def _ret(payload: dict):
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify(payload)

    if bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
        try:
            cache_ttl = int(current_app.config.get('QUIZ_CACHE_TTL_USER_COUNTS_SECONDS', 30) or 30)
        except Exception:
            cache_ttl = 30
        if cache_ttl > 0:
            try:
                cache_key = make_cache_key(
                    'quiz:user_counts',
                    {
                        'uid': int(uid),
                        'subject': subject,
                        'type': q_type,
                        'tag': tag,
                        'uv': get_user_quiz_version(int(uid)),
                        'qv': get_questions_version(),
                        'sv': get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get('status') == 'success':
                    if 'favorites' in cached and 'mistakes' in cached:
                        return jsonify(cached)
            except Exception:
                cache_key = None

    conn = get_db()

    fav_sql = """
        SELECT COUNT(1)
        FROM favorites f
        JOIN questions q ON q.id = f.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE f.user_id = ?
    """
    mis_sql = """
        SELECT COUNT(1)
        FROM mistakes m
        JOIN questions q ON q.id = m.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE m.user_id = ?
    """

    fav_params = [uid]
    mis_params = [uid]

    if subject != 'all':
        fav_sql += " AND s.name = ?"
        mis_sql += " AND s.name = ?"
        fav_params.append(subject)
        mis_params.append(subject)

    if q_type != 'all':
        fav_sql += " AND q.type = ?"
        mis_sql += " AND q.type = ?"
        fav_params.append(any_type_to_portable_type(q_type))
        mis_params.append(any_type_to_portable_type(q_type))

    # 标签筛选：标签为用户私有（存储在 user_progress）
    if tag and str(tag).lower() != 'all':
        from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag

        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({'status': 'success', 'favorites': 0, 'mistakes': 0})

        # 变量过多时避免 IN 触发 SQLite 参数上限：回退为取ID后求交集
        if len(tag_ids) > 900:
            tag_set = set(tag_ids)

            fav_id_rows = conn.execute(
                fav_sql.replace('SELECT COUNT(1)', 'SELECT q.id'),
                fav_params,
            ).fetchall()
            mis_id_rows = conn.execute(
                mis_sql.replace('SELECT COUNT(1)', 'SELECT q.id'),
                mis_params,
            ).fetchall()

            fav_ids = {int(r[0]) for r in fav_id_rows if r and r[0] is not None}
            mis_ids = {int(r[0]) for r in mis_id_rows if r and r[0] is not None}

            return _ret({
                'status': 'success',
                'favorites': len(fav_ids & tag_set),
                'mistakes': len(mis_ids & tag_set),
            })

        placeholders = ','.join(['?'] * len(tag_ids))
        fav_sql += f" AND q.id IN ({placeholders})"
        mis_sql += f" AND q.id IN ({placeholders})"
        fav_params.extend(list(tag_ids))
        mis_params.extend(list(tag_ids))

    fav_cnt = conn.execute(fav_sql, fav_params).fetchone()[0]
    mis_cnt = conn.execute(mis_sql, mis_params).fetchone()[0]

    return _ret({'status': 'success', 'favorites': fav_cnt, 'mistakes': mis_cnt})
