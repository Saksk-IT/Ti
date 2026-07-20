#!/usr/bin/env python3
"""Independent Gitless acceptance for the Phase 4C operator-core C2 anchor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

try:
    from tools import (
        build_phase4c_tag_migration_operator_core_post_push_anchor_contract
        as builder,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import build_phase4c_tag_migration_operator_core_post_push_anchor_contract \
        as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
EXPECTED_CONTRACT_SHA256 = (
    "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936"
)
EXPECTED_DOCUMENT_PAYLOAD_SHA256 = (
    "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64"
)
EXPECTED_CONTRACT_BYTE_COUNT = 84_461

_TOP_LEVEL_KEYS = {
    "contract_id", "schema_version", "captured_at", "status", "scope",
    "operator_core_contract", "independent_acceptance_evidence",
    "implementation_checkpoint", "independent_acceptance_checkpoint",
    "operator_core_authority_anchor", "transitive_node_b_anchor",
    "independent_copy_verification", "production_and_worm_boundary",
    "authorization", "route_state", "current_node_trust_boundary",
    "acceptance", "document_payload_sha256",
}
_TRUE_AUTHORIZATION_FIELDS = (
    "migration_global_preflight_evidence_closed",
    "migration_durable_ledger_freeze_design_evidence_closed",
    "operator_core_evidence_closed",
    "bounded_40001_40P01_retry_implemented",
    "operator_migration_implementation",
    "operator_core_control_sources_external_git_anchor_complete",
    "independent_acceptance_control_sources_external_git_anchor_complete",
    "source_successor_external_git_anchor_complete",
    "semantic_successor_external_git_anchor_complete",
    "bootstrap_control_sources_external_git_anchor_complete",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _regular_anchored_file(root: Path, relative: str) -> Path:
    allowed = set(builder.C0_CHANGES) | set(builder.C1_CHANGES) | {
        CONTRACT_RELATIVE,
    }
    value = Path(relative)
    if value.is_absolute() or relative not in allowed:
        raise AssertionError("operator-core C2 unknown or absolute anchor path")
    base = root.resolve(strict=True)
    candidate = base / value
    cursor = base
    for part in value.parts:
        cursor /= part
        if cursor.is_symlink():
            raise AssertionError(
                f"operator-core C2 anchor path is a symlink: {relative}"
            )
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AssertionError("operator-core C2 anchored source missing") from error
    if not resolved.is_relative_to(base) or not resolved.is_file():
        raise AssertionError("operator-core C2 anchored source escaped root")
    return resolved


def validate_contract(document: dict[str, Any]) -> None:
    """Validate semantic boundaries without trusting builder validation."""
    if (
        set(document) != _TOP_LEVEL_KEYS
        or document.get("contract_id") != builder.CONTRACT_ID
        or document.get("schema_version") != 1
        or document.get("captured_at") != builder.CAPTURED_AT
        or document.get("status") != builder.STATUS
        or document.get("scope") != builder.SCOPE
        or document.get("document_payload_sha256")
        != EXPECTED_DOCUMENT_PAYLOAD_SHA256
        or builder.document_payload_sha256(document)
        != EXPECTED_DOCUMENT_PAYLOAD_SHA256
    ):
        raise AssertionError("operator-core C2 contract identity/shape drifted")

    if document.get("operator_core_contract") != {
        "source": builder.OPERATOR_CONTRACT_RELATIVE,
        "contract_id": builder.OPERATOR_CONTRACT_ID,
        "sha256": builder.OPERATOR_CONTRACT_SHA256,
        "byte_count": builder.OPERATOR_CONTRACT_BYTE_COUNT,
        "document_payload_sha256": builder.OPERATOR_CONTRACT_PAYLOAD_SHA256,
        "immutable": True,
    }:
        raise AssertionError("operator-core C2 predecessor descriptor drifted")

    evidence = document.get("independent_acceptance_evidence", {})
    runner = evidence.get("runner", {})
    raw_report = runner.get("raw_report", {})
    if (
        evidence.get("source") != builder.EVIDENCE_RELATIVE
        or evidence.get("contract_id") != builder.EVIDENCE_ID
        or evidence.get("sha256") != builder.EVIDENCE_SHA256
        or evidence.get("byte_count") != builder.EVIDENCE_BYTE_COUNT
        or evidence.get("immutable") is not True
        or evidence.get("raw_report_required_for_gitless_build") is not False
        or runner.get("path") != builder.RUNNER_RELATIVE
        or runner.get("sha256") != builder.RUNNER_SHA256
        or runner.get("byte_count") != builder.RUNNER_BYTE_COUNT
        or runner.get("git_mode") != builder.RUNNER_GIT_MODE
        or raw_report.get("tracked") is not False
        or raw_report.get("embedded") is not False
        or raw_report.get("required_for_gitless_successor_acceptance") is not False
    ):
        raise AssertionError("operator-core C2 independent evidence drifted")

    c0 = document.get("implementation_checkpoint", {})
    c1 = document.get("independent_acceptance_checkpoint", {})
    c0_artifacts = c0.get("artifacts", {})
    c1_artifacts = c1.get("artifacts", {})
    if (
        {key: value for key, value in c0.items() if key != "artifacts"}
        != builder.C0_CHECKPOINT
        or c0_artifacts != builder.C0_CHANGES
        or {key: value for key, value in c1.items() if key != "artifacts"}
        != builder.C1_CHECKPOINT
        or c1_artifacts != builder.C1_CHANGES
        or c1.get("parent_oid") != c0.get("commit_oid")
        or len(c0_artifacts) != 56
        or sum(item["change_type"] == "A" for item in c0_artifacts.values())
        != 22
        or sum(item["change_type"] == "M" for item in c0_artifacts.values())
        != 34
        or tuple(c1_artifacts) != builder.C1_CONTROL_SOURCES
        or c1_artifacts[builder.EVIDENCE_RELATIVE]["mode"] != "100644"
        or c1_artifacts[builder.RUNNER_RELATIVE]["mode"] != "100755"
    ):
        raise AssertionError("operator-core C2 fixed checkpoints drifted")
    if (
        c1_artifacts[builder.EVIDENCE_RELATIVE]["sha256"]
        != evidence.get("sha256")
        or c1_artifacts[builder.EVIDENCE_RELATIVE]["byte_count"]
        != evidence.get("byte_count")
        or c1_artifacts[builder.RUNNER_RELATIVE]["sha256"]
        != runner.get("sha256")
        or c1_artifacts[builder.RUNNER_RELATIVE]["byte_count"]
        != runner.get("byte_count")
        or c1_artifacts[builder.RUNNER_RELATIVE]["mode"]
        != runner.get("git_mode")
    ):
        raise AssertionError("operator-core C2 evidence/runner cross-anchor drifted")

    anchor = document.get("operator_core_authority_anchor", {})
    controls = set(anchor.get("implementation_control_sources", ()))
    fixed = set(anchor.get("implementation_fixed_non_control_sources", ()))
    transitions = set(anchor.get("implementation_transition_sources", ()))
    if (
        tuple(anchor.get("implementation_control_sources", ()))
        != builder.C0_CONTROL_SOURCES
        or anchor.get("implementation_control_source_count") != 7
        or anchor.get("implementation_fixed_non_control_source_count") != 49
        or anchor.get("implementation_transition_source_count") != 34
        or tuple(anchor.get("independent_acceptance_control_sources", ()))
        != builder.C1_CONTROL_SOURCES
        or anchor.get("independent_acceptance_control_source_count") != 2
        or controls & fixed
        or controls | fixed != set(builder.C0_CHANGES)
        or transitions
        != {path for path, item in builder.C0_CHANGES.items()
            if item["change_type"] == "M"}
        or anchor.get("implementation_control_path_manifest_sha256")
        != "f9098c90c9ea2d75f3b5f2d08bb84ac075015c8f1b30160dd475d0d6d6e96f22"
        or anchor.get("implementation_fixed_manifest_sha256")
        != "a0b3742d34ff42cffe2b903644876bb2d6e4db55ffba9639125fa89376d0b376"
        or anchor.get("implementation_transition_manifest_sha256")
        != "cd7f19edd049c676de69cd2572a45c6c6235dfc7a6ac1a57248c7e508dae5487"
        or any(anchor.get(field) is not True for field in (
            "exact_disjoint_c0_7_plus_49_partition",
            "all_34_transitions_are_exact_modified_commit_blobs",
            "c0_and_c1_control_sources_external_git_anchor_complete",
            "ordinary_build_and_load_are_gitless",
            "explicit_fixed_commit_git_replay_available",
            "dynamic_source_discovery_forbidden",
            "live_head_or_ref_authority_forbidden",
        ))
    ):
        raise AssertionError("operator-core C2 authority partition drifted")

    transitive = document.get("transitive_node_b_anchor", {})
    node_b_predecessor = transitive.get("predecessor", {})
    node_b_git = transitive.get("git_authority", {})
    node_b_checkpoint = node_b_git.get("external_anchor_checkpoint", {})
    node_b_artifacts = node_b_git.get("external_anchor_artifacts", {})
    expected_node_b_artifacts = {
        "docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-"
        "freeze-design-post-push-anchor-contract.json",
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchor"
        "ContractParityTest.java",
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchor"
        "SuccessorAcceptance.java",
        "tools/build_phase4c_tag_migration_durable_ledger_freeze_design_"
        "post_push_anchor_contract.py",
        "tools/phase4c_tag_migration_durable_ledger_freeze_design_"
        "post_push_anchor_successor_acceptance.py",
        "tools/test_phase4c_tag_migration_durable_ledger_freeze_design_"
        "post_push_anchor_contract.py",
    }
    if (
        transitive.get("immutable") is not True
        or node_b_predecessor.get("source")
        != (
            "docs/refactor/phase4c/personal-bank-tag-migration-durable-"
            "ledger-freeze-design-post-push-anchor-contract.json"
        )
        or node_b_predecessor.get("sha256")
        != "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6"
        or node_b_predecessor.get("byte_count") != 15_550
        or node_b_predecessor.get("document_payload_sha256")
        != "840d8e06a755fc6c01f5357411023fd875ec5dd87e322608252782b1bbc39542"
        or node_b_predecessor.get("immutable") is not True
        or node_b_checkpoint.get("commit_oid")
        != "bbeb08efcccb0b9974dfefa2044aab43e0675f6f"
        or node_b_checkpoint.get("parent_oid")
        != "ea894b3a02787a91b688d7295cace37139f7f486"
        or node_b_checkpoint.get("changed_path_count") != 6
        or node_b_checkpoint.get("added_count") != 6
        or node_b_checkpoint.get("modified_count") != 0
        or node_b_checkpoint.get("deleted_count") != 0
        or node_b_git.get("external_anchor_artifact_count") != 6
        or len(node_b_artifacts) != 6
        or set(node_b_artifacts) != expected_node_b_artifacts
        or node_b_git.get("ordinary_build_and_load_require_git") is not False
        or node_b_git.get("live_head_main_or_origin_authority") is not False
    ):
        raise AssertionError("operator-core C2 transitive Node B anchor drifted")

    verification = document.get("independent_copy_verification", {})
    source_discovery = verification.get("verification", {}).get(
        "source_discovery", {}
    )
    original_closure = verification.get("original_closure", {})
    if (
        source_discovery.get("executed_inside_independent_copy") is not False
        or source_discovery.get("claimed_independent_copy_test_count") != 0
        or original_closure.get("fixed_c0_independent_copy_acceptance_closed")
        is not True
        or original_closure.get("proves_only_commit") != builder.C0_COMMIT
        or original_closure.get("proves_c1_evidence_commit") is not False
        or original_closure.get("proves_c2_anchor_commit") is not False
        or original_closure.get("self_hash_embedded") is not False
    ):
        raise AssertionError("operator-core C2 independent-copy boundary drifted")

    authorization = document.get("authorization", {})
    if (
        any(authorization.get(field) is not True
            for field in _TRUE_AUTHORIZATION_FIELDS)
        or authorization.get(
            "current_node_control_sources_external_git_anchor_complete"
        ) is not False
        or any(authorization.get(field) is not False
               for field in builder.PRODUCTION_FALSE_FIELDS)
        or document.get("route_state") != builder.ROUTE_STATE
    ):
        raise AssertionError("operator-core C2 authorization/route drifted")

    production = document.get("production_and_worm_boundary", {})
    if (
        production.get("worm", {}).get("current_report", {}).get("sha256")
        != "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f"
        or production.get("worm", {}).get("current_chain_node_count") != 8
        or production.get("accepted_runtime_file_count") != 300
        or production.get("current_runtime_file_count") != 307
        or any(production.get(field) is not True for field in (
            "c1_server_tree_unchanged_from_c0",
            "c1_server_src_main_tree_unchanged_from_c0",
            "c1_web_tree_unchanged_from_c0",
            "c1_miniprogram_tree_unchanged_from_c0",
        ))
        or any(production.get(field) is not False for field in (
            "production_schema_or_index_added",
            "production_connection_or_credentials_used",
            "production_data_read_or_mutated",
            "production_operator_executed",
            "user_compose_or_production_docker_mutated",
        ))
    ):
        raise AssertionError("operator-core C2 production/WORM boundary drifted")

    current = document.get("current_node_trust_boundary", {})
    anchored = set(builder.C0_CHANGES) | set(builder.C1_CHANGES)
    if (
        tuple(current.get("control_sources", ()))
        != builder.CURRENT_CONTROL_SOURCES
        or current.get("control_source_count") != 6
        or current.get("control_source_allowlist_exact") is not True
        or current.get("control_sources_excluded_from_self_authority")
        is not True
        or current.get("control_sources_external_git_anchor_complete")
        is not False
        or current.get("independently_signed_provenance") is not False
        or current.get("c2_commit_or_tree_identity_embedded") is not False
        or set(builder.CURRENT_CONTROL_SOURCES) & anchored
    ):
        raise AssertionError("operator-core C2 self-authority boundary drifted")

    acceptance = document.get("acceptance", {})
    if (
        acceptance.get("implementation_checkpoint_changed_path_count") != 56
        or acceptance.get("implementation_checkpoint_added_count") != 22
        or acceptance.get("implementation_checkpoint_modified_count") != 34
        or acceptance.get(
            "independent_acceptance_checkpoint_changed_path_count"
        ) != 2
        or acceptance.get("independent_acceptance_checkpoint_added_count") != 2
        or acceptance.get("implementation_control_source_count") != 7
        or acceptance.get("implementation_fixed_non_control_source_count")
        != 49
        or acceptance.get("implementation_transition_count") != 34
        or acceptance.get("independent_acceptance_control_source_count") != 2
        or acceptance.get("current_control_source_count") != 6
        or acceptance.get("anchor_closes_no_functional_gate") is not True
        or acceptance.get("c2_self_anchor_complete") is not False
        or acceptance.get("migrated_operation_count") != 13
        or acceptance.get("pending_operation_count") != 598
        or acceptance.get("production_cutover_operation_count") != 0
    ):
        raise AssertionError("operator-core C2 acceptance boundary drifted")


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    base = root.resolve(strict=True)
    payload = _regular_anchored_file(base, CONTRACT_RELATIVE).read_bytes()
    if (
        len(payload) != EXPECTED_CONTRACT_BYTE_COUNT
        or _sha256_bytes(payload) != EXPECTED_CONTRACT_SHA256
    ):
        raise AssertionError("operator-core C2 contract fixed bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("operator-core C2 contract must be a JSON object")
    validate_contract(document)
    built = builder.build_contract(base, repository_root=None)
    if document != built or payload != builder.serialized_contract(built):
        raise AssertionError("operator-core C2 contract differs from Gitless builder")
    return document


def minimal_fixture_paths() -> tuple[str, ...]:
    return (
        builder.OPERATOR_CONTRACT_RELATIVE,
        builder.EVIDENCE_RELATIVE,
        builder.RUNNER_RELATIVE,
        CONTRACT_RELATIVE,
    )


def checkpoint_paths() -> tuple[str, ...]:
    return tuple(builder.C0_CHANGES) + tuple(builder.C1_CHANGES)


def current_control_sources() -> tuple[str, ...]:
    return builder.CURRENT_CONTROL_SOURCES


def accepted_sha256(root: Path, relative: str) -> str | None:
    descriptor = builder.C0_CHANGES.get(relative) or builder.C1_CHANGES.get(
        relative
    )
    if descriptor is None or relative in builder.CURRENT_CONTROL_SOURCES:
        return None
    try:
        payload = _regular_anchored_file(root, relative).read_bytes()
    except AssertionError:
        return None
    if (
        len(payload) != descriptor["byte_count"]
        or _sha256_bytes(payload) != descriptor["sha256"]
    ):
        return None
    return str(descriptor["sha256"])


def _run_fixed_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("operator-core C2 acceptance forbids live Git refs")
    environment = os.environ.copy()
    for key in tuple(environment):
        if (
            key in {
                "GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE",
                "GIT_CONFIG_COUNT",
            }
            or key.startswith("GIT_CONFIG_KEY_")
            or key.startswith("GIT_CONFIG_VALUE_")
        ):
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
        raise AssertionError(
            "operator-core C2 independent fixed Git replay failed"
        ) from error
    return completed.stdout


def _fixed_git_text(repository_root: Path, *arguments: str) -> str:
    return _run_fixed_git(repository_root, *arguments).decode("utf-8").strip()


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


def _assert_diff(
    label: str,
    actual: bytes,
    expected: bytes | None,
    sha256: str,
    byte_count: int,
) -> None:
    if (
        len(actual) != byte_count
        or _sha256_bytes(actual) != sha256
        or (expected is not None and actual != expected)
    ):
        raise AssertionError(f"operator-core C2 {label} Git diff drifted")


def _replay_checkpoint(
    repository: Path,
    metadata: dict[str, Any],
    changes: dict[str, dict[str, Any]],
) -> None:
    commit = metadata["commit_oid"]
    parent = metadata["parent_oid"]
    if (
        _fixed_git_text(repository, "cat-file", "-t", commit) != "commit"
        or _fixed_git_text(
            repository, "rev-parse", "--verify", f"{commit}^{{commit}}"
        ) != commit
    ):
        raise AssertionError("operator-core C2 fixed commit object drifted")
    facts = _fixed_git_text(
        repository, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", commit
    ).splitlines()
    if facts != [
        metadata["root_tree_oid"], parent, metadata["authored_at"],
        metadata["committed_at"], metadata["subject"],
    ]:
        raise AssertionError("operator-core C2 commit facts drifted")
    if _fixed_git_text(repository, "show", "-s", "--format=%T", parent) \
            != metadata["parent_root_tree_oid"]:
        raise AssertionError("operator-core C2 parent root tree drifted")
    for key, relative in {
        "ti_java_tree_oid": "Ti-Java",
        "server_tree_oid": "Ti-Java/server",
        "server_src_main_tree_oid": "Ti-Java/server/src/main",
        "web_tree_oid": "Ti-Java/web",
        "miniprogram_tree_oid": "miniprogram-1",
    }.items():
        if (
            _fixed_git_text(repository, "rev-parse", f"{commit}:{relative}")
            != metadata[key]
            or _fixed_git_text(repository, "rev-parse", f"{parent}:{relative}")
            != metadata[f"parent_{key}"]
        ):
            raise AssertionError(f"operator-core C2 tree drifted: {relative}")

    diff = metadata["diff"]
    commands = (
        ("standard raw", ("--raw", "--abbrev=40"), _expected_raw(changes)),
        ("standard numstat", ("--numstat",), _expected_numstat(changes)),
        ("standard name-status", ("--name-status",),
         _expected_name_status(changes)),
        ("NUL raw", ("--raw", "--abbrev=40", "-z"), None),
        ("NUL numstat", ("--numstat", "-z"), None),
        ("NUL name-status", ("--name-status", "-z"), None),
    )
    for label, switches, expected in commands:
        actual = _run_fixed_git(
            repository, "diff-tree", "--no-commit-id", *switches, "-r", commit
        )
        key = label.lower().replace("-", "_").replace(" ", "_")
        _assert_diff(
            label, actual, expected,
            diff[f"{key}_sha256"], diff[f"{key}_byte_count"],
        )

    current_total = previous_total = added_total = 0
    modified_current = modified_parent = inserted = deleted = 0
    for path, item in changes.items():
        repository_path = item["repository_path"]
        if (
            not repository_path.startswith("Ti-Java/")
            or _fixed_git_text(
                repository, "rev-parse", f"{commit}:{repository_path}"
            ) != item["git_blob_oid"]
        ):
            raise AssertionError(f"operator-core C2 current tree blob drifted: {path}")
        current = _run_fixed_git(
            repository, "cat-file", "blob", item["git_blob_oid"]
        )
        if (
            len(current) != item["byte_count"]
            or _sha256_bytes(current) != item["sha256"]
        ):
            raise AssertionError(f"operator-core C2 current blob drifted: {path}")
        current_total += len(current)
        inserted += item["inserted_line_count"]
        deleted += item["deleted_line_count"]
        if item["change_type"] == "A":
            if _run_fixed_git(
                repository, "ls-tree", parent, "--", repository_path
            ):
                raise AssertionError(f"operator-core C2 added path existed: {path}")
            added_total += len(current)
        elif item["change_type"] == "M":
            if _fixed_git_text(
                repository, "rev-parse", f"{parent}:{repository_path}"
            ) != item["previous_git_blob_oid"]:
                raise AssertionError(f"operator-core C2 parent blob drifted: {path}")
            previous = _run_fixed_git(
                repository, "cat-file", "blob", item["previous_git_blob_oid"]
            )
            if (
                len(previous) != item["previous_byte_count"]
                or _sha256_bytes(previous) != item["previous_sha256"]
            ):
                raise AssertionError(f"operator-core C2 parent bytes drifted: {path}")
            previous_total += len(previous)
            modified_current += len(current)
            modified_parent += len(previous)
        else:
            raise AssertionError("operator-core C2 unsupported change type")
    if (
        len(changes) != metadata["changed_path_count"]
        or current_total != metadata["current_total_bytes"]
        or previous_total != metadata["parent_total_bytes"]
        or current_total - previous_total != metadata["net_byte_increase"]
        or added_total != metadata["added_total_bytes"]
        or modified_current != metadata["modified_current_total_bytes"]
        or modified_parent != metadata["modified_parent_total_bytes"]
        or inserted != metadata["inserted_line_count"]
        or deleted != metadata["deleted_line_count"]
    ):
        raise AssertionError("operator-core C2 checkpoint aggregates drifted")


def validate_fixed_git_checkpoints(
    repository_root: Path = ROOT.parent,
) -> None:
    """Replay fixed C0 and C1 without invoking the builder's replay."""
    repository = repository_root.resolve(strict=True)
    if Path(_fixed_git_text(
        repository, "rev-parse", "--show-toplevel"
    )).resolve() != repository:
        raise AssertionError("operator-core C2 repository root drifted")
    if _fixed_git_text(
        repository, "rev-parse", "--show-object-format"
    ) != "sha1":
        raise AssertionError("operator-core C2 Git object format drifted")
    document = load_contract(repository / "Ti-Java")
    _replay_checkpoint(
        repository,
        {key: value for key, value in document["implementation_checkpoint"].items()
         if key != "artifacts"},
        document["implementation_checkpoint"]["artifacts"],
    )
    _replay_checkpoint(
        repository,
        {key: value for key, value in
         document["independent_acceptance_checkpoint"].items()
         if key != "artifacts"},
        document["independent_acceptance_checkpoint"]["artifacts"],
    )
    if (
        document["independent_acceptance_checkpoint"]["parent_oid"]
        != document["implementation_checkpoint"]["commit_oid"]
    ):
        raise AssertionError("operator-core C2 C0/C1 chain drifted")

    operator = json.loads(
        (repository / "Ti-Java" / builder.OPERATOR_CONTRACT_RELATIVE).read_bytes()
    )
    overrides = operator["historical_source_successors"]["overrides"]
    c0_artifacts = document["implementation_checkpoint"]["artifacts"]
    for path, override in overrides.items():
        item = c0_artifacts[path]
        if (
            item["change_type"] != "M"
            or override["accepted_sha256"] != item["previous_sha256"]
            or override["accepted_byte_count"] != item["previous_byte_count"]
            or override["successor_sha256"] != item["sha256"]
            or override["successor_byte_count"] != item["byte_count"]
        ):
            raise AssertionError(
                f"operator-core C2 transition replay drifted: {path}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    arguments = parser.parse_args()
    document = load_contract(arguments.ti_java_root)
    if arguments.repository_root is not None:
        validate_fixed_git_checkpoints(arguments.repository_root)
    print(
        "phase4c operator-core C2 post-push anchor acceptance passed: "
        f"{document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
