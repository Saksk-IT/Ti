#!/usr/bin/env python3
"""Build the append-only Phase 4C user-counts full-parity bootstrap.

This builder is intentionally Gitless.  It binds the immutable predecessor,
the three reviewed Worker integration objects, the six exact evidence files,
and the INT verification results.  Its own six control sources are excluded
from self-authority until a later fixed Git anchor successor binds them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-full-parity-contract.json"
)
CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-http-full-parity-contract"
CAPTURED_AT = "2026-07-18T21:44:20+08:00"

PREDECESSOR = {
    "source": (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-http-typed-normalization-anchor-contract.json"
    ),
    "contract_id": (
        "ti.phase4c.personal-bank-user-counts-http-typed-normalization-"
        "anchor-contract"
    ),
    "sha256": "c713aa04a82f340ea04fdd5ae870bd5cfae82f099101431c664f047c2d5218ca",
    "byte_count": 43_737,
    "status": "typed_normalization_checkpoint_externally_anchored_routes_pending",
}

BASE_SHA = "765e4470f1ddb60f0ce6f23227d6303961f47fcf"

WORKERS = {
    "p4c-pg": {
        "branch": "codex/parallel-p4c-pg",
        "implementation_commit": "0f584743dbdc187b6bc6fc67899a2d6718cb13c8",
        "handoff_commit": "32c01975decceafb70a4cc837c13671e004e7525",
        "evidence": "pg16_pg18_termination_fingerprints_complete",
        "paths": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4cUserCountsTerminationFingerprintIT.java",
            "server/src/test/java/io/saksk/ti/support/"
            "Phase4cUserCountsTerminationFingerprintSupport.java",
            "server/src/test/resources/db/phase4c/"
            "073-personal-bank-user-counts-termination-fingerprint-seed.sql",
        ),
    },
    "p4c-tomcat": {
        "branch": "codex/parallel-p4c-tomcat",
        "implementation_commit": "cd7eba9bbee4edcb6a0e14fec5fdfdf613d2ea70",
        "handoff_commit": "45c8723620723fcc6800e93740b634b2d83630ce",
        "evidence": "real_tomcat_complete_response_header_matrix_complete",
        "paths": (
            "server/src/test/java/io/saksk/ti/integration/"
            "LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.java",
        ),
    },
    "p4c-redis": {
        "branch": "codex/parallel-p4c-redis",
        "implementation_commit": "ad4d90b30cc5d244983fe759199f77ddeacdfc52",
        "handoff_commit": "e3c549fa06aeb1149f94b4f5385d1666f9ed7e0d",
        "evidence": "same_service_redis_outage_and_recovery_complete",
        "paths": (
            "server/src/test/java/io/saksk/ti/web/security/"
            "Phase4cUserCountsRedisOutageRecoveryIT.java",
            "server/src/test/java/io/saksk/ti/web/security/support/"
            "Phase4cRedisNetworkGate.java",
        ),
    },
}

ARTIFACTS = {
    "server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.java": (
        "cd9a45f6cfc52342d235202519ace13883e37354a901a790304739b7507501c9",
        40_107,
    ),
    "server/src/test/java/io/saksk/ti/integration/Phase4cUserCountsTerminationFingerprintIT.java": (
        "aa55869a57233a34ceae59773456cbb759670db1624b844cae75e664f8c0701a",
        26_069,
    ),
    "server/src/test/java/io/saksk/ti/support/Phase4cUserCountsTerminationFingerprintSupport.java": (
        "e4c4fc6f73b5ee9eebc3ab2e9904a51d6c593ed711b4aaaa39a79971e887ce42",
        25_907,
    ),
    "server/src/test/java/io/saksk/ti/web/security/Phase4cUserCountsRedisOutageRecoveryIT.java": (
        "b07ec534e41a74c1fddc3d9c2b63a6ae26f57ab8918112dc7799f10b479239c4",
        39_719,
    ),
    "server/src/test/java/io/saksk/ti/web/security/support/Phase4cRedisNetworkGate.java": (
        "ac3bab1cd092dcce640954c167baf4f7de5e53dee8579e77fb36d632c410b5ab",
        7_245,
    ),
    "server/src/test/resources/db/phase4c/073-personal-bank-user-counts-termination-fingerprint-seed.sql": (
        "33a6a4ce9845fe8b51ae6d5006af9a394bdc51d8427183d2775b2ef1cb4e6b40",
        843,
    ),
}

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpFullParitySuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpFullParityContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_full_parity_contract.py",
    "tools/phase4c_http_full_parity_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_full_parity_contract.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def payload_sha256(document: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }).encode("utf-8"))


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"full parity path escapes root: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"full parity path contains symlink: {relative}")
    resolved = (resolved_root / candidate).resolve(strict=True)
    resolved.relative_to(resolved_root)
    if not resolved.is_file():
        raise AssertionError(f"full parity path is not a regular file: {relative}")
    return resolved


def artifact_descriptor(root: Path, relative: str, expected: tuple[str, int]) -> dict[str, Any]:
    payload = fixed_regular_file(root, relative).read_bytes()
    actual = (sha256_bytes(payload), len(payload))
    if actual != expected:
        raise AssertionError(f"full parity fixed bytes drifted: {relative}")
    return {"sha256": actual[0], "byte_count": actual[1]}


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    predecessor_payload = fixed_regular_file(root, PREDECESSOR["source"]).read_bytes()
    if (sha256_bytes(predecessor_payload), len(predecessor_payload)) != (
        PREDECESSOR["sha256"], PREDECESSOR["byte_count"]
    ):
        raise AssertionError("full parity predecessor bytes drifted")

    descriptors = {
        relative: artifact_descriptor(root, relative, expected)
        for relative, expected in ARTIFACTS.items()
    }
    worker_documents = {}
    for lane, worker in WORKERS.items():
        worker_documents[lane] = {
            "base_sha": BASE_SHA,
            "branch": worker["branch"],
            "implementation_commit": worker["implementation_commit"],
            "handoff_commit": worker["handoff_commit"],
            "integrated_paths": list(worker["paths"]),
            "central_authority_files_modified_by_worker": False,
            "handoff_file_integrated_into_main": False,
            worker["evidence"]: True,
        }

    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": "phase4c-personal-bank-user-counts-http-full-target-parity-bootstrap",
        "status": "full_target_parity_closed_external_anchor_pending_routes_pending",
        "predecessor": {**PREDECESSOR, "immutable": True},
        "worker_integration": {
            "integration_method": "reviewed_cherry_pick_no_commit_fixed_implementation_objects",
            "base_sha": BASE_SHA,
            "lane_count": 3,
            "lanes": worker_documents,
            "artifact_count": len(descriptors),
            "artifacts": descriptors,
            "shared_production_code_changed_by_int": False,
        },
        "verification": {
            "toolchain": "Java 25 / Maven 3.9.16",
            "heavy_verify_lock_held_for_all_maven_testcontainers_docker": True,
            "targeted_command": (
                "./infra/phase2/verify-in-maven-container.sh "
                "-DargLine=-javaagent:/root/.m2/repository/org/mockito/"
                "mockito-core/5.23.0/mockito-core-5.23.0.jar "
                "-Dit.test=Phase4cUserCountsTerminationFingerprintIT,"
                "LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT,"
                "Phase4cUserCountsRedisOutageRecoveryIT test-compile "
                "failsafe:integration-test failsafe:verify"
            ),
            "targeted_failsafe_tests": 13,
            "targeted_failures_errors_skipped": 0,
            "full_command": (
                "./infra/phase2/verify-in-maven-container.sh "
                "-DargLine=-javaagent:/root/.m2/repository/org/mockito/"
                "mockito-core/5.23.0/mockito-core-5.23.0.jar clean verify"
            ),
            "full_surefire_tests": 709,
            "full_failsafe_tests": 167,
            "full_failures_errors_skipped": 0,
            "full_total_time": "07:02 min",
            "testcontainers_remaining_after_verification": 0,
        },
        "parity": {
            "pg16_pg18_termination_fingerprints_complete": True,
            "real_tomcat_complete_response_header_matrix_complete": True,
            "same_service_redis_outage_and_recovery_complete": True,
            "full_target_parity_closed": True,
            "all_required_parity_prerequisites_true": True,
            "typed_parity_review_complete": True,
        },
        "authorization": {
            "current_bootstrap_sources_external_git_anchor_complete": False,
            "route_migration_eligible": False,
            "two_legacy_get_routes_migrated": False,
            "production_cutover": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "next_gate": "fixed_git_external_anchor_of_full_parity_bootstrap_sources",
        },
        "route_state": {
            "total_operation_count": 611,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "implemented_pending_get_count": 2,
            "derived_head_and_options_count_as_operations": False,
        },
        "source_authority": {
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "excluded_from_self_authority": True,
            "historical_contracts_and_worm_overwritten": False,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


if __name__ == "__main__":
    print(serialized_contract(build_contract()).decode("utf-8"), end="")
