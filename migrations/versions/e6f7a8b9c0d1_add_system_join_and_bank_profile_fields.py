# -*- coding: utf-8 -*-
"""add system join and bank profile fields

Revision ID: e6f7a8b9c0d1
Revises: f2b3c4d5e6f7
Create Date: 2026-03-07 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'e6f7a8b9c0d1'
down_revision = 'f2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_question_banks', sa.Column('join_mode', sa.Text(), nullable=False, server_default=sa.text("'free'")))
    op.add_column('user_question_banks', sa.Column('join_note', sa.Text(), nullable=True))

    op.create_table(
        'public_subject_users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('last_access_at', sa.DateTime(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('subject_id', 'user_id'),
    )
    op.create_index('ix_public_subject_users_subject_user', 'public_subject_users', ['subject_id', 'user_id'])


def downgrade():
    op.drop_index('ix_public_subject_users_subject_user', table_name='public_subject_users')
    op.drop_table('public_subject_users')
    op.drop_column('user_question_banks', 'join_note')
    op.drop_column('user_question_banks', 'join_mode')
