# -*- coding: utf-8 -*-
"""Admin API routes - campus management."""

from __future__ import annotations

from flask import current_app, request

from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import admin_required
from app.core.utils.validators import parse_int
from app.modules.admin.services.campus_management_service import CampusManagementService

from ..api_bp import admin_api_bp


_ALLOWED_SNAPSHOT_KINDS = {"schedule", "grades"}


def _snapshot_kind(value: str) -> str:
    kind = (value or "schedule").strip().lower()
    if kind not in _ALLOWED_SNAPSHOT_KINDS:
        raise ValueError("查询类型仅支持 schedule 或 grades")
    return kind


@admin_api_bp.route("/campus/credentials", methods=["GET"])
@admin_required
def api_campus_credentials():
    try:
        page = parse_int(request.args.get("page"), 1, 1)
        size = parse_int(request.args.get("size"), 20, 5, 100)
        data = CampusManagementService.list_credentials(
            search=(request.args.get("search") or "").strip(),
            page=page,
            size=size,
        )
        return success_response(data=data)
    except Exception as exc:
        current_app.logger.error("加载校园凭据失败: %s", type(exc).__name__, exc_info=True)
        return error_response("加载校园凭据失败，请稍后重试", status_code=500)


@admin_api_bp.route("/campus/records", methods=["GET"])
@admin_required
def api_campus_records():
    try:
        page = parse_int(request.args.get("page"), 1, 1)
        size = parse_int(request.args.get("size"), 20, 5, 100)
        data = CampusManagementService.list_records(
            search=(request.args.get("search") or "").strip(),
            page=page,
            size=size,
        )
        return success_response(data=data)
    except Exception as exc:
        current_app.logger.error("加载校园绑定记录失败: %s", type(exc).__name__, exc_info=True)
        return error_response("加载校园绑定记录失败，请稍后重试", status_code=500)


@admin_api_bp.route("/campus/records/<record_key>", methods=["GET"])
@admin_required
def api_campus_record_detail(record_key: str):
    try:
        data = CampusManagementService.get_record_detail(record_key)
        if data is None:
            return error_response("校园绑定记录不存在", status_code=404)
        return success_response(data=data)
    except Exception as exc:
        current_app.logger.error("加载校园绑定详情失败: %s", type(exc).__name__, exc_info=True)
        return error_response("加载校园绑定详情失败，请稍后重试", status_code=500)


@admin_api_bp.route("/campus/snapshots", methods=["GET"])
@admin_required
def api_campus_snapshots():
    try:
        kind = _snapshot_kind(request.args.get("kind") or "schedule")
        page = parse_int(request.args.get("page"), 1, 1)
        size = parse_int(request.args.get("size"), 20, 5, 100)
        raw_user_id = (request.args.get("user_id") or "").strip()
        user_id = parse_int(raw_user_id, 0, 0) or None
        data = CampusManagementService.list_snapshots(
            kind,
            user_id=user_id,
            search=(request.args.get("search") or "").strip(),
            page=page,
            size=size,
        )
        return success_response(data=data)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("加载校园查询快照失败: %s", type(exc).__name__, exc_info=True)
        return error_response("加载校园查询快照失败，请稍后重试", status_code=500)


@admin_api_bp.route("/campus/snapshots/<kind>/<int:snapshot_id>", methods=["GET"])
@admin_required
def api_campus_snapshot_detail(kind: str, snapshot_id: int):
    try:
        normalized_kind = _snapshot_kind(kind)
        data = CampusManagementService.get_snapshot_detail(normalized_kind, snapshot_id)
        if data is None:
            return error_response("查询记录不存在", status_code=404)
        return success_response(data=data)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("加载校园查询详情失败: %s", type(exc).__name__, exc_info=True)
        return error_response("加载校园查询详情失败，请稍后重试", status_code=500)
