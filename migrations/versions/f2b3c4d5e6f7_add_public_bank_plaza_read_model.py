# -*- coding: utf-8 -*-
"""add public bank plaza read model

Revision ID: f2b3c4d5e6f7
Revises: d4e5f6a7b8c9
Create Date: 2026-03-06 22:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'f2b3c4d5e6f7'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'plaza_boards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.UniqueConstraint('slug'),
    )

    op.add_column('subjects', sa.Column('plaza_board_id', sa.Integer(), nullable=True))
    op.add_column('subjects', sa.Column('is_plaza_featured', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('subjects', sa.Column('plaza_featured_weight', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('subjects', sa.Column('plaza_featured_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_subjects_plaza_board_id', 'subjects', 'plaza_boards', ['plaza_board_id'], ['id'], ondelete='SET NULL')

    op.add_column('user_question_banks', sa.Column('plaza_board_id', sa.Integer(), nullable=True))
    op.add_column('user_question_banks', sa.Column('is_plaza_featured', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('user_question_banks', sa.Column('plaza_featured_weight', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('user_question_banks', sa.Column('plaza_featured_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_user_question_banks_plaza_board_id', 'user_question_banks', 'plaza_boards', ['plaza_board_id'], ['id'], ondelete='SET NULL')

    op.create_table(
        'public_bank_plaza_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_image', sa.Text(), nullable=True),
        sa.Column('owner_label', sa.Text(), nullable=True),
        sa.Column('question_count_total', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('plaza_board_id', sa.Integer(), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('featured_weight', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('join_count_total', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('join_users_7d', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('join_users_30d', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('answer_count_7d', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('answer_count_30d', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('answer_users_7d', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('answer_users_30d', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('hot_score', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('active_score', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('recommended_score', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['plaza_board_id'], ['plaza_boards.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('source_type', 'source_id'),
    )
    op.create_index('ix_public_bank_plaza_metrics_tab_hot', 'public_bank_plaza_metrics', ['hot_score'])
    op.create_index('ix_public_bank_plaza_metrics_tab_active', 'public_bank_plaza_metrics', ['active_score'])
    op.create_index('ix_public_bank_plaza_metrics_tab_featured', 'public_bank_plaza_metrics', ['is_featured', 'featured_weight'])

    op.execute(
        """
        INSERT INTO plaza_boards (slug, name, description, sort_order, is_active)
        VALUES ('community-shared', '共建题库', '面向用户公开与加入流转的共建题库板块。', 10, true)
        """
    )
    op.execute(
        """
        INSERT INTO plaza_boards (slug, name, description, sort_order, is_active)
        SELECT 'subject-' || id, name, COALESCE(description, ''), 100 + id, true
        FROM subjects
        """
    )
    op.execute(
        """
        UPDATE subjects s
        SET plaza_board_id = pb.id
        FROM plaza_boards pb
        WHERE pb.slug = 'subject-' || s.id
        """
    )
    op.execute(
        """
        UPDATE user_question_banks
        SET plaza_board_id = (SELECT id FROM plaza_boards WHERE slug = 'community-shared' LIMIT 1)
        WHERE is_public = true AND status = 1 AND plaza_board_id IS NULL
        """
    )


def downgrade():
    op.drop_index('ix_public_bank_plaza_metrics_tab_featured', table_name='public_bank_plaza_metrics')
    op.drop_index('ix_public_bank_plaza_metrics_tab_active', table_name='public_bank_plaza_metrics')
    op.drop_index('ix_public_bank_plaza_metrics_tab_hot', table_name='public_bank_plaza_metrics')
    op.drop_table('public_bank_plaza_metrics')

    op.drop_constraint('fk_user_question_banks_plaza_board_id', 'user_question_banks', type_='foreignkey')
    op.drop_column('user_question_banks', 'plaza_featured_at')
    op.drop_column('user_question_banks', 'plaza_featured_weight')
    op.drop_column('user_question_banks', 'is_plaza_featured')
    op.drop_column('user_question_banks', 'plaza_board_id')

    op.drop_constraint('fk_subjects_plaza_board_id', 'subjects', type_='foreignkey')
    op.drop_column('subjects', 'plaza_featured_at')
    op.drop_column('subjects', 'plaza_featured_weight')
    op.drop_column('subjects', 'is_plaza_featured')
    op.drop_column('subjects', 'plaza_board_id')

    op.drop_table('plaza_boards')
