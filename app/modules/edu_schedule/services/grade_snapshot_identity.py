# -*- coding: utf-8 -*-
"""旧成绩快照的账号身份校验。"""

from __future__ import annotations

import json
from typing import Any, Dict

from .client import ScheduleAuthError


def validate_grade_identity(payload: Dict[str, Any], account: str) -> None:
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ScheduleAuthError("教务成绩为空，无法确认当前登录身份")
    if any(
        not isinstance(row, dict) or not str(row.get("xh") or "").strip()
        for row in rows
    ):
        raise ScheduleAuthError("教务成绩身份信息不完整")
    student_numbers = {str(row.get("xh") or "").strip() for row in rows}
    if student_numbers != {str(account or "").strip()}:
        raise ScheduleAuthError("教务成绩身份与当前绑定账号不一致")


def legacy_snapshot_payload_matches_account(
    normalized_payload_json: Any,
    raw_payload_json: Any,
    account: str,
) -> bool:
    """仅在规范化与原始成绩均明确属于同一账号时接受旧快照。"""
    expected_account = str(account or "").strip()
    if not expected_account:
        return False
    try:
        normalized = json.loads(str(normalized_payload_json or ""))
        raw_payload = json.loads(str(raw_payload_json or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(normalized, dict) or not isinstance(raw_payload, dict):
        return False

    student = normalized.get("student")
    normalized_account = (
        str(student.get("student_no") or "").strip()
        if isinstance(student, dict)
        else ""
    )
    if normalized_account != expected_account:
        return False

    rows = raw_payload.get("items")
    if not isinstance(rows, list) or not rows:
        return False
    raw_accounts = set()
    for row in rows:
        if not isinstance(row, dict):
            return False
        row_account = str(row.get("xh") or "").strip()
        if not row_account:
            return False
        raw_accounts.add(row_account)
    return raw_accounts == {expected_account}
