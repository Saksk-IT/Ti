#!/usr/bin/env python3
"""Build the fail-closed Phase 4C user-counts HTTP implementation contract.

The immutable HTTP entry contract remains the predecessor.  This builder
admits only its already-authorized production delta and requires a fresh WORM
tip plus the network, PostgreSQL, Redis, OpenAPI, and 59-case target evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

try:
    from tools import build_phase4c_personal_bank_user_counts_read_contract as read_builder
    from tools import phase2_wormhole_successor_acceptance as phase2_worm
except ModuleNotFoundError as error:  # Direct execution from tools/.
    if error.name not in {
        "tools",
        "tools.build_phase4c_personal_bank_user_counts_read_contract",
        "tools.phase2_wormhole_successor_acceptance",
    }:
        raise
    import build_phase4c_personal_bank_user_counts_read_contract as read_builder
    import phase2_wormhole_successor_acceptance as phase2_worm


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-contract.json"
)
CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-http-implementation-contract"
CONTRACT_STATUS = "implementation_present_parity_incomplete_routes_pending"
CONTRACT_SCOPE = "phase4c-personal-bank-user-counts-http-implementation"


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

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-http-entry-contract.json"
)
PREDECESSOR_ID = "ti.phase4c.personal-bank-user-counts-http-entry-contract"
PREDECESSOR_STATUS = "entry_gate_passed_http_implementation_not_started"
PREDECESSOR_SHA256 = (
    "d91d4ce6ccae982ded22a83ca9a7663042102c257565d3973b125e535f9c6676"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "ca430ec715d3b673e00f72fd8e290bed4b228970b9940864745e9c6d560a7402"
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
READ_BUILDER_RELATIVE = (
    "tools/build_phase4c_personal_bank_user_counts_read_contract.py"
)
READ_BUILDER_SHA256 = (
    "f923257659b03ffb0fd52a60894ba5b59df3ba242cf187416bf52edda2eeb3bd"
)

EXPECTED_PREDECESSOR_RUNTIME_FILE_COUNT = 288
EXPECTED_PREDECESSOR_RUNTIME_MANIFEST_SHA256 = (
    "145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc"
)
EXPECTED_CURRENT_RUNTIME_FILE_COUNT = 297
EXPECTED_MAIN_FILE_COUNT = 40
EXPECTED_MAIN_MANIFEST_SHA256 = (
    "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1"
)
EXPECTED_PUBLIC_APPLICATION_METHOD_COUNT = 27
EXPECTED_PUBLIC_APPLICATION_METHODS_SHA256 = (
    "c3b6b2eb984c1f910605bdf08c389484e5a675969c7e4ab71e5208c40d45530d"
)

WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
GOLDEN_RELATIVE = "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
GOLDEN_SHA256 = (
    "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1"
)
GOLDEN_CASE_PAYLOAD_SHA256 = (
    "0ace2f642523a62e802db3dc3d045d601743a277e7edf7e2cf214d00619a51bf"
)
GOLDEN_TARGET_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-mapping-evidence.json"
)
BOUNDARY_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-http-boundary-evidence.json"
)
RATE_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-rate-limit-evidence.json"
)
OPENAPI_RELATIVE = "openapi/phase4c-personal-bank-user-counts.openapi.json"
ROUTE_DELTA_RELATIVE = "docs/refactor/phase4c/route-parity-delta.csv"
OWNERSHIP_PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/effective-data-ownership-status.json"
)
OWNERSHIP_PREDECESSOR_SHA256 = (
    "025a9f24edfb502b49e672c7c0a2e52b6bba022d6337dfe56159ebd498b69eb7"
)
OWNERSHIP_DELTA_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-data-ownership-delta.csv"
)
OWNERSHIP_EFFECTIVE_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-effective-data-ownership-status.json"
)
OWNERSHIP_BASELINE_RELATIVE = "docs/refactor/03-data-ownership.csv"
OWNERSHIP_BASELINE_SHA256 = (
    "3f9cb0650c523593d7037dc24df902dbccdb3885f261f530e1725a9dc7a31748"
)
OWNERSHIP_PHASE4A_RELATIVE = (
    "docs/refactor/phase4a/effective-data-ownership-status.json"
)
OWNERSHIP_PHASE4A_SHA256 = (
    "455b45b6c838c2308b3018e690bd444b503d3493b6290fa3e5083c4f84e01127"
)
OWNERSHIP_RESOURCE_NAME = (
    "ti-java:learning:personal-bank-user-counts-read-rate:"
    "<api|web>:<identity:v1|ip:v1>:<hmac_sha256>:<second|hour|day>"
)
OWNERSHIP_PREDECESSOR_MANIFEST_SHA256 = (
    "76b6143812e7a352dd0c4eb515260d956ac963a26bc211f85c9bab182df45a3b"
)
OWNERSHIP_EFFECTIVE_MANIFEST_SHA256 = (
    "9767e2c6d6619be0db5f7b3f78335b23ff2020a9d756a2d6a3bf36eccc78908e"
)

EXPECTED_ADDED_RUNTIME_PATHS = (
    OPENAPI_RELATIVE,
    "server/src/main/java/io/saksk/ti/web/compat/LegacyPersonalBankUserCountsController.java",
    "server/src/main/java/io/saksk/ti/web/compat/LegacyPersonalBankUserCountsSecurityErrorWriter.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsCorsConfigurationSource.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRateLimitFilter.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRateLimitProperties.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRateLimiter.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRequestResolver.java",
    "server/src/main/java/io/saksk/ti/web/security/RedisPersonalBankUserCountsReadRateLimiter.java",
)
EXPECTED_CHANGED_RUNTIME_PATHS = (
    ".env.example",
    "compose.dev.yml",
    "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java",
    "server/src/main/java/io/saksk/ti/web/security/LoginRateLimitConfiguration.java",
    "server/src/main/resources/application-prod.yml",
    "server/src/main/resources/application.yml",
)
EXPECTED_FORBIDDEN_UNCHANGED_MAIN_PATHS = (
    "server/src/main/java/io/saksk/ti/identity/api/LegacyCredentialAuthenticationApi.java",
    "server/src/main/java/io/saksk/ti/web/security/TargetSessionAuthenticationFilter.java",
    "server/src/main/java/io/saksk/ti/web/request/RequestId.java",
    "server/src/main/java/io/saksk/ti/web/request/RequestIdFilter.java",
    "server/src/main/java/io/saksk/ti/web/LegacyDecimalPathInteger.java",
    "server/src/main/java/io/saksk/ti/web/error/GlobalExceptionHandler.java",
    "server/src/main/java/io/saksk/ti/web/error/SafeErrorController.java",
)

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

# Fixed predecessor hashes, copied from the immutable HTTP entry contract.
# Only these predecessor sources may move to reviewed successor bytes.
HTTP_ENTRY_SOURCE_ACCEPTED_SHA256 = {
    "README.md": "3d18a7b86354b8cad4d54a76a9a3722435dd570b612a5a9e65ca9a4aed2864b6",
    "docs/refactor/05-progress.md": (
        "f44a6efdec4342f13ea1f28831bdca9b36b84f48e932bd4f1d257070af555c7e"
    ),
    "docs/refactor/phase4c/README.md": (
        "07852f793ed84c90212c5b52dedcf82ed9b52ce9b229e35c56c94eafea253a8b"
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py": (
        "fdbf282f7be37e6138702e973bf67737c940e7944ac6103f8954902d5b8621e4"
    ),
    "tools/phase4c_http_entry_successor_acceptance.py": (
        "f66bdc4746f3ee720bfc13213e24c44e30140d4b0f311d2f8a53cd01b8e90f11"
    ),
    "tools/phase4c_read_successor_acceptance.py": (
        "8b4a57393021a304640797cc64a7f4d44aad83ab6d57c50d81f8158aa9008f82"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpEntrySuccessorAcceptance.java"
    ): "57930b46f1bcd0f0df4bedce1fb41de7b63c53f58b3a45eae49ab858ea1c277a",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ): "8a008483f70788ffc10158ae789b7b318e8478ad249514f0551d8b0361dcf52b",
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "6d493304cc01fcbc801b066700b98bb6b0a1750ee9e3d9ce03867ee6e92991cc"
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "c08ff0263d0da2c4e08733685256d7946a316a06772b8959c3520cc7947aaa76"
    ),
    "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java": (
        "aaf0b5cd5431dbaa6033bae195dcd42d04c3000d3c3f9ce1083abac54b18cb5a"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "LoginRateLimitConfiguration.java"
    ): "e681903ee752b3452bdbe5e7a4f2e93f60f95c7b34c77e6f1e552a7e891c08fe",
    "server/src/main/resources/application.yml": (
        "c760cebe37e4433874c1171782163a3572e92a73c565120b0fa2a52d45a40c5e"
    ),
    "server/src/main/resources/application-prod.yml": (
        "c7a804c93e0937676c4f398899700830df854bdcc404cc72361423d92525ce3f"
    ),
}

# The Phase 4B entry test already moved once under the immutable read
# successor.  The HTTP implementation is the next reviewed successor for
# that exact terminal byte sequence; keeping this separate from the HTTP
# entry predecessor map prevents either predecessor from authorizing paths it
# never recorded.
READ_TERMINAL_SOURCE_ACCEPTED_SHA256 = {
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "590f4d62c45c4fc9fdde9332f2de376f62481b672120c72389071e4a8bf334a7"
    ),
}

SOURCE_PATHS = {
    "predecessor": PREDECESSOR_RELATIVE,
    "read_predecessor": READ_PREDECESSOR_RELATIVE,
    "read_contract_builder": READ_BUILDER_RELATIVE,
    "phase4b_goldens": GOLDEN_RELATIVE,
    "http_boundary_evidence": BOUNDARY_RELATIVE,
    "rate_limit_evidence": RATE_RELATIVE,
    "golden_target_evidence": GOLDEN_TARGET_RELATIVE,
    "worm_tip": WORM_RELATIVE,
    "openapi_overlay": OPENAPI_RELATIVE,
    "route_delta": ROUTE_DELTA_RELATIVE,
    "ownership_predecessor": OWNERSHIP_PREDECESSOR_RELATIVE,
    "ownership_baseline": OWNERSHIP_BASELINE_RELATIVE,
    "ownership_phase4a": OWNERSHIP_PHASE4A_RELATIVE,
    "ownership_delta": OWNERSHIP_DELTA_RELATIVE,
    "ownership_effective": OWNERSHIP_EFFECTIVE_RELATIVE,
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
    "golden_target_test": (
        "server/src/test/java/io/saksk/ti/web/compat/"
        "LegacyPersonalBankUserCountsGoldenTargetMappingTest.java"
    ),
    "http_adapter_security_test": (
        "server/src/test/java/io/saksk/ti/web/compat/"
        "LegacyPersonalBankUserCountsHttpTest.java"
    ),
    "controller_unit_test": (
        "server/src/test/java/io/saksk/ti/web/compat/"
        "LegacyPersonalBankUserCountsControllerTest.java"
    ),
    "security_error_writer_unit_test": (
        "server/src/test/java/io/saksk/ti/web/compat/"
        "LegacyPersonalBankUserCountsSecurityErrorWriterTest.java"
    ),
    "cors_configuration_unit_test": (
        "server/src/test/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsCorsConfigurationSourceTest.java"
    ),
    "rate_limit_filter_unit_test": (
        "server/src/test/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRateLimitFilterTest.java"
    ),
    "rate_limit_properties_unit_test": (
        "server/src/test/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRateLimitPropertiesTest.java"
    ),
    "request_resolver_unit_test": (
        "server/src/test/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRequestResolverTest.java"
    ),
    "redis_rate_limiter_unit_test": (
        "server/src/test/java/io/saksk/ti/web/security/"
        "RedisPersonalBankUserCountsReadRateLimiterTest.java"
    ),
    "user_counts_rate_limit_secret_example": (
        "infra/phase2/secrets/"
        "ti-personal-bank-user-counts-rate-limit-key-secret.example"
    ),
    "openapi_route_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_openapi_route_contract.py"
    ),
    "contract_builder": (
        "tools/build_phase4c_personal_bank_user_counts_http_implementation_contract.py"
    ),
    "contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py"
    ),
    "python_successor_bridge": (
        "tools/phase4c_http_implementation_successor_acceptance.py"
    ),
    "java_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ),
    "java_contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpImplementationContractParityTest.java"
    ),
    "phase2_worm_validator": "tools/phase2_wormhole_successor_acceptance.py",
    "phase2_worm_validator_test": (
        "tools/test_phase2_wormhole_successor_acceptance.py"
    ),
    "phase2_worm_runner": "infra/phase2/verify-local-reference-wormhole.sh",
    "phase2_static_gate": "infra/phase2/verify-static.sh",
    "phase2_worm_readme": "infra/phase2/README.md",
    "phase2_reference_drift_manifest": (
        "infra/phase2/reference-drift-manifest.json"
    ),
    "phase2_build_context_hasher": "infra/phase2/hash-java-build-context.sh",
    "java_dockerfile": "server/Dockerfile",
    "historical_phase4b_entry_contract_test": (
        "tools/test_phase4b_personal_bank_user_counts_entry_contract.py"
    ),
    "historical_python_read_successor_bridge": (
        "tools/phase4c_read_successor_acceptance.py"
    ),
}
BRIDGE_SOURCE_KEYS = frozenset({"python_successor_bridge", "java_successor_bridge"})
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"


canonical_json = read_builder.canonical_json
sha256 = read_builder.sha256
sha256_json = read_builder.sha256_json
load_json = read_builder.load_json


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
        raise ValueError("implementation source contracts are missing")
    normalized = {}
    for name, reference in sources.items():
        if not isinstance(reference, dict):
            raise ValueError(f"invalid implementation source reference: {name}")
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
        raise ValueError(f"fixed implementation path escapes Ti-Java: {relative}")
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"fixed implementation path contains symlink: {relative}")
    try:
        resolved = (root / candidate).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise FileNotFoundError(
            f"required Phase4C HTTP implementation source is missing: {relative}"
        ) from error
    if not resolved.is_file():
        raise ValueError(f"fixed implementation path is not a file: {relative}")
    return resolved


def source_reference(relative: str) -> dict:
    path = fixed_regular_file(relative)
    return {"source": relative, "sha256": sha256(path)}


def validate_predecessors() -> tuple[dict, dict]:
    predecessor_path = fixed_regular_file(PREDECESSOR_RELATIVE)
    if sha256(predecessor_path) != PREDECESSOR_SHA256:
        raise ValueError("Phase4C HTTP entry predecessor is not byte immutable")
    predecessor = load_json(predecessor_path)
    if predecessor.get("contract_id") != PREDECESSOR_ID:
        raise ValueError("unexpected Phase4C HTTP entry predecessor id")
    if predecessor.get("status") != PREDECESSOR_STATUS:
        raise ValueError("unexpected Phase4C HTTP entry predecessor status")
    if predecessor.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("Phase4C HTTP entry predecessor payload field drifted")
    if document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("Phase4C HTTP entry predecessor payload is invalid")

    read_path = fixed_regular_file(READ_PREDECESSOR_RELATIVE)
    if sha256(read_path) != READ_PREDECESSOR_SHA256:
        raise ValueError("Phase4C read predecessor is not byte immutable")
    read = load_json(read_path)
    if read.get("document_payload_sha256") != READ_PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("Phase4C read predecessor payload field drifted")
    if document_payload_sha256(read) != READ_PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("Phase4C read predecessor payload is invalid")
    if predecessor.get("predecessor", {}).get("sha256") != READ_PREDECESSOR_SHA256:
        raise ValueError("HTTP entry predecessor no longer fixes the read predecessor")
    if read.get("source_contracts", {}).get("contract_builder") != {
        "source": READ_BUILDER_RELATIVE,
        "sha256": READ_BUILDER_SHA256,
    }:
        raise ValueError("read predecessor no longer fixes its contract builder")
    if sha256(fixed_regular_file(READ_BUILDER_RELATIVE)) != READ_BUILDER_SHA256:
        raise ValueError("read contract builder physical hash drifted")

    predecessor_sources = {
        reference["source"]: reference["sha256"]
        for reference in predecessor["source_contracts"].values()
    }
    for relative, accepted in HTTP_ENTRY_SOURCE_ACCEPTED_SHA256.items():
        if predecessor_sources.get(relative) != accepted:
            raise ValueError(f"fixed HTTP entry accepted hash drifted: {relative}")
    read_sources = {
        reference["source"]: reference["sha256"]
        for reference in read["source_contracts"].values()
    }
    for relative, accepted in READ_TERMINAL_SOURCE_ACCEPTED_SHA256.items():
        if read_sources.get(relative) != accepted:
            raise ValueError(f"fixed read-terminal accepted hash drifted: {relative}")
    return predecessor, read


def successor_source_overrides(
        accepted_sources: dict[str, str],
) -> dict[str, dict]:
    return {
        relative: {
            "source": relative,
            "accepted_sha256": accepted,
            "successor_sha256": sha256(fixed_regular_file(relative)),
        }
        for relative, accepted in sorted(accepted_sources.items())
    }


def validate_runtime_transition(predecessor: dict, read: dict) -> dict:
    baseline = read["implementation"]["production_runtime_surface"]
    baseline_files = baseline["files"]
    if baseline["file_count"] != EXPECTED_PREDECESSOR_RUNTIME_FILE_COUNT:
        raise ValueError("unexpected read-runtime predecessor file count")
    if baseline["manifest_sha256"] != EXPECTED_PREDECESSOR_RUNTIME_MANIFEST_SHA256:
        raise ValueError("unexpected read-runtime predecessor manifest hash")
    if sha256_json(baseline_files) != EXPECTED_PREDECESSOR_RUNTIME_MANIFEST_SHA256:
        raise ValueError("invalid embedded read-runtime predecessor manifest")
    entry_surface = predecessor["current_state"]["current_production_surface"]
    if entry_surface["production_runtime_file_count"] != baseline["file_count"]:
        raise ValueError("HTTP entry runtime count does not match read predecessor")
    if entry_surface["production_runtime_manifest_sha256"] != baseline["manifest_sha256"]:
        raise ValueError("HTTP entry runtime hash does not match read predecessor")

    physical_files = read_builder.production_runtime_manifest()
    accepted_paths = set(baseline_files) | set(EXPECTED_ADDED_RUNTIME_PATHS)
    if not accepted_paths <= set(physical_files):
        raise ValueError("HTTP implementation historical runtime paths are missing")
    current_files = {
        path: physical_files[path]
        for path in sorted(accepted_paths)
    }
    if physical_files != current_files:
        successor = tag_preflight_successor().validate_production_runtime_successor(
            ROOT,
            current_files,
            physical_files,
            view="full_runtime",
        )
        if (
            successor.accepted_file_count != EXPECTED_CURRENT_RUNTIME_FILE_COUNT
            or successor.accepted_manifest_sha256 != sha256_json(current_files)
            or successor.current_file_count != len(physical_files)
            or successor.current_manifest_sha256 != sha256_json(physical_files)
            or successor.changed_files
            or successor.deleted_files
        ):
            raise ValueError("tag preflight runtime successor descriptor drifted")
    added = {
        path: current_files[path]
        for path in sorted(set(current_files) - set(baseline_files))
    }
    changed = {
        path: {
            "predecessor_sha256": baseline_files[path],
            "successor_sha256": current_files[path],
        }
        for path in sorted(set(current_files) & set(baseline_files))
        if current_files[path] != baseline_files[path]
    }
    deleted = sorted(set(baseline_files) - set(current_files))
    if tuple(added) != tuple(sorted(EXPECTED_ADDED_RUNTIME_PATHS)):
        raise ValueError("HTTP implementation added runtime paths outside the exact allowlist")
    if tuple(changed) != tuple(sorted(EXPECTED_CHANGED_RUNTIME_PATHS)):
        raise ValueError("HTTP implementation changed runtime paths outside the exact allowlist")
    if deleted:
        raise ValueError("HTTP implementation deleted predecessor runtime files")
    if len(current_files) != EXPECTED_CURRENT_RUNTIME_FILE_COUNT:
        raise ValueError("unexpected HTTP implementation runtime file count")

    physical_learning_personalbank = read_builder.main_source_manifest()
    predecessor_main = read["implementation"][
        "learning_and_personalbank_main_source_manifest"
    ]
    if physical_learning_personalbank != predecessor_main:
        successor = tag_preflight_successor().validate_production_runtime_successor(
            ROOT,
            predecessor_main,
            physical_learning_personalbank,
            view="learning_personalbank_main",
        )
        if (
            successor.accepted_file_count != EXPECTED_MAIN_FILE_COUNT
            or successor.accepted_manifest_sha256 != EXPECTED_MAIN_MANIFEST_SHA256
            or successor.changed_files
            or successor.deleted_files
        ):
            raise ValueError("tag preflight main-source successor descriptor drifted")
    learning_personalbank = predecessor_main
    if len(learning_personalbank) != EXPECTED_MAIN_FILE_COUNT:
        raise ValueError("unexpected learning/personalbank source count")
    if sha256_json(learning_personalbank) != EXPECTED_MAIN_MANIFEST_SHA256:
        raise ValueError("learning/personalbank source manifest drifted")

    methods = read_builder.public_application_methods()
    predecessor_methods = predecessor["current_state"][
        "current_production_surface"
    ]["public_application_methods"]
    if methods != predecessor_methods:
        raise ValueError("the exact 27-method application API changed")
    if len(methods) != EXPECTED_PUBLIC_APPLICATION_METHOD_COUNT:
        raise ValueError("unexpected public application method count")
    if sha256_json(methods) != EXPECTED_PUBLIC_APPLICATION_METHODS_SHA256:
        raise ValueError("public application API manifest drifted")

    forbidden = {}
    for relative in EXPECTED_FORBIDDEN_UNCHANGED_MAIN_PATHS:
        if relative not in baseline_files or relative not in current_files:
            raise ValueError(f"forbidden main source is not in both manifests: {relative}")
        if current_files[relative] != baseline_files[relative]:
            raise ValueError(f"forbidden main source changed: {relative}")
        forbidden[relative] = current_files[relative]

    return {
        "predecessor": {
            "file_count": len(baseline_files),
            "manifest_sha256": sha256_json(baseline_files),
        },
        "current": {
            "file_count": len(current_files),
            "manifest_sha256": sha256_json(current_files),
            "files": current_files,
        },
        "exact_delta": {
            "added_file_count": len(added),
            "added_files": added,
            "changed_file_count": len(changed),
            "changed_files": changed,
            "deleted_file_count": 0,
            "deleted_files": [],
            "new_main_source_count": 8,
            "new_openapi_file_count": 1,
            "changed_main_source_count": 2,
            "changed_configuration_file_count": 4,
        },
        "learning_and_personalbank": {
            "file_count": len(learning_personalbank),
            "manifest_sha256": sha256_json(learning_personalbank),
            "files": learning_personalbank,
            "unchanged_from_read_predecessor": True,
        },
        "public_application_api": {
            "method_count": len(methods),
            "methods_sha256": sha256_json(methods),
            "methods": methods,
            "unchanged_from_http_entry_predecessor": True,
        },
        "forbidden_main_sources": {
            "unchanged": True,
            "files": forbidden,
        },
    }


def validate_route_and_openapi() -> dict:
    with fixed_regular_file(ROUTE_DELTA_RELATIVE).open(
            newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 2:
        raise ValueError("Phase4C route delta must contain exactly two GET rows")
    by_id = {row["route_id"]: row for row in rows}
    if set(by_id) != {route["route_id"] for route in ROUTES}:
        raise ValueError("Phase4C route delta contains unexpected route ids")
    for route in ROUTES:
        row = by_id[route["route_id"]]
        expected = {
            "path": route["path"],
            "method": "GET",
            "base_target_module": "personalbank",
            "phase4c_target_module": "learning",
            "base_migration_status": "pending",
            "phase4c_migration_status": "pending",
            "application_api": (
                "io.saksk.ti.learning.api.LearningApplicationApi"
                "#findPersonalBankUserCounts"
            ),
            "production_cutover": "false",
        }
        for field, value in expected.items():
            if row.get(field) != value:
                raise ValueError(f"route delta field drift for {route['route_id']}: {field}")

    openapi = load_json(fixed_regular_file(OPENAPI_RELATIVE))
    if openapi.get("openapi") != "3.1.2":
        raise ValueError("unexpected Phase4C OpenAPI version")
    expected_paths = {route["target_path"] for route in ROUTES}
    if set(openapi.get("paths", {})) != expected_paths:
        raise ValueError("Phase4C OpenAPI paths are not the exact two aliases")
    accounting = openapi.get("x-ti-route-accounting", {})
    expected_accounting = {
        "frozenBaselineOperationCount": 611,
        "predecessorMigratedOperationCount": 11,
        "phase4cLegacyGetDeltaCount": 0,
        "phase4cImplementedPendingGetCount": 2,
        "effectiveMigratedOperationCount": 11,
        "effectivePendingOperationCount": 600,
        "productionCutoverOperationCount": 0,
        "countedMethods": ["GET"],
        "documentedDerivedMethods": ["HEAD", "OPTIONS"],
        "derivedMethodsCountAsMigratedOperations": False,
    }
    if accounting != expected_accounting:
        raise ValueError("Phase4C OpenAPI route accounting drifted")
    for route in ROUTES:
        operation = openapi["paths"][route["target_path"]]["get"]
        if operation.get("x-ti-route-id") != route["route_id"]:
            raise ValueError(f"OpenAPI route id drift for {route['route_id']}")
        if operation.get("x-ti-migration") != {
            "status": "pending",
            "targetModule": "learning",
            "countsAsMigratedOperation": False,
            "productionCutover": False,
        }:
            raise ValueError(f"OpenAPI migration marker drift for {route['route_id']}")
    return {
        "route_delta": source_reference(ROUTE_DELTA_RELATIVE),
        "openapi_overlay": source_reference(OPENAPI_RELATIVE),
        "routes": list(ROUTES),
        "implemented_pending_get_count": 2,
        "migrated_operation_count": 11,
        "pending_operation_count": 600,
        "production_cutover_operation_count": 0,
        "route_migration_eligible": False,
        "counted_methods": ["GET"],
        "derived_methods": ["HEAD", "OPTIONS"],
    }


def require_fragments(relative: str, fragments: tuple[str, ...]) -> None:
    text = fixed_regular_file(relative).read_text(encoding="utf-8")
    for fragment in fragments:
        if fragment not in text:
            raise ValueError(f"required evidence fragment missing in {relative}: {fragment}")


def recompute_effective_owner_manifest(predecessor: dict) -> list[dict]:
    phase4a_path = fixed_regular_file(OWNERSHIP_PHASE4A_RELATIVE)
    if sha256(phase4a_path) != OWNERSHIP_PHASE4A_SHA256:
        raise ValueError("Phase4A ownership status physical hash drifted")
    if predecessor.get("predecessor") != {
        "source": "../phase4a/effective-data-ownership-status.json",
        "sha256": OWNERSHIP_PHASE4A_SHA256,
        "resource_count": 159,
        "immutable": True,
    }:
        raise ValueError("Phase4C ownership predecessor link drifted")

    phase4a = load_json(phase4a_path)
    if phase4a.get("contract_id") != "ti.phase4a.effective-data-ownership-status":
        raise ValueError("unexpected Phase4A ownership status id")
    if phase4a.get("baseline") != {
        "source": "../03-data-ownership.csv",
        "sha256": OWNERSHIP_BASELINE_SHA256,
        "resource_count": 154,
        "immutable": True,
    }:
        raise ValueError("Phase4A ownership baseline link drifted")
    phase4a_effective = phase4a.get("effective", {})
    if phase4a_effective.get("resource_count") != 159:
        raise ValueError("unexpected Phase4A ownership resource count")
    if phase4a_effective.get("resources_with_exactly_one_owner") != 159:
        raise ValueError("Phase4A ownership is not uniquely owned")

    baseline_path = fixed_regular_file(OWNERSHIP_BASELINE_RELATIVE)
    if sha256(baseline_path) != OWNERSHIP_BASELINE_SHA256:
        raise ValueError("ownership baseline physical hash drifted")
    base_rows = list(csv.DictReader(
        baseline_path.read_text(encoding="utf-8").splitlines()
    ))
    owners: dict[tuple[str, str], str] = {}
    for row in base_rows:
        key = (row.get("resource_kind", ""), row.get("resource_name", ""))
        owner = row.get("target_owner", "").strip()
        if not all(key) or not owner:
            raise ValueError(f"invalid base ownership row: {key}")
        if key in owners:
            raise ValueError(f"duplicate base ownership resource: {key}")
        owners[key] = owner
    if len(owners) != 154:
        raise ValueError("unexpected ownership baseline resource count")

    phase4a_new = phase4a_effective.get("new_resources", [])
    if not isinstance(phase4a_new, list) or len(phase4a_new) != 5:
        raise ValueError("unexpected Phase4A ownership additions")
    for resource in phase4a_new:
        key = (resource.get("resource_kind", ""), resource.get("resource_name", ""))
        owner = resource.get("owner", "").strip()
        if not all(key) or not owner:
            raise ValueError(f"invalid Phase4A ownership resource: {key}")
        if key in owners:
            raise ValueError(f"duplicate Phase4A ownership resource: {key}")
        owners[key] = owner
    if len(owners) != 159:
        raise ValueError("Phase4A effective ownership count mismatch")

    overrides = predecessor.get("effective", {}).get("owner_overrides", [])
    expected_override = {
        "resource_kind": "db_kv_namespace",
        "resource_name": "bank_<bank_id>_tags",
        "base_owner": "personalbank",
        "owner": "learning",
        "production_cutover": False,
    }
    if overrides != [expected_override]:
        raise ValueError("unexpected Phase4C ownership override")
    override_key = (
        expected_override["resource_kind"], expected_override["resource_name"]
    )
    if owners.get(override_key) != expected_override["base_owner"]:
        raise ValueError("Phase4C ownership override base owner drifted")
    owners[override_key] = expected_override["owner"]

    predecessor_manifest = [
        {"resource_kind": key[0], "resource_name": key[1], "owner": owner}
        for key, owner in sorted(owners.items())
    ]
    if sha256_json(predecessor_manifest) != OWNERSHIP_PREDECESSOR_MANIFEST_SHA256:
        raise ValueError("recomputed Phase4C predecessor owner manifest drifted")

    new_key = ("redis_key", OWNERSHIP_RESOURCE_NAME)
    if new_key in owners:
        raise ValueError("HTTP rate-limit ownership resource collides with predecessor")
    owners[new_key] = "learning"
    effective_manifest = [
        {"resource_kind": key[0], "resource_name": key[1], "owner": owner}
        for key, owner in sorted(owners.items())
    ]
    if len(effective_manifest) != 160:
        raise ValueError("HTTP effective ownership count mismatch")
    if sha256_json(effective_manifest) != OWNERSHIP_EFFECTIVE_MANIFEST_SHA256:
        raise ValueError("recomputed HTTP effective owner manifest drifted")
    return effective_manifest


def validate_data_ownership() -> dict:
    predecessor_path = fixed_regular_file(OWNERSHIP_PREDECESSOR_RELATIVE)
    if sha256(predecessor_path) != OWNERSHIP_PREDECESSOR_SHA256:
        raise ValueError("Phase4C ownership predecessor is not byte immutable")
    predecessor = load_json(predecessor_path)
    if predecessor.get("contract_id") != "ti.phase4c.effective-data-ownership-status":
        raise ValueError("unexpected Phase4C ownership predecessor id")
    if predecessor.get("document_payload_sha256") != document_payload_sha256(
            predecessor):
        raise ValueError("invalid Phase4C ownership predecessor payload")
    predecessor_effective = predecessor.get("effective", {})
    if predecessor_effective.get("resource_count") != 159:
        raise ValueError("unexpected Phase4C ownership predecessor count")
    if predecessor_effective.get("resources_with_exactly_one_owner") != 159:
        raise ValueError("Phase4C ownership predecessor is not uniquely owned")
    if predecessor_effective.get(
            "canonical_owner_manifest_sha256"
    ) != OWNERSHIP_PREDECESSOR_MANIFEST_SHA256:
        raise ValueError("Phase4C ownership predecessor manifest drifted")
    owner_manifest = recompute_effective_owner_manifest(predecessor)

    delta_path = fixed_regular_file(OWNERSHIP_DELTA_RELATIVE)
    rows = list(csv.DictReader(delta_path.read_text(encoding="utf-8").splitlines()))
    expected_row = {
        "resource_kind": "redis_key",
        "resource_name": OWNERSHIP_RESOURCE_NAME,
        "base_resource": "false",
        "phase4c_owner": "learning",
        "persistence_role": "runtime_rate_limit",
        "lifecycle": (
            "endpoint-isolated first-hit fixed windows; HMAC pseudonym only; "
            "integer counters with bounded PTTL"
        ),
        "evidence": (
            "RedisPersonalBankUserCountsReadRateLimiter + "
            "RedisPersonalBankUserCountsReadRateLimiterIT + "
            "LegacyPersonalBankUserCountsNetworkIT"
        ),
        "production_cutover": "false",
    }
    if rows != [expected_row]:
        raise ValueError("unexpected HTTP implementation ownership delta")

    effective_path = fixed_regular_file(OWNERSHIP_EFFECTIVE_RELATIVE)
    effective_document = load_json(effective_path)
    if effective_document.get("contract_id") != (
            "ti.phase4c.personal-bank-user-counts-http-"
            "effective-data-ownership-status"):
        raise ValueError("unexpected HTTP implementation ownership status id")
    if effective_document.get("schema_version") != 1:
        raise ValueError("unexpected HTTP implementation ownership schema")
    if effective_document.get("document_payload_sha256") != document_payload_sha256(
            effective_document):
        raise ValueError("invalid HTTP implementation ownership payload")
    if effective_document.get("predecessor") != {
        "source": "effective-data-ownership-status.json",
        "sha256": OWNERSHIP_PREDECESSOR_SHA256,
        "resource_count": 159,
        "canonical_owner_manifest_sha256": OWNERSHIP_PREDECESSOR_MANIFEST_SHA256,
        "immutable": True,
    }:
        raise ValueError("HTTP implementation ownership predecessor drifted")
    if effective_document.get("delta") != {
        "source": Path(OWNERSHIP_DELTA_RELATIVE).name,
        "sha256": sha256(delta_path),
        "new_resource_count": 1,
    }:
        raise ValueError("HTTP implementation ownership delta reference drifted")
    expected_resource = {
        "resource_kind": "redis_key",
        "resource_name": OWNERSHIP_RESOURCE_NAME,
        "owner": "learning",
        "persistence_role": "runtime_rate_limit",
        "business_fact": False,
        "production_cutover": False,
    }
    if effective_document.get("effective") != {
        "resource_count": 160,
        "resources_with_exactly_one_owner": 160,
        "canonical_owner_manifest_sha256": OWNERSHIP_EFFECTIVE_MANIFEST_SHA256,
        "new_resources": [expected_resource],
    }:
        raise ValueError("HTTP implementation effective ownership drifted")

    require_fragments(
        "server/src/main/java/io/saksk/ti/web/security/"
        "RedisPersonalBankUserCountsReadRateLimiter.java",
        (
            '"ti-java:learning:personal-bank-user-counts-read-rate:"',
            '"identity:v1"',
            '"ip:v1"',
            'prefix + ":second"',
            'prefix + ":hour"',
            'prefix + ":day"',
        ),
    )
    return {
        "predecessor": {
            **source_reference(OWNERSHIP_PREDECESSOR_RELATIVE),
            "resource_count": 159,
            "canonical_owner_manifest_sha256": (
                OWNERSHIP_PREDECESSOR_MANIFEST_SHA256
            ),
            "immutable": True,
        },
        "delta": {
            **source_reference(OWNERSHIP_DELTA_RELATIVE),
            "new_resource_count": 1,
        },
        "effective": {
            **source_reference(OWNERSHIP_EFFECTIVE_RELATIVE),
            "document_payload_sha256": effective_document[
                "document_payload_sha256"
            ],
            "resource_count": 160,
            "resources_with_exactly_one_owner": 160,
            "canonical_owner_manifest_sha256": (
                OWNERSHIP_EFFECTIVE_MANIFEST_SHA256
            ),
            "canonical_owner_manifest_recomputed": True,
            "new_resources": [expected_resource],
        },
    }


def validate_verification_evidence() -> dict:
    golden_path = fixed_regular_file(GOLDEN_RELATIVE)
    if sha256(golden_path) != GOLDEN_SHA256:
        raise ValueError("immutable 59-case Phase4B goldens drifted")
    golden = load_json(golden_path)
    if golden.get("case_count") != 59 or len(golden.get("cases", [])) != 59:
        raise ValueError("unexpected Phase4B golden case count")
    if golden.get("case_payload_sha256") != GOLDEN_CASE_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden case payload drifted")

    target = load_json(fixed_regular_file(GOLDEN_TARGET_RELATIVE))
    if target.get("evidence_id") != (
            "ti.phase4c.personal-bank-user-counts-golden-target-mapping-evidence"):
        raise ValueError("unexpected 59-case target evidence id")
    claim = target.get("claim", {})
    if claim.get("classification") != "PARTIAL_EXECUTION_MAPPING_LEDGER":
        raise ValueError("59-case target evidence classification drifted")
    if claim.get("full_target_parity_closed") is not False:
        raise ValueError("59-case target evidence overclaims full target parity")
    if claim.get("cutover_evidence") is not False:
        raise ValueError("59-case target evidence overclaims cutover evidence")
    if claim.get("route_migration_eligible") is not False:
        raise ValueError("59-case target evidence overclaims route migration eligibility")
    if target.get("source_golden") != {
        "path": GOLDEN_RELATIVE,
        "sha256": GOLDEN_SHA256,
        "case_payload_sha256": GOLDEN_CASE_PAYLOAD_SHA256,
        "case_count": 59,
    }:
        raise ValueError("59-case target evidence source binding drifted")
    expected_summary = {
        "case_count": 59,
        "mockmvc_case_count": 48,
        "bound_only_case_count": 11,
        "bound_authentication_case_count": 8,
        "bound_typed_database_case_count": 3,
    }
    if target.get("summary") != expected_summary or len(target.get("cases", [])) != 59:
        raise ValueError("59-case target evidence coverage drifted")
    golden_case_ids = [item.get("case_id") for item in golden.get("cases", [])]
    target_case_ids = [item.get("case_id") for item in target.get("cases", [])]
    if len(set(golden_case_ids)) != 59 or len(set(target_case_ids)) != 59:
        raise ValueError("59-case golden or mapping evidence has duplicate case ids")
    if target_case_ids != golden_case_ids:
        raise ValueError("59-case target evidence does not preserve the exact golden case set")
    allowed_http_differences = {
        f"P4C-LEARNING-{index:03d}" for index in range(7, 13)
    }
    expected_inherited_case_ids = [
        "access-shared-fetchone-first-row",
        "access-shared-cross-bank-record",
    ]
    inherited_case_ids = []
    for item in target["cases"]:
        differences = item.get("http_slice_difference_ids", [])
        if not isinstance(differences, list) or not set(differences).issubset(
                allowed_http_differences):
            raise ValueError(
                f"59-case mapping has an unapproved HTTP difference: {item.get('case_id')}"
            )
        if len(differences) != len(set(differences)):
            raise ValueError(
                f"59-case mapping repeats an HTTP difference: {item.get('case_id')}"
            )
        inherited = item.get("inherited_predecessor_difference_id")
        if inherited is not None and inherited != "P4C-LEARNING-006":
            raise ValueError(
                f"59-case mapping has an invalid inherited difference: {item.get('case_id')}"
            )
        if inherited is not None:
            inherited_case_ids.append(item.get("case_id"))
        if "P4C-LEARNING-006" in differences:
            raise ValueError(
                f"P4C-LEARNING-006 escaped inherited-only position: {item.get('case_id')}"
            )
    if inherited_case_ids != expected_inherited_case_ids:
        raise ValueError("P4C-LEARNING-006 inherited case set drifted")

    network = SOURCE_PATHS["network_it"]
    postgres = SOURCE_PATHS["postgres_it"]
    redis = SOURCE_PATHS["redis_it"]
    golden_test = SOURCE_PATHS["golden_target_test"]
    http_adapter_test = SOURCE_PATHS["http_adapter_security_test"]
    require_fragments(network, (
        "WebEnvironment.RANDOM_PORT",
        "HttpClient.newBuilder()",
        "realNetworkKeepsGetAndHeadStatusParityFor200302401403404And500",
        "realTomcatAndFirewallRejectEncodedSlashAndSemicolonsBeforeRouteSideEffects",
        "realNetworkOptionsTerminatesBeforeAuthenticationAndRateLimiting",
    ))
    require_fragments(postgres, (
        "POSTGRES_16",
        "POSTGRES_18",
        '"16.14"',
        '"18.4"',
        "servesRealControllerResponsesThroughReadOnlyJdbcOnPostgres16And18",
        "assertSqlFingerprint",
    ))
    require_fragments(redis, (
        "@Testcontainers",
        "realLuaUsesFirstHitTtlAndStopsBeforeEveryLongerWindowOnBreach",
        "independentClientsConvergeAtomicallyAndAliasesRemainIsolated",
    ))
    require_fragments(golden_test, (
        "executesOrTracksAllFiftyNineGoldenCases",
        "evidenceMapsTheExactGoldenSetWithoutPromotingTrackedCasesToParity",
        "assertThat(mockMvcCases).isEqualTo(48);",
    ))
    require_fragments(http_adapter_test, (
        "@WebMvcTest(",
        "excludeFilters = @ComponentScan.Filter(",
        "TargetSessionAuthenticationFilter.class",
        "TargetSessionReconciliationFilter.class",
    ))
    return {
        "real_network_tomcat": {
            **source_reference(network),
            "transport": "random-port Tomcat with java.net.http.HttpClient",
            "mock_mvc": False,
        },
        "postgresql_16_14_and_18_4": {
            **source_reference(postgres),
            "versions": ["16.14", "18.4"],
            "http_sql_fingerprint_parity": True,
            "read_only": True,
        },
        "redis_7": {
            **source_reference(redis),
            "real_lua": True,
            "atomic_concurrency_and_ttl": True,
            "alias_isolation": True,
        },
        "phase4b_59_case_mapping": {
            "golden": source_reference(GOLDEN_RELATIVE),
            "target_evidence": source_reference(GOLDEN_TARGET_RELATIVE),
            "test": source_reference(golden_test),
            "claim_classification": "PARTIAL_EXECUTION_MAPPING_LEDGER",
            "full_target_parity_closed": False,
            "cutover_evidence": False,
            "route_migration_eligible": False,
            "case_ids_sha256": sha256_json(golden_case_ids),
            "http_difference_ids": sorted(allowed_http_differences),
            "inherited_difference_id": "P4C-LEARNING-006",
            "inherited_case_ids": expected_inherited_case_ids,
            **expected_summary,
        },
        "http_adapter_security": {
            **source_reference(http_adapter_test),
            "mock_mvc": True,
            "full_authentication_filter_chain": False,
            "excluded_filters": [
                "TargetSessionAuthenticationFilter",
                "TargetSessionReconciliationFilter",
            ],
        },
        "openapi_and_route_contract": source_reference(
            SOURCE_PATHS["openapi_route_contract_test"]),
    }


def validate_worm(build_context_sha256: str) -> dict:
    # fixed_regular_file intentionally produces the fail-closed missing-WORM error.
    path = fixed_regular_file(WORM_RELATIVE)
    worm = load_json(path)
    if worm.get("schemaVersion") != 1:
        raise ValueError("unexpected HTTP implementation WORM schema version")
    if not worm.get("capturedAt"):
        raise ValueError("HTTP implementation WORM capture time is missing")
    source = worm.get("source", {})
    if source.get("legacySourceCommit") != "700006dfdfa063deb4387be572911e782bcea0d9":
        raise ValueError("HTTP implementation WORM legacy source drifted")
    read_role = worm.get("readRole", {})
    for field in (
        "selectPassed", "defaultTransactionReadOnly",
        "aclVerifiedWithReadOnlyDefaultDisabled", "insertRejected",
        "updateRejected", "deleteRejected", "ddlRejected", "temporaryDdlRejected",
    ):
        if read_role.get(field) is not True:
            raise ValueError(f"HTTP implementation WORM did not close read role: {field}")
    if read_role.get("temporaryPrivilege") is not False:
        raise ValueError("HTTP implementation WORM unexpectedly permits TEMP")
    java = worm.get("java", {})
    if java.get("buildContextSha256") != build_context_sha256:
        raise ValueError("HTTP implementation WORM does not bind current build context")
    if java.get("hibernateDdlAuto") != "validate":
        raise ValueError("HTTP implementation WORM does not preserve schema validation")
    if java.get("startupPassed") is not True or java.get("readinessPassed") is not True:
        raise ValueError("HTTP implementation WORM startup/readiness is not closed")
    if worm.get("flywayBaselineCreated") is not False:
        raise ValueError("HTTP implementation WORM overclaims a Flyway baseline")
    return {
        "source": WORM_RELATIVE,
        "sha256": sha256(path),
        "java_build_context_sha256": build_context_sha256,
        "read_role_closed": True,
        "hibernate_schema_mode": "validate",
        "production_schema_or_index_changed": False,
        "operator_migration_executed": False,
        "real_data_migration_executed": False,
        "production_cutover": False,
    }


def validate_phase2_fixed_chain(build_context_sha256: str) -> dict:
    dockerfile_sha256 = sha256(fixed_regular_file("server/Dockerfile"))
    accepted_report_sha256 = sha256(fixed_regular_file(WORM_RELATIVE))
    physical_build_context_sha256 = read_builder.java_build_context_sha256()
    if physical_build_context_sha256 == build_context_sha256:
        accepted_chain = phase2_worm.FIXED_EVIDENCE_CHAIN[:5]
        tip = phase2_worm.validate_evidence_chain(
            ROOT,
            fixed_regular_file("infra/phase2/reference-drift-manifest.json"),
            dockerfile_sha256,
            build_context_sha256,
            chain=accepted_chain,
            immutable_mirrors=phase2_worm.FIXED_IMMUTABLE_MIRRORS,
        )
        if tip.relative_path != WORM_RELATIVE or tip.sha256 != accepted_report_sha256:
            raise ValueError("Phase2 fixed WORM chain does not end at the HTTP checkpoint")
        if tip.predecessor_sha256 != phase2_worm.PHASE4C_READ_ACCESS_REPORT_SHA256:
            raise ValueError("Phase2 fixed WORM tip predecessor drifted")
        accepted_chain_node_count = len(accepted_chain)
    else:
        successor = tag_preflight_successor().validate_worm_successor(
            ROOT,
            accepted_report_sha256,
            build_context_sha256,
        )
        tip = phase2_worm.validate_fixed_chain(
            ROOT,
            fixed_regular_file("infra/phase2/reference-drift-manifest.json"),
            dockerfile_sha256,
            successor.current_build_context_sha256,
        )
        if (
            tip.sha256 != successor.current_report_sha256
            or tip.build_context_sha256 != successor.current_build_context_sha256
            or len(phase2_worm.FIXED_EVIDENCE_CHAIN)
            != successor.current_chain_node_count
        ):
            raise ValueError("Phase2 terminal WORM successor chain drifted")
        accepted_chain_node_count = successor.accepted_chain_node_count
    return {
        "node_count": accepted_chain_node_count,
        "tip_label": "phase4c-personal-bank-user-counts-http-implementation",
        "tip_sha256": accepted_report_sha256,
        "predecessor_sha256": phase2_worm.PHASE4C_READ_ACCESS_REPORT_SHA256,
        "dockerfile_sha256": dockerfile_sha256,
        "java_build_context_sha256": build_context_sha256,
    }


def build_contract() -> dict:
    predecessor, read = validate_predecessors()
    runtime = validate_runtime_transition(predecessor, read)
    route = validate_route_and_openapi()
    ownership = validate_data_ownership()
    verification = validate_verification_evidence()
    build_context = load_json(fixed_regular_file(WORM_RELATIVE))["java"][
        "buildContextSha256"
    ]
    fixed_worm_chain = validate_phase2_fixed_chain(build_context)
    worm = validate_worm(build_context)
    worm["fixed_phase2_chain"] = fixed_worm_chain

    source_contracts = {
        name: source_reference(relative)
        for name, relative in SOURCE_PATHS.items()
    }
    if set(source_contracts) != set(SOURCE_PATHS):
        raise ValueError("implementation source contract key drift")
    if len({item["source"] for item in source_contracts.values()}) != len(source_contracts):
        raise ValueError("duplicate implementation source references are forbidden")

    contract = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": "2026-07-18",
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "sha256": PREDECESSOR_SHA256,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "contract_id": PREDECESSOR_ID,
            "status": PREDECESSOR_STATUS,
            "immutable": True,
        },
        "source_contracts": dict(sorted(source_contracts.items())),
        "historical_successor_acceptance": {
            "predecessor_sha256": PREDECESSOR_SHA256,
            "http_entry_source_overrides": successor_source_overrides(
                HTTP_ENTRY_SOURCE_ACCEPTED_SHA256
            ),
            "read_terminal_source_overrides": successor_source_overrides(
                READ_TERMINAL_SOURCE_ACCEPTED_SHA256
            ),
            "successor_allowlist_exact": True,
            "predecessor_rewrite_forbidden": True,
            "arbitrary_source_hash_lookup_forbidden": True,
            "bridge_self_authorization_forbidden": True,
        },
        "implementation": {
            "production_runtime_transition": runtime,
            "java_build_context_sha256": build_context,
            "routes_and_openapi": route,
            "http_owner": "learning",
            "application_api": (
                "io.saksk.ti.learning.api.LearningApplicationApi"
                "#findPersonalBankUserCounts"
            ),
        },
        "data_ownership": ownership,
        "verification_evidence": verification,
        "worm_evidence": worm,
        "authorization": {
            "implementation_present": True,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "two_legacy_get_routes_migrated": False,
            "derived_head_and_options_count_as_migrated": False,
            "identity_api_or_global_auth_filter_change": False,
            "learning_or_personalbank_persistence_change": False,
            "production_schema_or_index": False,
            "operator_migration_implementation": False,
            "real_data_migration_execution": False,
            "migration_global_preflight_closed": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "production_cutover": False,
        },
        "acceptance": {
            "implementation_present": True,
            "predecessor_entry_contract_preserved": True,
            "exact_production_delta_verified": True,
            "learning_and_personalbank_sources_unchanged": True,
            "public_application_api_unchanged": True,
            "forbidden_main_sources_unchanged": True,
            "new_rate_limit_resource_has_one_learning_owner": True,
            "effective_resource_count": 160,
            "partial_network_postgres_redis_and_59_case_evidence_bound": True,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "implemented_pending_get_count": 2,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "operator_and_real_migration_remain_blocked": True,
            "next_gate": (
                "close_59_case_target_execution_and_full_authentication_chain_"
                "before_route_migration"
            ),
        },
    }
    contract["document_payload_sha256"] = sha256_json(contract)
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
