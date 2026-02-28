# -*- coding: utf-8 -*-
"""add phone, phone_verified, phone_verified_at to users

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-03-01 03:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    """检查列是否已存在（兼容 SQLite / PostgreSQL / MySQL）。"""
    dialect = conn.dialect.name
    try:
        if dialect == 'sqlite':
            result = conn.execute(text(f"PRAGMA table_info('{table}')"))
            return any(row[1] == column for row in result)
        elif dialect == 'postgresql':
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ), {'t': table, 'c': column})
            return result.fetchone() is not None
        else:  # mysql
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c "
                "AND table_schema = DATABASE()"
            ), {'t': table, 'c': column})
            return result.fetchone() is not None
    except Exception:
        return False


def _index_exists(conn, index_name: str) -> bool:
    """检查索引是否已存在。"""
    dialect = conn.dialect.name
    try:
        if dialect == 'sqlite':
            result = conn.execute(text(
                "SELECT 1 FROM sqlite_master WHERE type='index' AND name = :n"
            ), {'n': index_name})
            return result.fetchone() is not None
        elif dialect == 'postgresql':
            result = conn.execute(text(
                "SELECT 1 FROM pg_indexes WHERE indexname = :n"
            ), {'n': index_name})
            return result.fetchone() is not None
        else:  # mysql
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.statistics "
                "WHERE index_name = :n AND table_schema = DATABASE()"
            ), {'n': index_name})
            return result.fetchone() is not None
    except Exception:
        return False


def upgrade():
    conn = op.get_bind()

    # phone 列
    if not _column_exists(conn, 'users', 'phone'):
        op.add_column('users', sa.Column(
            'phone', sa.String(20), nullable=True,
        ))

    # phone 唯一索引
    if not _index_exists(conn, 'ix_users_phone'):
        op.create_index('ix_users_phone', 'users', ['phone'], unique=True)

    # phone_verified 列
    if not _column_exists(conn, 'users', 'phone_verified'):
        op.add_column('users', sa.Column(
            'phone_verified', sa.Boolean(),
            nullable=True, server_default=sa.text('0'),
        ))

    # phone_verified_at 列
    if not _column_exists(conn, 'users', 'phone_verified_at'):
        op.add_column('users', sa.Column(
            'phone_verified_at', sa.DateTime(), nullable=True,
        ))


def downgrade():
    conn = op.get_bind()

    if _column_exists(conn, 'users', 'phone_verified_at'):
        op.drop_column('users', 'phone_verified_at')

    if _column_exists(conn, 'users', 'phone_verified'):
        op.drop_column('users', 'phone_verified')

    if _index_exists(conn, 'ix_users_phone'):
        op.drop_index('ix_users_phone', table_name='users')

    if _column_exists(conn, 'users', 'phone'):
        op.drop_column('users', 'phone')
