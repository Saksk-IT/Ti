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
        return f"<EduGradeSnapshot id={self.id} user={self.user_id} term={self.xnm}-{self.xqm}>"
