#!/usr/bin/env python3
"""Build the external Git anchor for the Phase 4C post-push handoff.

The ordinary builder is Gitless.  It validates only immutable, code-fixed
files below ``Ti-Java``.  Optional Git replay fixes the complete ``1dae013``
commit identity, its exact sixteen-path delta, and every current blob.  The
six sources deliberately excluded by the predecessor are therefore anchored
without allowing this builder or the new validator to authorize themselves.
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
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json"
)

CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-"
    "post-push-anchor-contract"
)
CONTRACT_STATUS = (
    "target_execution_post_push_checkpoint_externally_anchored_"
    "typed_parity_pending_routes_pending"
)
CONTRACT_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-"
    "post-push-external-anchor"
)
CAPTURED_AT = "2026-07-18T14:04:12+08:00"
NEXT_GATE = (
    "typed_parity_real_tomcat_complete_response_headers_redis_refusal_"
    "interruption_same_instance_recovery_and_pg16_pg18_termination_identity_"
    "sql_nine_table_fingerprints_before_route_migration"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-post-push-contract"
)
PREDECESSOR_STATUS = (
    "target_execution_anchor_checkpoint_externally_anchored_"
    "typed_parity_pending_routes_pending"
)
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-post-push"
)
PREDECESSOR_CAPTURED_AT = "2026-07-18T13:10:47+08:00"
PREDECESSOR_SHA256 = (
    "3d7208eb2f70b9eb2b559e15acb4cc7882dacecf8cad941f2978678f93b12628"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "c2382550719d97e74f93db97bf74e70e246cca1e35ac6cc9c6c9e8d13b964dba"
)
PREDECESSOR_BYTE_COUNT = 17974

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "1dae013e11c76ad858d6695f166a32631eb1525e"
GIT_ROOT_TREE_OID = "30fd08f8aa8acac5b2b3e2be1e371849ce2adc8d"
GIT_PARENT_OID = "6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53"
TI_JAVA_TREE_OID = "1d9cc477713f1ff0e58fb9d71cf2e3035cbd314f"
GIT_AUTHORED_AT = "2026-07-18T14:04:12+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "test(java): hand off user counts target anchor"
GIT_CAPTURE_REF = "origin/main"
ZERO_OID = "0" * 40
ZERO_SHA256 = "0" * 64

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


def _change(
    relative: str,
    change_type: str,
    previous_blob_oid: str,
    git_blob_oid: str,
    sha256: str,
    byte_count: int,
    *,
    previous_mode: str = "100644",
    mode: str = "100644",
) -> dict[str, Any]:
    return {
        "ti_java_relative_path": relative,
        "repository_path": f"Ti-Java/{relative}",
        "change_type": change_type,
        "previous_mode": previous_mode,
        "mode": mode,
        "previous_git_blob_oid": previous_blob_oid,
        "object_type": "blob",
        "git_blob_oid": git_blob_oid,
        "sha256": sha256,
        "byte_count": byte_count,
    }


# Exact, path-sorted raw delta of 1dae013.  These descriptors are code-fixed;
# neither the predecessor nor the generated document can add another path.
CHECKPOINT_CHANGES = {
    "README.md": _change(
        "README.md", "M",
        "550bc40705fea9b603a3936de9de366ba49849ef",
        "b8878d9102157218625945785dcba00526cda5aa",
        "9c7608803dff193b898d14d13de92095ef001dfeb6099fde2a2ba546d4cd867c",
        37695,
    ),
    "docs/refactor/05-progress.md": _change(
        "docs/refactor/05-progress.md", "M",
        "1bcad604184f31cf24a0047bd248d457dda47402",
        "eef564d6974330fe4c851e0c1a122b99712bd1f6",
        "9ac3b2edaff690f105326aed3c7a87d4049b7f89a1af541038c8f0b032bf79ec",
        100798,
    ),
    "docs/refactor/phase4c/README.md": _change(
        "docs/refactor/phase4c/README.md", "M",
        "aa989184d7f0c4dea4fb66284346937269891fe2",
        "e41a660c873e8f5253320d3f9503957368758027",
        "649ad38f868840edf8ca16ce35156dd18ea7336da9869433bdaa0db2f604fec2",
        15137,
    ),
    PREDECESSOR_RELATIVE: _change(
        PREDECESSOR_RELATIVE, "A", ZERO_OID,
        "79449241fa383c909cedd15f732924f665f11648",
        PREDECESSOR_SHA256,
        PREDECESSOR_BYTE_COUNT,
        previous_mode="000000",
    ),
    "infra/phase2/README.md": _change(
        "infra/phase2/README.md", "M",
        "99a264aa12e44ddf34bda25156877890143d75a3",
        "673c6b73962605da6af7f7e4593e6cb223f76d6d",
        "4a5205e57bad5f54b60fd8ad1f21b8f32f5282bb4938a0244ea9f0977c34157e",
        6748,
    ),
    "infra/phase2/verify-static.sh": _change(
        "infra/phase2/verify-static.sh", "M",
        "c5e3d49701c6e2fa11676fe46b545cc87039b003",
        "3fd68528c824b522adc285ad82ec0babd7afb7eb",
        "357cd003b068997cbcb4ed194f785d3a1d1f310871ad1994c5102bcb1839f54d",
        13541,
        previous_mode="100755",
        mode="100755",
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java"
    ): _change(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
        "A", ZERO_OID,
        "773bca2a7dc42b334b66f9b5b11372cb2298eb53",
        "5cf9c260bbeac52480e814a0d98317932efe191a6e1ffac8a1c747e7bd0b9e17",
        43536,
        previous_mode="000000",
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): _change(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
        "M",
        "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
        "6a98738b1db5de7d3d32cfbafe72e16efe7dbd72",
        "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
        89014,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java"
    ): _change(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java",
        "A", ZERO_OID,
        "5b4c2e9fe0328e667cd767a0e8696a543c53bcb8",
        "5805a4517e02ec23af94546e551d4d3994aaed5667fc680f5b603d81e95f9304",
        15155,
        previous_mode="000000",
    ),
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_contract.py"
    ): _change(
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_contract.py",
        "M",
        "9cac3b5c6a3ecd0b98b71122864b5d706007645f",
        "c1910a9ccd2cc8e0773bfb0c7cfdd89c31806db1",
        "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
        61952,
    ),
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): _change(
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py",
        "A", ZERO_OID,
        "02dd94167e32a1ecc980870688d9f558095893b3",
        "89790dba5376e617128b8b5048f30db8e75f50491ff34f66507654ab3f79ecf3",
        29633,
        previous_mode="000000",
    ),
    "tools/phase2_wormhole_successor_acceptance.py": _change(
        "tools/phase2_wormhole_successor_acceptance.py", "M",
        "1ccfbe8c3b4837165f83bd8f2a85c5bb4c259cd7",
        "4fa4e6b00be61e65f2653b3baf35c2d63ea26fce",
        "b1eabe5dc758e8ff0c2b0d25f7a4878e7a38a4491db7ea3bffbe04018c579464",
        23319,
    ),
    "tools/phase4c_http_target_execution_post_push_successor_acceptance.py": _change(
        "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
        "A", ZERO_OID,
        "81ba7249f09204ee904829413d8ebff2714a2348",
        "4200844497d67071b1672f00a81ff6309bd6d3d2ac6b355b727e5100f1c9147d",
        28435,
        previous_mode="000000",
    ),
    "tools/phase4c_http_target_execution_successor_acceptance.py": _change(
        "tools/phase4c_http_target_execution_successor_acceptance.py", "M",
        "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
        "70248a346d5153062625bd124ab3d9a7c2fc019d",
        "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a",
        81902,
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": _change(
        "tools/test_phase2_wormhole_successor_acceptance.py", "M",
        "29f5fed3124d2b76178befed2e53276e3fa6ad75",
        "a538bc718fb2894054440b22227f8f8d93eef20d",
        "fae248af8e5b5e61634ac10bb8824d5437fd08c4d168c49faadff3e6983c1b9e",
        29314,
    ),
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): _change(
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py",
        "A", ZERO_OID,
        "c8462aff9f27889597717a351b1b86226d1fe46a",
        "5abd19cb1db4f96b59d09f7b0827628a0177d3fdb3b2fd5bcbb80d09208eb158",
        11159,
        previous_mode="000000",
    ),
}

POST_PUSH_SOURCE_PATHS = [
    PREDECESSOR_RELATIVE,
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


def _source(
    relative: str,
    accepted_blob_oid: str,
    accepted_sha256: str,
    accepted_byte_count: int,
    mode: str = "100644",
) -> dict[str, Any]:
    return {
        "source": relative,
        "repository_path": f"Ti-Java/{relative}",
        "accepted_git_commit_oid": GIT_COMMIT_OID,
        "accepted_git_blob_oid": accepted_blob_oid,
        "accepted_sha256": accepted_sha256,
        "accepted_byte_count": accepted_byte_count,
        "mode": mode,
    }


# Exact second-hop allowlist.  The final successor hashes are filled only from
# reviewed physical files after all collaborating edits settle; zero values
# keep the in-progress document honest and route promotion closed.
SUCCESSOR_SOURCES = {
    relative: _source(
        relative,
        CHECKPOINT_CHANGES[relative]["git_blob_oid"],
        CHECKPOINT_CHANGES[relative]["sha256"],
        CHECKPOINT_CHANGES[relative]["byte_count"],
        CHECKPOINT_CHANGES[relative]["mode"],
    )
    for relative in (
        "README.md",
        "docs/refactor/05-progress.md",
        "docs/refactor/phase4c/README.md",
        "infra/phase2/README.md",
        "infra/phase2/verify-static.sh",
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java",
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py",
        "tools/phase2_wormhole_successor_acceptance.py",
        "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
        "tools/test_phase2_wormhole_successor_acceptance.py",
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py",
    )
}
SUCCESSOR_SHA256 = {
    "README.md": "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57",
    "docs/refactor/05-progress.md": (
        "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf"
    ),
    "docs/refactor/phase4c/README.md": (
        "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61"
    ),
    "infra/phase2/README.md": (
        "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f"
    ),
    "infra/phase2/verify-static.sh": (
        "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835"
    ),
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java": (
        "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa"
    ),
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java": (
        "a8e81f0758928eb69c527a9d6bbcf00517160221ea7b1aca4b901b7d5a26cf48"
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py": (
        "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f"
    ),
    "tools/phase2_wormhole_successor_acceptance.py": (
        "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1"
    ),
    "tools/phase4c_http_target_execution_post_push_successor_acceptance.py": (
        "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c"
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": (
        "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb"
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py": (
        "d99d36f8b17e5072dcd130c4570ac074096a3c9ee2b9bf4f0f49fd2b1cd907e6"
    ),
}
SUCCESSOR_BYTE_COUNT = {
    "README.md": 37622,
    "docs/refactor/05-progress.md": 101162,
    "docs/refactor/phase4c/README.md": 15524,
    "infra/phase2/README.md": 6786,
    "infra/phase2/verify-static.sh": 13955,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java": 45004,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java": 16704,
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py": 31546,
    "tools/phase2_wormhole_successor_acceptance.py": 24199,
    "tools/phase4c_http_target_execution_post_push_successor_acceptance.py": 30640,
    "tools/test_phase2_wormhole_successor_acceptance.py": 36539,
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py": 11724,
}

CURRENT_ANCHOR_SOURCES = [
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_anchor_contract.py",
    "tools/phase4c_http_target_execution_post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_anchor_contract.py",
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


def _load_typed_normalization_successor_acceptance() -> object:
    """Lazily load the sole reviewed successor for advanced Phase2 bytes."""

    qualified_name = "tools.phase4c_http_typed_normalization_successor_acceptance"
    direct_name = "phase4c_http_typed_normalization_successor_acceptance"
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
            "fixed HTTP typed-normalization successor is required"
        ) from error


def _validate_current_or_typed_normalization_successor(
        root: Path,
        relative: str,
        accepted_sha256: str,
        payload: bytes,
) -> None:
    """Require unchanged c38 bytes or one exact code-fixed third hop."""

    physical_sha256 = sha256_bytes(payload)
    if physical_sha256 == accepted_sha256:
        if len(payload) != SUCCESSOR_BYTE_COUNT[relative]:
            raise AssertionError(
                f"post-push anchor successor size drifted: {relative}"
            )
        return
    acceptance = _load_typed_normalization_successor_acceptance()
    accepted_lookup = getattr(acceptance, "accepted_sha256", None)
    successor_lookup = getattr(acceptance, "successor_sha256", None)
    if not callable(accepted_lookup) or not callable(successor_lookup):
        raise AssertionError("typed-normalization successor API is incomplete")
    if accepted_lookup(relative) != accepted_sha256:
        raise AssertionError(
            f"typed-normalization successor does not accept historical bytes: {relative}"
        )
    if successor_lookup(root, relative) != physical_sha256:
        raise AssertionError(
            f"typed-normalization successor does not bind current bytes: {relative}"
        )


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed post-push anchor path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"fixed post-push anchor path contains symlink: {relative}"
            )
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed post-push anchor path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(
            f"fixed post-push anchor path is not a regular file: {relative}"
        )
    return resolved


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        document = json.loads(
            fixed_regular_file(root, relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(
            f"cannot read fixed post-push anchor JSON: {relative}"
        ) from error
    if not isinstance(document, dict):
        raise AssertionError(f"fixed JSON is not an object: {relative}")
    return document


def _validate_predecessor(root: Path) -> dict[str, Any]:
    path = fixed_regular_file(root, PREDECESSOR_RELATIVE)
    payload = path.read_bytes()
    if len(payload) != PREDECESSOR_BYTE_COUNT:
        raise AssertionError("post-push predecessor byte count drifted")
    if sha256_bytes(payload) != PREDECESSOR_SHA256:
        raise AssertionError("post-push predecessor physical SHA-256 drifted")
    predecessor = _read_json(root, PREDECESSOR_RELATIVE)
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
    historical = predecessor.get("historical_source_successors", {})
    if historical.get("current_post_push_sources") != sorted(POST_PUSH_SOURCE_PATHS):
        raise AssertionError("post-push predecessor excluded-source set drifted")
    if historical.get("current_post_push_sources_excluded_from_self_authority") is not True:
        raise AssertionError("post-push predecessor self-authority boundary drifted")
    if historical.get("current_successor_bytes_external_git_anchor_complete") is not False:
        raise AssertionError("post-push predecessor rewrote its open external anchor")
    authorization = predecessor.get("authorization", {})
    for field in (
        "typed_parity_review_complete",
        "full_target_parity_closed",
        "route_migration_eligible",
        "two_legacy_get_routes_migrated",
        "production_cutover",
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"post-push predecessor overclaims {field}")
    acceptance = predecessor.get("acceptance", {})
    if (
        acceptance.get("migrated_operation_count") != 11
        or acceptance.get("pending_operation_count") != 600
        or acceptance.get("production_cutover_operation_count") != 0
    ):
        raise AssertionError("post-push predecessor route counts drifted")
    return predecessor


def _validate_junit_manifest(root: Path) -> None:
    path = fixed_regular_file(root, JUNIT_MANIFEST_RELATIVE)
    if sha256_bytes(path.read_bytes()) != JUNIT_MANIFEST_SHA256:
        raise AssertionError("post-push anchor JUnit manifest hash drifted")
    manifest = _read_json(root, JUNIT_MANIFEST_RELATIVE)
    if (
        manifest.get("document_payload_sha256") != JUNIT_MANIFEST_PAYLOAD_SHA256
        or document_payload_sha256(manifest) != JUNIT_MANIFEST_PAYLOAD_SHA256
    ):
        raise AssertionError("post-push anchor JUnit manifest payload drifted")
    result = manifest.get("result", {})
    if (
        result.get("leaf_payload_sha256") != JUNIT_LEAF_PAYLOAD_SHA256
        or len(result.get("leaves", [])) != 60
    ):
        raise AssertionError("post-push anchor JUnit leaves drifted")
    raw = manifest.get("raw_report", {})
    if (
        raw.get("sha256") != JUNIT_RAW_REPORT_SHA256
        or raw.get("byte_count") != JUNIT_RAW_REPORT_BYTE_COUNT
    ):
        raise AssertionError("post-push anchor raw JUnit binding drifted")


def _validate_worm(root: Path) -> None:
    path = fixed_regular_file(root, WORM_RELATIVE)
    if sha256_bytes(path.read_bytes()) != WORM_SHA256:
        raise AssertionError("post-push anchor fifth WORM hash drifted")
    worm = _read_json(root, WORM_RELATIVE)
    if (
        worm.get("java", {}).get("buildContextSha256")
        != JAVA_BUILD_CONTEXT_SHA256
        or worm.get("java", {}).get("dockerfileSha256") != DOCKERFILE_SHA256
        or worm.get("restore", {}).get("canonicalSchemaDumpSha256")
        != CANONICAL_SCHEMA_DUMP_SHA256
        or worm.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("post-push anchor fifth WORM boundary drifted")


def successor_constants_settled() -> bool:
    return all(
        SUCCESSOR_SHA256.get(relative) not in (None, ZERO_SHA256)
        and SUCCESSOR_BYTE_COUNT.get(relative, 0) > 0
        for relative in SUCCESSOR_SOURCES
    )


def _validate_local_successors(root: Path) -> None:
    if not successor_constants_settled():
        return
    for relative in SUCCESSOR_SOURCES:
        payload = fixed_regular_file(root, relative).read_bytes()
        _validate_current_or_typed_normalization_successor(
            root,
            relative,
            SUCCESSOR_SHA256[relative],
            payload,
        )


def _successor_overrides() -> dict[str, dict[str, Any]]:
    return {
        relative: {
            **deepcopy(descriptor),
            "successor_sha256": SUCCESSOR_SHA256[relative],
            "successor_byte_count": SUCCESSOR_BYTE_COUNT[relative],
        }
        for relative, descriptor in sorted(SUCCESSOR_SOURCES.items())
    }


def _run_read_only_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(repository_root),
                *arguments,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
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


def _expected_raw_delta() -> list[str]:
    return [
        (
            f":{descriptor['previous_mode']} {descriptor['mode']} "
            f"{descriptor['previous_git_blob_oid']} {descriptor['git_blob_oid']} "
            f"{descriptor['change_type']}\t{descriptor['repository_path']}"
        )
        for descriptor in CHECKPOINT_CHANGES.values()
    ]


def _validate_git_blob(root: Path, descriptor: dict[str, Any]) -> None:
    repository_path = descriptor["repository_path"]
    line = _git_text(root, "ls-tree", GIT_COMMIT_OID, "--", repository_path)
    parts = line.split(None, 3)
    if len(parts) != 4 or parts[:3] != [
        descriptor["mode"],
        "blob",
        descriptor["git_blob_oid"],
    ]:
        raise AssertionError(f"post-push anchor tree entry drifted: {repository_path}")
    object_name = f"{GIT_COMMIT_OID}:{repository_path}"
    if _git_text(root, "rev-parse", object_name) != descriptor["git_blob_oid"]:
        raise AssertionError(f"post-push anchor blob OID drifted: {repository_path}")
    payload = _run_read_only_git(root, "cat-file", "blob", descriptor["git_blob_oid"])
    if (
        len(payload) != descriptor["byte_count"]
        or sha256_bytes(payload) != descriptor["sha256"]
    ):
        raise AssertionError(f"post-push anchor blob bytes drifted: {repository_path}")
    previous_oid = descriptor["previous_git_blob_oid"]
    if previous_oid != ZERO_OID and _git_text(root, "cat-file", "-t", previous_oid) != "blob":
        raise AssertionError(
            f"post-push anchor previous object is not a blob: {repository_path}"
        )


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    top = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise AssertionError("post-push anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("post-push anchor Git object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit":
        raise AssertionError("post-push anchor checkpoint is not a commit")
    if _git_text(root, "rev-parse", "--verify", f"{GIT_COMMIT_OID}^{{commit}}") != GIT_COMMIT_OID:
        raise AssertionError("post-push anchor commit resolved unexpectedly")
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
        raise AssertionError("post-push anchor Git commit identity drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java") != TI_JAVA_TREE_OID:
        raise AssertionError("post-push anchor Ti-Java subtree drifted")
    if _git_text(root, "cat-file", "-t", f"{GIT_COMMIT_OID}:Ti-Java") != "tree":
        raise AssertionError("post-push anchor Ti-Java object is not a tree")
    raw_delta = _git_text(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        GIT_COMMIT_OID,
    ).splitlines()
    if raw_delta != _expected_raw_delta():
        raise AssertionError("post-push anchor exact sixteen-path delta drifted")
    for descriptor in CHECKPOINT_CHANGES.values():
        _validate_git_blob(root, descriptor)


def build_contract(
    ti_java_root: Path = ROOT,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    _validate_predecessor(root)
    _validate_junit_manifest(root)
    _validate_worm(root)
    _validate_local_successors(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)

    transitions_settled = successor_constants_settled()
    post_push_artifacts = {
        relative: deepcopy(CHECKPOINT_CHANGES[relative])
        for relative in sorted(POST_PUSH_SOURCE_PATHS)
    }
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
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
                "added_count": 6,
                "modified_count": 10,
                "deleted_count": 0,
                "non_ti_java_count": 0,
                "inserted_line_count": 3799,
                "deleted_line_count": 89,
                "current_total_bytes": 605312,
                "added_total_bytes": 145892,
                "modified_current_total_bytes": 459420,
                "modified_parent_total_bytes": 436774,
                "net_byte_increase": 168538,
                "exact_sixteen_path_delta": True,
            },
            "artifacts": deepcopy(CHECKPOINT_CHANGES),
        },
        "post_push_source_anchor": {
            "accepted_checkpoint_commit_oid": GIT_COMMIT_OID,
            "source_paths": sorted(POST_PUSH_SOURCE_PATHS),
            "source_path_allowlist_exact": True,
            "source_count": 6,
            "source_total_bytes": 145892,
            "artifacts": post_push_artifacts,
            "predecessor_current_sources_external_git_anchor_complete": True,
            "predecessor_false_claim_preserved": True,
            "whole_commit_root_parent_and_ti_java_tree_fixed": True,
            "exact_sixteen_change_blobs_fixed": True,
            "arbitrary_git_object_lookup_forbidden": True,
            "dynamic_source_discovery_forbidden": True,
            "current_anchor_sources": sorted(CURRENT_ANCHOR_SOURCES),
            "current_anchor_sources_excluded_from_self_authority": True,
            "current_anchor_source_bytes_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "tamper_evident_scope": "fixed_git_commit_tree_delta_and_explicit_blobs",
        },
        "historical_source_successors": {
            "accepted_checkpoint_commit_oid": GIT_COMMIT_OID,
            "predecessor_historical_successor_allowlist_count": 10,
            "second_hop_successor_allowlist_count": 12,
            "successor_allowlist": sorted(SUCCESSOR_SOURCES),
            "successor_allowlist_exact": True,
            "arbitrary_source_lookup_forbidden": True,
            "accepted_hashes_from_fixed_git_blobs": True,
            "successor_hashes_code_fixed": True,
            "successor_transitions_settled": transitions_settled,
            "overrides": _successor_overrides(),
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
            "post_push_checkpoint_and_six_excluded_sources_external_git_anchor_complete": True,
            "historical_successor_transitions_settled": transitions_settled,
            "current_anchor_source_bytes_external_git_anchor_complete": False,
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
            "checkpoint_changed_path_count": 16,
            "checkpoint_added_count": 6,
            "checkpoint_modified_count": 10,
            "checkpoint_current_total_bytes": 605312,
            "post_push_source_anchor_count": 6,
            "post_push_source_anchor_total_bytes": 145892,
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
            "current_anchor_is_successor_bootstrap": True,
            "next_gate": NEXT_GATE,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialized_contract(document))


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
