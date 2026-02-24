from sqlalchemy import func

from app.core.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    n_type = db.Column(db.Text, nullable=False, default="info", server_default="info")
    priority = db.Column(db.Integer, default=0, server_default=db.text("0"))
    is_active = db.Column(db.Boolean, default=True, server_default=db.text("1"))
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())

    dismissals = db.relationship("NotificationDismissal", backref="notification", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Notification {self.id} type={self.n_type}>"


class NotificationDismissal(db.Model):
    __tablename__ = "notification_dismissals"
    __table_args__ = (
        db.UniqueConstraint("user_id", "notification_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_id = db.Column(
        db.Integer,
        db.ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    dismissed_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<NotificationDismissal user={self.user_id} notif={self.notification_id}>"
