#!/usr/bin/env python3
"""Build the Gitless Phase 4C learning route-scope entry contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from tools import (
        phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance
        as predecessor_acceptance,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance \
        as predecessor_acceptance


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/learning-route-scope-entry-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
MATRIX_RELATIVE = "docs/refactor/02-route-parity-matrix.csv"
MATRIX_SHA256 = (
    "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
)
PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-execution-protocol-post-push-anchor-contract.json"
)
PREDECESSOR_SHA256 = (
    "a6dff0717d0da91091f50cb7a51d35ffc66db364e966c568fec40bdb3ca936cd"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "1a8bf429fe15f85e380f417329c0ca25c3245a6f1254c774b1a14ee7ebc48164"
)
PREDECESSOR_BYTE_COUNT = 80_324
CONTRACT_ID = "ti.phase4c.learning-route-scope-entry-contract"
CAPTURED_AT = "2026-07-23T19:20:00+08:00"
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"


def _operations(
    rows: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    return tuple(rows)


TRANSACTION_WRITES = _operations((
    ("6d548bfd6830", "POST"),
    ("b52d3008d4d1", "POST"),
    ("87bb4fb340c8", "POST"),
    ("67dccafb3ea4", "POST"),
    ("bf3cb0c4f9ab", "POST"),
    ("c797832c43db", "POST"),
    ("278e1eac5eb4", "POST"),
    ("59c9c7366ec3", "POST"),
    ("624b5ac217d0", "PUT"),
))

PROGRESS_AND_TAGS = _operations((
    ("7f23a2deabf0", "DELETE"),
    ("7f23a2deabf0", "GET"),
    ("7f23a2deabf0", "POST"),
    ("1e59f49d87aa", "DELETE"),
    ("1e59f49d87aa", "GET"),
    ("1e59f49d87aa", "POST"),
    ("abe53704e095", "GET"),
    ("abe53704e095", "POST"),
    ("af8df0b4e70a", "DELETE"),
    ("af8df0b4e70a", "GET"),
    ("af8df0b4e70a", "POST"),
))

SELECTION_SEARCH_AND_COUNT = _operations((
    ("bacda2bed9be", "GET"),
    ("5272d44a3138", "GET"),
    ("9c473c8cfb67", "GET"),
    ("bf3236e06b84", "GET"),
    ("d3cd12aaca90", "GET"),
    ("91204289b3ce", "GET"),
    ("d895bea1983a", "GET"),
    ("c618fb5f9f97", "GET"),
    ("bb21e7730d04", "GET"),
))

STATISTICS_AND_DATA_CENTER = _operations((
    ("2dffa3596c39", "GET"),
    ("79d6503d1216", "GET"),
    ("b4487d996c52", "GET"),
    ("20f46b0b55fd", "GET"),
    ("cdbecd968cba", "GET"),
    ("2e2664962668", "GET"),
    ("52585295556c", "GET"),
    ("9ffa45b71103", "GET"),
    ("c21a8a1f1d3e", "GET"),
    ("7fd9b0fc8111", "GET"),
    ("bfc8079d63de", "GET"),
    ("6e4561abf335", "GET"),
    ("7de8331891aa", "GET"),
    ("088865391e1a", "GET"),
    ("18352825da6c", "GET"),
    ("497b72cfd701", "GET"),
))

MIGRATED_USER_COUNTS = _operations((
    ("6858f6fa506f", "GET"),
    ("006913d0d956", "GET"),
))

CROSS_DOMAIN_TRANSFERS = _operations((
    ("1156cacff587", "POST"),
    ("c256dab89924", "POST"),
    ("7de6db064715", "POST"),
))

LEGACY_SOURCE_SHA256 = {
    "app/modules/admin/routes/api_components/system_config.py":
        "6773c3068d81c912f5df8504a0ac9043297dc6536a99f221ba86361aa5687305",
    "app/modules/main/routes/pages_components/data_center.py":
        "616accd0b07a9764dc3e878f544e0d33c4362dc56cc9a4bfb67c1cf0064e7431",
    "app/modules/quiz/routes/api_components/core.py":
        "cee9606ad15b40ead85fd409cace6cf6621ef0e6b65b3068837bcf066142e600",
    "app/modules/quiz/routes/api_components/core_counts.py":
        "01cdbb4254f71b87d61de406524944b560c4e480d7f370ecb522effa8d325063",
    "app/modules/quiz/routes/api_components/core_grading.py":
        "b29be55bf8c87139817baea025cd76123409f97e8e3db625f01e37cde8c1f47d",
    "app/modules/quiz/routes/api_components/core_history.py":
        "6cd0322ef9707f64f6fca26700fb8e8b421e4e5c9bc069e8fc7ca17255559b33",
    "app/modules/quiz/routes/api_components/core_reinforce.py":
        "7250a12e47c481be761a48818397379e3a54655344b5516acef976b324c8cde8",
    "app/modules/quiz/routes/api_components/progress_tags_notifications.py":
        "4dfaa547800ee6a1e01d57fac4ccd235a524e98d1be90ec14e466b2094eddbfc",
    "app/modules/quiz/routes/api_components/questions_study.py":
        "c872216fc7361305a822a5c5f4238c4ec2887f1ad6e9376e4980f567d5fc50ca",
    "app/modules/quiz/routes/api_components/search.py":
        "33f45693ebadf56919d723b746e9490af7ac85257d9d9206a230edec1729c12e",
    "app/modules/quiz/routes/api_components/subjects.py":
        "2ab1ff6e2dded31c230a7905fd028b72bfdfe92ef840baed00de1163f740f36e",
    "app/modules/user/routes/api.py":
        "9ff19da21259d0fe1ccae205e8c286c83fd30534b10619911b1bcddce958606c",
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_regular(root: Path, relative: str) -> bytes:
    base = root.resolve(strict=True)
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise AssertionError("Phase 4C route-scope path must stay below Ti-Java")
    cursor = base
    for part in value.parts:
        cursor /= part
        if cursor.is_symlink():
            raise AssertionError(
                f"Phase 4C route-scope source is a symlink: {relative}"
            )
    candidate = (base / value).resolve(strict=True)
    if not candidate.is_relative_to(base) or not candidate.is_file():
        raise AssertionError(
            f"Phase 4C route-scope source escaped Ti-Java: {relative}"
        )
    return candidate.read_bytes()


def _matrix_rows(root: Path) -> tuple[list[dict[str, str]], bytes]:
    payload = _read_regular(root, MATRIX_RELATIVE)
    if _sha256(payload) != MATRIX_SHA256:
        raise AssertionError("Phase 4C frozen route matrix drifted")
    text = payload.decode("utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    if len(rows) != 592:
        raise AssertionError("Phase 4C frozen route rule count drifted")
    return rows, payload


def _expanded(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    operations: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        for method in row["methods"].split(","):
            key = (row["route_id"], method)
            if key in operations:
                raise AssertionError(
                    f"Phase 4C duplicate route operation in matrix: {key}"
                )
            operations[key] = row
    if len(operations) != 611:
        raise AssertionError("Phase 4C frozen route operation count drifted")
    return operations


def _describe(
    operation_map: dict[tuple[str, str], dict[str, str]],
    keys: tuple[tuple[str, str], ...],
    group: str,
    effective_owner: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for ordinal, key in enumerate(keys, start=1):
        row = operation_map.get(key)
        if row is None:
            raise AssertionError(f"Phase 4C route operation is missing: {key}")
        result.append({
            "ordinal": ordinal,
            "group": group,
            "route_id": key[0],
            "method": key[1],
            "path": row["path"],
            "endpoint": row["endpoint"],
            "legacy_module": row["legacy_module"],
            "source": row["source"],
            "baseline_target_module": row["target_module"],
            "effective_owner": effective_owner,
            "baseline_migration_status": row["migration_status"],
            "client_surfaces": [
                value for value in row["client_surfaces"].split(";") if value
            ],
        })
    return result


def _page_operations(
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for row in rows:
        if (
            row["target_module"] != "learning"
            or row["path"].startswith("/api/")
            or row["path"].startswith("/admin/api/")
        ):
            continue
        for method in row["methods"].split(","):
            pages.append({
                "route_id": row["route_id"],
                "method": method,
                "path": row["path"],
                "endpoint": row["endpoint"],
                "source": row["source"],
                "disposition": "phase6_web_page_shell",
                "migration_status": "pending",
            })
    pages.sort(key=lambda item: (item["path"], item["method"], item["route_id"]))
    if len(pages) != 21:
        raise AssertionError("Phase 4C page-shell operation count drifted")
    return pages


def _validate_partition(
    rows: list[dict[str, str]],
    operation_map: dict[tuple[str, str], dict[str, str]],
) -> None:
    groups = (
        TRANSACTION_WRITES,
        PROGRESS_AND_TAGS,
        SELECTION_SEARCH_AND_COUNT,
        STATISTICS_AND_DATA_CENTER,
        MIGRATED_USER_COUNTS,
        CROSS_DOMAIN_TRANSFERS,
    )
    flattened = [item for group in groups for item in group]
    if len(flattened) != len(set(flattened)):
        raise AssertionError("Phase 4C route-scope groups overlap")
    if tuple(map(len, groups)) != (9, 11, 9, 16, 2, 3):
        raise AssertionError("Phase 4C route-scope group cardinality drifted")
    for key in flattened:
        if key not in operation_map:
            raise AssertionError(f"Phase 4C route-scope key is missing: {key}")

    target_learning = {
        (row["route_id"], method)
        for row in rows
        if row["target_module"] == "learning"
        for method in row["methods"].split(",")
    }
    page_keys = {
        (item["route_id"], item["method"])
        for item in _page_operations(rows)
    }
    expected_baseline_learning = (
        set(TRANSACTION_WRITES)
        | set(PROGRESS_AND_TAGS)
        | (
            set(SELECTION_SEARCH_AND_COUNT)
            - {("c618fb5f9f97", "GET"), ("bb21e7730d04", "GET")}
        )
        | set(STATISTICS_AND_DATA_CENTER)
        | set(CROSS_DOMAIN_TRANSFERS)
        | page_keys
    )
    if len(target_learning) != 67 or target_learning != expected_baseline_learning:
        raise AssertionError("Phase 4C baseline learning operation partition drifted")


def document_payload_sha256(document: dict[str, Any]) -> str:
    normalized = dict(document)
    normalized.pop("document_payload_sha256", None)
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload)


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    predecessor = predecessor_acceptance.load_contract(resolved_root)
    predecessor_payload = _read_regular(resolved_root, PREDECESSOR_RELATIVE)
    if (
        len(predecessor_payload) != PREDECESSOR_BYTE_COUNT
        or _sha256(predecessor_payload) != PREDECESSOR_SHA256
        or predecessor.get("document_payload_sha256")
        != PREDECESSOR_PAYLOAD_SHA256
    ):
        raise AssertionError("Phase 4C route-scope predecessor drifted")

    rows, matrix_payload = _matrix_rows(resolved_root)
    operation_map = _expanded(rows)
    _validate_partition(rows, operation_map)

    groups = {
        "transaction_writes": _describe(
            operation_map, TRANSACTION_WRITES, "transaction_writes", "learning"
        ),
        "progress_and_tags": _describe(
            operation_map, PROGRESS_AND_TAGS, "progress_and_tags", "learning"
        ),
        "selection_search_and_count": _describe(
            operation_map,
            SELECTION_SEARCH_AND_COUNT,
            "selection_search_and_count",
            "learning",
        ),
        "statistics_and_data_center": _describe(
            operation_map,
            STATISTICS_AND_DATA_CENTER,
            "statistics_and_data_center",
            "learning",
        ),
    }
    migrated = _describe(
        operation_map,
        MIGRATED_USER_COUNTS,
        "migrated_personal_bank_user_counts",
        "learning",
    )
    transfers = _describe(
        operation_map,
        CROSS_DOMAIN_TRANSFERS,
        "cross_domain_transfer",
        "mixed",
    )
    for item in transfers:
        item["effective_owner"] = (
            "intelligence"
            if item["route_id"] == "1156cacff587"
            else "assessment"
        )
        item["disposition"] = "transfer_out_of_phase4c_learning_implementation"

    transaction_semantics = {
        "favorite_aliases": {
            "route_ids": ["6d548bfd6830", "b52d3008d4d1"],
            "shared_legacy_handler": "toggle_favorite",
            "rate_limit": "30/minute",
            "owner_tables": ["favorites"],
            "catalog_precondition": "question exists and subject access is allowed",
            "target_atomicity": "toggle row and publish cache invalidation only after commit",
        },
        "answer_aliases": {
            "route_ids": ["87bb4fb340c8", "67dccafb3ea4"],
            "shared_legacy_handler": "record_result",
            "rate_limit": "60/minute",
            "owner_tables": ["mistakes", "user_answers", "user_quiz_stats"],
            "target_atomicity": (
                "mistake transition, answer append, quota increment and idempotency "
                "receipt commit in one learning transaction"
            ),
            "legacy_without_idempotency_key": (
                "preserve one logical attempt per accepted HTTP request"
            ),
            "target_optional_idempotency_key": {
                "header": "Idempotency-Key",
                "same_actor_same_key_same_payload": "replay first committed response",
                "same_actor_same_key_different_payload": "409 conflict",
                "concurrent_same_key": "one commit; wait or replay; never double count",
                "persistence": "PostgreSQL learning-owned durable receipt",
            },
        },
        "study_learning": {
            "route_ids": ["bf3cb0c4f9ab"],
            "owner_tables": [
                "study_learning", "study_review", "mistakes", "user_bank_mistakes"
            ],
            "target_atomicity": (
                "streak/counters, mistake transition and first due-review creation "
                "commit together"
            ),
        },
        "study_review": {
            "route_ids": ["c797832c43db", "278e1eac5eb4"],
            "owner_tables": ["study_review"],
            "target_atomicity": "review level/due date or mastered state commits once",
        },
        "checkin": {
            "route_ids": ["59c9c7366ec3"],
            "owner_tables": ["user_checkins"],
            "natural_idempotency_key": ["user_id", "Asia/Shanghai local date"],
            "concurrency": "unique conflict resolves to the already committed checkin",
        },
        "question_edit": {
            "route_ids": ["624b5ac217d0"],
            "route_orchestrator": "learning compatibility HTTP boundary",
            "persistent_owner": "catalog",
            "required_dependency": "learning -> catalog::api",
            "forbidden": "learning SQL against questions",
        },
    }

    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": (
            "route_scope_partition_closed_transaction_write_golden_capture_only_"
            "implementation_route_promotion_and_cutover_unauthorized"
        ),
        "scope": "phase4c-learning-route-scope-and-ordered-execution-entry",
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "contract_id": predecessor["contract_id"],
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "fixed_d0_commit": "19db389aacad439f63cb93b930bea20ddd31f5e8",
            "fixed_d1_commit": "aff3c9e8d6b1ed33dc0a050c0e435572cddd51db",
            "fixed_d2_commit": "2579dfd344dbe318c9fb59d067c843356b98fece",
            "immutable": True,
        },
        "frozen_route_authority": {
            "source": MATRIX_RELATIVE,
            "sha256": _sha256(matrix_payload),
            "rule_count": 592,
            "operation_count": 611,
            "baseline_learning_operation_count": 67,
        },
        "phase4c_partition": {
            "total_operation_count": 71,
            "phase6_page_shell_operation_count": 21,
            "cross_domain_transfer_operation_count": 3,
            "learning_backend_operation_count": 47,
            "already_migrated_learning_operation_count": 2,
            "remaining_learning_operation_count": 45,
            "ordered_remaining_group_counts": [9, 11, 9, 16],
            "final_route_target": {
                "migrated": 58,
                "pending": 553,
                "production_cutover": 0,
            },
        },
        "ordered_learning_groups": groups,
        "already_migrated": migrated,
        "page_shells": _page_operations(rows),
        "cross_domain_transfers": transfers,
        "transaction_write_semantics": transaction_semantics,
        "legacy_source_authority": {
            "commit_oid": LEGACY_COMMIT,
            "transport_for_next_capture": (
                "read-only git archive of the fixed commit into a temporary directory"
            ),
            "source_sha256": LEGACY_SOURCE_SHA256,
            "live_worktree_is_not_authority": True,
        },
        "module_boundary": {
            "learning_owned_tables": [
                "favorites", "mistakes", "study_learning", "study_review",
                "user_answers", "user_bank_answers", "user_bank_favorites",
                "user_bank_mistakes", "user_checkins", "user_progress",
                "user_question_tag_items", "user_quiz_stats",
            ],
            "catalog_owned_tables": ["questions", "subjects"],
            "learning_may_call": [
                "catalog::api", "identity::api", "personalbank::api"
            ],
            "learning_direct_catalog_table_write_forbidden": True,
            "cross_module_database_transaction_forbidden": True,
        },
        "next_gate": {
            "name": "transaction-write fixed-commit golden and invariants",
            "exact_operation_count": 9,
            "required_evidence": [
                "complete fixed-commit app archive",
                "active caller attestation",
                "authentication, CSRF and rate-limit matrix",
                "request and response parity",
                "isolated database before/after fingerprints",
                "SQL and transaction trace",
                "duplicate and concurrent request outcomes",
                "rollback and retry boundaries",
            ],
            "implementation_authorized": False,
            "production_schema_or_flyway_authorized": False,
            "route_or_openapi_delta_authorized": False,
            "production_cutover_authorized": False,
        },
        "authorization": {
            "route_scope_partition_closed": True,
            "transaction_write_golden_capture_authorized": True,
            "transaction_write_implementation_authorized": False,
            "progress_and_tags_implementation_authorized": False,
            "selection_search_and_count_implementation_authorized": False,
            "statistics_and_data_center_implementation_authorized": False,
            "production_schema_or_index": False,
            "flyway_baseline_or_migration": False,
            "real_data_migration_execution": False,
            "legacy_runtime_permanently_disabled": False,
            "route_or_openapi_delta": False,
            "client_gateway_or_proxy_change": False,
            "production_cutover": False,
        },
        "route_state": {
            "total_operation_count": 611,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "legacy_flask_remains_production_owner": True,
        },
        "control_plane": {
            "bootstrap": True,
            "current_control_sources_external_git_anchor_complete": False,
            "self_signed": False,
            "closes_no_business_implementation_gate": True,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    payload = serialized_contract(build_contract())
    if arguments.check:
        if not arguments.output.is_file() or arguments.output.read_bytes() != payload:
            raise SystemExit("Phase 4C learning route-scope contract drifted")
        return 0
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
