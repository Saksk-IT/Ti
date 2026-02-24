from app.core.extensions import db
from sqlalchemy import func


class Exam(db.Model):
    __tablename__ = "exams"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, nullable=False)
    config_json = db.Column(db.Text)
    total_score = db.Column(db.Float, default=0, server_default=db.text("0"))
    status = db.Column(db.Text, default="ongoing", server_default=db.text("'ongoing'"))
    started_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    submitted_at = db.Column(db.DateTime)

    questions = db.relationship("ExamQuestion", backref="exam", lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Exam {self.id} user={self.user_id} status={self.status}>"


class ExamQuestion(db.Model):
    __tablename__ = "exam_questions"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(
        db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    question_id = db.Column(db.Integer, nullable=False)
    order_index = db.Column(db.Integer, nullable=False)
    score_val = db.Column(db.Float, default=1, server_default=db.text("1"))
    user_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean, nullable=True)
    answered_at = db.Column(db.DateTime)

    def __repr__(self) -> str:
        return f"<ExamQuestion {self.id} exam={self.exam_id} q={self.question_id}>"


class ExamTemplate(db.Model):
    __tablename__ = "exam_templates"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.Text, nullable=False)
    config_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ExamTemplate {self.id} title={self.title}>"
