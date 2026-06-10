# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db


def _make_admin_client(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin = true, is_locked = false WHERE id = :uid"),
            {"uid": seed_user["id"]},
        )
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["username"] = seed_user["username"]
        sess["is_admin"] = True
        sess["session_version"] = 0
    return client


def test_admin_users_api_returns_iso_times_and_recent_online_state(app, seed_user):
    client = _make_admin_client(app, seed_user)
    suffix = uuid4().hex[:8]
    active_username = f"admin_time_{suffix}_active"
    stale_username = f"admin_time_{suffix}_stale"
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    with app.app_context():
        password_hash = generate_password_hash("Test1234!")
        db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, is_admin, is_locked,
                    has_password_set, created_at, last_active
                )
                VALUES
                    (:active_username, :active_email, :password_hash, false, false, true, :created_at, :active_at),
                    (:stale_username, :stale_email, :password_hash, false, false, true, :created_at, :stale_at)
                """
            ),
            {
                "active_username": active_username,
                "active_email": f"{active_username}@test.example.com",
                "stale_username": stale_username,
                "stale_email": f"{stale_username}@test.example.com",
                "password_hash": password_hash,
                "created_at": now_utc - timedelta(days=1),
                "active_at": now_utc - timedelta(minutes=2),
                "stale_at": now_utc - timedelta(minutes=10),
            },
        )
        db.session.commit()

    response = client.get(f"/admin/api/users?search=admin_time_{suffix}&size=20")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"

    rows = {row["username"]: row for row in payload["data"]}
    assert rows[active_username]["is_online"] is True
    assert rows[stale_username]["is_online"] is False

    for row in rows.values():
        assert "GMT" not in row["created_at"]
        assert "T" in row["created_at"]
        assert row["created_at"].endswith("Z")
        assert row["last_active"].endswith("Z")
