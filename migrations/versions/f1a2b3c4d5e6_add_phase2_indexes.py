# -*- coding: utf-8 -*-
"""add phase2 indexes for high-concurrency optimization

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-02-28 20:00:00.000000
"""
from alembic import op
from sqlalchemy.exc import OperationalError, ProgrammingError

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None

_INDEXES = [
    # questions: 复合筛选覆盖 get_list()
    ('ix_questions_subject_type', 'questions', ['subject_id', 'type']),
    # email_verification_codes: 验证码查询热路径
    ('ix_email_codes_email_type_used', 'email_verification_codes', ['email', 'code_type', 'is_used']),
    # forum_posts: 帖子列表排序
    ('ix_forum_posts_board_deleted_created', 'forum_posts', ['board_id', 'is_deleted', 'created_at']),
    # forum_comments: 评论列表
    ('ix_forum_comments_post_deleted', 'forum_comments', ['post_id', 'is_deleted']),
    # notifications: 活跃通知查询
    ('ix_notifications_is_active', 'notifications', ['is_active']),
    # users: 微信登录查询
    ('ix_users_openid', 'users', ['openid']),
    # users: 邮箱登录查询
    ('ix_users_email', 'users', ['email']),
]


def upgrade():
    for name, table, columns in _INDEXES:
        try:
            op.create_index(name, table, columns)
        except (OperationalError, ProgrammingError):
            pass  # 索引可能已存在


def downgrade():
    for name, table, _columns in reversed(_INDEXES):
        try:
            op.drop_index(name, table_name=table)
        except (OperationalError, ProgrammingError):
            pass  # 索引可能不存在
