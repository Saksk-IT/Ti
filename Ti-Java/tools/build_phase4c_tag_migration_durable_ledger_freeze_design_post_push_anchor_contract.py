#!/usr/bin/env python3
"""Build the fixed post-push Git anchor for Phase 4C tag-migration Node B."""

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
    "docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-"
    "freeze-design-post-push-anchor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE

CONTRACT_ID = (
    "ti.phase4c.personal-bank-tag-migration-durable-ledger-freeze-design-"
    "post-push-anchor-contract"
)
CAPTURED_AT = "2026-07-19T13:33:45+08:00"
STATUS = (
    "durable_ledger_freeze_design_checkpoint_externally_anchored_"
    "production_schema_operator_apply_backup_and_cutover_unauthorized"
)
SCOPE = (
    "phase4c-personal-bank-tag-migration-durable-ledger-freeze-design-"
    "post-push-external-anchor"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-"
    "freeze-design-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-durable-ledger-freeze-design-"
    "contract"
)
PREDECESSOR_CAPTURED_AT = "2026-07-19T13:20:00+08:00"
PREDECESSOR_STATUS = (
    "durable_ledger_freeze_design_test_evidence_closed_production_freeze_"
    "schema_operator_apply_backup_and_cutover_unauthorized"
)
PREDECESSOR_SCOPE = (
    "phase4c-learning-owned-tag-migration-durable-ledger-freeze-design"
)
PREDECESSOR_SHA256 = (
    "995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "fba73f917a285b85cb8fcd7afd22a94f60bac960beb508f173caf0ea96079ffa"
)
PREDECESSOR_BYTE_COUNT = 23_110

NODE_A_ANCHOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-global-preflight-"
    "post-push-anchor-contract.json"
)
NODE_A_ANCHOR_SHA256 = (
    "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3"
)
NODE_A_ANCHOR_PAYLOAD_SHA256 = (
    "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e"
)
NODE_A_ANCHOR_BYTE_COUNT = 66_318
NODE_A_ANCHOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-global-preflight-"
    "post-push-anchor-contract"
)
NODE_A_ANCHOR_CAPTURED_AT = "2026-07-19T11:15:25+08:00"
NODE_A_EXTERNAL_ANCHOR_COMMIT = (
    "345deff63d2d3e867926f1e0d05d5e6d90885c4a"
)
NODE_A_EXTERNAL_CONTROL_SOURCES = (
    NODE_A_ANCHOR_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightPostPushAnchorContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance.java",
    "tools/build_phase4c_tag_migration_global_preflight_"
    "post_push_anchor_contract.py",
    "tools/phase4c_tag_migration_global_preflight_"
    "post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_global_preflight_"
    "post_push_anchor_contract.py",
)

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "ea894b3a02787a91b688d7295cace37139f7f486"
GIT_PARENT_OID = "345deff63d2d3e867926f1e0d05d5e6d90885c4a"
GIT_ROOT_TREE_OID = "57cfc3b195600b38a73e09673267143de346474d"
GIT_PARENT_ROOT_TREE_OID = "a59ee94d6cf533555d5d853ef11fa39e7612a22b"
GIT_TI_JAVA_TREE_OID = "cd5de2cb7f73400cd3d3fe2aa2d7bf48db21a3c8"
GIT_PARENT_TI_JAVA_TREE_OID = "87da31003c4d545762bac2a0de12ef4712300f04"
GIT_SERVER_TREE_OID = "fd7ccc66962e691eaaadc31e3dad409dbe392273"
GIT_PARENT_SERVER_TREE_OID = "4749b6ab453516ff7ca060d59d3759ffd2da6d6b"
GIT_SERVER_SRC_MAIN_TREE_OID = "21fe4902d57a11998502e63041b5a56fb039a090"
GIT_PARENT_SERVER_SRC_MAIN_TREE_OID = GIT_SERVER_SRC_MAIN_TREE_OID
GIT_WEB_TREE_OID = "a75f69a8205a56843feb055656ddb015ec5b5215"
GIT_PARENT_WEB_TREE_OID = GIT_WEB_TREE_OID
GIT_AUTHORED_AT = "2026-07-19T13:31:09+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "test(java): close tag migration ledger freeze design"
GIT_RAW_DELTA_SHA256 = (
    "a064ee789e91a047a1727deb181f7512408db66e822849e4145d35213ff6abbb"
)
GIT_NUMSTAT_SHA256 = (
    "21c2cb87a853bd1d702209f2868dd398b3798e53cdf94f9d3aa13f83cb70de04"
)
GIT_INSERTED_LINE_COUNT = 5_362
GIT_DELETED_LINE_COUNT = 0
CHECKPOINT_TOTAL_BYTES = 233_639

