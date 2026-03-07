# -*- coding: utf-8 -*-
"""
冒烟测试：认证端点

验证登录 API 的基本可达性和响应格式。
"""
import pytest


class TestLoginAPI:
    """Web 端登录 API 基本测试。"""

    @pytest.mark.smoke
    def test_login_missing_credentials(self, client):
        """POST /api/login 缺少凭据应返回 400 错误。"""
        resp = client.post("/api/login", json={})
        assert resp.status_code == 400

    @pytest.mark.smoke
    def test_login_wrong_password(self, client, seed_user):
        """POST /api/login 密码错误应返回认证失败。"""
        resp = client.post(
            "/api/login",
            json={
                "username": seed_user["email"],
                "password": "wrong_password_123",
            },
        )
        assert resp.status_code in (400, 401, 403)
        data = resp.get_json()
        assert data["status"] == "error"

    @pytest.mark.smoke
    def test_login_success(self, client, seed_user):
        """POST /api/login 正确凭据应登录成功。"""
        resp = client.post(
            "/api/login",
            json={
                "username": seed_user["email"],
                "password": seed_user["password"],
            },
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "success"


class TestAuthProtection:
    """认证保护测试。"""

    @pytest.mark.smoke
    def test_protected_page_redirects_when_unauthenticated(self, client):
        """未登录访问受保护页面应重定向到登录页。"""
        resp = client.get("/quiz", follow_redirects=False)
        assert resp.status_code in (302, 401)

    @pytest.mark.smoke
    def test_homepage_redirects_to_hub_or_login(self, client):
        """未登录访问首页应重定向（到 /hub 或 /login）。"""
        resp = client.get("/", follow_redirects=False)
        # 项目首页可能重定向到 /hub 或 /login
        assert resp.status_code in (200, 302)

    @pytest.mark.smoke
    def test_hub_accessible(self, client):
        """GET /hub 在白名单中，未登录应可访问。"""
        resp = client.get("/hub")
        assert resp.status_code == 200


class TestJWTAuth:
    """JWT 认证（小程序端模式）测试。"""

    @pytest.mark.smoke
    def test_jwt_header_accepted(self, client, jwt_headers):
        """带有效 JWT 的请求不应被认证拦截。"""
        resp = client.get("/api/ping", headers=jwt_headers)
        assert resp.status_code == 200

    @pytest.mark.smoke
    def test_invalid_jwt_rejected(self, client):
        """带无效 JWT 访问受保护 API 应被拒绝。"""
        headers = {
            "Authorization": "Bearer invalid.token.here",
            "Content-Type": "application/json",
        }
        resp = client.get("/api/quiz/subjects", headers=headers)
        assert resp.status_code in (401, 302, 403)
