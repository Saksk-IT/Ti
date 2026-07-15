# -*- coding: utf-8 -*-
"""教务查询后台任务服务。"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from flask import current_app, has_app_context

from app.core.utils.redis_utils import get_redis_connection, redis_get_json, redis_set_json

from .grade_query_task_cache import (
    grade_task_account_key,
    grade_task_cached_data,
    grade_task_matches_bound_account,
)
from .query_task_coordination import (
    QueryTaskCoordinationError,
    allocate_refresh_order,
    load_state as load_redis_state,
    register_or_coalesce,
    transition_state,
)
from .query_task_runtime import (
    backoff_seconds_for,
    is_upstream_busy,
    results_from_snapshots,
    retrying_message,
    stop_for_binding_change,
)
from .schedule_service import EduScheduleError, EduScheduleService, user_safe_error
from .webvpn_refresh import (
    WEBVPN_REFRESH_REQUIRED_MESSAGE,
    WebVPNSessionRefreshService,
    should_start_webvpn_refresh,
)


_QUERY_TASK_TTL_SECONDS = 1800
_QUERY_TASK_MAX_ATTEMPTS = None
_QUERY_TASK_BACKOFF_SECONDS = (5, 20, 60, 120, 300)
_QUERY_TASK_KEY_PREFIX = "edu_schedule:query_task:"
_QUERY_TASK_USER_KEY_PREFIX = "edu_schedule:user_query_tasks:"
_QUERY_TASK_DEDUPE_KEY_PREFIX = "edu_schedule:query_dedupe:"
_QUERY_TASK_REFRESH_ORDER_KEY_PREFIX = "edu_schedule:grade_refresh_order:"
_QUERY_TASK_LOCK = threading.Lock()
_QUERY_TASKS: Dict[str, Dict[str, Any]] = {}
_QUERY_TASK_JOBS: Dict[str, Dict[str, Any]] = {}
_QUERY_TASK_DEDUPES: Dict[str, str] = {}
_QUERY_TASK_USER_TASKS: Dict[int, List[str]] = {}
_QUERY_TASK_REFRESH_ORDERS: Dict[str, int] = {}
_QUERY_TASK_ACTIVE_STATUSES = {"pending", "running", "retrying", "webvpn_refresh_required"}
_QUERY_TASK_DEDUPE_STATUSES = {"pending", "running", "retrying"}
_sleep = time.sleep


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_key(task_id: str) -> str:
    return f"{_QUERY_TASK_KEY_PREFIX}{task_id}"


def _user_tasks_key(user_id: int) -> str:
    return f"{_QUERY_TASK_USER_KEY_PREFIX}{int(user_id)}"


def _redis_dedupe_key(dedupe_key: str) -> str:
    return f"{_QUERY_TASK_DEDUPE_KEY_PREFIX}{dedupe_key}"


def _refresh_order_key(user_id: int, account_key: Optional[str]) -> str:
    return (
        f"{_QUERY_TASK_REFRESH_ORDER_KEY_PREFIX}{int(user_id)}:"
        f"{str(account_key or 'schedule')}"
    )


def _next_memory_refresh_order(user_id: int, account_key: Optional[str]) -> int:
    key = _refresh_order_key(user_id, account_key)
    now_value = time.time_ns() // 1000
    with _QUERY_TASK_LOCK:
        previous = int(_QUERY_TASK_REFRESH_ORDERS.get(key) or 0)
        next_value = max(now_value, previous + 1)
        _QUERY_TASK_REFRESH_ORDERS[key] = next_value
    return next_value


def _normalize_terms(terms: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    return [{"xnm": str(term["xnm"]), "xqm": str(term["xqm"])} for term in terms]


def _dedupe_key(
    kind: str,
    user_id: int,
    terms: List[Dict[str, str]],
    account_key: Optional[str] = None,
    account_mode: Optional[str] = None,
    credential_key: Optional[str] = None,
) -> str:
    dedupe_terms = [] if kind == "grades" else terms
    payload = json.dumps(
        {
            "kind": kind,
            "user_id": int(user_id),
            "terms": dedupe_terms,
            "account_key": account_key if kind == "grades" else None,
            "account_mode": account_mode if kind == "grades" else None,
            "credential_key": credential_key if kind == "grades" else None,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cleanup_memory_tasks(now: float) -> None:
    expired_ids = [
        task_id
        for task_id, state in _QUERY_TASKS.items()
        if float(state.get("expires_at") or 0) <= now
    ]
    for task_id in expired_ids:
        _QUERY_TASKS.pop(task_id, None)
        _QUERY_TASK_JOBS.pop(task_id, None)
    for key, task_id in list(_QUERY_TASK_DEDUPES.items()):
        if task_id not in _QUERY_TASKS:
            _QUERY_TASK_DEDUPES.pop(key, None)
    for user_id, task_ids in list(_QUERY_TASK_USER_TASKS.items()):
        next_task_ids = [task_id for task_id in task_ids if task_id in _QUERY_TASKS]
        if next_task_ids:
            _QUERY_TASK_USER_TASKS[user_id] = next_task_ids
        else:
            _QUERY_TASK_USER_TASKS.pop(user_id, None)


def _save_state(state: Dict[str, Any]) -> Dict[str, Any]:
    next_state = {
        **state,
        "updated_at": _now_iso(),
        "expires_at": time.time() + _QUERY_TASK_TTL_SECONDS,
    }
    task_id = str(next_state["task_id"])
    if next_state.get("coordination_mode") == "redis":
        connection = get_redis_connection()
        if connection is None:
            raise QueryTaskCoordinationError("Redis 教务查询任务协调不可用")
        persisted_state = transition_state(
            connection,
            task_key=_task_key(task_id),
            dedupe_key=_redis_dedupe_key(str(next_state.get("dedupe_key") or "")),
            state=next_state,
            ttl_seconds=_QUERY_TASK_TTL_SECONDS,
        )
        with _QUERY_TASK_LOCK:
            _cleanup_memory_tasks(time.time())
            _QUERY_TASKS[task_id] = dict(persisted_state)
        return persisted_state

    with _QUERY_TASK_LOCK:
        _cleanup_memory_tasks(time.time())
        current_state = _QUERY_TASKS.get(task_id)
        if current_state:
            current_status = str(current_state.get("status") or "")
            next_status = str(next_state.get("status") or "")
            if current_status in {"cancelled", "succeeded", "failed"}:
                return dict(current_state)
            if (
                current_state.get("publish_claimed")
                and next_status not in {"succeeded", "failed"}
            ):
                return dict(current_state)
        _QUERY_TASKS[task_id] = next_state
        if next_state.get("publish_claimed"):
            dedupe_key = str(next_state.get("dedupe_key") or "")
            if _QUERY_TASK_DEDUPES.get(dedupe_key) == task_id:
                _QUERY_TASK_DEDUPES.pop(dedupe_key, None)
    return next_state


def _load_state(task_id: str) -> Optional[Dict[str, Any]]:
    with _QUERY_TASK_LOCK:
        _cleanup_memory_tasks(time.time())
        memory_state = _QUERY_TASKS.get(task_id)
    connection = get_redis_connection()
    if connection is not None:
        redis_state = load_redis_state(connection, _task_key(task_id))
        if redis_state is not None:
            with _QUERY_TASK_LOCK:
                _QUERY_TASKS[task_id] = dict(redis_state)
            return redis_state
        if isinstance(memory_state, dict) and memory_state.get("coordination_mode") == "redis":
            return None
    elif isinstance(memory_state, dict) and memory_state.get("coordination_mode") == "redis":
        return None
    return dict(memory_state) if isinstance(memory_state, dict) else None


def _store_job(task_id: str, job: Dict[str, Any]) -> None:
    with _QUERY_TASK_LOCK:
        _QUERY_TASK_JOBS[task_id] = dict(job)


def _load_job(task_id: str) -> Optional[Dict[str, Any]]:
    with _QUERY_TASK_LOCK:
        job = _QUERY_TASK_JOBS.get(task_id)
    return dict(job) if isinstance(job, dict) else None


def _unique_task_ids(task_ids: Iterable[str]) -> List[str]:
    seen = set()
    items: List[str] = []
    for raw_task_id in task_ids:
        task_id = str(raw_task_id or "").strip()
        if not task_id or task_id in seen:
            continue
        seen.add(task_id)
        items.append(task_id)
    return items


def _load_user_task_ids(user_id: int) -> List[str]:
    redis_ids = redis_get_json(_user_tasks_key(user_id))
    with _QUERY_TASK_LOCK:
        _cleanup_memory_tasks(time.time())
        memory_ids = list(_QUERY_TASK_USER_TASKS.get(int(user_id), []))
    if isinstance(redis_ids, list):
        return _unique_task_ids([*redis_ids, *memory_ids])
    return _unique_task_ids(memory_ids)


def _index_task(user_id: int, task_id: str) -> None:
    next_task_ids = _unique_task_ids([str(task_id), *_load_user_task_ids(user_id)])[:10]
    with _QUERY_TASK_LOCK:
        _QUERY_TASK_USER_TASKS[int(user_id)] = list(next_task_ids)
    redis_set_json(_user_tasks_key(user_id), next_task_ids, ttl_seconds=_QUERY_TASK_TTL_SECONDS)


def _public_state(state: Dict[str, Any]) -> Dict[str, Any]:
    blocked_keys = {
        "expires_at",
        "dedupe_key",
        "owner_user_id",
        "account_key",
        "account_mode",
        "credential_key",
        "prior_bound_credential_key",
        "coordination_mode",
        "refresh_order",
        "publish_claimed",
        "error",
        "error_type",
    }
    return {key: value for key, value in state.items() if key not in blocked_keys}


def _task_cached_data(
    kind: str,
    user_id: int,
    terms: List[Dict[str, str]],
    state: Dict[str, Any],
    *,
    upstream_authenticated: bool = False,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    if kind == "grades":
        return grade_task_cached_data(
            user_id,
            state,
            upstream_authenticated=upstream_authenticated,
        )
    return EduScheduleService.list_snapshots_for_terms(user_id, terms), None, []


def _discard_task_grade_refresh(kind: str, user_id: int, task_id: str) -> None:
    if kind == "grades":
        EduScheduleService.discard_grade_refresh(user_id, task_id)


def _cancelled_state(task_id: str) -> Optional[Dict[str, Any]]:
    state = _load_state(task_id)
    if state and state.get("status") == "cancelled":
        return _public_state(state)
    return None


def _claim_task_publish(task_id: str) -> bool:
    state = _load_state(task_id)
    if not state or state.get("status") not in {"running", "retrying"}:
        return False
    claimed_state = _save_state(
        {
            **state,
            "publish_claimed": True,
            "message": "成绩已获取，正在保存最新结果",
        }
    )
    return bool(
        claimed_state.get("publish_claimed")
        and claimed_state.get("status") in {"running", "retrying"}
    )


class EduScheduleQueryTaskService:
    """轻量级教务查询任务队列，优先用 Redis 保存状态，进程内线程执行。"""

    @staticmethod
    def enqueue(
        kind: str,
        user_id: int,
        terms: Iterable[Dict[str, str]],
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        remember: bool = False,
        autostart: bool = True,
    ) -> Dict[str, Any]:
        kind = str(kind or "").strip()
        if kind not in {"schedule", "grades"}:
            raise ValueError("教务查询类型不正确")
        user_id = int(user_id)
        normalized_terms = _normalize_terms(terms)
        if not (username and password) and not EduScheduleService.credential_status(user_id).get("has_credentials"):
            raise EduScheduleError("请先填写教务账号和密码")

        job_username = username
        job_password = password
        job_remember = bool(remember)
        prior_bound_credential_key = (
            EduScheduleService.get_bound_credential_key(user_id)
            if kind == "grades"
            else None
        )

        account_key = grade_task_account_key(user_id, username) if kind == "grades" else None
        account_mode = (
            "remember"
            if kind == "grades" and username and remember
            else "temporary"
            if kind == "grades" and username
            else "bound"
            if kind == "grades"
            else None
        )
        credential_key = (
            EduScheduleService.query_credential_key(username, password)
            if kind == "grades" and username and password
            else EduScheduleService.get_bound_credential_key(user_id)
            if kind == "grades"
            else None
        )
        if kind == "grades" and username and not remember:
            bound_account_key = EduScheduleService.get_bound_account_key(user_id)
            if bound_account_key and account_key != bound_account_key:
                raise EduScheduleError("临时教务账号与当前绑定账号不一致，请先更新账号绑定")

        dedupe_key = _dedupe_key(
            kind,
            user_id,
            normalized_terms,
            account_key,
            account_mode,
            credential_key,
        )
        connection = get_redis_connection()
        coordination_mode = "redis" if connection is not None else "memory"
        refresh_order = 0
        if kind == "grades":
            refresh_order = (
                allocate_refresh_order(
                    connection,
                    _refresh_order_key(user_id, account_key),
                    _QUERY_TASK_TTL_SECONDS,
                )
                if connection is not None
                else _next_memory_refresh_order(user_id, account_key)
            )
        task_id = secrets.token_urlsafe(18)
        now = time.time()
        state = {
            "task_id": task_id,
            "kind": kind,
            "account_key": account_key,
            "account_mode": account_mode,
            "credential_key": credential_key,
            "prior_bound_credential_key": prior_bound_credential_key,
            "owner_user_id": user_id,
            "terms": normalized_terms,
            "status": "pending",
            "message": "已提交后台查询，正在排队",
            "attempt": 0,
            "max_attempts": _QUERY_TASK_MAX_ATTEMPTS,
            "results": [],
            "snapshots": [],
            "grade_overview": None,
            "academic_year_averages": [],
            "credential": EduScheduleService.credential_status(user_id),
            "error": "",
            "error_type": "",
            "challenge": None,
            "coalesced": False,
            "coordination_mode": coordination_mode,
            "refresh_order": refresh_order,
            "publish_claimed": False,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "finished_at": None,
            "expires_at": now + _QUERY_TASK_TTL_SECONDS,
            "dedupe_key": dedupe_key,
        }
        snapshots, initial_grade_overview, initial_year_averages = _task_cached_data(
            kind,
            user_id,
            normalized_terms,
            state,
        )
        state = {
            **state,
            "results": results_from_snapshots(snapshots),
            "snapshots": snapshots,
            "grade_overview": initial_grade_overview,
            "academic_year_averages": initial_year_averages,
        }
        if connection is not None:
            created, persisted_state = register_or_coalesce(
                connection,
                dedupe_key=_redis_dedupe_key(dedupe_key),
                task_key=_task_key(task_id),
                task_key_prefix=_QUERY_TASK_KEY_PREFIX,
                state=state,
                ttl_seconds=_QUERY_TASK_TTL_SECONDS,
            )
            with _QUERY_TASK_LOCK:
                _cleanup_memory_tasks(time.time())
                _QUERY_TASKS[str(persisted_state["task_id"])] = dict(persisted_state)
            if not created:
                existing_state = {**persisted_state, "coalesced": True}
                _index_task(user_id, str(persisted_state["task_id"]))
                return _public_state(existing_state)
            state = persisted_state
        else:
            with _QUERY_TASK_LOCK:
                _cleanup_memory_tasks(time.time())
                existing_id = _QUERY_TASK_DEDUPES.get(dedupe_key)
                existing = _QUERY_TASKS.get(existing_id or "") if existing_id else None
                if not existing or existing.get("status") not in _QUERY_TASK_DEDUPE_STATUSES:
                    existing = None
                    _QUERY_TASKS[task_id] = dict(state)
                    _QUERY_TASK_DEDUPES[dedupe_key] = task_id
            if existing:
                _index_task(user_id, str(existing["task_id"]))
                return _public_state({**existing, "coalesced": True})

        _index_task(user_id, task_id)
        _store_job(
            task_id,
            {
                "kind": kind,
                "user_id": user_id,
                "terms": normalized_terms,
                "username": job_username,
                "password": job_password,
                "remember": job_remember,
                "account_key": account_key,
                "account_mode": account_mode,
                "credential_key": credential_key,
                "prior_bound_credential_key": prior_bound_credential_key,
                "refresh_order": refresh_order,
            },
        )
        if autostart:
            EduScheduleQueryTaskService._start_worker(task_id)
        return _public_state(state)

    @staticmethod
    def list_recent(owner_user_id: int, *, kind: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
        task_kind = str(kind or "").strip()
        if task_kind and task_kind not in {"schedule", "grades"}:
            raise ValueError("教务查询类型不正确")
        items: List[Dict[str, Any]] = []
        for task_id in _load_user_task_ids(int(owner_user_id)):
            state = _load_state(task_id)
            if not state:
                continue
            if int(state.get("owner_user_id") or 0) != int(owner_user_id):
                continue
            if task_kind and state.get("kind") != task_kind:
                continue
            if not grade_task_matches_bound_account(
                state,
                int(owner_user_id),
            ):
                continue
            items.append(state)
        if task_kind == "grades":
            items.sort(
                key=lambda item: (
                    int(item.get("refresh_order") or 0),
                    str(item.get("created_at") or ""),
                ),
                reverse=True,
            )
        else:
            items.sort(
                key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                reverse=True,
            )
        return [_public_state(item) for item in items[: max(1, int(limit))]]

    @staticmethod
    def get(task_id: str, owner_user_id: int) -> Dict[str, Any]:
        task_id = str(task_id or "").strip()
        state = _load_state(task_id)
        if not state:
            raise ValueError("查询任务不存在或已过期")
        if int(state.get("owner_user_id") or 0) != int(owner_user_id):
            raise ValueError("查询任务不存在或已过期")
        if not grade_task_matches_bound_account(
            state,
            int(owner_user_id),
        ):
            raise ValueError("查询任务不存在或已过期")
        return _public_state(state)

    @staticmethod
    def cancel(task_id: str, owner_user_id: int) -> Dict[str, Any]:
        task_id = str(task_id or "").strip()
        state = _load_state(task_id)
        if not state:
            raise ValueError("查询任务不存在或已过期")
        if int(state.get("owner_user_id") or 0) != int(owner_user_id):
            raise ValueError("查询任务不存在或已过期")
        if not grade_task_matches_bound_account(state, int(owner_user_id)):
            raise ValueError("查询任务不存在或已过期")
        if state.get("status") not in _QUERY_TASK_ACTIVE_STATUSES:
            return _public_state(state)

        next_state = _save_state({
            **state,
            "status": "cancelled",
            "message": "查询已停止",
            "challenge": None,
            "finished_at": _now_iso(),
        })
        if next_state.get("status") == "cancelled":
            dedupe_key = str(state.get("dedupe_key") or "")
            if dedupe_key:
                with _QUERY_TASK_LOCK:
                    if _QUERY_TASK_DEDUPES.get(dedupe_key) == task_id:
                        _QUERY_TASK_DEDUPES.pop(dedupe_key, None)
            _discard_task_grade_refresh(
                str(state.get("kind") or ""),
                int(owner_user_id),
                task_id,
            )
        return _public_state(next_state)

    @staticmethod
    def _start_worker(task_id: str) -> None:
        app = current_app._get_current_object() if has_app_context() else None

        def target() -> None:
            if app is not None:
                with app.app_context():
                    EduScheduleQueryTaskService.run_task(task_id)
                return
            EduScheduleQueryTaskService.run_task(task_id)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    @staticmethod
    def run_task(task_id: str) -> Dict[str, Any]:
        task_id = str(task_id or "").strip()
        state = _load_state(task_id)
        job = _load_job(task_id)
        if not state or not job:
            raise ValueError("查询任务不存在或已过期")
        cancelled_state = _cancelled_state(task_id)
        if cancelled_state:
            return cancelled_state

        kind = str(job["kind"])
        user_id = int(job["user_id"])
        terms = _normalize_terms(job["terms"])
        last_error: Optional[Exception] = None
        attempt = 0
        while True:
            cancelled_state = _cancelled_state(task_id)
            if cancelled_state:
                _discard_task_grade_refresh(kind, user_id, task_id)
                return cancelled_state
            attempt += 1
            if kind == "grades" and not grade_task_matches_bound_account(state, user_id):
                _discard_task_grade_refresh(kind, user_id, task_id)
                final_state = stop_for_binding_change(
                    state,
                    message="教务账号绑定已变更，本次旧账号查询已停止",
                    finished_at=_now_iso(),
                    save_state=_save_state,
                )
                return _public_state(final_state)
            status = "running" if attempt == 1 else "retrying"
            if kind == "grades":
                message = "正在连接教务系统并刷新全部成绩" if attempt == 1 else f"教务系统繁忙，正在第 {attempt} 次自动重试"
            else:
                message = "正在连接教务系统并查询" if attempt == 1 else f"教务系统繁忙，正在第 {attempt} 次自动重试"
            state = _save_state({
                **state,
                "status": status,
                "message": message,
                "attempt": attempt,
            })
            if state.get("status") == "cancelled":
                _discard_task_grade_refresh(kind, user_id, task_id)
                return _public_state(state)
            try:
                if kind == "grades":
                    data = EduScheduleService.query_grade_terms(
                        user_id,
                        terms,
                        username=job.get("username"),
                        password=job.get("password"),
                        remember=bool(job.get("remember")),
                        refresh_id=task_id,
                        expected_bound_credential_key=job.get(
                            "prior_bound_credential_key"
                        ),
                        enforce_expected_binding=bool(job.get("remember")),
                        refresh_order=int(job.get("refresh_order") or 0),
                        claim_publish=lambda: _claim_task_publish(task_id),
                    )
                else:
                    data = EduScheduleService.query_terms(
                        user_id,
                        terms,
                        username=job.get("username"),
                        password=job.get("password"),
                        remember=bool(job.get("remember")),
                    )
                cancelled_state = _cancelled_state(task_id)
                if cancelled_state:
                    _discard_task_grade_refresh(kind, user_id, task_id)
                    return cancelled_state
                if kind == "grades" and not grade_task_matches_bound_account(state, user_id):
                    _discard_task_grade_refresh(kind, user_id, task_id)
                    final_state = stop_for_binding_change(
                        state,
                        message="教务账号绑定已变更，本次旧账号结果未展示",
                        finished_at=_now_iso(),
                        save_state=_save_state,
                    )
                    return _public_state(final_state)
                snapshots, cached_overview, cached_year_averages = _task_cached_data(
                    kind,
                    user_id,
                    terms,
                    state,
                    upstream_authenticated=True,
                )
                published_snapshots = data.get("snapshots", snapshots) if kind == "grades" else snapshots
                published_overview = data.get("grade_overview", cached_overview)
                published_year_averages = data.get("academic_year_averages", cached_year_averages)
                final_state = _save_state({
                    **state,
                    "status": "succeeded",
                    "message": "全部成绩已同步" if kind == "grades" else "查询完成",
                    "results": data.get("results") or [],
                    "snapshots": published_snapshots,
                    "grade_overview": published_overview,
                    "academic_year_averages": published_year_averages,
                    "credential": data.get("credential") or EduScheduleService.credential_status(user_id),
                    "error": "",
                    "error_type": "",
                    "challenge": None,
                    "finished_at": _now_iso(),
                })
                if final_state.get("status") == "cancelled":
                    _discard_task_grade_refresh(kind, user_id, task_id)
                return _public_state(final_state)
            except Exception as exc:
                last_error = exc
                cancelled_state = _cancelled_state(task_id)
                if cancelled_state:
                    _discard_task_grade_refresh(kind, user_id, task_id)
                    return cancelled_state
                if kind == "grades" and not grade_task_matches_bound_account(state, user_id):
                    _discard_task_grade_refresh(kind, user_id, task_id)
                    final_state = stop_for_binding_change(
                        state,
                        message="教务账号绑定已变更，本次旧账号查询已停止",
                        finished_at=_now_iso(),
                        save_state=_save_state,
                    )
                    return _public_state(final_state)
                if should_start_webvpn_refresh(exc):
                    snapshots, cached_overview, cached_year_averages = _task_cached_data(
                        kind,
                        user_id,
                        terms,
                        state,
                    )
                    try:
                        challenge = WebVPNSessionRefreshService.start(owner_user_id=user_id)
                    except Exception as challenge_exc:
                        final_state = _save_state({
                            **state,
                            "status": "failed",
                            "message": user_safe_error(exc),
                            "results": results_from_snapshots(snapshots),
                            "snapshots": snapshots,
                            "grade_overview": cached_overview,
                            "academic_year_averages": cached_year_averages,
                            "error": str(challenge_exc) or user_safe_error(exc),
                            "error_type": type(challenge_exc).__name__,
                            "finished_at": _now_iso(),
                        })
                        return _public_state(final_state)
                    final_state = _save_state({
                        **state,
                        "status": "webvpn_refresh_required",
                        "message": WEBVPN_REFRESH_REQUIRED_MESSAGE,
                        "results": results_from_snapshots(snapshots),
                        "snapshots": snapshots,
                        "grade_overview": cached_overview,
                        "academic_year_averages": cached_year_averages,
                        "error": user_safe_error(exc),
                        "error_type": type(exc).__name__,
                        "challenge": challenge,
                        "finished_at": _now_iso(),
                    })
                    return _public_state(final_state)
                if is_upstream_busy(exc):
                    snapshots, cached_overview, cached_year_averages = _task_cached_data(
                        kind,
                        user_id,
                        terms,
                        state,
                    )
                    state = _save_state({
                        **state,
                        "status": "retrying",
                        "message": retrying_message(attempt, bool(snapshots)),
                        "results": results_from_snapshots(snapshots),
                        "snapshots": snapshots,
                        "grade_overview": cached_overview,
                        "academic_year_averages": cached_year_averages,
                        "error": user_safe_error(exc),
                        "error_type": type(exc).__name__,
                        "challenge": None,
                        "finished_at": None,
                    })
                    if state.get("status") == "cancelled":
                        _discard_task_grade_refresh(kind, user_id, task_id)
                        return _public_state(state)
                    _sleep(backoff_seconds_for(attempt, _QUERY_TASK_BACKOFF_SECONDS))
                    continue
                break

        snapshots, cached_overview, cached_year_averages = _task_cached_data(
            kind,
            user_id,
            terms,
            state,
        )
        error_message = user_safe_error(last_error) if last_error else "教务查询失败，请稍后重试"
        final_state = _save_state({
            **state,
            "status": "failed",
            "message": error_message,
            "results": results_from_snapshots(snapshots),
            "snapshots": snapshots,
            "grade_overview": cached_overview,
            "academic_year_averages": cached_year_averages,
            "error": error_message,
            "error_type": type(last_error).__name__ if last_error else "",
            "finished_at": _now_iso(),
        })
        return _public_state(final_state)