# ti-java-relative|blob-oid|sha256|bytes|insertions. The allowlist is fixed in
# code; neither ordinary construction nor Git replay discovers paths.
_CHECKPOINT_ROWS = r"""
docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-freeze-design-contract.json|6eccdd897ff9b14735e5aa3f91774b7f704f1174|995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041|23110|510
docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-freeze-design.md|aee5f4d29cd33249690fed378bcf4ec005e8b230|8a220b44b9d08cde628e5bb33e599ae58bbbce8adbc6c32961da3b17535d2b4e|9656|153
server/src/test/java/io/saksk/ti/integration/Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT.java|f0090b18ed3bb9aa3559434444337532cfd96a20|7131f32bbdd69e61876908fcc6ce5fa6eb87ff682e241d279192f876b1969124|103360|2333
server/src/test/resources/db/phase4c/074-legacy-personal-bank-tag-durable-ledger-freeze-design-schema.sql|57abe91aee7261e46bc7d1ac0c3df62ed210bde2|544cc31e81b77466ac491192534a8b0e4bab40933d2f71bb39096ea5441a3147|27251|792
server/src/test/resources/db/phase4c/075-legacy-personal-bank-tag-durable-ledger-freeze-design-seed.sql|16d0c701d5ebdeb9cdfb14f9dc86790beba2ab0a|6818a460dc1d860dc246df4d5106d398f18b2c2198bafdf297fefdd01b78738c|872|30
tools/build_phase4c_tag_migration_durable_ledger_freeze_design_contract.py|7bd549e10bcea029e4490e0d3bf7067cd2dda884|5431e95dbbf2107be6174c772f44d18418afb5703362982974c3dfdba6320054|39397|916
tools/phase4c_tag_migration_durable_ledger_freeze_design_successor_acceptance.py|1ccf0aac9ca8c036dcde517efc8927397b3ef737|3786c17b48cc1225c66fa5f618e3843430fc283af96e4fcd142dbf64968a527d|9656|212
tools/test_phase4c_tag_migration_durable_ledger_freeze_design_contract.py|59fe0e9ec082dbc8c931b8e4a415b5cebc793034|3ba4ee246d266c8a25890acc158640cbaf4405666de2f89837c9bbad9c3a2363|20337|416
""".strip()


def _checkpoint_changes() -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for row in _CHECKPOINT_ROWS.splitlines():
        relative, oid, sha256, byte_count, insertions = row.split("|")
        changes[relative] = {
            "repository_path": f"Ti-Java/{relative}",
            "ti_java_relative_path": relative,
            "change_type": "A",
            "previous_mode": "000000",
            "mode": "100644",
            "previous_git_blob_oid": "0" * 40,
            "git_blob_oid": oid,
            "object_type": "blob",
            "sha256": sha256,
            "byte_count": int(byte_count),
            "inserted_line_count": int(insertions),
            "deleted_line_count": 0,
        }
    return changes


CHECKPOINT_CHANGES = _checkpoint_changes()
CHECKPOINT_PATHS = tuple(CHECKPOINT_CHANGES)

