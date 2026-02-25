# -*- coding: utf-8 -*-
"""搜索相关路由：题目搜索。"""

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id

from ..api_bp import quiz_api_bp


def _build_named_in(prefix: str, values: list) -> tuple[str, dict]:
    """构建命名参数 IN 子句，返回 (placeholder_str, params_dict)"""
    params = {}
    names = []
    for i, v in enumerate(values):
        key = f"{prefix}_{i}"
        params[key] = v
        names.append(f":{key}")
    return ", ".join(names), params


@quiz_api_bp.route("/search", methods=["GET"])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_search_questions():
    """题目搜索（JSON，用于小程序）

    Query:
    - keyword: 搜索关键词（必填）
    - subject: 科目名称（可选，默认 all）
    - q_type/type: 题型（可选，默认 all）
    - source: 数据范围（all/favorites/mistakes，可选）
    - tag: 标签筛选（用户私有，可选）
    - page/per_page: 分页
    """
    import re
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    from app.core.utils.portable_question_format import any_type_to_portable_type, portable_type_to_q_type
    keyword = (request.args.get("keyword", "") or "").strip()
    subject = (request.args.get("subject", "all") or "all").strip()
    q_type = (request.args.get("q_type") or request.args.get("type") or "all").strip()
    source = (request.args.get("source") or "").strip().lower()
    tag = (request.args.get("tag") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    uid = current_user_id()

    # 无关键词：直接返回空结果（前端可做实时输入）
    if not keyword:
        return jsonify({
            "status": "success",
            "data": {"questions": [], "total": 0, "page": page, "per_page": per_page}
        })

    # 权限过滤：仅搜索可访问科目
    accessible_subject_ids = get_user_accessible_subjects(uid) if uid else []
    if not accessible_subject_ids:
        return jsonify({
            "status": "success",
            "data": {"questions": [], "total": 0, "page": page, "per_page": per_page}
        })

    search_term = f"%{keyword}%"
    sql_base = """
        SELECT q.id, q.content, q.type, s.name as subject,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = :uid
        LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = :uid
        WHERE (s.is_locked=false OR s.is_locked IS NULL)
          AND (q.content LIKE :search_term OR q.analysis LIKE :search_term
               OR q.options LIKE :search_term OR q.answer LIKE :search_term)
    """
    params: dict = {"uid": uid, "search_term": search_term}

    in_str, in_params = _build_named_in("asid", accessible_subject_ids)
    sql_base += f" AND q.subject_id IN ({in_str})"
    params.update(in_params)

    if subject and subject != "all":
        sql_base += " AND s.name = :subject_name"
        params["subject_name"] = subject

    if q_type and q_type != "all":
        sql_base += " AND q.type = :q_type"
        params["q_type"] = any_type_to_portable_type(q_type)

    if source == "favorites":
        sql_base += " AND f.id IS NOT NULL"
    elif source == "mistakes":
        sql_base += " AND m.id IS NOT NULL"

    # 标签筛选：标签为用户私有（存储于 user_progress）
    if tag and str(tag).lower() != "all":
        tag_ids = get_question_ids_by_tag(db.session.connection(), uid, tag)
        if not tag_ids:
            return jsonify({
                "status": "success",
                "data": {"questions": [], "total": 0, "page": page, "per_page": per_page}
            })

        tag_ids = sorted({int(x) for x in tag_ids})
        in_str_t, in_params_t = _build_named_in("tid", tag_ids)
        sql_base += f" AND q.id IN ({in_str_t})"
        params.update(in_params_t)

    # 统计总数
    count_sql = f"SELECT COUNT(*) FROM ({sql_base}) _sub"
    total = db.session.execute(text(count_sql), params).scalar() or 0

    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    params["limit_val"] = per_page
    params["offset_val"] = offset
    sql = sql_base + " ORDER BY q.id DESC LIMIT :limit_val OFFSET :offset_val"
    rows = db.session.execute(text(sql), params).fetchall()

    questions = []
    for row in rows:
        content_val = str(row[1]) if row[1] else ""
        try:
            text_preview = re.sub(r"<[^>]+>", "", content_val).replace("\n", " ").strip()
        except Exception:
            text_preview = content_val.replace("\n", " ").strip()
        if len(text_preview) > 80:
            text_preview = text_preview[:80] + "..."
        questions.append({
            "id": row[0],
            "content": content_val,
            "content_preview": text_preview,
            "q_type": portable_type_to_q_type(row[2]) if row[2] else "",
            "subject": row[3] or "",
            "is_fav": row[4] or 0,
            "is_mistake": row[5] or 0,
        })

    return jsonify({
        "status": "success",
        "data": {
            "questions": questions,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    })
