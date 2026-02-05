#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用启动文件 - 新版模块化结构

用途：
- 开发：python run.py
- 生产：建议 gunicorn + systemd（见 docs/systemd/README.md）
"""

from __future__ import annotations

import os


def _load_env() -> None:
    """加载 .env（可选依赖：python-dotenv）。"""
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    try:
        load_dotenv(override=False)
    except Exception:
        pass


def _normalize_config_name(raw: str | None) -> str:
    """标准化配置名称（development/production/testing）。"""
    name = (raw or "").strip()
    if not name:
        return "development"

    key = name.lower()
    mapping = {
        "dev": "development",
        "debug": "development",
        "development": "development",
        "prod": "production",
        "production": "production",
        "test": "testing",
        "testing": "testing",
    }
    return mapping.get(key, "development")


def _get_config_name() -> str:
    # 支持 FLASK_ENV / ENVIRONMENT / APP_ENV
    raw = os.environ.get("FLASK_ENV") or os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV")
    return _normalize_config_name(raw)


def _get_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return int(default)
    try:
        return int(raw)
    except Exception:
        return int(default)


def _should_print_banner(debug: bool) -> bool:
    # debug + 热重载时避免打印两次（父进程/子进程）
    return (not debug) or (os.environ.get("WERKZEUG_RUN_MAIN") == "true")


_load_env()

from app import create_app  # noqa: E402

config_name = _get_config_name()
app = create_app(config_name=config_name)

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = _get_int_env("PORT", 5000)
    debug = bool(app.config.get("DEBUG", False))

    if _should_print_banner(debug):
        print("=" * 60)
        print("  题库系统 - 模块化版本")
        print("=" * 60)
        print(f"  环境: {config_name}")
        print(f"  绑定: {host}:{port}")
        print(f"  本机: http://127.0.0.1:{port}")
        print(f"  调试: {debug}")
        print("=" * 60)

        if config_name == "development":
            print("\n[开发模式]")
            print("  - DEBUG/热重载：已启用")
            print("  - 邮件验证码：可配置为控制台输出（不发送真实邮件）\n")

        if config_name == "production":
            print("\n[生产模式]")
            if not os.environ.get("SECRET_KEY"):
                print("  警告: SECRET_KEY 未设置，请设置环境变量。")
                print('  生成示例: python -c "import secrets; print(secrets.token_urlsafe(32))"')
            if debug:
                print("  警告: 生产环境不应启用 DEBUG 模式。")
            print("  提示: 建议使用 gunicorn + systemd 部署（见 docs/systemd/README.md）。\n")

    app.run(host=host, port=port, debug=debug)

