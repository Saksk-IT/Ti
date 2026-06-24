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

import requests
from flask import current_app, has_app_context

from app.core.utils.redis_utils import redis_get_json, redis_set_json

from .client import ScheduleAuthError, ScheduleClientError
from .schedule_service import EduScheduleError, EduScheduleService, user_safe_error
from .webvpn_refresh import (
    WEBVPN_REFRESH_REQUIRED_MESSAGE,
    WebVPNSessionRefreshService,
    should_start_webvpn_refresh,
)


_QUERY_TASK_TTL_SECONDS = 1800
_QUERY_TASK_MAX_ATTEMPTS = 3
_QUERY_TASK_BACKOFF_SECONDS = (5, 20)
_QUERY_TASK_KEY_PREFIX = "edu_schedule:query_task:"
_QUERY_TASK_LOCK = threading.Lock()
_QUERY_TASKS: Dict[str, Dict[str, Any]] = {}
_QUERY_TASK_JOBS: Dict[str, Dict[str, Any]] = {}
_QUERY_TASK_DEDUPES: Dict[str, str] = {}
_sleep = time.sleep


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_key(task_id: str) -> str:
    return f"{_QUERY_TASK_KEY_PREFIX}{task_id}"


def _normalize_terms(terms: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    return [{"xnm": str(term["xnm"]), "xqm": str(term["xqm"])} for term in terms]


def _dedupe_key(kind: str, user_id: int, terms: List[Dict[str, str]]) -> str:
    payload = json.dumps(
        {"kind": kind, "user_id": int(user_id), "terms": terms},
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


def _save_state(state: Dict[str, Any]) -> Dict[str, Any]:
    next_state = {**state, "updated_at": _now_iso()}
    task_id = str(next_state["task_id"])
    with _QUERY_TASK_LOCK:
        _cleanup_memory_tasks(time.time())
        _QUERY_TASKS[task_id] = next_state
    redis_set_json(_task_key(task_id), next_state, ttl_seconds=_QUERY_TASK_TTL_SECONDS)
    return next_state


def _load_state(task_id: str) -> Optional[Dict[str, Any]]:
    redis_state = redis_get_json(_task_key(task_id))
    if isinstance(redis_state, dict):
        return redis_state
    with _QUERY_TASK_LOCK:
        _cleanup_memory_tasks(time.time())
        state = _QUERY_TASKS.get(task_id)
    return dict(state) if isinstance(state, dict) else None


def _store_job(task_id: str, job: Dict[str, Any]) -> None:
    with _QUERY_TASK_LOCK:
        _QUERY_TASK_JOBS[task_id] = dict(job)


def _load_job(task_id: str) -> Optional[Dict[str, Any]]:
    with _QUERY_TASK_LOCK:
        job = _QUERY_TASK_JOBS.get(task_id)
    return dict(job) if isinstance(job, dict) else None


def _snapshots_for(kind: str, user_id: int, terms: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    if kind == "grades":
        return EduScheduleService.list_grade_snapshots_for_terms(user_id, terms)
    return EduScheduleService.list_snapshots_for_terms(user_id, terms)


def _results_from_snapshots(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item.get("payload") for item in snapshots if isinstance(item.get("payload"), dict)]


def _busy_message(has_snapshot: bool) -> str:
    if has_snapshot:
        return "教务系统繁忙，当前展示上次成功结果，后台刷新暂未成功"
    return "教务系统繁忙，后台刷新暂未成功，请稍后重试"


def _is_upstream_busy(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if exc.__class__.__name__ in {"ReadTimeout", "ConnectTimeout", "Timeout"}:
        return True
    return isinstance(exc, ScheduleClientError) and not isinstance(exc, ScheduleAuthError)


def _public_state(state: Dict[str, Any]) -> Dict[str, Any]:
    blocked_keys = {"expires_at", "dedupe_key", "owner_user_id", "error", "error_type"}
    return {key: value for key, value in state.items() if key not in blocked_keys}


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

        dedupe_key = _dedupe_key(kind, user_id, normalized_terms)
        with _QUERY_TASK_LOCK:
            _cleanup_memory_tasks(time.time())
            existing_id = _QUERY_TASK_DEDUPES.get(dedupe_key)
            existing = _QUERY_TASKS.get(existing_id or "") if existing_id else None
        if existing and existing.get("status") in {"pending", "running", "retrying"}:
            return _public_state({**existing, "coalesced": True})

        task_id = secrets.token_urlsafe(18)
        now = time.time()
        snapshots = _snapshots_for(kind, user_id, normalized_terms)
        state = {
            "task_id": task_id,
            "kind": kind,
            "owner_user_id": user_id,
            "terms": normalized_terms,
            "status": "pending",
            "message": "已提交后台查询，正在排队",
            "attempt": 0,
            "max_attempts": _QUERY_TASK_MAX_ATTEMPTS,
            "results": _results_from_snapshots(snapshots),
            "snapshots": snapshots,
            "credential": EduScheduleService.credential_status(user_id),
            "error": "",
            "error_type": "",
            "challenge": None,
            "coalesced": False,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "finished_at": None,
            "expires_at": now + _QUERY_TASK_TTL_SECONDS,
            "dedupe_key": dedupe_key,
        }
        _save_state(state)
        with _QUERY_TASK_LOCK:
            _QUERY_TASK_DEDUPES[dedupe_key] = task_id
        _store_job(
            task_id,
            {
                "kind": kind,
                "user_id": user_id,
                "terms": normalized_terms,
                "username": username,
                "password": password,
                "remember": bool(remember),
            },
        )
        if autostart:
            EduScheduleQueryTaskService._start_worker(task_id)
        return _public_state(state)

    @staticmethod
    def get(task_id: str, owner_user_id: int) -> Dict[str, Any]:
        task_id = str(task_id or "").strip()
        state = _load_state(task_id)
        if not state:
            raise ValueError("查询任务不存在或已过期")
        if int(state.get("owner_user_id") or 0) != int(owner_user_id):
            raise ValueError("查询任务不存在或已过期")
        return _public_state(state)

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

        kind = str(job["kind"])
        user_id = int(job["user_id"])
        terms = _normalize_terms(job["terms"])
        last_error: Optional[Exception] = None
        for attempt in range(1, _QUERY_TASK_MAX_ATTEMPTS + 1):
            status = "running" if attempt == 1 else "retrying"
            message = "正在连接教务系统并查询" if attempt == 1 else f"教务系统繁忙，正在第 {attempt} 次尝试"
            state = _save_state({
                **state,
                "status": status,
                "message": message,
                "attempt": attempt,
            })
            try:
                if kind == "grades":
                    data = EduScheduleService.query_grade_terms(
                        user_id,
                        terms,
                        username=job.get("username"),
                        password=job.get("password"),
                        remember=bool(job.get("remember")),
                    )
                else:
                    data = EduScheduleService.query_terms(
                        user_id,
                        terms,
                        username=job.get("username"),
                        password=job.get("password"),
                        remember=bool(job.get("remember")),
                    )
                snapshots = _snapshots_for(kind, user_id, terms)
                final_state = _save_state({
                    **state,
                    "status": "succeeded",
                    "message": "查询完成",
                    "results": data.get("results") or [],
                    "snapshots": snapshots,
                    "credential": data.get("credential") or EduScheduleService.credential_status(user_id),
                    "error": "",
                    "error_type": "",
                    "challenge": None,
                    "finished_at": _now_iso(),
                })
                return _public_state(final_state)
            except Exception as exc:
                last_error = exc
                if should_start_webvpn_refresh(exc):
                    snapshots = _snapshots_for(kind, user_id, terms)
                    try:
                        challenge = WebVPNSessionRefreshService.start(owner_user_id=user_id)
                    except Exception as challenge_exc:
                        final_state = _save_state({
                            **state,
                            "status": "failed",
                            "message": user_safe_error(exc),
                            "results": _results_from_snapshots(snapshots),
                            "snapshots": snapshots,
                            "error": str(challenge_exc) or user_safe_error(exc),
                            "error_type": type(challenge_exc).__name__,
                            "finished_at": _now_iso(),
                        })
                        return _public_state(final_state)
                    final_state = _save_state({
                        **state,
                        "status": "webvpn_refresh_required",
                        "message": WEBVPN_REFRESH_REQUIRED_MESSAGE,
                        "results": _results_from_snapshots(snapshots),
                        "snapshots": snapshots,
                        "error": user_safe_error(exc),
                        "error_type": type(exc).__name__,
                        "challenge": challenge,
                        "finished_at": _now_iso(),
                    })
                    return _public_state(final_state)
                if attempt < _QUERY_TASK_MAX_ATTEMPTS and _is_upstream_busy(exc):
                    backoff_index = min(attempt - 1, len(_QUERY_TASK_BACKOFF_SECONDS) - 1)
                    _sleep(_QUERY_TASK_BACKOFF_SECONDS[backoff_index])
                    continue
                break

        snapshots = _snapshots_for(kind, user_id, terms)
        error_message = user_safe_error(last_error) if last_error else "教务查询失败，请稍后重试"
        final_state = _save_state({
            **state,
            "status": "failed",
            "message": _busy_message(bool(snapshots)) if last_error and _is_upstream_busy(last_error) else error_message,
            "results": _results_from_snapshots(snapshots),
            "snapshots": snapshots,
            "error": error_message,
            "error_type": type(last_error).__name__ if last_error else "",
            "finished_at": _now_iso(),
        })
        return _public_state(final_state)
