# -*- coding: utf-8 -*-
"""add forum upload tracking

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-06 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def _table_exists(conn, table: str) -> bool:
    dialect = conn.dialect.name
    try:
        if dialect == 'sqlite':
            result = conn.execute(text(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            ))
            return result.fetchone() is not None
        if dialect == 'postgresql':
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
            ), {'t': table})
            return result.fetchone() is not None
        result = conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :t AND table_schema = DATABASE()"
        ), {'t': table})
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade():
    conn = op.get_bind()

    if not _table_exists(conn, 'forum_uploads'):
        op.create_table(
            'forum_uploads',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('filename', sa.String(255), nullable=False),
            sa.Column('filepath', sa.Text(), nullable=False),
            sa.Column('uploader_id', sa.Integer(), nullable=False),
            sa.Column('post_id', sa.Integer(), nullable=True),
            sa.Column('is_attached', sa.Boolean(), nullable=False, server_default=text('false')),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['post_id'], ['forum_posts.id'], ondelete='CASCADE'),
        )

        # 创建索引
        op.create_index('idx_forum_uploads_uploader', 'forum_uploads', ['uploader_id'])
        op.create_index('idx_forum_uploads_post', 'forum_uploads', ['post_id'])
        op.create_index('idx_forum_uploads_attached', 'forum_uploads', ['is_attached', 'uploaded_at'])


def downgrade():
    conn = op.get_bind()

    if _table_exists(conn, 'forum_uploads'):
        op.drop_index('idx_forum_uploads_attached', table_name='forum_uploads')
        op.drop_index('idx_forum_uploads_post', table_name='forum_uploads')
        op.drop_index('idx_forum_uploads_uploader', table_name='forum_uploads')
        op.drop_table('forum_uploads')
