#!/usr/bin/env python3
"""Capture deterministic dual-alias personal-bank share-list read goldens."""

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
import re
import sys
import tempfile
from typing import Any, Iterator
from urllib.parse import urlencode


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-share-list-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_category_goldens as base  # noqa: E402


pinned_source = base.pinned_source
FIXED_REQUEST_ID = "phase4b-personal-bank-share-list-golden-request"
ROUTES = {
    "api-alias": {
        "route_id": "e817f8083d74",
        "path_template": "/api/user/banks/api/{bank_id}/shares",
        "route_template": "/api/user/banks/api/<int:bank_id>/shares",
        "legacy_handler": "user_bank_api_root.user_bank_api.get_shares",
        "registration_kind": "blueprint_compatibility_alias",
    },
    "web-alias": {
        "route_id": "c50102968322",
        "path_template": "/user/banks/api/{bank_id}/shares",
        "route_template": "/user/banks/api/<int:bank_id>/shares",
        "legacy_handler": "user_bank.user_bank_api.get_shares",
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
    "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
)
ACTORS = {
    "owner": 98001,
    "other": 98002,
}
BANKS = {
    "zero": 0,
    "owner": 98101,
    "inactive": 98102,
    "null_status": 98103,
    "status_two": 98104,
    "other_owner": 98105,
    "nullable": 98106,
    "missing": 98999,
    "negative_path": -1,
}
SHARES = {
    "null_created_cross_owner": -2,
    "newest": 0,
    "inactive": 98201,
    "expired_cross_owner": 98202,
    "oldest_active": 98203,
    "other_bank": 98204,
    "zero_bank": 98205,
    "nullable": 98206,
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    bank: str = "owner"
    session_actor: str | None = "owner"
    bearer_actor: str | None = None
    invalid_bearer: bool = False
    accept: str = "*/*"
    fixture_mode: str = "full"
    query: tuple[tuple[str, str], ...] = ()
    fail_owner_probe: bool = False
    fail_share_list: bool = False
    expected_status: int = 200
    expected_probe_attempts: int = 1
    expected_share_list_attempts: int = 1


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        anonymous_status = 401 if route == "api-alias" else 302
        bearer_status = 200 if route == "api-alias" else 302
        bearer_probe = 1 if route == "api-alias" else 0
        bearer_list = 1 if route == "api-alias" else 0
        specs.extend((
            CaseSpec(f"auth-session-owner-{route}", route),
            CaseSpec(
                f"auth-bearer-owner-{route}", route,
                session_actor=None,
                bearer_actor="owner",
                expected_status=bearer_status,
                expected_probe_attempts=bearer_probe,
                expected_share_list_attempts=bearer_list,
            ),
            CaseSpec(
                f"auth-session-other-{route}", route,
                session_actor="other",
                expected_status=404,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"auth-bearer-precedes-session-{route}", route,
                session_actor="other",
                bearer_actor="owner",
                expected_status=bearer_status,
                expected_probe_attempts=bearer_probe,
                expected_share_list_attempts=bearer_list,
            ),
            CaseSpec(
                f"auth-invalid-bearer-falls-back-session-{route}", route,
                invalid_bearer=True,
            ),
            CaseSpec(
                f"auth-anonymous-{route}", route,
                session_actor=None,
                expected_status=anonymous_status,
                expected_probe_attempts=0,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"data-empty-{route}", route,
                fixture_mode="empty",
            ),
            CaseSpec(
                f"data-query-parameters-ignored-{route}", route,
                query=(("active", "1"), ("sort", "asc"),
                       ("page", "2"), ("page", "3")),
            ),
            CaseSpec(
                f"data-nullable-fields-{route}", route,
                bank="nullable",
                fixture_mode="nullable",
            ),
            CaseSpec(f"bank-zero-{route}", route, bank="zero"),
            CaseSpec(
                f"bank-inactive-{route}", route,
                bank="inactive",
                expected_status=404,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"bank-null-status-{route}", route,
                bank="null_status",
                expected_status=404,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"bank-status-two-{route}", route,
                bank="status_two",
                expected_status=404,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"bank-other-owner-{route}", route,
                bank="other_owner",
                expected_status=404,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"bank-missing-{route}", route,
                bank="missing",
                expected_status=404,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"bank-negative-path-{route}", route,
                bank="negative_path",
                expected_status=404,
                expected_probe_attempts=0,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"fault-owner-probe-default-{route}", route,
                fail_owner_probe=True,
                expected_status=500,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"fault-owner-probe-json-{route}", route,
                accept="application/json",
                fail_owner_probe=True,
                expected_status=500,
                expected_share_list_attempts=0,
            ),
            CaseSpec(
                f"fault-share-list-default-{route}", route,
                fail_share_list=True,
                expected_status=500,
            ),
            CaseSpec(
                f"fault-share-list-json-{route}", route,
                accept="application/json",
                fail_share_list=True,
                expected_status=500,
            ),
        ))
    return tuple(specs)


CASE_SPECS = build_case_specs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


canonical_json = base.canonical_json
sha256_json = base.sha256_json
document_payload_sha256 = base.document_payload_sha256
render_document = base.render_document
normalized_value = base.normalized_value
normalized_sql = base.normalized_sql
is_select_statement = base.is_select_statement
is_dml_statement = base.is_dml_statement
is_ddl_statement = base.is_ddl_statement
reads_table = base.reads_table
is_table_dml = base.is_table_dml
is_user_last_active_dml = base.is_user_last_active_dml
table_fingerprint = base.table_fingerprint
reset_limiters = base.reset_limiters
response_headers = base.response_headers
normalized_response = base.normalized_response
credential_mode = base.credential_mode


def is_owner_status_probe(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return (
        sql.startswith("SELECT ID FROM USER_QUESTION_BANKS")
        and "WHERE ID =" in sql
        and "AND USER_ID =" in sql
        and "AND STATUS = 1" in sql
        and "JOIN" not in sql
    )


def is_share_list_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return (
        sql.startswith("SELECT * FROM BANK_SHARES")
        and "WHERE BANK_ID =" in sql
        and sql.endswith("ORDER BY CREATED_AT DESC")
        and "JOIN" not in sql
    )


def bind_count(parameters: Any) -> int:
    if isinstance(parameters, Mapping):
        return len(parameters)
    if isinstance(parameters, (list, tuple)):
        return len(parameters)
    return 0 if parameters is None else 1


@contextmanager
def sql_probe(
    engine: Any,
    *,
    fail_owner_probe: bool,
    fail_share_list: bool,
) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "owner_status_probe_attempts": 0,
        "owner_status_probe_bind_count": 0,
        "share_list_select_attempts": 0,
        "share_list_select_bind_count": 0,
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
        owner_probe = is_owner_status_probe(statement)
        share_list = is_share_list_select(statement)
        bank_write = is_table_dml(statement, "user_question_banks")
        share_write = is_table_dml(statement, "bank_shares")
        activity_write = is_user_last_active_dml(statement)
        if owner_probe:
            classification = "personal_bank_owner_status_probe"
        elif share_list:
            classification = "personal_bank_share_list_select"
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
        ledger["owner_status_probe_attempts"] += int(owner_probe)
        ledger["owner_status_probe_bind_count"] += bind_count(parameters) if owner_probe else 0
        ledger["share_list_select_attempts"] += int(share_list)
        ledger["share_list_select_bind_count"] += bind_count(parameters) if share_list else 0
        ledger["bank_table_dml_attempts"] += int(bank_write)
        ledger["share_table_dml_attempts"] += int(share_write)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if owner_probe and fail_owner_probe:
            raise RuntimeError("synthetic personal-bank owner probe failure")
        if share_list and fail_share_list:
            raise RuntimeError("synthetic personal-bank share list failure")

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
        business_sequence = [
            statement["classification"]
            for statement in ledger["statements"]
            if statement["classification"] in {
                "personal_bank_owner_status_probe",
                "personal_bank_share_list_select",
            }
        ]
        ledger["personal_bank_query_sequence"] = business_sequence
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


def user_identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    columns = (
        "id", "username", "is_admin", "is_subject_admin",
        "is_notification_admin", "is_locked", "session_version",
    )
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM users "
        "WHERE id IN (:owner, :other) ORDER BY id"
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
        "WHERE id IN (:owner, :other) ORDER BY id"
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
    selected = [row for row in rows if row["route_id"] in {
        route["route_id"] for route in ROUTES.values()
    }]
    if len(selected) != 2:
        raise AssertionError("personal-bank share-list routes are missing or duplicated")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "selected_rows_sha256": sha256_json(selected),
        "selected_rows": selected,
        "caller_inventory_complete": False,
        "caller_authority": "personal-bank-share-list-callers.json",
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
    if not document["closure"]["caller_attestation_complete"]:
        raise AssertionError("share-list caller evidence is not closed")
    return {
        "path": "docs/refactor/phase4b/personal-bank-share-list-callers.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "attestation_sha256": document["attestation_sha256"],
        "document_payload_sha256": document["document_payload_sha256"],
        "caller_attestation_complete": True,
    }


def bank_rows() -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    return [
        {
            "id": BANKS["zero"], "user_id": ACTORS["owner"],
            "name": "zero bank", "status": 1,
            "created_at": fixed, "updated_at": fixed,
        },
        {
            "id": BANKS["owner"], "user_id": ACTORS["owner"],
            "name": "owner bank 高数・α／🧪", "status": 1,
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
        {
            "id": BANKS["other_owner"], "user_id": ACTORS["other"],
            "name": "other owner bank", "status": 1,
            "created_at": fixed, "updated_at": fixed,
        },
        {
            "id": BANKS["nullable"], "user_id": ACTORS["owner"],
            "name": "nullable share bank", "status": 1,
            "created_at": fixed, "updated_at": fixed,
        },
    ]


def full_share_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": SHARES["null_created_cross_owner"],
            "bank_id": BANKS["owner"], "owner_id": ACTORS["other"],
            "share_code": None, "share_token": None, "permission": None,
            "expires_at": None, "max_uses": None, "current_uses": None,
            "is_active": None, "created_at": None,
        },
        {
            "id": SHARES["newest"],
            "bank_id": BANKS["owner"], "owner_id": ACTORS["owner"],
            "share_code": "ZERO0A", "share_token": "token-newest-00000001",
            "permission": "read", "expires_at": None, "max_uses": None,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 12, 0, 0),
        },
        {
            "id": SHARES["inactive"],
            "bank_id": BANKS["owner"], "owner_id": ACTORS["owner"],
            "share_code": "OFF002", "share_token": "token-inactive-000002",
            "permission": "copy", "expires_at": datetime(2027, 1, 1),
            "max_uses": 5, "current_uses": 2, "is_active": False,
            "created_at": datetime(2026, 7, 17, 11, 0, 0),
        },
        {
            "id": SHARES["expired_cross_owner"],
            "bank_id": BANKS["owner"], "owner_id": ACTORS["other"],
            "share_code": "OLD003", "share_token": "token-expired-000003",
            "permission": "read", "expires_at": datetime(2020, 1, 1),
            "max_uses": 1, "current_uses": 99, "is_active": True,
            "created_at": datetime(2026, 7, 17, 10, 0, 0),
        },
        {
            "id": SHARES["oldest_active"],
            "bank_id": BANKS["owner"], "owner_id": ACTORS["owner"],
            "share_code": "LIVE04", "share_token": "token-oldest-00000004",
            "permission": "unexpected-value", "expires_at": None,
            "max_uses": -1, "current_uses": -2, "is_active": True,
            "created_at": datetime(2026, 7, 17, 9, 0, 0),
        },
        {
            "id": SHARES["other_bank"],
            "bank_id": BANKS["other_owner"], "owner_id": ACTORS["other"],
            "share_code": "OTHER5", "share_token": "token-other-bank-00005",
            "permission": "read", "expires_at": None, "max_uses": None,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 13, 0, 0),
        },
        {
            "id": SHARES["zero_bank"],
            "bank_id": BANKS["zero"], "owner_id": ACTORS["owner"],
            "share_code": "ZERO06", "share_token": "token-zero-bank-00006",
            "permission": "read", "expires_at": None, "max_uses": 0,
            "current_uses": 0, "is_active": True,
            "created_at": datetime(2026, 7, 17, 8, 0, 0),
        },
    ]


