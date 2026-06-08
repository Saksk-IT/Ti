# -*- coding: utf-8 -*-
"""AI 聊天页面路由。"""
from flask import Blueprint, render_template

from app.core.utils.decorators import auth_required, current_user_id


ai_chat_pages_bp = Blueprint("ai_chat_pages", __name__)


@ai_chat_pages_bp.route("/ai-chat")
@auth_required
def ai_chat_page():
    """Web 前台 AI 聊天页面。"""
    return render_template("ai_chat/ai_chat.html", user_id=current_user_id())
