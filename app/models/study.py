# -*- coding: utf-8 -*-
"""学习与复习相关 ORM 模型。"""
from sqlalchemy import func

from app.core.extensions import db


class StudyLearning(db.Model):
    __tablename__ = "study_learning"
    __table_args__ = (
        db.UniqueConstraint("user_id", "source", "scope_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source = db.Column(db.Text, nullable=False)
    scope_id = db.Column(db.Integer, nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    streak = db.Column(db.Integer, default=0, server_default=db.text("0"))
    is_learned = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    correct_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    wrong_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    last_result = db.Column(db.Text)
    last_answered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<StudyLearning {self.id} user={self.user_id} q={self.question_id}>"


class StudyReview(db.Model):
    __tablename__ = "study_review"
    __table_args__ = (
        db.UniqueConstraint("user_id", "source", "scope_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source = db.Column(db.Text, nullable=False)
    scope_id = db.Column(db.Integer, nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    review_level = db.Column(db.Integer, default=0, server_default=db.text("0"))
    next_due_at = db.Column(db.DateTime)
    last_review_at = db.Column(db.DateTime)
    last_rating = db.Column(db.Text)
    lapse_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    is_mastered = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<StudyReview {self.id} user={self.user_id} q={self.question_id}>"
