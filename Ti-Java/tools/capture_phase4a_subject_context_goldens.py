#!/usr/bin/env python3
"""Capture deterministic dual-page subject-context goldens from pinned Flask source."""

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


FIXED_REQUEST_ID = "phase4a-subject-context-golden-request"
ROUTES = {
    "questions-page": {
        "route_id": "52ad8f899d66",
        "path_template": "/admin/subjects/{subject_id}/questions",
        "route_template": "/admin/subjects/<int:subject_id>/questions",
        "legacy_handler": "admin.admin_pages.admin_questions_page",
        "template": "admin/subjects/questions.html",
    },
    "duplicate-check-page": {
        "route_id": "5548b24849ed",
        "path_template": "/admin/subjects/{subject_id}/questions/duplicate-check",
        "route_template": "/admin/subjects/<int:subject_id>/questions/duplicate-check",
        "legacy_handler": "admin.admin_pages.admin_duplicate_check_page",
        "template": "admin/subjects/duplicate_check.html",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/models/subject.py",
    "app/models/user.py",
    "app/modules/admin/__init__.py",
    "app/modules/admin/routes/pages.py",
    "app/modules/admin/templates/admin/admin_base.html",
    "app/modules/admin/templates/admin/subjects/questions.html",
    "app/modules/admin/templates/admin/subjects/duplicate_check.html",
    "app/modules/admin/templates/admin/subjects/_question_list.html",
    "app/modules/admin/templates/admin/subjects/_question_form.html",
    "app/modules/admin/templates/admin/subjects/_question_scripts.html",
    "app/modules/admin/templates/admin/subjects/_question_styles.html",
    "app/modules/admin/templates/admin/subjects/_scripts.html",
    "app/modules/admin/templates/admin/subjects/legacy.html",
)
DYNAMIC_CALLERS = (
    {
        "path": "app/modules/admin/templates/admin/subjects/duplicate_check.html",
        "line": 347,
        "text": (
            "            <a href=\"/admin/subjects/{{ subject_id }}/questions\" "
            "class=\"btn btn-secondary\">"
        ),
        "target_route_id": "52ad8f899d66",
    },
    {
        "path": "app/modules/admin/templates/admin/subjects/legacy.html",
        "line": 268,
        "text": (
            "                    <a class=\"btn-quiet\" "
            "href=\"/admin/subjects/${subject.id}/questions\">题集管理</a>"
        ),
        "target_route_id": "52ad8f899d66",
    },
    {
        "path": "app/modules/admin/templates/admin/subjects/_question_scripts.html",
        "line": 788,
        "text": (
            "        window.location.href = "
            "\u0060/admin/subjects/$" + "{subjectId}/questions/duplicate-check\u0060;"
        ),
        "target_route_id": "5548b24849ed",
    },
    {
        "path": "app/modules/admin/templates/admin/subjects/_scripts.html",
        "line": 789,
        "text": (
            "        window.location.href = "
            "\u0060/admin/subjects/$" + "{subjectId}/questions/duplicate-check\u0060;"
        ),
        "target_route_id": "5548b24849ed",
    },
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
    "ordinary": 97101,
    "subject_admin": 97102,
    "notification_admin": 97103,
    "administrator": 97104,
}
SUBJECTS = {
    "zero": 0,
    "locked": 97201,
    "empty_name": 97202,
    "unicode_html_name": 97203,
    "normal": 97204,
}
MISSING_SUBJECT_ID = 97999
ORPHAN_SUBJECT_ID = 97888
QUESTIONS = {
    "normal": 97301,
    "locked": 97302,
    "unicode": 97303,
    "null_subject": 97304,
    "orphan_subject": 97305,
}
UNICODE_ND_NORMAL_ID = "٩٧٢٠٤"
INT_MAX = "2147483647"
INT_MAX_PLUS_ONE = "2147483648"
LONG_MAX = "9223372036854775807"
LONG_MAX_PLUS_ONE = "9223372036854775808"
NONNUMERIC_SUBJECT_ID = "not-a-subject"


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    category: str
    raw_subject_id: str
    session_actor: str | None = "administrator"
    bearer_actor: str | None = None
    accept: str = "*/*"
    fail_subject_select: bool = False
    expected_status: int = 200


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    normal = str(SUBJECTS["normal"])
    for route in ROUTES:
        specs.extend((
            CaseSpec(
                f"auth-admin-session-found-{route}",
                route, "auth", normal,
            ),
            CaseSpec(
                f"auth-subject-admin-session-found-{route}",
                route, "auth", normal, session_actor="subject_admin",
            ),
            CaseSpec(
                f"auth-ordinary-session-forbidden-{route}",
                route, "auth", normal, session_actor="ordinary",
                expected_status=403,
            ),
            CaseSpec(
                f"auth-notification-admin-session-forbidden-{route}",
                route, "auth", normal, session_actor="notification_admin",
                expected_status=403,
            ),
            CaseSpec(
                f"auth-anonymous-redirect-login-{route}",
                route, "auth", normal, session_actor=None,
                expected_status=302,
            ),
            CaseSpec(
                f"auth-admin-bearer-only-redirect-login-{route}",
                route, "auth", normal, session_actor=None,
                bearer_actor="administrator", expected_status=302,
            ),
            CaseSpec(
                f"auth-ordinary-session-plus-admin-bearer-redirect-login-{route}",
                route, "auth", normal, session_actor="ordinary",
                bearer_actor="administrator", expected_status=302,
            ),
            CaseSpec(
                f"data-locked-subject-found-{route}",
                route, "data", str(SUBJECTS["locked"]),
            ),
            CaseSpec(
                f"data-empty-name-found-{route}",
                route, "data", str(SUBJECTS["empty_name"]),
            ),
            CaseSpec(
                f"data-unicode-html-name-found-{route}",
                route, "data", str(SUBJECTS["unicode_html_name"]),
            ),
            CaseSpec(
                f"data-zero-id-found-{route}",
                route, "data", str(SUBJECTS["zero"]),
            ),
            CaseSpec(
                f"data-unicode-nd-id-found-{route}",
                route, "data", UNICODE_ND_NORMAL_ID,
            ),
            CaseSpec(
                f"data-leading-zero-id-found-{route}",
                route, "data", f"000{normal}",
            ),
            CaseSpec(
                f"data-missing-positive-id-{route}",
                route, "data", str(MISSING_SUBJECT_ID),
                accept="application/json", expected_status=404,
            ),
            CaseSpec(
                f"data-int-max-missing-{route}",
                route, "data", INT_MAX, expected_status=404,
            ),
            CaseSpec(
                f"data-int-max-plus-one-missing-{route}",
                route, "data", INT_MAX_PLUS_ONE, expected_status=404,
            ),
            CaseSpec(
                f"data-long-max-missing-{route}",
                route, "data", LONG_MAX, expected_status=404,
            ),
            CaseSpec(
                f"data-long-max-plus-one-bind-failure-{route}",
                route, "data", LONG_MAX_PLUS_ONE,
                accept="application/json", expected_status=500,
            ),
            CaseSpec(
                f"data-negative-route-miss-{route}",
                route, "data", "-1", expected_status=404,
            ),
            CaseSpec(
                f"data-nonnumeric-route-miss-{route}",
                route, "data", NONNUMERIC_SUBJECT_ID, expected_status=404,
            ),
            CaseSpec(
                f"fault-injected-db-failure-html-{route}",
                route, "fault", normal, fail_subject_select=True,
                expected_status=500,
            ),
            CaseSpec(
                f"fault-injected-db-failure-json-{route}",
                route, "fault", normal, accept="application/json",
                fail_subject_select=True, expected_status=500,
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


def is_subject_context_select(statement: Any) -> bool:
    sql = re.sub(r"\s*=\s*", "=", normalized_sql(statement))
    return bool(re.fullmatch(
        r"SELECT ID, NAME FROM SUBJECTS WHERE ID=(?:\?|:SID)",
        sql,
    ))


def reads_table(statement: Any, table: str) -> bool:
    sql = normalized_sql(statement)
    return is_select_statement(statement) and bool(
        re.search(rf"\b(?:FROM|JOIN)\s+{table.upper()}\b", sql)
    )


def is_table_dml(statement: Any, table: str) -> bool:
    return bool(re.match(
        rf"^(INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+{table.upper()}\b",
        normalized_sql(statement),
    ))


def is_user_last_active_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(r"^UPDATE\s+USERS\s+SET\s+LAST_ACTIVE\s*=", sql)) and bool(
        re.search(r"\bWHERE\s+USERS\.ID\s*=", sql)
    )


@contextmanager
def sql_probe(engine: Any, *, fail_subject_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "subject_context_select_attempts": 0,
        "subjects_select_attempts": 0,
        "questions_select_attempts": 0,
        "users_select_attempts": 0,
        "subjects_dml_attempts": 0,
        "questions_dml_attempts": 0,
        "user_last_active_dml_attempts": 0,
        "unexpected_dml_attempts": 0,
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
        subject_context = is_subject_context_select(statement)
        subjects_read = reads_table(statement, "subjects")
        questions_read = reads_table(statement, "questions")
        users_read = reads_table(statement, "users")
        subjects_write = is_table_dml(statement, "subjects")
        questions_write = is_table_dml(statement, "questions")
        activity_write = is_user_last_active_dml(statement)
        unexpected_dml = dml and not activity_write
        classification = (
            "subject_context_select" if subject_context
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
        ledger["subject_context_select_attempts"] += int(subject_context)
        ledger["subjects_select_attempts"] += int(subjects_read)
        ledger["questions_select_attempts"] += int(questions_read)
        ledger["users_select_attempts"] += int(users_read)
        ledger["subjects_dml_attempts"] += int(subjects_write)
        ledger["questions_dml_attempts"] += int(questions_write)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        ledger["unexpected_dml_attempts"] += int(unexpected_dml)
        if subject_context and fail_subject_select:
            raise RuntimeError("synthetic subject-context SELECT failure")

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
        "WHERE id IN (:ordinary, :subject_admin, :notification_admin, :administrator) "
        "ORDER BY id"
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
        "WHERE id IN (:ordinary, :subject_admin, :notification_admin, :administrator) "
        "ORDER BY id"
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
    if len(selected) != 2 or {row["route_id"] for row in selected} != route_ids:
        raise AssertionError("subject-context routes are missing or duplicated in route matrix")
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


def dynamic_caller_attestation(archived: Any) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for expected in DYNAMIC_CALLERS:
        lines = (archived.root / expected["path"]).read_text(encoding="utf-8").splitlines()
        line_number = int(expected["line"])
        if line_number < 1 or line_number > len(lines):
            raise AssertionError(f"audited caller line is out of range: {expected}")
        observed = lines[line_number - 1]
        if observed != expected["text"]:
            raise AssertionError(
                f"audited caller drifted at {expected['path']}:{line_number}: {observed!r}"
            )
        evidence.append({
            **expected,
            "line_sha256": hashlib.sha256(observed.encode("utf-8")).hexdigest(),
        })
    return evidence


def fixed_subject_rows() -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    return [
        {
            "id": SUBJECTS["zero"],
            "name": "零号科目",
            "description": "zero identifier fixture",
            "is_locked": False,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["locked"],
            "name": "锁定科目",
            "description": "locked subjects remain page-readable",
            "is_locked": True,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["empty_name"],
            "name": "",
            "description": "empty name fixture",
            "is_locked": None,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["unicode_html_name"],
            "name": '<算法 & "数据">・α／中文',
            "description": "unicode and HTML escaping fixture",
            "is_locked": False,
            "plaza_board_id": None,
            "is_plaza_featured": True,
            "plaza_featured_weight": -1,
            "plaza_featured_at": fixed,
            "created_at": fixed,
        },
        {
            "id": SUBJECTS["normal"],
            "name": "普通科目・β",
            "description": "normal auth fixture",
            "is_locked": False,
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        },
    ]


def fixed_question_rows() -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)

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
            "source": "phase4a-subject-context-golden",
            "created_by": ACTORS["administrator"],
            "updated_by": ACTORS["administrator"],
            "created_at": fixed,
            "updated_at": fixed,
        }

    return [
        row(QUESTIONS["normal"], SUBJECTS["normal"], "普通科目题"),
        row(QUESTIONS["locked"], SUBJECTS["locked"], "锁定科目题"),
        row(QUESTIONS["unicode"], SUBJECTS["unicode_html_name"], "Unicode 科目题"),
        row(QUESTIONS["null_subject"], None, "空科目外键题"),
        row(QUESTIONS["orphan_subject"], ORPHAN_SUBJECT_ID, "孤儿科目外键题"),
    ]


def seed_static_fixture(db: Any, User: Any) -> None:
    from sqlalchemy import text

    foreign_keys = db.session.execute(text("PRAGMA foreign_keys = OFF"))
    foreign_keys.close()
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4a_subject_context_{actor}",
            email=f"phase4a_subject_context_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=actor == "administrator",
            is_subject_admin=actor == "subject_admin",
            is_notification_admin=actor == "notification_admin",
            is_locked=False,
            session_version=7,
            created_at=fixed,
            last_active=None,
        ))
    db.session.commit()


def reset_case_facts(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    db.session.execute(text("DELETE FROM questions"))
    db.session.execute(text("DELETE FROM subjects"))
    db.session.execute(text(
        "INSERT INTO subjects "
        f"({', '.join(SUBJECT_COLUMNS)}) VALUES "
        f"({', '.join(':' + column for column in SUBJECT_COLUMNS)})"
    ), fixed_subject_rows())
    db.session.execute(text(
        "INSERT INTO questions "
        f"({', '.join(QUESTION_COLUMNS)}) VALUES "
        f"({', '.join(':' + column for column in QUESTION_COLUMNS)})"
    ), fixed_question_rows())
    db.session.execute(text(
        "UPDATE users SET last_active = NULL "
        "WHERE id IN (:ordinary, :subject_admin, :notification_admin, :administrator)"
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
            "username": f"phase4a_subject_context_{actor}",
            "session_version": 7,
            "is_admin": actor == "administrator",
            "is_subject_admin": actor == "subject_admin",
            "is_notification_admin": actor == "notification_admin",
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
        "body": normalized_value(payload) if payload is not None else raw.decode(
            "utf-8", errors="replace"
        ),
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
        expected = reset_case_facts(db)
        subjects_before = subject_fingerprint(db)
        questions_before = question_fingerprint(db)
        users_identity_before = user_identity_fingerprint(db)
        raw_activity_before, activity_before = user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    request_path = route["path_template"].format(subject_id=spec.raw_subject_id)
    with sql_probe(engine, fail_subject_select=spec.fail_subject_select) as sql:
        response = client.get(
            request_path,
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
    converter_match = spec.raw_subject_id.isdecimal()
    try:
        python_int_value: int | None = int(spec.raw_subject_id)
    except ValueError:
        python_int_value = None
    return {
        "case_id": spec.case_id,
        "category": spec.category,
        "route_key": spec.route,
        "route_id": route["route_id"],
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or "none",
        "credential_mode": credential_mode(spec),
        "request": {
            "method": "GET",
            "path": request_path,
            "route_template": route["route_template"],
            "path_parameter": {
                "name": "subject_id",
                "raw_text": spec.raw_subject_id,
                "python_int_value": python_int_value,
                "flask_int_converter_match": converter_match,
                "handler_subject_id": python_int_value if converter_match else None,
            },
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
    if len(CASE_SPECS) != 44 or len(cases) != 44 or len(by_id) != 44:
        raise AssertionError("subject-context case set drifted, duplicated, or is not exactly 44")

    no_subject_select_suffixes = {
        "auth-ordinary-session-forbidden",
        "auth-notification-admin-session-forbidden",
        "auth-anonymous-redirect-login",
        "auth-admin-bearer-only-redirect-login",
        "auth-ordinary-session-plus-admin-bearer-redirect-login",
        "data-negative-route-miss",
        "data-nonnumeric-route-miss",
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
        if not effects["subjects_match_case_fixture"] or not effects["questions_match_case_fixture"]:
            raise AssertionError(f"{spec.case_id} did not start from its isolated fixture")
        if not effects["subjects_unchanged"] or not effects["questions_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed catalog facts")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed a user identity/role fact")
        if effects["subjects_before"]["column_count"] != 9:
            raise AssertionError(f"{spec.case_id} lost the 9-column subjects fingerprint")
        if effects["questions_before"]["column_count"] != 15:
            raise AssertionError(f"{spec.case_id} lost the 15-column questions fingerprint")
        if sql["questions_select_attempts"] != 0:
            raise AssertionError(f"{spec.case_id} unexpectedly queried questions")
        if (
            sql["subjects_dml_attempts"]
            or sql["questions_dml_attempts"]
            or sql["ddl_attempts"]
            or sql["unexpected_dml_attempts"]
        ):
            raise AssertionError(f"{spec.case_id} attempted forbidden DML or request DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")

        prefix = spec.case_id.removesuffix("-" + spec.route)
        expected_subject_selects = 0 if prefix in no_subject_select_suffixes else 1
        if sql["subject_context_select_attempts"] != expected_subject_selects:
            raise AssertionError(
                f"{spec.case_id} subject SELECT attempts drifted: "
                f"expected={expected_subject_selects} "
                f"observed={sql['subject_context_select_attempts']}"
            )
        if sql["subjects_select_attempts"] != expected_subject_selects:
            raise AssertionError(f"{spec.case_id} gained a second subjects query")
        subject_statements = [
            statement for statement in sql["statements"]
            if statement["classification"] == "subject_context_select"
        ]
        if len(subject_statements) != expected_subject_selects:
            raise AssertionError(f"{spec.case_id} subject SELECT classification drifted")
        for statement in subject_statements:
            if statement["parameters"] != [int(spec.raw_subject_id)]:
                raise AssertionError(f"{spec.case_id} subject bind drifted: {statement}")
            if statement["executemany"]:
                raise AssertionError(f"{spec.case_id} subject lookup became executemany")

        expected_activity = (
            [ACTORS[spec.session_actor]]
            if spec.session_actor is not None and spec.bearer_actor is None
            else []
        )
        if effects["user_last_active_changed_user_ids"] != expected_activity:
            raise AssertionError(
                f"{spec.case_id} last_active drifted: expected={expected_activity} "
                f"observed={effects['user_last_active_changed_user_ids']}"
            )
        if sql["user_last_active_dml_attempts"] != len(expected_activity):
            raise AssertionError(f"{spec.case_id} last_active SQL ledger drifted")

    for route in ROUTES:
        ordinary = by_id[f"auth-ordinary-session-forbidden-{route}"]
        notification = by_id[f"auth-notification-admin-session-forbidden-{route}"]
        for case in (ordinary, notification):
            if case["response"]["body"] != {
                "status": "forbidden",
                "message": "需要管理员或科目管理员权限",
                "request_id": FIXED_REQUEST_ID,
                "status_code": 403,
            }:
                raise AssertionError(f"{case['case_id']} forbidden body drifted")

        for auth_case in (
            "auth-anonymous-redirect-login",
            "auth-admin-bearer-only-redirect-login",
            "auth-ordinary-session-plus-admin-bearer-redirect-login",
        ):
            response = by_id[f"{auth_case}-{route}"]["response"]
            if response["headers"].get("Location") != ["/login"]:
                raise AssertionError(f"{auth_case}-{route} redirect drifted")

        matched_missing = (
            by_id[f"data-missing-positive-id-{route}"]["response"],
            by_id[f"data-int-max-missing-{route}"]["response"],
            by_id[f"data-int-max-plus-one-missing-{route}"]["response"],
            by_id[f"data-long-max-missing-{route}"]["response"],
        )
        route_misses = (
            by_id[f"data-negative-route-miss-{route}"]["response"],
            by_id[f"data-nonnumeric-route-miss-{route}"]["response"],
        )
        overflow = by_id[f"data-long-max-plus-one-bind-failure-{route}"]["response"]
        for response in matched_missing:
            if (response["status"], response["body_kind"], response["body"]) != (
                404, "text", "科目不存在"
            ):
                raise AssertionError(f"direct missing-subject 404 drifted for {route}")
        for route_miss in route_misses:
            if route_miss["status"] != 404 or route_miss["body_kind"] != "text":
                raise AssertionError(f"route-level 404 drifted for {route}")
            if "404 - 页面未找到" not in route_miss["body"]:
                raise AssertionError(f"route-level 404 lost generic HTML for {route}")
        if (
            overflow["status"],
            overflow["body_kind"],
            overflow["body"].get("message"),
        ) != (500, "json", "An unexpected server error occurred."):
            raise AssertionError(f"signed-long overflow failure drifted for {route}")


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
            "subject_context_key_sources": key_source_attestation(archived),
            "audited_template_callers": dynamic_caller_attestation(archived),
        }
        with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-subject-context-data-") as data_dir:
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
                            full_fixture = reset_case_facts(db)
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
            "contract_id": "ti.phase4a.subject-context-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-17",
            "legacy_commit": pinned_source.LEGACY_COMMIT,
            "legacy_source_attestation": source_attestation,
            "route_status": {
                "target_internal_owner": "catalog",
                "http_owner": "operations",
                "migration_status": "pending",
                "production_cutover": False,
                "routes": list(ROUTES.values()),
                "controller_added": False,
                "openapi_delta": False,
                "route_delta": False,
            },
            "catalog_internal_primitive": {
                "capability": "find exact subject context by signed identifier",
                "table": "subjects",
                "selected_columns": ["id", "name"],
                "selected_column_count": 2,
                "query_variant_count": 1,
                "bind_count": 1,
                "filters": ["subjects.id = :sid"],
                "questions_query_count": 0,
                "pagination": None,
                "http_projection_owner": "operations until page auth and rendering parity migrate",
            },
            "request_effect_scope": {
                "subject_context_handler": (
                    "one typed subject SELECT by id when routing/auth reaches the handler; "
                    "zero questions SELECTs and no catalog DML or DDL"
                ),
                "surrounding_web_session": (
                    "Session-only requests may SELECT users and commit users.last_active before "
                    "authorization, route-miss handling, subject lookup, or rendering"
                ),
                "claim_boundary": (
                    "per-case ledgers separate the catalog read from authentication activity; "
                    "this evidence does not claim that the entire HTTP request is write-free"
                ),
            },
            "not_found_semantics": {
                "matched_route_missing_subject": (
                    "handler returns exact text body 科目不存在 with status 404, even when "
                    "Accept is application/json"
                ),
                "negative_route_miss": (
                    "Flask int converter rejects the path before the handler and the generic "
                    "HTML 404 handler responds"
                ),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite with "
                "foreign-key enforcement disabled only to model legacy orphan data; in-memory "
                "limiter; no current working-tree legacy import or persistent data"
            ),
            "case_isolation": (
                "every request resets fixed subjects/questions facts and actor last_active "
                "outside its SQL ledger, gets a fresh explicit credential scenario, reset "
                "limiter, deterministic remote address, pre/post 9-column subjects and "
                "15-column questions fingerprints, stable user-identity fingerprint, and a "
                "separate last_active ledger"
            ),
            "response_capture": (
                "full response body text and parsed body, body length/hash, and every test-client "
                "response header; session cookies are redacted and wall-clock activity values "
                "use explicit deterministic placeholders"
            ),
            "redaction": (
                "synthetic identities only; JWT, password hash, session-cookie values, and "
                "database-current last_active timestamps omitted; fixed request ID"
            ),
            "fixture": {
                "actors": ACTORS,
                "subjects": SUBJECTS,
                "missing_subject_id": MISSING_SUBJECT_ID,
                "orphan_subject_id": ORPHAN_SUBJECT_ID,
                "questions": QUESTIONS,
                "unicode_nd_normal_id": UNICODE_ND_NORMAL_ID,
                "signed_int_max": INT_MAX,
                "signed_int_max_plus_one": INT_MAX_PLUS_ONE,
                "signed_long_max": LONG_MAX,
                "signed_long_max_plus_one": LONG_MAX_PLUS_ONE,
                "nonnumeric_subject_id": NONNUMERIC_SUBJECT_ID,
                "full_subjects_fingerprint": full_fixture["subjects"],
                "full_questions_fingerprint": full_fixture["questions"],
            },
            "case_matrix": {
                "per_route": 22,
                "routes": 2,
                "categories_per_route": {
                    "auth": 7,
                    "data": 13,
                    "fault": 2,
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
        f"captured {document['case_count']} subject-context cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
