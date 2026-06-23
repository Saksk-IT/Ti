# -*- coding: utf-8 -*-
"""教务课表查询模块。"""

import os

from flask import Blueprint, Flask


def init_edu_schedule_module(app: Flask):
    from .routes.api import edu_schedule_api_bp
    from .routes.pages import edu_schedule_pages_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, "templates")

    edu_schedule_bp = Blueprint("edu_schedule", __name__, template_folder=template_dir)
    edu_schedule_bp.register_blueprint(edu_schedule_pages_bp)
    edu_schedule_bp.register_blueprint(edu_schedule_api_bp, url_prefix="/api")
    app.register_blueprint(edu_schedule_bp)
