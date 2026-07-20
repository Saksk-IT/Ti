#!/usr/bin/env python3
"""Build the fixed Phase 4C operator-core C0+C1 post-push anchor."""

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
    "docs/refactor/phase4c/personal-bank-tag-migration-operator-core-"
    "post-push-anchor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
CONTRACT_ID = (
    "ti.phase4c.personal-bank-tag-migration-operator-core-"
    "post-push-anchor-contract"
)
CAPTURED_AT = "2026-07-20T18:26:27+08:00"
STATUS = (
    "operator_core_and_independent_acceptance_checkpoints_externally_"
    "anchored_production_schema_freeze_backup_apply_and_cutover_unauthorized"
)
SCOPE = (
    "phase4c-personal-bank-tag-migration-operator-core-post-push-"
    "external-anchor"
)

OPERATOR_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-operator-core-contract.json"
)
OPERATOR_CONTRACT_ID = "ti.phase4c.personal-bank-tag-migration-operator-core-contract"
OPERATOR_CONTRACT_CAPTURED_AT = "2026-07-19T15:30:00+08:00"
OPERATOR_CONTRACT_SHA256 = (
    "2124d1b042f2df201ad3d8ca87fd19fa121b8d47cbaf51a60eb5271fe55b7fe8"
)
OPERATOR_CONTRACT_PAYLOAD_SHA256 = (
    "28f0fa1a5ec1c2e795c60d472b47d0ccb16d1b838a30dd0e7ac69fe738f53778"
)
OPERATOR_CONTRACT_BYTE_COUNT = 50_467

EVIDENCE_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-operator-core-"
    "independent-acceptance-evidence.json"
)
EVIDENCE_ID = (
    "ti.phase4c.personal-bank-tag-migration-operator-core-"
    "independent-acceptance-evidence"
)
EVIDENCE_SHA256 = (
    "4262361fbcf55452bae3d8a50340c4fc2f103ee07b562fce8879500e38691003"
)
EVIDENCE_BYTE_COUNT = 8_894
RUNNER_RELATIVE = "tools/run_phase4c_tag_migration_operator_core_independent_acceptance.sh"
RUNNER_SHA256 = "bcfa8b8a386579e7fddd212712fa045bf1d30a0bf7d6c7f8df5860b933de2774"
RUNNER_BYTE_COUNT = 65_880
RUNNER_GIT_MODE = "100755"

C0_COMMIT = "a70c365959e123950d30bff05adb4fabbb72d640"
C0_PARENT = "bbeb08efcccb0b9974dfefa2044aab43e0675f6f"
C1_COMMIT = "4ec9966f836378a33058b574fd1812d4d19cac10"
C1_PARENT = C0_COMMIT

C0_CONTROL_SOURCES = (
    OPERATOR_CONTRACT_RELATIVE,
    "docs/refactor/phase4c/personal-bank-tag-migration-operator-core.md",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java",
    "tools/build_phase4c_tag_migration_operator_core_contract.py",
    "tools/phase4c_tag_migration_operator_core_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_operator_core_contract.py",
)
C1_CONTROL_SOURCES = (EVIDENCE_RELATIVE, RUNNER_RELATIVE)
CURRENT_CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorSuccessorAcceptance.java",
    "tools/build_phase4c_tag_migration_operator_core_post_push_anchor_contract.py",
    "tools/phase4c_tag_migration_operator_core_post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_operator_core_post_push_anchor_contract.py",
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
    allowed = {OPERATOR_CONTRACT_RELATIVE, EVIDENCE_RELATIVE, RUNNER_RELATIVE, OUTPUT_RELATIVE}
    value = Path(relative)
    if value.is_absolute() or relative not in allowed:
        raise AssertionError("operator-core anchor unknown or absolute source")
    base = root.resolve(strict=True)
    candidate = base / value
    cursor = base
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"operator-core anchor source is a symlink: {relative}")
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AssertionError("operator-core anchor fixed source missing") from error
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise AssertionError("operator-core anchor source escaped or is not regular")
    return resolved


def _read_fixed_json(root: Path, relative: str, sha256: str, byte_count: int) -> dict[str, Any]:
    payload = _fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(f"operator-core anchor fixed bytes drifted: {relative}")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("operator-core anchor fixed JSON must be an object")
    return document


