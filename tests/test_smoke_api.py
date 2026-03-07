# -*- coding: utf-8 -*-
"""
冒烟测试：关键 API 端点可达性

验证核心业务模块的 API 端点在认证后可以正常响应。
"""
import pytest


class TestQuizAPI:
    """Quiz 模块 API 可达性测试。"""

    @pytest.mark.smoke
    def test_subjects_list(self, auth_client):
        """GET /api/quiz/subjects 应返回科目列表。"""
        resp = auth_client.get("/api/quiz/subjects")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    @pytest.mark.smoke
    def test_questions_count(self, client):
        """GET /api/questions/count 无需登录应可访问。"""
        resp = client.get("/api/questions/count")
        assert resp.status_code == 200


class TestUserAPI:
    """User 模块 API 可达性测试。"""

    @pytest.mark.smoke
    def test_profile_requires_auth(self, client):
        """GET /profile 未登录应重定向。"""
        resp = client.get("/profile", follow_redirects=False)
        assert resp.status_code in (302, 401)

    @pytest.mark.smoke
    def test_profile_accessible_when_authenticated(self, auth_client):
        """GET /profile 已登录应返回 200。"""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200


class TestPublicBankAPI:
    """公开题库 API 可达性测试。"""

    @pytest.mark.smoke
    def test_public_banks_list(self, client):
        """GET /api/public/banks 无需登录应可访问。"""
        resp = client.get("/api/public/banks")
        assert resp.status_code == 200

    @pytest.mark.smoke
    def test_public_banks_page(self, client):
        """GET /public/banks 无需登录应可访问。"""
        resp = client.get("/public/banks")
        assert resp.status_code == 200
