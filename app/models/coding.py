from app.core.extensions import db
from sqlalchemy import func


class CodingSubject(db.Model):
    __tablename__ = "coding_subjects"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    is_locked = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    questions = db.relationship("CodingQuestion", backref="subject", lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CodingSubject {self.id} name={self.name}>"


class CodingQuestion(db.Model):
    __tablename__ = "coding_questions"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coding_subject_id = db.Column(
        db.Integer, db.ForeignKey("coding_subjects.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.Text, nullable=False)
    q_type = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Text, nullable=False)
    code_template = db.Column(db.Text)
    programming_language = db.Column(db.Text, default="python", server_default=db.text("'python'"))
    time_limit = db.Column(db.Integer, default=5, server_default=db.text("5"))
    memory_limit = db.Column(db.Integer, default=128, server_default=db.text("128"))
    test_cases_json = db.Column(db.Text, nullable=False)
    examples = db.Column(db.Text)
    constraints = db.Column(db.Text)
    hints = db.Column(db.Text)
    is_enabled = db.Column(db.Boolean, default=True, server_default=db.text("1"))
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CodingQuestion {self.id} title={self.title}>"


class CodeSubmission(db.Model):
    __tablename__ = "code_submissions"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("coding_questions.id", ondelete="CASCADE"), nullable=False
    )
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)
    passed_cases = db.Column(db.Integer, default=0, server_default=db.text("0"))
    total_cases = db.Column(db.Integer, default=0, server_default=db.text("0"))
    execution_time = db.Column(db.Float)
    error_message = db.Column(db.Text)
    score = db.Column(db.Float, default=0.0, server_default=db.text("0.0"))
    submitted_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CodeSubmission {self.id} user={self.user_id} status={self.status}>"


class CodingStatistics(db.Model):
    __tablename__ = "coding_statistics"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("coding_questions.id", ondelete="CASCADE"), nullable=False
    )
    total_submissions = db.Column(db.Integer, default=0, server_default=db.text("0"))
    accepted_submissions = db.Column(db.Integer, default=0, server_default=db.text("0"))
    best_time = db.Column(db.Float)
    best_score = db.Column(db.Float, default=0.0, server_default=db.text("0.0"))
    first_accepted_at = db.Column(db.DateTime)
    last_submitted_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CodingStatistics {self.id} user={self.user_id} q={self.question_id}>"


class UserCodingStats(db.Model):
    __tablename__ = "user_coding_stats"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_submissions = db.Column(db.Integer, default=0, server_default=db.text("0"))
    accepted_submissions = db.Column(db.Integer, default=0, server_default=db.text("0"))
    solved_questions = db.Column(db.Integer, default=0, server_default=db.text("0"))
    total_score = db.Column(db.Float, default=0.0, server_default=db.text("0.0"))
    average_score = db.Column(db.Float, default=0.0, server_default=db.text("0.0"))
    acceptance_rate = db.Column(db.Float, default=0.0, server_default=db.text("0.0"))
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<UserCodingStats {self.id} user={self.user_id}>"


class CodeDraft(db.Model):
    __tablename__ = "code_drafts"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("coding_questions.id", ondelete="CASCADE"), nullable=False
    )
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.Text, default="python", server_default=db.text("'python'"))
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CodeDraft {self.id} user={self.user_id} q={self.question_id}>"
