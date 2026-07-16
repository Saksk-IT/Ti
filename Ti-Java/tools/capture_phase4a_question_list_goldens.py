#!/usr/bin/env python3
"""Capture deterministic dual-route question-list goldens from pinned Flask source."""

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


FIXED_REQUEST_ID = "phase4a-question-list-golden-request"
ROUTES = {
    "modern": {
        "route_id": "1437bc4bf41b",
        "path": "/admin/api/questions",
        "route_template": "/admin/api/questions",
        "legacy_handler": "admin.admin_api.get_filtered_questions",
    },
    "legacy": {
        "route_id": "6cd7322bea3b",
        "path": "/admin/questions",
        "route_template": "/admin/questions",
        "legacy_handler": "admin.admin_api_legacy.get_filtered_questions",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/core/utils/portable_question_format.py",
    "app/models/subject.py",
    "app/models/user.py",
    "app/modules/admin/__init__.py",
    "app/modules/admin/routes/api_components/questions.py",
    "app/modules/admin/routes/api_legacy.py",
)
QUESTION_COLUMNS = (
    "id",
    "subject_id",
    "type",
    "content",
    "options",
    "answer",
    "analysis",
    "tags",
    "difficulty",
    "image_path",
    "source",
    "created_by",
    "updated_by",
    "created_at",
    "updated_at",
)
LIST_COLUMNS = (
    "id",
    "subject_id",
    "type",
    "content",
    "difficulty",
    "tags",
    "image_path",
    "created_by",
    "updated_at",
)
USER_IDENTITY_COLUMNS = (
    "id",
    "username",
    "is_admin",
    "is_subject_admin",
    "is_notification_admin",
    "is_locked",
    "session_version",
)
ACTORS = {
    "ordinary": 91001,
    "subject_admin": 91002,
    "administrator": 91003,
}
SUBJECTS = {
    "negative": -1,
    "zero": 0,
    "primary": 92001,
    "other": 92002,
}
QUESTIONS = {
    "negative_id": -7,
    "essay": 93001,
    "raw_chinese_type": 93002,
    "negative_subject": 93003,
    "zero_subject": 93004,
    "other_subject": 93005,
    "fill": 93006,
    "nulls": 93007,
    "malformed": 93008,
    "valid": 93009,
}
ORPHAN_CREATOR_ID = 91999


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    query: tuple[tuple[str, str], ...] = ()
    session_actor: str | None = "administrator"
    bearer_actor: str | None = None
    accept: str = "*/*"
    empty_questions: bool = False
    fail_collection_select: bool = False
    expected_status: int = 200


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        specs.extend((
            CaseSpec(f"auth-administrator-{route}", route),
            CaseSpec(
                f"auth-subject-admin-{route}", route,
                session_actor="subject_admin",
            ),
            CaseSpec(
                f"auth-ordinary-{route}", route,
                session_actor="ordinary", expected_status=403,
            ),
            CaseSpec(
                f"auth-anonymous-{route}", route,
                session_actor=None, expected_status=302,
            ),
            CaseSpec(
                f"auth-bearer-only-{route}", route,
                session_actor=None, bearer_actor="administrator", expected_status=302,
            ),
            CaseSpec(
                f"auth-ordinary-session-plus-bearer-{route}", route,
                session_actor="ordinary", bearer_actor="administrator", expected_status=302,
            ),
            CaseSpec(f"data-empty-table-{route}", route, empty_questions=True),
            CaseSpec(f"data-default-multi-{route}", route),
            CaseSpec(
                f"subject-exact-{route}", route,
                query=(("subject_id", str(SUBJECTS["primary"])),),
            ),
            CaseSpec(
                f"subject-not-found-{route}", route,
                query=(("subject_id", "999999"),),
            ),
            CaseSpec(
                f"subject-empty-{route}", route,
                query=(("subject_id", ""),),
            ),
            CaseSpec(
                f"subject-zero-{route}", route,
                query=(("subject_id", "0"),),
            ),
            CaseSpec(
                f"subject-negative-{route}", route,
                query=(("subject_id", "-1"),),
            ),
            CaseSpec(
                f"subject-blank-{route}", route,
                query=(("subject_id", " "),),
            ),
            CaseSpec(
                f"subject-out-of-range-{route}", route,
                query=(("subject_id", "9223372036854775808"),),
            ),
            CaseSpec(
                f"subject-repeated-first-value-{route}", route,
                query=(
                    ("subject_id", str(SUBJECTS["primary"])),
                    ("subject_id", str(SUBJECTS["other"])),
                ),
            ),
            CaseSpec(f"type-default-all-{route}", route),
            CaseSpec(
                f"type-chinese-raw-{route}", route,
                query=(("type", "选择题"),),
            ),
            CaseSpec(
                f"type-single-choice-{route}", route,
                query=(("type", "single_choice"),),
            ),
            CaseSpec(
                f"type-single-alias-{route}", route,
                query=(("type", "single"),),
            ),
            CaseSpec(
                f"type-empty-{route}", route,
                query=(("type", ""),),
            ),
            CaseSpec(
                f"type-uppercase-all-{route}", route,
                query=(("type", "ALL"),),
            ),
            CaseSpec(
                f"type-unknown-{route}", route,
                query=(("type", "unknown"),),
            ),
            CaseSpec(
                f"fault-html-{route}", route,
                fail_collection_select=True, expected_status=500,
            ),
            CaseSpec(
                f"fault-json-{route}", route,
                accept="application/json", fail_collection_select=True,
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


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: Mapping[str, Any]) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
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
    return normalized_sql(statement).startswith(("INSERT ", "UPDATE ", "DELETE ", "REPLACE "))


def is_ddl_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith((
        "CREATE ", "ALTER ", "DROP ", "TRUNCATE ", "COMMENT ",
        "GRANT ", "REVOKE ", "VACUUM ", "ANALYZE ", "PRAGMA ",
    ))


def is_question_collection_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    signature = (
        "SELECT Q.ID, Q.SUBJECT_ID, Q.TYPE, Q.CONTENT, Q.DIFFICULTY, Q.TAGS, "
        "Q.IMAGE_PATH, U.USERNAME AS CREATED_BY, Q.UPDATED_AT FROM QUESTIONS Q "
        "LEFT JOIN USERS U ON Q.CREATED_BY = U.ID WHERE 1=1"
    )
    return sql.startswith(signature) and sql.endswith("ORDER BY Q.ID DESC")


def is_question_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(
        r"^(INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+QUESTIONS\b",
        sql,
    ))


def is_users_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return is_select_statement(statement) and bool(
        re.search(r"\b(?:FROM|JOIN)\s+USERS\b", sql)
    )


def is_user_last_active_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(
        r"^UPDATE\s+USERS\s+SET\s+LAST_ACTIVE\s*=", sql
    )) and bool(re.search(r"\bWHERE\s+USERS\.ID\s*=", sql))


@contextmanager
def sql_probe(engine: Any, *, fail_collection_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "question_collection_select_attempts": 0,
        "question_dml_attempts": 0,
        "users_select_attempts": 0,
        "auth_users_select_attempts": 0,
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
        collection = is_question_collection_select(statement)
        question_write = is_question_dml(statement)
        users_read = is_users_select(statement)
        activity_write = is_user_last_active_dml(statement)
        classification = (
            "question_collection_select" if collection
            else "user_last_active_dml" if activity_write
            else "question_dml" if question_write
            else "ddl" if ddl
            else "users_select" if users_read
            else "select" if select
            else "dml" if dml
            else "other"
        )
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
        ledger["question_collection_select_attempts"] += int(collection)
        ledger["question_dml_attempts"] += int(question_write)
        ledger["users_select_attempts"] += int(users_read)
        ledger["auth_users_select_attempts"] += int(users_read and not collection)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if collection and fail_collection_select:
            raise RuntimeError("synthetic question-list collection SELECT failure")

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield ledger
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        ledger["statement_count"] = len(ledger["statements"])
        ledger["classified_attempt_count"] = (
            ledger["select_attempts"]
            + ledger["dml_attempts"]
            + ledger["ddl_attempts"]
            + ledger["other_attempts"]
        )
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


def question_rows(db: Any) -> list[list[Any]]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        f"SELECT {', '.join(QUESTION_COLUMNS)} FROM questions ORDER BY id"
    )).fetchall()
    return [[normalized_value(value) for value in row] for row in rows]


