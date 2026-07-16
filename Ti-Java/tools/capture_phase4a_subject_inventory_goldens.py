#!/usr/bin/env python3
"""Capture deterministic admin subject-inventory goldens from pinned Flask source."""

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


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


FIXED_REQUEST_ID = "phase4a-subject-inventory-golden-request"
ROUTE = {
    "route_id": "6e1a36f5052d",
    "path": "/admin/api/subjects",
    "route_template": "/admin/api/subjects",
    "legacy_handler": "admin.admin_api.api_get_subjects",
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/models/subject.py",
    "app/models/user.py",
    "app/modules/admin/__init__.py",
    "app/modules/admin/routes/api.py",
    "app/modules/admin/routes/api_bp.py",
    "app/modules/admin/routes/api_components/subjects.py",
    "app/modules/admin/templates/admin/subjects/_question_scripts.html",
    "app/modules/admin/templates/admin/subjects/_scripts.html",
    "app/modules/admin/templates/admin/subjects/legacy.html",
)
SUBJECT_COLUMNS = (
    "id",
    "name",
    "description",
    "is_locked",
    "plaza_board_id",
    "is_plaza_featured",
    "plaza_featured_weight",
    "plaza_featured_at",
    "created_at",
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
    "ordinary": 94001,
    "subject_admin": 94002,
    "administrator": 94003,
}
SUBJECTS = {
    "negative_unlocked": -9,
    "zero_null_locked_empty_name": 0,
    "unicode_locked": 95001,
    "positive_unlocked": 95002,
}
SINGLE_SUBJECT_ID = -3
ORPHAN_SUBJECT_ID = 95999
QUESTIONS = {
    "negative_subject": 96001,
    "unicode_subject_first": 96002,
    "unicode_subject_second": 96003,
    "positive_subject": 96004,
    "null_subject": 96005,
    "orphan_subject": 96006,
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    session_actor: str | None = "administrator"
    bearer_actor: str | None = None
    accept: str = "*/*"
    fixture_mode: str = "full"
    fail_inventory_select: bool = False
    expected_status: int = 200


CASE_SPECS = (
    CaseSpec("auth-administrator"),
    CaseSpec("auth-subject-admin", session_actor="subject_admin"),
    CaseSpec("auth-ordinary", session_actor="ordinary", expected_status=403),
    CaseSpec("auth-anonymous", session_actor=None, expected_status=302),
    CaseSpec(
        "auth-bearer-only",
        session_actor=None,
        bearer_actor="administrator",
        expected_status=302,
    ),
    CaseSpec(
        "auth-ordinary-session-plus-admin-bearer",
        session_actor="ordinary",
        bearer_actor="administrator",
        expected_status=302,
    ),
    CaseSpec("data-empty-tables", fixture_mode="empty"),
    CaseSpec("data-single-subject", fixture_mode="single"),
    CaseSpec("data-multi-subject-edges", fixture_mode="full"),
    CaseSpec(
        "fault-html",
        fail_inventory_select=True,
        expected_status=500,
    ),
    CaseSpec(
        "fault-json",
        accept="application/json",
        fail_inventory_select=True,
        expected_status=500,
    ),
)


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


def is_subject_inventory_select(statement: Any) -> bool:
    return normalized_sql(statement) == (
        "SELECT S.ID, S.NAME, S.IS_LOCKED, COUNT(Q.ID) AS QUESTION_COUNT "
        "FROM SUBJECTS S LEFT JOIN QUESTIONS Q ON S.ID = Q.SUBJECT_ID "
        "GROUP BY S.ID, S.NAME, S.IS_LOCKED ORDER BY S.ID"
    )


def is_table_dml(statement: Any, table: str) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(
        rf"^(INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+{table.upper()}\b",
        sql,
    ))


def reads_table(statement: Any, table: str) -> bool:
    sql = normalized_sql(statement)
    return is_select_statement(statement) and bool(
        re.search(rf"\b(?:FROM|JOIN)\s+{table.upper()}\b", sql)
    )


def is_user_last_active_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(
        r"^UPDATE\s+USERS\s+SET\s+LAST_ACTIVE\s*=", sql
    )) and bool(re.search(r"\bWHERE\s+USERS\.ID\s*=", sql))


