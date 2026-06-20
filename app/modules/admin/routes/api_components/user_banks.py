# -*- coding: utf-8 -*-
"""Admin API routes - user question bank management."""

from __future__ import annotations

from typing import Any

from flask import current_app, request, session
from sqlalchemy import text

from app.core.extensions import db, limiter
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import admin_required
from app.modules.user_bank.routes.api_uploads import _save_image_file, _validate_image_file
from app.modules.user_bank.services.plaza_metrics_service import ensure_plaza_metrics

from ..api_bp import admin_api_bp


PROFILE_FIELDS = {"name", "description", "public_description", "cover_image"}


def _refresh_public_bank_plaza_metrics() -> None:
    """刷新公开题库广场读模型，避免后台更新后前台继续显示旧数据。"""
    try:
        ensure_plaza_metrics(force=True)
    except Exception:
        current_app.logger.warning("刷新题库广场读模型失败", exc_info=True)


def _bool_from_payload(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _validate_profile_payload(data: dict[str, Any], *, partial: bool = False) -> tuple[dict[str, Any], str]:
    values: dict[str, Any] = {}

    if not partial or "name" in data:
        name = str(data.get("name") or "").strip()
        if not name or len(name) < 2 or len(name) > 50:
            return {}, "题库名称需要2-50个字符"
        values["name"] = name

    if not partial or "description" in data:
        description = str(data.get("description") or "").strip()
        if len(description) > 200:
            return {}, "描述不能超过200个字符"
        values["description"] = description

    if not partial or "public_description" in data:
        public_description = str(data.get("public_description") or "").strip()
        if len(public_description) > 200:
            return {}, "公开描述不能超过200个字符"
        values["public_description"] = public_description

    if not partial or "cover_image" in data:
        cover_image = str(data.get("cover_image") or "").strip()
        if len(cover_image) > 500:
            return {}, "封面地址不能超过500个字符"
        values["cover_image"] = cover_image or None

    return values, ""


def _bank_query(where_sql: str = "", order_sql: str = "ORDER BY b.updated_at DESC, b.id DESC") -> str:
    return f"""
        SELECT
            b.id,
            b.user_id,
            b.name,
            COALESCE(b.description, '') AS description,
            COALESCE(b.public_description, '') AS public_description,
            b.cover_image,
            b.is_public,
            b.question_count,
            b.status,
            b.public_at,
            b.created_at,
            b.updated_at,
            u.username AS owner_username,
            u.email AS owner_email
        FROM user_question_banks b
        JOIN users u ON u.id = b.user_id
        WHERE b.status = 1
        {where_sql}
        {order_sql}
    """


def _serialize_bank(row) -> dict[str, Any]:
    m = row._mapping
    return {
        "id": int(m["id"]),
        "name": m["name"] or "",
        "description": m["description"] or "",
        "public_description": m["public_description"] or "",
        "cover_image": m["cover_image"] or "",
        "is_public": bool(m["is_public"]),
        "question_count": int(m["question_count"] or 0),
        "status": int(m["status"] or 0),
        "public_at": str(m["public_at"]) if m["public_at"] else None,
        "created_at": str(m["created_at"]) if m["created_at"] else None,
        "updated_at": str(m["updated_at"]) if m["updated_at"] else None,
        "owner": {
            "id": int(m["user_id"]),
            "username": m["owner_username"] or "",
            "email": m["owner_email"] or "",
        },
    }


def _fetch_bank(bank_id: int):
    return db.session.execute(
        text(_bank_query("AND b.id = :bank_id", "")),
        {"bank_id": int(bank_id)},
    ).fetchone()


@admin_api_bp.route("/user-banks", methods=["GET"])
@admin_required
def api_admin_list_user_banks():
    """获取所有用户创建的题库列表。"""
    keyword = str(request.args.get("keyword") or "").strip()
    is_public = request.args.get("is_public")
    params: dict[str, Any] = {}
    filters: list[str] = []

    if keyword:
        filters.append(
            """
            AND (
                LOWER(b.name) LIKE :keyword OR
                LOWER(COALESCE(b.description, '')) LIKE :keyword OR
                LOWER(COALESCE(b.public_description, '')) LIKE :keyword OR
                LOWER(COALESCE(u.username, '')) LIKE :keyword OR
                LOWER(COALESCE(u.email, '')) LIKE :keyword
            )
            """
        )
        params["keyword"] = f"%{keyword.lower()}%"

    if is_public in {"0", "1", "true", "false"}:
        public_value = is_public in {"1", "true"}
        filters.append("AND b.is_public = :is_public")
        params["is_public"] = public_value

    rows = db.session.execute(text(_bank_query("\n".join(filters))), params).fetchall()
    banks = [_serialize_bank(row) for row in rows]
    total_questions = sum(bank["question_count"] for bank in banks)
    public_count = sum(1 for bank in banks if bank["is_public"])

    return success_response(
        data={
            "banks": banks,
            "total": len(banks),
            "public_count": public_count,
            "total_questions": total_questions,
        }
    )


@admin_api_bp.route("/user-banks", methods=["POST"])
@admin_required
def api_admin_create_user_bank():
    """由后台创建题库，默认归属当前管理员。"""
    data = request.get_json(silent=True) or {}
    values, message = _validate_profile_payload(data)
    if message:
        return error_response(message)

    is_public = _bool_from_payload(data.get("is_public", False))
    user_id = int(session.get("user_id") or 0)
    if not user_id:
        return error_response("请先登录", 401, code=401)

    result = db.session.execute(
        text(
            """
            INSERT INTO user_question_banks (
                user_id, name, description, public_description, cover_image,
                is_public, public_at, status
            )
            VALUES (
                :user_id, :name, :description, :public_description, :cover_image,
                :is_public, CASE WHEN :is_public THEN CURRENT_TIMESTAMP ELSE NULL END, 1
            )
            RETURNING id
            """
        ),
        {
            "user_id": user_id,
            "is_public": is_public,
            **values,
        },
    )
    bank_id = int(result.scalar_one())
    db.session.commit()
    if is_public:
        _refresh_public_bank_plaza_metrics()

    return success_response(data={"bank": _serialize_bank(_fetch_bank(bank_id))}, message="题库创建成功")


@admin_api_bp.route("/user-banks/<int:bank_id>", methods=["PUT"])
@admin_required
def api_admin_update_user_bank(bank_id: int):
    """后台编辑任意用户题库资料。"""
    data = request.get_json(silent=True) or {}
    existing = _fetch_bank(bank_id)
    if not existing:
        return error_response("题库不存在", 404, code=404)

    values, message = _validate_profile_payload(data, partial=True)
    if message:
        return error_response(message)
    if not values:
        return error_response("没有要更新的内容")

    updates = [f"{field} = :{field}" for field in values]
    params = {"bank_id": int(bank_id), **values}
    db.session.execute(
        text(
            f"""
            UPDATE user_question_banks
            SET {", ".join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = :bank_id AND status = 1
            """
        ),
        params,
    )
    db.session.commit()
    if bool(existing._mapping["is_public"]) and any(field in values for field in PROFILE_FIELDS):
        _refresh_public_bank_plaza_metrics()

    return success_response(data={"bank": _serialize_bank(_fetch_bank(bank_id))}, message="题库更新成功")


@admin_api_bp.route("/user-banks/<int:bank_id>/public", methods=["POST"])
@admin_required
def api_admin_set_user_bank_public(bank_id: int):
    """后台统一管理任意用户题库公开状态。"""
    data = request.get_json(silent=True) or {}
    existing = _fetch_bank(bank_id)
    if not existing:
        return error_response("题库不存在", 404, code=404)

    is_public = _bool_from_payload(data.get("is_public", False))
    params: dict[str, Any] = {"bank_id": int(bank_id)}
    public_desc_sql = ""
    if "public_description" in data:
        public_description = str(data.get("public_description") or "").strip()
        if len(public_description) > 200:
            return error_response("公开描述不能超过200个字符")
        public_desc_sql = ", public_description = :public_description"
        params["public_description"] = public_description

    if is_public:
        db.session.execute(
            text(
                f"""
                UPDATE user_question_banks
                SET is_public = true,
                    public_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                    {public_desc_sql}
                WHERE id = :bank_id AND status = 1
                """
            ),
            params,
        )
        message = "题库已公开"
    else:
        db.session.execute(
            text(
                f"""
                UPDATE user_question_banks
                SET is_public = false,
                    public_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                    {public_desc_sql}
                WHERE id = :bank_id AND status = 1
                """
            ),
            params,
        )
        message = "题库已设为私密"

    db.session.commit()
    _refresh_public_bank_plaza_metrics()
    return success_response(data={"bank": _serialize_bank(_fetch_bank(bank_id))}, message=message)


@admin_api_bp.route("/user-banks/<int:bank_id>/cover/upload", methods=["POST"])
@admin_required
@limiter.limit("10 per minute;200 per day")
def api_admin_upload_user_bank_cover(bank_id: int):
    """后台上传任意用户题库封面。"""
    if not _fetch_bank(bank_id):
        return error_response("题库不存在", 404, code=404)

    file_storage = request.files.get("file") or request.files.get("cover")
    extension, message = _validate_image_file(file_storage, label="封面图片")
    if not extension:
        return error_response(message)

    try:
        saved = _save_image_file(
            file_storage,
            extension,
            folder="bank_covers",
            filename_prefix=f"bank_cover_admin_{int(session.get('user_id') or 0)}",
        )
    except Exception as exc:
        current_app.logger.error("后台题库封面上传失败: %s", exc, exc_info=True)
        return error_response("上传失败，请稍后重试", 500)

    return success_response(data=saved, message="封面上传成功")
