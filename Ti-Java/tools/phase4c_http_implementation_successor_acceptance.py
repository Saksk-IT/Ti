#!/usr/bin/env python3
"""Historical implementation validator with a target-execution bootstrap handoff.

The bridge uses only fixed key-to-path maps.  Contract-provided paths are
never followed, and the bridge files are provenance rather than members of
the predecessor-source successor allowlist.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

try:
    from tools.phase4c_http_target_execution_successor_acceptance import (
        accepted_sha256 as _target_execution_accepted_sha256,
        successor_sha256 as _target_execution_successor_sha256,
    )
except ModuleNotFoundError as error:  # Direct execution from tools/.
    if error.name not in {
        "tools",
        "tools.phase4c_http_target_execution_successor_acceptance",
    }:
        raise
    from phase4c_http_target_execution_successor_acceptance import (
        accepted_sha256 as _target_execution_accepted_sha256,
        successor_sha256 as _target_execution_successor_sha256,
    )


def _tag_preflight_successor():
    try:
        from tools import (
            phase4c_tag_migration_global_preflight_successor_acceptance
            as successor,
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


CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-http-implementation-contract"
CONTRACT_STATUS = "implementation_present_parity_incomplete_routes_pending"
CONTRACT_SCOPE = "phase4c-personal-bank-user-counts-http-implementation"
CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-contract.json"
)
CONTRACT_SHA256 = (
    "c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd"
)
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
PREDECESSOR_RUNTIME_SHA256 = (
    "145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc"
)
LEARNING_PERSONALBANK_SHA256 = (
    "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1"
)
PUBLIC_APPLICATION_METHODS_SHA256 = (
    "c3b6b2eb984c1f910605bdf08c389484e5a675969c7e4ab71e5208c40d45530d"
)

# Filled only after the WORM, all source bytes, and the final contract settle.
# The two bridge provenance hashes are normalized before this digest is made.
TRUST_PAYLOAD_SHA256 = "624bb2b801a51e0fd19ae4d4583d77c6b6195355685b202b4c5ac3aa56d2cf8f"
BRIDGE_PROVENANCE_SENTINEL = "<bridge-self-provenance-sha256>"
BRIDGE_SOURCE_KEYS = frozenset({"python_successor_bridge", "java_successor_bridge"})

WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
GOLDEN_TARGET_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-mapping-evidence.json"
)
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

ADDED_RUNTIME_PATHS = frozenset({
    "openapi/phase4c-personal-bank-user-counts.openapi.json",
    "server/src/main/java/io/saksk/ti/web/compat/LegacyPersonalBankUserCountsController.java",
    "server/src/main/java/io/saksk/ti/web/compat/LegacyPersonalBankUserCountsSecurityErrorWriter.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsCorsConfigurationSource.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRateLimitFilter.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRateLimitProperties.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRateLimiter.java",
    "server/src/main/java/io/saksk/ti/web/security/PersonalBankUserCountsReadRequestResolver.java",
    "server/src/main/java/io/saksk/ti/web/security/RedisPersonalBankUserCountsReadRateLimiter.java",
})
CHANGED_RUNTIME_PATHS = frozenset({
    ".env.example",
    "compose.dev.yml",
    "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java",
    "server/src/main/java/io/saksk/ti/web/security/LoginRateLimitConfiguration.java",
    "server/src/main/resources/application-prod.yml",
    "server/src/main/resources/application.yml",
})
FORBIDDEN_MAIN_PATHS = frozenset({
    "server/src/main/java/io/saksk/ti/identity/api/LegacyCredentialAuthenticationApi.java",
    "server/src/main/java/io/saksk/ti/web/security/TargetSessionAuthenticationFilter.java",
    "server/src/main/java/io/saksk/ti/web/request/RequestId.java",
    "server/src/main/java/io/saksk/ti/web/request/RequestIdFilter.java",
    "server/src/main/java/io/saksk/ti/web/LegacyDecimalPathInteger.java",
    "server/src/main/java/io/saksk/ti/web/error/GlobalExceptionHandler.java",
    "server/src/main/java/io/saksk/ti/web/error/SafeErrorController.java",
})

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

READ_TERMINAL_SOURCE_ACCEPTED_SHA256 = {
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "590f4d62c45c4fc9fdde9332f2de376f62481b672120c72389071e4a8bf334a7"
    ),
}

# A later target-execution contract may advance only these exact bytes from
# this historical implementation checkpoint.  Keeping the set here prevents
# a future expansion of the target bridge from retroactively authorizing an
# arbitrary source in this older trust root.
TARGET_EXECUTION_SUCCESSOR_ALLOWLIST = frozenset({
    "README.md",
    "docs/refactor/05-progress.md",
    "docs/refactor/phase4c/README.md",
    "docs/refactor/phase4c/route-parity-delta.csv",
    "infra/phase2/README.md",
    "infra/phase2/verify-static.sh",
    "tools/phase2_wormhole_successor_acceptance.py",
    "tools/test_phase2_wormhole_successor_acceptance.py",
    "tools/phase4c_http_implementation_successor_acceptance.py",
    "tools/phase4c_read_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ),
})

SOURCE_PATHS = {
    "predecessor": PREDECESSOR_RELATIVE,
    "read_predecessor": READ_PREDECESSOR_RELATIVE,
    "read_contract_builder": READ_BUILDER_RELATIVE,
    "phase4b_goldens": (
        "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
    ),
    "http_boundary_evidence": (
        "docs/refactor/phase4c/personal-bank-user-counts-http-boundary-evidence.json"
    ),
    "rate_limit_evidence": (
        "docs/refactor/phase4c/personal-bank-user-counts-rate-limit-evidence.json"
    ),
    "golden_target_evidence": GOLDEN_TARGET_RELATIVE,
    "worm_tip": WORM_RELATIVE,
    "openapi_overlay": "openapi/phase4c-personal-bank-user-counts.openapi.json",
    "route_delta": "docs/refactor/phase4c/route-parity-delta.csv",
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _payload_sha256(document: dict) -> str:
    return _sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def _trust_payload_sha256(document: dict) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    sources = payload.get("source_contracts")
    if not isinstance(sources, dict):
        raise AssertionError("implementation source contracts are missing")
    normalized = {}
    for name, fixed_path in SOURCE_PATHS.items():
        reference = sources.get(name)
        if not isinstance(reference, dict):
            raise AssertionError(f"missing fixed implementation source: {name}")
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


def _fixed_path(root: Path, relative: str, *, regular_file: bool) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed implementation path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"fixed implementation path contains symlink: {relative}")
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(f"fixed implementation path escaped or vanished: {relative}") from error
    if regular_file and not resolved.is_file():
        raise AssertionError(f"fixed implementation path is not a file: {relative}")
    return resolved


def _fixed_regular_file(root: Path, relative: str) -> Path:
    return _fixed_path(root, relative, regular_file=True)


def _validated_current_sha256(
        root: Path,
        relative: str,
        fixed_sha256: str,
        *,
        label: str,
) -> str:
    """Resolve historical bytes through one exact downstream owner.

    Every code-fixed historical path must retain its anchored digest even when
    its physical bytes happen to equal a rewritten contract reference. Any
    target-allowlisted drift is owned exclusively by the target-execution
    bridge.  Only a non-target path may use NodeA, which must bind the exact
    declaration and current bytes. The historical contract is never used to
    authorize its own changed bridge bytes.
    """
    if not _is_sha256(fixed_sha256):
        raise AssertionError(f"invalid fixed SHA-256 for {label}: {relative}")
    physical = _sha256(_fixed_regular_file(root, relative))
    if relative in TARGET_EXECUTION_SUCCESSOR_ALLOWLIST:
        target_accepted = _target_execution_accepted_sha256(relative)
        if target_accepted != fixed_sha256:
            raise AssertionError(
                f"target successor accepted hash drift for {label}: {relative}"
            )
        if physical == fixed_sha256:
            return physical
        successor = _target_execution_successor_sha256(root, relative)
        if successor != physical:
            raise AssertionError(f"target successor hash drift for {label}: {relative}")
        return physical

    if physical == fixed_sha256:
        return physical
    nodea = _tag_preflight_successor()
    nodea_accepted = getattr(nodea, "accepted_sha256", None)
    nodea_successor = getattr(nodea, "successor_sha256", None)
    if not callable(nodea_accepted) or not callable(nodea_successor):
        raise AssertionError("tag-preflight successor API is incomplete")
    if nodea_accepted(relative) != fixed_sha256:
        raise AssertionError(
            f"tag-preflight successor does not accept {label}: {relative}"
        )
    if nodea_successor(root, relative) != physical:
        raise AssertionError(
            f"tag-preflight successor does not bind current {label}: {relative}"
        )
    return physical


def _add_manifest_path(root: Path, relative: str, manifest: dict[str, str]) -> None:
    path = _fixed_path(root, relative, regular_file=False)
    if path.is_file():
        manifest[relative] = _sha256(path)
        return
    if not path.is_dir():
        raise AssertionError(f"runtime manifest source is not file/directory: {relative}")
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise AssertionError(f"runtime manifest contains symlink: {child}")
        if child.is_file():
            key = child.relative_to(root).as_posix()
            manifest[key] = _sha256(child)


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


def _recompute_effective_owner_manifest(
        root: Path,
        predecessor: dict,
) -> list[dict]:
    phase4a_path = _fixed_regular_file(root, OWNERSHIP_PHASE4A_RELATIVE)
    if _sha256(phase4a_path) != OWNERSHIP_PHASE4A_SHA256:
        raise AssertionError("Phase4A ownership status physical hash drifted")
    if predecessor.get("predecessor") != {
        "source": "../phase4a/effective-data-ownership-status.json",
        "sha256": OWNERSHIP_PHASE4A_SHA256,
        "resource_count": 159,
        "immutable": True,
    }:
        raise AssertionError("Phase4C ownership predecessor link drifted")

    with phase4a_path.open(encoding="utf-8") as handle:
        phase4a = json.load(handle)
    if phase4a.get("contract_id") != "ti.phase4a.effective-data-ownership-status":
        raise AssertionError("unexpected Phase4A ownership status id")
    if phase4a.get("baseline") != {
        "source": "../03-data-ownership.csv",
        "sha256": OWNERSHIP_BASELINE_SHA256,
        "resource_count": 154,
        "immutable": True,
    }:
        raise AssertionError("Phase4A ownership baseline link drifted")
    phase4a_effective = phase4a.get("effective", {})
    if phase4a_effective.get("resource_count") != 159:
        raise AssertionError("unexpected Phase4A ownership resource count")
    if phase4a_effective.get("resources_with_exactly_one_owner") != 159:
        raise AssertionError("Phase4A ownership is not uniquely owned")

    baseline_path = _fixed_regular_file(root, OWNERSHIP_BASELINE_RELATIVE)
    if _sha256(baseline_path) != OWNERSHIP_BASELINE_SHA256:
        raise AssertionError("ownership baseline physical hash drifted")
    with baseline_path.open(encoding="utf-8", newline="") as handle:
        base_rows = list(csv.DictReader(handle))
    owners: dict[tuple[str, str], str] = {}
    for row in base_rows:
        key = (row.get("resource_kind", ""), row.get("resource_name", ""))
        owner = row.get("target_owner", "").strip()
        if not all(key) or not owner:
            raise AssertionError(f"invalid base ownership row: {key}")
        if key in owners:
            raise AssertionError(f"duplicate base ownership resource: {key}")
        owners[key] = owner
    if len(owners) != 154:
        raise AssertionError("unexpected ownership baseline resource count")

    phase4a_new = phase4a_effective.get("new_resources", [])
    if not isinstance(phase4a_new, list) or len(phase4a_new) != 5:
        raise AssertionError("unexpected Phase4A ownership additions")
    for resource in phase4a_new:
        key = (resource.get("resource_kind", ""), resource.get("resource_name", ""))
        owner = resource.get("owner", "").strip()
        if not all(key) or not owner:
            raise AssertionError(f"invalid Phase4A ownership resource: {key}")
        if key in owners:
            raise AssertionError(f"duplicate Phase4A ownership resource: {key}")
        owners[key] = owner
    if len(owners) != 159:
        raise AssertionError("Phase4A effective ownership count mismatch")

    expected_override = {
        "resource_kind": "db_kv_namespace",
        "resource_name": "bank_<bank_id>_tags",
        "base_owner": "personalbank",
        "owner": "learning",
        "production_cutover": False,
    }
    overrides = predecessor.get("effective", {}).get("owner_overrides", [])
    if overrides != [expected_override]:
        raise AssertionError("unexpected Phase4C ownership override")
    override_key = (
        expected_override["resource_kind"], expected_override["resource_name"]
    )
    if owners.get(override_key) != expected_override["base_owner"]:
        raise AssertionError("Phase4C ownership override base owner drifted")
    owners[override_key] = expected_override["owner"]
    predecessor_manifest = [
        {"resource_kind": key[0], "resource_name": key[1], "owner": owner}
        for key, owner in sorted(owners.items())
    ]
    if _sha256_json(predecessor_manifest) != OWNERSHIP_PREDECESSOR_MANIFEST_SHA256:
        raise AssertionError("recomputed Phase4C predecessor owner manifest drifted")

    new_key = ("redis_key", OWNERSHIP_RESOURCE_NAME)
    if new_key in owners:
        raise AssertionError("HTTP rate-limit ownership resource collides with predecessor")
    owners[new_key] = "learning"
    effective_manifest = [
        {"resource_kind": key[0], "resource_name": key[1], "owner": owner}
        for key, owner in sorted(owners.items())
    ]
    if len(effective_manifest) != 160:
        raise AssertionError("HTTP effective ownership count mismatch")
    if _sha256_json(effective_manifest) != OWNERSHIP_EFFECTIVE_MANIFEST_SHA256:
        raise AssertionError("recomputed HTTP effective owner manifest drifted")
    return effective_manifest


def _load_immutable_contract_envelope(
        ti_java_root: Path,
) -> tuple[Path, dict] | None:
    """Load the byte-fixed historical contract for scoped successor lookups."""
    root = ti_java_root.resolve(strict=True)
    path = root / CONTRACT_RELATIVE
    if not path.is_file():
        return None
    if not _is_sha256(TRUST_PAYLOAD_SHA256):
        raise AssertionError("unsettled HTTP implementation trust payload SHA-256")
    path = _fixed_regular_file(root, CONTRACT_RELATIVE)
    if _sha256(path) != CONTRACT_SHA256:
        raise AssertionError("HTTP implementation historical contract bytes drifted")
    with path.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract, dict):
        raise AssertionError("HTTP implementation historical contract is not an object")
    if contract.get("schema_version") != 1 or contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("HTTP implementation historical contract identity drifted")
    if contract.get("status") != CONTRACT_STATUS or contract.get("scope") != CONTRACT_SCOPE:
        raise AssertionError("HTTP implementation historical contract boundary drifted")
    if contract.get("document_payload_sha256") != _payload_sha256(contract):
        raise AssertionError("HTTP implementation historical contract payload is invalid")
    if _trust_payload_sha256(contract) != TRUST_PAYLOAD_SHA256:
        raise AssertionError("HTTP implementation historical contract trust drifted")
    return root, contract


def load_http_implementation_successor_contract(ti_java_root: Path) -> dict | None:
    loaded = _load_immutable_contract_envelope(ti_java_root)
    if loaded is None:
        return None
    root, contract = loaded
    validate_http_implementation_successor_contract(contract, root)
    return contract


def validate_http_implementation_successor_contract(
        contract: dict,
        ti_java_root: Path,
) -> None:
    root = ti_java_root.resolve(strict=True)
    if contract.get("schema_version") != 1:
        raise AssertionError("unexpected HTTP implementation schema version")
    if contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("unexpected HTTP implementation contract id")
    if contract.get("status") != CONTRACT_STATUS:
        raise AssertionError("unexpected HTTP implementation contract status")
    if contract.get("scope") != CONTRACT_SCOPE:
        raise AssertionError("unexpected HTTP implementation contract scope")
    if contract.get("document_payload_sha256") != _payload_sha256(contract):
        raise AssertionError("invalid HTTP implementation document payload hash")

    predecessor = contract.get("predecessor", {})
    if predecessor != {
        "source": PREDECESSOR_RELATIVE,
        "sha256": PREDECESSOR_SHA256,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "immutable": True,
    }:
        raise AssertionError("HTTP entry predecessor was not preserved exactly")
    predecessor_path = _fixed_regular_file(root, PREDECESSOR_RELATIVE)
    if _sha256(predecessor_path) != PREDECESSOR_SHA256:
        raise AssertionError("HTTP entry predecessor physical hash drifted")
    with predecessor_path.open(encoding="utf-8") as handle:
        predecessor_document = json.load(handle)
    if predecessor_document.get("document_payload_sha256") != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("HTTP entry predecessor payload field drifted")
    if _payload_sha256(predecessor_document) != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("HTTP entry predecessor payload is invalid")
    predecessor_source_references = predecessor_document.get("source_contracts", {})
    predecessor_source_hashes: dict[str, str] = {}
    for reference in predecessor_source_references.values():
        relative = reference.get("source")
        if relative in predecessor_source_hashes:
            raise AssertionError("HTTP entry predecessor has duplicate source paths")
        predecessor_source_hashes[relative] = reference.get("sha256")
    for relative, accepted in HTTP_ENTRY_SOURCE_ACCEPTED_SHA256.items():
        if predecessor_source_hashes.get(relative) != accepted:
            raise AssertionError(
                f"accepted hash is not fixed by HTTP entry predecessor: {relative}"
            )

    read_path = _fixed_regular_file(root, READ_PREDECESSOR_RELATIVE)
    if _sha256(read_path) != READ_PREDECESSOR_SHA256:
        raise AssertionError("read-runtime predecessor physical hash drifted")
    with read_path.open(encoding="utf-8") as handle:
        read_predecessor = json.load(handle)
    if read_predecessor.get("document_payload_sha256") != (
            READ_PREDECESSOR_PAYLOAD_SHA256):
        raise AssertionError("read-runtime predecessor payload field drifted")
    if _payload_sha256(read_predecessor) != READ_PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("read-runtime predecessor payload is invalid")
    if read_predecessor.get("source_contracts", {}).get("contract_builder") != {
        "source": READ_BUILDER_RELATIVE,
        "sha256": READ_BUILDER_SHA256,
    }:
        raise AssertionError("read predecessor no longer fixes its contract builder")
    if _sha256(_fixed_regular_file(root, READ_BUILDER_RELATIVE)) != READ_BUILDER_SHA256:
        raise AssertionError("read contract builder physical hash drifted")
    read_source_hashes: dict[str, str] = {}
    for reference in read_predecessor.get("source_contracts", {}).values():
        relative = reference.get("source")
        if relative in read_source_hashes:
            raise AssertionError("read predecessor has duplicate source paths")
        read_source_hashes[relative] = reference.get("sha256")
    for relative, accepted in READ_TERMINAL_SOURCE_ACCEPTED_SHA256.items():
        if read_source_hashes.get(relative) != accepted:
            raise AssertionError(
                f"accepted hash is not fixed by read predecessor: {relative}"
            )
    baseline_surface = read_predecessor.get("implementation", {}).get(
        "production_runtime_surface", {})
    baseline_files = baseline_surface.get("files", {})
    if baseline_surface.get("file_count") != 288:
        raise AssertionError("unexpected physical read-runtime predecessor count")
    if baseline_surface.get("manifest_sha256") != PREDECESSOR_RUNTIME_SHA256:
        raise AssertionError("physical read-runtime predecessor manifest drifted")
    if _sha256_json(baseline_files) != PREDECESSOR_RUNTIME_SHA256:
        raise AssertionError("invalid embedded read-runtime predecessor files")

    history = contract.get("historical_successor_acceptance", {})
    if history.get("predecessor_sha256") != PREDECESSOR_SHA256:
        raise AssertionError("unexpected HTTP implementation historical predecessor")
    for flag in (
        "successor_allowlist_exact",
        "predecessor_rewrite_forbidden",
        "arbitrary_source_hash_lookup_forbidden",
        "bridge_self_authorization_forbidden",
    ):
        if history.get(flag) is not True:
            raise AssertionError(f"HTTP implementation trust flag is not closed: {flag}")
    overrides = history.get("http_entry_source_overrides", {})
    if set(overrides) != set(HTTP_ENTRY_SOURCE_ACCEPTED_SHA256):
        raise AssertionError("unexpected HTTP implementation successor source set")
    for relative, accepted in HTTP_ENTRY_SOURCE_ACCEPTED_SHA256.items():
        reference = overrides.get(relative, {})
        successor = reference.get("successor_sha256")
        if reference.get("source") != relative:
            raise AssertionError(f"HTTP implementation successor path drift: {relative}")
        if reference.get("accepted_sha256") != accepted:
            raise AssertionError(f"HTTP implementation accepted hash drift: {relative}")
        if not _is_sha256(successor):
            raise AssertionError(f"unsettled HTTP implementation successor hash: {relative}")
        _validated_current_sha256(
            root,
            relative,
            successor,
            label="HTTP implementation historical successor",
        )

    read_overrides = history.get("read_terminal_source_overrides", {})
    if set(read_overrides) != set(READ_TERMINAL_SOURCE_ACCEPTED_SHA256):
        raise AssertionError("unexpected read-terminal implementation successor set")
    for relative, accepted in READ_TERMINAL_SOURCE_ACCEPTED_SHA256.items():
        reference = read_overrides.get(relative, {})
        successor = reference.get("successor_sha256")
        if reference.get("source") != relative:
            raise AssertionError(
                f"read-terminal implementation successor path drift: {relative}"
            )
        if reference.get("accepted_sha256") != accepted:
            raise AssertionError(
                f"read-terminal implementation accepted hash drift: {relative}"
            )
        if not _is_sha256(successor):
            raise AssertionError(
                f"unsettled read-terminal implementation successor hash: {relative}"
            )
        _validated_current_sha256(
            root,
            relative,
            successor,
            label="read-terminal implementation historical successor",
        )

    sources = contract.get("source_contracts", {})
    if set(sources) != set(SOURCE_PATHS):
        raise AssertionError("unexpected HTTP implementation source contract set")
    for name, relative in SOURCE_PATHS.items():
        reference = sources.get(name, {})
        if reference.get("source") != relative:
            raise AssertionError(f"fixed implementation source path drift: {name}")
        if set(reference) != {"source", "sha256"}:
            raise AssertionError(f"fixed implementation source shape drift: {name}")
        _validated_current_sha256(
            root,
            relative,
            reference.get("sha256"),
            label=f"fixed implementation source {name}",
        )

    implementation = contract.get("implementation", {})
    if implementation.get("http_owner") != "learning":
        raise AssertionError("HTTP implementation owner drifted")
    if implementation.get("application_api") != (
            "io.saksk.ti.learning.api.LearningApplicationApi"
            "#findPersonalBankUserCounts"):
        raise AssertionError("HTTP implementation application API drifted")
    transition = implementation.get("production_runtime_transition", {})
    old = transition.get("predecessor", {})
    if old != {
        "file_count": 288,
        "manifest_sha256": PREDECESSOR_RUNTIME_SHA256,
    }:
        raise AssertionError("unexpected HTTP implementation runtime predecessor")
    current = transition.get("current", {})
    physical_runtime = _production_runtime_manifest(root)
    if current.get("file_count") != 297:
        raise AssertionError("unexpected HTTP implementation runtime file count")
    accepted_runtime = current.get("files")
    if not isinstance(accepted_runtime, dict) or len(accepted_runtime) != 297:
        raise AssertionError("HTTP implementation runtime manifest is incomplete")
    if accepted_runtime != physical_runtime:
        successor = _validate_runtime_successor(
            root,
            accepted_runtime,
            physical_runtime,
            view="full_runtime",
        )
        if (
            successor.accepted_file_count != 297
            or successor.accepted_manifest_sha256 != _sha256_json(accepted_runtime)
            or successor.current_file_count != len(physical_runtime)
            or successor.current_manifest_sha256 != _sha256_json(physical_runtime)
            or successor.changed_files
            or successor.deleted_files
        ):
            raise AssertionError("tag preflight runtime successor descriptor drifted")
    if current.get("manifest_sha256") != _sha256_json(accepted_runtime):
        raise AssertionError("invalid HTTP implementation runtime manifest hash")

    delta = transition.get("exact_delta", {})
    if set(delta.get("added_files", {})) != ADDED_RUNTIME_PATHS:
        raise AssertionError("unexpected HTTP implementation added runtime paths")
    if set(delta.get("changed_files", {})) != CHANGED_RUNTIME_PATHS:
        raise AssertionError("unexpected HTTP implementation changed runtime paths")
    if delta.get("deleted_files") != [] or delta.get("deleted_file_count") != 0:
        raise AssertionError("HTTP implementation deleted predecessor runtime files")
    expected_counts = {
        "added_file_count": 9,
        "changed_file_count": 6,
        "new_main_source_count": 8,
        "new_openapi_file_count": 1,
        "changed_main_source_count": 2,
        "changed_configuration_file_count": 4,
    }
    for field, expected in expected_counts.items():
        if delta.get(field) != expected:
            raise AssertionError(f"HTTP implementation delta count drift: {field}")
    computed_added = {
        relative: accepted_runtime[relative]
        for relative in sorted(set(accepted_runtime) - set(baseline_files))
    }
    computed_changed = {
        relative: {
            "predecessor_sha256": baseline_files[relative],
            "successor_sha256": accepted_runtime[relative],
        }
        for relative in sorted(set(accepted_runtime) & set(baseline_files))
        if accepted_runtime[relative] != baseline_files[relative]
    }
    computed_deleted = sorted(set(baseline_files) - set(accepted_runtime))
    if delta.get("added_files") != computed_added:
        raise AssertionError("HTTP implementation added delta was not independently derived")
    if delta.get("changed_files") != computed_changed:
        raise AssertionError("HTTP implementation changed delta was not independently derived")
    if delta.get("deleted_files") != computed_deleted:
        raise AssertionError("HTTP implementation deleted delta was not independently derived")

    module_surface = transition.get("learning_and_personalbank", {})
    if module_surface.get("file_count") != 40:
        raise AssertionError("unexpected learning/personalbank source count")
    if module_surface.get("manifest_sha256") != LEARNING_PERSONALBANK_SHA256:
        raise AssertionError("learning/personalbank source manifest drifted")
    if module_surface.get("unchanged_from_read_predecessor") is not True:
        raise AssertionError("learning/personalbank source equality is not closed")
    if _sha256_json(module_surface.get("files", {})) != LEARNING_PERSONALBANK_SHA256:
        raise AssertionError("invalid embedded learning/personalbank source manifest")

    api = transition.get("public_application_api", {})
    if api.get("method_count") != 27:
        raise AssertionError("unexpected public application method count")
    if api.get("methods_sha256") != PUBLIC_APPLICATION_METHODS_SHA256:
        raise AssertionError("public application method manifest drifted")
    predecessor_methods = predecessor_document["current_state"][
        "current_production_surface"
    ]["public_application_methods"]
    if api.get("methods") != predecessor_methods:
        raise AssertionError("public application methods changed from HTTP entry")
    if api.get("unchanged_from_http_entry_predecessor") is not True:
        raise AssertionError("public application API equality is not closed")

    forbidden = transition.get("forbidden_main_sources", {})
    if forbidden.get("unchanged") is not True:
        raise AssertionError("forbidden main sources are not marked unchanged")
    if set(forbidden.get("files", {})) != FORBIDDEN_MAIN_PATHS:
        raise AssertionError("unexpected forbidden main source set")
    for relative, digest in forbidden["files"].items():
        if physical_runtime.get(relative) != digest:
            raise AssertionError(f"forbidden main source drifted: {relative}")

    route = implementation.get("routes_and_openapi", {})
    if route.get("implemented_pending_get_count") != 2:
        raise AssertionError("unexpected Phase4C implemented pending GET count")
    if route.get("migrated_operation_count") != 11:
        raise AssertionError("unexpected Phase4C migrated operation count")
    if route.get("pending_operation_count") != 600:
        raise AssertionError("unexpected Phase4C pending operation count")
    if route.get("route_migration_eligible") is not False:
        raise AssertionError("HTTP implementation overclaims route migration eligibility")
    if route.get("production_cutover_operation_count") != 0:
        raise AssertionError("HTTP implementation overclaims production cutover")
    routes = route.get("routes", [])
    if len(routes) != 2 or {item.get("route_id") for item in routes} != {
        "6858f6fa506f", "006913d0d956"
    }:
        raise AssertionError("HTTP implementation route set drifted")
    for item in routes:
        if item.get("method") != "GET" or item.get("target_module") != "learning":
            raise AssertionError("HTTP implementation route ownership drifted")
        if item.get("migration_status") != "pending":
            raise AssertionError("HTTP implementation route is not pending")
        if item.get("production_cutover") is not False:
            raise AssertionError("HTTP implementation route overclaims cutover")

    ownership = contract.get("data_ownership", {})
    ownership_predecessor = ownership.get("predecessor", {})
    if ownership_predecessor != {
        "source": OWNERSHIP_PREDECESSOR_RELATIVE,
        "sha256": OWNERSHIP_PREDECESSOR_SHA256,
        "resource_count": 159,
        "canonical_owner_manifest_sha256": (
            OWNERSHIP_PREDECESSOR_MANIFEST_SHA256
        ),
        "immutable": True,
    }:
        raise AssertionError("HTTP ownership predecessor drifted")
    predecessor_ownership_path = _fixed_regular_file(
        root, OWNERSHIP_PREDECESSOR_RELATIVE)
    if _sha256(predecessor_ownership_path) != OWNERSHIP_PREDECESSOR_SHA256:
        raise AssertionError("HTTP ownership predecessor physical hash drifted")
    with predecessor_ownership_path.open(encoding="utf-8") as handle:
        predecessor_ownership_document = json.load(handle)
    if predecessor_ownership_document.get(
            "document_payload_sha256") != _payload_sha256(
            predecessor_ownership_document):
        raise AssertionError("HTTP ownership predecessor payload is invalid")
    _recompute_effective_owner_manifest(root, predecessor_ownership_document)

    ownership_delta = ownership.get("delta", {})
    delta_path = _fixed_regular_file(root, OWNERSHIP_DELTA_RELATIVE)
    if ownership_delta != {
        "source": OWNERSHIP_DELTA_RELATIVE,
        "sha256": _sha256(delta_path),
        "new_resource_count": 1,
    }:
        raise AssertionError("HTTP ownership delta reference drifted")
    with delta_path.open(encoding="utf-8", newline="") as handle:
        ownership_rows = list(csv.DictReader(handle))
    if ownership_rows != [{
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
    }]:
        raise AssertionError("HTTP ownership delta content drifted")

    expected_owned_resource = {
        "resource_kind": "redis_key",
        "resource_name": OWNERSHIP_RESOURCE_NAME,
        "owner": "learning",
        "persistence_role": "runtime_rate_limit",
        "business_fact": False,
        "production_cutover": False,
    }
    effective_reference = ownership.get("effective", {})
    effective_path = _fixed_regular_file(root, OWNERSHIP_EFFECTIVE_RELATIVE)
    with effective_path.open(encoding="utf-8") as handle:
        effective_document = json.load(handle)
    expected_effective_reference = {
        "source": OWNERSHIP_EFFECTIVE_RELATIVE,
        "sha256": _sha256(effective_path),
        "document_payload_sha256": effective_document.get(
            "document_payload_sha256"),
        "resource_count": 160,
        "resources_with_exactly_one_owner": 160,
        "canonical_owner_manifest_sha256": (
            OWNERSHIP_EFFECTIVE_MANIFEST_SHA256
        ),
        "canonical_owner_manifest_recomputed": True,
        "new_resources": [expected_owned_resource],
    }
    if effective_reference != expected_effective_reference:
        raise AssertionError("HTTP effective ownership reference drifted")
    if effective_document.get("document_payload_sha256") != _payload_sha256(
            effective_document):
        raise AssertionError("HTTP effective ownership payload is invalid")
    if effective_document.get("predecessor") != {
        "source": "effective-data-ownership-status.json",
        "sha256": OWNERSHIP_PREDECESSOR_SHA256,
        "resource_count": 159,
        "canonical_owner_manifest_sha256": (
            OWNERSHIP_PREDECESSOR_MANIFEST_SHA256
        ),
        "immutable": True,
    }:
        raise AssertionError("HTTP effective ownership predecessor drifted")
    if effective_document.get("delta") != {
        "source": Path(OWNERSHIP_DELTA_RELATIVE).name,
        "sha256": _sha256(delta_path),
        "new_resource_count": 1,
    }:
        raise AssertionError("HTTP effective ownership delta drifted")
    if effective_document.get("effective") != {
        "resource_count": 160,
        "resources_with_exactly_one_owner": 160,
        "canonical_owner_manifest_sha256": (
            OWNERSHIP_EFFECTIVE_MANIFEST_SHA256
        ),
        "new_resources": [expected_owned_resource],
    }:
        raise AssertionError("HTTP effective ownership content drifted")

    evidence = contract.get("verification_evidence", {})
    if evidence.get("real_network_tomcat", {}).get("mock_mvc") is not False:
        raise AssertionError("real network evidence was replaced with MockMvc")
    if evidence.get("postgresql_16_14_and_18_4", {}).get("versions") != [
        "16.14", "18.4"
    ]:
        raise AssertionError("PostgreSQL compatibility evidence drifted")
    redis = evidence.get("redis_7", {})
    for field in ("real_lua", "atomic_concurrency_and_ttl", "alias_isolation"):
        if redis.get(field) is not True:
            raise AssertionError(f"Redis evidence is not closed: {field}")
    golden = evidence.get("phase4b_59_case_mapping", {})
    if golden.get("claim_classification") != "PARTIAL_EXECUTION_MAPPING_LEDGER":
        raise AssertionError("59-case mapping classification drifted")
    if golden.get("full_target_parity_closed") is not False:
        raise AssertionError("59-case mapping overclaims full target parity")
    if golden.get("cutover_evidence") is not False:
        raise AssertionError("59-case mapping overclaims cutover evidence")
    if golden.get("route_migration_eligible") is not False:
        raise AssertionError("59-case mapping overclaims route migration eligibility")
    if golden.get("inherited_difference_id") != "P4C-LEARNING-006":
        raise AssertionError("59-case inherited difference drifted")
    expected_inherited_cases = [
        "access-shared-fetchone-first-row",
        "access-shared-cross-bank-record",
    ]
    if golden.get("inherited_case_ids") != expected_inherited_cases:
        raise AssertionError("59-case inherited case set drifted")
    if golden.get("http_difference_ids") != [
        f"P4C-LEARNING-{index:03d}" for index in range(7, 13)
    ]:
        raise AssertionError("59-case HTTP difference domain drifted")
    expected_golden_counts = {
        "case_count": 59,
        "mockmvc_case_count": 48,
        "bound_only_case_count": 11,
        "bound_authentication_case_count": 8,
        "bound_typed_database_case_count": 3,
    }
    for field, expected in expected_golden_counts.items():
        if golden.get(field) != expected:
            raise AssertionError(f"59-case mapping evidence drift: {field}")
    with _fixed_regular_file(root, GOLDEN_TARGET_RELATIVE).open(encoding="utf-8") as handle:
        mapping_document = json.load(handle)
    with _fixed_regular_file(
            root,
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
    ).open(encoding="utf-8") as handle:
        golden_document = json.load(handle)
    if mapping_document.get("claim", {}).get("classification") != (
            "PARTIAL_EXECUTION_MAPPING_LEDGER"):
        raise AssertionError("physical 59-case mapping classification drifted")
    if mapping_document.get("claim", {}).get("full_target_parity_closed") is not False:
        raise AssertionError("physical 59-case mapping overclaims target parity")
    if mapping_document.get("claim", {}).get("cutover_evidence") is not False:
        raise AssertionError("physical 59-case mapping overclaims cutover evidence")
    if mapping_document.get("claim", {}).get("route_migration_eligible") is not False:
        raise AssertionError("physical 59-case mapping overclaims route migration eligibility")
    mapping_cases = mapping_document.get("cases", [])
    if [item.get("case_id") for item in mapping_cases] != [
            item.get("case_id") for item in golden_document.get("cases", [])]:
        raise AssertionError("physical 59-case mapping case ids drifted")
    inherited_cases = []
    allowed_http_differences = set(golden["http_difference_ids"])
    for item in mapping_cases:
        differences = item.get("http_slice_difference_ids", [])
        if len(differences) != len(set(differences)):
            raise AssertionError("physical 59-case mapping repeats an HTTP difference")
        if not set(differences).issubset(allowed_http_differences):
            raise AssertionError("physical 59-case mapping has an unapproved HTTP difference")
        if "P4C-LEARNING-006" in differences:
            raise AssertionError("P4C-LEARNING-006 escaped inherited-only position")
        inherited = item.get("inherited_predecessor_difference_id")
        if inherited is not None:
            if inherited != "P4C-LEARNING-006":
                raise AssertionError("physical 59-case inherited difference drifted")
            inherited_cases.append(item.get("case_id"))
    if inherited_cases != expected_inherited_cases:
        raise AssertionError("physical 59-case inherited case set drifted")

    adapter = evidence.get("http_adapter_security", {})
    if adapter.get("mock_mvc") is not True:
        raise AssertionError("HTTP adapter evidence must remain explicitly MockMvc")
    if adapter.get("full_authentication_filter_chain") is not False:
        raise AssertionError("HTTP adapter evidence overclaims the authentication chain")
    if adapter.get("excluded_filters") != [
        "TargetSessionAuthenticationFilter",
        "TargetSessionReconciliationFilter",
    ]:
        raise AssertionError("HTTP adapter excluded-filter evidence drifted")

    worm_reference = contract.get("worm_evidence", {})
    if worm_reference.get("source") != WORM_RELATIVE:
        raise AssertionError("unexpected HTTP implementation WORM path")
    worm_path = _fixed_regular_file(root, WORM_RELATIVE)
    if worm_reference.get("sha256") != _sha256(worm_path):
        raise AssertionError("HTTP implementation WORM hash drifted")
    with worm_path.open(encoding="utf-8") as handle:
        worm = json.load(handle)
    if worm.get("java", {}).get("buildContextSha256") != (
            implementation.get("java_build_context_sha256")):
        raise AssertionError("HTTP implementation WORM build context drifted")
    fixed_chain = worm_reference.get("fixed_phase2_chain", {})
    if fixed_chain.get("node_count") != 5:
        raise AssertionError("HTTP implementation fixed WORM chain length drifted")
    if fixed_chain.get("tip_label") != (
            "phase4c-personal-bank-user-counts-http-implementation"):
        raise AssertionError("HTTP implementation fixed WORM tip label drifted")
    if fixed_chain.get("tip_sha256") != worm_reference.get("sha256"):
        raise AssertionError("HTTP implementation fixed WORM tip digest drifted")
    if fixed_chain.get("predecessor_sha256") != (
            "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"):
        raise AssertionError("HTTP implementation fixed WORM predecessor drifted")
    if fixed_chain.get("dockerfile_sha256") != _sha256(
            _fixed_regular_file(root, "server/Dockerfile")):
        raise AssertionError("HTTP implementation fixed WORM Dockerfile drifted")
    if fixed_chain.get("java_build_context_sha256") != (
            implementation.get("java_build_context_sha256")):
        raise AssertionError("HTTP implementation fixed WORM build context drifted")
    for field in (
        "production_schema_or_index_changed",
        "operator_migration_executed",
        "real_data_migration_executed",
        "production_cutover",
    ):
        if worm_reference.get(field) is not False:
            raise AssertionError(f"HTTP implementation WORM overclaims {field}")

    authorization = contract.get("authorization", {})
    if authorization.get("implementation_present") is not True:
        raise AssertionError("HTTP implementation presence is not authorized")
    if "http_implementation_complete" in authorization:
        raise AssertionError("obsolete HTTP completion claim is forbidden")
    for field in (
        "full_target_parity_closed",
        "route_migration_eligible",
        "two_legacy_get_routes_migrated",
        "derived_head_and_options_count_as_migrated",
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
        if authorization.get(field) is not False:
            raise AssertionError(f"HTTP implementation overclaims authorization: {field}")

    contract_acceptance = contract.get("acceptance", {})
    for field in (
        "implementation_present",
        "predecessor_entry_contract_preserved",
        "exact_production_delta_verified",
        "learning_and_personalbank_sources_unchanged",
        "public_application_api_unchanged",
        "forbidden_main_sources_unchanged",
        "new_rate_limit_resource_has_one_learning_owner",
        "partial_network_postgres_redis_and_59_case_evidence_bound",
        "operator_and_real_migration_remain_blocked",
    ):
        if contract_acceptance.get(field) is not True:
            raise AssertionError(f"HTTP implementation acceptance is not closed: {field}")
    if contract_acceptance.get("effective_resource_count") != 160:
        raise AssertionError("HTTP implementation effective resource count drifted")
    for field in ("full_target_parity_closed", "route_migration_eligible"):
        if contract_acceptance.get(field) is not False:
            raise AssertionError(f"HTTP implementation acceptance overclaims: {field}")
    if contract_acceptance.get("implemented_pending_get_count") != 2:
        raise AssertionError("HTTP implementation pending GET count drifted")
    if contract_acceptance.get("migrated_operation_count") != 11:
        raise AssertionError("HTTP implementation acceptance migrated count drifted")
    if contract_acceptance.get("pending_operation_count") != 600:
        raise AssertionError("HTTP implementation acceptance pending count drifted")
    if contract_acceptance.get("production_cutover_operation_count") != 0:
        raise AssertionError("HTTP implementation acceptance overclaims cutover")
    if contract_acceptance.get("next_gate") != (
            "close_59_case_target_execution_and_full_authentication_chain_"
            "before_route_migration"):
        raise AssertionError("HTTP implementation next gate drifted")

    if not _is_sha256(TRUST_PAYLOAD_SHA256):
        raise AssertionError("unsettled HTTP implementation trust payload SHA-256")
    if _trust_payload_sha256(contract) != TRUST_PAYLOAD_SHA256:
        raise AssertionError("HTTP implementation independent trust payload drifted")


def accepted_sha256(relative: str) -> str | None:
    return {
        **HTTP_ENTRY_SOURCE_ACCEPTED_SHA256,
        **READ_TERMINAL_SOURCE_ACCEPTED_SHA256,
    }.get(relative)


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    if relative in HTTP_ENTRY_SOURCE_ACCEPTED_SHA256:
        field = "http_entry_source_overrides"
    elif relative in READ_TERMINAL_SOURCE_ACCEPTED_SHA256:
        field = "read_terminal_source_overrides"
    else:
        return None
    loaded = _load_immutable_contract_envelope(ti_java_root)
    if loaded is None:
        return None
    root, contract = loaded
    reference = contract["historical_successor_acceptance"][field][relative]
    if reference.get("source") != relative:
        raise AssertionError(f"implementation successor path drifted: {relative}")
    if reference.get("accepted_sha256") != accepted_sha256(relative):
        raise AssertionError(f"implementation successor accepted hash drifted: {relative}")
    implementation_successor = contract["historical_successor_acceptance"][field][relative][
        "successor_sha256"
    ]
    return _validated_current_sha256(
        root,
        relative,
        implementation_successor,
        label="HTTP implementation successor",
    )


def fixed_source_sha256(ti_java_root: Path, relative: str) -> str | None:
    """Return a validated current hash only for a code-fixed source path."""
    names = [name for name, path in SOURCE_PATHS.items() if path == relative]
    if len(names) != 1:
        return None
    loaded = _load_immutable_contract_envelope(ti_java_root)
    if loaded is None:
        return None
    root, contract = loaded
    reference = contract["source_contracts"][names[0]]
    if reference.get("source") != relative:
        raise AssertionError(f"fixed implementation source path drifted: {names[0]}")
    return _validated_current_sha256(
        root,
        relative,
        reference["sha256"],
        label=f"fixed implementation source {names[0]}",
    )


def runtime_successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    """Return a validated hash only for the fixed implementation runtime delta."""
    if relative not in ADDED_RUNTIME_PATHS | CHANGED_RUNTIME_PATHS:
        return None
    loaded = _load_immutable_contract_envelope(ti_java_root)
    if loaded is None:
        return None
    root, contract = loaded
    successor = contract["implementation"]["production_runtime_transition"]["current"][
        "files"
    ][relative]
    if _sha256(_fixed_regular_file(root, relative)) != successor:
        raise AssertionError(f"implementation runtime successor drifted: {relative}")
    return successor
