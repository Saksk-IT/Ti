# -*- coding: utf-8 -*-
"""管理后台模块"""
import os
from flask import Flask, Blueprint, session, request, jsonify, redirect


def _check_admin_permission():
    """Admin 蓝图独立权限检查钩子。

    无论请求使用 session 还是 JWT，都必须验证 admin/科目管理员/通知管理员权限。
    此钩子独立于全局 before_request，防止 JWT 请求绕过 admin 权限检查。
    """
    path = request.path or ''
    if path.startswith('/admin/api/ai-change-records') and (
        request.headers.get('X-AI-Record-Token') or
        str(request.headers.get('Authorization') or '').startswith('Bearer ')
    ):
        return None

    # --- 1. 尝试从 session 获取身份 ---
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    is_subject_admin = session.get('is_subject_admin', False)
    is_notification_admin = session.get('is_notification_admin', False)

    # --- 2. 如果 session 无身份，尝试从 JWT 获取 ---
    if not user_id:
        jwt_header = request.headers.get('Authorization') or ''
        if jwt_header.startswith('Bearer '):
            from app.core.utils.jwt_utils import decode_jwt_token
            token = jwt_header[7:]
            payload = decode_jwt_token(token)
            if payload:
                user_id = payload.get('user_id')

            # 从数据库查询该用户的管理员权限
            if user_id:
                try:
                    from app.models.user import User as UserModel
                    u = UserModel.query.get(int(user_id))
                    if u:
                        is_admin = bool(u.is_admin)
                        is_subject_admin = bool(u.is_subject_admin)
                        is_notification_admin = bool(u.is_notification_admin)
                except Exception:
                    pass
    elif user_id:
        try:
            from app.models.user import User as UserModel
            u = UserModel.query.get(int(user_id))
            if u:
                is_admin = bool(u.is_admin)
                is_subject_admin = bool(u.is_subject_admin)
                is_notification_admin = bool(u.is_notification_admin)
                session['is_admin'] = is_admin
                session['is_subject_admin'] = is_subject_admin
                session['is_notification_admin'] = is_notification_admin
        except Exception:
            pass

    # --- 3. 未认证 ---
    if not user_id:
        if path.startswith('/admin/api'):
            return jsonify({'status': 'unauthorized', 'message': '需要登录'}), 401
        return redirect('/login')

    # --- 4. 权限判断（与全局钩子逻辑一致） ---
    is_subject_admin_path = (
        path.startswith('/admin/subjects') or
        path.startswith('/admin/api/subjects') or
        path.startswith('/admin/questions') or
        path == '/admin/types' or
        path == '/admin/download_template' or
        '/api/subjects' in path or
        '/api/questions' in path
    )
    is_notification_admin_path = (
        path.startswith('/admin/notifications') or
        path.startswith('/admin/api/notifications') or
        '/api/notifications' in path
    )

    if is_subject_admin_path:
        if not (is_admin or is_subject_admin):
            if path.startswith('/admin/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403
            return redirect('/')
    elif is_notification_admin_path:
        if not (is_admin or is_notification_admin):
            if path.startswith('/admin/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员或通知管理员权限'}), 403
            return redirect('/')
    elif not is_admin:
        if path.startswith('/admin/api'):
            return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
        return redirect('/')

    return None


def init_admin_module(app: Flask):
    """初始化管理后台模块"""
    from .routes.pages import admin_pages_bp
    from .routes.api import admin_api_bp
    from .routes.api_legacy import admin_api_legacy_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder=template_dir)

    # 为 admin 蓝图注册独立的权限检查钩子
    admin_bp.before_request(_check_admin_permission)

    admin_bp.register_blueprint(admin_pages_bp)
    admin_bp.register_blueprint(admin_api_bp, url_prefix='/api')
    # 向后兼容：注册旧路径的路由（/admin/types, /admin/questions）
    admin_bp.register_blueprint(admin_api_legacy_bp)
    app.register_blueprint(admin_bp)
