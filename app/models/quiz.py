from app.core.extensions import db
from sqlalchemy import func


class Favorite(db.Model):
    __tablename__ = 'favorites'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f'<Favorite user={self.user_id} question={self.question_id}>'


class Mistake(db.Model):
    __tablename__ = 'mistakes'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    wrong_count = db.Column(db.Integer, default=1, server_default=db.text('1'))
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())
    last_updated = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f'<Mistake user={self.user_id} question={self.question_id} wrong={self.wrong_count}>'


class UserAnswer(db.Model):
    __tablename__ = 'user_answers'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    user_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f'<UserAnswer user={self.user_id} question={self.question_id}>'


class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'p_key'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    p_key = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.TIMESTAMP, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())
    created_at = db.Column(db.TIMESTAMP, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f'<UserProgress user={self.user_id} key={self.p_key!r}>'


class UserCheckin(db.Model):
    __tablename__ = 'user_checkins'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'checkin_date'),
        {'extend_existing': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    checkin_date = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    def __repr__(self) -> str:
        return f'<UserCheckin user={self.user_id} date={self.checkin_date}>'


class UserQuizStats(db.Model):
    __tablename__ = 'user_quiz_stats'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    total_answered = db.Column(db.Integer, default=0, server_default=db.text('0'))
    last_reset_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f'<UserQuizStats user={self.user_id} answered={self.total_answered}>'
