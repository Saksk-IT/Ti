#!/usr/bin/env python3
"""Fixed trust root admitting the Phase 4C user-counts HTTP entry successor.

This module is intentionally independent of both Phase4C builders and the
historical read bridge.  The dependency direction is one way:
``phase4c_read_successor_acceptance -> this module``.  The new contract may
record this bridge as provenance, but the bridge never uses that record to
authorize itself and never performs an arbitrary source-contract lookup.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from tools.phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as implementation_accepted_sha256,
        successor_sha256 as implementation_successor_sha256,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as implementation_accepted_sha256,
        successor_sha256 as implementation_successor_sha256,
    )


CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-http-entry-contract"
CONTRACT_STATUS = "entry_gate_passed_http_implementation_not_started"
CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-http-entry-contract.json"
)
PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
PREDECESSOR_ID = "ti.phase4c.personal-bank-user-counts-read-contract"
PREDECESSOR_STATUS = "implemented_and_targeted_verified_http_aliases_deferred"
PREDECESSOR_SHA256 = (
    "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5"
)
EXPECTED_MAIN_MANIFEST_SHA256 = (
    "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1"
)
EXPECTED_RUNTIME_MANIFEST_SHA256 = (
    "145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc"
)
EXPECTED_ROUTE_MANIFEST_SHA256 = (
    "6f9cfdd6ba849233c51a27ed281856681d8a6ec3a0bda628da9184ec284e4b86"
)
EXPECTED_BUILD_CONTEXT_SHA256 = (
    "935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0"
)
TRUST_PAYLOAD_SHA256 = (
    "6301db3499e9d166048c678d8851da00e62e6ce56f331b3c5f1af15aa7c5cfc6"
)
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"
BRIDGE_SOURCE_KEYS = {
    "python_successor_bridge",
    "java_successor_bridge",
}
SOURCE_PATHS = {
    "application_config_baseline": "server/src/main/resources/application.yml",
    "approved_differences": "docs/refactor/phase4c/approved-differences.md",
    "boundary_capture_test": (
        "tools/test_capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py"
    ),
    "boundary_capture_tool": (
        "tools/capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py"
    ),
    "contract_builder": (
        "tools/build_phase4c_personal_bank_user_counts_http_entry_contract.py"
    ),
    "contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py"
    ),
    "decimal_path_integer": (
        "server/src/main/java/io/saksk/ti/web/LegacyDecimalPathInteger.java"
    ),
    "historical_composition_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_composition_contract.py"
    ),
    "historical_java_read_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ),
    "historical_python_read_bridge": "tools/phase4c_read_successor_acceptance.py",
    "historical_read_contract_test": (
        "tools/test_phase4c_personal_bank_user_counts_read_contract.py"
    ),
    "http_boundary_evidence": (
        "docs/refactor/phase4c/personal-bank-user-counts-http-boundary-evidence.json"
    ),
    "java_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpEntrySuccessorAcceptance.java"
    ),
    "phase3_authentication_differences": (
        "docs/refactor/phase3/approved-authentication-differences.md"
    ),
    "phase4b_callers": (
        "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
    ),
    "phase4b_entry": (
        "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json"
    ),
    "phase4b_goldens": (
        "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
    ),
    "phase4c_readme": "docs/refactor/phase4c/README.md",
    "predecessor": PREDECESSOR_RELATIVE,
    "production_config_baseline": (
        "server/src/main/resources/application-prod.yml"
    ),
    "progress": "docs/refactor/05-progress.md",
    "project_readme": "README.md",
    "python_successor_bridge": "tools/phase4c_http_entry_successor_acceptance.py",
    "rate_capture_test": (
        "tools/test_capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py"
    ),
    "rate_capture_tool": (
        "tools/capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py"
    ),
    "rate_limit_evidence": (
        "docs/refactor/phase4c/personal-bank-user-counts-rate-limit-evidence.json"
    ),
    "rate_wiring_baseline": (
        "server/src/main/java/io/saksk/ti/web/security/LoginRateLimitConfiguration.java"
    ),
    "request_id": "server/src/main/java/io/saksk/ti/web/request/RequestId.java",
    "request_id_filter": (
        "server/src/main/java/io/saksk/ti/web/request/RequestIdFilter.java"
    ),
    "request_id_filter_test": (
        "server/src/test/java/io/saksk/ti/web/request/RequestIdFilterTest.java"
    ),
    "security_baseline": (
        "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java"
    ),
    "worm_tip": (
        "docs/refactor/phase4c/personal-bank-user-counts-read-access-worm-evidence.json"
    ),
}

# Filled with exact reviewed hashes after all predecessor-source edits settle.
# This bridge is deliberately absent from the map: it cannot authorize itself.
SUCCESSOR_SOURCES: dict[str, dict[str, str]] = {
    "README.md": {
        "accepted_sha256": (
            "685ffde5088acb7e6c1a8e7825d9d7549f0f0567faf7dadf74a6c045a4bd4832"
        ),
        "successor_sha256": "3d18a7b86354b8cad4d54a76a9a3722435dd570b612a5a9e65ca9a4aed2864b6",
    },
    "docs/refactor/05-progress.md": {
        "accepted_sha256": (
            "71407c0fd99d1b8f982ea4e108e1dc5e0d9d472584824fb7a8ade325be65f1c2"
        ),
        "successor_sha256": "f44a6efdec4342f13ea1f28831bdca9b36b84f48e932bd4f1d257070af555c7e",
    },
    "docs/refactor/phase4c/README.md": {
        "accepted_sha256": (
            "1b685c0e61e9db4aeecf52595760f579bb8fad2b167dd9c8ca6646487d4b2101"
        ),
        "successor_sha256": "07852f793ed84c90212c5b52dedcf82ed9b52ce9b229e35c56c94eafea253a8b",
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ): {
        "accepted_sha256": (
            "8fec859106edd58364c04632afb978a2f7d7c36114e10d33157a60d1be17027d"
        ),
        "successor_sha256": "8a008483f70788ffc10158ae789b7b318e8478ad249514f0551d8b0361dcf52b",
    },
    "tools/phase4c_read_successor_acceptance.py": {
        "accepted_sha256": (
            "732a03f5a736079676259b302d90252e045444ef0d9986d619785d283553bbe3"
        ),
        "successor_sha256": "8b4a57393021a304640797cc64a7f4d44aad83ab6d57c50d81f8158aa9008f82",
    },
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": {
        "accepted_sha256": (
            "95adccd41a0bec4780f881adf845a6c65df67ec42b0d1925d81dbe4b971d8195"
        ),
        "successor_sha256": "6d493304cc01fcbc801b066700b98bb6b0a1750ee9e3d9ce03867ee6e92991cc",
    },
    "docs/refactor/phase4c/approved-differences.md": {
        "accepted_sha256": (
            "c8081e7adc62f6119b00a7f91cf5354da649510e6b3bde547670a807e9a52586"
        ),
        "successor_sha256": "921d6626ab11d59a9667e1942953807b0aa1a81c06c01094cc109312f9d6b300",
    },
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": {
        "accepted_sha256": (
            "08e82154d66ab4a112091ee97b40bc1c155aae14a4bd9ca0b6afbb9032e71bdd"
        ),
        "successor_sha256": "c08ff0263d0da2c4e08733685256d7946a316a06772b8959c3520cc7947aaa76",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_sha256(document: dict) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _trust_payload(document: dict) -> dict:
    """Return the exact reviewed payload without recursive bridge hashes.

    The two bridge files are provenance, not authority.  Replacing only their
    recorded physical hashes removes the otherwise unavoidable self/cross hash
    cycle while every source key/path and every other contract field remains
    part of the independent trust fingerprint.
    """
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    source_contracts = payload.get("source_contracts")
    if not isinstance(source_contracts, dict):
        raise AssertionError("HTTP entry source contracts are missing")
    normalized_sources: dict[str, dict] = {}
    for name, reference in source_contracts.items():
        if not isinstance(reference, dict):
            raise AssertionError(f"invalid HTTP entry source reference: {name}")
        normalized = dict(reference)
        if name in BRIDGE_SOURCE_KEYS:
            normalized["sha256"] = BRIDGE_PROVENANCE_SENTINEL
        normalized_sources[name] = normalized
    return {**payload, "source_contracts": normalized_sources}


def _trust_payload_sha256(document: dict) -> str:
    return hashlib.sha256(
        _canonical_json(_trust_payload(document)).encode("utf-8")
    ).hexdigest()


def _fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    cursor = resolved_root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"HTTP entry successor path contains symlink: {relative}")
    try:
        resolved = (resolved_root / relative).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"HTTP entry successor path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(f"HTTP entry successor path is not a file: {relative}")
    return resolved


def _validated_terminal_sha256(
        root: Path,
        relative: str,
        accepted_sha256: str,
) -> str:
    physical_sha256 = _sha256(_fixed_regular_file(root, relative))
    if physical_sha256 == accepted_sha256:
        return physical_sha256
    if implementation_accepted_sha256(relative) != accepted_sha256:
        raise AssertionError(
            f"HTTP implementation did not accept exact HTTP entry source: {relative}"
        )
    successor_sha256 = implementation_successor_sha256(root, relative)
    if successor_sha256 != physical_sha256:
        raise AssertionError(
            f"HTTP implementation successor file hash drift for {relative}"
        )
    return physical_sha256


def _validate_source_contracts(root: Path, source_contracts: object) -> None:
    if not isinstance(source_contracts, dict):
        raise AssertionError("HTTP entry source contracts are missing")
    if set(source_contracts) != set(SOURCE_PATHS):
        raise AssertionError("unexpected HTTP entry source contract set")
    for name, relative in SOURCE_PATHS.items():
        reference = source_contracts.get(name)
        if not isinstance(reference, dict) or set(reference) != {"source", "sha256"}:
            raise AssertionError(f"unexpected HTTP entry source contract shape: {name}")
        if reference.get("source") != relative:
            raise AssertionError(f"fixed HTTP entry source path drift: {name}")
        _validated_terminal_sha256(root, relative, reference.get("sha256"))


def load_http_entry_successor_contract(ti_java_root: Path) -> dict | None:
    path = ti_java_root / CONTRACT_RELATIVE
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        contract = json.load(handle)
    validate_http_entry_successor_contract(contract, ti_java_root)
    return contract


def validate_http_entry_successor_contract(
        contract: dict,
        ti_java_root: Path,
) -> None:
    if contract.get("schema_version") != 1:
        raise AssertionError("unexpected Phase4C HTTP entry schema version")
    if contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("unexpected Phase4C HTTP entry contract id")
    if contract.get("status") != CONTRACT_STATUS:
        raise AssertionError("unexpected Phase4C HTTP entry contract status")
    if contract.get("scope") != "phase4c-personal-bank-user-counts-http-entry-gate":
        raise AssertionError("unexpected Phase4C HTTP entry scope")
    if contract.get("document_payload_sha256") != _payload_sha256(contract):
        raise AssertionError("invalid Phase4C HTTP entry document payload hash")

    predecessor = contract.get("predecessor", {})
    expected_predecessor = {
        "source": PREDECESSOR_RELATIVE,
        "sha256": PREDECESSOR_SHA256,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "immutable": True,
    }
    if predecessor != expected_predecessor:
        raise AssertionError("Phase4C read predecessor was not preserved exactly")
    root = ti_java_root.resolve(strict=True)
    predecessor_path = _fixed_regular_file(root, PREDECESSOR_RELATIVE)
    if _sha256(predecessor_path) != PREDECESSOR_SHA256:
        raise AssertionError("Phase4C read predecessor physical hash drifted")
    with predecessor_path.open("r", encoding="utf-8") as handle:
        predecessor_document = json.load(handle)
    if predecessor_document.get("contract_id") != PREDECESSOR_ID:
        raise AssertionError("unexpected physical Phase4C read predecessor id")
    if predecessor_document.get("status") != PREDECESSOR_STATUS:
        raise AssertionError("unexpected physical Phase4C read predecessor status")
    if predecessor_document.get("document_payload_sha256") != (
            PREDECESSOR_PAYLOAD_SHA256):
        raise AssertionError("Phase4C read predecessor payload field drifted")
    if _payload_sha256(predecessor_document) != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("Phase4C read predecessor payload is invalid")

    history = contract.get("historical_successor_acceptance", {})
    if history.get("predecessor_sha256") != PREDECESSOR_SHA256:
        raise AssertionError("unexpected HTTP entry historical predecessor hash")
    if not history.get("successor_allowlist_exact"):
        raise AssertionError("HTTP entry successor allowlist is not exact")
    if not history.get("arbitrary_source_hash_lookup_forbidden"):
        raise AssertionError("arbitrary HTTP entry successor lookup is not forbidden")
    if not history.get("bridge_self_authorization_forbidden"):
        raise AssertionError("HTTP entry successor bridge self-authorization is not forbidden")
    references = history.get("read_source_overrides", {})
    if set(references) != set(SUCCESSOR_SOURCES):
        raise AssertionError("unexpected HTTP entry successor source set")
    for relative, fixed in SUCCESSOR_SOURCES.items():
        if len(fixed["successor_sha256"]) != 64:
            raise AssertionError(f"unsettled HTTP successor hash for {relative}")
        reference = references.get(relative, {})
        if reference != {
            "source": relative,
            "accepted_sha256": fixed["accepted_sha256"],
            "successor_sha256": fixed["successor_sha256"],
        }:
            raise AssertionError(f"HTTP entry successor reference drift for {relative}")
        _validated_terminal_sha256(root, relative, fixed["successor_sha256"])

    current = contract.get("current_state", {})
    if current.get("implementation_started"):
        raise AssertionError("HTTP entry contract misrepresents implementation as started")
    for field in (
        "controller_present",
        "route_security_present",
        "route_rate_limiter_present",
        "route_cors_present",
        "openapi_overlay_present",
    ):
        if current.get(field):
            raise AssertionError(f"HTTP entry contract overclaims current {field}")
    surface = current.get("current_production_surface", {})
    expected_surface = {
        "public_application_method_count": 27,
        "learning_and_personalbank_main_source_file_count": 40,
        "learning_and_personalbank_main_source_manifest_sha256": (
            EXPECTED_MAIN_MANIFEST_SHA256),
        "production_runtime_file_count": 288,
        "production_runtime_manifest_sha256": EXPECTED_RUNTIME_MANIFEST_SHA256,
        "route_status_file_count": 5,
        "route_status_manifest_sha256": EXPECTED_ROUTE_MANIFEST_SHA256,
        "java_build_context_sha256": EXPECTED_BUILD_CONTEXT_SHA256,
    }
    for field, expected in expected_surface.items():
        if surface.get(field) != expected:
            raise AssertionError(f"unexpected HTTP entry current surface field: {field}")
    for field in (
        "server_src_main_changed_by_gate",
        "production_resources_changed_by_gate",
        "openapi_or_contracts_changed_by_gate",
        "route_status_changed_by_gate",
    ):
        if surface.get(field):
            raise AssertionError(f"HTTP entry gate changed production surface: {field}")
    if current.get("migrated_operation_count") != 11:
        raise AssertionError("unexpected migrated route count at HTTP entry")
    if current.get("pending_operation_count") != 600:
        raise AssertionError("unexpected pending route count at HTTP entry")
    if current.get("production_cutover_operation_count") != 0:
        raise AssertionError("HTTP entry contract overclaims production cutover")

    authorization = contract.get("authorization", {})
    for field in (
        "future_controller",
        "future_route_specific_security",
        "future_route_specific_rate_limit",
        "future_route_specific_cors",
        "future_route_and_openapi_delta",
        "future_required_configuration",
    ):
        if not authorization.get(field):
            raise AssertionError(f"HTTP entry did not authorize exact future field: {field}")
    for field in (
        "current_http_implementation_started",
        "identity_api_or_global_auth_filter_change",
        "learning_or_personalbank_persistence_change",
        "production_schema_or_index",
        "operator_migration_implementation",
        "real_data_migration_execution",
        "migration_global_preflight_closed",
        "client_change",
        "gateway_or_proxy_change",
        "production_cutover",
    ):
        if authorization.get(field):
            raise AssertionError(f"HTTP entry accidentally authorized forbidden field: {field}")
    acceptance = contract.get("acceptance", {})
    if not acceptance.get("entry_evidence_closed"):
        raise AssertionError("HTTP entry evidence is not closed")
    if acceptance.get("current_http_implementation_started"):
        raise AssertionError("HTTP entry acceptance overclaims implementation")
    if not acceptance.get("future_exact_http_slice_authorized"):
        raise AssertionError("HTTP entry did not authorize its exact future slice")
    if not acceptance.get("routes_remain_pending"):
        raise AssertionError("HTTP entry moved pending routes too early")
    if acceptance.get("production_cutover"):
        raise AssertionError("HTTP entry overclaims production cutover")

    if _trust_payload_sha256(contract) != TRUST_PAYLOAD_SHA256:
        raise AssertionError(
            "Phase4C HTTP entry independent trust payload drifted"
        )
    _validate_source_contracts(root, contract.get("source_contracts"))


def accepted_sha256(relative: str) -> str | None:
    fixed = SUCCESSOR_SOURCES.get(relative)
    return None if fixed is None else fixed["accepted_sha256"]


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    contract = load_http_entry_successor_contract(ti_java_root)
    if contract is None:
        return None
    fixed = SUCCESSOR_SOURCES.get(relative)
    if fixed is None:
        return None
    return _validated_terminal_sha256(
        ti_java_root.resolve(strict=True),
        relative,
        fixed["successor_sha256"],
    )
