#!/usr/bin/env python3
"""Independent fail-closed acceptance for the Phase 4C Node A Git anchor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-global-preflight-post-push-anchor-contract.json"
)
CONTRACT_ID = (
    "ti.phase4c.personal-bank-tag-migration-global-preflight-"
    "post-push-anchor-contract"
)
CONTRACT_CAPTURED_AT = "2026-07-19T11:15:25+08:00"
CONTRACT_STATUS = (
    "global_preflight_checkpoint_externally_anchored_"
    "migration_design_operator_apply_and_cutover_unauthorized"
)
CONTRACT_SCOPE = (
    "phase4c-personal-bank-tag-migration-global-preflight-"
    "post-push-external-anchor"
)
CONTRACT_SHA256 = (
    "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3"
)
CONTRACT_PAYLOAD_SHA256 = (
    "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e"
)
CONTRACT_BYTE_COUNT = 66_318

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-global-preflight-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-global-preflight-contract"
)
PREDECESSOR_CAPTURED_AT = "2026-07-19T05:52:21+08:00"
PREDECESSOR_STATUS = (
    "global_preflight_bounded_payload_and_unicode_lossless_evidence_closed_"
    "migration_design_operator_apply_and_cutover_unauthorized"
)
PREDECESSOR_SCOPE = "phase4c-learning-owned-personal-bank-tag-global-preflight"
PREDECESSOR_SHA256 = (
    "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e"
)
PREDECESSOR_BYTE_COUNT = 102_931

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "256d5b347e2e5266eef084221807337427ceb16f"
GIT_PARENT_OID = "08328c3fe18e074f581bb9e782ee4ae86cf46c53"
GIT_ROOT_TREE_OID = "efcd304e85f597ac22840110630d9fc0ae9a8fb0"
GIT_PARENT_ROOT_TREE_OID = "ffd636fbedd6f39dc1975a8752b3a250a4bd184c"
GIT_TI_JAVA_TREE_OID = "e47d851f451fdf045d2c456065ae6913c69229d2"
GIT_PARENT_TI_JAVA_TREE_OID = "0e2fbc42f39f00753c4588e1ddc690725413b88c"
GIT_SERVER_TREE_OID = "0adfaa0bf6e0edeba2aceebce6c267421e3b8144"
GIT_PARENT_SERVER_TREE_OID = "0471b8408a1149f38b3c98d57b1a11cab8288d3a"
GIT_SERVER_SRC_MAIN_TREE_OID = "21fe4902d57a11998502e63041b5a56fb039a090"
GIT_PARENT_SERVER_SRC_MAIN_TREE_OID = (
    "7130e1d1fde766030689658cdd508794ab9a12d6"
)
GIT_WEB_TREE_OID = "a75f69a8205a56843feb055656ddb015ec5b5215"
GIT_AUTHORED_AT = "2026-07-19T11:15:25+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "refactor(java): close tag migration global preflight"
GIT_RAW_DELTA_SHA256 = (
    "035e51e17ce5b2596b604e479c244a1b2af711f14940730095a268257209ebcf"
)
GIT_NUMSTAT_SHA256 = (
    "8f06547f62f829b0b3c20f7596f0e5879377a76d08b5ee03ff5860f74792c7dd"
)

NODE_A_SOURCE_SUCCESSOR_MANIFEST_SHA256 = (
    "d1ab1bf37de977c934968a6d07cd711b6bec06e1b3bc22bbaa9978d8a3764b4a"
)
NODE_A_SEMANTIC_CONSUMER_MANIFEST_SHA256 = (
    "1fba3c51e73af84e21b54e6930272dc6cc1c058dbf7ceadaff8d73d1af1698db"
)
NODE_A_FIXED_SOURCE_MANIFEST_SHA256 = (
    "ec95c0105bf8f6d5e2c4b1cf3a32178a379b4efa17e1020cf4e320d49f0facbf"
)
NODE_A_CONTROL_SOURCE_MANIFEST_SHA256 = (
    "e78f71fc2a9b7d4e23ddc93ded7229c11f3d39c604d06f2c11f585bd4b0f813c"
)

CURRENT_CONTROL_SOURCES = (
    CONTRACT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightPostPushAnchorContractParityTest.java",
    "tools/build_phase4c_tag_migration_global_preflight_"
    "post_push_anchor_contract.py",
    "tools/phase4c_tag_migration_global_preflight_"
    "post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_global_preflight_"
    "post_push_anchor_contract.py",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _payload_sha256(document: dict[str, Any]) -> str:
    return _sha256_json({key: value for key, value in document.items()
                         if key != "document_payload_sha256"})


def _fixed_regular_file(root: Path, relative: str) -> Path:
    value = Path(relative)
    if (value.is_absolute() or not value.parts
            or any(part in ("", ".", "..") for part in value.parts)):
        raise AssertionError(f"Node A anchor path escapes root: {relative}")
    candidate = root.joinpath(*value.parts)
    cursor = root
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"Node A anchor path is a symlink: {relative}")
    if not candidate.is_file():
        raise AssertionError(f"Node A anchor path is not regular: {relative}")
    return candidate


def _read_json(root: Path, relative: str, expected_sha256: str,
               expected_bytes: int) -> dict[str, Any]:
    payload = _fixed_regular_file(root, relative).read_bytes()
    if (len(payload) != expected_bytes
            or _sha256_bytes(payload) != expected_sha256):
        raise AssertionError(f"Node A anchor fixed bytes drifted: {relative}")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError(f"Node A anchor JSON is not an object: {relative}")
    return document


def _predecessor(root: Path) -> dict[str, Any]:
    document = _read_json(root, PREDECESSOR_RELATIVE, PREDECESSOR_SHA256,
                          PREDECESSOR_BYTE_COUNT)
    if (document.get("contract_id") != PREDECESSOR_ID
            or document.get("captured_at") != PREDECESSOR_CAPTURED_AT
            or document.get("status") != PREDECESSOR_STATUS
            or document.get("scope") != PREDECESSOR_SCOPE
            or document.get("document_payload_sha256")
            != PREDECESSOR_PAYLOAD_SHA256
            or _payload_sha256(document) != PREDECESSOR_PAYLOAD_SHA256):
        raise AssertionError("Node A anchor predecessor identity drifted")
    return document


def _validate_artifacts(artifacts: object) -> dict[str, dict[str, Any]]:
    if not isinstance(artifacts, dict) or len(artifacts) != 63:
        raise AssertionError("Node A anchor artifact allowlist drifted")
    required = {
        "repository_path", "ti_java_relative_path", "change_type",
        "previous_mode", "mode", "previous_git_blob_oid", "git_blob_oid",
        "object_type", "sha256", "byte_count",
    }
    for relative, descriptor in artifacts.items():
        if (not isinstance(relative, str) or not isinstance(descriptor, dict)
                or set(descriptor) != required
                or descriptor.get("ti_java_relative_path") != relative
                or descriptor.get("repository_path") != f"Ti-Java/{relative}"
                or descriptor.get("change_type") not in {"A", "M"}
                or descriptor.get("object_type") != "blob"
                or descriptor.get("mode") not in {"100644", "100755"}
                or len(str(descriptor.get("git_blob_oid", ""))) != 40
                or len(str(descriptor.get("previous_git_blob_oid", ""))) != 40
                or len(str(descriptor.get("sha256", ""))) != 64
                or not isinstance(descriptor.get("byte_count"), int)):
            raise AssertionError(f"Node A anchor artifact drifted: {relative}")
    return artifacts


def validate(document: dict[str, Any], root: Path) -> None:
    expected_keys = {
        "contract_id", "schema_version", "captured_at", "status", "scope",
        "predecessor", "git_checkpoint", "node_a_authority_anchor",
        "route_state", "production_and_worm_boundary", "authorization",
        "current_node_trust_boundary", "acceptance",
        "document_payload_sha256",
    }
    if (set(document) != expected_keys
            or document.get("contract_id") != CONTRACT_ID
            or document.get("schema_version") != 1
            or document.get("captured_at") != CONTRACT_CAPTURED_AT
            or document.get("status") != CONTRACT_STATUS
            or document.get("scope") != CONTRACT_SCOPE
            or document.get("document_payload_sha256")
            != CONTRACT_PAYLOAD_SHA256
            or _payload_sha256(document) != CONTRACT_PAYLOAD_SHA256):
        raise AssertionError("Node A anchor contract identity/shape drifted")
    predecessor = _predecessor(root)
    if document.get("predecessor") != {
        "source": PREDECESSOR_RELATIVE,
        "contract_id": PREDECESSOR_ID,
        "captured_at": PREDECESSOR_CAPTURED_AT,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "sha256": PREDECESSOR_SHA256,
        "byte_count": PREDECESSOR_BYTE_COUNT,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "immutable": True,
    }:
        raise AssertionError("Node A anchor predecessor descriptor drifted")
    checkpoint = document.get("git_checkpoint", {})
    expected_checkpoint = {
        "object_format": GIT_OBJECT_FORMAT,
        "commit_oid": GIT_COMMIT_OID,
        "parent_oid": GIT_PARENT_OID,
        "unique_parent_fixed": True,
        "root_tree_oid": GIT_ROOT_TREE_OID,
        "parent_root_tree_oid": GIT_PARENT_ROOT_TREE_OID,
        "ti_java_tree_oid": GIT_TI_JAVA_TREE_OID,
        "parent_ti_java_tree_oid": GIT_PARENT_TI_JAVA_TREE_OID,
        "server_tree_oid": GIT_SERVER_TREE_OID,
        "parent_server_tree_oid": GIT_PARENT_SERVER_TREE_OID,
        "server_src_main_tree_oid": GIT_SERVER_SRC_MAIN_TREE_OID,
        "parent_server_src_main_tree_oid": GIT_PARENT_SERVER_SRC_MAIN_TREE_OID,
        "web_tree_oid": GIT_WEB_TREE_OID,
        "parent_web_tree_oid": GIT_WEB_TREE_OID,
        "web_tree_unchanged_from_parent": True,
        "server_src_main_tree_changed_from_parent": True,
        "authored_at": GIT_AUTHORED_AT,
        "committed_at": GIT_COMMITTED_AT,
        "subject": GIT_SUBJECT,
        "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
        "numstat_sha256": GIT_NUMSTAT_SHA256,
        "changed_path_count": 63,
        "added_count": 17,
        "modified_count": 46,
        "deleted_count": 0,
        "non_ti_java_count": 0,
        "inserted_line_count": 14_390,
        "deleted_line_count": 329,
        "current_total_bytes": 2_485_297,
        "added_total_bytes": 586_594,
        "modified_current_bytes": 1_898_703,
        "modified_parent_bytes": 1_806_829,
        "net_byte_increase": 678_468,
        "exact_sixty_three_path_delta": True,
    }
    for key, expected in expected_checkpoint.items():
        if checkpoint.get(key) != expected:
            raise AssertionError(f"Node A anchor checkpoint drifted: {key}")
    artifacts = _validate_artifacts(checkpoint.get("artifacts"))
    predecessor_bridges = predecessor["source_successor_bridges"]
    predecessor_authority = predecessor["source_authority"]
    node = document.get("node_a_authority_anchor", {})
    fixed_paths = sorted(
        descriptor["source"]
        for descriptor in predecessor_authority["fixed_sources"].values()
    )
    if (node.get("source_successor_paths") != predecessor_bridges["paths"]
            or node.get("source_successor_path_count") != 42
            or node.get("semantic_consumer_paths")
            != predecessor_bridges["semantic_consumer_paths"]
            or node.get("semantic_consumer_path_count") != 26
            or node.get("fixed_source_paths") != fixed_paths
            or node.get("fixed_source_count") != 72
            or node.get("control_sources")
            != predecessor_authority["control_sources"]
            or node.get("control_source_count") != 11
            or node.get("source_successor_manifest_sha256")
            != NODE_A_SOURCE_SUCCESSOR_MANIFEST_SHA256
            or node.get("semantic_consumer_manifest_sha256")
            != NODE_A_SEMANTIC_CONSUMER_MANIFEST_SHA256
            or node.get("fixed_source_manifest_sha256")
            != NODE_A_FIXED_SOURCE_MANIFEST_SHA256
            or node.get("control_source_manifest_sha256")
            != NODE_A_CONTROL_SOURCE_MANIFEST_SHA256
            or _sha256_json(predecessor_bridges["overrides"])
            != NODE_A_SOURCE_SUCCESSOR_MANIFEST_SHA256
            or _sha256_json({
                path: predecessor_bridges["overrides"][path]
                for path in predecessor_bridges["semantic_consumer_paths"]
            }) != NODE_A_SEMANTIC_CONSUMER_MANIFEST_SHA256
            or _sha256_json(predecessor_authority["fixed_sources"])
            != NODE_A_FIXED_SOURCE_MANIFEST_SHA256
            or _sha256_json(predecessor_authority["control_sources"])
            != NODE_A_CONTROL_SOURCE_MANIFEST_SHA256):
        raise AssertionError("Node A anchor predecessor authority drifted")
    transitions = set(node["source_successor_paths"])
    semantic = set(node["semantic_consumer_paths"])
    fixed = set(node["fixed_source_paths"])
    controls = set(node["control_sources"])
    changed = set(artifacts)
    if (len(transitions) != 42 or len(semantic) != 26
            or len(fixed) != 72 or len(controls) != 11
            or not semantic < transitions
            or controls & fixed or controls & transitions
            or changed != controls | (changed & fixed)
            or len(changed & fixed) != 52
            or transitions - (changed & fixed)
            or set(CURRENT_CONTROL_SOURCES) & (transitions | fixed | controls)):
        raise AssertionError("Node A anchor exact authority partition drifted")
    partition = node.get("delta_partition", {})
    expected_partition = {
        "control_path_count": 11,
        "control_added_count": 7,
        "control_modified_count": 4,
        "control_current_total_bytes": 554_504,
        "control_parent_total_bytes": 109_721,
        "changed_fixed_path_count": 52,
        "changed_fixed_added_count": 10,
        "changed_fixed_modified_count": 42,
        "changed_fixed_current_total_bytes": 1_930_793,
        "changed_fixed_parent_total_bytes": 1_697_108,
        "transition_current_total_bytes": 1_777_881,
        "transition_accepted_total_bytes": 1_697_108,
        "semantic_current_total_bytes": 1_179_001,
        "semantic_accepted_total_bytes": 1_137_011,
        "added_fixed_total_bytes": 152_912,
        "all_fixed_total_bytes": 2_533_362,
        "unchanged_fixed_path_count": 20,
        "unchanged_fixed_total_bytes": 602_569,
        "exact_disjoint_partition": True,
        "accepted_parent_and_successor_current_bytes_fixed": True,
    }
    if partition != expected_partition:
        raise AssertionError("Node A anchor byte partition drifted")
    truthy_node_fields = {
        "source_successor_path_allowlist_exact",
        "semantic_consumer_path_allowlist_exact",
        "fixed_source_path_allowlist_exact",
        "control_source_allowlist_exact",
        "all_42_source_successors_are_exact_commit_delta_blobs",
        "all_26_semantic_consumers_are_exact_commit_delta_blobs",
        "all_11_predecessor_controls_are_exact_commit_delta_blobs",
        "all_72_fixed_sources_are_fixed_by_ti_java_tree_and_manifests",
        "dynamic_source_discovery_forbidden",
        "live_head_or_ref_authority_forbidden",
        "source_successor_external_git_anchor_complete",
        "semantic_successor_external_git_anchor_complete",
        "bootstrap_control_sources_external_git_anchor_complete",
    }
    if any(node.get(field) is not True for field in truthy_node_fields):
        raise AssertionError("Node A anchor completion claims drifted")
    route = document.get("route_state", {})
    if route != {
        "migrated_operation_count": 13,
        "pending_operation_count": 598,
        "production_cutover_operation_count": 0,
        "total_operation_count": 611,
        "legacy_flask_remains_production_owner": True,
    }:
        raise AssertionError("Node A anchor route authority drifted")
    production = document.get("production_and_worm_boundary", {})
    if (production.get("terminal_worm_sha256")
            != "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344"
            or production.get("java_build_context_sha256")
            != "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"
            or production.get("dockerfile_sha256")
            != "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
            or production.get("main_addition_count") != 3
            or production.get("existing_main_modified_count") != 0
            or production.get("existing_main_deleted_count") != 0
            or production.get("web_tree_unchanged_from_parent") is not True
            or production.get("operator_or_apply_entrypoint_added") is not False):
        raise AssertionError("Node A anchor production/WORM boundary drifted")
    authorization = document.get("authorization", {})
    if (authorization.get("migration_global_preflight_evidence_closed") is not True
            or authorization.get("source_successor_external_git_anchor_complete")
            is not True
            or authorization.get("semantic_successor_external_git_anchor_complete")
            is not True
            or authorization.get(
                "bootstrap_control_sources_external_git_anchor_complete")
            is not True
            or any(authorization.get(field) is not False for field in (
                "migration_durable_ledger_freeze_design_evidence_closed",
                "migration_design_closed", "operator_migration_implementation",
                "production_schema_or_index", "real_data_migration_execution",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover",
            ))):
        raise AssertionError("Node A anchor authorization overclaim drifted")
    trust = document.get("current_node_trust_boundary", {})
    if (trust.get("control_sources") != list(CURRENT_CONTROL_SOURCES)
            or trust.get("control_source_count") != 6
            or trust.get("control_source_allowlist_exact") is not True
            or trust.get("control_sources_excluded_from_self_authority") is not True
            or trust.get("control_sources_external_git_anchor_complete") is not False
            or trust.get("independently_signed_provenance") is not False):
        raise AssertionError("Node A anchor current-node trust drifted")


def load(ti_java_root: Path = ROOT) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    document = _read_json(root, CONTRACT_RELATIVE, CONTRACT_SHA256,
                          CONTRACT_BYTE_COUNT)
    validate(document, root)
    return document


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(sorted({CONTRACT_RELATIVE, PREDECESSOR_RELATIVE}))


def checkpoint_paths(ti_java_root: Path = ROOT) -> tuple[str, ...]:
    return tuple(load(ti_java_root)["git_checkpoint"]["artifacts"])


def accepted_sha256(relative: str, ti_java_root: Path = ROOT) -> str | None:
    artifact = load(ti_java_root)["git_checkpoint"]["artifacts"].get(relative)
    return None if artifact is None else str(artifact["sha256"])


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    if any(argument in {"HEAD", "origin/main", "@", "--all"}
           for argument in arguments):
        raise AssertionError("Node A anchor live/ref Git authority is forbidden")
    environment = os.environ.copy()
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat", "PAGER": "cat", "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            ("git", "--no-optional-locks", *arguments), cwd=repository_root,
            env=environment, check=True, timeout=30,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AssertionError("Node A anchor read-only Git replay failed") from error
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("Node A anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("Node A anchor Git object format drifted")
    facts = _git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", GIT_COMMIT_OID
    ).splitlines()
    if facts != [GIT_ROOT_TREE_OID, GIT_PARENT_OID, GIT_AUTHORED_AT,
                 GIT_COMMITTED_AT, GIT_SUBJECT]:
        raise AssertionError("Node A anchor commit identity/parent drifted")
    expected_trees = {
        "Ti-Java": GIT_TI_JAVA_TREE_OID,
        "Ti-Java/server": GIT_SERVER_TREE_OID,
        "Ti-Java/server/src/main": GIT_SERVER_SRC_MAIN_TREE_OID,
        "Ti-Java/web": GIT_WEB_TREE_OID,
    }
    for relative, expected in expected_trees.items():
        if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:{relative}") != expected:
            raise AssertionError(f"Node A anchor tree drifted: {relative}")
    if (_git_text(root, "show", "-s", "--format=%T", GIT_PARENT_OID)
            != GIT_PARENT_ROOT_TREE_OID
            or _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java")
            != GIT_PARENT_TI_JAVA_TREE_OID
            or _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/server")
            != GIT_PARENT_SERVER_TREE_OID
            or _git_text(root, "rev-parse",
                         f"{GIT_PARENT_OID}:Ti-Java/server/src/main")
            != GIT_PARENT_SERVER_SRC_MAIN_TREE_OID
            or _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/web")
            != GIT_WEB_TREE_OID):
        raise AssertionError("Node A anchor parent tree boundary drifted")
    contract = load(root / "Ti-Java")
    artifacts = contract["git_checkpoint"]["artifacts"]
    raw = _run_git(root, "diff-tree", "--no-commit-id", "--raw",
                   "--abbrev=40", "-r", GIT_COMMIT_OID)
    expected_raw = [
        f":{item['previous_mode']} {item['mode']} "
        f"{item['previous_git_blob_oid']} {item['git_blob_oid']} "
        f"{item['change_type']}\t{item['repository_path']}"
        for item in artifacts.values()
    ]
    if (_sha256_bytes(raw) != GIT_RAW_DELTA_SHA256
            or raw.decode("utf-8").splitlines() != expected_raw):
        raise AssertionError("Node A anchor exact raw delta drifted")
    numstat = _run_git(root, "diff-tree", "--no-commit-id", "--numstat",
                       "-r", GIT_COMMIT_OID)
    parsed = [line.split("\t", 2)
              for line in numstat.decode("utf-8").splitlines()]
    if (_sha256_bytes(numstat) != GIT_NUMSTAT_SHA256
            or len(parsed) != 63
            or sum(int(parts[0]) for parts in parsed) != 14_390
            or sum(int(parts[1]) for parts in parsed) != 329
            or [parts[2] for parts in parsed]
            != [item["repository_path"] for item in artifacts.values()]):
        raise AssertionError("Node A anchor exact numstat drifted")
    for relative, item in artifacts.items():
        payload = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (len(payload) != item["byte_count"]
                or _sha256_bytes(payload) != item["sha256"]):
            raise AssertionError(f"Node A anchor blob drifted: {relative}")
    predecessor = _predecessor(root / "Ti-Java")
    fixed_sources = predecessor["source_authority"]["fixed_sources"]
    for descriptor in fixed_sources.values():
        relative = descriptor["source"]
        oid = _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java/{relative}")
        payload = _run_git(root, "cat-file", "blob", oid)
        if (len(payload) != descriptor["byte_count"]
                or _sha256_bytes(payload) != descriptor["sha256"]):
            raise AssertionError(f"Node A anchor fixed source drifted: {relative}")
    overrides = predecessor["source_successor_bridges"]["overrides"]
    for relative in predecessor["source_successor_bridges"]["paths"]:
        item = artifacts[relative]
        previous = _run_git(root, "cat-file", "blob",
                            item["previous_git_blob_oid"])
        override = overrides[relative]
        if (item["change_type"] != "M"
                or item["sha256"] != override["successor_sha256"]
                or item["byte_count"] != override["successor_byte_count"]
                or _sha256_bytes(previous) != override["accepted_sha256"]
                or len(previous) != override["accepted_byte_count"]):
            raise AssertionError(
                f"Node A anchor transition replay drifted: {relative}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    arguments = parser.parse_args()
    document = load(arguments.ti_java_root)
    if arguments.repository_root is not None:
        validate_git_checkpoint(arguments.repository_root)
    print(
        "Node A post-push anchor acceptance passed: "
        f"{document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
