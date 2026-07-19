#!/usr/bin/env python3
"""Build the gitless Phase 4C durable-ledger/freeze design contract."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-durable-ledger-freeze-design-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE

CONTRACT_ID = (
    "ti.phase4c.personal-bank-tag-migration-durable-ledger-freeze-"
    "design-contract"
)
CAPTURED_AT = "2026-07-19T13:20:00+08:00"
SCOPE = "phase4c-learning-owned-tag-migration-durable-ledger-freeze-design"
STATUS = (
    "durable_ledger_freeze_design_test_evidence_closed_"
    "production_freeze_schema_operator_apply_backup_and_cutover_unauthorized"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-global-preflight-post-push-anchor-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-global-preflight-"
    "post-push-anchor-contract"
)
PREDECESSOR_CAPTURED_AT = "2026-07-19T11:15:25+08:00"
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-tag-migration-global-preflight-"
    "post-push-external-anchor"
)
PREDECESSOR_STATUS = (
    "global_preflight_checkpoint_externally_anchored_"
    "migration_design_operator_apply_and_cutover_unauthorized"
)
PREDECESSOR_SHA256 = (
    "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e"
)
PREDECESSOR_BYTE_COUNT = 66_318

NODE_A_CONTRACT_SHA256 = (
    "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e"
)
NODE_A_CONTRACT_PAYLOAD_SHA256 = (
    "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e"
)
NODE_A_CONTRACT_BYTE_COUNT = 102_931

NODE_A_IMPLEMENTATION_CHECKPOINT = {
    "commit_oid": "256d5b347e2e5266eef084221807337427ceb16f",
    "parent_oid": "08328c3fe18e074f581bb9e782ee4ae86cf46c53",
    "root_tree_oid": "efcd304e85f597ac22840110630d9fc0ae9a8fb0",
    "parent_root_tree_oid": "ffd636fbedd6f39dc1975a8752b3a250a4bd184c",
    "ti_java_tree_oid": "e47d851f451fdf045d2c456065ae6913c69229d2",
    "parent_ti_java_tree_oid": "0e2fbc42f39f00753c4588e1ddc690725413b88c",
    "server_tree_oid": "0adfaa0bf6e0edeba2aceebce6c267421e3b8144",
    "parent_server_tree_oid": "0471b8408a1149f38b3c98d57b1a11cab8288d3a",
    "server_src_main_tree_oid": "21fe4902d57a11998502e63041b5a56fb039a090",
    "parent_server_src_main_tree_oid": (
        "7130e1d1fde766030689658cdd508794ab9a12d6"
    ),
    "web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "parent_web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "raw_delta_sha256": (
        "035e51e17ce5b2596b604e479c244a1b2af711f14940730095a268257209ebcf"
    ),
    "numstat_sha256": (
        "8f06547f62f829b0b3c20f7596f0e5879377a76d08b5ee03ff5860f74792c7dd"
    ),
    "changed_path_count": 63,
    "added_count": 17,
    "modified_count": 46,
    "deleted_count": 0,
    "subject": "refactor(java): close tag migration global preflight",
}

NODE_A_EXTERNAL_ANCHOR_ARTIFACTS = {
    PREDECESSOR_RELATIVE: {
        "git_blob_oid": "4870efa2769668590d356c8e8052ddf8f453e1ca",
        "mode": "100644",
        "sha256": PREDECESSOR_SHA256,
        "byte_count": PREDECESSOR_BYTE_COUNT,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightPostPushAnchorContractParityTest.java"
    ): {
        "git_blob_oid": "d94a60b74bb1735f4758772ccc3f348988b9b7bc",
        "mode": "100644",
        "sha256": (
            "9481b95ed60e559dae1919d83aa50b70f33649a968c4d24c33bd4c22aac1ff4a"
        ),
        "byte_count": 12_763,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance.java"
    ): {
        "git_blob_oid": "cdfef7bce7d51eae5420719f3acd9fb06e34b2d2",
        "mode": "100644",
        "sha256": (
            "d0cf01bb7a0d626962d9740e2175fc8546e4e2bda9e8b4f5a779c8cf367a74e0"
        ),
        "byte_count": 22_265,
    },
    "tools/build_phase4c_tag_migration_global_preflight_post_push_anchor_contract.py": {
        "git_blob_oid": "c7bfb875c49edbfdbe11ce78c19ea9484e53503f",
        "mode": "100644",
        "sha256": (
            "6e7b8f27e7587c3430e27f9adeec8ec12bf4c5be325e3ae616cae4d8fbdbec27"
        ),
        "byte_count": 50_605,
    },
    (
        "tools/phase4c_tag_migration_global_preflight_"
        "post_push_anchor_successor_acceptance.py"
    ): {
        "git_blob_oid": "a019840144f495d886030177cf4c04e4af5d1220",
        "mode": "100644",
        "sha256": (
            "3e2b3d6c06cff592176713578b779c5bac36f104a6ac52d30e187414763f05e3"
        ),
        "byte_count": 25_770,
    },
    "tools/test_phase4c_tag_migration_global_preflight_post_push_anchor_contract.py": {
        "git_blob_oid": "5943729f4fc0e98390314047ba6c0e186d9034d4",
        "mode": "100644",
        "sha256": (
            "0a1b044fc082edd4449d845c44d9da3dc5d10ea85c346a2c1fe8d093f8cf34bb"
        ),
        "byte_count": 13_002,
    },
}

NODE_A_EXTERNAL_ANCHOR_CHECKPOINT = {
    "object_format": "sha1",
    "commit_oid": "345deff63d2d3e867926f1e0d05d5e6d90885c4a",
    "parent_oid": "256d5b347e2e5266eef084221807337427ceb16f",
    "root_tree_oid": "a59ee94d6cf533555d5d853ef11fa39e7612a22b",
    "parent_root_tree_oid": "efcd304e85f597ac22840110630d9fc0ae9a8fb0",
    "ti_java_tree_oid": "87da31003c4d545762bac2a0de12ef4712300f04",
    "parent_ti_java_tree_oid": "e47d851f451fdf045d2c456065ae6913c69229d2",
    "server_tree_oid": "4749b6ab453516ff7ca060d59d3759ffd2da6d6b",
    "parent_server_tree_oid": "0adfaa0bf6e0edeba2aceebce6c267421e3b8144",
    "server_src_main_tree_oid": "21fe4902d57a11998502e63041b5a56fb039a090",
    "parent_server_src_main_tree_oid": (
        "21fe4902d57a11998502e63041b5a56fb039a090"
    ),
    "web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "parent_web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "authored_at": "2026-07-19T11:45:59+08:00",
    "committed_at": "2026-07-19T11:45:59+08:00",
    "subject": "test(java): anchor tag migration global preflight",
    "raw_delta_sha256": (
        "a2f2d57fa6e0d051fde8d5d4e536369b62f12b2a3186433eded6e39ef33c74ff"
    ),
    "numstat_sha256": (
        "9b7c2d8d38ec68119ce6e1b0539c3839565390d97e500e3e65e4fe4fe0937c12"
    ),
    "changed_path_count": 6,
    "added_count": 6,
    "modified_count": 0,
    "deleted_count": 0,
    "inserted_line_count": 3_426,
    "deleted_line_count": 0,
    "added_total_bytes": 190_723,
    "artifacts": NODE_A_EXTERNAL_ANCHOR_ARTIFACTS,
}

LEGACY_WRITER_SNAPSHOTS = {
    "bank_tag_get_fallback_writer": {
        "repository_path": "app/modules/user_bank/routes/api_tags.py",
        "mode": "100644",
        "git_blob_oid": "06e4a87d006ee152bd920c77c9606aebe2a14661",
        "sha256": (
            "e627d5dd64e27d80b28f2c200ec5e110bb9aedb6d73c225337071d5490284407"
        ),
        "byte_count": 11_710,
        "reads_reserved_bank_tag_key": True,
        "writes_target_when_target_is_empty": True,
        "commits_without_java_advisory_lock": True,
    },
    "generic_progress_writer": {
        "repository_path": (
            "app/modules/quiz/routes/api_components/"
            "progress_tags_notifications.py"
        ),
        "mode": "100644",
        "git_blob_oid": "a2dd8d426a3a441cd9099ece0c87376d893153a8",
        "sha256": (
            "4dfaa547800ee6a1e01d57fac4ccd235a524e98d1be90ec14e466b2094eddbfc"
        ),
        "byte_count": 11_340,
        "accepts_arbitrary_p_key_post": True,
        "accepts_arbitrary_p_key_delete": True,
        "commits_without_java_advisory_lock": True,
    },
}

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    (
        "docs/refactor/phase4c/"
        "personal-bank-tag-migration-durable-ledger-freeze-design.md"
    ),
    (
        "server/src/test/java/io/saksk/ti/integration/"
        "Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT.java"
    ),
    (
        "server/src/test/resources/db/phase4c/"
        "074-legacy-personal-bank-tag-durable-ledger-freeze-design-schema.sql"
    ),
    (
        "server/src/test/resources/db/phase4c/"
        "075-legacy-personal-bank-tag-durable-ledger-freeze-design-seed.sql"
    ),
    "tools/build_phase4c_tag_migration_durable_ledger_freeze_design_contract.py",
    (
        "tools/phase4c_tag_migration_durable_ledger_freeze_"
        "design_successor_acceptance.py"
    ),
    (
        "tools/test_phase4c_tag_migration_durable_ledger_"
        "freeze_design_contract.py"
    ),
)

FIXED_SOURCE_ALLOWLIST = (PREDECESSOR_RELATIVE,)
ROUTE_STATE = {
    "migrated_operation_count": 13,
    "pending_operation_count": 598,
    "production_cutover_operation_count": 0,
    "total_operation_count": 611,
    "legacy_flask_remains_production_owner": True,
}
STATES = ("PLANNED", "FROZEN", "APPLYING", "APPLIED", "BLOCKED")
TRANSITIONS = (
    {"from": "PLANNED", "version": 0, "to": "FROZEN", "next_version": 1},
    {"from": "FROZEN", "version": 1, "to": "APPLYING", "next_version": 2},
    {"from": "APPLYING", "version": 2, "to": "APPLIED", "next_version": 3},
    {"from": "PLANNED", "version": 0, "to": "BLOCKED", "next_version": 1},
    {"from": "FROZEN", "version": 1, "to": "BLOCKED", "next_version": 2},
    {"from": "APPLYING", "version": 2, "to": "BLOCKED", "next_version": 3},
)
RETRYABLE_SQLSTATES = ("40001", "40P01")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json(
        {
            key: value
            for key, value in document.items()
            if key != "document_payload_sha256"
        }
    )


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    value = Path(relative)
    if (
        value.is_absolute()
        or not value.parts
        or any(part in ("", ".", "..") for part in value.parts)
    ):
        raise AssertionError(f"Node B path escapes fixed root: {relative}")
    root = root.resolve(strict=True)
    cursor = root
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"Node B fixed source is a symlink: {relative}")
    if not cursor.is_file():
        raise AssertionError(f"Node B fixed source is not a regular file: {relative}")
    return cursor


def _run_fixed_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("Node B live/ref Git authority is forbidden")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
        }
    )
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
        raise AssertionError("Node B fixed Node A Git replay failed") from error
    return completed.stdout


def _fixed_git_text(repository_root: Path, *arguments: str) -> str:
    return _run_fixed_git(repository_root, *arguments).decode("utf-8").strip()


def validate_node_a_external_anchor_git(repository_root: Path) -> None:
    """Replay only the explicitly fixed 345deff six-blob checkpoint."""
    root = repository_root.resolve(strict=True)
    checkpoint = NODE_A_EXTERNAL_ANCHOR_CHECKPOINT
    commit_oid = checkpoint["commit_oid"]
    if Path(_fixed_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("Node B Git replay root is not explicit")
    if _fixed_git_text(root, "rev-parse", "--show-object-format") != "sha1":
        raise AssertionError("Node B Git object format drifted")
    facts = _fixed_git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", commit_oid
    ).splitlines()
    expected_facts = [
        checkpoint["root_tree_oid"],
        checkpoint["parent_oid"],
        checkpoint["authored_at"],
        checkpoint["committed_at"],
        checkpoint["subject"],
    ]
    if facts != expected_facts:
        raise AssertionError("Node B fixed external anchor commit drifted")
    tree_paths = {
        "Ti-Java": "ti_java_tree_oid",
        "Ti-Java/server": "server_tree_oid",
        "Ti-Java/server/src/main": "server_src_main_tree_oid",
        "Ti-Java/web": "web_tree_oid",
    }
    for relative, key in tree_paths.items():
        if _fixed_git_text(root, "rev-parse", f"{commit_oid}:{relative}") != checkpoint[key]:
            raise AssertionError(f"Node B fixed external anchor tree drifted: {relative}")
    parent_oid = checkpoint["parent_oid"]
    parent_tree_paths = {
        "Ti-Java": "parent_ti_java_tree_oid",
        "Ti-Java/server": "parent_server_tree_oid",
        "Ti-Java/server/src/main": "parent_server_src_main_tree_oid",
        "Ti-Java/web": "parent_web_tree_oid",
    }
    if _fixed_git_text(root, "show", "-s", "--format=%T", parent_oid) != checkpoint[
        "parent_root_tree_oid"
    ]:
        raise AssertionError("Node B fixed external anchor parent root drifted")
    for relative, key in parent_tree_paths.items():
        if _fixed_git_text(root, "rev-parse", f"{parent_oid}:{relative}") != checkpoint[key]:
            raise AssertionError(
                f"Node B fixed external anchor parent tree drifted: {relative}"
            )
    raw = _run_fixed_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        commit_oid,
    )
    expected_raw = [
        ":000000 100644 "
        "0000000000000000000000000000000000000000 "
        f"{artifact['git_blob_oid']} A\tTi-Java/{relative}"
        for relative, artifact in NODE_A_EXTERNAL_ANCHOR_ARTIFACTS.items()
    ]
    if (
        sha256_bytes(raw) != checkpoint["raw_delta_sha256"]
        or raw.decode("utf-8").splitlines() != expected_raw
    ):
        raise AssertionError("Node B fixed external anchor raw delta drifted")
    numstat = _run_fixed_git(
        root, "diff-tree", "--no-commit-id", "--numstat", "-r", commit_oid
    )
    parsed = [line.split("\t", 2) for line in numstat.decode("utf-8").splitlines()]
    if (
        sha256_bytes(numstat) != checkpoint["numstat_sha256"]
        or len(parsed) != 6
        or [parts[2] for parts in parsed]
        != [f"Ti-Java/{path}" for path in NODE_A_EXTERNAL_ANCHOR_ARTIFACTS]
        or sum(int(parts[0]) for parts in parsed)
        != checkpoint["inserted_line_count"]
        or sum(int(parts[1]) for parts in parsed) != 0
    ):
        raise AssertionError("Node B fixed external anchor numstat drifted")
    total_bytes = 0
    for relative, artifact in NODE_A_EXTERNAL_ANCHOR_ARTIFACTS.items():
        payload = _run_fixed_git(root, "cat-file", "blob", artifact["git_blob_oid"])
        if (
            len(payload) != artifact["byte_count"]
            or sha256_bytes(payload) != artifact["sha256"]
        ):
            raise AssertionError(
                f"Node B fixed external anchor blob drifted: {relative}"
            )
        total_bytes += len(payload)
    if total_bytes != checkpoint["added_total_bytes"]:
        raise AssertionError("Node B fixed external anchor byte total drifted")
    for name, snapshot in LEGACY_WRITER_SNAPSHOTS.items():
        relative = snapshot["repository_path"]
        tree_row = _fixed_git_text(
            root, "ls-tree", commit_oid, "--", relative
        ).split()
        if (
            len(tree_row) != 4
            or tree_row[0] != snapshot["mode"]
            or tree_row[1] != "blob"
            or tree_row[2] != snapshot["git_blob_oid"]
            or tree_row[3] != relative
        ):
            raise AssertionError(
                f"Node B fixed legacy writer Git identity drifted: {name}"
            )
        payload = _run_fixed_git(
            root, "cat-file", "blob", snapshot["git_blob_oid"]
        )
        if (
            len(payload) != snapshot["byte_count"]
            or sha256_bytes(payload) != snapshot["sha256"]
        ):
            raise AssertionError(
                f"Node B fixed legacy writer blob drifted: {name}"
            )


def load_predecessor(root: Path = ROOT) -> dict[str, Any]:
    payload = fixed_regular_file(root, PREDECESSOR_RELATIVE).read_bytes()
    if (
        len(payload) != PREDECESSOR_BYTE_COUNT
        or sha256_bytes(payload) != PREDECESSOR_SHA256
    ):
        raise AssertionError("Node B fixed Node A anchor bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("Node B predecessor must be a JSON object")
    if (
        document.get("contract_id") != PREDECESSOR_ID
        or document.get("captured_at") != PREDECESSOR_CAPTURED_AT
        or document.get("scope") != PREDECESSOR_SCOPE
        or document.get("status") != PREDECESSOR_STATUS
        or document.get("document_payload_sha256")
        != PREDECESSOR_PAYLOAD_SHA256
        or document_payload_sha256(document) != PREDECESSOR_PAYLOAD_SHA256
    ):
        raise AssertionError("Node B fixed Node A anchor identity drifted")
    embedded = document.get("predecessor", {})
    if (
        embedded.get("sha256") != NODE_A_CONTRACT_SHA256
        or embedded.get("document_payload_sha256")
        != NODE_A_CONTRACT_PAYLOAD_SHA256
        or embedded.get("byte_count") != NODE_A_CONTRACT_BYTE_COUNT
    ):
        raise AssertionError("Node B embedded Node A contract identity drifted")
    checkpoint = document.get("git_checkpoint", {})
    for key, expected in NODE_A_IMPLEMENTATION_CHECKPOINT.items():
        if checkpoint.get(key) != expected:
            raise AssertionError(
                f"Node B Node A implementation Git fact drifted: {key}"
            )
    authority = document.get("node_a_authority_anchor", {})
    if (
        authority.get("source_successor_path_count") != 42
        or authority.get("semantic_consumer_path_count") != 26
        or authority.get("fixed_source_count") != 72
        or authority.get("control_source_count") != 11
        or authority.get("source_successor_external_git_anchor_complete")
        is not True
        or authority.get("semantic_successor_external_git_anchor_complete")
        is not True
        or authority.get("bootstrap_control_sources_external_git_anchor_complete")
        is not True
    ):
        raise AssertionError("Node B Node A fixed authority summary drifted")
    authorization = document.get("authorization", {})
    if (
        authorization.get("migration_global_preflight_evidence_closed")
        is not True
        or authorization.get(
            "migration_durable_ledger_freeze_design_evidence_closed"
        )
        is not False
        or authorization.get("migration_design_closed") is not False
        or authorization.get("operator_migration_implementation") is not False
        or authorization.get("production_schema_or_index") is not False
        or authorization.get("real_data_migration_execution") is not False
        or authorization.get("production_cutover") is not False
    ):
        raise AssertionError("Node B Node A authorization boundary drifted")
    route = document.get("route_state", {})
    for key in (
        "migrated_operation_count",
        "pending_operation_count",
        "production_cutover_operation_count",
        "total_operation_count",
    ):
        if route.get(key) != ROUTE_STATE[key]:
            raise AssertionError(f"Node B Node A route fact drifted: {key}")
    return document


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    predecessor = load_predecessor(root)
    node_a_checkpoint = predecessor["git_checkpoint"]
    node_a_authority = predecessor["node_a_authority_anchor"]
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "scope": SCOPE,
        "status": STATUS,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "contract_id": PREDECESSOR_ID,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "scope": PREDECESSOR_SCOPE,
            "status": PREDECESSOR_STATUS,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "immutable": True,
            "node_a_contract": {
                "sha256": NODE_A_CONTRACT_SHA256,
                "byte_count": NODE_A_CONTRACT_BYTE_COUNT,
                "document_payload_sha256": NODE_A_CONTRACT_PAYLOAD_SHA256,
            },
        },
        "node_a_git_authority": {
            "implementation_checkpoint": deepcopy(
                NODE_A_IMPLEMENTATION_CHECKPOINT
            ),
            "implementation_checkpoint_exact_artifact_count": len(
                node_a_checkpoint["artifacts"]
            ),
            "source_successor_path_count": node_a_authority[
                "source_successor_path_count"
            ],
            "semantic_consumer_path_count": node_a_authority[
                "semantic_consumer_path_count"
            ],
            "fixed_source_count": node_a_authority["fixed_source_count"],
            "bootstrap_control_source_count": node_a_authority[
                "control_source_count"
            ],
            "external_anchor_checkpoint": deepcopy(
                NODE_A_EXTERNAL_ANCHOR_CHECKPOINT
            ),
            "live_head_or_ref_used": False,
            "ordinary_build_requires_git": False,
        },
        "durable_ledger_design": {
            "owner": "learning",
            "fixture_only": True,
            "production_relation_created": False,
            "flyway_migration_created": False,
            "migration_id_storage_type": "uuid",
            "arbitrary_text_migration_id_storable": False,
            "tables": {
                "ledger": "phase4c_tag_migration_design_ledger",
                "receipt": "phase4c_tag_migration_design_receipt",
                "target": "phase4c_tag_migration_design_target",
                "mutation_audit": "phase4c_tag_migration_design_mutation_audit",
                "statement_audit": "phase4c_tag_migration_design_statement_audit",
            },
            "state_machine": {
                "states": list(STATES),
                "initial_state": "PLANNED",
                "initial_version": 0,
                "terminal_states": ["APPLIED", "BLOCKED"],
                "transitions": list(TRANSITIONS),
                "compare_and_swap_predicate": [
                    "migration_id",
                    "expected_state",
                    "expected_version",
                    "migration_run_uuid",
                    "backup_manifest_sha256",
                    "cluster_database_identity_sha256",
                    "database_identity_sha256",
                    "preflight_digest_sha256",
                    "plan_digest_sha256",
                    "source_digest_sha256",
                    "target_digest_sha256",
                    "membership_digest_sha256",
                    "source_writer_stop_receipt_sha256",
                    "target_writer_stop_receipt_sha256",
                    "membership_writer_stop_receipt_sha256",
                    "restored_backup_sha256",
                ],
                "insert_requires_clean_planned_v0": True,
                "state_version_mapping_database_checked": True,
                "exactly_one_concurrent_winner": True,
                "state_and_version_advance_together": True,
                "identity_and_digest_columns_immutable": True,
                "created_at_immutable": True,
                "freeze_and_restore_digests_immutable_after_first_freeze": True,
                "illegal_transition_fails_closed": True,
                "applied_transition_immediate_complete_disposition_guard": True,
                "applied_transition_deferred_commit_guard": True,
                "zero_receipt_applied_transition_allowed": False,
                "unexplained_zero_target_applied_transition_allowed": False,
                "all_empty_noop_with_explicit_receipts_allowed": True,
                "blocked_code_allowlist": [
                    "DIGEST_DRIFT",
                    "RECEIPT_MISMATCH",
                    "TARGET_MISMATCH",
                    "IDENTITY_MISMATCH",
                    "ILLEGAL_STATE",
                ],
                "arbitrary_blocked_message_forbidden": True,
            },
            "receipt_protocol": {
                "append_only": True,
                "primary_key": ["migration_id", "source_row_id"],
                "receipt_inserted_before_target": True,
                "target_has_receipt_foreign_key": True,
                "receipt_source_row_has_source_foreign_key": True,
                "receipt_identity_and_digests_have_ledger_foreign_key": True,
                "receipt_freeze_restore_digests_have_ledger_foreign_key": True,
                "receipt_and_target_insert_require_applying": True,
                "deferred_commit_constraint_requires_applied": True,
                "deferred_commit_constraint_checks_target_count": True,
                "frozen_source_scope": "all_test_fixture_source_rows",
                "every_frozen_source_has_exactly_one_receipt": True,
                "empty_noop_requires_explicit_receipt": True,
                "empty_noop_requires_zero_target_rows": True,
                "material_disposition_requires_positive_target_rows": True,
                "receipt_target_and_applied_state_single_transaction": True,
                "receipt_first_replay": True,
                "exact_receipt_match_required": True,
                "receipt_mismatch_blocks": True,
                "confirmed_replay_business_dml": 0,
                "zero_row_or_on_conflict_dml_attempt_detected_by_statement_audit": True,
                "local_file_redis_or_user_progress_marker_allowed": False,
            },
            "target_fact_digest_protocol": {
                "domain_separator": (
                    "ti:phase4c:tag-migration:canonical-target-facts:v1"
                ),
                "canonical_inputs": ["distinct question_id", "tag_utf8"],
                "canonical_order": ["question_id_ascending", "tag_C_collation"],
                "field_encoding": "utf8_byte_length_prefix_then_value",
                "caller_supplied_target_fact_digest_column_present": False,
                "postgresql_recomputes_digest_from_canonical_facts": True,
                "applied_transition_compares_canonical_digest_to_ledger": True,
                "applied_transition_compares_canonical_digest_to_all_receipts": True,
                "java_recovery_independently_recomputes_canonical_digest": True,
                "wrong_facts_cannot_be_masked_by_caller_digest": True,
                "wrong_facts_transition_to_blocked_target_mismatch": True,
            },
            "database_identity": {
                "domain_separator": "ti:phase4c:tag-migration:run-identity:v1",
                "stored_as_sha256_only": True,
                "one_time_migration_run_uuid_required": True,
                "run_identity_inputs": [
                    "backup_manifest_sha256",
                    "migration_run_uuid",
                    "cluster_database_identity_sha256",
                ],
                "cluster_database_identity_domain_separator": (
                    "ti:phase4c:tag-migration:cluster-database:v1"
                ),
                "cluster_database_identity_inputs": [
                    "cluster_system_identifier",
                    "database_oid",
                    "server_version",
                    "server_address",
                    "server_port",
                ],
                "cluster_system_identifier_or_database_oid_stored_plain": False,
                "plain_database_name_or_user_stored": False,
                "ledger_receipt_and_fresh_recovery_identity_exact_match": True,
                "exact_match_required_for_cas_replay_and_ambiguity_recovery": True,
            },
        },
        "freeze_protocol_design": {
            "all_process_stop_required": [
                "legacy_web",
                "legacy_worker",
                "legacy_scheduler",
                "java_web",
                "java_worker",
                "java_scheduler",
            ],
            "all_existing_database_connections_drained_or_terminated": True,
            "new_connections_rejected_during_freeze": True,
            "backup_restored_into_new_isolated_target_database": True,
            "preflight_and_source_target_membership_digests_rechecked_after_restore": True,
            "freeze_receipts_bound_to_database_identity_and_backup_digest": True,
            "old_runtime_must_never_restart_after_applying_begins": True,
            "java_advisory_lock_is_only_cooperative_coordination": True,
            "legacy_writer_snapshots": deepcopy(LEGACY_WRITER_SNAPSHOTS),
            "legacy_writers_take_java_advisory_lock": False,
            "advisory_lock_alone_is_freeze_evidence": False,
            "production_source_write_freeze_evidenced": False,
            "production_target_write_freeze_evidenced": False,
            "production_membership_write_freeze_or_digest_recheck_evidenced": False,
            "production_connection_drain_evidenced": False,
            "production_backup_restore_evidenced": False,
        },
        "retry_and_ambiguity_design": {
            "retryable_sqlstates": list(RETRYABLE_SQLSTATES),
            "maximum_attempts": 3,
            "maximum_retries": 2,
            "fresh_transaction_per_attempt": True,
            "non_retryable_sqlstate_attempts": 1,
            "non_retryable_sqlstate_retries": 0,
            "unknown_or_missing_sqlstate_fails_closed": True,
            "real_postgresql_40001_evidenced": True,
            "real_postgresql_40P01_evidenced": True,
            "real_postgresql_40001_traversed_retry_loop": True,
            "real_postgresql_40P01_traversed_retry_loop": True,
            "ack_discard_after_commit_fixture_evidenced": True,
            "ack_discard_fixture_is_real_network_failure": False,
            "real_network_commit_ack_loss_evidenced": False,
            "ambiguous_commit_confirmation_requires": [
                "exact_receipt",
                "matching_one_time_migration_run_uuid",
                "matching_backup_manifest_sha256",
                "matching_cluster_database_identity_sha256",
                "matching_database_identity_sha256",
                "matching_target_digest_sha256",
                "independently_recomputed_canonical_question_tag_digest",
                "complete_disposition_receipt_set",
                "ledger_state_APPLIED",
            ],
            "ambiguous_commit_confirmation_business_dml": 0,
            "any_mismatch_blocks_without_retrying_apply": True,
            "production_retry_implementation_present": False,
        },
        "acl_and_sensitive_material_design": {
            "fixture_role": "ti_phase4c_tag_design_operator",
            "fixture_role_login": False,
            "fixture_role_password_or_connect_grant": False,
            "fixture_role_direct_connect_grant": False,
            "public_connect_revoked_in_disposable_database": True,
            "fixture_role_effective_connect_privilege": False,
            "fixture_uses_owner_connection_then_set_role": True,
            "fixture_role_superuser": False,
            "fixture_role_createdb": False,
            "fixture_role_createrole": False,
            "fixture_role_bypassrls": False,
            "fixture_role_create_schema_or_table": False,
            "source_select_only": True,
            "ledger_select_insert_update_only": True,
            "receipt_select_insert_only": True,
            "target_select_insert_only": True,
            "mutation_audit_not_visible_to_fixture_role": True,
            "statement_audit_not_visible_to_fixture_role": True,
            "receipt_update_or_delete_rejected": True,
            "legacy_key_raw_payload_tag_secret_or_credential_in_ledger": False,
            "legacy_key_raw_payload_tag_secret_or_credential_in_receipt": False,
            "sensitive_canary_present_only_in_test_source_fixture": True,
            "sensitive_canary_absent_from_contract_payload": True,
            "sensitive_canary_absent_from_ledger_receipt_and_mutation_audit": True,
            "sensitive_canary_rejected_as_uuid_migration_id": True,
            "mutation_audit_migration_id_storage_type": "uuid",
        },
        "evidence": {
            "classification": (
                "test-only PostgreSQL design evidence; no production connection, "
                "schema, freeze or migration"
            ),
            "postgresql_versions": ["16.14", "18.4"],
            "container_images_fixed_by_phase2": True,
            "integration_test_class": (
                "io.saksk.ti.integration."
                "Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT"
            ),
            "integration_test_methods": [
                "durableLedgerFreezeDesignEvidenceHoldsOnPostgres16",
                "durableLedgerFreezeDesignEvidenceHoldsOnPostgres18",
            ],
            "java_contract_parity_loaded_from_same_integration_test": True,
            "independent_java_acceptance_claimed": False,
            "cas_state_machine_and_illegal_transition": True,
            "concurrent_cas_one_winner_one_loser": True,
            "receipt_target_state_atomic_commit_and_rollback": True,
            "complete_disposition_set_guarded_on_applied_transition": True,
            "explicit_empty_noop_receipt_for_canary_source": True,
            "canonical_target_digest_postgresql_java_parity": True,
            "wrong_target_fact_and_digest_masking_blocked": True,
            "receipt_first_replay_zero_business_dml": True,
            "actual_40001_and_40P01_from_postgresql": True,
            "actual_40001_and_40P01_traverse_bounded_retry_loop": True,
            "only_40001_40P01_bounded_retry_classifier": True,
            "ack_discard_fixture_ambiguity_recovery": True,
            "ack_discard_fixture_real_network": False,
            "restricted_role_acl": True,
            "public_connect_effective_privilege_removed": True,
            "sensitive_canary_exclusion": True,
            "database_identity_digest": True,
            "production_database_connected": False,
            "production_credentials_read": False,
            "production_data_read_or_mutated": False,
            "production_operator_executed": False,
            "user_compose_or_production_docker_mutated": False,
        },
        "authorization": {
            "newly_closed_gates": [
                "migration_durable_ledger_freeze_design_evidence_closed"
            ],
            "migration_global_preflight_evidence_closed": True,
            "migration_durable_ledger_freeze_design_evidence_closed": True,
            "migration_design_closed": False,
            "production_durable_ledger_or_tombstone": False,
            "production_source_write_freeze_evidence_closed": False,
            "production_target_write_freeze_evidence_closed": False,
            "production_membership_write_freeze_or_digest_recheck_evidence_closed": False,
            "production_connection_drain_evidence_closed": False,
            "bounded_40001_40P01_retry_implemented": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "flyway_baseline_or_migration": False,
            "backup_and_rollback_evidence_closed": False,
            "real_data_migration_execution": False,
            "legacy_runtime_permanently_disabled": False,
            "route_or_openapi_delta": False,
            "client_gateway_or_proxy_change": False,
            "production_cutover": False,
            "source_successor_external_git_anchor_complete": True,
            "semantic_successor_external_git_anchor_complete": True,
            "bootstrap_control_sources_external_git_anchor_complete": True,
            "current_node_control_sources_external_git_anchor_complete": False,
        },
        "route_state": deepcopy(ROUTE_STATE),
        "source_authority": {
            "fixed_source_count": len(FIXED_SOURCE_ALLOWLIST),
            "fixed_source_allowlist": list(FIXED_SOURCE_ALLOWLIST),
            "fixed_sources": {
                PREDECESSOR_RELATIVE: {
                    "sha256": PREDECESSOR_SHA256,
                    "byte_count": PREDECESSOR_BYTE_COUNT,
                    "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
                }
            },
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "fixed_source_allowlist_exact": True,
            "dynamic_source_discovery": False,
            "ordinary_build_and_load_are_gitless": True,
            "live_head_or_ref_authority": False,
            "unknown_source": "reject",
            "absolute_parent_escape_or_symlink": "reject",
            "historical_contract_overwrite": False,
        },
        "next_gate": {
            "required_next": (
                "implement an explicitly authorized production ledger/schema and "
                "Operator, then prove real all-process freeze, connection drain, "
                "restored-backup identity, bounded retry, backup/rollback and apply"
            ),
            "production_execution_requires_explicit_user_authorization": True,
            "node_b_design_evidence_is_apply_authorization": False,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    payload = serialized_contract(build_contract())
    if arguments.write:
        arguments.output.write_bytes(payload)
    else:
        print(payload.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
