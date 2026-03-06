# -*- coding: utf-8 -*-
"""用户题库相关 ORM 模型。"""
from sqlalchemy import func

from app.core.extensions import db


class UserBankCategory(db.Model):
    __tablename__ = "user_bank_categories"
    __table_args__ = (
        db.UniqueConstraint("user_id", "name"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserBankCategory {self.id} user={self.user_id} name={self.name!r}>"


class UserQuestionBank(db.Model):
    __tablename__ = "user_question_banks"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("user_bank_categories.id", ondelete="SET NULL"))
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    cover_image = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    public_description = db.Column(db.Text)
    allow_copy = db.Column(db.Boolean, default=True, server_default=db.text("1"))
    public_at = db.Column(db.DateTime)
    question_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    share_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    public_use_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    status = db.Column(db.Integer, default=1, server_default=db.text("1"))
    plaza_board_id = db.Column(db.Integer, db.ForeignKey("plaza_boards.id", ondelete="SET NULL"))
    is_plaza_featured = db.Column(db.Boolean, default=False, server_default=db.text("false"))
    plaza_featured_weight = db.Column(db.Integer, default=0, server_default=db.text("0"))
    plaza_featured_at = db.Column(db.DateTime)
    join_mode = db.Column(db.Text, default='free', server_default=db.text("'free'"))
    join_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserQuestionBank {self.id} name={self.name!r}>"

class UserBankQuestion(db.Model):
    __tablename__ = "user_bank_questions"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, default="[]", server_default=db.text("'[]'"))
    answer = db.Column(db.Text, default="[]", server_default=db.text("'[]'"))
    analysis = db.Column(db.Text)
    tags = db.Column(db.Text, default="[]", server_default=db.text("'[]'"))
    difficulty = db.Column(db.Integer, default=1, server_default=db.text("1"))
    image_path = db.Column(db.Text)
    source_type = db.Column(db.Text, default="custom", server_default=db.text("'custom'"))
    source_question_id = db.Column(db.Integer)
    sort_order = db.Column(db.Integer, default=0, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserBankQuestion {self.id} bank={self.bank_id}>"


class BankShare(db.Model):
    __tablename__ = "bank_shares"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    share_code = db.Column(db.Text, unique=True)
    share_token = db.Column(db.Text, unique=True)
    permission = db.Column(db.Text, default="read", server_default=db.text("'read'"))
    expires_at = db.Column(db.DateTime)
    max_uses = db.Column(db.Integer)
    current_uses = db.Column(db.Integer, default=0, server_default=db.text("0"))
    is_active = db.Column(db.Boolean, default=True, server_default=db.text("1"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<BankShare {self.id} bank={self.bank_id}>"


class BankShareRecord(db.Model):
    __tablename__ = "bank_share_records"
    __table_args__ = (
        db.UniqueConstraint("share_id", "user_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    share_id = db.Column(db.Integer, db.ForeignKey("bank_shares.id", ondelete="CASCADE"), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.Integer, default=1, server_default=db.text("1"))
    last_access_at = db.Column(db.DateTime)
    access_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<BankShareRecord {self.id} share={self.share_id} user={self.user_id}>"

class UserBankAnswer(db.Model):
    __tablename__ = "user_bank_answers"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("user_bank_questions.id", ondelete="CASCADE"), nullable=False)
    user_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<UserBankAnswer {self.id} user={self.user_id} q={self.question_id}>"


class UserBankMistake(db.Model):
    __tablename__ = "user_bank_mistakes"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("user_bank_questions.id", ondelete="CASCADE"), nullable=False)
    wrong_count = db.Column(db.Integer, default=1, server_default=db.text("1"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserBankMistake {self.id} user={self.user_id} q={self.question_id}>"


class PublicBankUser(db.Model):
    __tablename__ = "public_bank_users"
    __table_args__ = (
        db.UniqueConstraint("bank_id", "user_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_access_at = db.Column(db.DateTime)
    access_count = db.Column(db.Integer, default=0, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PublicBankUser {self.id} bank={self.bank_id} user={self.user_id}>"


class UserBankFavorite(db.Model):
    __tablename__ = "user_bank_favorites"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey("user_question_banks.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("user_bank_questions.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<UserBankFavorite {self.id} user={self.user_id} q={self.question_id}>"
