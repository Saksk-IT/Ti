# -*- coding: utf-8 -*-
"""主页面路由"""
from flask import Blueprint
from .pages import main_pages_bp
from .api import main_api_bp

# 创建主蓝图（不指定template_folder，在模块初始化时处理）
main_bp = Blueprint('main', __name__)

# 注册子蓝图
main_bp.register_blueprint(main_pages_bp)
main_bp.register_blueprint(main_api_bp)