def _validate_operator_contract(document: dict[str, Any]) -> None:
    if (document.get("contract_id") != OPERATOR_CONTRACT_ID
            or document.get("captured_at") != OPERATOR_CONTRACT_CAPTURED_AT
            or document.get("document_payload_sha256")
            != OPERATOR_CONTRACT_PAYLOAD_SHA256
            or document_payload_sha256(document)
            != OPERATOR_CONTRACT_PAYLOAD_SHA256
            or document.get("route_state") != ROUTE_STATE):
        raise AssertionError("operator-core anchor predecessor identity drifted")
    authority = document.get("source_authority", {})
    controls = authority.get("control_sources", [])
    fixed = authority.get("fixed_non_control_sources", {})
    transitions = document.get("historical_source_successors", {}).get(
        "overrides", {}
    )
    control_paths = set(C0_CONTROL_SOURCES)
    fixed_paths = set(C0_CHANGES) - control_paths
    transition_paths = {
        path for path, item in C0_CHANGES.items()
        if item["change_type"] == "M"
    }
    if (tuple(controls) != C0_CONTROL_SOURCES
            or authority.get("control_source_count") != 7
            or authority.get("fixed_non_control_source_count") != 49
            or set(fixed) != fixed_paths
            or set(transitions) != transition_paths
            or control_paths & fixed_paths
            or control_paths | fixed_paths != set(C0_CHANGES)
            or sha256_json(controls)
            != "f9098c90c9ea2d75f3b5f2d08bb84ac075015c8f1b30160dd475d0d6d6e96f22"
            or sha256_json(fixed)
            != "a0b3742d34ff42cffe2b903644876bb2d6e4db55ffba9639125fa89376d0b376"
            or sha256_json(transitions)
            != "cd7f19edd049c676de69cd2572a45c6c6235dfc7a6ac1a57248c7e508dae5487"):
        raise AssertionError("operator-core C0 authority partition drifted")
    if (authority.get("control_sources_excluded_from_self_authority") is not True
            or authority.get("current_control_sources_external_git_anchor_complete")
            is not False
            or authority.get("dynamic_source_discovery") is not False
            or authority.get("ordinary_build_and_load_are_gitless") is not True
            or authority.get("live_head_main_or_origin_authority") is not False):
        raise AssertionError("operator-core C0 authority trust boundary drifted")
    for path, descriptor in fixed.items():
        item = C0_CHANGES[path]
        if (descriptor.get("source") != path
                or descriptor.get("sha256") != item["sha256"]
                or descriptor.get("byte_count") != item["byte_count"]):
            raise AssertionError(f"operator-core C0 fixed source drifted: {path}")
    for path, descriptor in transitions.items():
        item = C0_CHANGES[path]
        if (descriptor.get("source") != path
                or descriptor.get("accepted_sha256") != item["previous_sha256"]
                or descriptor.get("accepted_byte_count")
                != item["previous_byte_count"]
                or descriptor.get("successor_sha256") != item["sha256"]
                or descriptor.get("successor_byte_count") != item["byte_count"]):
            raise AssertionError(f"operator-core C0 transition drifted: {path}")
    controls_current = sum(C0_CHANGES[path]["byte_count"] for path in control_paths)
    fixed_current = sum(C0_CHANGES[path]["byte_count"] for path in fixed_paths)
    fixed_parent = sum(C0_CHANGES[path]["previous_byte_count"] for path in fixed_paths)
    transition_current = sum(C0_CHANGES[path]["byte_count"] for path in transition_paths)
    transition_parent = sum(
        C0_CHANGES[path]["previous_byte_count"] for path in transition_paths
    )
    if (sum(C0_CHANGES[path]["change_type"] == "A" for path in control_paths) != 7
            or sum(C0_CHANGES[path]["change_type"] == "A" for path in fixed_paths)
            != 15
            or sum(C0_CHANGES[path]["change_type"] == "M" for path in fixed_paths)
            != 34
            or controls_current != 267_725
            or fixed_current != 2_161_020
            or fixed_parent != 1_658_884
            or transition_current != 1_696_141
            or transition_parent != 1_658_884):
        raise AssertionError("operator-core C0 authority byte aggregates drifted")
    authorization = document.get("authorization", {})
    for field in (
        "migration_global_preflight_evidence_closed",
        "migration_durable_ledger_freeze_design_evidence_closed",
        "operator_core_evidence_closed",
        "bounded_40001_40P01_retry_implemented",
        "operator_migration_implementation",
    ):
        if authorization.get(field) is not True:
            raise AssertionError(f"operator-core C0 true gate drifted: {field}")
    for field in (
        "source_successor_external_git_anchor_complete",
        "semantic_successor_external_git_anchor_complete",
        "bootstrap_control_sources_external_git_anchor_complete",
        "current_node_control_sources_external_git_anchor_complete",
        *PRODUCTION_FALSE_FIELDS,
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"operator-core C0 closed gate drifted: {field}")
    node_b = document.get("node_b_git_authority", {})
    external = node_b.get("external_anchor_checkpoint", {})
    if (external.get("commit_oid")
            != "bbeb08efcccb0b9974dfefa2044aab43e0675f6f"
            or external.get("parent_oid")
            != "ea894b3a02787a91b688d7295cace37139f7f486"
            or external.get("changed_path_count") != 6
            or node_b.get("external_anchor_artifact_count") != 6
            or node_b.get("ordinary_build_and_load_require_git") is not False
            or node_b.get("live_head_main_or_origin_authority") is not False):
        raise AssertionError("operator-core transitive Node B authority drifted")
    worm = document.get("worm_successor", {})
    runtime = document.get("production_runtime_successor", {})
    if (worm.get("current_report", {}).get("sha256")
            != "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f"
            or worm.get("current_report", {}).get("byte_count") != 1_442
            or worm.get("current_chain_node_count") != 8
            or worm.get("current_build_context_sha256")
            != "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc"
            or worm.get("dockerfile_sha256")
            != "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
            or runtime.get("accepted_file_count") != 300
            or runtime.get("current_file_count") != 307
            or len(runtime.get("added_files", {})) != 7
            or len(runtime.get("changed_files", {})) != 1):
        raise AssertionError("operator-core C0 WORM/runtime boundary drifted")


def _validate_independent_evidence(document: dict[str, Any]) -> None:
    runner = document.get("independent_acceptance_runner", {})
    authority = document.get("fixed_c0_authority", {})
    verification = document.get("verification", {})
    if (document.get("contract_id") != EVIDENCE_ID
            or document.get("schema_version") != 1
            or document.get("status") != "passed"
            or document.get("scope")
            != "phase4c-learning-tag-migration-operator-core-fixed-c0-independent-copy"
            or document.get("route_state") != ROUTE_STATE
            or authority.get("commit_oid") != C0_COMMIT
            or authority.get("parent_oid") != C0_PARENT
            or authority.get("root_tree_oid") != C0_CHECKPOINT["root_tree_oid"]
            or authority.get("ti_java_tree_oid") != C0_CHECKPOINT["ti_java_tree_oid"]
            or authority.get("diff", {}).get("changed_path_count") != 56
            or authority.get("diff", {}).get("added_path_count") != 22
            or authority.get("diff", {}).get("modified_path_count") != 34):
        raise AssertionError("operator-core independent evidence C0 authority drifted")
    raw = runner.get("raw_report", {})
    if (runner.get("path") != RUNNER_RELATIVE
            or runner.get("sha256") != RUNNER_SHA256
            or runner.get("byte_count") != RUNNER_BYTE_COUNT
            or runner.get("git_mode") != RUNNER_GIT_MODE
            or raw.get("sha256")
            != "45e8a3d0eaed833c6730aca1d2b05fccf5f145e51fb9e753aad283c652486d9d"
            or raw.get("byte_count") != 8_762
            or raw.get("tracked") is not False
            or raw.get("embedded") is not False
            or raw.get("required_for_gitless_successor_acceptance") is not False):
        raise AssertionError("operator-core independent runner/report drifted")
    maven = verification.get("maven_full", {})
    focused = verification.get("focused_node_c", {})
    source_discovery = verification.get("source_discovery", {})
    if (verification.get("timezone") != "UTC"
            or any(verification.get(field) is not True for field in (
                "phase1_passed", "phase2_static_passed", "phase3_static_passed",
                "phase3_topology_static_passed", "topology_data_plane_passed",
            ))
            or verification.get("miniprogram")
            != {"tests": 36, "passed": 36, "failed": 0}
            or maven.get("surefire")
            != {"tests": 860, "failures": 0, "errors": 0, "skipped": 0}
            or maven.get("failsafe")
            != {"tests": 176, "failures": 0, "errors": 0, "skipped": 0}
            or focused.get("unit", {}).get("tests") != 83
            or focused.get("operator_integration", {}).get("tests") != 3
            or focused.get("retry_integration", {}).get("tests") != 2
            or source_discovery.get("executed_inside_independent_copy") is not False
            or source_discovery.get("claimed_independent_copy_test_count") != 0):
        raise AssertionError("operator-core independent verification drifted")
    for suite in focused.values():
        if any(suite.get(field) != 0 for field in ("failures", "errors", "skipped")):
            raise AssertionError("operator-core focused verification is not green")
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
        raise AssertionError("operator-core independent isolation/cleanup drifted")
    if any(document.get("production_boundary", {}).get(field) is not False
           for field in document.get("production_boundary", {})):
        raise AssertionError("operator-core independent production boundary drifted")
    closure = document.get("closure", {})
    if (closure.get("fixed_c0_independent_copy_acceptance_closed") is not True
            or closure.get("proves_only_commit") != C0_COMMIT
            or closure.get("proves_c1_evidence_commit") is not False
            or closure.get("proves_c2_anchor_commit") is not False
            or closure.get("operator_core_control_sources_external_git_anchor_complete")
            is not False
            or closure.get("self_hash_embedded") is not False):
        raise AssertionError("operator-core independent closure boundary drifted")


