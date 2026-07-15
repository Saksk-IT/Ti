# -*- coding: utf-8 -*-
"""教务课表业务服务。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

import requests
from flask import current_app
from sqlalchemy import or_

from app.core.extensions import db
from app.core.utils.credential_crypto import (
    CredentialCryptoError,
    credential_fingerprint,
    decrypt_secret,
    encrypt_secret,
)
from app.core.utils.redis_utils import get_redis_connection
from app.models.edu_schedule import (
    EduGradeOverviewSnapshot,
    EduGradeSnapshot,
    EduScheduleCredential,
    EduScheduleSnapshot,
)
from app.modules.admin.services.system_config_service import SystemConfigService

from .client import (
    JWXTClient,
    ScheduleAuthError,
    ScheduleClientError,
)
from .grade_overview import (
    calculate_cumulative_gpa,
    is_complete_grade_payload,
    serialize_grade_overview_rows,
)
from .grade_parser import normalize_grade_payload, split_grade_payload_by_term
from .grade_snapshot_batch import load_grade_refresh_batch
from .grade_snapshot_identity import (
    legacy_snapshot_payload_matches_account,
    validate_grade_identity,
)
from .parser import normalize_schedule_payload
from .schedule_support import EduScheduleError, mask_account, user_safe_error
from .upstream_executor import fetch_first_success, run_with_global_upstream_slot


_EDU_UPSTREAM_TASK_CONCURRENCY = 5
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
    def save_credentials_if_unchanged(
        user_id: int,
        username: str,
        password: str,
        expected_credential_key: Optional[str],
    ) -> Dict[str, Any]:
        cfg = SystemConfigService.get_edu_schedule_config()
        if not cfg.get("store_user_credentials", True):
            raise EduScheduleError("系统未开启保存教务凭据")
        item = (
            EduScheduleCredential.query
            .filter_by(user_id=int(user_id))
            .with_for_update()
            .first()
        )
        current_credential_key = None
        if item:
            try:
                current_credential_key = EduScheduleService.query_credential_key(
                    decrypt_secret(item.jwxt_username_ciphertext),
                    decrypt_secret(item.jwxt_password_ciphertext),
                )
            except CredentialCryptoError:
                current_credential_key = None
        if current_credential_key != expected_credential_key:
            db.session.rollback()
            raise EduScheduleError("教务账号绑定已变更，本次查询未覆盖新绑定")
        if item:
            db.session.delete(item)
        db.session.add(
            EduScheduleCredential(
                user_id=int(user_id),
                jwxt_username_ciphertext=encrypt_secret(username),
                jwxt_password_ciphertext=encrypt_secret(password),
                username_hint=mask_account(username),
            )
        )
        db.session.commit()
        return EduScheduleService.credential_status(user_id)

    @staticmethod
    def delete_credentials(user_id: int) -> None:
        EduScheduleCredential.query.filter_by(user_id=int(user_id)).delete()
        EduScheduleSnapshot.query.filter_by(user_id=int(user_id)).update(
            {
                EduScheduleSnapshot.jwxt_username_ciphertext: None,
                EduScheduleSnapshot.jwxt_password_ciphertext: None,
            },
            synchronize_session=False,
        )
        EduGradeSnapshot.query.filter_by(user_id=int(user_id)).update(
            {
                EduGradeSnapshot.jwxt_username_ciphertext: None,
                EduGradeSnapshot.jwxt_password_ciphertext: None,
            },
            synchronize_session=False,
        )
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
        return run_with_global_upstream_slot(fetch_once, get_redis_connection())

    @staticmethod
    def _fetch_first_success(fetch_once, *, cleanup_result=None):
        return fetch_first_success(
            fetch_once,
            task_concurrency=_EDU_UPSTREAM_TASK_CONCURRENCY,
            run_with_slot=EduScheduleService._run_with_global_upstream_slot,
            cleanup_result=cleanup_result,
        )

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
        refresh_id: Optional[str] = None,
        refresh_order: Optional[int] = None,
        claim_publish: Optional[Callable[[], bool]] = None,
        expected_bound_credential_key: Optional[str] = None,
        enforce_expected_binding: bool = False,
    ) -> Dict[str, Any]:
        cfg = SystemConfigService.get_edu_schedule_config()
        if not cfg.get("enabled", False):
            raise EduScheduleError("成绩查询功能未开启")

        uses_bound_credentials = not bool((username or "").strip() and password)
        account = (username or "").strip()
        secret = password or ""
        if account and secret:
            bound_account_key = EduScheduleService.get_bound_account_key(user_id)
            if (
                bound_account_key
                and bound_account_key != EduScheduleService.account_key(account)
                and not remember
            ):
                raise EduScheduleError("临时教务账号与当前绑定账号不一致，请先更新账号绑定")
        else:
            account, secret = EduScheduleService._load_credentials(user_id)

        fetch_result = EduScheduleService._fetch_first_success(
            lambda: JWXTClient(cfg).fetch_all_grades_authenticated(account, secret),
            cleanup_result=lambda result: result.close(),
        )
        official_gpa: Optional[Decimal] = None
        try:
            raw_payload = fetch_result.payload
            EduScheduleService._validate_grade_identity(raw_payload, account)
            if not is_complete_grade_payload(raw_payload):
                raise ScheduleClientError("教务成绩数据不完整，请稍后重试")
            calculated_gpa = calculate_cumulative_gpa(raw_payload)
            try:
                official_gpa = EduScheduleService._run_with_global_upstream_slot(
                    fetch_result.fetch_official_gpa
                )
            except (ScheduleClientError, requests.RequestException) as exc:
                current_app.logger.warning(
                    "官方累计 GPA 查询失败，使用系统估算或缓存: %s",
                    type(exc).__name__,
                )
        finally:
            fetch_result.close()

        account_key = EduScheduleService.account_key(account)
        if remember:
            if enforce_expected_binding:
                EduScheduleService.save_credentials_if_unchanged(
                    user_id,
                    account,
                    secret,
                    expected_bound_credential_key,
                )
            else:
                EduScheduleService.save_credentials(user_id, account, secret)
        if (
            (uses_bound_credentials or remember)
            and EduScheduleService.get_bound_account_key(user_id) != account_key
        ):
            raise EduScheduleError("教务账号绑定已变更，本次旧账号结果未保存")

        refresh_token = EduScheduleService._normalize_refresh_id(refresh_id)
        refresh_sequence = EduScheduleService._normalize_refresh_order(refresh_order)
        if claim_publish is not None and not claim_publish():
            raise EduScheduleError("成绩查询已停止，本次结果未保存")

        results: List[Dict[str, Any]] = []
        try:
            EduGradeSnapshot.query.filter_by(
                user_id=int(user_id),
                refresh_id=refresh_token,
            ).delete(synchronize_session=False)
            EduGradeOverviewSnapshot.query.filter_by(
                user_id=int(user_id),
                refresh_id=refresh_token,
            ).delete(synchronize_session=False)

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
                    refresh_id=refresh_token,
                    refresh_order=refresh_sequence,
                    commit=False,
                )
                results.append(normalized)

            db.session.add(
                EduGradeOverviewSnapshot(
                    user_id=int(user_id),
                    refresh_id=refresh_token,
                    refresh_order=refresh_sequence,
                    jwxt_account_key=account_key,
                    official_gpa=official_gpa,
                    calculated_gpa=calculated_gpa,
                    source=(
                        "official"
                        if official_gpa is not None
                        else "calculated"
                        if calculated_gpa is not None
                        else "unavailable"
                    ),
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        snapshots, grade_overview, year_averages = load_grade_refresh_batch(
            int(user_id),
            account_key,
            refresh_token,
        )

        return {
            "results": results,
            "snapshots": snapshots,
            "credential": EduScheduleService.credential_status(user_id),
            "grade_overview": grade_overview,
            "academic_year_averages": year_averages,
        }

    @staticmethod
    def _normalize_refresh_id(refresh_id: Optional[str]) -> str:
        value = str(refresh_id or "").strip()
        if value and len(value) <= 64 and all(char.isalnum() or char in "-_" for char in value):
            return value
        return uuid4().hex

    @staticmethod
    def _normalize_refresh_order(refresh_order: Optional[int]) -> int:
        try:
            value = int(refresh_order or 0)
        except (TypeError, ValueError):
            value = 0
        return value if value > 0 else time.time_ns() // 1000

    @staticmethod
    def _validate_grade_identity(payload: Dict[str, Any], account: str) -> None:
        validate_grade_identity(payload, account)

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
            .order_by(
                EduScheduleSnapshot.xnm.desc(),
                EduScheduleSnapshot.xqm.desc(),
                EduScheduleSnapshot.fetched_at.desc(),
                EduScheduleSnapshot.id.desc(),
            )
            .all()
        )
        return EduScheduleService._snapshot_rows_to_dicts(
            EduScheduleService._latest_rows_by_term(rows)
        )

    @staticmethod
    def list_snapshots_for_terms(user_id: int, terms: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen_terms = set()
        for term in terms:
            term_key = (str(term["xnm"]), str(term["xqm"]))
            if term_key in seen_terms:
                continue
            seen_terms.add(term_key)
            row = (
                EduScheduleSnapshot.query.filter_by(
                    user_id=int(user_id),
                    xnm=term_key[0],
                    xqm=term_key[1],
                )
                .order_by(EduScheduleSnapshot.fetched_at.desc(), EduScheduleSnapshot.id.desc())
                .first()
            )
            if row:
                items.extend(EduScheduleService._snapshot_rows_to_dicts([row]))
        return items

    @staticmethod
    def _latest_rows_by_term(rows) -> List[Any]:
        latest_rows = []
        seen_terms = set()
        for row in rows:
            term_key = (str(row.xnm or ""), str(row.xqm or ""))
            if term_key in seen_terms:
                continue
            seen_terms.add(term_key)
            latest_rows.append(row)
        return latest_rows

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
        refresh_id: Optional[str] = None,
        refresh_order: int = 0,
        commit: bool = True,
    ) -> None:
        snapshot = EduGradeSnapshot(
            user_id=user_id,
            xnm=xnm,
            xqm=xqm,
            refresh_id=refresh_id,
            refresh_order=EduScheduleService._normalize_refresh_order(refresh_order),
            jwxt_account_key=(
                credential_fingerprint(username, purpose="edu-jwxt-account")
                if username
                else None
            ),
            term_label=str(normalized.get("term", {}).get("label") or ""),
            jwxt_username_ciphertext=encrypt_secret(username) if username else None,
            jwxt_password_ciphertext=encrypt_secret(password) if password else None,
            payload_json=json.dumps(normalized, ensure_ascii=False),
            raw_payload_json=json.dumps(raw_payload, ensure_ascii=False),
        )
        db.session.add(snapshot)
        if commit:
            db.session.commit()

    @staticmethod
    def list_grade_snapshots(user_id: int) -> List[Dict[str, Any]]:
        account = EduScheduleService._bound_account(user_id)
        if not account:
            return []
        account_key = credential_fingerprint(account, purpose="edu-jwxt-account")
        return EduScheduleService._list_grade_snapshots_for_account(
            user_id,
            account,
            account_key,
        )

    @staticmethod
    def list_grade_snapshots_for_bound_account_key(
        user_id: int,
        expected_account_key: str,
    ) -> List[Dict[str, Any]]:
        account = EduScheduleService._bound_account(user_id)
        account_key = (
            credential_fingerprint(account, purpose="edu-jwxt-account")
            if account
            else ""
        )
        if not account or account_key != str(expected_account_key or "").strip():
            return []
        return EduScheduleService._list_grade_snapshots_for_account(
            user_id,
            account,
            account_key,
        )

    @staticmethod
    def _list_grade_snapshots_for_account(
        user_id: int,
        account: str,
        account_key: str,
    ) -> List[Dict[str, Any]]:
        rows = (
            EduGradeSnapshot.query
            .filter(EduGradeSnapshot.user_id == int(user_id))
            .filter(
                or_(
                    EduGradeSnapshot.jwxt_account_key == account_key,
                    EduGradeSnapshot.jwxt_account_key.is_(None),
                )
            )
            .order_by(
                EduGradeSnapshot.xnm.desc(),
                EduGradeSnapshot.xqm.desc(),
                EduGradeSnapshot.refresh_order.desc(),
                EduGradeSnapshot.fetched_at.desc(),
                EduGradeSnapshot.id.desc(),
            )
            .all()
        )
        rows = [
            row
            for row in rows
            if EduScheduleService._grade_snapshot_matches_account(row, account, account_key)
        ]
        if rows:
            newest_row = max(
                rows,
                key=lambda row: (
                    int(row.refresh_order or 0),
                    row.fetched_at or datetime.min,
                    row.id,
                ),
            )
            if newest_row.refresh_id:
                batch_rows = [row for row in rows if row.refresh_id == newest_row.refresh_id]
                return EduScheduleService._grade_snapshot_rows_to_dicts(batch_rows)
        return EduScheduleService._grade_snapshot_rows_to_dicts(EduScheduleService._latest_rows_by_term(rows))

    @staticmethod
    def get_grade_overview(user_id: int) -> Optional[Dict[str, Any]]:
        account = EduScheduleService._bound_account(user_id)
        if not account:
            return None
        return EduScheduleService._get_grade_overview_for_account(int(user_id), account)

    @staticmethod
    def list_grade_snapshots_by_account_key(
        user_id: int,
        account_key: str,
    ) -> List[Dict[str, Any]]:
        key = str(account_key or "").strip()
        if not key:
            return []
        rows = (
            EduGradeSnapshot.query
            .filter_by(user_id=int(user_id), jwxt_account_key=key)
            .order_by(
                EduGradeSnapshot.xnm.desc(),
                EduGradeSnapshot.xqm.desc(),
                EduGradeSnapshot.refresh_order.desc(),
                EduGradeSnapshot.fetched_at.desc(),
                EduGradeSnapshot.id.desc(),
            )
            .all()
        )
        if rows:
            newest_row = max(
                rows,
                key=lambda row: (
                    int(row.refresh_order or 0),
                    row.fetched_at or datetime.min,
                    row.id,
                ),
            )
            if newest_row.refresh_id:
                batch_rows = [row for row in rows if row.refresh_id == newest_row.refresh_id]
                return EduScheduleService._grade_snapshot_rows_to_dicts(batch_rows)
        return EduScheduleService._grade_snapshot_rows_to_dicts(
            EduScheduleService._latest_rows_by_term(rows)
        )

    @staticmethod
    def get_grade_overview_by_account_key(
        user_id: int,
        account_key: str,
    ) -> Optional[Dict[str, Any]]:
        key = str(account_key or "").strip()
        if not key:
            return None
        return EduScheduleService._get_grade_overview_for_account_key(int(user_id), key)

    @staticmethod
    def _bound_account(user_id: int) -> Optional[str]:
        credential = EduScheduleCredential.query.filter_by(user_id=int(user_id)).first()
        if not credential:
            return None
        try:
            return decrypt_secret(credential.jwxt_username_ciphertext)
        except CredentialCryptoError:
            return None

    @staticmethod
    def get_bound_account_key(user_id: int) -> Optional[str]:
        account = EduScheduleService._bound_account(user_id)
        if not account:
            return None
        return credential_fingerprint(account, purpose="edu-jwxt-account")

    @staticmethod
    def get_bound_credential_key(user_id: int) -> Optional[str]:
        credential = EduScheduleCredential.query.filter_by(user_id=int(user_id)).first()
        if not credential:
            return None
        try:
            username = decrypt_secret(credential.jwxt_username_ciphertext)
            password = decrypt_secret(credential.jwxt_password_ciphertext)
        except CredentialCryptoError:
            return None
        return EduScheduleService.query_credential_key(username, password)

    @staticmethod
    def account_key(account: str) -> str:
        return credential_fingerprint(account, purpose="edu-jwxt-account")

    @staticmethod
    def query_credential_key(account: str, password: str) -> str:
        return credential_fingerprint(
            f"{str(account or '').strip()}\0{str(password or '')}\0",
            purpose="edu-jwxt-query-credential",
        )

    @staticmethod
    def discard_grade_refresh(user_id: int, refresh_id: str) -> None:
        refresh_token = str(refresh_id or "").strip()
        if (
            not refresh_token
            or len(refresh_token) > 64
            or not all(char.isalnum() or char in "-_" for char in refresh_token)
        ):
            return
        try:
            EduGradeSnapshot.query.filter_by(
                user_id=int(user_id),
                refresh_id=refresh_token,
            ).delete(synchronize_session=False)
            EduGradeOverviewSnapshot.query.filter_by(
                user_id=int(user_id),
                refresh_id=refresh_token,
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def _grade_snapshot_matches_account(row, account: str, account_key: str) -> bool:
        if row.jwxt_account_key:
            return row.jwxt_account_key == account_key
        if row.jwxt_username_ciphertext:
            try:
                if decrypt_secret(row.jwxt_username_ciphertext) != account:
                    return False
            except CredentialCryptoError:
                return False
        return legacy_snapshot_payload_matches_account(
            row.payload_json,
            row.raw_payload_json,
            account,
        )

    @staticmethod
    def _get_grade_overview_for_account(user_id: int, account: str) -> Optional[Dict[str, Any]]:
        account_key = credential_fingerprint(account, purpose="edu-jwxt-account")
        return EduScheduleService._get_grade_overview_for_account_key(user_id, account_key)

    @staticmethod
    def _get_grade_overview_for_account_key(
        user_id: int,
        account_key: str,
    ) -> Optional[Dict[str, Any]]:
        rows = (
            EduGradeOverviewSnapshot.query
            .filter_by(user_id=int(user_id), jwxt_account_key=account_key)
            .order_by(
                EduGradeOverviewSnapshot.refresh_order.desc(),
                EduGradeOverviewSnapshot.fetched_at.desc(),
                EduGradeOverviewSnapshot.id.desc(),
            )
            .all()
        )
        return serialize_grade_overview_rows(rows)

    @staticmethod
    def list_grade_snapshots_for_terms(user_id: int, terms: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        account = EduScheduleService._bound_account(user_id)
        if not account:
            return []
        account_key = credential_fingerprint(account, purpose="edu-jwxt-account")
        items: List[Dict[str, Any]] = []
        seen_terms = set()
        for term in terms:
            term_key = (str(term["xnm"]), str(term["xqm"]))
            if term_key in seen_terms:
                continue
            seen_terms.add(term_key)
            rows = (
                EduGradeSnapshot.query.filter_by(
                    user_id=int(user_id),
                    xnm=term_key[0],
                    xqm=term_key[1],
                )
                .order_by(
                    EduGradeSnapshot.refresh_order.desc(),
                    EduGradeSnapshot.fetched_at.desc(),
                    EduGradeSnapshot.id.desc(),
                )
                .all()
            )
            row = next(
                (
                    candidate
                    for candidate in rows
                    if EduScheduleService._grade_snapshot_matches_account(
                        candidate,
                        account,
                        account_key,
                    )
                ),
                None,
            )
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
                "refresh_id": row.refresh_id,
                "refresh_order": int(row.refresh_order or 0),
                "term_label": row.term_label,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "payload": json.loads(row.payload_json or "{}"),
            }
            for row in rows
        ]
