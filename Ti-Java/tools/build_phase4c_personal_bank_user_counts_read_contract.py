#!/usr/bin/env python3
"""Build the fixed Phase 4C HTTP-neutral personal-bank user-counts read contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)
PREDECESSOR_SHA256 = (
    "ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b"
)
WORM_REPORT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-read-access-worm-evidence.json"
)
WORM_PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-worm-evidence.json"
)
WORM_PREDECESSOR_SHA256 = (
    "fade745bfa0da6ea7d4fc6a16dcee499149ee06dc1113fc92b5256df23cc42e9"
)
ROUTE_SURFACE_MANIFEST_SHA256 = (
    "6f9cfdd6ba849233c51a27ed281856681d8a6ec3a0bda628da9184ec284e4b86"
)
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

PYTHON_ACCEPTED_SHA256 = {
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py": (
        "866b749cdc00fe22451e4a4663702d98e4917e0d546f996f0d6cac6326f39d75"
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "114a07ce3ada1027c7e30a595b249c9f88244ffd0d0838b1507019f64711eb59"
    ),
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": (
        "03a5cefe9ea73ad86ff8755019d88abbb84778488fdb117dd9c4517a91040b86"
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "3459e74ed669e3f0aa6e4bc3e2e600f4a4b644a03fc7a382cd01a78ce873d254"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": (
        "5854e591041b8cb1892b805208903c5115027a8dbaeec56f8db8b98223301ada"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": (
        "2251ab9b5c15c0badf59b782fd9e7f76030f1bef33f8943fcfbf459972abc4be"
    ),
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "9fcd432a81f78eb78f0001e4e6d029e01f27047e56714c96d7fd47607d98c016"
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "c5c0a52d90553acc3699dab2534f6dc1ac0261940be6611f57ca293f3fb92207"
    ),
}

JAVA_ACCEPTED_SHA256 = {
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "ModuleContractParityTest.java"
    ): "35e25fa5ed4d5771701f8c1819b615bee9af441a6c64cbf1386df168f16610cb",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ): "171c36f7c3cdd2d2ff97998cade67ec99c3d825ec3bce4191094a3bcf0095b48",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ): "1bc3ba26b932eba694d0aeb4762e7973d51a0fee5bd69d0454799c223d56248a",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ): "1b24e8a8f1861a5adad96de9f087abc684b73e9a4dd496ffb7f1d071ddc307bc",
}

AUXILIARY_ACCEPTED_SHA256 = {
    "docs/refactor/05-progress.md": (
        "47ec2b9a2178dee8db91f0461b9abffbbe9dea0a5ba4dd3694d4f33643735bbf"
    ),
}

VERIFICATION_SOURCES = {
    "api_shape_contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsContractParityTest.java"
    ),
    "learning_composition_test": (
        "server/src/test/java/io/saksk/ti/learning/application/"
        "PersonalBankUserCountsServiceTest.java"
    ),
    "personalbank_facts_service_test": (
        "server/src/test/java/io/saksk/ti/personalbank/application/"
        "PersonalBankQuestionFactsServiceTest.java"
    ),
    "learning_adapter_test": (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/persistence/"
        "JdbcPersonalBankUserCountsQueryAdapterTest.java"
    ),
    "personalbank_adapter_test": (
        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/persistence/"
        "JdbcPersonalBankQuestionFactsQueryAdapterTest.java"
    ),
    "postgresql_compatibility_it": (
        "server/src/test/java/io/saksk/ti/integration/"
        "Phase4cPersonalBankUserCountsJdbcCompatibilityIT.java"
    ),
}

AUXILIARY_SOURCES = {
    "contract_builder": "tools/build_phase4c_personal_bank_user_counts_read_contract.py",
    "contract_test": "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
    "python_successor_bridge": "tools/phase4c_read_successor_acceptance.py",
    "java_successor_bridge": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cReadSuccessorAcceptance.java"
    ),
    "phase2_worm_successor_gate": "tools/phase2_wormhole_successor_acceptance.py",
    "phase2_worm_successor_test": "tools/test_phase2_wormhole_successor_acceptance.py",
    "phase2_static_verifier": "infra/phase2/verify-static.sh",
    "phase2_worm_runner": "infra/phase2/verify-local-reference-wormhole.sh",
    "phase2_readme": "infra/phase2/README.md",
    "phase1_validator": "tools/validate_phase1.py",
    "phase4c_readme": "docs/refactor/phase4c/README.md",
    "project_readme": "README.md",
    "progress": "docs/refactor/05-progress.md",
    "predecessor_worm_report": WORM_PREDECESSOR_RELATIVE,
    "worm_report": WORM_REPORT_RELATIVE,
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


def source_reference(relative: str) -> dict:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"required Phase4C read source is missing: {relative}")
    return {"source": relative, "sha256": sha256(path)}


def file_manifest(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


def manifest_payload(manifest: dict[str, str]) -> dict:
    return {
        "file_count": len(manifest),
        "manifest_sha256": sha256_json(manifest),
        "files": dict(sorted(manifest.items())),
    }


def main_source_manifest() -> dict[str, str]:
    root = ROOT / "server/src/main/java/io/saksk/ti"
    paths: list[Path] = []
    for module in ("learning", "personalbank"):
        paths.extend((root / module).rglob("*.java"))
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


def route_status_manifest() -> dict[str, str]:
    return {
        relative: sha256(ROOT / relative)
        for relative in (
            "docs/refactor/02-route-parity-matrix.csv",
            "docs/refactor/phase3/route-parity-delta.csv",
            "docs/refactor/phase3/effective-route-parity-status.json",
            "docs/refactor/phase4a/route-parity-delta.csv",
            "docs/refactor/phase4a/effective-route-parity-status.json",
        )
    }


def java_build_context_sha256() -> str:
    result = subprocess.run(
        [str(ROOT / "infra/phase2/hash-java-build-context.sh")],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    digest = result.stdout.strip()
    if len(digest) != 64:
        raise ValueError("Java build-context hasher did not return SHA-256")
    return digest


def public_application_methods() -> list[dict]:
    status = load_json(
        ROOT / "docs/refactor/phase4b/application-api-shape-status.json"
    )
    personalbank = load_json(
        ROOT / "docs/refactor/phase4b/"
        "personal-bank-usage-stats-application-api-shape.json"
    )["personalbank"]
    methods: list[dict] = []

    def append_methods(owner_api: str, entries: list[dict]) -> None:
        for method in entries:
            item = {
                "owner_api": owner_api,
                "name": method["name"],
                "return_type": method["return_type"],
                "parameter_types": method["parameter_types"],
            }
            if "generic_return_type" in method:
                item["generic_return_type"] = method["generic_return_type"]
            methods.append(item)

    for module in status["modules"]:
        if module["module_id"] == "personalbank":
            append_methods(personalbank["java_api"], personalbank["methods"])
            continue
        append_methods(module["java_api"], module["methods"])
        for additional in module.get("additional_public_apis") or []:
            append_methods(additional["java_api"], additional["methods"])

    append_methods(
        "io.saksk.ti.learning.api.LearningApplicationApi",
        [{
            "name": "findPersonalBankUserCounts",
            "return_type": "io.saksk.ti.learning.api.PersonalBankUserCountsResult",
            "parameter_types": [
                "io.saksk.ti.learning.api.AuthenticatedLearningViewer",
                "io.saksk.ti.learning.api.PersonalBankUserCountsQuery",
            ],
        }],
    )
    append_methods(
        "io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi",
        [
            {
                "name": "checkQuestionAccess",
                "return_type": (
                    "io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult"
                ),
                "parameter_types": [
                    "io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer",
                    "int",
                ],
            },
            {
                "name": "summarizeQuestions",
                "return_type": (
                    "io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult"
                ),
                "parameter_types": [
                    "io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer",
                    "io.saksk.ti.personalbank.api.PersonalBankQuestionSelection",
                ],
            },
            {
                "name": "inspectQuestionMembership",
                "return_type": (
                    "io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView"
                ),
                "parameter_types": ["int", "java.util.List"],
            },
        ],
    )
    if len(methods) != 27:
        raise ValueError(f"expected exact 27-method application shape, got {len(methods)}")
    return methods


def successor_sources(accepted: dict[str, str]) -> dict[str, dict]:
    return {
        relative: {
            "source": relative,
            "accepted_sha256": accepted_sha256,
            "successor_sha256": sha256(ROOT / relative),
        }
        for relative, accepted_sha256 in sorted(accepted.items())
    }


def validate_surface_delta(
        composition: dict,
        requirements: dict,
        main_manifest: dict[str, str],
        runtime_manifest: dict[str, str],
) -> None:
    historical_main = composition["production_baseline"][
        "learning_and_personalbank_main_source_manifest"
    ]
    expected_added = set(requirements["expected_added_main_sources"])
    expected_changed = set(requirements["expected_changed_main_sources"])
    if set(main_manifest) - set(historical_main) != expected_added:
        raise ValueError("unexpected Phase4C read main-source additions")
    if set(historical_main) - set(main_manifest):
        raise ValueError("Phase4C read deleted a historical main source")
    actual_changed = {
        relative
        for relative in set(main_manifest) & set(historical_main)
        if main_manifest[relative] != historical_main[relative]
    }
    if actual_changed != expected_changed:
        raise ValueError("unexpected Phase4C read main-source modifications")
    if len(main_manifest) != 40:
        raise ValueError("Phase4C read main-source manifest must contain 40 files")

    historical_runtime = composition["production_baseline"][
        "production_runtime_surface"
    ]["files"]
    if set(runtime_manifest) - set(historical_runtime) != expected_added:
        raise ValueError("unexpected Phase4C read production-runtime additions")
    if set(historical_runtime) - set(runtime_manifest):
        raise ValueError("Phase4C read deleted a production-runtime file")
    runtime_changed = {
        relative
        for relative in set(runtime_manifest) & set(historical_runtime)
        if runtime_manifest[relative] != historical_runtime[relative]
    }
    if runtime_changed != expected_changed:
        raise ValueError("unexpected Phase4C read production-runtime modifications")
    if len(runtime_manifest) != 288:
        raise ValueError("Phase4C read production-runtime surface must contain 288 files")


def build_contract() -> dict:
    predecessor_path = ROOT / PREDECESSOR_RELATIVE
    if sha256(predecessor_path) != PREDECESSOR_SHA256:
        raise ValueError("Phase4C composition predecessor is not byte-for-byte immutable")
    composition = load_json(predecessor_path)
    requirements = composition["successor_handoff"][
        "future_read_contract_requirements"
    ]
    if requirements["contract_id"] != (
        "ti.phase4c.personal-bank-user-counts-read-contract"
    ):
        raise ValueError("unexpected authorized Phase4C read contract id")

    main_manifest = main_source_manifest()
    runtime_manifest = production_runtime_manifest()
    validate_surface_delta(composition, requirements, main_manifest, runtime_manifest)

    route_manifest = route_status_manifest()
    route_surface = manifest_payload(route_manifest)
    if route_surface["manifest_sha256"] != ROUTE_SURFACE_MANIFEST_SHA256:
        raise ValueError("Phase4C read changed route status or OpenAPI evidence")
    if route_manifest != composition["production_baseline"]["route_status_surface"]["files"]:
        raise ValueError("Phase4C read route surface differs from its predecessor")

    build_context = java_build_context_sha256()
    predecessor_worm_path = ROOT / WORM_PREDECESSOR_RELATIVE
    if sha256(predecessor_worm_path) != WORM_PREDECESSOR_SHA256:
        raise ValueError("Phase4C read WORM predecessor is not byte-for-byte immutable")
    worm_path = ROOT / WORM_REPORT_RELATIVE
    worm = load_json(worm_path)
    if worm["java"]["buildContextSha256"] != build_context:
        raise ValueError("Phase4C read WORM does not bind the current Java build context")
    if worm["java"]["dockerfileSha256"] != DOCKERFILE_SHA256:
        raise ValueError("Phase4C read WORM Dockerfile hash drifted")
    if worm["restore"]["serverVersion"] != "18.4":
        raise ValueError("Phase4C read WORM did not restore PostgreSQL 18.4")
    if worm["restore"]["publicBaseTables"] != 70 or worm["restore"]["publicColumns"] != 617:
        raise ValueError("Phase4C read WORM schema dimensions drifted")
    if not worm["java"]["startupPassed"] or not worm["java"]["readinessPassed"]:
        raise ValueError("Phase4C read WORM startup/readiness did not pass")
    if not all(
        worm["readRole"][key]
        for key in (
            "selectPassed",
            "defaultTransactionReadOnly",
            "aclVerifiedWithReadOnlyDefaultDisabled",
            "insertRejected",
            "updateRejected",
            "deleteRejected",
            "ddlRejected",
            "temporaryDdlRejected",
        )
    ):
        raise ValueError("Phase4C read WORM read-only ACL evidence is incomplete")

    verification_hashes = {
        name: sha256(ROOT / relative)
        for name, relative in sorted(VERIFICATION_SOURCES.items())
    }
    source_contracts = {
        "composition_predecessor": source_reference(PREDECESSOR_RELATIVE),
        **{
            f"verification_{name}": source_reference(relative)
            for name, relative in sorted(VERIFICATION_SOURCES.items())
        },
        **{
            name: source_reference(relative)
            for name, relative in sorted(AUXILIARY_SOURCES.items())
        },
        **{
            f"historical_python_{index:02d}": source_reference(relative)
            for index, relative in enumerate(sorted(PYTHON_ACCEPTED_SHA256), 1)
        },
        **{
            f"historical_java_{index:02d}": source_reference(relative)
            for index, relative in enumerate(sorted(JAVA_ACCEPTED_SHA256), 1)
        },
    }

    authorization = {
        "http_neutral_java_implementation": True,
        "real_data_migration_execution": False,
        "operator_migration_implementation": False,
        "migration_global_preflight_evidence_closed": False,
        "http_controller": False,
        "security_or_rate_limit": False,
        "route_or_openapi_delta": False,
        "production_schema_or_index": False,
        "production_cutover": False,
    }
    forbidden = requirements["forbidden_authorizations"]
    if any(authorization[key] for key in forbidden):
        raise ValueError("Phase4C read accidentally authorized a forbidden surface")

    contract = {
        "contract_id": requirements["contract_id"],
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "status": requirements["status"],
        "scope": "phase4c-personal-bank-user-counts-http-neutral-read",
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "sha256": PREDECESSOR_SHA256,
            "contract_id": composition["contract_id"],
            "status": composition["status"],
        },
        "source_contracts": dict(sorted(source_contracts.items())),
        "historical_successor_acceptance": {
            "predecessor_contract_id": composition["contract_id"],
            "predecessor_sha256": PREDECESSOR_SHA256,
            "python_sources": successor_sources(PYTHON_ACCEPTED_SHA256),
            "java_sources": successor_sources(JAVA_ACCEPTED_SHA256),
            "auxiliary_sources": successor_sources(AUXILIARY_ACCEPTED_SHA256),
            "successor_allowlist_exact": True,
            "arbitrary_source_hash_lookup_forbidden": True,
        },
        "implementation": {
            "http_neutral_java_implemented": True,
            "implemented_public_application_method_count": 27,
            "public_application_methods": public_application_methods(),
            "main_source_scope": ["learning", "personalbank"],
            "learning_and_personalbank_main_source_manifest": main_manifest,
            "learning_and_personalbank_main_source_manifest_sha256": (
                sha256_json(main_manifest)
            ),
            "main_source_file_count": len(main_manifest),
            "added_main_sources": sorted(requirements["expected_added_main_sources"]),
            "changed_main_sources": requirements["expected_changed_main_sources"],
            "deleted_main_sources": [],
            "production_runtime_surface": manifest_payload(runtime_manifest),
            "java_build_context_sha256": build_context,
            "route_status_surface": route_surface,
            "verification_source_files": dict(sorted(VERIFICATION_SOURCES.items())),
            "verification_source_sha256": verification_hashes,
        },
        "required_behavior_evidence": requirements["required_behavior_evidence"],
        "security_access_policy": composition["security_access_policy"],
        "authorization": authorization,
        "migration_status": {
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "real_data_migration_executed": False,
            "operator_implemented": False,
        },
        "route_status": {
            "operations": composition["route_status"]["operations"],
            "routes_remain_pending": True,
            "route_or_openapi_delta": False,
            "controller_added": False,
            "security_matcher_added": False,
            "production_cutover": False,
        },
        "worm_successor_evidence": {
            "status": "fourth_versioned_tip_verified_historical_reports_immutable",
            "predecessor": {
                "source": WORM_PREDECESSOR_RELATIVE,
                "sha256": WORM_PREDECESSOR_SHA256,
            },
            "current_tip": {
                "source": WORM_REPORT_RELATIVE,
                "sha256": sha256(worm_path),
                "java_build_context_sha256": build_context,
                "dockerfile_sha256": DOCKERFILE_SHA256,
                "postgresql_version": "18.4",
                "public_base_tables": 70,
                "public_columns": 617,
                "startup_passed": True,
                "readiness_passed": True,
                "read_only_acl_passed": True,
            },
            "fixed_allowlist_gate": "tools/phase2_wormhole_successor_acceptance.py",
            "arbitrary_report_lookup_forbidden": True,
            "historical_report_overwrite_forbidden": True,
        },
        "acceptance": {
            "targeted_verification_passed": True,
            "http_neutral_read_implemented": True,
            "routes_remain_pending": True,
            "production_cutover": False,
            "next_gate": (
                "close_http_entry_contract_without_authorizing_operator_or_cutover"
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
