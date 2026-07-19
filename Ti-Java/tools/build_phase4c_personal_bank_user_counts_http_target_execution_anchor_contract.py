#!/usr/bin/env python3
"""Build the add-only external Git anchor for the Phase 4C target execution.

The anchor is intentionally asymmetric: it fixes the already-pushed bootstrap
commit and the physical bytes of its contract and two acceptance bridges.  It
does not put this builder, the new acceptance bridge, or its test into an
accepted-source map, so this node cannot authorize its own validator bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
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
CAPTURED_AT = "2026-07-18T12:14:52+08:00"
NEXT_GATE = (
    "commit_and_push_this_anchor_checkpoint_then_git_anchor_the_normalized_"
    "junit_manifest_bytes_before_typed_parity_network_redis_identity_review_"
    "or_route_migration"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-contract.json"
)
PREDECESSOR_REPOSITORY_PATH = f"Ti-Java/{PREDECESSOR_RELATIVE}"
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-contract"
)
PREDECESSOR_STATUS = (
    "target_dispositions_executed_typed_parity_review_pending_routes_pending"
)
PREDECESSOR_SCOPE = "phase4c-personal-bank-user-counts-http-target-execution"
PREDECESSOR_SHA256 = (
    "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "331c82ad941f4eeb3e07d1701271310f2b1dea91132794e4e5d1eb1b466fc458"
)
PREDECESSOR_TRUST_PAYLOAD_SHA256 = (
    "0634daf8ba1489a3f4fa6f1f958ee5042113fb2e62e2af9f864159c14fd92500"
)
PREDECESSOR_CAPTURED_AT = "2026-07-18T10:00:00+08:00"

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "0531b3c9272f9743a374edcf5c8bbeb72643eb1b"
GIT_ROOT_TREE_OID = "816e2a7376d147f4a4d1478586cd384edf2c2a8a"
GIT_PARENT_OID = "67dddb831bac8499e80f4af57c959e9c6b244519"
TI_JAVA_TREE_OID = "1d24e46d33c25170caddf6e25247a7b2945390e4"
GIT_COMMITTED_AT = "2026-07-18T12:14:52+08:00"
GIT_AUTHORED_AT = GIT_COMMITTED_AT
GIT_SUBJECT = "test(java): record user counts target execution bootstrap"
GIT_REMOTE_REF_AT_CAPTURE = "origin/main"

PYTHON_BRIDGE_RELATIVE = (
    "tools/phase4c_http_target_execution_successor_acceptance.py"
)
JAVA_BRIDGE_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
)

# Exact committed artifact descriptors.  Paths and hashes are code, never
# supplied by the contract being generated or validated.
ANCHOR_ARTIFACTS = {
    "target_execution_contract": {
        "ti_java_relative_path": PREDECESSOR_RELATIVE,
        "repository_path": PREDECESSOR_REPOSITORY_PATH,
        "git_blob_oid": "575f05d4da531822e013d68eb6fb16a00f2bf8e0",
        "sha256": PREDECESSOR_SHA256,
        "byte_count": 74597,
    },
    "python_successor_bridge": {
        "ti_java_relative_path": PYTHON_BRIDGE_RELATIVE,
        "repository_path": f"Ti-Java/{PYTHON_BRIDGE_RELATIVE}",
        "git_blob_oid": "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
        "sha256": (
            "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c"
        ),
        "byte_count": 78481,
    },
    "java_successor_bridge": {
        "ti_java_relative_path": JAVA_BRIDGE_RELATIVE,
        "repository_path": f"Ti-Java/{JAVA_BRIDGE_RELATIVE}",
        "git_blob_oid": "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
        "sha256": (
            "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15"
        ),
        "byte_count": 88021,
    },
    "target_execution_test": {
        "ti_java_relative_path": (
            "server/src/test/java/io/saksk/ti/integration/"
            "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java"
        ),
        "repository_path": (
            "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
            "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java"
        ),
        "git_blob_oid": "31a98f33aa2c8eb15a3476096965eb85d4912e06",
        "sha256": (
            "45b1a96fcc66a436551a8ce7604b304f2a479cece87c431a3a3c003da01d5ca1"
        ),
        "byte_count": 44479,
    },
    "target_execution_evidence": {
        "ti_java_relative_path": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-golden-target-execution-evidence.json"
        ),
        "repository_path": (
            "Ti-Java/docs/refactor/phase4c/"
            "personal-bank-user-counts-golden-target-execution-evidence.json"
        ),
        "git_blob_oid": "bb07875497bc51179a3d7023ca6abf485bd11559",
        "sha256": (
            "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002"
        ),
        "byte_count": 173397,
    },
    "phase4b_golden": {
        "ti_java_relative_path": (
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
        ),
        "repository_path": (
            "Ti-Java/docs/refactor/phase4b/"
            "golden-personal-bank-user-counts-reads.json"
        ),
        "git_blob_oid": "6421851f917765549c8b4df2b50f5be505f7d87c",
        "sha256": (
            "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1"
        ),
        "byte_count": 1200690,
    },
    "historical_mapping": {
        "ti_java_relative_path": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-golden-target-mapping-evidence.json"
        ),
        "repository_path": (
            "Ti-Java/docs/refactor/phase4c/"
            "personal-bank-user-counts-golden-target-mapping-evidence.json"
        ),
        "git_blob_oid": "77a8dedfceaf14beeca2236e98092462a3be8eea",
        "sha256": (
            "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3"
        ),
        "byte_count": 24595,
    },
    "maven_runner": {
        "ti_java_relative_path": "infra/phase2/verify-in-maven-container.sh",
        "repository_path": "Ti-Java/infra/phase2/verify-in-maven-container.sh",
        "git_blob_oid": "22f1479dbf9124d9ce95762f9fac4ddaebf3a8f6",
        "sha256": (
            "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e"
        ),
        "byte_count": 3131,
    },
    "maven_project": {
        "ti_java_relative_path": "server/pom.xml",
        "repository_path": "Ti-Java/server/pom.xml",
        "git_blob_oid": "ce9264784f7a9394d567458b7dba8a1648bdbc21",
        "sha256": (
            "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b"
        ),
        "byte_count": 9582,
    },
    "maven_wrapper": {
        "ti_java_relative_path": (
            "server/.mvn/wrapper/maven-wrapper.properties"
        ),
        "repository_path": (
            "Ti-Java/server/.mvn/wrapper/maven-wrapper.properties"
        ),
        "git_blob_oid": "6b152042d1fd9f6218a72c60b449abbd3f149b2d",
        "sha256": (
            "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab"
        ),
        "byte_count": 446,
    },
}

JUNIT_MANIFEST_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-target-execution-junit-manifest.json"
)
JUNIT_MANIFEST_ID = (
    "ti.phase4c.personal-bank-user-counts-target-execution-junit-manifest"
)
JUNIT_MANIFEST_STATUS = "passed_normalized_sensitive_runtime_output_removed"
JUNIT_MANIFEST_SCOPE = "phase4c-personal-bank-user-counts-target-execution-junit"
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
CANONICAL_SCHEMA_DUMP_SHA256 = (
    "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
)
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
JAVA_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)

BRIDGE_SOURCE_KEYS = frozenset({
    "python_successor_bridge",
    "java_successor_bridge",
})
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def predecessor_trust_payload_sha256(document: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    sources = payload.get("source_contracts")
    if not isinstance(sources, dict):
        raise ValueError("target-execution source contracts are missing")
    normalized: dict[str, dict[str, Any]] = {}
    for name, reference in sources.items():
        if not isinstance(reference, dict):
            raise ValueError(f"invalid target-execution source reference: {name}")
        item = dict(reference)
        if name in BRIDGE_SOURCE_KEYS:
            item["sha256"] = BRIDGE_PROVENANCE_SENTINEL
        normalized[name] = item
    return sha256_json({**payload, "source_contracts": normalized})


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"fixed anchor path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"fixed anchor path contains symlink: {relative}")
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise ValueError(f"fixed anchor path escaped or vanished: {relative}") from error
    if not resolved.is_file():
        raise ValueError(f"fixed anchor path is not a regular file: {relative}")
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load fixed JSON: {path}") from error
    if not isinstance(document, dict):
        raise ValueError(f"fixed JSON is not an object: {path}")
    return document


def validate_local_bootstrap(ti_java_root: Path) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    predecessor_path = fixed_regular_file(root, PREDECESSOR_RELATIVE)
    predecessor_descriptor = ANCHOR_ARTIFACTS["target_execution_contract"]
    predecessor_raw = predecessor_path.read_bytes()
    if len(predecessor_raw) != predecessor_descriptor["byte_count"]:
        raise ValueError("target-execution predecessor byte count drifted")
    if sha256_bytes(predecessor_raw) != PREDECESSOR_SHA256:
        raise ValueError("target-execution predecessor physical SHA-256 drifted")
    predecessor = read_json(predecessor_path)
    expected_identity = {
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "captured_at": PREDECESSOR_CAPTURED_AT,
    }
    if {key: predecessor.get(key) for key in expected_identity} != expected_identity:
        raise ValueError("target-execution predecessor identity drifted")
    if predecessor.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("target-execution predecessor payload field drifted")
    if document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("target-execution predecessor payload is invalid")
    if predecessor_trust_payload_sha256(predecessor) != (
            PREDECESSOR_TRUST_PAYLOAD_SHA256):
        raise ValueError("target-execution predecessor trust payload drifted")
    bridge = predecessor.get("bridge_provenance", {})
    if bridge.get("external_bridge_bytes_anchor_complete") is not False:
        raise ValueError("bootstrap predecessor no longer records its honest open anchor")
    if bridge.get("post_push_external_git_anchor_required_before_route_promotion") is not True:
        raise ValueError("bootstrap predecessor lost its post-push anchor requirement")
    return predecessor


def validate_junit_manifest(ti_java_root: Path) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    path = fixed_regular_file(root, JUNIT_MANIFEST_RELATIVE)
    if sha256_bytes(path.read_bytes()) != JUNIT_MANIFEST_SHA256:
        raise ValueError("normalized JUnit manifest physical SHA-256 drifted")
    manifest = read_json(path)
    expected_identity = {
        "schema_version": 1,
        "artifact_id": JUNIT_MANIFEST_ID,
        "status": JUNIT_MANIFEST_STATUS,
        "scope": JUNIT_MANIFEST_SCOPE,
    }
    if {key: manifest.get(key) for key in expected_identity} != expected_identity:
        raise ValueError("normalized JUnit manifest identity drifted")
    if manifest.get("document_payload_sha256") != JUNIT_MANIFEST_PAYLOAD_SHA256:
        raise ValueError("normalized JUnit manifest payload field drifted")
    if document_payload_sha256(manifest) != JUNIT_MANIFEST_PAYLOAD_SHA256:
        raise ValueError("normalized JUnit manifest payload is invalid")

    source_anchor = manifest.get("source_anchor", {})
    if source_anchor.get("git_commit_sha1") != GIT_COMMIT_OID:
        raise ValueError("normalized JUnit manifest commit anchor drifted")
    if source_anchor.get("git_parent_sha1") != GIT_PARENT_OID:
        raise ValueError("normalized JUnit manifest parent anchor drifted")
    if source_anchor.get("git_root_tree_sha1") != GIT_ROOT_TREE_OID:
        raise ValueError("normalized JUnit manifest root tree drifted")
    if source_anchor.get("ti_java_tree_sha1") != TI_JAVA_TREE_OID:
        raise ValueError("normalized JUnit manifest Ti-Java tree drifted")
    if source_anchor.get("capture_state_is_declared_metadata") is not True:
        raise ValueError("normalized JUnit capture-state boundary drifted")
    if source_anchor.get("normalizer_does_not_revalidate_mutable_remote_ref") is not True:
        raise ValueError("normalized JUnit mutable-ref boundary drifted")

    result = manifest.get("result", {})
    totals = result.get("totals")
    if totals != {
        "tests": 60,
        "passed": 60,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "flakes": 0,
    }:
        raise ValueError("normalized JUnit manifest totals drifted")
    leaves = result.get("leaves")
    if not isinstance(leaves, list) or len(leaves) != 60:
        raise ValueError("normalized JUnit manifest leaf count drifted")
    if sha256_json(leaves) != JUNIT_LEAF_PAYLOAD_SHA256:
        raise ValueError("normalized JUnit manifest leaf payload drifted")
    if result.get("leaf_payload_sha256") != JUNIT_LEAF_PAYLOAD_SHA256:
        raise ValueError("normalized JUnit manifest leaf payload field drifted")
    raw_report = manifest.get("raw_report", {})
    if raw_report.get("sha256") != JUNIT_RAW_REPORT_SHA256:
        raise ValueError("normalized JUnit raw report hash drifted")
    if raw_report.get("byte_count") != JUNIT_RAW_REPORT_BYTE_COUNT:
        raise ValueError("normalized JUnit raw report byte count drifted")
    if any(raw_report.get(field) is not False for field in (
            "tracked", "committed", "content_embedded")):
        raise ValueError("normalized JUnit manifest embedded or committed raw output")
    confidentiality = manifest.get("confidentiality", {})
    if confidentiality.get("sensitive_output_scan_passed") is not True:
        raise ValueError("normalized JUnit manifest sensitive-output gate is open")
    if confidentiality.get("independently_signed_provenance") is not False:
        raise ValueError("normalized JUnit manifest overclaims signed provenance")
    if confidentiality.get("repository_tamper_evident") is not False:
        raise ValueError("normalized JUnit manifest overclaims repository anchoring")
    if confidentiality.get("manifest_bytes_external_git_anchor_complete") is not False:
        raise ValueError("normalized JUnit manifest overclaims external byte anchoring")
    if confidentiality.get("post_push_successor_anchor_required") is not True:
        raise ValueError("normalized JUnit manifest lost its post-push anchor gate")
    if manifest.get("normalization_policy", {}).get("raw_report_hash_role") != (
            "single_execution_binding_not_cross_run_stability"):
        raise ValueError("normalized JUnit raw-report hash boundary drifted")
    return manifest


def validate_fifth_worm(ti_java_root: Path) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    path = fixed_regular_file(root, WORM_RELATIVE)
    if sha256_bytes(path.read_bytes()) != WORM_SHA256:
        raise ValueError("fifth WORM physical SHA-256 drifted")
    worm = read_json(path)
    if set(worm) != {
        "schemaVersion", "capturedAt", "source", "restore", "readRole",
        "java", "productionDatabaseVersion", "flywayBaselineCreated",
    }:
        raise ValueError("fifth WORM top-level shape drifted")
    if worm.get("schemaVersion") != 1:
        raise ValueError("fifth WORM schema drifted")
    if worm.get("source", {}).get("serverVersion") != "18.4":
        raise ValueError("fifth WORM PostgreSQL source version drifted")
    if worm.get("restore", {}).get("serverVersion") != "18.4":
        raise ValueError("fifth WORM restored PostgreSQL version drifted")
    if worm.get("restore", {}).get("canonicalSchemaDumpSha256") != (
            CANONICAL_SCHEMA_DUMP_SHA256):
        raise ValueError("fifth WORM canonical schema digest drifted")
    if worm.get("restore", {}).get("schemaDumpPersisted") is not False:
        raise ValueError("fifth WORM persisted its canonical schema dump")
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
        raise ValueError("fifth WORM complete read-role ACL evidence drifted")
    java = worm.get("java", {})
    if java.get("dockerfileSha256") != DOCKERFILE_SHA256:
        raise ValueError("fifth WORM Dockerfile digest drifted")
    if java.get("buildContextSha256") != JAVA_BUILD_CONTEXT_SHA256:
        raise ValueError("fifth WORM build-context digest drifted")
    if java.get("hibernateDdlAuto") != "validate":
        raise ValueError("fifth WORM Hibernate schema mode drifted")
    if java.get("startupPassed") is not True or java.get("readinessPassed") is not True:
        raise ValueError("fifth WORM Java startup/readiness drifted")
    if worm.get("flywayBaselineCreated") is not False:
        raise ValueError("fifth WORM unexpectedly created a Flyway baseline")
    if worm.get("productionDatabaseVersion") != "unknown":
        raise ValueError("fifth WORM production-version boundary drifted")

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
        raise ValueError("fifth WORM leaked an absolute path")
    serialized = json.dumps(worm, sort_keys=True).lower()
    for forbidden in ("password", "secret", "ti-postgres-1", "studyuser", "ti_db"):
        if forbidden in serialized:
            raise ValueError(f"fifth WORM leaked a sensitive identifier: {forbidden}")
    return worm


def _replay_phase2_fixed_acceptance(ti_java_root: Path) -> None:
    """Lazily replay the full Phase 2 gate only when explicitly requested."""
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
        [str(fixed_regular_file(root, "infra/phase2/hash-java-build-context.sh"))],
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
            fixed_regular_file(root, DRIFT_MANIFEST_RELATIVE),
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
            raise ValueError("Phase 2 historical fifth WORM replay drifted")
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
        fixed_regular_file(root, DRIFT_MANIFEST_RELATIVE),
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
        or successor.current_chain_node_count != 7
    ):
        raise ValueError("Phase 2 terminal WORM successor replay drifted")


def _run_read_only_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    command = [
        "git",
        "--no-optional-locks",
        "-C",
        str(repository_root),
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"read-only Git command failed: {arguments[0]}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
        raise ValueError(
            f"read-only Git command rejected {arguments[0]}: {detail}"
        )
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_read_only_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_anchor(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    top = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise ValueError("Git anchor repository root was not passed explicitly")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise ValueError("Git anchor object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit":
        raise ValueError("Git anchor object is not a commit")
    resolved = _git_text(root, "rev-parse", "--verify", f"{GIT_COMMIT_OID}^{{commit}}")
    if resolved != GIT_COMMIT_OID:
        raise ValueError("Git anchor commit resolved unexpectedly")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}^{{tree}}") != GIT_ROOT_TREE_OID:
        raise ValueError("Git anchor root tree drifted")
    if _git_text(root, "show", "-s", "--format=%P", GIT_COMMIT_OID) != GIT_PARENT_OID:
        raise ValueError("Git anchor parent drifted")
    if _git_text(root, "show", "-s", "--format=%aI", GIT_COMMIT_OID) != (
            GIT_AUTHORED_AT):
        raise ValueError("Git anchor author timestamp drifted")
    if _git_text(root, "show", "-s", "--format=%cI", GIT_COMMIT_OID) != (
            GIT_COMMITTED_AT):
        raise ValueError("Git anchor committer timestamp drifted")
    if _git_text(root, "show", "-s", "--format=%s", GIT_COMMIT_OID) != GIT_SUBJECT:
        raise ValueError("Git anchor subject drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java") != TI_JAVA_TREE_OID:
        raise ValueError("Git anchor Ti-Java subtree drifted")
    if _git_text(root, "cat-file", "-t", f"{GIT_COMMIT_OID}:Ti-Java") != "tree":
        raise ValueError("Git anchor Ti-Java object is not a tree")

    for name, descriptor in ANCHOR_ARTIFACTS.items():
        object_name = f"{GIT_COMMIT_OID}:{descriptor['repository_path']}"
        if _git_text(root, "cat-file", "-t", object_name) != "blob":
            raise ValueError(f"Git anchor artifact is not a blob: {name}")
        if _git_text(root, "rev-parse", object_name) != descriptor["git_blob_oid"]:
            raise ValueError(f"Git anchor blob OID drifted: {name}")
        raw = _run_read_only_git(root, "show", object_name)
        if len(raw) != descriptor["byte_count"]:
            raise ValueError(f"Git anchor artifact byte count drifted: {name}")
        if sha256_bytes(raw) != descriptor["sha256"]:
            raise ValueError(f"Git anchor artifact SHA-256 drifted: {name}")


def build_contract(
    ti_java_root: Path = ROOT,
    *,
    repository_root: Path | None = None,
    replay_phase2_fixed_acceptance: bool = False,
) -> dict[str, Any]:
    validate_local_bootstrap(ti_java_root)
    validate_junit_manifest(ti_java_root)
    validate_fifth_worm(ti_java_root)
    if replay_phase2_fixed_acceptance:
        _replay_phase2_fixed_acceptance(ti_java_root)
    if repository_root is not None:
        validate_git_anchor(repository_root)

    artifacts = {
        name: {
            "ti_java_relative_path": descriptor["ti_java_relative_path"],
            "repository_path": descriptor["repository_path"],
            "object_type": "blob",
            "git_blob_oid": descriptor["git_blob_oid"],
            "sha256": descriptor["sha256"],
            "byte_count": descriptor["byte_count"],
        }
        for name, descriptor in sorted(ANCHOR_ARTIFACTS.items())
    }
    contract: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "sha256": PREDECESSOR_SHA256,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "trust_payload_sha256": PREDECESSOR_TRUST_PAYLOAD_SHA256,
            "contract_id": PREDECESSOR_ID,
            "status": PREDECESSOR_STATUS,
            "scope": PREDECESSOR_SCOPE,
            "immutable": True,
        },
        "git_anchor": {
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
            "remote_ref_at_capture": GIT_REMOTE_REF_AT_CAPTURE,
            "mutable_ref_is_not_validation_authority": True,
            "artifact_paths_are_code_fixed": True,
            "artifacts": artifacts,
        },
        "external_anchor": {
            "state": "target_execution_bootstrap_contract_and_bridge_bytes_anchored",
            "anchored_artifact_count": 10,
            "anchored_artifact_keys": sorted(ANCHOR_ARTIFACTS),
            "external_git_and_bridge_bytes_anchor_complete": True,
            "predecessor_rewrite_forbidden": True,
            "arbitrary_git_object_lookup_forbidden": True,
            "dynamic_source_discovery_forbidden": True,
            "current_anchor_bridge_self_authorization_forbidden": True,
        },
        "junit_manifest": {
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
        },
        "worm_evidence": {
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
        },
        "authorization": {
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
        },
        "acceptance": {
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
        },
    }
    contract["document_payload_sha256"] = document_payload_sha256(contract)
    return contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the fixed Phase 4C target-execution external anchor."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=ROOT.parent,
        help="repository root used only for optional read-only Git object verification",
    )
    parser.add_argument(
        "--skip-git-object-verification",
        action="store_true",
        help="build from fixed local bytes without consulting a .git directory",
    )
    parser.add_argument(
        "--skip-phase2-fixed-acceptance-replay",
        action="store_true",
        help="skip the explicit full Phase 2 acceptance replay",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository_root = None if args.skip_git_object_verification else args.repository_root
    contract = build_contract(
        args.ti_java_root,
        repository_root=repository_root,
        replay_phase2_fixed_acceptance=(
            not args.skip_phase2_fixed_acceptance_replay
        ),
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
