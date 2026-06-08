# -*- coding: utf-8 -*-
"""管理员相关 CLI 命令。"""
import os

import click

from app.core.services.default_admin_service import DefaultAdminService


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "on", "yes", "y"}


def register_admin_cli(app):
    @app.cli.command("ensure-default-admin")
    @click.option("--username", envvar="DEFAULT_ADMIN_USERNAME", required=True, help="默认管理员用户名。")
    @click.option("--password", envvar="DEFAULT_ADMIN_PASSWORD", required=True, help="默认管理员密码。")
    @click.option("--email", envvar="DEFAULT_ADMIN_EMAIL", default=None, help="默认管理员邮箱。")
    @click.option("--phone", envvar="DEFAULT_ADMIN_PHONE", default=None, help="默认管理员手机号。")
    @click.option("--reset-password", is_flag=True, help="强制把已有管理员密码重置为 DEFAULT_ADMIN_PASSWORD。")
    def ensure_default_admin(username, password, email, phone, reset_password):
        """创建或修复默认管理员账号。"""
        result = DefaultAdminService.ensure_admin(
            username=username,
            password=password,
            email=email,
            phone=phone,
            reset_password=reset_password or _env_bool("DEFAULT_ADMIN_RESET_PASSWORD"),
        )
        login = result.phone or result.email or result.username
        click.echo(
            "默认管理员已就绪："
            f"id={result.user_id}, login={login}, "
            f"created={str(result.created).lower()}, "
            f"password_updated={str(result.password_updated).lower()}"
        )
