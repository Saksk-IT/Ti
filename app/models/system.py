# -*- coding: utf-8 -*-
"""系统配置与辅助表 ORM 模型。"""
from sqlalchemy import func

from app.core.extensions import db


class SystemConfig(db.Model):
    __tablename__ = "system_config"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    config_key = db.Column(db.Text, unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    def __repr__(self) -> str:
        return f"<SystemConfig {self.id} key={self.config_key!r}>"


class UserSubject(db.Model):
    __tablename__ = "user_subjects"
    __table_args__ = (
        db.UniqueConstraint("user_id", "subject_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    restricted_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    restricted_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    def __repr__(self) -> str:
        return f"<UserSubject {self.id} user={self.user_id} subject={self.subject_id}>"


class UserQuestionTagItem(db.Model):
    __tablename__ = "user_question_tag_items"
    __table_args__ = (
        db.PrimaryKeyConstraint("user_id", "scope", "scope_id", "question_id", "tag"),
        {"extend_existing": True},
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scope = db.Column(db.Text, nullable=False)
    scope_id = db.Column(db.Integer, nullable=False, server_default=db.text("0"))
    question_id = db.Column(db.Integer, nullable=False)
    tag = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserQuestionTagItem user={self.user_id} q={self.question_id} tag={self.tag!r}>"

class DuplicateCheckRecord(db.Model):
    __tablename__ = "duplicate_check_records"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    total_pairs = db.Column(db.Integer, default=0, server_default=db.text("0"))
    duplicates_json = db.Column(db.Text, nullable=False)
    similarity_threshold = db.Column(db.Float, default=0.8, server_default=db.text("0.8"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<DuplicateCheckRecord {self.id} subject={self.subject_id}>"


class ReinforceSimilarCache(db.Model):
    __tablename__ = "reinforce_similar_cache"
    __table_args__ = (
        db.UniqueConstraint("source", "scope_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source = db.Column(db.Text, nullable=False)
    scope_id = db.Column(db.Integer, nullable=False)
    version = db.Column(db.Text, nullable=False)
    pairs_json = db.Column(db.Text, nullable=False)
    pairs_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    computed_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ReinforceSimilarCache {self.id} source={self.source} scope={self.scope_id}>"


class SchemaMigration(db.Model):
    __tablename__ = "schema_migrations"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Text, primary_key=True)
    applied_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SchemaMigration {self.id}>"
