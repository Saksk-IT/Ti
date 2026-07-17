#!/usr/bin/env python3
"""Capture deterministic fixed-commit goldens for usage-stats read aliases."""

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
from typing import Any, Iterator, Optional
from urllib.parse import urlencode


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-usage-stats-callers.json"
CAPTURE_TEST = TOOLS_DIR / "test_capture_phase4b_personal_bank_usage_stats_goldens.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_share_list_goldens as shared  # noqa: E402


pinned_source = shared.pinned_source
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
FIXED_REQUEST_ID = "phase4b-personal-bank-usage-stats-golden-request"
FIXED_NOW_BJ = datetime(2026, 7, 17, 12, 0, 0)
ROUTES = {
    "api-alias": {
        "route_id": "d67a16965b08",
        "path_template": "/api/user/banks/api/{bank_id}/usage-stats",
        "route_template": "/api/user/banks/api/<int:bank_id>/usage-stats",
        "legacy_handler": "user_bank_api_root.user_bank_api.get_bank_usage_stats",
        "registration_kind": "blueprint_compatibility_alias",
    },
    "web-alias": {
        "route_id": "22aecd49a3c2",
        "path_template": "/user/banks/api/{bank_id}/usage-stats",
        "route_template": "/user/banks/api/<int:bank_id>/usage-stats",
        "legacy_handler": "user_bank.user_bank_api.get_bank_usage_stats",
        "registration_kind": "blueprint_decorator",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/core/utils/jwt_utils.py",
    "app/core/utils/time_utils.py",
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
    "owner": 99401,
    "other": 99402,
    "revoked": 99403,
    "shared_equal": 99404,
    "shared_null": 99405,
    "shared_malformed": 99406,
    "shared_expired": 99407,
    "public_only": 99408,
    "shared_multi_expiry": 99409,
    "inactive_share_user": 99410,
    "inactive_record_user": 99411,
    "shared_empty_expiry": 99412,
    "signed_negative": -99413,
    "zero": 0,
}
BANKS = {
    "owner_active": 99501,
    "inactive": 99502,
    "other_active": 99503,
    "missing": 99999,
}
SHARES = {
    "expired": 99601,
    "equal_now": 99602,
    "null_expiry": 99603,
    "malformed_expiry": 99604,
    "multi_future": 99605,
    "multi_past": 99606,
    "inactive": 99607,
    "null_active": 99608,
    "inactive_record": 99609,
    "owner": 99610,
    "empty_expiry": 99611,
    "signed_negative": 99612,
    "zero": 99613,
}
RECORDS = {
    "equal_now": 99701,
    "null_expiry": 99702,
    "malformed_expiry": 99703,
    "expired": 99704,
    "multi_future": 99705,
    "multi_past": 99706,
    "inactive_share": 99707,
    "null_active_share": 99708,
    "inactive_record": 99709,
    "owner": 99710,
    "empty_expiry": 99711,
    "signed_negative": 99712,
    "zero": 99713,
}
PUBLIC_USERS = {
    "owner": 99801,
    "overlap_shared": 99802,
    "public_only": 99803,
    "signed_negative": 99804,
    "zero": 99805,
}
BUSINESS_TABLES = (
    "user_question_banks",
    "bank_shares",
    "bank_share_records",
    "public_bank_users",
)


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    bank: str = "owner_active"
    session_actor: Optional[str] = "owner"
    bearer_actor: Optional[str] = None
    accept: str = "*/*"
    fixture_mode: str = "full"
    query: tuple[tuple[str, str], ...] = ()
    fail_bank_probe: bool = False
    fail_shared: bool = False
    fail_public: bool = False
    expected_status: int = 200
    expected_bank_attempts: int = 1
    expected_shared_attempts: int = 1
    expected_public_attempts: int = 1


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        bearer_status = 200 if route == "api-alias" else 302
        bearer_bank_attempts = 1 if route == "api-alias" else 0
        anonymous_status = 401 if route == "api-alias" else 302
        specs.extend((
            CaseSpec(f"auth-session-owner-{route}", route),
            CaseSpec(
                f"auth-bearer-owner-{route}",
                route,
                session_actor=None,
                bearer_actor="owner",
                expected_status=bearer_status,
                expected_bank_attempts=bearer_bank_attempts,
                expected_shared_attempts=bearer_bank_attempts,
                expected_public_attempts=bearer_bank_attempts,
            ),
            CaseSpec(
                f"auth-bearer-precedes-session-{route}",
                route,
                session_actor="owner",
                bearer_actor="other",
                expected_status=403 if route == "api-alias" else 302,
                expected_bank_attempts=bearer_bank_attempts,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"auth-state-invalid-bearer-does-not-fallback-session-{route}",
                route,
                session_actor="owner",
                bearer_actor="revoked",
                expected_status=401 if route == "api-alias" else 302,
                expected_bank_attempts=0,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"auth-anonymous-{route}",
                route,
                session_actor=None,
                expected_status=anonymous_status,
                expected_bank_attempts=0,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"data-owner-active-empty-{route}",
                route,
                fixture_mode="empty",
            ),
            CaseSpec(f"data-overlap-time-boundaries-{route}", route),
            CaseSpec(
                f"data-query-parameters-ignored-{route}",
                route,
                query=(("scope", "all"), ("at", "past"),
                       ("page", "2"), ("page", "3")),
            ),
            CaseSpec(
                f"bank-missing-{route}",
                route,
                bank="missing",
                expected_status=404,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"bank-inactive-{route}",
                route,
                bank="inactive",
                expected_status=404,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"bank-non-owner-{route}",
                route,
                session_actor="other",
                expected_status=403,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"fault-bank-probe-default-{route}",
                route,
                fail_bank_probe=True,
                expected_status=500,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"fault-bank-probe-json-{route}",
                route,
                accept="application/json, text/plain;q=0.5",
                fail_bank_probe=True,
                expected_status=500,
                expected_shared_attempts=0,
                expected_public_attempts=0,
            ),
            CaseSpec(
                f"fault-shared-query-degrades-{route}",
                route,
                fail_shared=True,
            ),
            CaseSpec(
                f"fault-public-query-degrades-{route}",
                route,
                fail_public=True,
            ),
            CaseSpec(
                f"fault-both-optional-queries-degrade-{route}",
                route,
                fail_shared=True,
                fail_public=True,
            ),
        ))
    return tuple(specs)


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
capture_environment = shared.capture_environment


def bind_count(parameters: Any) -> int:
    if isinstance(parameters, Mapping):
        return len(parameters)
    if isinstance(parameters, (list, tuple)):
        return len(parameters)
    return 0 if parameters is None else 1


def is_bank_probe(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return (
        sql.startswith("SELECT ID, USER_ID, IS_PUBLIC, STATUS FROM USER_QUESTION_BANKS")
        and "WHERE ID =" in sql
        and "JOIN" not in sql
    )


def is_shared_user_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return (
        sql.startswith("SELECT DISTINCT BSR.USER_ID AS USER_ID, BS.EXPIRES_AT AS EXPIRES_AT")
        and "FROM BANK_SHARE_RECORDS BSR" in sql
        and "JOIN BANK_SHARES BS ON BSR.SHARE_ID = BS.ID" in sql
        and "WHERE BSR.BANK_ID =" in sql
        and "BSR.STATUS = 1" in sql
        and "BS.IS_ACTIVE = TRUE" in sql
    )


def is_public_user_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return (
        sql.startswith("SELECT DISTINCT USER_ID FROM PUBLIC_BANK_USERS")
        and "WHERE BANK_ID =" in sql
        and "JOIN" not in sql
    )


@contextmanager
def sql_probe(
    engine: Any,
    *,
    fail_bank_probe: bool,
    fail_shared: bool,
    fail_public: bool,
) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "bank_probe_attempts": 0,
        "bank_probe_bind_count": 0,
        "shared_user_select_attempts": 0,
        "shared_user_select_bind_count": 0,
        "public_user_select_attempts": 0,
        "public_user_select_bind_count": 0,
        "business_table_dml_attempts": {
            table: 0 for table in BUSINESS_TABLES
        },
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
        bank_probe = is_bank_probe(statement)
        shared_select = is_shared_user_select(statement)
        public_select = is_public_user_select(statement)
        activity_write = is_user_last_active_dml(statement)
        table_writes = {
            table: is_table_dml(statement, table) for table in BUSINESS_TABLES
        }
        if bank_probe:
            classification = "personal_bank_usage_bank_probe"
        elif shared_select:
            classification = "personal_bank_usage_shared_users_select"
        elif public_select:
            classification = "personal_bank_usage_public_users_select"
        elif activity_write:
            classification = "user_last_active_dml"
        elif any(table_writes.values()):
            classification = "personal_bank_business_table_dml"
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
        ledger["bank_probe_attempts"] += int(bank_probe)
        ledger["bank_probe_bind_count"] += bind_count(parameters) if bank_probe else 0
        ledger["shared_user_select_attempts"] += int(shared_select)
        ledger["shared_user_select_bind_count"] += (
            bind_count(parameters) if shared_select else 0
        )
        ledger["public_user_select_attempts"] += int(public_select)
        ledger["public_user_select_bind_count"] += (
            bind_count(parameters) if public_select else 0
        )
        for table, wrote in table_writes.items():
            ledger["business_table_dml_attempts"][table] += int(wrote)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if bank_probe and fail_bank_probe:
            raise RuntimeError("synthetic personal-bank usage bank-probe failure")
        if shared_select and fail_shared:
            raise RuntimeError("synthetic personal-bank usage shared-query failure")
        if public_select and fail_public:
            raise RuntimeError("synthetic personal-bank usage public-query failure")

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
            if item["classification"].startswith("personal_bank_usage_")
        ]
        ledger["business_table_dml_attempt_count"] = sum(
            ledger["business_table_dml_attempts"].values()
        )
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


def user_identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    columns = (
        "id", "username", "is_admin", "is_subject_admin",
        "is_notification_admin", "is_locked", "session_version",
    )
    binds = ", ".join(f":{actor}" for actor in ACTORS)
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM users WHERE id IN ({binds}) ORDER BY id"
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

    binds = ", ".join(f":{actor}" for actor in ACTORS)
    rows = db.session.execute(text(
        f"SELECT id, last_active FROM users WHERE id IN ({binds}) ORDER BY id"
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
        raise AssertionError("personal-bank usage-stats routes are missing or duplicated")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "selected_rows_sha256": sha256_json(selected),
        "selected_rows": selected,
        "caller_inventory_complete": False,
        "caller_authority": "personal-bank-usage-stats-callers.json",
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
    if document.get("legacy_commit") != LEGACY_COMMIT:
        raise AssertionError("usage-stats caller evidence legacy commit drifted")
    if not document.get("closure", {}).get("caller_attestation_complete"):
        raise AssertionError("usage-stats caller evidence is not closed")
    route_ids = {route["route_id"] for route in document.get("routes", [])}
    if route_ids != {route["route_id"] for route in ROUTES.values()}:
        raise AssertionError("usage-stats caller evidence route set drifted")
    return {
        "path": "docs/refactor/phase4b/personal-bank-usage-stats-callers.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "attestation_sha256": document["attestation_sha256"],
        "document_payload_sha256": document["document_payload_sha256"],
        "caller_attestation_complete": True,
    }


def tool_provenance() -> dict[str, Any]:
    capture_tool = Path(__file__).resolve()
    if not CAPTURE_TEST.is_file():
        raise AssertionError(f"usage-stats golden contract test missing: {CAPTURE_TEST}")
    return {
        "capture_tool": {
            "path": "tools/capture_phase4b_personal_bank_usage_stats_goldens.py",
            "sha256": hashlib.sha256(capture_tool.read_bytes()).hexdigest(),
        },
        "capture_test": {
            "path": "tools/test_capture_phase4b_personal_bank_usage_stats_goldens.py",
            "sha256": hashlib.sha256(CAPTURE_TEST.read_bytes()).hexdigest(),
        },
        "execution_model": (
            "complete app/ tree archived from the immutable commit, isolated import, "
            "temporary SQLite, synthetic actors and a fixed Beijing clock"
        ),
    }


def bank_rows() -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    return [
        {
            "id": BANKS["owner_active"],
            "user_id": ACTORS["owner"],
            "name": "usage stats 高数・α／🧪",
            "is_public": None,
            "status": 1,
            "created_at": fixed,
            "updated_at": fixed,
        },
        {
            "id": BANKS["inactive"],
            "user_id": ACTORS["owner"],
            "name": "inactive usage bank",
            "is_public": True,
            "status": 0,
            "created_at": fixed,
            "updated_at": fixed,
        },
        {
            "id": BANKS["other_active"],
            "user_id": ACTORS["other"],
            "name": "other usage bank",
            "is_public": False,
            "status": 1,
            "created_at": fixed,
            "updated_at": fixed,
        },
    ]


def full_share_rows() -> list[dict[str, Any]]:
    rows = [
        ("expired", "2026-07-17 11:59:59", True),
        ("equal_now", "2026-07-17 12:00:00", True),
        ("null_expiry", None, True),
        ("malformed_expiry", "malformed-expiry", True),
        ("multi_future", "2026-07-17 13:00:00", True),
        ("multi_past", "2026-07-17 10:00:00", True),
        ("inactive", "2026-07-17 13:00:00", False),
        ("null_active", "2026-07-17 13:00:00", None),
        ("inactive_record", "2026-07-17 13:00:00", True),
        ("owner", None, True),
        ("empty_expiry", "", True),
        ("signed_negative", None, True),
        ("zero", None, True),
    ]
    return [
        {
            "id": SHARES[key],
            "bank_id": BANKS["owner_active"],
            "owner_id": ACTORS["owner"],
            "share_code": f"U{index:05d}",
            "share_token": f"usage-token-{index:04d}",
            "permission": "read",
            "expires_at": expires_at,
            "max_uses": None,
            "current_uses": 0,
            "is_active": is_active,
            "created_at": datetime(2026, 7, 17, 8, index, 0),
        }
        for index, (key, expires_at, is_active) in enumerate(rows, start=1)
    ]


def full_record_rows() -> list[dict[str, Any]]:
    assignments = (
        ("equal_now", "equal_now", "shared_equal", 1),
        ("null_expiry", "null_expiry", "shared_null", 1),
        ("malformed_expiry", "malformed_expiry", "shared_malformed", 1),
        ("expired", "expired", "shared_expired", 1),
        ("multi_future", "multi_future", "shared_multi_expiry", 1),
        ("multi_past", "multi_past", "shared_multi_expiry", 1),
        ("inactive_share", "inactive", "inactive_share_user", 1),
        ("null_active_share", "null_active", "inactive_share_user", 1),
        ("inactive_record", "inactive_record", "inactive_record_user", 0),
        ("owner", "owner", "owner", 1),
        ("empty_expiry", "empty_expiry", "shared_empty_expiry", 1),
        ("signed_negative", "signed_negative", "signed_negative", 1),
        ("zero", "zero", "zero", 1),
    )
    return [
        {
            "id": RECORDS[record],
            "share_id": SHARES[share],
            "bank_id": BANKS["owner_active"],
            "user_id": ACTORS[actor],
            "status": status,
            "last_access_at": datetime(2026, 7, 17, 9, index, 0),
            "access_count": index,
            "created_at": datetime(2026, 7, 17, 8, index, 0),
        }
        for index, (record, share, actor, status) in enumerate(assignments, start=1)
    ]


def full_public_rows() -> list[dict[str, Any]]:
    assignments = (
        ("owner", "owner"),
        ("overlap_shared", "shared_null"),
        ("public_only", "public_only"),
        ("signed_negative", "signed_negative"),
        ("zero", "zero"),
    )
    return [
        {
            "id": PUBLIC_USERS[row],
            "bank_id": BANKS["owner_active"],
            "user_id": ACTORS[actor],
            "last_access_at": datetime(2026, 7, 17, 10, index, 0),
            "access_count": index,
            "created_at": datetime(2026, 7, 17, 8, index, 0),
        }
        for index, (row, actor) in enumerate(assignments, start=1)
    ]


def fixture_rows(mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if mode == "full":
        return full_share_rows(), full_record_rows(), full_public_rows()
    if mode == "empty":
        return [], [], []
    raise AssertionError(f"unknown usage-stats fixture mode: {mode}")


def seed_static_actors(db: Any, User: Any) -> None:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4b_usage_{actor}",
            email=f"phase4b_usage_{actor}@test.example.com",
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


def _insert_rows(db: Any, table: str, rows: list[dict[str, Any]]) -> None:
    from sqlalchemy import text

    if not rows:
        return
    columns = tuple(rows[0])
    db.session.execute(text(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
        f"({', '.join(':' + column for column in columns)})"
    ), rows)


def reset_case_facts(db: Any, mode: str) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    for table in reversed(BUSINESS_TABLES):
        db.session.execute(text(f"DELETE FROM {table}"))
    _insert_rows(db, "user_question_banks", bank_rows())
    shares, records, public_users = fixture_rows(mode)
    _insert_rows(db, "bank_shares", shares)
    _insert_rows(db, "bank_share_records", records)
    _insert_rows(db, "public_bank_users", public_users)
    actor_binds = ", ".join(f":{actor}" for actor in ACTORS)
    db.session.execute(text(
        f"UPDATE users SET last_active = NULL WHERE id IN ({actor_binds})"
    ), ACTORS)
    db.session.commit()
    return {
        table: table_fingerprint(db, table) for table in BUSINESS_TABLES
    }


def set_actor_session(client: Any, actor: Optional[str]) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4b_usage_{actor}",
            "session_version": 11,
            "is_admin": False,
            "is_subject_admin": False,
            "is_notification_admin": False,
        })


def credential_mode(spec: CaseSpec) -> str:
    if spec.bearer_actor == "revoked" and spec.session_actor is not None:
        return "session+state_invalid_bearer"
    if spec.bearer_actor is not None and spec.session_actor is not None:
        return "session+valid_bearer"
    if spec.bearer_actor is not None:
        return "valid_bearer_only"
    if spec.session_actor is not None:
        return "session"
    return "none"


def recorded_request_headers(spec: CaseSpec) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.bearer_actor == "revoked":
        result["Authorization"] = "Bearer <redacted-state-invalid-synthetic-jwt>"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    return result


def live_request_headers(spec: CaseSpec, tokens: dict[str, str]) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.bearer_actor is not None:
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
        before = {table: table_fingerprint(db, table) for table in BUSINESS_TABLES}
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
        fail_bank_probe=spec.fail_bank_probe,
        fail_shared=spec.fail_shared,
        fail_public=spec.fail_public,
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
        after = {table: table_fingerprint(db, table) for table in BUSINESS_TABLES}
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
        "bearer_actor": spec.bearer_actor or "none",
        "credential_mode": credential_mode(spec),
        "fixture_mode": spec.fixture_mode,
        "fault_injection": {
            "bank_probe": spec.fail_bank_probe,
            "shared_query": spec.fail_shared,
            "public_query": spec.fail_public,
        },
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
            "business_tables_before": before,
            "business_tables_after": after,
            "business_tables_match_case_fixture": {
                table: before[table] == expected[table] for table in BUSINESS_TABLES
            },
            "business_tables_unchanged": {
                table: before[table] == after[table] for table in BUSINESS_TABLES
            },
            "users_identity_before": identity_before,
            "users_identity_after": identity_after,
            "users_identity_unchanged": identity_before == identity_after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def response_stats(case: dict[str, Any]) -> dict[str, Any]:
    body = case["response"]["body"]
    if not isinstance(body, dict):
        raise AssertionError(f"{case['case_id']} response is not an object")
    data = body.get("data")
    if not isinstance(data, dict):
        raise AssertionError(f"{case['case_id']} usage-stats envelope drifted")
    return data


def _expected_sequence(spec: CaseSpec) -> list[str]:
    return (
        ["personal_bank_usage_bank_probe"] * spec.expected_bank_attempts
        + ["personal_bank_usage_shared_users_select"] * spec.expected_shared_attempts
        + ["personal_bank_usage_public_users_select"] * spec.expected_public_attempts
    )


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 32 or len(cases) != 32 or len(by_id) != 32:
        raise AssertionError("usage-stats case set must contain 32 unique cases")
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
        if not all(effects["business_tables_match_case_fixture"].values()):
            raise AssertionError(f"{spec.case_id} did not start from its isolated fixture")
        if not all(effects["business_tables_unchanged"].values()):
            raise AssertionError(f"{spec.case_id} changed personal-bank business facts")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed identity facts")
        if sql["business_table_dml_attempt_count"] != 0:
            raise AssertionError(f"{spec.case_id} attempted personal-bank business DML")
        if sql["ddl_attempts"] != 0:
            raise AssertionError(f"{spec.case_id} attempted request DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")
        expected_attempts = (
            spec.expected_bank_attempts,
            spec.expected_shared_attempts,
            spec.expected_public_attempts,
        )
        observed_attempts = (
            sql["bank_probe_attempts"],
            sql["shared_user_select_attempts"],
            sql["public_user_select_attempts"],
        )
        if observed_attempts != expected_attempts:
            raise AssertionError(
                f"{spec.case_id} query attempts drifted: "
                f"expected={expected_attempts} observed={observed_attempts}"
            )
        for expected, bind_key in (
            (spec.expected_bank_attempts, "bank_probe_bind_count"),
            (spec.expected_shared_attempts, "shared_user_select_bind_count"),
            (spec.expected_public_attempts, "public_user_select_bind_count"),
        ):
            if sql[bind_key] != expected:
                raise AssertionError(f"{spec.case_id} single bank-id bind drifted")
        if sql["personal_bank_query_sequence"] != _expected_sequence(spec):
            raise AssertionError(f"{spec.case_id} business query sequence drifted")

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

    full_stats = {
        "bank_id": BANKS["owner_active"],
        "is_public": False,
        "owner_id": ACTORS["owner"],
        "owner_count": 1,
        "shared_users": 5,
        "public_users": 3,
        "total_users": 7,
        "total_users_excluding_owner": 6,
    }
    empty_stats = {
        **full_stats,
        "shared_users": 0,
        "public_users": 0,
        "total_users": 1,
        "total_users_excluding_owner": 0,
    }
    for route in ROUTES:
        for case_id in (
            f"auth-session-owner-{route}",
            f"data-overlap-time-boundaries-{route}",
            f"data-query-parameters-ignored-{route}",
        ):
            if response_stats(by_id[case_id]) != full_stats:
                raise AssertionError(f"{case_id} overlap/time-boundary result drifted")
        if route == "api-alias":
            if response_stats(by_id[f"auth-bearer-owner-{route}"]) != full_stats:
                raise AssertionError("API bearer owner result drifted")
        if response_stats(by_id[f"data-owner-active-empty-{route}"]) != empty_stats:
            raise AssertionError(f"data-owner-active-empty-{route} drifted")
        ignored = by_id[f"data-query-parameters-ignored-{route}"]
        if ignored["request"]["query"] != [
            ["scope", "all"], ["at", "past"], ["page", "2"], ["page", "3"],
        ]:
            raise AssertionError(f"data-query-parameters-ignored-{route} lost duplicates")

        shared_fault = response_stats(by_id[f"fault-shared-query-degrades-{route}"])
        public_fault = response_stats(by_id[f"fault-public-query-degrades-{route}"])
        both_fault = response_stats(by_id[f"fault-both-optional-queries-degrade-{route}"])
        if (shared_fault["shared_users"], shared_fault["public_users"],
                shared_fault["total_users"], shared_fault["total_users_excluding_owner"]) != (0, 3, 4, 3):
            raise AssertionError(f"fault-shared-query-degrades-{route} drifted")
        if (public_fault["shared_users"], public_fault["public_users"],
                public_fault["total_users"], public_fault["total_users_excluding_owner"]) != (5, 0, 6, 5):
            raise AssertionError(f"fault-public-query-degrades-{route} drifted")
        if both_fault != empty_stats:
            raise AssertionError(f"fault-both-optional-queries-degrade-{route} drifted")

        missing = by_id[f"bank-missing-{route}"]["response"]["body"]
        inactive = by_id[f"bank-inactive-{route}"]["response"]["body"]
        forbidden = by_id[f"bank-non-owner-{route}"]["response"]["body"]
        if missing.get("code") != 1 or missing.get("message") != "题库不存在或已被删除":
            raise AssertionError(f"bank-missing-{route} 404 contract drifted")
        if inactive.get("code") != 1 or inactive.get("message") != "题库不存在或已被删除":
            raise AssertionError(f"bank-inactive-{route} 404 contract drifted")
        if forbidden.get("code") != 403 or forbidden.get("message") != "无权查看（仅创建者可见）":
            raise AssertionError(f"bank-non-owner-{route} 403 contract drifted")

        default_fault = by_id[f"fault-bank-probe-default-{route}"]
        json_fault = by_id[f"fault-bank-probe-json-{route}"]
        if "synthetic personal-bank usage" in default_fault["response"]["body_text"]:
            raise AssertionError(f"fault-bank-probe-default-{route} leaked injection")
        if "synthetic personal-bank usage" in json_fault["response"]["body_text"]:
            raise AssertionError(f"fault-bank-probe-json-{route} leaked injection")
        expected_default_kind = "json" if route == "api-alias" else "text"
        if default_fault["response"]["body_kind"] != expected_default_kind:
            raise AssertionError(f"fault-bank-probe-default-{route} media drifted")
        if json_fault["response"]["body_kind"] != "json":
            raise AssertionError(f"fault-bank-probe-json-{route} must be JSON")

    precedence = by_id["auth-bearer-precedes-session-api-alias"]
    if precedence["response"]["status"] != 403:
        raise AssertionError("valid bearer must precede the owner Session identity")
    invalid = by_id[
        "auth-state-invalid-bearer-does-not-fallback-session-api-alias"
    ]
    invalid_body = invalid["response"]["body"]
    if invalid_body.get("status") != "unauthorized" or "会话已失效" not in invalid_body.get("message", ""):
        raise AssertionError("state-invalid bearer must not fall back to Session")
    if by_id["auth-anonymous-api-alias"]["response"]["body_kind"] != "json":
        raise AssertionError("anonymous API alias must return JSON 401")
    for case_id in (
        "auth-bearer-owner-web-alias",
        "auth-bearer-precedes-session-web-alias",
        "auth-state-invalid-bearer-does-not-fallback-session-web-alias",
        "auth-anonymous-web-alias",
    ):
        if by_id[case_id]["response"]["headers"].get("Location") != ["/login"]:
            raise AssertionError(f"{case_id} must redirect to /login")

    safe_json_500 = {
        "status": "error",
        "message": "An unexpected server error occurred.",
        "status_code": 500,
        "payload": None,
        "request_id": FIXED_REQUEST_ID,
    }
    for case_id in (
        "fault-bank-probe-default-api-alias",
        "fault-bank-probe-json-api-alias",
        "fault-bank-probe-json-web-alias",
    ):
        if by_id[case_id]["response"]["body"] != safe_json_500:
            raise AssertionError(f"{case_id} safe JSON 500 drifted")
    if by_id["fault-bank-probe-default-web-alias"]["response"]["body"] != (
        "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>"
    ):
        raise AssertionError("Web default bank-probe failure HTML drifted")


def capture_document(legacy_root: Path) -> dict[str, Any]:
    if pinned_source.LEGACY_COMMIT != LEGACY_COMMIT:
        raise AssertionError("shared legacy commit authority drifted")
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "frozen_route_matrix": matrix_attestation(),
            "key_sources": key_source_attestation(archived),
            "complete_caller_attestation": caller_evidence_reference(),
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4b-personal-bank-usage-stats-data-"
        ) as data_dir:
            with capture_environment(data_dir):
                with pinned_source.archived_legacy_import_environment(archived.root):
                    import app as legacy_app
                    from app.core.extensions import db
                    from app.core.utils.jwt_utils import generate_jwt_token
                    from app.models.user import User
                    from app.modules.user_bank.routes import api_shares

                    pinned_source.assert_module_from_archive(legacy_app, archived.root)
                    pinned_source.assert_module_from_archive(api_shares, archived.root)
                    previous_logging = logging.root.manager.disable
                    original_now_bj = api_shares.now_bj
                    logging.disable(logging.CRITICAL)
                    legacy_app._start_background_tasks = lambda _app: None
                    api_shares.now_bj = lambda: FIXED_NOW_BJ
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
                        api_shares.now_bj = original_now_bj
                        logging.disable(previous_logging)
                        with app.app_context():
                            db.session.remove()

        provenance = tool_provenance()
        document: dict[str, Any] = {
            "contract_id": "ti.phase4b.personal-bank-usage-stats-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-17",
            "legacy_commit": LEGACY_COMMIT,
            "fixed_beijing_time": FIXED_NOW_BJ.isoformat(sep=" "),
            "legacy_source_attestation": source_attestation,
            "provenance": {
                **provenance,
                "hashes": {
                    "legacy_handler_source_sha256": source_attestation[
                        "key_sources"
                    ]["app/modules/user_bank/routes/api_shares.py"]["sha256"],
                    "caller_evidence_sha256": source_attestation[
                        "complete_caller_attestation"
                    ]["sha256"],
                    "case_payload_sha256": sha256_json(cases),
                    "capture_tool_sha256": provenance["capture_tool"]["sha256"],
                    "capture_test_sha256": provenance["capture_test"]["sha256"],
                },
            },
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
                "bank_probe": (
                    "SELECT id, user_id, is_public, status FROM user_question_banks "
                    "WHERE id = :bank_id"
                ),
                "shared_users": (
                    "SELECT DISTINCT bsr.user_id AS user_id, bs.expires_at AS expires_at "
                    "FROM bank_share_records bsr JOIN bank_shares bs ON bsr.share_id = bs.id "
                    "WHERE bsr.bank_id = :bank_id AND bsr.status = 1 AND bs.is_active = true"
                ),
                "public_users": (
                    "SELECT DISTINCT user_id FROM public_bank_users WHERE bank_id = :bank_id"
                ),
                "binds_per_statement": ["bank_id"],
                "query_parameters": "ignored",
                "pagination": None,
                "ordering": None,
            },
            "usage_count_contract": {
                "expiry_clock": "fixed naive Beijing local datetime",
                "expired_when": "expires_at < now_bj()",
                "equal_to_now": "valid",
                "null_expiry": "valid",
                "falsey_expiry": "NULL, empty string, 0 and False are valid before parsing",
                "empty_string_expiry_fixture": "valid",
                "truthy_malformed_expiry": "expired",
                "aware_vs_naive_comparison_error": "expired",
                "shared_distinct_sql_key": ["user_id", "expires_at"],
                "shared_set_key_after_expiry_filter": "user_id",
                "user_id_conversion": "int(value or 0); conversion failures are ignored",
                "zero_user_id": "ignored by later truthy filtering",
                "negative_user_id": "truthy and therefore counted",
                "owner_excluded_from_shared_users": True,
                "owner_excluded_from_public_users": True,
                "shared_and_public_categories_mutually_subtracted": False,
                "total_users": "set union of owner, valid shared users and public users",
                "owner_count": 1,
                "is_public_null_serializes_as": False,
                "physical_bank_constraints": (
                    "user_question_banks.user_id and status are integer-backed; owner id is "
                    "NOT NULL and status is treated through int(status or 0)"
                ),
            },
            "failure_contract": {
                "bank_probe": (
                    "uncaught: API/default or Accept application/json prefix returns safe JSON; "
                    "Web default returns generic Chinese HTML"
                ),
                "shared_query": "caught independently and degraded to an empty shared set",
                "public_query": "caught independently and degraded to an empty public set",
                "both_optional_queries": "HTTP 200 owner-only counts",
                "injected_exception_redacted": True,
            },
            "authentication_contract": {
                "session": "accepted on both aliases and may update users.last_active",
                "api_bearer": "accepted and precedes Session identity",
                "state_invalid_bearer": "does not fall back to a valid Session",
                "web_bearer": "global Web gate redirects to /login before the route decorator",
                "anonymous_api": "JSON 401",
                "anonymous_web": "redirect /login",
                "bearer_last_active": "valid or state-invalid bearer precedence does not write Session activity",
            },
            "request_effect_scope": {
                "handler": "three SELECT-only stages with two independent optional-query fallbacks",
                "business_tables": list(BUSINESS_TABLES),
                "business_table_writes": 0,
                "surrounding_session_side_effect": "users.last_active may be committed before handler entry",
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory limiter; synthetic identities; fixed now_bj; no current worktree legacy import"
            ),
            "redaction": (
                "JWT, password hash, session-cookie values and database-current last_active "
                "timestamps are omitted or represented by deterministic placeholders"
            ),
            "fixture": {
                "actors": ACTORS,
                "banks": BANKS,
                "shares": SHARES,
                "records": RECORDS,
                "public_users": PUBLIC_USERS,
                "full_table_fingerprints": full_fixture,
                "expected_full_stats": {
                    "shared_users": 5,
                    "public_users": 3,
                    "total_users": 7,
                    "total_users_excluding_owner": 6,
                },
                "boundary_rows": {
                    "equal_now_valid": SHARES["equal_now"],
                    "null_expiry_valid": SHARES["null_expiry"],
                    "malformed_expiry_excluded": SHARES["malformed_expiry"],
                    "expired_excluded": SHARES["expired"],
                    "empty_string_expiry_valid": SHARES["empty_expiry"],
                    "same_user_multiple_expiries": ACTORS["shared_multi_expiry"],
                    "shared_public_overlap": ACTORS["shared_null"],
                    "owner_in_both_categories": ACTORS["owner"],
                    "zero_user_id_ignored_in_both_sources": ACTORS["zero"],
                    "negative_user_id_counted_in_both_sources": ACTORS["signed_negative"],
                },
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
        f"captured {document['case_count']} personal-bank usage-stats cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
