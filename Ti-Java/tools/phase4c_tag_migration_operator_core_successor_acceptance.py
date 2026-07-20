#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C tag operator-core successor."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

try:
    from tools import build_phase4c_tag_migration_operator_core_contract as builder
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_operator_core_contract",
    }:
        raise
    import build_phase4c_tag_migration_operator_core_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "2124d1b042f2df201ad3d8ca87fd19fa121b8d47cbaf51a60eb5271fe55b7fe8"
CONTRACT_PAYLOAD_SHA256 = (
    "28f0fa1a5ec1c2e795c60d472b47d0ccb16d1b838a30dd0e7ac69fe738f53778"
)
CONTRACT_BYTE_COUNT = 50_467
BUILD_CONTEXT_SCRIPT_RELATIVE = "infra/phase2/hash-java-build-context.sh"


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
    current_report_sha256: str
    current_build_context_sha256: str
    current_chain_node_count: int


def _load_contract_envelope(root: Path) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if (
        len(payload) != CONTRACT_BYTE_COUNT
        or builder.sha256_bytes(payload) != CONTRACT_SHA256
    ):
        raise AssertionError("operator-core contract bytes drifted")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError("operator-core contract is unreadable") from error
    if not isinstance(document, dict):
        raise AssertionError("operator-core contract is not an object")
    if (
        document.get("schema_version") != 1
        or document.get("contract_id") != builder.CONTRACT_ID
        or document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.document_payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError("operator-core contract envelope drifted")
    return document


def _validate_authorization(document: Mapping[str, Any]) -> None:
    expected = {
        "newly_closed_gates": list(builder.NEWLY_CLOSED_GATES),
        "migration_global_preflight_evidence_closed": True,
        "migration_durable_ledger_freeze_design_evidence_closed": True,
        "operator_core_evidence_closed": True,
        "bounded_40001_40P01_retry_implemented": True,
        "operator_migration_implementation": True,
        "migration_design_closed": False,
        "production_durable_ledger_or_tombstone": False,
        "production_source_write_freeze_evidence_closed": False,
        "production_target_write_freeze_evidence_closed": False,
        "production_membership_write_freeze_or_digest_recheck_evidence_closed": False,
        "production_connection_drain_evidence_closed": False,
        "production_schema_or_index": False,
        "flyway_baseline_or_migration": False,
        "backup_and_rollback_evidence_closed": False,
        "real_data_migration_execution": False,
        "legacy_runtime_permanently_disabled": False,
        "route_or_openapi_delta": False,
        "client_gateway_or_proxy_change": False,
        "production_cutover": False,
        "source_successor_external_git_anchor_complete": False,
        "semantic_successor_external_git_anchor_complete": False,
        "bootstrap_control_sources_external_git_anchor_complete": False,
        "current_node_control_sources_external_git_anchor_complete": False,
    }
    if document.get("authorization") != expected:
        raise AssertionError("operator-core authorization boundary drifted")


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    resolved_root = root.resolve(strict=True)
    if document != builder.build_contract(resolved_root):
        raise AssertionError("operator-core deterministic contract drifted")
    _validate_authorization(document)
    if document.get("route_state") != builder.ROUTE_STATE:
        raise AssertionError("operator-core route state drifted")
    schema = document.get("schema_and_acl_verification", {})
    evidence = document.get("evidence", {})
    receipts = document.get("operator_core_implementation", {}).get(
        "writer_stop_receipts", {}
    )
    if (
        schema.get("expected_catalog_sha256")
        != builder.EXPECTED_CATALOG_SHA256
        or evidence.get("targeted_unit_test_count") != 83
        or receipts.get("pairwise_distinct_required") is not True
        or evidence.get(
            "sparse_partial_receipt_business_facts_and_existing_receipts_unchanged"
        )
        is not True
        or evidence.get(
            "sparse_partial_receipt_durable_block_run_and_single_audit_only"
        )
        is not True
        or "sparse_partial_receipt_rejected_without_fingerprint_change" in evidence
    ):
        raise AssertionError("operator-core P1 evidence identity drifted")

    predecessor = document.get("predecessor", {})
    if predecessor != {
        "source": builder.PREDECESSOR_RELATIVE,
        "contract_id": builder.PREDECESSOR_ID,
        "captured_at": builder.PREDECESSOR_CAPTURED_AT,
        "scope": builder.PREDECESSOR_SCOPE,
        "status": builder.PREDECESSOR_STATUS,
        "sha256": builder.PREDECESSOR_SHA256,
        "byte_count": builder.PREDECESSOR_BYTE_COUNT,
        "document_payload_sha256": builder.PREDECESSOR_PAYLOAD_SHA256,
        "immutable": True,
    }:
        raise AssertionError("operator-core predecessor drifted")

    authority = document.get("source_authority", {})
    fixed_sources = authority.get("fixed_non_control_sources")
    if (
        authority.get("fixed_non_control_source_count")
        != builder.FIXED_NON_CONTROL_SOURCE_COUNT
        or authority.get("control_source_count") != builder.CONTROL_SOURCE_COUNT
        or authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or authority.get("control_sources_excluded_from_self_authority") is not True
        or authority.get("current_control_sources_external_git_anchor_complete")
        is not False
        or authority.get("dynamic_source_discovery") is not False
        or authority.get("ordinary_build_and_load_are_gitless") is not True
        or authority.get("live_head_main_or_origin_authority") is not False
        or not isinstance(fixed_sources, dict)
        or set(fixed_sources) != set(builder.SOURCE_FILES)
    ):
        raise AssertionError("operator-core source authority drifted")
    for relative, (sha256, byte_count) in builder.SOURCE_FILES.items():
        if fixed_sources.get(relative) != {
            "source": relative,
            "sha256": sha256,
            "byte_count": byte_count,
        }:
            raise AssertionError(
                f"operator-core fixed source descriptor drifted: {relative}"
            )

    successors = document.get("historical_source_successors", {})
    if (
        successors.get("predecessor_checkpoint") != builder.NODE_B_ANCHOR_COMMIT
        or successors.get("override_count") != builder.SOURCE_TRANSITION_COUNT
        or successors.get("overrides") != builder.SOURCE_TRANSITIONS
        or successors.get("accepted_bytes_replayable_from_fixed_predecessor")
        is not True
        or successors.get("successor_external_git_anchor_complete") is not False
        or successors.get("unknown_path") != "reject"
    ):
        raise AssertionError("operator-core source transitions drifted")

    runtime = document.get("production_runtime_successor", {})
    if (
        runtime.get("accepted_file_count") != builder.ACCEPTED_PRODUCTION_FILE_COUNT
        or runtime.get("accepted_manifest_sha256")
        != builder.ACCEPTED_PRODUCTION_MANIFEST_SHA256
        or runtime.get("current_file_count") != builder.CURRENT_PRODUCTION_FILE_COUNT
        or runtime.get("current_manifest_sha256")
        != builder.CURRENT_PRODUCTION_MANIFEST_SHA256
        or runtime.get("added_files")
        != dict(sorted(builder.PRODUCTION_RUNTIME_ADDITIONS.items()))
        or runtime.get("changed_files")
        != dict(sorted(builder.PRODUCTION_RUNTIME_CHANGES.items()))
        or runtime.get("deleted_files") != []
    ):
        raise AssertionError("operator-core production runtime successor drifted")
    main = runtime.get("learning_personalbank_main", {})
    if (
        main.get("accepted_file_count")
        != builder.ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or main.get("accepted_manifest_sha256")
        != builder.ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
        or main.get("current_file_count")
        != builder.CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or main.get("current_manifest_sha256")
        != builder.CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
    ):
        raise AssertionError("operator-core learning/personalbank successor drifted")

    worm = document.get("worm_successor", {})
    if (
        worm.get("accepted_report", {}).get("sha256")
        != builder.WORM_PREDECESSOR_SHA256
        or worm.get("accepted_build_context_sha256")
        != builder.ACCEPTED_BUILD_CONTEXT_SHA256
        or worm.get("accepted_chain_node_count") != 7
        or worm.get("current_report", {}).get("source") != builder.WORM_RELATIVE
        or worm.get("current_report", {}).get("sha256") != builder.WORM_SHA256
        or worm.get("current_report", {}).get("byte_count")
        != builder.WORM_BYTE_COUNT
        or worm.get("current_build_context_sha256")
        != builder.CURRENT_BUILD_CONTEXT_SHA256
        or worm.get("dockerfile_sha256") != builder.DOCKERFILE_SHA256
        or worm.get("current_chain_node_count") != 8
        or worm.get("appended_node_count") != 1
        or worm.get("historical_nodes_rewritten") is not False
    ):
        raise AssertionError("operator-core WORM successor drifted")


def load(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    document = _load_contract_envelope(resolved_root)
    validate(document, resolved_root)
    return document


def source_transition(root: Path, relative: str) -> dict[str, Any] | None:
    transition = builder.SOURCE_TRANSITIONS.get(relative)
    if transition is None:
        return None
    resolved_root = root.resolve(strict=True)
    document = load(resolved_root)
    actual = document["historical_source_successors"]["overrides"].get(relative)
    if actual != transition:
        raise AssertionError(
            f"operator-core source-transition contract drifted: {relative}"
        )
    payload = builder.fixed_regular_file(resolved_root, relative).read_bytes()
    if (
        len(payload) != transition["successor_byte_count"]
        or builder.sha256_bytes(payload) != transition["successor_sha256"]
    ):
        raise AssertionError(
            f"operator-core source-transition bytes drifted: {relative}"
        )
    return dict(transition)


def accepted_sha256(relative: str) -> str | None:
    transition = builder.SOURCE_TRANSITIONS.get(relative)
    return None if transition is None else str(transition["accepted_sha256"])


def successor_sha256(root: Path, relative: str) -> str | None:
    transition = source_transition(root, relative)
    return None if transition is None else str(transition["successor_sha256"])


def _runtime_view(
    root: Path,
    view: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    accepted, current = builder.production_runtime_manifests(root)
    document = load(root)
    runtime = document["production_runtime_successor"]
    if view == "full_runtime":
        return accepted, current, runtime
    if view == "learning_personalbank_main":
        return (
            builder._learning_personalbank_main(accepted),
            builder._learning_personalbank_main(current),
            runtime["learning_personalbank_main"],
        )
    raise AssertionError(f"operator-core unknown production view: {view}")


def validate_production_runtime_successor(
    root: Path,
    accepted_files: Mapping[str, str],
    current_files: Mapping[str, str],
    *,
    view: str = "full_runtime",
) -> ProductionRuntimeSuccessor:
    resolved_root = root.resolve(strict=True)
    expected_accepted, expected_current, semantic = _runtime_view(
        resolved_root, view
    )
    normalized_accepted = dict(sorted(accepted_files.items()))
    normalized_current = dict(sorted(current_files.items()))
    if (
        normalized_accepted != expected_accepted
        or len(normalized_accepted) != semantic["accepted_file_count"]
        or builder.sha256_json(normalized_accepted)
        != semantic["accepted_manifest_sha256"]
    ):
        raise AssertionError("operator-core rejected accepted production manifest")
    if (
        normalized_current != expected_current
        or len(normalized_current) != semantic["current_file_count"]
        or builder.sha256_json(normalized_current)
        != semantic["current_manifest_sha256"]
    ):
        raise AssertionError("operator-core rejected current production manifest")
    return ProductionRuntimeSuccessor(
        view=view,
        accepted_file_count=int(semantic["accepted_file_count"]),
        accepted_manifest_sha256=str(semantic["accepted_manifest_sha256"]),
        current_file_count=int(semantic["current_file_count"]),
        current_manifest_sha256=str(semantic["current_manifest_sha256"]),
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
    worm = document["worm_successor"]
    if (
        accepted_report_sha256 != builder.WORM_PREDECESSOR_SHA256
        or accepted_build_context_sha256 != builder.ACCEPTED_BUILD_CONTEXT_SHA256
        or worm["accepted_chain_node_count"] != 7
    ):
        raise AssertionError("operator-core rejected WORM predecessor")
    script = builder.fixed_regular_file(
        resolved_root, BUILD_CONTEXT_SCRIPT_RELATIVE
    )
    result = subprocess.run(
        ["/bin/sh", str(script)],
        cwd=resolved_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    physical_build_context = result.stdout.strip()
    if (
        result.returncode != 0
        or physical_build_context != builder.CURRENT_BUILD_CONTEXT_SHA256
        or physical_build_context != worm["current_build_context_sha256"]
    ):
        raise AssertionError("operator-core physical build-context successor drifted")
    return WormSuccessor(
        accepted_report_sha256=accepted_report_sha256,
        accepted_build_context_sha256=accepted_build_context_sha256,
        accepted_chain_node_count=int(worm["accepted_chain_node_count"]),
        current_report_sha256=str(worm["current_report"]["sha256"]),
        current_build_context_sha256=physical_build_context,
        current_chain_node_count=int(worm["current_chain_node_count"]),
    )


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                CONTRACT_RELATIVE,
                builder.PREDECESSOR_RELATIVE,
                builder.GLOBAL_PREFLIGHT_CONTRACT_RELATIVE,
                builder.HISTORICAL_RUNTIME_CONTRACT_RELATIVE,
                BUILD_CONTEXT_SCRIPT_RELATIVE,
                *builder.SOURCE_FILES,
            )
        )
    )


def semantic_fixture_paths(root: Path = ROOT) -> tuple[str, ...]:
    _, current = builder.production_runtime_manifests(root.resolve(strict=True))
    build_context_paths = (
        relative
        for relative in current
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
    return tuple(dict.fromkeys((*minimal_fixture_paths(), *build_context_paths)))


def main() -> None:
    accepted = load()
    print(
        json.dumps(
            {
                "accepted": True,
                "operator_core_evidence_closed": accepted["authorization"][
                    "operator_core_evidence_closed"
                ],
                "operator_migration_implementation": accepted["authorization"][
                    "operator_migration_implementation"
                ],
                "production_cutover": accepted["authorization"][
                    "production_cutover"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
