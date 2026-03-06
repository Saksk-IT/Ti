# -*- coding: utf-8 -*-
"""题库广场读模型。"""

from sqlalchemy import func

from app.core.extensions import db


class PlazaBoard(db.Model):
    __tablename__ = 'plaza_boards'
    __table_args__ = (
        db.UniqueConstraint('slug'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0, server_default=db.text('0'))
    is_active = db.Column(db.Boolean, default=True, server_default=db.text('true'))
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f'<PlazaBoard {self.id} {self.slug!r}>'


class PublicBankPlazaMetric(db.Model):
    __tablename__ = 'public_bank_plaza_metrics'
    __table_args__ = (
        db.UniqueConstraint('source_type', 'source_id'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_type = db.Column(db.Text, nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    cover_image = db.Column(db.Text)
    owner_label = db.Column(db.Text)
    question_count_total = db.Column(db.Integer, default=0, server_default=db.text('0'))
    plaza_board_id = db.Column(db.Integer, db.ForeignKey('plaza_boards.id', ondelete='SET NULL'))
    is_featured = db.Column(db.Boolean, default=False, server_default=db.text('false'))
    featured_weight = db.Column(db.Integer, default=0, server_default=db.text('0'))
    published_at = db.Column(db.DateTime)
    last_activity_at = db.Column(db.DateTime)
    join_count_total = db.Column(db.Integer, default=0, server_default=db.text('0'))
    join_users_7d = db.Column(db.Integer, default=0, server_default=db.text('0'))
    join_users_30d = db.Column(db.Integer, default=0, server_default=db.text('0'))
    answer_count_7d = db.Column(db.Integer, default=0, server_default=db.text('0'))
    answer_count_30d = db.Column(db.Integer, default=0, server_default=db.text('0'))
    answer_users_7d = db.Column(db.Integer, default=0, server_default=db.text('0'))
    answer_users_30d = db.Column(db.Integer, default=0, server_default=db.text('0'))
    hot_score = db.Column(db.Float, default=0, server_default=db.text('0'))
    active_score = db.Column(db.Float, default=0, server_default=db.text('0'))
    recommended_score = db.Column(db.Float, default=0, server_default=db.text('0'))
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f'<PublicBankPlazaMetric {self.source_type}:{self.source_id}>'
