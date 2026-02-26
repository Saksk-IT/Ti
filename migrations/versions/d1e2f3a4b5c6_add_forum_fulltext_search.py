# -*- coding: utf-8 -*-
"""add forum posts fulltext search index (PostgreSQL GIN)

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-02-26 21:00:00.000000
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        # 添加 tsvector 生成列 + GIN 索引
        try:
            conn.execute(text("""
                ALTER TABLE forum_posts
                ADD COLUMN IF NOT EXISTS search_vector tsvector
                GENERATED ALWAYS AS (
                    setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(content, '')), 'B')
                ) STORED
            """))
        except (OperationalError, ProgrammingError):
            pass

        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_forum_posts_search
                ON forum_posts USING GIN (search_vector)
            """))
        except (OperationalError, ProgrammingError):
            pass


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        try:
            conn.execute(text("DROP INDEX IF EXISTS ix_forum_posts_search"))
        except (OperationalError, ProgrammingError):
            pass

        try:
            conn.execute(text(
                "ALTER TABLE forum_posts DROP COLUMN IF EXISTS search_vector"
            ))
        except (OperationalError, ProgrammingError):
            pass
