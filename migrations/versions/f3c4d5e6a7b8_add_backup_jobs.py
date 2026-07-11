# -*- coding: utf-8 -*-
"""add backup jobs

Revision ID: f3c4d5e6a7b8
Revises: d0e1f2a3b4c5
Create Date: 2026-07-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f3c4d5e6a7b8"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "backup_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("trigger", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("active_slot", sa.String(length=16), nullable=True, server_default="global"),
        sa.Column("schedule_slot", sa.String(length=32), nullable=True),
        sa.Column("object_key", sa.String(length=1024), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("worker_token", sa.String(length=36), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'deleting')",
            name="ck_backup_jobs_status",
        ),
        sa.CheckConstraint(
            "trigger IN ('manual', 'scheduled')",
            name="ck_backup_jobs_trigger",
        ),
        sa.CheckConstraint(
            "active_slot IS NULL OR active_slot = 'global'",
            name="ck_backup_jobs_active_slot",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("active_slot", name="uq_backup_jobs_active_slot"),
        sa.UniqueConstraint("schedule_slot", name="uq_backup_jobs_schedule_slot"),
    )
    op.create_index(
        "ix_backup_jobs_status_created",
        "backup_jobs",
        ["status", "created_at"],
    )


def downgrade():
    op.drop_index("ix_backup_jobs_status_created", table_name="backup_jobs")
    op.drop_table("backup_jobs")
