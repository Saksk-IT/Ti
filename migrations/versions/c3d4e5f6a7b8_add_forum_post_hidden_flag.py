# -*- coding: utf-8 -*-
"""add forum post hidden flag

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f607
Create Date: 2026-03-04 18:35:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f607'
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    dialect = conn.dialect.name
    try:
        if dialect == 'sqlite':
            result = conn.execute(text(f"PRAGMA table_info('{table}')"))
            return any(row[1] == column for row in result)
        if dialect == 'postgresql':
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ), {'t': table, 'c': column})
            return result.fetchone() is not None
        result = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c "
            "AND table_schema = DATABASE()"
        ), {'t': table, 'c': column})
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade():
    conn = op.get_bind()

    if not _column_exists(conn, 'forum_posts', 'is_hidden'):
        op.add_column(
            'forum_posts',
            sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default=text('false')),
        )

    try:
        conn.execute(text('UPDATE forum_posts SET is_hidden = false WHERE is_hidden IS NULL'))
    except (OperationalError, ProgrammingError):
        pass



def downgrade():
    conn = op.get_bind()

    if _column_exists(conn, 'forum_posts', 'is_hidden'):
        op.drop_column('forum_posts', 'is_hidden')
