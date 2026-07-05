# -*- coding: utf-8 -*-
"""add ai change records

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-05 17:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_change_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.String(length=160), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="codex"),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("external_id", name="uq_ai_change_records_external_id"),
    )
    op.create_index(
        "ix_ai_change_records_category_created",
        "ai_change_records",
        ["category", "created_at"],
    )
    op.create_index(
        "ix_ai_change_records_source_created",
        "ai_change_records",
        ["source", "created_at"],
    )


def downgrade():
    op.drop_index("ix_ai_change_records_source_created", table_name="ai_change_records")
    op.drop_index("ix_ai_change_records_category_created", table_name="ai_change_records")
    op.drop_table("ai_change_records")