@contextmanager
def sql_probe(engine: Any, *, fail_inventory_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "subject_inventory_select_attempts": 0,
        "subjects_select_attempts": 0,
        "questions_select_attempts": 0,
        "users_select_attempts": 0,
        "subjects_dml_attempts": 0,
        "questions_dml_attempts": 0,
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
        inventory = is_subject_inventory_select(statement)
        subjects_read = reads_table(statement, "subjects")
        questions_read = reads_table(statement, "questions")
        users_read = reads_table(statement, "users")
        subjects_write = is_table_dml(statement, "subjects")
        questions_write = is_table_dml(statement, "questions")
        activity_write = is_user_last_active_dml(statement)
        classification = (
            "subject_inventory_select" if inventory
            else "user_last_active_dml" if activity_write
            else "subjects_dml" if subjects_write
            else "questions_dml" if questions_write
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
        ledger["subject_inventory_select_attempts"] += int(inventory)
        ledger["subjects_select_attempts"] += int(subjects_read)
        ledger["questions_select_attempts"] += int(questions_read)
        ledger["users_select_attempts"] += int(users_read)
        ledger["subjects_dml_attempts"] += int(subjects_write)
        ledger["questions_dml_attempts"] += int(questions_write)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if inventory and fail_inventory_select:
            raise RuntimeError("synthetic subject-inventory SELECT failure")

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


def table_fingerprint(db: Any, table: str, columns: tuple[str, ...]) -> dict[str, Any]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
    )).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "columns": list(columns),
        "column_count": len(columns),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def subject_fingerprint(db: Any) -> dict[str, Any]:
    return table_fingerprint(db, "subjects", SUBJECT_COLUMNS)


def question_fingerprint(db: Any) -> dict[str, Any]:
    return table_fingerprint(db, "questions", QUESTION_COLUMNS)


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
    selected = [row for row in rows if row["route_id"] == ROUTE["route_id"]]
    if len(selected) != 1:
        raise AssertionError("subject-inventory route is missing or duplicated in route matrix")
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


def fixed_subject_rows(mode: str) -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 16, 8, 0, 0)
    if mode == "empty":
        return []
    if mode == "single":
        return [{
            "id": SINGLE_SUBJECT_ID,
            "name": "单一科目・β",
            "description": "single subject fixture",
            "is_locked": True,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        }]
    if mode != "full":
        raise AssertionError(f"unknown fixture mode: {mode}")
    return [
        {
            "id": SUBJECTS["negative_unlocked"],
            "name": "负主键科目",
            "description": "negative signed identifier",
            "is_locked": False,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["zero_null_locked_empty_name"],
            "name": "",
            "description": None,
            "is_locked": None,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["unicode_locked"],
            "name": "算法基础・α／中文",
            "description": "unicode subject name",
            "is_locked": True,
            "plaza_board_id": None,
            "is_plaza_featured": True,
            "plaza_featured_weight": -1,
            "plaza_featured_at": fixed,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["positive_unlocked"],
            "name": "数据库系统",
            "description": "positive signed identifier",
            "is_locked": False,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
    ]


def fixed_question_rows(mode: str) -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 16, 8, 0, 0)

    def row(question_id: int, subject_id: int | None, content: str) -> dict[str, Any]:
        return {
            "id": question_id,
            "subject_id": subject_id,
            "type": "essay",
            "content": content,
            "options": "[]",
            "answer": "[]",
            "analysis": None,
            "tags": "[]",
            "difficulty": 1,
            "image_path": None,
            "source": "phase4a-subject-inventory-golden",
            "created_by": ACTORS["administrator"],
            "updated_by": ACTORS["administrator"],
            "created_at": fixed,
            "updated_at": fixed,
        }

    if mode == "empty":
        return []
    if mode == "single":
        return [
            row(96101, SINGLE_SUBJECT_ID, "单科目题一"),
            row(96102, SINGLE_SUBJECT_ID, "单科目题二"),
            row(96103, None, "单科目场景空科目外键题"),
            row(96104, ORPHAN_SUBJECT_ID, "单科目场景孤儿科目外键题"),
        ]
    if mode != "full":
        raise AssertionError(f"unknown fixture mode: {mode}")
    return [
        row(QUESTIONS["negative_subject"], SUBJECTS["negative_unlocked"], "负主键科目题"),
        row(QUESTIONS["unicode_subject_first"], SUBJECTS["unicode_locked"], "Unicode 科目题一"),
        row(QUESTIONS["unicode_subject_second"], SUBJECTS["unicode_locked"], "Unicode 科目题二"),
        row(QUESTIONS["positive_subject"], SUBJECTS["positive_unlocked"], "正主键科目题"),
        row(QUESTIONS["null_subject"], None, "空科目外键题"),
        row(QUESTIONS["orphan_subject"], ORPHAN_SUBJECT_ID, "孤儿科目外键题"),
    ]


