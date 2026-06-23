# -*- coding: utf-8 -*-
"""教务课表页面路由。"""

from flask import Blueprint, render_template

from app.core.utils.decorators import login_required


edu_schedule_pages_bp = Blueprint("edu_schedule_pages", __name__)


@edu_schedule_pages_bp.route("/edu-schedule")
@login_required
def edu_schedule_page():
    return render_template("edu_schedule/index.html")
