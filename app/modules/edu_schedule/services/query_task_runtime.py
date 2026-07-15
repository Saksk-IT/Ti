# -*- coding: utf-8 -*-
"""教务查询任务的重试与结果辅助函数。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import requests

from .client import ScheduleAuthError, ScheduleClientError


_BACKOFF_SECONDS = (5, 20, 60, 120, 300)


def results_from_snapshots(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item.get("payload") for item in snapshots if isinstance(item.get("payload"), dict)]


def retrying_message(attempt: int, has_snapshot: bool) -> str:
    if has_snapshot:
        return f"教务系统繁忙，当前展示上次成功结果，后台会继续自动重试（第 {attempt} 次未成功）"
    return f"教务系统繁忙，后台会继续自动重试（第 {attempt} 次未成功）"


def backoff_seconds_for(attempt: int, delays=_BACKOFF_SECONDS) -> int:
    index = min(max(0, int(attempt) - 1), len(delays) - 1)
    return int(delays[index])


def is_upstream_busy(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if exc.__class__.__name__ in {"ReadTimeout", "ConnectTimeout", "Timeout"}:
        return True
    return isinstance(exc, ScheduleClientError) and not isinstance(exc, ScheduleAuthError)


def stop_for_binding_change(
    state: Dict[str, Any],
    *,
    message: str,
    finished_at: str,
    save_state: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    stopped_state = save_state(
        {
            **state,
            "status": "cancelled",
            "message": message,
            "results": [],
            "snapshots": [],
            "grade_overview": None,
            "academic_year_averages": [],
            "challenge": None,
            "finished_at": finished_at,
        }
    )
    if stopped_state.get("publish_claimed"):
        return save_state({**stopped_state, "status": "failed", "message": message})
    return stopped_state