CURRENT_CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
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
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    payload = deepcopy(document)
    payload.pop("document_payload_sha256", None)
    return sha256_json(payload)


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (canonical_json(document) + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    if relative.startswith("/") or relative not in {
        PREDECESSOR_RELATIVE, NODE_A_ANCHOR_RELATIVE, OUTPUT_RELATIVE
    }:
        raise AssertionError("Node B anchor unknown or absolute source")
    base = root.resolve(strict=True)
    candidate = base / relative
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AssertionError("Node B anchor fixed source missing") from error
    if not resolved.is_relative_to(base) or candidate.is_symlink():
        raise AssertionError("Node B anchor source escaped or is a symlink")
    if not resolved.is_file():
        raise AssertionError("Node B anchor source is not a regular file")
    return resolved


def _read_fixed_predecessor(root: Path) -> dict[str, Any]:
    payload = fixed_regular_file(root, PREDECESSOR_RELATIVE).read_bytes()
    if (
        len(payload) != PREDECESSOR_BYTE_COUNT
        or sha256_bytes(payload) != PREDECESSOR_SHA256
    ):
        raise AssertionError("Node B anchor predecessor physical bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("Node B anchor predecessor must be an object")
    if (
        document.get("contract_id") != PREDECESSOR_ID
        or document.get("captured_at") != PREDECESSOR_CAPTURED_AT
        or document.get("status") != PREDECESSOR_STATUS
        or document.get("scope") != PREDECESSOR_SCOPE
        or document.get("document_payload_sha256")
        != PREDECESSOR_PAYLOAD_SHA256
        or document_payload_sha256(document) != PREDECESSOR_PAYLOAD_SHA256
    ):
        raise AssertionError("Node B anchor predecessor identity drifted")
    _validate_predecessor_authority(document)
    return document


def _read_fixed_node_a_anchor(root: Path) -> dict[str, Any]:
    payload = fixed_regular_file(root, NODE_A_ANCHOR_RELATIVE).read_bytes()
    if (
        len(payload) != NODE_A_ANCHOR_BYTE_COUNT
        or sha256_bytes(payload) != NODE_A_ANCHOR_SHA256
    ):
        raise AssertionError("Node B anchor transitive Node A bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("Node B anchor transitive Node A must be an object")
    if (
        document.get("contract_id") != NODE_A_ANCHOR_ID
        or document.get("captured_at") != NODE_A_ANCHOR_CAPTURED_AT
        or document.get("document_payload_sha256")
        != NODE_A_ANCHOR_PAYLOAD_SHA256
        or document_payload_sha256(document) != NODE_A_ANCHOR_PAYLOAD_SHA256
        or document.get("authorization", {}).get(
            "migration_global_preflight_evidence_closed"
        )
        is not True
        or document.get("authorization", {}).get(
            "migration_durable_ledger_freeze_design_evidence_closed"
        )
        is not False
        or document.get("route_state") != ROUTE_STATE
    ):
        raise AssertionError("Node B anchor transitive Node A identity drifted")
    return document


def _validate_predecessor_authority(document: dict[str, Any]) -> None:
    source = document.get("source_authority", {})
    authorization = document.get("authorization", {})
    predecessor = document.get("predecessor", {})
    node_a_authority = document.get("node_a_git_authority", {})
    node_a_external = node_a_authority.get("external_anchor_checkpoint", {})
    if (
        tuple(source.get("control_sources", ())) != CHECKPOINT_PATHS
        or source.get("control_source_count") != 8
        or source.get("control_sources_excluded_from_self_authority") is not True
        or source.get("control_sources_external_git_anchor_complete") is not False
        or source.get("dynamic_source_discovery") is not False
        or source.get("ordinary_build_and_load_are_gitless") is not True
        or source.get("live_head_or_ref_authority") is not False
    ):
        raise AssertionError("Node B anchor predecessor control authority drifted")
    if (
        predecessor.get("source") != NODE_A_ANCHOR_RELATIVE
        or predecessor.get("sha256") != NODE_A_ANCHOR_SHA256
        or predecessor.get("byte_count") != NODE_A_ANCHOR_BYTE_COUNT
        or predecessor.get("document_payload_sha256")
        != NODE_A_ANCHOR_PAYLOAD_SHA256
    ):
        raise AssertionError("Node B anchor Node A predecessor drifted")
    if (
        node_a_external.get("commit_oid") != NODE_A_EXTERNAL_ANCHOR_COMMIT
        or node_a_external.get("parent_oid")
        != "256d5b347e2e5266eef084221807337427ceb16f"
        or node_a_external.get("changed_path_count") != 6
        or node_a_external.get("added_count") != 6
        or node_a_external.get("modified_count") != 0
        or node_a_external.get("deleted_count") != 0
        or tuple(node_a_external.get("artifacts", {}))
        != NODE_A_EXTERNAL_CONTROL_SOURCES
        or node_a_external.get("artifacts", {}).get(
            NODE_A_ANCHOR_RELATIVE, {}
        ).get("sha256")
        != NODE_A_ANCHOR_SHA256
        or node_a_external.get("artifacts", {}).get(
            NODE_A_ANCHOR_RELATIVE, {}
        ).get("byte_count")
        != NODE_A_ANCHOR_BYTE_COUNT
        or node_a_authority.get("ordinary_build_requires_git") is not False
        or node_a_authority.get("live_head_or_ref_used") is not False
    ):
        raise AssertionError("Node B anchor Node A external authority drifted")
    if (
        authorization.get("newly_closed_gates")
        != ["migration_durable_ledger_freeze_design_evidence_closed"]
        or authorization.get("migration_global_preflight_evidence_closed")
        is not True
        or authorization.get(
            "migration_durable_ledger_freeze_design_evidence_closed"
        )
        is not True
        or authorization.get("source_successor_external_git_anchor_complete")
        is not True
        or authorization.get("semantic_successor_external_git_anchor_complete")
        is not True
        or authorization.get(
            "bootstrap_control_sources_external_git_anchor_complete"
        )
        is not True
        or any(authorization.get(field) is not False
               for field in PRODUCTION_FALSE_FIELDS)
        or document.get("route_state") != ROUTE_STATE
    ):
        raise AssertionError("Node B anchor authorization/route boundary drifted")


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("Node B anchor live/ref Git authority is forbidden")
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
        raise AssertionError("Node B anchor read-only Git replay failed") from error
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def _expected_raw_delta() -> list[str]:
    return [
        f":{item['previous_mode']} {item['mode']} "
        f"{item['previous_git_blob_oid']} {item['git_blob_oid']} "
        f"{item['change_type']}\t{item['repository_path']}"
        for item in CHECKPOINT_CHANGES.values()
    ]


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("Node B anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("Node B anchor Git object format drifted")
    if (
        _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit"
        or _git_text(root, "rev-parse", "--verify", f"{GIT_COMMIT_OID}^{{commit}}")
        != GIT_COMMIT_OID
    ):
        raise AssertionError("Node B anchor commit object drifted")
    facts = _git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", GIT_COMMIT_OID
    ).splitlines()
    if facts != [
        GIT_ROOT_TREE_OID,
        GIT_PARENT_OID,
        GIT_AUTHORED_AT,
        GIT_COMMITTED_AT,
        GIT_SUBJECT,
    ]:
        raise AssertionError("Node B anchor commit identity/unique parent drifted")
    trees = {
        "Ti-Java": GIT_TI_JAVA_TREE_OID,
        "Ti-Java/server": GIT_SERVER_TREE_OID,
        "Ti-Java/server/src/main": GIT_SERVER_SRC_MAIN_TREE_OID,
        "Ti-Java/web": GIT_WEB_TREE_OID,
    }
    parent_trees = {
        "Ti-Java": GIT_PARENT_TI_JAVA_TREE_OID,
        "Ti-Java/server": GIT_PARENT_SERVER_TREE_OID,
        "Ti-Java/server/src/main": GIT_PARENT_SERVER_SRC_MAIN_TREE_OID,
        "Ti-Java/web": GIT_PARENT_WEB_TREE_OID,
    }
    if _git_text(root, "show", "-s", "--format=%T", GIT_PARENT_OID) \
            != GIT_PARENT_ROOT_TREE_OID:
        raise AssertionError("Node B anchor parent root tree drifted")
    for relative, expected in trees.items():
        if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:{relative}") \
                != expected:
            raise AssertionError(f"Node B anchor tree drifted: {relative}")
    for relative, expected in parent_trees.items():
        if _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:{relative}") \
                != expected:
            raise AssertionError(f"Node B anchor parent tree drifted: {relative}")
    if (
        GIT_SERVER_TREE_OID == GIT_PARENT_SERVER_TREE_OID
        or GIT_SERVER_SRC_MAIN_TREE_OID != GIT_PARENT_SERVER_SRC_MAIN_TREE_OID
        or GIT_WEB_TREE_OID != GIT_PARENT_WEB_TREE_OID
    ):
        raise AssertionError("Node B anchor production tree boundary drifted")
    raw = _run_git(
        root, "diff-tree", "--no-commit-id", "--raw", "--abbrev=40", "-r",
        GIT_COMMIT_OID,
    )
    if (
        sha256_bytes(raw) != GIT_RAW_DELTA_SHA256
        or raw.decode("utf-8").splitlines() != _expected_raw_delta()
    ):
        raise AssertionError("Node B anchor exact eight-path raw delta drifted")
    numstat_raw = _run_git(
        root, "diff-tree", "--no-commit-id", "--numstat", "-r", GIT_COMMIT_OID
    )
    if sha256_bytes(numstat_raw) != GIT_NUMSTAT_SHA256:
        raise AssertionError("Node B anchor raw numstat drifted")
    parsed = [line.split("\t", 2)
              for line in numstat_raw.decode("utf-8").splitlines()]
    expected_numstat = [
        [str(item["inserted_line_count"]), "0", item["repository_path"]]
        for item in CHECKPOINT_CHANGES.values()
    ]
    if parsed != expected_numstat:
        raise AssertionError("Node B anchor exact numstat rows drifted")
    total_bytes = 0
    for relative, item in CHECKPOINT_CHANGES.items():
        if _git_text(
            root, "rev-parse", f"{GIT_COMMIT_OID}:{item['repository_path']}"
        ) != item["git_blob_oid"]:
            raise AssertionError(f"Node B anchor tree blob drifted: {relative}")
        if _run_git(
            root, "ls-tree", GIT_PARENT_OID, "--", item["repository_path"]
        ):
            raise AssertionError(f"Node B anchor added path existed in parent: {relative}")
        payload = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (
            len(payload) != item["byte_count"]
            or sha256_bytes(payload) != item["sha256"]
        ):
            raise AssertionError(f"Node B anchor Git blob drifted: {relative}")
        total_bytes += len(payload)
    if (
        len(CHECKPOINT_CHANGES) != 8
        or any(not item["repository_path"].startswith("Ti-Java/")
               for item in CHECKPOINT_CHANGES.values())
        or sum(item["inserted_line_count"]
               for item in CHECKPOINT_CHANGES.values())
        != GIT_INSERTED_LINE_COUNT
        or sum(item["deleted_line_count"]
               for item in CHECKPOINT_CHANGES.values())
        != GIT_DELETED_LINE_COUNT
        or total_bytes != CHECKPOINT_TOTAL_BYTES
    ):
        raise AssertionError("Node B anchor aggregate boundary drifted")


def build_contract(
    ti_java_root: Path = ROOT,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    predecessor = _read_fixed_predecessor(root)
    node_a_anchor = _read_fixed_node_a_anchor(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)
    control_sources = predecessor["source_authority"]["control_sources"]
    artifacts = deepcopy(CHECKPOINT_CHANGES)
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": STATUS,
        "scope": SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "contract_id": PREDECESSOR_ID,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "status": PREDECESSOR_STATUS,
            "scope": PREDECESSOR_SCOPE,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "immutable": True,
        },
        "git_checkpoint": {
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
            "parent_server_src_main_tree_oid":
                GIT_PARENT_SERVER_SRC_MAIN_TREE_OID,
            "web_tree_oid": GIT_WEB_TREE_OID,
            "parent_web_tree_oid": GIT_PARENT_WEB_TREE_OID,
            "server_src_main_tree_unchanged_from_parent": True,
            "web_tree_unchanged_from_parent": True,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_COMMITTED_AT,
            "subject": GIT_SUBJECT,
            "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
            "numstat_sha256": GIT_NUMSTAT_SHA256,
            "changed_path_count": 8,
            "added_count": 8,
            "modified_count": 0,
            "deleted_count": 0,
            "non_ti_java_count": 0,
            "inserted_line_count": GIT_INSERTED_LINE_COUNT,
            "deleted_line_count": GIT_DELETED_LINE_COUNT,
            "current_total_bytes": CHECKPOINT_TOTAL_BYTES,
            "exact_eight_added_path_delta": True,
            "artifacts": artifacts,
        },
        "node_b_control_source_anchor": {
            "control_sources": list(control_sources),
            "control_source_count": 8,
            "control_source_allowlist_exact": True,
            "control_source_path_manifest_sha256": sha256_json(control_sources),
            "control_source_blob_manifest_sha256": sha256_json(artifacts),
            "all_controls_are_exact_commit_delta_blobs": True,
            "all_controls_absent_from_parent": True,
            "predecessor_control_sources_external_git_anchor_complete": True,
            "ordinary_build_and_load_are_gitless": True,
            "explicit_fixed_commit_git_replay_available": True,
            "dynamic_source_discovery_forbidden": True,
            "live_head_or_ref_authority_forbidden": True,
        },
        "transitive_node_a_anchor": {
            "source": NODE_A_ANCHOR_RELATIVE,
            "contract_id": NODE_A_ANCHOR_ID,
            "captured_at": NODE_A_ANCHOR_CAPTURED_AT,
            "sha256": NODE_A_ANCHOR_SHA256,
            "byte_count": NODE_A_ANCHOR_BYTE_COUNT,
            "document_payload_sha256": NODE_A_ANCHOR_PAYLOAD_SHA256,
            "implementation_checkpoint_commit_oid": node_a_anchor[
                "git_checkpoint"
            ]["commit_oid"],
            "external_anchor_checkpoint_commit_oid":
                NODE_A_EXTERNAL_ANCHOR_COMMIT,
            "external_anchor_control_sources":
                list(NODE_A_EXTERNAL_CONTROL_SOURCES),
            "external_anchor_artifacts": deepcopy(
                predecessor["node_a_git_authority"]
                ["external_anchor_checkpoint"]["artifacts"]
            ),
            "external_anchor_artifact_count": 6,
            "immutable": True,
        },
        "inherited_evidence_and_authorization": {
            "migration_global_preflight_evidence_closed": True,
            "migration_durable_ledger_freeze_design_evidence_closed": True,
            "source_successor_external_git_anchor_complete": True,
            "semantic_successor_external_git_anchor_complete": True,
            "bootstrap_control_sources_external_git_anchor_complete": True,
            "node_b_control_sources_external_git_anchor_complete": True,
            **{field: False for field in PRODUCTION_FALSE_FIELDS},
        },
        "route_state": deepcopy(ROUTE_STATE),
        "production_boundary": {
            "checkpoint_contains_only_docs_tests_and_tools": True,
            "server_src_main_tree_unchanged_from_parent": True,
            "web_tree_unchanged_from_parent": True,
            "production_schema_or_index_added": False,
            "operator_or_apply_entrypoint_added": False,
            "production_connection_or_credentials_used": False,
            "production_data_read_or_mutated": False,
            "user_compose_or_production_docker_mutated": False,
        },
        "current_node_trust_boundary": {
            "control_sources": list(CURRENT_CONTROL_SOURCES),
            "control_source_count": 6,
            "control_source_allowlist_exact": True,
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "tamper_evident_scope": (
                "fixed_node_b_predecessor_commit_tree_delta_and_eight_blobs"
            ),
        },
        "acceptance": {
            "anchor_closes_no_functional_gate": True,
            "checkpoint_changed_path_count": 8,
            "checkpoint_added_count": 8,
            "checkpoint_modified_count": 0,
            "checkpoint_deleted_count": 0,
            "node_b_control_source_count": 8,
            "current_control_source_count": 6,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "migration_design_closed": False,
            "production_cutover": False,
            "next_gate": (
                "production ledger/schema and operator implementation evidence"
            ),
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path, default=ROOT.parent)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-git-replay", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    document = build_contract(
        arguments.ti_java_root,
        repository_root=(None if arguments.skip_git_replay
                         else arguments.repository_root),
    )
    payload = serialized_contract(document)
    if arguments.check:
        if arguments.output.read_bytes() != payload:
            raise AssertionError("Node B post-push anchor contract drifted")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_bytes(payload)
    print(f"Node B post-push anchor passed: {sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