def question_fingerprint(db: Any) -> dict[str, Any]:
    rows = question_rows(db)
    return {
        "columns": list(QUESTION_COLUMNS),
        "column_count": len(QUESTION_COLUMNS),
        "row_count": len(rows),
        "rows_sha256": sha256_json(rows),
    }


def user_identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        f"SELECT {', '.join(USER_IDENTITY_COLUMNS)} FROM users "
        "WHERE id IN (:ordinary, :subject_admin, :administrator) ORDER BY id"
    ), ACTORS).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "columns": list(USER_IDENTITY_COLUMNS),
        "column_count": len(USER_IDENTITY_COLUMNS),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def user_activity_snapshot(db: Any) -> tuple[dict[int, Any], list[dict[str, Any]]]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        "SELECT id, last_active FROM users "
        "WHERE id IN (:ordinary, :subject_admin, :administrator) ORDER BY id"
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
    if {row["route_id"] for row in selected} != route_ids:
        raise AssertionError("question-list routes are missing from the frozen route matrix")
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


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def fixture_rows() -> list[dict[str, Any]]:
    fixed = "2026-07-16 08:00:00"
    base = {
        "subject_id": SUBJECTS["primary"],
        "type": "essay",
        "content": "固定题干",
        "options": "[]",
        "answer": "[]",
        "analysis": "固定解析",
        "tags": compact_json(["phase4a"]),
        "difficulty": 2,
        "image_path": None,
        "source": "phase4a-question-list-golden",
        "created_by": ACTORS["administrator"],
        "updated_by": ACTORS["administrator"],
        "created_at": fixed,
        "updated_at": fixed,
    }

    def row(question_id: int, **updates: Any) -> dict[str, Any]:
        result = {**base, "id": question_id}
        result.update(updates)
        return result

    return [
        row(QUESTIONS["negative_id"], content="负题目主键简答题"),
        row(QUESTIONS["essay"], content="普通简答题"),
        row(
            QUESTIONS["raw_chinese_type"], type="选择题",
            content="数据库原始中文题型",
        ),
        row(
            QUESTIONS["negative_subject"], subject_id=SUBJECTS["negative"],
            type="single_choice", content="负数科目题",
        ),
        row(
            QUESTIONS["zero_subject"], subject_id=SUBJECTS["zero"],
            type="boolean", content="零号科目题",
        ),
        row(
            QUESTIONS["other_subject"], subject_id=SUBJECTS["other"],
            type="multi_choice", content="另一科目题",
        ),
        row(
            QUESTIONS["fill"], type="fill", content="甲{1}乙{0}丙",
            answer=compact_json([["零"], ["一"]]),
        ),
        row(
            QUESTIONS["nulls"], type="essay", content="可空字段题",
            tags=None, difficulty=None, image_path=None,
            created_by=None, updated_by=None,
        ),
        row(
            QUESTIONS["malformed"], type="single_choice", content="畸形字段题",
            tags="[broken-tags", image_path="not-json-image",
            created_by=ORPHAN_CREATOR_ID,
        ),
        row(
            QUESTIONS["valid"], type="single_choice", content="合法字段题",
            tags=compact_json(["数学", "核心"]),
            image_path=compact_json(["/uploads/questions/list.png"]),
            created_by=ACTORS["administrator"],
        ),
    ]


