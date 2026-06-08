# -*- coding: utf-8 -*-
"""AI 聊天会话 ORM 模型。"""
from sqlalchemy import func

from app.core.extensions import db


class AIChatSession(db.Model):
    __tablename__ = "ai_chat_sessions"
    __table_args__ = (
        db.Index("ix_ai_chat_sessions_user_updated", "user_id", "updated_at"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.Text, nullable=False)
    model = db.Column(db.Text, nullable=False)
    provider = db.Column(db.Text, nullable=False, default="custom", server_default="custom")
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    messages = db.relationship(
        "AIChatMessage",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<AIChatSession {self.id} user={self.user_id}>"


class AIChatMessage(db.Model):
    __tablename__ = "ai_chat_messages"
    __table_args__ = (
        db.Index("ix_ai_chat_messages_session_created", "session_id", "created_at"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False, default="", server_default="")
    model = db.Column(db.Text)
    provider = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, default="completed", server_default="completed")
    error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<AIChatMessage {self.id} session={self.session_id} role={self.role}>"
