from sqlalchemy import func

from app.core.extensions import db


class Popup(db.Model):
    __tablename__ = "popups"
    __table_args__ = (
        db.CheckConstraint(
            "popup_type IN ('info', 'warning', 'success', 'error')",
            name="ck_popups_popup_type",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    popup_type = db.Column(db.Text, nullable=False, default="info", server_default="info")
    is_active = db.Column(db.Boolean, default=True, server_default=db.text("1"))
    priority = db.Column(db.Integer, default=0, server_default=db.text("0"))
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())

    dismissals = db.relationship("PopupDismissal", backref="popup", lazy="dynamic")
    views = db.relationship("PopupView", backref="popup", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Popup {self.id} type={self.popup_type}>"


class PopupDismissal(db.Model):
    __tablename__ = "popup_dismissals"
    __table_args__ = (
        db.UniqueConstraint("user_id", "popup_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    popup_id = db.Column(
        db.Integer, db.ForeignKey("popups.id", ondelete="CASCADE"), nullable=False
    )
    dismissed_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PopupDismissal user={self.user_id} popup={self.popup_id}>"


class PopupView(db.Model):
    __tablename__ = "popup_views"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    popup_id = db.Column(
        db.Integer, db.ForeignKey("popups.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    viewed_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PopupView popup={self.popup_id} user={self.user_id}>"
