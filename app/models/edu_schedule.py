# -*- coding: utf-8 -*-
"""教务课表相关 ORM 模型。"""

from sqlalchemy import func

from app.core.extensions import db


class EduScheduleCredential(db.Model):
    __tablename__ = "edu_schedule_credentials"
    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_edu_schedule_credentials_user_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jwxt_username_ciphertext = db.Column(db.Text, nullable=False)
    jwxt_password_ciphertext = db.Column(db.Text, nullable=False)
    username_hint = db.Column(db.Text, nullable=False, server_default="")
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<EduScheduleCredential id={self.id} user={self.user_id}>"


class EduScheduleSnapshot(db.Model):
    __tablename__ = "edu_schedule_snapshots"
    __table_args__ = ({"extend_existing": True},)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    xnm = db.Column(db.String(4), nullable=False)
    xqm = db.Column(db.String(8), nullable=False)
    term_label = db.Column(db.Text, nullable=False, server_default="")
    jwxt_username_ciphertext = db.Column(db.Text, nullable=True)
    jwxt_password_ciphertext = db.Column(db.Text, nullable=True)
    payload_json = db.Column(db.Text, nullable=False)
    raw_payload_json = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<EduScheduleSnapshot id={self.id} user={self.user_id} term={self.xnm}-{self.xqm}>"


class EduGradeSnapshot(db.Model):
    __tablename__ = "edu_grade_snapshots"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "refresh_id",
            "xnm",
            "xqm",
            name="uq_edu_grade_snapshots_user_refresh_term",
        ),
        db.Index("ix_edu_grade_snapshots_user_refresh", "user_id", "refresh_id"),
        db.Index(
            "ix_edu_grade_snapshots_user_account_fetched",
            "user_id",
            "jwxt_account_key",
            "refresh_order",
            "fetched_at",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    xnm = db.Column(db.String(4), nullable=False)
    xqm = db.Column(db.String(8), nullable=False)
    refresh_id = db.Column(db.String(64), nullable=True)
    refresh_order = db.Column(
        db.BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    jwxt_account_key = db.Column(db.String(64), nullable=True)
    term_label = db.Column(db.Text, nullable=False, server_default="")
    jwxt_username_ciphertext = db.Column(db.Text, nullable=True)
    jwxt_password_ciphertext = db.Column(db.Text, nullable=True)
    payload_json = db.Column(db.Text, nullable=False)
    raw_payload_json = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<EduGradeSnapshot id={self.id} user={self.user_id} term={self.xnm}-{self.xqm}>"


class EduGradeOverviewSnapshot(db.Model):
    __tablename__ = "edu_grade_overview_snapshots"
    __table_args__ = (
        db.UniqueConstraint("user_id", "refresh_id", name="uq_edu_grade_overview_user_refresh"),
        db.CheckConstraint(
            "source IN ('official', 'calculated', 'unavailable')",
            name="ck_edu_grade_overview_source",
        ),
        db.CheckConstraint(
            "official_gpa IS NULL OR (official_gpa >= 0 AND official_gpa <= 5)",
            name="ck_edu_grade_overview_official_range",
        ),
        db.CheckConstraint(
            "calculated_gpa IS NULL OR (calculated_gpa >= 0 AND calculated_gpa <= 5)",
            name="ck_edu_grade_overview_calculated_range",
        ),
        db.CheckConstraint(
            "(source = 'official' AND official_gpa IS NOT NULL) "
            "OR (source = 'calculated' AND calculated_gpa IS NOT NULL) "
            "OR (source = 'unavailable' AND official_gpa IS NULL AND calculated_gpa IS NULL)",
            name="ck_edu_grade_overview_source_value",
        ),
        db.Index(
            "ix_edu_grade_overview_user_account_fetched",
            "user_id",
            "jwxt_account_key",
            "refresh_order",
            "fetched_at",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_id = db.Column(db.String(64), nullable=False)
    refresh_order = db.Column(
        db.BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    jwxt_account_key = db.Column(db.String(64), nullable=False)
    official_gpa = db.Column(db.Numeric(6, 2), nullable=True)
    calculated_gpa = db.Column(db.Numeric(6, 2), nullable=True)
    source = db.Column(db.String(16), nullable=False)
    fetched_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<EduGradeOverviewSnapshot id={self.id} user={self.user_id} source={self.source}>"
