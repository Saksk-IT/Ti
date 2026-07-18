#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C full-parity bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from tools import build_phase4c_personal_bank_user_counts_http_full_parity_contract as builder
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_http_full_parity_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "13df3a1f81ca909d62e89495564215e92a757e41889aa91658db55e33717b787"
CONTRACT_PAYLOAD_SHA256 = "7eecb6279b2e2b5532dab21c171b9fca3a7bb6129ff2f4dff3bfcf7941196da2"
CONTRACT_BYTE_COUNT = 7_477


def _read_contract(root: Path) -> tuple[bytes, dict[str, Any]]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if len(payload) != CONTRACT_BYTE_COUNT or builder.sha256_bytes(payload) != CONTRACT_SHA256:
        raise AssertionError("full parity contract physical bytes drifted")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError("full parity contract is unreadable") from error
    if not isinstance(document, dict):
        raise AssertionError("full parity contract is not an object")
    return payload, document


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    if document.get("schema_version") != 1:
        raise AssertionError("full parity schema version drifted")
    if document.get("contract_id") != builder.CONTRACT_ID:
        raise AssertionError("full parity contract identity drifted")
    if document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256:
        raise AssertionError("full parity payload declaration drifted")
    if builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256:
        raise AssertionError("full parity payload hash drifted")

    parity = document.get("parity")
    if not isinstance(parity, dict):
        raise AssertionError("full parity evidence is absent")
    for field in (
        "pg16_pg18_termination_fingerprints_complete",
        "real_tomcat_complete_response_header_matrix_complete",
        "same_service_redis_outage_and_recovery_complete",
        "full_target_parity_closed",
        "all_required_parity_prerequisites_true",
        "typed_parity_review_complete",
    ):
        if parity.get(field) is not True:
            raise AssertionError(f"full parity prerequisite is not closed: {field}")

    verification = document.get("verification")
    expected_verification = {
        "targeted_failsafe_tests": 13,
        "targeted_failures_errors_skipped": 0,
        "full_surefire_tests": 709,
        "full_failsafe_tests": 167,
        "full_failures_errors_skipped": 0,
        "testcontainers_remaining_after_verification": 0,
    }
    if not isinstance(verification, dict) or any(
        verification.get(key) != value
        for key, value in expected_verification.items()
    ):
        raise AssertionError("full parity verification totals drifted")
    if verification.get("heavy_verify_lock_held_for_all_maven_testcontainers_docker") is not True:
        raise AssertionError("full parity heavy verification lock evidence is absent")

    integration = document.get("worker_integration")
    if not isinstance(integration, dict) or integration.get("lane_count") != 3:
        raise AssertionError("full parity Worker integration count drifted")
    if integration.get("artifact_count") != len(builder.ARTIFACTS):
        raise AssertionError("full parity artifact count drifted")
    lanes = integration.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != set(builder.WORKERS):
        raise AssertionError("full parity Worker lane set drifted")
    for lane, expected in builder.WORKERS.items():
        actual = lanes[lane]
        if (
            actual.get("base_sha") != builder.BASE_SHA
            or actual.get("branch") != expected["branch"]
            or actual.get("implementation_commit") != expected["implementation_commit"]
            or actual.get("handoff_commit") != expected["handoff_commit"]
            or actual.get("integrated_paths") != list(expected["paths"])
            or actual.get("central_authority_files_modified_by_worker") is not False
            or actual.get("handoff_file_integrated_into_main") is not False
            or actual.get(expected["evidence"]) is not True
        ):
            raise AssertionError(f"full parity Worker declaration drifted: {lane}")

    authorization = document.get("authorization")
    if not isinstance(authorization, dict):
        raise AssertionError("full parity authorization is absent")
    if authorization.get("current_bootstrap_sources_external_git_anchor_complete") is not False:
        raise AssertionError("full parity bootstrap overclaims external provenance")
    if authorization.get("route_migration_eligible") is not False:
        raise AssertionError("full parity bootstrap overclaims route eligibility")
    for forbidden in (
        "two_legacy_get_routes_migrated",
        "production_cutover",
        "operator_migration_implementation",
        "production_schema_or_index",
        "real_data_migration_execution",
        "client_change",
        "gateway_or_proxy_change",
    ):
        if authorization.get(forbidden) is not False:
            raise AssertionError(f"full parity bootstrap overclaims forbidden action: {forbidden}")

    route = document.get("route_state")
    if route != {
        "total_operation_count": 611,
        "migrated_operation_count": 11,
        "pending_operation_count": 600,
        "production_cutover_operation_count": 0,
        "implemented_pending_get_count": 2,
        "derived_head_and_options_count_as_operations": False,
    }:
        raise AssertionError("full parity bootstrap route state drifted")

    authority = document.get("source_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("control_source_count") != len(builder.CONTROL_SOURCES)
        or authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or authority.get("excluded_from_self_authority") is not True
        or authority.get("historical_contracts_and_worm_overwritten") is not False
    ):
        raise AssertionError("full parity source-authority boundary drifted")

    if document != builder.build_contract(root):
        raise AssertionError("full parity deterministic rebuild drifted")


def load(root: Path = ROOT) -> dict[str, Any]:
    _, document = _read_contract(root)
    validate(document, root)
    return document


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(dict.fromkeys((CONTRACT_RELATIVE, builder.PREDECESSOR["source"], *builder.ARTIFACTS)))


if __name__ == "__main__":
    accepted = load()
    print(json.dumps({
        "accepted": True,
        "contract_id": accepted["contract_id"],
        "full_target_parity_closed": accepted["parity"]["full_target_parity_closed"],
        "route_migration_eligible": accepted["authorization"]["route_migration_eligible"],
    }, sort_keys=True))
