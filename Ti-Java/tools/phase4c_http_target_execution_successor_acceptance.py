#!/usr/bin/env python3
"""Bootstrap validator for the Phase 4C target-execution contract.

This module deliberately does not import the HTTP implementation successor
bridge.  Every path that it reads is selected by code, never by a path
reported by the contract under validation.  Its bridge-normalized trust
payload breaks a recursive hash cycle; a later Git-anchored node must fix the
physical bytes of this bridge before either route can be promoted.
"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import importlib
import json
from pathlib import Path
import subprocess


def _tag_preflight_successor():
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


def _validate_runtime_successor(*args, **kwargs):
    return _tag_preflight_successor().validate_production_runtime_successor(
        *args, **kwargs
    )


def _validate_worm_successor(*args, **kwargs):
    return _tag_preflight_successor().validate_worm_successor(*args, **kwargs)


CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-contract"
)
CONTRACT_STATUS = (
    "target_dispositions_executed_typed_parity_review_pending_routes_pending"
)
CONTRACT_SCOPE = "phase4c-personal-bank-user-counts-http-target-execution"
CONTRACT_CAPTURED_AT = "2026-07-18T10:00:00+08:00"
NEXT_GATE = (
    "commit_and_push_this_bootstrap_checkpoint_then_anchor_its_git_commit_"
    "contract_sha256_and_both_bridge_sha256_in_the_next_node_before_typed_"
    "parity_network_redis_identity_review_or_route_migration"
)
CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-contract.json"
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

# Settle this only after the contract and both bridge source files are final.
# The bridge hashes are normalized to BRIDGE_PROVENANCE_SENTINEL first, so the
# digest remains stable when this constant is replaced with the final value.
TRUST_PAYLOAD_SHA256 = (
    "0634daf8ba1489a3f4fa6f1f958ee5042113fb2e62e2af9f864159c14fd92500"
)
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"
BRIDGE_SOURCE_KEYS = frozenset({
    "python_successor_bridge",
    "java_successor_bridge",
})

TARGET_EXECUTION_EVIDENCE_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-execution-evidence.json"
)
TARGET_EXECUTION_EVIDENCE_ID = (
    "ti.phase4c.personal-bank-user-counts-golden-target-execution-evidence"
)
TARGET_EXECUTION_EVIDENCE_SHA256 = (
    "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002"
)
TARGET_EXECUTION_EVIDENCE_PAYLOAD_SHA256 = (
    "5ca521f808aa67ea4589d044d04a0037e448dc9d2a519e3b6af7d776b2cb89de"
)
TARGET_EXECUTION_CASE_PAYLOAD_SHA256 = (
    "75be10b21c2c006d978575dda314003536ac8920ecd6c6fbe64cfdd264d2b17f"
)
EXPECTED_PRE_BUSINESS_FAMILIES = [
    "BANK_ACCESS",
    "SHARE_ACCESS",
    "TAG_MEMBERSHIP",
    "FAVORITE_MEMBERSHIP",
    "MISTAKE_MEMBERSHIP",
    "QUESTION_SUMMARY",
]
PHASE4B_GOLDEN_RELATIVE = (
    "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
)
PHASE4B_GOLDEN_SHA256 = (
    "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1"
)
PHASE4B_CASE_PAYLOAD_SHA256 = (
    "0ace2f642523a62e802db3dc3d045d601743a277e7edf7e2cf214d00619a51bf"
)
PHASE4B_DOCUMENT_PAYLOAD_SHA256 = (
    "e2415f68b5324c60a073a6dec47f069488c72b9ed2605aea2de34241728c4110"
)
PHASE4B_CASE_IDS_SHA256 = (
    "d8c9aa1c8fdcfd833f2d7bbba3e21adcc3e696954b8756ace69405428bbdfad8"
)
HISTORICAL_MAPPING_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-mapping-evidence.json"
)
HISTORICAL_MAPPING_SHA256 = (
    "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3"
)
TARGET_EXECUTION_IT_RELATIVE = (
    "server/src/test/java/io/saksk/ti/integration/"
    "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java"
)
FAULT_DATA_SOURCE_RELATIVE = (
    "server/src/test/java/io/saksk/ti/support/"
    "Phase4cUserCountsFaultInjectingDataSource.java"
)
TARGET_EXECUTION_SEED_RELATIVE = (
    "server/src/test/resources/db/phase4c/"
    "071-personal-bank-user-counts-golden-target-seed.sql"
)
SOURCE_CHECKPOINT_COMMIT = "67dddb831bac8499e80f4af57c959e9c6b244519"
SOURCE_CHECKPOINT_COMMITTED_AT = "2026-07-18T09:57:07+08:00"
SOURCE_CHECKPOINT_SUBJECT = "test(java): remove legacy credential expiry bombs"

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
PRODUCTION_FILE_COUNT = 297
PRODUCTION_MANIFEST_SHA256 = (
    "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79"
)
ROUTE_DELTA_SHA256 = (
    "fc3c61f84fba411ed2b5509f841c0183c4da7250ecbfc9c6d1ba03cbb3c01f9e"
)
OPENAPI_SHA256 = (
    "076957f391fd9aed65861d0633ad4b21d88b391df5217b10e2105b88b56605c9"
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
READ_BUILDER_RELATIVE = (
    "tools/build_phase4c_personal_bank_user_counts_read_contract.py"
)
READ_BUILDER_SHA256 = (
    "f923257659b03ffb0fd52a60894ba5b59df3ba242cf187416bf52edda2eeb3bd"
)

# Contract sources are exact: a contract cannot redirect any key to a path of
# its choosing.  This preliminary map follows the agreed target-execution
# schema and is expanded only by editing this trust root together with review.
SOURCE_PATHS = {
    "predecessor": PREDECESSOR_RELATIVE,
    "phase4c_read_predecessor": READ_PREDECESSOR_RELATIVE,
    "phase4b_all_shares_entry_anchor": PHASE4B_ALL_SHARES_ENTRY_RELATIVE,
    "phase4b_goldens": PHASE4B_GOLDEN_RELATIVE,
    "historical_partial_mapping": HISTORICAL_MAPPING_RELATIVE,
    "target_execution_evidence": TARGET_EXECUTION_EVIDENCE_RELATIVE,
    "target_execution_it": TARGET_EXECUTION_IT_RELATIVE,
    "fault_injecting_data_source": FAULT_DATA_SOURCE_RELATIVE,
    "target_execution_seed": TARGET_EXECUTION_SEED_RELATIVE,
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
    "openapi_overlay": "openapi/phase4c-personal-bank-user-counts.openapi.json",
    "route_delta": "docs/refactor/phase4c/route-parity-delta.csv",
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

# These accepted values are taken only from physically fixed predecessor and
# historical-anchor records. They are not discovered at runtime and no path
# outside this map is authorized.
HISTORICAL_SOURCE_ACCEPTED_SHA256 = {
    "README.md": (
        "37d97e57cd8526615d828601dc56fc344b6e9e8cd400da85ebb9bf77b87ca20e"
    ),
    "docs/refactor/05-progress.md": (
        "12935066fb4a2c53c78213e2b269028b9e24342034640467cfcb1d4bb47858a9"
    ),
    "docs/refactor/phase4c/README.md": (
        "c44612d78bdafa7bc550feed7496588f0d163f8f1dda72fba917a4590f1f7064"
    ),
    "docs/refactor/phase4c/route-parity-delta.csv": ROUTE_DELTA_SHA256,
    "infra/phase2/README.md": (
        "2d5d4fa1f26ce1fde3a273631f309aab5496c64641acba0b26b814e3ec4b64d1"
    ),
    "infra/phase2/verify-static.sh": (
        "5e26d01247dce13342972d4b189460f7ae6f788506c57550b42b5b1f4f658821"
    ),
    "tools/phase2_wormhole_successor_acceptance.py": (
        "ac0f2adf78f09fd25fa27d2846dd972e877ca00f63dd37eb4efb05935c50cc13"
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": (
        "c30199997348f971f29a9dfd1d87cba67513c56bb9e241dfc23d195a479ff230"
    ),
    "tools/phase4c_http_implementation_successor_acceptance.py": (
        "e46e28e065613dec3cedfcadcddaeda91354c8901543dd3f5eeb6d8bff4cd1cd"
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py": (
        "f4d9ae7fe8b2c48238469a7b53a434d6c10269aadfbc154bea7d30eddfceddc6"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ): "cd212636e08ce74efa9efbc3ee988f14b69032f6fc3f7e927a591737b35e29d3",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ): "7b486e7dfe6e6e7e24435854e7c0545b5f9fdaec785974fb44cd0978f8e40fa5",
    "tools/phase4c_read_successor_acceptance.py": (
        "af08c2611bfb4f9a566ac01a644c65807a0b2eb3f60c61ad0344e8c958cda8a9"
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "2ed3c3d1168aeea07d863bcdd6c81522bc59e78d253242b9f36f3808b9ca0b40"
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "6869964c169b6970df0c9f762957664f2e711c2abb309a4e5a2a3689cb636f29"
    ),
    "server/src/test/java/io/saksk/ti/integration/Phase3AuthenticationIT.java": (
        "cbafdbd774ab13429c834b20c7a89eab63f10f35edfc20173181bbbdf0e2e85c"
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "b41ad9f6252ec74c4914ad9bd5652d150bd08359b26fb26498c34fd3a337a186"
    ),
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "5299925446ed7ef84828ea7de875cfdd070bff260e06a590cad2fd474473dd77"
    ),
}
HISTORICAL_SOURCE_ACCEPTED_PROVENANCE = {
    relative: (
        "phase4c_read_predecessor.source_contracts"
        if relative in {
            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_read_contract.py",
        }
        else "phase4b_all_shares_entry.source_contracts"
        if relative == (
            "server/src/test/java/io/saksk/ti/integration/Phase3AuthenticationIT.java"
        )
        else "predecessor.historical_successor_acceptance"
        if relative in {
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            (
                "server/src/test/java/io/saksk/ti/architecture/"
                "Phase4cReadSuccessorAcceptance.java"
            ),
            "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
        }
        else "predecessor.source_contracts"
    )
    for relative in HISTORICAL_SOURCE_ACCEPTED_SHA256
}

SUMMARY_EXPECTED = {
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
    "http_status_counts": {
        "200": 34,
        "302": 5,
        "401": 3,
        "403": 10,
        "500": 5,
    },
    "bound_only_case_count": 0,
    "mocked_application_result_case_count": 0,
    "junit_leaf_test_count": 60,
    "supplementary_junit_test_count": 1,
}
DISPOSITION_COUNTS_EXPECTED = {
    "EXECUTED_FULL_CONTEXT_HTTP": 46,
    "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT": 11,
    "EXECUTED_TYPED_REJECTION": 1,
    "EXECUTED_TYPED_COLLAPSE": 1,
}
TYPED_DISPOSITIONS = {
    "access-shared-malformed-expiry-value-error": "EXECUTED_TYPED_REJECTION",
    "access-shared-aware-expiry-type-error": "EXECUTED_TYPED_COLLAPSE",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _payload_sha256(document: dict) -> str:
    return _sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def _bridge_normalized_payload_sha256(document: dict) -> str:
    """Hash a contract while normalizing only the two fixed bridge keys."""
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    sources = payload.get("source_contracts")
    if not isinstance(sources, dict):
        raise AssertionError("contract source references are missing")
    normalized: dict[str, dict] = {}
    for name, reference in sources.items():
        if not isinstance(reference, dict):
            raise AssertionError(f"invalid contract source reference: {name}")
        item = dict(reference)
        if name in BRIDGE_SOURCE_KEYS:
            item["sha256"] = BRIDGE_PROVENANCE_SENTINEL
        normalized[name] = item
    return _sha256_json({**payload, "source_contracts": normalized})


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_post_push_successor_acceptance() -> object:
    """Import the fixed terminal successor only when physical bytes drift.

    Keeping this import out of module initialization prevents the terminal
    bridge from forming an import cycle while it validates these historical
    bytes.  Only the two code-fixed module names are ever attempted.
    """
    qualified_name = (
        "tools.phase4c_http_target_execution_post_push_successor_acceptance"
    )
    direct_name = "phase4c_http_target_execution_post_push_successor_acceptance"
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
            "fixed target-execution post-push successor acceptance is required"
        ) from error


def _current_or_post_push_successor_sha256(
        root: Path,
        relative: str,
        declared_sha256: object,
        physical_sha256: str,
        *,
        label: str,
) -> str:
    """Accept current bytes directly or through one exact owned successor.

    A non-null post-push acceptance owns the path exclusively.  NodeA is
    consulted only when that predecessor explicitly returns ``None``.  The
    selected owner must independently name both the historical declaration and
    current regular-file hash; every malformed or unknown transition fails
    closed.
    """
    if declared_sha256 == physical_sha256:
        return physical_sha256
    if not _is_sha256(declared_sha256):
        raise AssertionError(f"{label} declared SHA-256 is invalid")

    acceptance = _load_post_push_successor_acceptance()
    accepted_lookup = getattr(acceptance, "accepted_sha256", None)
    successor_lookup = getattr(acceptance, "successor_sha256", None)
    if not callable(accepted_lookup) or not callable(successor_lookup):
        raise AssertionError(
            "fixed target-execution post-push successor API is incomplete"
        )
    post_push_accepted = accepted_lookup(relative)
    if post_push_accepted is not None:
        if post_push_accepted != declared_sha256:
            raise AssertionError(
                f"post-push successor does not accept historical bytes: {relative}"
            )
        if successor_lookup(root, relative) != physical_sha256:
            raise AssertionError(
                f"post-push successor does not bind current bytes: {relative}"
            )
        return physical_sha256

    nodea = _tag_preflight_successor()
    nodea_accepted = getattr(nodea, "accepted_sha256", None)
    nodea_successor = getattr(nodea, "successor_sha256", None)
    if not callable(nodea_accepted) or not callable(nodea_successor):
        raise AssertionError("tag-preflight successor API is incomplete")
    if nodea_accepted(relative) != declared_sha256:
        raise AssertionError(
            f"tag-preflight successor does not accept historical bytes: {relative}"
        )
    if nodea_successor(root, relative) != physical_sha256:
        raise AssertionError(
            f"tag-preflight successor does not bind current bytes: {relative}"
        )
    return physical_sha256


def _fixed_path(root: Path, relative: str, *, regular_file: bool) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed target-execution path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"fixed target-execution path contains symlink: {relative}"
            )
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed target-execution path escaped or vanished: {relative}"
        ) from error
    if regular_file and not resolved.is_file():
        raise AssertionError(
            f"fixed target-execution path is not a regular file: {relative}"
        )
    return resolved


def _fixed_regular_file(root: Path, relative: str) -> Path:
    return _fixed_path(root, relative, regular_file=True)


def _read_json(root: Path, relative: str) -> dict:
    with _fixed_regular_file(root, relative).open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise AssertionError(f"fixed JSON source is not an object: {relative}")
    return document


def _trust_payload_sha256(document: dict) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    sources = payload.get("source_contracts")
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_PATHS):
        raise AssertionError("target-execution source-contract key set drifted")
    for name, fixed_path in SOURCE_PATHS.items():
        reference = sources.get(name)
        if not isinstance(reference, dict):
            raise AssertionError(f"missing target-execution source: {name}")
        if reference.get("source") != fixed_path:
            raise AssertionError(f"target-execution source path drifted: {name}")
    return _bridge_normalized_payload_sha256(document)


def _add_manifest_path(
        root: Path,
        relative: str,
        manifest: dict[str, str],
) -> None:
    path = _fixed_path(root, relative, regular_file=False)
    if path.is_file():
        manifest[relative] = _sha256(path)
        return
    if not path.is_dir():
        raise AssertionError(f"runtime manifest source is invalid: {relative}")
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise AssertionError(f"runtime manifest contains symlink: {child}")
        if child.is_file():
            manifest[child.relative_to(root).as_posix()] = _sha256(child)


def _production_runtime_manifest(root: Path) -> dict[str, str]:
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
        _add_manifest_path(root, relative, manifest)
    return dict(sorted(manifest.items()))


def _validate_reference(
        root: Path,
        reference: object,
        expected_relative: str,
        *,
        label: str,
) -> str:
    if not isinstance(reference, dict):
        raise AssertionError(f"{label} reference is missing")
    if reference.get("source") != expected_relative:
        raise AssertionError(f"{label} followed a non-fixed source path")
    physical = _sha256(_fixed_regular_file(root, expected_relative))
    return _current_or_post_push_successor_sha256(
        root,
        expected_relative,
        reference.get("sha256"),
        physical,
        label=label,
    )


def _validate_predecessor(root: Path, contract: dict) -> dict:
    path = _fixed_regular_file(root, PREDECESSOR_RELATIVE)
    if _sha256(path) != PREDECESSOR_SHA256:
        raise AssertionError("target-execution predecessor physical hash drifted")
    predecessor = _read_json(root, PREDECESSOR_RELATIVE)
    if predecessor.get("contract_id") != PREDECESSOR_ID:
        raise AssertionError("unexpected target-execution predecessor id")
    if predecessor.get("status") != PREDECESSOR_STATUS:
        raise AssertionError("unexpected target-execution predecessor status")
    if predecessor.get("scope") != PREDECESSOR_SCOPE:
        raise AssertionError("unexpected target-execution predecessor scope")
    if predecessor.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("predecessor payload field drifted")
    if _payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("predecessor document payload is invalid")
    if _bridge_normalized_payload_sha256(predecessor) != (
            PREDECESSOR_TRUST_PAYLOAD_SHA256):
        raise AssertionError("predecessor independent trust payload drifted")

    expected_reference = {
        "source": PREDECESSOR_RELATIVE,
        "sha256": PREDECESSOR_SHA256,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "trust_payload_sha256": PREDECESSOR_TRUST_PAYLOAD_SHA256,
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "immutable": True,
    }
    if contract.get("predecessor") != expected_reference:
        raise AssertionError("target-execution predecessor reference drifted")

    historical = predecessor.get("historical_successor_acceptance", {})
    old_overrides = historical.get("http_entry_source_overrides", {})
    for relative in (
        "README.md",
        "docs/refactor/05-progress.md",
        "docs/refactor/phase4c/README.md",
    ):
        if old_overrides.get(relative, {}).get("successor_sha256") != (
                HISTORICAL_SOURCE_ACCEPTED_SHA256[relative]):
            raise AssertionError(
                f"fixed predecessor history no longer proves accepted hash: {relative}"
            )

    predecessor_sources = predecessor.get("source_contracts", {})
    fixed_source_keys = {
        "docs/refactor/phase4c/route-parity-delta.csv": "route_delta",
        "infra/phase2/README.md": "phase2_worm_readme",
        "infra/phase2/verify-static.sh": "phase2_static_gate",
        "tools/phase2_wormhole_successor_acceptance.py": (
            "phase2_worm_validator"
        ),
        "tools/test_phase2_wormhole_successor_acceptance.py": (
            "phase2_worm_validator_test"
        ),
        "tools/phase4c_http_implementation_successor_acceptance.py": (
            "python_successor_bridge"
        ),
        (
            "tools/test_phase4c_personal_bank_user_counts_"
            "http_implementation_contract.py"
        ): "contract_test",
        (
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpImplementationSuccessorAcceptance.java"
        ): "java_successor_bridge",
        "tools/phase4c_read_successor_acceptance.py": (
            "historical_python_read_successor_bridge"
        ),
    }
    for relative, source_key in fixed_source_keys.items():
        reference = predecessor_sources.get(source_key, {})
        if reference.get("source") != relative:
            raise AssertionError(
                f"fixed predecessor source path no longer proves allowlist: {relative}"
            )
        if reference.get("sha256") != HISTORICAL_SOURCE_ACCEPTED_SHA256[relative]:
            raise AssertionError(
                f"fixed predecessor source hash no longer proves allowlist: {relative}"
            )
    return predecessor


def _validate_anchor_contract(
        root: Path,
        relative: str,
        expected_sha256: str,
        expected_payload_sha256: str,
        expected_id: str,
        expected_status: str,
) -> dict:
    path = _fixed_regular_file(root, relative)
    if _sha256(path) != expected_sha256:
        raise AssertionError(f"historical anchor bytes drifted: {relative}")
    document = _read_json(root, relative)
    if document.get("contract_id") != expected_id:
        raise AssertionError(f"historical anchor id drifted: {relative}")
    if document.get("status") != expected_status:
        raise AssertionError(f"historical anchor status drifted: {relative}")
    if document.get("document_payload_sha256") != expected_payload_sha256:
        raise AssertionError(f"historical anchor payload field drifted: {relative}")
    if _payload_sha256(document) != expected_payload_sha256:
        raise AssertionError(f"historical anchor payload is invalid: {relative}")
    return document


def _validate_sources(root: Path, contract: dict) -> None:
    sources = contract.get("source_contracts")
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_PATHS):
        raise AssertionError("target-execution fixed source set drifted")
    for name, relative in SOURCE_PATHS.items():
        _validate_reference(root, sources.get(name), relative, label=name)


def _reference_path(reference: object) -> str | None:
    if not isinstance(reference, dict):
        return None
    value = reference.get("path", reference.get("source"))
    return value if isinstance(value, str) else None


def _validate_evidence(root: Path, contract: dict) -> None:
    evidence_path = _fixed_regular_file(root, TARGET_EXECUTION_EVIDENCE_RELATIVE)
    evidence_sha256 = _sha256(evidence_path)
    if evidence_sha256 != TARGET_EXECUTION_EVIDENCE_SHA256:
        raise AssertionError("target-execution evidence physical hash drifted")
    evidence = _read_json(root, TARGET_EXECUTION_EVIDENCE_RELATIVE)
    if evidence.get("schema_version") != 1:
        raise AssertionError("target-execution evidence schema drifted")
    if evidence.get("evidence_id") != TARGET_EXECUTION_EVIDENCE_ID:
        raise AssertionError("target-execution evidence id drifted")
    if evidence.get("document_payload_sha256") != (
            TARGET_EXECUTION_EVIDENCE_PAYLOAD_SHA256):
        raise AssertionError("target-execution evidence payload field drifted")
    if _payload_sha256(evidence) != TARGET_EXECUTION_EVIDENCE_PAYLOAD_SHA256:
        raise AssertionError("target-execution evidence payload is invalid")
    checkpoint = evidence.get("source_checkpoint", {})
    if checkpoint.get("commit") != SOURCE_CHECKPOINT_COMMIT:
        raise AssertionError("target-execution source checkpoint drifted")
    if checkpoint.get("committed_at") != SOURCE_CHECKPOINT_COMMITTED_AT:
        raise AssertionError("target-execution source checkpoint timestamp drifted")
    if checkpoint.get("subject") != SOURCE_CHECKPOINT_SUBJECT:
        raise AssertionError("target-execution source checkpoint subject drifted")
    checkpoint_artifacts = checkpoint.get("artifacts", {})
    expected_checkpoint_artifacts = {
        "target_execution_test": TARGET_EXECUTION_IT_RELATIVE,
        "fault_injecting_data_source": FAULT_DATA_SOURCE_RELATIVE,
        "postgresql_seed": TARGET_EXECUTION_SEED_RELATIVE,
    }
    if set(checkpoint_artifacts) != set(expected_checkpoint_artifacts):
        raise AssertionError("target-execution checkpoint artifact set drifted")
    for name, relative in expected_checkpoint_artifacts.items():
        reference = checkpoint_artifacts.get(name, {})
        if reference.get("path") != relative:
            raise AssertionError(f"checkpoint source path drifted: {name}")
        if reference.get("sha256") != _sha256(_fixed_regular_file(root, relative)):
            raise AssertionError(f"checkpoint source hash drifted: {name}")
    if _reference_path(evidence.get("source_golden")) != PHASE4B_GOLDEN_RELATIVE:
        raise AssertionError("target-execution evidence golden path drifted")
    if evidence.get("source_golden", {}).get("sha256") != PHASE4B_GOLDEN_SHA256:
        raise AssertionError("target-execution evidence golden hash drifted")
    if evidence.get("source_golden", {}).get("ordered_case_ids_sha256") != (
            PHASE4B_CASE_IDS_SHA256):
        raise AssertionError("target-execution evidence golden id hash drifted")
    if _reference_path(evidence.get("historical_mapping")) != (
            HISTORICAL_MAPPING_RELATIVE):
        raise AssertionError("target-execution evidence mapping path drifted")
    if evidence.get("historical_mapping", {}).get("sha256") != (
            HISTORICAL_MAPPING_SHA256):
        raise AssertionError("target-execution evidence mapping hash drifted")

    golden_path = _fixed_regular_file(root, PHASE4B_GOLDEN_RELATIVE)
    if _sha256(golden_path) != PHASE4B_GOLDEN_SHA256:
        raise AssertionError("Phase4B golden physical hash drifted")
    golden = _read_json(root, PHASE4B_GOLDEN_RELATIVE)
    if golden.get("case_payload_sha256") != PHASE4B_CASE_PAYLOAD_SHA256:
        raise AssertionError("Phase4B golden case payload drifted")
    if _sha256_json(golden.get("cases")) != PHASE4B_CASE_PAYLOAD_SHA256:
        raise AssertionError("Phase4B golden cases no longer match their payload")
    if golden.get("document_payload_sha256") != PHASE4B_DOCUMENT_PAYLOAD_SHA256:
        raise AssertionError("Phase4B golden document payload field drifted")
    if _payload_sha256(golden) != PHASE4B_DOCUMENT_PAYLOAD_SHA256:
        raise AssertionError("Phase4B golden document payload is invalid")
    golden_cases = golden.get("cases")
    if not isinstance(golden_cases, list) or len(golden_cases) != 59:
        raise AssertionError("Phase4B golden case count drifted")
    golden_ids = [item.get("case_id") for item in golden_cases]
    if len(set(golden_ids)) != 59:
        raise AssertionError("Phase4B golden case ids are not an exact set")
    if _sha256_json(golden_ids) != PHASE4B_CASE_IDS_SHA256:
        raise AssertionError("Phase4B golden case-id order drifted")

    mapping_path = _fixed_regular_file(root, HISTORICAL_MAPPING_RELATIVE)
    if _sha256(mapping_path) != HISTORICAL_MAPPING_SHA256:
        raise AssertionError("historical target mapping physical hash drifted")
    mapping = _read_json(root, HISTORICAL_MAPPING_RELATIVE)
    mapping_cases = mapping.get("cases")
    if not isinstance(mapping_cases, list):
        raise AssertionError("historical target mapping cases are missing")
    if [item.get("case_id") for item in mapping_cases] != golden_ids:
        raise AssertionError("historical mapping is not the exact golden case order")
    mapping_by_id = {item["case_id"]: item for item in mapping_cases}

    summary = evidence.get("summary")
    if not isinstance(summary, dict):
        raise AssertionError("target-execution evidence summary is missing")
    for field, expected in SUMMARY_EXPECTED.items():
        if summary.get(field) != expected:
            raise AssertionError(f"target-execution summary drifted: {field}")
    if summary.get("execution_disposition_counts") != DISPOSITION_COUNTS_EXPECTED:
        raise AssertionError("target-execution disposition summary drifted")

    cases = evidence.get("cases")
    if not isinstance(cases, list) or len(cases) != 59:
        raise AssertionError("target-execution evidence must contain 59 cases")
    if _sha256_json(cases) != TARGET_EXECUTION_CASE_PAYLOAD_SHA256:
        raise AssertionError("target-execution physical case payload drifted")
    if [item.get("case_id") for item in cases] != golden_ids:
        raise AssertionError("target-execution evidence case set/order drifted")

    normal_case_ids = [
        item["case_id"]
        for item in golden_cases
        if item["case_id"] not in TYPED_DISPOSITIONS
        and item.get("fault_injection", {}).get("stage") is None
    ]
    fault_case_ids = [
        item["case_id"]
        for item in golden_cases
        if item.get("fault_injection", {}).get("stage") is not None
    ]
    execution_order = normal_case_ids + fault_case_ids + list(TYPED_DISPOSITIONS)
    execution_ordinal_by_id = {
        case_id: ordinal
        for ordinal, case_id in enumerate(execution_order, start=1)
    }

    observed_dispositions: Counter[str] = Counter()
    observed_aliases: Counter[str] = Counter()
    observed_statuses: Counter[str] = Counter()
    business_jdbc_reached_http_count = 0
    pre_business_jdbc_termination_http_count = 0
    pre_business_jdbc_termination_status_counts: Counter[str] = Counter()
    for ordinal, (case, source_case) in enumerate(
            zip(cases, golden_cases),
            start=1,
    ):
        case_id = source_case["case_id"]
        if case.get("canonical_case_ordinal") != ordinal:
            raise AssertionError(f"canonical case ordinal drifted: {case_id}")
        if case.get("execution_ordinal") != execution_ordinal_by_id[case_id]:
            raise AssertionError(f"execution ordinal drifted: {case_id}")
        if case.get("junit", {}).get("disposition_leaf_ordinal") != (
                execution_ordinal_by_id[case_id] + 1):
            raise AssertionError(f"JUnit leaf ordinal drifted: {case_id}")
        request = source_case.get("request", {})
        path = request.get("path", "")
        expected_alias = "api" if path.startswith("/api/") else "web"
        if case.get("alias") != expected_alias:
            raise AssertionError(f"case alias drifted: {case_id}")
        if case.get("route_id") != source_case.get("route_id"):
            raise AssertionError(f"case route id drifted: {case_id}")
        case_request = case.get("source_request", {})
        for field, expected in {
            "method": request.get("method"),
            "path": path,
            "query": request.get("query"),
            "credential_mode": source_case.get("credential_mode"),
            "session_actor": source_case.get("session_actor"),
            "bearer_actor": source_case.get("bearer_actor"),
        }.items():
            if case_request.get(field) != expected:
                raise AssertionError(f"case request {field} drifted: {case_id}")
        if case.get("source_golden_response_status") != source_case.get(
                "response", {}).get("status"):
            raise AssertionError(f"source golden response status drifted: {case_id}")

        mapping_case = mapping_by_id[case_id]
        expected_status = mapping_case.get("target_status")
        if case.get("target_status") != expected_status:
            raise AssertionError(f"case target status drifted: {case_id}")
        if case.get("source_case_classification") != mapping_case.get(
                "adapter_execution"):
            raise AssertionError(f"case source classification drifted: {case_id}")
        if case.get("historical_binding_ids") != mapping_case.get("bindings"):
            raise AssertionError(f"case historical bindings drifted: {case_id}")
        for field in (
            "http_slice_difference_ids",
            "inherited_predecessor_difference_id",
            "target_data_source_case",
            "tracking_note",
        ):
            if (field in case) != (field in mapping_case):
                raise AssertionError(
                    f"case mapping field presence drifted: {case_id}:{field}"
                )
            if field in mapping_case and case[field] != mapping_case[field]:
                raise AssertionError(
                    f"case mapping field drifted: {case_id}:{field}"
                )
        disposition = case.get("execution_disposition")
        fault_stage = source_case.get("fault_injection", {}).get("stage")
        if case_id in TYPED_DISPOSITIONS:
            expected_disposition = TYPED_DISPOSITIONS[case_id]
        elif fault_stage is not None:
            expected_disposition = (
                "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT"
            )
        else:
            expected_disposition = "EXECUTED_FULL_CONTEXT_HTTP"
        if disposition != expected_disposition:
            raise AssertionError(f"case disposition drifted: {case_id}")
        if case.get("http_execution") is not (expected_status is not None):
            raise AssertionError(f"case HTTP execution marker drifted: {case_id}")

        fault_evidence = case.get("fault_evidence")
        typed_evidence = case.get("typed_evidence")
        if fault_stage is not None:
            if not isinstance(fault_evidence, dict) or typed_evidence is not None:
                raise AssertionError(f"fault evidence binding drifted: {case_id}")
            expected_occurrences = {
                "personal_bank_user_counts_total_all": 1,
                "personal_bank_user_counts_favorites_count": 2,
                "personal_bank_user_counts_mistakes_count": 3,
                "personal_bank_user_counts_types_all": 4,
                "personal_bank_user_counts_share_access_probe": 1,
            }
            occurrence = expected_occurrences.get(fault_stage)
            if occurrence is None:
                raise AssertionError(f"unknown fault family binding: {case_id}")
            expected_family = (
                "SHARE_ACCESS"
                if fault_stage == "personal_bank_user_counts_share_access_probe"
                else "QUESTION_SUMMARY"
            )
            expected_fault = {
                "family": expected_family,
                "occurrence": occurrence,
                "initial_sqlstate": "42703",
                "poisoned_transaction_sqlstate": "25P02",
                "fault_connection_read_only": True,
                "rollback_after_fault_on_same_connection": True,
                "failed_family_occurrence_has_no_success_record": True,
                "later_same_family_success_after_rollback_on_different_connection_required": (
                    expected_status == 200
                    and expected_family == "QUESTION_SUMMARY"
                    and occurrence < 4
                ),
            }
            if fault_evidence != expected_fault:
                raise AssertionError(f"fault evidence drifted: {case_id}")
        elif case_id in TYPED_DISPOSITIONS:
            if fault_evidence is not None or not isinstance(typed_evidence, dict):
                raise AssertionError(f"typed evidence binding drifted: {case_id}")
            if expected_disposition == "EXECUTED_TYPED_REJECTION":
                expected_typed_evidence = {
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
                if typed_evidence != expected_typed_evidence:
                    raise AssertionError(f"typed rejection evidence drifted: {case_id}")
            else:
                expected_typed_evidence = {
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
                if typed_evidence != expected_typed_evidence:
                    raise AssertionError(f"typed collapse evidence drifted: {case_id}")
        elif fault_evidence is not None or typed_evidence is not None:
            raise AssertionError(f"ordinary case has specialized evidence: {case_id}")

        if expected_status is not None and case.get("side_effect_assertions") != {
            "nine_table_database_fingerprint_unchanged": True,
            "write_dml_count": 0,
            "users_last_active_write_dml_count": 0,
            "schema_mutation_count": 0,
            "rate_limit_assertion_mode": "RESPONSE_HEADER_CONDITIONED",
        }:
            raise AssertionError(f"HTTP side-effect evidence drifted: {case_id}")

        if expected_status is not None:
            sql_boundary = case.get("sql_boundary")
            if not isinstance(sql_boundary, dict) or not isinstance(
                    sql_boundary.get("business_jdbc_reached"), bool):
                raise AssertionError(
                    f"HTTP business JDBC marker drifted: {case_id}"
                )
            if sql_boundary["business_jdbc_reached"]:
                business_jdbc_reached_http_count += 1
                if sql_boundary.get("business_connections_read_only") is not True:
                    raise AssertionError(
                        f"HTTP business JDBC read-only marker drifted: {case_id}"
                    )
            else:
                pre_business_jdbc_termination_http_count += 1
                pre_business_jdbc_termination_status_counts[str(expected_status)] += 1
                expected_termination = (
                    "WEB_PRE_AUTHENTICATION"
                    if expected_status == 302
                    else "AUTHENTICATION"
                )
                execution_families = sql_boundary.get("execution_families")
                if (
                    expected_status not in {302, 401}
                    or sql_boundary.get("execution_family_assertion") != "EXACT"
                    or sql_boundary.get("termination") != expected_termination
                    or not isinstance(execution_families, list)
                    or (
                        expected_status == 302
                        and execution_families != []
                    )
                    or (
                        expected_status == 401
                        and execution_families not in ([], ["AUTHORITY_USERS"])
                    )
                    or (
                        expected_status == 401
                        and sql_boundary.get("business_execution_families_absent")
                        != EXPECTED_PRE_BUSINESS_FAMILIES
                    )
                ):
                    raise AssertionError(
                        f"HTTP pre-business termination boundary drifted: {case_id}"
                    )

        observed_dispositions[str(disposition)] += 1
        if expected_status is not None:
            observed_aliases[expected_alias] += 1
            observed_statuses[str(expected_status)] += 1

    if dict(observed_dispositions) != DISPOSITION_COUNTS_EXPECTED:
        raise AssertionError("physical case disposition counts drifted")
    if observed_aliases != Counter({"api": 43, "web": 14}):
        raise AssertionError("physical HTTP alias counts drifted")
    if dict(observed_statuses) != SUMMARY_EXPECTED["http_status_counts"]:
        raise AssertionError("physical HTTP status counts drifted")
    if business_jdbc_reached_http_count != 49 or (
            pre_business_jdbc_termination_http_count != 8):
        raise AssertionError("physical business JDBC reach counts drifted")
    if pre_business_jdbc_termination_status_counts != Counter({
            "302": 5, "401": 3}):
        raise AssertionError("physical pre-business status counts drifted")

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
    for field, expected in expected_harness_boundaries.items():
        if harness.get(field) != expected:
            raise AssertionError(f"target-execution harness drifted: {field}")
    if harness.get("postgresql", {}).get("version") != "18.4" or harness.get(
            "postgresql", {}).get("real_container") is not True:
        raise AssertionError("target-execution PostgreSQL harness drifted")
    if harness.get("redis", {}).get("version") != "7.4.7" or harness.get(
            "redis", {}).get("real_container") is not True:
        raise AssertionError("target-execution Redis harness drifted")

    boundaries = evidence.get("route_worm_and_parity_boundaries", {})
    if boundaries.get("implementation_build_context_sha256") != (
            JAVA_BUILD_CONTEXT_SHA256):
        raise AssertionError("evidence build-context boundary drifted")
    if boundaries.get("implementation_chain_node_count") != 5:
        raise AssertionError("evidence WORM chain length drifted")
    implementation_worm = boundaries.get("implementation_worm", {})
    if implementation_worm != {
        "path": WORM_RELATIVE,
        "sha256": WORM_SHA256,
        "reused": True,
    }:
        raise AssertionError("evidence did not reuse the fifth WORM")
    if boundaries.get("target_execution_worm_created") is not False:
        raise AssertionError("evidence created an unauthorized sixth WORM")
    if boundaries.get("route_counts") != {
            "migrated": 11,
            "pending": 600,
            "cutover": 0,
    }:
        raise AssertionError("evidence route counts drifted")
    for field in (
        "full_target_parity_closed",
        "route_migration_eligible",
        "production_cutover_evidence",
    ):
        if boundaries.get(field) is not False:
            raise AssertionError(f"evidence overclaims {field}")
    claim = evidence.get("claim", {})
    if claim.get("classification") != "TARGET_EXECUTION_DISPOSITION_LEDGER":
        raise AssertionError("target-execution evidence classification drifted")
    for field in (
        "full_target_execution_dispositions_closed",
    ):
        if claim.get(field) is not True:
            raise AssertionError(f"target-execution evidence did not close {field}")
    if claim.get("historical_bound_only_cases_remaining") != 0:
        raise AssertionError("target-execution evidence retains bound-only cases")
    for field in (
        "mocked_application_results_used",
        "full_target_parity_closed",
        "route_migration_eligible",
        "cutover_evidence",
    ):
        if claim.get(field) is not False:
            raise AssertionError(f"target-execution evidence overclaims {field}")

    verification = contract.get("verification_evidence", {})
    reference = verification.get("target_execution", {})
    if reference.get("source") != TARGET_EXECUTION_EVIDENCE_RELATIVE:
        raise AssertionError("contract target-execution evidence path drifted")
    if reference.get("sha256") != evidence_sha256:
        raise AssertionError("contract target-execution evidence hash drifted")
    if reference.get("evidence_id") != TARGET_EXECUTION_EVIDENCE_ID:
        raise AssertionError("contract target-execution evidence id drifted")
    if reference.get("document_payload_sha256") != evidence.get(
            "document_payload_sha256"):
        raise AssertionError("contract target-execution evidence payload drifted")
    if reference.get("case_payload_sha256") != TARGET_EXECUTION_CASE_PAYLOAD_SHA256:
        raise AssertionError("contract target-execution case payload drifted")
    if reference.get("case_ids_sha256") != PHASE4B_CASE_IDS_SHA256:
        raise AssertionError("contract target-execution case-id hash drifted")
    if reference.get("summary") != SUMMARY_EXPECTED:
        raise AssertionError("contract target-execution summary drifted")
    if reference.get("disposition_counts") != DISPOSITION_COUNTS_EXPECTED:
        raise AssertionError("contract target-execution disposition counts drifted")

    historical_reference = verification.get("historical_partial_mapping")
    if historical_reference != {
        "source": HISTORICAL_MAPPING_RELATIVE,
        "sha256": HISTORICAL_MAPPING_SHA256,
        "classification": "PARTIAL_EXECUTION_MAPPING_LEDGER",
        "case_count": 59,
        "immutable": True,
    }:
        raise AssertionError("contract historical mapping reference drifted")
    junit_reference = verification.get("junit")
    if junit_reference != {
        "source": TARGET_EXECUTION_IT_RELATIVE,
        "sha256": _sha256(_fixed_regular_file(root, TARGET_EXECUTION_IT_RELATIVE)),
        "case_leaf_count": 59,
        "supplementary_leaf_count": 1,
        "total_leaf_count": 60,
    }:
        raise AssertionError("contract target-execution JUnit reference drifted")
    if verification.get("postgresql") != {
        "version": "18.4",
        "real_container": True,
        "read_only": True,
        "users_last_active_write_dml_count": 0,
    }:
        raise AssertionError("contract target-execution PostgreSQL proof drifted")


def _validate_production_surface(root: Path, contract: dict, predecessor: dict) -> None:
    if _sha256(_fixed_regular_file(root, READ_BUILDER_RELATIVE)) != (
            READ_BUILDER_SHA256):
        raise AssertionError("fixed production manifest implementation drifted")
    predecessor_current = predecessor.get("implementation", {}).get(
        "production_runtime_transition", {}
    ).get("current", {})
    if predecessor_current.get("file_count") != PRODUCTION_FILE_COUNT:
        raise AssertionError("predecessor production file count drifted")
    if predecessor_current.get("manifest_sha256") != PRODUCTION_MANIFEST_SHA256:
        raise AssertionError("predecessor production manifest hash drifted")
    predecessor_files = predecessor_current.get("files")
    if not isinstance(predecessor_files, dict) or len(predecessor_files) != 297:
        raise AssertionError("predecessor production manifest is incomplete")
    if _sha256_json(predecessor_files) != PRODUCTION_MANIFEST_SHA256:
        raise AssertionError("predecessor production manifest files drifted")

    physical_files = _production_runtime_manifest(root)
    if physical_files != predecessor_files:
        successor = _validate_runtime_successor(
            root,
            predecessor_files,
            physical_files,
            view="full_runtime",
        )
        if (
            successor.accepted_file_count != PRODUCTION_FILE_COUNT
            or successor.accepted_manifest_sha256 != PRODUCTION_MANIFEST_SHA256
            or successor.current_file_count != len(physical_files)
            or successor.current_manifest_sha256 != _sha256_json(physical_files)
            or successor.changed_files
            or successor.deleted_files
        ):
            raise AssertionError("tag preflight runtime successor descriptor drifted")
    surface = contract.get("production_surface")
    if surface != {
        "file_count": PRODUCTION_FILE_COUNT,
        "manifest_sha256": PRODUCTION_MANIFEST_SHA256,
        "files": predecessor_files,
        "unchanged_from_predecessor": True,
    }:
        raise AssertionError("target-execution production surface drifted")


def _validate_worm_and_routes(root: Path, contract: dict, predecessor: dict) -> None:
    worm_path = _fixed_regular_file(root, WORM_RELATIVE)
    if _sha256(worm_path) != WORM_SHA256:
        raise AssertionError("fifth implementation WORM physical hash drifted")
    worm = _read_json(root, WORM_RELATIVE)
    if worm.get("java", {}).get("dockerfileSha256") != DOCKERFILE_SHA256:
        raise AssertionError("fifth WORM Dockerfile hash drifted")
    if worm.get("java", {}).get("buildContextSha256") != JAVA_BUILD_CONTEXT_SHA256:
        raise AssertionError("fifth WORM build-context hash drifted")
    if _sha256(_fixed_regular_file(root, "server/Dockerfile")) != DOCKERFILE_SHA256:
        raise AssertionError("physical Java Dockerfile drifted")
    result = subprocess.run(
        [str(_fixed_regular_file(root, "infra/phase2/hash-java-build-context.sh"))],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    physical_build_context = result.stdout.strip()
    if physical_build_context != JAVA_BUILD_CONTEXT_SHA256:
        successor = _validate_worm_successor(
            root,
            WORM_SHA256,
            JAVA_BUILD_CONTEXT_SHA256,
        )
        if (
            successor.accepted_chain_node_count != 5
            or successor.current_build_context_sha256 != physical_build_context
            or successor.current_chain_node_count != 9
        ):
            raise AssertionError("tag preflight WORM successor descriptor drifted")
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
            raise AssertionError(f"fifth WORM read-role proof drifted: {field}")
    if read_role.get("temporaryPrivilege") is not False:
        raise AssertionError("fifth WORM unexpectedly permits TEMP")

    predecessor_worm = predecessor.get("worm_evidence", {})
    fixed_chain = predecessor_worm.get("fixed_phase2_chain", {})
    if predecessor_worm.get("source") != WORM_RELATIVE:
        raise AssertionError("predecessor fifth WORM path drifted")
    if predecessor_worm.get("sha256") != WORM_SHA256:
        raise AssertionError("predecessor fifth WORM hash drifted")
    if fixed_chain.get("node_count") != 5:
        raise AssertionError("fixed WORM chain node count drifted")
    if fixed_chain.get("tip_sha256") != WORM_SHA256:
        raise AssertionError("fixed WORM chain tip drifted")
    if fixed_chain.get("predecessor_sha256") != WORM_PREDECESSOR_SHA256:
        raise AssertionError("fixed WORM chain predecessor drifted")
    if fixed_chain.get("java_build_context_sha256") != JAVA_BUILD_CONTEXT_SHA256:
        raise AssertionError("fixed WORM chain build context drifted")
    worm_reference = contract.get("worm_evidence")
    if worm_reference != {
        "source": WORM_RELATIVE,
        "sha256": WORM_SHA256,
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
    }:
        raise AssertionError("target-execution fifth WORM reuse reference drifted")

    if _sha256(_fixed_regular_file(
            root, "openapi/phase4c-personal-bank-user-counts.openapi.json")) != (
            OPENAPI_SHA256):
        raise AssertionError("OpenAPI overlay changed during target execution")
    routes = contract.get("routes_and_openapi")
    inherited_routes = predecessor.get("implementation", {}).get(
        "routes_and_openapi"
    )
    if not isinstance(inherited_routes, dict):
        raise AssertionError("predecessor routes/OpenAPI boundary is missing")
    expected_routes = {
        **{
            key: value
            for key, value in inherited_routes.items()
            if key not in {"route_delta", "openapi_overlay"}
        },
        "route_delta": {
            "source": "docs/refactor/phase4c/route-parity-delta.csv",
            "sha256": _sha256(_fixed_regular_file(
                root, "docs/refactor/phase4c/route-parity-delta.csv")),
        },
        "openapi_overlay": {
            "source": "openapi/phase4c-personal-bank-user-counts.openapi.json",
            "sha256": OPENAPI_SHA256,
        },
    }
    if routes != expected_routes:
        raise AssertionError("target-execution routes/OpenAPI boundary drifted")
    if routes.get("migrated_operation_count") != 11:
        raise AssertionError("target-execution migrated route count drifted")
    if routes.get("pending_operation_count") != 600:
        raise AssertionError("target-execution pending route count drifted")
    if routes.get("production_cutover_operation_count") != 0:
        raise AssertionError("target-execution overclaims route cutover")
    if routes.get("route_migration_eligible") is not False:
        raise AssertionError("target-execution overclaims route eligibility")
    with _fixed_regular_file(
            root,
            "docs/refactor/phase4c/route-parity-delta.csv",
    ).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_rows = {
        "6858f6fa506f": (
            "/api/user/banks/api/<int:bank_id>/user-counts"
        ),
        "006913d0d956": (
            "/user/banks/api/<int:bank_id>/user-counts"
        ),
    }
    if len(rows) != 2 or {row.get("route_id") for row in rows} != set(
            expected_rows):
        raise AssertionError("route delta no longer contains the exact two routes")
    for row in rows:
        if row.get("path") != expected_rows[row["route_id"]]:
            raise AssertionError("route delta path drifted")
        if row.get("method") != "GET":
            raise AssertionError("route delta counted a non-GET operation")
        if row.get("phase4c_target_module") != "learning":
            raise AssertionError("route delta target module drifted")
        if row.get("phase4c_migration_status") != "pending":
            raise AssertionError("route delta overclaims migration")
        if row.get("production_cutover") != "false":
            raise AssertionError("route delta overclaims cutover")


def _validate_historical_successors(root: Path, contract: dict) -> None:
    read_predecessor = _validate_anchor_contract(
        root,
        READ_PREDECESSOR_RELATIVE,
        READ_PREDECESSOR_SHA256,
        READ_PREDECESSOR_PAYLOAD_SHA256,
        "ti.phase4c.personal-bank-user-counts-read-contract",
        "implemented_and_targeted_verified_http_aliases_deferred",
    )
    all_shares_entry = _validate_anchor_contract(
        root,
        PHASE4B_ALL_SHARES_ENTRY_RELATIVE,
        PHASE4B_ALL_SHARES_ENTRY_SHA256,
        PHASE4B_ALL_SHARES_ENTRY_PAYLOAD_SHA256,
        "ti.phase4b.personal-bank-all-shares-entry-contract",
        "entry_gate_passed_implementation_not_started",
    )
    anchor_indexes = {
        "phase4c_read_predecessor.source_contracts": {
            reference.get("source"): reference.get("sha256")
            for reference in read_predecessor.get("source_contracts", {}).values()
            if isinstance(reference, dict)
        },
        "phase4b_all_shares_entry.source_contracts": {
            reference.get("source"): reference.get("sha256")
            for reference in all_shares_entry.get("source_contracts", {}).values()
            if isinstance(reference, dict)
        },
    }
    historical = contract.get("historical_successor_acceptance", {})
    if set(historical) != {
            "predecessor_sha256",
            "predecessor_trust_payload_sha256",
            "anchored_source_overrides",
            "successor_allowlist",
            "successor_allowlist_exact",
            "accepted_hashes_independently_located",
            "predecessor_rewrite_forbidden",
            "arbitrary_source_hash_lookup_forbidden",
            "current_bridges_excluded_from_historical_accepted_hash_allowlist",
    }:
        raise AssertionError("historical successor shape drifted")
    if historical.get("predecessor_sha256") != PREDECESSOR_SHA256:
        raise AssertionError("historical successor predecessor hash drifted")
    if historical.get("predecessor_trust_payload_sha256") != (
            PREDECESSOR_TRUST_PAYLOAD_SHA256):
        raise AssertionError("historical successor predecessor trust drifted")
    overrides = historical.get("anchored_source_overrides")
    if not isinstance(overrides, dict) or set(overrides) != set(
            HISTORICAL_SOURCE_ACCEPTED_SHA256):
        raise AssertionError("historical successor allowlist is not exact")
    for relative, accepted in HISTORICAL_SOURCE_ACCEPTED_SHA256.items():
        entry = overrides.get(relative)
        provenance = HISTORICAL_SOURCE_ACCEPTED_PROVENANCE[relative]
        anchor_index = anchor_indexes.get(provenance)
        if anchor_index is not None and anchor_index.get(relative) != accepted:
            raise AssertionError(
                f"historical anchor does not contain accepted bytes: {relative}"
            )
        if not isinstance(entry, dict) or set(entry) != {
                "source",
                "accepted_sha256",
                "accepted_hash_provenance",
                "successor_sha256",
        }:
            raise AssertionError(f"historical successor entry drifted: {relative}")
        if entry.get("source") != relative:
            raise AssertionError(f"historical successor path drifted: {relative}")
        if entry.get("accepted_sha256") != accepted:
            raise AssertionError(
                f"historical successor accepted hash drifted: {relative}"
            )
        if entry.get("accepted_hash_provenance") != provenance:
            raise AssertionError(
                f"historical successor provenance drifted: {relative}"
            )
        physical = _sha256(_fixed_regular_file(root, relative))
        _current_or_post_push_successor_sha256(
            root,
            relative,
            entry.get("successor_sha256"),
            physical,
            label=f"historical successor {relative}",
        )
    if historical.get("successor_allowlist") != sorted(
            HISTORICAL_SOURCE_ACCEPTED_SHA256):
        raise AssertionError("historical successor allowlist declaration drifted")
    for field in (
        "successor_allowlist_exact",
        "accepted_hashes_independently_located",
        "predecessor_rewrite_forbidden",
        "arbitrary_source_hash_lookup_forbidden",
        "current_bridges_excluded_from_historical_accepted_hash_allowlist",
    ):
        if historical.get(field) is not True:
            raise AssertionError(f"historical successor guard is open: {field}")


def _validate_bridge_provenance(contract: dict) -> None:
    expected = {
        "state": "bootstrap_pending_post_push_external_git_anchor",
        "normalized_source_keys": sorted(BRIDGE_SOURCE_KEYS),
        "normalization_sentinel": BRIDGE_PROVENANCE_SENTINEL,
        "source_hashes_normalized_to_break_recursive_cycle": True,
        "physical_hash_binding_scope": "current_contract_and_worktree_only",
        "external_bridge_bytes_anchor_complete": False,
        "post_push_external_git_anchor_required_before_route_promotion": True,
    }
    if contract.get("bridge_provenance") != expected:
        raise AssertionError("target-execution bridge bootstrap boundary drifted")


def _validate_claim_boundaries(root: Path, contract: dict) -> None:
    ownership_path = _fixed_regular_file(root, OWNERSHIP_RELATIVE)
    if _sha256(ownership_path) != OWNERSHIP_SHA256:
        raise AssertionError("effective ownership physical hash drifted")
    ownership_document = _read_json(root, OWNERSHIP_RELATIVE)
    if ownership_document.get("document_payload_sha256") != (
            OWNERSHIP_PAYLOAD_SHA256):
        raise AssertionError("effective ownership payload field drifted")
    if _payload_sha256(ownership_document) != OWNERSHIP_PAYLOAD_SHA256:
        raise AssertionError("effective ownership payload is invalid")
    if contract.get("data_ownership") != {
        "source": OWNERSHIP_RELATIVE,
        "sha256": OWNERSHIP_SHA256,
        "document_payload_sha256": OWNERSHIP_PAYLOAD_SHA256,
        "resource_count": 160,
        "resources_with_exactly_one_owner": 160,
        "canonical_owner_manifest_sha256": OWNERSHIP_MANIFEST_SHA256,
        "unchanged_from_predecessor": True,
    }:
        raise AssertionError("target execution changed data ownership")
    authorization = contract.get("authorization", {})
    if set(authorization) != {
            "target_dispositions_executed",
            "all_59_target_dispositions_executed",
            "typed_parity_review_complete",
            "full_target_parity_closed",
            "route_migration_eligible",
            "external_bridge_bytes_anchor_complete",
            "route_promotion_blocked_by_bridge_bootstrap",
            "two_legacy_get_routes_migrated",
            "derived_head_and_options_count_as_migrated",
            "production_schema_or_index",
            "operator_migration_implementation",
            "real_data_migration_execution",
            "migration_global_preflight_closed",
            "client_change",
            "gateway_or_proxy_change",
            "production_cutover",
    }:
        raise AssertionError("target-execution authorization shape drifted")
    if authorization.get("target_dispositions_executed") is not True:
        raise AssertionError("target execution is not positively authorized")
    if authorization.get("all_59_target_dispositions_executed") is not True:
        raise AssertionError("all 59 target dispositions are not authorized")
    if authorization.get("typed_parity_review_complete") is not False:
        raise AssertionError("typed parity review is prematurely closed")
    for field in (
        "full_target_parity_closed",
        "route_migration_eligible",
        "external_bridge_bytes_anchor_complete",
        "two_legacy_get_routes_migrated",
        "production_cutover",
    ):
        if authorization.get(field) is not False:
            raise AssertionError(f"target-execution authorization overclaims {field}")
    if authorization.get("route_promotion_blocked_by_bridge_bootstrap") is not True:
        raise AssertionError("bridge bootstrap no longer blocks route promotion")
    acceptance = contract.get("acceptance", {})
    if set(acceptance) != {
            "target_dispositions_executed",
            "all_59_target_dispositions_executed",
            "typed_parity_review_complete",
            "case_count",
            "http_execution_count",
            "business_jdbc_reached_http_count",
            "pre_business_jdbc_termination_http_count",
            "pre_business_jdbc_termination_status_counts",
            "typed_postgresql_disposition_count",
            "bound_only_case_count",
            "mocked_application_result_case_count",
            "junit_leaf_test_count",
            "full_target_parity_closed",
            "route_migration_eligible",
            "external_bridge_bytes_anchor_complete",
            "post_push_external_git_anchor_required_before_route_migration",
            "implemented_pending_get_count",
            "migrated_operation_count",
            "pending_operation_count",
            "production_cutover_operation_count",
            "production_cutover",
            "effective_resource_count",
            "resources_with_exactly_one_owner",
            "production_runtime_unchanged",
            "new_worm",
            "new_worm_report_created",
            "production_build_context_unchanged",
            "operator_and_real_migration_remain_blocked",
            "next_gate",
    }:
        raise AssertionError("target-execution acceptance shape drifted")
    if acceptance.get("target_dispositions_executed") is not True:
        raise AssertionError("target execution acceptance is not closed")
    if acceptance.get("all_59_target_dispositions_executed") is not True:
        raise AssertionError("all 59 target dispositions are not accepted")
    if acceptance.get("typed_parity_review_complete") is not False:
        raise AssertionError("typed parity review is prematurely accepted")
    if acceptance.get("business_jdbc_reached_http_count") != 49 or (
            acceptance.get("pre_business_jdbc_termination_http_count") != 8):
        raise AssertionError("target-execution acceptance JDBC reach counts drifted")
    if acceptance.get("pre_business_jdbc_termination_status_counts") != {
            "302": 5, "401": 3}:
        raise AssertionError("target-execution acceptance pre-business statuses drifted")
    for field in (
        "full_target_parity_closed",
        "route_migration_eligible",
        "external_bridge_bytes_anchor_complete",
    ):
        if acceptance.get(field) is not False:
            raise AssertionError(f"target-execution acceptance overclaims {field}")
    if acceptance.get(
            "post_push_external_git_anchor_required_before_route_migration"
    ) is not True:
        raise AssertionError("target-execution acceptance lost post-push anchor gate")
    if acceptance.get("migrated_operation_count") != 11:
        raise AssertionError("target-execution acceptance migrated count drifted")
    if acceptance.get("pending_operation_count") != 600:
        raise AssertionError("target-execution acceptance pending count drifted")
    if acceptance.get("production_cutover_operation_count") != 0:
        raise AssertionError("target-execution acceptance cutover count drifted")
    if acceptance.get("production_cutover") is not False:
        raise AssertionError("target-execution acceptance overclaims cutover")
    if acceptance.get("new_worm_report_created") is not False:
        raise AssertionError("target-execution acceptance invented a sixth WORM")
    if acceptance.get("production_build_context_unchanged") is not True:
        raise AssertionError("target-execution build-context boundary is open")
    if acceptance.get("next_gate") != NEXT_GATE:
        raise AssertionError("target-execution next gate drifted")


def validate_http_target_execution_successor_contract(
        contract: dict,
        ti_java_root: Path,
) -> None:
    """Validate a target-execution contract against only code-fixed sources."""
    if not isinstance(contract, dict):
        raise AssertionError("target-execution contract is not a JSON object")
    root = ti_java_root.resolve(strict=True)
    if set(contract) != {
            "contract_id",
            "schema_version",
            "captured_at",
            "status",
            "scope",
            "predecessor",
            "source_contracts",
            "historical_successor_acceptance",
            "bridge_provenance",
            "production_surface",
            "verification_evidence",
            "routes_and_openapi",
            "data_ownership",
            "worm_evidence",
            "authorization",
            "acceptance",
            "document_payload_sha256",
    }:
        raise AssertionError("target-execution contract top-level shape drifted")
    if contract.get("schema_version") != 1:
        raise AssertionError("target-execution contract schema drifted")
    if contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("target-execution contract id drifted")
    if contract.get("status") != CONTRACT_STATUS:
        raise AssertionError("target-execution contract status drifted")
    if contract.get("scope") != CONTRACT_SCOPE:
        raise AssertionError("target-execution contract scope drifted")
    if contract.get("captured_at") != CONTRACT_CAPTURED_AT:
        raise AssertionError("target-execution capture timestamp drifted")
    if contract.get("document_payload_sha256") != _payload_sha256(contract):
        raise AssertionError("target-execution contract document payload is invalid")

    predecessor = _validate_predecessor(root, contract)
    _validate_sources(root, contract)
    _validate_evidence(root, contract)
    _validate_production_surface(root, contract, predecessor)
    _validate_worm_and_routes(root, contract, predecessor)
    _validate_historical_successors(root, contract)
    _validate_bridge_provenance(contract)
    _validate_claim_boundaries(root, contract)

    if not _is_sha256(TRUST_PAYLOAD_SHA256):
        raise AssertionError("unsettled target-execution trust payload SHA-256")
    if _trust_payload_sha256(contract) != TRUST_PAYLOAD_SHA256:
        raise AssertionError("target-execution bridge-normalized trust payload drifted")


def load_http_target_execution_successor_contract(
        ti_java_root: Path,
) -> dict | None:
    """Load and validate the fixed contract; return ``None`` when absent."""
    root = ti_java_root.resolve(strict=True)
    path = root / CONTRACT_RELATIVE
    if not path.exists():
        return None
    path = _fixed_regular_file(root, CONTRACT_RELATIVE)
    with path.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    validate_http_target_execution_successor_contract(contract, root)
    return contract


def accepted_sha256(relative: str) -> str | None:
    """Return the code-fixed predecessor hash for an allowlisted path only."""
    return HISTORICAL_SOURCE_ACCEPTED_SHA256.get(relative)


def _load_successor_envelope(ti_java_root: Path) -> tuple[Path, dict] | None:
    """Validate the code-fixed contract envelope without replaying every proof.

    Historical bridges call ``successor_sha256`` once per source.  Replaying
    PostgreSQL/WORM/runtime validation for every lookup creates a multiplicative
    chain.  The bridge-normalized payload binds the contract except for the two
    recursively normalized bridge source hashes; ``bridge_provenance`` keeps
    that bootstrap boundary explicit and blocks route promotion until a later
    Git-anchored node fixes those bytes.  Each lookup still verifies the
    requested physical source below, and the production gate calls full
    ``load``.
    """
    root = ti_java_root.resolve(strict=True)
    path = root / CONTRACT_RELATIVE
    if not path.exists():
        return None
    contract = _read_json(root, CONTRACT_RELATIVE)
    if contract.get("schema_version") != 1:
        raise AssertionError("target-execution successor envelope schema drifted")
    if contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("target-execution successor envelope id drifted")
    if contract.get("status") != CONTRACT_STATUS:
        raise AssertionError("target-execution successor envelope status drifted")
    if contract.get("scope") != CONTRACT_SCOPE:
        raise AssertionError("target-execution successor envelope scope drifted")
    if contract.get("captured_at") != CONTRACT_CAPTURED_AT:
        raise AssertionError("target-execution successor envelope timestamp drifted")
    if contract.get("document_payload_sha256") != _payload_sha256(contract):
        raise AssertionError("target-execution successor envelope payload is invalid")
    _validate_bridge_provenance(contract)
    if contract.get("authorization", {}).get("route_migration_eligible") is not False:
        raise AssertionError("target-execution successor envelope promotes routes")
    if not _is_sha256(TRUST_PAYLOAD_SHA256):
        raise AssertionError("unsettled target-execution trust payload SHA-256")
    if _trust_payload_sha256(contract) != TRUST_PAYLOAD_SHA256:
        raise AssertionError(
            "target-execution successor envelope bridge-normalized trust drifted"
        )
    return root, contract


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    """Return a validated successor hash only for the historical allowlist."""
    accepted = HISTORICAL_SOURCE_ACCEPTED_SHA256.get(relative)
    if accepted is None:
        return None
    loaded = _load_successor_envelope(ti_java_root)
    if loaded is None:
        return None
    root, contract = loaded
    entry = contract.get("historical_successor_acceptance", {}).get(
        "anchored_source_overrides", {}
    ).get(relative)
    if not isinstance(entry, dict):
        raise AssertionError(f"target-execution successor entry is missing: {relative}")
    successor = entry.get("successor_sha256")
    if entry.get("source") != relative or entry.get("accepted_sha256") != accepted:
        raise AssertionError(f"target-execution successor entry drifted: {relative}")
    if not _is_sha256(successor):
        raise AssertionError(f"target-execution successor hash is invalid: {relative}")
    physical = _sha256(_fixed_regular_file(root, relative))
    return _current_or_post_push_successor_sha256(
        root,
        relative,
        successor,
        physical,
        label=f"target-execution successor {relative}",
    )


def fixed_source_sha256(ti_java_root: Path, relative: str) -> str | None:
    """Return a validated current hash for one code-fixed target source only."""
    names = [name for name, path in SOURCE_PATHS.items() if path == relative]
    if len(names) != 1:
        return None
    loaded = _load_successor_envelope(ti_java_root)
    if loaded is None:
        return None
    root, contract = loaded
    reference = contract.get("source_contracts", {}).get(names[0])
    if not isinstance(reference, dict) or reference.get("source") != relative:
        raise AssertionError(f"target-execution fixed source drifted: {relative}")
    digest = reference.get("sha256")
    if not _is_sha256(digest):
        raise AssertionError(f"target-execution fixed source hash is invalid: {relative}")
    physical = _sha256(_fixed_regular_file(root, relative))
    return _current_or_post_push_successor_sha256(
        root,
        relative,
        digest,
        physical,
        label=f"target-execution fixed source {relative}",
    )
