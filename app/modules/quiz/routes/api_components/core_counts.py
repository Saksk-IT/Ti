# -*- coding: utf-8 -*-
"""题目计数路由 — 题目数量查询 + 用户收藏/错题计数

从 core.py 拆分，提供 /questions/count 和 /questions/user_counts 接口。
"""

from flask import request, jsonify, current_app
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import (
    get_questions_version,
    get_subjects_version,
    get_user_quiz_version,
    make_cache_key,
)

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request


def _build_named_in(prefix: str, values: list) -> tuple[str, dict]:
    """构建命名参数 IN 子句，返回 (placeholder_str, params_dict)"""
    params = {}
    names = []
    for i, v in enumerate(values):
        key = f"{prefix}_{i}"
        params[key] = v
        names.append(f":{key}")
    return ", ".join(names), params


@quiz_api_bp.route("/questions/count")
@limiter.exempt  # 题目数量查询不限流
def api_questions_count():
    """获取题目数量（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type
    from app.core.utils.database import get_db

    subject = request.args.get("subject", "all")
    q_type = request.args.get("type", "all")
    mode = request.args.get("mode", "").lower()
    source = request.args.get("source", "").lower()  # 兼容背题模式下的来源
    tag = (request.args.get("tag") or "").strip()
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

    if bool(current_app.config.get("QUIZ_API_CACHE_ENABLED", True)):
        try:
            cache_ttl = int(current_app.config.get("QUIZ_CACHE_TTL_COUNTS_SECONDS", 60) or 60)
        except Exception:
            cache_ttl = 60
        if cache_ttl > 0:
            try:
                uv = get_user_quiz_version(int(uid)) if uid else 0
                cache_key = make_cache_key(
                    "quiz:questions_count",
                    {
                        "uid": int(uid) if uid else 0,
                        "subject": subject,
                        "type": q_type,
                        "mode": mode,
                        "source": source,
                        "tag": tag,
                        "uv": int(uv),
                        "qv": get_questions_version(),
                        "sv": get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get("status") == "success" and "count" in cached:
                    return jsonify(cached)
            except Exception:
                cache_key = None

    # 获取用户可访问的科目ID列表（用于权限过滤）
    accessible_subject_ids = None
    if uid:
        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return _ret({"status": "success", "count": 0})

    # 兼容新的 source 参数，优先使用 source，其次 mode
    target = source if source in ("favorites", "mistakes") else mode

    params: dict = {}

    if target == "favorites":
        if not uid:
            return _ret({"status": "success", "count": 0})
        base_sql = ("FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id "
                     "JOIN favorites f ON f.question_id = q.id AND f.user_id = :uid "
                     "WHERE (s.is_locked=0 OR s.is_locked IS NULL)")
        params["uid"] = uid
    elif target == "mistakes":
        if not uid:
            return _ret({"status": "success", "count": 0})
        base_sql = ("FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id "
                     "JOIN mistakes m ON m.question_id = q.id AND m.user_id = :uid "
                     "WHERE (s.is_locked=0 OR s.is_locked IS NULL)")
        params["uid"] = uid
    else:
        base_sql = ("FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id "
                     "WHERE (s.is_locked=0 OR s.is_locked IS NULL)")

    # 添加权限过滤
    if accessible_subject_ids is not None:
        in_str, in_params = _build_named_in("asid", accessible_subject_ids)
        base_sql += f" AND q.subject_id IN ({in_str})"
        params.update(in_params)

    if subject != "all":
        base_sql += " AND s.name = :subject_name"
        params["subject_name"] = subject

    if q_type != "all":
        base_sql += " AND q.type = :q_type"
        params["q_type"] = any_type_to_portable_type(q_type)

    # 标签筛选：无登录 / 无命中直接返回 0（标签是用户私有）
    if tag and str(tag).lower() != "all":
        if not uid:
            return _ret({"status": "success", "count": 0})
        conn = get_db()
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({"status": "success", "count": 0})

        # 变量过多时：回退为取ID后求交集
        if len(tag_ids) > 900:
            id_rows = db.session.execute(
                text("SELECT q.id " + base_sql), params
            ).fetchall()
            base_ids = {int(r[0]) for r in id_rows if r and r[0] is not None}
            return _ret({"status": "success", "count": len(base_ids & set(tag_ids))})

        in_str, in_params = _build_named_in("tid", list(tag_ids))
        sql = "SELECT COUNT(1) " + base_sql + f" AND q.id IN ({in_str})"
        params.update(in_params)
        cnt = db.session.execute(text(sql), params).scalar()
        return _ret({"status": "success", "count": cnt or 0})

    sql = "SELECT COUNT(1) " + base_sql
    cnt = db.session.execute(text(sql), params).scalar()
    return _ret({"status": "success", "count": cnt or 0})


@quiz_api_bp.route("/questions/user_counts")
@limiter.exempt  # 用户计数查询不限流
def api_user_counts():
    """获取用户的收藏和错题数量"""
    from app.core.utils.portable_question_format import any_type_to_portable_type
    from app.core.utils.database import get_db

    subject = request.args.get("subject", "all")
    q_type = request.args.get("type", "all")
    tag = (request.args.get("tag") or "").strip()
    uid = _get_uid_from_request()

    if not uid:
        return jsonify({"status": "success", "favorites": 0, "mistakes": 0})

    cache_key = None
    cache_ttl = 0

    def _ret(payload: dict):
        if cache_key and cache_ttl > 0:
            try:
                redis_set_json(cache_key, payload, ttl_seconds=cache_ttl)
            except Exception:
                pass
        return jsonify(payload)

    if bool(current_app.config.get("QUIZ_API_CACHE_ENABLED", True)):
        try:
            cache_ttl = int(current_app.config.get("QUIZ_CACHE_TTL_USER_COUNTS_SECONDS", 30) or 30)
        except Exception:
            cache_ttl = 30
        if cache_ttl > 0:
            try:
                cache_key = make_cache_key(
                    "quiz:user_counts",
                    {
                        "uid": int(uid),
                        "subject": subject,
                        "type": q_type,
                        "tag": tag,
                        "uv": get_user_quiz_version(int(uid)),
                        "qv": get_questions_version(),
                        "sv": get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get("status") == "success":
                    if "favorites" in cached and "mistakes" in cached:
                        return jsonify(cached)
            except Exception:
                cache_key = None

    fav_sql = """
        SELECT COUNT(1)
        FROM favorites f
        JOIN questions q ON q.id = f.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE f.user_id = :uid
    """
    mis_sql = """
        SELECT COUNT(1)
        FROM mistakes m
        JOIN questions q ON q.id = m.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE m.user_id = :uid
    """

    fav_params: dict = {"uid": uid}
    mis_params: dict = {"uid": uid}

    if subject != "all":
        fav_sql += " AND s.name = :subject_name"
        mis_sql += " AND s.name = :subject_name"
        fav_params["subject_name"] = subject
        mis_params["subject_name"] = subject

    if q_type != "all":
        portable = any_type_to_portable_type(q_type)
        fav_sql += " AND q.type = :q_type"
        mis_sql += " AND q.type = :q_type"
        fav_params["q_type"] = portable
        mis_params["q_type"] = portable

    # 标签筛选：标签为用户私有（存储在 user_progress）
    if tag and str(tag).lower() != "all":
        from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag

        conn = get_db()
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return _ret({"status": "success", "favorites": 0, "mistakes": 0})

        # 变量过多时：回退为取ID后求交集
        if len(tag_ids) > 900:
            tag_set = set(tag_ids)

            fav_id_rows = db.session.execute(
                text(fav_sql.replace("SELECT COUNT(1)", "SELECT q.id")),
                fav_params,
            ).fetchall()
            mis_id_rows = db.session.execute(
                text(mis_sql.replace("SELECT COUNT(1)", "SELECT q.id")),
                mis_params,
            ).fetchall()

            fav_ids = {int(r[0]) for r in fav_id_rows if r and r[0] is not None}
            mis_ids = {int(r[0]) for r in mis_id_rows if r and r[0] is not None}

            return _ret({
                "status": "success",
                "favorites": len(fav_ids & tag_set),
                "mistakes": len(mis_ids & tag_set),
            })

        in_str_f, in_params_f = _build_named_in("ftid", list(tag_ids))
        in_str_m, in_params_m = _build_named_in("mtid", list(tag_ids))
        fav_sql += f" AND q.id IN ({in_str_f})"
        mis_sql += f" AND q.id IN ({in_str_m})"
        fav_params.update(in_params_f)
        mis_params.update(in_params_m)

    fav_cnt = db.session.execute(text(fav_sql), fav_params).scalar() or 0
    mis_cnt = db.session.execute(text(mis_sql), mis_params).scalar() or 0

    return _ret({"status": "success", "favorites": fav_cnt, "mistakes": mis_cnt})
