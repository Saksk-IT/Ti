# -*- coding: utf-8 -*-
"""聊天页面路由"""
from flask import Blueprint, render_template, session, redirect, request

chat_pages_bp = Blueprint('chat_pages', __name__)


@chat_pages_bp.route('/forum')
def forum_page():
    """论坛页面（由原站内聊天页改造）"""
    if not session.get('user_id'):
        return ("请先登录", 401)
    return render_template(
        'chat/chat.html',
        logged_in=True,
        username=session.get('username'),
        user_id=session.get('user_id'),
        is_admin=bool(session.get('is_admin')),
        is_subject_admin=bool(session.get('is_subject_admin')),
        is_notification_admin=bool(session.get('is_notification_admin')),
    )


@chat_pages_bp.route('/chat')
def chat_page():
    """兼容旧入口：/chat -> /forum"""
    if not session.get('user_id'):
        return ("请先登录", 401)
    qs = request.query_string.decode('utf-8') if request.query_string else ''
    target = '/forum' + ('?' + qs if qs else '')
    return redirect(target)


