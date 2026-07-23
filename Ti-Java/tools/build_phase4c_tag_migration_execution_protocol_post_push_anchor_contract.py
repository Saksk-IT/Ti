#!/usr/bin/env python3
"""Build the fixed Phase 4C execution-protocol D0+D1 post-push anchor."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-"
    "post-push-anchor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
CONTRACT_ID = (
    "ti.phase4c.personal-bank-tag-migration-execution-protocol-"
    "post-push-anchor-contract"
)
CAPTURED_AT = "2026-07-23T17:47:54+08:00"
STATUS = (
    "execution_protocol_and_independent_acceptance_checkpoints_externally_"
    "anchored_production_schema_freeze_backup_apply_runtime_disable_and_"
    "cutover_unauthorized"
)
SCOPE = (
    "phase4c-personal-bank-tag-migration-execution-protocol-post-push-"
    "external-anchor"
)

EXECUTION_PROTOCOL_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-contract.json"
)
EXECUTION_PROTOCOL_CONTRACT_ID = "ti.phase4c.personal-bank-tag-migration-execution-protocol-contract"
EXECUTION_PROTOCOL_CONTRACT_CAPTURED_AT = "2026-07-20T21:15:00+08:00"
EXECUTION_PROTOCOL_CONTRACT_SHA256 = (
    "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14"
)
EXECUTION_PROTOCOL_CONTRACT_PAYLOAD_SHA256 = (
    "42599261bc5632feed89fc41637ee1a98cff844dd9dc776f889d155a0567a7c4"
)
EXECUTION_PROTOCOL_CONTRACT_BYTE_COUNT = 44_336

EVIDENCE_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-"
    "independent-acceptance-evidence.json"
)
EVIDENCE_ID = (
    "ti.phase4c.personal-bank-tag-migration-execution-protocol-"
    "independent-acceptance-evidence"
)
EVIDENCE_SHA256 = (
    "eb874216f39a008d2da6df51d31471dd1dc11773781f840cd06afa87ebddf993"
)
EVIDENCE_BYTE_COUNT = 9_561
RUNNER_RELATIVE = "tools/run_phase4c_tag_migration_execution_protocol_independent_acceptance.sh"
RUNNER_SHA256 = "127a99443a670362e81349742477f5ba596df5694fe50fec6b64f485ece3d994"
RUNNER_BYTE_COUNT = 66_124
RUNNER_GIT_MODE = "100755"

D0_COMMIT = "19db389aacad439f63cb93b930bea20ddd31f5e8"
D0_PARENT = "4c47d1ea220ae9e310338bbf23b74d87d477e20f"
D1_COMMIT = "aff3c9e8d6b1ed33dc0a050c0e435572cddd51db"
D1_PARENT = D0_COMMIT

D0_CONTROL_SOURCES = (
    EXECUTION_PROTOCOL_CONTRACT_RELATIVE,
    "docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol.md",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java",
    "tools/build_phase4c_tag_migration_execution_protocol_contract.py",
    "tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_execution_protocol_contract.py",
)
D1_CONTROL_SOURCES = (EVIDENCE_RELATIVE, RUNNER_RELATIVE)
CURRENT_CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolPostPushAnchorContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance.java",
    "tools/build_phase4c_tag_migration_execution_protocol_post_push_anchor_contract.py",
    "tools/phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_execution_protocol_post_push_anchor_contract.py",
)
ROUTE_STATE = {
    "migrated_operation_count": 13,
    "pending_operation_count": 598,
    "production_cutover_operation_count": 0,
    "total_operation_count": 611,
    "legacy_flask_remains_production_owner": True,
}
PRODUCTION_FALSE_FIELDS = (
    "migration_design_closed",
    "production_durable_ledger_or_tombstone",
    "production_source_write_freeze_evidence_closed",
    "production_target_write_freeze_evidence_closed",
    "production_membership_write_freeze_or_digest_recheck_evidence_closed",
    "production_connection_drain_evidence_closed",
    "durable_evidence_nonce_journal",
    "operator_runtime_wiring",
    "production_trust_roots_or_key_rotation_audit",
    "production_schema_or_index",
    "flyway_baseline_or_migration",
    "backup_and_rollback_evidence_closed",
    "real_data_migration_execution",
    "legacy_runtime_permanently_disabled",
    "route_or_openapi_delta",
    "client_gateway_or_proxy_change",
    "production_cutover",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    payload = deepcopy(document)
    payload.pop("document_payload_sha256", None)
    return sha256_json(payload)


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _fixed_regular_file(root: Path, relative: str) -> Path:
    allowed = {EXECUTION_PROTOCOL_CONTRACT_RELATIVE, EVIDENCE_RELATIVE, RUNNER_RELATIVE, OUTPUT_RELATIVE}
    value = Path(relative)
    if value.is_absolute() or relative not in allowed:
        raise AssertionError("execution-protocol anchor unknown or absolute source")
    base = root.resolve(strict=True)
    candidate = base / value
    cursor = base
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"execution-protocol anchor source is a symlink: {relative}")
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AssertionError("execution-protocol anchor fixed source missing") from error
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise AssertionError("execution-protocol anchor source escaped or is not regular")
    return resolved


def _read_fixed_json(root: Path, relative: str, sha256: str, byte_count: int) -> dict[str, Any]:
    payload = _fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(f"execution-protocol anchor fixed bytes drifted: {relative}")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("execution-protocol anchor fixed JSON must be an object")
    return document


def _validate_execution_protocol_contract(document: dict[str, Any]) -> None:
    if (document.get("contract_id") != EXECUTION_PROTOCOL_CONTRACT_ID
            or document.get("captured_at") != EXECUTION_PROTOCOL_CONTRACT_CAPTURED_AT
            or document.get("document_payload_sha256")
            != EXECUTION_PROTOCOL_CONTRACT_PAYLOAD_SHA256
            or document_payload_sha256(document)
            != EXECUTION_PROTOCOL_CONTRACT_PAYLOAD_SHA256
            or document.get("route_state") != ROUTE_STATE):
        raise AssertionError("execution-protocol anchor predecessor identity drifted")
    authority = document.get("source_authority", {})
    controls = authority.get("control_sources", [])
    fixed = authority.get("fixed_non_control_sources", {})
    transitions = document.get("historical_source_successors", {}).get(
        "overrides", {}
    )
    control_paths = set(D0_CONTROL_SOURCES)
    fixed_paths = set(D0_CHANGES) - control_paths
    transition_paths = {
        path for path, item in D0_CHANGES.items()
        if item["change_type"] == "M"
    }
    if (tuple(controls) != D0_CONTROL_SOURCES
            or authority.get("control_source_count") != 7
            or authority.get("fixed_non_control_source_count") != 48
            or set(fixed) != fixed_paths
            or set(transitions) != transition_paths
            or control_paths & fixed_paths
            or control_paths | fixed_paths != set(D0_CHANGES)
            or sha256_json(controls)
            != "b0d38af07b440adc413433c8307350fd135921117b42b0749d520ca26367e089"
            or sha256_json(fixed)
            != "f701ca15dc594369a43234f5b0615d6ad7d7e27a80e30c013002650084faefd7"
            or sha256_json(transitions)
            != "3a360d9e4c636b8c3e731bacd7d0598c75d73c1e77d18c013c7131569e16e6e3"):
        raise AssertionError("execution-protocol D0 authority partition drifted")
    if (authority.get("control_sources_excluded_from_self_authority") is not True
            or authority.get("current_control_sources_external_git_anchor_complete")
            is not False
            or authority.get("dynamic_source_discovery") is not False
            or authority.get("ordinary_build_and_load_are_gitless") is not True
            or authority.get("fixed_c2_commit_replay_is_explicit_only") is not True
            or authority.get("live_head_main_or_origin_authority") is not False):
        raise AssertionError("execution-protocol D0 authority trust boundary drifted")
    for path, descriptor in fixed.items():
        item = D0_CHANGES[path]
        if (descriptor.get("source") != path
                or descriptor.get("sha256") != item["sha256"]
                or descriptor.get("byte_count") != item["byte_count"]):
            raise AssertionError(f"execution-protocol D0 fixed source drifted: {path}")
    for path, descriptor in transitions.items():
        item = D0_CHANGES[path]
        if (descriptor.get("source") != path
                or descriptor.get("accepted_sha256") != item["previous_sha256"]
                or descriptor.get("accepted_byte_count")
                != item["previous_byte_count"]
                or descriptor.get("successor_sha256") != item["sha256"]
                or descriptor.get("successor_byte_count") != item["byte_count"]):
            raise AssertionError(f"execution-protocol D0 transition drifted: {path}")
    controls_current = sum(D0_CHANGES[path]["byte_count"] for path in control_paths)
    fixed_current = sum(D0_CHANGES[path]["byte_count"] for path in fixed_paths)
    fixed_parent = sum(D0_CHANGES[path]["previous_byte_count"] for path in fixed_paths)
    transition_current = sum(D0_CHANGES[path]["byte_count"] for path in transition_paths)
    transition_parent = sum(
        D0_CHANGES[path]["previous_byte_count"] for path in transition_paths
    )
    if (sum(D0_CHANGES[path]["change_type"] == "A" for path in control_paths) != 7
            or sum(D0_CHANGES[path]["change_type"] == "A" for path in fixed_paths)
            != 11
            or sum(D0_CHANGES[path]["change_type"] == "M" for path in fixed_paths)
            != 37
            or controls_current != 219_047
            or fixed_current != 1_890_914
            or fixed_parent != 1_626_323
            or transition_current != 1_668_984
            or transition_parent != 1_626_323):
        raise AssertionError("execution-protocol D0 authority byte aggregates drifted")
    authorization = document.get("authorization", {})
    for field in (
        "migration_global_preflight_evidence_closed",
        "migration_durable_ledger_freeze_design_evidence_closed",
        "operator_core_evidence_closed",
        "bounded_40001_40P01_retry_implemented",
        "operator_migration_implementation",
        "migration_execution_protocol_implemented",
        "cryptographic_evidence_verifier_implemented",
        "local_test_backup_restore_execution_rehearsal_closed",
    ):
        if authorization.get(field) is not True:
            raise AssertionError(f"execution-protocol D0 true gate drifted: {field}")
    for field in (
        "source_successor_external_git_anchor_complete",
        "semantic_successor_external_git_anchor_complete",
        "bootstrap_control_sources_external_git_anchor_complete",
        "current_node_control_sources_external_git_anchor_complete",
        *PRODUCTION_FALSE_FIELDS,
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"execution-protocol D0 closed gate drifted: {field}")
    predecessor = document.get("predecessor", {})
    if (predecessor.get("contract_id")
            != "ti.phase4c.personal-bank-tag-migration-operator-core-post-push-anchor-contract"
            or predecessor.get("fixed_commit_oid")
            != "4c47d1ea220ae9e310338bbf23b74d87d477e20f"
            or predecessor.get("sha256")
            != "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936"
            or predecessor.get("document_payload_sha256")
            != "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64"
            or predecessor.get("byte_count") != 84_461
            or predecessor.get("immutable") is not True):
        raise AssertionError("execution-protocol transitive Node C authority drifted")
    worm = document.get("worm_successor", {})
    runtime = document.get("production_runtime_successor", {})
    if (worm.get("current_report", {}).get("sha256")
            != "5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c"
            or worm.get("current_report", {}).get("byte_count") != 1_442
            or worm.get("current_chain_node_count") != 9
            or worm.get("current_build_context_sha256")
            != "36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7"
            or worm.get("dockerfile_sha256")
            != "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
            or runtime.get("accepted_file_count") != 307
            or runtime.get("current_file_count") != 311
            or len(runtime.get("added_files", {})) != 4
            or len(runtime.get("changed_files", {})) != 0):
        raise AssertionError("execution-protocol D0 WORM/runtime boundary drifted")


def _validate_independent_evidence(document: dict[str, Any]) -> None:
    runner = document.get("independent_acceptance_runner", {})
    authority = document.get("fixed_d0_authority", {})
    verification = document.get("verification", {})
    if (document.get("contract_id") != EVIDENCE_ID
            or document.get("schema_version") != 1
            or document.get("status") != "passed"
            or document.get("scope")
            != "phase4c-learning-tag-migration-execution-protocol-fixed-d0-independent-copy"
            or document.get("route_state") != ROUTE_STATE
            or authority.get("commit_oid") != D0_COMMIT
            or authority.get("parent_oid") != D0_PARENT
            or authority.get("root_tree_oid") != D0_CHECKPOINT["root_tree_oid"]
            or authority.get("ti_java_tree_oid") != D0_CHECKPOINT["ti_java_tree_oid"]
            or authority.get("diff", {}).get("changed_path_count") != 55
            or authority.get("diff", {}).get("added_path_count") != 18
            or authority.get("diff", {}).get("modified_path_count") != 37):
        raise AssertionError("execution-protocol independent evidence D0 authority drifted")
    raw = runner.get("raw_report", {})
    if (runner.get("path") != RUNNER_RELATIVE
            or runner.get("sha256") != RUNNER_SHA256
            or runner.get("byte_count") != RUNNER_BYTE_COUNT
            or runner.get("git_mode") != RUNNER_GIT_MODE
            or raw.get("sha256")
            != "183efaafbe3a55643780b43350853c402d22c9af8919d619fcd6f448b8b07489"
            or raw.get("byte_count") != 8_718
            or raw.get("tracked") is not False
            or raw.get("embedded") is not False
            or raw.get("required_for_gitless_successor_acceptance") is not False):
        raise AssertionError("execution-protocol independent runner/report drifted")
    maven = verification.get("maven_full", {})
    focused = verification.get("focused_node_d", {})
    source_discovery = verification.get("source_discovery", {})
    if (verification.get("timezone") != "UTC"
            or any(verification.get(field) is not True for field in (
                "phase1_passed", "phase2_static_passed", "phase3_static_passed",
                "phase3_topology_static_passed", "topology_data_plane_passed",
            ))
            or verification.get("miniprogram")
            != {"tests": 36, "passed": 36, "failed": 0}
            or maven.get("surefire")
            != {"tests": 898, "failures": 0, "errors": 0, "skipped": 0}
            or maven.get("failsafe")
            != {"tests": 178, "failures": 0, "errors": 0, "skipped": 0}
            or focused.get("unit", {}).get("tests") != 31
            or focused.get("execution_protocol_integration", {}).get("tests") != 2
            or source_discovery.get("executed_inside_independent_copy") is not False
            or source_discovery.get("claimed_independent_copy_test_count") != 0):
        raise AssertionError("execution-protocol independent verification drifted")
    for suite in focused.values():
        if any(suite.get(field) != 0 for field in ("failures", "errors", "skipped")):
            raise AssertionError("execution-protocol focused verification is not green")
    compose = verification.get("compose", {})
    cleanup = verification.get("cleanup", {})
    if (compose.get("healthy_service_count") != 3
            or compose.get("restarted_service_count") != 3
            or compose.get("all_services_healthy_after_restart") is not True
            or compose.get("source_worktree_bind_count") != 0
            or compose.get("environment_secret_value_count") != 0
            or any(cleanup.get(field) != 0 for field in (
                "container_residue", "network_residue", "volume_residue",
                "image_residue", "cache_volume_residue", "port_residue",
            ))):
        raise AssertionError("execution-protocol independent isolation/cleanup drifted")
    if any(document.get("production_boundary", {}).get(field) is not False
           for field in document.get("production_boundary", {})):
        raise AssertionError("execution-protocol independent production boundary drifted")
    closure = document.get("closure", {})
    if (closure.get("fixed_d0_independent_copy_acceptance_closed") is not True
            or closure.get("proves_only_commit") != D0_COMMIT
            or closure.get("proves_d1_evidence_commit") is not False
            or closure.get("proves_d2_anchor_commit") is not False
            or closure.get("execution_protocol_control_sources_external_git_anchor_complete")
            is not False
            or closure.get("self_hash_embedded") is not False):
        raise AssertionError("execution-protocol independent closure boundary drifted")


def _read_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _read_fixed_json(
        root, EXECUTION_PROTOCOL_CONTRACT_RELATIVE,
        EXECUTION_PROTOCOL_CONTRACT_SHA256, EXECUTION_PROTOCOL_CONTRACT_BYTE_COUNT,
    )
    _validate_execution_protocol_contract(contract)
    evidence = _read_fixed_json(root, EVIDENCE_RELATIVE, EVIDENCE_SHA256, EVIDENCE_BYTE_COUNT)
    runner = _fixed_regular_file(root, RUNNER_RELATIVE)
    runner_bytes = runner.read_bytes()
    runner_mode = f"{stat.S_IFREG | stat.S_IMODE(runner.stat().st_mode):06o}"
    if (len(runner_bytes) != RUNNER_BYTE_COUNT or sha256_bytes(runner_bytes) != RUNNER_SHA256
            or runner_mode != RUNNER_GIT_MODE):
        raise AssertionError("execution-protocol independent runner identity drifted")
    _validate_independent_evidence(evidence)
    return contract, evidence


def build_contract(
    ti_java_root: Path = ROOT,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    predecessor, evidence = _read_inputs(root)
    if repository_root is not None:
        validate_fixed_git_checkpoints(repository_root)
    authorization = {
        "migration_global_preflight_evidence_closed": True,
        "migration_durable_ledger_freeze_design_evidence_closed": True,
        "operator_core_evidence_closed": True,
        "execution_protocol_evidence_closed": True,
        "bounded_40001_40P01_retry_implemented": True,
        "operator_migration_implementation": True,
        "migration_execution_protocol_implemented": True,
        "cryptographic_evidence_verifier_implemented": True,
        "local_test_backup_restore_execution_rehearsal_closed": True,
        "execution_protocol_control_sources_external_git_anchor_complete": True,
        "independent_acceptance_control_sources_external_git_anchor_complete": True,
        "source_successor_external_git_anchor_complete": True,
        "semantic_successor_external_git_anchor_complete": True,
        "bootstrap_control_sources_external_git_anchor_complete": True,
        "current_node_control_sources_external_git_anchor_complete": False,
        **{field: False for field in PRODUCTION_FALSE_FIELDS},
    }
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": STATUS,
        "scope": SCOPE,
        "execution_protocol_contract": {
            "source": EXECUTION_PROTOCOL_CONTRACT_RELATIVE,
            "contract_id": EXECUTION_PROTOCOL_CONTRACT_ID,
            "sha256": EXECUTION_PROTOCOL_CONTRACT_SHA256,
            "byte_count": EXECUTION_PROTOCOL_CONTRACT_BYTE_COUNT,
            "document_payload_sha256": EXECUTION_PROTOCOL_CONTRACT_PAYLOAD_SHA256,
            "immutable": True,
        },
        "independent_acceptance_evidence": {
            "source": EVIDENCE_RELATIVE,
            "contract_id": EVIDENCE_ID,
            "sha256": EVIDENCE_SHA256,
            "byte_count": EVIDENCE_BYTE_COUNT,
            "captured_at": evidence["captured_at"],
            "runner": deepcopy(evidence["independent_acceptance_runner"]),
            "raw_report_required_for_gitless_build": False,
            "immutable": True,
        },
        "implementation_checkpoint": _checkpoint_document(D0_CHECKPOINT, D0_CHANGES),
        "independent_acceptance_checkpoint": _checkpoint_document(D1_CHECKPOINT, D1_CHANGES),
        "execution_protocol_authority_anchor": _authority_anchor(predecessor),
        "transitive_node_c_anchor": {
            "predecessor": deepcopy(predecessor["predecessor"]),
            "immutable": True,
        },
        "independent_copy_verification": {
            "fixed_archive": deepcopy(evidence["fixed_archive"]),
            "verification": deepcopy(evidence["verification"]),
            "docker_and_host_trust_boundary": deepcopy(evidence["docker_and_host_trust_boundary"]),
            "original_closure": deepcopy(evidence["closure"]),
        },
        "production_and_worm_boundary": _production_boundary(predecessor),
        "authorization": authorization,
        "route_state": deepcopy(ROUTE_STATE),
        "current_node_trust_boundary": {
            "control_sources": list(CURRENT_CONTROL_SOURCES),
            "control_source_count": 6,
            "control_source_allowlist_exact": True,
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "d2_commit_or_tree_identity_embedded": False,
        },
        "acceptance": {
            "implementation_checkpoint_changed_path_count": 55,
            "implementation_checkpoint_added_count": 18,
            "implementation_checkpoint_modified_count": 37,
            "independent_acceptance_checkpoint_changed_path_count": 2,
            "independent_acceptance_checkpoint_added_count": 2,
            "implementation_control_source_count": 7,
            "implementation_fixed_non_control_source_count": 48,
            "implementation_transition_count": 37,
            "independent_acceptance_control_source_count": 2,
            "current_control_source_count": 6,
            "anchor_closes_no_functional_gate": True,
            "d2_self_anchor_complete": False,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "next_gate": (
                "Phase 4C business-route migration remains separately required; "
                "production apply and cutover remain unauthorized"
            ),
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


# The complete fixed checkpoints and validators are appended below.  Keeping the
# construction API above stable lets the Python and Java consumers bind the final schema.
_D0_ROWS = r"""
docs/refactor/05-progress.md|M|100644|100644|436c57475a6b5a6b47dcdec22d96d173f0600ea4|1a018df4fe7418c7fe6d5e723336261cdd2d22cf|71fc8bf98bc4fb50645df473ee79b2bc33856ca928f49da7aecc96a7d1040f9d|109838|2fb55e0aaaeff28c3c3def877b5be51ae2ea6358272222f0e0f8232dec69867f|109911|7|6
docs/refactor/phase4c/README.md|M|100644|100644|338c0d80d8d48f062ee66bcb59c3b6bd2641ca47|673416e51f84546305d4d42b92eb3996c237555e|f061ac5e2b240e3b8c367f9db817c84346a309e9872cfbdeeafe8d3ff8689230|29918|ab5144697dfded1778d40209958a2c3fdcc7bfc1b08d5dde481cc6a8f009ed6e|31994|30|4
docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-contract.json|A|000000|100644|0000000000000000000000000000000000000000|a28dff8df00848ed235e3f0100582c6df15c60b1|-|0|e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14|44336|741|0
docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-worm-evidence.json|A|000000|100644|0000000000000000000000000000000000000000|fb638a6559792f38d19b9e01b7a4e8cf60c8e009|-|0|5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c|1442|42|0
docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol.md|A|000000|100644|0000000000000000000000000000000000000000|18ed72b9a611f7b64eb516c4ab4f8bbcc014ea07|-|0|bcae940ed30588c628e1b4f80567770d61cd92b0d6fb0191229a889c2e5223ed|7512|99|0
infra/phase2/README.md|M|100644|100644|9f0c925ca75b12f24775a262ce4e99d6cc3804e5|2f674460dcc6eeb41c2c0d0caf08b372ba0ef526|d5c8647397016f93c8ea2b5e83b41818ea00498fd7e699cc1119930f1995e21b|8018|187895861b607be2cfddb63320b4ee52dc4efd7706e94afd5d56a07169832216|9031|2|2
infra/phase2/verify-static.sh|M|100755|100755|1a27ee8bb00128a46d98de35684edc9f5e6dd5e5|3ff3abf797d024271043463d3f334c7fdc92ee4f|2a1a5a5453a1090f6132971081d4ac2448803023acb50d474ced491bafe8efc3|17491|6878d027fc21c1564840771609f0f2e9dfa6eb2bb483b56b6abfd1e9386eb4a3|18597|18|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/Ed25519TagMigrationEvidenceVerifier.java|A|000000|100644|0000000000000000000000000000000000000000|7700eaa88dd8ca1ecdc514bf9fc722044d4ffdc4|-|0|0db53a72f3ecbb5a72eefde3a4b042d3771727792cf9bc7b008b4dc7928c3573|53495|1321|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationExecutionProtocol.java|A|000000|100644|0000000000000000000000000000000000000000|3bb7bde36b0af079dec3b8d6d6af81c485a24985|-|0|9fbacb71fb333d4c6d90127255c12108321c2cec90666300e9bfbc5d7d82657c|8972|217|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidate.java|A|000000|100644|0000000000000000000000000000000000000000|107d380634e038cebc158d27e4b251f5980d312d|-|0|e324adad954d337cfd92ec77f7fd5eb30db9d002b5be6a37d73c4a92e3161c8d|5394|156|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidateFactory.java|A|000000|100644|0000000000000000000000000000000000000000|b52af186a3eedf9aff66ee09d652ca0c759be3c6|-|0|336d24f66a57becafb0ac579f18d89391a935070510456de8626224672abcb54|8504|191|0
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java|M|100644|100644|06f3d781bd8a62e859b196c2d750cd8dcc37943f|bab8edb83f8d0e35498affe249611818c388d8bc|9f929532d8c31f96f4e3e5cd24ee199220c82ad2aac46f5944ee0d54cd22dbb6|91381|ef55aee6c941c124653138a482769e19a85ab72b5e3ed83ee6d15803b15c2d6d|91381|1|1
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java|M|100644|100644|45c1e9b99c372a338243eb875b2e113e7863d259|2d73c631533c5f5be13d577959527062c2b2d2b1|cb4cabfce2cded7cde291b54d2c2dd98cc397887d24141e5164250a8811fb369|79867|c20a6bd120b9c6eb2e930b8d1ac574814c2ac075b893de717991dce7e4af631e|80004|3|0
server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java|M|100644|100644|48f23b74a78b3c0ff474c817931eb344ae7210e0|cabb5c5ba289090d8a88111bde3b1fb0edc8c7f7|137f3a9911d886610300aecc95a13f05d5621d18c19acf491194f1b8b741efe3|17439|6ed99111749568ffeffe8f04e029cc273a9e60d59b6fdaf3e6eefe5e2a668ffb|18511|26|4
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolContractParityTest.java|A|000000|100644|0000000000000000000000000000000000000000|fde18b32f98ce0cdd5e1adc2aa56fc3befd917c7|-|0|4f0f67109a93096e9d10153a953ec43a45a464c17bd882a86a00a48917d8d4b9|15306|326|0
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java|A|000000|100644|0000000000000000000000000000000000000000|9a9f88ceaf7791c5b8060a4272161a130e08e6b6|-|0|85b32075327dcbffd4790f760d2cd91714c183a4ccda509b5f71278cfdcd65d2|51291|953|0
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java|M|100644|100644|69af67392719d35c19decf063ed6e0b7c0a920cc|ee04b2574a4ba11b302cedb5150abbcc983cbde7|bdb3ee1169dfe164016a2afc6a46e6e3fff7abe9b8602988ab9d0c0ecff86158|43784|849d3fe9b644f7811c13c4ba24a119170f1120a38c86635c3a6d5942e8cd44b9|46172|66|16
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java|M|100644|100644|0f830da46360e9c6e5a27b3b5e8964994949bd48|e042520beec1918eb92e240055c26ababe014a9a|e5471121ea2fc52f9e36712b222578e24323d5785dddf27b27a86799867fc99f|102527|f3046ce6749f6f0facc3db8b18ee3227c04f6ff0ced54f4df56871e1b7192677|102737|7|4
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java|M|100644|100644|0db00609bf1d1de1c9c720c6ecd2223c74428885|3db1859581177d73861e8eec538d2ef71412512e|f7dad6c7d51769669fda0cb2c26a7c3991ad3bfae27178c9c8a470f6addff361|27467|9076e30366370c7ed61b962c0a987d1c2b1758e749bd1cc44f98f43387c4fd5b|28965|43|17
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java|M|100644|100644|2f39ed66c73b189a94a997062851c8d416532837|9be8f43bfa537bf79c8839e6de3871777ab5486c|486bbc757e44408dc9237eade44ec3f4e2cd60bd2d3360c1cc54bdaf426eacb1|19496|124d72fa07fcb3306e5476416afc124a2e2d51549406a1fee8483b757a7ab7bc|20374|25|7
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java|M|100644|100644|d13d34ef8fb5ad97b333c0581bd7ed2288a81c06|5e609c8e12dbcabb7f00a68cb85ee0c7ce1378ed|83840dc07301be40828df8bd46f214bc2d50342bde6f8fb8412eca1ae3a7092c|83287|35a2352ba8218594919dd2b08108c644ada708b9885300ccfa22d1f17a931831|89356|143|23
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java|M|100644|100644|810ac931232c5f5ec078cb5d59c94cce5b344a7a|8ca76094d978ef0ac14bda0e7af41578e8956983|bd83bffe8851e2368f3d9280d213b7adac1b4073dbe2296bd1d6e1c6183a454e|51156|e81298382c14c91689348997e3ab6b9a9d1722fa0decbbd8f4a525bf0a07db74|51293|3|0
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java|M|100644|100644|535abcb351e1f523f2b7e350c06a63163e98642c|ea48e432dee5d4be7fb9a58e7e17c2282177c9a9|ea9affd42829d4560c2b974e8d189bd6feac340112732cf15b89d797f7b4f7af|11762|57e45fe2031115551b8ae1035751a8cb2ef3e0de7de500511d02acff3400bd73|12204|10|1
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/Ed25519TagMigrationEvidenceVerifierTest.java|A|000000|100644|0000000000000000000000000000000000000000|653cb983620e3d0e34b758306362f674d01a958d|-|0|dac1055f16b551fe934aea35d820fdf04c6a356ea74d31f58afeb744feb53da7|32990|841|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationExecutionProtocolStaticTest.java|A|000000|100644|0000000000000000000000000000000000000000|3d29088bd4256a80f13b8fa6e277a910b9684340|-|0|f6f3227cdcae98dbf348691359e3dd13c4cd3a1af045a19234030d117a19c989|11445|264|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT.java|A|000000|100644|0000000000000000000000000000000000000000|55fa482f9d28ff098abd04a24abb1fd33f5fab7e|-|0|cfd4b4944e5f7b40c18b0ae10ebec8efaca0ef71a63446079ab776217037c1da|75966|1762|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidateFactoryTest.java|A|000000|100644|0000000000000000000000000000000000000000|5f98bd6e7e6412dcf458144aded6e1e17c25abe9|-|0|12d2bb0f0e6f99a7731d1315900dd28a06020d7e16e23e9943477beff3842795|17286|390|0
server/src/test/resources/db/phase4c/078-legacy-personal-bank-tag-migration-execution-protocol-schema.sql|A|000000|100644|0000000000000000000000000000000000000000|d84358a758206f726023dbee7aef232609020bef|-|0|b93e738bff82e4c5b19fa41570e73f807aad2c32f78e8e7a6e517c42db5d9c9b|4368|105|0
server/src/test/resources/db/phase4c/079-legacy-personal-bank-tag-migration-execution-protocol-seed.sql|A|000000|100644|0000000000000000000000000000000000000000|6f8dccad46d10837647bf9573af025b2b2b0c796|-|0|c84d8511797d16b85025561f591b9248105a38b99d1944b6b04332dfc62588fe|2068|60|0
tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py|M|100644|100644|58e58492a558d7a11d232b0ac1bc54288cbae93a|788a84ce6415f8c389fe3c9630b3e6bc085940a7|8d96674c8ea55f6050133945f0f58fe365ea9383d7660ba3c6d3423cf63bc7c5|36240|90ff8b73b778025b16de2c46ec1b4e789f0e677fccd03f67a9aeea546b90753a|36240|1|1
tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py|M|100644|100644|78b44b2b631d02210ce5318d19a64f3308af1b7c|8466af282595e13de4dc9e7329a420cfef96efba|c9d21809bd136ed131ee20ac6baabf0b6b67bcc85f03fab9fccedcd02c86f2c0|65798|bf4b24b4e9568dde5d88ee0985cd765c063ee09e9ec2e5dc9a19f59ee6f66f0b|65798|1|1
tools/build_phase4c_tag_migration_execution_protocol_contract.py|A|000000|100644|0000000000000000000000000000000000000000|b7d79efe6b1ad6be8401fab7ab104a76ed2eff71|-|0|bcb7c0f3098f49d4af385324fd9a2377656e9fefba0d7e2e02ebc94b04cc5636|65614|1031|0
tools/build_phase4c_tag_migration_global_preflight_contract.py|M|100644|100644|acbef90234ad00715d7f290f895153b25089de7b|863425d1db39faa44ba8ef6c577bd538640c2785|604c550ceb144c0bdca1d92e915a166d84c582cd53084f934bac71e171154ddf|129684|4efc2cf1a1e0e637dab550d44783e90082d597a18496e2fe63b15fff65b89e66|129994|12|4
tools/phase2_wormhole_successor_acceptance.py|M|100644|100644|b863cf9e8cfcaab2a3ba855431b7207fae63e515|f3f64e7dd2f19a1935dce92709bf3c145096b362|afd967894036289ad3587fc740c97931d1ca5492a9208829536bf6745a840ebc|30285|fed88c98f558a70398181b68edfabf2b75f2ab62184793230cb17a7efce96acd|32082|39|0
tools/phase4c_http_target_execution_anchor_successor_acceptance.py|M|100644|100644|7619ad3f87a0875815f42b03d89b5b1f9adbe397|7208309d7b0986970309d856aab366ca414f4462|810efb88c88efeb35b7a1f182214dc8873ca7099d8f6dfb8ce6b1af651dd3ecd|36566|e002d6aefee761693087cf549d65f84f4887bb5b7146f8c19b36d9810f3a4cf7|36566|1|1
tools/phase4c_http_target_execution_successor_acceptance.py|M|100644|100644|31bc79a7ff51677880c131521d65a7452f4cdb69|586427e9788f345d32570a38a78083d8e11d8b74|4048e962b5db2d332c0955099a77637c3542b77e58fd233b5460296c1f86abd9|84585|39f997767d20c0e0382c6277da873ae8062a5823cd78910c0f4209823ad682a0|84585|1|1
tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py|A|000000|100644|0000000000000000000000000000000000000000|cfc7ca84573794864436f050995963ffa9486c79|-|0|434bb8ab22083dab4f63efb2b77ab0b86ebd55d2946726e0902579c458458789|20338|525|0
tools/phase4c_tag_migration_global_preflight_successor_acceptance.py|M|100644|100644|e13d989ac9d6c9c98c3577af6fdd587c9eca0339|b74ee6c1d7e46969e4c04c8361262c94984f208a|6fe3bf23d53ccaccd33f3ccaf31466cf0fc44df0f71bcc6f798765519fe12f95|32367|d7a116cb3432e280b97a076347b1e659be4cfe9a811d879ead4c4eb886a2679d|33035|31|7
tools/phase4c_tag_migration_operator_core_successor_acceptance.py|M|100644|100644|dc8b98c37da6b755408bafb28323412a18b23328|18f64a98711473f3bfca312e6e2064b23f9d7c9b|c7e672f3a0d0ab959735de906c0e5131232c0dab17b698480f6a42cfb5871ee4|17419|6efd1cb559a6d7da470c2a454dc981db9d7ff670f8053b8b9b9597af270b18f3|25844|238|18
tools/test_phase2_wormhole_successor_acceptance.py|M|100644|100644|8c1dec264fedf8a6ffce01238bdfacdce1a9aa94|b8fe872e19edd1536427c4d1094e3d1dd14a8514|2c4881c5083c8e4ca2cf294ece486895e26d932d1f59d067f8da32ef544c63bc|54340|cf2e7f8023ee9036f94e2ff46a1464b8af1bbe5e20e8b5382f49198bb50b9313|55974|51|12
tools/test_phase4b_personal_bank_all_shares_entry_contract.py|M|100644|100644|2fe7883a0eac6093600ddcf62718149f5b5fafa0|d151ad93d30eaf975e3ae420beb5f046f43c08d5|ab79ec3edc9f903a9917ae85450633982031f341aa219e75de08d69db0c63d26|24250|612e5de6dffc85b20e19f7cfb882bf2caa36a796d29c500cb0598b308781cc4c|25488|32|3
tools/test_phase4b_personal_bank_all_shares_read_contract.py|M|100644|100644|573f9cf3b18388c2a6995ee103685120ebc533be|0b4ccf4d4337ad5d3d37517e4d6380fb80144b2e|a308ba6b14bb9e960006378bdf165dc2dfece856bb09bf827d600a7a6f28e060|19452|46f08e7c6e57696609eda1f89eaaba9023dd6dbe6a3ec999dbfaca6dfed49a1e|20644|30|3
tools/test_phase4b_personal_bank_share_list_entry_contract.py|M|100644|100644|b8d998a058c13eaaf50234f50e73b4cb22f46d55|59362ea49d53ffda2e23969464f187c01ee92bed|3b59d4f9f4c3cafe84feb4bc0a902db1822455e73660f29461d2385370377122|33266|7d692b2c577f584ba2534e20c017d941129fe7db50b38bb5f1597d1da697f806|34561|36|5
tools/test_phase4b_personal_bank_share_list_read_contract.py|M|100644|100644|2a661ffda5e90eb7f7579b543bc28ceed55f6d00|3e1e0be143b4b8a59334eb07199854a9b12e113f|49441844f63e05ca57e0b89c751cca3b1b574c984223e588d40bac9e7613501f|45548|1f3dceccb6637949f197637b2ca1edf0f0a7269b202cecf0a0da4cbf12fe8e6b|46740|31|4
tools/test_phase4b_personal_bank_usage_stats_entry_contract.py|M|100644|100644|be92ef0ad6aebaec7660745eeaa82f38df14463c|b7b34447988c0ff26ffa1858e455b92450309c26|9625aad3553408ef631d055735af33b4b21847aaaf8a57d540dd582cba025ab9|25599|9b9fcfc637a62a7407a56557846284d60a3c03a65bd82ebcd4641e840c488b59|26791|30|3
tools/test_phase4b_personal_bank_usage_stats_read_contract.py|M|100644|100644|ff24a7287e02fc42720200994ce73af7799df710|c8b2c74b4a32645a9ab69a592a4bd907a18c054a|7c8a27ef4e97ed731dd4b0dd357942e32e75a45db3d9e482e7513b1e8c1820a4|34464|a34dfbeab04bbcbe66847c7f033e56a76e202dbdb71a669a25c8baf9f0cac884|35656|30|3
tools/test_phase4b_personal_bank_user_counts_entry_contract.py|M|100644|100644|8144af74c4027be7545a9765d234d5c27ced432d|1b400f84ca02ce8ff7c35f7c3792200716c78bc0|409a2663e26f559108e815a805f42f566f2a7dfea8d1da8f9aab966efa0a14cb|37035|08af86b0cf2b6fb8c59d531500ddc58ca5b0ffc003929e054eb0062f9e25e638|37521|13|4
tools/test_phase4c_personal_bank_user_counts_composition_contract.py|M|100644|100644|42f5474769a190526970517c77ca5c7542cc637e|e77d320dc524eb158f755f7ab15b01fd179a3b54|18cdd0df59a7cfa6d052192ca85fe59cd50415fe263ae172133958d59df1f544|60156|c405f432a55caaa7ede0375b18fbc8819b82b3ffeb62e29f10ff5f0793b45c20|60642|12|3
tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py|M|100644|100644|ba48e3e38075203fb4427c6e141f0b837780ea96|febd08126f517d4f8efbf09a9d4da14939d651b6|17e77b5204bdec0b2deb43517354fada893802321a1cfa8f446151fcb5a2b0c9|32398|a05b7f0052e66d4233227a9995f0fc9ea1f34cba00269c1ea0999acaa60d801b|32398|1|1
tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py|M|100644|100644|bf24cb37535cf77568b4c9ad63cf984b966cf5b2|630dfb29f5a7de5c1e7e5f4b815bfce60adfe8b6|7e6039fd7288cd16980149b385f71faa79659092f5bd187c14d060a19c08fe84|34398|6ebf44750d2eb5320c79351e9fa7a2e242207da3e4a4c400a0e9b110625546e3|34398|2|2
tools/test_phase4c_personal_bank_user_counts_read_contract.py|M|100644|100644|c2b8ce88c6f9edbafd8be7387de95ddf8fb9b17c|dffa34a30271b9d29b5b90c4cc096603ead25059|3aacc3a54b0ecc6314f0f84d51057f657e8c188d1f673d931092c40c3f39106b|24536|d8c745ff35f298f91afb8a723bc7676187c7da4a67000b02eb7ab2752a0d3522|24536|2|2
tools/test_phase4c_tag_migration_execution_protocol_contract.py|A|000000|100644|0000000000000000000000000000000000000000|8a000f1258bda6618bf6b936076fd0655fe1fd46|-|0|63ef875a69da1ed669010b484384a1e0013c87e4c1f8a059d124a01a96a643a8|14650|352|0
tools/test_phase4c_tag_migration_global_preflight_contract.py|M|100644|100644|67c0190f9f27ee9478e0660040589f69ef5220e5|9f05194372c130a92fbab3cc851a7f1b0fd078be|28548d878900d0aeba6b983ba307af077b4ebdd01a6b27f4c496bf6ae472c313|38541|f40cfec25a0cbcd5ef250ba3ba93408cf73c397e77e1a7dd7d03c67da0b1ed1a|40427|53|14
tools/test_phase4c_tag_migration_operator_core_contract.py|M|100644|100644|7c18a8df5d575eca691e4f3cb87967dc791062ec|c1f871c38beb788d4c76f369efedde60497bb93f|d3f89f0943d6aace6545f3f97ccc997d0c3aee9bc7175363bd47930281dfa42f|18250|3c480aa1fd2378ed2c059965663c516c3ed5390c3c1e165f9a7e6855176df4b5|19902|60|22
tools/test_phase4c_tag_migration_operator_core_post_push_anchor_contract.py|M|100644|100644|f42436a7ffc3bde29a5fb2eba60e6480c5f44e5b|15f5fe75a568b4261c23c30b6fd1692de938add1|2ddf897a07152d1a4a12f044ffe3d290591f86a3b21463aa1e25d74186345cb0|17715|ca947234c2ffe31f929cbd443101c01215b6a8a2d2ea7d454afa950a83a3f120|18632|24|2
""".strip()
_D1_ROWS = r"""
docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-independent-acceptance-evidence.json|A|000000|100644|0000000000000000000000000000000000000000|f21f8173a5eb634391c141d17dec1f21e69d0765|-|0|eb874216f39a008d2da6df51d31471dd1dc11773781f840cd06afa87ebddf993|9561|240|0
tools/run_phase4c_tag_migration_execution_protocol_independent_acceptance.sh|A|000000|100755|0000000000000000000000000000000000000000|e13cdffb503a48cb8767f445716db409efbd2599|-|0|127a99443a670362e81349742477f5ba596df5694fe50fec6b64f485ece3d994|66124|1653|0
""".strip()


def _changes(rows: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows.splitlines():
        (
            relative, change_type, previous_mode, mode, previous_oid, oid,
            previous_sha256, previous_bytes, sha256, byte_count,
            insertions, deletions,
        ) = row.split("|")
        if relative in result:
            raise AssertionError(f"duplicate fixed checkpoint path: {relative}")
        result[relative] = {
            "repository_path": f"Ti-Java/{relative}",
            "ti_java_relative_path": relative,
            "change_type": change_type,
            "previous_mode": previous_mode,
            "mode": mode,
            "previous_git_blob_oid": previous_oid,
            "git_blob_oid": oid,
            "object_type": "blob",
            "previous_sha256": (
                None if previous_sha256 == "-" else previous_sha256
            ),
            "previous_byte_count": int(previous_bytes),
            "sha256": sha256,
            "byte_count": int(byte_count),
            "inserted_line_count": int(insertions),
            "deleted_line_count": int(deletions),
        }
    return result


D0_CHANGES = _changes(_D0_ROWS)
D1_CHANGES = _changes(_D1_ROWS)

D0_CHECKPOINT = {
    "object_format": "sha1",
    "commit_oid": D0_COMMIT,
    "parent_oid": D0_PARENT,
    "unique_parent_fixed": True,
    "root_tree_oid": "76ddb6bfd9a864c350dcdf86303518404227afae",
    "parent_root_tree_oid": "e6ef65c88e87dd73a380f7e7fb095506b9e9b4bd",
    "ti_java_tree_oid": "a6c06e505bb3fbd1792ebcc02a78074d306ba830",
    "parent_ti_java_tree_oid": "e214920a30f837aa1760bd4fbc14687f45e9c79d",
    "server_tree_oid": "4743880e2a4bdd6c58c4d274ecdf50fb939c9d06",
    "parent_server_tree_oid": "8deb885bcddbe35485ff67c6a07ded2a77bd3e2e",
    "server_src_main_tree_oid": "9abb4667d87a9433a67d0556dbeac37e10c87dfc",
    "parent_server_src_main_tree_oid": "bdd88effe149c61fada2300a4ec85bb2a3fdaf1c",
    "web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "parent_web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "miniprogram_tree_oid": "9e4f37fe49303329df392dfbe64d2ce9064b7c86",
    "parent_miniprogram_tree_oid": "9e4f37fe49303329df392dfbe64d2ce9064b7c86",
    "authored_at": "2026-07-23T17:20:26+08:00",
    "committed_at": "2026-07-23T17:20:26+08:00",
    "subject": "feat(java): add tag migration execution protocol",
    "changed_path_count": 55,
    "added_count": 18,
    "modified_count": 37,
    "deleted_count": 0,
    "non_ti_java_count": 0,
    "inserted_line_count": 10_491,
    "deleted_line_count": 201,
    "current_total_bytes": 2_109_961,
    "parent_total_bytes": 1_626_323,
    "net_byte_increase": 483_638,
    "added_total_bytes": 440_977,
    "modified_current_total_bytes": 1_668_984,
    "modified_parent_total_bytes": 1_626_323,
    "exact_fifty_five_path_delta": True,
    "diff": {
        "standard_raw_sha256": "02edc714c98d4ef9cff4f1fdc0a9164e5cdbc8b68ac167fe47f7c107ee307e6c",
        "standard_raw_byte_count": 10_331,
        "standard_numstat_sha256": "54aae46c9f36d3959f980434db36aee85088ff8a2c09a7e6abde6d2a1c11cbf8",
        "standard_numstat_byte_count": 5_175,
        "standard_name_status_sha256": "dbcdea6367033d145b9e19e2b157004a6b34c662e754fa80916b55373cb64cd7",
        "standard_name_status_byte_count": 4_996,
        "nul_raw_sha256": "6186a3200dbc095dc92a93a53128c6c314ee9445a722a85d439eecc7f109c3be",
        "nul_raw_byte_count": 10_331,
        "nul_numstat_sha256": "ed68630f5627c70359d4651276eba4c174117ef292f4716328c383d1fa54b78b",
        "nul_numstat_byte_count": 5_175,
        "nul_name_status_sha256": "1c0b855bbf744b0b8378edecee0cefef257c1bb50d96a0a7bd4c2c1b6a490342",
        "nul_name_status_byte_count": 4_996,
    },
}

D1_CHECKPOINT = {
    "object_format": "sha1",
    "commit_oid": D1_COMMIT,
    "parent_oid": D1_PARENT,
    "unique_parent_fixed": True,
    "parent_is_implementation_checkpoint": True,
    "root_tree_oid": "0d8753b49ba98aeaacdeacfd7d5da3f1d393af75",
    "parent_root_tree_oid": D0_CHECKPOINT["root_tree_oid"],
    "ti_java_tree_oid": "f7fcff1a9e897b157ff09ea6aa247cd15a9d96f4",
    "parent_ti_java_tree_oid": D0_CHECKPOINT["ti_java_tree_oid"],
    "server_tree_oid": D0_CHECKPOINT["server_tree_oid"],
    "parent_server_tree_oid": D0_CHECKPOINT["server_tree_oid"],
    "server_src_main_tree_oid": D0_CHECKPOINT["server_src_main_tree_oid"],
    "parent_server_src_main_tree_oid": D0_CHECKPOINT["server_src_main_tree_oid"],
    "web_tree_oid": D0_CHECKPOINT["web_tree_oid"],
    "parent_web_tree_oid": D0_CHECKPOINT["web_tree_oid"],
    "miniprogram_tree_oid": D0_CHECKPOINT["miniprogram_tree_oid"],
    "parent_miniprogram_tree_oid": D0_CHECKPOINT["miniprogram_tree_oid"],
    "authored_at": "2026-07-23T17:47:54+08:00",
    "committed_at": "2026-07-23T17:47:54+08:00",
    "subject": "test(java): independently accept tag migration execution protocol",
    "changed_path_count": 2,
    "added_count": 2,
    "modified_count": 0,
    "deleted_count": 0,
    "non_ti_java_count": 0,
    "inserted_line_count": 1_893,
    "deleted_line_count": 0,
    "current_total_bytes": 75_685,
    "parent_total_bytes": 0,
    "net_byte_increase": 75_685,
    "added_total_bytes": 75_685,
    "modified_current_total_bytes": 0,
    "modified_parent_total_bytes": 0,
    "exact_two_added_path_delta": True,
    "diff": {
        "standard_raw_sha256": "d6c6f6132cfc52ed2e17932564c8755134616409ffb1e3949b2dde8922c32de7",
        "standard_raw_byte_count": 397,
        "standard_numstat_sha256": "cce0b9d2d0dee877e467d59d58f90815a0627ef65337c37bf43ab0bf51c72c00",
        "standard_numstat_byte_count": 212,
        "standard_name_status_sha256": "4213964d784d1167340ff5f564ce29b8d7b3efc3e0e9954ea2f412dd3af03b18",
        "standard_name_status_byte_count": 203,
        "nul_raw_sha256": "15d50c97fd6f74d1e6e13eabf00d4d3adf1680b377cbb9a14515b7fba411bf37",
        "nul_raw_byte_count": 397,
        "nul_numstat_sha256": "6b09db4c5155e6a499d906729322a21ca2804f10b56ecf2d22fabf92e2dd441a",
        "nul_numstat_byte_count": 212,
        "nul_name_status_sha256": "c21c2e6bd5127068fc3f425e73d418da69307ded9bc53fa4e09b79a99218eda6",
        "nul_name_status_byte_count": 203,
    },
}


def _checkpoint_document(metadata: dict[str, Any], changes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = deepcopy(metadata)
    result["artifacts"] = deepcopy(changes)
    return result


def _authority_anchor(predecessor: dict[str, Any]) -> dict[str, Any]:
    fixed = predecessor["source_authority"]["fixed_non_control_sources"]
    transitions = predecessor["historical_source_successors"]["overrides"]
    return {
        "implementation_control_sources": list(D0_CONTROL_SOURCES),
        "implementation_control_source_count": 7,
        "implementation_fixed_non_control_sources": list(fixed),
        "implementation_fixed_non_control_source_count": 48,
        "implementation_transition_sources": list(transitions),
        "implementation_transition_source_count": 37,
        "independent_acceptance_control_sources": list(D1_CONTROL_SOURCES),
        "independent_acceptance_control_source_count": 2,
        "implementation_control_path_manifest_sha256": sha256_json(D0_CONTROL_SOURCES),
        "implementation_fixed_manifest_sha256": sha256_json(fixed),
        "implementation_transition_manifest_sha256": sha256_json(transitions),
        "implementation_artifact_manifest_sha256": sha256_json(D0_CHANGES),
        "independent_acceptance_artifact_manifest_sha256": sha256_json(D1_CHANGES),
        "exact_disjoint_d0_7_plus_48_partition": True,
        "all_37_transitions_are_exact_modified_commit_blobs": True,
        "d0_and_d1_control_sources_external_git_anchor_complete": True,
        "ordinary_build_and_load_are_gitless": True,
        "explicit_fixed_commit_git_replay_available": True,
        "dynamic_source_discovery_forbidden": True,
        "live_head_or_ref_authority_forbidden": True,
    }


def _production_boundary(predecessor: dict[str, Any]) -> dict[str, Any]:
    worm = predecessor["worm_successor"]
    runtime = predecessor["production_runtime_successor"]
    return {
        "worm": deepcopy(worm),
        "accepted_runtime_file_count": runtime["accepted_file_count"],
        "current_runtime_file_count": runtime["current_file_count"],
        "accepted_runtime_manifest_sha256": runtime["accepted_manifest_sha256"],
        "current_runtime_manifest_sha256": runtime["current_manifest_sha256"],
        "runtime_added_files": deepcopy(runtime["added_files"]),
        "runtime_changed_files": deepcopy(runtime["changed_files"]),
        "d1_server_tree_unchanged_from_d0": True,
        "d1_server_src_main_tree_unchanged_from_d0": True,
        "d1_web_tree_unchanged_from_d0": True,
        "d1_miniprogram_tree_unchanged_from_d0": True,
        "production_schema_or_index_added": False,
        "production_connection_or_credentials_used": False,
        "production_data_read_or_mutated": False,
        "production_operator_executed": False,
        "user_compose_or_production_docker_mutated": False,
    }


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("execution-protocol anchor live/ref Git authority is forbidden")
    environment = os.environ.copy()
    for key in tuple(environment):
        if (key in {
                "GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE",
                "GIT_CONFIG_COUNT",
        } or key.startswith("GIT_CONFIG_KEY_")
                or key.startswith("GIT_CONFIG_VALUE_")):
            environment.pop(key, None)
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "PAGER": "cat",
        "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            ("git", "--no-optional-locks", *arguments),
            cwd=repository_root,
            env=environment,
            check=True,
            timeout=30,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AssertionError("execution-protocol anchor fixed Git replay failed") from error
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def _expected_raw(changes: dict[str, dict[str, Any]]) -> bytes:
    return "".join(
        f":{item['previous_mode']} {item['mode']} "
        f"{item['previous_git_blob_oid']} {item['git_blob_oid']} "
        f"{item['change_type']}\t{item['repository_path']}\n"
        for item in changes.values()
    ).encode("utf-8")


def _expected_numstat(changes: dict[str, dict[str, Any]]) -> bytes:
    return "".join(
        f"{item['inserted_line_count']}\t{item['deleted_line_count']}\t"
        f"{item['repository_path']}\n"
        for item in changes.values()
    ).encode("utf-8")


def _expected_name_status(changes: dict[str, dict[str, Any]]) -> bytes:
    return "".join(
        f"{item['change_type']}\t{item['repository_path']}\n"
        for item in changes.values()
    ).encode("utf-8")


def _assert_diff_identity(
    label: str,
    actual: bytes,
    expected: bytes | None,
    expected_sha256: str,
    expected_bytes: int,
) -> None:
    if (len(actual) != expected_bytes
            or sha256_bytes(actual) != expected_sha256
            or (expected is not None and actual != expected)):
        raise AssertionError(f"execution-protocol {label} fixed Git diff drifted")


def _validate_git_checkpoint(
    repository_root: Path,
    metadata: dict[str, Any],
    changes: dict[str, dict[str, Any]],
) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("execution-protocol anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != "sha1":
        raise AssertionError("execution-protocol anchor Git object format drifted")
    commit = metadata["commit_oid"]
    parent = metadata["parent_oid"]
    if (_git_text(root, "cat-file", "-t", commit) != "commit"
            or _git_text(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
            != commit):
        raise AssertionError("execution-protocol anchor fixed commit object drifted")
    facts = _git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", commit
    ).splitlines()
    if facts != [
        metadata["root_tree_oid"], parent, metadata["authored_at"],
        metadata["committed_at"], metadata["subject"],
    ]:
        raise AssertionError("execution-protocol anchor commit identity/parent drifted")
    if _git_text(root, "show", "-s", "--format=%T", parent) \
            != metadata["parent_root_tree_oid"]:
        raise AssertionError("execution-protocol anchor parent root tree drifted")
    tree_paths = {
        "ti_java_tree_oid": "Ti-Java",
        "server_tree_oid": "Ti-Java/server",
        "server_src_main_tree_oid": "Ti-Java/server/src/main",
        "web_tree_oid": "Ti-Java/web",
        "miniprogram_tree_oid": "miniprogram-1",
    }
    for key, relative in tree_paths.items():
        if _git_text(root, "rev-parse", f"{commit}:{relative}") != metadata[key]:
            raise AssertionError(f"execution-protocol anchor current tree drifted: {relative}")
        parent_key = f"parent_{key}"
        if _git_text(root, "rev-parse", f"{parent}:{relative}") \
                != metadata[parent_key]:
            raise AssertionError(f"execution-protocol anchor parent tree drifted: {relative}")
    diff = metadata["diff"]
    raw = _run_git(
        root, "diff-tree", "--no-commit-id", "--raw", "--abbrev=40", "-r", commit
    )
    numstat = _run_git(
        root, "diff-tree", "--no-commit-id", "--numstat", "-r", commit
    )
    name_status = _run_git(
        root, "diff-tree", "--no-commit-id", "--name-status", "-r", commit
    )
    _assert_diff_identity(
        "standard raw", raw, _expected_raw(changes),
        diff["standard_raw_sha256"], diff["standard_raw_byte_count"],
    )
    _assert_diff_identity(
        "standard numstat", numstat, _expected_numstat(changes),
        diff["standard_numstat_sha256"], diff["standard_numstat_byte_count"],
    )
    _assert_diff_identity(
        "standard name-status", name_status, _expected_name_status(changes),
        diff["standard_name_status_sha256"],
        diff["standard_name_status_byte_count"],
    )
    raw_nul = _run_git(
        root, "diff-tree", "--no-commit-id", "--raw", "--abbrev=40", "-r", "-z", commit
    )
    numstat_nul = _run_git(
        root, "diff-tree", "--no-commit-id", "--numstat", "-r", "-z", commit
    )
    name_status_nul = _run_git(
        root, "diff-tree", "--no-commit-id", "--name-status", "-r", "-z", commit
    )
    _assert_diff_identity(
        "NUL raw", raw_nul, None,
        diff["nul_raw_sha256"], diff["nul_raw_byte_count"],
    )
    _assert_diff_identity(
        "NUL numstat", numstat_nul, None,
        diff["nul_numstat_sha256"], diff["nul_numstat_byte_count"],
    )
    _assert_diff_identity(
        "NUL name-status", name_status_nul, None,
        diff["nul_name_status_sha256"], diff["nul_name_status_byte_count"],
    )
    current_total = previous_total = added_total = 0
    modified_current = modified_parent = inserted = deleted = 0
    for path, item in changes.items():
        repository_path = item["repository_path"]
        if not repository_path.startswith("Ti-Java/"):
            raise AssertionError("execution-protocol anchor non-Ti-Java path")
        if _git_text(root, "rev-parse", f"{commit}:{repository_path}") \
                != item["git_blob_oid"]:
            raise AssertionError(f"execution-protocol anchor current blob drifted: {path}")
        current = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (len(current) != item["byte_count"]
                or sha256_bytes(current) != item["sha256"]):
            raise AssertionError(f"execution-protocol anchor current bytes drifted: {path}")
        current_total += len(current)
        inserted += item["inserted_line_count"]
        deleted += item["deleted_line_count"]
        if item["change_type"] == "A":
            if _run_git(root, "ls-tree", parent, "--", repository_path):
                raise AssertionError(f"execution-protocol anchor added path existed: {path}")
            added_total += len(current)
        elif item["change_type"] == "M":
            if _git_text(root, "rev-parse", f"{parent}:{repository_path}") \
                    != item["previous_git_blob_oid"]:
                raise AssertionError(f"execution-protocol anchor parent blob drifted: {path}")
            previous = _run_git(
                root, "cat-file", "blob", item["previous_git_blob_oid"]
            )
            if (len(previous) != item["previous_byte_count"]
                    or sha256_bytes(previous) != item["previous_sha256"]):
                raise AssertionError(f"execution-protocol anchor parent bytes drifted: {path}")
            previous_total += len(previous)
            modified_current += len(current)
            modified_parent += len(previous)
        else:
            raise AssertionError("execution-protocol anchor unsupported change type")
    if (len(changes) != metadata["changed_path_count"]
            or sum(item["change_type"] == "A" for item in changes.values())
            != metadata["added_count"]
            or sum(item["change_type"] == "M" for item in changes.values())
            != metadata["modified_count"]
            or current_total != metadata["current_total_bytes"]
            or previous_total != metadata["parent_total_bytes"]
            or current_total - previous_total != metadata["net_byte_increase"]
            or added_total != metadata["added_total_bytes"]
            or modified_current != metadata["modified_current_total_bytes"]
            or modified_parent != metadata["modified_parent_total_bytes"]
            or inserted != metadata["inserted_line_count"]
            or deleted != metadata["deleted_line_count"]):
        raise AssertionError("execution-protocol anchor checkpoint aggregates drifted")


def validate_fixed_git_checkpoints(repository_root: Path) -> None:
    _validate_git_checkpoint(repository_root, D0_CHECKPOINT, D0_CHANGES)
    _validate_git_checkpoint(repository_root, D1_CHECKPOINT, D1_CHANGES)
    if (D1_CHECKPOINT["parent_oid"] != D0_CHECKPOINT["commit_oid"]
            or tuple(D1_CHANGES) != D1_CONTROL_SOURCES
            or D1_CHANGES[EVIDENCE_RELATIVE]["mode"] != "100644"
            or D1_CHANGES[RUNNER_RELATIVE]["mode"] != "100755"):
        raise AssertionError("execution-protocol D0/D1 fixed checkpoint chain drifted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    document = build_contract(arguments.ti_java_root, repository_root=arguments.repository_root)
    payload = serialized_contract(document)
    if arguments.check:
        if arguments.output.read_bytes() != payload:
            raise AssertionError("execution-protocol post-push anchor contract drifted")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_bytes(payload)
    print(f"execution-protocol post-push anchor passed: {sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
