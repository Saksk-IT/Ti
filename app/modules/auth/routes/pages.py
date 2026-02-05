# -*- coding: utf-8 -*-
"""认证页面路由"""
from flask import Blueprint, render_template, request, redirect, current_app

from app.modules.auth.services.web_login_service import WebLoginService, set_web_session

auth_pages_bp = Blueprint('auth_pages', __name__)

def _sanitize_next_path(next_path: str) -> str:
    v = (next_path or "").strip()
    if not v:
        return "/hub"
    if "://" in v or v.startswith("//") or v.startswith("\\"):
        return "/hub"
    if not v.startswith("/"):
        v = "/" + v
    return v


@auth_pages_bp.route('/web_login/exchange_redirect')
def web_login_exchange_redirect():
    """
    WebView 自动登录跳转页：
    - 消费一次性 token
    - 写入 Web session
    - 跳转到 next（站内路径）
    """
    token = (request.args.get("token") or "").strip()
    next_path = _sanitize_next_path(request.args.get("next") or "")

    from urllib.parse import quote
    next_q = quote(next_path, safe="/")

    if not token:
        return redirect(f"/login?from=webview&redirect={next_q}")

    try:
        token_data = WebLoginService.consume_exchange_token(token)
        user_id = int(token_data["user_id"])
        sid = str(token_data.get("sid") or "")
        set_web_session(user_id)
        if sid:
            WebLoginService.mark_exchanged(sid)
        return redirect(next_path)
    except Exception as e:
        current_app.logger.warning(f"webview 自动登录失败: {e}")
        return redirect(f"/login?from=webview&redirect={next_q}")


@auth_pages_bp.route('/login')
def login_page():
    """登录页面"""
    from_param = request.args.get('from', '')
    redirect_url = request.args.get('redirect', '')
    
    # 根据 from 参数设置提示信息
    tips = {
        'quiz': '刷题',
        'memo': '背题',
        '背题': '背题',
        'favorites': '收藏本',
        '收藏本': '收藏本',
        'mistakes': '错题本',
        '错题本': '错题本',
        'exam': '考试',
        '考试': '考试',
        'exams': '考试',
        'profile': '个人中心',
        'search': '搜索'
    }
    
    tip_message = tips.get(from_param, '')
    if tip_message:
        tip_message = f'使用{tip_message}功能需要先登录'
    
    return render_template('auth/login.html', 
                         mode='login',
                         from_param=from_param,
                         redirect_url=redirect_url,
                         tip_message=tip_message)


# 注册功能已移除，使用邮箱验证码自动注册
# @auth_pages_bp.route('/register')
# def register_page():
#     return render_template('auth/login.html', mode='register')


@auth_pages_bp.route('/terms')
def terms_page():
    """服务协议页面"""
    return render_template('auth/terms.html')


@auth_pages_bp.route('/privacy')
def privacy_page():
    """隐私保护协议页面"""
    return render_template('auth/privacy.html')

