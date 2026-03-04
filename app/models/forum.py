# -*- coding: utf-8 -*-
"""论坛模块 ORM 模型"""
from sqlalchemy import func, text
from app.core.extensions import db


class ForumBoard(db.Model):
    """版块"""
    __tablename__ = 'forum_boards'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    board_type = db.Column(db.String(20), nullable=False, default='custom')  # 'subject' | 'custom'
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True)
    icon = db.Column(db.String(50), default='')
    sort_order = db.Column(db.Integer, default=0, server_default=text('0'))
    is_active = db.Column(db.Boolean, default=True, server_default=text('true'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    posts = db.relationship('ForumPost', back_populates='board', lazy='dynamic')


class ForumPost(db.Model):
    """帖子"""
    __tablename__ = 'forum_posts'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    board_id = db.Column(db.Integer, db.ForeignKey('forum_boards.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False, default='')
    content_format = db.Column(db.String(10), default='html')
    markdown_source = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, default=list)
    summary = db.Column(db.Text, nullable=True)
    images = db.Column(db.JSON, default=list)
    question_refs = db.Column(db.JSON, default=list)
    poll = db.Column(db.JSON, nullable=True)  # {"question":"...", "options":["A","B"], "multiple": false}

    is_pinned = db.Column(db.Boolean, default=False, server_default=text('false'))
    is_featured = db.Column(db.Boolean, default=False, server_default=text('false'))
    is_locked = db.Column(db.Boolean, default=False, server_default=text('false'))
    is_hidden = db.Column(db.Boolean, default=False, server_default=text('false'))
    is_deleted = db.Column(db.Boolean, default=False, server_default=text('false'))
    deleted_by = db.Column(db.Integer, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    comment_count = db.Column(db.Integer, default=0, server_default=text('0'))
    like_count = db.Column(db.Integer, default=0, server_default=text('0'))
    favorite_count = db.Column(db.Integer, default=0, server_default=text('0'))
    view_count = db.Column(db.Integer, default=0, server_default=text('0'))

    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())
    last_comment_at = db.Column(db.DateTime, nullable=True)

    board = db.relationship('ForumBoard', back_populates='posts')
    comments = db.relationship('ForumComment', back_populates='post', lazy='dynamic')


class ForumComment(db.Model):
    """评论（支持楼中楼）"""
    __tablename__ = 'forum_comments'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_comments.id', ondelete='CASCADE'), nullable=True)
    reply_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    content = db.Column(db.Text, nullable=False)

    is_deleted = db.Column(db.Boolean, default=False, server_default=text('false'))
    deleted_by = db.Column(db.Integer, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    like_count = db.Column(db.Integer, default=0, server_default=text('0'))
    reply_count = db.Column(db.Integer, default=0, server_default=text('0'))

    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    post = db.relationship('ForumPost', back_populates='comments')
    replies = db.relationship('ForumComment', backref=db.backref('parent', remote_side='ForumComment.id'), lazy='dynamic')


class ForumLike(db.Model):
    """点赞"""
    __tablename__ = 'forum_likes'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_forum_like'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(10), nullable=False)  # 'post' | 'comment'
    target_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())


class ForumFavorite(db.Model):
    """收藏"""
    __tablename__ = 'forum_favorites'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='uq_forum_favorite'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())


class ForumReaction(db.Model):
    """表情回应"""
    __tablename__ = 'forum_reactions'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'target_type', 'target_id', 'emoji', name='uq_forum_reaction'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(10), nullable=False)  # 'post' | 'comment'
    target_id = db.Column(db.Integer, nullable=False)
    emoji = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())


class ForumPollVote(db.Model):
    """投票"""
    __tablename__ = 'forum_poll_votes'
    __table_args__ = (
        db.UniqueConstraint('post_id', 'user_id', 'option_index', name='uq_forum_poll_vote'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    option_index = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())


class ForumReport(db.Model):
    """举报"""
    __tablename__ = 'forum_reports'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(10), nullable=False)  # 'post' | 'comment'
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(50), nullable=False)
    detail = db.Column(db.Text, default='')
    status = db.Column(db.String(20), nullable=False, default='pending', server_default=text("'pending'"))
    handled_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    handled_at = db.Column(db.DateTime, nullable=True)
    handle_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())


class ForumMention(db.Model):
    """@提及"""
    __tablename__ = 'forum_mentions'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_type = db.Column(db.String(10), nullable=False)  # 'post' | 'comment'
    source_id = db.Column(db.Integer, nullable=False)
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    mentioner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_read = db.Column(db.Boolean, default=False, server_default=text('false'))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())


class ForumUserBan(db.Model):
    """用户封禁"""
    __tablename__ = 'forum_user_bans'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    banned_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reason = db.Column(db.Text, nullable=False, default='')
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, server_default=text('true'))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
