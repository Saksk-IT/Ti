#!/usr/bin/env python3
"""Fail-closed successor acceptance for transaction-write full parity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:
    from tools import build_phase4c_learning_transaction_write_http_full_parity_contract as builder
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_learning_transaction_write_http_full_parity_contract",
    }:
        raise
    import build_phase4c_learning_transaction_write_http_full_parity_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "40b38a443d7f7d754cc42ce43fa854b0c3c18dc66f4920a2f07d451601d6d1db"
CONTRACT_PAYLOAD_SHA256 = (
    "83ca7d51d768540ed744830c74f07eb1fd1f63db88c293ea4ec83e41d6a6c1e1"
)
CONTRACT_BYTE_COUNT = 15_604


def _read_contract(root: Path) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if (
        CONTRACT_BYTE_COUNT < 0
        or len(payload) != CONTRACT_BYTE_COUNT
        or builder.sha256_bytes(payload) != CONTRACT_SHA256
    ):
        raise AssertionError(
            "transaction-write full-parity contract physical bytes drifted"
        )
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(
            "transaction-write full-parity contract is unreadable"
        ) from error
    if not isinstance(document, dict):
        raise AssertionError(
            "transaction-write full-parity contract is not an object"
        )
    if (
        document.get("schema_version") != 1
        or document.get("contract_id") != builder.CONTRACT_ID
        or document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError(
            "transaction-write full-parity contract envelope drifted"
        )
    return document


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    resolved_root = root.resolve(strict=True)
    if document != builder.build_contract(resolved_root):
        raise AssertionError(
            "transaction-write full-parity deterministic rebuild drifted"
        )
    if document.get("status") != builder.STATUS:
        raise AssertionError("transaction-write full-parity status drifted")
    predecessor = document.get("predecessor", {})
    if (
        predecessor.get("node_d_contract")
        != {**builder.NODE_D_CONTRACT, "immutable": True}
        or predecessor.get("node_d_external_anchor")
        != {**builder.NODE_D_ANCHOR, "immutable": True}
        or predecessor.get("fixed_checkpoint") != builder.BASE_CHECKPOINT
    ):
        raise AssertionError(
            "transaction-write full-parity predecessor drifted"
        )
    if document.get("implementation_checkpoint") != builder.IMPLEMENTATION_CHECKPOINT:
        raise AssertionError(
            "transaction-write full-parity checkpoint drifted"
        )
    historical = document.get("historical_source_successors", {})
    expected_transitions = {
        relative: {"source": relative, **transition}
        for relative, transition in builder.SOURCE_TRANSITIONS.items()
    }
    if (
        historical.get("accepted_checkpoint")
        != builder.BASE_CHECKPOINT["commit_oid"]
        or historical.get("successor_checkpoint")
        != builder.IMPLEMENTATION_CHECKPOINT["commit_oid"]
        or historical.get("transition_count") != len(builder.SOURCE_TRANSITIONS)
        or historical.get("transitions") != expected_transitions
        or historical.get("dynamic_source_discovery") is not False
        or historical.get("unknown_path") != "reject"
    ):
        raise AssertionError(
            "transaction-write full-parity source successors drifted"
        )
    evidence = document.get("fixed_evidence", {})
    if (
        evidence.get("artifact_count") != len(builder.EVIDENCE_FILES)
        or evidence.get("real_random_port_tomcat_full_filter_chain") is not True
        or evidence.get("target_session_flask_session_and_bearer_to_controller")
        is not True
        or evidence.get("redis_7_4_atomicity_outage_and_recovery") is not True
        or evidence.get("postgresql_versions") != ["16.14", "18.4"]
        or evidence.get("users_last_active_business_dml_count") != 0
        or evidence.get("openapi_3_1_2_exact_operation_count") != 9
        or evidence.get("worm_chain_node_count") != 10
    ):
        raise AssertionError(
            "transaction-write full-parity evidence drifted"
        )
    parity = document.get("parity", {})
    if (
        parity.get("operation_count") != 9
        or any(
            parity.get(field) is not True
            for field in (
                "target_execution_complete",
                "authentication_execution_complete",
                "http_and_cors_complete",
                "idempotency_complete",
                "redis_complete",
                "postgresql_16_14_and_18_4_complete",
                "openapi_complete",
                "worm_complete",
                "full_target_parity_closed",
            )
        )
    ):
        raise AssertionError("transaction-write full-parity claim drifted")
    authorization = document.get("authorization", {})
    if (
        authorization.get(
            "bootstrap_control_sources_external_git_anchor_complete"
        )
        is not False
        or authorization.get("route_migration_eligible") is not False
        or authorization.get("nine_transaction_write_operations_migrated")
        is not False
        or any(
            authorization.get(field) is not False
            for field in (
                "route_or_openapi_delta",
                "production_cutover",
                "production_schema_execution",
                "real_data_migration_execution",
                "client_change",
                "gateway_or_proxy_change",
            )
        )
    ):
        raise AssertionError(
            "transaction-write full-parity authorization drifted"
        )
    if document.get("route_state") != {
        "total_operation_count": 611,
        "migrated_operation_count": 13,
        "pending_operation_count": 598,
        "production_cutover_operation_count": 0,
        "implemented_pending_operation_count": 9,
    }:
        raise AssertionError("transaction-write full-parity route state drifted")
    authority = document.get("source_authority", {})
    if (
        authority.get("control_source_count") != len(builder.CONTROL_SOURCES)
        or authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or authority.get("control_sources_excluded_from_self_authority")
        is not True
        or authority.get("fixed_transition_allowlist_exact") is not True
        or authority.get("ordinary_build_is_gitless") is not True
        or authority.get("live_head_main_or_origin_authority") is not False
        or authority.get("historical_contracts_or_worm_overwritten") is not False
    ):
        raise AssertionError(
            "transaction-write full-parity source authority drifted"
        )


def load(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    document = _read_contract(resolved_root)
    validate(document, resolved_root)
    return document


def load_node_d_predecessor(root: Path = ROOT) -> dict[str, Any]:
    """Validate current successors and return the immutable Node D document."""
    resolved_root = root.resolve(strict=True)
    load(resolved_root)
    return builder.read_fixed_json(resolved_root, builder.NODE_D_CONTRACT)


def source_transition(
    root: Path, relative: str
) -> dict[str, Any] | None:
    transition = builder.SOURCE_TRANSITIONS.get(relative)
    if transition is None:
        return None
    resolved_root = root.resolve(strict=True)
    document = load(resolved_root)
    actual = document["historical_source_successors"]["transitions"].get(
        relative
    )
    expected = {"source": relative, **transition}
    if actual != expected:
        raise AssertionError(
            f"transaction-write full-parity transition drifted: {relative}"
        )
    payload = builder.fixed_regular_file(resolved_root, relative).read_bytes()
    if (
        len(payload) != transition["successor_byte_count"]
        or builder.sha256_bytes(payload) != transition["successor_sha256"]
    ):
        raise AssertionError(
            f"transaction-write full-parity transition bytes drifted: {relative}"
        )
    return dict(expected)


def transition_from_node_d(
    root: Path,
    relative: str,
    accepted_sha256: str,
    accepted_byte_count: int,
) -> dict[str, Any] | None:
    transition = source_transition(root, relative)
    if transition is None:
        return None
    if (
        transition["accepted_sha256"] != accepted_sha256
        or transition["accepted_byte_count"] != accepted_byte_count
    ):
        raise AssertionError(
            f"transaction-write full-parity Node D origin drifted: {relative}"
        )
    return transition


def accepted_sha256(relative: str) -> str | None:
    transition = builder.SOURCE_TRANSITIONS.get(relative)
    return None if transition is None else str(transition["accepted_sha256"])


def successor_sha256(root: Path, relative: str) -> str | None:
    transition = source_transition(root, relative)
    return None if transition is None else str(transition["successor_sha256"])


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                CONTRACT_RELATIVE,
                builder.NODE_D_CONTRACT["source"],
                builder.NODE_D_ANCHOR["source"],
                *builder.node_d.SOURCE_FILES,
                *builder.SOURCE_TRANSITIONS,
                *builder.EVIDENCE_FILES,
            )
        )
    )


def contract_envelope(root: Path = ROOT) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    document = json.loads(payload)
    if document != builder.build_contract(root):
        raise AssertionError(
            "transaction-write full-parity final contract is not deterministic"
        )
    return {
        "contract_sha256": builder.sha256_bytes(payload),
        "contract_payload_sha256": builder.payload_sha256(document),
        "contract_byte_count": len(payload),
    }


def main() -> None:
    document = load()
    print(
        json.dumps(
            {
                "accepted": True,
                "contract_id": document["contract_id"],
                "full_target_parity_closed": document["parity"][
                    "full_target_parity_closed"
                ],
                "route_migration_eligible": document["authorization"][
                    "route_migration_eligible"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
