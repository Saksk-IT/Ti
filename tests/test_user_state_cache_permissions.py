# -*- coding: utf-8 -*-
"""用户状态缓存与 Web 管理员权限回归测试。"""

from uuid import uuid4

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.core.utils.jwt_utils import generate_jwt_token
from app.core.utils.user_state_cache import (
    get_user_state,
    has_complete_web_session_state,
    invalidate_user_state,
    set_user_state,
)


def test_partial_jwt_user_state_cache_does_not_strip_web_admin_permission(app):
    """JWT 写入的旧版部分缓存不应让 Web 管理员请求被误判为无权限。"""
    with app.app_context():
        suffix = uuid4().hex[:8]
        username = f"admin_cache_{suffix}"
        row = db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, is_admin, is_subject_admin,
                    is_notification_admin, is_locked, session_version, has_password_set
                )
                VALUES (
                    :username, :email, :password_hash, true, false,
                    false, false, 0, true
                )
                RETURNING id
                """
            ),
            {
                "username": username,
                "email": f"{username}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
            },
        ).fetchone()
        db.session.commit()
        user_id = int(row[0])
        invalidate_user_state(user_id)
        set_user_state(
            user_id,
            {
                "session_version": 0,
                "is_locked": False,
                "openid": f"test_openid_{user_id}",
            },
        )

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["username"] = username
        sess["is_admin"] = True
        sess["is_subject_admin"] = False
        sess["is_notification_admin"] = False
        sess["session_version"] = 0

    response = client.get("/admin/campus", follow_redirects=False)

    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess["is_admin"] is True


def test_jwt_validation_writes_complete_user_state_for_web_session(app):
    """JWT 校验写入的缓存应包含 Web 会话同步所需的权限字段。"""
    with app.app_context():
        suffix = uuid4().hex[:8]
        username = f"jwt_cache_{suffix}"
        openid = f"openid_{suffix}"
        row = db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, openid, is_admin,
                    is_subject_admin, is_notification_admin, is_locked,
                    session_version, has_password_set
                )
                VALUES (
                    :username, :email, :password_hash, :openid, true,
                    false, false, false, 0, true
                )
                RETURNING id
                """
            ),
            {
                "username": username,
                "email": f"{username}@test.example.com",
                "password_hash": generate_password_hash("Test1234!"),
                "openid": openid,
            },
        ).fetchone()
        db.session.commit()
        user_id = int(row[0])
        invalidate_user_state(user_id)
        token = generate_jwt_token(user_id=user_id, openid=openid, session_version=0)

    response = app.test_client().get(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    with app.app_context():
        cached_state = get_user_state(user_id)
    assert has_complete_web_session_state(cached_state)
    assert cached_state["is_admin"] is True
    assert cached_state["email"] == f"{username}@test.example.com"
