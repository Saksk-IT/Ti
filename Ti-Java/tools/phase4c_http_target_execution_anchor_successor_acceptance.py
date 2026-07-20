#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C external target anchor.

``load(root)`` validates only code-fixed files below ``root`` and never needs a
Git directory.  Callers that possess the parent repository may additionally
pass ``repository_root`` to replay the fixed commit/blob checks.  This module
does not import the anchor builder and does not accept its own bytes.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-anchor-contract.json"
)
CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-anchor-contract"
)
CONTRACT_STATUS = (
    "target_execution_bootstrap_externally_anchored_"
    "normalized_junit_manifest_bootstrap_bound_routes_pending"
)
CONTRACT_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-external-anchor"
)
CONTRACT_CAPTURED_AT = "2026-07-18T12:14:52+08:00"
CONTRACT_SHA256 = (
    "f966f9229949a37811da2402d3baf05dd78643ec4104a8f921dee10188bcd203"
)
CONTRACT_PAYLOAD_SHA256 = (
    "dbfe37e3e0d9b80ebb378a58b58aa7b15371d737b389f06f24f3018adb6b311e"
)
NEXT_GATE = (
    "commit_and_push_this_anchor_checkpoint_then_git_anchor_the_normalized_"
    "junit_manifest_bytes_before_typed_parity_network_redis_identity_review_"
    "or_route_migration"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-contract"
)
PREDECESSOR_STATUS = (
    "target_dispositions_executed_typed_parity_review_pending_routes_pending"
)
PREDECESSOR_SCOPE = "phase4c-personal-bank-user-counts-http-target-execution"
PREDECESSOR_CAPTURED_AT = "2026-07-18T10:00:00+08:00"
PREDECESSOR_SHA256 = (
    "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "331c82ad941f4eeb3e07d1701271310f2b1dea91132794e4e5d1eb1b466fc458"
)
PREDECESSOR_TRUST_PAYLOAD_SHA256 = (
    "0634daf8ba1489a3f4fa6f1f958ee5042113fb2e62e2af9f864159c14fd92500"
)

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "0531b3c9272f9743a374edcf5c8bbeb72643eb1b"
GIT_ROOT_TREE_OID = "816e2a7376d147f4a4d1478586cd384edf2c2a8a"
GIT_PARENT_OID = "67dddb831bac8499e80f4af57c959e9c6b244519"
TI_JAVA_TREE_OID = "1d24e46d33c25170caddf6e25247a7b2945390e4"
GIT_AUTHORED_AT = "2026-07-18T12:14:52+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "test(java): record user counts target execution bootstrap"

ANCHOR_ARTIFACTS = {
    "target_execution_contract": (
        PREDECESSOR_RELATIVE,
        f"Ti-Java/{PREDECESSOR_RELATIVE}",
        "575f05d4da531822e013d68eb6fb16a00f2bf8e0",
        PREDECESSOR_SHA256,
        74597,
    ),
    "python_successor_bridge": (
        "tools/phase4c_http_target_execution_successor_acceptance.py",
        "Ti-Java/tools/phase4c_http_target_execution_successor_acceptance.py",
        "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
        "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c",
        78481,
    ),
    "java_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
        "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
        "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
        "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15",
        88021,
    ),
    "target_execution_test": (
        "server/src/test/java/io/saksk/ti/integration/"
        "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java",
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java",
        "31a98f33aa2c8eb15a3476096965eb85d4912e06",
        "45b1a96fcc66a436551a8ce7604b304f2a479cece87c431a3a3c003da01d5ca1",
        44479,
    ),
    "target_execution_evidence": (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-golden-target-execution-evidence.json",
        "Ti-Java/docs/refactor/phase4c/"
        "personal-bank-user-counts-golden-target-execution-evidence.json",
        "bb07875497bc51179a3d7023ca6abf485bd11559",
        "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002",
        173397,
    ),
    "phase4b_golden": (
        "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
        "Ti-Java/docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
        "6421851f917765549c8b4df2b50f5be505f7d87c",
        "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1",
        1200690,
    ),
    "historical_mapping": (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-golden-target-mapping-evidence.json",
        "Ti-Java/docs/refactor/phase4c/"
        "personal-bank-user-counts-golden-target-mapping-evidence.json",
        "77a8dedfceaf14beeca2236e98092462a3be8eea",
        "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3",
        24595,
    ),
    "maven_runner": (
        "infra/phase2/verify-in-maven-container.sh",
        "Ti-Java/infra/phase2/verify-in-maven-container.sh",
        "22f1479dbf9124d9ce95762f9fac4ddaebf3a8f6",
        "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e",
        3131,
    ),
    "maven_project": (
        "server/pom.xml",
        "Ti-Java/server/pom.xml",
        "ce9264784f7a9394d567458b7dba8a1648bdbc21",
        "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b",
        9582,
    ),
    "maven_wrapper": (
        "server/.mvn/wrapper/maven-wrapper.properties",
        "Ti-Java/server/.mvn/wrapper/maven-wrapper.properties",
        "6b152042d1fd9f6218a72c60b449abbd3f149b2d",
        "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab",
        446,
    ),
}

JUNIT_MANIFEST_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-target-execution-junit-manifest.json"
)
JUNIT_MANIFEST_SHA256 = (
    "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b"
)
JUNIT_MANIFEST_PAYLOAD_SHA256 = (
    "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c"
)
JUNIT_LEAF_PAYLOAD_SHA256 = (
    "77b0f4955931f2ad3206b7a1c0f9c9649b25a18c49bf1b259c452d169e5f0e04"
)
JUNIT_RAW_REPORT_SHA256 = (
    "bb114a5571ef645ba37864dae1862a3657d92755a60479d734ce3c72f8de24ab"
)
JUNIT_RAW_REPORT_BYTE_COUNT = 63450

WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
WORM_SHA256 = (
    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
)
WORM_PREDECESSOR_SHA256 = (
    "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
)
DRIFT_MANIFEST_RELATIVE = "infra/phase2/reference-drift-manifest.json"
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
JAVA_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
CANONICAL_SCHEMA_DUMP_SHA256 = (
    "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
)

BRIDGE_SOURCE_KEYS = frozenset({
    "python_successor_bridge",
    "java_successor_bridge",
})
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _payload_sha256(document: dict[str, Any]) -> str:
    return _sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def _predecessor_trust_sha256(document: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    sources = payload.get("source_contracts")
    if not isinstance(sources, dict):
        raise AssertionError("target-execution predecessor sources are missing")
    normalized: dict[str, dict[str, Any]] = {}
    for name, reference in sources.items():
        if not isinstance(reference, dict):
            raise AssertionError(f"invalid predecessor source reference: {name}")
        item = dict(reference)
        if name in BRIDGE_SOURCE_KEYS:
            item["sha256"] = BRIDGE_PROVENANCE_SENTINEL
        normalized[name] = item
    return _sha256_json({**payload, "source_contracts": normalized})


def _fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed external-anchor path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"fixed external-anchor path contains symlink: {relative}"
            )
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed external-anchor path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(
            f"fixed external-anchor path is not a regular file: {relative}"
        )
    return resolved


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        document = json.loads(
            _fixed_regular_file(root, relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"cannot load fixed JSON: {relative}") from error
    if not isinstance(document, dict):
        raise AssertionError(f"fixed JSON is not an object: {relative}")
    return document


def _artifact_document() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "ti_java_relative_path": descriptor[0],
            "repository_path": descriptor[1],
            "object_type": "blob",
            "git_blob_oid": descriptor[2],
            "sha256": descriptor[3],
            "byte_count": descriptor[4],
        }
        for name, descriptor in sorted(ANCHOR_ARTIFACTS.items())
    }


def _validate_local_artifacts(root: Path) -> dict[str, Any]:
    predecessor_descriptor = ANCHOR_ARTIFACTS["target_execution_contract"]
    predecessor_path = _fixed_regular_file(root, PREDECESSOR_RELATIVE)
    predecessor_raw = predecessor_path.read_bytes()
    if (
        len(predecessor_raw) != predecessor_descriptor[4]
        or _sha256_bytes(predecessor_raw) != PREDECESSOR_SHA256
    ):
        raise AssertionError("external-anchor predecessor physical bytes drifted")
    predecessor = _read_json(root, PREDECESSOR_RELATIVE)
    if predecessor.get("contract_id") != PREDECESSOR_ID:
        raise AssertionError("external-anchor predecessor id drifted")
    if predecessor.get("status") != PREDECESSOR_STATUS:
        raise AssertionError("external-anchor predecessor status drifted")
    if predecessor.get("scope") != PREDECESSOR_SCOPE:
        raise AssertionError("external-anchor predecessor scope drifted")
    if predecessor.get("captured_at") != PREDECESSOR_CAPTURED_AT:
        raise AssertionError("external-anchor predecessor timestamp drifted")
    if predecessor.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("external-anchor predecessor payload field drifted")
    if _payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("external-anchor predecessor payload is invalid")
    if _predecessor_trust_sha256(predecessor) != PREDECESSOR_TRUST_PAYLOAD_SHA256:
        raise AssertionError("external-anchor predecessor trust payload drifted")
    provenance = predecessor.get("bridge_provenance", {})
    if provenance.get("external_bridge_bytes_anchor_complete") is not False:
        raise AssertionError("bootstrap predecessor no longer has its honest open anchor")
    return predecessor


def _validate_junit_manifest(root: Path) -> dict[str, Any]:
    path = _fixed_regular_file(root, JUNIT_MANIFEST_RELATIVE)
    if _sha256_bytes(path.read_bytes()) != JUNIT_MANIFEST_SHA256:
        raise AssertionError("normalized JUnit manifest physical hash drifted")
    manifest = _read_json(root, JUNIT_MANIFEST_RELATIVE)
    if set(manifest) != {
        "schema_version", "artifact_id", "status", "scope", "source_anchor",
        "source_inputs", "runner", "raw_report", "normalization_policy",
        "result", "confidentiality", "document_payload_sha256",
    }:
        raise AssertionError("normalized JUnit manifest top-level shape drifted")
    if manifest.get("schema_version") != 1:
        raise AssertionError("normalized JUnit manifest schema drifted")
    if manifest.get("artifact_id") != (
            "ti.phase4c.personal-bank-user-counts-target-execution-junit-manifest"):
        raise AssertionError("normalized JUnit manifest id drifted")
    if manifest.get("status") != "passed_normalized_sensitive_runtime_output_removed":
        raise AssertionError("normalized JUnit manifest status drifted")
    if manifest.get("scope") != (
            "phase4c-personal-bank-user-counts-target-execution-junit"):
        raise AssertionError("normalized JUnit manifest scope drifted")
    if manifest.get("document_payload_sha256") != JUNIT_MANIFEST_PAYLOAD_SHA256:
        raise AssertionError("normalized JUnit manifest payload field drifted")
    if _payload_sha256(manifest) != JUNIT_MANIFEST_PAYLOAD_SHA256:
        raise AssertionError("normalized JUnit manifest payload is invalid")

    source_anchor = manifest.get("source_anchor", {})
    if source_anchor.get("git_commit_sha1") != GIT_COMMIT_OID:
        raise AssertionError("normalized JUnit manifest commit drifted")
    if source_anchor.get("git_parent_sha1") != GIT_PARENT_OID:
        raise AssertionError("normalized JUnit manifest parent drifted")
    if source_anchor.get("git_root_tree_sha1") != GIT_ROOT_TREE_OID:
        raise AssertionError("normalized JUnit manifest root tree drifted")
    if source_anchor.get("ti_java_tree_sha1") != TI_JAVA_TREE_OID:
        raise AssertionError("normalized JUnit manifest subtree drifted")
    if source_anchor.get("capture_state_is_declared_metadata") is not True:
        raise AssertionError("normalized JUnit capture-state boundary drifted")
    if source_anchor.get("normalizer_does_not_revalidate_mutable_remote_ref") is not True:
        raise AssertionError("normalized JUnit mutable-ref boundary drifted")

    source_inputs = manifest.get("source_inputs")
    if not isinstance(source_inputs, dict) or set(source_inputs) != set(
            ANCHOR_ARTIFACTS):
        raise AssertionError("normalized JUnit source-input set drifted")
    for name, descriptor in ANCHOR_ARTIFACTS.items():
        reference = source_inputs.get(name)
        if not isinstance(reference, dict):
            raise AssertionError(f"normalized JUnit source is missing: {name}")
        if reference.get("path") != descriptor[0]:
            raise AssertionError(f"normalized JUnit source path drifted: {name}")
        if reference.get("sha256") != descriptor[3]:
            raise AssertionError(f"normalized JUnit source hash drifted: {name}")

    result = manifest.get("result", {})
    if result.get("totals") != {
        "tests": 60, "passed": 60, "failures": 0, "errors": 0,
        "skipped": 0, "flakes": 0,
    }:
        raise AssertionError("normalized JUnit totals drifted")
    leaves = result.get("leaves")
    if not isinstance(leaves, list) or len(leaves) != 60:
        raise AssertionError("normalized JUnit leaf count drifted")
    if _sha256_json(leaves) != JUNIT_LEAF_PAYLOAD_SHA256:
        raise AssertionError("normalized JUnit leaf payload drifted")
    if result.get("leaf_payload_sha256") != JUNIT_LEAF_PAYLOAD_SHA256:
        raise AssertionError("normalized JUnit leaf field drifted")
    raw = manifest.get("raw_report", {})
    if raw.get("sha256") != JUNIT_RAW_REPORT_SHA256:
        raise AssertionError("normalized JUnit raw report hash drifted")
    if raw.get("byte_count") != JUNIT_RAW_REPORT_BYTE_COUNT:
        raise AssertionError("normalized JUnit raw report size drifted")
    if any(raw.get(field) is not False for field in (
            "tracked", "committed", "content_embedded")):
        raise AssertionError("normalized JUnit raw report escaped its boundary")
    confidentiality = manifest.get("confidentiality", {})
    if confidentiality.get("sensitive_output_scan_passed") is not True:
        raise AssertionError("normalized JUnit sensitive-output gate is open")
    if confidentiality.get("independently_signed_provenance") is not False:
        raise AssertionError("normalized JUnit overclaims signed provenance")
    if confidentiality.get("repository_tamper_evident") is not False:
        raise AssertionError("normalized JUnit overclaims repository anchoring")
    if confidentiality.get("manifest_bytes_external_git_anchor_complete") is not False:
        raise AssertionError("normalized JUnit overclaims external byte anchoring")
    if confidentiality.get("post_push_successor_anchor_required") is not True:
        raise AssertionError("normalized JUnit lost its post-push anchor gate")
    if manifest.get("normalization_policy", {}).get("raw_report_hash_role") != (
            "single_execution_binding_not_cross_run_stability"):
        raise AssertionError("normalized JUnit raw-report hash boundary drifted")
    return manifest


