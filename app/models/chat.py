from sqlalchemy import func

from app.core.extensions import db


class ChatConversation(db.Model):
    __tablename__ = "chat_conversations"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    c_type = db.Column(db.Text, nullable=False, default="direct", server_default="direct")
    title = db.Column(db.Text)
    direct_pair_key = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())

    members = db.relationship("ChatMember", backref="conversation", lazy="dynamic")
    messages = db.relationship("ChatMessage", backref="conversation", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<ChatConversation {self.id} type={self.c_type}>"


class ChatMember(db.Model):
    __tablename__ = "chat_members"
    __table_args__ = (
        db.UniqueConstraint("conversation_id", "user_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = db.Column(db.Text, default="member", server_default="member")
    last_read_message_id = db.Column(db.Integer, default=0, server_default=db.text("0"))
    joined_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ChatMember conv={self.conversation_id} user={self.user_id}>"


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.Text, default="text", server_default="text")
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ChatMessage {self.id} conv={self.conversation_id}>"


class UserRemark(db.Model):
    __tablename__ = "user_remarks"
    __table_args__ = (
        db.UniqueConstraint("owner_user_id", "target_user_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    remark = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<UserRemark owner={self.owner_user_id} target={self.target_user_id}>"
