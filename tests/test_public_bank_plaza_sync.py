# -*- coding: utf-8 -*-
"""公开题库广场与后台科目管理的一致性测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.core.extensions import db


def _build_admin_client(app, seed_user):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user["id"]
        sess["username"] = seed_user["username"]
        sess["is_admin"] = True
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
