# -*- coding: utf-8 -*-
"""AI 改动记录入口测试。"""

from uuid import uuid4

from sqlalchemy import text

from app.core.extensions import db
from app.models.system import SystemConfig


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
    return client


def test_admin_can_record_ai_bug_change(app, seed_user):
    client = _make_admin_client(app, seed_user)
    external_id = f"codex-bug-{uuid4().hex[:8]}"

    response = client.post(
        "/admin/api/ai-change-records",
        json={
            "source": "codex",
            "external_id": external_id,
            "category": "fix",
            "title": "修复题库导入异常",
            "changes": ["修复 JSON 导入校验", "补充导入失败提示"],
            "files": ["app/modules/admin/routes/api_components/questions_io.py"],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["data"]["category"] == "bug"
    assert payload["data"]["summary"] == "修复题库导入异常"
    assert payload["data"]["created_by"] == seed_user["id"]

    with app.app_context():
        row = db.session.execute(
            text(
                """
                SELECT category, summary, source, external_id, created_by
                FROM ai_change_records
                WHERE external_id = :external_id
                """
            ),
            {"external_id": external_id},
        ).mappings().one()

    assert row["category"] == "bug"
    assert row["summary"] == "修复题库导入异常"
    assert row["source"] == "codex"
    assert row["created_by"] == seed_user["id"]

    retry_response = client.post(
        "/admin/api/ai-change-records",
        json={
            "source": "codex",
            "external_id": external_id,
            "category": "fix",
            "title": "重复提交不应重复写入",
        },
    )
    assert retry_response.status_code == 200
    assert retry_response.get_json()["data"]["id"] == payload["data"]["id"]


def test_token_client_can_record_and_list_ai_feature_change(app):
    token = f"record-token-{uuid4().hex[:8]}"
    external_id = f"mcp-feature-{uuid4().hex[:8]}"
    with app.app_context():
        SystemConfig.query.filter_by(config_key="ai_change_record_token").delete()
        db.session.add(
            SystemConfig(
                config_key="ai_change_record_token",
                config_value=token,
                description="AI 改动记录调用令牌",
            )
        )
        db.session.commit()

    client = app.test_client()
    response = client.post(
        "/admin/api/ai-change-records",
        headers={"X-AI-Record-Token": token},
        json={
            "source": "mcp",
            "external_id": external_id,
            "title": "新增 AI 改动记录入口",
            "changes": ["新增 Codex/MCP 写入入口", "后台可按功能记录查询"],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["category"] == "feature"
    assert payload["data"]["summary"] == "新增 AI 改动记录入口"
    assert payload["data"]["created_by"] is None

    list_response = client.get(
        "/admin/api/ai-change-records",
        headers={"X-AI-Record-Token": token},
        query_string={"q": external_id, "category": "feature"},
    )

    assert list_response.status_code == 200
    rows = list_response.get_json()["data"]["items"]
    assert len(rows) == 1
    assert rows[0]["external_id"] == external_id
    assert rows[0]["summary"] == "新增 AI 改动记录入口"
