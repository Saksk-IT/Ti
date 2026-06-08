# -*- coding: utf-8 -*-
"""Flask CLI 命令注册入口。"""


def register_cli_commands(app):
    from app.core.cli.admin import register_admin_cli

    register_admin_cli(app)
