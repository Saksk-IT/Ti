#!/usr/bin/env python3
"""Capture deterministic, desensitized legacy HTTP samples in an isolated DB."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


# The capture must not leave ignored bytecode artifacts in the protected legacy tree.
sys.dont_write_bytecode = True


NONDETERMINISTIC_RESPONSE_KEYS = {"request_id", "trace_id", "correlation_id"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
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


def response_payload(response: Any) -> Any:
    payload = response.get_json(silent=True)
    if payload is not None:
        return normalize_payload(payload)
    text = response.get_data(as_text=True)
    return {"body_excerpt": text[:1000], "truncated": len(text) > 1000}


def capture(
    *,
    domain: str,
    client: Any,
    method: str,
    path: str,
    request_json: dict[str, Any] | None = None,
    recorded_request_json: dict[str, Any] | None = None,
    request_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = client.open(
        path,
        method=method,
        json=request_json,
        headers=request_headers,
    )
    headers = {
        name: response.headers[name]
        for name in ("Content-Type", "Location")
        if name in response.headers
    }
    return {
        "domain": domain,
        "legacy_contract_source": "isolated Flask test client at commit 700006dfdfa063deb4387be572911e782bcea0d9",
        "request": {
            "method": method,
            "path": path,
            "json": recorded_request_json if recorded_request_json is not None else request_json,
            "headers": request_headers or {},
        },
        "response": {
            "status": response.status_code,
            "headers": headers,
            "body": response_payload(response),
        },
    }


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    output_dir = args.output_dir.resolve()
    if not (legacy_root / "app" / "__init__.py").is_file():
        raise SystemExit(f"Not a Ti legacy root: {legacy_root}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ti-java-golden-") as data_dir:
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
        from app.models.quiz import Mistake, UserAnswer
        from app.models.subject import Question, Subject
        from app.models.user import User

        logging.disable(logging.CRITICAL)
        legacy_app._start_background_tasks = lambda _app: None
        app = legacy_app.create_app("testing")
        samples: list[dict[str, Any]] = []
        try:
            with app.app_context():
                db.create_all()
                user = User(
                    username="golden_user",
                    email="golden_user@test.example.com",
                    password_hash=generate_password_hash("Golden-Test-Password-123!"),
                    has_password_set=True,
                    email_verified=True,
                    is_admin=True,
                    is_subject_admin=True,
                    is_notification_admin=True,
                )
                subject = Subject(
                    name="Golden Subject",
                    description="Deterministic phase-0 contract fixture",
                    is_locked=False,
                )
                db.session.add_all([user, subject])
                db.session.flush()
                question = Question(
                    subject_id=subject.id,
                    type="选择题",
                    content="2 + 2 = ?",
                    options=json.dumps(
                        [
                            {"key": "A", "value": "3"},
                            {"key": "B", "value": "4"},
                        ],
                        ensure_ascii=False,
                    ),
                    answer="B",
                    analysis="2 + 2 equals 4.",
                    tags="[]",
                    difficulty=1,
                    source="phase-0-golden-fixture",
                    created_by=user.id,
                    updated_by=user.id,
                )
                db.session.add(question)
                db.session.commit()
                user_id = int(user.id)
                question_id = int(question.id)

            login_body = {
                "username": "golden_user@test.example.com",
                "password": "Golden-Test-Password-123!",
                "remember": False,
                "redirect": "/",
            }
            samples.append(
                capture(
                    domain="identity",
                    client=app.test_client(),
                    method="POST",
                    path="/api/login",
                    request_json=login_body,
                    recorded_request_json={**login_body, "password": "<redacted-test-password>"},
                )
            )

            auth_client = app.test_client()
            with auth_client.session_transaction() as session:
                session["user_id"] = user_id
                session["username"] = "golden_user"
                session["is_admin"] = True
                session["is_subject_admin"] = True
                session["is_notification_admin"] = True
                session["session_version"] = 0

            samples.append(
                capture(
                    domain="catalog",
                    client=app.test_client(),
                    method="GET",
                    path="/api/public/banks/summary",
                )
            )
            learning_sample = capture(
                domain="learning",
                client=auth_client,
                method="POST",
                path="/api/record_result",
                request_json={
                    "question_id": question_id,
                    "is_correct": True,
                    "clear_mistake_on_correct": True,
                },
                request_headers={"X-Requested-With": "XMLHttpRequest"},
            )
            with app.app_context():
                answer = UserAnswer.query.filter_by(
                    user_id=user_id,
                    question_id=question_id,
                ).one_or_none()
                learning_sample["postconditions"] = {
                    "user_answers_count": UserAnswer.query.filter_by(
                        user_id=user_id,
                        question_id=question_id,
                    ).count(),
                    "latest_answer": {
                        "user_id": int(answer.user_id) if answer else None,
                        "question_id": int(answer.question_id) if answer else None,
                        "is_correct": bool(answer.is_correct) if answer else None,
                        "user_answer": answer.user_answer if answer else None,
                    },
                    "mistakes_count": Mistake.query.filter_by(
                        user_id=user_id,
                        question_id=question_id,
                    ).count(),
                }
            samples.append(learning_sample)
            samples.extend(
                [
                    capture(
                        domain="assessment",
                        client=auth_client,
                        method="GET",
                        path="/api/exams/records",
                    ),
                    capture(
                        domain="community",
                        client=auth_client,
                        method="GET",
                        path="/api/forum/boards",
                    ),
                    capture(
                        domain="campus",
                        client=auth_client,
                        method="GET",
                        path="/api/edu-schedule/status",
                    ),
                    capture(
                        domain="operations",
                        client=auth_client,
                        method="GET",
                        path="/admin/api/subjects",
                    ),
                ]
            )
        finally:
            with app.app_context():
                db.session.remove()
                db.drop_all()

    filenames: list[str] = []
    for index, sample in enumerate(samples, start=1):
        filename = f"{index:02d}-{sample['domain']}.json"
        (output_dir / filename).write_text(
            json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        filenames.append(filename)

    manifest = {
        "captured_at": "2026-07-16",
        "legacy_commit": "700006dfdfa063deb4387be572911e782bcea0d9",
        "isolation": "temporary SQLite database; no production or local persistent database access",
        "redaction": "test-only identity; passwords replaced in recorded requests; cookies and request IDs omitted",
        "samples": filenames,
        "all_success": all(sample["response"]["status"] < 400 for sample in samples),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["all_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
