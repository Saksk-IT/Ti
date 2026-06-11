# -*- coding: utf-8 -*-
"""公开题库广场与后台科目管理的一致性测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.user_state_cache import invalidate_user_state
from app.modules.user_bank.services.plaza_metrics_service import ensure_plaza_metrics


def _build_admin_client(app, seed_user):
    with app.app_context():
        db.session.execute(
            text("UPDATE users SET is_admin = 1, is_subject_admin = 1 WHERE id = :uid"),
            {"uid": int(seed_user["id"])},
        )
        db.session.commit()
        invalidate_user_state(int(seed_user["id"]))

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["username"] = seed_user["username"]
        sess["is_admin"] = True
        sess["is_subject_admin"] = True
        sess["session_version"] = 0
    return client


def test_subject_rename_updates_public_bank_plaza_immediately(app, seed_user):
    """后台重命名系统题库后，题库广场列表应立即返回新名称。"""
    suffix = uuid.uuid4().hex[:8]
    original_name = f"测试系统题库-{suffix}"
    renamed_name = f"测试系统题库已改名-{suffix}"
    subject_id = None
    client = _build_admin_client(app, seed_user)

    try:
        create_resp = client.post(
            "/admin/api/subjects",
            json={"name": original_name},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert create_resp.status_code == 200
        assert create_resp.get_json()["status"] == "success"

        with app.app_context():
            row = db.session.execute(
                text("SELECT id FROM subjects WHERE name = :name"),
                {"name": original_name},
            ).fetchone()
            assert row is not None
            subject_id = int(row[0])

        first_resp = client.get("/api/public/banks/list?per_page=100")
        assert first_resp.status_code == 200
        first_items = first_resp.get_json()["data"]["items"]
        assert any(
            item["source_type"] == "system"
            and item["id"] == subject_id
            and item["name"] == original_name
            for item in first_items
        )

        rename_resp = client.put(
            f"/admin/api/subjects/{subject_id}",
            json={"name": renamed_name},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert rename_resp.status_code == 200
        assert rename_resp.get_json()["status"] == "success"

        second_resp = client.get("/api/public/banks/list?per_page=100")
        assert second_resp.status_code == 200
        second_items = second_resp.get_json()["data"]["items"]
        assert any(
            item["source_type"] == "system"
            and item["id"] == subject_id
            and item["name"] == renamed_name
            for item in second_items
        )
    finally:
        if subject_id is not None:
            with app.app_context():
                db.session.execute(text("DELETE FROM subjects WHERE id = :subject_id"), {"subject_id": subject_id})
                db.session.execute(
                    text(
                        """
                        DELETE FROM public_bank_plaza_metrics
                        WHERE source_type = 'system' AND source_id = :subject_id
                        """
                    ),
                    {"subject_id": subject_id},
                )
                db.session.commit()


def test_public_and_my_bank_lists_include_owner_avatar(app, seed_user):
    """题库广场与我的题库列表都应返回题库作者头像。"""
    suffix = uuid.uuid4().hex[:8]
    owner_username = f"avatar_owner_{suffix}"
    owner_avatar = f"/uploads/avatars/avatar_{suffix}.png"
    bank_name = f"头像测试题库-{suffix}"
    owner_id = None
    bank_id = None
    client = _build_admin_client(app, seed_user)

    try:
        with app.app_context():
            owner_id = db.session.execute(
                text(
                    """
                    INSERT INTO users (username, email, password_hash, avatar, is_admin, has_password_set)
                    VALUES (:username, :email, :password_hash, :avatar, 0, 1)
                    RETURNING id
                    """
                ),
                {
                    "username": owner_username,
                    "email": f"{owner_username}@test.example.com",
                    "password_hash": "test",
                    "avatar": owner_avatar,
                },
            ).scalar_one()
            bank_id = db.session.execute(
                text(
                    """
                    INSERT INTO user_question_banks (
                        user_id, name, description, is_public, public_at, status, question_count
                    )
                    VALUES (:owner_id, :name, 'avatar fixture', true, CURRENT_TIMESTAMP, 1, 3)
                    RETURNING id
                    """
                ),
                {"owner_id": int(owner_id), "name": bank_name},
            ).scalar_one()
            db.session.execute(
                text(
                    """
                    INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
                    VALUES (:bank_id, :user_id, CURRENT_TIMESTAMP, 1)
                    """
                ),
                {"bank_id": int(bank_id), "user_id": int(seed_user["id"])},
            )
            db.session.commit()
            ensure_plaza_metrics(force=True)

        plaza_resp = client.get(f"/api/public/banks/list?keyword={bank_name}&per_page=5")
        assert plaza_resp.status_code == 200
        plaza_items = plaza_resp.get_json()["data"]["items"]
        plaza_item = next(item for item in plaza_items if item["source_type"] == "user_public" and item["id"] == bank_id)
        assert plaza_item["owner_avatar"] == owner_avatar

        my_resp = client.get(f"/user/banks/api/overview?scope=public&keyword={bank_name}&per_page=5")
        assert my_resp.status_code == 200
        my_items = my_resp.get_json()["data"]["items"]
        my_item = next(item for item in my_items if item["source_type"] == "user" and item["id"] == bank_id)
        assert my_item["owner_avatar"] == owner_avatar
    finally:
        with app.app_context():
            if bank_id is not None:
                db.session.execute(text("DELETE FROM public_bank_users WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
                db.session.execute(text("DELETE FROM public_bank_plaza_metrics WHERE source_type = 'user_public' AND source_id = :bank_id"), {"bank_id": int(bank_id)})
                db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            if owner_id is not None:
                db.session.execute(text("DELETE FROM users WHERE id = :owner_id"), {"owner_id": int(owner_id)})
            db.session.commit()


def test_my_created_bank_list_includes_cover_image(app, seed_user):
    """我的题库里“我创建的题库”列表应返回题库封面。"""
    suffix = uuid.uuid4().hex[:8]
    bank_name = f"封面列表题库-{suffix}"
    cover_image = f"/uploads/bank_covers/bank_cover_{suffix}.png"
    bank_id = None
    client = _build_admin_client(app, seed_user)

    try:
        with app.app_context():
            bank_id = db.session.execute(
                text(
                    """
                    INSERT INTO user_question_banks (
                        user_id, name, description, cover_image, is_public, status, question_count
                    )
                    VALUES (:user_id, :name, 'cover fixture', :cover_image, true, 1, 5)
                    RETURNING id
                    """
                ),
                {
                    "user_id": int(seed_user["id"]),
                    "name": bank_name,
                    "cover_image": cover_image,
                },
            ).scalar_one()
            db.session.commit()

        my_resp = client.get(f"/user/banks/api/overview?scope=created&keyword={bank_name}&per_page=5")
        assert my_resp.status_code == 200
        my_items = my_resp.get_json()["data"]["items"]
        my_item = next(item for item in my_items if item["id"] == bank_id and item["kind"] == "created")
        assert my_item["cover_image"] == cover_image
    finally:
        with app.app_context():
            if bank_id is not None:
                db.session.execute(text("DELETE FROM public_bank_plaza_metrics WHERE source_type = 'user_public' AND source_id = :bank_id"), {"bank_id": int(bank_id)})
                db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.commit()