def nullable_share_rows() -> list[dict[str, Any]]:
    return [{
        "id": SHARES["nullable"],
        "bank_id": BANKS["nullable"],
        "owner_id": ACTORS["owner"],
        "share_code": None,
        "share_token": None,
        "permission": None,
        "expires_at": None,
        "max_uses": None,
        "current_uses": None,
        "is_active": None,
        "created_at": None,
    }]


def share_rows(mode: str) -> list[dict[str, Any]]:
    if mode == "full":
        return full_share_rows()
    if mode == "empty":
        return []
    if mode == "nullable":
        return nullable_share_rows()
    raise AssertionError(f"unknown share fixture mode: {mode}")


def seed_static_actors(db: Any, User: Any) -> None:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4b_share_{actor}",
            email=f"phase4b_share_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=False,
            is_subject_admin=False,
            is_notification_admin=False,
            is_locked=False,
            session_version=11,
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
        "UPDATE users SET last_active = NULL WHERE id IN (:owner, :other)"
    ), ACTORS)
    db.session.commit()
    return {
        "banks": table_fingerprint(db, "user_question_banks"),
        "shares": table_fingerprint(db, "bank_shares"),
    }


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4b_share_{actor}",
            "session_version": 11,
            "is_admin": False,
            "is_subject_admin": False,
            "is_notification_admin": False,
        })


