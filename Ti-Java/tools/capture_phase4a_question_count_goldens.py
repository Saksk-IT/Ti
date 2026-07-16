#!/usr/bin/env python3
"""Capture deterministic question-count goldens from the pinned Flask app."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import csv
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


FIXED_REQUEST_ID = "phase4a-question-count-golden-request"
ROUTES = {
    "alias": {
        "route_id": "c618fb5f9f97",
        "path": "/api/questions/count",
        "endpoint": "api_questions_count",
        "registration": "app/modules/quiz/__init__.py::add_url_rule",
    },
    "blueprint": {
        "route_id": "bb21e7730d04",
        "path": "/api/quiz/questions/count",
        "endpoint": "quiz_api.api_questions_count",
        "registration": "app/modules/quiz/routes/api_components/core_counts.py:34",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/cache_utils.py",
    "app/core/utils/portable_question_format.py",
    "app/core/utils/rate_limit.py",
    "app/core/utils/redis_utils.py",
    "app/core/utils/subject_permissions.py",
    "app/core/utils/user_question_tags.py",
    "app/modules/quiz/__init__.py",
    "app/modules/quiz/routes/api.py",
    "app/modules/quiz/routes/api_shared.py",
    "app/modules/quiz/routes/api_components/core.py",
    "app/modules/quiz/routes/api_components/core_counts.py",
    "app/modules/quiz/services/question_tags_service.py",
)
ACTORS = {"ordinary": 7101, "administrator": 7102, "legacy_tags": 7103}
SUBJECTS = {"open_a": 7201, "open_b": 7202, "locked": 7203, "empty": 7204}
QUESTIONS = {
    "a_single": 7301,
    "a_multi": 7302,
    "a_essay": 7303,
    "b_boolean": 7304,
    "locked_fill": 7305,
    "null_essay": 7306,
}
ACCESSIBLE_SUBJECTS = {
    "ordinary": (7201, 7203, 7204),
    "legacy_tags": (7201, 7203, 7204),
    "administrator": (7201, 7202, 7203, 7204),
}
FAVORITES = {"ordinary": {7301, 7304, 7305, 7306}}
MISTAKES = {"ordinary": {7302, 7303, 7304}}
TAGS = {
    ("ordinary", "重点"): {7301, 7302, 7304},
    ("legacy_tags", "旧标"): {7303},
}
TABLE_ORDER = {
    "users": "id",
    "subjects": "id",
    "questions": "id",
    "user_subjects": "id",
    "favorites": "id",
    "mistakes": "id",
    "user_progress": "id",
    "user_question_tag_items": "user_id, scope, scope_id, question_id, tag",
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    actor: str | None
    query: tuple[tuple[str, str], ...] = ()
    expected_status: int = 200
    expected_count: int | None = None
    expected_message: str | None = None
    fail_count_select: bool = False
    invalid_bearer: bool = False
    session_actor: str | None = None
    bearer_actor: str | None = None
    session_only: bool = False


CASE_SPECS = (
    CaseSpec("alias-anonymous-default", "alias", None, expected_count=5),
    CaseSpec("blueprint-anonymous-default", "blueprint", None, expected_status=401, expected_message="请先登录"),
    CaseSpec("alias-ordinary-default", "alias", "ordinary", expected_count=3),
    CaseSpec("blueprint-ordinary-default", "blueprint", "ordinary", expected_count=3),
    CaseSpec("alias-administrator-default", "alias", "administrator", expected_count=4),
    CaseSpec("blueprint-administrator-default", "blueprint", "administrator", expected_count=4),
    CaseSpec("alias-anonymous-open-b", "alias", None, (("subject", "开放乙"),), expected_count=1),
    CaseSpec("alias-ordinary-restricted-b", "alias", "ordinary", (("subject", "开放乙"),), expected_count=0),
    CaseSpec("blueprint-administrator-open-b", "blueprint", "administrator", (("subject", "开放乙"),), expected_count=1),
    CaseSpec("alias-anonymous-locked", "alias", None, (("subject", "锁定科目"),), expected_count=0),
    CaseSpec("blueprint-administrator-locked", "blueprint", "administrator", (("subject", "锁定科目"),), expected_count=0),
    CaseSpec("alias-ordinary-type-chinese", "alias", "ordinary", (("type", "选择题"),), expected_count=1),
    CaseSpec("blueprint-ordinary-type-chinese", "blueprint", "ordinary", (("type", "选择题"),), expected_count=1),
    CaseSpec("alias-anonymous-type-unknown", "alias", None, (("type", "unknown"),), expected_count=2),
    CaseSpec("blueprint-administrator-type-upper-all", "blueprint", "administrator", (("type", "ALL"),), expected_count=1),
    CaseSpec("blueprint-ordinary-candidate", "blueprint", "ordinary", (("subject", "开放甲"), ("type", "single")), expected_count=1),
    CaseSpec("alias-ordinary-favorites", "alias", "ordinary", (("source", "favorites"),), expected_count=1),
    CaseSpec("blueprint-ordinary-favorites", "blueprint", "ordinary", (("source", "favorites"),), expected_count=1),
    CaseSpec("alias-ordinary-mistakes", "alias", "ordinary", (("source", "mistakes"),), expected_count=2),
    CaseSpec("blueprint-ordinary-mistakes", "blueprint", "ordinary", (("mode", "mistakes"),), expected_count=2),
    CaseSpec("alias-ordinary-tag", "alias", "ordinary", (("tag", "重点"),), expected_count=2),
    CaseSpec("blueprint-ordinary-tag", "blueprint", "ordinary", (("tag", "重点"),), expected_count=2),
    CaseSpec("alias-legacy-tag-store", "alias", "legacy_tags", (("tag", "旧标"),), expected_count=0),
    CaseSpec("blueprint-legacy-tag-store", "blueprint", "legacy_tags", (("tag", "旧标"),), expected_count=0),
    CaseSpec("alias-anonymous-source-favorites", "alias", None, (("source", "favorites"),), expected_count=0),
    CaseSpec("blueprint-anonymous-source-favorites", "blueprint", None, (("source", "favorites"),), expected_status=401, expected_message="请先登录"),
    CaseSpec("alias-anonymous-mode-favorites", "alias", None, (("mode", "favorites"),), expected_status=401, expected_message="请先登录后使用此功能"),
    CaseSpec(
        "alias-source-over-mode", "alias", "ordinary",
        (("source", "favorites"), ("mode", "mistakes")),
        expected_count=1, session_actor="ordinary", session_only=True,
    ),
    CaseSpec("blueprint-source-over-mode", "blueprint", "ordinary", (("source", "favorites"), ("mode", "mistakes")), expected_count=1),
    CaseSpec("alias-duplicate-subject-first", "alias", "ordinary", (("subject", "开放甲"), ("subject", "开放乙")), expected_count=3),
    CaseSpec("blueprint-tag-upper-all", "blueprint", "ordinary", (("tag", "ALL"),), expected_count=3),
    CaseSpec("alias-invalid-bearer", "alias", None, expected_count=5, invalid_bearer=True),
    CaseSpec("blueprint-invalid-bearer", "blueprint", None, expected_status=401, expected_message="请先登录", invalid_bearer=True),
    CaseSpec(
        "blueprint-session-over-bearer", "blueprint", "administrator",
        expected_count=4, session_actor="administrator", bearer_actor="ordinary",
    ),
    CaseSpec("alias-count-failure", "alias", "ordinary", expected_status=500, expected_message="An unexpected server error occurred.", fail_count_select=True),
    CaseSpec("blueprint-count-failure", "blueprint", "ordinary", expected_status=500, expected_message="An unexpected server error occurred.", fail_count_select=True),
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


def render_document(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def normalized_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def normalized_sql(statement: Any) -> str:
    return " ".join(str(statement).split()).upper()


def first_arg(query: tuple[tuple[str, str], ...], name: str, default: str) -> str:
    return next((value for key, value in query if key == name), default)


def matrix_attestation() -> dict[str, Any]:
    payload = MATRIX.read_bytes()
    text = payload.decode("utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    selected = [row for row in rows if row["route_id"] in {r["route_id"] for r in ROUTES.values()}]
    if {row["route_id"] for row in selected} != {r["route_id"] for r in ROUTES.values()}:
        raise AssertionError("question-count routes are missing from the frozen route matrix")
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


def table_fingerprints(db: Any) -> dict[str, Any]:
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    result: dict[str, Any] = {}
    for table, order_by in TABLE_ORDER.items():
        columns = [column["name"] for column in inspector.get_columns(table)]
        rows = db.session.execute(text(f"SELECT * FROM {table} ORDER BY {order_by}")).fetchall()
        normalized = [[normalized_scalar(value) for value in row] for row in rows]
        result[table] = {
            "columns": columns,
            "row_count": len(normalized),
            "sha256": sha256_json(normalized),
        }
    return result


@contextmanager
def sql_probe(engine: Any, *, fail_count_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "question_count_select_attempts": 0,
        "catalog_selects": 0,
        "identity_selects": 0,
        "learning_selects": 0,
        "question_write_attempts": 0,
        "learning_data_write_attempts": 0,
        "tag_schema_ddl_attempts": 0,
    }

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        _parameters: Any,
        _context: Any,
        _executemany: Any,
    ) -> None:
        sql = normalized_sql(statement)
        ledger["statements"].append(sql)
        is_select = sql.startswith("SELECT")
        if is_select and "COUNT(1)" in sql and " FROM QUESTIONS " in sql:
            ledger["question_count_select_attempts"] += 1
            if fail_count_select:
                raise RuntimeError("synthetic question-count SELECT failure")
        if is_select and (" FROM QUESTIONS " in sql or " JOIN SUBJECTS " in sql or " FROM SUBJECTS " in sql):
            ledger["catalog_selects"] += 1
        if is_select and (" FROM USERS " in sql or " FROM USER_SUBJECTS " in sql):
            ledger["identity_selects"] += 1
        if is_select and any(f" {table} " in sql for table in ("FAVORITES", "MISTAKES", "USER_PROGRESS", "USER_QUESTION_TAG_ITEMS")):
            ledger["learning_selects"] += 1
        if sql.startswith(("INSERT INTO QUESTIONS", "UPDATE QUESTIONS", "DELETE FROM QUESTIONS")):
            ledger["question_write_attempts"] += 1
        if sql.startswith(("INSERT INTO USER_QUESTION_TAG_ITEMS", "UPDATE USER_QUESTION_TAG_ITEMS", "DELETE FROM USER_QUESTION_TAG_ITEMS")):
            ledger["learning_data_write_attempts"] += 1
        if sql.startswith(("CREATE TABLE", "CREATE INDEX")) and "USER_QUESTION_TAG_ITEMS" in sql:
            ledger["tag_schema_ddl_attempts"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield ledger
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        ledger["statement_count"] = len(ledger["statements"])
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


@contextmanager
def cache_probe(core_counts: Any, cache_utils: Any) -> Iterator[dict[str, Any]]:
    ledger: dict[str, Any] = {
        "version_get_keys": [],
        "version_set_attempts": [],
        "response_cache_get_keys": [],
        "response_cache_set_attempts": [],
    }
    originals = {
        "redis_get_text": cache_utils.redis_get_text,
        "redis_set_text": cache_utils.redis_set_text,
        "redis_get_json": core_counts.redis_get_json,
        "redis_set_json": core_counts.redis_set_json,
    }

    def get_text(key: str) -> Any:
        ledger["version_get_keys"].append(str(key))
        return originals["redis_get_text"](key)

    def set_text(key: str, value: str, ttl_seconds: int | None = None, *, nx: bool = False) -> Any:
        ledger["version_set_attempts"].append({
            "key": str(key), "value": str(value), "ttl_seconds": ttl_seconds, "nx": bool(nx),
        })
        return originals["redis_set_text"](key, value, ttl_seconds, nx=nx)

    def get_json(key: str) -> Any:
        ledger["response_cache_get_keys"].append(str(key))
        return originals["redis_get_json"](key)

    def set_json(key: str, value: Any, ttl_seconds: int | None = None) -> Any:
        ledger["response_cache_set_attempts"].append({
            "key": str(key), "payload": value, "ttl_seconds": ttl_seconds,
        })
        return originals["redis_set_json"](key, value, ttl_seconds=ttl_seconds)

    cache_utils.redis_get_text = get_text
    cache_utils.redis_set_text = set_text
    core_counts.redis_get_json = get_json
    core_counts.redis_set_json = set_json
    try:
        yield ledger
    finally:
        cache_utils.redis_get_text = originals["redis_get_text"]
        cache_utils.redis_set_text = originals["redis_set_text"]
        core_counts.redis_get_json = originals["redis_get_json"]
        core_counts.redis_set_json = originals["redis_set_json"]


def reset_limiters(app: Any) -> None:
    for limiter in app.extensions.get("limiter", set()):
        limiter.reset()


def candidate_question_ids(db: Any, actor: str | None, query: tuple[tuple[str, str], ...], convert_type: Any) -> list[int]:
    from sqlalchemy import text

    subject = first_arg(query, "subject", "all")
    q_type = first_arg(query, "type", "all")
    sql = (
        "SELECT q.id FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id "
        "WHERE (s.is_locked=false OR s.is_locked IS NULL)"
    )
    params: dict[str, Any] = {}
    if actor is not None:
        accessible = ACCESSIBLE_SUBJECTS[actor]
        names = []
        for index, subject_id in enumerate(accessible):
            key = f"asid_{index}"
            names.append(f":{key}")
            params[key] = subject_id
        sql += " AND q.subject_id IN (" + ", ".join(names) + ")"
    if subject != "all":
        sql += " AND s.name = :subject_name"
        params["subject_name"] = subject
    if q_type != "all":
        sql += " AND q.type = :q_type"
        params["q_type"] = convert_type(q_type)
    sql += " ORDER BY q.id"
    return [int(row[0]) for row in db.session.execute(text(sql), params).fetchall()]


def expected_result_ids(candidates: list[int], actor: str | None, query: tuple[tuple[str, str], ...]) -> list[int]:
    result = set(candidates)
    mode = first_arg(query, "mode", "").lower()
    source = first_arg(query, "source", "").lower()
    target = source if source in {"favorites", "mistakes"} else mode
    if target == "favorites":
        result &= FAVORITES.get(actor or "", set())
    elif target == "mistakes":
        result &= MISTAKES.get(actor or "", set())
    tag = first_arg(query, "tag", "").strip()
    if tag and tag.lower() != "all":
        tag = re.sub(r"\s+", " ", tag).strip()[:20].strip()
        result &= TAGS.get((actor or "", tag), set())
    return sorted(result)


def normalized_response(response: Any) -> dict[str, Any]:
    payload = response.get_json(silent=True)
    body: Any = payload if payload is not None else response.get_data(as_text=True)
    headers: dict[str, str] = {}
    for name in (
        "Content-Type", "Location", "Vary", "X-RateLimit-Limit",
        "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After",
    ):
        if name not in response.headers:
            continue
        headers[name] = (
            "<dynamic-epoch-second>" if name == "X-RateLimit-Reset"
            else "<dynamic-positive-seconds>" if name == "Retry-After"
            else response.headers[name]
        )
    return {
        "status": response.status_code,
        "headers": headers,
        "body": body,
        "body_sha256": hashlib.sha256(response.get_data()).hexdigest(),
    }


def capture_case(
    client: Any,
    db: Any,
    core_counts: Any,
    cache_utils: Any,
    convert_type: Any,
    tokens: dict[str, str],
    spec: CaseSpec,
) -> dict[str, Any]:
    route = ROUTES[spec.route]
    with client.session_transaction() as session:
        session.clear()
        if spec.session_actor is not None:
            session.update({
                "user_id": ACTORS[spec.session_actor],
                "username": f"phase4a_count_{spec.session_actor}",
                "session_version": 7,
                "is_admin": spec.session_actor == "administrator",
                "is_subject_admin": False,
                "is_notification_admin": False,
            })
    reset_limiters(client.application)
    with client.application.app_context():
        candidates = candidate_question_ids(db, spec.actor, spec.query, convert_type)
        expected_ids = expected_result_ids(candidates, spec.actor, spec.query)
        before = table_fingerprints(db)
        engine = db.engine
        db.session.remove()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    headers = {"Accept": "application/json", "X-Request-ID": FIXED_REQUEST_ID}
    if spec.invalid_bearer:
        headers["Authorization"] = "Bearer " + "invalid-synthetic-token"
    elif spec.actor is not None and not spec.session_only:
        headers["Authorization"] = "Bearer " + tokens[spec.bearer_actor or spec.actor]
    with cache_probe(core_counts, cache_utils) as cache, sql_probe(
        engine, fail_count_select=spec.fail_count_select
    ) as sql:
        response = client.get(
            route["path"],
            query_string=list(spec.query),
            headers=headers,
            environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
            follow_redirects=False,
        )
    with client.application.app_context():
        try:
            db.session.rollback()
        finally:
            db.session.remove()
        after = table_fingerprints(db)
        db.session.remove()
    return {
        "case_id": spec.case_id,
        "route": spec.route,
        "route_id": route["route_id"],
        "actor": spec.actor or "anonymous",
        "credential_mode": (
            "session+valid_bearer"
            if spec.session_actor is not None and spec.bearer_actor is not None
            else "session"
            if spec.session_only
            else "invalid_bearer"
            if spec.invalid_bearer
            else "valid_bearer"
            if spec.actor is not None
            else "none"
        ),
        "request": {
            "method": "GET",
            "path": route["path"],
            "path_with_query": route["path"] + (("?" + urlencode(spec.query)) if spec.query else ""),
            "query": [list(item) for item in spec.query],
            "headers": {
                "Accept": "application/json",
                "X-Request-ID": FIXED_REQUEST_ID,
                **(
                    {"Authorization": "Bearer <redacted-invalid-synthetic-token>"}
                    if spec.invalid_bearer
                    else {"Authorization": "Bearer <redacted-valid-synthetic-jwt>"}
                    if spec.actor and not spec.session_only
                    else {}
                ),
            },
        },
        "response": normalized_response(response),
        "catalog_primitive": {
            "candidate_question_ids": candidates,
            "candidate_count": len(candidates),
        },
        "future_learning_composition": {
            "expected_result_question_ids_if_authorized": expected_ids,
            "expected_count_if_authorized": len(expected_ids),
        },
        "observed_get_effects": {
            "route_limiter_consumed": "X-RateLimit-Limit" in response.headers,
            "sql": sql,
            "cache": cache,
            "tables_before": before,
            "tables_after": after,
            "tables_unchanged": before == after,
        },
    }


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(by_id) != len(CASE_SPECS) or len(by_id) != len(cases):
        raise AssertionError("question-count case set drifted or contains duplicates")
    for spec in CASE_SPECS:
        case = by_id[spec.case_id]
        response = case["response"]
        if response["status"] != spec.expected_status:
            raise AssertionError(f"{spec.case_id} status drifted: {response['status']}")
        body = response["body"]
        if spec.expected_count is not None:
            if body.get("status") != "success" or body.get("count") != spec.expected_count:
                raise AssertionError(f"{spec.case_id} count envelope drifted: {body}")
            if body.get("data") != {"count": spec.expected_count} or body.get("message") != "":
                raise AssertionError(f"{spec.case_id} normalized success envelope drifted")
        if spec.expected_message is not None and body.get("message") != spec.expected_message:
            raise AssertionError(f"{spec.case_id} message drifted: {body}")
        effects = case["observed_get_effects"]
        if not effects["tables_unchanged"]:
            raise AssertionError(f"{spec.case_id} persisted a table change")
        if effects["sql"]["question_write_attempts"] != 0:
            raise AssertionError(f"{spec.case_id} attempted a questions write")

    for route in ("alias", "blueprint"):
        legacy = by_id[f"{route}-legacy-tag-store"]["observed_get_effects"]["sql"]
        if legacy["learning_data_write_attempts"] != 0 or legacy["tag_schema_ddl_attempts"] == 0:
            raise AssertionError(f"{route} legacy-tag GET side effects drifted")
        failure = by_id[f"{route}-count-failure"]
        if failure["observed_get_effects"]["sql"]["question_count_select_attempts"] != 1:
            raise AssertionError(f"{route} fault did not attempt one count SELECT")
    for case_id in (
        "blueprint-anonymous-default",
        "blueprint-anonymous-source-favorites",
        "alias-anonymous-mode-favorites",
        "blueprint-invalid-bearer",
    ):
        effects = by_id[case_id]["observed_get_effects"]
        if effects["route_limiter_consumed"] or effects["sql"]["statement_count"] != 0:
            raise AssertionError(f"{case_id} did not stop before the view")


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


def seed_fixture(db: Any, models: dict[str, Any]) -> None:
    fixed = datetime(2026, 7, 16, 8, 0, 0)
    User = models["User"]
    Subject = models["Subject"]
    Question = models["Question"]
    UserSubject = models["UserSubject"]
    Favorite = models["Favorite"]
    Mistake = models["Mistake"]
    UserProgress = models["UserProgress"]
    UserQuestionTagItem = models["UserQuestionTagItem"]
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4a_count_{actor}",
            email=f"phase4a_count_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=actor == "administrator",
            is_subject_admin=False,
            is_notification_admin=False,
            is_locked=False,
            session_version=7,
            created_at=fixed,
        ))
    db.session.add_all([
        Subject(id=7201, name="开放甲", description="open A", is_locked=False, created_at=fixed),
        Subject(id=7202, name="开放乙", description="nullable lock", is_locked=False, created_at=fixed),
        Subject(id=7203, name="锁定科目", description="locked", is_locked=True, created_at=fixed),
        Subject(id=7204, name="空科目", description="empty", is_locked=False, created_at=fixed),
    ])
    types = {
        7301: (7201, "single_choice"), 7302: (7201, "multi_choice"),
        7303: (7201, "essay"), 7304: (7202, "boolean"),
        7305: (7203, "fill"), 7306: (None, "essay"),
    }
    for question_id, (subject_id, q_type) in types.items():
        db.session.add(Question(
            id=question_id, subject_id=subject_id, type=q_type,
            content=f"Synthetic question {question_id}", options="[]", answer="[]",
            analysis=None, tags="[]", difficulty=1, source="phase4a-question-count-golden",
            created_by=7102, updated_by=7102, created_at=fixed, updated_at=fixed,
        ))
    db.session.flush()
    db.session.execute(db.text("UPDATE subjects SET is_locked=NULL WHERE id=7202"))
    for offset, actor in enumerate(("ordinary", "legacy_tags"), start=1):
        db.session.add(UserSubject(
            id=7400 + offset, user_id=ACTORS[actor], subject_id=7202,
            restricted_by=7102, restricted_at=fixed,
        ))
    for offset, question_id in enumerate(sorted(FAVORITES["ordinary"]), start=1):
        db.session.add(Favorite(id=7500 + offset, user_id=7101, question_id=question_id, created_at=fixed))
    for offset, question_id in enumerate(sorted(MISTAKES["ordinary"]), start=1):
        db.session.add(Mistake(
            id=7600 + offset, user_id=7101, question_id=question_id,
            wrong_count=1, created_at=fixed, updated_at=fixed, last_updated=fixed,
        ))
    for question_id in sorted(TAGS[("ordinary", "重点")]):
        scope_id = 7201 if question_id in {7301, 7302} else 7202
        db.session.add(UserQuestionTagItem(
            user_id=7101, scope="question_center", scope_id=scope_id,
            question_id=question_id, tag="重点", created_at=fixed, updated_at=fixed,
        ))
    db.session.add(UserProgress(
        id=7701, user_id=7103, p_key="question_tags_v1",
        data=canonical_json({"version": 1, "tags": ["旧标"], "bindings": {"7303": ["旧标"]}}),
        created_at=fixed, updated_at=fixed,
    ))
    db.session.commit()


def capture_document(legacy_root: Path) -> dict[str, Any]:
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "question_count_key_sources": key_source_attestation(archived),
            "frozen_route_matrix": matrix_attestation(),
        }
        with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-question-count-data-") as data_dir, capture_environment(data_dir):
            with pinned_source.archived_legacy_import_environment(archived.root):
                import app as legacy_app
                from app.core.extensions import db
                from app.core.utils import cache_utils
                from app.core.utils.jwt_utils import generate_jwt_token
                from app.core.utils.portable_question_format import any_type_to_portable_type
                from app.models.quiz import Favorite, Mistake, UserProgress
                from app.models.subject import Question, Subject
                from app.models.system import UserQuestionTagItem, UserSubject
                from app.models.user import User
                from app.modules.quiz.routes.api_components import core_counts

                pinned_source.assert_module_from_archive(legacy_app, archived.root)
                previous_logging = logging.root.manager.disable
                logging.disable(logging.CRITICAL)
                legacy_app._start_background_tasks = lambda _app: None
                app = legacy_app.create_app("testing")
                app.config.update(
                    JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                    PROPAGATE_EXCEPTIONS=False,
                    QUIZ_API_CACHE_ENABLED=True,
                    QUIZ_CACHE_TTL_COUNTS_SECONDS=60,
                    RATELIMIT_ENABLED=True,
                    RATELIMIT_HEADERS_ENABLED=True,
                    TESTING=True,
                )
                try:
                    with app.app_context():
                        db.create_all()
                        seed_fixture(db, {
                            "User": User, "Subject": Subject, "Question": Question,
                            "UserSubject": UserSubject, "Favorite": Favorite, "Mistake": Mistake,
                            "UserProgress": UserProgress, "UserQuestionTagItem": UserQuestionTagItem,
                        })
                        fixture_fingerprints = table_fingerprints(db)
                        tokens = {
                            actor: generate_jwt_token(user_id=user_id, openid="", session_version=7)
                            for actor, user_id in ACTORS.items()
                        }
                    client = app.test_client()
                    for spec in CASE_SPECS:
                        if spec.session_only and spec.session_actor is not None:
                            legacy_app._should_update_last_active(ACTORS[spec.session_actor], 60)
                    cases = [
                        capture_case(
                            client, db, core_counts, cache_utils,
                            any_type_to_portable_type, tokens, spec,
                        )
                        for spec in CASE_SPECS
                    ]
                    assert_case_contracts(cases)
                finally:
                    logging.disable(previous_logging)
                    with app.app_context():
                        db.session.remove()

        return {
            "contract_id": "ti.phase4a.question-count-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-16",
            "legacy_commit": pinned_source.LEGACY_COMMIT,
            "legacy_source_attestation": source_attestation,
            "route_status": {
                "target_module_in_frozen_matrix": "catalog",
                "migration_status": "pending",
                "production_cutover": False,
                "routes": list(ROUTES.values()),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory Flask limiter; no current working-tree legacy import or persistent data"
            ),
            "fixture": {
                "actors": ACTORS,
                "subjects": SUBJECTS,
                "questions": QUESTIONS,
                "table_fingerprints": fixture_fingerprints,
            },
            "catalog_primitive_contract": {
                "candidate_order": "question id ascending for evidence only; HTTP returns a scalar count",
                "anonymous": "unlocked or NULL-lock subjects, including NULL subject_id",
                "authenticated": "same lock rule plus actor-accessible subject IDs; NULL subject_id excluded",
                "subject": "exact name match; only exact lowercase all disables the filter",
                "type": "only exact lowercase all disables the filter; otherwise legacy portable conversion applies",
                "learning_tables_required": False,
            },
            "future_learning_composition": {
                "owner": "learning",
                "facts": ["favorites", "mistakes", "user_question_tag_items", "user_progress"],
                "rule": "intersect catalog candidate IDs with actor-owned source and tag IDs",
                "route_auth_difference": (
                    "anonymous alias is public except mode favorites/mistakes; blueprint requires session or valid JWT"
                ),
                "legacy_tag_fallback_observation": {
                    "source": "app/modules/quiz/services/question_tags_service.py",
                    "source_sha256": source_attestation["question_count_key_sources"]
                        ["app/modules/quiz/services/question_tags_service.py"]["sha256"],
                    "intended_path": "read user_progress and lazily populate user_question_tag_items",
                    "captured_fixed_stack_result": (
                        "both routes return count 0; idempotent tag DDL is attempted; migration DML is not reached"
                    ),
                    "reason": (
                        "the legacy row['data'] access is caught by the fixed SQLAlchemy stack and becomes an empty store"
                    ),
                    "future_requirement": (
                        "do not treat this capture as positive lazy-migration evidence; learning must decide and test "
                        "the intended old-store compatibility explicitly"
                    ),
                },
            },
            "legacy_get_side_effect_facts": {
                "response_cache": "GET reads/initializes version keys and attempts a TTL response-cache write",
                "rate_limit": "the shared 60/minute;600/hour wrapper consumes endpoint-scoped runtime state after global auth",
                "tag_read": (
                    "GET executes idempotent tag-table DDL; the fixed-stack legacy user_progress row reader "
                    "does not reach migration DML in the captured fallback cases"
                ),
                "transaction": "the handler has no explicit commit; every case records post-rollback table fingerprints",
                "session": (
                    "the Session-only precedence case primes the in-memory last_active throttle before capture; "
                    "the mixed Session+Bearer case follows the valid-Bearer global-auth branch"
                ),
            },
            "redaction": "synthetic identities only; JWT values omitted; fixed request ID",
            "case_count": len(cases),
            "case_payload_sha256": sha256_json(cases),
            "cases": cases,
        }


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        f"captured {document['case_count']} question-count cases "
        f"sha256={document['case_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
