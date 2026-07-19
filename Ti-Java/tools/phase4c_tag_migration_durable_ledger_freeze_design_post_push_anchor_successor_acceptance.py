#!/usr/bin/env python3
"""Gitless acceptance for the Phase 4C Node B post-push anchor."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

try:
    from tools import (
        build_phase4c_tag_migration_durable_ledger_freeze_design_post_push_anchor_contract
        as builder,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import build_phase4c_tag_migration_durable_ledger_freeze_design_post_push_anchor_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
EXPECTED_CONTRACT_SHA256 = (
    "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6"
)
EXPECTED_DOCUMENT_PAYLOAD_SHA256 = (
    "840d8e06a755fc6c01f5357411023fd875ec5dd87e322608252782b1bbc39542"
)
EXPECTED_CONTRACT_BYTE_COUNT = 15_550
EXPECTED_CONTROL_PATH_MANIFEST_SHA256 = (
    "752e8f4665e6bab412ee7f19e04c772ee08e7c6ff3f1a57a6eed99955f058a52"
)
EXPECTED_CONTROL_BLOB_MANIFEST_SHA256 = (
    "9afa04ced62c1ad15683efcddb941d62bef257ba2ddc53908b3d9f110d5060c0"
)


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if (
        len(payload) != EXPECTED_CONTRACT_BYTE_COUNT
        or builder.sha256_bytes(payload) != EXPECTED_CONTRACT_SHA256
    ):
        raise AssertionError("Node B anchor contract fixed bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("Node B anchor contract must be a JSON object")
    if (
        document.get("document_payload_sha256")
        != EXPECTED_DOCUMENT_PAYLOAD_SHA256
        or builder.document_payload_sha256(document)
        != EXPECTED_DOCUMENT_PAYLOAD_SHA256
    ):
        raise AssertionError("Node B anchor contract payload identity drifted")
    expected = builder.build_contract(root)
    if document != expected or payload != builder.serialized_contract(expected):
        raise AssertionError("Node B anchor differs from Gitless builder")
    validate_contract(document)
    return document


def validate_contract(document: dict[str, Any]) -> None:
    if (
        document.get("contract_id") != builder.CONTRACT_ID
        or document.get("captured_at") != builder.CAPTURED_AT
        or document.get("status") != builder.STATUS
        or document.get("scope") != builder.SCOPE
    ):
        raise AssertionError("Node B anchor contract identity drifted")
    predecessor = document.get("predecessor", {})
    if predecessor != {
        "source": builder.PREDECESSOR_RELATIVE,
        "contract_id": builder.PREDECESSOR_ID,
        "captured_at": builder.PREDECESSOR_CAPTURED_AT,
        "status": builder.PREDECESSOR_STATUS,
        "scope": builder.PREDECESSOR_SCOPE,
        "sha256": builder.PREDECESSOR_SHA256,
        "byte_count": builder.PREDECESSOR_BYTE_COUNT,
        "document_payload_sha256": builder.PREDECESSOR_PAYLOAD_SHA256,
        "immutable": True,
    }:
        raise AssertionError("Node B anchor predecessor descriptor drifted")
    checkpoint = document.get("git_checkpoint", {})
    artifacts = checkpoint.get("artifacts", {})
    if (
        checkpoint.get("object_format") != builder.GIT_OBJECT_FORMAT
        or checkpoint.get("commit_oid") != builder.GIT_COMMIT_OID
        or checkpoint.get("parent_oid") != builder.GIT_PARENT_OID
        or checkpoint.get("root_tree_oid") != builder.GIT_ROOT_TREE_OID
        or checkpoint.get("ti_java_tree_oid") != builder.GIT_TI_JAVA_TREE_OID
        or checkpoint.get("server_tree_oid") != builder.GIT_SERVER_TREE_OID
        or checkpoint.get("server_src_main_tree_oid")
        != builder.GIT_SERVER_SRC_MAIN_TREE_OID
        or checkpoint.get("web_tree_oid") != builder.GIT_WEB_TREE_OID
        or checkpoint.get("raw_delta_sha256")
        != builder.GIT_RAW_DELTA_SHA256
        or checkpoint.get("numstat_sha256")
        != builder.GIT_NUMSTAT_SHA256
        or checkpoint.get("changed_path_count") != 8
        or checkpoint.get("added_count") != 8
        or checkpoint.get("modified_count") != 0
        or checkpoint.get("deleted_count") != 0
        or checkpoint.get("non_ti_java_count") != 0
        or checkpoint.get("inserted_line_count") != 5_362
        or checkpoint.get("deleted_line_count") != 0
        or checkpoint.get("current_total_bytes") != 233_639
        or artifacts != builder.CHECKPOINT_CHANGES
    ):
        raise AssertionError("Node B anchor fixed checkpoint drifted")
    anchor = document.get("node_b_control_source_anchor", {})
    if (
        tuple(anchor.get("control_sources", ())) != builder.CHECKPOINT_PATHS
        or anchor.get("control_source_count") != 8
        or anchor.get("control_source_path_manifest_sha256")
        != EXPECTED_CONTROL_PATH_MANIFEST_SHA256
        or anchor.get("control_source_blob_manifest_sha256")
        != EXPECTED_CONTROL_BLOB_MANIFEST_SHA256
        or anchor.get("all_controls_are_exact_commit_delta_blobs") is not True
        or anchor.get("all_controls_absent_from_parent") is not True
        or anchor.get(
            "predecessor_control_sources_external_git_anchor_complete"
        )
        is not True
        or anchor.get("ordinary_build_and_load_are_gitless") is not True
        or anchor.get("dynamic_source_discovery_forbidden") is not True
        or anchor.get("live_head_or_ref_authority_forbidden") is not True
    ):
        raise AssertionError("Node B control-source anchor drifted")
    node_a = document.get("transitive_node_a_anchor", {})
    if (
        node_a.get("source") != builder.NODE_A_ANCHOR_RELATIVE
        or node_a.get("contract_id") != builder.NODE_A_ANCHOR_ID
        or node_a.get("sha256") != builder.NODE_A_ANCHOR_SHA256
        or node_a.get("byte_count") != builder.NODE_A_ANCHOR_BYTE_COUNT
        or node_a.get("document_payload_sha256")
        != builder.NODE_A_ANCHOR_PAYLOAD_SHA256
        or node_a.get("external_anchor_checkpoint_commit_oid")
        != builder.NODE_A_EXTERNAL_ANCHOR_COMMIT
        or tuple(node_a.get("external_anchor_control_sources", ()))
        != builder.NODE_A_EXTERNAL_CONTROL_SOURCES
        or node_a.get("external_anchor_artifact_count") != 6
        or tuple(node_a.get("external_anchor_artifacts", {}))
        != builder.NODE_A_EXTERNAL_CONTROL_SOURCES
        or node_a.get("immutable") is not True
    ):
        raise AssertionError("Node B transitive Node A anchor drifted")
    authorization = document.get("inherited_evidence_and_authorization", {})
    for field in (
        "migration_global_preflight_evidence_closed",
        "migration_durable_ledger_freeze_design_evidence_closed",
        "source_successor_external_git_anchor_complete",
        "semantic_successor_external_git_anchor_complete",
        "bootstrap_control_sources_external_git_anchor_complete",
        "node_b_control_sources_external_git_anchor_complete",
    ):
        if authorization.get(field) is not True:
            raise AssertionError(f"Node B inherited true gate drifted: {field}")
    for field in builder.PRODUCTION_FALSE_FIELDS:
        if authorization.get(field) is not False:
            raise AssertionError(f"Node B production boundary drifted: {field}")
    if document.get("route_state") != builder.ROUTE_STATE:
        raise AssertionError("Node B anchor route boundary drifted")
    production = document.get("production_boundary", {})
    if (
        production.get("checkpoint_contains_only_docs_tests_and_tools")
        is not True
        or production.get("server_src_main_tree_unchanged_from_parent")
        is not True
        or production.get("web_tree_unchanged_from_parent") is not True
        or any(production.get(field) is not False for field in (
            "production_schema_or_index_added",
            "operator_or_apply_entrypoint_added",
            "production_connection_or_credentials_used",
            "production_data_read_or_mutated",
            "user_compose_or_production_docker_mutated",
        ))
    ):
        raise AssertionError("Node B anchor production evidence drifted")
    current = document.get("current_node_trust_boundary", {})
    if (
        tuple(current.get("control_sources", ()))
        != builder.CURRENT_CONTROL_SOURCES
        or current.get("control_source_count") != 6
        or current.get("control_sources_excluded_from_self_authority")
        is not True
        or current.get("control_sources_external_git_anchor_complete")
        is not False
        or current.get("independently_signed_provenance") is not False
    ):
        raise AssertionError("Node B anchor current self-authority drifted")
    if document.get("acceptance", {}).get(
        "anchor_closes_no_functional_gate"
    ) is not True:
        raise AssertionError("Node B anchor functional-gate boundary drifted")


def _run_fixed_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("Node B anchor acceptance forbids live Git refs")
    environment = os.environ.copy()
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
        raise AssertionError(
            "Node B anchor acceptance read-only Git replay failed"
        ) from error
    return completed.stdout


def _fixed_git_text(repository_root: Path, *arguments: str) -> str:
    return _run_fixed_git(repository_root, *arguments).decode("utf-8").strip()


def validate_fixed_git_checkpoint(repository_root: Path = ROOT.parent) -> None:
    """Independently replay the fixed commit without trusting builder replay."""
    repository = repository_root.resolve(strict=True)
    document = load_contract(repository / "Ti-Java")
    checkpoint = document["git_checkpoint"]
    commit_oid = checkpoint["commit_oid"]
    parent_oid = checkpoint["parent_oid"]
    if Path(_fixed_git_text(
        repository, "rev-parse", "--show-toplevel"
    )).resolve() != repository:
        raise AssertionError("Node B anchor acceptance repository root drifted")
    if _fixed_git_text(
        repository, "rev-parse", "--show-object-format"
    ) != checkpoint["object_format"]:
        raise AssertionError("Node B anchor acceptance object format drifted")
    facts = _fixed_git_text(
        repository,
        "show",
        "-s",
        "--format=%T%n%P%n%aI%n%cI%n%s",
        commit_oid,
    ).splitlines()
    if facts != [
        checkpoint["root_tree_oid"],
        parent_oid,
        checkpoint["authored_at"],
        checkpoint["committed_at"],
        checkpoint["subject"],
    ]:
        raise AssertionError("Node B anchor acceptance commit facts drifted")
    if _fixed_git_text(
        repository, "show", "-s", "--format=%T", parent_oid
    ) != checkpoint["parent_root_tree_oid"]:
        raise AssertionError("Node B anchor acceptance parent tree drifted")
    for key, relative in (
        ("ti_java_tree_oid", "Ti-Java"),
        ("server_tree_oid", "Ti-Java/server"),
        ("server_src_main_tree_oid", "Ti-Java/server/src/main"),
        ("web_tree_oid", "Ti-Java/web"),
    ):
        if _fixed_git_text(
            repository, "rev-parse", f"{commit_oid}:{relative}"
        ) != checkpoint[key]:
            raise AssertionError(
                f"Node B anchor acceptance current tree drifted: {relative}"
            )
    for key, relative in (
        ("parent_ti_java_tree_oid", "Ti-Java"),
        ("parent_server_tree_oid", "Ti-Java/server"),
        ("parent_server_src_main_tree_oid", "Ti-Java/server/src/main"),
        ("parent_web_tree_oid", "Ti-Java/web"),
    ):
        if _fixed_git_text(
            repository, "rev-parse", f"{parent_oid}:{relative}"
        ) != checkpoint[key]:
            raise AssertionError(
                f"Node B anchor acceptance parent tree drifted: {relative}"
            )
    artifacts = checkpoint["artifacts"]
    expected_raw = [
        f":{item['previous_mode']} {item['mode']} "
        f"{item['previous_git_blob_oid']} {item['git_blob_oid']} "
        f"{item['change_type']}\t{item['repository_path']}"
        for item in artifacts.values()
    ]
    raw = _run_fixed_git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        commit_oid,
    )
    if (
        builder.sha256_bytes(raw) != checkpoint["raw_delta_sha256"]
        or raw.decode("utf-8").splitlines() != expected_raw
    ):
        raise AssertionError("Node B anchor acceptance raw delta drifted")
    numstat = _run_fixed_git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--numstat",
        "-r",
        commit_oid,
    )
    expected_numstat = [
        f"{item['inserted_line_count']}\t{item['deleted_line_count']}\t"
        f"{item['repository_path']}"
        for item in artifacts.values()
    ]
    if (
        builder.sha256_bytes(numstat) != checkpoint["numstat_sha256"]
        or numstat.decode("utf-8").splitlines() != expected_numstat
    ):
        raise AssertionError("Node B anchor acceptance numstat drifted")
    for relative, item in artifacts.items():
        if _fixed_git_text(
            repository,
            "rev-parse",
            f"{commit_oid}:{item['repository_path']}",
        ) != item["git_blob_oid"]:
            raise AssertionError(
                f"Node B anchor acceptance tree blob drifted: {relative}"
            )
        if _run_fixed_git(
            repository, "ls-tree", parent_oid, "--", item["repository_path"]
        ):
            raise AssertionError(
                f"Node B anchor acceptance parent path exists: {relative}"
            )
        payload = _run_fixed_git(
            repository, "cat-file", "blob", item["git_blob_oid"]
        )
        if (
            len(payload) != item["byte_count"]
            or builder.sha256_bytes(payload) != item["sha256"]
        ):
            raise AssertionError(
                f"Node B anchor acceptance Git blob drifted: {relative}"
            )


def accepted_sha256(root: Path, relative: str) -> str | None:
    descriptor = builder.CHECKPOINT_CHANGES.get(relative)
    if descriptor is None:
        return None
    candidate = root.resolve(strict=True) / relative
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if (
        not resolved.is_relative_to(root.resolve(strict=True))
        or candidate.is_symlink()
        or not resolved.is_file()
    ):
        return None
    payload = resolved.read_bytes()
    if (
        len(payload) != descriptor["byte_count"]
        or builder.sha256_bytes(payload) != descriptor["sha256"]
    ):
        return None
    return descriptor["sha256"]


def current_control_sources() -> tuple[str, ...]:
    return builder.CURRENT_CONTROL_SOURCES


def main() -> None:
    load_contract()
    validate_fixed_git_checkpoint()
    print("phase4c tag migration Node B post-push anchor acceptance: OK")


if __name__ == "__main__":
    main()
