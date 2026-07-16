#!/usr/bin/env python3
"""Capture deterministic dual-alias personal-bank category read goldens."""

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
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


FIXED_REQUEST_ID = "phase4b-personal-bank-category-golden-request"
ROUTES = {
    "api-alias": {
        "route_id": "19b37a262989",
        "path": "/api/user/banks/api/categories",
        "route_template": "/api/user/banks/api/categories",
        "legacy_handler": "user_bank_api_root.user_bank_api.get_categories",
        "registration_kind": "blueprint_compatibility_alias",
    },
    "web-alias": {
        "route_id": "e32aec766730",
        "path": "/user/banks/api/categories",
        "route_template": "/user/banks/api/categories",
        "legacy_handler": "user_bank.user_bank_api.get_categories",
        "registration_kind": "blueprint_decorator",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/api_response.py",
    "app/core/utils/decorators.py",
    "app/models/user.py",
    "app/models/user_bank.py",
    "app/modules/user_bank/__init__.py",
    "app/modules/user_bank/routes/api.py",
    "app/modules/user_bank/routes/api_base.py",
    "app/modules/user_bank/routes/api_categories.py",
    "app/modules/user_bank/templates/user_bank/public/categories.html",
)
ACTORS = {
    "owner": 97001,
    "other": 97002,
}
CATEGORIES = {
    "negative": -2,
    "zero": 0,
    "unicode": 97101,
    "empty_name": 97102,
    "other_owner": 97103,
    "nullable": 97104,
}
BANKS = {
    "negative_active_owner": -4,
    "negative_inactive_owner": 0,
    "negative_active_other_owner": 97201,
    "zero_active_other_owner": 97202,
    "unicode_inactive": 97203,
    "other_category_active": 97204,
    "unicode_status_two": 97205,
    "unicode_status_null": 97206,
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
    fail_category_select: bool = False
    expected_status: int = 200


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        anonymous_status = 401 if route == "api-alias" else 302
        bearer_status = 200 if route == "api-alias" else 302
        specs.extend((
            CaseSpec(f"auth-session-owner-{route}", route),
            CaseSpec(
                f"auth-bearer-owner-{route}", route,
                session_actor=None, bearer_actor="owner",
                expected_status=bearer_status,
            ),
            CaseSpec(
                f"auth-session-other-{route}", route,
                session_actor="other",
            ),
            CaseSpec(
                f"auth-bearer-precedes-session-{route}", route,
                session_actor="other", bearer_actor="owner",
                expected_status=bearer_status,
            ),
            CaseSpec(
                f"auth-invalid-bearer-falls-back-session-{route}", route,
                invalid_bearer=True,
            ),
            CaseSpec(
                f"auth-anonymous-{route}", route,
                session_actor=None, expected_status=anonymous_status,
            ),
            CaseSpec(
                f"data-empty-{route}", route,
                fixture_mode="empty",
            ),
            CaseSpec(
                f"data-query-parameters-ignored-{route}", route,
                query=(("category_id", "999"), ("sort", "desc"),
                       ("page", "2"), ("page", "3")),
            ),
            CaseSpec(
                f"data-nullable-fields-{route}", route,
                fixture_mode="nullable",
            ),
            CaseSpec(
                f"fault-default-{route}", route,
                fail_category_select=True, expected_status=500,
            ),
            CaseSpec(
                f"fault-json-{route}", route,
                accept="application/json",
                fail_category_select=True, expected_status=500,
            ),
        ))
    return tuple(specs)


CASE_SPECS = build_case_specs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: Mapping[str, Any]) -> str:
    return sha256_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    })


