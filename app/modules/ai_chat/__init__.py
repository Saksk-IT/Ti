# -*- coding: utf-8 -*-
"""Web 前台 AI 聊天模块。"""
import os

from flask import Blueprint, Flask


def init_ai_chat_module(app: Flask):
    """初始化 AI 聊天模块。"""
    from .routes.api import ai_chat_api_bp
    from .routes.pages import ai_chat_pages_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, "templates")

    ai_chat_bp = Blueprint("ai_chat", __name__, template_folder=template_dir)
    ai_chat_bp.register_blueprint(ai_chat_pages_bp)
    ai_chat_bp.register_blueprint(ai_chat_api_bp, url_prefix="/api")
    app.register_blueprint(ai_chat_bp)
