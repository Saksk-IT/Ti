# -*- coding: utf-8 -*-
"""默认管理员账号初始化服务。"""
from dataclasses import dataclass
import re
from typing import Optional

from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.extensions import db
from app.core.utils.validators import validate_password, validate_username


PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


@dataclass(frozen=True)
class DefaultAdminResult:
    user_id: int
    username: str
    email: Optional[str]
    phone: Optional[str]
    created: bool
    password_updated: bool
    promoted_to_admin: bool
    unlocked: bool


class DefaultAdminService:
    """创建或修复部署默认管理员。"""

    @staticmethod
    def ensure_admin(
        *,
        username: str,
        password: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        reset_password: bool = False,
    ) -> DefaultAdminResult:
        username = (username or "").strip()
        password = password or ""
        email = (email or "").strip() or None
        phone = (phone or "").strip() or None

        DefaultAdminService._validate(username, password, email, phone)

        rows = DefaultAdminService._find_candidates(username=username, email=email, phone=phone)
        user_ids = {int(row._mapping["id"]) for row in rows}
        if len(user_ids) > 1:
            raise ValueError("默认管理员配置匹配到多个用户，请先手动合并 username/email/phone")

        if not rows:
            return DefaultAdminService._create_admin(
                username=username,
                password=password,
                email=email,
                phone=phone,
            )

        row = rows[0]._mapping
        return DefaultAdminService._update_admin(
            row=row,
            username=username,
            password=password,
            email=email,
            phone=phone,
            reset_password=reset_password,
        )

    @staticmethod
    def _validate(username: str, password: str, email: Optional[str], phone: Optional[str]) -> None:
        username_ok, username_error = validate_username(username)
        if not username_ok:
            raise ValueError(username_error)

        password_ok, password_error = validate_password(password)
        if not password_ok:
            raise ValueError(password_error)

        if not email and not phone:
            raise ValueError("默认管理员必须配置邮箱或手机号，登录接口不支持纯用户名登录")

        if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
            raise ValueError("默认管理员邮箱格式不正确")

        if phone and not PHONE_RE.fullmatch(phone):
            raise ValueError("默认管理员手机号格式不正确")

    @staticmethod
    def _find_candidates(*, username: str, email: Optional[str], phone: Optional[str]):
        clauses = ["username = :username"]
        params = {"username": username, "email": email, "phone": phone}
        if email:
            clauses.append("email = :email")
        if phone:
            clauses.append("phone = :phone")

        return db.session.execute(
            text(f"SELECT * FROM users WHERE {' OR '.join(clauses)}"),
            params,
        ).fetchall()

    @staticmethod
    def _create_admin(*, username: str, password: str, email: Optional[str], phone: Optional[str]) -> DefaultAdminResult:
        password_hash = generate_password_hash(password)
        row = db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, password_hash, is_admin, is_locked, session_version,
                    email, email_verified, phone, phone_verified, has_password_set
                )
                VALUES (
                    :username, :password_hash, true, false, 0,
                    :email, :email_verified, :phone, :phone_verified, true
                )
                RETURNING id
                """
            ),
            {
                "username": username,
                "password_hash": password_hash,
                "email": email,
                "email_verified": bool(email),
                "phone": phone,
                "phone_verified": bool(phone),
            },
        ).fetchone()
        db.session.commit()

        return DefaultAdminResult(
            user_id=int(row._mapping["id"]),
            username=username,
            email=email,
            phone=phone,
            created=True,
            password_updated=True,
            promoted_to_admin=True,
            unlocked=True,
        )

    @staticmethod
    def _update_admin(
        *,
        row,
        username: str,
        password: str,
        email: Optional[str],
        phone: Optional[str],
        reset_password: bool,
    ) -> DefaultAdminResult:
        user_id = int(row["id"])
        existing_hash = str(row.get("password_hash") or "")
        should_update_password = reset_password or not existing_hash.strip()
        if should_update_password and existing_hash:
            should_update_password = not check_password_hash(existing_hash, password)

        promoted_to_admin = not bool(row.get("is_admin"))
        unlocked = bool(row.get("is_locked"))
        should_bump_session = should_update_password or promoted_to_admin or unlocked

        db.session.execute(
            text(
                """
                UPDATE users
                SET username = :username,
                    email = COALESCE(:email, email),
                    email_verified = CASE WHEN :email IS NULL THEN email_verified ELSE true END,
                    phone = COALESCE(:phone, phone),
                    phone_verified = CASE WHEN :phone IS NULL THEN phone_verified ELSE true END,
                    password_hash = CASE
                        WHEN :should_update_password THEN :password_hash
                        ELSE password_hash
                    END,
                    has_password_set = true,
                    is_admin = true,
                    is_locked = false,
                    session_version = CASE
                        WHEN :should_bump_session THEN COALESCE(session_version, 0) + 1
                        ELSE session_version
                    END
                WHERE id = :user_id
                """
            ),
            {
                "user_id": user_id,
                "username": username,
                "email": email,
                "phone": phone,
                "should_update_password": should_update_password,
                "password_hash": generate_password_hash(password) if should_update_password else existing_hash,
                "should_bump_session": should_bump_session,
            },
        )
        db.session.commit()

        refreshed = db.session.execute(
            text("SELECT username, email, phone FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        ).fetchone()._mapping

        return DefaultAdminResult(
            user_id=user_id,
            username=str(refreshed["username"]),
            email=refreshed.get("email"),
            phone=refreshed.get("phone"),
            created=False,
            password_updated=should_update_password,
            promoted_to_admin=promoted_to_admin,
            unlocked=unlocked,
        )
