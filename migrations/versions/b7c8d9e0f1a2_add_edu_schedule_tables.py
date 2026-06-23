# -*- coding: utf-8 -*-
"""add edu schedule tables

Revision ID: b7c8d9e0f1a2
Revises: a7b8c9d0e1f2
Create Date: 2026-06-24 06:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'b7c8d9e0f1a2'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'edu_schedule_credentials',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('jwxt_username_ciphertext', sa.Text(), nullable=False),
        sa.Column('jwxt_password_ciphertext', sa.Text(), nullable=False),
        sa.Column('username_hint', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_edu_schedule_credentials_user_id'),
    )

    op.create_table(
        'edu_schedule_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('xnm', sa.String(length=4), nullable=False),
        sa.Column('xqm', sa.String(length=8), nullable=False),
        sa.Column('term_label', sa.Text(), nullable=False, server_default=''),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('raw_payload_json', sa.Text(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'xnm', 'xqm', name='uq_edu_schedule_snapshots_user_term'),
    )
    op.create_index('ix_edu_schedule_snapshots_user_fetched', 'edu_schedule_snapshots', ['user_id', 'fetched_at'])


def downgrade():
    op.drop_index('ix_edu_schedule_snapshots_user_fetched', table_name='edu_schedule_snapshots')
    op.drop_table('edu_schedule_snapshots')
    op.drop_table('edu_schedule_credentials')