def render_document(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def normalized_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        return {
            str(key): normalized_value(child)
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [normalized_value(child) for child in value]
    return value


def normalized_sql(statement: Any) -> str:
    return " ".join(str(statement).split()).upper()


def is_select_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith(("SELECT ", "WITH "))


def is_dml_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith(
        ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ")
    )


def is_ddl_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith((
        "CREATE ", "ALTER ", "DROP ", "TRUNCATE ", "COMMENT ",
        "GRANT ", "REVOKE ", "VACUUM ", "ANALYZE ", "PRAGMA ",
    ))


def is_category_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return all(fragment in sql for fragment in (
        "SELECT C.*,",
        "SELECT COUNT(*) FROM USER_QUESTION_BANKS",
        "WHERE CATEGORY_ID = C.ID AND STATUS = 1",
        "AS BANK_COUNT FROM USER_BANK_CATEGORIES C",
        "WHERE C.USER_ID =",
        "ORDER BY C.SORT_ORDER ASC, C.ID ASC",
    ))


def reads_table(statement: Any, table: str) -> bool:
    return is_select_statement(statement) and bool(re.search(
        rf"\b(?:FROM|JOIN)\s+{table.upper()}\b", normalized_sql(statement)
    ))


def is_table_dml(statement: Any, table: str) -> bool:
    return bool(re.match(
        rf"^(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+{table.upper()}\b",
        normalized_sql(statement),
    ))


def is_user_last_active_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(r"^UPDATE\s+USERS\s+SET\s+LAST_ACTIVE\s*=", sql)) \
        and bool(re.search(r"\bWHERE\s+USERS\.ID\s*=", sql))


@contextmanager
def sql_probe(engine: Any, *, fail_category_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "category_select_attempts": 0,
        "category_select_bind_count": 0,
        "category_table_dml_attempts": 0,
        "bank_table_dml_attempts": 0,
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
        category_query = is_category_select(statement)
        category_write = is_table_dml(statement, "user_bank_categories")
        bank_write = is_table_dml(statement, "user_question_banks")
        activity_write = is_user_last_active_dml(statement)
        if category_query:
            classification = "personal_bank_category_select"
        elif activity_write:
            classification = "user_last_active_dml"
        elif category_write:
            classification = "category_table_dml"
        elif bank_write:
            classification = "bank_table_dml"
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
        normalized_parameters = normalized_value(parameters)
        ledger["statements"].append({
            "sql": normalized,
            "parameters": normalized_parameters,
            "executemany": bool(executemany),
            "classification": classification,
        })
        ledger["select_attempts"] += int(select)
        ledger["dml_attempts"] += int(dml)
        ledger["ddl_attempts"] += int(ddl)
        ledger["other_attempts"] += int(not select and not dml and not ddl)
        ledger["category_select_attempts"] += int(category_query)
        if category_query:
            if isinstance(parameters, Mapping):
                ledger["category_select_bind_count"] += len(parameters)
            elif isinstance(parameters, (list, tuple)):
                ledger["category_select_bind_count"] += len(parameters)
        ledger["category_table_dml_attempts"] += int(category_write)
        ledger["bank_table_dml_attempts"] += int(bank_write)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if category_query and fail_category_select:
            raise RuntimeError("synthetic personal-bank category SELECT failure")

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
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


def table_fingerprint(db: Any, table: str) -> dict[str, Any]:
    from sqlalchemy import inspect, text

    columns = [column["name"] for column in inspect(db.engine).get_columns(table)]
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
    )).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "columns": columns,
        "column_count": len(columns),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


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
        raise AssertionError("personal-bank category routes are missing or duplicated")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "selected_rows_sha256": sha256_json(selected),
        "selected_rows": selected,
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


def caller_attestation(archived: Any) -> dict[str, Any]:
    source = "app/modules/user_bank/templates/user_bank/public/categories.html"
    payload = (archived.root / source).read_text(encoding="utf-8")
    direct_get = [
        {"source": source, "line": line_number, "text": line.strip()}
        for line_number, line in enumerate(payload.splitlines(), 1)
        if "api('/user/banks/api/categories')" in line
    ]
    render_references: list[dict[str, Any]] = []
    for path in sorted((archived.root / "app").rglob("*")):
        if not path.is_file() or path.suffix not in {".py", ".html", ".js", ".ts"}:
            continue
        text_value = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text_value.splitlines(), 1):
            if "user_bank/public/categories.html" in line or "public/categories.html" in line:
                render_references.append({
                    "source": path.relative_to(archived.root).as_posix(),
                    "line": line_number,
                    "text": line.strip(),
                })
    result = {
        "direct_get_occurrences": direct_get,
        "api_alias_direct_occurrences": [],
        "template_render_references": render_references,
        "caller_state": "dormant",
        "reason": (
            "the archived template contains the Web alias GET call but the complete archived "
            "app tree contains no render/include reference to that template; the /api alias "
            "has no direct static caller"
        ),
    }
    result["attestation_sha256"] = sha256_json(result)
    return result


