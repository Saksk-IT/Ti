#!/usr/bin/env python3
"""Capture deterministic dual-route question-detail goldens from pinned Flask source."""

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


FIXED_REQUEST_ID = "phase4a-question-detail-golden-request"
ROUTES = {
    "modern": {
        "route_id": "8cb323acac12",
        "path_template": "/admin/api/questions/{question_id}",
        "route_template": "/admin/api/questions/<int:question_id>",
        "legacy_handler": "admin.admin_api.get_single_question",
    },
    "legacy": {
        "route_id": "d7d727b88aea",
        "path_template": "/admin/questions/{question_id}",
        "route_template": "/admin/questions/<int:question_id>",
        "legacy_handler": "admin.admin_api_legacy.get_single_question",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/core/utils/image_helpers.py",
    "app/core/utils/portable_question_format.py",
    "app/core/utils/pqf_rows.py",
    "app/models/subject.py",
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
ACTORS = {
    "ordinary": 8101,
    "subject_admin": 8102,
    "administrator": 8103,
}
SUBJECT_ID = 8201
QUESTIONS = {
    "zero": 0,
    "single": 8301,
    "multi": 8302,
    "boolean": 8303,
    "fill": 8304,
    "essay_nulls": 8305,
    "malformed_json": 8306,
    "grouped_images": 8307,
    "unknown_type": 8308,
}


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str
    raw_question_id: str
    session_actor: str | None = "administrator"
    bearer_actor: str | None = None
    accept: str = "*/*"
    fail_detail_select: bool = False
    expected_status: int = 200


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        specs.extend((
            CaseSpec(f"auth-administrator-{route}", route, str(QUESTIONS["single"])),
            CaseSpec(
                f"auth-subject-admin-{route}", route, str(QUESTIONS["single"]),
                session_actor="subject_admin",
            ),
            CaseSpec(
                f"auth-ordinary-{route}", route, str(QUESTIONS["single"]),
                session_actor="ordinary", expected_status=403,
            ),
            CaseSpec(
                f"auth-anonymous-{route}", route, str(QUESTIONS["single"]),
                session_actor=None, expected_status=302,
            ),
            CaseSpec(
                f"auth-bearer-only-{route}", route, str(QUESTIONS["single"]),
                session_actor=None, bearer_actor="administrator", expected_status=302,
            ),
            CaseSpec(
                f"auth-ordinary-session-plus-bearer-{route}", route,
                str(QUESTIONS["single"]), session_actor="ordinary",
                bearer_actor="administrator", expected_status=302,
            ),
        ))
        for fixture_name in (
            "single",
            "multi",
            "boolean",
            "fill",
            "essay_nulls",
            "malformed_json",
            "grouped_images",
            "unknown_type",
        ):
            specs.append(CaseSpec(
                f"data-{fixture_name.replace('_', '-')}-{route}",
                route,
                str(QUESTIONS[fixture_name]),
            ))
        specs.extend((
            CaseSpec(f"id-zero-{route}", route, str(QUESTIONS["zero"])),
            CaseSpec(f"id-unicode-digits-{route}", route, "٨٣٠١"),
            CaseSpec(f"id-leading-zero-{route}", route, "00008301"),
            CaseSpec(
                f"id-not-found-{route}", route, "8999",
                accept="application/json", expected_status=404,
            ),
            CaseSpec(
                f"id-huge-signed-64-{route}", route, "9223372036854775807",
                accept="application/json", expected_status=404,
            ),
            CaseSpec(
                f"id-overflow-{route}", route, "9223372036854775808",
                accept="application/json", expected_status=500,
            ),
            CaseSpec(
                f"id-negative-{route}", route, "-1",
                expected_status=404,
            ),
            CaseSpec(
                f"fault-html-{route}", route, str(QUESTIONS["single"]),
                fail_detail_select=True, expected_status=500,
            ),
            CaseSpec(
                f"fault-json-{route}", route, str(QUESTIONS["single"]),
                accept="application/json", fail_detail_select=True,
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


def is_question_detail_select(statement: Any) -> bool:
    sql = re.sub(r"\s*=\s*", "=", normalized_sql(statement))
    return sql.startswith("SELECT * FROM QUESTIONS WHERE ID=")


def is_select_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith(("SELECT ", "WITH "))


def is_dml_statement(statement: Any) -> bool:
    return normalized_sql(statement).startswith(("INSERT ", "UPDATE ", "DELETE ", "REPLACE "))


def is_question_dml(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return sql.startswith((
        "INSERT INTO QUESTIONS",
        "UPDATE QUESTIONS",
        "DELETE FROM QUESTIONS",
        "REPLACE INTO QUESTIONS",
    ))


@contextmanager
def sql_probe(engine: Any, *, fail_detail_select: bool) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event

    ledger: dict[str, Any] = {
        "statements": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "question_detail_select_attempts": 0,
        "question_dml_attempts": 0,
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
        detail = is_question_detail_select(statement)
        question_write = is_question_dml(statement)
        ledger["statements"].append({
            "sql": normalized,
            "parameters": normalized_value(parameters),
            "executemany": bool(executemany),
            "classification": (
                "question_detail_select" if detail
                else "question_dml" if question_write
                else "select" if select
                else "dml" if dml
                else "other"
            ),
        })
        ledger["select_attempts"] += int(select)
        ledger["dml_attempts"] += int(dml)
        ledger["question_detail_select_attempts"] += int(detail)
        ledger["question_dml_attempts"] += int(question_write)
        if detail and fail_detail_select:
            raise RuntimeError("synthetic question-detail SELECT failure")

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield ledger
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        ledger["statement_count"] = len(ledger["statements"])
        ledger["statements_sha256"] = sha256_json(ledger["statements"])


def question_rows(db: Any) -> list[list[Any]]:
    from sqlalchemy import text

    rows = db.session.execute(text(
        f"SELECT {', '.join(QUESTION_COLUMNS)} FROM questions ORDER BY id"
    )).fetchall()
    return [
        [normalized_value(value) for value in row]
        for row in rows
    ]


def question_fingerprint(db: Any) -> dict[str, Any]:
    rows = question_rows(db)
    return {
        "columns": list(QUESTION_COLUMNS),
        "column_count": len(QUESTION_COLUMNS),
        "row_count": len(rows),
        "rows_sha256": sha256_json(rows),
    }


def matrix_attestation() -> dict[str, Any]:
    payload = MATRIX.read_bytes()
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
    route_ids = {route["route_id"] for route in ROUTES.values()}
    selected = [row for row in rows if row["route_id"] in route_ids]
    if {row["route_id"] for row in selected} != route_ids:
        raise AssertionError("question-detail routes are missing from the frozen route matrix")
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
        "subject_id": SUBJECT_ID,
        "analysis": "固定解析",
        "tags": compact_json(["phase4a"]),
        "difficulty": 2,
        "image_path": None,
        "source": "phase4a-question-detail-golden",
        "created_by": ACTORS["administrator"],
        "updated_by": ACTORS["administrator"],
        "created_at": fixed,
        "updated_at": fixed,
    }

    def row(question_id: int, q_type: str, content: str, options: Any, answer: Any, **extra: Any) -> dict[str, Any]:
        result = {
            **base,
            "id": question_id,
            "type": q_type,
            "content": content,
            "options": (
                options if options is None or isinstance(options, str) else compact_json(options)
            ),
            "answer": (
                answer if answer is None or isinstance(answer, str) else compact_json(answer)
            ),
        }
        result.update(extra)
        return result

    return [
        row(QUESTIONS["zero"], "single_choice", "零号题", ["零", "壹"], [0]),
        row(
            QUESTIONS["single"], "single_choice", "单选：请选择 Beta",
            ["Alpha", "Beta", "Gamma"], [1], tags=compact_json(["数学", "核心"]),
            image_path="/uploads/questions/single.png",
        ),
        row(
            QUESTIONS["multi"], "multi_choice", "多选：请选择红和蓝",
            ["红", "绿", "蓝"], [2, 0, 2], difficulty=5,
        ),
        row(
            QUESTIONS["boolean"], "boolean", "判断：天空是蓝色", [], [True],
            analysis="判断题解析",
        ),
        row(
            QUESTIONS["fill"], "fill", "甲{1}乙{0}丙", [], [["零", "0"], ["一"]],
            analysis="填空占位顺序解析",
        ),
        row(
            QUESTIONS["essay_nulls"], "essay", "可空字段简答题", None, None,
            analysis=None, tags=None, difficulty=None,
            image_path=None, source=None, created_by=None, updated_by=None,
            created_at=None, updated_at=None,
        ),
        row(
            QUESTIONS["malformed_json"], "single_choice", "JSON 损坏题",
            "[broken-options", "{broken-answer", tags="[broken-tags",
            image_path="not-json-image",
        ),
        row(
            QUESTIONS["grouped_images"], "single_choice", "图片分组题", ["甲", "乙"], [0],
            image_path=compact_json({
                "content": [
                    "/uploads/questions/stem.png",
                    "uploads/questions/stem.png",
                    " questions/extra.png ",
                ],
                "answer": ["/uploads/questions/answer.png"],
                "explanation": ["uploads/questions/explain.png"],
            }),
        ),
        row(
            QUESTIONS["unknown_type"], "mystery_case", "未知题型", ["Uno", "Dos"], [1],
            analysis="未知类型解析",
        ),
    ]


def seed_fixture(db: Any, User: Any, Subject: Any) -> dict[str, Any]:
    from sqlalchemy import text

    fixed = datetime(2026, 7, 16, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4a_detail_{actor}",
            email=f"phase4a_detail_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=actor == "administrator",
            is_subject_admin=actor == "subject_admin",
            is_notification_admin=False,
            is_locked=False,
            session_version=7,
            created_at=fixed,
        ))
    db.session.add(Subject(
        id=SUBJECT_ID,
        name="题目详情证据科目",
        description="public synthetic fixture",
        is_locked=False,
        created_at=fixed,
    ))
    db.session.flush()
    rows = fixture_rows()
    db.session.execute(text(
        "INSERT INTO questions "
        f"({', '.join(QUESTION_COLUMNS)}) VALUES "
        f"({', '.join(':' + column for column in QUESTION_COLUMNS)})"
    ), rows)
    db.session.commit()
    return question_fingerprint(db)


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4a_detail_{actor}",
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
    tokens: dict[str, str],
    spec: CaseSpec,
) -> dict[str, Any]:
    route = ROUTES[spec.route]
    path = route["path_template"].format(question_id=spec.raw_question_id)
    set_actor_session(client, spec.session_actor)
    reset_limiters(client.application)
    with client.application.app_context():
        before = question_fingerprint(db)
        engine = db.engine
        db.session.remove()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    with sql_probe(engine, fail_detail_select=spec.fail_detail_select) as sql:
        response = client.get(
            path,
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
        db.session.remove()
    try:
        parsed_id: int | None = int(spec.raw_question_id)
    except ValueError:
        parsed_id = None
    return {
        "case_id": spec.case_id,
        "route": spec.route,
        "route_id": route["route_id"],
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or "none",
        "credential_mode": credential_mode(spec),
        "request": {
            "method": "GET",
            "path": path,
            "route_template": route["route_template"],
            "path_parameter": {
                "name": "question_id",
                "raw_text": spec.raw_question_id,
                "python_int_value": parsed_id,
            },
            "query": [],
            "headers": recorded_request_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "response": normalized_response(response),
        "observed_get_effects": {
            "sql": sql,
            "questions_before": before,
            "questions_after": after,
            "questions_unchanged": before == after,
        },
    }


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(by_id) != len(CASE_SPECS) or len(cases) != len(CASE_SPECS):
        raise AssertionError("question-detail case set drifted or contains duplicates")
    for spec in CASE_SPECS:
        case = by_id[spec.case_id]
        response = case["response"]
        effects = case["observed_get_effects"]
        if response["status"] != spec.expected_status:
            raise AssertionError(
                f"{spec.case_id} status drifted: expected={spec.expected_status} "
                f"observed={response['status']} body={response['body']}"
            )
        if not effects["questions_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed a question fact")
        if effects["sql"]["question_dml_attempts"] != 0:
            raise AssertionError(f"{spec.case_id} attempted questions DML")
        if effects["questions_before"]["column_count"] != 15:
            raise AssertionError(f"{spec.case_id} lost the 15-column fingerprint")

    for route in ROUTES:
        for actor in ("administrator", "subject-admin"):
            case = by_id[f"auth-{actor}-{route}"]
            if case["observed_get_effects"]["sql"]["question_detail_select_attempts"] != 1:
                raise AssertionError(f"{case['case_id']} did not read one question row")
        for scenario in (
            "ordinary",
            "anonymous",
            "bearer-only",
            "ordinary-session-plus-bearer",
        ):
            case = by_id[f"auth-{scenario}-{route}"]
            if case["observed_get_effects"]["sql"]["question_detail_select_attempts"] != 0:
                raise AssertionError(f"{case['case_id']} crossed the pre-query auth boundary")
        for fixture_name in (
            "single", "multi", "boolean", "fill", "essay-nulls",
            "malformed-json", "grouped-images", "unknown-type",
        ):
            case = by_id[f"data-{fixture_name}-{route}"]
            if case["observed_get_effects"]["sql"]["question_detail_select_attempts"] != 1:
                raise AssertionError(f"{case['case_id']} did not execute exactly one detail SELECT")
        for edge in ("zero", "unicode-digits", "leading-zero", "not-found", "huge-signed-64", "overflow"):
            case = by_id[f"id-{edge}-{route}"]
            if case["observed_get_effects"]["sql"]["question_detail_select_attempts"] != 1:
                raise AssertionError(f"{case['case_id']} query count drifted")
        negative = by_id[f"id-negative-{route}"]
        if negative["observed_get_effects"]["sql"]["question_detail_select_attempts"] != 0:
            raise AssertionError(f"{negative['case_id']} unexpectedly matched the Flask int route")
        for mode in ("html", "json"):
            failure = by_id[f"fault-{mode}-{route}"]
            if failure["observed_get_effects"]["sql"]["question_detail_select_attempts"] != 1:
                raise AssertionError(f"{failure['case_id']} did not attempt the injected SELECT")

    modern = by_id["data-grouped-images-modern"]["response"]["body"]
    legacy = by_id["data-grouped-images-legacy"]["response"]["body"]
    if not isinstance(modern.get("image_path"), str) or not modern["image_path"].startswith("["):
        raise AssertionError("modern grouped-image compatibility wrapper drifted")
    if legacy.get("content_images") != ["questions/stem.png", "questions/extra.png"]:
        raise AssertionError("legacy grouped-image normalization drifted")
    if "portable_type" in by_id["data-single-modern"]["response"]["body"]:
        raise AssertionError("modern route unexpectedly exposed portable fields")
    if by_id["data-single-legacy"]["response"]["body"].get("portable_type") != "single_choice":
        raise AssertionError("legacy portable projection drifted")


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
            "question_detail_key_sources": key_source_attestation(archived),
        }
        with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-question-detail-data-") as data_dir:
            with capture_environment(data_dir):
                with pinned_source.archived_legacy_import_environment(archived.root):
                    import app as legacy_app
                    from app.core.extensions import db
                    from app.core.utils.jwt_utils import generate_jwt_token
                    from app.models.subject import Subject
                    from app.models.user import User

                    pinned_source.assert_module_from_archive(legacy_app, archived.root)
                    previous_logging = logging.root.manager.disable
                    logging.disable(logging.CRITICAL)
                    legacy_app._start_background_tasks = lambda _app: None
                    app = legacy_app.create_app("testing")
                    app.config.update(
                        JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                        PROPAGATE_EXCEPTIONS=False,
                        RATELIMIT_ENABLED=False,
                        TESTING=True,
                    )
                    try:
                        with app.app_context():
                            db.create_all()
                            fixture_fingerprint = seed_fixture(db, User, Subject)
                            tokens = {
                                actor: generate_jwt_token(
                                    user_id=user_id, openid="", session_version=7,
                                )
                                for actor, user_id in ACTORS.items()
                            }
                            db.session.remove()
                        for user_id in ACTORS.values():
                            legacy_app._should_update_last_active(user_id, 60)
                        client = app.test_client()
                        cases = [
                            capture_case(client, db, tokens, spec)
                            for spec in CASE_SPECS
                        ]
                        assert_case_contracts(cases)
                    finally:
                        logging.disable(previous_logging)
                        with app.app_context():
                            db.session.remove()

        return {
            "contract_id": "ti.phase4a.question-detail-read-goldens",
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
                "capability": "read one immutable question fact row by numeric id",
                "table": "questions",
                "columns": list(QUESTION_COLUMNS),
                "column_count": len(QUESTION_COLUMNS),
                "legacy_sql": "SELECT * FROM questions WHERE id=:qid",
                "http_projection_owner": "operations until auth and payload parity are migrated",
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory limiter; no current working-tree legacy import or persistent data"
            ),
            "case_isolation": (
                "every request gets a fresh explicit Session scenario, reset limiter, deterministic "
                "remote address, pre/post 15-column questions fingerprint, and isolated SQL ledger; "
                "last-active throttles are primed outside every request ledger"
            ),
            "response_capture": (
                "full response body text and parsed body, body length/hash, and every test-client "
                "response header; session cookies are redacted and wall-clock limiter headers "
                "are represented by explicit deterministic placeholders"
            ),
            "redaction": (
                "synthetic identities only; JWT and session-cookie values omitted; fixed request ID"
            ),
            "fixture": {
                "actors": ACTORS,
                "subject_id": SUBJECT_ID,
                "questions": QUESTIONS,
                "questions_fingerprint": fixture_fingerprint,
            },
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
        f"captured {document['case_count']} question-detail cases "
        f"sha256={document['case_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
