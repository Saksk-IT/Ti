#!/usr/bin/env python3
"""Capture deterministic Phase 4A subject-read contracts from isolated Flask state."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


sys.dont_write_bytecode = True

NONDETERMINISTIC_RESPONSE_KEYS = {"request_id", "trace_id", "correlation_id"}
FINGERPRINT_TABLES = (
    "users",
    "subjects",
    "questions",
    "user_subjects",
    "user_answers",
    "mistakes",
    "favorites",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def normalize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize_payload(child)
            for key, child in value.items()
            if str(key).lower() not in NONDETERMINISTIC_RESPONSE_KEYS
        }
    if isinstance(value, list):
        return [normalize_payload(child) for child in value]
    return value


def capture(
    client: Any,
    *,
    case_id: str,
    actor: str,
    path: str,
    authorization: str | None,
) -> dict[str, Any]:
    headers = {"Authorization": authorization} if authorization else {}
    response = client.get(path, headers=headers)
    payload = response.get_json(silent=True)
    if payload is None:
        raw = response.get_data(as_text=True)
        payload = {"body_excerpt": raw[:1000], "truncated": len(raw) > 1000}
    return {
        "case_id": case_id,
        "actor": actor,
        "request": {
            "method": "GET",
            "path": path,
            "headers": {"Authorization": "Bearer <redacted-test-jwt>"}
            if authorization
            else {},
        },
        "response": {
            "status": response.status_code,
            "headers": {
                name: (
                    "<dynamic-epoch-second>"
                    if name == "X-RateLimit-Reset"
                    else "<dynamic-positive-seconds>"
                    if name == "Retry-After"
                    else response.headers[name]
                )
                for name in (
                    "Content-Type",
                    "Cache-Control",
                    "Vary",
                    "X-RateLimit-Limit",
                    "X-RateLimit-Remaining",
                    "X-RateLimit-Reset",
                    "Retry-After",
                )
                if name in response.headers
            },
            "body": normalize_payload(payload),
        },
    }


def database_fingerprint(db: Any) -> dict[str, list[list[Any]]]:
    from sqlalchemy import text

    result: dict[str, list[list[Any]]] = {}
    for table in FINGERPRINT_TABLES:
        rows = db.session.execute(text(f"SELECT * FROM {table} ORDER BY id")).fetchall()
        result[table] = [
            [value.isoformat(sep=" ") if isinstance(value, datetime) else value for value in row]
            for row in rows
        ]
    return result


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    output = args.output.resolve()
    if not (legacy_root / "app" / "__init__.py").is_file():
        raise SystemExit(f"Not a Ti legacy root: {legacy_root}")

    with tempfile.TemporaryDirectory(prefix="ti-java-phase4a-subject-golden-") as data_dir:
        os.environ["DATA_DIR"] = data_dir
        os.environ["FLASK_ENV"] = "testing"
        os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
        os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
        os.environ.pop("REDIS_URL", None)
        sys.path.insert(0, str(legacy_root))
        os.chdir(legacy_root)

        from werkzeug.security import generate_password_hash

        import app as legacy_app
        from app.core.extensions import db
        from app.core.utils.jwt_utils import generate_jwt_token
        from app.models.quiz import Favorite, Mistake, UserAnswer
        from app.models.subject import Question, Subject
        from app.models.system import UserSubject
        from app.models.user import User

        logging.disable(logging.CRITICAL)
        legacy_app._start_background_tasks = lambda _app: None
        app = legacy_app.create_app("testing")
        app.config.update(
            QUIZ_API_CACHE_ENABLED=False,
            RATELIMIT_ENABLED=True,
            TESTING=True,
        )

        try:
            with app.app_context():
                db.create_all()
                ordinary = User(
                    id=4101,
                    username="phase4a_reader",
                    email="phase4a_reader@test.example.com",
                    password_hash=generate_password_hash("PUBLIC-TEST-ONLY-Phase4A!"),
                    has_password_set=True,
                    email_verified=True,
                    is_admin=False,
                    session_version=3,
                )
                administrator = User(
                    id=4102,
                    username="phase4a_admin",
                    email="phase4a_admin@test.example.com",
                    password_hash=generate_password_hash("PUBLIC-TEST-ONLY-Phase4A!"),
                    has_password_set=True,
                    email_verified=True,
                    is_admin=True,
                    session_version=5,
                )
                subjects = [
                    Subject(id=4201, name="算法基础", description="visible", is_locked=False),
                    Subject(id=4202, name="数据库系统", description=None, is_locked=None),
                    Subject(id=4203, name="锁定科目", description="locked", is_locked=True),
                    Subject(id=4204, name="受限科目", description="restricted", is_locked=False),
                ]
                db.session.add_all([ordinary, administrator, *subjects])
                db.session.flush()

                questions = [
                    Question(
                        id=4301,
                        subject_id=4201,
                        type="single_choice",
                        content="A",
                        options="[]",
                        answer="[]",
                        tags="[]",
                        difficulty=1,
                        created_by=4102,
                        updated_by=4102,
                    ),
                    Question(
                        id=4302,
                        subject_id=4201,
                        type="boolean",
                        content="B",
                        options="[]",
                        answer="[]",
                        tags="[]",
                        difficulty=1,
                        created_by=4102,
                        updated_by=4102,
                    ),
                    Question(
                        id=4303,
                        subject_id=4203,
                        type="fill",
                        content="C",
                        options="[]",
                        answer="[]",
                        tags="[]",
                        difficulty=1,
                        created_by=4102,
                        updated_by=4102,
                    ),
                    Question(
                        id=4304,
                        subject_id=4204,
                        type="essay",
                        content="D",
                        options="[]",
                        answer="[]",
                        tags="[]",
                        difficulty=1,
                        created_by=4102,
                        updated_by=4102,
                    ),
                ]
                db.session.add_all(questions)
                db.session.flush()
                db.session.add(
                    UserSubject(
                        id=4401,
                        user_id=4101,
                        subject_id=4204,
                        restricted_by=4102,
                        restricted_at=datetime(2026, 7, 15, 8, 0, 0),
                    )
                )
                db.session.add_all(
                    [
                        UserAnswer(
                            id=4501,
                            user_id=4101,
                            question_id=4301,
                            user_answer="A",
                            is_correct=True,
                            created_at=datetime(2026, 7, 15, 9, 0, 0),
                        ),
                        UserAnswer(
                            id=4502,
                            user_id=4101,
                            question_id=4302,
                            user_answer="false",
                            is_correct=False,
                            created_at=datetime(2026, 7, 15, 10, 30, 0),
                        ),
                        Mistake(
                            id=4601,
                            user_id=4101,
                            question_id=4302,
                            wrong_count=2,
                            created_at=datetime(2026, 7, 15, 10, 30, 0),
                            updated_at=datetime(2026, 7, 15, 10, 30, 0),
                            last_updated=datetime(2026, 7, 15, 10, 30, 0),
                        ),
                        Favorite(
                            id=4701,
                            user_id=4101,
                            question_id=4301,
                            created_at=datetime(2026, 7, 15, 11, 0, 0),
                        ),
                    ]
                )
                db.session.commit()
                ordinary_jwt = generate_jwt_token(
                    4101, "", expires_in=3600, session_version=3
                )
                administrator_jwt = generate_jwt_token(
                    4102, "", expires_in=3600, session_version=5
                )
                before = database_fingerprint(db)

            client = app.test_client()
            cases = [
                capture(
                    client,
                    case_id="subjects-ordinary",
                    actor="ordinary",
                    path="/api/quiz/subjects",
                    authorization=f"Bearer {ordinary_jwt}",
                ),
                capture(
                    client,
                    case_id="subjects-administrator",
                    actor="administrator",
                    path="/api/quiz/subjects",
                    authorization=f"Bearer {administrator_jwt}",
                ),
                capture(
                    client,
                    case_id="subjects-unauthenticated",
                    actor="anonymous",
                    path="/api/quiz/subjects",
                    authorization=None,
                ),
                capture(
                    client,
                    case_id="subjects-meta-ordinary",
                    actor="ordinary",
                    path="/api/quiz/subjects/meta",
                    authorization=f"Bearer {ordinary_jwt}",
                ),
                capture(
                    client,
                    case_id="subjects-meta-administrator",
                    actor="administrator",
                    path="/api/quiz/subjects/meta",
                    authorization=f"Bearer {administrator_jwt}",
                ),
                capture(
                    client,
                    case_id="subjects-meta-unauthenticated",
                    actor="anonymous",
                    path="/api/quiz/subjects/meta",
                    authorization=None,
                ),
            ]

            # The first ordinary subjects request above consumed request 1. Complete the
            # observed 60/minute budget, then capture the first rejected request (61).
            for request_number in range(2, 61):
                response = client.get(
                    "/api/quiz/subjects",
                    headers={"Authorization": f"Bearer {ordinary_jwt}"},
                )
                if response.status_code != 200:
                    raise AssertionError(
                        f"legacy subjects limit rejected request {request_number}: "
                        f"HTTP {response.status_code}"
                    )
            cases.append(
                capture(
                    client,
                    case_id="subjects-rate-limited",
                    actor="ordinary",
                    path="/api/quiz/subjects",
                    authorization=f"Bearer {ordinary_jwt}",
                )
            )

            with app.app_context():
                after = database_fingerprint(db)

            document = {
                "contract_id": "ti.phase4a.subject-read-goldens",
                "schema_version": 1,
                "captured_at": "2026-07-16",
                "legacy_commit": "700006dfdfa063deb4387be572911e782bcea0d9",
                "isolation": "temporary SQLite database; no production or persistent local data",
                "cache_mode": "legacy QUIZ_API_CACHE_ENABLED=false; rate limiting remains enabled",
                "redaction": "synthetic identities only; JWTs omitted; request IDs normalized out",
                "database_side_effect_free": before == after,
                "cases": cases,
            }
            if not document["database_side_effect_free"]:
                raise AssertionError("legacy subject GETs mutated the isolated fixture database")
            if any(case["response"]["status"] >= 500 for case in cases):
                raise AssertionError("legacy subject golden capture returned a server error")

            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({
                "output": str(output),
                "case_count": len(cases),
                "database_side_effect_free": True,
            }, ensure_ascii=False))
        finally:
            with app.app_context():
                db.session.remove()
                db.drop_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
