# -*- coding: utf-8 -*-
"""教务课表 JSON 规范化。"""

from __future__ import annotations

from typing import Any, Dict, List


_DAY_NAMES = {
    "1": "星期一",
    "2": "星期二",
    "3": "星期三",
    "4": "星期四",
    "5": "星期五",
    "6": "星期六",
    "7": "星期日",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _course_item(row: Dict[str, Any]) -> Dict[str, Any]:
    location = "".join(part for part in [_text(row.get("lh")), _text(row.get("cdmc"))] if part)
    return {
        "course_name": _text(row.get("kcmc")),
        "teacher": _text(row.get("xm") or row.get("jsxm")),
        "weeks": _text(row.get("zcd") or row.get("qsjsz")),
        "location": location,
        "campus": _text(row.get("xqmc")),
        "credits": _text(row.get("xf")),
        "assessment": _text(row.get("khfsmc")),
        "section": _text(row.get("jc") or row.get("jcs")),
        "section_order": _section_order(_text(row.get("jcor") or row.get("jcs") or row.get("jc"))),
    }


def _section_order(section: str) -> int:
    head = (section or "").split("-", 1)[0].replace("节", "").strip()
    return int(head) if head.isdigit() else 999


def _day_name(row: Dict[str, Any]) -> str:
    day = _text(row.get("xqj"))
    return _text(row.get("xqjmc")) or _DAY_NAMES.get(day, day)


def normalize_schedule_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """将教务接口原始 JSON 规范化成页面和 API 统一使用的结构。"""
    xsxx = payload.get("xsxx") if isinstance(payload.get("xsxx"), dict) else {}
    courses = payload.get("kbList") if isinstance(payload.get("kbList"), list) else []
    practice = payload.get("sjkList") if isinstance(payload.get("sjkList"), list) else []

    week_table: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    flat_courses: List[Dict[str, Any]] = []

    for row in courses:
        if not isinstance(row, dict):
            continue
        day_name = _day_name(row)
        section = _text(row.get("jc") or row.get("jcs"))
        if not day_name or not section:
            continue
        item = _course_item(row)
        flat_courses.append({"day": day_name, **item})
        week_table.setdefault(day_name, {}).setdefault(section, []).append(item)

    for day_items in week_table.values():
        for items in day_items.values():
            items.sort(key=lambda item: int(item.get("section_order") or 999))

    practice_courses = [
        _course_item(row)
        for row in practice
        if isinstance(row, dict) and _text(row.get("kcmc"))
    ]

    xnm = _text(xsxx.get("XNM") or payload.get("xnm"))
    xqm = _text(xsxx.get("XQM") or payload.get("xqm"))
    year_name = _text(xsxx.get("XNMC")) or (f"{xnm}-{int(xnm) + 1}" if xnm.isdigit() else "")
    term_name = _text(xsxx.get("XQMMC"))

    return {
        "student": {
            "name": _text(xsxx.get("XM")),
            "student_no": _text(xsxx.get("XH")),
            "class_name": _text(xsxx.get("BJMC")),
            "major_name": _text(xsxx.get("ZYMC")),
        },
        "term": {
            "xnm": xnm,
            "xqm": xqm,
            "year_name": year_name,
            "term_name": term_name,
            "label": _term_label(xnm, xqm, year_name, term_name),
        },
        "courses": sorted(flat_courses, key=lambda item: (_day_sort(item.get("day")), item.get("section_order", 999))),
        "week_table": week_table,
        "practice_courses": practice_courses,
    }


def _day_sort(day_name: str) -> int:
    for idx, name in enumerate(_DAY_NAMES.values(), start=1):
        if day_name == name:
            return idx
    return 99


def _term_label(xnm: str, xqm: str, year_name: str, term_name: str) -> str:
    if year_name and term_name:
        return f"{year_name} 第{term_name}学期"
    mapping = {"3": "第一学期", "12": "第二学期", "16": "第三学期"}
    if xnm:
        next_year = str(int(xnm) + 1) if xnm.isdigit() else ""
        return f"{xnm}-{next_year} {mapping.get(xqm, xqm)}".strip()
    return mapping.get(xqm, xqm)
