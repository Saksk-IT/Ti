# -*- coding: utf-8 -*-
"""教务课表业务服务。"""

from __future__ import annotations

import concurrent.futures
import json
import secrets
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.extensions import db
from app.core.utils.credential_crypto import decrypt_secret, encrypt_secret
from app.core.utils.redis_utils import get_redis_connection
from app.models.edu_schedule import EduGradeSnapshot, EduScheduleCredential, EduScheduleSnapshot
from app.modules.admin.services.system_config_service import SystemConfigService

from .client import (
    JWXTClient,
    ScheduleAuthError,
    ScheduleClientError,
    WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE,
)
from .grade_parser import normalize_grade_payload, split_grade_payload_by_term
from .parser import normalize_schedule_payload


_EDU_UPSTREAM_TASK_CONCURRENCY = 5
_EDU_UPSTREAM_GLOBAL_CONCURRENCY = 20
_EDU_UPSTREAM_SEMAPHORE = threading.BoundedSemaphore(_EDU_UPSTREAM_GLOBAL_CONCURRENCY)
_EDU_UPSTREAM_REDIS_KEY = "edu_schedule:upstream_slots"
_EDU_UPSTREAM_REDIS_TTL_SECONDS = 120
_EDU_UPSTREAM_SLOT_WAIT_SECONDS = 0.05
_EDU_UPSTREAM_ACQUIRE_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local token = ARGV[3]
local now = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - ttl)
if redis.call('ZCARD', key) < limit then
  redis.call('ZADD', key, now, token)
  redis.call('EXPIRE', key, ttl)
  return 1
