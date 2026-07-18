#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C user-counts route successor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from tools import build_phase4c_personal_bank_user_counts_route_promotion_contract as builder
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_route_promotion_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "e5bc53bb8c011c5cf2f08447543aa3e5dd2a045b6226f064c6594a3639d7b5c9"
CONTRACT_PAYLOAD_SHA256 = "1503c4dd5905abb70a77835e6602d8e51a7f042f5eed6b0a25a9a0de4b5f6e0f"
CONTRACT_BYTE_COUNT = 4_365


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    if document.get("schema_version") != 1 or document.get("contract_id") != builder.CONTRACT_ID:
        raise AssertionError("route promotion contract identity drifted")
    if (
        document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError("route promotion contract payload drifted")

    parity = document.get("parity")
    for field in (
        "pg16_pg18_termination_fingerprints_complete",
        "real_tomcat_complete_response_header_matrix_complete",
        "same_service_redis_outage_and_recovery_complete",
        "full_target_parity_closed",
        "route_migration_eligible",
    ):
        if not isinstance(parity, dict) or parity.get(field) is not True:
            raise AssertionError(f"route promotion prerequisite drifted: {field}")

    authority = document.get("route_authority")
    if not isinstance(authority, dict):
        raise AssertionError("route promotion authority is absent")
    if authority.get("sources") != builder.SOURCES:
        raise AssertionError("route promotion sources drifted")
    if authority.get("promoted_routes") != list(builder.ROUTES):
        raise AssertionError("route promotion route set drifted")
    if authority.get("historical_matrix_and_deltas_overwritten") is not False:
        raise AssertionError("route promotion overwrites history")
    if authority.get("effective_status") != {
        "source": builder.EFFECTIVE_RELATIVE,
        "sha256": builder.EFFECTIVE_SHA256,
        "document_payload_sha256": builder.EFFECTIVE_PAYLOAD_SHA256,
        "byte_count": builder.EFFECTIVE_BYTE_COUNT,
    }:
        raise AssertionError("route promotion effective status descriptor drifted")

    authorization = document.get("authorization")
    if not isinstance(authorization, dict):
        raise AssertionError("route promotion authorization is absent")
    if authorization.get("two_legacy_get_routes_migrated") is not True:
        raise AssertionError("route promotion is not authorized")
    if authorization.get("derived_head_and_options_count_as_migrated") is not False:
        raise AssertionError("route promotion counts derived operations")
    for field in (
        "production_cutover",
        "operator_migration_implementation",
        "production_schema_or_index",
        "real_data_migration_execution",
        "client_change",
        "gateway_or_proxy_change",
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"route promotion overclaims forbidden action: {field}")
    if document.get("route_state") != {
        "total_operation_count": 611,
        "migrated_operation_count": 13,
        "pending_operation_count": 598,
        "production_cutover_operation_count": 0,
    }:
        raise AssertionError("route promotion effective counts drifted")

    source_authority = document.get("source_authority")
    if (
        not isinstance(source_authority, dict)
        or source_authority.get("control_source_count") != 6
        or source_authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or source_authority.get("excluded_from_self_authority") is not True
        or source_authority.get("historical_contracts_and_worm_overwritten") is not False
    ):
        raise AssertionError("route promotion source-authority boundary drifted")
    if document != builder.build_contract(root):
        raise AssertionError("route promotion deterministic rebuild drifted")


def load(root: Path = ROOT) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if len(payload) != CONTRACT_BYTE_COUNT or builder.sha256_bytes(payload) != CONTRACT_SHA256:
        raise AssertionError("route promotion contract physical bytes drifted")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError("route promotion contract is unreadable") from error
    if not isinstance(document, dict):
        raise AssertionError("route promotion contract is not an object")
    validate(document, root)
    return document


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(dict.fromkeys((
        CONTRACT_RELATIVE,
        builder.EFFECTIVE_RELATIVE,
        *(descriptor["source"] for descriptor in builder.SOURCES.values()),
    )))


if __name__ == "__main__":
    accepted = load()
    print(json.dumps({
        "accepted": True,
        "migrated": accepted["route_state"]["migrated_operation_count"],
        "pending": accepted["route_state"]["pending_operation_count"],
        "production_cutover": accepted["authorization"]["production_cutover"],
    }, sort_keys=True))
