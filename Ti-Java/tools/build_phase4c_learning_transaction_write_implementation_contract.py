#!/usr/bin/env python3
"""Build the Phase 4C transaction-write implementation authorization contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
GOLDEN = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-golden-evidence.json"
)
CALLERS = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-callers.json"
)
ENTRY = (
    TI_JAVA / "docs/refactor/phase4c/learning-route-scope-entry-contract.json"
)
BUILD_TEST = (
    TOOLS_DIR
    / "test_phase4c_learning_transaction_write_implementation_contract.py"
)
DEFAULT_OUTPUT = (
    TI_JAVA
    / "docs/refactor/phase4c/"
    "learning-transaction-write-implementation-contract.json"
)
sys.dont_write_bytecode = True


PREDECESSOR_COMMIT = "22a1d81b14be61129427ca614a68ea12befde919"
PREDECESSOR_TREE = "ef89ceba871d2794c6e3f37e5dc0ef5408e084c5"
PREDECESSOR_PARENT = "33b07f8b8b0fec2bd7ffa8c8af16254815479eba"
GOLDEN_SHA256 = (
    "0d64e42b1d73c031151e76bb29c3d6a2e1f445c93bafcecb16e9d56fc3c12057"
)
CALLERS_SHA256 = (
    "9425f54c1cdd27c902fbb87712cfe6d7ffb81d4540d7759720b57d0b235862c3"
)
ENTRY_SHA256 = (
    "73c235dac971a52b2bf620565f3e4070c663a9584a63b2cc0a668f121cb73684"
)
ROUTE_MATRIX_SHA256 = (
    "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
)
ROUTES = (
    ("6d548bfd6830", "POST", "/api/favorite", "learning", "favorite"),
    (
        "b52d3008d4d1",
        "POST",
        "/api/quiz/favorite",
        "learning",
        "favorite",
    ),
    (
        "87bb4fb340c8",
        "POST",
        "/api/record_result",
        "learning",
        "record-result",
    ),
    (
        "67dccafb3ea4",
        "POST",
        "/api/quiz/record_result",
        "learning",
        "record-result",
    ),
    (
        "bf3cb0c4f9ab",
        "POST",
        "/api/quiz/study/learn/record",
        "learning",
        "study-learn",
    ),
    (
        "c797832c43db",
        "POST",
        "/api/quiz/study/review/record",
        "learning",
        "study-review-record",
    ),
    (
        "278e1eac5eb4",
        "POST",
        "/api/quiz/study/review/master",
        "learning",
        "study-review-master",
    ),
    (
        "59c9c7366ec3",
        "POST",
        "/api/user/checkin",
        "learning",
        "checkin",
    ),
    (
        "624b5ac217d0",
        "PUT",
        "/api/quiz/questions/{questionId}",
        "catalog",
        "question-edit",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
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


def fixed_file(
    path: Path,
    *,
    relative: str,
    expected_sha256: str,
    expected_contract_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise AssertionError(f"fixed predecessor drifted: {relative}")
    document = json.loads(payload)
    if document["contract_id"] != expected_contract_id:
        raise AssertionError(f"fixed predecessor identity drifted: {relative}")
    return document, {
        "path": relative,
        "sha256": digest,
        "size_bytes": len(payload),
        "document_payload_sha256": document["document_payload_sha256"],
    }


def source_provenance() -> dict[str, Any]:
    builder = Path(__file__).read_bytes()
    test = BUILD_TEST.read_bytes()
    return {
        "builder": {
            "path": (
                "tools/"
                "build_phase4c_learning_transaction_write_implementation_contract.py"
            ),
            "sha256": hashlib.sha256(builder).hexdigest(),
            "size_bytes": len(builder),
        },
        "builder_test": {
            "path": (
                "tools/"
                "test_phase4c_learning_transaction_write_implementation_contract.py"
            ),
            "sha256": hashlib.sha256(test).hexdigest(),
            "size_bytes": len(test),
        },
        "secrets_embedded": False,
    }


def route_records() -> list[dict[str, Any]]:
    return [
        {
            "ordinal": ordinal,
            "route_id": route_id,
            "method": method,
            "path": path,
            "persistent_owner": owner,
            "semantic_group": semantic_group,
            "migration_status_before": "pending",
            "implementation_authorized": True,
            "route_delta_authorized": False,
            "production_cutover": False,
        }
        for ordinal, (route_id, method, path, owner, semantic_group)
        in enumerate(ROUTES, start=1)
    ]


def build_document() -> dict[str, Any]:
    golden, golden_ref = fixed_file(
        GOLDEN,
        relative=(
            "docs/refactor/phase4c/"
            "learning-transaction-write-golden-evidence.json"
        ),
        expected_sha256=GOLDEN_SHA256,
        expected_contract_id=(
            "ti.phase4c.learning-transaction-write-golden-execution"
        ),
    )
    callers, callers_ref = fixed_file(
        CALLERS,
        relative=(
            "docs/refactor/phase4c/"
            "learning-transaction-write-callers.json"
        ),
        expected_sha256=CALLERS_SHA256,
        expected_contract_id=(
            "ti.phase4c.learning-transaction-write-caller-attestation"
        ),
    )
    entry, entry_ref = fixed_file(
        ENTRY,
        relative=(
            "docs/refactor/phase4c/learning-route-scope-entry-contract.json"
        ),
        expected_sha256=ENTRY_SHA256,
        expected_contract_id="ti.phase4c.learning-route-scope-entry-contract",
    )
    if not golden["closure"]["golden_execution_complete"]:
        raise AssertionError("golden execution is not closed")
    if not callers["closure"]["caller_attestation_complete"]:
        raise AssertionError("caller attestation is not closed")
    if entry["frozen_route_authority"]["sha256"] != ROUTE_MATRIX_SHA256:
        raise AssertionError("route matrix authority drifted")

    routes = route_records()
    document: dict[str, Any] = {
        "contract_id": (
            "ti.phase4c.learning-transaction-write-implementation-contract"
        ),
        "schema_version": 1,
        "captured_at": "2026-07-23T20:05:00+08:00",
        "predecessor": {
            "commit_oid": PREDECESSOR_COMMIT,
            "root_tree_oid": PREDECESSOR_TREE,
            "parent_commit_oid": PREDECESSOR_PARENT,
            "golden_evidence": golden_ref,
            "caller_evidence": callers_ref,
            "route_scope_entry": entry_ref,
            "predecessor_commit_is_fixed": True,
            "live_worktree_is_not_authority": True,
        },
        "scope": {
            "operation_count": len(routes),
            "routes": routes,
            "route_ids_sha256": sha256_json([
                route["route_id"] for route in routes
            ]),
            "semantic_group_count": 7,
            "learning_persistent_owner_count": 8,
            "catalog_persistent_owner_count": 1,
        },
        "approved_differences": [
            {
                "difference_id": "P4C-TW-AD-001",
                "title": "restore study learning and review writes",
                "affected_route_ids": [
                    "bf3cb0c4f9ab",
                    "c797832c43db",
                    "278e1eac5eb4",
                ],
                "legacy_observation": (
                    "valid requests return safe HTTP 500 before business DML "
                    "under the fixed SQLAlchemy 2 runtime"
                ),
                "target_behavior": (
                    "valid authorized requests commit exactly one learning "
                    "state transition and return the intended success envelope"
                ),
                "compatibility_preserved": [
                    "authentication",
                    "CSRF boundary",
                    "route-specific rate limit",
                    "validation errors",
                    "scope authorization",
                    "success response field names",
                ],
                "reason": (
                    "the fixed behavior is an execution defect that contradicts "
                    "the handler's documented and client-consumed intent"
                ),
                "approved": True,
            },
            {
                "difference_id": "P4C-TW-AD-002",
                "title": "restore checkin persistence",
                "affected_route_ids": ["59c9c7366ec3"],
                "legacy_observation": (
                    "valid requests return HTTP 500 because a string is bound "
                    "to a DateTime column"
                ),
                "target_behavior": (
                    "the first request atomically creates today's checkin; "
                    "subsequent requests return the original successful result "
                    "with just_checked_in=false"
                ),
                "compatibility_preserved": [
                    "authentication",
                    "global rate limit",
                    "response field names",
                    "calendar and streak semantics",
                ],
                "reason": (
                    "the DateTime bind mismatch is an implementation defect, "
                    "not an intentional public contract"
                ),
                "approved": True,
            },
            {
                "difference_id": "P4C-TW-AD-003",
                "title": "make question edit persist in catalog",
                "affected_route_ids": ["624b5ac217d0"],
                "legacy_observation": (
                    "the route returns HTTP 200 while swallowing the failed "
                    "UPDATE and returning unchanged question data"
                ),
                "target_behavior": (
                    "catalog atomically persists the validated edit and returns "
                    "the updated representation"
                ),
                "compatibility_preserved": [
                    "admin or subject-admin authorization",
                    "CSRF boundary",
                    "10/minute route limit",
                    "validation errors",
                    "success response field names",
                ],
                "reason": (
                    "a successful no-op is deceptive and violates the route's "
                    "client-visible editing purpose"
                ),
                "approved": True,
            },
        ],
        "idempotency_contract": {
            "header": "Idempotency-Key",
            "optional": True,
            "maximum_utf8_bytes": 255,
            "blank_is_absent": True,
            "key_storage": "HMAC-SHA-256 only; raw keys are never persisted or logged",
            "request_fingerprint": (
                "SHA-256 of method, canonical route semantic group, actor id, "
                "normalized path variables, and canonical JSON body"
            ),
            "same_actor_key_same_payload": (
                "replay the first committed HTTP status and response body"
            ),
            "same_actor_key_different_payload": "HTTP 409",
            "different_actor_same_key": "independent",
            "concurrent_same_key": (
                "one business commit; contenders block on the unique receipt "
                "and replay the committed result"
            ),
            "failed_transaction": (
                "receipt and business mutation roll back together; a retry may "
                "acquire the key and execute"
            ),
            "without_header": (
                "preserve one legacy-compatible logical attempt for every "
                "accepted request"
            ),
            "response_replay_headers": [
                "content type",
                "route-compatible response body",
            ],
            "excluded_replay_headers": [
                "request id",
                "rate-limit counters",
                "date",
            ],
        },
        "schema_authorization": {
            "authorized": True,
            "production_execution_authorized": False,
            "migration_tool": "Flyway",
            "tables": [
                {
                    "table": "learning_idempotency_receipts",
                    "persistent_owner": "learning",
                    "required_columns": [
                        "actor_id bigint",
                        "operation varchar",
                        "key_hmac bytea",
                        "request_sha256 bytea",
                        "state varchar",
                        "response_status integer",
                        "response_body jsonb",
                        "created_at timestamptz",
                        "completed_at timestamptz",
                        "expires_at timestamptz",
                    ],
                    "primary_key": [
                        "actor_id",
                        "operation",
                        "key_hmac",
                    ],
                    "business_transaction_atomicity": True,
                },
                {
                    "table": "catalog_question_edit_commands",
                    "persistent_owner": "catalog",
                    "required_columns": [
                        "actor_id bigint",
                        "key_hmac bytea",
                        "request_sha256 bytea",
                        "question_id bigint",
                        "state varchar",
                        "response_status integer",
                        "response_body jsonb",
                        "created_at timestamptz",
                        "completed_at timestamptz",
                        "expires_at timestamptz",
                    ],
                    "primary_key": ["actor_id", "key_hmac"],
                    "question_update_transaction_atomicity": True,
                },
            ],
            "required_guards": [
                "non-null and state check constraints",
                "bounded operation/state values",
                "expiry cleanup index",
                "no raw idempotency key column",
                "PostgreSQL 16 and 18 integration tests",
                "forward-only migration; no automatic production execution",
            ],
        },
        "module_boundary": {
            "learning_owned_tables": [
                "favorites",
                "mistakes",
                "study_learning",
                "study_review",
                "user_answers",
                "user_checkins",
                "user_quiz_stats",
                "learning_idempotency_receipts",
            ],
            "catalog_owned_tables": [
                "questions",
                "subjects",
                "catalog_question_edit_commands",
            ],
            "learning_direct_sql_to_catalog_tables_forbidden": True,
            "catalog_direct_sql_to_learning_tables_forbidden": True,
            "question_edit_call_direction": "learning HTTP -> catalog::api",
            "cross_module_database_transaction_forbidden": True,
            "question_edit_idempotency_owner": "catalog",
            "allowed_application_dependencies": [
                "learning -> catalog::api",
                "learning -> identity::api",
                "learning -> personalbank::api",
            ],
        },
        "transaction_contract": {
            "favorite": (
                "permission check before mutation; toggle and receipt in one "
                "learning transaction"
            ),
            "record_result": (
                "permission and quota checks precede mutation; mistake, latest "
                "answer, quota increment, and receipt commit atomically"
            ),
            "study_learn": (
                "scope authorization, learning row, mistake row, review "
                "activation, and receipt commit atomically"
            ),
            "study_review_record": (
                "review schedule transition and receipt commit atomically"
            ),
            "study_review_master": (
                "master flag, next due timestamp, and receipt commit atomically"
            ),
            "checkin": (
                "unique actor/date insert plus response calculation and receipt "
                "commit atomically"
            ),
            "question_edit": (
                "catalog command receipt and question update commit atomically "
                "inside catalog; learning owns no catalog transaction"
            ),
            "rollback": "no partial business or receipt rows",
            "retry": "bounded only for transient SQLSTATE allowlist",
        },
        "http_contract": {
            "credential_modes": [
                "Target Session",
                "Flask-compatible Session",
                "Bearer JWT",
            ],
            "write_csrf": (
                "valid Bearer bypasses XHR marker; Session requires "
                "X-Requested-With=XMLHttpRequest"
            ),
            "route_limits": {
                "favorite": "30/minute",
                "record-result": "60/minute",
                "study-learn": "60/minute",
                "study-review-record": "60/minute",
                "study-review-master": "30/minute",
                "checkin": "global inherited limit",
                "question-edit": "10/minute",
            },
            "aliases_share_application_behavior": True,
            "aliases_preserve_distinct_paths": True,
            "errors_use_route_compatible_safe_envelopes": True,
            "request_id_never_replayed_from_idempotency_receipt": True,
        },
        "implementation_evidence_required": [
            "unit tests for every application transition and validation branch",
            "real HTTP tests for all three credential modes and CSRF ordering",
            "real Redis explicit route-limit and connection-failure tests",
            "PostgreSQL 16 and 18 transaction, constraint and concurrency tests",
            "same-key replay, conflict, rollback and concurrent-one-commit tests",
            "catalog API delegation proof with no learning SQL to questions",
            "ArchUnit module and table-ownership checks",
            "OpenAPI 3.1 parity for all nine operations",
            "route matrix delta only after the complete implementation gate",
            "full Maven test and verify with zero failures",
        ],
        "authorization": {
            "transaction_write_implementation": True,
            "scoped_flyway_migrations": True,
            "approved_difference_implementation": True,
            "unit_and_integration_tests": True,
            "openapi_draft": True,
            "route_matrix_delta": False,
            "production_schema_execution": False,
            "production_cutover": False,
            "legacy_runtime_disable": False,
            "progress_and_tags_group": False,
            "selection_search_and_count_group": False,
            "statistics_and_data_center_group": False,
        },
        "route_state": {
            "migrated_operation_count_before": 13,
            "pending_operation_count_before": 598,
            "production_cutover_operation_count": 0,
            "migrated_operation_count_after_contract": 13,
            "pending_operation_count_after_contract": 598,
            "implementation_contract_is_not_route_migration": True,
        },
        "control_plane": {
            "predecessor_is_fixed_commit": True,
            "golden_physical_bytes_fixed": True,
            "caller_physical_bytes_fixed": True,
            "self_signed": False,
            "externally_anchored": False,
            "post_push_anchor_required": True,
        },
        "status": {
            "golden_gate_closed": True,
            "approved_differences_closed": True,
            "implementation_authorized": True,
            "implementation_complete": False,
            "route_migration_complete": False,
            "production_cutover": False,
            "next_gate": (
                "transaction-write schema, application, HTTP, Redis and "
                "PostgreSQL implementation evidence"
            ),
        },
        "provenance": source_provenance(),
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    args = parse_args()
    document = build_document()
    rendered = render_document(document)
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_bytes() != rendered:
            raise SystemExit(f"implementation contract drifted: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
