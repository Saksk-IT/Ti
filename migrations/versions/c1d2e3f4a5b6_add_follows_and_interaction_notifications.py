# -*- coding: utf-8 -*-
"""add user_follows and interaction_notifications tables

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-02-26 18:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
    ), {'t': name}).fetchone()
    return result is not None


def _index_safe(name: str, table: str, columns: list[str]):
    try:
        op.create_index(name, table, columns)
    except (OperationalError, ProgrammingError):
        pass


def _constraint_safe(table: str, constraint_sql: str):
    """尝试添加约束，已存在则跳过"""
    try:
        op.get_bind().execute(text(constraint_sql))
    except (OperationalError, ProgrammingError):
        pass


def upgrade():
    # ── user_follows ──
    if not _table_exists('user_follows'):
        op.create_table(
            'user_follows',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('follower_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('following_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
            sa.UniqueConstraint('follower_id', 'following_id', name='uq_user_follows_pair'),
            sa.CheckConstraint('follower_id != following_id', name='ck_user_follows_no_self'),
        )
    else:
        # 表已存在，确保约束存在
        _constraint_safe('user_follows',
            "ALTER TABLE user_follows ADD CONSTRAINT uq_user_follows_pair UNIQUE (follower_id, following_id)")
        _constraint_safe('user_follows',
            "ALTER TABLE user_follows ADD CONSTRAINT ck_user_follows_no_self CHECK (follower_id != following_id)")
    _index_safe('ix_user_follows_follower', 'user_follows', ['follower_id'])
    _index_safe('ix_user_follows_following', 'user_follows', ['following_id'])

    # ── interaction_notifications ──
    if not _table_exists('interaction_notifications'):
        op.create_table(
            'interaction_notifications',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('action_type', sa.String(20), nullable=False),
            sa.Column('target_type', sa.String(20), nullable=True),
            sa.Column('target_id', sa.Integer(), nullable=True),
            sa.Column('post_id', sa.Integer(), nullable=True),
            sa.Column('content_preview', sa.String(200), server_default=''),
            sa.Column('is_read', sa.Boolean(), server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
            sa.UniqueConstraint(
                'user_id', 'actor_id', 'action_type', 'target_type', 'target_id',
                name='uq_interaction_notifications_dedup',
            ),
        )
    else:
        _constraint_safe('interaction_notifications',
            "ALTER TABLE interaction_notifications ADD CONSTRAINT uq_interaction_notifications_dedup "
            "UNIQUE (user_id, actor_id, action_type, target_type, target_id)")
    _index_safe('ix_interaction_notifications_user', 'interaction_notifications', ['user_id', 'is_read'])


def downgrade():
    op.drop_table('interaction_notifications')
    op.drop_table('user_follows')
