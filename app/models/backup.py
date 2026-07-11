# -*- coding: utf-8 -*-
"""数据库备份任务 ORM 模型。"""

from __future__ import annotations

import uuid
from datetime import timezone
from typing import Any, Dict, Optional

from sqlalchemy import func

from app.core.extensions import db


def _isoformat(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    normalized = (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )
    return normalized.isoformat().replace("+00:00", "Z")


def _active_slot_default(context: Any) -> Optional[str]:
    status = str(context.get_current_parameters().get("status") or "queued")
    return "global" if status in {"queued", "running"} else None


class BackupJob(db.Model):
    """一次数据库备份任务及其对象存储结果。"""

    __tablename__ = "backup_jobs"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'deleting')",
            name="ck_backup_jobs_status",
        ),
        db.CheckConstraint(
            "trigger IN ('manual', 'scheduled')",
            name="ck_backup_jobs_trigger",
        ),
        db.CheckConstraint(
            "active_slot IS NULL OR active_slot = 'global'",
            name="ck_backup_jobs_active_slot",
        ),
        db.UniqueConstraint("active_slot", name="uq_backup_jobs_active_slot"),
        db.UniqueConstraint("schedule_slot", name="uq_backup_jobs_schedule_slot"),
        db.Index("ix_backup_jobs_status_created", "status", "created_at"),
        {"extend_existing": True},
    )

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    status = db.Column(
        db.String(16), nullable=False, default="queued", server_default="queued"
    )
    trigger = db.Column(
        db.String(16), nullable=False, default="manual", server_default="manual"
    )
    active_slot = db.Column(
        db.String(16),
        nullable=True,
        default=_active_slot_default,
        server_default="global",
    )
    schedule_slot = db.Column(db.String(32), nullable=True)
    object_key = db.Column(db.String(1024))
    filename = db.Column(db.String(255))
    size_bytes = db.Column(db.BigInteger)
    sha256 = db.Column(db.String(64))
    error_message = db.Column(db.Text)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at = db.Column(db.DateTime)
    lease_expires_at = db.Column(db.DateTime)
    worker_token = db.Column(db.String(36))
    completed_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(
        db.DateTime, nullable=False, default=func.now(), server_default=func.now()
    )

    def to_dict(self) -> Dict[str, Any]:
        """使用固定白名单序列化，避免未来新增内部字段时意外外泄。"""
        return {
            "id": self.id,
            "status": self.status,
            "trigger": self.trigger,
            "object_key": self.object_key,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "started_at": _isoformat(self.started_at),
            "completed_at": _isoformat(self.completed_at),
            "expires_at": _isoformat(self.expires_at),
            "created_at": _isoformat(self.created_at),
        }

    def __repr__(self) -> str:
        return f"<BackupJob {self.id} status={self.status!r}>"
