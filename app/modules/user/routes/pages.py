# -*- coding: utf-8 -*-
"""用户页面路由"""
from flask import Blueprint, render_template, session, redirect, url_for

user_pages_bp = Blueprint('user_pages', __name__)


@user_pages_bp.route('/profile')
def profile():
    """用户个人中心"""
    if not session.get('user_id'):
        return redirect(url_for('auth.auth_pages.login_page'))
    
    return render_template('user/profile.html',
                         logged_in=True,
                         username=session.get('username'),
                         user_id=session.get('user_id'))


