#!/usr/bin/env python3
"""Capture deterministic dual-route admin question-export goldens."""

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


FIXED_REQUEST_ID = "phase4a-question-export-golden-request"
ROUTES = {
    "modern": {
        "route_id": "4a33d8e15da5",
        "path": "/admin/api/questions/export",
        "route_template": "/admin/api/questions/export",
        "legacy_handler": "admin.admin_api.export_questions_api",
    },
    "legacy": {
        "route_id": "712a47789f1d",
        "path": "/admin/questions/export",
        "route_template": "/admin/questions/export",
        "legacy_handler": "admin.admin_api_legacy.export_questions_api",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/core/utils/json_helpers.py",
    "app/models/subject.py",
    "app/models/user.py",
    "app/modules/admin/__init__.py",
    "app/modules/admin/routes/api.py",
    "app/modules/admin/routes/api_bp.py",
    "app/modules/admin/routes/api_components/questions_io.py",
    "app/modules/admin/routes/api_legacy.py",
    "app/modules/admin/templates/admin/subjects/questions.html",
    "app/modules/admin/templates/admin/subjects/_question_scripts.html",
    "app/modules/admin/templates/admin/subjects/_scripts.html",
    "app/modules/admin/templates/admin/subjects/_styles.html",
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
    "ordinary": 98101,
    "subject_admin": 98102,
    "administrator": 98103,
    "notification_admin": 98104,
}
SUBJECTS = {
    "negative": -1,
    "zero": 0,
    "primary": 98201,
    "empty_name": 98202,
    "other": 98203,
}
ORPHAN_SUBJECT_ID = 98999
UNICODE_ND_PRIMARY = "٩٨٢٠١"
INT4_OUT_OF_RANGE = "2147483648"
QUESTIONS = {
    "negative_id": -7,
    "zero_id": 0,
    "negative_subject": 98301,
    "db_null": 98302,
    "json_null": 98303,
    "empty_raw": 98304,
    "malformed": 98305,
    "array": 98306,
    "object": 98307,
    "scalar": 98308,
    "empty_subject_name": 98309,
    "orphan_subject": 98310,
    "null_subject": 98311,
    "other_subject": 98312,
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    query: tuple[tuple[str, str], ...] = ()
    session_actor: str | None = "administrator"
    bearer_actor: str | None = None
    accept: str = "*/*"
    empty_questions: bool = False
    fail_export_select: bool = False
    expected_status: int = 200


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        specs.extend((
            CaseSpec(f"auth-administrator-session-{route}", route),
            CaseSpec(
                f"auth-subject-admin-session-{route}", route,
                session_actor="subject_admin",
            ),
            CaseSpec(
                f"auth-ordinary-session-forbidden-{route}", route,
                session_actor="ordinary", expected_status=403,
            ),
            CaseSpec(
                f"auth-notification-admin-session-forbidden-{route}", route,
                session_actor="notification_admin", expected_status=403,
            ),
            CaseSpec(
                f"auth-anonymous-redirect-login-{route}", route,
                session_actor=None, expected_status=302,
            ),
            CaseSpec(
                f"auth-administrator-bearer-only-redirect-login-{route}", route,
                session_actor=None, bearer_actor="administrator", expected_status=302,
            ),
            CaseSpec(
                f"auth-ordinary-session-plus-administrator-bearer-redirect-login-{route}",
                route,
                session_actor="ordinary", bearer_actor="administrator",
                expected_status=302,
            ),
            CaseSpec(f"data-empty-table-{route}", route, empty_questions=True),
            CaseSpec(f"subject-missing-default-{route}", route),
            CaseSpec(
                f"subject-empty-{route}", route,
                query=(("subject_id", ""),),
            ),
            CaseSpec(
                f"subject-blank-{route}", route,
                query=(("subject_id", " "),),
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
                f"subject-exact-{route}", route,
                query=(("subject_id", str(SUBJECTS["primary"])),),
            ),
            CaseSpec(
                f"subject-exact-type-ignored-{route}", route,
                query=(
                    ("subject_id", str(SUBJECTS["primary"])),
                    ("type", "definitely-not-matching"),
                ),
            ),
            CaseSpec(
                f"subject-no-match-{route}", route,
                query=(("subject_id", "999999"),),
            ),
            CaseSpec(
                f"subject-repeated-first-value-{route}", route,
                query=(
                    ("subject_id", str(SUBJECTS["primary"])),
                    ("subject_id", str(SUBJECTS["other"])),
                ),
            ),
            CaseSpec(
                f"subject-invalid-{route}", route,
                query=(("subject_id", "not-an-integer"),),
            ),
            CaseSpec(
                f"subject-unicode-nd-{route}", route,
                query=(("subject_id", UNICODE_ND_PRIMARY),),
            ),
            CaseSpec(
                f"subject-int4-out-of-range-{route}", route,
                query=(("subject_id", INT4_OUT_OF_RANGE),),
            ),
            CaseSpec(
                f"fault-html-{route}", route,
                fail_export_select=True, expected_status=500,
            ),
            CaseSpec(
                f"fault-json-{route}", route,
                accept="application/json", fail_export_select=True,
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
    return normalized_sql(statement).startswith(
        ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ")
    )


def is_ddl_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith((
        "CREATE ", "ALTER ", "DROP ", "TRUNCATE ", "COMMENT ",
        "GRANT ", "REVOKE ", "VACUUM ", "ANALYZE ", "PRAGMA ",
    ))


def is_export_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return all(fragment in sql for fragment in (
        "SELECT Q.ID, Q.SUBJECT_ID, S.NAME AS SUBJECT_NAME,",
        "Q.OPTIONS, Q.ANSWER, Q.ANALYSIS",
        "Q.DIFFICULTY, Q.TAGS",
        "FROM QUESTIONS Q LEFT JOIN SUBJECTS S ON Q.SUBJECT_ID = S.ID",
        "WHERE 1=1",
        "ORDER BY Q.ID",
    ))


def is_fact_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return bool(re.match(
        r"^(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+"
        r"(?:QUESTIONS|SUBJECTS)\b",
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
def sql_probe(engine: Any, *, fail_export_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "export_select_attempts": 0,
        "fact_dml_attempts": 0,
        "users_select_attempts": 0,
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
        export = is_export_select(statement)
        fact_write = is_fact_dml(statement)
        users_read = is_users_select(statement)
        activity_write = is_user_last_active_dml(statement)
        classification = (
            "question_export_select" if export
            else "user_last_active_dml" if activity_write
            else "catalog_fact_dml" if fact_write
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
        ledger["export_select_attempts"] += int(export)
        ledger["fact_dml_attempts"] += int(fact_write)
        ledger["users_select_attempts"] += int(users_read)
        ledger["user_last_active_dml_attempts"] += int(activity_write)
        if export and fail_export_select:
            raise RuntimeError("synthetic question-export SELECT failure")

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


def table_fingerprint(
    db: Any,
    *,
    table: str,
    columns: tuple[str, ...],
) -> dict[str, Any]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
    )).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "table": table,
        "columns": list(columns),
        "column_count": len(columns),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def user_identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        f"SELECT {', '.join(USER_IDENTITY_COLUMNS)} FROM users "
        "WHERE id IN (:ordinary, :subject_admin, :administrator, "
        ":notification_admin) ORDER BY id"
    ), ACTORS).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "table": "users",
        "columns": list(USER_IDENTITY_COLUMNS),
        "column_count": len(USER_IDENTITY_COLUMNS),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def facts_fingerprint(db: Any) -> dict[str, Any]:
    facts = {
        "questions": table_fingerprint(
            db, table="questions", columns=QUESTION_COLUMNS,
        ),
        "subjects": table_fingerprint(
            db, table="subjects", columns=SUBJECT_COLUMNS,
        ),
        "user_identity": user_identity_fingerprint(db),
    }
    return {**facts, "combined_sha256": sha256_json(facts)}


def user_activity_snapshot(db: Any) -> tuple[dict[int, Any], list[dict[str, Any]]]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        "SELECT id, last_active FROM users "
        "WHERE id IN (:ordinary, :subject_admin, :administrator, "
        ":notification_admin) ORDER BY id"
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
        raise AssertionError("question-export routes are missing from the route matrix")
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


def template_caller_attestation(archived: Any) -> dict[str, Any]:
    templates_root = archived.root / "app/modules/admin/templates"
    route_occurrences: dict[str, list[dict[str, Any]]] = {
        route: [] for route in ROUTES
    }
    include_occurrences: list[dict[str, Any]] = []
    route_patterns = {
        route: re.compile(re.escape(details["path"]) + r"(?=[?'\"`])")
        for route, details in ROUTES.items()
    }
    include_pattern = re.compile(
        r"\{%\s*include\s+[\"']admin/subjects/"
        r"(_question_scripts|_scripts|_styles)\.html[\"']\s*%\}"
    )
    for path in sorted(templates_root.rglob("*.html")):
        relative = path.relative_to(archived.root).as_posix()
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1,
        ):
            stripped = line.strip()
            for route, pattern in route_patterns.items():
                if pattern.search(line):
                    route_occurrences[route].append({
                        "source": relative,
                        "line": line_number,
                        "line_sha256": hashlib.sha256(
                            stripped.encode("utf-8")
                        ).hexdigest(),
                    })
            match = include_pattern.search(line)
            if match:
                include_occurrences.append({
                    "source": relative,
                    "line": line_number,
                    "included": (
                        "app/modules/admin/templates/admin/subjects/"
                        f"{match.group(1)}.html"
                    ),
                    "line_sha256": hashlib.sha256(
                        stripped.encode("utf-8")
                    ).hexdigest(),
                })

    active_template = (
        "app/modules/admin/templates/admin/subjects/_question_scripts.html"
    )
    dormant_modern_template = (
        "app/modules/admin/templates/admin/subjects/_scripts.html"
    )
    active_include = [
        item for item in include_occurrences
        if item["source"].endswith("/questions.html")
        and item["included"] == active_template
    ]
    modern_inbound = [
        item for item in include_occurrences
        if item["included"] == dormant_modern_template
    ]
    if len(active_include) != 1:
        raise AssertionError("active question-export template include chain drifted")
    if modern_inbound:
        raise AssertionError("modern _scripts.html unexpectedly became reachable")
    return {
        "scan_root": "app/modules/admin/templates",
        "direct_route_occurrences": route_occurrences,
        "include_occurrences": include_occurrences,
        "reachability": {
            "active_legacy_chain": {
                "page": "app/modules/admin/templates/admin/subjects/questions.html",
                "include": active_include[0],
                "direct_caller": active_template,
                "target_route_id": ROUTES["legacy"]["route_id"],
                "status": "active",
            },
            "modern_template": {
                "direct_caller": dormant_modern_template,
                "inbound_include_count": 0,
                "target_route_id": ROUTES["modern"]["route_id"],
                "status": "dormant_in_frozen_archive",
            },
            "legacy_compatibility_fragment": {
                "source": "app/modules/admin/templates/admin/subjects/_styles.html",
                "inbound_include_count": sum(
                    item["included"].endswith("/_styles.html")
                    for item in include_occurrences
                ),
                "status": "dormant_in_frozen_archive",
            },
        },
        "attestation_sha256": sha256_json({
            "direct_route_occurrences": route_occurrences,
            "include_occurrences": include_occurrences,
        }),
    }


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def subject_fixture_rows() -> list[dict[str, Any]]:
    fixed = "2026-07-17 08:00:00"
    names = {
        "negative": "负数科目",
        "zero": "零号科目",
        "primary": "导出证据・α／中文",
        "empty_name": "",
        "other": "其他科目",
    }
    return [
        {
            "id": subject_id,
            "name": names[key],
            "description": "public synthetic export fixture",
            "is_locked": key == "other",
            "plaza_board_id": None,
            "is_plaza_featured": False,
            "plaza_featured_weight": 0,
            "plaza_featured_at": None,
            "created_at": fixed,
        }
        for key, subject_id in SUBJECTS.items()
    ]


def question_fixture_rows() -> list[dict[str, Any]]:
    fixed = "2026-07-17 08:00:00"
    base = {
        "subject_id": SUBJECTS["primary"],
        "type": "essay",
        "content": "固定导出题干",
        "options": "[]",
        "answer": "[]",
        "analysis": "固定导出解析",
        "tags": compact_json(["phase4a", "export"]),
        "difficulty": 2,
        "image_path": None,
        "source": "phase4a-question-export-golden",
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
        row(
            QUESTIONS["negative_id"],
            content="负数题目主键・Unicode",
        ),
        row(
            QUESTIONS["zero_id"],
            subject_id=SUBJECTS["zero"], type="boolean",
            content="零号题目与零难度", difficulty=0,
        ),
        row(
            QUESTIONS["negative_subject"],
            subject_id=SUBJECTS["negative"], type="single_choice",
            content="负数科目题", difficulty=-2,
        ),
        row(
            QUESTIONS["db_null"],
            type="", content="", options=None, answer=None,
            analysis=None, tags=None, difficulty=None,
        ),
        row(
            QUESTIONS["json_null"],
            content="JSON null 字面量", options="null", answer="null",
            tags="null",
        ),
        row(
            QUESTIONS["empty_raw"],
            content="空白 JSON 文本", options="", answer="   ", tags="\t",
        ),
        row(
            QUESTIONS["malformed"],
            content="畸形 JSON 文本", options="[broken-options",
            answer="{broken-answer", tags="not-json-tags",
        ),
        row(
            QUESTIONS["array"],
            type="multi_choice", content="数组 JSON",
            options=compact_json(["甲", {"key": "B"}]),
            answer=compact_json([0, True, None]),
            tags=compact_json(["数学", ""]),
        ),
        row(
            QUESTIONS["object"],
            content="对象 JSON",
            options=compact_json({"A": "甲"}),
            answer=compact_json({"value": "A"}),
            tags=compact_json({"topic": "代数"}),
        ),
        row(
            QUESTIONS["scalar"],
            content="标量 JSON",
            options=compact_json("单值"), answer="7", tags="false",
        ),
        row(
            QUESTIONS["empty_subject_name"],
            subject_id=SUBJECTS["empty_name"], content="空科目名题",
        ),
        row(
            QUESTIONS["orphan_subject"],
            subject_id=ORPHAN_SUBJECT_ID, content="孤儿科目题",
        ),
        row(
            QUESTIONS["null_subject"],
            subject_id=None, content="空科目外键题",
        ),
        row(
            QUESTIONS["other_subject"],
            subject_id=SUBJECTS["other"], content="其他科目题",
        ),
    ]


def seed_static_actors(db: Any, User: Any) -> None:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4a_export_{actor}",
            email=f"phase4a_export_{actor}@test.example.com",
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


def reset_case_facts(db: Any, *, empty_questions: bool) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    db.session.execute(text("DELETE FROM questions"))
    db.session.execute(text("DELETE FROM subjects"))
    db.session.execute(text(
        "INSERT INTO subjects "
        f"({', '.join(SUBJECT_COLUMNS)}) VALUES "
        f"({', '.join(':' + column for column in SUBJECT_COLUMNS)})"
    ), subject_fixture_rows())
    if not empty_questions:
        db.session.execute(text(
            "INSERT INTO questions "
            f"({', '.join(QUESTION_COLUMNS)}) VALUES "
            f"({', '.join(':' + column for column in QUESTION_COLUMNS)})"
        ), question_fixture_rows())
    db.session.execute(text(
        "UPDATE users SET last_active = NULL "
        "WHERE id IN (:ordinary, :subject_admin, :administrator, "
        ":notification_admin)"
    ), ACTORS)
    db.session.commit()
    return facts_fingerprint(db)


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4a_export_{actor}",
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
        expected_facts = reset_case_facts(
            db, empty_questions=spec.empty_questions,
        )
        before = facts_fingerprint(db)
        raw_activity_before, activity_before = user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    with sql_probe(engine, fail_export_select=spec.fail_export_select) as sql:
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
        after = facts_fingerprint(db)
        raw_activity_after, activity_after = user_activity_snapshot(db)
        db.session.remove()
    changed_activity_ids = sorted(
        user_id
        for user_id in raw_activity_before
        if raw_activity_before[user_id] != raw_activity_after[user_id]
    )
    query_items = [{"name": name, "value": value} for name, value in spec.query]
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
            "query_string": urlencode(list(spec.query)),
            "headers": recorded_request_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "response": normalized_response(response),
        "observed_get_effects": {
            "engine": "SQLite from archived Flask testing configuration",
            "sql": sql,
            "facts_before": before,
            "facts_after": after,
            "facts_match_case_fixture": before == expected_facts,
            "facts_unchanged": before == after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def response_questions(case: dict[str, Any]) -> list[dict[str, Any]]:
    body = case["response"]["body"]
    if not isinstance(body, dict):
        return []
    questions = body.get("questions")
    return questions if isinstance(questions, list) else []


def response_ids(case: dict[str, Any]) -> list[int]:
    return [int(item["id"]) for item in response_questions(case)]


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(CASE_SPECS) != 44 or len(by_id) != 44 or len(cases) != 44:
        raise AssertionError(
            "question-export case set drifted, duplicated, or is not exactly 44"
        )
    all_ids = sorted(QUESTIONS.values())
    primary_ids = sorted((
        QUESTIONS["negative_id"],
        QUESTIONS["db_null"],
        QUESTIONS["json_null"],
        QUESTIONS["empty_raw"],
        QUESTIONS["malformed"],
        QUESTIONS["array"],
        QUESTIONS["object"],
        QUESTIONS["scalar"],
    ))

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
        if not effects["facts_match_case_fixture"]:
            raise AssertionError(f"{spec.case_id} did not start from isolated facts")
        if not effects["facts_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed catalog or identity facts")
        if effects["facts_before"]["questions"]["column_count"] != 15:
            raise AssertionError(f"{spec.case_id} lost the question fingerprint")
        if effects["facts_before"]["subjects"]["column_count"] != 9:
            raise AssertionError(f"{spec.case_id} lost the subject fingerprint")
        if sql["fact_dml_attempts"] != 0 or sql["ddl_attempts"] != 0:
            raise AssertionError(f"{spec.case_id} attempted catalog DML or DDL")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")
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
        for actor in ("administrator", "subject-admin"):
            case = by_id[f"auth-{actor}-session-{route}"]
            if case["response"]["status"] != 200:
                raise AssertionError(f"{case['case_id']} auth success drifted")
            if case["observed_get_effects"]["sql"]["export_select_attempts"] != 1:
                raise AssertionError(f"{case['case_id']} did not execute one export SELECT")
        for prefix in (
            "auth-ordinary-session-forbidden",
            "auth-notification-admin-session-forbidden",
            "auth-anonymous-redirect-login",
            "auth-administrator-bearer-only-redirect-login",
            "auth-ordinary-session-plus-administrator-bearer-redirect-login",
        ):
            case = by_id[f"{prefix}-{route}"]
            if case["observed_get_effects"]["sql"]["export_select_attempts"] != 0:
                raise AssertionError(f"{case['case_id']} crossed auth-before-query")

        empty = by_id[f"data-empty-table-{route}"]
        if response_questions(empty) != []:
            raise AssertionError(f"{empty['case_id']} empty export drifted")
        if empty["response"]["body"]["count"] != 0:
            raise AssertionError(f"{empty['case_id']} empty count drifted")
        default = by_id[f"subject-missing-default-{route}"]
        if response_ids(default) != all_ids:
            raise AssertionError(f"{default['case_id']} lost strict id ASC ordering")
        default_items = {
            item["id"]: item for item in response_questions(default)
        }
        locked_subject_item = default_items.get(QUESTIONS["other_subject"])
        if locked_subject_item is None:
            raise AssertionError(
                f"{default['case_id']} excluded the locked-subject question"
            )
        if (
            locked_subject_item["subject_id"] != SUBJECTS["other"]
            or locked_subject_item["subject_name"] != "其他科目"
        ):
            raise AssertionError(
                f"{default['case_id']} changed the locked-subject projection"
            )

        expected_filters = {
            "empty": all_ids,
            "blank": [],
            "zero": [QUESTIONS["zero_id"]],
            "negative": [QUESTIONS["negative_subject"]],
            "exact": primary_ids,
            "exact-type-ignored": primary_ids,
            "no-match": [],
            "repeated-first-value": primary_ids,
            "invalid": [],
            "unicode-nd": [],
            "int4-out-of-range": [],
        }
        for scenario, expected in expected_filters.items():
            case = by_id[f"subject-{scenario}-{route}"]
            if response_ids(case) != expected:
                raise AssertionError(
                    f"{case['case_id']} SQLite raw filter drifted: "
                    f"expected={expected} observed={response_ids(case)}"
                )
        type_ignored = by_id[f"subject-exact-type-ignored-{route}"]
        expected_meta = {
            "scope": "question_center",
            "subject_id": str(SUBJECTS["primary"]),
        }
        if type_ignored["response"]["body"]["meta"] != expected_meta:
            raise AssertionError(
                f"{type_ignored['case_id']} exposed non-legacy filter metadata"
            )

        modern = by_id[f"subject-missing-default-modern"]["response"]["body"]
        legacy = by_id[f"subject-missing-default-legacy"]["response"]["body"]
        if route == "modern":
            body = default["response"]["body"]
            expected_data = {
                "meta": body["meta"],
                "count": body["count"],
                "questions": body["questions"],
            }
            if body.get("status") != "success" or body.get("message") != "":
                raise AssertionError("modern success status/message envelope drifted")
            if body.get("request_id") != FIXED_REQUEST_ID:
                raise AssertionError("modern request_id envelope drifted")
            if body.get("data") != expected_data:
                raise AssertionError("modern after_request data mirror drifted")
        else:
            body = default["response"]["body"]
            if set(body) != {"meta", "count", "questions", "request_id"}:
                raise AssertionError("legacy envelope unexpectedly gained modern fields")
            if body["request_id"] != FIXED_REQUEST_ID:
                raise AssertionError("legacy request_id envelope drifted")
        if modern["questions"] != modern["data"]["questions"]:
            raise AssertionError("modern top-level/data question mirror drifted")
        if modern["meta"] != legacy["meta"]:
            raise AssertionError("dual-route success meta drifted")
        if modern["questions"] != legacy["questions"]:
            raise AssertionError("dual-route question projection drifted")

        items = {item["id"]: item for item in response_questions(default)}
        nulls = items[QUESTIONS["db_null"]]
        if (nulls["type"], nulls["content"], nulls["analysis"]) != ("", "", ""):
            raise AssertionError("text default projection drifted")
        if nulls["difficulty"] != 1:
            raise AssertionError("null difficulty default drifted")
        if items[QUESTIONS["zero_id"]]["difficulty"] != 1:
            raise AssertionError("zero difficulty default drifted")
        if items[QUESTIONS["negative_subject"]]["difficulty"] != -2:
            raise AssertionError("negative difficulty preservation drifted")
        for field in ("options", "answer", "tags"):
            if nulls[field] != []:
                raise AssertionError(f"database-null {field} fallback drifted")
            if items[QUESTIONS["json_null"]][field] is not None:
                raise AssertionError(f"JSON-null {field} projection drifted")
            if items[QUESTIONS["empty_raw"]][field] != []:
                raise AssertionError(f"empty {field} fallback drifted")
            if items[QUESTIONS["malformed"]][field] != []:
                raise AssertionError(f"malformed {field} fallback drifted")
        expected_array = {
            "options": ["甲", {"key": "B"}],
            "answer": [0, True, None],
            "tags": ["数学", ""],
        }
        expected_object = {
            "options": {"A": "甲"},
            "answer": {"value": "A"},
            "tags": {"topic": "代数"},
        }
        expected_scalar = {
            "options": "单值",
            "answer": 7,
            "tags": False,
        }
        for field in ("options", "answer", "tags"):
            if items[QUESTIONS["array"]][field] != expected_array[field]:
                raise AssertionError(f"array {field} projection drifted")
            if items[QUESTIONS["object"]][field] != expected_object[field]:
                raise AssertionError(f"object {field} projection drifted")
            if items[QUESTIONS["scalar"]][field] != expected_scalar[field]:
                raise AssertionError(f"scalar {field} projection drifted")
        for question_key in (
            "empty_subject_name", "orphan_subject", "null_subject",
        ):
            if items[QUESTIONS[question_key]]["subject_name"] != "默认科目":
                raise AssertionError(f"{question_key} subject default drifted")
        if items[QUESTIONS["negative_id"]]["subject_name"] != "导出证据・α／中文":
            raise AssertionError("exact Unicode subject name drifted")

        for mode in ("html", "json"):
            failure = by_id[f"fault-{mode}-{route}"]
            if failure["observed_get_effects"]["sql"]["export_select_attempts"] != 1:
                raise AssertionError(f"{failure['case_id']} did not attempt export SELECT")
            expected_kind = "text" if mode == "html" else "json"
            if failure["response"]["body_kind"] != expected_kind:
                raise AssertionError(f"{failure['case_id']} failure negotiation drifted")


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
            "question_export_key_sources": key_source_attestation(archived),
            "template_callers": template_caller_attestation(archived),
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4a-question-export-data-",
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
            "contract_id": "ti.phase4a.question-export-read-goldens",
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
            },
            "catalog_fact_shape": {
                "capability": "raw question export snapshot input",
                "tables": ["questions", "subjects"],
                "selected_columns": [
                    "q.id", "q.subject_id", "s.name AS subject_name",
                    "q.type", "q.content", "q.options", "q.answer",
                    "q.analysis", "q.difficulty", "q.tags",
                ],
                "ordering": "q.id ASC",
                "subject_filter": (
                    "request.args.get first raw string; predicate and meta field only "
                    "when Python-truthy"
                ),
                "http_projection_owner": (
                    "operations owns authentication, raw parameter interpretation, "
                    "defaults, safe_load, envelopes and safe errors"
                ),
            },
            "engine_scope": {
                "captured": "archived Flask testing configuration on temporary SQLite",
                "portable_facts": (
                    "handler source, first-value/truthiness parsing, SQL text shape, "
                    "ordering, projection and envelopes"
                ),
                "engine_specific_edges": [
                    "blank subject_id",
                    "invalid subject_id",
                    "Unicode Nd subject_id",
                    "subject_id outside PostgreSQL integer range",
                ],
                "non_claim": (
                    "SQLite empty-result behavior for raw-text integer comparisons is not "
                    "claimed as PostgreSQL behavior; Phase 4H requires PostgreSQL HTTP "
                    "compatibility evidence before route migration"
                ),
            },
            "request_effect_scope": {
                "export_handler": "one SELECT-only export query; no catalog DML or DDL",
                "surrounding_web_session": (
                    "may SELECT users and commit users.last_active before authorization "
                    "or export execution"
                ),
                "claim_boundary": (
                    "per-case SQL ledgers separate export reads from authentication activity"
                ),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory limiter; no current working-tree legacy import or persistent data"
            ),
            "case_isolation": (
                "every request rebuilds subjects and full/empty questions, resets actor "
                "last_active outside its SQL ledger, gets an explicit fresh Session scenario, "
                "reset limiter, deterministic remote address, pre/post 15-column question, "
                "9-column subject and stable identity fingerprints, plus activity ledger"
            ),
            "response_capture": (
                "full response body text and parsed body, body length/hash, and every test-client "
                "response header; cookies and dynamic rate-limit values are redacted"
            ),
            "redaction": (
                "public synthetic identities and data only; JWT, password hash, session-cookie "
                "values and database-current last_active timestamps omitted; fixed request ID"
            ),
            "fixture": {
                "actors": ACTORS,
                "subjects": SUBJECTS,
                "locked_subject_ids": [SUBJECTS["other"]],
                "questions": QUESTIONS,
                "orphan_subject_id": ORPHAN_SUBJECT_ID,
                "unicode_nd_primary": UNICODE_ND_PRIMARY,
                "int4_out_of_range": INT4_OUT_OF_RANGE,
                "full_facts_fingerprint": full_fixture_fingerprint,
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
        f"captured {document['case_count']} question-export cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
