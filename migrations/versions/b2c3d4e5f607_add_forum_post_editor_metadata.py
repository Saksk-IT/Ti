# -*- coding: utf-8 -*-
"""add forum post editor metadata fields

Revision ID: b2c3d4e5f607
Revises: a2b3c4d5e6f7
Create Date: 2026-03-04 12:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f607'
down_revision = 'a2b3c4d5e6f7'
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
    dialect = conn.dialect.name

    if not _column_exists(conn, 'forum_posts', 'cover_image'):
        op.add_column('forum_posts', sa.Column('cover_image', sa.Text(), nullable=True))

    if not _column_exists(conn, 'forum_posts', 'tags'):
        if dialect == 'postgresql':
            op.add_column(
                'forum_posts',
                sa.Column('tags', sa.JSON(), nullable=True, server_default=text("'[]'::jsonb")),
            )
        else:
            op.add_column(
                'forum_posts',
                sa.Column('tags', sa.JSON(), nullable=True, server_default='[]'),
            )

    if not _column_exists(conn, 'forum_posts', 'summary'):
        op.add_column('forum_posts', sa.Column('summary', sa.Text(), nullable=True))

    if not _column_exists(conn, 'forum_posts', 'markdown_source'):
        op.add_column('forum_posts', sa.Column('markdown_source', sa.Text(), nullable=True))

    try:
        conn.execute(text(
            "UPDATE forum_posts SET tags = '[]' "
            "WHERE tags IS NULL"
        ))
    except (OperationalError, ProgrammingError):
        pass


def downgrade():
    conn = op.get_bind()

    if _column_exists(conn, 'forum_posts', 'markdown_source'):
        op.drop_column('forum_posts', 'markdown_source')
    if _column_exists(conn, 'forum_posts', 'summary'):
        op.drop_column('forum_posts', 'summary')
    if _column_exists(conn, 'forum_posts', 'tags'):
        op.drop_column('forum_posts', 'tags')
    if _column_exists(conn, 'forum_posts', 'cover_image'):
        op.drop_column('forum_posts', 'cover_image')
