# -*- coding: utf-8 -*-
"""add user_follows and interaction_notifications tables

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-02-26 18:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    # ── user_follows ──
    op.create_table(
        'user_follows',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('follower_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('following_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('follower_id', 'following_id', name='uq_user_follows_pair'),
        sa.CheckConstraint('follower_id != following_id', name='ck_user_follows_no_self'),
    )
    op.create_index('ix_user_follows_follower', 'user_follows', ['follower_id'])
    op.create_index('ix_user_follows_following', 'user_follows', ['following_id'])

    # ── interaction_notifications ──
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
    op.create_index('ix_interaction_notifications_user', 'interaction_notifications', ['user_id', 'is_read'])


def downgrade():
    op.drop_table('interaction_notifications')
    op.drop_table('user_follows')
