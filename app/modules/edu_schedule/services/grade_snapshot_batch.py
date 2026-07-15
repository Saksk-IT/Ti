# -*- coding: utf-8 -*-
"""从同一成绩刷新批次生成页面汇总。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.models.edu_schedule import EduGradeOverviewSnapshot, EduGradeSnapshot

from .grade_overview import (
    calculate_academic_year_weighted_averages,
    serialize_grade_overview_rows,
)


def summarize_grade_snapshot_batch(
    user_id: int,
    account_key: Optional[str],
    snapshots: List[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """将 GPA 与年度均分固定到已读取的成绩批次，避免并发刷新串批。"""
    academic_year_averages = calculate_academic_year_weighted_averages(snapshots)
    key = str(account_key or "").strip()
    if not key or not snapshots:
        return None, academic_year_averages

    latest_snapshot = max(
        snapshots,
        key=lambda item: (
            int(item.get("refresh_order") or 0),
            str(item.get("fetched_at") or ""),
            int(item.get("id") or 0),
        ),
    )
    refresh_id = str(latest_snapshot.get("refresh_id") or "").strip()
    rows = (
        EduGradeOverviewSnapshot.query
        .filter_by(user_id=int(user_id), jwxt_account_key=key)
        .order_by(
            EduGradeOverviewSnapshot.refresh_order.desc(),
            EduGradeOverviewSnapshot.fetched_at.desc(),
            EduGradeOverviewSnapshot.id.desc(),
        )
        .all()
    )
    if refresh_id:
        current_index = next(
            (index for index, row in enumerate(rows) if row.refresh_id == refresh_id),
            None,
        )
        if current_index is None:
            return None, academic_year_averages
        rows = rows[current_index:]
    else:
        cutoff = int(latest_snapshot.get("refresh_order") or 0)
        rows = [row for row in rows if int(row.refresh_order or 0) <= cutoff]
    return serialize_grade_overview_rows(rows), academic_year_averages


def load_grade_refresh_batch(
    user_id: int,
    account_key: str,
    refresh_id: str,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """按刷新标识读取任务自己发布的完整成绩批次。"""
    rows = (
        EduGradeSnapshot.query
        .filter_by(
            user_id=int(user_id),
            jwxt_account_key=str(account_key or "").strip(),
            refresh_id=str(refresh_id or "").strip(),
        )
        .order_by(EduGradeSnapshot.xnm.desc(), EduGradeSnapshot.xqm.desc(), EduGradeSnapshot.id.desc())
        .all()
    )
    snapshots = [
        {
            "id": row.id,
            "xnm": row.xnm,
            "xqm": row.xqm,
            "refresh_id": row.refresh_id,
            "refresh_order": int(row.refresh_order or 0),
            "term_label": row.term_label,
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            "payload": json.loads(row.payload_json or "{}"),
        }
        for row in rows
    ]
    overview, year_averages = summarize_grade_snapshot_batch(user_id, account_key, snapshots)
    return snapshots, overview, year_averages
