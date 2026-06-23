# -*- coding: utf-8 -*-
"""教务课表业务服务。"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.extensions import db
from app.core.utils.credential_crypto import decrypt_secret, encrypt_secret
from app.models.edu_schedule import EduGradeSnapshot, EduScheduleCredential, EduScheduleSnapshot
from app.modules.admin.services.system_config_service import SystemConfigService

from .client import JWXTClient, ScheduleAuthError, ScheduleClientError
from .grade_parser import normalize_grade_payload
from .parser import normalize_schedule_payload


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

        client = JWXTClient(cfg)
        results: List[Dict[str, Any]] = []
        for term in terms:
            raw_payload = client.fetch_schedule(account, secret, str(term["xnm"]), str(term["xqm"]))
            normalized = normalize_schedule_payload(raw_payload)
            EduScheduleService._save_snapshot(int(user_id), str(term["xnm"]), str(term["xqm"]), normalized, raw_payload)
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

        client = JWXTClient(cfg)
        results: List[Dict[str, Any]] = []
        for term in terms:
            raw_payload = client.fetch_grades(account, secret, str(term["xnm"]), str(term["xqm"]))
            normalized = normalize_grade_payload(raw_payload, str(term["xnm"]), str(term["xqm"]))
            EduScheduleService._save_grade_snapshot(
                int(user_id),
                str(term["xnm"]),
                str(term["xqm"]),
                normalized,
                raw_payload,
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
    ) -> None:
        EduScheduleSnapshot.query.filter_by(user_id=user_id, xnm=xnm, xqm=xqm).delete()
        snapshot = EduScheduleSnapshot(
            user_id=user_id,
            xnm=xnm,
            xqm=xqm,
            term_label=str(normalized.get("term", {}).get("label") or ""),
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
    ) -> None:
        EduGradeSnapshot.query.filter_by(user_id=user_id, xnm=xnm, xqm=xqm).delete()
        snapshot = EduGradeSnapshot(
            user_id=user_id,
            xnm=xnm,
            xqm=xqm,
            term_label=str(normalized.get("term", {}).get("label") or ""),
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
        return "上游登录失败，请检查授权信息后重试"
    if isinstance(exc, ScheduleClientError):
        return "教务查询失败，请稍后重试"
    if isinstance(exc, EduScheduleError):
        return str(exc)
    return "教务查询失败，请稍后重试"
