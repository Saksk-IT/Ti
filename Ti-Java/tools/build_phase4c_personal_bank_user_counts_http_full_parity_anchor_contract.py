#!/usr/bin/env python3
"""Build the fixed Git anchor for the Phase 4C full-parity bootstrap."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-full-parity-anchor-contract.json"
)
CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-http-full-parity-anchor-contract"
CAPTURED_AT = "2026-07-18T21:52:39+08:00"

PREDECESSOR = {
    "source": (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-http-full-parity-contract.json"
    ),
    "contract_id": "ti.phase4c.personal-bank-user-counts-http-full-parity-contract",
    "sha256": "13df3a1f81ca909d62e89495564215e92a757e41889aa91658db55e33717b787",
    "document_payload_sha256": (
        "7eecb6279b2e2b5532dab21c171b9fca3a7bb6129ff2f4dff3bfcf7941196da2"
    ),
    "byte_count": 7_477,
    "status": "full_target_parity_closed_external_anchor_pending_routes_pending",
}

GIT_COMMIT_OID = "848af89cb99ae0330ec1f0955cf23749a044d40e"
GIT_PARENT_OID = "765e4470f1ddb60f0ce6f23227d6303961f47fcf"
GIT_ROOT_TREE_OID = "9cbb82ee611128bba95a3b726021dab9adde1011"
GIT_TI_JAVA_TREE_OID = "88107eea64154eccba9c48e853ba08a52371c27c"
GIT_SUBJECT = "test(java): close phase4c user counts parity"
GIT_AUTHORED_AT = "2026-07-18T21:52:39+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_RAW_DELTA_SHA256 = "31eaf6a354572681641dcace593e0d7eb0b3304ed4cfc6e380841dca6c5864b3"


def _artifact(change: str, old_mode: str, new_mode: str, old_oid: str,
              new_oid: str, sha256: str, byte_count: int) -> dict[str, Any]:
    return {
        "change_type": change,
        "previous_mode": old_mode,
        "mode": new_mode,
        "previous_git_blob_oid": old_oid,
        "git_blob_oid": new_oid,
        "object_type": "blob",
        "sha256": sha256,
        "byte_count": byte_count,
    }


ZERO_OID = "0" * 40
CHECKPOINT = {
    "README.md": _artifact("M", "100644", "100644", "7bebf852c223c7b414872746c07c1e5ba4f8a1c1", "57f736213bb2434dab0c85cf4934d4c0b70bd699", "3bae759a577df3f4cc0e5ea417a634c4d0ad635acfa8d3b1fba2587469e0b302", 38_663),
    "docs/refactor/05-progress.md": _artifact("M", "100644", "100644", "e73756dd7d2da15755c0d10e695821cd8a5ee7ff", "76b586198594bf18e759a420cd2c8a3f4d4ea819", "c904e0ddd2f0dfb4aabe09e21e36768b7a241a5e0d50af2126ecb16e8da4cb51", 103_147),
    "docs/refactor/phase4c/README.md": _artifact("M", "100644", "100644", "c645e5391df73752bb4359b606420f3138dde457", "bf5d3154025bbdcb7fe0a2c2792bb64032948560", "ccd7da42d8d7d9d08a579943c98aeaf871947f4964636063cc05b68888683221", 21_178),
    "docs/refactor/phase4c/personal-bank-user-counts-http-full-parity-contract.json": _artifact("A", "000000", "100644", ZERO_OID, "d4e8d333766b084351c28644bbc30c87c0668183", "13df3a1f81ca909d62e89495564215e92a757e41889aa91658db55e33717b787", 7_477),
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpFullParitySuccessorAcceptance.java": _artifact("A", "000000", "100644", ZERO_OID, "ed68807e31141ee68b6a16ba71e3ace460e31e74", "703eeaff656912bd67eb553fe6e1accf8cf6c4e9bc99a59bf71d13423f33baf7", 8_577),
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpFullParityContractParityTest.java": _artifact("A", "000000", "100644", ZERO_OID, "19f01670c1a1b40b212411bd347cab6f01699be9", "45ad052dfe392bf614f8af03f40bf77a954fb82648c2a1e97cb715f7818dace4", 6_586),
    "server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.java": _artifact("A", "000000", "100644", ZERO_OID, "6381cdda667b13c9edd10fc07c8d8623006c151a", "cd9a45f6cfc52342d235202519ace13883e37354a901a790304739b7507501c9", 40_107),
    "server/src/test/java/io/saksk/ti/integration/Phase4cUserCountsTerminationFingerprintIT.java": _artifact("A", "000000", "100644", ZERO_OID, "6a54ad5f862005e36ce06f5a35da3f02e37c512f", "aa55869a57233a34ceae59773456cbb759670db1624b844cae75e664f8c0701a", 26_069),
    "server/src/test/java/io/saksk/ti/support/Phase4cUserCountsTerminationFingerprintSupport.java": _artifact("A", "000000", "100644", ZERO_OID, "ab562b29a979f0a3c9f7bc8f64be19a9a363fd57", "e4c4fc6f73b5ee9eebc3ab2e9904a51d6c593ed711b4aaaa39a79971e887ce42", 25_907),
    "server/src/test/java/io/saksk/ti/web/security/Phase4cUserCountsRedisOutageRecoveryIT.java": _artifact("A", "000000", "100644", ZERO_OID, "303d88f5e7b12ba7abeb7f01178aaabbe6c96510", "b07ec534e41a74c1fddc3d9c2b63a6ae26f57ab8918112dc7799f10b479239c4", 39_719),
    "server/src/test/java/io/saksk/ti/web/security/support/Phase4cRedisNetworkGate.java": _artifact("A", "000000", "100644", ZERO_OID, "c1590235099c2c6ba0eb74a26ad83afe5b18f65d", "ac3bab1cd092dcce640954c167baf4f7de5e53dee8579e77fb36d632c410b5ab", 7_245),
    "server/src/test/resources/db/phase4c/073-personal-bank-user-counts-termination-fingerprint-seed.sql": _artifact("A", "000000", "100644", ZERO_OID, "e52a5e9095a1847ab2742c02b8a485a555b3055e", "33a6a4ce9845fe8b51ae6d5006af9a394bdc51d8427183d2775b2ef1cb4e6b40", 843),
    "tools/build_phase4c_personal_bank_user_counts_http_full_parity_contract.py": _artifact("A", "000000", "100644", ZERO_OID, "61ffdd2c3994f410eca4b78615aa29edd5bdd245", "6ae98b23ca5d475f266608ae0ee443800d004004062a30f60b1895d1551ea585", 11_271),
    "tools/phase4c_http_full_parity_successor_acceptance.py": _artifact("A", "000000", "100644", ZERO_OID, "a951992f6c90c5400952c6bf4ab4e0a6c3086152", "a28c01c637cf61acc6dc476abe540d13a247c9298086d660c899f2af17c23cf0", 7_171),
    "tools/test_phase4c_personal_bank_user_counts_http_full_parity_contract.py": _artifact("A", "000000", "100644", ZERO_OID, "be4289798cc7635484c8f3dd1799d8ef0a282335", "c9ba6025c127c92f1f20d2eefe753f02256d9aa3ed7e37c04e94093ed1044d14", 6_313),
}

BOOTSTRAP_SOURCES = (
    PREDECESSOR["source"],
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpFullParitySuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpFullParityContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_full_parity_contract.py",
    "tools/phase4c_http_full_parity_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_full_parity_contract.py",
)

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpFullParityAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpFullParityAnchorContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract.py",
    "tools/phase4c_http_full_parity_anchor_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def payload_sha256(document: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    }).encode("utf-8"))


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"full parity anchor path escapes root: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"full parity anchor path contains symlink: {relative}")
    resolved = (resolved_root / candidate).resolve(strict=True)
    resolved.relative_to(resolved_root)
    if not resolved.is_file():
        raise AssertionError(f"full parity anchor path is not a regular file: {relative}")
    return resolved


def _validate_bytes(root: Path, relative: str, sha256: str, byte_count: int) -> bytes:
    payload = fixed_regular_file(root, relative).read_bytes()
    if sha256_bytes(payload) != sha256 or len(payload) != byte_count:
        raise AssertionError(f"full parity anchor fixed bytes drifted: {relative}")
    return payload


def _run_git(repository_root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    command = ["git", "-C", str(repository_root), *arguments]
    completed = subprocess.run(command, check=True, capture_output=True)
    return completed.stdout if binary else completed.stdout.decode("utf-8")


def validate_git_checkpoint(repository_root: Path) -> None:
    metadata = _run_git(
        repository_root,
        "show", "-s", "--format=%H%n%P%n%T%n%aI%n%cI%n%s", GIT_COMMIT_OID,
    ).splitlines()
    expected = [GIT_COMMIT_OID, GIT_PARENT_OID, GIT_ROOT_TREE_OID,
                GIT_AUTHORED_AT, GIT_COMMITTED_AT, GIT_SUBJECT]
    if metadata != expected:
        raise AssertionError("full parity anchor Git metadata drifted")
    ti_java_tree = _run_git(repository_root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java").strip()
    if ti_java_tree != GIT_TI_JAVA_TREE_OID:
        raise AssertionError("full parity anchor Ti-Java tree drifted")
    raw = _run_git(
        repository_root, "diff-tree", "--no-commit-id", "--no-renames", "--raw",
        "-r", "--abbrev=40", GIT_PARENT_OID, GIT_COMMIT_OID, binary=True,
    )
    if sha256_bytes(raw) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("full parity anchor raw delta drifted")
    actual_paths = _run_git(
        repository_root, "diff-tree", "--no-commit-id", "--no-renames",
        "--name-only", "-r", GIT_PARENT_OID, GIT_COMMIT_OID,
    ).splitlines()
    if actual_paths != [f"Ti-Java/{relative}" for relative in CHECKPOINT]:
        raise AssertionError("full parity anchor changed path set drifted")
    for relative, descriptor in CHECKPOINT.items():
        blob = _run_git(repository_root, "cat-file", "blob", descriptor["git_blob_oid"], binary=True)
        if (sha256_bytes(blob) != descriptor["sha256"]
                or len(blob) != descriptor["byte_count"]):
            raise AssertionError(f"full parity anchor Git blob drifted: {relative}")


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    predecessor = _validate_bytes(
        root, PREDECESSOR["source"], PREDECESSOR["sha256"], PREDECESSOR["byte_count"])
    parsed = json.loads(predecessor)
    if parsed.get("document_payload_sha256") != PREDECESSOR["document_payload_sha256"]:
        raise AssertionError("full parity anchor predecessor payload drifted")

    anchored = {}
    for relative in BOOTSTRAP_SOURCES:
        descriptor = CHECKPOINT[relative]
        _validate_bytes(root, relative, descriptor["sha256"], descriptor["byte_count"])
        anchored[relative] = {
            "git_blob_oid": descriptor["git_blob_oid"],
            "sha256": descriptor["sha256"],
            "byte_count": descriptor["byte_count"],
            "mode": descriptor["mode"],
        }

    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": "phase4c-personal-bank-user-counts-http-full-parity-external-anchor",
        "status": "full_target_parity_externally_anchored_route_migration_eligible",
        "predecessor": {**PREDECESSOR, "immutable": True},
        "git_checkpoint": {
            "object_format": "sha1",
            "commit_oid": GIT_COMMIT_OID,
            "parent_oid": GIT_PARENT_OID,
            "root_tree_oid": GIT_ROOT_TREE_OID,
            "ti_java_tree_oid": GIT_TI_JAVA_TREE_OID,
            "subject": GIT_SUBJECT,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_COMMITTED_AT,
            "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
            "changed_path_count": len(CHECKPOINT),
            "added_path_count": sum(value["change_type"] == "A" for value in CHECKPOINT.values()),
            "modified_path_count": sum(value["change_type"] == "M" for value in CHECKPOINT.values()),
            "exact_changed_paths": list(CHECKPOINT),
            "artifacts": CHECKPOINT,
        },
        "full_parity_source_anchor": {
            "source_count": len(BOOTSTRAP_SOURCES),
            "source_paths": list(BOOTSTRAP_SOURCES),
            "artifacts": anchored,
            "predecessor_bootstrap_sources_external_git_anchor_complete": True,
            "current_anchor_sources_excluded_from_self_authority": True,
            "current_anchor_source_bytes_external_git_anchor_complete": False,
        },
        "parity": {
            "pg16_pg18_termination_fingerprints_complete": True,
            "real_tomcat_complete_response_header_matrix_complete": True,
            "same_service_redis_outage_and_recovery_complete": True,
            "full_target_parity_closed": True,
            "typed_parity_review_complete": True,
        },
        "authorization": {
            "full_parity_checkpoint_and_six_excluded_sources_external_git_anchor_complete": True,
            "route_migration_eligible": True,
            "two_legacy_get_routes_migrated": False,
            "production_cutover": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "next_gate": "append_only_user_counts_route_parity_successor_delta",
        },
        "route_state": {
            "total_operation_count": 611,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "implemented_pending_get_count": 2,
        },
        "source_authority": {
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "excluded_from_self_authority": True,
            "historical_contracts_and_worm_overwritten": False,
        },
        "worm_evidence": {
            "source": (
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-http-implementation-worm-evidence.json"
            ),
            "sha256": "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
            "java_build_context_sha256": "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3",
            "fixed_chain_node_count": 5,
            "reused": True,
            "new_worm_report_created": False,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


if __name__ == "__main__":
    print(serialized_contract(build_contract()).decode("utf-8"), end="")
