# -*- coding: utf-8 -*-
"""add forum phase2 tables

Revision ID: a1b2c3d4e5f6
Revises: f8a2c1d3e4b5
Create Date: 2026-02-26 04:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f8a2c1d3e4b5'
branch_labels = None
depends_on = None


def upgrade():
    # forum_posts 新增 poll 字段
    op.add_column('forum_posts', sa.Column('poll', sa.JSON(), nullable=True))

    # forum_reactions
    op.create_table('forum_reactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.String(10), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('emoji', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'target_type', 'target_id', 'emoji', name='uq_forum_reaction'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_forum_reactions_target', 'forum_reactions', ['target_type', 'target_id'])

    # forum_poll_votes
    op.create_table('forum_poll_votes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('option_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'user_id', 'option_index', name='uq_forum_poll_vote'),
        sa.ForeignKeyConstraint(['post_id'], ['forum_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_forum_poll_votes_post', 'forum_poll_votes', ['post_id'])

    # forum_reports
    op.create_table('forum_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.String(10), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('detail', sa.Text(), server_default='', nullable=True),
        sa.Column('status', sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('handled_by', sa.Integer(), nullable=True),
        sa.Column('handled_at', sa.DateTime(), nullable=True),
        sa.Column('handle_note', sa.Text(), server_default='', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['handled_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_forum_reports_status', 'forum_reports', ['status'])
    op.create_index('ix_forum_reports_target', 'forum_reports', ['target_type', 'target_id'])

    # forum_mentions
    op.create_table('forum_mentions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_type', sa.String(10), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('mentioned_user_id', sa.Integer(), nullable=False),
        sa.Column('mentioner_id', sa.Integer(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mentioner_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_forum_mentions_user', 'forum_mentions', ['mentioned_user_id', 'is_read'])
    op.create_index('ix_forum_mentions_source', 'forum_mentions', ['source_type', 'source_id'])

    # forum_user_bans
    op.create_table('forum_user_bans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('banned_by', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), server_default='', nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['banned_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_forum_user_bans_user', 'forum_user_bans', ['user_id', 'is_active'])


def downgrade():
    op.drop_table('forum_user_bans')
    op.drop_table('forum_mentions')
    op.drop_table('forum_reports')
    op.drop_table('forum_poll_votes')
    op.drop_table('forum_reactions')
    op.drop_column('forum_posts', 'poll')
