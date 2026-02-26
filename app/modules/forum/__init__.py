# -*- coding: utf-8 -*-
"""论坛模块"""
import os
from flask import Flask, Blueprint


def init_forum_module(app: Flask):
    """初始化论坛模块"""
    from .routes.pages import forum_pages_bp
    from .routes.api import forum_api_bp
    from .routes.api_follow import forum_user_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    forum_bp = Blueprint('forum', __name__, template_folder=template_dir)
    forum_bp.register_blueprint(forum_pages_bp)
    forum_bp.register_blueprint(forum_api_bp, url_prefix='/api/forum')
    forum_bp.register_blueprint(forum_user_api_bp, url_prefix='/api')
    app.register_blueprint(forum_bp)

    # 确保论坛图片上传目录存在
    forum_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'forum')
    os.makedirs(forum_upload_dir, exist_ok=True)