def category_rows(mode: str) -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    if mode == "empty":
        return []
    if mode == "nullable":
        return [{
            "id": CATEGORIES["nullable"],
            "user_id": ACTORS["owner"],
            "name": "可空字段分类",
            "description": None,
            "sort_order": None,
            "created_at": None,
            "updated_at": None,
        }]
    if mode != "full":
        raise AssertionError(f"unknown fixture mode: {mode}")
    return [
        {
            "id": CATEGORIES["negative"],
            "user_id": ACTORS["owner"],
            "name": "负主键分类",
            "description": "signed category identifier",
            "sort_order": -5,
            "created_at": fixed,
            "updated_at": fixed,
        },
        {
            "id": CATEGORIES["zero"],
            "user_id": ACTORS["owner"],
            "name": "",
            "description": "",
            "sort_order": 0,
            "created_at": fixed,
            "updated_at": fixed,
        },
        {
            "id": CATEGORIES["unicode"],
            "user_id": ACTORS["owner"],
            "name": "高数・α／🧪",
            "description": "Unicode 描述",
            "sort_order": 0,
            "created_at": fixed,
            "updated_at": fixed,
        },
        {
            "id": CATEGORIES["empty_name"],
            "user_id": ACTORS["owner"],
            "name": "尾部分类",
            "description": None,
            "sort_order": 9,
            "created_at": fixed,
            "updated_at": fixed,
        },
        {
            "id": CATEGORIES["other_owner"],
            "user_id": ACTORS["other"],
            "name": "其他用户分类",
            "description": "must not leak to owner",
            "sort_order": -100,
            "created_at": fixed,
            "updated_at": fixed,
        },
    ]


def bank_rows(mode: str) -> list[dict[str, Any]]:
    if mode != "full":
        return []
    fixed = datetime(2026, 7, 17, 8, 0, 0)

    def row(
        bank_id: int,
        user_id: int,
        category_id: int,
        name: str,
        status: int | None,
    ) -> dict[str, Any]:
        return {
            "id": bank_id,
            "user_id": user_id,
            "category_id": category_id,
            "name": name,
            "status": status,
            "created_at": fixed,
            "updated_at": fixed,
        }

    return [
        row(BANKS["negative_active_owner"], ACTORS["owner"],
            CATEGORIES["negative"], "active owner bank", 1),
        row(BANKS["negative_inactive_owner"], ACTORS["owner"],
            CATEGORIES["negative"], "inactive owner bank", 0),
        row(BANKS["negative_active_other_owner"], ACTORS["other"],
            CATEGORIES["negative"], "cross-owner active bank counted by category", 1),
        row(BANKS["zero_active_other_owner"], ACTORS["other"],
            CATEGORIES["zero"], "second cross-owner active bank", 1),
        row(BANKS["unicode_inactive"], ACTORS["owner"],
            CATEGORIES["unicode"], "inactive unicode category bank", -1),
        row(BANKS["other_category_active"], ACTORS["other"],
            CATEGORIES["other_owner"], "other category active bank", 1),
        row(BANKS["unicode_status_two"], ACTORS["owner"],
            CATEGORIES["unicode"], "status two is not active", 2),
        row(BANKS["unicode_status_null"], ACTORS["owner"],
            CATEGORIES["unicode"], "null status is not active", None),
    ]


def seed_static_actors(db: Any, User: Any) -> None:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4b_category_{actor}",
            email=f"phase4b_category_{actor}@test.example.com",
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
    db.session.execute(text("DELETE FROM user_question_banks"))
    db.session.execute(text("DELETE FROM user_bank_categories"))
    categories = category_rows(mode)
    banks = bank_rows(mode)
    if categories:
        columns = tuple(categories[0])
        db.session.execute(text(
            "INSERT INTO user_bank_categories "
            f"({', '.join(columns)}) VALUES "
            f"({', '.join(':' + column for column in columns)})"
        ), categories)
    if banks:
        columns = tuple(banks[0])
        db.session.execute(text(
            "INSERT INTO user_question_banks "
            f"({', '.join(columns)}) VALUES "
            f"({', '.join(':' + column for column in columns)})"
        ), banks)
    db.session.execute(text(
        "UPDATE users SET last_active = NULL WHERE id IN (:owner, :other)"
    ), ACTORS)
    db.session.commit()
    return {
        "categories": table_fingerprint(db, "user_bank_categories"),
        "banks": table_fingerprint(db, "user_question_banks"),
    }


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4b_category_{actor}",
            "session_version": 11,
            "is_admin": False,
            "is_subject_admin": False,
            "is_notification_admin": False,
        })


def reset_limiters(app: Any) -> None:
    for limiter in app.extensions.get("limiter", set()):
        limiter.reset()


def response_headers(response: Any) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name in sorted(set(response.headers.keys()), key=str.lower):
        values = response.headers.getlist(name)
        if name.lower() == "set-cookie":
            values = ["<redacted-session-cookie>" for _value in values]
        elif name.lower() == "x-ratelimit-reset":
            values = ["<rate-limit-reset-epoch>" for _value in values]
        elif name.lower() == "retry-after":
            values = ["<dynamic-seconds>" for _value in values]
        result[name] = values
    return result


