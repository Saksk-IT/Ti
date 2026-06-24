# -*- coding: utf-8 -*-
"""教务课表页面路由。"""

from datetime import date

from flask import Blueprint, render_template

from app.core.utils.decorators import login_required


edu_schedule_pages_bp = Blueprint("edu_schedule_pages", __name__)


def _default_academic_year(today: date | None = None) -> int:
    current = today or date.today()
    return current.year if current.month >= 9 else current.year - 1


def _academic_year_options() -> list[dict[str, object]]:
    default_year = _default_academic_year()
    start_year = default_year - 6
    end_year = default_year + 2
    return [
        {
            "value": str(year),
            "label": f"{year}~{year + 1}",
            "selected": year == default_year,
        }
        for year in range(start_year, end_year + 1)
    ]


def _render_campus_page(template_name: str):
    return render_template(
        template_name,
        academic_year_options=_academic_year_options(),
    )


@edu_schedule_pages_bp.route("/edu-schedule")
@login_required
def edu_schedule_page():
    return _render_campus_page("edu_schedule/index.html")


@edu_schedule_pages_bp.route("/edu-grades")
@login_required
def edu_grades_page():
    return _render_campus_page("edu_schedule/grades.html")
