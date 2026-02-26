# -*- coding: utf-8 -*-
"""add is_revoked column to chat_messages

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-02-27 03:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    try:
        if dialect == 'postgresql':
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS "
                "is_revoked BOOLEAN NOT NULL DEFAULT false"
            ))
        else:
            # SQLite
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN is_revoked BOOLEAN NOT NULL DEFAULT 0"
            ))
    except (OperationalError, ProgrammingError):
        # Column may already exist
        pass


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        try:
            conn.execute(text("ALTER TABLE chat_messages DROP COLUMN IF EXISTS is_revoked"))
        except (OperationalError, ProgrammingError):
            pass
    # SQLite does not support DROP COLUMN in older versions; skip
