# -*- coding: utf-8 -*-
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.core.extensions import db
from app.models.ai_chat import AIChatMessage, AIChatSession
from app.models.system import SystemConfig


AI_KEYS = [
    "ai_provider",
    "ai_api_key",
    "ai_base_url",
    "ai_api_type",
    "ai_model",
    "ai_allowed_models",
]


def _clear_ai_configs():
    SystemConfig.query.filter(SystemConfig.config_key.in_(AI_KEYS)).delete(synchronize_session=False)
    db.session.commit()


def _seed_ai_configs():
    rows = {
        "ai_provider": "custom",
        "ai_api_key": "test-ai-key",
        "ai_base_url": "https://ai.example.test/v1",
        "ai_api_type": "chat_completions",
        "ai_model": "model-a",
        "ai_allowed_models": '["model-a", "model-b"]',
    }
    for key, value in rows.items():
        db.session.add(SystemConfig(config_key=key, config_value=value, description="test"))
    db.session.commit()


def _create_other_user(app):
    with app.app_context():
        db.session.execute(
            text(
                "INSERT INTO users (username, email, password_hash, is_admin, has_password_set) "
                "VALUES (:u, :e, :p, 0, 1)"
            ),
            {
                "u": "ai_other_user",
                "e": "ai_other@test.example.com",
                "p": generate_password_hash("Test1234!"),
            },
        )
        db.session.commit()
        row = db.session.execute(text("SELECT id FROM users WHERE username = :u"), {"u": "ai_other_user"}).fetchone()
        return int(row[0])


def test_ai_chat_page_requires_login(client):
    response = client.get("/ai-chat")
    assert response.status_code in (302, 401)


def test_ai_chat_page_loads_for_session_user(auth_client):
    response = auth_client.get("/ai-chat")
    assert response.status_code == 200
    assert "AI 聊天" in response.get_data(as_text=True)


def test_ai_chat_api_requires_login(client):
    response = client.get("/api/ai-chat/sessions")
    assert response.status_code == 401
    assert response.get_json()["status"] == "unauthorized"


def test_ai_chat_models_and_session_roundtrip(app, auth_client):
    with app.app_context():
        _clear_ai_configs()
        _seed_ai_configs()
    try:
        response = auth_client.get("/api/ai-chat/models")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["code"] == 0
        assert data["data"]["default_model"] == "model-a"
        assert [item["id"] for item in data["data"]["models"]] == ["model-a", "model-b"]

        response = auth_client.post(
            "/api/ai-chat/sessions",
            json={"title": "测试会话", "model": "model-b"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 200
        created = response.get_json()["data"]["session"]
        assert created["title"] == "测试会话"
        assert created["model"] == "model-b"

        response = auth_client.get(f"/api/ai-chat/sessions/{created['id']}/messages")
        assert response.status_code == 200
        assert response.get_json()["data"]["messages"] == []
    finally:
        with app.app_context():
            AIChatMessage.query.delete()
            AIChatSession.query.delete()
            _clear_ai_configs()


def test_ai_chat_rejects_invalid_model(app, auth_client):
    with app.app_context():
        _clear_ai_configs()
        _seed_ai_configs()
    try:
        response = auth_client.post(
            "/api/ai-chat/sessions",
            json={"title": "非法模型", "model": "expensive-model"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 400
        assert response.get_json()["message"] == "所选模型不可用"
    finally:
        with app.app_context():
            _clear_ai_configs()


def test_ai_chat_session_owner_is_enforced(app, auth_client, seed_user):
    other_user_id = _create_other_user(app)
    with app.app_context():
        _clear_ai_configs()
        _seed_ai_configs()
        session_row = AIChatSession(
            user_id=other_user_id,
            title="其他用户会话",
            model="model-a",
            provider="custom",
        )
        db.session.add(session_row)
        db.session.commit()
        session_id = session_row.id
    try:
        response = auth_client.get(f"/api/ai-chat/sessions/{session_id}/messages")
        assert response.status_code == 404

        response = auth_client.patch(
            f"/api/ai-chat/sessions/{session_id}",
            json={"title": "越权修改"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 404
    finally:
        with app.app_context():
            AIChatMessage.query.delete()
            AIChatSession.query.delete()
            db.session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": other_user_id})
            db.session.commit()
            _clear_ai_configs()


def test_ai_chat_stream_saves_messages(app, auth_client, monkeypatch):
    with app.app_context():
        _clear_ai_configs()
        _seed_ai_configs()

    def fake_stream_text(self, **kwargs):
        assert kwargs["model"] == "model-a"
        assert kwargs["messages"][-1]["content"] == "你好"
        yield "你好"
        yield "，这里是 AI。"

    monkeypatch.setattr("app.modules.quiz.services.ai_client.AIClient.stream_text", fake_stream_text)

    try:
        create_response = auth_client.post(
            "/api/ai-chat/sessions",
            json={"title": "流式测试", "model": "model-a"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        session_id = create_response.get_json()["data"]["session"]["id"]

        response = auth_client.post(
            f"/api/ai-chat/sessions/{session_id}/messages/stream",
            json={"content": "你好", "model": "model-a"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "event: meta" in body
        assert "event: delta" in body
        assert "event: done" in body

        with app.app_context():
            rows = AIChatMessage.query.filter_by(session_id=session_id).order_by(AIChatMessage.id.asc()).all()
            assert [row.role for row in rows] == ["user", "assistant"]
            assert rows[0].content == "你好"
            assert rows[1].content == "你好，这里是 AI。"
            assert rows[1].status == "completed"
    finally:
        with app.app_context():
            AIChatMessage.query.delete()
            AIChatSession.query.delete()
            _clear_ai_configs()


def test_ai_chat_stream_persists_failed_reply_when_runtime_missing(app, auth_client):
    with app.app_context():
        _clear_ai_configs()
        rows = {
            "ai_provider": "custom",
            "ai_base_url": "https://ai.example.test/v1",
            "ai_api_type": "chat_completions",
            "ai_model": "model-a",
            "ai_allowed_models": '["model-a"]',
        }
        for key, value in rows.items():
            db.session.add(SystemConfig(config_key=key, config_value=value, description="test"))
        db.session.commit()

    try:
        create_response = auth_client.post(
            "/api/ai-chat/sessions",
            json={"title": "失败落库", "model": "model-a"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        session_id = create_response.get_json()["data"]["session"]["id"]

        response = auth_client.post(
            f"/api/ai-chat/sessions/{session_id}/messages/stream",
            json={"content": "请回答", "model": "model-a"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "event: meta" in body
        assert "event: error" in body

        with app.app_context():
            rows = AIChatMessage.query.filter_by(session_id=session_id).order_by(AIChatMessage.id.asc()).all()
            assert [row.role for row in rows] == ["user", "assistant"]
            assert rows[0].content == "请回答"
            assert rows[0].status == "completed"
            assert rows[1].content == ""
            assert rows[1].status == "failed"
            assert rows[1].error == "AI 回复失败"
    finally:
        with app.app_context():
            AIChatMessage.query.delete()
            AIChatSession.query.delete()
            _clear_ai_configs()
