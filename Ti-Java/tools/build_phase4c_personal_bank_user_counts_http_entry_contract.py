#!/usr/bin/env python3
"""Build the Phase 4C personal-bank user-counts HTTP entry gate.

The generated document authorizes one future, exact HTTP implementation slice.
It deliberately does not claim that a controller, security matcher, OpenAPI
operation, migration operator, schema change, or production cutover exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from tools import build_phase4c_personal_bank_user_counts_read_contract as read_builder
except ModuleNotFoundError:  # Direct script execution from tools/.
    import build_phase4c_personal_bank_user_counts_read_contract as read_builder


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "docs/refactor/phase4c/personal-bank-user-counts-http-entry-contract.json"
)
CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-http-entry-contract"
CONTRACT_STATUS = "entry_gate_passed_http_implementation_not_started"
PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
PREDECESSOR_SHA256 = (
    "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5"
)
PREDECESSOR_ID = "ti.phase4c.personal-bank-user-counts-read-contract"
PREDECESSOR_STATUS = "implemented_and_targeted_verified_http_aliases_deferred"
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"

EXPECTED_MAIN_FILE_COUNT = 40
EXPECTED_MAIN_MANIFEST_SHA256 = (
    "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1"
)
EXPECTED_RUNTIME_FILE_COUNT = 288
EXPECTED_RUNTIME_MANIFEST_SHA256 = (
    "145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc"
)
EXPECTED_ROUTE_FILE_COUNT = 5
EXPECTED_ROUTE_MANIFEST_SHA256 = (
    "6f9cfdd6ba849233c51a27ed281856681d8a6ec3a0bda628da9184ec284e4b86"
)
EXPECTED_BUILD_CONTEXT_SHA256 = (
    "935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0"
)
WORM_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-access-worm-evidence.json"
)
WORM_SHA256 = (
    "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
)

PHASE4B_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json"
)
PHASE4B_ENTRY_SHA256 = (
    "1ec41fde1e17dd1f09a9aa737aadd9ada1f64c41f4e44f1df87dbf0613c30ee6"
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
CALLERS_RELATIVE = "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
CALLERS_SHA256 = (
    "bad7e19e44710f57841a2681f1b45bfcce85c67b46f1882d2f22f45da86961fc"
)
CALLERS_ATTESTATION_SHA256 = (
    "1b650434114f6824ae65e20bc2ead275e651853c026387ddd3461690009dc3fb"
)
CALLERS_DOCUMENT_PAYLOAD_SHA256 = (
    "0470c6d6a5daa33474f0c2b794cce7bebcbc86c763eec31f190864fd8d858669"
)

BOUNDARY_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-http-boundary-evidence.json"
)
BOUNDARY_SHA256 = (
    "bb08482f2628dccdf8e5a4fc7c1e669b28787f0c4309f5c65707d0a29e1867c9"
)
BOUNDARY_CASE_COUNT = 62
BOUNDARY_CASE_PAYLOAD_SHA256 = (
    "f577ff99a7f04030fd5f4dae0f95610351d4fcfff92de7e9ca0c406516725dbf"
)
BOUNDARY_DOCUMENT_PAYLOAD_SHA256 = (
    "3e8f7c24548d979723d2601c11221b9e569de7b342e6c3c0d8daa25de74cdd2f"
)
BOUNDARY_RUNTIME_ROUTE_MAP_SHA256 = (
    "1f95547d515cf881f2ae2a3e71fc957230845125371e299bcaa6ffb23b201925"
)
BOUNDARY_CORS_OBSERVATIONS_SHA256 = (
    "084b1dd3e2ea5df43d7a5faa6f640259daa468c32834b093adf3a98547bae8ca"
)
BOUNDARY_CAPTURE_TOOL_SHA256 = (
    "7d73d7973119f07cd013aaa02ff2306d3346e59b4fd182df84a95ec1db640e87"
)
BOUNDARY_CAPTURE_TEST_SHA256 = (
    "5d0c4add2dbb252d31b943602ef4745f103484e8cd71d0de60ab584ccbcf97b4"
)
RATE_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-rate-limit-evidence.json"
)
RATE_SHA256 = (
    "b0f08ddba54641e776df368ecb10361154a7434aee5d734c379a34d42538e66b"
)
RATE_DOCUMENT_PAYLOAD_SHA256 = (
    "13dc4604b83be5b46f6931f3bc513cdfb3ee2dd6503891973d8797715bad44fc"
)
RATE_RUNTIME_EVIDENCE_PAYLOAD_SHA256 = (
    "3300a3b3257bd1a8ae8e8fde4abdedf31dd481f510738ba25c2ac8661f3d5ba4"
)
RATE_CAPTURE_TOOL_SHA256 = (
    "8c3e88e1cbeb8b931cadcdc83c046c2cccb662ed514e29711895fcf92e771ddc"
)
RATE_CAPTURE_TEST_SHA256 = (
    "72ca166e97a5728b53ae435d5bddc73bcd7b5a4ee02544ed2ad56fd89ce581f7"
)
RATE_EVIDENCE_STATUS = (
    "fixed_legacy_observation_only_target_proposal_not_authorized"
)

# These are the only historical contract sources changed by this entry gate.
# Values are the hashes accepted by the immediately preceding fixed trust root,
# never hashes discovered from the current worktree.
READ_SOURCE_ACCEPTED_SHA256 = {
    "README.md": "685ffde5088acb7e6c1a8e7825d9d7549f0f0567faf7dadf74a6c045a4bd4832",
    "docs/refactor/05-progress.md": (
        "71407c0fd99d1b8f982ea4e108e1dc5e0d9d472584824fb7a8ade325be65f1c2"
    ),
    "docs/refactor/phase4c/README.md": (
        "1b685c0e61e9db4aeecf52595760f579bb8fad2b167dd9c8ca6646487d4b2101"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ): "8fec859106edd58364c04632afb978a2f7d7c36114e10d33157a60d1be17027d",
    "tools/phase4c_read_successor_acceptance.py": (
        "732a03f5a736079676259b302d90252e045444ef0d9986d619785d283553bbe3"
    ),
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "95adccd41a0bec4780f881adf845a6c65df67ec42b0d1925d81dbe4b971d8195"
    ),
    "docs/refactor/phase4c/approved-differences.md": (
        "c8081e7adc62f6119b00a7f91cf5354da649510e6b3bde547670a807e9a52586"
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "08e82154d66ab4a112091ee97b40bc1c155aae14a4bd9ca0b6afbb9032e71bdd"
    ),
}

CURRENT_GATE_SOURCES = {
    "contract_builder": (
        "tools/build_phase4c_personal_bank_user_counts_http_entry_contract.py"
    ),
    "contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py"
    ),
    "python_successor_bridge": "tools/phase4c_http_entry_successor_acceptance.py",
    "java_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpEntrySuccessorAcceptance.java"
    ),
    "historical_python_read_bridge": "tools/phase4c_read_successor_acceptance.py",
    "historical_java_read_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ),
    "historical_read_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_read_contract.py"
    ),
    "historical_composition_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_composition_contract.py"
    ),
    "boundary_capture_tool": (
        "tools/capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py"
    ),
    "boundary_capture_test": (
        "tools/test_capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py"
    ),
    "rate_capture_tool": (
        "tools/capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py"
    ),
    "rate_capture_test": (
        "tools/test_capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py"
    ),
    "approved_differences": "docs/refactor/phase4c/approved-differences.md",
    "phase4c_readme": "docs/refactor/phase4c/README.md",
    "project_readme": "README.md",
    "progress": "docs/refactor/05-progress.md",
    "phase3_authentication_differences": (
        "docs/refactor/phase3/approved-authentication-differences.md"
    ),
    "request_id": "server/src/main/java/io/saksk/ti/web/request/RequestId.java",
    "request_id_filter": (
        "server/src/main/java/io/saksk/ti/web/request/RequestIdFilter.java"
    ),
    "request_id_filter_test": (
        "server/src/test/java/io/saksk/ti/web/request/RequestIdFilterTest.java"
    ),
    "decimal_path_integer": (
        "server/src/main/java/io/saksk/ti/web/LegacyDecimalPathInteger.java"
    ),
    "security_baseline": (
        "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java"
    ),
    "rate_wiring_baseline": (
        "server/src/main/java/io/saksk/ti/web/security/LoginRateLimitConfiguration.java"
    ),
    "application_config_baseline": "server/src/main/resources/application.yml",
    "production_config_baseline": "server/src/main/resources/application-prod.yml",
}

FUTURE_NEW_MAIN_SOURCES = [
    (
        "server/src/main/java/io/saksk/ti/web/compat/"
        "LegacyPersonalBankUserCountsController.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/compat/"
        "LegacyPersonalBankUserCountsSecurityErrorWriter.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRequestResolver.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRateLimiter.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRateLimitProperties.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "RedisPersonalBankUserCountsReadRateLimiter.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsReadRateLimitFilter.java"
    ),
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "PersonalBankUserCountsCorsConfigurationSource.java"
    ),
]
FUTURE_CHANGED_MAIN_SOURCES = [
    "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java",
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "LoginRateLimitConfiguration.java"
    ),
]
FUTURE_CHANGED_RESOURCES = [
    "server/src/main/resources/application.yml",
    "server/src/main/resources/application-prod.yml",
    ".env.example",
    "compose.dev.yml",
]
FUTURE_OPENAPI_OVERLAY = (
    "openapi/phase4c-personal-bank-user-counts.openapi.json"
)

FORBIDDEN_FUTURE_MAIN_SOURCES = [
    "server/src/main/java/io/saksk/ti/identity/api/LegacyCredentialAuthenticationApi.java",
    (
        "server/src/main/java/io/saksk/ti/web/security/"
        "TargetSessionAuthenticationFilter.java"
    ),
    "server/src/main/java/io/saksk/ti/web/request/RequestId.java",
    "server/src/main/java/io/saksk/ti/web/request/RequestIdFilter.java",
    "server/src/main/java/io/saksk/ti/web/LegacyDecimalPathInteger.java",
    "server/src/main/java/io/saksk/ti/web/error/GlobalExceptionHandler.java",
    "server/src/main/java/io/saksk/ti/web/error/SafeErrorController.java",
]

ROUTES = [
    {
        "alias": "api",
        "route_id": "6858f6fa506f",
        "method": "GET",
        "legacy_path": "/api/user/banks/api/<int:bank_id>/user-counts",
        "target_path": "/api/user/banks/api/{bank_id}/user-counts",
        "http_owner": "learning",
        "migration_status": "pending",
        "production_cutover": False,
    },
    {
        "alias": "web",
        "route_id": "006913d0d956",
        "method": "GET",
        "legacy_path": "/user/banks/api/<int:bank_id>/user-counts",
        "target_path": "/user/banks/api/{bank_id}/user-counts",
        "http_owner": "learning",
        "migration_status": "pending",
        "production_cutover": False,
    },
]


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


def source_reference(relative: str) -> dict:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"required Phase4C HTTP entry source is missing: {relative}")
    return {"source": relative, "sha256": sha256(path)}


def exact_document(
        relative: str,
        *,
        contract_id: str,
        legacy_commit: str | None = None,
) -> dict:
    document = load_json(ROOT / relative)
    if document.get("contract_id") != contract_id:
        raise ValueError(f"unexpected contract id in {relative}")
    if document.get("schema_version") != 1:
        raise ValueError(f"unexpected schema version in {relative}")
    if legacy_commit is not None and document.get("legacy_commit") != legacy_commit:
        raise ValueError(f"unexpected legacy commit in {relative}")
    if document.get("document_payload_sha256") != document_payload_sha256(document):
        raise ValueError(f"invalid document payload hash in {relative}")
    return document


def successor_sources() -> dict[str, dict]:
    return {
        relative: {
            "source": relative,
            "accepted_sha256": accepted,
            "successor_sha256": sha256(ROOT / relative),
        }
        for relative, accepted in sorted(READ_SOURCE_ACCEPTED_SHA256.items())
    }


def validate_current_surface(predecessor: dict) -> dict:
    main = read_builder.main_source_manifest()
    runtime = read_builder.production_runtime_manifest()
    route = read_builder.route_status_manifest()
    build_context = read_builder.java_build_context_sha256()

    if len(main) != EXPECTED_MAIN_FILE_COUNT:
        raise ValueError("unexpected learning/personalbank main-source file count")
    if sha256_json(main) != EXPECTED_MAIN_MANIFEST_SHA256:
        raise ValueError("learning/personalbank main-source manifest drift")
    if main != predecessor["implementation"][
            "learning_and_personalbank_main_source_manifest"]:
        raise ValueError("HTTP entry gate changed the implemented read surface")
    if len(runtime) != EXPECTED_RUNTIME_FILE_COUNT:
        raise ValueError("unexpected production runtime file count")
    if sha256_json(runtime) != EXPECTED_RUNTIME_MANIFEST_SHA256:
        raise ValueError("production runtime surface drifted before HTTP implementation")
    if runtime != predecessor["implementation"]["production_runtime_surface"]["files"]:
        raise ValueError("HTTP entry gate changed the production runtime surface")
    if len(route) != EXPECTED_ROUTE_FILE_COUNT:
        raise ValueError("unexpected route status file count")
    if sha256_json(route) != EXPECTED_ROUTE_MANIFEST_SHA256:
        raise ValueError("route/OpenAPI status changed before HTTP implementation")
    if route != predecessor["implementation"]["route_status_surface"]["files"]:
        raise ValueError("HTTP entry gate changed predecessor route status")
    if build_context != EXPECTED_BUILD_CONTEXT_SHA256:
        raise ValueError("Java production build context drifted before HTTP implementation")
    if predecessor["implementation"]["public_application_methods"] != (
            read_builder.public_application_methods()):
        raise ValueError("the exact 27-method application surface drifted")
    return {
        "public_application_method_count": 27,
        "public_application_methods": predecessor["implementation"][
            "public_application_methods"],
        "learning_and_personalbank_main_source_file_count": len(main),
        "learning_and_personalbank_main_source_manifest_sha256": sha256_json(main),
        "production_runtime_file_count": len(runtime),
        "production_runtime_manifest_sha256": sha256_json(runtime),
        "route_status_file_count": len(route),
        "route_status_manifest_sha256": sha256_json(route),
        "java_build_context_sha256": build_context,
        "server_src_main_changed_by_gate": False,
        "production_resources_changed_by_gate": False,
        "openapi_or_contracts_changed_by_gate": False,
        "route_status_changed_by_gate": False,
    }


def evidence_summary() -> dict:
    if sha256(ROOT / PHASE4B_ENTRY_RELATIVE) != PHASE4B_ENTRY_SHA256:
        raise ValueError("immutable Phase4B entry contract drifted")
    if sha256(ROOT / GOLDEN_RELATIVE) != GOLDEN_SHA256:
        raise ValueError("immutable 59-case golden evidence drifted")
    if sha256(ROOT / CALLERS_RELATIVE) != CALLERS_SHA256:
        raise ValueError("immutable caller evidence drifted")
    if sha256(ROOT / BOUNDARY_RELATIVE) != BOUNDARY_SHA256:
        raise ValueError("fixed HTTP boundary evidence drifted")
    if sha256(ROOT / RATE_RELATIVE) != RATE_SHA256:
        raise ValueError("fixed rate-limit evidence drifted")
    golden = exact_document(
        GOLDEN_RELATIVE,
        contract_id="ti.phase4b.personal-bank-user-counts-read-goldens",
        legacy_commit=LEGACY_COMMIT,
    )
    callers = exact_document(
        CALLERS_RELATIVE,
        contract_id="ti.phase4b.personal-bank-user-counts-caller-attestation",
        legacy_commit=LEGACY_COMMIT,
    )
    boundary = exact_document(
        BOUNDARY_RELATIVE,
        contract_id="ti.phase4c.personal-bank-user-counts-http-boundary-evidence",
        legacy_commit=LEGACY_COMMIT,
    )
    rate = exact_document(
        RATE_RELATIVE,
        contract_id="ti.phase4c.personal-bank-user-counts-rate-limit-evidence",
        legacy_commit=LEGACY_COMMIT,
    )
    if golden.get("case_count") != 59:
        raise ValueError("unexpected Phase4B golden case count")
    if golden.get("case_payload_sha256") != GOLDEN_CASE_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden case payload drifted")
    if golden.get("document_payload_sha256") != GOLDEN_DOCUMENT_PAYLOAD_SHA256:
        raise ValueError("Phase4B golden document payload drifted")
    if callers.get("attestation_sha256") != CALLERS_ATTESTATION_SHA256:
        raise ValueError("caller attestation payload drifted")
    if callers.get("document_payload_sha256") != CALLERS_DOCUMENT_PAYLOAD_SHA256:
        raise ValueError("caller document payload drifted")

    coverage = boundary.get("coverage", {})
    if boundary.get("case_count") != BOUNDARY_CASE_COUNT:
        raise ValueError("HTTP boundary evidence case count drifted")
    if boundary.get("case_payload_sha256") != BOUNDARY_CASE_PAYLOAD_SHA256:
        raise ValueError("HTTP boundary case payload drifted")
    if boundary.get("document_payload_sha256") != (
            BOUNDARY_DOCUMENT_PAYLOAD_SHA256):
        raise ValueError("HTTP boundary document payload drifted")
    if boundary["runtime_route_map"].get("selected_rules_sha256") != (
            BOUNDARY_RUNTIME_ROUTE_MAP_SHA256):
        raise ValueError("HTTP boundary runtime route map drifted")
    boundary_hashes = boundary["provenance"]["hashes"]
    if boundary_hashes.get("cors_observations_sha256") != (
            BOUNDARY_CORS_OBSERVATIONS_SHA256):
        raise ValueError("HTTP boundary CORS observations drifted")
    if boundary["provenance"]["capture_tool"].get("sha256") != (
            BOUNDARY_CAPTURE_TOOL_SHA256):
        raise ValueError("HTTP boundary capture tool drifted")
    if boundary["provenance"]["capture_test"].get("sha256") != (
            BOUNDARY_CAPTURE_TEST_SHA256):
        raise ValueError("HTTP boundary capture test drifted")
    if set(coverage.get("methods", [])) != {"GET", "HEAD", "OPTIONS"}:
        raise ValueError("HTTP boundary evidence lost method coverage")
    if not coverage.get("cors"):
        raise ValueError("HTTP boundary evidence did not close CORS/preflight")
    if rate.get("status") != RATE_EVIDENCE_STATUS:
        raise ValueError("rate-limit evidence status drifted")
    if rate.get("document_payload_sha256") != RATE_DOCUMENT_PAYLOAD_SHA256:
        raise ValueError("rate-limit document payload drifted")
    if rate["legacy_source_facts"]["base_configuration"]["windows"] != [
        {"count": 10, "unit": "second"},
        {"count": 500, "unit": "hour"},
        {"count": 5000, "unit": "day"},
    ]:
        raise ValueError("legacy base rate windows drifted")
    production = rate["legacy_source_facts"]["production_configuration"]
    if production.get("default_multiplier") != 100:
        raise ValueError("legacy production rate multiplier drifted")
    if production.get("default_effective_value") != (
            "500000/day;50000/hour;1000/second"):
        raise ValueError("legacy production effective rate limits drifted")
    rate_hashes = rate["provenance"]["hashes"]
    if rate_hashes.get("runtime_evidence_payload_sha256") != (
            RATE_RUNTIME_EVIDENCE_PAYLOAD_SHA256):
        raise ValueError("rate runtime evidence payload drifted")
    if rate["provenance"]["capture_tool"].get("sha256") != (
            RATE_CAPTURE_TOOL_SHA256):
        raise ValueError("rate capture tool drifted")
    if rate["provenance"]["capture_test"].get("sha256") != (
            RATE_CAPTURE_TEST_SHA256):
        raise ValueError("rate capture test drifted")

    return {
        "legacy_commit": LEGACY_COMMIT,
        "phase4b_entry": {
            "source": PHASE4B_ENTRY_RELATIVE,
            "sha256": PHASE4B_ENTRY_SHA256,
        },
        "callers": {
            "source": CALLERS_RELATIVE,
            "sha256": CALLERS_SHA256,
            "attestation_sha256": CALLERS_ATTESTATION_SHA256,
            "document_payload_sha256": CALLERS_DOCUMENT_PAYLOAD_SHA256,
            "repository_match_count": callers["full_repository_scan"]["match_count"],
            "matched_source_count": callers["full_repository_scan"][
                "matched_source_count"],
            "closed": callers["closure"]["caller_attestation_complete"],
        },
        "phase4b_goldens": {
            "source": GOLDEN_RELATIVE,
            "sha256": GOLDEN_SHA256,
            "case_count": golden["case_count"],
            "case_payload_sha256": golden["case_payload_sha256"],
            "document_payload_sha256": golden["document_payload_sha256"],
        },
        "http_boundary": {
            "source": BOUNDARY_RELATIVE,
            "sha256": BOUNDARY_SHA256,
            "case_count": boundary["case_count"],
            "case_payload_sha256": boundary["case_payload_sha256"],
            "document_payload_sha256": boundary["document_payload_sha256"],
            "runtime_route_map_sha256": boundary["runtime_route_map"][
                "selected_rules_sha256"],
            "complete_app_archive_sha256": boundary["legacy_source_attestation"]
                ["complete_app_archive"]["archive_sha256"],
            "capture_tool_sha256": boundary["provenance"]["capture_tool"]["sha256"],
            "capture_test_sha256": boundary["provenance"]["capture_test"]["sha256"],
            "cors_runtime_covered": True,
        },
        "rate_limit": {
            "source": RATE_RELATIVE,
            "sha256": RATE_SHA256,
            "document_payload_sha256": rate["document_payload_sha256"],
            "runtime_evidence_payload_sha256": rate["provenance"]["hashes"]
                ["runtime_evidence_payload_sha256"],
            "capture_tool_sha256": rate["provenance"]["capture_tool"]["sha256"],
            "capture_test_sha256": rate["provenance"]["capture_test"]["sha256"],
            "base_windows": rate["legacy_source_facts"]["base_configuration"]
                ["windows"],
            "production_default_multiplier": production["default_multiplier"],
            "production_default_effective_value": production[
                "default_effective_value"],
            "alias_buckets": rate["legacy_runtime_observations"]
                ["scope_identity_and_negotiation"]["alias_buckets"]["result"],
            "redis_connection_refusal_status": rate["legacy_runtime_observations"]
                ["redis_storage_failure"]["response"]["status"],
        },
    }


def target_http_contract() -> dict:
    return {
        "ownership": {
            "http_owner": "learning",
            "application_api": (
                "io.saksk.ti.learning.api.LearningApplicationApi"
                "#findPersonalBankUserCounts"
            ),
            "viewer_source": "authoritative authenticated principal only",
            "client_supplied_viewer_id_forbidden": True,
            "cross_module_direction": "learning -> personalbank::api",
        },
        "authentication": {
            "api_alias": [
                "authoritative target Session",
                "successfully exchanged legacy Flask Session",
                "valid legacy Bearer for this request only",
            ],
            "web_alias": [
                "authoritative target Session",
                "successfully exchanged legacy Flask Session",
            ],
            "explicit_authorization_selects_bearer": True,
            "cookie_fallback_after_authorization_forbidden": True,
            "web_any_authorization_result": "302 Location /login",
            "api_rejected_bearer_or_anonymous": {
                "status": 401,
                "body": {
                    "status": "unauthorized",
                    "message": "请先登录",
                    "status_code": 401,
                    "request_id": "<request-id>",
                },
            },
            "enumeration_resistant_rejections": [
                "anonymous",
                "malformed or duplicate Authorization",
                "invalid signature",
                "expired token",
                "stale session_version",
                "revoked, missing, or locked identity",
            ],
            "inherited_difference": "P3-AUTH-006",
            "stable_difference": "P4C-LEARNING-007",
            "email_bind_required_parity_claimed": False,
        },
        "query_parameters": {
            "repeated_parameter_rule": "first value wins",
            "q_type": {
                "default": "",
                "normalization": "trim; case-insensitive all means no filter",
                "unknown": "essay",
            },
            "source": {
                "default": "all",
                "special_exact_lowercase_values": ["favorites", "mistakes"],
                "other": "all",
            },
            "tag": {
                "default": "",
                "bypass_only_exact_lowercase": "all",
                "other_nonempty": "normalized learning-owned tag filter",
            },
        },
        "application_result": {
            "available_status": 200,
            "available_body_fields_exact": [
                "status", "code", "data", "message", "request_id",
            ],
            "data_fields_exact": [
                "total", "favorites", "mistakes", "types",
                "shuffle_options_available",
            ],
            "count_domain": "signed JSON integer backed by Java long",
            "denied_status": 403,
            "denied_body": {
                "status": "error",
                "code": 403,
                "message": "无权访问此题库",
                "status_code": 403,
                "request_id": "<request-id>",
            },
            "denied_forbids_fields": ["data", "payload"],
            "terminal_denial": True,
            "permission_recheck_before_zero_or_tag_return": True,
            "optional_field_fail_soft_only_for_infrastructure_or_query_failure": True,
            "policy_sources": [
                "P4C-LEARNING-002", "P4C-LEARNING-005", "P4C-LEARNING-006",
            ],
        },
        "path": {
            "normalizer": "io.saksk.ti.web.LegacyDecimalPathInteger",
            "matches": "one nonempty segment consisting only of Unicode Nd code points",
            "leading_zero_and_unicode_nd": "normalize by numeric value",
            "percent_encoded_ascii_or_utf8_nd": (
                "strictly decode once, then apply the same Unicode Nd rule"
            ),
            "zero": {
                "status": 403,
                "authentication": True,
                "rate_limited": True,
                "application_called": False,
            },
            "application_domain": "1..2147483647",
            "above_integer_max": {
                "status": 500,
                "authentication": True,
                "rate_limited": True,
                "application_called": False,
                "business_sql": 0,
                "bounded_parse": "length and lexical comparison before integer conversion",
            },
            "converter_miss": {
                "examples": ["negative", "empty", "non-Nd", "extra segment"],
                "status": 404,
                "rate_limited": False,
                "application_called": False,
            },
            "encoded_slash_or_ambiguous_path": {
                "status": 400,
                "layer": "StrictHttpFirewall",
                "rate_limited": False,
                "application_called": False,
            },
            "semicolon_matrix": {
                "status": 400,
                "layer": "StrictHttpFirewall",
                "rate_limited": False,
                "application_called": False,
            },
            "stable_difference": "P4C-LEARNING-011",
        },
        "methods": {
            "get": "authenticate, rate limit, invoke learning application API",
            "head": {
                "same_status_auth_rate_application_and_sql_as_get": True,
                "body_bytes_for_every_status": 0,
                "stable_difference": "P4C-LEARNING-012",
            },
            "bare_options": {
                "status": 204,
                "body_bytes": 0,
                "allow": ["GET", "HEAD", "OPTIONS"],
                "authentication": False,
                "rate_limited": False,
                "session_mutation": False,
                "application_called": False,
                "sql": 0,
            },
        },
        "cors": {
            "scope": "API alias only",
            "web_alias_acao": False,
            "allowed_origin_sources": [
                "https://servicewechat.com",
                "explicit configured origins",
                "development-profile localhost/127.0.0.1 ports 5000 and 3000",
            ],
            "wildcard_origin": False,
            "credentials": False,
            "allowed_methods": ["GET", "HEAD", "OPTIONS"],
            "allowed_headers": ["Content-Type", "Authorization", "X-Request-ID"],
            "allowed_simple_api_request": (
                "continue to authentication, rate limit, and the application path"
            ),
            "disallowed_simple_api_request": {
                "status": 403,
                "body_bytes": 0,
                "access_control_allow_origin": False,
                "authentication": False,
                "rate_limited": False,
                "session_mutation": False,
                "application_called": False,
                "sql": 0,
            },
            "valid_preflight": {
                "status": 204,
                "body_bytes": 0,
                "authentication": False,
                "rate_limited": False,
                "session_mutation": False,
                "application_called": False,
                "sql": 0,
            },
            "invalid_preflight": {
                "status": 403,
                "body_bytes": 0,
                "access_control_allow_origin": False,
                "side_effects": 0,
            },
            "stable_difference": "P4C-LEARNING-010",
        },
        "rate_limit": {
            "algorithm": "atomic Redis fixed windows; stop after first breached window",
            "base_limits": {
                "per_second": 10,
                "per_hour": 500,
                "per_day": 5000,
            },
            "development_default_multiplier": 1,
            "production_default_multiplier": 100,
            "production_effective_defaults": {
                "per_second": 1000,
                "per_hour": 50000,
                "per_day": 500000,
            },
            "deployment_override": "route-specific override then TI_RATE_LIMIT_MULTIPLIER",
            "alias_buckets": "independent",
            "actor": (
                "authoritative effective TargetAuthenticatedPrincipal; "
                "trusted client address fallback for rejected credentials"
            ),
            "raw_identity_or_address_in_redis": False,
            "keying": "domain-separated HMAC-SHA-256 pseudonym",
            "response_headers": [
                "X-RateLimit-Limit", "X-RateLimit-Remaining",
                "X-RateLimit-Reset", "Retry-After",
            ],
            "rate_limited_status": 429,
            "rate_limited_body_fields_exact": [
                "status", "message", "payload", "status_code", "request_id",
            ],
            "rate_limited_payload": None,
            "storage_failure": {
                "status": 503,
                "fail_closed": True,
                "rate_headers": False,
                "internal_details": False,
            },
            "stable_difference": "P4C-LEARNING-009",
        },
        "failure_negotiation": {
            "api_500": {
                "content_type": "application/json",
                "body": {
                    "status": "error",
                    "message": "An unexpected server error occurred.",
                    "payload": None,
                    "status_code": 500,
                    "request_id": "<request-id>",
                },
            },
            "web_500_default_html": (
                "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>"
            ),
            "web_500_json_when_raw_accept_starts_with": "application/json",
            "global_exception_handler_changes_forbidden": True,
        },
        "request_id": {
            "source": "io.saksk.ti.web.request.RequestId#from",
            "client_header_validation_owned_by_existing_filter": True,
            "body_and_response_header_must_match": True,
        },
        "identity_activity": {
            "users_last_active_dml": 0,
            "methods": ["GET", "HEAD", "OPTIONS"],
            "allowed_runtime_effects": [
                "authoritative Session registry/cookie reconciliation",
                "successful legacy Flask Session exchange",
            ],
            "stable_difference": "P4C-LEARNING-008",
        },
        "headers": {
            "security": [
                "X-Content-Type-Options: nosniff",
                "X-Frame-Options: SAMEORIGIN",
                "Referrer-Policy: strict-origin-when-cross-origin",
            ],
            "api_vary_tokens": ["Origin", "Cookie"],
            "web_vary_tokens": ["Cookie"],
            "vary_tokens_must_be_merged": True,
        },
    }


def build_contract() -> dict:
    predecessor_path = ROOT / PREDECESSOR_RELATIVE
    if sha256(predecessor_path) != PREDECESSOR_SHA256:
        raise ValueError("Phase4C read predecessor is not byte-for-byte immutable")
    predecessor = load_json(predecessor_path)
    if predecessor.get("contract_id") != PREDECESSOR_ID:
        raise ValueError("unexpected Phase4C read predecessor id")
    if predecessor.get("status") != PREDECESSOR_STATUS:
        raise ValueError("unexpected Phase4C read predecessor status")
    if predecessor.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("Phase4C read predecessor payload drifted")
    if document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise ValueError("Phase4C read predecessor payload is invalid")

    current_surface = validate_current_surface(predecessor)
    evidence = evidence_summary()
    worm_path = ROOT / WORM_RELATIVE
    if sha256(worm_path) != WORM_SHA256:
        raise ValueError("existing Phase4C WORM tip drifted")
    worm = load_json(worm_path)
    if worm["java"]["buildContextSha256"] != EXPECTED_BUILD_CONTEXT_SHA256:
        raise ValueError("existing WORM tip does not bind the current production context")

    source_contracts = {
        "predecessor": source_reference(PREDECESSOR_RELATIVE),
        "phase4b_entry": source_reference(PHASE4B_ENTRY_RELATIVE),
        "phase4b_goldens": source_reference(GOLDEN_RELATIVE),
        "phase4b_callers": source_reference(CALLERS_RELATIVE),
        "http_boundary_evidence": source_reference(BOUNDARY_RELATIVE),
        "rate_limit_evidence": source_reference(RATE_RELATIVE),
        "worm_tip": source_reference(WORM_RELATIVE),
        **{
            name: source_reference(relative)
            for name, relative in CURRENT_GATE_SOURCES.items()
        },
    }
    if len(source_contracts) != len(set(
            reference["source"] for reference in source_contracts.values())):
        raise ValueError("duplicate HTTP entry source references are forbidden")

    authorization = {
        "current_http_implementation_started": False,
        "future_controller": True,
        "future_route_specific_security": True,
        "future_route_specific_rate_limit": True,
        "future_route_specific_cors": True,
        "future_route_and_openapi_delta": True,
        "future_required_configuration": True,
        "identity_api_or_global_auth_filter_change": False,
        "learning_or_personalbank_persistence_change": False,
        "production_schema_or_index": False,
        "operator_migration_implementation": False,
        "real_data_migration_execution": False,
        "migration_global_preflight_closed": False,
        "client_change": False,
        "gateway_or_proxy_change": False,
        "production_cutover": False,
    }

    contract = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "status": CONTRACT_STATUS,
        "scope": "phase4c-personal-bank-user-counts-http-entry-gate",
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
            "read_source_overrides": successor_sources(),
            "successor_allowlist_exact": True,
            "arbitrary_source_hash_lookup_forbidden": True,
            "bridge_self_authorization_forbidden": True,
        },
        "current_state": {
            "implementation_started": False,
            "controller_present": False,
            "route_security_present": False,
            "route_rate_limiter_present": False,
            "route_cors_present": False,
            "openapi_overlay_present": False,
            "current_production_surface": current_surface,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "routes": ROUTES,
        },
        "evidence": evidence,
        "stable_differences": [
            "P3-AUTH-006",
            "P4C-LEARNING-001", "P4C-LEARNING-002", "P4C-LEARNING-003",
            "P4C-LEARNING-004", "P4C-LEARNING-005", "P4C-LEARNING-006",
            "P4C-LEARNING-007", "P4C-LEARNING-008", "P4C-LEARNING-009",
            "P4C-LEARNING-010", "P4C-LEARNING-011", "P4C-LEARNING-012",
        ],
        "target_http_contract": target_http_contract(),
        "authorization": authorization,
        "authorized_future_slice": {
            "implementation_started": False,
            "new_main_sources_exact": FUTURE_NEW_MAIN_SOURCES,
            "changed_main_sources_exact": FUTURE_CHANGED_MAIN_SOURCES,
            "changed_resources_exact": FUTURE_CHANGED_RESOURCES,
            "new_openapi_overlay_exact": FUTURE_OPENAPI_OVERLAY,
            "required_route_delta_rows": 2,
            "future_migrated_operation_count": 13,
            "future_pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "forbidden_main_sources": FORBIDDEN_FUTURE_MAIN_SOURCES,
            "required_test_families": [
                "request resolver and Unicode/path boundary unit tests",
                "full filter-chain authentication and authorization tests",
                "route-scoped CORS and response-header tests",
                "GET/HEAD/OPTIONS method and zero-body tests",
                "three-window limiter unit, Redis integration, concurrency and TTL tests",
                "controller envelope, negotiation and terminal-denial tests",
                "PostgreSQL 16.14 and 18.4 HTTP/query/fingerprint integration tests",
                "OpenAPI overlay and generated contract tests",
                "59-case golden parity with only approved differences",
                "production manifest, route status, WORM and build-context gates",
            ],
        },
        "worm_evidence": {
            "source": WORM_RELATIVE,
            "sha256": WORM_SHA256,
            "java_build_context_sha256": EXPECTED_BUILD_CONTEXT_SHA256,
            "new_worm_required_for_current_gate": False,
            "new_worm_required_after_future_production_change": True,
        },
        "acceptance": {
            "entry_evidence_closed": True,
            "current_http_implementation_started": False,
            "future_exact_http_slice_authorized": True,
            "routes_remain_pending": True,
            "operator_and_real_migration_remain_blocked": True,
            "production_cutover": False,
            "next_gate": (
                "implement_and_verify_exact_http_slice_without_operator_or_cutover"
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
