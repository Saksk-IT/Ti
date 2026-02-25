"""add forum tables

Revision ID: f8a2c1d3e4b5
Revises: 3a7dbef5d592
Create Date: 2026-02-26 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f8a2c1d3e4b5'
down_revision = '3a7dbef5d592'
branch_labels = None
depends_on = None


def upgrade():
    # forum_boards
    op.create_table('forum_boards',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=True),
        sa.Column('board_type', sa.String(20), server_default='custom', nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=True),
        sa.Column('icon', sa.String(50), server_default='', nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_forum_boards_sort', 'forum_boards', ['sort_order'])
    op.create_index('ix_forum_boards_subject', 'forum_boards', ['subject_id'],
                     unique=True, postgresql_where=sa.text('subject_id IS NOT NULL'))

    # forum_posts
    op.create_table('forum_posts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('board_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), server_default='', nullable=False),
        sa.Column('content_format', sa.String(10), server_default='html', nullable=True),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('question_refs', sa.JSON(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('is_featured', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('is_locked', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('comment_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('like_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('favorite_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('view_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_comment_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['board_id'], ['forum_boards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_forum_posts_board_created', 'forum_posts', ['board_id', 'is_deleted', 'created_at'])
    op.create_index('ix_forum_posts_author', 'forum_posts', ['author_id', 'is_deleted'])
    op.create_index('ix_forum_posts_pinned', 'forum_posts', ['board_id', 'is_pinned', 'last_comment_at'])

    # forum_comments
    op.create_table('forum_comments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('reply_to_user_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('like_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('reply_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['post_id'], ['forum_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['forum_comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reply_to_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_forum_comments_post', 'forum_comments', ['post_id', 'is_deleted', 'created_at'])
    op.create_index('ix_forum_comments_parent', 'forum_comments', ['parent_id'])
    op.create_index('ix_forum_comments_author', 'forum_comments', ['author_id'])

    # forum_likes
    op.create_table('forum_likes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.String(10), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_forum_like'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # forum_favorites
    op.create_table('forum_favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', name='uq_forum_favorite'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['forum_posts.id'], ondelete='CASCADE'),
    )


def downgrade():
    op.drop_table('forum_favorites')
    op.drop_table('forum_likes')
    op.drop_table('forum_comments')
    op.drop_table('forum_posts')
    op.drop_table('forum_boards')
