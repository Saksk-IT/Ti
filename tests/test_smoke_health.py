# -*- coding: utf-8 -*-
"""
冒烟测试：健康检查端点

验证应用能够正常启动并响应基本请求。
"""
import pytest


class TestHealthCheck:
    """健康检查 /api/ping 端点测试。"""

    @pytest.mark.smoke
    def test_ping_returns_200(self, client):
        """GET /api/ping 应返回 200 + success 状态。"""
        resp = client.get("/api/ping")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["pong"] is True

    @pytest.mark.smoke
    def test_ping_deep_without_services(self, client):
        """GET /api/ping?deep=1 在测试环境（无 Redis）应返回 503 或 200。

        测试环境使用 SQLite 且无 Redis，deep=1 会检测 Redis 连通性，
        预期 503（Redis 不可用）或 200（如果项目优雅降级）。
        两种情况都说明深度检查逻辑正常工作。
        """
        resp = client.get("/api/ping?deep=1")
        assert resp.status_code in (200, 503)


class TestAppFactory:
    """应用工厂基本验证。"""

    @pytest.mark.smoke
    def test_app_is_testing(self, app):
        """应用配置应为 TESTING=True。"""
        assert app.config["TESTING"] is True

    @pytest.mark.smoke
    def test_app_has_secret_key(self, app):
        """应用应有 SECRET_KEY。"""
        assert app.config["SECRET_KEY"]

    @pytest.mark.smoke
    def test_blueprints_registered(self, app):
        """核心蓝图应已注册。"""
        bp_names = set(app.blueprints.keys())
        expected = {"auth", "main", "quiz", "exam", "user"}
        missing = expected - bp_names
        assert not missing, f"缺少蓝图: {missing}"
