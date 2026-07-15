# -*- coding: utf-8 -*-
"""成绩查询任务的账号绑定与缓存隔离。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .grade_snapshot_batch import summarize_grade_snapshot_batch
from .schedule_service import EduScheduleService


def grade_task_account_key(user_id: int, username: Optional[str]) -> Optional[str]:
    account = str(username or "").strip()
    if account:
        return EduScheduleService.account_key(account)
    return EduScheduleService.get_bound_account_key(user_id)


def grade_task_matches_bound_account(state: Dict[str, Any], user_id: int) -> bool:
    if state.get("kind") != "grades":
        return True
    task_account_key = str(state.get("account_key") or "")
    task_credential_key = str(state.get("credential_key") or "")
    account_mode = str(state.get("account_mode") or "bound")
    bound_account_key = EduScheduleService.get_bound_account_key(user_id)
    bound_credential_key = EduScheduleService.get_bound_credential_key(user_id)
    if account_mode == "remember":
        prior_credential_key = state.get("prior_bound_credential_key")
        return bool(task_account_key) and bool(task_credential_key) and (
            bound_credential_key == task_credential_key
            or bound_credential_key == prior_credential_key
        )
    if not bound_account_key:
        return bool(task_account_key) and bool(task_credential_key) and account_mode == "temporary"
    if not task_account_key or task_account_key != bound_account_key:
        return False
    if account_mode == "temporary":
        return bool(task_credential_key)
    if account_mode != "bound":
        return False
    return bool(task_credential_key) and task_credential_key == bound_credential_key


def grade_task_cached_data(
    user_id: int,
    state: Dict[str, Any],
    *,
    upstream_authenticated: bool = False,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    if not grade_task_matches_bound_account(state, user_id):
        return [], None, []
    account_key = str(state.get("account_key") or "")
    if not account_key:
        return [], None, []
    account_mode = str(state.get("account_mode") or "bound")
    if account_mode in {"temporary", "remember"} and not upstream_authenticated:
        return [], None, []
    snapshots = (
        EduScheduleService.list_grade_snapshots_for_bound_account_key(
            user_id,
            account_key,
        )
        if account_mode == "bound"
        else EduScheduleService.list_grade_snapshots_by_account_key(
            user_id,
            account_key,
        )
    )
    overview, year_averages = summarize_grade_snapshot_batch(
        user_id,
        account_key,
        snapshots,
    )
    return snapshots, overview, year_averages
