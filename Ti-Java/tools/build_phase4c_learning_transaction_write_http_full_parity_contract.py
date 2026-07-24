#!/usr/bin/env python3
"""Build the append-only Phase 4C transaction-write full-parity bootstrap.

The ordinary builder is Gitless and accepts only fixed paths.  It composes the
externally anchored Node D checkpoint with the reviewed transaction-write
implementation checkpoint.  Its own control plane remains self-excluded until
the next post-push anchor fixes those bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

try:
    from tools import build_phase4c_tag_migration_execution_protocol_contract as node_d
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_execution_protocol_contract",
    }:
        raise
    import build_phase4c_tag_migration_execution_protocol_contract as node_d


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "learning-transaction-write-http-full-parity-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
CONTRACT_ID = "ti.phase4c.learning-transaction-write-http-full-parity-contract"
CAPTURED_AT = "2026-07-24T17:10:00+08:00"
STATUS = "full_target_execution_closed_external_control_anchor_pending_routes_pending"

NODE_D_CONTRACT = {
    "source": node_d.OUTPUT_RELATIVE,
    "contract_id": node_d.CONTRACT_ID,
    "sha256": "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14",
    "document_payload_sha256": (
        "42599261bc5632feed89fc41637ee1a98cff844dd9dc776f889d155a0567a7c4"
    ),
    "byte_count": 44_336,
}
NODE_D_ANCHOR = {
    "source": (
        "docs/refactor/phase4c/"
        "personal-bank-tag-migration-execution-protocol-post-push-anchor-contract.json"
    ),
    "contract_id": (
        "ti.phase4c.personal-bank-tag-migration-execution-protocol-"
        "post-push-anchor-contract"
    ),
    "sha256": "a6dff0717d0da91091f50cb7a51d35ffc66db364e966c568fec40bdb3ca936cd",
    "document_payload_sha256": (
        "1a8bf429fe15f85e380f417329c0ca25c3245a6f1254c774b1a14ee7ebc48164"
    ),
    "byte_count": 80_324,
}

BASE_CHECKPOINT = {
    "commit_oid": "2579dfd344dbe318c9fb59d067c843356b98fece",
    "parent_commit_oid": "aff3c9e8d6b1ed33dc0a050c0e435572cddd51db",
    "root_tree_oid": "b92075fbf838961f25e882aec87d7b0f137ff738",
    "ti_java_tree_oid": "b6027658c2dcb2436a427aa39bea686506d1a6e2",
    "committed_at": "2026-07-23T18:42:34+08:00",
    "subject": "test(java): anchor tag migration execution protocol",
}
IMPLEMENTATION_CHECKPOINT = {
    "commit_oid": "b635d1db3b9d71698d9a40cc729a215d67a6906f",
    "parent_commit_oid": "681c1ef5ca70cc392998f6db6309df55134d4551",
    "root_tree_oid": "2acbc3215742f377ba3347b5531defd60ad9740a",
    "ti_java_tree_oid": "5ce1810e80a2c39cf710db20d0723a2e180ce0b8",
    "committed_at": "2026-07-24T16:25:15+08:00",
    "subject": "test(java): append transaction write worm evidence",
    "raw_delta_sha256": (
        "a63400fde90be49c168c67b95650db8e218c99a19ab74ede8443857dfa89f154"
    ),
    "changed_path_count": 184,
    "added_path_count": 167,
    "modified_path_count": 17,
    "deleted_path_count": 0,
    "inserted_line_count": 70_774,
    "deleted_line_count": 23,
}

# Exact physical transitions between the fixed Node D and implementation
# checkpoints.  This is intentionally handwritten and reviewable: no glob,
# current-tree discovery or live-ref authority is used by the ordinary build.
SOURCE_TRANSITIONS: dict[str, dict[str, Any]] = {
    "docs/refactor/05-progress.md": {
        "accepted_byte_count": 109_911,
        "accepted_sha256": "2fb55e0aaaeff28c3c3def877b5be51ae2ea6358272222f0e0f8232dec69867f",
        "successor_byte_count": 122_201,
        "successor_sha256": "4720c1ef1f1dc9d0a7dd6ce8a4c9eb4b1fd4a55c40cd106158fd8060472212de",
    },
    "infra/phase2/README.md": {
        "accepted_byte_count": 9_031,
        "accepted_sha256": "187895861b607be2cfddb63320b4ee52dc4efd7706e94afd5d56a07169832216",
        "successor_byte_count": 9_073,
        "successor_sha256": "12455289b964d2eeee2f700768f7ff60fa73e13c81f696dbf1a7671714b30aac",
    },
    "infra/phase2/verify-local-reference-wormhole.sh": {
        "accepted_byte_count": 23_482,
        "accepted_sha256": "3267a16d4690f6332f72d6bcfe9a6351f79bcef46b13f974156fd98bfc22fe6d",
        "successor_byte_count": 24_892,
        "successor_sha256": "fb947695b66d600f5bebf16e2fadadfbdb97ab373e812b1f3f2ff9b9dd06b44f",
    },
    "infra/phase2/verify-static.sh": {
        "accepted_byte_count": 18_597,
        "accepted_sha256": "6878d027fc21c1564840771609f0f2e9dfa6eb2bb483b56b6abfd1e9386eb4a3",
        "successor_byte_count": 19_350,
        "successor_sha256": "f915ded1c5c86b4ab2872016307a59370dd4c75c45cee9734af30af99ba54ff4",
    },
    "server/pom.xml": {
        "accepted_byte_count": 9_582,
        "accepted_sha256": "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b",
        "successor_byte_count": 9_830,
        "successor_sha256": "0996c59ac315bad6d24c699adbd5b49f808abf2d5d33be6be7272c382da34431",
    },
    "server/src/main/java/io/saksk/ti/catalog/api/SubjectMetadataApplicationApi.java": {
        "accepted_byte_count": 362,
        "accepted_sha256": "ef6b469d8d4838d39d35888e05ebe23c66dfd8722c318d0401cff965274eb1e5",
        "successor_byte_count": 440,
        "successor_sha256": "66daaadd194f58b38043af7b1159a180df8439e0a7431618dfd35281c7992977",
    },
    "server/src/main/java/io/saksk/ti/catalog/application/SubjectMetadataQueryService.java": {
        "accepted_byte_count": 1_502,
        "accepted_sha256": "1aac46da47fe15f9dd74083cd45490cab274415d16d4c3acb280d9b12ca31966",
        "successor_byte_count": 1_947,
        "successor_sha256": "46404d2ffdd46ad58eae0a61cffedaaa4765d1ff68a42dc1210813a28d525360",
    },
    "server/src/main/java/io/saksk/ti/catalog/application/port/SubjectContextQueryPort.java": {
        "accepted_byte_count": 314,
        "accepted_sha256": "51c2881c1de7bf353784e2b86b700f7f73adf2904cd838470a6ec0d0d937368b",
        "successor_byte_count": 536,
        "successor_sha256": "ebc5e029efeeed2102d9ebdb81da2cd60337febf7e51d724fcfd49de46cfc91b",
    },
    "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/JdbcSubjectContextQueryAdapter.java": {
        "accepted_byte_count": 1_169,
        "accepted_sha256": "e3555ed59030c2024fbbb0bb0d752292fda42581ced0abb6e89fa4af4b256bdc",
        "successor_byte_count": 2_238,
        "successor_sha256": "81ff1bd0a4275ebc72d2618369d039d89215c2d235c38d9bddd92feba241be47",
    },
    "server/src/main/java/io/saksk/ti/web/config/ProductionSecretsConfiguration.java": {
        "accepted_byte_count": 2_287,
        "accepted_sha256": "c2f56f255d879cf4955c71a5dd385b125c0b6c49d5c26f3cd2e4b98533092331",
        "successor_byte_count": 2_551,
        "successor_sha256": "f59ca847ddee461be4db59e507592e0eec3a5670ab96c56478de4d0ca9cd5d67",
    },
    "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java": {
        "accepted_byte_count": 21_994,
        "accepted_sha256": "8e6a064d9880a37a597ce9c3422ac4028580b54e60694e6ec7741c9829e8eb70",
        "successor_byte_count": 27_356,
        "successor_sha256": "288fa46653b922e47d1d9019a5ffdb94c2743f3e5175bbef06c26fc88f3f5cfe",
    },
    "server/src/main/java/io/saksk/ti/web/security/LoginRateLimitConfiguration.java": {
        "accepted_byte_count": 3_965,
        "accepted_sha256": "be9d75e7e9496e489f2d2447b7bfb13ab0815be254bdba47aaba91b1048fd9ed",
        "successor_byte_count": 4_948,
        "successor_sha256": "c37cf7a54d290fce85b5963e7b66f51224815d44deaf43dd876d435db93c299d",
    },
    "server/src/main/resources/application-prod.yml": {
        "accepted_byte_count": 2_724,
        "accepted_sha256": "b741dc5efbe7b0f81750b24c7ad1c48930ca2bb3a104f99f5eb3fb163617d53b",
        "successor_byte_count": 3_477,
        "successor_sha256": "9c7c214292b66ba13d7b2fada9370011cae4cec66b30de359818407ec016c680",
    },
    "server/src/main/resources/application.yml": {
        "accepted_byte_count": 6_053,
        "accepted_sha256": "6f5584026bcdd412db7a09ab8fde946556011aefabf7ca578441d5548f1a855c",
        "successor_byte_count": 7_237,
        "successor_sha256": "3335936419b6cf361e0e0e7397c639b0838b2e01175144fc5895d05b6258ed04",
    },
    "server/src/test/java/io/saksk/ti/catalog/application/SubjectMetadataQueryServiceTest.java": {
        "accepted_byte_count": 6_258,
        "accepted_sha256": "d3d4824dd0442ce139cee51776bd50f7d3d40e7bbddb557feefec9932d42c374",
        "successor_byte_count": 7_952,
        "successor_sha256": "660214c26b31fae95c3f26a2711522a2b485a9a8e41ce9158f0329d8b4a6500f",
    },
    "server/src/test/java/io/saksk/ti/learning/LearningModuleContextTest.java": {
        "accepted_byte_count": 1_707,
        "accepted_sha256": "694044896e01aee33c9cf82f8284680caa177e4272089a511f0c5361e2bcd48f",
        "successor_byte_count": 2_407,
        "successor_sha256": "92b0a927722487789bd9fe0905e3673cc33f2c407dc8b5163d5c3c2199dd9cbb",
    },
    "server/src/test/java/io/saksk/ti/web/config/ProductionSecretsConfigurationTest.java": {
        "accepted_byte_count": 3_609,
        "accepted_sha256": "5f2729c1afd722654dac03087c0078947358c95d082cd348685e8855f1c2ad19",
        "successor_byte_count": 4_517,
        "successor_sha256": "24b98da9b4db32f86f2e0709665482e9617d88cfe844a32165b9e10e8f5705e8",
    },
}

EVIDENCE_FILES: dict[str, tuple[str, int]] = {
    "docs/refactor/phase4c/learning-transaction-write-implementation-contract.json": (
        "c4f4b2aed1836ffb2515ca6f13d0e5d822557e57be1a8befc7b696959a814cd3",
        15_652,
    ),
    "docs/refactor/phase4c/learning-transaction-write-implementation-post-push-anchor.json": (
        "2fc43a8c5eda052daac305cd7ed289bd6eecfa4f0ce9ed7cb56d282468cdc593",
        2_668,
    ),
    "openapi/phase4c-learning-transaction-write.openapi.json": (
        "678ccd1b1ac43a5db129180cc3ad6d5201ed30d4b84391a7cb763f1ecc0f1060",
        75_627,
    ),
    "docs/refactor/phase4c/learning-transaction-write-http-worm-evidence.json": (
        "dd165106d7b3a73512acdbf89924b352e3f1ad027132b8a8519af957a47de599",
        1_442,
    ),
    "docs/refactor/phase4c/learning-transaction-write-http-effective-data-ownership-status.json": (
        "d3b0c0d46b1009f517a0170934f128af56126604e2772fd826e6ae355c9feed2",
        1_333,
    ),
    "server/src/test/java/io/saksk/ti/integration/LegacyTransactionWriteRealTomcatIT.java": (
        "e7300f3ccc99ac994845341dc12b820af1bdce3574a63bc8f473dc3bebc51139",
        44_209,
    ),
    "server/src/test/java/io/saksk/ti/integration/LegacyTransactionWritePostgres16IT.java": (
        "a51da1c29ed1ebc8585961c082a7a64e33ba98d2fa68d71f8894c13fa2592442",
        15_764,
    ),
    "server/src/test/java/io/saksk/ti/web/security/RedisTransactionWriteRateLimiterIT.java": (
        "ec90cb9420dad9a3cb240e3880f935622f2db2f01f16bd444cabc8408ce11c30",
        18_664,
    ),
}

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cLearningTransactionWriteHttpFullParityContractParityTest.java",
    "tools/build_phase4c_learning_transaction_write_http_full_parity_contract.py",
    "tools/phase4c_learning_transaction_write_http_full_parity_successor_acceptance.py",
    "tools/test_phase4c_learning_transaction_write_http_full_parity_contract.py",
    "tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def payload_sha256(document: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise AssertionError(f"transaction-write parity path escapes root: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"transaction-write parity path is a symlink: {relative}"
            )
    resolved = (resolved_root / candidate).resolve(strict=True)
    resolved.relative_to(resolved_root)
    if not resolved.is_file():
        raise AssertionError(
            f"transaction-write parity path is not a regular file: {relative}"
        )
    return resolved


def validated_bytes(
    root: Path, relative: str, sha256: str, byte_count: int
) -> bytes:
    payload = fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(
            f"transaction-write parity fixed bytes drifted: {relative}"
        )
    return payload


def read_fixed_json(
    root: Path, descriptor: dict[str, Any]
) -> dict[str, Any]:
    payload = validated_bytes(
        root,
        str(descriptor["source"]),
        str(descriptor["sha256"]),
        int(descriptor["byte_count"]),
    )
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(
            f"transaction-write parity JSON is unreadable: {descriptor['source']}"
        ) from error
    if not isinstance(document, dict):
        raise AssertionError(
            f"transaction-write parity JSON is not an object: {descriptor['source']}"
        )
    if (
        document.get("contract_id") != descriptor["contract_id"]
        or document.get("document_payload_sha256")
        != descriptor["document_payload_sha256"]
    ):
        raise AssertionError(
            f"transaction-write parity JSON identity drifted: {descriptor['source']}"
        )
    return document


def _validate_node_d_sources(root: Path) -> None:
    for relative, (accepted_sha256, accepted_bytes) in node_d.SOURCE_FILES.items():
        transition = SOURCE_TRANSITIONS.get(relative)
        if transition is None:
            validated_bytes(root, relative, accepted_sha256, accepted_bytes)
            continue
        if (
            transition["accepted_sha256"] != accepted_sha256
            or transition["accepted_byte_count"] != accepted_bytes
        ):
            raise AssertionError(
                f"transaction-write parity Node D transition origin drifted: {relative}"
            )
        validated_bytes(
            root,
            relative,
            str(transition["successor_sha256"]),
            int(transition["successor_byte_count"]),
        )


def _validate_inputs(root: Path) -> None:
    node_d_document = read_fixed_json(root, NODE_D_CONTRACT)
    if node_d_document.get("historical_source_successors", {}).get(
        "predecessor_checkpoint"
    ) != node_d.PREDECESSOR_COMMIT:
        raise AssertionError("transaction-write parity Node D contract drifted")
    anchor = read_fixed_json(root, NODE_D_ANCHOR)
    if (
        anchor.get("authorization", {}).get(
            "execution_protocol_control_sources_external_git_anchor_complete"
        )
        is not True
        or anchor.get("route_state", {}).get("migrated_operation_count") != 13
        or anchor.get("route_state", {}).get("pending_operation_count") != 598
        or anchor.get("route_state", {}).get(
            "production_cutover_operation_count"
        )
        != 0
    ):
        raise AssertionError("transaction-write parity Node D anchor drifted")
    _validate_node_d_sources(root)
    for relative, transition in SOURCE_TRANSITIONS.items():
        validated_bytes(
            root,
            relative,
            str(transition["successor_sha256"]),
            int(transition["successor_byte_count"]),
        )
    for relative, (sha256, byte_count) in EVIDENCE_FILES.items():
        validated_bytes(root, relative, sha256, byte_count)


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    _validate_inputs(resolved_root)
    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": "phase4c-learning-transaction-write-http-full-target-execution",
        "status": STATUS,
        "predecessor": {
            "node_d_contract": {**NODE_D_CONTRACT, "immutable": True},
            "node_d_external_anchor": {**NODE_D_ANCHOR, "immutable": True},
            "fixed_checkpoint": BASE_CHECKPOINT,
        },
        "implementation_checkpoint": IMPLEMENTATION_CHECKPOINT,
        "historical_source_successors": {
            "accepted_checkpoint": BASE_CHECKPOINT["commit_oid"],
            "successor_checkpoint": IMPLEMENTATION_CHECKPOINT["commit_oid"],
            "transition_count": len(SOURCE_TRANSITIONS),
            "transitions": {
                relative: {"source": relative, **transition}
                for relative, transition in SOURCE_TRANSITIONS.items()
            },
            "dynamic_source_discovery": False,
            "unknown_path": "reject",
        },
        "fixed_evidence": {
            "artifact_count": len(EVIDENCE_FILES),
            "artifacts": {
                relative: {
                    "source": relative,
                    "sha256": descriptor[0],
                    "byte_count": descriptor[1],
                }
                for relative, descriptor in EVIDENCE_FILES.items()
            },
            "real_random_port_tomcat_full_filter_chain": True,
            "target_session_flask_session_and_bearer_to_controller": True,
            "redis_7_4_atomicity_outage_and_recovery": True,
            "postgresql_versions": ["16.14", "18.4"],
            "users_last_active_business_dml_count": 0,
            "openapi_3_1_2_exact_operation_count": 9,
            "worm_chain_node_count": 10,
            "worm_report_sha256": (
                "dd165106d7b3a73512acdbf89924b352e3f1ad027132b8a8519af957a47de599"
            ),
            "java_build_context_sha256": (
                "5e4247d0a43405661cef27b91b4169273e8ad096bfa750b4ba4488ca6c247224"
            ),
        },
        "parity": {
            "operation_count": 9,
            "target_execution_complete": True,
            "authentication_execution_complete": True,
            "http_and_cors_complete": True,
            "idempotency_complete": True,
            "redis_complete": True,
            "postgresql_16_14_and_18_4_complete": True,
            "openapi_complete": True,
            "worm_complete": True,
            "full_target_parity_closed": True,
        },
        "authorization": {
            "bootstrap_control_sources_external_git_anchor_complete": False,
            "route_migration_eligible": False,
            "nine_transaction_write_operations_migrated": False,
            "route_or_openapi_delta": False,
            "production_cutover": False,
            "production_schema_execution": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "next_gate": (
                "post_push_external_git_anchor_of_bootstrap_control_sources"
            ),
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
            "fixed_transition_allowlist_exact": True,
            "ordinary_build_is_gitless": True,
            "live_head_main_or_origin_authority": False,
            "fixed_checkpoint_git_replay_is_explicit_only": True,
            "historical_contracts_or_worm_overwritten": False,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root.parent), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"transaction-write parity fixed Git replay failed: {' '.join(args)}"
        )
    return completed.stdout


def verify_fixed_git_checkpoints(root: Path = ROOT) -> None:
    resolved_root = root.resolve(strict=True)
    if (
        _git(
            resolved_root,
            "rev-parse",
            f"{BASE_CHECKPOINT['commit_oid']}^{{tree}}",
        ).strip()
        != BASE_CHECKPOINT["root_tree_oid"]
        or _git(
            resolved_root,
            "rev-parse",
            f"{IMPLEMENTATION_CHECKPOINT['commit_oid']}^{{tree}}",
        ).strip()
        != IMPLEMENTATION_CHECKPOINT["root_tree_oid"]
        or _git(
            resolved_root,
            "rev-parse",
            f"{BASE_CHECKPOINT['commit_oid']}^{{tree}}:Ti-Java",
        ).strip()
        != BASE_CHECKPOINT["ti_java_tree_oid"]
        or _git(
            resolved_root,
            "rev-parse",
            f"{IMPLEMENTATION_CHECKPOINT['commit_oid']}^{{tree}}:Ti-Java",
        ).strip()
        != IMPLEMENTATION_CHECKPOINT["ti_java_tree_oid"]
    ):
        raise AssertionError("transaction-write parity fixed Git tree drifted")
    raw = _git(
        resolved_root,
        "diff",
        "--raw",
        "--no-abbrev",
        BASE_CHECKPOINT["commit_oid"],
        IMPLEMENTATION_CHECKPOINT["commit_oid"],
        "--",
        "Ti-Java",
    ).encode("utf-8")
    if sha256_bytes(raw) != IMPLEMENTATION_CHECKPOINT["raw_delta_sha256"]:
        raise AssertionError("transaction-write parity fixed Git delta drifted")
    for relative, transition in SOURCE_TRANSITIONS.items():
        accepted = _git(
            resolved_root,
            "show",
            f"{BASE_CHECKPOINT['commit_oid']}:Ti-Java/{relative}",
        ).encode("utf-8")
        successor = _git(
            resolved_root,
            "show",
            f"{IMPLEMENTATION_CHECKPOINT['commit_oid']}:Ti-Java/{relative}",
        ).encode("utf-8")
        if (
            len(accepted) != transition["accepted_byte_count"]
            or sha256_bytes(accepted) != transition["accepted_sha256"]
            or len(successor) != transition["successor_byte_count"]
            or sha256_bytes(successor) != transition["successor_sha256"]
        ):
            raise AssertionError(
                f"transaction-write parity fixed Git transition drifted: {relative}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-fixed-git-checkpoints", action="store_true")
    args = parser.parse_args()
    document = build_contract(ROOT)
    payload = serialized_contract(document)
    if args.verify_fixed_git_checkpoints:
        verify_fixed_git_checkpoints(ROOT)
    if args.check:
        if args.output.read_bytes() != payload:
            raise SystemExit("transaction-write full-parity contract drifted")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