def normalized_response(response: Any) -> dict[str, Any]:
    raw = response.get_data()
    payload = response.get_json(silent=True)
    return {
        "status": response.status_code,
        "headers": response_headers(response),
        "body_kind": "json" if payload is not None else "text",
        "body": normalized_value(payload) if payload is not None else raw.decode(
            "utf-8", errors="replace"
        ),
        "body_text": raw.decode("utf-8", errors="replace"),
        "body_length_bytes": len(raw),
        "body_sha256": hashlib.sha256(raw).hexdigest(),
    }


def credential_mode(spec: CaseSpec) -> str:
    if spec.invalid_bearer and spec.session_actor is not None:
        return "session+invalid_bearer"
    if spec.bearer_actor is not None and spec.session_actor is not None:
        return "session+valid_bearer"
    if spec.bearer_actor is not None:
        return "valid_bearer_only"
    if spec.session_actor is not None:
        return "session"
    return "none"


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
        categories_before = table_fingerprint(db, "user_bank_categories")
        banks_before = table_fingerprint(db, "user_question_banks")
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
    with sql_probe(engine, fail_category_select=spec.fail_category_select) as sql:
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
        categories_after = table_fingerprint(db, "user_bank_categories")
        banks_after = table_fingerprint(db, "user_question_banks")
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
        "bearer_actor": spec.bearer_actor or ("invalid" if spec.invalid_bearer else "none"),
        "credential_mode": credential_mode(spec),
        "fixture_mode": spec.fixture_mode,
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
            "categories_before": categories_before,
            "categories_after": categories_after,
            "categories_match_case_fixture": categories_before == expected["categories"],
            "categories_unchanged": categories_before == categories_after,
            "banks_before": banks_before,
            "banks_after": banks_after,
            "banks_match_case_fixture": banks_before == expected["banks"],
            "banks_unchanged": banks_before == banks_after,
            "users_identity_before": identity_before,
            "users_identity_after": identity_after,
            "users_identity_unchanged": identity_before == identity_after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def response_categories(case: dict[str, Any]) -> list[dict[str, Any]]:
    body = case["response"]["body"]
    if not isinstance(body, dict):
        raise AssertionError(f"{case['case_id']} response is not an object")
    data = body.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise AssertionError(f"{case['case_id']} category envelope drifted")
    return data["categories"]


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 22 or len(cases) != 22 or len(by_id) != 22:
        raise AssertionError("personal-bank category case set must contain 22 unique cases")

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
        if not effects["categories_match_case_fixture"] or not effects["banks_match_case_fixture"]:
            raise AssertionError(f"{spec.case_id} did not start from its isolated fixture")
        if not effects["categories_unchanged"] or not effects["banks_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed personal-bank business facts")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed user identity facts")
        if effects["categories_before"]["column_count"] != 7:
            raise AssertionError(f"{spec.case_id} lost the seven-column category row")
        if sql["category_table_dml_attempts"] or sql["bank_table_dml_attempts"] or sql["ddl_attempts"]:
            raise AssertionError(f"{spec.case_id} attempted business DML or request DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")

        expected_activity = []
        if spec.session_actor is not None and spec.bearer_actor is None:
            expected_activity = [ACTORS[spec.session_actor]]
        if effects["user_last_active_changed_user_ids"] != expected_activity:
            raise AssertionError(
                f"{spec.case_id} last_active drifted: expected={expected_activity} "
                f"observed={effects['user_last_active_changed_user_ids']}"
            )
        if sql["user_last_active_dml_attempts"] != len(expected_activity):
            raise AssertionError(f"{spec.case_id} last_active ledger drifted")

        handler_reached = spec.expected_status == 200 or spec.fail_category_select
        expected_query_count = 1 if handler_reached else 0
        if sql["category_select_attempts"] != expected_query_count:
            raise AssertionError(f"{spec.case_id} auth/query boundary drifted")
        if expected_query_count and sql["category_select_bind_count"] != 1:
            raise AssertionError(f"{spec.case_id} must bind exactly one current user ID")

    expected_owner = [
        (CATEGORIES["negative"], ACTORS["owner"], "负主键分类", -5, 2),
        (CATEGORIES["zero"], ACTORS["owner"], "", 0, 1),
        (CATEGORIES["unicode"], ACTORS["owner"], "高数・α／🧪", 0, 0),
        (CATEGORIES["empty_name"], ACTORS["owner"], "尾部分类", 9, 0),
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
            rows = response_categories(by_id[case_id])
            actual = [
                (row["id"], row["user_id"], row["name"], row["sort_order"], row["bank_count"])
                for row in rows
            ]
            if actual != expected_owner:
                raise AssertionError(f"{case_id} projection/filter/order/count drifted: {actual}")
            if any(set(row) != {
                "id", "user_id", "name", "description", "sort_order",
                "created_at", "updated_at", "bank_count",
            } for row in rows):
                raise AssertionError(f"{case_id} must expose c.* plus bank_count")

        other = response_categories(by_id[f"auth-session-other-{route}"])
        if [(row["id"], row["bank_count"]) for row in other] != [
            (CATEGORIES["other_owner"], 1)
        ]:
            raise AssertionError(f"auth-session-other-{route} leaked another user's categories")
        if response_categories(by_id[f"data-empty-{route}"]) != []:
            raise AssertionError(f"data-empty-{route} must return an empty categories array")
        nullable = response_categories(by_id[f"data-nullable-fields-{route}"])
        if len(nullable) != 1 or any(nullable[0][field] is not None for field in (
            "description", "sort_order", "created_at", "updated_at",
        )):
            raise AssertionError(f"data-nullable-fields-{route} lost raw null fields")
        if nullable[0]["bank_count"] != 0:
            raise AssertionError(f"data-nullable-fields-{route} zero count drifted")

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
                    raise AssertionError(
                        f"{case_id} must preserve the Web alias global redirect"
                    )

        for fault in ("fault-default", "fault-json"):
            case = by_id[f"{fault}-{route}"]
            if "synthetic personal-bank" in case["response"]["body_text"]:
                raise AssertionError(f"{case['case_id']} leaked the injected failure")
        if by_id[f"fault-default-{route}"]["response"]["body_kind"] != (
            "json" if route == "api-alias" else "text"
        ):
            raise AssertionError(f"fault-default-{route} content negotiation drifted")
        if by_id[f"fault-json-{route}"]["response"]["body_kind"] != "json":
            raise AssertionError(f"fault-json-{route} must use safe JSON")


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
            "callers": caller_attestation(archived),
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4b-personal-bank-category-data-"
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
            "contract_id": "ti.phase4b.personal-bank-category-read-goldens",
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
            "personalbank_internal_primitive": {
                "capability": "list the authenticated identity's category rows with active bank counts",
                "tables": ["user_bank_categories", "user_question_banks"],
                "selected_columns": [
                    "id", "user_id", "name", "description", "sort_order",
                    "created_at", "updated_at", "bank_count",
                ],
                "selected_column_count": 8,
                "query_variant_count": 1,
                "bind_count": 1,
                "filter": "c.user_id equals the authenticated identity",
                "count_semantics": (
                    "count banks whose category_id equals c.id and status equals 1; "
                    "bank.user_id is deliberately not filtered"
                ),
                "pagination": None,
                "ordering": "c.sort_order ASC then signed c.id ASC",
                "query_parameters": "ignored",
            },
            "request_effect_scope": {
                "handler": "one SELECT-only aggregate; no personal-bank DML or DDL",
                "surrounding_web_session": (
                    "may SELECT users and commit users.last_active before the handler"
                ),
                "claim_boundary": (
                    "per-case ledgers separate the category read from authentication activity"
                ),
            },
            "dialect_observation": (
                "this isolated HTTP capture uses SQLite; its ASC null placement and raw "
                "YYYY-MM-DD HH:MM:SS timestamp strings are not PostgreSQL HTTP evidence. "
                "The checked PostgreSQL gate proves ASC NULLS LAST and nullable LocalDateTime "
                "mapping; the archived Flask JSON-provider attestation separately fixes RFC1123 "
                "datetime serialization, while a full PostgreSQL-backed legacy HTTP gate remains "
                "deferred until route-adapter migration."
            ),
            "caller_state": (
                "the only direct archived GET caller is in an unrendered dormant Web template; "
                "the /api compatibility alias has no direct static caller"
            ),
            "legacy_datetime_serializer_attestation": {
                "provider": "archived Flask app.json provider",
                "input": "datetime(2026, 7, 17, 8, 0, 0)",
                "output": serialized_datetime,
                "database_model_columns": {
                    "created_at": "DateTime nullable",
                    "updated_at": "DateTime nullable",
                },
                "scope": (
                    "model-type plus serializer contract only; not a PostgreSQL driver or full "
                    "legacy handler response"
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
                "categories": CATEGORIES,
                "banks": BANKS,
                "full_categories_fingerprint": full_fixture["categories"],
                "full_banks_fingerprint": full_fixture["banks"],
                "active_status_one_bank_count": 4,
                "inactive_or_non_one_bank_count": 4,
                "cross_owner_active_bank_count": 2,
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
        f"captured {document['case_count']} personal-bank category cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