end
return 0
"""


class EduScheduleError(RuntimeError):
    """课表业务错误。"""


def mask_account(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 4:
        return "***"
    return f"{text[:4]}****{text[-4:]}"


class EduScheduleService:
    """用户教务凭据和课表查询服务。"""

    @staticmethod
    def save_credentials(user_id: int, username: str, password: str) -> Dict[str, Any]:
        cfg = SystemConfigService.get_edu_schedule_config()
        if not cfg.get("store_user_credentials", True):
            raise EduScheduleError("系统未开启保存教务凭据")

        EduScheduleCredential.query.filter_by(user_id=int(user_id)).delete()
        item = EduScheduleCredential(
            user_id=int(user_id),
            jwxt_username_ciphertext=encrypt_secret(username),
            jwxt_password_ciphertext=encrypt_secret(password),
            username_hint=mask_account(username),
        )
        db.session.add(item)
        db.session.commit()
        return EduScheduleService.credential_status(user_id)

    @staticmethod
    def delete_credentials(user_id: int) -> None:
        EduScheduleCredential.query.filter_by(user_id=int(user_id)).delete()
        db.session.commit()

    @staticmethod
    def credential_status(user_id: int) -> Dict[str, Any]:
        row = EduScheduleCredential.query.filter_by(user_id=int(user_id)).first()
        return {
            "has_credentials": bool(row),
            "username_hint": row.username_hint if row else "",
        }

    @staticmethod
    def _load_credentials(user_id: int) -> Tuple[str, str]:
        row = EduScheduleCredential.query.filter_by(user_id=int(user_id)).first()
        if not row:
            raise EduScheduleError("请先填写教务账号和密码")
        return (
            decrypt_secret(row.jwxt_username_ciphertext),
            decrypt_secret(row.jwxt_password_ciphertext),
        )

    @staticmethod
    def _run_with_global_upstream_slot(fetch_once):
        redis_conn = get_redis_connection()
        if redis_conn is not None:
            token = secrets.token_urlsafe(18)
            acquired = False
            try:
                while not acquired:
                    raw_acquired = redis_conn.eval(
                        _EDU_UPSTREAM_ACQUIRE_SCRIPT,
                        1,
                        _EDU_UPSTREAM_REDIS_KEY,
                        _EDU_UPSTREAM_GLOBAL_CONCURRENCY,
                        _EDU_UPSTREAM_REDIS_TTL_SECONDS,
                        token,
                        time.time(),
                    )
                    acquired = int(raw_acquired or 0) == 1
                    if not acquired:
                        time.sleep(_EDU_UPSTREAM_SLOT_WAIT_SECONDS)
                return fetch_once()
            except Exception:
                if acquired:
                    raise
            finally:
                if acquired:
                    try:
                        redis_conn.zrem(_EDU_UPSTREAM_REDIS_KEY, token)
                    except Exception:
                        pass

        _EDU_UPSTREAM_SEMAPHORE.acquire()
        try:
            return fetch_once()
        finally:
            _EDU_UPSTREAM_SEMAPHORE.release()

    @staticmethod
    def _select_hedged_error(errors: List[Exception]) -> Exception:
        for exc in errors:
            if isinstance(exc, ScheduleAuthError):
                return exc
        return errors[-1] if errors else ScheduleClientError("教务查询失败，请稍后重试")

    @staticmethod
    def _fetch_first_success(fetch_once):
        worker_count = max(1, min(_EDU_UPSTREAM_TASK_CONCURRENCY, _EDU_UPSTREAM_GLOBAL_CONCURRENCY))
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="edu-upstream",
        )
        futures = [
            executor.submit(EduScheduleService._run_with_global_upstream_slot, fetch_once)
            for _ in range(worker_count)
        ]
        errors: List[Exception] = []
        try:
            for future in concurrent.futures.as_completed(futures):
                try:
                    return future.result()
                except Exception as exc:
                    errors.append(exc)
            raise EduScheduleService._select_hedged_error(errors)
        finally:
            for future in futures:
                if not future.done():
                    future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def query_terms(
        user_id: int,
        terms: Iterable[Dict[str, str]],
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        remember: bool = False,
    ) -> Dict[str, Any]:
        cfg = SystemConfigService.get_edu_schedule_config()
        if not cfg.get("enabled", False):
            raise EduScheduleError("课表查询功能未开启")

        account = (username or "").strip()
        secret = password or ""
        if account and secret:
            if remember:
                EduScheduleService.save_credentials(user_id, account, secret)
        else:
            account, secret = EduScheduleService._load_credentials(user_id)

        results: List[Dict[str, Any]] = []
        for term in terms:
            xnm = str(term["xnm"])
            xqm = str(term["xqm"])
            raw_payload = EduScheduleService._fetch_first_success(
                lambda xnm=xnm, xqm=xqm: JWXTClient(cfg).fetch_schedule(account, secret, xnm, xqm)
            )
            normalized = normalize_schedule_payload(raw_payload)
            EduScheduleService._save_snapshot(
                int(user_id),
                xnm,
                xqm,
                normalized,
                raw_payload,
                username=account,
                password=secret,
            )
            results.append(normalized)

        return {
            "results": results,
            "credential": EduScheduleService.credential_status(user_id),
        }

    @staticmethod
    def query_grade_terms(
        user_id: int,
        terms: Iterable[Dict[str, str]],
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        remember: bool = False,
    ) -> Dict[str, Any]:
        cfg = SystemConfigService.get_edu_schedule_config()
        if not cfg.get("enabled", False):
            raise EduScheduleError("成绩查询功能未开启")

        account = (username or "").strip()
        secret = password or ""
        if account and secret:
            if remember:
                EduScheduleService.save_credentials(user_id, account, secret)
        else:
            account, secret = EduScheduleService._load_credentials(user_id)

        raw_payload = EduScheduleService._fetch_first_success(
            lambda: JWXTClient(cfg).fetch_all_grades(account, secret)
        )

        results: List[Dict[str, Any]] = []
        for term_payload in split_grade_payload_by_term(raw_payload):
            normalized = normalize_grade_payload(term_payload)
            xnm = str(normalized.get("term", {}).get("xnm") or "")
            xqm = str(normalized.get("term", {}).get("xqm") or "")
            if not xnm or not xqm:
                continue
            EduScheduleService._save_grade_snapshot(
                int(user_id),
                xnm,
                xqm,
                normalized,
                term_payload,
                username=account,
                password=secret,
            )
            results.append(normalized)

        return {
            "results": results,
            "credential": EduScheduleService.credential_status(user_id),
        }

    @staticmethod
    def _save_snapshot(
        user_id: int,
        xnm: str,
        xqm: str,
        normalized: Dict[str, Any],
        raw_payload: Dict[str, Any],
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        snapshot = EduScheduleSnapshot(
            user_id=user_id,
            xnm=xnm,
            xqm=xqm,
            term_label=str(normalized.get("term", {}).get("label") or ""),
            jwxt_username_ciphertext=encrypt_secret(username) if username else None,
            jwxt_password_ciphertext=encrypt_secret(password) if password else None,
            payload_json=json.dumps(normalized, ensure_ascii=False),
            raw_payload_json=json.dumps(raw_payload, ensure_ascii=False),
        )
        db.session.add(snapshot)
        db.session.commit()

    @staticmethod
    def list_snapshots(user_id: int) -> List[Dict[str, Any]]:
        rows = (
            EduScheduleSnapshot.query
            .filter_by(user_id=int(user_id))
            .order_by(EduScheduleSnapshot.xnm.desc(), EduScheduleSnapshot.xqm.desc())
            .all()
        )
        return EduScheduleService._snapshot_rows_to_dicts(rows)

    @staticmethod
    def list_snapshots_for_terms(user_id: int, terms: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for term in terms:
            row = EduScheduleSnapshot.query.filter_by(
                user_id=int(user_id),
                xnm=str(term["xnm"]),
                xqm=str(term["xqm"]),
            ).first()
            if row:
                items.extend(EduScheduleService._snapshot_rows_to_dicts([row]))
        return items

    @staticmethod
    def _snapshot_rows_to_dicts(rows) -> List[Dict[str, Any]]:
        return [
            {
                "id": row.id,
                "xnm": row.xnm,
                "xqm": row.xqm,
                "term_label": row.term_label,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "payload": json.loads(row.payload_json or "{}"),
            }
            for row in rows
        ]

    @staticmethod
    def _save_grade_snapshot(
        user_id: int,
        xnm: str,
        xqm: str,
        normalized: Dict[str, Any],
        raw_payload: Dict[str, Any],
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        snapshot = EduGradeSnapshot(
            user_id=user_id,
            xnm=xnm,
            xqm=xqm,
            term_label=str(normalized.get("term", {}).get("label") or ""),
            jwxt_username_ciphertext=encrypt_secret(username) if username else None,
            jwxt_password_ciphertext=encrypt_secret(password) if password else None,
            payload_json=json.dumps(normalized, ensure_ascii=False),
            raw_payload_json=json.dumps(raw_payload, ensure_ascii=False),
        )
        db.session.add(snapshot)
        db.session.commit()

    @staticmethod
    def list_grade_snapshots(user_id: int) -> List[Dict[str, Any]]:
        rows = (
            EduGradeSnapshot.query
            .filter_by(user_id=int(user_id))
            .order_by(EduGradeSnapshot.xnm.desc(), EduGradeSnapshot.xqm.desc())
            .all()
        )
        return EduScheduleService._grade_snapshot_rows_to_dicts(rows)

    @staticmethod
    def list_grade_snapshots_for_terms(user_id: int, terms: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for term in terms:
            row = EduGradeSnapshot.query.filter_by(
                user_id=int(user_id),
                xnm=str(term["xnm"]),
                xqm=str(term["xqm"]),
            ).first()
            if row:
                items.extend(EduScheduleService._grade_snapshot_rows_to_dicts([row]))
        return items

    @staticmethod
    def _grade_snapshot_rows_to_dicts(rows) -> List[Dict[str, Any]]:
        return [
            {
                "id": row.id,
                "xnm": row.xnm,
                "xqm": row.xqm,
                "term_label": row.term_label,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "payload": json.loads(row.payload_json or "{}"),
            }
            for row in rows
        ]


def user_safe_error(exc: Exception) -> str:
    if isinstance(exc, ScheduleAuthError):
        auth_message = str(exc).strip()
        if auth_message == WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE:
            return WEBVPN_INTERACTIVE_CHALLENGE_MESSAGE
        if auth_message == "教务系统账号或密码错误":
            return "教务系统账号或密码错误，请检查绑定信息后重试"
        if auth_message == "WebVPN 登录态不可用":
            return "WebVPN 登录态不可用，请联系管理员在后台刷新 WebVPN 登录态"
        if auth_message == "WebVPN 未配置可用登录态":
            return "WebVPN 未配置可用登录态，请在后台配置有效 Cookie 或登录信息"
        return "上游登录失败，请检查授权信息后重试"
    if isinstance(exc, ScheduleClientError):
        return "教务查询失败，请稍后重试"
    if isinstance(exc, EduScheduleError):
        return str(exc)
    return "教务查询失败，请稍后重试"
