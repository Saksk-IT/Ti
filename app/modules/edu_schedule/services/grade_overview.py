# -*- coding: utf-8 -*-
"""累计学分绩点解析与估算。"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from typing import Any, Dict, Optional


_GPA_QUANTUM = Decimal("0.01")
_CREDIT_GRADE_POINT_TOLERANCE = Decimal("0.05")
_MIN_GPA = Decimal("0")
_MAX_GPA = Decimal("5")
_OFFICIAL_GPA_PATTERN = re.compile(
    r"当前所有课程平均学分绩点[（(]GPA[）)][:：]([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)


class GradeOverviewParseError(ValueError):
    """官方累计 GPA 页面无法安全解析。"""


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data:
            self._parts.append(data)

    def visible_text(self) -> str:
        return " ".join(self._parts)


def _decimal(value: Any) -> Optional[Decimal]:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _quantize_gpa(value: Decimal) -> Decimal:
    return value.quantize(_GPA_QUANTUM, rounding=ROUND_HALF_UP)


def is_complete_grade_payload(payload: Dict[str, Any]) -> bool:
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return False
    if any(
        not isinstance(row, dict)
        or not str(row.get("xnm") or "").strip()
        or not str(row.get("xqm") or "").strip()
        for row in rows
    ):
        return False
    total_result = payload.get("totalResult")
    if total_result is None:
        return True
    try:
        expected_row_count = int(str(total_result).strip())
    except (TypeError, ValueError):
        return False
    return expected_row_count >= 0 and expected_row_count == len(rows)


def parse_official_gpa_html(html_text: str) -> Decimal:
    """仅从带有固定中文标签的可见文本中提取官方累计 GPA。"""
    parser = _VisibleTextParser()
    try:
        parser.feed(str(html_text or ""))
        parser.close()
    except Exception as exc:
        raise GradeOverviewParseError("官方 GPA 页面格式不正确") from exc

    compact_text = re.sub(r"\s+", "", parser.visible_text())
    match = _OFFICIAL_GPA_PATTERN.search(compact_text)
    if not match:
        raise GradeOverviewParseError("官方 GPA 页面未找到累计绩点")

    value = _decimal(match.group(1))
    if value is None or value < _MIN_GPA or value > _MAX_GPA:
        raise GradeOverviewParseError("官方 GPA 数值超出合理范围")
    return _quantize_gpa(value)


def calculate_cumulative_gpa(payload: Dict[str, Any]) -> Optional[Decimal]:
    """基于全量原始成绩按学分加权估算累计 GPA。"""
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not is_complete_grade_payload(payload):
        return None

    total_credits = Decimal("0")
    total_credit_grade_points = Decimal("0")
    for row in rows:
        if not isinstance(row, dict):
            continue
        credits = _decimal(row.get("xf"))
        grade_point = _decimal(row.get("jd"))
        if (
            credits is None
            or credits <= 0
            or grade_point is None
            or grade_point < _MIN_GPA
            or grade_point > _MAX_GPA
        ):
            continue
        expected_credit_grade_point = credits * grade_point
        credit_grade_point = _decimal(row.get("xfjd"))
        if credit_grade_point is None:
            credit_grade_point = expected_credit_grade_point
        if (
            credit_grade_point < 0
            or credit_grade_point > credits * _MAX_GPA
            or abs(credit_grade_point - expected_credit_grade_point)
            > _CREDIT_GRADE_POINT_TOLERANCE
        ):
            continue
        total_credits += credits
        total_credit_grade_points += credit_grade_point

    if total_credits <= 0:
        return None
    result = total_credit_grade_points / total_credits
    if result < _MIN_GPA or result > _MAX_GPA:
        return None
    return _quantize_gpa(result)


def calculate_academic_year_weighted_averages(
    snapshots: list[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """按学年汇总有绩点课程的百分制学分加权平均分。"""
    groups: Dict[str, Dict[str, Any]] = {}
    seen_terms: set[tuple[str, str]] = set()
    for snapshot in snapshots:
        payload = snapshot.get("payload") if isinstance(snapshot, dict) else None
        if not isinstance(payload, dict):
            continue
        term = payload.get("term")
        grades = payload.get("grades")
        if not isinstance(term, dict) or not isinstance(grades, list):
            continue
        xnm = str(term.get("xnm") or "").strip()
        xqm = str(term.get("xqm") or "").strip()
        if not xnm or not xqm or (xnm, xqm) in seen_terms:
            continue
        seen_terms.add((xnm, xqm))
        year_name = str(term.get("year_name") or "").strip()
        if not year_name and xnm.isdigit():
            year_name = f"{xnm}-{int(xnm) + 1}"
        current = groups.get(
            xnm,
            {
                "xnm": xnm,
                "year_name": year_name or xnm,
                "weighted_score_sum": Decimal("0"),
                "included_credits": Decimal("0"),
                "included_course_count": 0,
            },
        )
        next_group = current
        for grade in grades:
            if not isinstance(grade, dict):
                continue
            grade_point = _decimal(grade.get("grade_point"))
            credits = _decimal(grade.get("credits"))
            converted_score = _decimal(grade.get("converted_score"))
            if (
                grade_point is None
                or grade_point < _MIN_GPA
                or grade_point > _MAX_GPA
                or credits is None
                or credits <= 0
                or converted_score is None
                or converted_score < 0
                or converted_score > 100
            ):
                continue
            next_group = {
                **next_group,
                "weighted_score_sum": (
                    next_group["weighted_score_sum"] + credits * converted_score
                ),
                "included_credits": next_group["included_credits"] + credits,
                "included_course_count": next_group["included_course_count"] + 1,
            }
        groups = {**groups, xnm: next_group}

    valid_groups = [
        group
        for group in groups.values()
        if group["included_credits"] > 0 and group["included_course_count"] > 0
    ]
    ordered_xnm = sorted(groups, key=_academic_year_sort_key)
    year_numbers = {xnm: index + 1 for index, xnm in enumerate(ordered_xnm)}
    results = [
        {
            "xnm": group["xnm"],
            "year_name": group["year_name"],
            "year_number": year_numbers[group["xnm"]],
            "weighted_average": float(
                _quantize_gpa(
                    group["weighted_score_sum"] / group["included_credits"]
                )
            ),
            "included_credits": float(group["included_credits"]),
            "included_course_count": int(group["included_course_count"]),
        }
        for group in valid_groups
    ]
    return sorted(results, key=lambda item: _academic_year_sort_key(item["xnm"]), reverse=True)


def _academic_year_sort_key(value: str) -> tuple[int, str]:
    text = str(value or "").strip()
    return (int(text), text) if text.isdigit() else (-1, text)


def serialize_grade_overview_rows(rows: list[Any]) -> Optional[Dict[str, Any]]:
    """将同一账号的累计 GPA 快照整理成稳定的前端结构。"""
    if not rows:
        return None
    latest = rows[0]
    official_row = next((row for row in rows if row.official_gpa is not None), None)
    source_row = official_row or latest
    display_value = source_row.official_gpa if official_row else latest.calculated_gpa
    if display_value is None:
        return None
    is_cached = bool(official_row and official_row.id != latest.id)
    return {
        "display_gpa": float(display_value),
        "official_gpa": (
            float(official_row.official_gpa)
            if official_row and official_row.official_gpa is not None
            else None
        ),
        "calculated_gpa": (
            float(latest.calculated_gpa)
            if latest.calculated_gpa is not None
            else None
        ),
        "source": "official" if official_row else "calculated",
        "source_label": (
            "教务系统官方（缓存）"
            if is_cached
            else "教务系统官方"
            if official_row
            else "系统估算"
        ),
        "is_cached": is_cached,
        "refresh_id": source_row.refresh_id,
        "latest_refresh_id": latest.refresh_id,
        "official_refresh_id": official_row.refresh_id if official_row else None,
        "calculated_refresh_id": latest.refresh_id if latest.calculated_gpa is not None else None,
        "fetched_at": source_row.fetched_at.isoformat() if source_row.fetched_at else None,
        "official_fetched_at": (
            official_row.fetched_at.isoformat()
            if official_row and official_row.fetched_at
            else None
        ),
        "calculated_fetched_at": (
            latest.fetched_at.isoformat()
            if latest.calculated_gpa is not None and latest.fetched_at
            else None
        ),
    }
