#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C tag global-preflight successor."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Mapping
from typing import Any

try:
    from tools import build_phase4c_tag_migration_global_preflight_contract as builder
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_global_preflight_contract",
    }:
        raise
    import build_phase4c_tag_migration_global_preflight_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e"
CONTRACT_PAYLOAD_SHA256 = "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e"
CONTRACT_BYTE_COUNT = 102_931


@dataclass(frozen=True)
class ProductionRuntimeSuccessor:
    view: str
    accepted_file_count: int
    accepted_manifest_sha256: str
    current_file_count: int
    current_manifest_sha256: str
    added_files: tuple[tuple[str, str], ...]
    changed_files: tuple[tuple[str, str], ...]
    deleted_files: tuple[str, ...]


@dataclass(frozen=True)
class WormSuccessor:
    accepted_report_sha256: str
    accepted_build_context_sha256: str
    accepted_chain_node_count: int
    first_successor_report_sha256: str
    first_successor_build_context_sha256: str
    first_successor_chain_node_count: int
    current_report_sha256: str
    current_build_context_sha256: str
    current_chain_node_count: int


def _validate_exact_authorization(document: dict[str, Any]) -> None:
    expected = {
        "newly_closed_gates": list(builder.NEWLY_CLOSED_GATES),
        "migration_global_preflight_evidence_closed": True,
        "migration_design_closed": False,
        "operator_migration_implementation": False,
        "production_schema_or_index": False,
        "real_data_migration_execution": False,
        "production_cutover": False,
        "route_or_openapi_delta": False,
        "http_security_or_rate_limit_delta": False,
        "client_gateway_or_proxy_change": False,
        "source_successor_external_git_anchor_complete": False,
        "semantic_successor_external_git_anchor_complete": False,
        "bootstrap_control_sources_external_git_anchor_complete": False,
    }
    if document.get("authorization") != expected:
        raise AssertionError("tag preflight authorization boundary drifted")


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    if (
        document.get("schema_version") != 1
        or document.get("contract_id") != builder.CONTRACT_ID
    ):
        raise AssertionError("tag preflight contract identity drifted")
    if (
        document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError("tag preflight contract payload drifted")

    predecessors = document.get("append_only_predecessors")
    if not isinstance(predecessors, dict):
        raise AssertionError("tag preflight predecessors are absent")
    for name in (
        "semantic_composition",
        "current_route_promotion",
        "approved_differences",
        "effective_data_ownership",
    ):
        predecessor = predecessors.get(name)
        if not isinstance(predecessor, dict) or predecessor.get("immutable") is not True:
            raise AssertionError(f"tag preflight predecessor is mutable: {name}")
    if predecessors["semantic_composition"]["sha256"] != (
        "ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b"
    ):
        raise AssertionError("tag preflight composition physical authority drifted")
    if predecessors["current_route_promotion"]["sha256"] != (
        "e5bc53bb8c011c5cf2f08447543aa3e5dd2a045b6226f064c6594a3639d7b5c9"
    ):
        raise AssertionError("tag preflight route physical authority drifted")
    if predecessors["approved_differences"]["sha256"] != (
        "921d6626ab11d59a9667e1942953807b0aa1a81c06c01094cc109312f9d6b300"
    ):
        raise AssertionError("tag preflight approved differences physical authority drifted")
    if predecessors["approved_differences"].get("accepted_migration_ids") != list(
        builder.MIGRATION_APPROVED_DIFFERENCE_IDS
    ):
        raise AssertionError("tag preflight migration approved IDs drifted")

    bridges = document.get("source_successor_bridges")
    if not isinstance(bridges, dict):
        raise AssertionError("tag preflight source-successor bridges are absent")
    expected_overrides = {
        relative: {
            "source": relative,
            **transition,
            "successor_authority": builder.SOURCES[
                builder.SOURCE_SUCCESSOR_SOURCE_NAMES[relative]
            ],
            "transition_fixed_by_this_contract": True,
            "successor_external_git_anchor_complete": False,
        }
        for relative, transition in sorted(builder.SOURCE_SUCCESSORS.items())
    }
    if (
        bridges.get("path_count") != len(builder.SOURCE_SUCCESSORS)
        or bridges.get("paths") != sorted(builder.SOURCE_SUCCESSORS)
        or bridges.get("path_allowlist_exact") is not True
        or bridges.get("typed_phase2_paths")
        != sorted(builder.TYPED_PHASE2_SOURCE_SUCCESSORS)
        or bridges.get("phase6_typed_bridge_paths")
        != sorted(builder.PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS)
        or bridges.get("phase6_document_paths")
        != sorted(builder.PHASE6_DOCUMENT_SOURCE_SUCCESSORS)
        or bridges.get("phase6_bootstrap_paths")
        != sorted(builder.PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS)
        or bridges.get("semantic_consumer_paths")
        != sorted(builder.SEMANTIC_CONSUMER_SOURCE_SUCCESSORS)
        or bridges.get("post_push_bridge_paths")
        != sorted(builder.POST_PUSH_BRIDGE_SOURCE_SUCCESSORS)
        or bridges.get("typed_normalization_bridge_paths")
        != sorted(builder.TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS)
        or bridges.get("overrides") != expected_overrides
        or bridges.get("historical_typed_anchor_contract")
        != builder.SOURCES["typed_anchor_contract"]
        or bridges.get("historical_phase6_source_successor_anchor_contract")
        != builder.SOURCES["phase6_source_successor_anchor_contract"]
        or bridges.get("unknown_paths") != "reject"
        or bridges.get("symlink_or_root_escape") != "reject"
        or bridges.get("dynamic_source_discovery") is not False
        or bridges.get("live_git_head_authority") is not False
        or bridges.get("source_successor_external_git_anchor_complete")
        is not False
    ):
        raise AssertionError("tag preflight source-successor bridge drifted")

    protocol = document.get("global_preflight_protocol")
    if not isinstance(protocol, dict):
        raise AssertionError("tag preflight protocol is absent")
    connection = protocol.get("connection")
    if connection != {
        "dedicated_connection": True,
        "session_level_postgresql_advisory_lock_across_complete_sweep": True,
        "read_only": True,
        "isolation": "SERIALIZABLE",
        "deferrable": True,
        "acquire_setup_and_close_failures_are_global_blockers": True,
        "global_failure_codes": list(builder.GLOBAL_FAILURE_CODES),
    }:
        raise AssertionError("tag preflight connection protocol drifted")
    selection = protocol.get("selection_and_parsing")
    if selection != {
        "strict_namespace_and_round_trip": True,
        "strict_json_duplicate_keys_and_trailing_tokens_rejected": True,
        "per_payload_utf8_byte_limit": 1_048_576,
        "oversized_payload_rejected_before_json_parsing": True,
        "python_compatible_unicode_whitespace_normalization": True,
        "legacy_list_json_array_string_and_csv_forms_supported": True,
        "twenty_unicode_code_point_cleaning_and_collision_detection": True,
        "postgresql_text_lossless_required": True,
        "nul_and_unpaired_surrogates_rejected": True,
        "valid_surrogate_pairs_preserved": True,
        "unicode_case_and_normalization_forms_preserved": True,
        "positive_canonical_question_ids_required": True,
        "invalid_key_or_data_is_reported_not_dropped": True,
    }:
        raise AssertionError("tag preflight bounded/lossless parsing drifted")
    source_bounds = protocol.get("source_sweep_bounds")
    if source_bounds != {
        "maximum_reserved_source_rows": 100_000,
        "maximum_reserved_source_utf8_bytes": 268_435_456,
        "source_fetch_size": 16,
        "sql_octet_length_checked_before_payload_materialization": True,
        "oversized_payload_materialized": False,
        "oversized_payload_classification": "INVALID_DATA/PAYLOAD_LIMIT_EXCEEDED",
        "oversized_payload_target_or_membership_read": False,
        "bounds_are_production_scale_evidence": False,
    }:
        raise AssertionError("tag preflight source sweep bounds drifted")
    aggregation = protocol.get("aggregation")
    if (
        not isinstance(aggregation, dict)
        or aggregation.get("historical_row_outcomes")
        != list(builder.HISTORICAL_ROW_OUTCOMES)
        or aggregation.get("historical_reporting_groups")
        != builder.HISTORICAL_REPORTING_GROUPS
        or aggregation.get("historical_vocabulary_is_apply_predecessor_only") is not True
        or aggregation.get("dry_run_emits_migrated_or_transaction_failure_outcomes")
        is not False
        or aggregation.get("preflight_dispositions")
        != list(builder.PREFLIGHT_DISPOSITIONS)
        or aggregation.get("preflight_reporting_groups")
        != builder.PREFLIGHT_REPORTING_GROUPS
        or aggregation.get("preflight_statuses") != list(builder.PREFLIGHT_STATUSES)
        or aggregation.get("global_all_or_block") is not True
        or aggregation.get("all_rows_are_classified_without_first_blocker_short_circuit")
        is not True
        or aggregation.get("raw_tag_or_credential_material_in_report") is not False
    ):
        raise AssertionError("tag preflight all-or-block aggregation drifted")
    mutation = protocol.get("mutation_safety")
    if mutation != {
        "mode": "DRY_RUN",
        "source_dml": 0,
        "target_dml": 0,
        "schema_or_index_ddl": 0,
        "mutation_statement_count": 0,
        "source_target_schema_and_index_fingerprints_unchanged": True,
    }:
        raise AssertionError("tag preflight dry-run mutation boundary drifted")

    evidence = document.get("evidence")
    if not isinstance(evidence, dict):
        raise AssertionError("tag preflight evidence is absent")
    required_true_evidence = (
        "mixed_fixture_global_blocker_aggregation",
        "session_lock_contention_and_release_after_connection_close",
        "dry_run_zero_mutation_fingerprints",
        "bounded_source_payload_and_sweep_limits_evidenced",
        "unicode_postgresql_text_losslessness_evidenced",
        "historical_row_primitive_is_only_a_predecessor",
    )
    if evidence.get("postgresql_versions") != ["16.14", "18.4"]:
        raise AssertionError("tag preflight PostgreSQL matrix drifted")
    if (
        evidence.get("mixed_fixture_candidate_count") != 16
        or evidence.get("mixed_fixture_reporting_group_counts")
        != builder.MIXED_FIXTURE_REPORTING_GROUP_COUNTS
    ):
        raise AssertionError("tag preflight mixed fixture aggregation drifted")
    for field in required_true_evidence:
        if evidence.get(field) is not True:
            raise AssertionError(f"tag preflight evidence is not closed: {field}")
    for field in (
        "historical_row_primitive_reclassified_as_global_preflight",
        "bounded_payload_or_unicode_hardening_authorizes_apply",
        "production_database_connected",
        "production_credentials_read",
        "production_data_read_or_mutated",
        "production_operator_executed",
    ):
        if evidence.get(field) is not False:
            raise AssertionError(f"tag preflight evidence overclaims: {field}")

    fail_closed = document.get("apply_fail_closed")
    if not isinstance(fail_closed, dict):
        raise AssertionError("tag preflight fail-closed boundary is absent")
    if fail_closed.get("durable_marker_absence_blocks_apply") is not True:
        raise AssertionError("tag preflight durable marker does not fail closed")
    if fail_closed.get("planner_apply_prerequisite_blockers") != list(
        builder.APPLY_PREREQUISITE_BLOCKERS
    ):
        raise AssertionError("tag preflight planner prerequisite blockers drifted")
    for field in (
        "production_apply_authorized",
        "planner_cleanliness_eligibility_is_production_authorization",
        "durable_migration_ledger_or_tombstone_exists",
        "source_write_freeze_evidenced",
        "target_write_freeze_or_common_version_protocol_evidenced",
        "membership_write_freeze_or_digest_recheck_evidenced",
        "bounded_40001_40P01_retry_implemented",
        "backup_and_rollback_evidence_exists",
        "production_data_cleanliness_or_scale_proven",
        "all_dispositions_approved",
        "real_apply_path_present",
    ):
        if fail_closed.get(field) is not False:
            raise AssertionError(f"tag preflight apply prerequisite overclaims: {field}")

    _validate_exact_authorization(document)
    if document.get("route_state") != builder.ROUTE_STATE:
        raise AssertionError("tag preflight route state drifted")

    if document.get("historical_semantic_successors") != (
        builder._historical_semantic_successor_authority(root)
    ):
        raise AssertionError("tag preflight historical semantic successor drifted")

    build_context = document.get("build_context_authority")
    if not isinstance(build_context, dict):
        raise AssertionError("tag preflight build context authority is absent")
    if build_context.get("old_worm_predecessor", {}).get("sha256") != (
        "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
    ):
        raise AssertionError("tag preflight old WORM predecessor drifted")
    if build_context.get("initial_worm_successor") != {
        **builder.SOURCES["tag_global_preflight_worm_successor"],
        "java_build_context_sha256": builder.TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256,
        "dockerfile_sha256": builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
        "predecessor_sha256": builder.TAG_GLOBAL_PREFLIGHT_WORM_PREDECESSOR_SHA256,
        "fixed_chain_node_count": 6,
        "immutable": True,
    }:
        raise AssertionError("tag preflight initial WORM successor drifted")
    if build_context.get("new_worm_successor") != {
        **builder.SOURCES["tag_global_preflight_hardening_worm_successor"],
        "java_build_context_sha256": (
            builder.TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256
        ),
        "dockerfile_sha256": builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
        "predecessor_sha256": (
            builder.TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_PREDECESSOR_SHA256
        ),
        "fixed_chain_node_count": 7,
        "immutable": True,
    }:
        raise AssertionError("tag preflight hardening WORM successor drifted")
    for field in (
        "current_build_context_changed",
        "initial_worm_successor_appended",
        "new_worm_successor_was_required",
        "new_worm_successor_appended",
        "new_build_context_worm_closed",
    ):
        if build_context.get(field) is not True:
            raise AssertionError(f"tag preflight WORM successor closure drifted: {field}")
    if (
        build_context.get("new_main_source_count") != len(builder.NEW_MAIN_SOURCE_NAMES)
        or build_context.get("new_main_sources")
        != [builder.SOURCES[name] for name in builder.NEW_MAIN_SOURCE_NAMES]
    ):
        raise AssertionError("tag preflight new main-source authority drifted")
    for field in (
        "spring_component_runner_scheduler_or_http_registration",
        "apply_statement_or_operator_entrypoint_added",
        "old_tip_reused_as_current",
        "initial_worm_tip_reused_as_current",
        "new_worm_successor_required",
        "historical_worm_chain_overwritten",
    ):
        if build_context.get(field) is not False:
            raise AssertionError(f"tag preflight WORM overclaim drifted: {field}")

    if document.get("next_gate") != {
        "worm_successor_gate": "closed by the fixed seventh hardening WORM node",
        "required_next": (
            "design and separately authorize the durable ledger, freeze/recheck, "
            "bounded retry, backup/rollback and operator apply protocol"
        ),
        "production_execution_requires_explicit_user_authorization": True,
    }:
        raise AssertionError("tag preflight next gate drifted")

    source_authority = document.get("source_authority")
    if (
        not isinstance(source_authority, dict)
        or source_authority.get("fixed_source_count") != len(builder.SOURCES)
        or source_authority.get("fixed_sources") != builder.SOURCES
        or source_authority.get("unknown_sources") != "reject"
        or source_authority.get("symlink_or_root_escape") != "reject"
        or source_authority.get("control_source_count") != len(builder.CONTROL_SOURCES)
        or source_authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or source_authority.get("control_sources_excluded_from_self_authority") is not True
        or source_authority.get("control_sources_external_git_anchor_complete")
        is not False
        or source_authority.get("dynamic_source_discovery") is not False
        or source_authority.get("historical_contracts_or_evidence_overwritten") is not False
        or source_authority.get("source_successor_path_count")
        != len(builder.SOURCE_SUCCESSORS)
        or source_authority.get("source_successor_paths")
        != sorted(builder.SOURCE_SUCCESSORS)
    ):
        raise AssertionError("tag preflight source authority drifted")
    source_paths = {descriptor["source"] for descriptor in builder.SOURCES.values()}
    if source_paths.intersection(builder.CONTROL_SOURCES):
        raise AssertionError("tag preflight control source entered self-authority")

    if document != builder.build_contract(root):
        raise AssertionError("tag preflight deterministic rebuild drifted")


def _load_contract_envelope(root: Path) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if (
        CONTRACT_BYTE_COUNT < 0
        or CONTRACT_SHA256 == "PENDING_GENERATED_CONTRACT_SHA256"
        or len(payload) != CONTRACT_BYTE_COUNT
        or builder.sha256_bytes(payload) != CONTRACT_SHA256
    ):
        raise AssertionError("tag preflight contract physical bytes drifted")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError("tag preflight contract is unreadable") from error
    if not isinstance(document, dict):
        raise AssertionError("tag preflight contract is not an object")
    if (
        document.get("schema_version") != 1
        or document.get("contract_id") != builder.CONTRACT_ID
        or document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError("tag preflight contract envelope drifted")
    return document


def load(root: Path = ROOT) -> dict[str, Any]:
    document = _load_contract_envelope(root)
    validate(document, root)
    return document


def accepted_sha256(relative: str) -> str | None:
    transition = builder.SOURCE_SUCCESSORS.get(relative)
    return None if transition is None else str(transition["accepted_sha256"])


def successor_sha256(root: Path, relative: str) -> str | None:
    transition = builder.SOURCE_SUCCESSORS.get(relative)
    if transition is None:
        return None
    resolved_root = root.resolve(strict=True)
    document = _load_contract_envelope(resolved_root)
    actual = document["source_successor_bridges"]["overrides"].get(relative)
    expected = {
        "source": relative,
        **transition,
        "successor_authority": builder.SOURCES[
            builder.SOURCE_SUCCESSOR_SOURCE_NAMES[relative]
        ],
        "transition_fixed_by_this_contract": True,
        "successor_external_git_anchor_complete": False,
    }
    if actual != expected:
        raise AssertionError(
            f"tag preflight source-successor contract drifted: {relative}"
        )
    payload = builder.fixed_regular_file(resolved_root, relative).read_bytes()
    physical = builder.sha256_bytes(payload)
    if (
        physical != transition["successor_sha256"]
        or len(payload) != transition["successor_byte_count"]
    ):
        raise AssertionError(
            f"tag preflight source-successor bytes drifted: {relative}"
        )
    return physical


def validate_production_runtime_successor(
    root: Path,
    accepted_files: Mapping[str, str],
    current_files: Mapping[str, str],
    *,
    view: str = "full_runtime",
) -> ProductionRuntimeSuccessor:
    resolved_root = root.resolve(strict=True)
    document = load(resolved_root)
    production = document["historical_semantic_successors"][
        "production_runtime_manifest"
    ]
    historical = builder._validated_json(
        resolved_root, "historical_target_execution_contract"
    )["production_surface"]
    historical_files = historical["files"]
    if view == "full_runtime":
        semantic = production
        expected_accepted = historical_files
    elif view == "learning_personalbank_main":
        semantic = production["learning_personalbank_main"]
        prefixes = (
            "server/src/main/java/io/saksk/ti/learning/",
            "server/src/main/java/io/saksk/ti/personalbank/",
        )
        expected_accepted = {
            relative: digest
            for relative, digest in historical_files.items()
            if relative.startswith(prefixes)
        }
    else:
        raise AssertionError(f"tag preflight unknown production view: {view}")
    normalized_accepted = dict(sorted(accepted_files.items()))
    normalized_current = dict(sorted(current_files.items()))
    if (
        normalized_accepted != expected_accepted
        or len(normalized_accepted) != semantic["accepted_file_count"]
        or builder.sha256_bytes(
            builder.canonical_json(normalized_accepted).encode("utf-8")
        )
        != semantic["accepted_manifest_sha256"]
    ):
        raise AssertionError("tag preflight rejected historical production manifest")
    expected_successor = dict(normalized_accepted)
    expected_successor.update(semantic["added_files"])
    expected_successor = dict(sorted(expected_successor.items()))
    if (
        normalized_current != expected_successor
        or len(normalized_current) != semantic["successor_file_count"]
        or builder.sha256_bytes(
            builder.canonical_json(normalized_current).encode("utf-8")
        )
        != semantic["successor_manifest_sha256"]
    ):
        raise AssertionError("tag preflight rejected current production manifest")
    return ProductionRuntimeSuccessor(
        view=view,
        accepted_file_count=int(semantic["accepted_file_count"]),
        accepted_manifest_sha256=str(semantic["accepted_manifest_sha256"]),
        current_file_count=int(semantic["successor_file_count"]),
        current_manifest_sha256=str(semantic["successor_manifest_sha256"]),
        added_files=tuple(sorted(semantic["added_files"].items())),
        changed_files=tuple(sorted(semantic["changed_files"].items())),
        deleted_files=tuple(sorted(semantic["deleted_files"])),
    )


def validate_worm_successor(
    root: Path,
    accepted_report_sha256: str,
    accepted_build_context_sha256: str,
) -> WormSuccessor:
    resolved_root = root.resolve(strict=True)
    document = load(resolved_root)
    semantic = document["historical_semantic_successors"][
        "java_build_context_and_worm_chain"
    ]
    if (
        accepted_report_sha256 != semantic["accepted_worm"]["sha256"]
        or accepted_build_context_sha256
        != semantic["accepted_build_context_sha256"]
        or semantic["accepted_chain_node_count"] != 5
        or semantic["first_successor_chain_node_count"] != 6
        or semantic["terminal_successor_chain_node_count"] != 7
        or semantic["appended_node_count"] != 2
        or semantic["historical_nodes_rewritten"] is not False
    ):
        raise AssertionError("tag preflight rejected build-context/WORM successor")
    script = builder.fixed_regular_file(
        resolved_root, "infra/phase2/hash-java-build-context.sh"
    )
    result = subprocess.run(
        ["/bin/sh", str(script)],
        cwd=resolved_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    physical_build_context_sha256 = result.stdout.strip()
    if (
        result.returncode != 0
        or physical_build_context_sha256
        != semantic["terminal_successor_build_context_sha256"]
    ):
        raise AssertionError("tag preflight physical build-context successor drifted")
    return WormSuccessor(
        accepted_report_sha256=accepted_report_sha256,
        accepted_build_context_sha256=accepted_build_context_sha256,
        accepted_chain_node_count=int(semantic["accepted_chain_node_count"]),
        first_successor_report_sha256=str(
            semantic["first_successor_worm"]["sha256"]
        ),
        first_successor_build_context_sha256=str(
            semantic["first_successor_build_context_sha256"]
        ),
        first_successor_chain_node_count=int(
            semantic["first_successor_chain_node_count"]
        ),
        current_report_sha256=str(semantic["terminal_successor_worm"]["sha256"]),
        current_build_context_sha256=physical_build_context_sha256,
        current_chain_node_count=int(semantic["terminal_successor_chain_node_count"]),
    )


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(dict.fromkeys((
        CONTRACT_RELATIVE,
        *(descriptor["source"] for descriptor in builder.SOURCES.values()),
        *builder.PHASE2_FIXED_CHAIN_FIXTURE_PATHS,
    )))


def semantic_fixture_paths(root: Path = ROOT) -> tuple[str, ...]:
    historical = builder._validated_json(
        root.resolve(strict=True), "historical_target_execution_contract"
    )["production_surface"]["files"]
    build_context_files = (
        relative
        for relative in historical
        if relative in {
            "server/Dockerfile",
            "server/.dockerignore",
            "server/mvnw",
            "server/pom.xml",
            "server/build-versions.properties",
        }
        or relative.startswith("server/.mvn/")
        or relative.startswith("server/src/main/")
    )
    return tuple(dict.fromkeys((
        *minimal_fixture_paths(),
        "infra/phase2/hash-java-build-context.sh",
        *build_context_files,
        *builder.PRODUCTION_MANIFEST_ADDITIONS,
    )))


if __name__ == "__main__":
    accepted = load()
    print(json.dumps({
        "accepted": True,
        "migration_global_preflight_evidence_closed": accepted["authorization"][
            "migration_global_preflight_evidence_closed"
        ],
        "operator_migration_implementation": accepted["authorization"][
            "operator_migration_implementation"
        ],
        "production_cutover": accepted["authorization"]["production_cutover"],
    }, sort_keys=True))