def recorded_request_headers(spec: CaseSpec) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer <redacted-invalid-synthetic-jwt>"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    return result


def live_request_headers(spec: CaseSpec, tokens: dict[str, str]) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
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
    bank_id = BANKS[spec.bank]
    path = route["path_template"].format(bank_id=bank_id)
    query_string = urlencode(spec.query)
    target = path + ("?" + query_string if query_string else "")
    with sql_probe(
        engine,
        fail_owner_probe=spec.fail_owner_probe,
        fail_share_list=spec.fail_share_list,
    ) as sql:
        response = client.get(
            target,
            headers=live_request_headers(spec, tokens),
            environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
            follow_redirects=False,
        )
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
        "bank_fixture": spec.bank,
        "bank_id": bank_id,
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or ("invalid" if spec.invalid_bearer else "none"),
        "credential_mode": credential_mode(spec),
        "fixture_mode": spec.fixture_mode,
        "request": {
            "method": "GET",
            "path": path,
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
        raise AssertionError(f"{case['case_id']} share-list envelope drifted")
    return data["shares"]


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 40 or len(cases) != 40 or len(by_id) != 40:
        raise AssertionError("personal-bank share-list case set must contain 40 unique cases")
    fields = {
        "id", "bank_id", "owner_id", "share_code", "share_token",
        "permission", "expires_at", "max_uses", "current_uses",
        "is_active", "created_at",
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
        if sql["bank_table_dml_attempts"] or sql["share_table_dml_attempts"] or sql["ddl_attempts"]:
            raise AssertionError(f"{spec.case_id} attempted business DML or request DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")
        if sql["owner_status_probe_attempts"] != spec.expected_probe_attempts:
            raise AssertionError(f"{spec.case_id} owner/status probe boundary drifted")
        if sql["share_list_select_attempts"] != spec.expected_share_list_attempts:
            raise AssertionError(f"{spec.case_id} share-list query boundary drifted")
        if spec.expected_probe_attempts and sql["owner_status_probe_bind_count"] != 2:
            raise AssertionError(f"{spec.case_id} owner/status probe must bind bank and viewer")
        if spec.expected_share_list_attempts and sql["share_list_select_bind_count"] != 1:
            raise AssertionError(f"{spec.case_id} share list must bind only bank")
        expected_sequence = (
            ["personal_bank_owner_status_probe"] * spec.expected_probe_attempts
            + ["personal_bank_share_list_select"] * spec.expected_share_list_attempts
        )
        if sql["personal_bank_query_sequence"] != expected_sequence:
            raise AssertionError(
                f"{spec.case_id} query sequence drifted: {sql['personal_bank_query_sequence']}"
            )

        expected_activity: list[int] = []
        if spec.session_actor is not None and spec.bearer_actor is None:
            expected_activity = [ACTORS[spec.session_actor]]
        if effects["user_last_active_changed_user_ids"] != expected_activity:
            raise AssertionError(
                f"{spec.case_id} last_active drifted: expected={expected_activity} "
                f"observed={effects['user_last_active_changed_user_ids']}"
            )
        if sql["user_last_active_dml_attempts"] != len(expected_activity):
            raise AssertionError(f"{spec.case_id} last_active ledger drifted")

    expected_owner_order = [
        SHARES["newest"], SHARES["inactive"], SHARES["expired_cross_owner"],
        SHARES["oldest_active"], SHARES["null_created_cross_owner"],
    ]
    for route in ROUTES:
        success_ids = [
            f"auth-session-owner-{route}",
            f"auth-invalid-bearer-falls-back-session-{route}",
            f"data-query-parameters-ignored-{route}",
        ]
        if route == "api-alias":
            success_ids.extend((
                f"auth-bearer-owner-{route}",
                f"auth-bearer-precedes-session-{route}",
            ))
        for case_id in success_ids:
            body = by_id[case_id]["response"]["body"]
            if body.get("code") != 0 or body.get("status") != "success":
                raise AssertionError(f"{case_id} success envelope drifted")
            rows = response_shares(by_id[case_id])
            if [row["id"] for row in rows] != expected_owner_order:
                raise AssertionError(f"{case_id} SQLite observation order drifted")
            if any(set(row) != fields for row in rows):
                raise AssertionError(f"{case_id} must expose all eleven raw share columns")
            if rows[1]["is_active"] != 0:
                raise AssertionError(f"{case_id} filtered or recast the inactive row")
            if rows[2]["owner_id"] != ACTORS["other"]:
                raise AssertionError(f"{case_id} filtered the cross-owner share row")
            if not str(rows[2]["expires_at"]).startswith("2020-01-01 00:00:00"):
                raise AssertionError(f"{case_id} filtered or changed the expired row")
            if rows[-1]["created_at"] is not None:
                raise AssertionError(f"{case_id} lost the nullable created_at row")

        if response_shares(by_id[f"data-empty-{route}"]) != []:
            raise AssertionError(f"data-empty-{route} must return an empty shares array")
        nullable = response_shares(by_id[f"data-nullable-fields-{route}"])
        if len(nullable) != 1 or any(nullable[0][field] is not None for field in (
            "share_code", "share_token", "permission", "expires_at", "max_uses",
            "current_uses", "is_active", "created_at",
        )):
            raise AssertionError(f"data-nullable-fields-{route} lost raw nullable fields")
        zero = response_shares(by_id[f"bank-zero-{route}"])
        if [row["id"] for row in zero] != [SHARES["zero_bank"]]:
            raise AssertionError(f"bank-zero-{route} must preserve bank id zero")

        for prefix in (
            "auth-session-other", "bank-inactive", "bank-null-status",
            "bank-status-two", "bank-other-owner", "bank-missing",
        ):
            body = by_id[f"{prefix}-{route}"]["response"]["body"]
            if body.get("code") != 1 or body.get("message") != "题库不存在或无权操作":
                raise AssertionError(f"{prefix}-{route} probe short-circuit envelope drifted")

        anonymous = by_id[f"auth-anonymous-{route}"]
        if route == "api-alias":
            if anonymous["response"]["body_kind"] != "json":
                raise AssertionError("/api alias anonymous response must be JSON")
        elif anonymous["response"]["headers"].get("Location") != ["/login"]:
            raise AssertionError("/user alias anonymous response must redirect to /login")
        if route == "web-alias":
            for case_id in (
                f"auth-bearer-owner-{route}",
                f"auth-bearer-precedes-session-{route}",
            ):
                if by_id[case_id]["response"]["headers"].get("Location") != ["/login"]:
                    raise AssertionError(f"{case_id} must preserve the Web alias redirect")

        for fault in (
            "fault-owner-probe-default", "fault-owner-probe-json",
            "fault-share-list-default", "fault-share-list-json",
        ):
            case = by_id[f"{fault}-{route}"]
            if "synthetic personal-bank" in case["response"]["body_text"]:
                raise AssertionError(f"{case['case_id']} leaked the injected failure")
        for fault in ("fault-owner-probe-default", "fault-share-list-default"):
            if by_id[f"{fault}-{route}"]["response"]["body_kind"] != (
                "json" if route == "api-alias" else "text"
            ):
                raise AssertionError(f"{fault}-{route} content negotiation drifted")
        for fault in ("fault-owner-probe-json", "fault-share-list-json"):
            if by_id[f"{fault}-{route}"]["response"]["body_kind"] != "json":
                raise AssertionError(f"{fault}-{route} must use safe JSON")


@contextmanager
def capture_environment(data_dir: str) -> Iterator[None]:
    updates = {
        "DATA_DIR": data_dir,
        "FLASK_ENV": "testing",
        "RATELIMIT_STORAGE_URI": "memory://",
        "RATELIMIT_STORAGE_URL": "memory://",
        "JWT_USER_STATE_CACHE_TTL_SECONDS": "0",
    }
    old = {key: os.environ.get(key) for key in (*updates, "REDIS_URL")}
    os.environ.update(updates)
    os.environ.pop("REDIS_URL", None)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def capture_document(legacy_root: Path) -> dict[str, Any]:
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "frozen_route_matrix": matrix_attestation(),
            "key_sources": key_source_attestation(archived),
            "complete_caller_attestation": caller_evidence_reference(),
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4b-personal-bank-share-list-data-"
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
                    serialized_datetime = json.loads(app.json.dumps({
                        "value": datetime(2026, 7, 17, 8, 0, 0),
                    }))["value"]
                    if serialized_datetime != "Fri, 17 Jul 2026 08:00:00 GMT":
                        raise AssertionError(
                            "archived Flask datetime JSON serialization drifted: "
                            f"{serialized_datetime}"
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
            "contract_id": "ti.phase4b.personal-bank-share-list-read-goldens",
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
            "legacy_query_sequence": {
                "shape": "owner_status_probe_then_share_list",
                "statements": [
                    {
                        "ordinal": 1,
                        "purpose": "owner_status_probe",
                        "sql": (
                            "SELECT id FROM user_question_banks WHERE id = :bank_id "
                            "AND user_id = :uid AND status = 1"
                        ),
                        "binds": ["bank_id", "uid"],
                        "no_row": "HTTP 404 and second query is not attempted",
                        "failure": "HTTP 500 and second query is not attempted",
                    },
                    {
                        "ordinal": 2,
                        "purpose": "share_list",
                        "sql": (
                            "SELECT * FROM bank_shares WHERE bank_id = :bank_id "
                            "ORDER BY created_at DESC"
                        ),
                        "binds": ["bank_id"],
                        "executed_only_after_probe_row": True,
                        "failure": "HTTP 500 after the successful probe",
                    },
                ],
                "join_authorized": False,
                "parallel_execution_authorized": False,
            },
            "response_contract": {
                "success_envelope": "code=0,status=success,data.shares=array",
                "selected_columns": [
                    "id", "bank_id", "owner_id", "share_code", "share_token",
                    "permission", "expires_at", "max_uses", "current_uses",
                    "is_active", "created_at",
                ],
                "selected_column_count": 11,
                "filters_not_present": [
                    "owner_id", "is_active", "expires_at", "permission",
                ],
                "pagination": None,
                "query_parameters": "ignored",
                "ordering": "created_at DESC only; no stable tie-breaker",
            },
            "request_effect_scope": {
                "handler": "two sequential SELECT-only statements at most",
                "surrounding_web_session": (
                    "may SELECT users and commit users.last_active before the handler"
                ),
                "claim_boundary": (
                    "per-case ledgers separate personal-bank reads from authentication activity"
                ),
            },
            "dialect_observation": {
                "sqlite_capture": (
                    "raw SQLite text queries expose booleans as 0/1 and datetime values as raw "
                    "YYYY-MM-DD strings, while DESC places NULL last"
                ),
                "postgresql_target": (
                    "PostgreSQL 16.14 and 18.4 place NULL first for DESC by default and expose "
                    "boolean/datetime JDBC types; separate checked evidence must be authoritative"
                ),
                "migration_rule": (
                    "future JDBC SQL must spell DESC NULLS FIRST explicitly, must not add an id "
                    "tie-breaker, and must preserve all eleven nullable/raw fields"
                ),
                "equal_created_at": "legacy order is unspecified and must not be strengthened",
            },
            "legacy_datetime_serializer_attestation": {
                "provider": "archived Flask app.json provider",
                "input": "datetime(2026, 7, 17, 8, 0, 0)",
                "output": serialized_datetime,
                "scope": (
                    "serializer behavior only; PostgreSQL JDBC mapping is a separate entry gate"
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
                "returned_owner_bank_share_count": 5,
                "cross_owner_returned_count": 2,
                "inactive_returned_count": 1,
                "expired_returned_count": 1,
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
        f"captured {document['case_count']} personal-bank share-list cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
