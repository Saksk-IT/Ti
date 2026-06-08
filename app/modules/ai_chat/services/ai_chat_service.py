# -*- coding: utf-8 -*-
"""Web 前台 AI 聊天业务服务。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from flask import current_app

from app.core.extensions import db
from app.core.utils.json_helpers import safe_load
from app.core.utils.time_utils import now_bj
from app.models.ai_chat import AIChatMessage, AIChatSession
from app.modules.admin.services.system_config_service import SystemConfigService
from app.modules.quiz.services.ai_client import AIClient


MAX_MESSAGE_CHARS = 4000
MAX_TITLE_CHARS = 60
MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_CHARS = 16000
DEFAULT_SYSTEM_PROMPT = (
    "你是 SAK 题库系统的学习助手。请用简体中文回答，优先给出清晰、可执行、"
    "适合学习场景的建议。遇到不确定信息时说明不确定性，不要编造事实。"
)


@dataclass(frozen=True)
class ModelOption:
    id: str
    label: str
    provider: str
    default: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "provider": self.provider,
            "default": self.default,
        }


def _clean_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        text = text[:limit]
    return text


def _safe_model_id(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > 120:
        text = text[:120]
    return text


def _truncate_error(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > 500:
        text = text[:500]
    return text


def _title_from_prompt(prompt: str) -> str:
    title = " ".join((prompt or "").strip().split())
    if not title:
        return "新的 AI 会话"
    return title[:MAX_TITLE_CHARS]


def get_model_options() -> Dict[str, Any]:
    """返回普通用户可选择的后台允许模型。"""
    cfg = SystemConfigService.get_ai_config()
    provider = str(cfg.get("provider") or "custom").strip().lower() or "custom"
    default_model = _safe_model_id(cfg.get("model") or "qwen-plus")

    raw_allowed = ""
    row = SystemConfigService.get_config("ai_allowed_models")
    if row and row.get("config_value"):
        raw_allowed = str(row.get("config_value") or "")

    parsed = safe_load(raw_allowed, None)
    model_ids: List[str] = []
    labels: Dict[str, str] = {}

    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                model_id = _safe_model_id(item.get("id") or item.get("model") or item.get("value"))
                label = str(item.get("label") or item.get("name") or model_id).strip()
            else:
                model_id = _safe_model_id(item)
                label = model_id
            if model_id and model_id not in model_ids:
                model_ids.append(model_id)
                labels[model_id] = label or model_id
    elif raw_allowed:
        for part in raw_allowed.replace("\n", ",").split(","):
            model_id = _safe_model_id(part)
            if model_id and model_id not in model_ids:
                model_ids.append(model_id)
                labels[model_id] = model_id

    if default_model and default_model not in model_ids:
        model_ids.insert(0, default_model)
        labels[default_model] = default_model

    options = [
        ModelOption(
            id=model_id,
            label=labels.get(model_id) or model_id,
            provider=provider,
            default=(model_id == default_model),
        ).to_dict()
        for model_id in model_ids
    ]
    return {
        "models": options,
        "default_model": default_model,
        "provider": provider,
        "model_source": cfg.get("model_source") or "custom",
    }


def validate_model(model: Optional[str]) -> str:
    options = get_model_options()
    allowed = {str(item.get("id") or "") for item in options.get("models", [])}
    selected = _safe_model_id(model or options.get("default_model"))
    if not selected:
        raise ValueError("后台尚未配置可用模型")
    if selected not in allowed:
        raise ValueError("所选模型不可用")
    return selected


def assert_ai_runtime_ready() -> None:
    cfg = SystemConfigService.get_ai_config()
    if not str(cfg.get("api_key") or "").strip():
        raise RuntimeError("AI 服务尚未配置")
    if not str(cfg.get("base_url") or "").strip():
        raise RuntimeError("AI 服务地址尚未配置")


def serialize_session(row: AIChatSession) -> Dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "model": row.model,
        "provider": row.provider,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_message(row: AIChatMessage) -> Dict[str, Any]:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "role": row.role,
        "content": row.content,
        "model": row.model,
        "provider": row.provider,
        "status": row.status,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_sessions(user_id: int, limit: int = 80) -> List[Dict[str, Any]]:
    rows = (
        AIChatSession.query
        .filter_by(user_id=int(user_id))
        .order_by(AIChatSession.updated_at.desc(), AIChatSession.id.desc())
        .limit(max(1, min(int(limit or 80), 120)))
        .all()
    )
    return [serialize_session(row) for row in rows]


def get_session_for_user(session_id: int, user_id: int) -> AIChatSession:
    row = AIChatSession.query.filter_by(id=int(session_id), user_id=int(user_id)).first()
    if not row:
        raise LookupError("会话不存在")
    return row


def create_session(user_id: int, model: Optional[str] = None, title: Optional[str] = None) -> AIChatSession:
    cfg = SystemConfigService.get_ai_config()
    selected_model = validate_model(model)
    row = AIChatSession(
        user_id=int(user_id),
        title=_clean_text(title, MAX_TITLE_CHARS) or "新的 AI 会话",
        model=selected_model,
        provider=str(cfg.get("provider") or "custom").strip().lower() or "custom",
        created_at=now_bj(),
        updated_at=now_bj(),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_session(
    session_id: int,
    user_id: int,
    *,
    title: Optional[str] = None,
    model: Optional[str] = None,
) -> AIChatSession:
    row = get_session_for_user(session_id, user_id)
    if title is not None:
        clean_title = _clean_text(title, MAX_TITLE_CHARS)
        if not clean_title:
            raise ValueError("会话标题不能为空")
        row.title = clean_title
    if model is not None:
        row.model = validate_model(model)
    row.updated_at = now_bj()
    db.session.commit()
    return row


def delete_session(session_id: int, user_id: int) -> None:
    row = get_session_for_user(session_id, user_id)
    db.session.delete(row)
    db.session.commit()


def list_messages(session_id: int, user_id: int) -> List[Dict[str, Any]]:
    row = get_session_for_user(session_id, user_id)
    messages = (
        AIChatMessage.query
        .filter_by(session_id=row.id, user_id=int(user_id))
        .order_by(AIChatMessage.id.asc())
        .all()
    )
    return [serialize_message(msg) for msg in messages]


def _build_context(session_id: int, user_id: int, latest_prompt: str) -> List[Dict[str, str]]:
    rows = (
        AIChatMessage.query
        .filter(
            AIChatMessage.session_id == int(session_id),
            AIChatMessage.user_id == int(user_id),
            AIChatMessage.status == "completed",
            AIChatMessage.role.in_(("user", "assistant")),
        )
        .order_by(AIChatMessage.id.desc())
        .limit(MAX_CONTEXT_MESSAGES)
        .all()
    )
    rows = list(reversed(rows))

    messages: List[Dict[str, str]] = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    total_chars = len(DEFAULT_SYSTEM_PROMPT)
    for row in rows:
        content = str(row.content or "").strip()
        if not content:
            continue
        next_total = total_chars + len(content)
        if next_total > MAX_CONTEXT_CHARS:
            continue
        messages.append({"role": row.role, "content": content})
        total_chars = next_total

    messages.append({"role": "user", "content": latest_prompt})
    return messages


def _insert_message(
    *,
    session_id: int,
    user_id: int,
    role: str,
    content: str,
    model: Optional[str],
    provider: Optional[str],
    status: str,
    error: Optional[str] = None,
) -> AIChatMessage:
    row = AIChatMessage(
        session_id=int(session_id),
        user_id=int(user_id),
        role=role,
        content=content,
        model=model,
        provider=provider,
        status=status,
        error=error,
        created_at=now_bj(),
    )
    db.session.add(row)
    db.session.flush()
    return row


def _event(name: str, data: Dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_chat_reply(
    *,
    session_id: int,
    user_id: int,
    content: str,
    model: Optional[str] = None,
) -> Iterable[str]:
    """生成 SSE 事件并持久化一轮 AI 会话。"""
    prompt = _clean_text(content, MAX_MESSAGE_CHARS)
    if not prompt:
        raise ValueError("消息不能为空")
    if len(str(content or "").strip()) > MAX_MESSAGE_CHARS:
        raise ValueError(f"消息过长（最多 {MAX_MESSAGE_CHARS} 字）")

    session_row = get_session_for_user(session_id, user_id)
    cfg = SystemConfigService.get_ai_config()
    selected_model = validate_model(model or session_row.model)
    provider = str(cfg.get("provider") or session_row.provider or "custom").strip().lower() or "custom"

    messages = _build_context(session_row.id, user_id, prompt)
    now = now_bj()
    user_msg = _insert_message(
        session_id=session_row.id,
        user_id=int(user_id),
        role="user",
        content=prompt,
        model=selected_model,
        provider=provider,
        status="completed",
    )
    assistant_msg = _insert_message(
        session_id=session_row.id,
        user_id=int(user_id),
        role="assistant",
        content="",
        model=selected_model,
        provider=provider,
        status="streaming",
    )
    if session_row.title == "新的 AI 会话":
        session_row.title = _title_from_prompt(prompt)
    session_row.model = selected_model
    session_row.provider = provider
    session_row.updated_at = now
    db.session.commit()

    yield _event("meta", {
        "session": serialize_session(session_row),
        "user_message": serialize_message(user_msg),
        "assistant_message": serialize_message(assistant_msg),
    })

    client = AIClient(
        api_key=str(cfg.get("api_key") or ""),
        base_url=str(cfg.get("base_url") or ""),
        api_type=str(cfg.get("api_type") or "chat_completions"),
        provider=provider,
    )

    try:
        assert_ai_runtime_ready()
        reply_parts: List[str] = []
        for delta in client.stream_text(
            model=selected_model,
            messages=messages,
            temperature=0.3,
            top_p=0.85,
            max_tokens=1200,
            timeout=int(cfg.get("timeout") or 25),
        ):
            text = str(delta or "")
            if not text:
                continue
            reply_parts.append(text)
            yield _event("delta", {"message_id": assistant_msg.id, "text": text})

        reply = "".join(reply_parts).strip()
        if not reply:
            raise RuntimeError("AI 未返回有效内容")

        assistant_msg.content = reply
        assistant_msg.status = "completed"
        assistant_msg.error = None
        session_row.updated_at = now_bj()
        db.session.commit()
        yield _event("done", {
            "message": serialize_message(assistant_msg),
            "session": serialize_session(session_row),
        })
    except GeneratorExit:
        assistant_msg.status = "failed"
        assistant_msg.error = "客户端已断开连接"
        session_row.updated_at = now_bj()
        db.session.commit()
        raise
    except Exception as exc:
        db.session.rollback()
        try:
            assistant_msg = db.session.get(AIChatMessage, assistant_msg.id)
            session_row = db.session.get(AIChatSession, session_row.id)
            if assistant_msg:
                assistant_msg.status = "failed"
                assistant_msg.error = "AI 回复失败"
                assistant_msg.content = ""
            if session_row:
                session_row.updated_at = now_bj()
            db.session.commit()
        except Exception:
            db.session.rollback()
        current_app.logger.warning(
            "AI聊天回复失败: user_id=%s session_id=%s message_id=%s error=%s",
            user_id,
            session_id,
            getattr(assistant_msg, "id", None),
            exc.__class__.__name__,
            exc_info=True,
        )
        yield _event("error", {
            "message_id": getattr(assistant_msg, "id", None),
            "message": "AI 回复失败，请稍后重试。",
        })
