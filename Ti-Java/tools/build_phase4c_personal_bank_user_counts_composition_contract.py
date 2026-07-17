#!/usr/bin/env python3
"""Build the Phase 4C user-counts composition and ownership contracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/refactor/phase4c"
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
PHASE4B_ACCEPTED_COMMIT = "2ca3e16d9585de55313fd2de9b1429a6351d9683"
PHASE4B_ENTRY_CONTRACT_ACCEPTED_SHA256 = (
    "1ec41fde1e17dd1f09a9aa737aadd9ada1f64c41f4e44f1df87dbf0613c30ee6"
)
PHASE4C_ENTRY_JAVA_BUILD_CONTEXT_SHA256 = (
    "c59ee688646b7c23f0f883b4c1377d2a33b507e7dd08b978e98cf3ebdc11825c"
)
PHASE4C_ENTRY_PRODUCTION_SURFACE_MANIFEST_SHA256 = (
    "7d6113701aac8268f22e8b58b3c52d7d8ea388ddaa06aa2d3d7bd334edd17ebd"
)
PHASE4C_ENTRY_ROUTE_SURFACE_MANIFEST_SHA256 = (
    "6f9cfdd6ba849233c51a27ed281856681d8a6ec3a0bda628da9184ec284e4b86"
)
PHASE4B_WORM_REPORT_SHA256 = (
    "779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad"
)
PHASE4C_ENTRY_WORM_REPORT_SHA256 = (
    "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884"
)
NAMESPACE = "bank_<bank_id>_tags"
ROUTES = [
    {
        "route_id": "6858f6fa506f",
        "method": "GET",
        "path": "/api/user/banks/api/<int:bank_id>/user-counts",
        "surface": "miniprogram",
    },
    {
        "route_id": "006913d0d956",
        "method": "GET",
        "path": "/user/banks/api/<int:bank_id>/user-counts",
        "surface": "web",
    },
]
PHASE4C_FORWARD_ADDITIONS = [
    "Ti-Java/docs/refactor/phase4c/README.md",
    "Ti-Java/docs/refactor/phase4c/approved-differences.md",
    "Ti-Java/docs/refactor/phase4c/data-ownership-delta.csv",
    "Ti-Java/docs/refactor/phase4c/effective-data-ownership-status.json",
    (
        "Ti-Java/docs/refactor/phase4c/"
        "personal-bank-user-counts-composition-contract.json"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "Phase4cLegacyPersonalBankTagMigrationEvidenceIT.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cSuccessorAcceptance.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/learning/infrastructure/"
        "persistence/LegacyPersonalBankTagMigrationEvidence.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/learning/infrastructure/"
        "persistence/LegacyPersonalBankTagMigrationEvidenceTest.java"
    ),
    (
        "Ti-Java/server/src/test/resources/db/phase4c/"
        "069-legacy-personal-bank-tag-migration-schema.sql"
    ),
    (
        "Ti-Java/server/src/test/resources/db/phase4c/"
        "070-legacy-personal-bank-tag-migration-seed.sql"
    ),
    "Ti-Java/tools/build_phase4c_personal_bank_user_counts_composition_contract.py",
    "Ti-Java/tools/phase4c_successor_acceptance.py",
    "Ti-Java/tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
    (
        "Ti-Java/docs/refactor/phase4c/"
        "personal-bank-user-counts-entry-worm-evidence.json"
    ),
    "Ti-Java/tools/phase2_wormhole_successor_acceptance.py",
    "Ti-Java/tools/test_phase2_wormhole_successor_acceptance.py",
]
PHASE4B_ACCEPTED_FILE_SHA256 = {
    "README.md": "df70f0038f03c71bcbeb01a0f5edb75b6c115e2f1844a774350b0d269bfd3787",
    "docs/refactor/05-progress.md": (
        "0d08ea5c4c6f0c61c6d8c2a722d1e95ce0bfe999d523db2c0b9cdca7bc213bb9"
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "0c2be82c561aa7f02e6db4b71d4f91ebf1b772f92d4e193a3812e92722c2ba2a"
    ),
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": (
        "75e4235fad3bbe8edfd34829a82ff4a6cff8798fee1ac6cfeab072e6f2f81913"
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "65fe01833802612620ffa26e1771cd9215c5866d65a933bc34be4a806ee42c63"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": (
        "0eb5fa3ae1eab5001e1a44e77d312ad425967d746370b8f6da6f18a202089f8d"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": (
        "60c6dc113f42093c2ff2ff21405cdebadb76fd99886fc94c1b15ab616955aac4"
    ),
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "f5329e12eac3b18e2742c85d40d7c25591fb83fc2cdb3c0d215e240fa0566def"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ): "0716fcfa788c530517f2da5ef87a943c3ed2d960e50e599d66756e6e84d29973",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ): "d6326b2aa91ceb2bb502bc8847d233c26a2741996a7bc3bf627c9731c6318523",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ): "343b8b4cf4e9df575e1a5f14743d39c2d31e2b7b20f9c604bcab3f17081e6a1e",
}
PHASE4B_SUCCESSOR_SOURCE_KEYS = {
    "docs/refactor/05-progress.md": "progress",
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "all_shares_entry_successor_test"
    ),
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": (
        "all_shares_read_successor_test"
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "share_list_acceptance_successor_test"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": (
        "usage_stats_entry_successor_test"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": (
        "usage_stats_read_successor_test"
    ),
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "phase4b_entry_contract_test"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ): "all_shares_java_successor_test",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ): "share_list_java_successor_test",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ): "usage_stats_java_successor_test",
}
# These values preserve the canonical Phase4A/4B WORM manifest, which can be
# older than the files accepted at the immediate Phase4B predecessor commit.
WORM_HISTORICAL_HASH_OVERRIDES = {
    "README.md": PHASE4B_ACCEPTED_FILE_SHA256["README.md"],
    "infra/phase2/README.md": (
        "4dd7e88f99cb8639e91acd181c3f07749a1ff38dc95256eda6d6e55566623ef2"
    ),
    "infra/phase2/verify-local-reference-wormhole.sh": (
        "9aebdb8a7e477c464a6750b73c76f9336d1191230762ae8369ebe8cc1b82ad49"
    ),
    "infra/phase2/verify-static.sh": (
        "5a9cd32fa094f25d32fcd71da6cd17d0fdc353d02fdfc6c2886ac5128777102d"
    ),
    "tools/validate_phase1.py": (
        "a38fce0e7f13530196ab424f7f7da75816c3e32ae6ac149986a5914875a62c5e"
    ),
    "docs/refactor/05-progress.md": (
        "89fa432fba5b793b002cc034dda4c7a92a666e0b871c1ef744ed0d90a55b7e63"
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "cc4d90ece5436c7f0841e417581f9a9bb6fef6251e247faa0136b4e3694228cc"
    ),
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": (
        "c8a1b8180513bf7ca7b5cbb8f0b428b54d11b6972dc93175485447ab93863570"
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "76cf1941682ad21197920b874855cfcd0f5e851bcc714ead071671aba5502d6f"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": (
        "3e4428cc2a57b2531f8fbee9de0fb5de01542dff7124e249bf88325625086962"
    ),
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": (
        PHASE4B_ACCEPTED_FILE_SHA256[
            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py"
        ]
    ),
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        PHASE4B_ACCEPTED_FILE_SHA256[
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py"
        ]
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ): "9fa934116dc01ea7b88b2ac85ae41f1d354efb96e8a20fcbc7de6b00cfdf93d5",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ): "b37147f2f1fc0bd4dbe7582d5457026e46d0e5ee323eb8b1480325eca8658fdb",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ): PHASE4B_ACCEPTED_FILE_SHA256[
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ],
}


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_payload_sha256(document: dict) -> str:
    payload = {
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, document: dict) -> None:
    document["document_payload_sha256"] = json_payload_sha256(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def source_reference(relative: str) -> dict:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"required Phase 4C source is missing: {relative}")
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
        "manifest_sha256": hashlib.sha256(
            canonical_json(manifest).encode("utf-8")
        ).hexdigest(),
        "files": manifest,
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
    if digest != PHASE4C_ENTRY_JAVA_BUILD_CONTEXT_SHA256:
        raise ValueError(f"unexpected Phase4C entry Java build context: {digest}")
    return digest


def ownership_row() -> dict:
    rows = list(csv.DictReader(
        (ROOT / "docs/refactor/03-data-ownership.csv")
        .read_text(encoding="utf-8")
        .splitlines()
    ))
    matches = [
        row for row in rows
        if row["resource_kind"] == "db_kv_namespace"
        and row["resource_name"] == NAMESPACE
    ]
    if len(matches) != 1:
        raise ValueError("bank tag compatibility namespace must have one Phase 1 row")
    return matches[0]


def canonical_effective_owners(phase4a: dict) -> list[dict]:
    base_rows = list(csv.DictReader(
        (ROOT / "docs/refactor/03-data-ownership.csv")
        .read_text(encoding="utf-8")
        .splitlines()
    ))
    owners: dict[tuple[str, str], str] = {}
    for row in base_rows:
        key = (row["resource_kind"], row["resource_name"])
        if key in owners:
            raise ValueError(f"duplicate base ownership resource: {key}")
        owner = row["target_owner"].strip()
        if not owner:
            raise ValueError(f"missing base ownership owner: {key}")
        owners[key] = owner

    for resource in phase4a["effective"]["new_resources"]:
        key = (resource["resource_kind"], resource["resource_name"])
        if key in owners:
            raise ValueError(f"duplicate Phase4A ownership resource: {key}")
        owner = resource["owner"].strip()
        if not owner:
            raise ValueError(f"missing Phase4A ownership owner: {key}")
        owners[key] = owner

    expected_count = phase4a["effective"]["resource_count"]
    if len(owners) != expected_count:
        raise ValueError(
            f"effective ownership count mismatch: {len(owners)} != {expected_count}"
        )

    override_key = ("db_kv_namespace", NAMESPACE)
    if owners.get(override_key) != "personalbank":
        raise ValueError("unexpected effective predecessor owner for bank tag namespace")
    owners[override_key] = "learning"
    return [
        {"resource_kind": key[0], "resource_name": key[1], "owner": owner}
        for key, owner in sorted(owners.items())
    ]


def write_ownership_overlay(output_dir: Path) -> tuple[Path, Path]:
    base = ownership_row()
    if base["target_owner"] != "personalbank":
        raise ValueError("unexpected Phase 1 owner for bank tag compatibility namespace")

    delta_path = output_dir / "data-ownership-delta.csv"
    delta_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "resource_kind",
        "resource_name",
        "base_owner",
        "phase4c_owner",
        "persistence_role",
        "lifecycle",
        "evidence",
        "production_cutover",
    ]
    row = {
        "resource_kind": "db_kv_namespace",
        "resource_name": NAMESPACE,
        "base_owner": "personalbank",
        "phase4c_owner": "learning",
        "persistence_role": "legacy_compatibility_state",
        "lifecycle": (
            "operator-only explicit migration; source retained; normal GET and startup "
            "migration forbidden"
        ),
        "evidence": (
            "phase4b personal-bank-user-counts entry/golden plus Phase4C composition "
            "and migration evidence"
        ),
        "production_cutover": "false",
    }
    with delta_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)

    phase4a_path = ROOT / "docs/refactor/phase4a/effective-data-ownership-status.json"
    phase4a = load_json(phase4a_path)
    resource_count = phase4a["effective"]["resource_count"]
    owner_manifest = canonical_effective_owners(phase4a)
    effective_path = output_dir / "effective-data-ownership-status.json"
    effective = {
        "contract_id": "ti.phase4c.effective-data-ownership-status",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "predecessor": {
            "source": "../phase4a/effective-data-ownership-status.json",
            "sha256": sha256(phase4a_path),
            "resource_count": resource_count,
            "immutable": True,
        },
        "delta": {
            "source": "data-ownership-delta.csv",
            "sha256": sha256(delta_path),
            "owner_override_count": 1,
            "new_resource_count": 0,
        },
        "effective": {
            "resource_count": resource_count,
            "resources_with_exactly_one_owner": resource_count,
            "canonical_owner_manifest_sha256": hashlib.sha256(
                canonical_json(owner_manifest).encode("utf-8")
            ).hexdigest(),
            "owner_overrides": [{
                "resource_kind": "db_kv_namespace",
                "resource_name": NAMESPACE,
                "base_owner": "personalbank",
                "owner": "learning",
                "production_cutover": False,
            }],
        },
    }
    write_json(effective_path, effective)
    return delta_path, effective_path


def main_source_manifest() -> dict[str, str]:
    root = ROOT / "server/src/main/java/io/saksk/ti"
    paths = []
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


def build_contract(output_dir: Path, delta_path: Path, effective_path: Path) -> dict:
    predecessor_path = (
        ROOT / "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json"
    )
    predecessor = load_json(predecessor_path)
    predecessor_sha256 = sha256(predecessor_path)
    if predecessor_sha256 != PHASE4B_ENTRY_CONTRACT_ACCEPTED_SHA256:
        raise ValueError(
            "Phase4B user-counts contract must remain byte-for-byte immutable: "
            f"{predecessor_sha256}"
        )
    shape_path = (
        ROOT / "docs/refactor/phase4b/"
        "personal-bank-usage-stats-application-api-shape.json"
    )
    shape = load_json(shape_path)
    route_matrix_path = ROOT / "docs/refactor/02-route-parity-matrix.csv"
    route_delta_path = ROOT / "docs/refactor/phase4a/route-parity-delta.csv"
    effective_route_path = (
        ROOT / "docs/refactor/phase4a/effective-route-parity-status.json"
    )
    effective_route = load_json(effective_route_path)["effective"]
    modules_path = ROOT / "docs/refactor/phase1/module-contracts.json"
    modules = {
        item["module_id"]: item for item in load_json(modules_path)["modules"]
    }
    if modules["learning"]["allowed_dependencies"].count("personalbank") != 1:
        raise ValueError("learning -> personalbank dependency must already be accepted")
    if "learning" in modules["personalbank"]["allowed_dependencies"]:
        raise ValueError("personalbank -> learning must remain forbidden")
    route_rows = list(csv.DictReader(
        route_matrix_path.read_text(encoding="utf-8").splitlines()
    ))
    route_by_id = {row["route_id"]: row for row in route_rows}
    for route in ROUTES:
        row = route_by_id.get(route["route_id"])
        if row is None or row["migration_status"] != "pending":
            raise ValueError(f"user-counts route is not pending: {route['route_id']}")
    route_counts = effective_route["migration_status"]
    if effective_route["production_cutover_operation_count"] != 0:
        raise ValueError("production route cutover must remain zero")

    source_contracts = {
        "phase4b_entry_contract": source_reference(
            "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json"
        ),
        "phase4b_entry_contract_test": source_reference(
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py"
        ),
        "phase4b_golden": source_reference(
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
        ),
        "phase4b_callers": source_reference(
            "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
        ),
        "phase4b_query_plan": source_reference(
            "docs/refactor/phase4b/personal-bank-user-counts-query-plan-evidence.json"
        ),
        "application_api_shape": source_reference(
            "docs/refactor/phase4b/"
            "personal-bank-usage-stats-application-api-shape.json"
        ),
        "phase4a_question_count_contract": source_reference(
            "docs/refactor/phase4a/question-count-read-contract.json"
        ),
        "module_contracts": source_reference(
            "docs/refactor/phase1/module-contracts.json"
        ),
        "route_parity_matrix": source_reference(
            "docs/refactor/02-route-parity-matrix.csv"
        ),
        "route_parity_delta": source_reference(
            "docs/refactor/phase4a/route-parity-delta.csv"
        ),
        "effective_route_status": source_reference(
            "docs/refactor/phase4a/effective-route-parity-status.json"
        ),
        "phase3_route_parity_delta": source_reference(
            "docs/refactor/phase3/route-parity-delta.csv"
        ),
        "phase3_effective_route_status": source_reference(
            "docs/refactor/phase3/effective-route-parity-status.json"
        ),
        "openapi": source_reference("contracts/openapi.json"),
        "openapi_manual_overrides": source_reference(
            "contracts/openapi-manual-overrides.json"
        ),
        "phase3_authentication_openapi": source_reference(
            "openapi/phase3-authentication.openapi.json"
        ),
        "phase4a_public_bank_openapi": source_reference(
            "openapi/phase4a-public-bank.openapi.json"
        ),
        "phase4a_subject_directory_openapi": source_reference(
            "openapi/phase4a-subject-directory.openapi.json"
        ),
        "server_pom": source_reference("server/pom.xml"),
        "server_dockerfile": source_reference("server/Dockerfile"),
        "compose_dev": source_reference("compose.dev.yml"),
        "java_build_context_hasher": source_reference(
            "infra/phase2/hash-java-build-context.sh"
        ),
        "phase2_static_verifier": source_reference(
            "infra/phase2/verify-static.sh"
        ),
        "phase2_wormhole_runner": source_reference(
            "infra/phase2/verify-local-reference-wormhole.sh"
        ),
        "phase2_wormhole_readme": source_reference("infra/phase2/README.md"),
        "phase2_historical_worm_report": source_reference(
            "infra/phase2/local-reference-verification.json"
        ),
        "phase4b_historical_worm_report": source_reference(
            "docs/refactor/phase4b/personal-bank-share-list-worm-evidence.json"
        ),
        "phase4c_entry_worm_report": source_reference(
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-entry-worm-evidence.json"
        ),
        "phase2_worm_successor_gate": source_reference(
            "tools/phase2_wormhole_successor_acceptance.py"
        ),
        "phase2_worm_successor_test": source_reference(
            "tools/test_phase2_wormhole_successor_acceptance.py"
        ),
        "base_data_ownership": source_reference(
            "docs/refactor/03-data-ownership.csv"
        ),
        "phase4a_effective_data_ownership": source_reference(
            "docs/refactor/phase4a/effective-data-ownership-status.json"
        ),
        "phase4c_data_ownership_delta": {
            "source": "docs/refactor/phase4c/data-ownership-delta.csv",
            "sha256": sha256(delta_path),
        },
        "phase4c_effective_data_ownership": {
            "source": "docs/refactor/phase4c/effective-data-ownership-status.json",
            "sha256": sha256(effective_path),
        },
        "approved_differences": source_reference(
            "docs/refactor/phase4c/approved-differences.md"
        ),
        "project_readme": source_reference("README.md"),
        "phase4c_readme": source_reference("docs/refactor/phase4c/README.md"),
        "progress": source_reference("docs/refactor/05-progress.md"),
        "phase1_validator": source_reference("tools/validate_phase1.py"),
        "migration_evidence_java": source_reference(
            "server/src/test/java/io/saksk/ti/learning/infrastructure/persistence/"
            "LegacyPersonalBankTagMigrationEvidence.java"
        ),
        "migration_evidence_unit_test": source_reference(
            "server/src/test/java/io/saksk/ti/learning/infrastructure/persistence/"
            "LegacyPersonalBankTagMigrationEvidenceTest.java"
        ),
        "migration_evidence_jdbc_test": source_reference(
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4cLegacyPersonalBankTagMigrationEvidenceIT.java"
        ),
        "migration_schema_fixture": source_reference(
            "server/src/test/resources/db/phase4c/"
            "069-legacy-personal-bank-tag-migration-schema.sql"
        ),
        "migration_seed_fixture": source_reference(
            "server/src/test/resources/db/phase4c/"
            "070-legacy-personal-bank-tag-migration-seed.sql"
        ),
        "contract_builder": source_reference(
            "tools/build_phase4c_personal_bank_user_counts_composition_contract.py"
        ),
        "successor_acceptance_bridge": source_reference(
            "tools/phase4c_successor_acceptance.py"
        ),
        "successor_acceptance_java_bridge": source_reference(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cSuccessorAcceptance.java"
        ),
        "contract_test": source_reference(
            "tools/test_phase4c_personal_bank_user_counts_composition_contract.py"
        ),
        "share_list_acceptance_successor_test": source_reference(
            "tools/test_phase4b_personal_bank_share_list_read_contract.py"
        ),
        "all_shares_entry_successor_test": source_reference(
            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py"
        ),
        "all_shares_read_successor_test": source_reference(
            "tools/test_phase4b_personal_bank_all_shares_read_contract.py"
        ),
        "usage_stats_entry_successor_test": source_reference(
            "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py"
        ),
        "usage_stats_read_successor_test": source_reference(
            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py"
        ),
        "share_list_java_successor_test": source_reference(
            "server/src/test/java/io/saksk/ti/architecture/"
            "PersonalBankShareListContractParityTest.java"
        ),
        "all_shares_java_successor_test": source_reference(
            "server/src/test/java/io/saksk/ti/architecture/"
            "PersonalBankAllSharesContractParityTest.java"
        ),
        "usage_stats_java_successor_test": source_reference(
            "server/src/test/java/io/saksk/ti/architecture/"
            "PersonalBankUsageStatsContractParityTest.java"
        ),
    }

    approved_difference_ids = [
        "P4C-LEARNING-001",
        "P4C-LEARNING-002",
        "P4C-LEARNING-003",
        "P4C-LEARNING-004",
        "P4C-LEARNING-005",
        "P4C-LEARNING-006",
    ]
    current_method_count = shape["implemented_public_application_method_count"]
    successor_files = {}
    for relative, source_key in PHASE4B_SUCCESSOR_SOURCE_KEYS.items():
        reference = source_contracts[source_key]
        if reference["source"] != relative:
            raise ValueError(f"successor source key mismatch: {source_key}")
        successor_files[relative] = {
            "accepted_sha256": PHASE4B_ACCEPTED_FILE_SHA256[relative],
            "successor_sha256": reference["sha256"],
            "source_contract_key": source_key,
        }
    runtime_manifest = production_runtime_manifest()
    runtime_surface = manifest_payload(runtime_manifest)
    if (
        runtime_surface["manifest_sha256"]
        != PHASE4C_ENTRY_PRODUCTION_SURFACE_MANIFEST_SHA256
    ):
        raise ValueError("Phase4C entry production surface differs from accepted commit")
    route_surface = manifest_payload(route_status_manifest())
    if route_surface["manifest_sha256"] != PHASE4C_ENTRY_ROUTE_SURFACE_MANIFEST_SHA256:
        raise ValueError("Phase4C entry route surface differs from accepted commit")
    build_context_sha256 = java_build_context_sha256()
    historical_worm = source_contracts["phase2_historical_worm_report"]
    phase4b_historical_worm = source_contracts["phase4b_historical_worm_report"]
    phase4c_worm = source_contracts["phase4c_entry_worm_report"]
    if historical_worm["sha256"] != PHASE4B_WORM_REPORT_SHA256:
        raise ValueError("Phase2 historical WORM report changed")
    if phase4b_historical_worm["sha256"] != PHASE4B_WORM_REPORT_SHA256:
        raise ValueError("Phase4B historical WORM report changed")
    if phase4c_worm["sha256"] != PHASE4C_ENTRY_WORM_REPORT_SHA256:
        raise ValueError("Phase4C entry WORM report changed")
    phase4c_worm_document = load_json(ROOT / phase4c_worm["source"])
    if (
        phase4c_worm_document.get("java", {}).get("buildContextSha256")
        != PHASE4C_ENTRY_JAVA_BUILD_CONTEXT_SHA256
    ):
        raise ValueError("Phase4C entry WORM build context changed")
    contract = {
        "contract_id": "ti.phase4c.personal-bank-user-counts-composition-contract",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "status": (
            "composition_and_migration_primitives_closed_"
            "http_neutral_implementation_authorized"
        ),
        "scope": "phase4c-personal-bank-user-counts-composition-gate",
        "legacy_commit": LEGACY_COMMIT,
        "predecessor": {
            "source": "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json",
            "sha256": predecessor_sha256,
            "accepted_commit": PHASE4B_ACCEPTED_COMMIT,
            "contract_id": predecessor["contract_id"],
            "status": predecessor["status"],
            "evidence_closed": predecessor["acceptance"]["evidence_closed"],
            "implementation_authorized": predecessor["acceptance"][
                "implementation_authorized"
            ],
        },
        "source_contracts": source_contracts,
        "historical_acceptance": {
            "accepted_commit": PHASE4B_ACCEPTED_COMMIT,
            "immutable_predecessor": {
                "source": (
                    "docs/refactor/phase4b/"
                    "personal-bank-user-counts-entry-contract.json"
                ),
                "sha256": PHASE4B_ENTRY_CONTRACT_ACCEPTED_SHA256,
            },
            "accepted_file_sha256": dict(sorted(PHASE4B_ACCEPTED_FILE_SHA256.items())),
            "successor_aware_test_files": dict(sorted(successor_files.items())),
            "successor_allowlist_exact": True,
            "arbitrary_source_hash_lookup_forbidden": True,
        },
        "ownership_overlay": {
            "resource_kind": "db_kv_namespace",
            "resource_name": NAMESPACE,
            "historical_owner": "personalbank",
            "phase4c_effective_owner": "learning",
            "physical_source_table": "user_progress",
            "physical_target_table": "user_question_tag_items",
            "physical_table_owner": "learning",
            "scope_only": True,
            "other_user_progress_namespaces_unchanged": True,
            "personalbank_tables_unchanged": [
                "user_question_banks",
                "user_bank_questions",
                "bank_shares",
                "bank_share_records",
            ],
            "dependency_direction": "learning -> personalbank::api",
            "reverse_dependency_forbidden": True,
        },
        "planned_public_api_shape": {
            "current_implemented_public_application_method_count": current_method_count,
            "authorized_future_method_count": current_method_count + 4,
            "learning": {
                "java_api": "io.saksk.ti.learning.api.LearningApplicationApi",
                "methods": [{
                    "name": "findPersonalBankUserCounts",
                    "return_type": (
                        "io.saksk.ti.learning.api.PersonalBankUserCountsResult"
                    ),
                    "parameter_types": [
                        "io.saksk.ti.learning.api.AuthenticatedLearningViewer",
                        "io.saksk.ti.learning.api.PersonalBankUserCountsQuery",
                    ],
                    "direct_http_operation": False,
                }],
                "immutable_types": {
                    "AuthenticatedLearningViewer": ["long identityId"],
                    "PersonalBankUserCountsQuery": [
                        "int bankId",
                        "String rawQuestionType",
                        "String rawSource",
                        "String rawTag",
                    ],
                    "PersonalBankUserCountsResult": [
                        "Outcome AVAILABLE|DENIED",
                        "Optional<PersonalBankUserCountsView> data",
                    ],
                    "PersonalBankUserCountsView": [
                        "long total",
                        "long favorites",
                        "long mistakes",
                        "List<String> types",
                        "boolean shuffleOptionsAvailable",
                    ],
                },
            },
            "personalbank": {
                "java_api": (
                    "io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi"
                ),
                "additional_public_api": True,
                "methods": [
                    {
                        "name": "checkQuestionAccess",
                        "return_type": (
                            "io.saksk.ti.personalbank.api."
                            "PersonalBankQuestionAccessResult"
                        ),
                        "parameter_types": [
                            "io.saksk.ti.personalbank.api."
                            "AuthenticatedPersonalBankViewer",
                            "int",
                        ],
                        "direct_http_operation": False,
                    },
                    {
                        "name": "summarizeQuestions",
                        "return_type": (
                            "io.saksk.ti.personalbank.api."
                            "PersonalBankQuestionFactsResult"
                        ),
                        "parameter_types": [
                            "io.saksk.ti.personalbank.api."
                            "AuthenticatedPersonalBankViewer",
                            "io.saksk.ti.personalbank.api."
                            "PersonalBankQuestionSelection",
                        ],
                        "direct_http_operation": False,
                    },
                    {
                        "name": "inspectQuestionMembership",
                        "return_type": (
                            "io.saksk.ti.personalbank.api."
                            "PersonalBankQuestionMembershipView"
                        ),
                        "parameter_types": [
                            "int",
                            "java.util.List<java.lang.Integer>",
                        ],
                        "direct_http_operation": False,
                    },
                ],
                "immutable_types": {
                    "PersonalBankQuestionSelection": [
                        "int bankId",
                        "Optional<String> portableType",
                        "Optional<List<Integer>> candidateQuestionIds",
                    ],
                    "PersonalBankQuestionAccessResult": [
                        "Outcome AVAILABLE|DENIED",
                    ],
                    "PersonalBankQuestionFactsResult": [
                        "Outcome AVAILABLE|DENIED",
                        "Optional<PersonalBankQuestionFactsView> data",
                    ],
                    "PersonalBankQuestionFactsView": [
                        "long total",
                        "List<PersonalBankQuestionTypeCount> rawTypes",
                    ],
                    "PersonalBankQuestionTypeCount": [
                        "Optional<String> rawType",
                        "long count",
                    ],
                    "PersonalBankQuestionMembershipView": [
                        "int bankId",
                        "boolean bankExists",
                        "List<Integer> existingQuestionIds",
                        "String membershipDigest",
                    ],
                },
                "immutability_and_validation": {
                    "records_are_top_level": True,
                    "lists_use_copy_of": True,
                    "optionals_are_non_null": True,
                    "ids_are_positive_except_definition_sentinel_not_exposed": True,
                    "counts_are_non_negative_long": True,
                    "facts_result_data_present_iff_available": True,
                    "membership_ids_are_positive_distinct_sorted": True,
                    "membership_digest": {
                        "algorithm": "SHA-256",
                        "encoding": "UTF-8",
                        "hex": "64 lowercase characters",
                        "canonical_json_key_order": [
                            "bank_id",
                            "bank_exists",
                            "existing_question_ids",
                        ],
                        "canonical_json_whitespace": "none",
                        "ids": "positive distinct ascending",
                        "example": (
                            '{"bank_id":7101,"bank_exists":true,'
                            '"existing_question_ids":[8101,8102]}'
                        ),
                    },
                },
                "selection_semantics": {
                    "bank_id": "required int",
                    "portable_type": "Optional.empty means no type restriction",
                    "candidate_question_ids_absent": "no candidate restriction",
                    "candidate_question_ids_present_empty": "determinate empty result",
                    "candidate_question_ids_nonempty": (
                        "positive immutable distinct sorted IDs bound as PostgreSQL integer[]"
                    ),
                },
                "summary_semantics": (
                    "provider-owned raw type buckets and bigint counts only; null/empty "
                    "raw types remain countable but are omitted by learning display mapping"
                ),
                "forbidden_exposure": [
                    "persistence entities or repositories",
                    "SQL rows, maps or infrastructure types",
                    "question content, answer or analysis",
                    "learning-owned favorites, mistakes, progress or tag facts",
                ],
            },
        },
        "request_normalization": {
            "duplicate_query_keys": "HTTP adapter takes the first value",
            "q_type": (
                "trim; case-insensitive all becomes absent; every other nonempty value "
                "uses frozen portable-type normalization and unknown becomes essay"
            ),
            "source": (
                "trim; only exact lowercase favorites and mistakes are special; all "
                "other values use ALL"
            ),
            "tag": (
                "trim; empty or exact lowercase all bypasses tag lookup; matching is "
                "otherwise case-sensitive"
            ),
            "tag_question_ids": (
                "positive parsed IDs are distinct and sorted; a present tag with no "
                "IDs enters a mandatory personalbank access recheck, then returns "
                "the zero view before optional statistics queries"
            ),
            "no_pagination_or_time_window": True,
            "evidence_boundary_900_is_not_a_production_limit": True,
        },
        "orchestration": {
            "owner": "learning",
            "outer_transaction": "NOT_SUPPORTED; no cross-module database transaction",
            "ordered_stages": [
                {
                    "stage": "access",
                    "failure": "hard",
                    "provider": "personalbank::api",
                },
                {
                    "stage": "tag_membership",
                    "failure": "infrastructure/query failure becomes empty candidate set",
                    "provider": "learning local port",
                    "only_when": "raw tag is nonempty and not exact lowercase all",
                },
                {
                    "stage": "zero_view_access_recheck",
                    "failure": "hard; DENIED is terminal and query failure propagates",
                    "provider": "personalbank::api#checkQuestionAccess",
                    "only_when": "tag lookup is empty or failed",
                    "available": "return zero view before optional statistics queries",
                    "denied": "return terminal DENIED without data",
                },
                {
                    "stage": "total",
                    "failure": "hard",
                    "source_membership": (
                        "strict favorites/mistakes local read only for matching source"
                    ),
                    "facts": "personalbank summary with access recheck",
                },
                {
                    "stage": "favorites",
                    "failure": "field fallback 0",
                    "provider": "personalbank::api#summarizeQuestions",
                    "denied": "terminal DENIED; discard every partial field",
                    "fail_soft_scope": "infrastructure/query exception only, never DENIED",
                    "transaction": "independent module-local REQUIRES_NEW read-only",
                },
                {
                    "stage": "mistakes",
                    "failure": "field fallback 0",
                    "provider": "personalbank::api#summarizeQuestions",
                    "denied": "terminal DENIED; discard every partial field",
                    "fail_soft_scope": "infrastructure/query exception only, never DENIED",
                    "transaction": "independent module-local REQUIRES_NEW read-only",
                },
                {
                    "stage": "types",
                    "failure": "field fallback [] and shuffle false",
                    "provider": "personalbank::api#summarizeQuestions",
                    "denied": "terminal DENIED; discard every partial field",
                    "fail_soft_scope": "infrastructure/query exception only, never DENIED",
                    "source_membership": (
                        "fresh favorites/mistakes local read only for matching source"
                    ),
                    "transaction": "independent module-local REQUIRES_NEW read-only",
                },
            ],
            "source_sequences": {
                "ALL": ["all-total", "favorites", "mistakes", "all-types"],
                "FAVORITES": [
                    "favorites-total",
                    "favorites-again",
                    "mistakes",
                    "favorites-types",
                ],
                "MISTAKES": [
                    "mistakes-total",
                    "favorites",
                    "mistakes-again",
                    "mistakes-types",
                ],
            },
            "early_return_access_recheck": {
                "required_before": [
                    "tag membership is determinately empty",
                    "tag membership failure falls back to empty",
                    "any zero-view return before total facts",
                ],
                "provider": "personalbank::api#checkQuestionAccess",
                "denied": "terminal DENIED and discard every partial result",
                "infrastructure_failure": "hard failure; zero-view return is forbidden",
            },
            "learning_owned_relations": [
                "user_bank_favorites",
                "user_bank_mistakes",
                "user_progress",
                "user_question_tag_items",
            ],
            "personalbank_owned_relations": [
                "user_question_banks",
                "bank_shares",
                "bank_share_records",
                "user_bank_questions",
            ],
            "cross_module_transaction": False,
            "n_plus_one_authorized": False,
            "authorization_outcome": {
                "denied_is_terminal_for_every_personalbank_call": True,
                "discard_partial_result_on_denied": True,
                "fail_soft_never_applies_to_denied": True,
                "tag_zero_view_requires_personalbank_access_recheck": True,
            },
        },
        "result_semantics": {
            "access_denied": "DENIED without data; future HTTP adapter maps to legacy 403",
            "count_jdbc_type": "PostgreSQL int8 mapped to Java long",
            "raw_type_order": "SQL raw q.type ascending before display mapping",
            "raw_null_or_empty_type": "counted but omitted from types",
            "unknown_raw_type": "简答题",
            "post_mapping_deduplication": False,
            "shuffle_options_available": (
                "types is nonempty and every mapped type is 选择题 or 多选题"
            ),
            "http_envelope_outside_application_api": True,
        },
        "explicit_bank_tag_migration": {
            "owner": "learning",
            "execution": "operator-only one-shot job; startup and HTTP invocation forbidden",
            "default_mode": "dry-run",
            "source": {
                "table": "user_progress",
                "namespace_regex": "^bank_[1-9][0-9]*_tags$",
                "key_round_trip_required": True,
                "source_mutation_or_deletion": False,
            },
            "target": {
                "table": "user_question_tag_items",
                "scope": "user_bank",
                "scope_id": "bank ID parsed from p_key",
                "target_delete_or_update": False,
                "insert": (
                    "full primary key with ON CONFLICT "
                    "(user_id, scope, scope_id, question_id, tag) DO NOTHING"
                ),
            },
            "legacy_mapping": {
                "root": "JSON object",
                "tags": (
                    "missing becomes empty; present list is parsed; present non-list "
                    "or non-string list item is invalid and blocks production apply"
                ),
                "question_tags": (
                    "missing becomes empty; present object is parsed; present "
                    "non-object is invalid and blocks production apply; each value is "
                    "a string list, JSON-array string or comma-separated string"
                ),
                "tag_cleaning": [
                    "legacy normalize_tags",
                    "trim",
                    "truncate to 20 Unicode code points",
                    "trim again",
                    "drop empty and case-insensitive all",
                    "case-sensitive first-occurrence deduplication",
                    "distinct pre-truncation values collapsing to one tag are invalid",
                ],
                "tag_cleaning_collision": (
                    "one raw tag preserves legacy 20-code-point truncation; distinct "
                    "raw values that collide after cleaning or truncation are an "
                    "explicit invalid disposition and block production apply"
                ),
                "definitions": "merged tags use question_id=0",
                "bindings": (
                    "legacy int-compatible positive IDs are canonicalized; parse, "
                    "nonpositive and normalized-ID conflicts are explicit invalid "
                    "dispositions in production preflight"
                ),
                "scope": "user_bank",
            },
            "membership_validation": {
                "provider": "personalbank::api#inspectQuestionMembership",
                "bank_must_exist": True,
                "question_must_belong_to_bank": True,
                "catalog_dependency": False,
                "unresolved_or_orphan_blocks_apply": True,
            },
            "target_precedence": {
                "existing_scope_rows_prevent_automatic_writes": True,
                "precedence_requires_valid_source_plan": True,
                "source_plan_must_be_subset_of_target": True,
                "target_tags_must_be_canonical": True,
                "positive_target_questions_must_belong_to_bank": True,
                "automatic_merge": False,
                "source_not_subset_of_target": "target_conflict blocks cutover",
            },
            "target_absence_after_prior_migration": {
                "ambiguous_without_durable_marker": True,
                "test_primitive_behavior": (
                    "retained compatibility source can repopulate an emptied target"
                ),
                "operator_requirement": (
                    "a durable migration ledger/version or equivalent tombstone must "
                    "distinguish never-migrated state from intentional target deletion"
                ),
                "operator_design_closed": False,
            },
            "transaction": {
                "global_single_runner": (
                    "dedicated connection holds one session-level PostgreSQL advisory "
                    "lock across the complete preflight and every row transaction"
                ),
                "unit_of_work": "one user_progress source row",
                "source_lock": "SELECT FOR UPDATE",
                "isolation": "SERIALIZABLE",
                "test_primitive_retry": False,
                "production_operator_retry_requirement": (
                    "bounded retry for SQLSTATE 40001 and 40P01"
                ),
                "failure": (
                    "attempt rollback for a pre-commit failure; only a successful rollback "
                    "or a non-ambiguous SQLSTATE proves zero committed rows after writes; "
                    "rollback failure is orthogonal, while SQLSTATE class 08, 40003 or an "
                    "absent SQLSTATE during commit after changed rows remains unknown"
                ),
                "operator_design_status": (
                    "not closed until write freezes/version rechecks and global blocker "
                    "aggregation are independently evidenced"
                ),
            },
            "row_outcomes": [
                "MIGRATED",
                "EMPTY_NOOP",
                "TARGET_ALREADY_PRESENT",
                "TARGET_CONFLICT",
                "INVALID_KEY",
                "INVALID_DATA",
                "BANK_MISSING",
                "ORPHAN_QUESTION",
                "SOURCE_DISAPPEARED",
                "FAILED_ROLLED_BACK",
                "ROLLBACK_FAILED",
                "COMMIT_OUTCOME_UNKNOWN",
            ],
            "reporting_groups": {
                "eligible": [
                    "MIGRATED",
                    "EMPTY_NOOP",
                    "TARGET_ALREADY_PRESENT",
                ],
                "conflict": ["TARGET_CONFLICT"],
                "invalid": ["INVALID_KEY", "INVALID_DATA"],
                "unresolved": [
                    "BANK_MISSING",
                    "ORPHAN_QUESTION",
                    "SOURCE_DISAPPEARED",
                ],
                "transaction_failed": [
                    "FAILED_ROLLED_BACK",
                    "ROLLBACK_FAILED",
                    "COMMIT_OUTCOME_UNKNOWN",
                ],
            },
            "apply_preconditions": [
                "legacy source bank-tag writes are frozen",
                "normalized target tag writes are frozen or use a common version/lock protocol",
                "personalbank bank/question membership writes are frozen or digest-revalidated",
                "dry-run unresolved/conflict/orphan/invalid counts are zero or approved",
                "backup and rollback evidence exists",
            ],
            "idempotency": (
                "an immediate second execution while normalized target rows remain performs "
                "zero DML; deletion/tombstone behavior requires a durable migration marker"
            ),
            "get_runtime_ddl": False,
            "get_runtime_dml": False,
            "production_schema_or_index_delta": False,
            "real_data_execution_authorized": False,
        },
        "approved_differences": {
            "source": "docs/refactor/phase4c/approved-differences.md",
            "ids": approved_difference_ids,
        },
        "migration_evidence": {
            "scope": (
                "test-only row-transaction primitive and PostgreSQL compatibility "
                "evidence; not a complete operator run"
            ),
            "postgresql_versions": ["16.14", "18.4"],
            "proves": [
                "strict namespace selection",
                "strict JSON rejects duplicate object keys and trailing tokens",
                "Python-compatible Unicode whitespace normalization",
                "invalid raw field, normalized-ID and truncation conflicts become blockers",
                "legacy JSON-array-string and comma-separated tag values are normalized",
                "target precedence only after a valid source plan is proven a target subset",
                "proper-subset target evidence and source drift target_conflict",
                "target tag canonicality and positive-question bank membership validation",
                "source-row lock and per-row atomic rollback",
                (
                    "rollback failure is tracked orthogonally and only ambiguous "
                    "post-write commit outcomes remain unknown"
                ),
                "insert-only ON CONFLICT statement is accepted and executed",
                "second fixture sweep is zero DML through target precedence",
                "source, non-target namespace, schema and index fingerprints unchanged",
            ],
            "does_not_prove": [
                "global dry-run/preflight or all-or-block apply decision",
                "global aggregation and approval of invalid or target-conflict dispositions",
                "real network commit-response loss or ambiguous commit recovery",
                "concurrent lock contention or ON CONFLICT race resolution",
                "post-migration target deletion, tombstones or durable migration-ledger behavior",
                "connection acquisition, setup or close failure aggregation across the sweep",
                "source, normalized-target and membership write-freeze protocol",
                "production data cleanliness or scale",
                "production operator credentials or backup readiness",
                "production implementation completion",
                "HTTP parity or production cutover",
            ],
        },
        "security_access_policy": {
            "cross_bank_share_coherence_closed": True,
            "requested_bank_join_required": True,
            "share_record_bank_and_share_bank_must_match": True,
            "valid_grant_selection": (
                "any deterministic same-bank active grant with a null or strictly future "
                "Beijing-local expiry grants read access"
            ),
            "allowed_share_permissions": ["read", "copy"],
            "unknown_or_null_permission": "deny",
            "equal_expiry_is_denied": True,
            "cross_bank_fixture_expected_outcome": "DENIED",
            "multiple_share_rows_are_not_fetchone_order_dependent": True,
            "source_evidence": (
                "phase4b golden access-shared-cross-bank-record and "
                "access-shared-fetchone-first-row"
            ),
        },
        "production_baseline": {
            "implemented_public_application_method_count": current_method_count,
            "migrated_route_count": route_counts["migrated"],
            "pending_route_count": route_counts["pending"],
            "production_cutover_count": effective_route[
                "production_cutover_operation_count"
            ],
            "learning_and_personalbank_main_source_manifest": main_source_manifest(),
            "accepted_commit": PHASE4B_ACCEPTED_COMMIT,
            "java_build_context_sha256": build_context_sha256,
            "production_runtime_surface": runtime_surface,
            "route_status_surface": route_surface,
            "production_runtime_surface_scope": [
                "server/src/main/**",
                "server/pom.xml",
                "server/Dockerfile",
                "server/.dockerignore",
                "server/.mvn/**",
                "server/mvnw",
                "server/mvnw.cmd",
                "server/build-versions.properties",
                "compose.dev.yml",
                ".env.example",
                "contracts/**",
                "openapi/**",
            ],
            "route_rule_count": len(route_rows),
            "expanded_route_operation_count": effective_route[
                "expanded_operation_count"
            ],
        },
        "worm_successor_evidence": {
            "status": "versioned_successor_tip_verified_historical_reports_immutable",
            "historical_anchor": {
                "phase2_source": historical_worm["source"],
                "phase4b_copy_source": phase4b_historical_worm["source"],
                "sha256": PHASE4B_WORM_REPORT_SHA256,
            },
            "current_tip": {
                "source": phase4c_worm["source"],
                "sha256": PHASE4C_ENTRY_WORM_REPORT_SHA256,
                "java_build_context_sha256": (
                    PHASE4C_ENTRY_JAVA_BUILD_CONTEXT_SHA256
                ),
                "dockerfile_sha256": phase4c_worm_document["java"][
                    "dockerfileSha256"
                ],
                "postgresql_version": phase4c_worm_document["restore"][
                    "serverVersion"
                ],
                "public_base_tables": phase4c_worm_document["restore"][
                    "publicBaseTables"
                ],
                "public_columns": phase4c_worm_document["restore"][
                    "publicColumns"
                ],
                "readiness_passed": phase4c_worm_document["java"][
                    "readinessPassed"
                ],
            },
            "fixed_allowlist_gate": source_contracts[
                "phase2_worm_successor_gate"
            ]["source"],
            "arbitrary_report_lookup_forbidden": True,
            "runner_requires_explicit_versioned_report": True,
            "historical_report_overwrite_forbidden": True,
        },
        "successor_handoff": {
            "phase4b_entry_test": (
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py"
            ),
            "phase4b_test_is_successor_aware": True,
            "future_read_contract": (
                "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
            ),
            "future_read_contract_requirements": {
                "contract_id": "ti.phase4c.personal-bank-user-counts-read-contract",
                "status": "implemented_and_targeted_verified_http_aliases_deferred",
                "predecessor_source": (
                    "docs/refactor/phase4c/"
                    "personal-bank-user-counts-composition-contract.json"
                ),
                "document_payload_sha256_required": True,
                "exact_main_source_scope": ["learning", "personalbank"],
                "implemented_public_application_method_count": (
                    current_method_count + 4
                ),
                "expected_changed_main_sources": [
                    (
                        "server/src/main/java/io/saksk/ti/learning/api/"
                        "LearningApplicationApi.java"
                    ),
                ],
                "expected_added_main_sources": {
                    (
                        "server/src/main/java/io/saksk/ti/learning/api/"
                        "AuthenticatedLearningViewer.java"
                    ): ["publicrecordAuthenticatedLearningViewer(longidentityId)"],
                    (
                        "server/src/main/java/io/saksk/ti/learning/api/"
                        "PersonalBankUserCountsQuery.java"
                    ): [
                        "publicrecordPersonalBankUserCountsQuery(intbankId,"
                        "StringrawQuestionType,StringrawSource,StringrawTag)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/learning/api/"
                        "PersonalBankUserCountsResult.java"
                    ): [
                        "publicrecordPersonalBankUserCountsResult(Outcomeoutcome,"
                        "Optional<PersonalBankUserCountsView>data)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/learning/api/"
                        "PersonalBankUserCountsView.java"
                    ): [
                        "publicrecordPersonalBankUserCountsView(longtotal,"
                        "longfavorites,longmistakes,List<String>types,"
                        "booleanshuffleOptionsAvailable)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionFactsApi.java"
                    ): [
                        "PersonalBankQuestionAccessResultcheckQuestionAccess("
                        "AuthenticatedPersonalBankViewerviewer,intbankId);",
                        "PersonalBankQuestionFactsResultsummarizeQuestions("
                        "AuthenticatedPersonalBankViewerviewer,"
                        "PersonalBankQuestionSelectionselection);",
                        "PersonalBankQuestionMembershipViewinspectQuestionMembership("
                        "intbankId,List<Integer>questionIds);",
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionSelection.java"
                    ): [
                        "publicrecordPersonalBankQuestionSelection(intbankId,"
                        "Optional<String>portableType,"
                        "Optional<List<Integer>>candidateQuestionIds)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionAccessResult.java"
                    ): [
                        "publicrecordPersonalBankQuestionAccessResult(Outcomeoutcome)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionFactsResult.java"
                    ): [
                        "publicrecordPersonalBankQuestionFactsResult(Outcomeoutcome,"
                        "Optional<PersonalBankQuestionFactsView>data)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionFactsView.java"
                    ): [
                        "publicrecordPersonalBankQuestionFactsView(longtotal,"
                        "List<PersonalBankQuestionTypeCount>rawTypes)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionTypeCount.java"
                    ): [
                        "publicrecordPersonalBankQuestionTypeCount("
                        "Optional<String>rawType,longcount)"
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/api/"
                        "PersonalBankQuestionMembershipView.java"
                    ): [
                        "publicrecordPersonalBankQuestionMembershipView(intbankId,"
                        "booleanbankExists,List<Integer>existingQuestionIds,"
                            "StringmembershipDigest)"
                        ],
                    (
                        "server/src/main/java/io/saksk/ti/learning/application/"
                        "PersonalBankUserCountsService.java"
                    ): [
                        "implementsLearningApplicationApi",
                        "Propagation.NOT_SUPPORTED",
                        "findPersonalBankUserCounts",
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/learning/application/port/"
                        "PersonalBankUserCountsQueryPort.java"
                    ): [
                        "findQuestionIdsByTag",
                        "findFavoriteQuestionIds",
                        "findMistakeQuestionIds",
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        "persistence/JdbcPersonalBankUserCountsQueryAdapter.java"
                    ): [
                        "implementsPersonalBankUserCountsQueryPort",
                        "Propagation.REQUIRES_NEW",
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/application/"
                        "PersonalBankQuestionFactsService.java"
                    ): [
                        "implementsPersonalBankQuestionFactsApi",
                        "checkQuestionAccess",
                        "summarizeQuestions",
                        "inspectQuestionMembership",
                        "Propagation.REQUIRES_NEW",
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/application/port/"
                        "PersonalBankQuestionFactsQueryPort.java"
                    ): [
                        "findAccess",
                        "summarizeQuestions",
                        "inspectQuestionMembership",
                    ],
                    (
                        "server/src/main/java/io/saksk/ti/personalbank/infrastructure/"
                        "persistence/JdbcPersonalBankQuestionFactsQueryAdapter.java"
                    ): [
                        "implementsPersonalBankQuestionFactsQueryPort",
                        "user_question_banks",
                        "user_bank_questions",
                    ],
                },
                "changed_source_compact_java_fragments": {
                    (
                        "server/src/main/java/io/saksk/ti/learning/api/"
                        "LearningApplicationApi.java"
                    ): [
                        "PersonalBankUserCountsResultfindPersonalBankUserCounts("
                        "AuthenticatedLearningViewerviewer,"
                        "PersonalBankUserCountsQueryquery);"
                    ],
                },
                "required_verification_sources": {
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
                        "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                        "persistence/JdbcPersonalBankUserCountsQueryAdapterTest.java"
                    ),
                    "personalbank_adapter_test": (
                        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
                        "persistence/JdbcPersonalBankQuestionFactsQueryAdapterTest.java"
                    ),
                    "postgresql_compatibility_it": (
                        "server/src/test/java/io/saksk/ti/integration/"
                        "Phase4cPersonalBankUserCountsJdbcCompatibilityIT.java"
                    ),
                },
                "required_verification_test_methods": {
                    "api_shape_contract_parity_test": [
                        "exposesExactTwentySevenMethodHttpNeutralShape",
                        "keepsLearningToPersonalbankApiDependencyOneWay",
                    ],
                    "learning_composition_test": [
                        "rechecksAccessBeforeReturningZeroView",
                        "deniedFromAnyPersonalbankCallIsTerminal",
                        "optionalFailuresRemainFieldLocal",
                        "preservesOrderedLegacyQuerySequence",
                    ],
                    "personalbank_facts_service_test": [
                        "rejectsCrossBankShareGrant",
                        "selectsDeterministicValidSameBankGrant",
                        "rechecksAccessForEveryFactsCall",
                    ],
                    "learning_adapter_test": [
                        "bindsCandidateIdsAsSinglePostgresqlIntegerArray",
                        "keepsOptionalQueriesInIndependentReadOnlyTransactions",
                    ],
                    "personalbank_adapter_test": [
                        "joinsShareRecordToRequestedBank",
                        "preservesMembershipDigestAndTypedIds",
                    ],
                    "postgresql_compatibility_it": [
                        "runsOnPostgres16And18",
                        "recoversFromTwentyFiveP02WithIndependentTransactions",
                        "preservesSchemaAndBusinessRows",
                    ],
                },
                "required_behavior_evidence": {
                    "tag_zero_view_access_recheck": True,
                    "denied_is_terminal_at_every_personalbank_call": True,
                    "optional_query_failures_are_field_local": True,
                    "ordered_source_sequences_match_legacy": True,
                    "candidate_ids_use_typed_postgresql_integer_array": True,
                    "no_cross_module_transaction": True,
                    "postgresql_versions": ["16.14", "18.4"],
                    "postgresql_25p02_recovery_uses_independent_transactions": True,
                    "schema_and_business_rows_unchanged": True,
                    "cross_bank_share_coherence_closed": True,
                    "deterministic_share_grant_selection": True,
                    "unknown_share_permission_denied": True,
                },
                "production_surface_delta": {
                    "baseline_manifest_sha256": (
                        PHASE4C_ENTRY_PRODUCTION_SURFACE_MANIFEST_SHA256
                    ),
                    "baseline_java_build_context_sha256": (
                        PHASE4C_ENTRY_JAVA_BUILD_CONTEXT_SHA256
                    ),
                    "exact_changed_or_added_main_sources": (
                        1 + 17
                    ),
                    "main_source_deletions": 0,
                    "main_resources_delta": 0,
                    "http_security_openapi_route_schema_deployment_delta": 0,
                },
                "forbidden_authorizations": [
                    "real_data_migration_execution",
                    "operator_migration_implementation",
                    "migration_global_preflight_evidence_closed",
                    "http_controller",
                    "security_or_rate_limit",
                    "route_or_openapi_delta",
                    "production_schema_or_index",
                    "production_cutover",
                ],
                "operator_migration_implementation_requires": (
                    "migration_global_preflight_evidence_closed"
                ),
            },
            "historical_hash_overrides": main_source_manifest(),
            "read_contract_must_bind_current_main_sources": True,
        },
        "forward_handoff": {
            "historical_acceptance": {
                "accepted_commit": PHASE4B_ACCEPTED_COMMIT,
                "chain_anchor": (
                    "docs/refactor/phase4b/"
                    "personal-bank-share-list-read-contract.json"
                ),
                "immutable_predecessor_sha256": (
                    PHASE4B_ENTRY_CONTRACT_ACCEPTED_SHA256
                ),
            },
            "forward_additions": sorted(PHASE4C_FORWARD_ADDITIONS),
            "historical_hash_overrides": dict(
                sorted(WORM_HISTORICAL_HASH_OVERRIDES.items())
            ),
        },
        "route_status": {
            "operations": [
                {
                    **route,
                    "baseline_target_module": "personalbank",
                    "reviewed_owner": "learning",
                    "migration_status": "pending",
                    "production_cutover": False,
                }
                for route in ROUTES
            ],
            "controller_added": False,
            "security_matcher_added": False,
            "route_delta_added": False,
            "openapi_delta_added": False,
        },
        "change_budget": {
            "production_java_files_added": 0,
            "production_java_files_modified": 0,
            "http_controllers_added": 0,
            "application_methods_added": 0,
            "production_schema_files_added": 0,
            "production_indexes_added": 0,
            "route_delta_rows_added": 0,
            "openapi_operations_migrated": 0,
            "production_cutover_operations": 0,
            "ownership_overrides": 1,
            "test_only_java_files_added": 4,
            "test_only_sql_fixtures_added": 2,
            "historical_contract_files_modified": 0,
            "successor_aware_python_tests_modified": 6,
            "successor_aware_java_tests_modified": 3,
            "project_readme_files_modified": 1,
            "successor_bridge_python_files_added": 1,
            "successor_bridge_java_files_added": 1,
            "phase2_worm_successor_files_added": 1,
            "phase2_worm_successor_tests_added": 1,
            "versioned_worm_reports_added": 1,
            "phase2_verification_files_modified": 2,
            "phase2_readme_files_modified": 1,
            "phase1_verification_files_modified": 1,
            "production_surface_manifest_sha256": (
                PHASE4C_ENTRY_PRODUCTION_SURFACE_MANIFEST_SHA256
            ),
            "java_build_context_sha256": PHASE4C_ENTRY_JAVA_BUILD_CONTEXT_SHA256,
        },
        "authorization": {
            "composition_contract_closed": True,
            "ownership_conflict_closed": True,
            "migration_design_closed": False,
            "migration_row_primitive_design_closed": True,
            "migration_row_transaction_primitive_evidence_closed": True,
            "migration_global_preflight_evidence_closed": False,
            "http_neutral_java_implementation": True,
            "operator_migration_implementation": False,
            "real_data_migration_execution": False,
            "http_controller": False,
            "security_or_rate_limit": False,
            "route_or_openapi_delta": False,
            "production_schema_or_index": False,
            "production_cutover": False,
        },
        "acceptance": {
            "passed": True,
            "next_gate": (
                "implement_http_neutral_learning_composition_while_operator_"
                "global_preflight_remains_blocked"
            ),
            "future_shape_method_count": current_method_count + 4,
            "routes_remain_pending": True,
            "production_cutover": False,
        },
    }
    return contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    delta_path, effective_path = write_ownership_overlay(output_dir)
    contract = build_contract(output_dir, delta_path, effective_path)
    write_json(
        output_dir / "personal-bank-user-counts-composition-contract.json",
        contract,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
