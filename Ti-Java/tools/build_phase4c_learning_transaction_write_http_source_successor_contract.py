#!/usr/bin/env python3
"""Build the transaction-write source/runtime successor bootstrap.

This node externally fixes the preceding full-parity bootstrap commit and
composes its reviewed source transitions with the current production runtime
and ten-node WORM.  Bridge sources changed by this node remain self-excluded
until the next post-push anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

try:
    from tools import phase4c_learning_transaction_write_http_integration_successor as integration
    from tools import build_phase4c_learning_transaction_write_http_full_parity_contract as predecessor
    from tools import build_phase4c_tag_migration_execution_protocol_contract as node_d
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_learning_transaction_write_http_full_parity_contract",
        "tools.build_phase4c_tag_migration_execution_protocol_contract",
    }:
        raise
    import build_phase4c_learning_transaction_write_http_full_parity_contract as predecessor
    import phase4c_learning_transaction_write_http_integration_successor as integration
    import build_phase4c_tag_migration_execution_protocol_contract as node_d


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "learning-transaction-write-http-source-successor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
CONTRACT_ID = "ti.phase4c.learning-transaction-write-http-source-successor-contract"
CAPTURED_AT = "2026-07-24T17:05:00+08:00"
STATUS = (
    "full_parity_bootstrap_externally_anchored_runtime_and_worm_successor_"
    "closed_current_bridge_anchor_pending_routes_pending"
)

PREDECESSOR = {
    "source": predecessor.OUTPUT_RELATIVE,
    "contract_id": predecessor.CONTRACT_ID,
    "sha256": "40b38a443d7f7d754cc42ce43fa854b0c3c18dc66f4920a2f07d451601d6d1db",
    "document_payload_sha256": (
        "83ca7d51d768540ed744830c74f07eb1fd1f63db88c293ea4ec83e41d6a6c1e1"
    ),
    "byte_count": 15_604,
}
BOOTSTRAP_CHECKPOINT = {
    "commit_oid": "6ed81347467a4155887300b7e4ae36589204af79",
    "parent_commit_oid": "b635d1db3b9d71698d9a40cc729a215d67a6906f",
    "root_tree_oid": "74115f3c94ccab64da81be5ae8c8109bb3ec0034",
    "ti_java_tree_oid": "f43ea25fe0d86855df0563f3cf5a3853b3791d01",
    "committed_at": "2026-07-24T16:50:36+08:00",
    "subject": "test(java): close transaction write full parity",
}
BOOTSTRAP_CONTROL_SOURCES: dict[str, dict[str, Any]] = {
    predecessor.OUTPUT_RELATIVE: {
        "sha256": "40b38a443d7f7d754cc42ce43fa854b0c3c18dc66f4920a2f07d451601d6d1db",
        "byte_count": 15_604,
        "git_blob_oid": "b13b9d8dd770464f61a0f76d46a500239f5535bc",
    },
    "server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.java": {
        "sha256": "b54f0e04ace4a101d06832fdb99f412a83ce0ee2c9a12aeded482c2c8ebdadbb",
        "byte_count": 25_784,
        "git_blob_oid": "728c6bfd5b03b8c308a0c66d03a001abde0a6c9e",
    },
    "server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParityContractParityTest.java": {
        "sha256": "24f587dda5a78ce19003eb062b3279150cdc71c5c8f4751a977819aadd8eb5a1",
        "byte_count": 5_313,
        "git_blob_oid": "2c446524e99e6510e867ac3a1f7594025ab2016e",
    },
    "tools/build_phase4c_learning_transaction_write_http_full_parity_contract.py": {
        "sha256": "e34df1686912e5eb40be9380f79420963ec3dd270053f4f1afc92b934f422c41",
        "byte_count": 24_262,
        "git_blob_oid": "93e1e37da95bca8252b0c19203397bb14910761d",
    },
    "tools/phase4c_learning_transaction_write_http_full_parity_successor_acceptance.py": {
        "sha256": "146ffdb8b82b33a9cab9a52eac4a0ce14a46254175bf7207ab4ab5c4a3bd4c95",
        "byte_count": 11_098,
        "git_blob_oid": "bf99128d2395632c4eb43e93f084420ed675623b",
    },
    "tools/test_phase4c_learning_transaction_write_http_full_parity_contract.py": {
        "sha256": "b44fd3a871253e9a826379b09c1d4c4e3f6bd8353d83af2c3281f328b5bcc536",
        "byte_count": 4_957,
        "git_blob_oid": "265bcb7add6f63fe7c1e34c1b954d34866baa7fa",
    },
    "tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py": {
        "sha256": "0119bedfa3e0298aa1f9019d8ec8e20995e0b49058a360763d209759a444929d",
        "byte_count": 23_894,
        "git_blob_oid": "39ee69e0dbaf3a9d1429e0aed70166e550da6e22",
    },
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java": {
        "sha256": "ba719c5ca08453c22696ff7a3e316936a937371830620a405fdcca424e6afb9a",
        "byte_count": 53_120,
        "git_blob_oid": "777841196e7c1eb28931ffcba902f86f8241731a",
    },
}

FULL_RUNTIME = {
    "accepted_file_count": 311,
    "accepted_manifest_sha256": (
        "053ffc0a6a6ecc02ffb7cd2a8545af339bef35ffd502dcdbfbc0de8b11977d4a"
    ),
    "current_file_count": 395,
    "current_manifest_sha256": (
        "d90cdbfe0da59544f44e859488c1a3df602857c53d7f082fe5bc9166464b3045"
    ),
    "added_file_count": 84,
    "changed_file_count": 10,
    "deleted_file_count": 0,
}
LEARNING_PERSONALBANK_MAIN = {
    "accepted_file_count": 54,
    "accepted_manifest_sha256": (
        "66e7874b40dcbfc46fa349e7d4d8cd36025a82a03df009f985a6fc30d2edead6"
    ),
    "current_file_count": 105,
    "current_manifest_sha256": (
        "b5821442ec7066e807d16c0d9a5a0cf30d96479b49df96cba64f1d8863cbb738"
    ),
    "added_file_count": 51,
    "changed_file_count": 0,
    "deleted_file_count": 0,
}
WORM = {
    "accepted_report_source": node_d.WORM_RELATIVE,
    "accepted_report_sha256": node_d.WORM_SHA256,
    "accepted_build_context_sha256": node_d.CURRENT_BUILD_CONTEXT_SHA256,
    "accepted_chain_node_count": 9,
    "current_report_source": (
        "docs/refactor/phase4c/"
        "learning-transaction-write-http-worm-evidence.json"
    ),
    "current_report_sha256": (
        "dd165106d7b3a73512acdbf89924b352e3f1ad027132b8a8519af957a47de599"
    ),
    "current_report_byte_count": 1_442,
    "current_build_context_sha256": (
        "5e4247d0a43405661cef27b91b4169273e8ad096bfa750b4ba4488ca6c247224"
    ),
    "current_chain_node_count": 10,
}

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cLearningTransactionWriteHttpSourceSuccessorContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cLearningTransactionWriteHttpFullParityContractParityTest.java",
    "tools/build_phase4c_learning_transaction_write_http_source_successor_contract.py",
    "tools/phase4c_learning_transaction_write_http_source_successor_acceptance.py",
    "tools/test_phase4c_learning_transaction_write_http_source_successor_contract.py",
    "tools/build_phase4c_tag_migration_execution_protocol_contract.py",
    "tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationExecutionProtocolContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationExecutionProtocolPostPushAnchor"
    "SuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationExecutionProtocolPostPushAnchor"
    "ContractParityTest.java",
    "tools/phase4c_http_implementation_successor_acceptance.py",
    "tools/phase4c_http_target_execution_successor_acceptance.py",
    "tools/phase4c_http_target_execution_post_push_"
    "successor_acceptance.py",
    "tools/phase4c_http_target_execution_post_push_anchor_"
    "successor_acceptance.py",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_anchor_contract.py",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_contract.py",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_contract.py",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py",
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
    "tools/test_capture_phase4c_learning_transaction_write_goldens.py",
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
    "tools/test_phase4b_personal_bank_share_list_read_contract.py",
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
    "tools/phase4c_tag_migration_operator_core_successor_acceptance.py",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationOperatorCoreContractParityTest.java",
    "tools/build_phase4c_tag_migration_global_preflight_contract.py",
    "tools/phase4c_tag_migration_global_preflight_successor_acceptance.py",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightContractParityTest.java",
    "tools/phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_execution_protocol_contract.py",
    "tools/test_phase4c_tag_migration_operator_core_contract.py",
    "tools/test_phase4c_tag_migration_global_preflight_contract.py",
    "tools/capture_phase4c_learning_transaction_write_goldens.py",
    "tools/build_phase4c_learning_transaction_write_http_full_parity_contract.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def payload_sha256(document: dict[str, Any]) -> str:
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
    resolved_root = root.resolve(strict=True)
    value = Path(relative)
    if (
        value.is_absolute()
        or not value.parts
        or any(part in {"", ".", ".."} for part in value.parts)
    ):
        raise AssertionError(f"transaction-write source path escapes root: {relative}")
    cursor = resolved_root
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"transaction-write source path is a symlink: {relative}"
            )
    path = (resolved_root / value).resolve(strict=True)
    path.relative_to(resolved_root)
    if not path.is_file():
        raise AssertionError(
            f"transaction-write source path is not a regular file: {relative}"
        )
    return path


def production_runtime_manifest(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for relative in (
        "server/src/main",
        "server/pom.xml",
        "server/Dockerfile",
        "server/.dockerignore",
        "server/.mvn",
        "server/mvnw",
        "server/mvnw.cmd",
        "server/build-versions.properties",
        "compose.dev.yml",
        ".env.example",
        "contracts",
        "openapi",
    ):
        path = (root / relative).resolve(strict=True)
        candidates = (path,) if path.is_file() else tuple(sorted(path.rglob("*")))
        for child in candidates:
            if child.is_symlink():
                raise AssertionError(
                    f"transaction-write runtime contains a symlink: {child}"
                )
            if not child.is_file():
                continue
            key = child.relative_to(root).as_posix()
            manifest[key] = sha256_bytes(child.read_bytes())
    return dict(sorted(manifest.items()))


def learning_personalbank_main(
    manifest: dict[str, str],
) -> dict[str, str]:
    return node_d._learning_personalbank_main(manifest)


def _validate_current(root: Path) -> None:
    predecessor_payload = fixed_regular_file(
        root, PREDECESSOR["source"]
    ).read_bytes()
    if (
        len(predecessor_payload) != PREDECESSOR["byte_count"]
        or sha256_bytes(predecessor_payload) != PREDECESSOR["sha256"]
    ):
        raise AssertionError("transaction-write source predecessor drifted")
    document = json.loads(predecessor_payload)
    if (
        document.get("contract_id") != PREDECESSOR["contract_id"]
        or document.get("document_payload_sha256")
        != PREDECESSOR["document_payload_sha256"]
    ):
        raise AssertionError("transaction-write source predecessor identity drifted")
    for relative, transition in predecessor.SOURCE_TRANSITIONS.items():
        payload = fixed_regular_file(root, relative).read_bytes()
        if (
            len(payload) != transition["successor_byte_count"]
            or sha256_bytes(payload) != transition["successor_sha256"]
        ) and not integration.accepts(root, relative, transition["successor_sha256"], transition["successor_byte_count"]):
            raise AssertionError(
                f"transaction-write source transition drifted: {relative}"
            )
    for relative, (accepted_sha256, accepted_bytes) in node_d.SOURCE_FILES.items():
        if relative in CONTROL_SOURCES:
            continue
        transition = predecessor.SOURCE_TRANSITIONS.get(relative)
        if transition is None:
            payload = fixed_regular_file(root, relative).read_bytes()
            if (
                len(payload) != accepted_bytes
                or sha256_bytes(payload) != accepted_sha256
            ):
                raise AssertionError(
                    f"transaction-write source Node D bytes drifted: {relative}"
                )
            continue
        if (
            transition["accepted_sha256"] != accepted_sha256
            or transition["accepted_byte_count"] != accepted_bytes
        ):
            raise AssertionError(
                f"transaction-write source Node D origin drifted: {relative}"
            )
    current = production_runtime_manifest(root)
    scoped = learning_personalbank_main(current)
    if (
        len(current) != FULL_RUNTIME["current_file_count"]
        or sha256_json(current) != FULL_RUNTIME["current_manifest_sha256"]
        or len(scoped) != LEARNING_PERSONALBANK_MAIN["current_file_count"]
        or sha256_json(scoped)
        != LEARNING_PERSONALBANK_MAIN["current_manifest_sha256"]
    ):
        raise AssertionError("transaction-write source runtime manifest drifted")
    worm = fixed_regular_file(root, WORM["current_report_source"]).read_bytes()
    if (
        len(worm) != WORM["current_report_byte_count"]
        or sha256_bytes(worm) != WORM["current_report_sha256"]
    ):
        raise AssertionError("transaction-write source WORM report drifted")


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    _validate_current(resolved_root)
    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": "phase4c-learning-transaction-write-http-source-runtime-successor",
        "status": STATUS,
        "predecessor": {**PREDECESSOR, "immutable": True},
        "bootstrap_external_anchor": {
            "fixed_checkpoint": BOOTSTRAP_CHECKPOINT,
            "anchored_control_source_count": len(BOOTSTRAP_CONTROL_SOURCES),
            "anchored_control_sources": {
                relative: {"source": relative, **descriptor}
                for relative, descriptor in BOOTSTRAP_CONTROL_SOURCES.items()
            },
            "predecessor_control_sources_external_git_anchor_complete": True,
            "live_ref_authority": False,
        },
        "source_successors": {
            "accepted_checkpoint": predecessor.BASE_CHECKPOINT["commit_oid"],
            "successor_checkpoint": predecessor.IMPLEMENTATION_CHECKPOINT[
                "commit_oid"
            ],
            "transition_count": len(predecessor.SOURCE_TRANSITIONS),
            "transitions": {
                relative: {"source": relative, **transition}
                for relative, transition in predecessor.SOURCE_TRANSITIONS.items()
            },
            "dynamic_source_discovery": False,
            "unknown_path": "reject",
        },
        "semantic_successors": {
            "full_runtime": FULL_RUNTIME,
            "learning_personalbank_main": LEARNING_PERSONALBANK_MAIN,
            "java_build_context_and_worm": WORM,
        },
        "authorization": {
            "predecessor_control_sources_external_git_anchor_complete": True,
            "current_bridge_control_sources_external_git_anchor_complete": False,
            "full_target_parity_closed": True,
            "route_migration_eligible": False,
            "nine_transaction_write_operations_migrated": False,
            "route_delta": False,
            "production_cutover": False,
            "production_schema_execution": False,
            "real_data_migration_execution": False,
            "next_gate": "post_push_external_anchor_of_current_bridge_controls",
        },
        "route_state": {
            "total_operation_count": 611,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "implemented_pending_operation_count": 9,
        },
        "source_authority": {
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "control_sources_excluded_from_self_authority": True,
            "ordinary_build_is_gitless": True,
            "fixed_checkpoint_replay_is_explicit_only": True,
            "live_head_main_or_origin_authority": False,
            "historical_contracts_or_worm_overwritten": False,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


def _git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root.parent), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "transaction-write source fixed Git replay failed: "
            + " ".join(arguments)
        )
    return completed.stdout


def verify_fixed_git_checkpoint(root: Path = ROOT) -> None:
    resolved_root = root.resolve(strict=True)
    if (
        _git(
            resolved_root,
            "rev-parse",
            f"{BOOTSTRAP_CHECKPOINT['commit_oid']}^{{tree}}",
        ).decode().strip()
        != BOOTSTRAP_CHECKPOINT["root_tree_oid"]
        or _git(
            resolved_root,
            "rev-parse",
            f"{BOOTSTRAP_CHECKPOINT['commit_oid']}^{{tree}}:Ti-Java",
        ).decode().strip()
        != BOOTSTRAP_CHECKPOINT["ti_java_tree_oid"]
    ):
        raise AssertionError("transaction-write source fixed Git tree drifted")
    for relative, descriptor in BOOTSTRAP_CONTROL_SOURCES.items():
        blob = _git(
            resolved_root,
            "rev-parse",
            f"{BOOTSTRAP_CHECKPOINT['commit_oid']}:Ti-Java/{relative}",
        ).decode().strip()
        payload = _git(
            resolved_root,
            "cat-file",
            "blob",
            str(descriptor["git_blob_oid"]),
        )
        if (
            blob != descriptor["git_blob_oid"]
            or len(payload) != descriptor["byte_count"]
            or sha256_bytes(payload) != descriptor["sha256"]
        ):
            raise AssertionError(
                f"transaction-write source fixed Git control drifted: {relative}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-fixed-git-checkpoint", action="store_true")
    args = parser.parse_args()
    document = build_contract(ROOT)
    payload = serialized_contract(document)
    if args.verify_fixed_git_checkpoint:
        verify_fixed_git_checkpoint(ROOT)
    if args.check:
        if args.output.read_bytes() != payload:
            raise SystemExit("transaction-write source successor contract drifted")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
