# -*- coding: utf-8 -*-
"""AI 改动记录 ORM 模型。"""

from sqlalchemy import func

from app.core.extensions import db


class AIChangeRecord(db.Model):
    __tablename__ = "ai_change_records"
    __table_args__ = (
        db.Index("ix_ai_change_records_category_created", "category", "created_at"),
        db.Index("ix_ai_change_records_source_created", "source", "created_at"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(16), nullable=False)
    summary = db.Column(db.String(160), nullable=False)
    detail_json = db.Column(db.Text, nullable=False, default="{}", server_default="{}")
    source = db.Column(db.String(32), nullable=False, default="codex", server_default="codex")
    external_id = db.Column(db.String(128), unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(
        db.DateTime,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<AIChangeRecord {self.id} {self.category!r}>"
