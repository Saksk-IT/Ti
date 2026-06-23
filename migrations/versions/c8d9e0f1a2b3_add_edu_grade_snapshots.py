# -*- coding: utf-8 -*-
"""add edu grade snapshots

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-06-24 06:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'c8d9e0f1a2b3'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'edu_grade_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('xnm', sa.String(length=4), nullable=False),
        sa.Column('xqm', sa.String(length=8), nullable=False),
        sa.Column('term_label', sa.Text(), nullable=False, server_default=''),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('raw_payload_json', sa.Text(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'xnm', 'xqm', name='uq_edu_grade_snapshots_user_term'),
    )
    op.create_index('ix_edu_grade_snapshots_user_fetched', 'edu_grade_snapshots', ['user_id', 'fetched_at'])


def downgrade():
    op.drop_index('ix_edu_grade_snapshots_user_fetched', table_name='edu_grade_snapshots')
    op.drop_table('edu_grade_snapshots')
