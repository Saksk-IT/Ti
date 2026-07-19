#!/usr/bin/env python3
"""Gitless acceptance for the Phase 4C Node B design contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from tools import (
        build_phase4c_tag_migration_durable_ledger_freeze_design_contract
        as builder,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import build_phase4c_tag_migration_durable_ledger_freeze_design_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
EXPECTED_CONTRACT_SHA256 = (
    "995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041"
)
EXPECTED_DOCUMENT_PAYLOAD_SHA256 = (
    "fba73f917a285b85cb8fcd7afd22a94f60bac960beb508f173caf0ea96079ffa"
)
EXPECTED_CONTRACT_BYTE_COUNT = 23_110


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if (
        len(payload) != EXPECTED_CONTRACT_BYTE_COUNT
        or builder.sha256_bytes(payload) != EXPECTED_CONTRACT_SHA256
    ):
        raise AssertionError("Node B design contract fixed bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("Node B design contract must be a JSON object")
    if (
        document.get("document_payload_sha256")
        != EXPECTED_DOCUMENT_PAYLOAD_SHA256
        or builder.document_payload_sha256(document)
        != EXPECTED_DOCUMENT_PAYLOAD_SHA256
    ):
        raise AssertionError("Node B design contract payload identity drifted")
    expected = builder.build_contract(root)
    if document != expected or payload != builder.serialized_contract(expected):
        raise AssertionError("Node B design contract differs from gitless builder")
    validate_contract(document)
    return document


def validate_contract(document: dict[str, Any]) -> None:
    if (
        document.get("contract_id") != builder.CONTRACT_ID
        or document.get("captured_at") != builder.CAPTURED_AT
        or document.get("scope") != builder.SCOPE
        or document.get("status") != builder.STATUS
    ):
        raise AssertionError("Node B design contract identity drifted")
    predecessor = document.get("predecessor", {})
    if (
        predecessor.get("source") != builder.PREDECESSOR_RELATIVE
        or predecessor.get("sha256") != builder.PREDECESSOR_SHA256
        or predecessor.get("byte_count") != builder.PREDECESSOR_BYTE_COUNT
        or predecessor.get("document_payload_sha256")
        != builder.PREDECESSOR_PAYLOAD_SHA256
    ):
        raise AssertionError("Node B design predecessor drifted")
    git = document.get("node_a_git_authority", {})
    if (
        git.get("implementation_checkpoint")
        != builder.NODE_A_IMPLEMENTATION_CHECKPOINT
        or git.get("external_anchor_checkpoint")
        != builder.NODE_A_EXTERNAL_ANCHOR_CHECKPOINT
        or git.get("ordinary_build_requires_git") is not False
        or git.get("live_head_or_ref_used") is not False
    ):
        raise AssertionError("Node B fixed Node A Git authority drifted")
    state = document.get("durable_ledger_design", {}).get("state_machine", {})
    if (
        state.get("states") != list(builder.STATES)
        or state.get("transitions") != list(builder.TRANSITIONS)
        or state.get("initial_state") != "PLANNED"
        or state.get("initial_version") != 0
        or state.get("terminal_states") != ["APPLIED", "BLOCKED"]
        or state.get("applied_transition_immediate_complete_disposition_guard")
        is not True
        or state.get("applied_transition_deferred_commit_guard") is not True
        or state.get("zero_receipt_applied_transition_allowed") is not False
        or state.get("unexplained_zero_target_applied_transition_allowed")
        is not False
        or state.get("all_empty_noop_with_explicit_receipts_allowed") is not True
    ):
        raise AssertionError("Node B durable-ledger state machine drifted")
    durable = document.get("durable_ledger_design", {})
    receipt = durable.get("receipt_protocol", {})
    target = durable.get("target_fact_digest_protocol", {})
    if (
        durable.get("migration_id_storage_type") != "uuid"
        or durable.get("arbitrary_text_migration_id_storable") is not False
        or receipt.get("frozen_source_scope")
        != "all_test_fixture_source_rows"
        or receipt.get("every_frozen_source_has_exactly_one_receipt") is not True
        or receipt.get("empty_noop_requires_explicit_receipt") is not True
        or receipt.get("empty_noop_requires_zero_target_rows") is not True
        or receipt.get("material_disposition_requires_positive_target_rows")
        is not True
    ):
        raise AssertionError("Node B disposition completeness drifted")
    if (
        target.get("domain_separator")
        != "ti:phase4c:tag-migration:canonical-target-facts:v1"
        or target.get("caller_supplied_target_fact_digest_column_present")
        is not False
        or target.get("postgresql_recomputes_digest_from_canonical_facts")
        is not True
        or target.get("applied_transition_compares_canonical_digest_to_ledger")
        is not True
        or target.get(
            "applied_transition_compares_canonical_digest_to_all_receipts"
        )
        is not True
        or target.get("java_recovery_independently_recomputes_canonical_digest")
        is not True
        or target.get("wrong_facts_cannot_be_masked_by_caller_digest") is not True
    ):
        raise AssertionError("Node B canonical target-fact digest drifted")
    retry = document.get("retry_and_ambiguity_design", {})
    if (
        retry.get("retryable_sqlstates") != list(builder.RETRYABLE_SQLSTATES)
        or retry.get("maximum_attempts") != 3
        or retry.get("maximum_retries") != 2
        or retry.get("non_retryable_sqlstate_attempts") != 1
        or retry.get("non_retryable_sqlstate_retries") != 0
        or retry.get("real_postgresql_40001_traversed_retry_loop") is not True
        or retry.get("real_postgresql_40P01_traversed_retry_loop") is not True
        or retry.get("ack_discard_fixture_is_real_network_failure") is not False
        or retry.get("real_network_commit_ack_loss_evidenced") is not False
        or retry.get("production_retry_implementation_present") is not False
    ):
        raise AssertionError("Node B retry/ambiguity boundary drifted")
    authorization = document.get("authorization", {})
    if authorization.get("newly_closed_gates") != [
        "migration_durable_ledger_freeze_design_evidence_closed"
    ]:
        raise AssertionError("Node B newly closed gate drifted")
    if (
        authorization.get("migration_global_preflight_evidence_closed") is not True
        or authorization.get(
            "migration_durable_ledger_freeze_design_evidence_closed"
        )
        is not True
    ):
        raise AssertionError("Node B inherited/new design evidence gates drifted")
    acl = document.get("acl_and_sensitive_material_design", {})
    if (
        acl.get("public_connect_revoked_in_disposable_database") is not True
        or acl.get("fixture_role_effective_connect_privilege") is not False
        or acl.get("sensitive_canary_rejected_as_uuid_migration_id") is not True
        or acl.get("mutation_audit_migration_id_storage_type") != "uuid"
    ):
        raise AssertionError("Node B CONNECT/migration-id safety drifted")
    for field in (
        "migration_design_closed",
        "production_durable_ledger_or_tombstone",
        "production_source_write_freeze_evidence_closed",
        "production_target_write_freeze_evidence_closed",
        "production_membership_write_freeze_or_digest_recheck_evidence_closed",
        "production_connection_drain_evidence_closed",
        "bounded_40001_40P01_retry_implemented",
        "operator_migration_implementation",
        "production_schema_or_index",
        "flyway_baseline_or_migration",
        "backup_and_rollback_evidence_closed",
        "real_data_migration_execution",
        "legacy_runtime_permanently_disabled",
        "route_or_openapi_delta",
        "client_gateway_or_proxy_change",
        "production_cutover",
        "current_node_control_sources_external_git_anchor_complete",
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"Node B forbidden authorization became true: {field}")
    if document.get("route_state") != builder.ROUTE_STATE:
        raise AssertionError("Node B route state drifted")
    source = document.get("source_authority", {})
    if (
        source.get("fixed_source_allowlist")
        != list(builder.FIXED_SOURCE_ALLOWLIST)
        or source.get("control_sources") != list(builder.CONTROL_SOURCES)
        or source.get("fixed_source_count") != 1
        or source.get("control_source_count") != 8
        or source.get("control_sources_excluded_from_self_authority") is not True
        or source.get("control_sources_external_git_anchor_complete") is not False
        or source.get("dynamic_source_discovery") is not False
        or source.get("ordinary_build_and_load_are_gitless") is not True
        or source.get("live_head_or_ref_authority") is not False
    ):
        raise AssertionError("Node B fixed/control source authority drifted")
    if set(builder.FIXED_SOURCE_ALLOWLIST) & set(builder.CONTROL_SOURCES):
        raise AssertionError("Node B controls cannot authorize themselves")


def main() -> None:
    load_contract()
    print("phase4c tag migration durable-ledger/freeze design acceptance: OK")


if __name__ == "__main__":
    main()