def seed_static_fixture(db: Any, User: Any) -> None:
    from sqlalchemy import text

    fixed = datetime(2026, 7, 16, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4a_list_{actor}",
            email=f"phase4a_list_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=actor == "administrator",
            is_subject_admin=actor == "subject_admin",
            is_notification_admin=False,
            is_locked=False,
            session_version=7,
            created_at=fixed,
            last_active=None,
        ))
    subjects = [
        {
            "id": subject_id,
            "name": f"题目列表证据科目-{name}",
            "description": "public synthetic fixture",
            "is_locked": False,
            "created_at": fixed,
        }
        for name, subject_id in SUBJECTS.items()
    ]
    db.session.execute(text(
        "INSERT INTO subjects (id, name, description, is_locked, created_at) "
        "VALUES (:id, :name, :description, :is_locked, :created_at)"
    ), subjects)
    db.session.commit()


def reset_case_facts(db: Any, *, empty_questions: bool) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    db.session.execute(text("DELETE FROM questions"))
    if not empty_questions:
        db.session.execute(text(
            "INSERT INTO questions "
            f"({', '.join(QUESTION_COLUMNS)}) VALUES "
            f"({', '.join(':' + column for column in QUESTION_COLUMNS)})"
        ), fixture_rows())
    db.session.execute(text(
        "UPDATE users SET last_active = NULL "
        "WHERE id IN (:ordinary, :subject_admin, :administrator)"
    ), ACTORS)
    db.session.commit()
    return question_fingerprint(db)


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4a_list_{actor}",
            "session_version": 7,
            "is_admin": actor == "administrator",
            "is_subject_admin": actor == "subject_admin",
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
            values = ["<dynamic-epoch-second>" for _value in values]
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
        "body": normalized_value(payload) if payload is not None else raw.decode("utf-8", errors="replace"),
        "body_text": raw.decode("utf-8", errors="replace"),
        "body_length_bytes": len(raw),
        "body_sha256": hashlib.sha256(raw).hexdigest(),
    }


