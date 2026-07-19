#!/usr/bin/env python3
"""Build the Git-fixed post-push handoff for Phase 4C target execution.

The document fixes the already-pushed ``6c1b03d`` checkpoint and its exact
nine-file add-only delta.  It also carries a deliberately narrow successor
allowlist for the historical bridges and progress documents changed by this
handoff.  The builder never discovers paths from a contract and ordinary
``build_contract`` is independent of Git and historical Python imports.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-contract.json"
)

CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-post-push-contract"
)
CONTRACT_STATUS = (
    "target_execution_anchor_checkpoint_externally_anchored_"
    "typed_parity_pending_routes_pending"
)
CONTRACT_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-post-push"
)
CAPTURED_AT = "2026-07-18T13:10:47+08:00"
NEXT_GATE = (
    "typed_parity_real_tomcat_complete_response_headers_redis_refusal_"
    "interruption_same_instance_recovery_and_pg16_pg18_termination_identity_"
    "sql_nine_table_fingerprints_before_route_migration"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-anchor-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-anchor-contract"
)
PREDECESSOR_STATUS = (
    "target_execution_bootstrap_externally_anchored_"
    "normalized_junit_manifest_bootstrap_bound_routes_pending"
)
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-external-anchor"
)
PREDECESSOR_CAPTURED_AT = "2026-07-18T12:14:52+08:00"
PREDECESSOR_SHA256 = (
    "f966f9229949a37811da2402d3baf05dd78643ec4104a8f921dee10188bcd203"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "dbfe37e3e0d9b80ebb378a58b58aa7b15371d737b389f06f24f3018adb6b311e"
)

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53"
GIT_ROOT_TREE_OID = "47a1df74676ff2838bec7d01f371787720aea559"
GIT_PARENT_OID = "0531b3c9272f9743a374edcf5c8bbeb72643eb1b"
TI_JAVA_TREE_OID = "7c0e65fa52ffa95567b0d7e266bd4e590af22f5a"
GIT_AUTHORED_AT = "2026-07-18T13:10:47+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "test(java): anchor user counts target execution"
GIT_CAPTURE_REF = "origin/main"

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
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
JAVA_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
CANONICAL_SCHEMA_DUMP_SHA256 = (
    "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
)


def _artifact(
    relative: str,
    blob_oid: str,
    sha256: str,
    byte_count: int,
    mode: str = "100644",
) -> dict[str, Any]:
    return {
        "ti_java_relative_path": relative,
        "repository_path": f"Ti-Java/{relative}",
        "object_type": "blob",
        "git_blob_oid": blob_oid,
        "sha256": sha256,
        "byte_count": byte_count,
        "mode": mode,
    }


CHECKPOINT_ARTIFACTS = {
    "anchor_contract": _artifact(
        PREDECESSOR_RELATIVE,
        "75a25eacdea16cc2d3349eadad24b1370a9ae4bd",
        PREDECESSOR_SHA256,
        10974,
    ),
    "junit_manifest": _artifact(
        JUNIT_MANIFEST_RELATIVE,
        "da3cef8743dbf436b4d631f081b706c705961bdd",
        JUNIT_MANIFEST_SHA256,
        33246,
    ),
    "java_anchor_acceptance": _artifact(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionAnchorSuccessorAcceptance.java",
        "4434b28df67afdd682d09e7c091c2007a34a0187",
        "1e2bd94c5e13389375cee448615149d8409cc311ca97e2fc78ebcafa33cd1030",
        41210,
    ),
    "java_anchor_parity_test": _artifact(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionAnchorContractParityTest.java",
        "ac82ead5ba1bce096bcbfa363f1500a447981755",
        "9b4e885f8c3727081c0cfcd6cd5901f1bf7a1f9059c81e9badd1273133a4676c",
        12996,
    ),
    "anchor_builder": _artifact(
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_anchor_contract.py",
        "b3af05cc0a086122e4dd9b0a61f0389bcbe880c3",
        "b87133b5c187561970c322a92eb22f84cb7a768a9168870cc7517dd973616667",
        34518,
    ),
    "junit_normalizer": _artifact(
        "tools/normalize_phase4c_personal_bank_user_counts_"
        "target_execution_junit.py",
        "470c36c6b18b3573ac4e3aecb6443a1fb5290349",
        "f6d90113c69d9c1bef2e3d53f839539a481bbcd674c7b598b2fb4aff88a3879a",
        27174,
    ),
    "python_anchor_acceptance": _artifact(
        "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
        "14cfc16aad7fbae8df09a46c846d890a43663587",
        "03b411be87bd9f8d4dbb94ddcfb9495ec7523fb5c9482f3c1fb4098d1ab7e455",
        34568,
    ),
    "junit_normalizer_test": _artifact(
        "tools/test_normalize_phase4c_personal_bank_user_counts_"
        "target_execution_junit.py",
        "5e36f76fdca87d1f5fc83e2a1cab1dc3285cb684",
        "f2397e35c76f063f356edfb9f2491f17157cfaa07cfbc0d3a39a28b4e2957d5d",
        12068,
    ),
    "python_anchor_contract_test": _artifact(
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_anchor_contract.py",
        "78ba394d3a5b9b833e5496d685a31f5375280bb0",
        "3306aed29941fd9703f36443f43bbb65646b48bed1f6f848d6109683057769e5",
        15921,
    ),
}


def _source(
    relative: str,
    blob_oid: str,
    accepted_sha256: str,
    accepted_byte_count: int,
    mode: str = "100644",
) -> dict[str, Any]:
    return {
        "repository_path": f"Ti-Java/{relative}",
        "git_blob_oid": blob_oid,
        "accepted_sha256": accepted_sha256,
        "accepted_byte_count": accepted_byte_count,
        "mode": mode,
    }


SUCCESSOR_SOURCES = {
    "README.md": _source(
        "README.md",
        "550bc40705fea9b603a3936de9de366ba49849ef",
        "321d23e47d0df0714ea632b2c8c1d3d05d0e67bf69d53e3a52e387e4a949bda4",
        37209,
    ),
    "docs/refactor/05-progress.md": _source(
        "docs/refactor/05-progress.md",
        "1bcad604184f31cf24a0047bd248d457dda47402",
        "e2363a603e9b82368185b6fef3e9882a3e586ce5b5eca14a8b5cddcbca7d6faf",
        98860,
    ),
    "docs/refactor/phase4c/README.md": _source(
        "docs/refactor/phase4c/README.md",
        "aa989184d7f0c4dea4fb66284346937269891fe2",
        "f43ae7ca31038fcc45a05874cfc5c8a460edfe2833936bf4418f37706771d472",
        13854,
    ),
    "infra/phase2/README.md": _source(
        "infra/phase2/README.md",
        "99a264aa12e44ddf34bda25156877890143d75a3",
        "55f9d05fa583e581d6a5b92ec4f1e3e53690a40b5087da456a84ef996b4d3f7b",
        6378,
    ),
    "infra/phase2/verify-static.sh": _source(
        "infra/phase2/verify-static.sh",
        "c5e3d49701c6e2fa11676fe46b545cc87039b003",
        "eb01988f26a56293338a7bcd8bc83487b2d8cd0c1c081ae75272bc73dfa28a94",
        13155,
        "100755",
    ),
    "tools/phase2_wormhole_successor_acceptance.py": _source(
        "tools/phase2_wormhole_successor_acceptance.py",
        "1ccfbe8c3b4837165f83bd8f2a85c5bb4c259cd7",
        "f3a56bd684b508f69bc387d741f1c0277d0c4a7f4130aec984fd359fa8dc0f3a",
        21178,
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": _source(
        "tools/test_phase2_wormhole_successor_acceptance.py",
        "29f5fed3124d2b76178befed2e53276e3fa6ad75",
        "ce70d5f35c7725d0f93f27619c5828f294ac259fc20f8594a3ac71b5f5f6f72d",
        19647,
    ),
    (
        "tools/"
        "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py"
    ): _source(
        "tools/"
        "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
        "9cac3b5c6a3ecd0b98b71122864b5d706007645f",
        "51d3c9bf425319e7a0cd7a49e7244f058e09f14ac363f9278000192cb4a69d3b",
        59991,
    ),
    "tools/phase4c_http_target_execution_successor_acceptance.py": _source(
        "tools/phase4c_http_target_execution_successor_acceptance.py",
        "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
        "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c",
        78481,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): _source(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
        "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
        "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15",
        88021,
    ),
}

# Filled only with reviewed physical bytes.  The values are deliberately code,
# not values read from the contract being generated.
SUCCESSOR_SHA256 = {
    "README.md": (
        "9c7608803dff193b898d14d13de92095ef001dfeb6099fde2a2ba546d4cd867c"
    ),
    "docs/refactor/05-progress.md": (
        "9ac3b2edaff690f105326aed3c7a87d4049b7f89a1af541038c8f0b032bf79ec"
    ),
    "docs/refactor/phase4c/README.md": (
        "649ad38f868840edf8ca16ce35156dd18ea7336da9869433bdaa0db2f604fec2"
    ),
    "infra/phase2/README.md": (
        "4a5205e57bad5f54b60fd8ad1f21b8f32f5282bb4938a0244ea9f0977c34157e"
    ),
    "infra/phase2/verify-static.sh": (
        "357cd003b068997cbcb4ed194f785d3a1d1f310871ad1994c5102bcb1839f54d"
    ),
    "tools/phase2_wormhole_successor_acceptance.py": (
        "b1eabe5dc758e8ff0c2b0d25f7a4878e7a38a4491db7ea3bffbe04018c579464"
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": (
        "fae248af8e5b5e61634ac10bb8824d5437fd08c4d168c49faadff3e6983c1b9e"
    ),
    (
        "tools/"
        "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py"
    ): "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
    "tools/phase4c_http_target_execution_successor_acceptance.py": (
        "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
}
SUCCESSOR_BYTE_COUNT = {
    "README.md": 37695,
    "docs/refactor/05-progress.md": 100798,
    "docs/refactor/phase4c/README.md": 15137,
    "infra/phase2/README.md": 6748,
    "infra/phase2/verify-static.sh": 13541,
    "tools/phase2_wormhole_successor_acceptance.py": 23319,
    "tools/test_phase2_wormhole_successor_acceptance.py": 29314,
    (
        "tools/"
        "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py"
    ): 61952,
    "tools/phase4c_http_target_execution_successor_acceptance.py": 81902,
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): 89014,
}
NODEA_SEMANTIC_SUCCESSOR_PATHS = frozenset({
    "tools/"
    "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
    "tools/phase4c_http_target_execution_successor_acceptance.py",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ),
})

CURRENT_POST_PUSH_SOURCES = [
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-contract.json",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py",
    "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py",
]


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


def _load_post_push_anchor_successor_acceptance() -> object:
    """Lazily load the sole reviewed successor for advanced local bytes."""
    qualified_name = (
        "tools.phase4c_http_target_execution_post_push_anchor_"
        "successor_acceptance"
    )
    direct_name = (
        "phase4c_http_target_execution_post_push_anchor_successor_acceptance"
    )
    try:
        return importlib.import_module(qualified_name)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", qualified_name}:
            raise
    try:
        return importlib.import_module(direct_name)
    except ModuleNotFoundError as error:
        if error.name != direct_name:
            raise
        raise AssertionError(
            "fixed target-execution post-push anchor successor is required"
        ) from error


def _load_tag_preflight_successor_acceptance() -> object:
    qualified_name = (
        "tools.phase4c_tag_migration_global_preflight_successor_acceptance"
    )
    direct_name = "phase4c_tag_migration_global_preflight_successor_acceptance"
    try:
        return importlib.import_module(qualified_name)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", qualified_name}:
            raise
    try:
        return importlib.import_module(direct_name)
    except ModuleNotFoundError as error:
        if error.name != direct_name:
            raise
        raise AssertionError(
            "fixed tag-preflight successor acceptance is required"
        ) from error


def _validate_current_or_anchor_successor(
        root: Path,
        relative: str,
        accepted_sha256: str,
        payload: bytes,
) -> None:
    """Require unchanged bytes or one exact code-fixed anchor transition."""
    physical_sha256 = sha256_bytes(payload)
    if physical_sha256 == accepted_sha256:
        if len(payload) != SUCCESSOR_BYTE_COUNT[relative]:
            raise AssertionError(
                f"post-push successor source size drifted: {relative}"
            )
        return
    acceptance = _load_post_push_anchor_successor_acceptance()
    accepted_lookup = getattr(acceptance, "accepted_sha256", None)
    successor_lookup = getattr(acceptance, "successor_sha256", None)
    if not callable(accepted_lookup) or not callable(successor_lookup):
        raise AssertionError("post-push anchor successor API is incomplete")
    anchor_accepted = accepted_lookup(relative)
    if anchor_accepted is not None:
        if anchor_accepted != accepted_sha256:
            raise AssertionError(
                f"post-push anchor does not accept historical bytes: {relative}"
            )
        if successor_lookup(root, relative) != physical_sha256:
            raise AssertionError(
                f"post-push anchor does not bind current bytes: {relative}"
            )
        return
    if relative not in NODEA_SEMANTIC_SUCCESSOR_PATHS:
        raise AssertionError(
            f"post-push anchor does not accept historical bytes: {relative}"
        )
    nodea = _load_tag_preflight_successor_acceptance()
    nodea_accepted = getattr(nodea, "accepted_sha256", None)
    nodea_successor = getattr(nodea, "successor_sha256", None)
    if not callable(nodea_accepted) or not callable(nodea_successor):
        raise AssertionError("tag-preflight successor API is incomplete")
    if nodea_accepted(relative) != accepted_sha256:
        raise AssertionError(
            f"tag-preflight successor does not accept post-push source: {relative}"
        )
    if nodea_successor(root, relative) != physical_sha256:
        raise AssertionError(
            f"tag-preflight successor does not bind post-push source: {relative}"
        )


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed post-push path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"fixed post-push path contains symlink: {relative}")
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed post-push path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(f"fixed post-push path is not a regular file: {relative}")
    return resolved


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        document = json.loads(
            fixed_regular_file(root, relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"cannot read fixed post-push JSON: {relative}") from error
    if not isinstance(document, dict):
        raise AssertionError(f"fixed post-push JSON is not an object: {relative}")
    return document


def _validate_local_inputs(ti_java_root: Path) -> None:
    predecessor_path = fixed_regular_file(ti_java_root, PREDECESSOR_RELATIVE)
    if sha256_bytes(predecessor_path.read_bytes()) != PREDECESSOR_SHA256:
        raise AssertionError("post-push predecessor physical hash drifted")
    predecessor = _read_json(ti_java_root, PREDECESSOR_RELATIVE)
    if {
        "contract_id": predecessor.get("contract_id"),
        "status": predecessor.get("status"),
        "scope": predecessor.get("scope"),
        "captured_at": predecessor.get("captured_at"),
        "document_payload_sha256": predecessor.get("document_payload_sha256"),
    } != {
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "captured_at": PREDECESSOR_CAPTURED_AT,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
    }:
        raise AssertionError("post-push predecessor identity drifted")
    if document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("post-push predecessor payload is invalid")

    manifest_path = fixed_regular_file(ti_java_root, JUNIT_MANIFEST_RELATIVE)
    if sha256_bytes(manifest_path.read_bytes()) != JUNIT_MANIFEST_SHA256:
        raise AssertionError("post-push JUnit manifest physical hash drifted")
    manifest = _read_json(ti_java_root, JUNIT_MANIFEST_RELATIVE)
    if manifest.get("document_payload_sha256") != JUNIT_MANIFEST_PAYLOAD_SHA256:
        raise AssertionError("post-push JUnit manifest payload field drifted")
    if document_payload_sha256(manifest) != JUNIT_MANIFEST_PAYLOAD_SHA256:
        raise AssertionError("post-push JUnit manifest payload is invalid")
    confidentiality = manifest.get("confidentiality", {})
    if (
        confidentiality.get("manifest_bytes_external_git_anchor_complete") is not False
        or confidentiality.get("post_push_successor_anchor_required") is not True
    ):
        raise AssertionError("historical JUnit manifest boundary was rewritten")

    worm_path = fixed_regular_file(ti_java_root, WORM_RELATIVE)
    if sha256_bytes(worm_path.read_bytes()) != WORM_SHA256:
        raise AssertionError("post-push fifth WORM hash drifted")
    worm = _read_json(ti_java_root, WORM_RELATIVE)
    if worm.get("java", {}).get("buildContextSha256") != JAVA_BUILD_CONTEXT_SHA256:
        raise AssertionError("post-push fifth WORM build-context drifted")
    if worm.get("java", {}).get("dockerfileSha256") != DOCKERFILE_SHA256:
        raise AssertionError("post-push fifth WORM Dockerfile drifted")
    if worm.get("restore", {}).get("canonicalSchemaDumpSha256") != (
        CANONICAL_SCHEMA_DUMP_SHA256
    ):
        raise AssertionError("post-push fifth WORM schema digest drifted")

    for relative, expected in SUCCESSOR_SHA256.items():
        path = fixed_regular_file(ti_java_root, relative)
        if expected == "0" * 64 or SUCCESSOR_BYTE_COUNT[relative] <= 0:
            raise AssertionError(f"unsettled post-push successor source: {relative}")
        payload = path.read_bytes()
        _validate_current_or_anchor_successor(
            ti_java_root,
            relative,
            expected,
            payload,
        )


def _run_read_only_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        capture_output=True,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AssertionError(f"read-only Git command failed: {detail}")
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_read_only_git(repository_root, *arguments).decode("utf-8").strip()


def _validate_git_blob(
    repository_root: Path,
    repository_path: str,
    blob_oid: str,
    sha256: str,
    byte_count: int,
    mode: str,
) -> None:
    tree_line = _git_text(
        repository_root,
        "ls-tree",
        GIT_COMMIT_OID,
        "--",
        repository_path,
    )
    parts = tree_line.split(None, 3)
    if len(parts) != 4 or parts[:3] != [mode, "blob", blob_oid]:
        raise AssertionError(f"post-push Git tree entry drifted: {repository_path}")
    if _git_text(repository_root, "rev-parse", f"{GIT_COMMIT_OID}:{repository_path}") != blob_oid:
        raise AssertionError(f"post-push Git blob OID drifted: {repository_path}")
    payload = _run_read_only_git(repository_root, "cat-file", "blob", blob_oid)
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(f"post-push Git blob payload drifted: {repository_path}")


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("post-push Git object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit":
        raise AssertionError("post-push Git checkpoint is not a commit")
    facts = _git_text(
        root,
        "show",
        "-s",
        "--format=%T%n%P%n%aI%n%cI%n%s",
        GIT_COMMIT_OID,
    ).splitlines()
    if facts != [
        GIT_ROOT_TREE_OID,
        GIT_PARENT_OID,
        GIT_AUTHORED_AT,
        GIT_COMMITTED_AT,
        GIT_SUBJECT,
    ]:
        raise AssertionError("post-push Git commit identity drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java") != TI_JAVA_TREE_OID:
        raise AssertionError("post-push Ti-Java subtree drifted")

    expected_paths = {
        descriptor["repository_path"]
        for descriptor in CHECKPOINT_ARTIFACTS.values()
    }
    rows = _git_text(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        GIT_COMMIT_OID,
    ).splitlines()
    parsed = [row.split("\t", 1) for row in rows if row]
    if len(parsed) != 9 or any(len(row) != 2 or row[0] != "A" for row in parsed):
        raise AssertionError("post-push checkpoint is not an exact nine-file add-only delta")
    if {row[1] for row in parsed} != expected_paths:
        raise AssertionError("post-push checkpoint delta path set drifted")

    for descriptor in CHECKPOINT_ARTIFACTS.values():
        _validate_git_blob(
            root,
            descriptor["repository_path"],
            descriptor["git_blob_oid"],
            descriptor["sha256"],
            descriptor["byte_count"],
            descriptor["mode"],
        )
    for relative, descriptor in SUCCESSOR_SOURCES.items():
        _validate_git_blob(
            root,
            descriptor["repository_path"],
            descriptor["git_blob_oid"],
            descriptor["accepted_sha256"],
            descriptor["accepted_byte_count"],
            descriptor["mode"],
        )


def _successor_overrides() -> dict[str, dict[str, Any]]:
    return {
        relative: {
            "source": relative,
            "accepted_git_commit_oid": GIT_COMMIT_OID,
            "accepted_git_blob_oid": descriptor["git_blob_oid"],
            "accepted_sha256": descriptor["accepted_sha256"],
            "accepted_byte_count": descriptor["accepted_byte_count"],
            "successor_sha256": SUCCESSOR_SHA256[relative],
            "successor_byte_count": SUCCESSOR_BYTE_COUNT[relative],
            "mode": descriptor["mode"],
        }
        for relative, descriptor in sorted(SUCCESSOR_SOURCES.items())
    }


def build_contract(
    ti_java_root: Path = ROOT,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    _validate_local_inputs(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)

    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "sha256": PREDECESSOR_SHA256,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "contract_id": PREDECESSOR_ID,
            "status": PREDECESSOR_STATUS,
            "scope": PREDECESSOR_SCOPE,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "immutable": True,
        },
        "git_checkpoint": {
            "object_format": GIT_OBJECT_FORMAT,
            "commit_oid": GIT_COMMIT_OID,
            "root_tree_oid": GIT_ROOT_TREE_OID,
            "parent_oid": GIT_PARENT_OID,
            "ti_java_tree_oid": TI_JAVA_TREE_OID,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_COMMITTED_AT,
            "subject": GIT_SUBJECT,
            "capture_ref_metadata": GIT_CAPTURE_REF,
            "capture_ref_is_validation_authority": False,
            "diff": {
                "added_count": 9,
                "modified_count": 0,
                "deleted_count": 0,
                "non_ti_java_count": 0,
                "added_total_bytes": 222675,
                "exact_add_only_delta": True,
            },
            "artifacts": deepcopy(CHECKPOINT_ARTIFACTS),
        },
        "checkpoint_anchor": {
            "whole_commit_object_fixed": True,
            "root_tree_parent_and_ti_java_subtree_fixed": True,
            "exact_nine_artifact_blobs_fixed": True,
            "normalized_junit_manifest_blob_external_git_anchor_complete": True,
            "anchor_contract_builder_acceptances_and_tests_external_git_anchor_complete": True,
            "historical_manifest_false_claim_preserved": True,
            "current_post_push_contract_and_validator_bytes_excluded": True,
            "origin_ref_is_metadata_not_authority": True,
            "independently_signed_provenance": False,
            "tamper_evident_scope": "fixed_git_commit_tree_and_explicit_blobs",
        },
        "historical_source_successors": {
            "accepted_checkpoint_commit_oid": GIT_COMMIT_OID,
            "successor_allowlist": sorted(SUCCESSOR_SOURCES),
            "successor_allowlist_exact": True,
            "arbitrary_source_lookup_forbidden": True,
            "accepted_hashes_from_fixed_git_blobs": True,
            "overrides": _successor_overrides(),
            "current_post_push_sources": sorted(CURRENT_POST_PUSH_SOURCES),
            "current_post_push_sources_excluded_from_self_authority": True,
            "current_successor_bytes_external_git_anchor_complete": False,
        },
        "junit_execution": {
            "source": JUNIT_MANIFEST_RELATIVE,
            "sha256": JUNIT_MANIFEST_SHA256,
            "document_payload_sha256": JUNIT_MANIFEST_PAYLOAD_SHA256,
            "leaf_payload_sha256": JUNIT_LEAF_PAYLOAD_SHA256,
            "raw_report_sha256": JUNIT_RAW_REPORT_SHA256,
            "raw_report_byte_count": JUNIT_RAW_REPORT_BYTE_COUNT,
            "case_leaf_count": 59,
            "supplementary_leaf_count": 1,
            "total_leaf_count": 60,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "manifest_blob_external_git_anchor_complete": True,
            "historical_manifest_document_rewritten": False,
        },
        "worm_evidence": {
            "source": WORM_RELATIVE,
            "sha256": WORM_SHA256,
            "predecessor_sha256": WORM_PREDECESSOR_SHA256,
            "fixed_chain_node_count": 5,
            "reused": True,
            "new_worm_report_created": False,
            "java_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
            "dockerfile_sha256": DOCKERFILE_SHA256,
            "canonical_schema_dump_sha256": CANONICAL_SCHEMA_DUMP_SHA256,
        },
        "authorization": {
            "target_dispositions_executed": True,
            "all_59_target_dispositions_executed": True,
            "bootstrap_and_anchor_checkpoint_bytes_external_git_anchor_complete": True,
            "junit_manifest_bytes_external_git_anchor_complete": True,
            "current_handoff_successor_bytes_external_git_anchor_complete": False,
            "typed_parity_review_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "two_legacy_get_routes_migrated": False,
            "derived_head_and_options_count_as_migrated": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "production_cutover": False,
        },
        "acceptance": {
            "checkpoint_artifact_count": 9,
            "checkpoint_added_total_bytes": 222675,
            "junit_leaf_test_count": 60,
            "target_case_count": 59,
            "http_execution_count": 57,
            "typed_postgresql_disposition_count": 2,
            "mocked_application_result_case_count": 0,
            "bound_only_case_count": 0,
            "typed_parity_review_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "implemented_pending_get_count": 2,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "production_cutover": False,
            "current_handoff_is_bootstrap": True,
            "next_gate": NEXT_GATE,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path, default=ROOT.parent)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-git-replay", action="store_true")
    args = parser.parse_args()
    document = build_contract(
        args.ti_java_root,
        repository_root=None if args.skip_git_replay else args.repository_root,
    )
    _write_json(args.output, document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
