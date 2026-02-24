from sqlalchemy import func

from app.core.extensions import db


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    is_locked = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    session_version = db.Column(db.Integer, default=0, server_default=db.text("0"))
    avatar = db.Column(db.Text)
    contact = db.Column(db.Text)
    college = db.Column(db.Text)
    last_active = db.Column(db.DateTime)
    is_subject_admin = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    is_notification_admin = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, server_default=func.now())
    email = db.Column(db.Text)
    email_verified = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    email_verified_at = db.Column(db.DateTime)
    has_password_set = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    openid = db.Column(db.Text)

    verification_codes = db.relationship(
        "EmailVerificationCode", back_populates="user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


class EmailVerificationCode(db.Model):
    __tablename__ = "email_verification_codes"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, nullable=False)
    code_type = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    is_used = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    used_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="verification_codes")

    def __repr__(self) -> str:
        return f"<EmailVerificationCode id={self.id} email={self.email!r} type={self.code_type!r}>"
