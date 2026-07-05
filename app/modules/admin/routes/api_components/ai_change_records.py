# -*- coding: utf-8 -*-
"""Admin API routes - AI change records."""

from __future__ import annotations

import hmac
import os
from functools import wraps

from flask import current_app, request, session

from ..api_bp import admin_api_bp
from app.core.extensions import db
from app.core.utils.api_response import error_response, success_response
from app.core.utils.validators import parse_int
from app.models.system import SystemConfig
from app.modules.admin.schemas import AIChangeRecordCreateSchema
from app.modules.admin.services.ai_change_record_service import AIChangeRecordService


def _configured_record_token() -> str:
    env_token = str(os.environ.get("AI_CHANGE_RECORD_TOKEN") or "").strip()
    if env_token:
        return env_token

    row = SystemConfig.query.filter_by(config_key="ai_change_record_token").first()
    return str(row.config_value or "").strip() if row else ""


def _request_record_token() -> str:
    header_token = str(request.headers.get("X-AI-Record-Token") or "").strip()
    if header_token:
        return header_token

    auth_header = str(request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return ""


def _has_valid_record_token() -> bool:
    expected = _configured_record_token()
    received = _request_record_token()
    return bool(expected and received and hmac.compare_digest(received, expected))


def _record_auth_required(view_func):
    @wraps(view_func)
    def decorated(*args, **kwargs):
        if session.get("user_id") and session.get("is_admin"):
            return view_func(*args, **kwargs)
        if _has_valid_record_token():
            return view_func(*args, **kwargs)
        if session.get("user_id"):
            return error_response("需要管理员权限", status_code=403)
        return error_response("缺少 AI 改动记录调用令牌或管理员登录", status_code=401)

    return decorated


@admin_api_bp.route("/ai-change-records", methods=["POST"])
@_record_auth_required
def create_ai_change_record():
    """创建 AI 改动记录，供 Codex/MCP 或后台管理员调用。"""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("请求数据不能为空", status_code=400)

    try:
        schema = AIChangeRecordCreateSchema.model_validate(payload)
        created_by = session.get("user_id") if session.get("is_admin") else None
        data = AIChangeRecordService.create_record(schema.model_dump(), created_by=created_by)
        return success_response(data=data, message="AI 改动记录已保存")
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("AI 改动记录保存失败: %s", exc, exc_info=True)
        return error_response("AI 改动记录保存失败", status_code=500)


@admin_api_bp.route("/ai-change-records", methods=["GET"])
@_record_auth_required
def list_ai_change_records():
    """查询 AI 改动记录。"""
    try:
        data = AIChangeRecordService.list_records(
            category=str(request.args.get("category") or "").strip(),
            q=str(request.args.get("q") or "").strip(),
            page=parse_int(request.args.get("page"), 1, min_val=1),
            size=parse_int(request.args.get("size"), 20, min_val=1, max_val=100),
        )
        return success_response(data=data)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("AI 改动记录查询失败: %s", exc, exc_info=True)
        return error_response("AI 改动记录查询失败", status_code=500)
