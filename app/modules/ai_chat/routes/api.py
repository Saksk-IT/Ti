# -*- coding: utf-8 -*-
"""AI 聊天 API。"""
from flask import Blueprint, Response, request, stream_with_context

from app.core.extensions import limiter
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.validators import parse_int
from app.modules.ai_chat.services import ai_chat_service


ai_chat_api_bp = Blueprint("ai_chat_api", __name__)


def _uid() -> int:
    return int(current_user_id() or 0)


@ai_chat_api_bp.route("/ai-chat/models", methods=["GET"])
@auth_required
@limiter.limit("120/minute")
def ai_chat_models():
    return success_response(data=ai_chat_service.get_model_options())


@ai_chat_api_bp.route("/ai-chat/sessions", methods=["GET"])
@auth_required
@limiter.limit("120/minute")
def ai_chat_sessions():
    limit = parse_int(request.args.get("limit"), 80, min_val=1, max_val=120)
    return success_response(data={"sessions": ai_chat_service.list_sessions(_uid(), limit=limit)})


@ai_chat_api_bp.route("/ai-chat/sessions", methods=["POST"])
@auth_required
@limiter.limit("30/minute")
def ai_chat_create_session():
    data = request.get_json(silent=True) or {}
    try:
        row = ai_chat_service.create_session(
            _uid(),
            model=data.get("model"),
            title=data.get("title") or data.get("prompt"),
        )
        return success_response(data={"session": ai_chat_service.serialize_session(row)}, message="会话已创建")
    except ValueError as exc:
        return error_response(str(exc), status_code=400)


@ai_chat_api_bp.route("/ai-chat/sessions/<int:session_id>/messages", methods=["GET"])
@auth_required
@limiter.limit("120/minute")
def ai_chat_messages(session_id: int):
    try:
        return success_response(data={"messages": ai_chat_service.list_messages(session_id, _uid())})
    except LookupError:
        return error_response("会话不存在", status_code=404)


@ai_chat_api_bp.route("/ai-chat/sessions/<int:session_id>", methods=["PATCH"])
@auth_required
@limiter.limit("30/minute")
def ai_chat_update_session(session_id: int):
    data = request.get_json(silent=True) or {}
    try:
        row = ai_chat_service.update_session(
            session_id,
            _uid(),
            title=data.get("title") if "title" in data else None,
            model=data.get("model") if "model" in data else None,
        )
        return success_response(data={"session": ai_chat_service.serialize_session(row)}, message="会话已更新")
    except LookupError:
        return error_response("会话不存在", status_code=404)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)


@ai_chat_api_bp.route("/ai-chat/sessions/<int:session_id>", methods=["DELETE"])
@auth_required
@limiter.limit("30/minute")
def ai_chat_delete_session(session_id: int):
    try:
        ai_chat_service.delete_session(session_id, _uid())
        return success_response(message="会话已删除")
    except LookupError:
        return error_response("会话不存在", status_code=404)


@ai_chat_api_bp.route("/ai-chat/sessions/<int:session_id>/messages/stream", methods=["POST"])
@auth_required
@limiter.limit("10/minute;60/hour")
def ai_chat_stream_message(session_id: int):
    data = request.get_json(silent=True) or {}
    content = data.get("content")
    model = data.get("model")

    try:
        uid = _uid()
        ai_chat_service.get_session_for_user(session_id, uid)
        ai_chat_service.validate_model(model)
        if not str(content or "").strip():
            return error_response("消息不能为空", status_code=400)
        if len(str(content or "").strip()) > ai_chat_service.MAX_MESSAGE_CHARS:
            return error_response(f"消息过长（最多 {ai_chat_service.MAX_MESSAGE_CHARS} 字）", status_code=400)
    except LookupError:
        return error_response("会话不存在", status_code=404)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)

    stream = ai_chat_service.stream_chat_reply(
        session_id=session_id,
        user_id=_uid(),
        content=content,
        model=model,
    )
    return Response(
        stream_with_context(stream),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )
