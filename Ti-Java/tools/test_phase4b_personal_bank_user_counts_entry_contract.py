#!/usr/bin/env python3
"""Fail-closed checks for the personal-bank user-counts entry-only contract."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import unittest

try:
    from tools.phase4c_successor_acceptance import (
        ACCEPTED_COMMIT,
        ACCEPTED_PREDECESSOR_SHA256,
        load_successor_contract,
    )
    from tools.phase4c_read_successor_acceptance import (
        load_composition_predecessor_contract,
        load_read_successor_contract,
        successor_sha256,
    )
    from tools.phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as implementation_accepted_sha256,
        fixed_source_sha256 as implementation_fixed_source_sha256,
        load_http_implementation_successor_contract,
        successor_sha256 as implementation_successor_sha256,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase4c_successor_acceptance import (
        ACCEPTED_COMMIT,
        ACCEPTED_PREDECESSOR_SHA256,
        load_successor_contract,
    )
    from phase4c_read_successor_acceptance import (
        load_composition_predecessor_contract,
        load_read_successor_contract,
        successor_sha256,
    )
    from phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as implementation_accepted_sha256,
        fixed_source_sha256 as implementation_fixed_source_sha256,
        load_http_implementation_successor_contract,
        successor_sha256 as implementation_successor_sha256,
    )


ROOT = Path(__file__).resolve().parents[1]
PHASE4B = ROOT / "docs/refactor/phase4b"
CONTRACT_PATH = PHASE4B / "personal-bank-user-counts-entry-contract.json"
PREDECESSOR_PATH = PHASE4B / "personal-bank-usage-stats-read-contract.json"
SHAPE_PATH = PHASE4B / "personal-bank-usage-stats-application-api-shape.json"
CALLERS_PATH = PHASE4B / "personal-bank-user-counts-callers.json"
GOLDEN_PATH = PHASE4B / "golden-personal-bank-user-counts-reads.json"
PLAN_PATH = PHASE4B / "personal-bank-user-counts-query-plan-evidence.json"
MATRIX_PATH = ROOT / "docs/refactor/02-route-parity-matrix.csv"
EFFECTIVE_PATH = ROOT / "docs/refactor/phase4a/effective-route-parity-status.json"
OWNERSHIP_PATH = ROOT / "docs/refactor/03-data-ownership.csv"
MODULES_PATH = ROOT / "docs/refactor/phase1/module-contracts.json"
OPENAPI_PATH = ROOT / "contracts/openapi.json"
ROUTE_DELTA_PATH = ROOT / "docs/refactor/phase4a/route-parity-delta.csv"
PHASE4C_COMPOSITION_PATH = (
    ROOT / "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)
ROUTE_KEYS = {
    "6858f6fa506f|GET|/api/user/banks/api/<int:bank_id>/user-counts",
    "006913d0d956|GET|/user/banks/api/<int:bank_id>/user-counts",
}
OPENAPI_PATHS = {
    "6858f6fa506f": "/api/user/banks/api/{bank_id}/user-counts",
    "006913d0d956": "/user/banks/api/{bank_id}/user-counts",
}
PERSONALBANK_TABLES = {
    "user_question_banks",
    "bank_shares",
    "bank_share_records",
    "user_bank_questions",
}
LEARNING_TABLES = {
    "user_bank_favorites",
    "user_bank_mistakes",
    "user_progress",
    "user_question_tag_items",
}
EXPECTED_PERSONALBANK_METHODS = {
    "listCategories",
    "findShares",
    "listOwnedShares",
    "findUsageStats",
}
QUERY_IDS = [
    "personal-bank-user-counts-bank-access",
    "personal-bank-user-counts-share-access",
    "personal-bank-user-counts-all-count",
    "personal-bank-user-counts-favorites-count",
    "personal-bank-user-counts-mistakes-count",
    "personal-bank-user-counts-all-types",
    "personal-bank-user-counts-favorites-types",
    "personal-bank-user-counts-mistakes-types",
]
FORWARD_PATHS = {
    "Ti-Java/docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json",
    "Ti-Java/tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict) -> str:
    return sha256_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    })


def python_test_count(path: Path) -> int:
    return len(re.findall(
        r"^\s+def test_[A-Za-z0-9_]+\(",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    ))


def java_test_count(path: Path) -> int:
    return len(re.findall(
        r"^\s+@Test\s*$",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    ))


def learning_and_personalbank_main_source_manifest() -> dict[str, str]:
    root = ROOT / "server/src/main/java/io/saksk/ti"
    paths = []
    for module in ("learning", "personalbank"):
        paths.extend((root / module).rglob("*.java"))
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


def compact_java_code(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", "", source)
    return re.sub(r"\s+", "", source)


def file_manifest(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
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


def junit_test_methods(path: Path) -> set[str]:
    return set(re.findall(
        r"@Test\s+(?:public\s+|private\s+|protected\s+)?void\s+([A-Za-z0-9_]+)\s*\(",
        path.read_text(encoding="utf-8"),
    ))


class Phase4bPersonalBankUserCountsEntryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phase4c_read = load_read_successor_contract(ROOT)
        cls.contract = load_json(CONTRACT_PATH)
        cls.predecessor = load_json(PREDECESSOR_PATH)
        cls.shape = load_json(SHAPE_PATH)
        cls.callers = load_json(CALLERS_PATH)
        cls.golden = load_json(GOLDEN_PATH)
        cls.plan = load_json(PLAN_PATH)
        cls.effective = load_json(EFFECTIVE_PATH)
        cls.modules = load_json(MODULES_PATH)
        cls.openapi = load_json(OPENAPI_PATH)
        cls.phase4c_composition = (
            load_composition_predecessor_contract(ROOT)
            if cls.phase4c_read is not None
            else load_successor_contract(ROOT)
        )
        if cls.phase4c_composition is None:
            raise AssertionError("Phase4C composition contract is required")
        cls.http_implementation = load_http_implementation_successor_contract(ROOT)
        if cls.http_implementation is None:
            raise AssertionError("Phase4C HTTP implementation contract is required")

    def test_01_identity_predecessor_sources_payload_and_forward_handoff_close(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-user-counts-entry-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "evidence_closed_but_production_implementation_blocked_pending_learning_composition",
            contract["status"],
        )
        self.assertEqual(
            "personal-bank-user-counts-entry-only-boundary-decision",
            contract["scope"],
        )
        self.assertEqual(
            "700006dfdfa063deb4387be572911e782bcea0d9",
            contract["legacy_commit"],
        )

        predecessor = contract["predecessor"]
        self.assertEqual(
            "docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json",
            predecessor["source"],
        )
        self.assertEqual(sha256(PREDECESSOR_PATH), predecessor["sha256"])
        self.assertEqual(self.predecessor["status"], predecessor["status"])
        self.assertTrue(predecessor["usage_stats_internal_read_closed"])
        self.assertFalse(predecessor["usage_stats_http_aliases_migrated"])
        self.assertFalse(predecessor["production_cutover"])
        self.assertTrue(FORWARD_PATHS.issubset(set(
            self.predecessor["forward_handoff"]["forward_additions"]
        )))

        for name, reference in contract["source_contracts"].items():
            source = ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            if name == "entry_contract_test":
                relative = reference["source"]
                self.assertEqual(
                    self.phase4c_composition["historical_acceptance"]
                    ["accepted_file_sha256"][relative],
                    reference["sha256"],
                )
                composition_handoff = self.phase4c_composition[
                    "historical_acceptance"
                ]["successor_aware_test_files"][relative]
                self.assertEqual(
                    reference["sha256"], composition_handoff["accepted_sha256"], name
                )
                read_handoff = self.phase4c_read[
                    "historical_successor_acceptance"
                ]["python_sources"][relative]
                self.assertEqual(
                    composition_handoff["successor_sha256"],
                    read_handoff["accepted_sha256"],
                    name,
                )
                self.assertEqual(
                    read_handoff["successor_sha256"],
                    implementation_accepted_sha256(relative),
                    name,
                )
                self.assertEqual(
                    sha256(source), implementation_successor_sha256(ROOT, relative), name
                )
                self.assertNotEqual(reference["sha256"], sha256(source), name)
            else:
                self.assertEqual(reference["sha256"], sha256(source), name)
        self.assertEqual(
            contract["document_payload_sha256"],
            document_payload_sha256(contract),
        )
        successor = self.phase4c_composition
        self.assertEqual(
            "ti.phase4c.personal-bank-user-counts-composition-contract",
            successor["contract_id"],
        )
        self.assertEqual(
            "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json",
            successor["predecessor"]["source"],
        )
        self.assertEqual(ACCEPTED_COMMIT, successor["predecessor"]["accepted_commit"])
        self.assertEqual(ACCEPTED_PREDECESSOR_SHA256, sha256(CONTRACT_PATH))
        self.assertEqual(sha256(CONTRACT_PATH), successor["predecessor"]["sha256"])
        self.assertEqual(contract["contract_id"], successor["predecessor"]["contract_id"])

    def test_02_application_shape_stays_at_23_and_production_java_is_unchanged(self):
        baseline = self.contract["production_baseline"]
        self.assertEqual(23, baseline["implemented_public_application_method_count"])
        self.assertEqual(
            23, self.shape["implemented_public_application_method_count"]
        )
        self.assertEqual(
            EXPECTED_PERSONALBANK_METHODS,
            {method["name"] for method in self.shape["personalbank"]["methods"]},
        )
        self.assertEqual(
            EXPECTED_PERSONALBANK_METHODS,
            set(baseline["personalbank_application_methods"]),
        )
        self.assertFalse(self.contract["entry_decision"]["implementation_authorized"])
        self.assertEqual(
            self.predecessor["implementation"]["personalbank_main_source_manifest"],
            baseline["personalbank_main_source_manifest"],
        )
        production_root = ROOT / "server/src/main/java/io/saksk/ti"
        if self.phase4c_read is None:
            for relative, expected_hash in baseline[
                "personalbank_main_source_manifest"
            ].items():
                self.assertEqual(expected_hash, sha256(ROOT / relative), relative)
            self.assertEqual([], list(production_root.rglob("*UserCounts*.java")))
            api_source = (
                ROOT / "server/src/main/java/io/saksk/ti/personalbank/api/"
                "PersonalBankApplicationApi.java"
            ).read_text(encoding="utf-8")
            self.assertNotIn("findUserCounts", api_source)
            self.assertEqual(
                0,
                self.phase4c_composition["change_budget"][
                    "production_java_files_added"
                ],
            )
        else:
            read_contract = self.phase4c_read
            requirements = self.phase4c_composition["successor_handoff"][
                "future_read_contract_requirements"
            ]
            self.assertEqual(requirements["contract_id"], read_contract["contract_id"])
            self.assertEqual(requirements["status"], read_contract["status"])
            self.assertEqual(
                read_contract["document_payload_sha256"],
                document_payload_sha256(read_contract),
            )
            read_predecessor = read_contract["predecessor"]
            self.assertEqual(
                requirements["predecessor_source"], read_predecessor["source"]
            )
            self.assertEqual(
                sha256(PHASE4C_COMPOSITION_PATH), read_predecessor["sha256"]
            )
            self.assertEqual(
                self.phase4c_composition["contract_id"],
                read_predecessor["contract_id"],
            )

            successor = read_contract["implementation"]
            self.assertTrue(successor["http_neutral_java_implemented"])
            self.assertEqual(
                requirements["implemented_public_application_method_count"],
                successor["implemented_public_application_method_count"],
            )
            current_manifest = learning_and_personalbank_main_source_manifest()
            self.assertTrue(current_manifest)
            self.assertEqual(40, len(current_manifest))
            self.assertEqual(
                current_manifest,
                successor["learning_and_personalbank_main_source_manifest"],
            )
            self.assertEqual(
                requirements["exact_main_source_scope"],
                successor["main_source_scope"],
            )
            historical_manifest = self.phase4c_composition["production_baseline"][
                "learning_and_personalbank_main_source_manifest"
            ]
            self.assertNotEqual(historical_manifest, current_manifest)
            expected_changed = set(requirements["expected_changed_main_sources"])
            expected_added = set(requirements["expected_added_main_sources"])
            self.assertEqual(
                expected_added,
                set(current_manifest) - set(historical_manifest),
            )
            self.assertEqual(set(), set(historical_manifest) - set(current_manifest))
            self.assertEqual(
                expected_changed,
                {
                    relative for relative in set(historical_manifest) & set(current_manifest)
                    if historical_manifest[relative] != current_manifest[relative]
                },
            )
            for relative in requirements["expected_changed_main_sources"]:
                self.assertIn(relative, historical_manifest)
                self.assertIn(relative, current_manifest)
                self.assertNotEqual(
                    historical_manifest[relative], current_manifest[relative], relative
                )
            for relative, fragments in requirements[
                "expected_added_main_sources"
            ].items():
                self.assertNotIn(relative, historical_manifest)
                self.assertIn(relative, current_manifest)
                compact = compact_java_code(ROOT / relative)
                for fragment in fragments:
                    self.assertIn(fragment, compact, relative)

            baseline_surface = self.phase4c_composition["production_baseline"][
                "production_runtime_surface"
            ]["files"]
            read_surface = successor["production_runtime_surface"]["files"]
            self.assertEqual(expected_added, set(read_surface) - set(baseline_surface))
            self.assertEqual(set(), set(baseline_surface) - set(read_surface))
            self.assertEqual(
                expected_changed,
                {
                    relative for relative in set(baseline_surface) & set(read_surface)
                    if baseline_surface[relative] != read_surface[relative]
                },
            )
            transition = self.http_implementation["implementation"][
                "production_runtime_transition"
            ]
            self.assertEqual({
                "file_count": 288,
                "manifest_sha256": successor["production_runtime_surface"][
                    "manifest_sha256"
                ],
            }, transition["predecessor"])
            current_surface = production_runtime_manifest()
            self.assertEqual(297, len(current_surface))
            self.assertEqual(current_surface, transition["current"]["files"])
            self.assertEqual(9, transition["exact_delta"]["added_file_count"])
            self.assertEqual(6, transition["exact_delta"]["changed_file_count"])
            self.assertEqual(0, transition["exact_delta"]["deleted_file_count"])
            self.assertEqual(
                self.phase4c_composition["production_baseline"]
                ["route_status_surface"]["files"],
                route_status_manifest(),
            )
            for relative, fragments in requirements[
                    "changed_source_compact_java_fragments"
            ].items():
                compact = compact_java_code(ROOT / relative)
                for fragment in fragments:
                    self.assertIn(fragment, compact, relative)

            verification_files = successor["verification_source_files"]
            verification_hashes = successor["verification_source_sha256"]
            self.assertEqual(set(verification_files), set(verification_hashes))
            self.assertEqual(
                set(requirements["required_verification_sources"]),
                set(verification_files),
            )
            for name, relative in requirements[
                    "required_verification_sources"
            ].items():
                self.assertEqual(relative, verification_files[name])
                source = ROOT / relative
                self.assertTrue(source.is_file(), name)
                if sha256(source) == verification_hashes[name]:
                    terminal_hash = verification_hashes[name]
                else:
                    terminal_hash = implementation_fixed_source_sha256(ROOT, relative)
                self.assertEqual(sha256(source), terminal_hash, name)
                parity_code = compact_java_code(source)
                self.assertIn("@Test", parity_code)
                required_methods = requirements["required_verification_test_methods"][name]
                actual_methods = junit_test_methods(source)
                self.assertTrue(set(required_methods).issubset(actual_methods), name)
                for method_name in required_methods:
                    self.assertIn(f"@Testvoid{method_name}(", parity_code, name)
                if name == "api_shape_contract_parity_test":
                    for method_name in (
                        "findPersonalBankUserCounts",
                        "checkQuestionAccess",
                        "summarizeQuestions",
                        "inspectQuestionMembership",
                    ):
                        self.assertIn(method_name, parity_code)
            behavior = requirements["required_behavior_evidence"]
            self.assertEqual(["16.14", "18.4"], behavior["postgresql_versions"])
            self.assertTrue(all(
                value for key, value in behavior.items()
                if key != "postgresql_versions"
            ))
            self.assertEqual(
                self.phase4c_composition["security_access_policy"],
                read_contract["security_access_policy"],
            )
            authorization = read_contract["authorization"]
            for key in requirements["forbidden_authorizations"]:
                self.assertFalse(authorization[key], key)
            self.assertFalse(authorization["operator_migration_implementation"])
            self.assertFalse(authorization["migration_global_preflight_evidence_closed"])
            self.assertTrue(read_contract["acceptance"]["routes_remain_pending"])
            self.assertFalse(read_contract["acceptance"]["production_cutover"])

    def test_03_routes_retain_personalbank_baseline_but_review_to_learning(self):
        operations = self.contract["route_status"]["operations"]
        self.assertEqual(ROUTE_KEYS, {
            f"{item['route_id']}|{item['method']}|{item['path']}"
            for item in operations
        })
        rows = list(csv.DictReader(MATRIX_PATH.read_text(
            encoding="utf-8"
        ).splitlines()))
        selected = {row["route_id"]: row for row in rows if row["route_id"] in {
            "6858f6fa506f", "006913d0d956"
        }}
        self.assertEqual(2, len(selected))
        for operation in operations:
            route_id = operation["route_id"]
            matrix = selected[route_id]
            self.assertEqual("personalbank", matrix["target_module"])
            self.assertEqual("pending", matrix["migration_status"])
            self.assertEqual("personalbank", operation["baseline_target_module"])
            self.assertEqual("learning", operation["reviewed_use_case_owner"])
            self.assertEqual("learning", operation["reviewed_http_owner"])
            self.assertEqual("pending", operation["migration_status"])
            self.assertFalse(operation["production_cutover"])

            openapi_operation = self.openapi["paths"][
                OPENAPI_PATHS[route_id]
            ]["get"]
            self.assertEqual("pending", openapi_operation["x-ti-migration"]["status"])
            self.assertEqual(
                "personalbank",
                openapi_operation["x-ti-migration"]["targetModule"],
            )
            self.assertEqual(
                "inferred", openapi_operation["x-ti-contract-maturity"]
            )

        effective = self.effective["effective"]
        self.assertEqual(11, effective["migration_status"]["migrated"])
        self.assertEqual(600, effective["migration_status"]["pending"])
        self.assertEqual(0, effective["production_cutover_operation_count"])
        migrated = {row["route_id"] for row in effective["migrated_operations"]}
        self.assertTrue({"6858f6fa506f", "006913d0d956"}.isdisjoint(migrated))
        route_delta = ROUTE_DELTA_PATH.read_text(encoding="utf-8")
        self.assertNotIn("6858f6fa506f", route_delta)
        self.assertNotIn("006913d0d956", route_delta)

    def test_04_learning_owns_four_tables_and_dependency_direction_is_one_way(self):
        ownership = list(csv.DictReader(OWNERSHIP_PATH.read_text(
            encoding="utf-8"
        ).splitlines()))
        owners = {
            row["resource_name"]: row["target_owner"]
            for row in ownership if row["resource_kind"] == "table"
        }
        for table in PERSONALBANK_TABLES:
            self.assertEqual("personalbank", owners[table], table)
        for table in LEARNING_TABLES:
            self.assertEqual("learning", owners[table], table)

        modules = {module["module_id"]: module for module in self.modules["modules"]}
        self.assertIn("personalbank", modules["learning"]["allowed_dependencies"])
        self.assertNotIn("learning", modules["personalbank"]["allowed_dependencies"])
        decision = self.contract["module_boundary_decision"]
        self.assertEqual(sorted(LEARNING_TABLES), sorted(
            decision["personalbank_forbidden_learning_tables"]
        ))
        self.assertEqual("learning", decision["complete_use_case_owner"])
        self.assertEqual("personalbank::api", decision["personalbank_call_surface"])
        self.assertEqual(
            "learning_to_personalbank_api",
            decision["required_composition_direction"],
        )

    def test_05_caller_attestation_and_dual_surface_consumers_are_closed(self):
        gate = self.contract["entry_prerequisites"]["caller_attestation"]
        self.assertTrue(gate["passed"])
        self.assertEqual(43, gate["repository_match_count"])
        self.assertEqual(24, gate["matched_source_count"])
        self.assertEqual(19, gate["capability_or_mixed_source_count"])
        self.assertEqual(
            self.callers["attestation_sha256"], gate["attestation_sha256"]
        )
        self.assertEqual(
            self.callers["document_payload_sha256"],
            gate["document_payload_sha256"],
        )
        self.assertTrue(all(self.callers["closure"].values()))
        counting = self.callers["caller_counting"]
        self.assertEqual(1, counting["legacy_web_direct_network_call_site_count"])
        self.assertEqual(7, counting[
            "legacy_miniprogram_typescript_direct_call_site_count"
        ])
        self.assertEqual(1, counting[
            "legacy_miniprogram_indirect_consumer_count"
        ])
        self.assertEqual(2, counting["legacy_test_request_site_count"])

    def test_06_fifty_nine_goldens_close_behavior_but_not_ownership(self):
        gate = self.contract["entry_prerequisites"]["fixed_commit_golden"]
        self.assertTrue(gate["passed"])
        self.assertEqual(59, gate["case_count"])
        self.assertEqual(59, self.golden["case_count"])
        self.assertEqual(59, len(self.golden["cases"]))
        self.assertEqual(
            self.golden["case_payload_sha256"], gate["case_payload_sha256"]
        )
        self.assertEqual(
            self.golden["document_payload_sha256"],
            gate["document_payload_sha256"],
        )
        self.assertEqual(0, self.golden["request_effect_scope"][
            "normal_statistics_business_dml"
        ])
        self.assertEqual(
            "not established by this evidence",
            self.golden["tag_compatibility_contract"]["approved_java_behavior"],
        )
        self.assertIn(
            "not direct PostgreSQL",
            self.golden["failure_and_transaction_contract"][
                "postgresql_poison_simulation"
            ],
        )
        self.assertFalse(gate["implementation_or_owner_authorized_by_goldens"])

    def test_07_query_plan_sql_jdbc_and_large_tag_evidence_are_closed(self):
        gate = self.contract["entry_prerequisites"]["jdbc_and_query_plans"]
        self.assertTrue(gate["passed"])
        self.assertEqual(
            "ti.phase4b.personal-bank-user-counts-query-plan-evidence",
            self.plan["contract_id"],
        )
        self.assertEqual(gate["file_sha256"], sha256(PLAN_PATH))
        self.assertEqual(
            gate["document_payload_sha256"], self.plan["document_payload_sha256"]
        )
        self.assertEqual(["16.14", "18.4"], gate["postgresql_versions"])
        self.assertEqual(
            gate["postgresql_versions"],
            self.plan["cross_version_contract"]["observed_versions"],
        )
        self.assertEqual(8, gate["query_family_count"])
        self.assertEqual(
            8,
            self.plan["sql_contract"]["unique_query_family_count"],
        )
        self.assertEqual(QUERY_IDS, gate["query_order"])
        self.assertEqual(
            QUERY_IDS,
            self.plan["sql_contract"]["manifest"]["query_order"],
        )
        self.assertEqual(2, gate["access_query_count"])
        self.assertEqual(2, self.plan["sql_contract"]["access_query_count"])
        self.assertEqual(4, gate["statistics_query_count_per_nonempty_read"])
        self.assertEqual(
            4,
            self.plan["sql_contract"][
                "statistics_runtime_statement_count_per_nonempty_source"
            ],
        )
        self.assertEqual(14, gate["observation_count_per_version"])
        self.assertTrue(all(
            len(engine["observations"]) == 14 for engine in self.plan["engines"]
        ))
        self.assertEqual(900, gate["large_tag_parameter_count"])
        self.assertEqual(
            900,
            self.plan["dynamic_tag_manifest_safety"]["large_tag_parameter_count"],
        )
        self.assertTrue(gate["large_tag_prepare_execute_succeeded"])
        cross_version = self.plan["cross_version_contract"]
        self.assertTrue(cross_version["large_tag_prepare_execute_succeeded"])
        self.assertEqual("25P02", gate["transaction_poisoning_sqlstate"])
        self.assertEqual(
            "25P02",
            self.plan["transaction_failure_boundary"][
                "manifest_declared_sqlstate"
            ],
        )
        self.assertTrue(gate["rollback_restored_readability"])
        self.assertTrue(cross_version["rollback_recovery_observed"])
        self.assertTrue(gate["cross_version_results_equal"])
        self.assertTrue(cross_version["canonical_results_equal_across_versions"])
        self.assertTrue(gate["schema_index_and_data_fingerprints_unchanged"])
        self.assertTrue(
            cross_version["schema_index_and_data_fingerprints_unchanged"]
        )
        self.assertFalse(gate["schema_or_index_change_authorized"])
        self.assertFalse(self.plan["claim_limits"]["schema_change_authorized"])
        self.assertFalse(self.plan["claim_limits"]["index_change_authorized"])
        self.assertFalse(gate["implementation_authorized"])
        self.assertEqual(
            "personalbank",
            self.plan["route_migration_status"]["baseline_target_module"],
        )
        self.assertEqual(
            "learning",
            self.plan["route_migration_status"]["reviewed_use_case_owner"],
        )

    def test_08_evidence_sources_fixtures_and_test_method_counts_are_bound(self):
        verification = self.contract["targeted_evidence_verification"]
        counts = verification["test_method_counts"]
        sources = self.contract["source_contracts"]
        expected = {
            "caller_tool_tests": python_test_count(
                ROOT / sources["caller_capture_tool_test"]["source"]
            ),
            "golden_tool_tests": python_test_count(
                ROOT / sources["golden_capture_tool_test"]["source"]
            ),
            "query_plan_tool_tests": python_test_count(
                ROOT / sources["query_plan_capture_tool_test"]["source"]
            ),
            "sql_contract_tests": java_test_count(
                ROOT / sources["sql_contract_test"]["source"]
            ),
            "sql_manifest_tests": java_test_count(
                ROOT / sources["sql_manifest_test"]["source"]
            ),
            "jdbc_compatibility_tests": java_test_count(
                ROOT / sources["jdbc_compatibility_test"]["source"]
            ),
            "entry_contract_tests": python_test_count(Path(__file__)),
        }
        self.assertEqual(expected, counts)
        self.assertEqual(sum(expected.values()), verification["total_test_methods"])
        self.assertEqual(0, verification["failures"])
        self.assertEqual(0, verification["errors"])
        self.assertTrue(verification["passed"])

        sql_text = (
            ROOT / sources["evidence_sql"]["source"]
        ).read_text(encoding="utf-8")
        manifest_text = (
            ROOT / sources["sql_manifest_test"]["source"]
        ).read_text(encoding="utf-8")
        jdbc_text = (
            ROOT / sources["jdbc_compatibility_test"]["source"]
        ).read_text(encoding="utf-8")
        self.assertIn("EVIDENCE_MAX_TAG_PARAMETER_COUNT = 900", sql_text)
        self.assertIn('manifest.put("implementation_authorized", false)', manifest_text)
        self.assertIn('isEqualTo("25P02")', jdbc_text)
        for name in ("postgres_schema_fixture", "postgres_seed_fixture"):
            source = ROOT / sources[name]["source"]
            self.assertIn("server/src/test/resources/", source.as_posix())
            self.assertNotIn("migrations/", source.as_posix())

    def test_09_tag_get_writes_require_migration_and_difference_approval(self):
        gate = self.contract["tag_migration_gate"]
        self.assertFalse(gate["runtime_get_ddl_authorized"])
        self.assertFalse(gate["runtime_get_dml_authorized"])
        self.assertFalse(gate["lazy_tag_migration_authorized"])
        self.assertTrue(gate["explicit_idempotent_migration_required"])
        self.assertTrue(gate["difference_approval_required"])
        self.assertEqual("learning", gate["migration_owner"])
        self.assertEqual(
            sorted(["user_progress", "user_question_tag_items"]),
            sorted(gate["migration_tables"]),
        )
        self.assertFalse(gate["production_schema_or_index_delta_authorized"])
        self.assertFalse(gate["cutover_authorized_before_gate_closure"])

    def test_10_entry_only_gate_adds_no_java_http_schema_index_or_cutover(self):
        changes = self.contract["change_budget"]
        self.assertEqual(0, changes["production_java_files_added"])
        self.assertEqual(0, changes["production_java_files_modified"])
        self.assertEqual(0, changes["http_controllers_added"])
        self.assertEqual(0, changes["application_methods_added"])
        self.assertEqual(0, changes["production_schema_files_added"])
        self.assertEqual(0, changes["production_indexes_added"])
        self.assertEqual(0, changes["route_delta_rows_added"])
        self.assertEqual(0, changes["openapi_operations_migrated"])
        self.assertEqual(0, changes["production_cutover_operations"])
        self.assertEqual(9, len(changes))
        self.assertEqual(
            [
                "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json",
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
            ],
            self.contract["entry_only_artifacts"]["files"],
        )
        self.assertEqual(0, self.contract["entry_only_artifacts"]["production_files"])
        acceptance = self.contract["acceptance"]
        self.assertTrue(acceptance["evidence_closed"])
        self.assertFalse(acceptance["implementation_authorized"])
        self.assertEqual(
            "pending_learning_composition_contract",
            acceptance["next_required_gate"],
        )
        self.assertFalse(acceptance["production_cutover"])


if __name__ == "__main__":
    unittest.main()
