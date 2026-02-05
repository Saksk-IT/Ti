# -*- coding: utf-8 -*-
from flask import current_app, redirect, render_template, session

from app.core.utils.database import get_db
from app.core.utils.decorators import login_required

from .bp import main_pages_bp


@main_pages_bp.route('/profile')
@login_required
def profile_page():
    """个人资料展示页"""
    uid = session.get('user_id')
    return render_template(
        'main/profile/profile_display.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/account')
def account_page():
    """账号管理页面"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/account/profile')
def account_profile_page():
    """账号 - 个人资料"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/account/security')
def account_security_page():
    """账号 - 账号安全"""
    return redirect('/settings/account/security')


@main_pages_bp.route('/account/bindings')
def account_bindings_page():
    """账号 - 账号绑定"""
    return redirect('/settings/account/bindings')


@main_pages_bp.route('/settings')
def settings_page():
    """设置页入口"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/settings/account/profile')
def settings_account_profile_page():
    """设置 - 账号管理 - 个人资料"""
    return render_template('main/account/profile.html')


@main_pages_bp.route('/settings/account/security')
def settings_account_security_page():
    """设置 - 账号管理 - 账号安全"""
    return render_template('main/account/security.html')


@main_pages_bp.route('/settings/account/bindings')
def settings_account_bindings_page():
    """设置 - 账号管理 - 账号绑定"""
    return render_template('main/account/bindings.html')


@main_pages_bp.route('/settings/hotkeys')
def settings_hotkeys_page():
    """设置 - 快捷键"""
    return render_template('main/settings/hotkeys.html')


@main_pages_bp.route('/settings/practice')
def settings_practice_page():
    """设置 - 通用"""
    return render_template('main/settings/practice.html')


@main_pages_bp.route('/settings/theme')
def settings_theme_page():
    """设置 - 主题"""
    return render_template('main/settings/theme.html')


@main_pages_bp.route('/settings/about')
def settings_about_page():
    """设置 - 关于"""
    conn = get_db()
    admin = None
    try:
        admin = conn.execute(
            """
            SELECT id, username, email, contact
            FROM users
            WHERE is_admin = 1
            ORDER BY (last_active IS NULL) ASC, last_active DESC, id ASC
            LIMIT 1
            """
        ).fetchone()
    except Exception as e:
        current_app.logger.warning(f"settings about admin query failed: {e}")
        admin = None

    admin_available = bool(admin)
    admin_username = admin['username'] if admin and 'username' in admin.keys() else ''
    admin_email = ''
    admin_wechat = ''
    if admin:
        if 'email' in admin.keys():
            admin_email = (admin['email'] or '').strip()
        if 'contact' in admin.keys():
            admin_wechat = (admin['contact'] or '').strip()

    chat_disabled_reason = ''
    if session.get('is_admin'):
        chat_disabled_reason = '您当前已是管理员，无需发起站内聊天。'
    elif not admin_available:
        chat_disabled_reason = '系统暂未配置管理员账号，请稍后再试。'

    return render_template(
        'main/settings/about.html',
        admin_available=admin_available,
        admin_username=admin_username,
        admin_email=admin_email,
        admin_wechat=admin_wechat,
        chat_disabled_reason=chat_disabled_reason,
    )

