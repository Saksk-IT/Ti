# -*- coding: utf-8 -*-
"""关注系统 + 互动通知 ORM 模型"""
from app.core.extensions import db


class UserFollow(db.Model):
    __tablename__ = 'user_follows'

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('follower_id', 'following_id', name='uq_user_follows'),
        db.CheckConstraint('follower_id != following_id', name='ck_no_self_follow'),
    )


class InteractionNotification(db.Model):
    __tablename__ = 'interaction_notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)
    target_type = db.Column(db.String(20))
    target_id = db.Column(db.Integer)
    post_id = db.Column(db.Integer)
    content_preview = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
