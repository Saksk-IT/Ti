# -*- coding: utf-8 -*-
"""
pytest 基础 fixtures

提供 Flask 应用、数据库、客户端和认证相关的 fixtures，
供所有测试模块复用。
"""
import os
import pytest
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# 测试环境变量覆盖（必须在 import app 之前设置）
# .env 文件中的 Redis/限流配置会被 load_dotenv 加载，
# 测试环境需要覆盖为内存存储以避免依赖外部服务。
# ---------------------------------------------------------------------------
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
os.environ.pop("REDIS_URL", None)

from app import create_app  # noqa: E402
from app.core.extensions import db as _db  # noqa: E402


# ---------------------------------------------------------------------------
# 应用 & 数据库
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """创建测试用 Flask 应用（整个测试会话共享）。"""
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def db_session(app):
    """每个测试函数独立的数据库事务，测试结束后自动回滚。"""
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        session = _db.session
        yield session
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# HTTP 客户端
# ---------------------------------------------------------------------------

@pytest.fixture
def client(app):
    """未认证的 Flask 测试客户端。"""
    return app.test_client()


@pytest.fixture
def auth_client(app, seed_user):
    """已通过 Session 登录的 Flask 测试客户端（Web 端模式）。"""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["username"] = seed_user["username"]
    return c


# ---------------------------------------------------------------------------
# 种子数据
# ---------------------------------------------------------------------------

TEST_USER = {
    "username": "testuser",
    "email": "testuser@test.example.com",
    "password": "Test1234!",
}


@pytest.fixture(scope="session")
def seed_user(app):
    """创建测试用户并返回其信息字典（整个会话共享）。"""
    from sqlalchemy import text

    with app.app_context():
        row = _db.session.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": TEST_USER["username"]},
        ).fetchone()

        if row is None:
            _db.session.execute(
                text(
                    "INSERT INTO users (username, email, password_hash, is_admin, has_password_set) "
                    "VALUES (:u, :e, :p, 0, 1)"
                ),
                {
                    "u": TEST_USER["username"],
                    "e": TEST_USER["email"],
                    "p": generate_password_hash(TEST_USER["password"]),
                },
            )
            _db.session.commit()
            row = _db.session.execute(
                text("SELECT id FROM users WHERE username = :u"),
                {"u": TEST_USER["username"]},
            ).fetchone()

        return {
            "id": row[0],
            "username": TEST_USER["username"],
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        }


# ---------------------------------------------------------------------------
# JWT 认证（小程序端模式）
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_headers(app, seed_user):
    """返回带有效 JWT Bearer Token 的请求头字典。"""
    from app.core.utils.jwt_utils import generate_jwt_token

    with app.app_context():
        token = generate_jwt_token(
            user_id=seed_user["id"],
            openid=f"test_openid_{seed_user['id']}",
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
