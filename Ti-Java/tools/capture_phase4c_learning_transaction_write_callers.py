#!/usr/bin/env python3
"""Capture fixed-commit caller evidence for Phase 4C transaction writes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
ROUTE_MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
ENTRY_CONTRACT = (
    TI_JAVA / "docs/refactor/phase4c/learning-route-scope-entry-contract.json"
)
CAPTURE_TEST = TOOLS_DIR / "test_capture_phase4c_learning_transaction_write_callers.py"
DEFAULT_OUTPUT = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-callers.json"
)
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
EXPECTED_ROUTE_MATRIX_SHA256 = (
    "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
)
EXPECTED_ENTRY_CONTRACT_SHA256 = (
    "73c235dac971a52b2bf620565f3e4070c663a9584a63b2cc0a668f121cb73684"
)
ROUTE_IDS = (
    "6d548bfd6830",
    "b52d3008d4d1",
    "87bb4fb340c8",
    "67dccafb3ea4",
    "bf3cb0c4f9ab",
    "c797832c43db",
    "278e1eac5eb4",
    "59c9c7366ec3",
    "624b5ac217d0",
)

CALLERS = (
    {
        "caller_id": "web-search-toggle-favorite",
        "route_id": "6d548bfd6830",
        "surface": "web",
        "source": "app/modules/main/templates/main/search/search.html",
        "line": 1459,
        "contains": "fetch('/api/favorite'",
        "transport": "web-main-fetch",
    },
    {
        "caller_id": "web-quiz-toggle-favorite",
        "route_id": "6d548bfd6830",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_09_settings_modal.html"
        ),
        "line": 267,
        "contains": ": '/api/favorite';",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "miniprogram-toggle-favorite",
        "route_id": "b52d3008d4d1",
        "surface": "miniprogram",
        "source": "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        "line": 279,
        "contains": "request('/quiz/favorite', 'POST'",
        "transport": "miniprogram-request",
    },
    {
        "caller_id": "web-quiz-record-result",
        "route_id": "87bb4fb340c8",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_08_check_answer.html"
        ),
        "line": 43,
        "contains": ": '/api/record_result';",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "web-subjective-self-eval-record-result",
        "route_id": "87bb4fb340c8",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_08_check_answer.html"
        ),
        "line": 293,
        "contains": "await fetch('/api/record_result'",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "miniprogram-record-result",
        "route_id": "67dccafb3ea4",
        "surface": "miniprogram",
        "source": "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        "line": 263,
        "contains": "request('/quiz/record_result', 'POST'",
        "transport": "miniprogram-request",
    },
    {
        "caller_id": "web-study-learn-record",
        "route_id": "bf3cb0c4f9ab",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_07_render_show_question.html"
        ),
        "line": 788,
        "contains": "fetch('/api/quiz/study/learn/record'",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "web-study-review-record",
        "route_id": "c797832c43db",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_07_render_show_question.html"
        ),
        "line": 807,
        "contains": "fetch('/api/quiz/study/review/record'",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "web-study-review-master",
        "route_id": "278e1eac5eb4",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_07_render_show_question.html"
        ),
        "line": 835,
        "contains": "fetch('/api/quiz/study/review/master'",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "web-user-checkin",
        "route_id": "59c9c7366ec3",
        "surface": "web",
        "source": "app/modules/main/templates/main/hub/hub.html",
        "line": 1517,
        "contains": "fetch('/api/user/checkin'",
        "transport": "web-main-fetch",
    },
    {
        "caller_id": "miniprogram-user-checkin",
        "route_id": "59c9c7366ec3",
        "surface": "miniprogram",
        "source": "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        "line": 614,
        "contains": "request('/user/checkin', 'POST')",
        "transport": "miniprogram-request",
    },
    {
        "caller_id": "web-question-edit",
        "route_id": "624b5ac217d0",
        "surface": "web",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/assets/js/"
            "_03_question_edit.html"
        ),
        "line": 429,
        "contains": "`/api/quiz/questions/${qid}`",
        "transport": "web-quiz-fetch",
    },
    {
        "caller_id": "miniprogram-question-edit",
        "route_id": "624b5ac217d0",
        "surface": "miniprogram",
        "source": "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        "line": 833,
        "contains": "request(`/quiz/questions/${questionId}`, 'PUT', data)",
        "transport": "miniprogram-request",
    },
)

TRANSPORTS = (
    {
        "transport_id": "web-main-fetch",
        "source": "app/modules/main/templates/main/shared/app_shell.html",
        "line": 37,
        "contains": (
            "opts.headers.set('X-Requested-With', 'XMLHttpRequest');"
        ),
        "credential": "same-origin Session",
        "csrf_boundary": "XHR marker injected by the shared app shell",
    },
    {
        "transport_id": "web-quiz-fetch",
        "source": (
            "app/modules/quiz/templates/quiz/partials/quiz/head/_head_meta.html"
        ),
        "line": 41,
        "contains": (
            "opts.headers.set('X-Requested-With', 'XMLHttpRequest');"
        ),
        "credential": "same-origin Session",
        "csrf_boundary": "XHR marker injected by the quiz document head",
    },
    {
        "transport_id": "miniprogram-request",
        "source": "miniprogram-1/miniprogram/utils/api-client.ts",
        "line": 115,
        "contains": (
            "'Authorization': tokenAtRequest ? `Bearer ${tokenAtRequest}` : ''"
        ),
        "credential": "Bearer token",
        "csrf_boundary": "valid JWT bypasses the legacy API write XHR check",
    },
)

SCAN_PATTERN = re.compile(
    r"/api/favorite|/api/record_result|/quiz/favorite|/quiz/record_result|"
    r"/api/quiz/study/(?:learn/record|review/(?:record|master))|"
    r"/api/user/checkin|/user/checkin|/api/quiz/questions|"
    r"/quiz/questions/"
)


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


def read_fixed_blob(legacy_root: Path, path: str) -> bytes:
    return pinned_source._run_read_only_git(
        legacy_root, "show", f"{LEGACY_COMMIT}:{path}"
    )


def source_line(
    legacy_root: Path,
    *,
    source: str,
    line: int,
    contains: str,
) -> dict[str, Any]:
    payload = read_fixed_blob(legacy_root, source)
    lines = payload.decode("utf-8-sig").splitlines()
    if line < 1 or line > len(lines):
        raise AssertionError(f"caller line out of range: {source}:{line}")
    text = lines[line - 1].strip()
    if contains not in text:
        raise AssertionError(
            f"caller drifted at {source}:{line}: expected {contains!r}, "
            f"observed {text!r}"
        )
    return {
        "source": source,
        "line": line,
        "text": text,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_size_bytes": len(payload),
        "git_blob": pinned_source._git_blob_id(payload, "sha1"),
    }


def matrix_attestation() -> dict[str, Any]:
    payload = ROUTE_MATRIX.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_ROUTE_MATRIX_SHA256:
        raise AssertionError("frozen route matrix drifted")
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
    selected = [row for row in rows if row["route_id"] in ROUTE_IDS]
    if (
        len(selected) != len(ROUTE_IDS)
        or {row["route_id"] for row in selected} != set(ROUTE_IDS)
    ):
        raise AssertionError("transaction-write route set is incomplete")
    if any(
        row["migration_status"] != "pending"
        or row["target_module"] != "learning"
        for row in selected
    ):
        raise AssertionError("transaction-write route authority drifted")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": digest,
        "size_bytes": len(payload),
        "selected_rows": selected,
        "selected_rows_sha256": sha256_json(selected),
    }


def entry_contract_attestation() -> dict[str, Any]:
    payload = ENTRY_CONTRACT.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_ENTRY_CONTRACT_SHA256:
        raise AssertionError("learning route-scope entry contract drifted")
    document = json.loads(payload.decode("utf-8"))
    if (
        not document["authorization"][
            "transaction_write_golden_capture_authorized"
        ]
        or document["next_gate"]["name"]
        != "transaction-write fixed-commit golden and invariants"
    ):
        raise AssertionError("entry contract does not authorize caller capture")
    return {
        "path": (
            "docs/refactor/phase4c/"
            "learning-route-scope-entry-contract.json"
        ),
        "sha256": digest,
        "size_bytes": len(payload),
        "document_payload_sha256": document["document_payload_sha256"],
    }


def full_fixed_commit_scan(legacy_root: Path) -> dict[str, Any]:
    raw = pinned_source._run_read_only_git(
        legacy_root,
        "grep",
        "-n",
        "-I",
        "-E",
        (
            "/api/favorite|/api/record_result|/quiz/favorite|"
            "/quiz/record_result|/api/quiz/study/learn/record|"
            "/api/quiz/study/review/record|"
            "/api/quiz/study/review/master|/api/user/checkin|"
            "/user/checkin|/api/quiz/questions|/quiz/questions/"
        ),
        LEGACY_COMMIT,
        "--",
        "app",
        "miniprogram-1",
        ":(exclude)miniprogram-1/analyse-data.json",
    ).decode("utf-8")
    prefix = LEGACY_COMMIT + ":"
    matches: list[dict[str, Any]] = []
    for record in raw.splitlines():
        if not record.startswith(prefix):
            raise AssertionError("fixed-commit grep emitted an unpinned record")
        path, line, text = record[len(prefix):].split(":", 2)
        if not SCAN_PATTERN.search(text):
            raise AssertionError("fixed-commit caller scan classification drifted")
        matches.append({
            "source": path,
            "line": int(line),
            "text": text.strip(),
        })
    matches.sort(key=lambda item: (item["source"], item["line"], item["text"]))
    if not matches:
        raise AssertionError("fixed-commit caller scan is empty")
    return {
        "scope": [
            "fixed commit app/",
            "fixed commit miniprogram-1/",
        ],
        "excluded_paths": ["miniprogram-1/analyse-data.json"],
        "pattern": SCAN_PATTERN.pattern,
        "match_count": len(matches),
        "matches_sha256": sha256_json(matches),
        "matches": matches,
    }


def capture_document(legacy_root: Path) -> dict[str, Any]:
    resolved = pinned_source._read_git_text(
        legacy_root, "rev-parse", f"{LEGACY_COMMIT}^{{commit}}"
    )
    if resolved != LEGACY_COMMIT:
        raise AssertionError("legacy commit authority drifted")
    root_tree = pinned_source._read_git_text(
        legacy_root, "rev-parse", f"{LEGACY_COMMIT}^{{tree}}"
    )
    caller_records = []
    for caller in CALLERS:
        caller_records.append({
            **{key: value for key, value in caller.items() if key != "contains"},
            "source_attestation": source_line(
                legacy_root,
                source=caller["source"],
                line=caller["line"],
                contains=caller["contains"],
            ),
        })
    transport_records = []
    for transport in TRANSPORTS:
        transport_records.append({
            **{
                key: value
                for key, value in transport.items()
                if key != "contains"
            },
            "source_attestation": source_line(
                legacy_root,
                source=transport["source"],
                line=transport["line"],
                contains=transport["contains"],
            ),
        })
    by_route = {
        route_id: sorted(
            caller["caller_id"]
            for caller in caller_records
            if caller["route_id"] == route_id
        )
        for route_id in ROUTE_IDS
    }
    if any(not callers for callers in by_route.values()):
        raise AssertionError("every transaction-write operation needs an active caller")
    tool_payload = Path(__file__).read_bytes()
    test_payload = CAPTURE_TEST.read_bytes()
    document: dict[str, Any] = {
        "contract_id": (
            "ti.phase4c.learning-transaction-write-caller-attestation"
        ),
        "schema_version": 1,
        "captured_at": "2026-07-23",
        "legacy_commit": LEGACY_COMMIT,
        "legacy_root_tree": root_tree,
        "predecessor": entry_contract_attestation(),
        "route_matrix": matrix_attestation(),
        "caller_attestation": {
            "caller_count": len(caller_records),
            "route_count": len(by_route),
            "surface_counts": {
                "web": sum(
                    caller["surface"] == "web" for caller in caller_records
                ),
                "miniprogram": sum(
                    caller["surface"] == "miniprogram"
                    for caller in caller_records
                ),
            },
            "callers_by_route": by_route,
            "callers": caller_records,
            "caller_set_sha256": sha256_json(caller_records),
            "active_caller_attestation_complete": True,
        },
        "transport_attestation": {
            "transport_count": len(transport_records),
            "transports": transport_records,
            "all_callers_have_transport": all(
                caller["transport"]
                in {
                    transport["transport_id"]
                    for transport in transport_records
                }
                for caller in caller_records
            ),
            "web_session_write_has_xhr_marker": True,
            "miniprogram_write_has_bearer_transport": True,
        },
        "full_fixed_commit_usage_scan": full_fixed_commit_scan(legacy_root),
        "ownership_boundary": {
            "learning_owned_route_ids": list(ROUTE_IDS[:-1]),
            "catalog_owned_route_ids": [ROUTE_IDS[-1]],
            "question_edit_dependency": "learning -> catalog::api",
            "learning_direct_question_table_write_forbidden": True,
        },
        "closure": {
            "caller_attestation_complete": True,
            "golden_execution_complete": False,
            "implementation_authorized": False,
            "route_delta_authorized": False,
            "migration_status": "pending",
            "production_cutover": False,
            "next_gate": (
                "fixed-commit route execution, isolated database before/after "
                "fingerprints, SQL/transaction trace, duplicate/concurrent "
                "outcomes, and rollback/retry boundaries"
            ),
        },
        "provenance": {
            "source_transport": (
                "read-only git show/grep against the immutable legacy commit"
            ),
            "capture_tool": {
                "path": (
                    "tools/"
                    "capture_phase4c_learning_transaction_write_callers.py"
                ),
                "sha256": hashlib.sha256(tool_payload).hexdigest(),
                "size_bytes": len(tool_payload),
            },
            "capture_test": {
                "path": (
                    "tools/"
                    "test_capture_phase4c_learning_transaction_write_callers.py"
                ),
                "sha256": hashlib.sha256(test_payload).hexdigest(),
                "size_bytes": len(test_payload),
            },
            "secrets_captured": False,
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
            raise SystemExit(f"caller evidence drifted: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
