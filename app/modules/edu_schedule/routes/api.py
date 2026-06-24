# -*- coding: utf-8 -*-
"""教务课表用户 API。"""

from __future__ import annotations

from flask import Blueprint, current_app, request
from pydantic import ValidationError

from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import auth_required, current_user_id

from ..schemas import EduScheduleCredentialSchema, EduScheduleQuerySchema
from ..services.client import ScheduleAuthError, ScheduleClientError
from ..services.schedule_service import EduScheduleService, user_safe_error
from ..services.webvpn_refresh import (
    WEBVPN_REFRESH_REQUIRED_ERROR_CODE,
    WEBVPN_REFRESH_REQUIRED_MESSAGE,
    WebVPNSessionRefreshService,
    should_start_webvpn_refresh,
)


edu_schedule_api_bp = Blueprint("edu_schedule_api", __name__)


def _webvpn_refresh_required_response(user_id: int):
    challenge = WebVPNSessionRefreshService.start(owner_user_id=int(user_id))
    return error_response(
        WEBVPN_REFRESH_REQUIRED_MESSAGE,
        status_code=409,
        code=409,
        error_code=WEBVPN_REFRESH_REQUIRED_ERROR_CODE,
        data=challenge,
    )


@edu_schedule_api_bp.route("/edu-schedule/status", methods=["GET"])
@auth_required
def api_schedule_status():
    user_id = int(current_user_id() or 0)
    return success_response(
        data={
            "credential": EduScheduleService.credential_status(user_id),
            "snapshots": EduScheduleService.list_snapshots(user_id),
            "grade_snapshots": EduScheduleService.list_grade_snapshots(user_id),
        }
    )


@edu_schedule_api_bp.route("/edu-schedule/credentials", methods=["POST"])
@auth_required
def api_save_schedule_credentials():
    user_id = int(current_user_id() or 0)
    try:
        schema = EduScheduleCredentialSchema.model_validate(request.get_json(silent=True) or {})
        data = EduScheduleService.save_credentials(user_id, schema.username, schema.password)
        return success_response(data=data, message="教务凭据已加密保存")
    except ValidationError:
        current_app.logger.warning("保存教务凭据输入校验失败: ValidationError")
        return error_response("输入参数不正确", status_code=400)
    except Exception as exc:
        current_app.logger.warning("保存教务凭据失败: %s", type(exc).__name__)
        return error_response(user_safe_error(exc), status_code=400)


@edu_schedule_api_bp.route("/edu-schedule/credentials", methods=["DELETE"])
@auth_required
def api_delete_schedule_credentials():
    user_id = int(current_user_id() or 0)
    EduScheduleService.delete_credentials(user_id)
    return success_response(data={"has_credentials": False, "username_hint": ""}, message="教务凭据已删除")


@edu_schedule_api_bp.route("/edu-schedule/query", methods=["POST"])
@auth_required
def api_query_schedule():
    user_id = int(current_user_id() or 0)
    try:
        schema = EduScheduleQuerySchema.model_validate(request.get_json(silent=True) or {})
        data = EduScheduleService.query_terms(
            user_id,
            [term.model_dump() for term in schema.terms],
            username=schema.username,
            password=schema.password,
            remember=schema.remember,
        )
        return success_response(data=data, message="课表查询成功")
    except ValidationError:
        current_app.logger.warning("教务课表查询输入校验失败: ValidationError")
        return error_response("输入参数不正确", status_code=400)
    except Exception as exc:
        current_app.logger.warning("教务课表查询失败: %s", type(exc).__name__)
        if should_start_webvpn_refresh(exc):
            try:
                return _webvpn_refresh_required_response(user_id)
            except Exception as refresh_exc:
                current_app.logger.warning("生成 WebVPN 验证码失败: %s", type(refresh_exc).__name__)
        return error_response(user_safe_error(exc), status_code=400)


@edu_schedule_api_bp.route("/edu-schedule/grades/query", methods=["POST"])
@auth_required
def api_query_grades():
    user_id = int(current_user_id() or 0)
    try:
        schema = EduScheduleQuerySchema.model_validate(request.get_json(silent=True) or {})
        data = EduScheduleService.query_grade_terms(
            user_id,
            [term.model_dump() for term in schema.terms],
            username=schema.username,
            password=schema.password,
            remember=schema.remember,
        )
        return success_response(data=data, message="成绩查询成功")
    except ValidationError:
        current_app.logger.warning("教务成绩查询输入校验失败: ValidationError")
        return error_response("输入参数不正确", status_code=400)
    except Exception as exc:
        current_app.logger.warning("教务成绩查询失败: %s", type(exc).__name__)
        if should_start_webvpn_refresh(exc):
            try:
                return _webvpn_refresh_required_response(user_id)
            except Exception as refresh_exc:
                current_app.logger.warning("生成 WebVPN 验证码失败: %s", type(refresh_exc).__name__)
        return error_response(user_safe_error(exc), status_code=400)


@edu_schedule_api_bp.route("/edu-schedule/webvpn-session/complete", methods=["POST"])
@auth_required
def api_complete_user_webvpn_session_refresh():
    user_id = int(current_user_id() or 0)
    try:
        payload = request.get_json(silent=True) or {}
        data = WebVPNSessionRefreshService.complete(
            str(payload.get("challenge_id") or ""),
            str(payload.get("captcha_code") or ""),
            owner_user_id=user_id,
        )
        return success_response(data=data, message="WebVPN 登录态已刷新")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except (ScheduleAuthError, ScheduleClientError) as exc:
        current_app.logger.warning("用户提交 WebVPN 验证码失败: %s", type(exc).__name__)
        return error_response(user_safe_error(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error("用户提交 WebVPN 验证码失败: %s", type(exc).__name__, exc_info=True)
        return error_response("提交 WebVPN 验证码失败，请稍后重试", status_code=500)


@edu_schedule_api_bp.route("/edu-schedule/snapshots", methods=["GET"])
@auth_required
def api_list_schedule_snapshots():
    user_id = int(current_user_id() or 0)
    return success_response(data={"snapshots": EduScheduleService.list_snapshots(user_id)})


@edu_schedule_api_bp.route("/edu-schedule/grades/snapshots", methods=["GET"])
@auth_required
def api_list_grade_snapshots():
    user_id = int(current_user_id() or 0)
    return success_response(data={"snapshots": EduScheduleService.list_grade_snapshots(user_id)})
