#!/usr/bin/env python3
"""Capture deterministic fixed-commit goldens for the all-shares read aliases."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import contextmanager
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterator
from urllib.parse import urlencode


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-all-shares-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_share_list_goldens as shared  # noqa: E402


pinned_source = shared.pinned_source
FIXED_REQUEST_ID = "phase4b-personal-bank-all-shares-golden-request"
FALLBACK_HOST = "legacy-all-shares.example:8443"
CONFIGURED_SHARE_BASE_URL = "https://configured-share.example/root/"
ROUTES = {
    "api-alias": {
        "route_id": "a6fda3638fc3",
        "path": "/api/user/banks/api/shares/all",
        "route_template": "/api/user/banks/api/shares/all",
        "legacy_handler": "user_bank_api_root.user_bank_api.get_all_shares",
        "registration_kind": "blueprint_compatibility_alias",
    },
    "web-alias": {
        "route_id": "0fdd3026f636",
        "path": "/user/banks/api/shares/all",
        "route_template": "/user/banks/api/shares/all",
        "legacy_handler": "user_bank.user_bank_api.get_all_shares",
        "registration_kind": "blueprint_decorator",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/models/user.py",
    "app/models/user_bank.py",
    "app/modules/user_bank/__init__.py",
    "app/modules/user_bank/routes/api.py",
    "app/modules/user_bank/routes/api_base.py",
    "app/modules/user_bank/routes/api_shares.py",
    "app/modules/user_bank/routes/pages.py",
    "app/modules/user_bank/templates/user_bank/manage/shares_manage_all.html",
    "app/modules/user_bank/templates/user_bank/shared/base.html",
)
ACTORS = {
    "owner": 99001,
    "other": 99002,
    "revoked": 99003,
}
BANKS = {
    "owner_active": 99101,
    "other_active": 99102,
    "inactive": 99103,
    "null_status": 99104,
    "status_two": 99105,
}
SHARES = {
    "null_created": -7,
    "special_token_inactive_expired": 0,
    "empty_token_cross_bank_owner": 99202,
    "ordinary": 99203,
    "inactive_bank": 99204,
    "null_status_bank": 99205,
    "status_two_bank": 99206,
    "other_owner": 99207,
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    session_actor: str | None = "owner"
    bearer_actor: str | None = None
    invalid_bearer: bool = False
    accept: str = "*/*"
    fixture_mode: str = "full"
    query: tuple[tuple[str, str], ...] = ()
    configured_share_base: bool = False
    fail_all_shares: bool = False
    expected_status: int = 200
    expected_query_attempts: int = 1


def build_case_specs() -> tuple[CaseSpec, ...]:
    return (
        CaseSpec("auth-session-mixed-api-alias", "api-alias"),
        CaseSpec(
            "auth-bearer-api-alias", "api-alias",
            session_actor=None, bearer_actor="owner",
        ),
        CaseSpec(
            "auth-bearer-precedes-session-api-alias", "api-alias",
            session_actor="owner", bearer_actor="other",
        ),
        CaseSpec(
            "auth-invalid-bearer-falls-back-session-api-alias", "api-alias",
            invalid_bearer=True,
        ),
        CaseSpec(
            "auth-anonymous-api-alias", "api-alias",
            session_actor=None, expected_status=401, expected_query_attempts=0,
        ),
        CaseSpec(
            "auth-state-invalid-bearer-api-alias", "api-alias",
            session_actor=None, bearer_actor="revoked",
            expected_status=401, expected_query_attempts=0,
        ),
        CaseSpec("data-empty-api-alias", "api-alias", fixture_mode="empty"),
        CaseSpec(
            "data-query-parameters-ignored-api-alias", "api-alias",
            query=(("active", "1"), ("sort", "asc"),
                   ("page", "2"), ("page", "3")),
        ),
        CaseSpec(
            "data-configured-share-base-api-alias", "api-alias",
            configured_share_base=True,
        ),
        CaseSpec(
            "fault-default-api-alias", "api-alias",
            fail_all_shares=True, expected_status=500,
        ),
        CaseSpec(
            "fault-json-api-alias", "api-alias",
            accept="application/json", fail_all_shares=True, expected_status=500,
        ),
        CaseSpec("auth-session-mixed-web-alias", "web-alias"),
        CaseSpec(
            "auth-bearer-web-alias", "web-alias",
            session_actor=None, bearer_actor="owner",
            expected_status=302, expected_query_attempts=0,
        ),
        CaseSpec(
            "auth-bearer-precedes-session-web-alias", "web-alias",
            session_actor="owner", bearer_actor="other",
            expected_status=302, expected_query_attempts=0,
        ),
        CaseSpec(
            "auth-invalid-bearer-falls-back-session-web-alias", "web-alias",
            invalid_bearer=True,
        ),
        CaseSpec(
            "auth-anonymous-web-alias", "web-alias",
            session_actor=None, expected_status=302, expected_query_attempts=0,
        ),
        CaseSpec("data-empty-web-alias", "web-alias", fixture_mode="empty"),
        CaseSpec(
            "data-query-parameters-ignored-web-alias", "web-alias",
            query=(("active", "1"), ("sort", "asc"),
                   ("page", "2"), ("page", "3")),
        ),
        CaseSpec(
            "fault-default-web-alias", "web-alias",
            fail_all_shares=True, expected_status=500,
        ),
        CaseSpec(
            "fault-json-web-alias", "web-alias",
            accept="application/json", fail_all_shares=True, expected_status=500,
        ),
    )


CASE_SPECS = build_case_specs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


canonical_json = shared.canonical_json
sha256_json = shared.sha256_json
document_payload_sha256 = shared.document_payload_sha256
render_document = shared.render_document
normalized_value = shared.normalized_value
normalized_sql = shared.normalized_sql
is_select_statement = shared.is_select_statement
is_dml_statement = shared.is_dml_statement
is_ddl_statement = shared.is_ddl_statement
reads_table = shared.reads_table
is_table_dml = shared.is_table_dml
is_user_last_active_dml = shared.is_user_last_active_dml
table_fingerprint = shared.table_fingerprint
reset_limiters = shared.reset_limiters
normalized_response = shared.normalized_response
credential_mode = shared.credential_mode
capture_environment = shared.capture_environment


def bind_count(parameters: Any) -> int:
    if isinstance(parameters, Mapping):
        return len(parameters)
    if isinstance(parameters, (list, tuple)):
        return len(parameters)
    return 0 if parameters is None else 1


def is_all_shares_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return (
        sql.startswith("SELECT BS.*, B.NAME AS BANK_NAME FROM BANK_SHARES BS")
        and "JOIN USER_QUESTION_BANKS B ON BS.BANK_ID = B.ID" in sql
        and "WHERE BS.OWNER_ID =" in sql
        and "AND B.STATUS = 1" in sql
        and sql.endswith("ORDER BY BS.CREATED_AT DESC")
    )


@contextmanager
def sql_probe(engine: Any, *, fail_all_shares: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "all_shares_select_attempts": 0,
        "all_shares_select_bind_count": 0,
        "bank_table_dml_attempts": 0,
        "share_table_dml_attempts": 0,
        "user_last_active_dml_attempts": 0,
    }

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        parameters: Any,
        _context: Any,
        executemany: Any,
    ) -> None:
        normalized = normalized_sql(statement)
        select = is_select_statement(statement)
        dml = is_dml_statement(statement)
        ddl = is_ddl_statement(statement)
        all_shares = is_all_shares_select(statement)
        bank_write = is_table_dml(statement, "user_question_banks")
        share_write = is_table_dml(statement, "bank_shares")
        activity_write = is_user_last_active_dml(statement)
        if all_shares:
            classification = "personal_bank_all_shares_select"
        elif activity_write:
            classification = "user_last_active_dml"
        elif bank_write:
            classification = "bank_table_dml"
        elif share_write:
            classification = "share_table_dml"
        elif ddl:
            classification = "ddl"
        elif reads_table(statement, "users"):
            classification = "users_select"
        elif select:
            classification = "select"
        elif dml:
            classification = "dml"
        else:
            classification = "other"
        ledger["statements"].append({
            "sql": normalized,
            "parameters": normalized_value(parameters),
            "executemany": bool(executemany),
            "classification": classification,
        })
        ledger["select_attempts"] += int(select)
        ledger["dml_attempts"] += int(dml)
        ledger["ddl_attempts"] += int(ddl)
        ledger["other_attempts"] += int(not select and not dml and not ddl)
        ledger["all_shares_select_attempts"] += int(all_shares)
        if all_shares:
            ledger["all_shares_select_bind_count"] += bind_count(parameters)
        ledger["bank_table_dml_attempts"] += int(bank_write)
        ledger["share_table_dml_attempts"] += int(share_write)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if all_shares and fail_all_shares:
            raise RuntimeError("synthetic personal-bank all-shares failure")

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield ledger
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        ledger["statement_count"] = len(ledger["statements"])
        ledger["classified_attempt_count"] = (
            ledger["select_attempts"] + ledger["dml_attempts"]
            + ledger["ddl_attempts"] + ledger["other_attempts"]
        )
        ledger["personal_bank_query_sequence"] = [
            item["classification"] for item in ledger["statements"]
            if item["classification"] == "personal_bank_all_shares_select"
        ]
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


def user_identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    columns = (
        "id", "username", "is_admin", "is_subject_admin",
        "is_notification_admin", "is_locked", "session_version",
    )
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM users "
        "WHERE id IN (:owner, :other, :revoked) ORDER BY id"
    ), ACTORS).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "columns": list(columns),
        "column_count": len(columns),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def user_activity_snapshot(db: Any) -> tuple[dict[int, Any], list[dict[str, Any]]]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        "SELECT id, last_active FROM users "
        "WHERE id IN (:owner, :other, :revoked) ORDER BY id"
    ), ACTORS).fetchall()
    raw = {int(row[0]): row[1] for row in rows}
    recorded = [
        {
            "user_id": user_id,
            "last_active": None if value is None else "<database-current-timestamp>",
        }
        for user_id, value in sorted(raw.items())
    ]
    return raw, recorded


def matrix_attestation() -> dict[str, Any]:
    payload = MATRIX.read_bytes()
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
    route_ids = {route["route_id"] for route in ROUTES.values()}
    selected = [row for row in rows if row["route_id"] in route_ids]
    if len(selected) != 2:
        raise AssertionError("personal-bank all-shares routes are missing or duplicated")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "selected_rows_sha256": sha256_json(selected),
        "selected_rows": selected,
        "caller_inventory_complete": False,
        "caller_authority": "personal-bank-all-shares-callers.json",
    }


def key_source_attestation(archived: Any) -> dict[str, dict[str, Any]]:
    object_format = archived.attestation["git_object_format"]
    result: dict[str, dict[str, Any]] = {}
    for path in KEY_SOURCE_FILES:
        payload = (archived.root / path).read_bytes()
        result[path] = {
            "git_blob": pinned_source._git_blob_id(payload, object_format),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    return result


def caller_evidence_reference() -> dict[str, Any]:
    payload = CALLERS.read_bytes()
    document = json.loads(payload.decode("utf-8"))
    if document.get("legacy_commit") != pinned_source.LEGACY_COMMIT:
        raise AssertionError("all-shares caller evidence legacy commit drifted")
    closure = document.get("closure", {})
    if not closure.get("caller_attestation_complete"):
        raise AssertionError("all-shares caller evidence is not closed")
    route_ids = {route["route_id"] for route in document.get("routes", [])}
    if route_ids != {route["route_id"] for route in ROUTES.values()}:
        raise AssertionError("all-shares caller evidence route set drifted")
    return {
        "path": "docs/refactor/phase4b/personal-bank-all-shares-callers.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "attestation_sha256": document["attestation_sha256"],
        "document_payload_sha256": document["document_payload_sha256"],
        "caller_attestation_complete": True,
    }


def bank_rows() -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    return [
        {
            "id": BANKS["owner_active"], "user_id": ACTORS["owner"],
            "name": "owner bank 高数・α／🧪", "status": 1,
            "created_at": fixed, "updated_at": fixed,
        },
        {
            "id": BANKS["other_active"], "user_id": ACTORS["other"],
            "name": "", "status": 1,
            "created_at": fixed, "updated_at": fixed,
        },
        {
            "id": BANKS["inactive"], "user_id": ACTORS["owner"],
            "name": "inactive bank", "status": 0,
            "created_at": fixed, "updated_at": fixed,
        },
        {
            "id": BANKS["null_status"], "user_id": ACTORS["owner"],
            "name": "null status bank", "status": None,
            "created_at": fixed, "updated_at": fixed,
        },
        {
            "id": BANKS["status_two"], "user_id": ACTORS["owner"],
            "name": "status two bank", "status": 2,
            "created_at": fixed, "updated_at": fixed,
        },
    ]


def full_share_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": SHARES["null_created"],
            "bank_id": BANKS["owner_active"], "owner_id": ACTORS["owner"],
            "share_code": None, "share_token": None, "permission": None,
            "expires_at": None, "max_uses": None, "current_uses": None,
            "is_active": None, "created_at": None,
        },
        {
            "id": SHARES["special_token_inactive_expired"],
            "bank_id": BANKS["owner_active"], "owner_id": ACTORS["owner"],
            "share_code": "ZERO0A", "share_token": "raw&?/#+ token",
            "permission": "copy", "expires_at": datetime(2020, 1, 1),
            "max_uses": 1, "current_uses": 99, "is_active": False,
            "created_at": datetime(2026, 7, 17, 12, 0, 0),
        },
        {
            "id": SHARES["empty_token_cross_bank_owner"],
            "bank_id": BANKS["other_active"], "owner_id": ACTORS["owner"],
            "share_code": "EMPTY2", "share_token": "",
            "permission": "unexpected-value", "expires_at": None,
            "max_uses": -1, "current_uses": -2, "is_active": True,
            "created_at": datetime(2026, 7, 17, 11, 0, 0),
        },
        {
            "id": SHARES["ordinary"],
            "bank_id": BANKS["owner_active"], "owner_id": ACTORS["owner"],
            "share_code": None, "share_token": "ordinary-token-0003",
            "permission": "read", "expires_at": datetime(2027, 1, 1),
            "max_uses": 5, "current_uses": 2, "is_active": True,
            "created_at": datetime(2026, 7, 17, 10, 0, 0),
        },
        {
            "id": SHARES["inactive_bank"],
            "bank_id": BANKS["inactive"], "owner_id": ACTORS["owner"],
            "share_code": "INACT4", "share_token": "inactive-bank-token",
            "permission": "read", "expires_at": None, "max_uses": None,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 15, 0, 0),
        },
        {
            "id": SHARES["null_status_bank"],
            "bank_id": BANKS["null_status"], "owner_id": ACTORS["owner"],
            "share_code": "NULLS5", "share_token": "null-status-token",
            "permission": "read", "expires_at": None, "max_uses": None,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 14, 0, 0),
        },
        {
            "id": SHARES["status_two_bank"],
            "bank_id": BANKS["status_two"], "owner_id": ACTORS["owner"],
            "share_code": "TWO006", "share_token": "status-two-token",
            "permission": "read", "expires_at": None, "max_uses": None,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 13, 0, 0),
        },
        {
            "id": SHARES["other_owner"],
            "bank_id": BANKS["owner_active"], "owner_id": ACTORS["other"],
            "share_code": "OTHER7", "share_token": "other-owner-token",
            "permission": "read", "expires_at": None, "max_uses": 0,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 16, 0, 0),
        },
    ]


def share_rows(mode: str) -> list[dict[str, Any]]:
    if mode == "full":
        return full_share_rows()
    if mode == "empty":
        return []
    raise AssertionError(f"unknown all-shares fixture mode: {mode}")


def seed_static_actors(db: Any, User: Any) -> None:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4b_all_shares_{actor}",
            email=f"phase4b_all_shares_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=False,
            is_subject_admin=False,
            is_notification_admin=False,
            is_locked=False,
            session_version=12 if actor == "revoked" else 11,
            created_at=fixed,
            last_active=None,
        ))
    db.session.commit()


def reset_case_facts(db: Any, mode: str) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    db.session.execute(text("DELETE FROM bank_shares"))
    db.session.execute(text("DELETE FROM user_question_banks"))
    banks = bank_rows()
    bank_columns = tuple(banks[0])
    db.session.execute(text(
        "INSERT INTO user_question_banks "
        f"({', '.join(bank_columns)}) VALUES "
        f"({', '.join(':' + column for column in bank_columns)})"
    ), banks)
    shares = share_rows(mode)
    if shares:
        share_columns = tuple(shares[0])
        db.session.execute(text(
            "INSERT INTO bank_shares "
            f"({', '.join(share_columns)}) VALUES "
            f"({', '.join(':' + column for column in share_columns)})"
        ), shares)
    db.session.execute(text(
        "UPDATE users SET last_active = NULL "
        "WHERE id IN (:owner, :other, :revoked)"
    ), ACTORS)
    db.session.commit()
    return {
        "banks": table_fingerprint(db, "user_question_banks"),
        "shares": table_fingerprint(db, "bank_shares"),
    }


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction(base_url=f"http://{FALLBACK_HOST}") as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4b_all_shares_{actor}",
            "session_version": 11,
            "is_admin": False,
            "is_subject_admin": False,
            "is_notification_admin": False,
        })


def recorded_request_headers(spec: CaseSpec) -> dict[str, str]:
    result = {
        "Accept": spec.accept,
        "Host": FALLBACK_HOST,
        "X-Request-ID": FIXED_REQUEST_ID,
    }
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer <redacted-invalid-synthetic-jwt>"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    return result


def live_request_headers(spec: CaseSpec, tokens: dict[str, str]) -> dict[str, str]:
    result = {
        "Accept": spec.accept,
        "X-Request-ID": FIXED_REQUEST_ID,
    }
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer synthetic-invalid-token"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer " + tokens[spec.bearer_actor]
    return result


def capture_case(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
    spec: CaseSpec,
) -> dict[str, Any]:
    set_actor_session(client, spec.session_actor)
    reset_limiters(client.application)
    with client.application.app_context():
        expected = reset_case_facts(db, spec.fixture_mode)
        banks_before = table_fingerprint(db, "user_question_banks")
        shares_before = table_fingerprint(db, "bank_shares")
        identity_before = user_identity_fingerprint(db)
        raw_activity_before, activity_before = user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    route = ROUTES[spec.route]
    query_string = urlencode(spec.query)
    target = route["path"] + ("?" + query_string if query_string else "")
    missing = object()
    original_share_base = client.application.config.pop("SHARE_BASE_URL", missing)
    if spec.configured_share_base:
        client.application.config["SHARE_BASE_URL"] = CONFIGURED_SHARE_BASE_URL
    try:
        with sql_probe(engine, fail_all_shares=spec.fail_all_shares) as sql:
            response = client.get(
                target,
                headers=live_request_headers(spec, tokens),
                base_url=f"http://{FALLBACK_HOST}",
                environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
                follow_redirects=False,
            )
    finally:
        client.application.config.pop("SHARE_BASE_URL", None)
        if original_share_base is not missing:
            client.application.config["SHARE_BASE_URL"] = original_share_base
    with client.application.app_context():
        try:
            db.session.rollback()
        finally:
            db.session.remove()
        banks_after = table_fingerprint(db, "user_question_banks")
        shares_after = table_fingerprint(db, "bank_shares")
        identity_after = user_identity_fingerprint(db)
        raw_activity_after, activity_after = user_activity_snapshot(db)
        db.session.remove()
    changed_activity_ids = sorted(
        user_id for user_id in raw_activity_before
        if raw_activity_before[user_id] != raw_activity_after[user_id]
    )
    return {
        "case_id": spec.case_id,
        "route_id": route["route_id"],
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or (
            "invalid" if spec.invalid_bearer else "none"
        ),
        "credential_mode": credential_mode(spec),
        "fixture_mode": spec.fixture_mode,
        "share_base_mode": "configured" if spec.configured_share_base else "host_fallback",
        "request": {
            "method": "GET",
            "path": route["path"],
            "route_template": route["route_template"],
            "query": [list(item) for item in spec.query],
            "query_string": query_string,
            "headers": recorded_request_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "response": normalized_response(response),
        "observed_get_effects": {
            "sql": sql,
            "banks_before": banks_before,
            "banks_after": banks_after,
            "banks_match_case_fixture": banks_before == expected["banks"],
            "banks_unchanged": banks_before == banks_after,
            "shares_before": shares_before,
            "shares_after": shares_after,
            "shares_match_case_fixture": shares_before == expected["shares"],
            "shares_unchanged": shares_before == shares_after,
            "users_identity_before": identity_before,
            "users_identity_after": identity_after,
            "users_identity_unchanged": identity_before == identity_after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def response_shares(case: dict[str, Any]) -> list[dict[str, Any]]:
    body = case["response"]["body"]
    if not isinstance(body, dict):
        raise AssertionError(f"{case['case_id']} response is not an object")
    data = body.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("shares"), list):
        raise AssertionError(f"{case['case_id']} all-shares envelope drifted")
    return data["shares"]


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 20 or len(cases) != 20 or len(by_id) != 20:
        raise AssertionError("personal-bank all-shares case set must contain 20 unique cases")
    base_fields = {
        "id", "bank_id", "owner_id", "share_code", "share_token",
        "permission", "expires_at", "max_uses", "current_uses",
        "is_active", "created_at", "bank_name",
    }

    for spec in CASE_SPECS:
        case = by_id[spec.case_id]
        response = case["response"]
        effects = case["observed_get_effects"]
        sql = effects["sql"]
        if response["status"] != spec.expected_status:
            raise AssertionError(
                f"{spec.case_id} status drifted: expected={spec.expected_status} "
                f"observed={response['status']} body={response['body']}"
            )
        if not effects["banks_match_case_fixture"] or not effects["shares_match_case_fixture"]:
            raise AssertionError(f"{spec.case_id} did not start from its isolated fixture")
        if not effects["banks_unchanged"] or not effects["shares_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed personal-bank business facts")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed user identity facts")
        if effects["shares_before"]["column_count"] != 11:
            raise AssertionError(f"{spec.case_id} lost the eleven-column bank_shares row")
        if sql["bank_table_dml_attempts"] or sql["share_table_dml_attempts"]:
            raise AssertionError(f"{spec.case_id} attempted personal-bank DML")
        if sql["ddl_attempts"]:
            raise AssertionError(f"{spec.case_id} attempted request DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")
        if sql["all_shares_select_attempts"] != spec.expected_query_attempts:
            raise AssertionError(f"{spec.case_id} all-shares query boundary drifted")
        if spec.expected_query_attempts and sql["all_shares_select_bind_count"] != 1:
            raise AssertionError(f"{spec.case_id} must bind only the viewer owner id")
        if sql["personal_bank_query_sequence"] != (
            ["personal_bank_all_shares_select"] * spec.expected_query_attempts
        ):
            raise AssertionError(f"{spec.case_id} query sequence drifted")

        expected_activity: list[int] = []
        if spec.session_actor is not None and spec.bearer_actor is None:
            expected_activity = [ACTORS[spec.session_actor]]
        if effects["user_last_active_changed_user_ids"] != expected_activity:
            raise AssertionError(
                f"{spec.case_id} last_active drifted: expected={expected_activity} "
                f"observed={effects['user_last_active_changed_user_ids']}"
            )
        if sql["user_last_active_dml_attempts"] != len(expected_activity):
            raise AssertionError(f"{spec.case_id} last_active SQL ledger drifted")

    owner_order = [
        SHARES["special_token_inactive_expired"],
        SHARES["empty_token_cross_bank_owner"],
        SHARES["ordinary"],
        SHARES["null_created"],
    ]
    other_order = [SHARES["other_owner"]]
    fallback_prefix = f"http://{FALLBACK_HOST}/bank/join?token="
    configured_prefix = CONFIGURED_SHARE_BASE_URL + "/bank/join?token="
    owner_successes = (
        "auth-session-mixed-api-alias",
        "auth-bearer-api-alias",
        "auth-invalid-bearer-falls-back-session-api-alias",
        "data-query-parameters-ignored-api-alias",
        "auth-session-mixed-web-alias",
        "auth-invalid-bearer-falls-back-session-web-alias",
        "data-query-parameters-ignored-web-alias",
    )
    for case_id in owner_successes:
        body = by_id[case_id]["response"]["body"]
        if body.get("code") != 0 or body.get("status") != "success":
            raise AssertionError(f"{case_id} success envelope drifted")
        rows = response_shares(by_id[case_id])
        if [row["id"] for row in rows] != owner_order:
            raise AssertionError(f"{case_id} SQLite owner order/filter drifted")
        for row in rows:
            expected_fields = base_fields | ({"share_link"} if row["share_token"] else set())
            if set(row) != expected_fields:
                raise AssertionError(f"{case_id} row field set drifted: {row}")
        if rows[0]["share_link"] != fallback_prefix + "raw&?/#+ token":
            raise AssertionError(f"{case_id} Host fallback/raw token link drifted")
        if "share_link" in rows[1] or rows[1]["bank_name"] != "":
            raise AssertionError(f"{case_id} empty token/bank name semantics drifted")
        if rows[0]["is_active"] != 0 or not str(rows[0]["expires_at"]).startswith("2020"):
            raise AssertionError(f"{case_id} filtered inactive/expired share")
        if rows[-1]["created_at"] is not None:
            raise AssertionError(f"{case_id} lost nullable row or SQLite NULL-last order")

    precedence = response_shares(
        by_id["auth-bearer-precedes-session-api-alias"]
    )
    if [row["id"] for row in precedence] != other_order:
        raise AssertionError("valid bearer must precede the Session identity on /api")
    if precedence[0]["share_link"] != fallback_prefix + "other-owner-token":
        raise AssertionError("bearer actor share link drifted")

    configured = response_shares(by_id["data-configured-share-base-api-alias"])
    if [row["id"] for row in configured] != owner_order:
        raise AssertionError("configured SHARE_BASE_URL case changed row selection")
    if configured[0]["share_link"] != configured_prefix + "raw&?/#+ token":
        raise AssertionError("configured SHARE_BASE_URL slash/token semantics drifted")

    for route in ROUTES:
        if response_shares(by_id[f"data-empty-{route}"]) != []:
            raise AssertionError(f"data-empty-{route} must return shares=[]")
        baseline = response_shares(by_id[f"auth-session-mixed-{route}"])
        ignored = by_id[f"data-query-parameters-ignored-{route}"]
        if ignored["request"]["query"] != [
            ["active", "1"], ["sort", "asc"], ["page", "2"], ["page", "3"],
        ] or response_shares(ignored) != baseline:
            raise AssertionError(f"data-query-parameters-ignored-{route} drifted")

    anonymous_api = by_id["auth-anonymous-api-alias"]
    if anonymous_api["response"]["body_kind"] != "json":
        raise AssertionError("/api anonymous response must be JSON")
    invalid_state = by_id["auth-state-invalid-bearer-api-alias"]
    invalid_body = invalid_state["response"]["body"]
    if invalid_body.get("status") != "unauthorized" or "会话已失效" not in invalid_body.get("message", ""):
        raise AssertionError("state-invalid bearer response drifted")
    for case_id in (
        "auth-bearer-web-alias",
        "auth-bearer-precedes-session-web-alias",
        "auth-anonymous-web-alias",
    ):
        if by_id[case_id]["response"]["headers"].get("Location") != ["/login"]:
            raise AssertionError(f"{case_id} must redirect to /login")

    for route in ROUTES:
        default = by_id[f"fault-default-{route}"]
        json_fault = by_id[f"fault-json-{route}"]
        if "synthetic personal-bank" in default["response"]["body_text"]:
            raise AssertionError(f"fault-default-{route} leaked the injected failure")
        if "synthetic personal-bank" in json_fault["response"]["body_text"]:
            raise AssertionError(f"fault-json-{route} leaked the injected failure")
        expected_default_kind = "json" if route == "api-alias" else "text"
        if default["response"]["body_kind"] != expected_default_kind:
            raise AssertionError(f"fault-default-{route} negotiation drifted")
        if json_fault["response"]["body_kind"] != "json":
            raise AssertionError(f"fault-json-{route} must be safe JSON")
    safe_json_500 = {
        "status": "error",
        "message": "An unexpected server error occurred.",
        "status_code": 500,
        "payload": None,
        "request_id": FIXED_REQUEST_ID,
    }
    for case_id in (
        "fault-default-api-alias",
        "fault-json-api-alias",
        "fault-json-web-alias",
    ):
        if by_id[case_id]["response"]["body"] != safe_json_500:
            raise AssertionError(f"{case_id} safe JSON 500 envelope drifted")


def capture_document(legacy_root: Path) -> dict[str, Any]:
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "frozen_route_matrix": matrix_attestation(),
            "key_sources": key_source_attestation(archived),
            "complete_caller_attestation": caller_evidence_reference(),
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4b-personal-bank-all-shares-data-"
        ) as data_dir:
            with capture_environment(data_dir):
                with pinned_source.archived_legacy_import_environment(archived.root):
                    import app as legacy_app
                    from app.core.extensions import db
                    from app.core.utils.jwt_utils import generate_jwt_token
                    from app.models.user import User

                    pinned_source.assert_module_from_archive(legacy_app, archived.root)
                    previous_logging = logging.root.manager.disable
                    logging.disable(logging.CRITICAL)
                    legacy_app._start_background_tasks = lambda _app: None
                    app = legacy_app.create_app("testing")
                    app.config.update(
                        JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                        LAST_ACTIVE_UPDATE_INTERVAL_SECONDS=60,
                        PROPAGATE_EXCEPTIONS=False,
                        RATELIMIT_ENABLED=False,
                        TESTING=True,
                    )
                    try:
                        with app.app_context():
                            db.create_all()
                            seed_static_actors(db, User)
                            full_fixture = reset_case_facts(db, "full")
                            tokens = {
                                actor: generate_jwt_token(
                                    user_id=user_id,
                                    openid="",
                                    session_version=11,
                                )
                                for actor, user_id in ACTORS.items()
                            }
                            db.session.remove()
                        client = app.test_client()
                        cases = [
                            capture_case(client, db, legacy_app, tokens, spec)
                            for spec in CASE_SPECS
                        ]
                        assert_case_contracts(cases)
                    finally:
                        logging.disable(previous_logging)
                        with app.app_context():
                            db.session.remove()

        document: dict[str, Any] = {
            "contract_id": "ti.phase4b.personal-bank-all-shares-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-17",
            "legacy_commit": pinned_source.LEGACY_COMMIT,
            "legacy_source_attestation": source_attestation,
            "route_status": {
                "target_internal_owner": "personalbank",
                "http_owner": "personalbank",
                "migration_status": "pending",
                "production_cutover": False,
                "routes": ROUTES,
                "controller_added": False,
                "openapi_delta": False,
                "route_delta": False,
            },
            "legacy_query": {
                "shape": "single joined all-shares select",
                "sql": (
                    "SELECT bs.*, b.name as bank_name FROM bank_shares bs "
                    "JOIN user_question_banks b ON bs.bank_id = b.id "
                    "WHERE bs.owner_id = :uid AND b.status = 1 "
                    "ORDER BY bs.created_at DESC"
                ),
                "binds": ["uid"],
                "statement_count": 1,
                "pagination": None,
                "query_parameters": "ignored",
                "secondary_sort": None,
            },
            "response_contract": {
                "success_envelope": "code=0,status=success,data.shares=array",
                "raw_selected_columns": [
                    "id", "bank_id", "owner_id", "share_code", "share_token",
                    "permission", "expires_at", "max_uses", "current_uses",
                    "is_active", "created_at", "bank_name",
                ],
                "conditional_field": "share_link only when share_token is Python-truthy",
                "filters_not_present": [
                    "bank.user_id", "share.is_active", "share.expires_at",
                    "share.permission", "share.max_uses", "share.current_uses",
                ],
                "ordering": "created_at DESC only; no stable tie-breaker",
                "empty": "HTTP 200 with data.shares=[]",
            },
            "share_link_contract": {
                "base_expression": (
                    "current_app.config.get('SHARE_BASE_URL', "
                    "request.host_url.rstrip('/'))"
                ),
                "link_expression": "f'{base_url}/bank/join?token={share_token}'",
                "fallback_host": FALLBACK_HOST,
                "fallback_prefix": f"http://{FALLBACK_HOST}/bank/join?token=",
                "configured_value": CONFIGURED_SHARE_BASE_URL,
                "configured_prefix": CONFIGURED_SHARE_BASE_URL + "/bank/join?token=",
                "normalizes_configured_trailing_slash": False,
                "url_encodes_token": False,
                "falsey_token_omits_key": True,
            },
            "authentication_contract": {
                "api_alias": (
                    "valid bearer is accepted and precedes Session; invalid bearer falls back "
                    "to Session; anonymous is JSON 401; state-invalid bearer is 401"
                ),
                "web_alias": (
                    "Session is accepted; any decodable bearer bypasses the Session branch and "
                    "is redirected to /login before the route decorator; invalid bearer falls "
                    "back to Session; anonymous redirects to /login"
                ),
                "session_side_effect": (
                    "surrounding auth may commit users.last_active before the read or its fault"
                ),
                "bearer_side_effect": "valid JWT does not update users.last_active",
            },
            "failure_contract": {
                "api_default": "safe JSON 500",
                "web_default": "generic Chinese HTML 500",
                "accept_application_json_prefix": "safe JSON 500",
                "injected_exception_redacted": True,
            },
            "request_effect_scope": {
                "handler": "one SELECT-only statement",
                "personal_bank_business_tables": "unchanged",
                "surrounding_web_session": (
                    "may SELECT users/system_config and commit users.last_active"
                ),
            },
            "dialect_observation": {
                "sqlite_capture": (
                    "raw SQLite text queries expose booleans as 0/1 and datetime values as raw "
                    "YYYY-MM-DD strings; DESC places NULL last"
                ),
                "postgresql_target": (
                    "PostgreSQL DESC places NULL first by default and returns native "
                    "boolean/datetime values"
                ),
                "migration_rule": (
                    "preserve PostgreSQL DESC NULLS FIRST and do not invent an id tie-breaker"
                ),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory limiter; synthetic identities; no current worktree legacy import"
            ),
            "redaction": (
                "JWT, password hash, session-cookie values and database-current last_active "
                "timestamps are omitted or represented by deterministic placeholders"
            ),
            "fixture": {
                "actors": ACTORS,
                "banks": BANKS,
                "shares": SHARES,
                "full_banks_fingerprint": full_fixture["banks"],
                "full_shares_fingerprint": full_fixture["shares"],
                "owner_returned_count": 4,
                "other_returned_count": 1,
                "excluded_bank_status_count": 3,
                "excluded_other_owner_count": 1,
                "inactive_expired_returned_count": 1,
                "null_created_at_returned_count": 1,
            },
            "case_count": len(cases),
            "case_payload_sha256": sha256_json(cases),
            "cases": cases,
        }
        document["document_payload_sha256"] = document_payload_sha256(document)
        return document


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        f"captured {document['case_count']} personal-bank all-shares cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
