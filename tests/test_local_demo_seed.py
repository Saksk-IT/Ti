import importlib.util
from pathlib import Path

import pytest
from flask import Flask
from werkzeug.security import check_password_hash

from app import models as m
from app.core.extensions import db


@pytest.fixture
def demo_db(tmp_path):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
    )
    db.init_app(app)
    script = next(
        path for path in (Path(__file__).resolve().parents[1] / "scripts").glob("*.py")
        if "def _run_reset_and_seed(" in path.read_text(encoding="utf-8")
    )
    spec = importlib.util.spec_from_file_location("local_demo_seed", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with app.app_context():
        db.create_all()
        yield module
        db.session.remove()
        db.drop_all()


def test_empty_database_gets_complete_demo_and_repeat_preserves_changes(demo_db):
    summary = demo_db._run_reset_and_seed(empty_only=True)
    db.session.commit()
    assert summary["deleted_tables"] == {}
    assert m.User.query.count() == 7
    assert m.Subject.query.count() == 2
    assert m.Question.query.count() == 4
    assert m.UserQuestionBank.query.count() == 9
    assert m.UserBankQuestion.query.count() == 18
    assert m.Exam.query.count() == 3
    assert m.ForumPost.query.count() > 0
    assert m.ChatMessage.query.count() > 0
    admin = m.User.query.filter_by(email="admin@example.dev").one()
    assert admin.is_admin
    assert check_password_hash(admin.password_hash, "DevPass123!")
    admin.username = "edited_admin"
    db.session.commit()

    assert demo_db._run_reset_and_seed(empty_only=True) == summary
    db.session.commit()
    assert m.User.query.count() == 7
    assert m.Question.query.count() == 4
    assert m.User.query.filter_by(email="admin@example.dev").one().username == "edited_admin"


def test_existing_user_is_preserved_and_seed_is_refused(demo_db):
    db.session.add(m.User(username="existing", password_hash="preserved"))
    db.session.commit()
    with pytest.raises(RuntimeError):
        demo_db._run_reset_and_seed(empty_only=True)
    db.session.rollback()
    assert m.User.query.one().password_hash == "preserved"
    assert m.Subject.query.count() == 0
    assert m.SystemConfig.query.count() == 0
