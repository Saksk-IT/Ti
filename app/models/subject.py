from app.core.extensions import db
from sqlalchemy import func


class Subject(db.Model):
    __tablename__ = 'subjects'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    is_locked = db.Column(db.Boolean, default=False, server_default=db.text("0"))
    plaza_board_id = db.Column(db.Integer, db.ForeignKey('plaza_boards.id', ondelete='SET NULL'))
    is_plaza_featured = db.Column(db.Boolean, default=False, server_default=db.text("false"))
    plaza_featured_weight = db.Column(db.Integer, default=0, server_default=db.text('0'))
    plaza_featured_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())

    questions = db.relationship('Question', back_populates='subject', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<Subject {self.id} {self.name!r}>'


class Question(db.Model):
    __tablename__ = 'questions'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'))
    type = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, default='[]', server_default='[]')
    answer = db.Column(db.Text, default='[]', server_default='[]')
    analysis = db.Column(db.Text)
    tags = db.Column(db.Text, default='[]', server_default='[]')
    difficulty = db.Column(db.Integer, default=1, server_default=db.text('1'))
    image_path = db.Column(db.Text)
    source = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), server_default=func.now(), onupdate=db.func.now())

    subject = db.relationship('Subject', back_populates='questions')

    def __repr__(self) -> str:
        return f'<Question {self.id} type={self.type!r}>'
