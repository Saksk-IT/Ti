#!/usr/bin/env python3
"""Capture deterministic dual-route question-type goldens from pinned Flask source."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterator


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


FIXED_REQUEST_ID = "phase4a-question-type-golden-request"
ROUTES = {
    "modern": {
        "route_id": "e4cbe4d6bcc8",
        "path": "/admin/api/types",
        "legacy_handler": "admin.admin_api.get_question_types",
    },
    "legacy": {
        "route_id": "3a346cb29186",
        "path": "/admin/types",
        "legacy_handler": "admin.admin_api_legacy.get_question_types",
    },
}
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/utils/decorators.py",
    "app/core/utils/portable_question_format.py",
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
    "ordinary": 6101,
    "subject_admin": 6102,
    "administrator": 6103,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalized_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def question_rows(db: Any) -> list[list[Any]]:
    from sqlalchemy import text

    columns = ", ".join(QUESTION_COLUMNS)
    rows = db.session.execute(text(f"SELECT {columns} FROM questions ORDER BY id")).fetchall()
    return [[normalized_scalar(value) for value in row] for row in rows]


def question_fingerprint(db: Any) -> dict[str, Any]:
    rows = question_rows(db)
    return {
        "columns": list(QUESTION_COLUMNS),
        "row_count": len(rows),
        "sha256": sha256_json(rows),
    }


def normalized_sql(statement: Any) -> str:
    return " ".join(str(statement).split()).upper()


def is_question_type_select(statement: Any) -> bool:
    sql = normalized_sql(statement)
    return sql.startswith("SELECT DISTINCT ") and " FROM QUESTIONS" in sql


@contextmanager
def catalog_sql_probe(engine: Any, *, fail: bool) -> Iterator[dict[str, int]]:
    from sqlalchemy import event

    counters = {"select_attempts": 0, "writes": 0}

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        _parameters: Any,
        _context: Any,
        _executemany: Any,
    ) -> None:
        sql = normalized_sql(statement)
        if is_question_type_select(statement):
            counters["select_attempts"] += 1
            if fail:
                raise RuntimeError("synthetic question-type SELECT failure")
        if sql.startswith(("INSERT INTO QUESTIONS", "UPDATE QUESTIONS", "DELETE FROM QUESTIONS")):
            counters["writes"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield counters
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def replace_question_types(db: Any, Question: Any, values: list[str]) -> None:
    db.session.query(Question).delete(synchronize_session=False)
    for offset, value in enumerate(values):
        db.session.add(Question(
            id=6300 + offset,
            subject_id=6201,
            type=value,
            content=f"Synthetic question type row {offset}",
            options="[]",
            answer="[]",
            analysis=None,
            tags="[]",
            difficulty=1,
            image_path=None,
            source="phase4a-question-type-golden",
            created_by=6103,
            updated_by=6103,
            created_at=datetime(2026, 7, 16, 8, 0, offset % 60),
            updated_at=datetime(2026, 7, 16, 8, 0, offset % 60),
        ))
    db.session.commit()


def set_actor_session(client: Any, actor: str | None) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        user_id = ACTORS[actor]
        session.update({
            "user_id": user_id,
            "username": f"phase4a_{actor}",
            "session_version": 7,
            "is_admin": actor == "administrator",
            "is_subject_admin": actor == "subject_admin",
            "is_notification_admin": False,
        })


def normalized_response(response: Any) -> dict[str, Any]:
    content_type = response.headers.get("Content-Type", "")
    payload = response.get_json(silent=True)
    body: Any = payload if payload is not None else response.get_data(as_text=True)
    return {
        "status": response.status_code,
        "headers": {
            name: response.headers[name]
            for name in ("Content-Type", "Location", "Vary")
            if name in response.headers
        },
        "body": body,
        "body_sha256": hashlib.sha256(response.get_data()).hexdigest(),
        "mimetype": response.mimetype,
        "content_type": content_type,
    }


def recorded_headers(*, bearer: bool, accept: str) -> dict[str, str]:
    headers = {"Accept": accept, "X-Request-ID": FIXED_REQUEST_ID}
    if bearer:
        headers["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    return headers


def live_headers(*, token: str | None, accept: str) -> dict[str, str]:
    headers = {"Accept": accept, "X-Request-ID": FIXED_REQUEST_ID}
    if token is not None:
        headers["Authorization"] = "Bearer" + " " + token
    return headers


def capture_case(
    client: Any,
    db: Any,
    *,
    case_id: str,
    route_name: str,
    actor: str | None,
    token: str | None,
    accept: str = "*/*",
    fail_select: bool = False,
) -> dict[str, Any]:
    route = ROUTES[route_name]
    set_actor_session(client, actor)
    registered_limiters = client.application.extensions.get("limiter", set())
    for limiter in registered_limiters:
        limiter.reset()
    before = question_fingerprint(db)
    address_digest = hashlib.sha256(case_id.encode("utf-8")).digest()
    remote_address = f"198.51.{address_digest[0]}.{address_digest[1]}"
    with catalog_sql_probe(db.engine, fail=fail_select) as sql:
        response = client.get(
            route["path"],
            headers=live_headers(token=token, accept=accept),
            environ_overrides={"REMOTE_ADDR": remote_address},
            follow_redirects=False,
        )
    try:
        db.session.rollback()
    except Exception:
        db.session.remove()
    after = question_fingerprint(db)
    return {
        "case_id": case_id,
        "route": route_name,
        "route_id": route["route_id"],
        "actor": actor or "anonymous",
        "credential_mode": (
            "session+valid_bearer"
            if actor is not None and token is not None
            else "valid_bearer_only"
            if token is not None
            else "session"
            if actor is not None
            else "none"
        ),
        "request": {
            "method": "GET",
            "path": route["path"],
            "headers": recorded_headers(bearer=token is not None, accept=accept),
        },
        "response": normalized_response(response),
        "catalog_effects": {
            "question_type_select_attempts": sql["select_attempts"],
            "question_write_statements": sql["writes"],
            "questions_before": before,
            "questions_after": after,
            "questions_unchanged": before == after,
        },
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


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(by_id) != len(cases):
        raise AssertionError("duplicate golden case ID")
    if not all(case["catalog_effects"]["questions_unchanged"] for case in cases):
        raise AssertionError("a GET changed catalog question facts")
    if not all(case["catalog_effects"]["question_write_statements"] == 0 for case in cases):
        raise AssertionError("a GET attempted a questions write")

    expected_success = ["判断题", "填空题", "多选题", "简答题", "选择题"]
    for route in ROUTES:
        if by_id[f"populated-admin-{route}"]["response"]["body"] != expected_success:
            raise AssertionError(f"{route} populated label order drifted")
        if by_id[f"empty-admin-{route}"]["response"]["body"] != []:
            raise AssertionError(f"{route} empty result drifted")
        if by_id[f"anonymous-{route}"]["response"]["status"] != 302:
            raise AssertionError(f"{route} anonymous status drifted")
        if by_id[f"bearer-only-{route}"]["response"]["status"] != 302:
            raise AssertionError(f"{route} bearer-only status drifted")
        if by_id[f"session-plus-bearer-{route}"]["response"]["status"] != 302:
            raise AssertionError(f"{route} session+bearer status drifted")
        if by_id[f"fault-html-{route}"]["catalog_effects"]["question_type_select_attempts"] != 1:
            raise AssertionError(f"{route} fault did not attempt exactly one catalog SELECT")
        if by_id[f"fault-json-{route}"]["catalog_effects"]["question_type_select_attempts"] != 1:
            observed = by_id[f"fault-json-{route}"]
            raise AssertionError(
                f"{route} JSON fault did not attempt exactly one catalog SELECT: "
                f"status={observed['response']['status']} effects={observed['catalog_effects']}"
            )

    if by_id["subject-admin-modern"]["response"]["status"] != 403:
        raise AssertionError("modern subject-admin auth drifted")
    if by_id["subject-admin-legacy"]["response"]["status"] != 200:
        raise AssertionError("legacy subject-admin auth drifted")
    if by_id["whitespace-admin-modern"]["response"]["body"] != []:
        raise AssertionError("modern whitespace behavior drifted")
    if by_id["whitespace-admin-legacy"]["response"]["body"] != ["简答题"]:
        raise AssertionError("legacy whitespace behavior drifted")
    if by_id["mixed-whitespace-admin-modern"]["response"]["body"] != ["选择题"]:
        raise AssertionError("modern mixed whitespace behavior drifted")
    if by_id["mixed-whitespace-admin-legacy"]["response"]["body"] != ["简答题", "选择题"]:
        raise AssertionError("legacy mixed whitespace behavior drifted")
    if by_id["fault-html-modern"]["response"]["status"] != 500:
        raise AssertionError("modern HTML fault status drifted")
    if by_id["fault-json-modern"]["response"]["status"] != 500:
        raise AssertionError("modern JSON fault status drifted")
    if by_id["fault-html-legacy"]["response"]["body"] != []:
        raise AssertionError("legacy HTML fault fallback drifted")
    if by_id["fault-json-legacy"]["response"]["body"] != []:
        raise AssertionError("legacy JSON fault fallback drifted")


def capture_document(legacy_root: Path) -> dict[str, Any]:
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "question_type_key_sources": key_source_attestation(archived),
        }
        with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-question-type-data-") as data_dir:
            os.environ["DATA_DIR"] = data_dir
            os.environ["FLASK_ENV"] = "testing"
            os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
            os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
            os.environ["JWT_USER_STATE_CACHE_TTL_SECONDS"] = "0"
            os.environ.pop("REDIS_URL", None)
            with pinned_source.archived_legacy_import_environment(archived.root):
                import app as legacy_app
                from app.core.extensions import db
                from app.core.utils.jwt_utils import generate_jwt_token
                from app.models.subject import Question, Subject
                from app.models.user import User

                pinned_source.assert_module_from_archive(legacy_app, archived.root)
                logging.disable(logging.CRITICAL)
                legacy_app._start_background_tasks = lambda _app: None
                app = legacy_app.create_app("testing")
                app.config.update(
                    JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                    PROPAGATE_EXCEPTIONS=False,
                    RATELIMIT_ENABLED=False,
                    TESTING=True,
                )

                with app.app_context():
                    db.create_all()
                    users = [
                        User(
                            id=user_id,
                            username=f"phase4a_{actor}",
                            email=f"phase4a_{actor}@test.example.com",
                            password_hash="public-test-only-password-hash",
                            has_password_set=True,
                            email_verified=True,
                            is_admin=actor == "administrator",
                            is_subject_admin=actor == "subject_admin",
                            is_notification_admin=False,
                            is_locked=False,
                            session_version=7,
                        )
                        for actor, user_id in ACTORS.items()
                    ]
                    db.session.add_all(users)
                    db.session.add(Subject(
                        id=6201,
                        name="题型证据科目",
                        description="public synthetic fixture",
                        is_locked=False,
                    ))
                    db.session.commit()
                    token = generate_jwt_token(
                        user_id=ACTORS["administrator"],
                        openid="",
                        session_version=7,
                    )
                    client = app.test_client()

                    canonical_and_alias_values = [
                        "single_choice", "single", " SINGLECHOICE ",
                        "multi_choice", "multi", "multiple", "MULTICHOICE",
                        "boolean", "bool", "judge", "true_false", "TRUEFALSE",
                        "fill", "fill_in_the_blank", "fill-in-the-blank", "fillblank",
                        "FILL_IN_THE_BLANK_QUESTION", "essay", "short_answer", "SHORTANSWER",
                        "unknown", "选择题", "\u00a0single\u00a0", "\u3000multi\u3000", "",
                        "single_choice",
                    ]
                    replace_question_types(db, Question, canonical_and_alias_values)
                    cases: list[dict[str, Any]] = []
                    for route in ROUTES:
                        cases.append(capture_case(
                            client, db,
                            case_id=f"populated-admin-{route}",
                            route_name=route,
                            actor="administrator",
                            token=None,
                        ))
                        cases.append(capture_case(
                            client, db,
                            case_id=f"subject-admin-{route}",
                            route_name=route,
                            actor="subject_admin",
                            token=None,
                        ))
                        cases.append(capture_case(
                            client, db,
                            case_id=f"ordinary-{route}",
                            route_name=route,
                            actor="ordinary",
                            token=None,
                        ))
                        cases.append(capture_case(
                            client, db,
                            case_id=f"anonymous-{route}",
                            route_name=route,
                            actor=None,
                            token=None,
                        ))
                        cases.append(capture_case(
                            client, db,
                            case_id=f"bearer-only-{route}",
                            route_name=route,
                            actor=None,
                            token=token,
                        ))
                        cases.append(capture_case(
                            client, db,
                            case_id=f"session-plus-bearer-{route}",
                            route_name=route,
                            actor="administrator",
                            token=token,
                        ))

                    replace_question_types(db, Question, [])
                    for route in ROUTES:
                        cases.append(capture_case(
                            client, db,
                            case_id=f"empty-admin-{route}",
                            route_name=route,
                            actor="administrator",
                            token=None,
                        ))

                    replace_question_types(db, Question, ["", "   ", "\u00a0", "\u3000"])
                    for route in ROUTES:
                        cases.append(capture_case(
                            client, db,
                            case_id=f"whitespace-admin-{route}",
                            route_name=route,
                            actor="administrator",
                            token=None,
                        ))

                    replace_question_types(
                        db, Question, ["single_choice", "", "   ", "\u00a0", "\u3000"])
                    for route in ROUTES:
                        cases.append(capture_case(
                            client, db,
                            case_id=f"mixed-whitespace-admin-{route}",
                            route_name=route,
                            actor="administrator",
                            token=None,
                        ))

                    replace_question_types(db, Question, ["single_choice"])
                    for route in ROUTES:
                        cases.append(capture_case(
                            client, db,
                            case_id=f"fault-html-{route}",
                            route_name=route,
                            actor="administrator",
                            token=None,
                            accept="*/*",
                            fail_select=True,
                        ))
                        cases.append(capture_case(
                            client, db,
                            case_id=f"fault-json-{route}",
                            route_name=route,
                            actor="administrator",
                            token=None,
                            accept="application/json",
                            fail_select=True,
                        ))

                    assert_case_contracts(cases)
                    return {
                        "contract_id": "ti.phase4a.question-type-read-goldens",
                        "schema_version": 1,
                        "captured_at": "2026-07-16",
                        "legacy_commit": pinned_source.LEGACY_COMMIT,
                        "legacy_source_attestation": source_attestation,
                        "route_status": {
                            "http_owner": "operations",
                            "migration_status": "pending",
                            "production_cutover": False,
                            "routes": list(ROUTES.values()),
                        },
                        "isolation": (
                            "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                            "no current working-tree legacy import and no persistent data"
                        ),
                        "case_isolation": (
                            "the global in-memory limiter is reset and a deterministic synthetic "
                            "remote address is assigned before each independent case; neither route "
                            "declares a route-specific limiter"
                        ),
                        "redaction": (
                            "synthetic identities only; valid JWT values omitted; fixed request ID"
                        ),
                        "case_count": len(cases),
                        "case_payload_sha256": sha256_json(cases),
                        "cases": cases,
                    }


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.resolve().write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"captured {document['case_count']} question-type cases "
        f"sha256={document['case_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
