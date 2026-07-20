#!/usr/bin/env python3
"""Build the fail-closed Phase 4C user-counts target-execution contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-contract.json"
)
CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-contract"
)
CONTRACT_STATUS = (
    "target_dispositions_executed_typed_parity_review_pending_routes_pending"
)
CONTRACT_SCOPE = "phase4c-personal-bank-user-counts-http-target-execution"
CAPTURED_AT = "2026-07-18T10:00:00+08:00"


def tag_preflight_successor():
    try:
        from tools import (
            phase4c_tag_migration_global_preflight_successor_acceptance
            as successor
        )
    except ModuleNotFoundError as error:  # Direct execution from tools/.
        if error.name not in {
            "tools",
            "tools.phase4c_tag_migration_global_preflight_successor_acceptance",
        }:
            raise
        import phase4c_tag_migration_global_preflight_successor_acceptance \
            as successor
    return successor
NEXT_GATE = (
    "commit_and_push_this_bootstrap_checkpoint_then_anchor_its_git_commit_"
    "contract_sha256_and_both_bridge_sha256_in_the_next_node_before_typed_"
    "parity_network_redis_identity_review_or_route_migration"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-implementation-contract"
)
PREDECESSOR_STATUS = "implementation_present_parity_incomplete_routes_pending"
PREDECESSOR_SCOPE = "phase4c-personal-bank-user-counts-http-implementation"
PREDECESSOR_SHA256 = (
    "c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "f6eff86bea6a1d04bc43bfe8a532ff952f295c6aa2d1d89f6b40f6fe02dc91f9"
)
PREDECESSOR_TRUST_PAYLOAD_SHA256 = (
    "624bb2b801a51e0fd19ae4d4583d77c6b6195355685b202b4c5ac3aa56d2cf8f"
)
READ_PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
READ_PREDECESSOR_SHA256 = (
    "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73"
)
READ_PREDECESSOR_PAYLOAD_SHA256 = (
    "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5"
)
PHASE4B_ALL_SHARES_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-all-shares-entry-contract.json"
)
PHASE4B_ALL_SHARES_ENTRY_SHA256 = (
    "b4311e170cde6657a9ddd30885f17cd847f56a61e8e8f24c159be425d5931fbb"
)
PHASE4B_ALL_SHARES_ENTRY_PAYLOAD_SHA256 = (
    "f99637c5efa2eddc3c26beced868002da8b145c3eb022aba0355316bbe4b97ae"
)

GOLDEN_RELATIVE = "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
GOLDEN_SHA256 = (
    "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1"
)
GOLDEN_CASE_PAYLOAD_SHA256 = (
    "0ace2f642523a62e802db3dc3d045d601743a277e7edf7e2cf214d00619a51bf"
)
GOLDEN_DOCUMENT_PAYLOAD_SHA256 = (
    "e2415f68b5324c60a073a6dec47f069488c72b9ed2605aea2de34241728c4110"
)
GOLDEN_ORDERED_CASE_IDS_SHA256 = (
    "d8c9aa1c8fdcfd833f2d7bbba3e21adcc3e696954b8756ace69405428bbdfad8"
)
PARTIAL_MAPPING_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-mapping-evidence.json"
)
PARTIAL_MAPPING_SHA256 = (
    "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3"
)
TARGET_EVIDENCE_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-execution-evidence.json"
)
TARGET_EVIDENCE_ID = (
    "ti.phase4c.personal-bank-user-counts-golden-target-execution-evidence"
)
TARGET_EVIDENCE_SHA256 = (
    "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002"
)
TARGET_EVIDENCE_CASE_PAYLOAD_SHA256 = (
    "75be10b21c2c006d978575dda314003536ac8920ecd6c6fbe64cfdd264d2b17f"
)
TARGET_EVIDENCE_DOCUMENT_PAYLOAD_SHA256 = (
    "5ca521f808aa67ea4589d044d04a0037e448dc9d2a519e3b6af7d776b2cb89de"
)
SOURCE_CHECKPOINT_COMMIT = "67dddb831bac8499e80f4af57c959e9c6b244519"
SOURCE_CHECKPOINT_COMMITTED_AT = "2026-07-18T09:57:07+08:00"
SOURCE_CHECKPOINT_SUBJECT = "test(java): remove legacy credential expiry bombs"

EXPECTED_RUNTIME_FILE_COUNT = 297
EXPECTED_RUNTIME_MANIFEST_SHA256 = (
    "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79"
)
READ_BUILDER_RELATIVE = (
    "tools/build_phase4c_personal_bank_user_counts_read_contract.py"
)
READ_BUILDER_SHA256 = (
    "f923257659b03ffb0fd52a60894ba5b59df3ba242cf187416bf52edda2eeb3bd"
)

WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
WORM_SHA256 = (
    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
)
JAVA_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
OWNERSHIP_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-effective-data-ownership-status.json"
)
OWNERSHIP_SHA256 = (
    "9f29ee2e27695a1d36a0ca0e5a8ffbe76172b1d3583ca6ee3cf3099e43d758b2"
)
OWNERSHIP_PAYLOAD_SHA256 = (
    "37b9f1a922ced2691f1a040c10eda077c893118f092a6ba68c90fcf640bd0193"
)
OWNERSHIP_MANIFEST_SHA256 = (
    "9767e2c6d6619be0db5f7b3f78335b23ff2020a9d756a2d6a3bf36eccc78908e"
)
OPENAPI_RELATIVE = "openapi/phase4c-personal-bank-user-counts.openapi.json"
ROUTE_DELTA_RELATIVE = "docs/refactor/phase4c/route-parity-delta.csv"

TYPED_REJECTION_CASE_ID = "access-shared-malformed-expiry-value-error"
TYPED_COLLAPSE_CASE_ID = "access-shared-aware-expiry-type-error"
EXPECTED_DISPOSITION_COUNTS = {
    "EXECUTED_FULL_CONTEXT_HTTP": 46,
    "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT": 11,
    "EXECUTED_TYPED_REJECTION": 1,
    "EXECUTED_TYPED_COLLAPSE": 1,
}
EXPECTED_HTTP_STATUS_COUNTS = {
    "200": 34,
    "302": 5,
    "401": 3,
    "403": 10,
    "500": 5,
}
EXPECTED_PRE_BUSINESS_FAMILIES = [
    "BANK_ACCESS",
    "SHARE_ACCESS",
    "TAG_MEMBERSHIP",
    "FAVORITE_MEMBERSHIP",
    "MISTAKE_MEMBERSHIP",
    "QUESTION_SUMMARY",
]
EXPECTED_EXECUTION_SUMMARY = {
    "case_count": 59,
    "http_execution_count": 57,
    "business_jdbc_reached_http_count": 49,
    "pre_business_jdbc_termination_http_count": 8,
    "pre_business_jdbc_termination_status_counts": {"302": 5, "401": 3},
    "non_fault_http_execution_count": 46,
    "fault_http_execution_count": 11,
    "typed_postgresql_disposition_count": 2,
    "api_alias_http_execution_count": 43,
    "web_alias_http_execution_count": 14,
    "http_status_counts": EXPECTED_HTTP_STATUS_COUNTS,
    "bound_only_case_count": 0,
    "mocked_application_result_case_count": 0,
    "junit_leaf_test_count": 60,
    "supplementary_junit_test_count": 1,
}

ROUTES = (
    {
        "route_id": "6858f6fa506f",
        "alias": "api",
        "path": "/api/user/banks/api/<int:bank_id>/user-counts",
        "target_path": "/api/user/banks/api/{bank_id}/user-counts",
        "method": "GET",
        "target_module": "learning",
        "migration_status": "pending",
        "production_cutover": False,
    },
    {
        "route_id": "006913d0d956",
        "alias": "web",
        "path": "/user/banks/api/<int:bank_id>/user-counts",
        "target_path": "/user/banks/api/{bank_id}/user-counts",
        "method": "GET",
        "target_module": "learning",
        "migration_status": "pending",
        "production_cutover": False,
    },
)

# Only these implementation-predecessor sources may advance to successor bytes.
IMPLEMENTATION_PREDECESSOR_SUCCESSOR_ALLOWLIST = (
    "README.md",
    "docs/refactor/05-progress.md",
    "docs/refactor/phase4c/README.md",
    ROUTE_DELTA_RELATIVE,
    "infra/phase2/README.md",
    "infra/phase2/verify-static.sh",
    "tools/phase2_wormhole_successor_acceptance.py",
    "tools/test_phase2_wormhole_successor_acceptance.py",
    "tools/phase4c_http_implementation_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ),
    "tools/phase4c_read_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
)
READ_PREDECESSOR_SUCCESSOR_ALLOWLIST = (
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
    "tools/test_phase4b_personal_bank_share_list_read_contract.py",
)
TAG_PREFLIGHT_NORMALIZED_SUCCESSOR_PATHS = frozenset(
    {
        "tools/phase4c_read_successor_acceptance.py",
        (
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cReadSuccessorAcceptance.java"
        ),
        *READ_PREDECESSOR_SUCCESSOR_ALLOWLIST,
    }
)
PHASE4B_ALL_SHARES_ENTRY_SUCCESSOR_ALLOWLIST = (
    "server/src/test/java/io/saksk/ti/integration/Phase3AuthenticationIT.java",
)
HISTORICAL_SUCCESSOR_ALLOWLIST = (
    *IMPLEMENTATION_PREDECESSOR_SUCCESSOR_ALLOWLIST,
    *READ_PREDECESSOR_SUCCESSOR_ALLOWLIST,
    *PHASE4B_ALL_SHARES_ENTRY_SUCCESSOR_ALLOWLIST,
)

SOURCE_PATHS = {
    "predecessor": PREDECESSOR_RELATIVE,
    "phase4c_read_predecessor": READ_PREDECESSOR_RELATIVE,
    "phase4b_all_shares_entry_anchor": PHASE4B_ALL_SHARES_ENTRY_RELATIVE,
    "phase4b_goldens": GOLDEN_RELATIVE,
    "historical_partial_mapping": PARTIAL_MAPPING_RELATIVE,
    "target_execution_evidence": TARGET_EVIDENCE_RELATIVE,
    "target_execution_it": (
        "server/src/test/java/io/saksk/ti/integration/"
        "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java"
    ),
    "fault_injecting_data_source": (
        "server/src/test/java/io/saksk/ti/support/"
        "Phase4cUserCountsFaultInjectingDataSource.java"
    ),
    "target_execution_seed": (
        "server/src/test/resources/db/phase4c/"
        "071-personal-bank-user-counts-golden-target-seed.sql"
    ),
    "phase3_authentication_it": (
        "server/src/test/java/io/saksk/ti/integration/Phase3AuthenticationIT.java"
    ),
    "auth_schema": "server/src/test/resources/db/phase3/030-auth-schema.sql",
    "share_list_schema": (
        "server/src/test/resources/db/phase4b/"
        "062-personal-bank-share-list-schema.sql"
    ),
    "usage_stats_schema": (
        "server/src/test/resources/db/phase4b/"
        "065-personal-bank-usage-stats-schema.sql"
    ),
    "user_counts_schema": (
        "server/src/test/resources/db/phase4b/"
        "067-personal-bank-user-counts-schema.sql"
    ),
    "phase2_minimal_reference_schema": (
        "server/src/test/resources/db/phase2/minimal-reference-schema.sql"
    ),
    "phase2_readonly_role": (
        "server/src/test/resources/db/phase2/020-test-readonly-role.sql"
    ),
    "container_images": (
        "server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java"
    ),
    "postgres_containers": (
        "server/src/test/java/io/saksk/ti/support/Phase2PostgresContainers.java"
    ),
    "network_it": (
        "server/src/test/java/io/saksk/ti/integration/"
        "LegacyPersonalBankUserCountsNetworkIT.java"
    ),
    "postgres_it": (
        "server/src/test/java/io/saksk/ti/integration/"
        "Phase4cPersonalBankUserCountsJdbcCompatibilityIT.java"
    ),
    "redis_it": (
        "server/src/test/java/io/saksk/ti/web/security/"
        "RedisPersonalBankUserCountsReadRateLimiterIT.java"
    ),
    "server_pom": "server/pom.xml",
    "application_test_configuration": (
        "server/src/main/resources/application-test.yml"
    ),
    "approved_differences": "docs/refactor/phase4c/approved-differences.md",
    "openapi_overlay": OPENAPI_RELATIVE,
    "route_delta": ROUTE_DELTA_RELATIVE,
    "ownership_effective": OWNERSHIP_RELATIVE,
    "worm_tip": WORM_RELATIVE,
    "phase2_build_context_hasher": "infra/phase2/hash-java-build-context.sh",
    "read_contract_builder": READ_BUILDER_RELATIVE,
    "contract_builder": (
        "tools/"
        "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py"
    ),
    "contract_test": (
        "tools/"
        "test_phase4c_personal_bank_user_counts_http_target_execution_contract.py"
    ),
    "python_successor_bridge": (
        "tools/phase4c_http_target_execution_successor_acceptance.py"
    ),
    "java_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ),
    "java_contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionContractParityTest.java"
    ),
    "project_readme": "README.md",
    "progress": "docs/refactor/05-progress.md",
    "phase4c_readme": "docs/refactor/phase4c/README.md",
    "phase2_readme": "infra/phase2/README.md",
    "phase2_static_gate": "infra/phase2/verify-static.sh",
    "phase2_worm_validator": "tools/phase2_wormhole_successor_acceptance.py",
    "phase2_worm_validator_test": (
        "tools/test_phase2_wormhole_successor_acceptance.py"
    ),
    "historical_python_implementation_successor_bridge": (
        "tools/phase4c_http_implementation_successor_acceptance.py"
    ),
    "historical_implementation_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py"
    ),
    "historical_java_implementation_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ),
    "historical_python_read_successor_bridge": (
        "tools/phase4c_read_successor_acceptance.py"
    ),
    "historical_java_read_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ),
    "historical_all_shares_entry_contract_test": (
        "tools/test_phase4b_personal_bank_all_shares_entry_contract.py"
    ),
    "historical_share_list_read_contract_test": (
        "tools/test_phase4b_personal_bank_share_list_read_contract.py"
    ),
    "historical_composition_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_composition_contract.py"
    ),
    "historical_read_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_read_contract.py"
    ),
}

BRIDGE_SOURCE_KEYS = frozenset({"python_successor_bridge", "java_successor_bridge"})
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"

# These exact bytes were captured by the immutable target-execution contract and
# were subsequently handed off through the code-fixed post-push successor.  The
# historical builder must keep reproducing that document even after the listed
# files advance; current bytes are authorized only by the successor contract.
POST_PUSH_CHECKPOINT_ACCEPTED_SHA256 = {
    "tools/phase4c_http_implementation_successor_acceptance.py": (
        "54438d9ee44d391b813a1c3503444dd65d627e3b5932971e49ef549650fbbff4"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ): (
        "1d2c193fb7a63173850bfee7ce382e7b4bc417c5b3879f3ef4bb43187f980275"
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "b81c8fb13f2ce4dd0d917a0876b88a20804bd1d272a7c261563dad9513d42f17"
    ),
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "641c90d33de50daeb3a1a1c9a3ae5027562273f780f88e6a26cf00ad3bd462ac"
    ),
    (
        "tools/test_phase4c_personal_bank_user_counts_"
        "http_target_execution_contract.py"
    ): (
        "a8ce7fc93fe022d16a10e4bdd0fa9bff55788b076eb78601efba373c29c54a4b"
    ),
    (
        "tools/test_phase4c_personal_bank_user_counts_"
        "http_implementation_contract.py"
    ): (
        "9c61d6cefdd980457197fb850f690c6adc1a84fdb3d21905a2a5cfdb1bc258c2"
    ),
    "README.md": (
        "321d23e47d0df0714ea632b2c8c1d3d05d0e67bf69d53e3a52e387e4a949bda4"
    ),
    "docs/refactor/05-progress.md": (
        "e2363a603e9b82368185b6fef3e9882a3e586ce5b5eca14a8b5cddcbca7d6faf"
    ),
    "docs/refactor/phase4c/README.md": (
        "f43ae7ca31038fcc45a05874cfc5c8a460edfe2833936bf4418f37706771d472"
    ),
    "infra/phase2/README.md": (
        "55f9d05fa583e581d6a5b92ec4f1e3e53690a40b5087da456a84ef996b4d3f7b"
    ),
    "infra/phase2/verify-static.sh": (
        "eb01988f26a56293338a7bcd8bc83487b2d8cd0c1c081ae75272bc73dfa28a94"
    ),
    "tools/phase2_wormhole_successor_acceptance.py": (
        "f3a56bd684b508f69bc387d741f1c0277d0c4a7f4130aec984fd359fa8dc0f3a"
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": (
        "ce70d5f35c7725d0f93f27619c5828f294ac259fc20f8594a3ac71b5f5f6f72d"
    ),
    "tools/phase4c_http_target_execution_successor_acceptance.py": (
        "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c"
    ),
    "tools/phase4c_read_successor_acceptance.py": (
        "1e494bce628e87bc2db3d01742fb929752fedaefd7563defccad7b972c951980"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ): (
        "5047c8b0a36450a72ba74a460db115ab33a58861b64216fa2cc67a7ddb0a026d"
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "e37b0418e8018d58135c5b1c55149d9679dfedb21f8b67fca3425b874ea23efc"
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "ffde7c337edf81ba8cf1a457800e89e3150df10b44ea7da50e99436534caa671"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15",
    (
        "tools/"
        "build_phase4c_personal_bank_user_counts_http_target_execution_contract.py"
    ): "51d3c9bf425319e7a0cd7a49e7244f058e09f14ac363f9278000192cb4a69d3b",
}


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def document_payload_sha256(document: dict) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def trust_payload(document: dict) -> dict:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    sources = payload.get("source_contracts")
    if not isinstance(sources, dict):
        raise ValueError("target-execution source contracts are missing")
    normalized = {}
    for name, reference in sources.items():
        if not isinstance(reference, dict):
            raise ValueError(f"invalid target-execution source reference: {name}")
        item = dict(reference)
        if name in BRIDGE_SOURCE_KEYS:
            item["sha256"] = BRIDGE_PROVENANCE_SENTINEL
        normalized[name] = item
    return {**payload, "source_contracts": normalized}


def trust_payload_sha256(document: dict) -> str:
    return sha256_json(trust_payload(document))


def fixed_regular_file(relative: str) -> Path:
    root = ROOT.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"fixed target-execution path escapes Ti-Java: {relative}")
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(
                f"fixed target-execution path contains symlink: {relative}"
            )
    try:
        resolved = (root / candidate).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise FileNotFoundError(
            f"required Phase4C target-execution source is missing: {relative}"
        ) from error
    if not resolved.is_file():
        raise ValueError(f"fixed target-execution path is not a file: {relative}")
    return resolved


def source_reference(relative: str) -> dict:
    return {
        "source": relative,
        "sha256": POST_PUSH_CHECKPOINT_ACCEPTED_SHA256.get(
            relative,
            sha256(fixed_regular_file(relative)),
        ),
    }


def file_manifest(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    if root.is_symlink():
        raise ValueError(f"manifest root contains symlink: {root}")
    if root.is_file():
        paths = [fixed_regular_file(root.relative_to(ROOT).as_posix())]
    else:
        entries = list(root.rglob("*"))
        symlinks = [path for path in entries if path.is_symlink()]
        if symlinks:
            raise ValueError(
                "production manifest contains symlink: "
                f"{symlinks[0].relative_to(ROOT).as_posix()}"
            )
        paths = [
            fixed_regular_file(path.relative_to(ROOT).as_posix())
            for path in entries
            if path.is_file()
        ]
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


def production_runtime_manifest() -> dict[str, str]:
    manifest = file_manifest(ROOT / "server/src/main")
    for relative in (
        "server/pom.xml",
        "server/Dockerfile",
        "server/.dockerignore",
        "server/.mvn",
        "server/mvnw",
        "server/mvnw.cmd",
        "server/build-versions.properties",
        "compose.dev.yml",
        ".env.example",
    ):
        manifest.update(file_manifest(ROOT / relative))
    manifest.update(file_manifest(ROOT / "contracts"))
    manifest.update(file_manifest(ROOT / "openapi"))
    return dict(sorted(manifest.items()))


def validate_predecessor() -> dict:
    path = fixed_regular_file(PREDECESSOR_RELATIVE)
    if sha256(path) != PREDECESSOR_SHA256:
        raise ValueError("HTTP implementation predecessor is not byte immutable")
    predecessor = load_json(path)
    expected_identity = {
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
    }
    if {key: predecessor.get(key) for key in expected_identity} != expected_identity:
        raise ValueError("HTTP implementation predecessor identity drifted")
    if predecessor.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("HTTP implementation predecessor payload field drifted")
    if document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("HTTP implementation predecessor payload is invalid")
    if trust_payload_sha256(predecessor) != PREDECESSOR_TRUST_PAYLOAD_SHA256:
        raise ValueError("HTTP implementation predecessor trust payload drifted")
    return predecessor


def validate_production_surface(predecessor: dict) -> dict:
    embedded = predecessor.get("implementation", {}).get(
        "production_runtime_transition", {}
    ).get("current")
    if not isinstance(embedded, dict):
        raise ValueError("predecessor production runtime surface is missing")
    if embedded.get("file_count") != EXPECTED_RUNTIME_FILE_COUNT:
        raise ValueError("predecessor runtime file count drifted")
    if embedded.get("manifest_sha256") != EXPECTED_RUNTIME_MANIFEST_SHA256:
        raise ValueError("predecessor runtime manifest field drifted")
    embedded_files = embedded.get("files")
    if not isinstance(embedded_files, dict):
        raise ValueError("predecessor runtime files are missing")
    if len(embedded_files) != EXPECTED_RUNTIME_FILE_COUNT:
        raise ValueError("predecessor embedded runtime file set is incomplete")
    if sha256_json(embedded_files) != EXPECTED_RUNTIME_MANIFEST_SHA256:
        raise ValueError("predecessor embedded runtime manifest is invalid")

    if sha256(fixed_regular_file(READ_BUILDER_RELATIVE)) != READ_BUILDER_SHA256:
        raise ValueError("fixed read-contract runtime manifest implementation drifted")
    current = production_runtime_manifest()
    if current != embedded_files:
        successor = tag_preflight_successor().validate_production_runtime_successor(
            ROOT,
            embedded_files,
            current,
            view="full_runtime",
        )
        if (
            successor.accepted_file_count != EXPECTED_RUNTIME_FILE_COUNT
            or successor.accepted_manifest_sha256
            != EXPECTED_RUNTIME_MANIFEST_SHA256
            or successor.current_file_count != len(current)
            or successor.current_manifest_sha256 != sha256_json(current)
            or successor.changed_files
            or successor.deleted_files
        ):
            raise ValueError("tag preflight runtime successor descriptor drifted")
    return {
        "file_count": EXPECTED_RUNTIME_FILE_COUNT,
        "manifest_sha256": EXPECTED_RUNTIME_MANIFEST_SHA256,
        "files": embedded_files,
        "unchanged_from_predecessor": True,
    }


def expected_disposition(case_id: str) -> str:
    if case_id == TYPED_REJECTION_CASE_ID:
        return "EXECUTED_TYPED_REJECTION"
    if case_id == TYPED_COLLAPSE_CASE_ID:
        return "EXECUTED_TYPED_COLLAPSE"
    if case_id.startswith("fault-"):
        return "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT"
    return "EXECUTED_FULL_CONTEXT_HTTP"


def case_alias(golden_case: dict) -> str:
    path = golden_case.get("request", {}).get("path")
    if not isinstance(path, str):
        raise ValueError(f"golden request path is missing: {golden_case.get('case_id')}")
    if path.startswith("/api/user/banks/api/"):
        return "api"
    if path.startswith("/user/banks/api/"):
        return "web"
    raise ValueError(f"golden request has an unexpected alias: {path}")


def require_optional_mapping_field(
        evidence_case: dict,
        mapping_case: dict,
        field: str,
        case_id: str,
) -> None:
    if (field in evidence_case) != (field in mapping_case):
        raise ValueError(f"target mapping field presence drifted: {case_id}:{field}")
    if field in mapping_case and evidence_case[field] != mapping_case[field]:
        raise ValueError(f"target mapping field drifted: {case_id}:{field}")


def expected_fault_evidence(fault_stage: str, target_status: int) -> dict:
    occurrences = {
        "personal_bank_user_counts_total_all": 1,
        "personal_bank_user_counts_favorites_count": 2,
        "personal_bank_user_counts_mistakes_count": 3,
        "personal_bank_user_counts_types_all": 4,
        "personal_bank_user_counts_share_access_probe": 1,
    }
    occurrence = occurrences.get(fault_stage)
    if occurrence is None:
        raise ValueError(f"unknown target fault stage: {fault_stage}")
    family = (
        "SHARE_ACCESS"
        if fault_stage == "personal_bank_user_counts_share_access_probe"
        else "QUESTION_SUMMARY"
    )
    return {
        "family": family,
        "occurrence": occurrence,
        "initial_sqlstate": "42703",
        "poisoned_transaction_sqlstate": "25P02",
        "fault_connection_read_only": True,
        "rollback_after_fault_on_same_connection": True,
        "failed_family_occurrence_has_no_success_record": True,
        "later_same_family_success_after_rollback_on_different_connection_required": (
            target_status == 200
            and family == "QUESTION_SUMMARY"
            and occurrence < 4
        ),
    }


def validate_target_execution_evidence() -> dict:
    golden_path = fixed_regular_file(GOLDEN_RELATIVE)
    if sha256(golden_path) != GOLDEN_SHA256:
        raise ValueError("immutable Phase4B golden bytes drifted")
    golden = load_json(golden_path)
    golden_cases = golden.get("cases")
    if not isinstance(golden_cases, list) or len(golden_cases) != 59:
        raise ValueError("Phase4B golden case count drifted")
    if golden.get("case_count") != 59:
        raise ValueError("Phase4B golden case_count field drifted")
    if golden.get("case_payload_sha256") != GOLDEN_CASE_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden case payload field drifted")
    if sha256_json(golden_cases) != GOLDEN_CASE_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden case payload is invalid")
    if golden.get("document_payload_sha256") != GOLDEN_DOCUMENT_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden document payload field drifted")
    if document_payload_sha256(golden) != GOLDEN_DOCUMENT_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden document payload is invalid")
    golden_case_ids = [item.get("case_id") for item in golden_cases]
    if len(set(golden_case_ids)) != 59 or any(
            not isinstance(case_id, str) for case_id in golden_case_ids):
        raise ValueError("Phase4B golden case ids are invalid")
    if sha256_json(golden_case_ids) != GOLDEN_ORDERED_CASE_IDS_SHA256:
        raise ValueError("Phase4B golden ordered case ids drifted")

    mapping_path = fixed_regular_file(PARTIAL_MAPPING_RELATIVE)
    if sha256(mapping_path) != PARTIAL_MAPPING_SHA256:
        raise ValueError("historical partial mapping is not byte immutable")
    mapping = load_json(mapping_path)
    if mapping.get("claim", {}).get("classification") != (
            "PARTIAL_EXECUTION_MAPPING_LEDGER"):
        raise ValueError("historical partial mapping classification drifted")
    mapping_cases = mapping.get("cases")
    if not isinstance(mapping_cases, list) or [
            item.get("case_id") for item in mapping_cases] != golden_case_ids:
        raise ValueError("historical partial mapping case order drifted")
    mapping_by_id = {item["case_id"]: item for item in mapping_cases}

    evidence_path = fixed_regular_file(TARGET_EVIDENCE_RELATIVE)
    evidence = load_json(evidence_path)
    if evidence.get("schema_version") != 1:
        raise ValueError("unexpected target-execution evidence schema")
    if evidence.get("evidence_id") != TARGET_EVIDENCE_ID:
        raise ValueError("unexpected target-execution evidence id")
    if sha256(evidence_path) != TARGET_EVIDENCE_SHA256:
        raise ValueError("target-execution evidence is not byte immutable")
    if evidence.get("source_golden") != {
        "path": GOLDEN_RELATIVE,
        "sha256": GOLDEN_SHA256,
        "case_count": 59,
        "case_payload_sha256": GOLDEN_CASE_PAYLOAD_SHA256,
        "ordered_case_ids_sha256": GOLDEN_ORDERED_CASE_IDS_SHA256,
        "document_payload_sha256": GOLDEN_DOCUMENT_PAYLOAD_SHA256,
        "canonical_order_preserved": True,
    }:
        raise ValueError("target-execution evidence golden binding drifted")
    if evidence.get("historical_mapping") != {
        "path": PARTIAL_MAPPING_RELATIVE,
        "sha256": PARTIAL_MAPPING_SHA256,
        "evidence_id": (
            "ti.phase4c.personal-bank-user-counts-golden-target-"
            "mapping-evidence"
        ),
        "classification": "PARTIAL_EXECUTION_MAPPING_LEDGER",
        "immutable_historical_predecessor": True,
        "relabeled_or_rewritten": False,
    }:
        raise ValueError("target-execution evidence historical binding drifted")
    claim = evidence.get("claim")
    expected_claim = {
        "classification": "TARGET_EXECUTION_DISPOSITION_LEDGER",
        "full_target_execution_dispositions_closed": True,
        "historical_bound_only_cases_remaining": 0,
        "mocked_application_results_used": False,
        "full_target_parity_closed": False,
        "route_migration_eligible": False,
        "cutover_evidence": False,
    }
    if not isinstance(claim, dict) or any(
            claim.get(key) != value for key, value in expected_claim.items()):
        raise ValueError("target-execution evidence claim drifted or overclaims parity")

    summary = evidence.get("summary")
    if not isinstance(summary, dict) or any(
            summary.get(key) != value
            for key, value in EXPECTED_EXECUTION_SUMMARY.items()):
        raise ValueError("target-execution evidence summary drifted")
    if summary.get("execution_disposition_counts") != EXPECTED_DISPOSITION_COUNTS:
        raise ValueError("target-execution disposition summary drifted")
    cases = evidence.get("cases")
    if not isinstance(cases, list) or len(cases) != 59:
        raise ValueError("target-execution evidence must contain exactly 59 cases")
    if sha256_json(cases) != TARGET_EVIDENCE_CASE_PAYLOAD_SHA256:
        raise ValueError("target-execution evidence case payload is invalid")
    if evidence.get("document_payload_sha256") != (
            TARGET_EVIDENCE_DOCUMENT_PAYLOAD_SHA256):
        raise ValueError("target-execution evidence payload field drifted")
    if document_payload_sha256(evidence) != TARGET_EVIDENCE_DOCUMENT_PAYLOAD_SHA256:
        raise ValueError("target-execution evidence document payload is invalid")

    checkpoint = evidence.get("source_checkpoint")
    if not isinstance(checkpoint, dict) or checkpoint.get("commit") != (
            SOURCE_CHECKPOINT_COMMIT):
        raise ValueError("target-execution source checkpoint drifted")
    if checkpoint.get("committed_at") != SOURCE_CHECKPOINT_COMMITTED_AT:
        raise ValueError("target-execution source checkpoint timestamp drifted")
    if checkpoint.get("subject") != SOURCE_CHECKPOINT_SUBJECT:
        raise ValueError("target-execution source checkpoint subject drifted")
    checkpoint_artifacts = checkpoint.get("artifacts")
    expected_checkpoint_artifacts = {
        "target_execution_test": SOURCE_PATHS["target_execution_it"],
        "fault_injecting_data_source": SOURCE_PATHS[
            "fault_injecting_data_source"],
        "postgresql_seed": SOURCE_PATHS["target_execution_seed"],
    }
    if not isinstance(checkpoint_artifacts, dict) or set(
            checkpoint_artifacts) != set(expected_checkpoint_artifacts):
        raise ValueError("target-execution checkpoint artifact set drifted")
    for name, relative in expected_checkpoint_artifacts.items():
        reference = checkpoint_artifacts.get(name)
        expected_reference = {
            "path": relative,
            "sha256": sha256(fixed_regular_file(relative)),
        }
        if reference != expected_reference:
            raise ValueError(f"target-execution checkpoint artifact drifted: {name}")

    case_ids = [item.get("case_id") for item in cases]
    if case_ids != golden_case_ids or len(set(case_ids)) != 59:
        raise ValueError("target-execution evidence does not preserve golden case order")
    disposition_counts: Counter[str] = Counter()
    http_status_counts: Counter[str] = Counter()
    http_alias_counts: Counter[str] = Counter()
    business_jdbc_reached_http_count = 0
    pre_business_jdbc_termination_http_count = 0
    pre_business_jdbc_termination_status_counts: Counter[str] = Counter()
    expected_execution_case_ids = [
        case_id
        for case_id in golden_case_ids
        if expected_disposition(case_id) == "EXECUTED_FULL_CONTEXT_HTTP"
    ] + [
        case_id
        for case_id in golden_case_ids
        if expected_disposition(case_id)
        == "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT"
    ] + [TYPED_REJECTION_CASE_ID, TYPED_COLLAPSE_CASE_ID]
    execution_ordinals = {
        case_id: ordinal
        for ordinal, case_id in enumerate(expected_execution_case_ids, start=1)
    }
    for ordinal, (item, golden_case) in enumerate(zip(cases, golden_cases), start=1):
        case_id = golden_case["case_id"]
        mapping_case = mapping_by_id[case_id]
        disposition = expected_disposition(case_id)
        alias = case_alias(golden_case)
        if item.get("execution_disposition") != disposition:
            raise ValueError(f"target disposition drifted: {case_id}")
        if item.get("alias") != alias:
            raise ValueError(f"target execution alias drifted: {case_id}")
        if item.get("route_id") != golden_case.get("route_id"):
            raise ValueError(f"target execution route id drifted: {case_id}")
        if item.get("source_case_classification") != mapping_case.get(
                "adapter_execution"):
            raise ValueError(f"target source classification drifted: {case_id}")
        if item.get("historical_binding_ids") != mapping_case.get("bindings"):
            raise ValueError(f"target historical bindings drifted: {case_id}")
        for field in (
            "http_slice_difference_ids",
            "inherited_predecessor_difference_id",
            "target_data_source_case",
            "tracking_note",
        ):
            require_optional_mapping_field(item, mapping_case, field, case_id)
        if item.get("canonical_case_ordinal") != ordinal:
            raise ValueError(f"canonical case ordinal drifted: {case_id}")
        execution_ordinal = execution_ordinals[case_id]
        if item.get("execution_ordinal") != execution_ordinal:
            raise ValueError(f"execution ordinal drifted: {case_id}")
        if item.get("junit", {}).get("disposition_leaf_ordinal") != (
                execution_ordinal + 1):
            raise ValueError(f"JUnit disposition leaf ordinal drifted: {case_id}")
        source_request = item.get("source_request")
        golden_request = golden_case.get("request", {})
        expected_source_request = {
            "method": golden_request.get("method"),
            "path": golden_request.get("path"),
            "query": golden_request.get("query"),
            "credential_mode": golden_case.get("credential_mode"),
            "session_actor": golden_case.get("session_actor"),
            "bearer_actor": golden_case.get("bearer_actor"),
        }
        if source_request != expected_source_request:
            raise ValueError(f"target source request binding drifted: {case_id}")
        if item.get("source_golden_response_status") != golden_case.get(
                "response", {}).get("status"):
            raise ValueError(f"source golden response status drifted: {case_id}")
        typed = disposition.startswith("EXECUTED_TYPED_")
        if item.get("http_execution") is not (not typed):
            raise ValueError(f"target HTTP execution marker drifted: {case_id}")
        disposition_counts[disposition] += 1
        if typed:
            if "target_status" not in item or item["target_status"] is not None:
                raise ValueError(f"typed target status must be null: {case_id}")
            if item.get("fault_evidence") is not None:
                raise ValueError(f"typed case also contains fault evidence: {case_id}")
            if case_id == TYPED_REJECTION_CASE_ID:
                expected_typed = {
                    "input": "malformed-expiry",
                    "operation": (
                        "CAST parameter AS timestamp without time zone during "
                        "bank_shares insert"
                    ),
                    "attempted_bank_share_id": 99656,
                    "attempted_bank_share_record_id": 99676,
                    "sqlstate": "22007",
                    "persisted_bank_share_row_count": 0,
                    "bank_shares_total_unchanged": True,
                    "bank_share_records_total_unchanged": True,
                }
            else:
                expected_typed = {
                    "inputs": [
                        "2026-07-17 13:00:00+08:00",
                        "2026-07-17 13:00:00-05:00",
                    ],
                    "postgresql_type": "timestamp without time zone",
                    "projected_local_datetime": "2026-07-17T13:00:00",
                    "both_inputs_equal_after_projection": True,
                    "source_offset_provenance_erased": True,
                    "approved_null_expiry_bank_share_id": 99660,
                    "approved_null_expiry_is_sql_null": True,
                    "bank_shares_total_unchanged": True,
                    "bank_share_records_total_unchanged": True,
                }
            if item.get("typed_evidence") != expected_typed:
                raise ValueError(f"typed target evidence drifted: {case_id}")
            continue
        target_status = item.get("target_status")
        expected_status = mapping_case.get("target_status")
        if not isinstance(target_status, int) or target_status != expected_status:
            raise ValueError(f"target HTTP status drifted: {case_id}")
        expected_side_effects = {
            "nine_table_database_fingerprint_unchanged": True,
            "write_dml_count": 0,
            "users_last_active_write_dml_count": 0,
            "schema_mutation_count": 0,
            "rate_limit_assertion_mode": "RESPONSE_HEADER_CONDITIONED",
        }
        if item.get("side_effect_assertions") != expected_side_effects:
            raise ValueError(f"target HTTP side effects drifted: {case_id}")
        fault_stage = golden_case.get("fault_injection", {}).get("stage")
        if fault_stage is None:
            if item.get("fault_evidence") is not None or item.get(
                    "typed_evidence") is not None:
                raise ValueError(
                    f"ordinary HTTP case has specialized evidence: {case_id}"
                )
        else:
            if item.get("fault_evidence") != expected_fault_evidence(
                    fault_stage, target_status):
                raise ValueError(f"target PostgreSQL abort evidence drifted: {case_id}")
            if item.get("typed_evidence") is not None:
                raise ValueError(f"fault case also contains typed evidence: {case_id}")
        http_status_counts[str(target_status)] += 1
        http_alias_counts[alias] += 1
        sql_boundary = item.get("sql_boundary")
        if not isinstance(sql_boundary, dict) or not isinstance(
                sql_boundary.get("business_jdbc_reached"), bool):
            raise ValueError(
                f"target HTTP business JDBC marker drifted: {case_id}"
            )
        if sql_boundary["business_jdbc_reached"]:
            business_jdbc_reached_http_count += 1
            if sql_boundary.get("business_connections_read_only") is not True:
                raise ValueError(
                    f"target HTTP business JDBC read-only marker drifted: {case_id}"
                )
        else:
            pre_business_jdbc_termination_http_count += 1
            pre_business_jdbc_termination_status_counts[str(target_status)] += 1
            expected_termination = (
                "WEB_PRE_AUTHENTICATION"
                if target_status == 302
                else "AUTHENTICATION"
            )
            execution_families = sql_boundary.get("execution_families")
            if (
                target_status not in {302, 401}
                or sql_boundary.get("execution_family_assertion") != "EXACT"
                or sql_boundary.get("termination") != expected_termination
                or not isinstance(execution_families, list)
                or (
                    target_status == 302
                    and execution_families != []
                )
                or (
                    target_status == 401
                    and execution_families not in ([], ["AUTHORITY_USERS"])
                )
                or (
                    target_status == 401
                    and sql_boundary.get("business_execution_families_absent")
                    != EXPECTED_PRE_BUSINESS_FAMILIES
                )
            ):
                raise ValueError(
                    f"target HTTP pre-business termination boundary drifted: {case_id}"
                )
    if dict(sorted(disposition_counts.items())) != dict(
            sorted(EXPECTED_DISPOSITION_COUNTS.items())):
        raise ValueError("target execution disposition counts drifted")
    if dict(sorted(http_status_counts.items())) != EXPECTED_HTTP_STATUS_COUNTS:
        raise ValueError("target execution HTTP status distribution drifted")
    if dict(sorted(http_alias_counts.items())) != {"api": 43, "web": 14}:
        raise ValueError("target execution HTTP alias distribution drifted")
    if business_jdbc_reached_http_count != 49 or (
            pre_business_jdbc_termination_http_count != 8):
        raise ValueError("target execution business JDBC reach counts drifted")
    if dict(sorted(pre_business_jdbc_termination_status_counts.items())) != {
            "302": 5, "401": 3}:
        raise ValueError("target execution pre-business status counts drifted")

    harness = evidence.get("execution_harness", {})
    expected_harness_boundaries = {
        "full_spring_context": True,
        "full_production_filter_chain": True,
        "excluded_production_filters": [],
        "mocked_application_or_authentication_ports": [],
        "transport": "MockMvc",
        "real_tomcat_transport": False,
        "same_thread_execution": True,
    }
    if not isinstance(harness, dict) or any(
            harness.get(field) != value
            for field, value in expected_harness_boundaries.items()):
        raise ValueError("target-execution harness boundary drifted")
    if harness.get("postgresql", {}).get("version") != "18.4" or harness.get(
            "postgresql", {}).get("real_container") is not True:
        raise ValueError("target-execution PostgreSQL harness drifted")
    if harness.get("redis", {}).get("version") != "7.4.7" or harness.get(
            "redis", {}).get("real_container") is not True:
        raise ValueError("target-execution Redis harness drifted")

    boundaries = evidence.get("route_worm_and_parity_boundaries", {})
    if boundaries.get("implementation_worm") != {
        "path": WORM_RELATIVE,
        "sha256": WORM_SHA256,
        "reused": True,
    }:
        raise ValueError("target-execution evidence did not reuse the fifth WORM")
    expected_boundaries = {
        "implementation_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
        "implementation_chain_node_count": 5,
        "target_execution_worm_created": False,
        "route_counts": {"migrated": 11, "pending": 600, "cutover": 0},
        "full_target_parity_closed": False,
        "route_migration_eligible": False,
        "production_cutover_evidence": False,
    }
    if not isinstance(boundaries, dict) or any(
            boundaries.get(field) != value
            for field, value in expected_boundaries.items()):
        raise ValueError("target-execution route/WORM boundary drifted")

    return {
        "target_execution": {
            **source_reference(TARGET_EVIDENCE_RELATIVE),
            "evidence_id": TARGET_EVIDENCE_ID,
            "case_payload_sha256": TARGET_EVIDENCE_CASE_PAYLOAD_SHA256,
            "document_payload_sha256": evidence["document_payload_sha256"],
            "case_ids_sha256": sha256_json(case_ids),
            "summary": {key: summary[key] for key in EXPECTED_EXECUTION_SUMMARY},
            "disposition_counts": dict(sorted(disposition_counts.items())),
        },
        "historical_partial_mapping": {
            **source_reference(PARTIAL_MAPPING_RELATIVE),
            "classification": "PARTIAL_EXECUTION_MAPPING_LEDGER",
            "case_count": 59,
            "immutable": True,
        },
        "junit": {
            **source_reference(SOURCE_PATHS["target_execution_it"]),
            "case_leaf_count": 59,
            "supplementary_leaf_count": 1,
            "total_leaf_count": 60,
        },
        "postgresql": {
            "version": "18.4",
            "real_container": True,
            "read_only": True,
            "users_last_active_write_dml_count": 0,
        },
    }


def validate_routes_and_openapi(predecessor: dict) -> dict:
    inherited = predecessor.get("implementation", {}).get("routes_and_openapi")
    if not isinstance(inherited, dict):
        raise ValueError("predecessor route and OpenAPI evidence is missing")
    expected_counts = {
        "implemented_pending_get_count": 2,
        "migrated_operation_count": 11,
        "pending_operation_count": 600,
        "production_cutover_operation_count": 0,
        "route_migration_eligible": False,
        "counted_methods": ["GET"],
        "derived_methods": ["HEAD", "OPTIONS"],
    }
    if inherited.get("routes") != list(ROUTES) or any(
            inherited.get(key) != value for key, value in expected_counts.items()):
        raise ValueError("predecessor route accounting drifted")
    openapi_reference = inherited.get("openapi_overlay")
    if not isinstance(openapi_reference, dict) or openapi_reference.get("source") != (
            OPENAPI_RELATIVE):
        raise ValueError("predecessor OpenAPI reference drifted")
    if sha256(fixed_regular_file(OPENAPI_RELATIVE)) != openapi_reference.get("sha256"):
        raise ValueError("Phase4C OpenAPI bytes drifted")

    with fixed_regular_file(ROUTE_DELTA_RELATIVE).open(
            newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 2 or {row.get("route_id") for row in rows} != {
            route["route_id"] for route in ROUTES}:
        raise ValueError("route delta must retain the exact two GET routes")
    by_id = {row["route_id"]: row for row in rows}
    for route in ROUTES:
        row = by_id[route["route_id"]]
        required = {
            "path": route["path"],
            "method": "GET",
            "phase4c_target_module": "learning",
            "phase4c_migration_status": "pending",
            "production_cutover": "false",
        }
        if any(row.get(key) != value for key, value in required.items()):
            raise ValueError(f"route delta overclaims migration: {route['route_id']}")
    return {
        **{key: inherited[key] for key in inherited if key not in {
            "route_delta", "openapi_overlay"}},
        "route_delta": source_reference(ROUTE_DELTA_RELATIVE),
        "openapi_overlay": source_reference(OPENAPI_RELATIVE),
    }


def validate_data_ownership() -> dict:
    path = fixed_regular_file(OWNERSHIP_RELATIVE)
    if sha256(path) != OWNERSHIP_SHA256:
        raise ValueError("effective data ownership bytes drifted")
    ownership = load_json(path)
    if ownership.get("document_payload_sha256") != OWNERSHIP_PAYLOAD_SHA256:
        raise ValueError("effective data ownership payload field drifted")
    if document_payload_sha256(ownership) != OWNERSHIP_PAYLOAD_SHA256:
        raise ValueError("effective data ownership payload is invalid")
    effective = ownership.get("effective")
    expected = {
        "resource_count": 160,
        "resources_with_exactly_one_owner": 160,
        "canonical_owner_manifest_sha256": OWNERSHIP_MANIFEST_SHA256,
    }
    if not isinstance(effective, dict) or any(
            effective.get(key) != value for key, value in expected.items()):
        raise ValueError("effective data ownership accounting drifted")
    return {
        **source_reference(OWNERSHIP_RELATIVE),
        "document_payload_sha256": OWNERSHIP_PAYLOAD_SHA256,
        **expected,
        "unchanged_from_predecessor": True,
    }


def java_build_context_sha256() -> str:
    result = subprocess.run(
        [str(fixed_regular_file("infra/phase2/hash-java-build-context.sh"))],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def validate_worm() -> dict:
    path = fixed_regular_file(WORM_RELATIVE)
    if sha256(path) != WORM_SHA256:
        raise ValueError("fixed implementation WORM bytes drifted")
    build_context = java_build_context_sha256()
    if build_context != JAVA_BUILD_CONTEXT_SHA256:
        successor = tag_preflight_successor().validate_worm_successor(
            ROOT,
            WORM_SHA256,
            JAVA_BUILD_CONTEXT_SHA256,
        )
        if (
            successor.accepted_chain_node_count != 5
            or successor.current_build_context_sha256 != build_context
            or successor.current_chain_node_count != 8
        ):
            raise ValueError("tag preflight WORM successor descriptor drifted")
    worm = load_json(path)
    java = worm.get("java", {})
    if java.get("buildContextSha256") != JAVA_BUILD_CONTEXT_SHA256:
        raise ValueError("implementation WORM Java build context binding drifted")
    if java.get("hibernateDdlAuto") != "validate":
        raise ValueError("implementation WORM schema mode drifted")
    read_role = worm.get("readRole", {})
    for field in (
        "selectPassed",
        "defaultTransactionReadOnly",
        "aclVerifiedWithReadOnlyDefaultDisabled",
        "insertRejected",
        "updateRejected",
        "deleteRejected",
        "ddlRejected",
        "temporaryDdlRejected",
    ):
        if read_role.get(field) is not True:
            raise ValueError(f"implementation WORM read-role field drifted: {field}")
    if read_role.get("temporaryPrivilege") is not False:
        raise ValueError("implementation WORM unexpectedly permits TEMP")
    return {
        **source_reference(WORM_RELATIVE),
        "java_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
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


def predecessor_source_index(predecessor: dict) -> dict[str, str]:
    sources = predecessor.get("source_contracts")
    if not isinstance(sources, dict):
        raise ValueError("predecessor source contracts are missing")
    index: dict[str, str] = {}
    for reference in sources.values():
        if not isinstance(reference, dict):
            raise ValueError("predecessor source reference is invalid")
        relative = reference.get("source")
        digest = reference.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ValueError("predecessor source reference is incomplete")
        if relative in index and index[relative] != digest:
            raise ValueError(f"predecessor has conflicting source hashes: {relative}")
        index[relative] = digest
    return index


def predecessor_terminal_overrides(predecessor: dict) -> dict[str, str]:
    historical = predecessor.get("historical_successor_acceptance")
    if not isinstance(historical, dict):
        raise ValueError("predecessor historical successor acceptance is missing")
    index: dict[str, str] = {}
    for value in historical.values():
        if not isinstance(value, dict):
            continue
        for reference in value.values():
            if not isinstance(reference, dict):
                continue
            relative = reference.get("source")
            digest = reference.get("successor_sha256")
            if not isinstance(relative, str) or not isinstance(digest, str):
                continue
            if relative in index and index[relative] != digest:
                raise ValueError(
                    f"predecessor has conflicting terminal hashes: {relative}"
                )
            index[relative] = digest
    return index


def validate_additional_anchor_contract(
        relative: str,
        expected_sha256: str,
        expected_payload_sha256: str,
        expected_id: str,
        expected_status: str,
) -> dict:
    path = fixed_regular_file(relative)
    if sha256(path) != expected_sha256:
        raise ValueError(f"historical anchor contract bytes drifted: {relative}")
    document = load_json(path)
    if document.get("contract_id") != expected_id:
        raise ValueError(f"historical anchor contract id drifted: {relative}")
    if document.get("status") != expected_status:
        raise ValueError(f"historical anchor contract status drifted: {relative}")
    if document.get("document_payload_sha256") != expected_payload_sha256:
        raise ValueError(f"historical anchor payload field drifted: {relative}")
    if document_payload_sha256(document) != expected_payload_sha256:
        raise ValueError(f"historical anchor payload is invalid: {relative}")
    return document


def validate_historical_successor_acceptance(predecessor: dict) -> dict:
    direct = predecessor_source_index(predecessor)
    terminal = predecessor_terminal_overrides(predecessor)
    read_predecessor = validate_additional_anchor_contract(
        READ_PREDECESSOR_RELATIVE,
        READ_PREDECESSOR_SHA256,
        READ_PREDECESSOR_PAYLOAD_SHA256,
        "ti.phase4c.personal-bank-user-counts-read-contract",
        "implemented_and_targeted_verified_http_aliases_deferred",
    )
    read_direct = predecessor_source_index(read_predecessor)
    all_shares_entry = validate_additional_anchor_contract(
        PHASE4B_ALL_SHARES_ENTRY_RELATIVE,
        PHASE4B_ALL_SHARES_ENTRY_SHA256,
        PHASE4B_ALL_SHARES_ENTRY_PAYLOAD_SHA256,
        "ti.phase4b.personal-bank-all-shares-entry-contract",
        "entry_gate_passed_implementation_not_started",
    )
    all_shares_direct = predecessor_source_index(all_shares_entry)
    overrides = {}
    for relative in HISTORICAL_SUCCESSOR_ALLOWLIST:
        if relative in IMPLEMENTATION_PREDECESSOR_SUCCESSOR_ALLOWLIST:
            accepted = direct.get(relative)
            provenance = "predecessor.source_contracts"
            if accepted is None:
                accepted = terminal.get(relative)
                provenance = "predecessor.historical_successor_acceptance"
        elif relative in READ_PREDECESSOR_SUCCESSOR_ALLOWLIST:
            accepted = read_direct.get(relative)
            provenance = "phase4c_read_predecessor.source_contracts"
        elif relative in PHASE4B_ALL_SHARES_ENTRY_SUCCESSOR_ALLOWLIST:
            accepted = all_shares_direct.get(relative)
            provenance = "phase4b_all_shares_entry.source_contracts"
        else:  # pragma: no cover - exact tuple partition above is code-fixed.
            accepted = None
            provenance = ""
        if accepted is None:
            raise ValueError(
                f"allowlisted source has no predecessor-anchored hash: {relative}"
            )
        normalized = POST_PUSH_CHECKPOINT_ACCEPTED_SHA256.get(relative)
        if relative in TAG_PREFLIGHT_NORMALIZED_SUCCESSOR_PATHS:
            successor = tag_preflight_successor()
            if (
                normalized is None
                or successor.accepted_sha256(relative) != normalized
                or successor.successor_sha256(ROOT, relative)
                != sha256(fixed_regular_file(relative))
            ):
                raise ValueError(
                    "tag preflight historical source normalization drifted: "
                    f"{relative}"
                )
        overrides[relative] = {
            "source": relative,
            "accepted_sha256": accepted,
            "accepted_hash_provenance": provenance,
            "successor_sha256": POST_PUSH_CHECKPOINT_ACCEPTED_SHA256.get(
                relative,
                sha256(fixed_regular_file(relative)),
            ),
        }
    if tuple(sorted(overrides)) != tuple(sorted(HISTORICAL_SUCCESSOR_ALLOWLIST)):
        raise ValueError("historical successor allowlist is not exact")
    return {
        "predecessor_sha256": PREDECESSOR_SHA256,
        "predecessor_trust_payload_sha256": PREDECESSOR_TRUST_PAYLOAD_SHA256,
        "anchored_source_overrides": dict(sorted(overrides.items())),
        "successor_allowlist": sorted(HISTORICAL_SUCCESSOR_ALLOWLIST),
        "successor_allowlist_exact": True,
        "accepted_hashes_independently_located": True,
        "predecessor_rewrite_forbidden": True,
        "arbitrary_source_hash_lookup_forbidden": True,
        "current_bridges_excluded_from_historical_accepted_hash_allowlist": True,
    }


def build_contract() -> dict:
    predecessor = validate_predecessor()
    production_surface = validate_production_surface(predecessor)
    verification = validate_target_execution_evidence()
    routes = validate_routes_and_openapi(predecessor)
    ownership = validate_data_ownership()
    worm = validate_worm()
    historical = validate_historical_successor_acceptance(predecessor)

    source_contracts = {
        name: source_reference(relative)
        for name, relative in SOURCE_PATHS.items()
    }
    if set(source_contracts) != set(SOURCE_PATHS):
        raise ValueError("target-execution source contract key drift")
    if len({item["source"] for item in source_contracts.values()}) != len(
            source_contracts):
        raise ValueError("duplicate target-execution source references are forbidden")

    contract = {
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
        "source_contracts": dict(sorted(source_contracts.items())),
        "historical_successor_acceptance": historical,
        "bridge_provenance": {
            "state": "bootstrap_pending_post_push_external_git_anchor",
            "normalized_source_keys": sorted(BRIDGE_SOURCE_KEYS),
            "normalization_sentinel": BRIDGE_PROVENANCE_SENTINEL,
            "source_hashes_normalized_to_break_recursive_cycle": True,
            "physical_hash_binding_scope": "current_contract_and_worktree_only",
            "external_bridge_bytes_anchor_complete": False,
            "post_push_external_git_anchor_required_before_route_promotion": True,
        },
        "production_surface": production_surface,
        "verification_evidence": verification,
        "routes_and_openapi": routes,
        "data_ownership": ownership,
        "worm_evidence": worm,
        "authorization": {
            "target_dispositions_executed": True,
            "all_59_target_dispositions_executed": True,
            "typed_parity_review_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "external_bridge_bytes_anchor_complete": False,
            "route_promotion_blocked_by_bridge_bootstrap": True,
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
            "target_dispositions_executed": True,
            "all_59_target_dispositions_executed": True,
            "typed_parity_review_complete": False,
            "case_count": 59,
            "http_execution_count": 57,
            "business_jdbc_reached_http_count": 49,
            "pre_business_jdbc_termination_http_count": 8,
            "pre_business_jdbc_termination_status_counts": {
                "302": 5,
                "401": 3,
            },
            "typed_postgresql_disposition_count": 2,
            "bound_only_case_count": 0,
            "mocked_application_result_case_count": 0,
            "junit_leaf_test_count": 60,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "external_bridge_bytes_anchor_complete": False,
            "post_push_external_git_anchor_required_before_route_migration": True,
            "implemented_pending_get_count": 2,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "production_cutover": False,
            "effective_resource_count": 160,
            "resources_with_exactly_one_owner": 160,
            "production_runtime_unchanged": True,
            "new_worm": False,
            "new_worm_report_created": False,
            "production_build_context_unchanged": True,
            "operator_and_real_migration_remain_blocked": True,
            "next_gate": NEXT_GATE,
        },
    }
    contract["document_payload_sha256"] = document_payload_sha256(contract)
    return contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    output = parse_args().output.resolve()
    contract = build_contract()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
