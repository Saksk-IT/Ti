# -*- coding: utf-8 -*-
"""教务成绩 JSON 规范化。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> Optional[float]:
    text = _text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _term_label(xnm: str, xqm: str, year_name: str, term_name: str) -> str:
    if year_name and term_name:
        return f"{year_name} 第{term_name}学期"
    mapping = {"3": "第一学期", "12": "第二学期", "16": "第三学期"}
    if xnm:
        next_year = str(int(xnm) + 1) if xnm.isdigit() else ""
        return f"{xnm}-{next_year} {mapping.get(xqm, xqm)}".strip()
    return mapping.get(xqm, xqm)


def _grade_item(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "course_code": _text(row.get("kch") or row.get("kch_id")),
        "course_name": _text(row.get("kcmc")),
        "course_type": _text(row.get("kcxzmc") or row.get("kklxdm")),
        "course_tag": _text(row.get("kcbj") or row.get("kcgsmc")),
        "teacher": _text(row.get("jsxm")),
        "department": _text(row.get("kkbmmc")),
        "credits": _text(row.get("xf")),
        "hours": _text(row.get("zxs") or row.get("rwzxs")),
        "score": _text(row.get("cj")),
        "converted_score": _text(row.get("bfzcj")),
        "grade_point": _text(row.get("jd")),
        "credit_grade_point": _text(row.get("xfjd")),
        "assessment": _text(row.get("khfsmc")),
        "exam_type": _text(row.get("ksxz")),
        "note": _text(row.get("cjbz")),
    }


def normalize_grade_payload(payload: Dict[str, Any], xnm: str = "", xqm: str = "") -> Dict[str, Any]:
    """将正方成绩接口返回值整理成前端稳定结构。"""
    rows = payload.get("items") if isinstance(payload.get("items"), list) else []
    dict_rows = [row for row in rows if isinstance(row, dict)]
    first = dict_rows[0] if dict_rows else {}

    term_xnm = _text(first.get("xnm") or xnm)
    term_xqm = _text(first.get("xqm") or xqm)
    year_name = _text(first.get("xnmmc")) or (f"{term_xnm}-{int(term_xnm) + 1}" if term_xnm.isdigit() else "")
    term_name = _text(first.get("xqmmc"))

    grades = [_grade_item(row) for row in dict_rows if _text(row.get("kcmc"))]
    total_credits = 0.0
    graded_credits = 0.0
    total_grade_points = 0.0
    for row in grades:
        credits = _number(row.get("credits"))
        grade_point = _number(row.get("grade_point"))
        credit_grade_point = _number(row.get("credit_grade_point"))
        if credits is not None:
            total_credits += credits
        if credits is not None and grade_point is not None:
            graded_credits += credits
        if credit_grade_point is not None:
            total_grade_points += credit_grade_point

    gpa = round(total_grade_points / graded_credits, 2) if graded_credits else 0.0

    return {
        "student": {
            "name": _text(first.get("xm")),
            "student_no": _text(first.get("xh")),
            "class_name": _text(first.get("bj")),
            "major_name": _text(first.get("zymc")),
            "college_name": _text(first.get("jgmc") or first.get("zsxymc")),
        },
        "term": {
            "xnm": term_xnm,
            "xqm": term_xqm,
            "year_name": year_name,
            "term_name": term_name,
            "label": _term_label(term_xnm, term_xqm, year_name, term_name),
        },
        "summary": {
            "course_count": len(grades),
            "total_credits": round(total_credits, 2),
            "graded_credits": round(graded_credits, 2),
            "total_grade_points": round(total_grade_points, 2),
            "gpa": gpa,
        },
        "grades": grades,
    }