def seed_static_fixture(db: Any, User: Any) -> None:
    from sqlalchemy import text

    foreign_keys = db.session.execute(text("PRAGMA foreign_keys = OFF"))
    foreign_keys.close()
    fixed = datetime(2026, 7, 16, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4a_subject_inventory_{actor}",
            email=f"phase4a_subject_inventory_{actor}@test.example.com",
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
    db.session.commit()


def reset_case_facts(db: Any, mode: str) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    db.session.execute(text("DELETE FROM questions"))
    db.session.execute(text("DELETE FROM subjects"))
    subjects = fixed_subject_rows(mode)
    questions = fixed_question_rows(mode)
    if subjects:
        db.session.execute(text(
            "INSERT INTO subjects "
            f"({', '.join(SUBJECT_COLUMNS)}) VALUES "
            f"({', '.join(':' + column for column in SUBJECT_COLUMNS)})"
        ), subjects)
    if questions:
        db.session.execute(text(
            "INSERT INTO questions "
            f"({', '.join(QUESTION_COLUMNS)}) VALUES "
            f"({', '.join(':' + column for column in QUESTION_COLUMNS)})"
        ), questions)
    db.session.execute(text(
        "UPDATE users SET last_active = NULL "
        "WHERE id IN (:ordinary, :subject_admin, :administrator)"
    ), ACTORS)
    db.session.commit()
    return {
        "subjects": subject_fingerprint(db),
        "questions": question_fingerprint(db),
    }


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4a_subject_inventory_{actor}",
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
    set_actor_session(client, spec.session_actor)
    reset_limiters(client.application)
    with client.application.app_context():
        expected = reset_case_facts(db, spec.fixture_mode)
        subjects_before = subject_fingerprint(db)
        questions_before = question_fingerprint(db)
        users_identity_before = user_identity_fingerprint(db)
        raw_activity_before, activity_before = user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    with sql_probe(engine, fail_inventory_select=spec.fail_inventory_select) as sql:
        response = client.get(
            ROUTE["path"],
            headers=live_request_headers(spec, tokens),
            environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
            follow_redirects=False,
        )
    with client.application.app_context():
        try:
            db.session.rollback()
        finally:
            db.session.remove()
        subjects_after = subject_fingerprint(db)
        questions_after = question_fingerprint(db)
        users_identity_after = user_identity_fingerprint(db)
        raw_activity_after, activity_after = user_activity_snapshot(db)
        db.session.remove()
    changed_activity_ids = sorted(
        user_id
        for user_id in raw_activity_before
        if raw_activity_before[user_id] != raw_activity_after[user_id]
    )
    return {
        "case_id": spec.case_id,
        "route_id": ROUTE["route_id"],
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or "none",
        "credential_mode": credential_mode(spec),
        "fixture_mode": spec.fixture_mode,
        "request": {
            "method": "GET",
            "path": ROUTE["path"],
            "route_template": ROUTE["route_template"],
            "query": [],
            "query_string": "",
            "headers": recorded_request_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "response": normalized_response(response),
        "observed_get_effects": {
            "sql": sql,
            "subjects_before": subjects_before,
            "subjects_after": subjects_after,
            "subjects_match_case_fixture": subjects_before == expected["subjects"],
            "subjects_unchanged": subjects_before == subjects_after,
            "questions_before": questions_before,
            "questions_after": questions_after,
            "questions_match_case_fixture": questions_before == expected["questions"],
            "questions_unchanged": questions_before == questions_after,
            "users_identity_before": users_identity_before,
            "users_identity_after": users_identity_after,
            "users_identity_unchanged": users_identity_before == users_identity_after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 11 or len(cases) != 11 or len(by_id) != 11:
        raise AssertionError("subject-inventory case set drifted, duplicated, or is not exactly 11")

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
        if not effects["subjects_match_case_fixture"] or not effects["questions_match_case_fixture"]:
            raise AssertionError(f"{spec.case_id} did not start from its isolated fixture")
        if not effects["subjects_unchanged"] or not effects["questions_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed catalog facts")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed a user identity/role fact")
        if effects["subjects_before"]["column_count"] != 9:
            raise AssertionError(f"{spec.case_id} lost the 9-column subject fingerprint")
        if effects["questions_before"]["column_count"] != 15:
            raise AssertionError(f"{spec.case_id} lost the 15-column question fingerprint")
        if sql["subjects_dml_attempts"] or sql["questions_dml_attempts"] or sql["ddl_attempts"]:
            raise AssertionError(f"{spec.case_id} attempted catalog DML or request DDL")
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

    for case_id in (
        "auth-administrator",
        "auth-subject-admin",
        "data-empty-tables",
        "data-single-subject",
        "data-multi-subject-edges",
    ):
        case = by_id[case_id]
        sql = case["observed_get_effects"]["sql"]
        if sql["subject_inventory_select_attempts"] != 1:
            raise AssertionError(f"{case_id} did not execute one inventory SELECT")
        inventory = [
            statement
            for statement in sql["statements"]
            if statement["classification"] == "subject_inventory_select"
        ]
        if len(inventory) != 1 or inventory[0]["parameters"] not in ([], {}):
            raise AssertionError(f"{case_id} inventory query gained dynamic binds")

    for case_id in (
        "auth-ordinary",
        "auth-anonymous",
        "auth-bearer-only",
        "auth-ordinary-session-plus-admin-bearer",
    ):
        if by_id[case_id]["observed_get_effects"]["sql"]["subject_inventory_select_attempts"]:
            raise AssertionError(f"{case_id} crossed the auth-before-query boundary")

    for case_id in ("fault-html", "fault-json"):
        if by_id[case_id]["observed_get_effects"]["sql"]["subject_inventory_select_attempts"] != 1:
            raise AssertionError(f"{case_id} did not attempt the injected inventory SELECT")

    if by_id["data-empty-tables"]["response"]["body"] != []:
        raise AssertionError("empty-table subject inventory body drifted")
    single = by_id["data-single-subject"]["response"]["body"]
    if single != [{
        "id": SINGLE_SUBJECT_ID,
        "name": "单一科目・β",
        "is_locked": 1,
        "question_count": 2,
    }]:
        raise AssertionError(f"single-subject projection drifted: {single}")
    multi = by_id["data-multi-subject-edges"]["response"]["body"]
    expected_multi = [
        {"id": -9, "name": "负主键科目", "is_locked": 0, "question_count": 1},
        {"id": 0, "name": "", "is_locked": None, "question_count": 0},
        {"id": 95001, "name": "算法基础・α／中文", "is_locked": 1, "question_count": 2},
        {"id": 95002, "name": "数据库系统", "is_locked": 0, "question_count": 1},
    ]
    if multi != expected_multi:
        raise AssertionError(f"multi-subject projection/order drifted: {multi}")


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
            "subject_inventory_key_sources": key_source_attestation(archived),
        }
        with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-subject-inventory-data-") as data_dir:
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
                            full_fixture = reset_case_facts(db, "full")
                            tokens = {
                                actor: generate_jwt_token(
                                    user_id=user_id,
                                    openid="",
                                    session_version=7,
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
            "contract_id": "ti.phase4a.subject-inventory-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-16",
            "legacy_commit": pinned_source.LEGACY_COMMIT,
            "legacy_source_attestation": source_attestation,
            "route_status": {
                "target_internal_owner": "catalog",
                "http_owner": "operations",
                "migration_status": "pending",
                "production_cutover": False,
                "route": ROUTE,
                "controller_added": False,
                "openapi_delta": False,
                "route_delta": False,
            },
            "catalog_internal_primitive": {
                "capability": "read every subject inventory summary with assigned question count",
                "tables": ["subjects", "questions"],
                "selected_columns": ["id", "name", "is_locked", "question_count"],
                "selected_column_count": 4,
                "query_variant_count": 1,
                "bind_count": 0,
                "filters": [],
                "pagination": None,
                "ordering": "signed s.id ASC",
                "count_semantics": "COUNT(q.id) after subjects LEFT JOIN questions on subject_id",
                "http_projection_owner": "operations until auth and payload parity are migrated",
            },
            "request_effect_scope": {
                "subject_inventory_handler": (
                    "one SELECT-only subjects/questions aggregate; no catalog DML or DDL"
                ),
                "surrounding_web_session": (
                    "may SELECT users and commit users.last_active before the inventory handler"
                ),
                "claim_boundary": (
                    "per-case ledgers separate the inventory read from authentication activity; "
                    "this evidence does not claim that the entire HTTP request is write-free"
                ),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite with "
                "foreign-key enforcement disabled only to model legacy orphan data; in-memory "
                "limiter; no current working-tree legacy import or persistent data"
            ),
            "dialect_observation": (
                "the pinned raw text query on isolated SQLite serializes non-null booleans as "
                "JSON 0/1 and preserves null; PostgreSQL Boolean runtime parity is a separate gate"
            ),
            "case_isolation": (
                "every request resets empty, single, or full subjects/questions facts and actor "
                "last_active outside its SQL ledger, gets a fresh explicit Session scenario, "
                "reset limiter, deterministic remote address, pre/post 9-column subjects and "
                "15-column questions fingerprints, stable user-identity fingerprint, and a "
                "separate last_active ledger"
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
                "single_subject_id": SINGLE_SUBJECT_ID,
                "questions": QUESTIONS,
                "orphan_subject_id": ORPHAN_SUBJECT_ID,
                "full_subjects_fingerprint": full_fixture["subjects"],
                "full_questions_fingerprint": full_fixture["questions"],
                "full_association_facts": {
                    "assigned_question_count": 4,
                    "null_subject_question_count": 1,
                    "orphan_subject_question_count": 1,
                    "response_question_count_sum": 4,
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
        f"captured {document['case_count']} subject-inventory cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
