#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C full-parity Git anchor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from tools import build_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract as builder
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "77c15295db2addf223ac425dfbbde687c4be3685fd6c6a9b842db7a238b58836"
CONTRACT_PAYLOAD_SHA256 = "eb76c6bf825b4efe0ad6d1ed0a1d2fa02eb1025226c9168c6fe42108dc4ff816"
CONTRACT_BYTE_COUNT = 14_885


def validate_git_checkpoint(repository_root: Path) -> None:
    builder.validate_git_checkpoint(repository_root)


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    if document.get("schema_version") != 1 or document.get("contract_id") != builder.CONTRACT_ID:
        raise AssertionError("full parity anchor identity drifted")
    if (
        document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError("full parity anchor payload drifted")

    checkpoint = document.get("git_checkpoint")
    if not isinstance(checkpoint, dict):
        raise AssertionError("full parity anchor checkpoint is absent")
    expected_checkpoint = {
        "commit_oid": builder.GIT_COMMIT_OID,
        "parent_oid": builder.GIT_PARENT_OID,
        "root_tree_oid": builder.GIT_ROOT_TREE_OID,
        "ti_java_tree_oid": builder.GIT_TI_JAVA_TREE_OID,
        "raw_delta_sha256": builder.GIT_RAW_DELTA_SHA256,
        "changed_path_count": 15,
        "added_path_count": 12,
        "modified_path_count": 3,
    }
    if any(checkpoint.get(key) != value for key, value in expected_checkpoint.items()):
        raise AssertionError("full parity anchor checkpoint metadata drifted")
    if checkpoint.get("exact_changed_paths") != list(builder.CHECKPOINT):
        raise AssertionError("full parity anchor changed path list drifted")
    if checkpoint.get("artifacts") != builder.CHECKPOINT:
        raise AssertionError("full parity anchor artifact descriptors drifted")

    source_anchor = document.get("full_parity_source_anchor")
    if not isinstance(source_anchor, dict):
        raise AssertionError("full parity source anchor is absent")
    if (
        source_anchor.get("source_count") != 6
        or source_anchor.get("source_paths") != list(builder.BOOTSTRAP_SOURCES)
        or set(source_anchor.get("artifacts", {})) != set(builder.BOOTSTRAP_SOURCES)
        or source_anchor.get("predecessor_bootstrap_sources_external_git_anchor_complete") is not True
        or source_anchor.get("current_anchor_sources_excluded_from_self_authority") is not True
        or source_anchor.get("current_anchor_source_bytes_external_git_anchor_complete") is not False
    ):
        raise AssertionError("full parity source anchor boundary drifted")

    parity = document.get("parity")
    for field in (
        "pg16_pg18_termination_fingerprints_complete",
        "real_tomcat_complete_response_header_matrix_complete",
        "same_service_redis_outage_and_recovery_complete",
        "full_target_parity_closed",
        "typed_parity_review_complete",
    ):
        if not isinstance(parity, dict) or parity.get(field) is not True:
            raise AssertionError(f"full parity anchor prerequisite drifted: {field}")

    authorization = document.get("authorization")
    if not isinstance(authorization, dict):
        raise AssertionError("full parity anchor authorization is absent")
    if authorization.get(
        "full_parity_checkpoint_and_six_excluded_sources_external_git_anchor_complete"
    ) is not True:
        raise AssertionError("full parity bootstrap sources are not externally anchored")
    if authorization.get("route_migration_eligible") is not True:
        raise AssertionError("full parity anchor route eligibility is absent")
    for field in (
        "two_legacy_get_routes_migrated",
        "production_cutover",
        "operator_migration_implementation",
        "production_schema_or_index",
        "real_data_migration_execution",
        "client_change",
        "gateway_or_proxy_change",
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"full parity anchor overclaims forbidden action: {field}")

    if document.get("route_state") != {
        "total_operation_count": 611,
        "migrated_operation_count": 11,
        "pending_operation_count": 600,
        "production_cutover_operation_count": 0,
        "implemented_pending_get_count": 2,
    }:
        raise AssertionError("full parity anchor route state drifted")

    authority = document.get("source_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("control_source_count") != 6
        or authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or authority.get("excluded_from_self_authority") is not True
        or authority.get("historical_contracts_and_worm_overwritten") is not False
    ):
        raise AssertionError("full parity anchor source-authority boundary drifted")
    if document != builder.build_contract(root):
        raise AssertionError("full parity anchor deterministic rebuild drifted")


def load(root: Path = ROOT) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if len(payload) != CONTRACT_BYTE_COUNT or builder.sha256_bytes(payload) != CONTRACT_SHA256:
        raise AssertionError("full parity anchor contract physical bytes drifted")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError("full parity anchor contract is unreadable") from error
    if not isinstance(document, dict):
        raise AssertionError("full parity anchor contract is not an object")
    validate(document, root)
    return document


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(dict.fromkeys((CONTRACT_RELATIVE, builder.PREDECESSOR["source"], *builder.BOOTSTRAP_SOURCES)))


if __name__ == "__main__":
    accepted = load()
    print(json.dumps({
        "accepted": True,
        "commit_oid": accepted["git_checkpoint"]["commit_oid"],
        "full_target_parity_closed": accepted["parity"]["full_target_parity_closed"],
        "route_migration_eligible": accepted["authorization"]["route_migration_eligible"],
    }, sort_keys=True))