def credential_mode(spec: CaseSpec) -> str:
    if spec.session_actor is not None and spec.bearer_actor is not None:
        return "session+valid_bearer"
    if spec.bearer_actor is not None:
        return "valid_bearer_only"
    if spec.session_actor is not None:
        return "session"
    return "none"


def recorded_request_headers(spec: CaseSpec) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.bearer_actor is not None:
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
    route = ROUTES[spec.route]
    set_actor_session(client, spec.session_actor)
    reset_limiters(client.application)
    with client.application.app_context():
        expected_questions = reset_case_facts(db, empty_questions=spec.empty_questions)
        before = question_fingerprint(db)
        users_identity_before = user_identity_fingerprint(db)
        raw_activity_before, activity_before = user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    with sql_probe(engine, fail_collection_select=spec.fail_collection_select) as sql:
        response = client.get(
            route["path"],
            query_string=list(spec.query),
            headers=live_request_headers(spec, tokens),
            environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
            follow_redirects=False,
        )
    with client.application.app_context():
        try:
            db.session.rollback()
        finally:
            db.session.remove()
        after = question_fingerprint(db)
        users_identity_after = user_identity_fingerprint(db)
        raw_activity_after, activity_after = user_activity_snapshot(db)
        db.session.remove()
    changed_activity_ids = sorted(
        user_id
        for user_id in raw_activity_before
        if raw_activity_before[user_id] != raw_activity_after[user_id]
    )
    query_items = [{"name": name, "value": value} for name, value in spec.query]
    query_string = urlencode(list(spec.query))
    return {
        "case_id": spec.case_id,
        "route": spec.route,
        "route_id": route["route_id"],
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or "none",
        "credential_mode": credential_mode(spec),
        "fixture_mode": "empty_questions" if spec.empty_questions else "full_questions",
        "request": {
            "method": "GET",
            "path": route["path"],
            "route_template": route["route_template"],
            "query": query_items,
            "query_string": query_string,
            "headers": recorded_request_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "response": normalized_response(response),
        "observed_get_effects": {
            "sql": sql,
            "questions_before": before,
            "questions_after": after,
            "questions_match_case_fixture": before == expected_questions,
            "questions_unchanged": before == after,
            "users_identity_before": users_identity_before,
            "users_identity_after": users_identity_after,
            "users_identity_unchanged": users_identity_before == users_identity_after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def response_ids(case: dict[str, Any]) -> list[int]:
    body = case["response"]["body"]
    if not isinstance(body, list):
        return []
    return [int(item["id"]) for item in body]


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 50 or len(by_id) != 50 or len(cases) != 50:
        raise AssertionError("question-list case set drifted, duplicated, or is not exactly 50")
    expected_desc = sorted(QUESTIONS.values(), reverse=True)
    primary_desc = sorted((
        QUESTIONS["negative_id"], QUESTIONS["essay"],
        QUESTIONS["raw_chinese_type"], QUESTIONS["fill"],
        QUESTIONS["nulls"], QUESTIONS["malformed"], QUESTIONS["valid"],
    ), reverse=True)
    single_choice_desc = sorted((
        QUESTIONS["negative_subject"], QUESTIONS["malformed"], QUESTIONS["valid"],
    ), reverse=True)
    essay_desc = sorted((
        QUESTIONS["negative_id"], QUESTIONS["essay"], QUESTIONS["nulls"],
    ), reverse=True)

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
        if not effects["questions_match_case_fixture"]:
            raise AssertionError(f"{spec.case_id} did not start from its isolated fixture")
        if not effects["questions_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed a question fact")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed a user identity/role fact")
        if effects["questions_before"]["column_count"] != 15:
            raise AssertionError(f"{spec.case_id} lost the 15-column question fingerprint")
        if sql["question_dml_attempts"] != 0 or sql["ddl_attempts"] != 0:
            raise AssertionError(f"{spec.case_id} attempted question DML or request DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")

        expected_activity = (
            [ACTORS[spec.session_actor]]
            if spec.session_actor is not None and spec.bearer_actor is None
            else []
        )
        if effects["user_last_active_changed_user_ids"] != expected_activity:
            raise AssertionError(
                f"{spec.case_id} last_active side effect drifted: "
                f"expected={expected_activity} "
                f"observed={effects['user_last_active_changed_user_ids']}"
            )
        if sql["user_last_active_dml_attempts"] != len(expected_activity):
            raise AssertionError(f"{spec.case_id} last_active SQL ledger drifted")

    for route in ROUTES:
        for actor in ("administrator", "subject-admin"):
            case = by_id[f"auth-{actor}-{route}"]
            if case["response"]["status"] != 200:
                raise AssertionError(f"{case['case_id']} auth status drifted")
            if case["observed_get_effects"]["sql"]["question_collection_select_attempts"] != 1:
                raise AssertionError(f"{case['case_id']} did not execute one collection SELECT")
        for scenario in (
            "ordinary", "anonymous", "bearer-only", "ordinary-session-plus-bearer",
        ):
            case = by_id[f"auth-{scenario}-{route}"]
            if case["observed_get_effects"]["sql"]["question_collection_select_attempts"] != 0:
                raise AssertionError(f"{case['case_id']} crossed the auth-before-query boundary")

        empty = by_id[f"data-empty-table-{route}"]
        if empty["response"]["body"] != []:
            raise AssertionError(f"{empty['case_id']} empty-table body drifted")
        if empty["observed_get_effects"]["questions_before"]["row_count"] != 0:
            raise AssertionError(f"{empty['case_id']} is not an empty-table fixture")
        default = by_id[f"data-default-multi-{route}"]
        if response_ids(default) != expected_desc:
            raise AssertionError(f"{default['case_id']} lost strict id DESC ordering")

        expected_subjects = {
            "exact": primary_desc,
            "not-found": [],
            "empty": expected_desc,
            "zero": [QUESTIONS["zero_subject"]],
            "negative": [QUESTIONS["negative_subject"]],
            "blank": [],
            "out-of-range": [],
            "repeated-first-value": primary_desc,
        }
        for scenario, expected in expected_subjects.items():
            case = by_id[f"subject-{scenario}-{route}"]
            if response_ids(case) != expected:
                raise AssertionError(
                    f"{case['case_id']} subject filter drifted: "
                    f"expected={expected} observed={response_ids(case)}"
                )

        expected_types = {
            "default-all": expected_desc,
            "chinese-raw": single_choice_desc,
            "single-choice": single_choice_desc if route == "modern" else essay_desc,
            "single-alias": single_choice_desc if route == "modern" else essay_desc,
            "empty": essay_desc,
            "uppercase-all": essay_desc,
            "unknown": essay_desc,
        }
        for scenario, expected in expected_types.items():
            case = by_id[f"type-{scenario}-{route}"]
            if response_ids(case) != expected:
                raise AssertionError(
                    f"{case['case_id']} type filter drifted: "
                    f"expected={expected} observed={response_ids(case)}"
                )

        for mode in ("html", "json"):
            failure = by_id[f"fault-{mode}-{route}"]
            if failure["observed_get_effects"]["sql"]["question_collection_select_attempts"] != 1:
                raise AssertionError(f"{failure['case_id']} did not attempt the injected SELECT")

    modern = {
        item["id"]: item
        for item in by_id["data-default-multi-modern"]["response"]["body"]
    }
    legacy = {
        item["id"]: item
        for item in by_id["data-default-multi-legacy"]["response"]["body"]
    }
    if modern[QUESTIONS["fill"]]["content"] != "甲__乙__丙":
        raise AssertionError("modern PQF fill-content projection drifted")
    if legacy[QUESTIONS["fill"]]["content"] != "甲{1}乙{0}丙":
        raise AssertionError("legacy raw fill-content projection drifted")
    if modern[QUESTIONS["valid"]]["tags"] != "数学,核心":
        raise AssertionError("modern valid tag projection drifted")
    if legacy[QUESTIONS["valid"]]["tags"] != ["数学", "核心"]:
        raise AssertionError("legacy valid tag projection drifted")
    if modern[QUESTIONS["nulls"]]["tags"] != "":
        raise AssertionError("modern null tag projection drifted")
    if legacy[QUESTIONS["nulls"]]["tags"] is not None:
        raise AssertionError("legacy null tag projection drifted")
    for projection in (modern, legacy):
        if projection[QUESTIONS["malformed"]]["tags"] != "[broken-tags":
            raise AssertionError("malformed tags were not retained")
        if projection[QUESTIONS["malformed"]]["image_path"] != '["not-json-image"]':
            raise AssertionError("malformed/scalar image compatibility wrapper drifted")
        if projection[QUESTIONS["nulls"]]["image_path"] != "[]":
            raise AssertionError("null image projection drifted")
        if projection[QUESTIONS["valid"]]["created_by"] != "phase4a_list_administrator":
            raise AssertionError("existing creator LEFT JOIN projection drifted")
        if projection[QUESTIONS["malformed"]]["created_by"] is not None:
            raise AssertionError("orphan creator LEFT JOIN projection drifted")
        if projection[QUESTIONS["nulls"]]["created_by"] is not None:
            raise AssertionError("null creator LEFT JOIN projection drifted")


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
            "question_list_key_sources": key_source_attestation(archived),
        }
        with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-question-list-data-") as data_dir:
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
                            seed_static_fixture(db, User)
                            full_fixture_fingerprint = reset_case_facts(
                                db, empty_questions=False,
                            )
                            tokens = {
                                actor: generate_jwt_token(
                                    user_id=user_id, openid="", session_version=7,
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
            "contract_id": "ti.phase4a.question-list-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-16",
            "legacy_commit": pinned_source.LEGACY_COMMIT,
            "legacy_source_attestation": source_attestation,
            "route_status": {
                "target_internal_owner": "catalog",
                "http_owner": "operations",
                "migration_status": "pending",
                "production_cutover": False,
                "routes": list(ROUTES.values()),
            },
            "catalog_internal_primitive": {
                "capability": "read a filtered question collection projection",
                "table": "questions",
                "joined_table": "users",
                "selected_columns": list(LIST_COLUMNS),
                "selected_column_count": len(LIST_COLUMNS),
                "ordering": "q.id DESC",
                "subject_filter": "raw first-value query string, applied only when truthy",
                "type_filter": "route-specific legacy normalization, applied unless exactly lowercase all",
                "http_projection_owner": "operations until auth and payload parity are migrated",
            },
            "request_effect_scope": {
                "question_collection_handler": (
                    "one SELECT-only collection query; no questions DML or DDL"
                ),
                "surrounding_web_session": (
                    "may SELECT users and commit users.last_active before the collection handler"
                ),
                "claim_boundary": (
                    "per-case ledgers separate collection reads from authentication activity; "
                    "this evidence does not claim that the entire HTTP request is write-free"
                ),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory limiter; no current working-tree legacy import or persistent data"
            ),
            "case_isolation": (
                "every request resets the full or empty questions fixture and actor last_active "
                "outside its SQL ledger, gets a fresh explicit Session scenario, reset limiter, "
                "deterministic remote address, pre/post 15-column questions fingerprint, "
                "pre/post stable user-identity fingerprint, and a separate last_active ledger"
            ),
            "response_capture": (
                "full response body text and parsed body, body length/hash, and every test-client "
                "response header; session cookies are redacted and wall-clock activity values "
                "are represented by explicit deterministic placeholders"
            ),
            "redaction": (
                "synthetic identities only; JWT, password hash, session-cookie values, and "
                "database-current last_active timestamps omitted; fixed request ID"
            ),
            "fixture": {
                "actors": ACTORS,
                "subjects": SUBJECTS,
                "questions": QUESTIONS,
                "orphan_creator_id": ORPHAN_CREATOR_ID,
                "full_questions_fingerprint": full_fixture_fingerprint,
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
        f"captured {document['case_count']} question-list cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