def _read_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _read_fixed_json(
        root, OPERATOR_CONTRACT_RELATIVE,
        OPERATOR_CONTRACT_SHA256, OPERATOR_CONTRACT_BYTE_COUNT,
    )
    _validate_operator_contract(contract)
    evidence = _read_fixed_json(root, EVIDENCE_RELATIVE, EVIDENCE_SHA256, EVIDENCE_BYTE_COUNT)
    runner = _fixed_regular_file(root, RUNNER_RELATIVE)
    runner_bytes = runner.read_bytes()
    runner_mode = f"{stat.S_IFREG | stat.S_IMODE(runner.stat().st_mode):06o}"
    if (len(runner_bytes) != RUNNER_BYTE_COUNT or sha256_bytes(runner_bytes) != RUNNER_SHA256
            or runner_mode != RUNNER_GIT_MODE):
        raise AssertionError("operator-core independent runner identity drifted")
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
        "bounded_40001_40P01_retry_implemented": True,
        "operator_migration_implementation": True,
        "operator_core_control_sources_external_git_anchor_complete": True,
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
        "operator_core_contract": {
            "source": OPERATOR_CONTRACT_RELATIVE,
            "contract_id": OPERATOR_CONTRACT_ID,
            "sha256": OPERATOR_CONTRACT_SHA256,
            "byte_count": OPERATOR_CONTRACT_BYTE_COUNT,
            "document_payload_sha256": OPERATOR_CONTRACT_PAYLOAD_SHA256,
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
        "implementation_checkpoint": _checkpoint_document(C0_CHECKPOINT, C0_CHANGES),
        "independent_acceptance_checkpoint": _checkpoint_document(C1_CHECKPOINT, C1_CHANGES),
        "operator_core_authority_anchor": _authority_anchor(predecessor),
        "transitive_node_b_anchor": {
            "predecessor": deepcopy(predecessor["predecessor"]),
            "git_authority": deepcopy(predecessor["node_b_git_authority"]),
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
            "c2_commit_or_tree_identity_embedded": False,
        },
        "acceptance": {
            "implementation_checkpoint_changed_path_count": 56,
            "implementation_checkpoint_added_count": 22,
            "implementation_checkpoint_modified_count": 34,
            "independent_acceptance_checkpoint_changed_path_count": 2,
            "independent_acceptance_checkpoint_added_count": 2,
            "implementation_control_source_count": 7,
            "implementation_fixed_non_control_source_count": 49,
            "implementation_transition_count": 34,
            "independent_acceptance_control_source_count": 2,
            "current_control_source_count": 6,
            "anchor_closes_no_functional_gate": True,
            "c2_self_anchor_complete": False,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "next_gate": "Node D whole-execution protocol remains separately required",
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


# The complete fixed checkpoints and validators are appended below.  Keeping the
# construction API above stable lets the Python and Java consumers bind the final schema.
_C0_ROWS = r"""
docs/refactor/05-progress.md|M|100644|100644|8024a5d49022f1aa135cd7e4a984f760f666cf2f|436c57475a6b5a6b47dcdec22d96d173f0600ea4|8478e44622fc666fdb9a377b15ced624e34d104d1fcbb9b36a4913cfb3ddedf0|107912|71fc8bf98bc4fb50645df473ee79b2bc33856ca928f49da7aecc96a7d1040f9d|109838|7|5
docs/refactor/phase4c/README.md|M|100644|100644|15ea8a348a9d6cf54a46b9cad953908da3296c71|338c0d80d8d48f062ee66bcb59c3b6bd2641ca47|4d75ba666d7d45d620a4fba4574e4c2640b754c5a6beadbdbfdee5498aa3cc48|26858|f061ac5e2b240e3b8c367f9db817c84346a309e9872cfbdeeafe8d3ff8689230|29918|38|0
docs/refactor/phase4c/personal-bank-tag-migration-operator-core-contract.json|A|000000|100644|0000000000000000000000000000000000000000|848866b7eb6ec58f36cf0468ee025a6516ff251f|-|0|2124d1b042f2df201ad3d8ca87fd19fa121b8d47cbaf51a60eb5271fe55b7fe8|50467|833|0
docs/refactor/phase4c/personal-bank-tag-migration-operator-core-worm-evidence.json|A|000000|100644|0000000000000000000000000000000000000000|f0ba737bdac1e53ee3f8a2601f159653d89fa60a|-|0|db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f|1442|42|0
docs/refactor/phase4c/personal-bank-tag-migration-operator-core.md|A|000000|100644|0000000000000000000000000000000000000000|5549609426f5408c6782b318f6c5e975aedb1c65|-|0|a27a57d55011a86b33966426cd8d046cfdd032f77f7bb54c045a429fbdf6cc02|8162|136|0
infra/phase2/README.md|M|100644|100644|83919691c5e8b1e16aaa7a1522d4ba5ac74ce70f|9f0c925ca75b12f24775a262ce4e99d6cc3804e5|a0c467bfc8aa0f0b64b4d520f9cda60ff081a340f016647e1da934c73b7b99d5|7474|d5c8647397016f93c8ea2b5e83b41818ea00498fd7e699cc1119930f1995e21b|8018|2|2
infra/phase2/verify-static.sh|M|100755|100755|adf88dd68d10de4d55165a43384fec0589a94f2e|1a27ee8bb00128a46d98de35684edc9f5e6dd5e5|893ca920d0ed1bd62e16509893fa30bbfc72b88368d66d96c2ebc5c2fbae38dc|16417|2a1a5a5453a1090f6132971081d4ac2448803023acb50d474ced491bafe8efc3|17491|18|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/BoundedSqlRetry.java|A|000000|100644|0000000000000000000000000000000000000000|b70977e2c5d25fd4ba828e81889d3d9751038d75|-|0|4f3a37fc45d5fbeab21e4092de79d2e01dbb4c3db516d69a7e39ec6e486de2d6|9021|263|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/JdbcTagMigrationStore.java|A|000000|100644|0000000000000000000000000000000000000000|48aaddbe3a8134c2dacecc4ba72c9239d3e62fee|-|0|8adf102211041e33243f6e76bab1eda9100cc3e44ee54d9a5468a6c7cdb4c242|68333|1500|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagGlobalPreflight.java|M|100644|100644|9b4b6c87bbdae94d52e56b821654a5e044f74e71|3bd71a30445051b2e7f43c637a9652c618f76bad|cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76|35830|c6dd412fcfa23f8e59ccf6e2a0d7c741e1cc684015b73e92cfb77cab3300e746|36070|15|11
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationOperatorCore.java|A|000000|100644|0000000000000000000000000000000000000000|a05206aa01cbd45ab3ee0a3213f3042c96acc152|-|0|2a70c9e9cc7e5acdb1aa5059114fdb34e910a9f4c7d124dc17f62ad06360987b|78742|1735|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationCommand.java|A|000000|100644|0000000000000000000000000000000000000000|9034c47b47b47623d5841b3e901f4ea98d930cf1|-|0|4d1d2a059a6ca2874cd8a787dee860482f035bad9cdb8ea62451b80fd41445a0|4822|129|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationDigests.java|A|000000|100644|0000000000000000000000000000000000000000|874ce955c22b5a74b7a397ca57519d1a2d3094d2|-|0|92520a2abb405024fcfb760c0d710b2bf50e0f6ad4c22d2dd2b7f25547f8a7ec|12330|297|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationResult.java|A|000000|100644|0000000000000000000000000000000000000000|394c0a499e6262fc01d037e868fbeeaa342e7040|-|0|eb9c6ccdae328a9bbff331e05ca324af2bce1e008d8ab6fddad442a9af7cbd81|4785|139|0
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationSchemaVerifier.java|A|000000|100644|0000000000000000000000000000000000000000|a5c640f624d742d728ea73af6c5ce734fe1ca717|-|0|7b28cd9ac19d328166f124052c2d0d8ba57ea7bbc1257e8aad399cb2c1d2750f|54778|1101|0
server/src/test/java/io/saksk/ti/architecture/ModuleContractParityTest.java|M|100644|100644|cf799016429c12a5d1f4f06bfb5358605d776205|a803344c3786a7780ec4bbee07aec33b9c486ade|984863bff3762adc8e375f0073559bb1e0e1d0ed16c368147087fdc3ca4efcd1|182577|9f32b0d204ea8d7d78b3ca5e0112cb4bd70bc31ce98cf16c032afd7545d67c61|182760|17|11
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java|M|100644|100644|ad349777c43cbe0f07c15d9bf3e1621139557c9d|06f3d781bd8a62e859b196c2d750cd8dcc37943f|10d19deb68495db02f9113dd58bdf7bbf7dfa67a8885c49f7dd88685f574ff78|91381|9f929532d8c31f96f4e3e5cd24ee199220c82ad2aac46f5944ee0d54cd22dbb6|91381|1|1
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java|M|100644|100644|5e99fef2ea9d2b0807f8b1d003c7851893fefe26|45c1e9b99c372a338243eb875b2e113e7863d259|ec7c98b04a26f25940fd5b9ec4120ebd478aa41798d4040f1cce97336898d6d2|79735|cb4cabfce2cded7cde291b54d2c2dd98cc397887d24141e5164250a8811fb369|79867|3|0
server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java|M|100644|100644|ede9ab2803ef8b8b98c8e9fbc9b2c96de426856f|48f23b74a78b3c0ff474c817931eb344ae7210e0|faff2f55f48cdaa8bab92530347cda47a0f3ba4dc4227c86242afb94d78aebc0|17295|137f3a9911d886610300aecc95a13f05d5621d18c19acf491194f1b8b741efe3|17439|11|8
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java|M|100644|100644|33e9a10a4450201ef1df9975854004084832001b|69af67392719d35c19decf063ed6e0b7c0a920cc|15dd2e02d5230970358d1761a8298cf44b837c7beda7459d4c4a69173c42f472|38080|bdb3ee1169dfe164016a2afc6a46e6e3fff7abe9b8602988ab9d0c0ecff86158|43784|106|11
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java|M|100644|100644|3890b307df0391755d2cb597e85c5d87f86cec99|0f830da46360e9c6e5a27b3b5e8964994949bd48|4a7a9ee5338b8a2dc3b57fd660b3ca9dc30b81e0fcb68d06437bd0f53d3a58b0|94373|e5471121ea2fc52f9e36712b222578e24323d5785dddf27b27a86799867fc99f|102527|177|23
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java|A|000000|100644|0000000000000000000000000000000000000000|0db00609bf1d1de1c9c720c6ecd2223c74428885|-|0|f7dad6c7d51769669fda0cb2c26a7c3991ad3bfae27178c9c8a470f6addff361|27467|560|0
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java|A|000000|100644|0000000000000000000000000000000000000000|d13d34ef8fb5ad97b333c0581bd7ed2288a81c06|-|0|83840dc07301be40828df8bd46f214bc2d50342bde6f8fb8412eca1ae3a7092c|83287|1558|0
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java|M|100644|100644|824ef36d39fe097f7f238ddfb1e9261316939536|810ac931232c5f5ec078cb5d59c94cce5b344a7a|e5ccdf547d1c11edaf58298a2759241c64731c048bc1bef67f5be046237c01aa|51024|bd83bffe8851e2368f3d9280d213b7adac1b4073dbe2296bd1d6e1c6183a454e|51156|3|0
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java|M|100644|100644|56241815979f836bba81bfc30482a5b835819895|535abcb351e1f523f2b7e350c06a63163e98642c|e61b445cbedddd5b71efe7dda22811128414b58089bf1525aaa4017485f6675d|11762|ea9affd42829d4560c2b974e8d189bd6feac340112732cf15b89d797f7b4f7af|11762|2|2
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/BoundedSqlRetryTest.java|A|000000|100644|0000000000000000000000000000000000000000|17b414fd34fc4a8eedee237258c6369bce7e8d0a|-|0|8e0e5f522b76e3569ff8bf1ef59949cc0830a72e17a7d62f85af465fd409a2b8|20398|479|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagGlobalPreflightTest.java|M|100644|100644|b562a4133cc055d57d7333a1988075031d7b81f9|000ef6d6bdd6a17818ff6efa36f64fb6682731c9|8fc30419dee8be99b8081f873d38921fdedb2beea42a7c1b4c8e2241e844ce3f|34570|ff4ff3dee678874b5acb0d9d2d380aee01fbcc5454c82746c1e0564113c40aaf|34622|2|1
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationOperatorCoreStaticTest.java|A|000000|100644|0000000000000000000000000000000000000000|82684de996c8e0de2496b2abe6b41c6b98ac001a|-|0|d828e25633e5029d10a781f171a1eb719ddc565954928ed77f6375f20b89e3a3|17734|381|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/Phase4cBoundedSqlRetryPostgresIT.java|A|000000|100644|0000000000000000000000000000000000000000|a6f806495de52a64fc102eb807dd6b0d77213202|-|0|105b8cd83b4c3beb043c3d98cda0da160c4f496919846ae9c7ffdf8b32f00263|19658|473|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/Phase4cLegacyPersonalBankTagOperatorCoreIT.java|A|000000|100644|0000000000000000000000000000000000000000|a976075af5867f5361a5b2d02594727e2b1bbb3f|-|0|891bbac391e21454ad309ac568bf2f3cc5f5fa82c0ea3da9936005308b70197c|96139|2124|0
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationValueTypesTest.java|A|000000|100644|0000000000000000000000000000000000000000|be6e0e6864987110ad4824814ba19505f9c730c7|-|0|ba9d21a78bc58afc5627b217ad255cba6dcfc5d94d4732140b2d6494faec8857|34019|790|0
server/src/test/resources/db/phase4c/076-legacy-personal-bank-tag-operator-core-schema.sql|A|000000|100644|0000000000000000000000000000000000000000|e05f723935bbeef5d4fd353a57e8c0510534935b|-|0|c6cf2ec3c0d0c43a7032305f3180163cb78ec933b01edbc8ad877db07d96d173|39696|928|0
server/src/test/resources/db/phase4c/077-legacy-personal-bank-tag-operator-core-seed.sql|A|000000|100644|0000000000000000000000000000000000000000|ffd90b2e84251a9d25fbf95c6186ee9d773d5a86|-|0|4d0ead5c5bff645b67bffba46272bb5564d9f37d60d3a3a0e6f1e7dd744beccf|2982|71|0
tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py|M|100644|100644|2ee18b389990d3b17336884c6b88f3bcb4f17861|58e58492a558d7a11d232b0ac1bc54288cbae93a|624d741b383866ce1bb8ec49c24445164665096cdf5b9ab679b2561c61ab7e9a|36240|8d96674c8ea55f6050133945f0f58fe365ea9383d7660ba3c6d3423cf63bc7c5|36240|1|1
tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py|M|100644|100644|0ad1af01a78e60d0fee126d44d5f455eaf978cbc|78b44b2b631d02210ce5318d19a64f3308af1b7c|3064c164d300499d958947068d3acd50c8823c741d9a0144860b5f3b1b532f7d|65798|c9d21809bd136ed131ee20ac6baabf0b6b67bcc85f03fab9fccedcd02c86f2c0|65798|1|1
tools/build_phase4c_tag_migration_global_preflight_contract.py|M|100644|100644|2564bdc7f0decf91c273256421c0b90108b59cb9|acbef90234ad00715d7f290f895153b25089de7b|fa5fb43b5caa24006c5d08b94a12eeafaa25be927165f14ae4cf170ff59c03d5|124466|604c550ceb144c0bdca1d92e915a166d84c582cd53084f934bac71e171154ddf|129684|119|9
tools/build_phase4c_tag_migration_operator_core_contract.py|A|000000|100644|0000000000000000000000000000000000000000|82e6fcb1c058ce7d355be32eeca64adca86af1d0|-|0|1b26944078d10d0e52752fb8f3fff04d40646e3ce6fab68786a6afc7de9e6194|62673|1457|0
tools/phase2_wormhole_successor_acceptance.py|M|100644|100644|097866ed80a1534e4adab5015fb40b2c57cc1468|b863cf9e8cfcaab2a3ba855431b7207fae63e515|5c93b9aa00d3faec19ebc8d6472bd9e8ab1903a7116d487ff8a711fc60fd8d20|28590|afd967894036289ad3587fc740c97931d1ca5492a9208829536bf6745a840ebc|30285|39|0
tools/phase4c_http_target_execution_anchor_successor_acceptance.py|M|100644|100644|6cace9389eb64752ec85637915b6bd1891706446|7619ad3f87a0875815f42b03d89b5b1f9adbe397|e91c56e91cdeff3bf069407d8e43d7d1b76fb131c875cf536e561976fe395141|36566|810efb88c88efeb35b7a1f182214dc8873ca7099d8f6dfb8ce6b1af651dd3ecd|36566|1|1
tools/phase4c_http_target_execution_successor_acceptance.py|M|100644|100644|b1e21ca7471b6faaf2842bb3766736f39334b102|31bc79a7ff51677880c131521d65a7452f4cdb69|daca285575123c6b3d690c52977bbf8797fa46d5db75862b774805acb586a230|84585|4048e962b5db2d332c0955099a77637c3542b77e58fd233b5460296c1f86abd9|84585|1|1
tools/phase4c_tag_migration_global_preflight_successor_acceptance.py|M|100644|100644|7de3f4025d780814a0a1ffe1ac95f9bf15d7c894|e13d989ac9d6c9c98c3577af6fdd587c9eca0339|258ba0903f318aae40ebeba1b693bd97fe13ea534e1afcb423f1a373b9e05a44|27736|6fe3bf23d53ccaccd33f3ccaf31466cf0fc44df0f71bcc6f798765519fe12f95|32367|119|15
tools/phase4c_tag_migration_operator_core_successor_acceptance.py|A|000000|100644|0000000000000000000000000000000000000000|dc8b98c37da6b755408bafb28323412a18b23328|-|0|c7e672f3a0d0ab959735de906c0e5131232c0dab17b698480f6a42cfb5871ee4|17419|433|0
tools/test_phase2_wormhole_successor_acceptance.py|M|100644|100644|ce500babe903983b5dc61bdf2206108172628b9e|8c1dec264fedf8a6ffce01238bdfacdce1a9aa94|e61ed72335bba631cf34ebfe06fae8d391e7828622eba17d0240f59efed379a3|52825|2c4881c5083c8e4ca2cf294ece486895e26d932d1f59d067f8da32ef544c63bc|54340|44|11
tools/test_phase4b_personal_bank_all_shares_entry_contract.py|M|100644|100644|ee92a7c2ebdb8ae874324405daa350dedfe749a2|2fe7883a0eac6093600ddcf62718149f5b5fafa0|31dec8b10fad1f044ecbca4a76da0d4f1f97ffbbe32e075895e050372ff8ba4a|24249|ab79ec3edc9f903a9917ae85450633982031f341aa219e75de08d69db0c63d26|24250|2|2
tools/test_phase4b_personal_bank_all_shares_read_contract.py|M|100644|100644|23889fd141dc034f9f72e2b01a4fb8317432c3e9|573f9cf3b18388c2a6995ee103685120ebc533be|7afd91f0e0048cba029d38965c900da670d5f327b8b9541b0962533b1b1f09eb|19451|a308ba6b14bb9e960006378bdf165dc2dfece856bb09bf827d600a7a6f28e060|19452|2|2
tools/test_phase4b_personal_bank_share_list_entry_contract.py|M|100644|100644|7df80701b89014f1f6709e304db3ce1d5e0da3fc|b8d998a058c13eaaf50234f50e73b4cb22f46d55|32b4d8e625f452ba20852fe64805086a6d878f3f8518298e7340122ff6120943|33265|3b59d4f9f4c3cafe84feb4bc0a902db1822455e73660f29461d2385370377122|33266|2|2
tools/test_phase4b_personal_bank_share_list_read_contract.py|M|100644|100644|1d1720238d0a1a82d30dcad10e068405fabb4b7d|2a661ffda5e90eb7f7579b543bc28ceed55f6d00|047563af77f5786b0af24eeb20f8d287163df44778aad1ee56d1805a05207ec4|45547|49441844f63e05ca57e0b89c751cca3b1b574c984223e588d40bac9e7613501f|45548|2|2
tools/test_phase4b_personal_bank_usage_stats_entry_contract.py|M|100644|100644|550883d86e3bdf8a0fcae82fc568a8fff0204b78|be92ef0ad6aebaec7660745eeaa82f38df14463c|4f3c9ab19370eabd6dbe6dbea047d1e176c3a4e8ed947035a54dc210b75e2057|25598|9625aad3553408ef631d055735af33b4b21847aaaf8a57d540dd582cba025ab9|25599|2|2
tools/test_phase4b_personal_bank_usage_stats_read_contract.py|M|100644|100644|98e4aebd874eefde518d9bec6b979f33fd3452bc|ff24a7287e02fc42720200994ce73af7799df710|0a980e05a5fd4204e5db630447c7b018d54e2e89b64e7f069eb1329f85a5d372|34463|7c8a27ef4e97ed731dd4b0dd357942e32e75a45db3d9e482e7513b1e8c1820a4|34464|2|2
tools/test_phase4b_personal_bank_user_counts_entry_contract.py|M|100644|100644|c725a2afbe664ae8325dc18463d2690de87c66d7|8144af74c4027be7545a9765d234d5c27ced432d|162e057e07d6d0d0f73b6ee8bf9210fd98c492369222ce649a4f5bd5418b16b4|37033|409a2663e26f559108e815a805f42f566f2a7dfea8d1da8f9aab966efa0a14cb|37035|4|4
tools/test_phase4c_personal_bank_user_counts_composition_contract.py|M|100644|100644|5ec3ce4c4b6f5c8524a47b5ae595e635249245e5|42f5474769a190526970517c77ca5c7542cc637e|51ab42d0a220f3e91ac07a9b3ab1f6a2ca6c366b994de200effae31a074a766b|60156|18cdd0df59a7cfa6d052192ca85fe59cd50415fe263ae172133958d59df1f544|60156|3|3
tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py|M|100644|100644|6cdf4e9578f3e2929588417853561461d9bd79dd|ba48e3e38075203fb4427c6e141f0b837780ea96|fcc4eee103b33604addfd17e453793dd41c498de62fe0538e873520dbd285b26|32398|17e77b5204bdec0b2deb43517354fada893802321a1cfa8f446151fcb5a2b0c9|32398|1|1
tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py|M|100644|100644|8d6844edc1f356d3201b0e59550177e3c5add968|bf24cb37535cf77568b4c9ad63cf984b966cf5b2|469c46bde8e339ef28a461f3fd2a34ee7e02bfa12cb75eec4f881454049e7957|34398|7e6039fd7288cd16980149b385f71faa79659092f5bd187c14d060a19c08fe84|34398|2|2
tools/test_phase4c_personal_bank_user_counts_read_contract.py|M|100644|100644|57f5d9ec83f23b06ef358bbed5dc9f7defbeea71|c2b8ce88c6f9edbafd8be7387de95ddf8fb9b17c|6c302395dca0d7d319233e6463ed65b26aa3ea103c90511752ae4cac710dbaad|24536|3aacc3a54b0ecc6314f0f84d51057f657e8c188d1f673d931092c40c3f39106b|24536|2|2
tools/test_phase4c_tag_migration_global_preflight_contract.py|M|100644|100644|099afdeb2891ddf1237a633766960b7947487841|67c0190f9f27ee9478e0660040589f69ef5220e5|3644acb20bb3ddf220d1c088c2e52778742892d8bae843c697314372fa858b87|35696|28548d878900d0aeba6b983ba307af077b4ebdd01a6b27f4c496bf6ae472c313|38541|82|15
tools/test_phase4c_tag_migration_operator_core_contract.py|A|000000|100644|0000000000000000000000000000000000000000|7c18a8df5d575eca691e4f3cb87967dc791062ec|-|0|d3f89f0943d6aace6545f3f97ccc997d0c3aee9bc7175363bd47930281dfa42f|18250|368|0
""".strip()

_C1_ROWS = r"""
docs/refactor/phase4c/personal-bank-tag-migration-operator-core-independent-acceptance-evidence.json|A|000000|100644|0000000000000000000000000000000000000000|b6a1a56380aa21647c84924d1e5fb0d7176f2d90|-|0|4262361fbcf55452bae3d8a50340c4fc2f103ee07b562fce8879500e38691003|8894|225|0
tools/run_phase4c_tag_migration_operator_core_independent_acceptance.sh|A|000000|100755|0000000000000000000000000000000000000000|85988f35846dd318fe03d133a2a31333459c84a2|-|0|bcfa8b8a386579e7fddd212712fa045bf1d30a0bf7d6c7f8df5860b933de2774|65880|1638|0
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


C0_CHANGES = _changes(_C0_ROWS)
C1_CHANGES = _changes(_C1_ROWS)

C0_CHECKPOINT = {
    "object_format": "sha1",
    "commit_oid": C0_COMMIT,
    "parent_oid": C0_PARENT,
    "unique_parent_fixed": True,
    "root_tree_oid": "e23d0e8551dc8fd3338ba0682154eebe4a9e9f2f",
    "parent_root_tree_oid": "2df48a21e622d0e5e3731fe2617ddaedbf466866",
    "ti_java_tree_oid": "38f6aafbeb7888a5539d6ab3b4b6b8d9ae522194",
    "parent_ti_java_tree_oid": "ce2c2035763ac4512fa2bcaaa73cacb255212756",
    "server_tree_oid": "c4243039f367f7f917a3f9c85c190ebc5233a0fb",
    "parent_server_tree_oid": "931e1268a43465023e23b31d903d5d7b3219981d",
    "server_src_main_tree_oid": "bdd88effe149c61fada2300a4ec85bb2a3fdaf1c",
    "parent_server_src_main_tree_oid": "21fe4902d57a11998502e63041b5a56fb039a090",
    "web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "parent_web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "miniprogram_tree_oid": "9e4f37fe49303329df392dfbe64d2ce9064b7c86",
    "parent_miniprogram_tree_oid": "9e4f37fe49303329df392dfbe64d2ce9064b7c86",
    "authored_at": "2026-07-20T14:48:15+08:00",
    "committed_at": "2026-07-20T14:48:15+08:00",
    "subject": "refactor(java): close tag migration operator core",
    "changed_path_count": 56,
    "added_count": 22,
    "modified_count": 34,
    "deleted_count": 0,
    "non_ti_java_count": 0,
    "inserted_line_count": 16_630,
    "deleted_line_count": 153,
    "current_total_bytes": 2_428_745,
    "parent_total_bytes": 1_658_884,
    "net_byte_increase": 769_861,
    "added_total_bytes": 732_604,
    "modified_current_total_bytes": 1_696_141,
    "modified_parent_total_bytes": 1_658_884,
    "exact_fifty_six_path_delta": True,
    "diff": {
        "standard_raw_sha256": "6892e663c1d1b5572c28c8aa489fc5721af4b4dbe7771edbbef12cf870bd5371",
        "standard_raw_byte_count": 10_443,
        "standard_numstat_sha256": "a42f9a7d5da81d41b08204bd26ffdbfc4da728f2541d417967c107d2f14dd87c",
        "standard_numstat_byte_count": 5_194,
        "standard_name_status_sha256": "2de8de0fd74bc734fe8cd4acb93dd50471b8179eb87e148c7f66e57188565d1d",
        "standard_name_status_byte_count": 5_011,
        "nul_raw_sha256": "ed145d808516678306ea1610fac1428244df90162371727ba9c1e4936381a196",
        "nul_raw_byte_count": 10_443,
        "nul_numstat_sha256": "f7b183cb1df7833418c014cd0a2d2a622dd0be43165e1dfa3dc6da5a7891d023",
        "nul_numstat_byte_count": 5_194,
        "nul_name_status_sha256": "22eb3e088ab24c2fcdb8defad142a01f6ba5a36bb81d9f0b5aec380a178c8725",
        "nul_name_status_byte_count": 5_011,
    },
}

C1_CHECKPOINT = {
    "object_format": "sha1",
    "commit_oid": C1_COMMIT,
    "parent_oid": C1_PARENT,
    "unique_parent_fixed": True,
    "parent_is_implementation_checkpoint": True,
    "root_tree_oid": "2cedbb629b02505ac378536bb30833cd46c3c0c4",
    "parent_root_tree_oid": C0_CHECKPOINT["root_tree_oid"],
    "ti_java_tree_oid": "23aa906d57ada83da307050c8104ce0d956d54f9",
    "parent_ti_java_tree_oid": C0_CHECKPOINT["ti_java_tree_oid"],
    "server_tree_oid": C0_CHECKPOINT["server_tree_oid"],
    "parent_server_tree_oid": C0_CHECKPOINT["server_tree_oid"],
    "server_src_main_tree_oid": C0_CHECKPOINT["server_src_main_tree_oid"],
    "parent_server_src_main_tree_oid": C0_CHECKPOINT["server_src_main_tree_oid"],
    "web_tree_oid": C0_CHECKPOINT["web_tree_oid"],
    "parent_web_tree_oid": C0_CHECKPOINT["web_tree_oid"],
    "miniprogram_tree_oid": C0_CHECKPOINT["miniprogram_tree_oid"],
    "parent_miniprogram_tree_oid": C0_CHECKPOINT["miniprogram_tree_oid"],
    "authored_at": "2026-07-20T18:26:27+08:00",
    "committed_at": "2026-07-20T18:26:27+08:00",
    "subject": "test(java): independently accept tag migration operator core",
    "changed_path_count": 2,
    "added_count": 2,
    "modified_count": 0,
    "deleted_count": 0,
    "non_ti_java_count": 0,
    "inserted_line_count": 1_863,
    "deleted_line_count": 0,
    "current_total_bytes": 74_774,
    "parent_total_bytes": 0,
    "net_byte_increase": 74_774,
    "added_total_bytes": 74_774,
    "modified_current_total_bytes": 0,
    "modified_parent_total_bytes": 0,
    "exact_two_added_path_delta": True,
    "diff": {
        "standard_raw_sha256": "928be8249730a7ba13f53f72edabc6c4578c2b4ecda58eec460c2fc11ceb4799",
        "standard_raw_byte_count": 387,
        "standard_numstat_sha256": "5066258a321368389572169e873c3650d69a88045279e5342ea279a379a49be0",
        "standard_numstat_byte_count": 202,
        "standard_name_status_sha256": "1b5b0b004bb9678769ac4426b64fd060de3e074a1c8641bb9915411f0753fee8",
        "standard_name_status_byte_count": 193,
        "nul_raw_sha256": "39abf866ca67a9abf7b82be0d50a416cc8ffcfd986c9e52dfb4fb9e772eb9cfd",
        "nul_raw_byte_count": 387,
        "nul_numstat_sha256": "ea7fac5ee9192b0e61aa8b088d5227b933011f425208c4e1643ae9d609563c90",
        "nul_numstat_byte_count": 202,
        "nul_name_status_sha256": "dc9e7520d96b8aed4b2c742618d2da94a3ebf2418dfd9f25f7783ef9eaf44933",
        "nul_name_status_byte_count": 193,
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
        "implementation_control_sources": list(C0_CONTROL_SOURCES),
        "implementation_control_source_count": 7,
        "implementation_fixed_non_control_sources": list(fixed),
        "implementation_fixed_non_control_source_count": 49,
        "implementation_transition_sources": list(transitions),
        "implementation_transition_source_count": 34,
        "independent_acceptance_control_sources": list(C1_CONTROL_SOURCES),
        "independent_acceptance_control_source_count": 2,
        "implementation_control_path_manifest_sha256": sha256_json(C0_CONTROL_SOURCES),
        "implementation_fixed_manifest_sha256": sha256_json(fixed),
        "implementation_transition_manifest_sha256": sha256_json(transitions),
        "implementation_artifact_manifest_sha256": sha256_json(C0_CHANGES),
        "independent_acceptance_artifact_manifest_sha256": sha256_json(C1_CHANGES),
        "exact_disjoint_c0_7_plus_49_partition": True,
        "all_34_transitions_are_exact_modified_commit_blobs": True,
        "c0_and_c1_control_sources_external_git_anchor_complete": True,
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
        "c1_server_tree_unchanged_from_c0": True,
        "c1_server_src_main_tree_unchanged_from_c0": True,
        "c1_web_tree_unchanged_from_c0": True,
        "c1_miniprogram_tree_unchanged_from_c0": True,
        "production_schema_or_index_added": False,
        "production_connection_or_credentials_used": False,
        "production_data_read_or_mutated": False,
        "production_operator_executed": False,
        "user_compose_or_production_docker_mutated": False,
    }


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("operator-core anchor live/ref Git authority is forbidden")
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
        raise AssertionError("operator-core anchor fixed Git replay failed") from error
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
        raise AssertionError(f"operator-core {label} fixed Git diff drifted")


def _validate_git_checkpoint(
    repository_root: Path,
    metadata: dict[str, Any],
    changes: dict[str, dict[str, Any]],
) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("operator-core anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != "sha1":
        raise AssertionError("operator-core anchor Git object format drifted")
    commit = metadata["commit_oid"]
    parent = metadata["parent_oid"]
    if (_git_text(root, "cat-file", "-t", commit) != "commit"
            or _git_text(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
            != commit):
        raise AssertionError("operator-core anchor fixed commit object drifted")
    facts = _git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", commit
    ).splitlines()
    if facts != [
        metadata["root_tree_oid"], parent, metadata["authored_at"],
        metadata["committed_at"], metadata["subject"],
    ]:
        raise AssertionError("operator-core anchor commit identity/parent drifted")
    if _git_text(root, "show", "-s", "--format=%T", parent) \
            != metadata["parent_root_tree_oid"]:
        raise AssertionError("operator-core anchor parent root tree drifted")
    tree_paths = {
        "ti_java_tree_oid": "Ti-Java",
        "server_tree_oid": "Ti-Java/server",
        "server_src_main_tree_oid": "Ti-Java/server/src/main",
        "web_tree_oid": "Ti-Java/web",
        "miniprogram_tree_oid": "miniprogram-1",
    }
    for key, relative in tree_paths.items():
        if _git_text(root, "rev-parse", f"{commit}:{relative}") != metadata[key]:
            raise AssertionError(f"operator-core anchor current tree drifted: {relative}")
        parent_key = f"parent_{key}"
        if _git_text(root, "rev-parse", f"{parent}:{relative}") \
                != metadata[parent_key]:
            raise AssertionError(f"operator-core anchor parent tree drifted: {relative}")
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
            raise AssertionError("operator-core anchor non-Ti-Java path")
        if _git_text(root, "rev-parse", f"{commit}:{repository_path}") \
                != item["git_blob_oid"]:
            raise AssertionError(f"operator-core anchor current blob drifted: {path}")
        current = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (len(current) != item["byte_count"]
                or sha256_bytes(current) != item["sha256"]):
            raise AssertionError(f"operator-core anchor current bytes drifted: {path}")
        current_total += len(current)
        inserted += item["inserted_line_count"]
        deleted += item["deleted_line_count"]
        if item["change_type"] == "A":
            if _run_git(root, "ls-tree", parent, "--", repository_path):
                raise AssertionError(f"operator-core anchor added path existed: {path}")
            added_total += len(current)
        elif item["change_type"] == "M":
            if _git_text(root, "rev-parse", f"{parent}:{repository_path}") \
                    != item["previous_git_blob_oid"]:
                raise AssertionError(f"operator-core anchor parent blob drifted: {path}")
            previous = _run_git(
                root, "cat-file", "blob", item["previous_git_blob_oid"]
            )
            if (len(previous) != item["previous_byte_count"]
                    or sha256_bytes(previous) != item["previous_sha256"]):
                raise AssertionError(f"operator-core anchor parent bytes drifted: {path}")
            previous_total += len(previous)
            modified_current += len(current)
            modified_parent += len(previous)
        else:
            raise AssertionError("operator-core anchor unsupported change type")
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
        raise AssertionError("operator-core anchor checkpoint aggregates drifted")


def validate_fixed_git_checkpoints(repository_root: Path) -> None:
    _validate_git_checkpoint(repository_root, C0_CHECKPOINT, C0_CHANGES)
    _validate_git_checkpoint(repository_root, C1_CHECKPOINT, C1_CHANGES)
    if (C1_CHECKPOINT["parent_oid"] != C0_CHECKPOINT["commit_oid"]
            or tuple(C1_CHANGES) != C1_CONTROL_SOURCES
            or C1_CHANGES[EVIDENCE_RELATIVE]["mode"] != "100644"
            or C1_CHANGES[RUNNER_RELATIVE]["mode"] != "100755"):
        raise AssertionError("operator-core C0/C1 fixed checkpoint chain drifted")


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
            raise AssertionError("operator-core post-push anchor contract drifted")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_bytes(payload)
    print(f"operator-core post-push anchor passed: {sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
