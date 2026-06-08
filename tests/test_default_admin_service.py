# -*- coding: utf-8 -*-
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.core.services.default_admin_service import DefaultAdminService
from app.core.services.user_service import UserService


def _delete_user(username: str, phone: str | None = None, email: str | None = None) -> None:
    clauses = ["username = :username"]
    params = {"username": username, "phone": phone, "email": email}
    if phone:
        clauses.append("phone = :phone")
    if email:
        clauses.append("email = :email")
    db.session.execute(text(f"DELETE FROM users WHERE {' OR '.join(clauses)}"), params)
    db.session.commit()


def test_ensure_default_admin_creates_login_ready_admin(app):
    username = "13900001111"
    phone = "13900001111"
    password = "Admin12345"

    with app.app_context():
        _delete_user(username, phone=phone)

        result = DefaultAdminService.ensure_admin(
            username=username,
            phone=phone,
            password=password,
        )

        row = db.session.execute(
            text(
                """
                SELECT username, phone, is_admin, is_locked, has_password_set, phone_verified
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": result.user_id},
        ).fetchone()._mapping

        assert result.created is True
        assert result.password_updated is True
        assert row["username"] == username
        assert row["phone"] == phone
        assert bool(row["is_admin"]) is True
        assert bool(row["is_locked"]) is False
        assert bool(row["has_password_set"]) is True
        assert bool(row["phone_verified"]) is True
        assert UserService.verify_password(phone, password)["id"] == result.user_id


def test_ensure_default_admin_restores_existing_user_password_and_permissions(app):
    username = "admin_restore"
    phone = "13900002222"
    old_password = "Oldpass123"
    new_password = "Newpass123"

    with app.app_context():
        _delete_user(username, phone=phone)
        db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, phone, password_hash, is_admin, is_locked,
                    has_password_set, phone_verified, session_version
                )
                VALUES (
                    :username, :phone, :password_hash, false, true,
                    false, false, 0
                )
                """
            ),
            {
                "username": username,
                "phone": phone,
                "password_hash": generate_password_hash(old_password),
            },
        )
        db.session.commit()

        result = DefaultAdminService.ensure_admin(
            username=username,
            phone=phone,
            password=new_password,
            reset_password=True,
        )

        row = db.session.execute(
            text(
                """
                SELECT is_admin, is_locked, has_password_set, phone_verified, session_version
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": result.user_id},
        ).fetchone()._mapping

        assert result.created is False
        assert result.password_updated is True
        assert result.promoted_to_admin is True
        assert result.unlocked is True
        assert bool(row["is_admin"]) is True
        assert bool(row["is_locked"]) is False
        assert bool(row["has_password_set"]) is True
        assert bool(row["phone_verified"]) is True
        assert int(row["session_version"]) == 1
        assert UserService.verify_password(phone, new_password)["id"] == result.user_id
        assert UserService.verify_password(phone, old_password) is None