def _validate_worm(root: Path) -> None:
    path = _fixed_regular_file(root, WORM_RELATIVE)
    if _sha256_bytes(path.read_bytes()) != WORM_SHA256:
        raise AssertionError("fifth WORM physical SHA-256 drifted")
    worm = _read_json(root, WORM_RELATIVE)
    if set(worm) != {
        "schemaVersion", "capturedAt", "source", "restore", "readRole",
        "java", "productionDatabaseVersion", "flywayBaselineCreated",
    }:
        raise AssertionError("fifth WORM top-level shape drifted")
    if worm.get("schemaVersion") != 1:
        raise AssertionError("fifth WORM schema drifted")
    if worm.get("source", {}).get("serverVersion") != "18.4":
        raise AssertionError("fifth WORM source version drifted")
    restore = worm.get("restore", {})
    if restore.get("serverVersion") != "18.4":
        raise AssertionError("fifth WORM restored version drifted")
    if worm.get("restore", {}).get("canonicalSchemaDumpSha256") != (
            CANONICAL_SCHEMA_DUMP_SHA256):
        raise AssertionError("fifth WORM canonical schema digest drifted")
    if restore.get("schemaDumpPersisted") is not False:
        raise AssertionError("fifth WORM persisted its schema dump")
    expected_read_role = {
        "selectPassed": True,
        "defaultTransactionReadOnly": True,
        "temporaryPrivilege": False,
        "aclVerifiedWithReadOnlyDefaultDisabled": True,
        "insertRejected": True,
        "updateRejected": True,
        "deleteRejected": True,
        "ddlRejected": True,
        "temporaryDdlRejected": True,
    }
    if worm.get("readRole") != expected_read_role:
        raise AssertionError("fifth WORM read-role ACL evidence drifted")
    java = worm.get("java", {})
    if java.get("dockerfileSha256") != DOCKERFILE_SHA256:
        raise AssertionError("fifth WORM Dockerfile digest drifted")
    if java.get("buildContextSha256") != JAVA_BUILD_CONTEXT_SHA256:
        raise AssertionError("fifth WORM build-context digest drifted")
    if java.get("hibernateDdlAuto") != "validate":
        raise AssertionError("fifth WORM Hibernate mode drifted")
    if java.get("startupPassed") is not True or java.get("readinessPassed") is not True:
        raise AssertionError("fifth WORM startup/readiness drifted")
    if worm.get("productionDatabaseVersion") != "unknown":
        raise AssertionError("fifth WORM production-version boundary drifted")
    if worm.get("flywayBaselineCreated") is not False:
        raise AssertionError("fifth WORM Flyway boundary drifted")

    def scalar_values(node: Any):
        if isinstance(node, dict):
            for value in node.values():
                yield from scalar_values(value)
        elif isinstance(node, list):
            for value in node:
                yield from scalar_values(value)
        else:
            yield node

    strings = [value for value in scalar_values(worm) if isinstance(value, str)]
    if any(value.startswith("/") for value in strings):
        raise AssertionError("fifth WORM leaked an absolute path")
    serialized = json.dumps(worm, sort_keys=True).lower()
    for forbidden in ("password", "secret", "ti-postgres-1", "studyuser", "ti_db"):
        if forbidden in serialized:
            raise AssertionError(
                f"fifth WORM leaked a sensitive identifier: {forbidden}"
            )


