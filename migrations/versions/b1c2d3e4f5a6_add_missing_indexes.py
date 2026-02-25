# -*- coding: utf-8 -*-
"""add missing indexes

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26 00:00:00.000000
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

_INDEXES = [
    ('ix_questions_subject_id', 'questions', ['subject_id']),
    ('ix_user_answers_user_question', 'user_answers', ['user_id', 'question_id']),
    ('ix_user_answers_user_created', 'user_answers', ['user_id', 'created_at']),
    ('ix_favorites_user_question', 'favorites', ['user_id', 'question_id']),
    ('ix_mistakes_user_question', 'mistakes', ['user_id', 'question_id']),
    ('ix_study_review_user_due', 'study_review', ['user_id', 'next_due_at']),
    ('ix_chat_messages_conv_created', 'chat_messages', ['conversation_id', 'created_at']),
    ('ix_exam_questions_exam_id', 'exam_questions', ['exam_id']),
    ('ix_user_bank_questions_bank_id', 'user_bank_questions', ['bank_id']),
    ('ix_user_progress_user_id', 'user_progress', ['user_id']),
    ('ix_user_bank_answers_user_bank', 'user_bank_answers', ['user_id', 'bank_id']),
    ('ix_user_bank_favorites_user_bank', 'user_bank_favorites', ['user_id', 'bank_id']),
    ('ix_user_bank_mistakes_user_bank', 'user_bank_mistakes', ['user_id', 'bank_id']),
    ('ix_user_subjects_user_id', 'user_subjects', ['user_id']),
    ('ix_code_submissions_user_question', 'code_submissions', ['user_id', 'question_id']),
]


def upgrade():
    for name, table, columns in _INDEXES:
        try:
            op.create_index(name, table, columns)
        except Exception:
            pass


def downgrade():
    for name, table, _columns in reversed(_INDEXES):
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass
