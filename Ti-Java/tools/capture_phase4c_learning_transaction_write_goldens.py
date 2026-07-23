#!/usr/bin/env python3
"""Capture fixed-commit Phase 4C transaction-write execution evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
from importlib import metadata
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
from typing import Any, Iterator


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
ROUTE_MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
ENTRY_CONTRACT = (
    TI_JAVA / "docs/refactor/phase4c/learning-route-scope-entry-contract.json"
)
CALLER_EVIDENCE = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-callers.json"
)
CAPTURE_TEST = TOOLS_DIR / "test_capture_phase4c_learning_transaction_write_goldens.py"
DEFAULT_OUTPUT = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-golden-evidence.json"
)
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402
import capture_phase4b_personal_bank_category_goldens as shared  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
EXPECTED_ENTRY_CONTRACT_SHA256 = (
    "73c235dac971a52b2bf620565f3e4070c663a9584a63b2cc0a668f121cb73684"
)
EXPECTED_CALLER_EVIDENCE_SHA256 = (
    "9425f54c1cdd27c902fbb87712cfe6d7ffb81d4540d7759720b57d0b235862c3"
)
EXPECTED_ROUTE_MATRIX_SHA256 = (
    "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
)
FIXED_NOW_BJ = datetime(2026, 7, 23, 12, 0, 0)
FIXED_TODAY = date(2026, 7, 23)
USER_ID = 91001
ADMIN_ID = 91002
SUBJECT_ADMIN_ID = 91003
SUBJECT_ID = 92001
QUESTION_ID = 93001
MISSING_QUESTION_ID = 93999
BUSINESS_TABLES = (
    "favorites",
    "mistakes",
    "user_answers",
    "user_quiz_stats",
    "study_learning",
    "study_review",
    "user_checkins",
    "questions",
)
RESET_TABLES = (
    "study_review",
    "study_learning",
    "user_answers",
    "mistakes",
    "favorites",
    "user_quiz_stats",
    "user_checkins",
    "user_subjects",
    "questions",
    "subjects",
)
KEY_SOURCE_FILES = (
    "requirements.txt",
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/services/quiz_data_service.py",
    "app/core/utils/decorators.py",
    "app/core/utils/portable_question_sync.py",
    "app/core/utils/subject_permissions.py",
    "app/models/quiz.py",
    "app/models/study.py",
    "app/models/user.py",
    "app/modules/quiz/__init__.py",
    "app/modules/quiz/routes/api_components/core.py",
    "app/modules/quiz/routes/api_components/questions_study.py",
    "app/modules/quiz/routes/api_shared.py",
    "app/modules/user/routes/api.py",
)
_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})?$"
)


@dataclass(frozen=True)
class Operation:
    operation_id: str
    route_id: str
    method: str
    path: str
    rate_limit: str | None
    actor: str
    invalid_payload: dict[str, Any]
    success_payload: dict[str, Any]
    semantic_group: str


OPERATIONS = (
    Operation(
        "favorite-web-alias",
        "6d548bfd6830",
        "POST",
        "/api/favorite",
        "30/minute",
        "user",
        {"question_id": "not-an-integer"},
        {"question_id": QUESTION_ID},
        "favorite",
    ),
    Operation(
        "favorite-quiz-api",
        "b52d3008d4d1",
        "POST",
        "/api/quiz/favorite",
        "30/minute",
        "user",
        {"question_id": "not-an-integer"},
        {"question_id": QUESTION_ID},
        "favorite",
    ),
    Operation(
        "record-result-web-alias",
        "87bb4fb340c8",
        "POST",
        "/api/record_result",
        "60/minute",
        "user",
        {},
        {"question_id": QUESTION_ID, "is_correct": False},
        "record-result",
    ),
    Operation(
        "record-result-quiz-api",
        "67dccafb3ea4",
        "POST",
        "/api/quiz/record_result",
        "60/minute",
        "user",
        {},
        {"question_id": QUESTION_ID, "is_correct": False},
        "record-result",
    ),
    Operation(
        "study-learn-record",
        "bf3cb0c4f9ab",
        "POST",
        "/api/quiz/study/learn/record",
        "60/minute",
        "user",
        {"question_id": "not-an-integer"},
        {
            "question_id": QUESTION_ID,
            "is_correct": True,
            "source": "public",
            "subject": "高等数学",
        },
        "study-learn",
    ),
    Operation(
        "study-review-record",
        "c797832c43db",
        "POST",
        "/api/quiz/study/review/record",
        "60/minute",
        "user",
        {"question_id": QUESTION_ID, "rating": "invalid"},
        {
            "question_id": QUESTION_ID,
            "rating": "known",
            "source": "public",
            "subject": "高等数学",
        },
        "study-review-record",
    ),
    Operation(
        "study-review-master",
        "278e1eac5eb4",
        "POST",
        "/api/quiz/study/review/master",
        "30/minute",
        "user",
        {"question_id": "not-an-integer"},
        {
            "question_id": QUESTION_ID,
            "is_mastered": True,
            "source": "public",
            "subject": "高等数学",
        },
        "study-review-master",
    ),
    Operation(
        "user-checkin",
        "59c9c7366ec3",
        "POST",
        "/api/user/checkin",
        None,
        "user",
        {},
        {},
        "checkin",
    ),
    Operation(
        "question-edit",
        "624b5ac217d0",
        "PUT",
        f"/api/quiz/questions/{QUESTION_ID}",
        "10/minute",
        "admin",
        {"content": 123},
        {
            "content": "更新后的题干",
            "q_type": "选择题",
            "options": [
                {"key": "A", "value": "甲"},
                {"key": "B", "value": "乙"},
            ],
            "answer": "A",
            "explanation": "更新后的解析",
        },
        "question-edit",
    ),
)
OPERATION_BY_ID = {operation.operation_id: operation for operation in OPERATIONS}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", type=Path, default=TI_JAVA.parent)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def render_document(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return "<database-datetime>"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"bytes_sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, Mapping):
        return {
            str(key): normalize_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    if isinstance(value, str) and _DATETIME_RE.fullmatch(value):
        return "<database-datetime>"
    return value


def normalized_sql(statement: Any) -> str:
    return " ".join(str(statement).strip().split())


def classify_sql(statement: Any) -> str:
    sql = normalized_sql(statement).upper()
    if sql.startswith("SELECT") and " FROM QUESTIONS " in f" {sql} ":
        return "questions_select"
    if sql.startswith("UPDATE QUESTIONS "):
        return "questions_update"
    if " FROM FAVORITES " in f" {sql} " and sql.startswith("SELECT"):
        return "favorites_select"
    if sql.startswith("INSERT INTO FAVORITES"):
        return "favorites_insert"
    if sql.startswith("DELETE FROM FAVORITES"):
        return "favorites_delete"
    if " FROM MISTAKES " in f" {sql} " and sql.startswith("SELECT"):
        return "mistakes_select"
    if sql.startswith("INSERT INTO MISTAKES"):
        return "mistakes_insert"
    if sql.startswith("UPDATE MISTAKES"):
        return "mistakes_update"
    if sql.startswith("DELETE FROM MISTAKES"):
        return "mistakes_delete"
    if sql.startswith("INSERT INTO USER_ANSWERS"):
        return "user_answers_insert"
    if sql.startswith("DELETE FROM USER_ANSWERS"):
        return "user_answers_delete"
    if "STUDY_LEARNING" in sql:
        return "study_learning_sql"
    if "STUDY_REVIEW" in sql:
        return "study_review_sql"
    if "USER_CHECKINS" in sql:
        return "user_checkins_sql"
    if "USER_QUIZ_STATS" in sql:
        return "user_quiz_stats_sql"
    if sql.startswith("UPDATE USERS") and "LAST_ACTIVE" in sql:
        return "user_last_active_update"
    if " FROM USERS " in f" {sql} " and sql.startswith("SELECT"):
        return "users_select"
    if " FROM USER_SUBJECTS " in f" {sql} " and sql.startswith("SELECT"):
        return "user_subjects_select"
    if sql.startswith("SELECT"):
        return "select"
    if sql.startswith(("INSERT", "UPDATE", "DELETE")):
        return "dml"
    return "other"


@contextmanager
def execution_environment(data_dir: str) -> Iterator[None]:
    updates = {
        "DATA_DIR": data_dir,
        "FLASK_ENV": "testing",
        "JWT_USER_STATE_CACHE_TTL_SECONDS": "0",
        "RATELIMIT_STORAGE_URI": "memory://",
        "RATELIMIT_STORAGE_URL": "memory://",
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


def read_fixed_blob(legacy_root: Path, archived: Any, path: str) -> tuple[bytes, str]:
    archive_path = archived.root / path
    if archive_path.is_file():
        return archive_path.read_bytes(), "verified complete app/ archive"
    return (
        pinned_source._run_read_only_git(
            legacy_root, "show", f"{LEGACY_COMMIT}:{path}"
        ),
        "git show from verified fixed commit",
    )


def key_source_attestation(
    legacy_root: Path, archived: Any
) -> dict[str, dict[str, Any]]:
    object_format = archived.attestation["git_object_format"]
    result = {}
    for path in KEY_SOURCE_FILES:
        payload, transport = read_fixed_blob(legacy_root, archived, path)
        result[path] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "git_blob": pinned_source._git_blob_id(payload, object_format),
            "size_bytes": len(payload),
            "transport": transport,
        }
    return result


def file_attestation(
    path: Path, expected_sha256: str, relative_path: str
) -> dict[str, Any]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise AssertionError(f"fixed predecessor drifted: {relative_path}")
    return {
        "path": relative_path,
        "sha256": digest,
        "size_bytes": len(payload),
        "document_payload_sha256": json.loads(payload)[
            "document_payload_sha256"
        ],
    }


def route_matrix_attestation() -> dict[str, Any]:
    payload = ROUTE_MATRIX.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_ROUTE_MATRIX_SHA256:
        raise AssertionError("route matrix drifted")
    import csv

    rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
    route_ids = {operation.route_id for operation in OPERATIONS}
    selected = [row for row in rows if row["route_id"] in route_ids]
    if len(selected) != len(OPERATIONS):
        raise AssertionError("transaction-write route matrix is incomplete")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": digest,
        "size_bytes": len(payload),
        "selected_rows": selected,
        "selected_rows_sha256": sha256_json(selected),
    }


def normalized_response(response: Any) -> dict[str, Any]:
    body = response.get_json(silent=True)
    if body is None:
        body = response.get_data(as_text=True)
    headers: dict[str, list[str]] = {}
    for name in sorted(set(response.headers.keys()), key=str.lower):
        values = response.headers.getlist(name)
        lower = name.lower()
        if lower == "set-cookie":
            values = ["<redacted-session-cookie>" for _ in values]
        elif lower == "x-ratelimit-reset":
            values = ["<rate-limit-reset-epoch>" for _ in values]
        elif lower == "retry-after":
            values = ["<dynamic-seconds>" for _ in values]
        headers[name] = values
    return {
        "status": response.status_code,
        "content_type": response.content_type,
        "body": normalize_value(body),
        "headers": headers,
    }


def table_fingerprint(db: Any, table: str, *, include_rows: bool) -> dict[str, Any]:
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    columns = [column["name"] for column in inspector.get_columns(table)]
    primary_key = (
        inspector.get_pk_constraint(table).get("constrained_columns") or []
    )
    ordering = primary_key or columns
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM {table} "
        f"ORDER BY {', '.join(ordering)}"
    )).fetchall()
    normalized = [
        [normalize_value(value) for value in row]
        for row in rows
    ]
    result = {
        "columns": columns,
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }
    if include_rows:
        result["rows"] = normalized
    return result


def business_snapshot(db: Any, *, include_rows: bool) -> dict[str, Any]:
    return {
        table: table_fingerprint(db, table, include_rows=include_rows)
        for table in BUSINESS_TABLES
    }


def identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        "SELECT id, username, is_admin, is_subject_admin, is_locked, "
        "session_version, last_active FROM users "
        "WHERE id IN (:user_id, :admin_id, :subject_admin_id) ORDER BY id"
    ), {
        "user_id": USER_ID,
        "admin_id": ADMIN_ID,
        "subject_admin_id": SUBJECT_ADMIN_ID,
    }).fetchall()
    normalized = [[normalize_value(value) for value in row] for row in rows]
    return {
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
        "rows": normalized,
    }


def _insert_question_fixture(db: Any) -> None:
    from sqlalchemy import text

    db.session.execute(text(
        "INSERT INTO subjects "
        "(id, name, description, is_locked, created_at) "
        "VALUES (:id, :name, :description, :is_locked, :created_at)"
    ), {
        "id": SUBJECT_ID,
        "name": "高等数学",
        "description": "Phase 4C 固定夹具",
        "is_locked": False,
        "created_at": FIXED_NOW_BJ,
    })
    db.session.execute(text(
        "INSERT INTO questions "
        "(id, subject_id, type, content, options, answer, analysis, tags, "
        "difficulty, source, created_by, updated_by, created_at, updated_at) "
        "VALUES (:id, :subject_id, :type, :content, :options, :answer, "
        ":analysis, :tags, :difficulty, :source, :created_by, :updated_by, "
        ":created_at, :updated_at)"
    ), {
        "id": QUESTION_ID,
        "subject_id": SUBJECT_ID,
        "type": "single_choice",
        "content": "原始题干",
        "options": json.dumps([
            {"key": "A", "value": "甲"},
            {"key": "B", "value": "乙"},
        ], ensure_ascii=False, separators=(",", ":")),
        "answer": '["A"]',
        "analysis": "原始解析",
        "tags": "[]",
        "difficulty": 1,
        "source": "phase4c-golden",
        "created_by": ADMIN_ID,
        "updated_by": ADMIN_ID,
        "created_at": FIXED_NOW_BJ,
        "updated_at": FIXED_NOW_BJ,
    })


def reset_fixture(
    db: Any,
    legacy_app: Any,
    *,
    seed_mistake: bool = False,
    restrict_user: bool = False,
) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    for table in RESET_TABLES:
        db.session.execute(text(f"DELETE FROM {table}"))
    _insert_question_fixture(db)
    if seed_mistake:
        db.session.execute(text(
            "INSERT INTO mistakes "
            "(id, user_id, question_id, wrong_count, created_at, "
            "updated_at, last_updated) "
            "VALUES (1, :uid, :qid, 2, :now, :now, :now)"
        ), {"uid": USER_ID, "qid": QUESTION_ID, "now": FIXED_NOW_BJ})
    if restrict_user:
        db.session.execute(text(
            "INSERT INTO user_subjects (id, user_id, subject_id) "
            "VALUES (1, :uid, :subject_id)"
        ), {"uid": USER_ID, "subject_id": SUBJECT_ID})
    db.session.execute(text(
        "UPDATE users SET last_active = NULL "
        "WHERE id IN (:user_id, :admin_id, :subject_admin_id)"
    ), {
        "user_id": USER_ID,
        "admin_id": ADMIN_ID,
        "subject_admin_id": SUBJECT_ADMIN_ID,
    })
    db.session.commit()
    with legacy_app._LAST_ACTIVE_LOCK:
        marker = time.monotonic()
        legacy_app._LAST_ACTIVE_TS.clear()
        legacy_app._LAST_ACTIVE_TS.update({
            USER_ID: marker,
            ADMIN_ID: marker,
            SUBJECT_ADMIN_ID: marker,
        })
    return business_snapshot(db, include_rows=False)


def seed_actors(db: Any, User: Any) -> None:
    actors = (
        (USER_ID, "user", False, False),
        (ADMIN_ID, "admin", True, False),
        (SUBJECT_ADMIN_ID, "subject_admin", False, True),
    )
    for user_id, label, is_admin, is_subject_admin in actors:
        db.session.add(User(
            id=user_id,
            username=f"phase4c_{label}",
            email=f"phase4c_{label}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=is_admin,
            is_subject_admin=is_subject_admin,
            is_notification_admin=False,
            is_locked=False,
            session_version=21,
            created_at=FIXED_NOW_BJ,
            last_active=None,
        ))
    db.session.commit()


def actor_id(actor: str) -> int:
    return ADMIN_ID if actor == "admin" else USER_ID


def set_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        uid = actor_id(actor)
        session.update({
            "user_id": uid,
            "username": f"phase4c_{actor}",
            "session_version": 21,
            "is_admin": actor == "admin",
            "is_subject_admin": False,
            "is_notification_admin": False,
        })


def reset_limiters(app: Any) -> None:
    for limiter in app.extensions.get("limiter", set()):
        limiter.reset()


@contextmanager
def sql_probe(
    engine: Any,
    *,
    fail_classification: str | None = None,
) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event
    from sqlalchemy.engine import Connection

    ledger: dict[str, Any] = {
        "statements": [],
        "transaction_events": [],
        "raw_connection_execute_attempts": [],
        "fault_events": [],
    }

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        parameters: Any,
        _context: Any,
        executemany: Any,
    ) -> None:
        classification = classify_sql(statement)
        item = {
            "classification": classification,
            "sql": normalized_sql(statement),
            "parameters": normalize_value(parameters),
            "executemany": bool(executemany),
        }
        ledger["statements"].append(item)
        if (
            fail_classification is not None
            and classification == fail_classification
            and not ledger["fault_events"]
        ):
            ledger["fault_events"].append({
                "classification": classification,
                "kind": "synthetic_before_cursor_failure",
            })
            raise RuntimeError(
                f"synthetic Phase 4C failure at {classification}"
            )

    def transaction_event(name: str):
        def record(_connection: Any) -> None:
            ledger["transaction_events"].append(name)

        return record

    begin = transaction_event("begin")
    commit = transaction_event("commit")
    rollback = transaction_event("rollback")
    original_execute = Connection.execute

    def instrumented_execute(
        connection: Any, statement: Any, *args: Any, **kwargs: Any
    ) -> Any:
        if isinstance(statement, str):
            ledger["raw_connection_execute_attempts"].append({
                "sql": normalized_sql(statement),
                "positional_arguments": normalize_value(args),
                "keyword_argument_names": sorted(kwargs),
            })
        return original_execute(connection, statement, *args, **kwargs)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "begin", begin)
    event.listen(engine, "commit", commit)
    event.listen(engine, "rollback", rollback)
    Connection.execute = instrumented_execute
    try:
        yield ledger
    finally:
        Connection.execute = original_execute
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "begin", begin)
        event.remove(engine, "commit", commit)
        event.remove(engine, "rollback", rollback)
        ledger["statement_count"] = len(ledger["statements"])
        ledger["classification_counts"] = dict(sorted(Counter(
            statement["classification"]
            for statement in ledger["statements"]
        ).items()))
        ledger["statements_sha256"] = sha256_json(ledger["statements"])
        ledger["transaction_events_sha256"] = sha256_json(
            ledger["transaction_events"]
        )
        ledger["raw_connection_execute_attempts_sha256"] = sha256_json(
            ledger["raw_connection_execute_attempts"]
        )


def request_headers(
    case_id: str,
    *,
    credential: str,
    xhr: bool,
    tokens: dict[str, str],
    actor: str,
) -> tuple[dict[str, str], dict[str, str]]:
    live = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-ID": f"phase4c-{case_id}",
    }
    recorded = dict(live)
    if xhr:
        live["X-Requested-With"] = "XMLHttpRequest"
        recorded["X-Requested-With"] = "XMLHttpRequest"
    if credential == "bearer":
        live["Authorization"] = "Bearer " + tokens[actor]
        recorded["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    elif credential == "invalid-bearer":
        live["Authorization"] = "Bearer fixed-invalid-token"
        recorded["Authorization"] = "Bearer <redacted-invalid-synthetic-jwt>"
    return live, recorded


def perform_request(
    client: Any,
    operation: Operation,
    payload: dict[str, Any],
    *,
    case_id: str,
    credential: str,
    xhr: bool,
    tokens: dict[str, str],
    engine: Any,
    fail_classification: str | None = None,
) -> dict[str, Any]:
    session_actor = operation.actor if credential == "session" else None
    set_session(client, session_actor)
    live_headers, recorded_headers = request_headers(
        case_id,
        credential=credential,
        xhr=xhr,
        tokens=tokens,
        actor=operation.actor,
    )
    digest = hashlib.sha256(case_id.encode("utf-8")).digest()
    remote_address = f"198.51.{digest[0]}.{digest[1]}"
    with sql_probe(
        engine, fail_classification=fail_classification
    ) as ledger:
        response = client.open(
            operation.path,
            method=operation.method,
            json=payload,
            headers=live_headers,
            environ_overrides={"REMOTE_ADDR": remote_address},
            follow_redirects=False,
        )
    return {
        "request": {
            "method": operation.method,
            "path": operation.path,
            "headers": recorded_headers,
            "json": payload,
            "remote_address": remote_address,
            "credential": credential,
        },
        "response": normalized_response(response),
        "execution": ledger,
    }


def capture_isolated_case(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
    operation: Operation,
    *,
    case_id: str,
    payload: dict[str, Any],
    credential: str,
    xhr: bool,
    seed_mistake: bool = False,
    restrict_user: bool = False,
    fail_classification: str | None = None,
    include_rows: bool = False,
) -> dict[str, Any]:
    reset_limiters(client.application)
    with client.application.app_context():
        fixture = reset_fixture(
            db,
            legacy_app,
            seed_mistake=seed_mistake,
            restrict_user=restrict_user,
        )
        before = business_snapshot(db, include_rows=include_rows)
        identity_before = identity_fingerprint(db)
        engine = db.engine
        db.session.remove()
    observed = perform_request(
        client,
        operation,
        payload,
        case_id=case_id,
        credential=credential,
        xhr=xhr,
        tokens=tokens,
        engine=engine,
        fail_classification=fail_classification,
    )
    with client.application.app_context():
        db.session.rollback()
        db.session.remove()
        after = business_snapshot(db, include_rows=include_rows)
        identity_after = identity_fingerprint(db)
        db.session.remove()
    return {
        "case_id": case_id,
        "operation_id": operation.operation_id,
        "route_id": operation.route_id,
        **observed,
        "database": {
            "fixture_fingerprints": fixture,
            "before": before,
            "after": after,
            "changed_tables": [
                table
                for table in BUSINESS_TABLES
                if before[table] != after[table]
            ],
            "identity_before": identity_before,
            "identity_after": identity_after,
            "identity_unchanged": identity_before == identity_after,
        },
    }


def capture_auth_csrf_matrix(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
) -> list[dict[str, Any]]:
    modes = (
        ("session-xhr", "session", True),
        ("bearer-no-xhr", "bearer", False),
        ("session-missing-xhr", "session", False),
        ("anonymous-xhr", "none", True),
        ("invalid-bearer-xhr", "invalid-bearer", True),
    )
    cases = []
    for operation in OPERATIONS:
        for suffix, credential, xhr in modes:
            case_id = f"auth-{operation.operation_id}-{suffix}"
            cases.append(capture_isolated_case(
                client,
                db,
                legacy_app,
                tokens,
                operation,
                case_id=case_id,
                payload=operation.invalid_payload,
                credential=credential,
                xhr=xhr,
            ))
    return cases


def capture_business_cases(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
) -> list[dict[str, Any]]:
    specs = (
        ("favorite-web-alias-add", "favorite-web-alias", {}, False, False),
        ("favorite-quiz-api-add", "favorite-quiz-api", {}, False, False),
        (
            "record-result-web-wrong",
            "record-result-web-alias",
            {},
            False,
            False,
        ),
        (
            "record-result-quiz-correct-clears-mistake",
            "record-result-quiz-api",
            {
                "payload": {
                    "question_id": QUESTION_ID,
                    "is_correct": True,
                    "clear_mistake_on_correct": True,
                }
            },
            True,
            False,
        ),
        ("study-learn-runtime-failure", "study-learn-record", {}, False, False),
        (
            "study-review-record-runtime-failure",
            "study-review-record",
            {},
            False,
            False,
        ),
        (
            "study-review-master-runtime-failure",
            "study-review-master",
            {},
            False,
            False,
        ),
        ("checkin-runtime-failure", "user-checkin", {}, False, False),
        ("question-edit-successful-noop", "question-edit", {}, False, False),
        (
            "favorite-forbidden-subject",
            "favorite-quiz-api",
            {},
            False,
            True,
        ),
        (
            "question-edit-regular-user-forbidden",
            "question-edit",
            {"credential": "session", "actor_override": "user"},
            False,
            False,
        ),
    )
    cases = []
    for case_id, operation_id, overrides, seed_mistake, restrict_user in specs:
        operation = OPERATION_BY_ID[operation_id]
        actor_override = overrides.get("actor_override")
        if actor_override is not None:
            operation = Operation(
                operation.operation_id,
                operation.route_id,
                operation.method,
                operation.path,
                operation.rate_limit,
                actor_override,
                operation.invalid_payload,
                operation.success_payload,
                operation.semantic_group,
            )
        cases.append(capture_isolated_case(
            client,
            db,
            legacy_app,
            tokens,
            operation,
            case_id=case_id,
            payload=overrides.get("payload", operation.success_payload),
            credential=overrides.get("credential", "session"),
            xhr=True,
            seed_mistake=seed_mistake,
            restrict_user=restrict_user,
            include_rows=True,
        ))
    return cases


def compact_outcome(observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "response": observed["response"],
        "execution": observed["execution"],
    }


def capture_duplicate_sequences(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
) -> list[dict[str, Any]]:
    canonical_ids = (
        "favorite-quiz-api",
        "record-result-quiz-api",
        "study-learn-record",
        "study-review-record",
        "study-review-master",
        "user-checkin",
        "question-edit",
    )
    results = []
    for operation_id in canonical_ids:
        operation = OPERATION_BY_ID[operation_id]
        reset_limiters(client.application)
        with client.application.app_context():
            reset_fixture(db, legacy_app)
            before = business_snapshot(db, include_rows=True)
            engine = db.engine
            db.session.remove()
        outcomes = []
        for attempt in (1, 2):
            observed = perform_request(
                client,
                operation,
                operation.success_payload,
                case_id=f"duplicate-{operation_id}-{attempt}",
                credential="session",
                xhr=True,
                tokens=tokens,
                engine=engine,
            )
            outcomes.append(compact_outcome(observed))
        with client.application.app_context():
            db.session.rollback()
            db.session.remove()
            after = business_snapshot(db, include_rows=True)
            db.session.remove()
        results.append({
            "operation_id": operation_id,
            "semantic_group": operation.semantic_group,
            "attempt_count": 2,
            "outcomes": outcomes,
            "database_before": before,
            "database_after": after,
            "changed_tables": [
                table
                for table in BUSINESS_TABLES
                if before[table] != after[table]
            ],
        })
    return results


def _concurrent_response(response: Any) -> dict[str, Any]:
    normalized = normalized_response(response)
    body = normalized["body"]
    if isinstance(body, dict) and "request_id" in body:
        body["request_id"] = "<concurrent-request-id>"
    normalized["headers"].pop("X-Request-ID", None)
    normalized["headers"].pop("Set-Cookie", None)
    return normalized


def capture_concurrent_operation(
    app: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
    operation: Operation,
) -> dict[str, Any]:
    from sqlalchemy import event

    with app.app_context():
        reset_fixture(db, legacy_app)
        before = business_snapshot(db, include_rows=True)
        engine = db.engine
        db.session.remove()
    reset_limiters(app)
    start = threading.Barrier(2)
    stage = threading.Barrier(2)
    outcomes: list[dict[str, Any]] = []
    errors: list[str] = []
    lock = threading.Lock()

    def after_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        _parameters: Any,
        _context: Any,
        _executemany: Any,
    ) -> None:
        classification = classify_sql(statement)
        target = (
            operation.semantic_group == "favorite"
            and classification == "favorites_select"
        ) or (
            operation.semantic_group == "record-result"
            and classification == "user_answers_delete"
        )
        if target:
            stage.wait(timeout=8)

    use_stage = operation.semantic_group in {"favorite", "record-result"}
    if use_stage:
        event.listen(engine, "after_cursor_execute", after_cursor_execute)

    def worker(index: int) -> None:
        try:
            client = app.test_client()
            start.wait(timeout=8)
            response = client.open(
                operation.path,
                method=operation.method,
                json=operation.success_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + tokens[operation.actor],
                    "X-Request-ID": f"phase4c-concurrent-{index}",
                },
                environ_overrides={
                    "REMOTE_ADDR": f"203.0.113.{40 + index}"
                },
                follow_redirects=False,
            )
            with lock:
                outcomes.append(_concurrent_response(response))
        except Exception as error:  # pragma: no cover - evidence guard
            with lock:
                errors.append(type(error).__name__)

    threads = [
        threading.Thread(target=worker, args=(index,), daemon=True)
        for index in (1, 2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    if use_stage:
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
    if any(thread.is_alive() for thread in threads):
        raise AssertionError(
            f"concurrent probe timed out: {operation.operation_id}"
        )
    if errors or len(outcomes) != 2:
        raise AssertionError(
            f"concurrent probe failed: {operation.operation_id} {errors}"
        )
    outcomes.sort(key=canonical_json)
    with app.app_context():
        db.session.rollback()
        db.session.remove()
        after = business_snapshot(db, include_rows=True)
        db.session.remove()
    return {
        "operation_id": operation.operation_id,
        "semantic_group": operation.semantic_group,
        "real_flask_requests": True,
        "shared_temporary_sqlite": True,
        "synchronized_after_read_before_write": use_stage,
        "request_count": 2,
        "outcomes": outcomes,
        "status_histogram": {
            str(status): count
            for status, count in sorted(Counter(
                outcome["status"] for outcome in outcomes
            ).items())
        },
        "database_before": before,
        "database_after": after,
        "changed_tables": [
            table
            for table in BUSINESS_TABLES
            if before[table] != after[table]
        ],
    }


def capture_concurrency(
    app: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
) -> list[dict[str, Any]]:
    canonical_ids = (
        "favorite-quiz-api",
        "record-result-quiz-api",
        "study-learn-record",
        "study-review-record",
        "study-review-master",
        "user-checkin",
        "question-edit",
    )
    return [
        capture_concurrent_operation(
            app, db, legacy_app, tokens, OPERATION_BY_ID[operation_id]
        )
        for operation_id in canonical_ids
    ]


def rate_attempt_count(operation: Operation) -> int:
    if operation.rate_limit is None:
        return 12
    return int(operation.rate_limit.split("/", 1)[0]) + 2


def capture_rate_limits(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
) -> list[dict[str, Any]]:
    results = []
    for operation in OPERATIONS:
        reset_limiters(client.application)
        with client.application.app_context():
            reset_fixture(db, legacy_app)
            before = business_snapshot(db, include_rows=False)
            db.session.remove()
        set_session(client, operation.actor)
        attempts = rate_attempt_count(operation)
        statuses = []
        final_response = None
        for attempt in range(1, attempts + 1):
            response = client.open(
                operation.path,
                method=operation.method,
                json=operation.invalid_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Request-ID": (
                        f"phase4c-rate-{operation.operation_id}-{attempt}"
                    ),
                },
                environ_overrides={
                    "REMOTE_ADDR": (
                        f"192.0.2.{20 + list(OPERATION_BY_ID).index(operation.operation_id)}"
                    )
                },
                follow_redirects=False,
            )
            statuses.append(response.status_code)
            final_response = normalized_response(response)
        with client.application.app_context():
            db.session.rollback()
            db.session.remove()
            after = business_snapshot(db, include_rows=False)
            db.session.remove()
        results.append({
            "operation_id": operation.operation_id,
            "declared_route_limit": operation.rate_limit,
            "base_limits_overridden_for_route_isolation": False,
            "attempt_count": attempts,
            "status_histogram": {
                str(status): count
                for status, count in sorted(Counter(statuses).items())
            },
            "first_429_attempt": (
                statuses.index(429) + 1 if 429 in statuses else None
            ),
            "final_response": final_response,
            "database_unchanged": before == after,
        })
    return results


def capture_rollback_retry(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
) -> list[dict[str, Any]]:
    specs = (
        ("favorite-quiz-api", "favorites_insert"),
        ("record-result-quiz-api", "user_answers_insert"),
    )
    results = []
    for operation_id, failure in specs:
        operation = OPERATION_BY_ID[operation_id]
        reset_limiters(client.application)
        with client.application.app_context():
            reset_fixture(db, legacy_app)
            before = business_snapshot(db, include_rows=True)
            engine = db.engine
            db.session.remove()
        failed = perform_request(
            client,
            operation,
            operation.success_payload,
            case_id=f"rollback-{operation_id}-failure",
            credential="session",
            xhr=True,
            tokens=tokens,
            engine=engine,
            fail_classification=failure,
        )
        with client.application.app_context():
            db.session.rollback()
            db.session.remove()
            after_failure = business_snapshot(db, include_rows=True)
            db.session.remove()
        retried = perform_request(
            client,
            operation,
            operation.success_payload,
            case_id=f"rollback-{operation_id}-retry",
            credential="session",
            xhr=True,
            tokens=tokens,
            engine=engine,
        )
        with client.application.app_context():
            db.session.rollback()
            db.session.remove()
            after_retry = business_snapshot(db, include_rows=True)
            db.session.remove()
        results.append({
            "operation_id": operation_id,
            "injected_failure_classification": failure,
            "failure_outcome": compact_outcome(failed),
            "retry_outcome": compact_outcome(retried),
            "database_before": before,
            "database_after_failure": after_failure,
            "database_after_retry": after_retry,
            "failure_rolled_back_all_business_changes": (
                before == after_failure
            ),
            "retry_changed_tables": [
                table
                for table in BUSINESS_TABLES
                if after_failure[table] != after_retry[table]
            ],
        })
    for operation_id in (
        "study-learn-record",
        "study-review-record",
        "study-review-master",
        "user-checkin",
        "question-edit",
    ):
        operation = OPERATION_BY_ID[operation_id]
        reset_limiters(client.application)
        with client.application.app_context():
            reset_fixture(db, legacy_app)
            before = business_snapshot(db, include_rows=True)
            engine = db.engine
            db.session.remove()
        attempts = [
            perform_request(
                client,
                operation,
                operation.success_payload,
                case_id=f"inherent-retry-{operation_id}-{attempt}",
                credential="session",
                xhr=True,
                tokens=tokens,
                engine=engine,
            )
            for attempt in (1, 2)
        ]
        with client.application.app_context():
            db.session.rollback()
            db.session.remove()
            after = business_snapshot(db, include_rows=True)
            db.session.remove()
        results.append({
            "operation_id": operation_id,
            "injected_failure_classification": None,
            "legacy_inherent_failure_or_noop": True,
            "attempts": [compact_outcome(attempt) for attempt in attempts],
            "database_before": before,
            "database_after": after,
            "database_unchanged": before == after,
        })
    return results


def schema_invariants(db: Any) -> dict[str, Any]:
    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    result = {}
    for table in BUSINESS_TABLES:
        result[table] = {
            "primary_key": inspector.get_pk_constraint(table),
            "unique_constraints": inspector.get_unique_constraints(table),
            "foreign_keys": inspector.get_foreign_keys(table),
        }
    return normalize_value(result)


def runtime_route_map(app: Any) -> list[dict[str, Any]]:
    route_ids_by_path_method = {
        (operation.path, operation.method): operation.route_id
        for operation in OPERATIONS
        if operation.operation_id != "question-edit"
    }
    route_ids_by_path_method[(
        "/api/quiz/questions/<int:question_id>",
        "PUT",
    )] = "624b5ac217d0"
    selected = []
    for rule in app.url_map.iter_rules():
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            key = (rule.rule, method)
            if key in route_ids_by_path_method:
                selected.append({
                    "route_id": route_ids_by_path_method[key],
                    "path": rule.rule,
                    "method": method,
                    "endpoint": rule.endpoint,
                })
    selected.sort(key=lambda item: item["route_id"])
    if len(selected) != len(OPERATIONS):
        raise AssertionError("real Flask route map does not contain all 9 writes")
    return selected


def assert_capture_contract(
    auth_cases: list[dict[str, Any]],
    business_cases: list[dict[str, Any]],
    duplicates: list[dict[str, Any]],
    concurrency: list[dict[str, Any]],
    rates: list[dict[str, Any]],
    rollback_retry: list[dict[str, Any]],
) -> None:
    if len(auth_cases) != len(OPERATIONS) * 5:
        raise AssertionError("auth/CSRF matrix is incomplete")
    for case in auth_cases:
        suffix = case["case_id"]
        status = case["response"]["status"]
        if suffix.endswith("session-missing-xhr") and status != 403:
            raise AssertionError(f"CSRF boundary drifted: {suffix}={status}")
        if (
            suffix.endswith("anonymous-xhr")
            or suffix.endswith("invalid-bearer-xhr")
        ) and status != 401:
            raise AssertionError(f"authentication boundary drifted: {suffix}={status}")
        if case["database"]["changed_tables"]:
            raise AssertionError(f"auth probe mutated business data: {suffix}")
        if not case["database"]["identity_unchanged"]:
            raise AssertionError(f"auth probe mutated identity: {suffix}")

    business = {case["case_id"]: case for case in business_cases}
    expected_statuses = {
        "favorite-web-alias-add": 200,
        "favorite-quiz-api-add": 200,
        "record-result-web-wrong": 200,
        "record-result-quiz-correct-clears-mistake": 200,
        "study-learn-runtime-failure": 500,
        "study-review-record-runtime-failure": 500,
        "study-review-master-runtime-failure": 500,
        "checkin-runtime-failure": 500,
        "question-edit-successful-noop": 200,
        "favorite-forbidden-subject": 403,
        "question-edit-regular-user-forbidden": 403,
    }
    if set(business) != set(expected_statuses):
        raise AssertionError("business case set is incomplete")
    for case_id, expected in expected_statuses.items():
        observed = business[case_id]["response"]["status"]
        if observed != expected:
            raise AssertionError(
                f"{case_id} status drifted: expected={expected} observed={observed}"
            )
    if business["favorite-web-alias-add"]["database"]["changed_tables"] != [
        "favorites"
    ]:
        raise AssertionError("favorite alias write set drifted")
    if business["favorite-quiz-api-add"]["database"]["changed_tables"] != [
        "favorites"
    ]:
        raise AssertionError("favorite quiz write set drifted")
    for case_id in (
        "study-learn-runtime-failure",
        "study-review-record-runtime-failure",
        "study-review-master-runtime-failure",
        "checkin-runtime-failure",
        "question-edit-successful-noop",
    ):
        if business[case_id]["database"]["changed_tables"]:
            raise AssertionError(f"legacy failure/no-op drifted: {case_id}")
    raw = business["study-learn-runtime-failure"]["execution"][
        "raw_connection_execute_attempts"
    ]
    if not raw or "SELECT id FROM subjects" not in raw[0]["sql"]:
        raise AssertionError("study raw SQLAlchemy 2 failure is not evidenced")
    raw_update = business["question-edit-successful-noop"]["execution"][
        "raw_connection_execute_attempts"
    ]
    if not any("UPDATE questions" in item["sql"] for item in raw_update):
        raise AssertionError("question-edit swallowed update is not evidenced")

    if len(duplicates) != 7 or len(concurrency) != 7:
        raise AssertionError("duplicate/concurrency semantic groups are incomplete")
    if not all(item["attempt_count"] == 2 for item in duplicates):
        raise AssertionError("duplicate attempts drifted")
    if not all(item["request_count"] == 2 for item in concurrency):
        raise AssertionError("concurrent attempts drifted")
    favorite_concurrent = next(
        item for item in concurrency if item["semantic_group"] == "favorite"
    )
    if favorite_concurrent["status_histogram"] != {"200": 1, "500": 1}:
        raise AssertionError("favorite concurrent outcome drifted")
    record_concurrent = next(
        item
        for item in concurrency
        if item["semantic_group"] == "record-result"
    )
    if record_concurrent["status_histogram"] != {"500": 2}:
        raise AssertionError("record-result concurrent outcome drifted")

    for rate in rates:
        operation = OPERATION_BY_ID[rate["operation_id"]]
        if operation.rate_limit is None:
            if rate["first_429_attempt"] != 11:
                raise AssertionError("checkin inherited global limit drifted")
        else:
            threshold = int(operation.rate_limit.split("/", 1)[0])
            if rate["first_429_attempt"] != threshold + 1:
                raise AssertionError(
                    f"route limit drifted: {operation.operation_id}"
                )
        if not rate["database_unchanged"]:
            raise AssertionError("rate probe mutated business data")
    if len(rollback_retry) != 7:
        raise AssertionError("rollback/retry matrix is incomplete")
    for item in rollback_retry[:2]:
        if not item["failure_rolled_back_all_business_changes"]:
            raise AssertionError("injected failure was not rolled back")


def capture_document(legacy_root: Path) -> dict[str, Any]:
    if pinned_source.LEGACY_COMMIT != LEGACY_COMMIT:
        raise AssertionError("shared legacy authority drifted")
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        source = {
            "complete_app_archive": archived.attestation,
            "key_sources": key_source_attestation(legacy_root, archived),
            "route_matrix": route_matrix_attestation(),
            "entry_contract": file_attestation(
                ENTRY_CONTRACT,
                EXPECTED_ENTRY_CONTRACT_SHA256,
                (
                    "docs/refactor/phase4c/"
                    "learning-route-scope-entry-contract.json"
                ),
            ),
            "caller_evidence": file_attestation(
                CALLER_EVIDENCE,
                EXPECTED_CALLER_EVIDENCE_SHA256,
                (
                    "docs/refactor/phase4c/"
                    "learning-transaction-write-callers.json"
                ),
            ),
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-phase4c-learning-transaction-write-"
        ) as data_dir:
            with execution_environment(data_dir):
                with pinned_source.archived_legacy_import_environment(
                    archived.root
                ):
                    import app as legacy_app
                    from app.core.extensions import db
                    from app.core.utils.jwt_utils import generate_jwt_token
                    from app.models.user import User
                    from app.modules.quiz.routes.api_components import (
                        questions_study,
                    )
                    from app.modules.user.routes import api as user_api

                    pinned_source.assert_module_from_archive(
                        legacy_app, archived.root
                    )
                    previous_logging = logging.root.manager.disable
                    logging.disable(logging.CRITICAL)
                    legacy_app._start_background_tasks = lambda _app: None
                    original_study_now = questions_study.now_bj
                    original_user_now = user_api.now_bj
                    original_user_today = user_api.today_bj
                    questions_study.now_bj = lambda: FIXED_NOW_BJ
                    user_api.now_bj = lambda: FIXED_NOW_BJ
                    user_api.today_bj = lambda: FIXED_TODAY
                    app = legacy_app.create_app("testing")
                    app.config.update(
                        JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                        LAST_ACTIVE_UPDATE_INTERVAL_SECONDS=3600,
                        PROPAGATE_EXCEPTIONS=False,
                        TESTING=True,
                    )
                    try:
                        with app.app_context():
                            db.create_all()
                            seed_actors(db, User)
                            reset_fixture(db, legacy_app)
                            tokens = {
                                "user": generate_jwt_token(
                                    user_id=USER_ID,
                                    openid="",
                                    session_version=21,
                                ),
                                "admin": generate_jwt_token(
                                    user_id=ADMIN_ID,
                                    openid="",
                                    session_version=21,
                                ),
                            }
                            routes = runtime_route_map(app)
                            schema = schema_invariants(db)
                            db.session.remove()
                        client = app.test_client()
                        auth_cases = capture_auth_csrf_matrix(
                            client, db, legacy_app, tokens
                        )
                        business_cases = capture_business_cases(
                            client, db, legacy_app, tokens
                        )
                        duplicate_sequences = capture_duplicate_sequences(
                            client, db, legacy_app, tokens
                        )
                        concurrent_outcomes = capture_concurrency(
                            app, db, legacy_app, tokens
                        )
                        rate_limits = capture_rate_limits(
                            client, db, legacy_app, tokens
                        )
                        rollback_retry = capture_rollback_retry(
                            client, db, legacy_app, tokens
                        )
                        assert_capture_contract(
                            auth_cases,
                            business_cases,
                            duplicate_sequences,
                            concurrent_outcomes,
                            rate_limits,
                            rollback_retry,
                        )
                    finally:
                        questions_study.now_bj = original_study_now
                        user_api.now_bj = original_user_now
                        user_api.today_bj = original_user_today
                        logging.disable(previous_logging)
                        with app.app_context():
                            db.session.remove()

        tool_payload = Path(__file__).read_bytes()
        test_payload = CAPTURE_TEST.read_bytes()
        document: dict[str, Any] = {
            "contract_id": (
                "ti.phase4c.learning-transaction-write-golden-execution"
            ),
            "schema_version": 1,
            "captured_at": "2026-07-23",
            "legacy_commit": LEGACY_COMMIT,
            "fixed_beijing_time": FIXED_NOW_BJ.isoformat(sep=" "),
            "source_authority": source,
            "runtime": {
                "execution_model": (
                    "complete app/ archive from the immutable commit; real "
                    "Flask routes; temporary SQLite; synthetic identities; "
                    "fixed business clock; in-memory route-limit storage"
                ),
                "dependency_versions": {
                    "flask": metadata.version("Flask"),
                    "flask_sqlalchemy": metadata.version("Flask-SQLAlchemy"),
                    "sqlalchemy": metadata.version("SQLAlchemy"),
                    "flask_limiter": metadata.version("Flask-Limiter"),
                },
                "effective_testing_base_limits": (
                    "5000 per day;500 per hour;10 per second"
                ),
                "explicit_route_decorators_replace_the_default_limit": True,
                "production_traffic_observed": False,
                "production_database_observed": False,
            },
            "runtime_route_map": routes,
            "schema_invariants": schema,
            "authentication_csrf_matrix": {
                "operation_count": len(OPERATIONS),
                "credential_mode_count_per_operation": 5,
                "case_count": len(auth_cases),
                "cases": auth_cases,
                "cases_sha256": sha256_json(auth_cases),
                "complete": True,
            },
            "request_response_database_parity": {
                "case_count": len(business_cases),
                "cases": business_cases,
                "cases_sha256": sha256_json(business_cases),
                "complete": True,
            },
            "duplicate_request_outcomes": {
                "semantic_group_count": len(duplicate_sequences),
                "sequences": duplicate_sequences,
                "sequences_sha256": sha256_json(duplicate_sequences),
                "complete": True,
            },
            "concurrent_request_outcomes": {
                "semantic_group_count": len(concurrent_outcomes),
                "cases": concurrent_outcomes,
                "cases_sha256": sha256_json(concurrent_outcomes),
                "complete": True,
            },
            "rate_limit_matrix": {
                "operation_count": len(rate_limits),
                "cases": rate_limits,
                "cases_sha256": sha256_json(rate_limits),
                "complete": True,
            },
            "rollback_retry_matrix": {
                "semantic_group_count": len(rollback_retry),
                "cases": rollback_retry,
                "cases_sha256": sha256_json(rollback_retry),
                "complete": True,
            },
            "legacy_defects_observed": [
                {
                    "defect_id": "study-raw-connection-sqlalchemy2",
                    "affected_route_ids": [
                        "bf3cb0c4f9ab",
                        "c797832c43db",
                        "278e1eac5eb4",
                    ],
                    "observation": (
                        "real routes return safe HTTP 500 before business DML "
                        "because Connection.execute receives a raw string and "
                        "positional tuple under SQLAlchemy 2"
                    ),
                    "silent_fix_forbidden": True,
                    "approved_difference_required": True,
                },
                {
                    "defect_id": "checkin-datetime-string-bind",
                    "affected_route_ids": ["59c9c7366ec3"],
                    "observation": (
                        "real route returns HTTP 500 and rolls back because a "
                        "formatted string is bound to a SQLAlchemy DateTime column"
                    ),
                    "silent_fix_forbidden": True,
                    "approved_difference_required": True,
                },
                {
                    "defect_id": "question-edit-swallowed-portable-update",
                    "affected_route_ids": ["624b5ac217d0"],
                    "observation": (
                        "real route attempts a raw positional UPDATE, swallows "
                        "the SQLAlchemy 2 exception, commits no question DML, "
                        "and returns HTTP 200 with unchanged data"
                    ),
                    "persistent_owner": "catalog",
                    "silent_fix_forbidden": True,
                    "approved_difference_required": True,
                },
            ],
            "closure": {
                "complete_fixed_commit_app_archive": True,
                "active_caller_attestation": True,
                "authentication_csrf_rate_matrix": True,
                "request_response_parity": True,
                "isolated_database_before_after_fingerprints": True,
                "sql_and_transaction_trace": True,
                "duplicate_and_concurrent_outcomes": True,
                "rollback_and_retry_boundaries": True,
                "golden_execution_complete": True,
                "implementation_authorized": False,
                "route_delta_authorized": False,
                "migration_status": "pending",
                "production_cutover": False,
                "next_gate": (
                    "independent golden successor contract and explicit "
                    "approved-difference decisions before implementation"
                ),
            },
            "provenance": {
                "capture_tool": {
                    "path": (
                        "tools/"
                        "capture_phase4c_learning_transaction_write_goldens.py"
                    ),
                    "sha256": hashlib.sha256(tool_payload).hexdigest(),
                    "size_bytes": len(tool_payload),
                },
                "capture_test": {
                    "path": (
                        "tools/"
                        "test_capture_phase4c_learning_transaction_write_goldens.py"
                    ),
                    "sha256": hashlib.sha256(test_payload).hexdigest(),
                    "size_bytes": len(test_payload),
                },
                "secrets_captured": False,
                "synthetic_identity_only": True,
            },
        }
        document["document_payload_sha256"] = document_payload_sha256(document)
        return document


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    rendered = render_document(document)
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_bytes() != rendered:
            raise SystemExit(f"transaction-write golden drifted: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
