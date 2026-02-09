# -*- coding: utf-8 -*-
"""Dashboard Utility 演示页面路由。"""

from flask import redirect, render_template, session

from .bp import main_pages_bp


@main_pages_bp.route('/dashboard/utility')
def dashboard_utility_page():
    """UtilityHub 仪表板演示页面。"""
    uid = session.get('user_id')
    if not uid:
        return redirect('/login')

    return render_template(
        'main/dashboard/dashboard_utility.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=int(uid),
    )