def _replay_phase2_fixed_acceptance(ti_java_root: Path) -> None:
    """Lazily import and replay Phase 2 only for an explicit caller."""
    try:
        from tools import phase2_wormhole_successor_acceptance as phase2_worm
    except ModuleNotFoundError as error:  # Direct execution from tools/.
        if error.name not in {
            "tools",
            "tools.phase2_wormhole_successor_acceptance",
        }:
            raise
        import phase2_wormhole_successor_acceptance as phase2_worm

    root = ti_java_root.resolve(strict=True)
    result = subprocess.run(
        [str(_fixed_regular_file(root, "infra/phase2/hash-java-build-context.sh"))],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    physical_build_context = result.stdout.strip()
    if physical_build_context == JAVA_BUILD_CONTEXT_SHA256:
        tip = phase2_worm.validate_evidence_chain(
            root,
            _fixed_regular_file(root, DRIFT_MANIFEST_RELATIVE),
            DOCKERFILE_SHA256,
            JAVA_BUILD_CONTEXT_SHA256,
            chain=phase2_worm.FIXED_EVIDENCE_CHAIN[:5],
            immutable_mirrors=phase2_worm.FIXED_IMMUTABLE_MIRRORS,
        )
        if (
            tip.label != "phase4c-personal-bank-user-counts-http-implementation"
            or tip.relative_path != WORM_RELATIVE
            or tip.sha256 != WORM_SHA256
            or tip.predecessor_sha256 != WORM_PREDECESSOR_SHA256
            or tip.dockerfile_sha256 != DOCKERFILE_SHA256
            or tip.build_context_sha256 != JAVA_BUILD_CONTEXT_SHA256
        ):
            raise AssertionError("Phase 2 historical fifth WORM replay drifted")
        return

    try:
        from tools.phase4c_tag_migration_global_preflight_successor_acceptance import (
            validate_worm_successor,
        )
    except ModuleNotFoundError as error:  # Direct execution from tools/.
        if error.name not in {
            "tools",
            "tools.phase4c_tag_migration_global_preflight_successor_acceptance",
        }:
            raise
        from phase4c_tag_migration_global_preflight_successor_acceptance import (
            validate_worm_successor,
        )
    successor = validate_worm_successor(
        root, WORM_SHA256, JAVA_BUILD_CONTEXT_SHA256
    )
    tip = phase2_worm.validate_fixed_acceptance(
        root,
        _fixed_regular_file(root, DRIFT_MANIFEST_RELATIVE),
        DOCKERFILE_SHA256,
        successor.current_build_context_sha256,
    )
    if (
        successor.accepted_report_sha256 != WORM_SHA256
        or successor.accepted_build_context_sha256 != JAVA_BUILD_CONTEXT_SHA256
        or successor.accepted_chain_node_count != 5
        or tip.sha256 != successor.current_report_sha256
        or tip.dockerfile_sha256 != DOCKERFILE_SHA256
        or tip.build_context_sha256 != successor.current_build_context_sha256
        or successor.current_chain_node_count != 8
    ):
        raise AssertionError("Phase 2 terminal WORM successor replay drifted")


def validate_contract(document: dict[str, Any], ti_java_root: Path) -> None:
    if not isinstance(document, dict):
        raise AssertionError("external-anchor contract is not a JSON object")
    if set(document) != {
        "contract_id", "schema_version", "captured_at", "status", "scope",
        "predecessor", "git_anchor", "external_anchor", "junit_manifest",
        "worm_evidence", "authorization", "acceptance",
        "document_payload_sha256",
    }:
        raise AssertionError("external-anchor contract top-level shape drifted")
    if document.get("schema_version") != 1:
        raise AssertionError("external-anchor contract schema drifted")
    if document.get("contract_id") != CONTRACT_ID:
        raise AssertionError("external-anchor contract id drifted")
    if document.get("status") != CONTRACT_STATUS:
        raise AssertionError("external-anchor contract status drifted")
    if document.get("scope") != CONTRACT_SCOPE:
        raise AssertionError("external-anchor contract scope drifted")
    if document.get("captured_at") != CONTRACT_CAPTURED_AT:
        raise AssertionError("external-anchor contract timestamp drifted")
    if document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256:
        raise AssertionError("external-anchor payload field drifted")
    if _payload_sha256(document) != CONTRACT_PAYLOAD_SHA256:
        raise AssertionError("external-anchor document payload is invalid")

    expected_predecessor = {
        "source": PREDECESSOR_RELATIVE,
        "sha256": PREDECESSOR_SHA256,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "trust_payload_sha256": PREDECESSOR_TRUST_PAYLOAD_SHA256,
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "immutable": True,
    }
    if document.get("predecessor") != expected_predecessor:
        raise AssertionError("external-anchor predecessor reference drifted")

    expected_git_anchor = {
        "state": "fixed_pushed_bootstrap_commit_objects_verified",
        "object_format": GIT_OBJECT_FORMAT,
        "commit_oid": GIT_COMMIT_OID,
        "root_tree_oid": GIT_ROOT_TREE_OID,
        "parent_oid": GIT_PARENT_OID,
        "ti_java_subtree": "Ti-Java",
        "ti_java_tree_oid": TI_JAVA_TREE_OID,
        "authored_at": GIT_AUTHORED_AT,
        "committed_at": GIT_COMMITTED_AT,
        "subject": GIT_SUBJECT,
        "remote_ref_at_capture": "origin/main",
        "mutable_ref_is_not_validation_authority": True,
        "artifact_paths_are_code_fixed": True,
        "artifacts": _artifact_document(),
    }
    if document.get("git_anchor") != expected_git_anchor:
        raise AssertionError("external-anchor Git object declaration drifted")
    expected_external = {
        "state": "target_execution_bootstrap_contract_and_bridge_bytes_anchored",
        "anchored_artifact_count": 10,
        "anchored_artifact_keys": sorted(ANCHOR_ARTIFACTS),
        "external_git_and_bridge_bytes_anchor_complete": True,
        "predecessor_rewrite_forbidden": True,
        "arbitrary_git_object_lookup_forbidden": True,
        "dynamic_source_discovery_forbidden": True,
        "current_anchor_bridge_self_authorization_forbidden": True,
    }
    if document.get("external_anchor") != expected_external:
        raise AssertionError("external-anchor completion boundary drifted")

    expected_junit = {
        "source": JUNIT_MANIFEST_RELATIVE,
        "sha256": JUNIT_MANIFEST_SHA256,
        "document_payload_sha256": JUNIT_MANIFEST_PAYLOAD_SHA256,
        "leaf_payload_sha256": JUNIT_LEAF_PAYLOAD_SHA256,
        "raw_report_sha256": JUNIT_RAW_REPORT_SHA256,
        "raw_report_byte_count": JUNIT_RAW_REPORT_BYTE_COUNT,
        "tests": 60,
        "passed": 60,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "flakes": 0,
        "normalized_junit_manifest_bound": True,
        "manifest_bytes_external_git_anchor_complete": False,
        "post_push_successor_anchor_required": True,
        "raw_report_not_tracked_or_embedded": True,
        "independently_signed_provenance": False,
    }
    if document.get("junit_manifest") != expected_junit:
        raise AssertionError("external-anchor JUnit manifest boundary drifted")

    expected_worm = {
        "source": WORM_RELATIVE,
        "sha256": WORM_SHA256,
        "fixed_chain_node_count": 5,
        "predecessor_sha256": WORM_PREDECESSOR_SHA256,
        "dockerfile_sha256": DOCKERFILE_SHA256,
        "java_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
        "canonical_schema_dump_sha256": CANONICAL_SCHEMA_DUMP_SHA256,
        "phase2_fixed_acceptance_closed": True,
        "temporary_privilege": False,
        "sensitive_information_scan_passed": True,
        "new_worm": False,
        "new_worm_report_created": False,
        "production_build_context_unchanged": True,
        "read_role_closed": True,
        "hibernate_schema_mode": "validate",
        "production_schema_or_index_changed": False,
        "operator_migration_executed": False,
        "real_data_migration_executed": False,
        "production_cutover": False,
    }
    if document.get("worm_evidence") != expected_worm:
        raise AssertionError("external-anchor fifth WORM boundary drifted")

    expected_authorization = {
        "external_git_and_bridge_bytes_anchor_complete": True,
        "normalized_junit_manifest_bound": True,
        "junit_manifest_tests_passed": True,
        "junit_manifest_bytes_external_git_anchor_complete": False,
        "post_push_junit_manifest_successor_anchor_required": True,
        "typed_parity_review_complete": False,
        "full_target_parity_closed": False,
        "route_migration_eligible": False,
        "two_legacy_get_routes_migrated": False,
        "derived_head_and_options_count_as_migrated": False,
        "production_schema_or_index": False,
        "operator_migration_implementation": False,
        "real_data_migration_execution": False,
        "migration_global_preflight_closed": False,
        "client_change": False,
        "gateway_or_proxy_change": False,
        "production_cutover": False,
    }
    if document.get("authorization") != expected_authorization:
        raise AssertionError("external-anchor authorization boundary drifted")
    expected_acceptance = {
        "external_git_and_bridge_bytes_anchor_complete": True,
        "normalized_junit_manifest_bound": True,
        "junit_manifest_tests": 60,
        "junit_manifest_passed": 60,
        "junit_manifest_bytes_external_git_anchor_complete": False,
        "post_push_junit_manifest_successor_anchor_required": True,
        "typed_parity_review_complete": False,
        "full_target_parity_closed": False,
        "route_migration_eligible": False,
        "implemented_pending_get_count": 2,
        "migrated_operation_count": 11,
        "pending_operation_count": 600,
        "production_cutover_operation_count": 0,
        "production_cutover": False,
        "new_worm": False,
        "production_build_context_unchanged": True,
        "operator_and_real_migration_remain_blocked": True,
        "next_gate": NEXT_GATE,
    }
    if document.get("acceptance") != expected_acceptance:
        raise AssertionError("external-anchor acceptance boundary drifted")

    root = ti_java_root.resolve(strict=True)
    _validate_local_artifacts(root)
    _validate_junit_manifest(root)
    _validate_worm(root)


def _run_read_only_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            [
                "git", "--no-optional-locks", "-C", str(repository_root),
                *arguments,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssertionError(
            f"read-only Git command failed: {arguments[0]}"
        ) from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
        raise AssertionError(
            f"read-only Git command rejected {arguments[0]}: {detail}"
        )
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_read_only_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_anchor(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    top = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise AssertionError("Git repository root was not passed explicitly")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("Git object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit":
        raise AssertionError("fixed Git anchor is not a commit")
    if _git_text(root, "rev-parse", "--verify", f"{GIT_COMMIT_OID}^{{commit}}") != (
            GIT_COMMIT_OID):
        raise AssertionError("fixed Git anchor resolved unexpectedly")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}^{{tree}}") != (
            GIT_ROOT_TREE_OID):
        raise AssertionError("fixed Git root tree drifted")
    if _git_text(root, "show", "-s", "--format=%P", GIT_COMMIT_OID) != GIT_PARENT_OID:
        raise AssertionError("fixed Git parent drifted")
    if _git_text(root, "show", "-s", "--format=%aI", GIT_COMMIT_OID) != GIT_AUTHORED_AT:
        raise AssertionError("fixed Git author timestamp drifted")
    if _git_text(root, "show", "-s", "--format=%cI", GIT_COMMIT_OID) != GIT_COMMITTED_AT:
        raise AssertionError("fixed Git committer timestamp drifted")
    if _git_text(root, "show", "-s", "--format=%s", GIT_COMMIT_OID) != GIT_SUBJECT:
        raise AssertionError("fixed Git subject drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java") != TI_JAVA_TREE_OID:
        raise AssertionError("fixed Git Ti-Java tree drifted")
    if _git_text(root, "cat-file", "-t", f"{GIT_COMMIT_OID}:Ti-Java") != "tree":
        raise AssertionError("fixed Git Ti-Java object is not a tree")
    for name, descriptor in ANCHOR_ARTIFACTS.items():
        object_name = f"{GIT_COMMIT_OID}:{descriptor[1]}"
        if _git_text(root, "cat-file", "-t", object_name) != "blob":
            raise AssertionError(f"fixed Git artifact is not a blob: {name}")
        if _git_text(root, "rev-parse", object_name) != descriptor[2]:
            raise AssertionError(f"fixed Git blob OID drifted: {name}")
        raw = _run_read_only_git(root, "show", object_name)
        if len(raw) != descriptor[4] or _sha256_bytes(raw) != descriptor[3]:
            raise AssertionError(f"fixed Git artifact bytes drifted: {name}")


def load(
    ti_java_root: Path,
    *,
    repository_root: Path | None = None,
    replay_phase2_fixed_acceptance: bool = False,
) -> dict[str, Any]:
    """Load the fixed anchor; Git replay is opt-in and never implicit."""
    root = ti_java_root.resolve(strict=True)
    contract_path = _fixed_regular_file(root, CONTRACT_RELATIVE)
    if _sha256_bytes(contract_path.read_bytes()) != CONTRACT_SHA256:
        raise AssertionError("external-anchor contract physical SHA-256 drifted")
    contract = _read_json(root, CONTRACT_RELATIVE)
    validate_contract(contract, root)
    if replay_phase2_fixed_acceptance:
        _replay_phase2_fixed_acceptance(root)
    if repository_root is not None:
        validate_git_anchor(repository_root)
    return contract


def anchored_sha256(relative: str) -> str | None:
    """Return one code-fixed committed artifact hash; unknown paths stay closed."""
    matches = [descriptor[3] for descriptor in ANCHOR_ARTIFACTS.values()
               if descriptor[0] == relative]
    return matches[0] if len(matches) == 1 else None
