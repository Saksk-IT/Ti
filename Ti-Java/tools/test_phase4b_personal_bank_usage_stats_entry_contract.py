#!/usr/bin/env python3
"""Fail-closed checks for the Phase 4B personal-bank usage-stats entry gate."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import unittest

try:
    from tools.phase4c_read_successor_acceptance import (
        load_read_successor_contract,
        successor_sha256,
        validate_tag_preflight_production_runtime_successor,
    )
    from tools.phase4c_tag_migration_global_preflight_successor_acceptance import (
        validation_session as acceptance_validation_session,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase4c_read_successor_acceptance import (
        load_read_successor_contract,
        successor_sha256,
        validate_tag_preflight_production_runtime_successor,
    )
    from phase4c_tag_migration_global_preflight_successor_acceptance import (
        validation_session as acceptance_validation_session,
    )


ROOT = Path(__file__).resolve().parents[1]
PHASE4B = ROOT / "docs" / "refactor" / "phase4b"
CONTRACT_PATH = PHASE4B / "personal-bank-usage-stats-entry-contract.json"
CONTRACT_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json"
)
PREDECESSOR_PATH = PHASE4B / "personal-bank-all-shares-read-contract.json"
SUCCESSOR_PATH = PHASE4B / "personal-bank-usage-stats-read-contract.json"
CALLERS_PATH = PHASE4B / "personal-bank-usage-stats-callers.json"
GOLDEN_PATH = PHASE4B / "golden-personal-bank-usage-stats-reads.json"
PLAN_PATH = PHASE4B / "personal-bank-usage-stats-query-plan-evidence.json"
EFFECTIVE_PATH = ROOT / "docs" / "refactor" / "phase4a" / (
    "effective-route-parity-status.json"
)
PHASE4C_COMPOSITION_PATH = (
    ROOT / "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)

ROUTE_KEYS = {
    "d67a16965b08|GET|/api/user/banks/api/<int:bank_id>/usage-stats",
    "22aecd49a3c2|GET|/user/banks/api/<int:bank_id>/usage-stats",
}
OPENAPI_PATHS = {
    "d67a16965b08": "/api/user/banks/api/{bank_id}/usage-stats",
    "22aecd49a3c2": "/user/banks/api/{bank_id}/usage-stats",
}
HTTP_METHODS = {
    "get", "put", "post", "delete", "options", "head", "patch", "trace"
}
QUERY_IDS = [
    "personal-bank-usage-stats-bank-probe",
    "personal-bank-usage-stats-shared-users",
    "personal-bank-usage-stats-public-users",
]
VIEW_COMPONENTS = [
    {"name": "bankId", "java_type": "int", "nullable": False},
    {"name": "publicBank", "java_type": "boolean", "nullable": False},
    {"name": "ownerId", "java_type": "long", "nullable": False},
    {"name": "ownerCount", "java_type": "int", "nullable": False},
    {"name": "sharedUsers", "java_type": "int", "nullable": False},
    {"name": "publicUsers", "java_type": "int", "nullable": False},
    {"name": "totalUsers", "java_type": "int", "nullable": False},
    {
        "name": "totalUsersExcludingOwner",
        "java_type": "int",
        "nullable": False,
    },
]
SOURCE_HANDOFFS = {
    "application_api": ("main_source", "application_api"),
    "application_service": ("main_source", "application_service"),
    "entry_contract_test": (
        "verification_source", "entry_forward_handoff_test"
    ),
    "all_shares_entry_forward_handoff_test": (
        "verification_source", "all_shares_entry_forward_handoff_test"
    ),
    "all_shares_read_forward_handoff_test": (
        "verification_source", "all_shares_read_forward_handoff_test"
    ),
    "all_shares_java_forward_handoff_test": (
        "verification_source", "all_shares_contract_parity_test"
    ),
    "share_list_read_transitive_forward_handoff_test": (
        "verification_source", "share_read_contract_test"
    ),
    "share_list_java_transitive_forward_handoff_test": (
        "verification_source", "share_list_contract_parity_test"
    ),
    "progress_forward_handoff": (
        "verification_source", "progress_forward_handoff"
    ),
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
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


_VALIDATED_READ_SUCCESSORS: dict[str, str] = {}


def capture_validated_read_successors(contract: dict | None) -> None:
    if contract is None:
        return
    history = contract["historical_successor_acceptance"]
    for section in ("python_sources", "java_sources", "auxiliary_sources"):
        for relative in history[section]:
            _VALIDATED_READ_SUCCESSORS[relative] = sha256(ROOT / relative)


def phase4c_successor_hash(relative: str) -> str | None:
    validated = _VALIDATED_READ_SUCCESSORS.get(relative)
    if validated is None:
        return successor_sha256(ROOT, relative)
    if sha256(ROOT / relative) != validated:
        raise AssertionError(f"validated read successor drifted: {relative}")
    return validated


def learning_and_personalbank_main_source_manifest() -> dict[str, str]:
    main_root = ROOT / "server/src/main/java/io/saksk/ti"
    paths = []
    for module in ("learning", "personalbank"):
        paths.extend((main_root / module).rglob("*.java"))
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


def python_test_count(path: Path) -> int:
    return len(re.findall(r"^\s+def test_[A-Za-z0-9_]+\(", path.read_text(
        encoding="utf-8"
    ), re.MULTILINE))


def java_test_count(path: Path) -> int:
    return len(re.findall(r"^\s+@Test\s*$", path.read_text(
        encoding="utf-8"
    ), re.MULTILINE))


class Phase4bPersonalBankUsageStatsEntryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._validation_session = acceptance_validation_session()
        cls._validation_session.__enter__()
        cls.addClassCleanup(cls._validation_session.__exit__, None, None, None)
        cls.read_successor = load_read_successor_contract(ROOT)
        capture_validated_read_successors(cls.read_successor)
        cls.contract = load_json(CONTRACT_PATH)
        cls.predecessor = load_json(PREDECESSOR_PATH)
        cls.successor = load_json(SUCCESSOR_PATH)
        cls.callers = load_json(CALLERS_PATH)
        cls.golden = load_json(GOLDEN_PATH)
        cls.plan = load_json(PLAN_PATH)
        cls.effective = load_json(EFFECTIVE_PATH)
        cls.openapi = load_json(ROOT / "contracts" / "openapi.json")

    def test_01_identity_predecessor_sources_and_payload_are_closed(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-entry-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "entry_gate_passed_implementation_not_started", contract["status"]
        )
        self.assertEqual(
            "personalbank-usage-stats-preimplementation-entry-gate",
            contract["scope"],
        )
        self.assertEqual(
            "700006dfdfa063deb4387be572911e782bcea0d9",
            contract["legacy_commit"],
        )

        predecessor = contract["predecessor"]
        self.assertEqual(
            "docs/refactor/phase4b/personal-bank-all-shares-read-contract.json",
            predecessor["source"],
        )
        self.assertEqual(sha256(PREDECESSOR_PATH), predecessor["sha256"])
        self.assertEqual(
            "c7e0a2e80506352263cc18693046f18cb3c4272e29f0c49b64b933a344472b6f",
            predecessor["sha256"],
        )
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            predecessor["status"],
        )
        self.assertEqual(predecessor["status"], self.predecessor["status"])
        self.assertTrue(predecessor["all_shares_internal_read_closed"])
        self.assertFalse(predecessor["all_shares_http_aliases_migrated"])
        self.assertFalse(predecessor["production_cutover"])

        successor = self.successor
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-read-contract",
            successor["contract_id"],
        )
        self.assertEqual(CONTRACT_RELATIVE, successor["predecessor"]["source"])
        self.assertEqual(sha256(CONTRACT_PATH), successor["predecessor"]["sha256"])

        for name, reference in contract["source_contracts"].items():
            source = ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            current_hash = sha256(source)
            handoff = SOURCE_HANDOFFS.get(name)
            if handoff is None:
                self.assertEqual(reference["sha256"], current_hash, name)
                continue
            section, successor_name = handoff
            files = successor["implementation"][f"{section}_files"]
            hashes = successor["implementation"][f"{section}_sha256"]
            self.assertEqual(reference["source"], files[successor_name], name)
            phase4c_hash = phase4c_successor_hash(reference["source"])
            if self.read_successor is not None:
                if phase4c_hash is None:
                    self.assertEqual(current_hash, hashes[successor_name], name)
                else:
                    self.assertEqual(current_hash, phase4c_hash, name)
            elif phase4c_hash is None:
                self.assertEqual(current_hash, hashes[successor_name], name)
            else:
                self.assertEqual(current_hash, phase4c_hash, name)
                self.assertNotEqual(current_hash, hashes[successor_name], name)
            self.assertNotEqual(reference["sha256"], current_hash, name)

        java_handoff = contract["source_contracts"][
            "share_list_java_transitive_forward_handoff_test"
        ]
        self.assertEqual(
            "server/src/test/java/io/saksk/ti/architecture/"
            "PersonalBankShareListContractParityTest.java",
            java_handoff["source"],
        )

        self.assertEqual(
            contract["document_payload_sha256"],
            document_payload_sha256(contract),
        )

    def test_02_callers_goldens_plans_and_targeted_counts_are_exact(self):
        prerequisites = self.contract["entry_prerequisites"]

        caller = prerequisites["caller_attestation"]
        self.assertEqual(2, self.callers["caller_counting"]
                         ["fixed_commit_legacy_logical_caller_count"])
        self.assertTrue(self.callers["caller_counting"]
                        ["both_legacy_caller_families_active"])
        self.assertTrue(self.callers["closure"]["caller_attestation_complete"])
        self.assertEqual(self.callers["attestation_sha256"],
                         caller["attestation_sha256"])
        self.assertEqual(self.callers["document_payload_sha256"],
                         caller["document_payload_sha256"])

        golden = prerequisites["fixed_commit_golden"]
        self.assertEqual(32, self.golden["case_count"])
        self.assertEqual(self.golden["case_payload_sha256"],
                         golden["case_payload_sha256"])
        self.assertEqual(self.golden["document_payload_sha256"],
                         golden["document_payload_sha256"])
        self.assertEqual(self.golden["document_payload_sha256"],
                         document_payload_sha256(self.golden))
        self.assertEqual(0, self.golden["request_effect_scope"]
                         ["business_table_writes"])

        plan = prerequisites["jdbc_and_query_plans"]
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-query-plan-evidence",
            self.plan["contract_id"],
        )
        self.assertEqual(["16.14", "18.4"], [
            engine["server_version"] for engine in self.plan["engines"]
        ])
        self.assertEqual(QUERY_IDS, self.plan["sql_contract"]["query_order"])
        self.assertEqual(3, self.plan["sql_contract"]["query_count"])
        self.assertTrue(self.plan["sql_contract"]["sequential_execution_required"])
        self.assertTrue(self.plan["sql_contract"]["short_circuit_after_bank_probe"])
        self.assertEqual(
            "independently_degrade_to_empty",
            self.plan["sql_contract"]["shared_and_public_failure_boundaries"],
        )
        self.assertFalse(self.plan["sql_contract"]["production_source_added"])
        self.assertTrue(self.plan["cross_version_contract"]["passed"])
        self.assertEqual(self.plan["document_payload_sha256"],
                         plan["document_payload_sha256"])
        self.assertEqual(self.plan["document_payload_sha256"],
                         document_payload_sha256(self.plan))

        verification = prerequisites["targeted_evidence_verification"]
        self.assertEqual(8, python_test_count(
            ROOT / "tools/test_capture_phase4b_personal_bank_usage_stats_callers.py"
        ))
        self.assertEqual(11, python_test_count(
            ROOT / "tools/test_capture_phase4b_personal_bank_usage_stats_goldens.py"
        ))
        self.assertEqual(16, python_test_count(
            ROOT / "tools/test_capture_phase4b_personal_bank_usage_stats_query_plans.py"
        ))
        sql_tests = sum(java_test_count(ROOT / path) for path in (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUsageStatsEvidenceSqlContractTest.java",
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUsageStatsEvidenceSqlManifestTest.java",
        ))
        self.assertEqual(5, sql_tests)
        self.assertEqual(2, java_test_count(
            ROOT / "server/src/test/java/io/saksk/ti/integration/"
            "Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT.java"
        ))
        self.assertEqual(
            {
                "caller_tool_tests": 8,
                "golden_tool_tests": 11,
                "query_plan_tool_tests": 16,
                "sql_unit_tests": 5,
                "postgresql_compatibility_tests": 2,
                "failures": 0,
                "errors": 0,
                "passed": True,
            },
            verification,
        )

    def test_03_three_queries_short_circuit_fail_soft_and_time_are_frozen(self):
        frozen = self.contract["frozen_internal_contract"]
        manifest = self.plan["sql_contract"]["manifest"]
        self.assertEqual(3, frozen["query_count"])
        self.assertTrue(frozen["sequential_execution_required"])
        self.assertTrue(frozen["short_circuit_after_bank_probe"])
        self.assertFalse(frozen["join_or_query_collapse_authorized"])
        self.assertFalse(frozen["parallel_execution_authorized"])
        self.assertEqual(manifest["queries"], frozen["query_sequence"])
        self.assertEqual(QUERY_IDS, [
            query["query_id"] for query in frozen["query_sequence"]
        ])

        failure = frozen["failure_semantics"]
        self.assertEqual("propagate", failure["bank_probe_failure"])
        self.assertEqual("return NOT_FOUND and execute no later query",
                         failure["bank_missing_or_inactive"])
        self.assertEqual("return FORBIDDEN and execute no later query",
                         failure["viewer_or_owner_invalid_or_mismatched"])
        self.assertEqual("independently degrade to empty set",
                         failure["shared_query_failure"])
        self.assertEqual("independently degrade to empty set",
                         failure["public_query_failure"])
        self.assertEqual("AVAILABLE owner-only counts",
                         failure["both_optional_queries_fail"])

        time = frozen["time_semantics"]
        self.assertEqual("java.time.Clock", time["injectable_clock"])
        self.assertEqual("Asia/Shanghai", time["zone"])
        self.assertEqual("expires_at < now", time["expired_when"])
        self.assertEqual("valid", time["equal_to_now"])
        self.assertEqual("valid", time["null_expiry"])
        self.assertEqual("valid", time["empty_string_expiry"])
        self.assertEqual("expired", time["truthy_malformed_expiry"])

        counts = frozen["usage_count_semantics"]
        self.assertEqual(["user_id", "expires_at"],
                         counts["shared_sql_distinct_key"])
        self.assertEqual("user_id", counts["shared_set_key_after_expiry_filter"])
        self.assertEqual("ignored", counts["zero_user_id"])
        self.assertEqual("counted", counts["negative_user_id"])
        self.assertTrue(counts["shared_and_public_categories_count_independently"])
        self.assertEqual("owner plus shared/public set union",
                         counts["total_users"])
        self.assertEqual(1, counts["owner_count"])

    def test_04_explicit_tristate_view_and_implemented_successor_are_exact(self):
        shape = self.contract["expected_application_shape"]
        self.assertEqual(
            "io.saksk.ti.personalbank.api.PersonalBankApplicationApi",
            shape["public_api"],
        )
        self.assertEqual("findUsageStats", shape["method_name"])
        self.assertEqual(
            "PersonalBankUsageStatsResult findUsageStats("
            "AuthenticatedPersonalBankViewer viewer, int bankId)",
            shape["signature"],
        )
        self.assertEqual(
            "io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult",
            shape["return_type"],
        )
        self.assertEqual(
            [
                "io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer",
                "int",
            ],
            shape["parameter_types"],
        )
        self.assertEqual(["AVAILABLE", "NOT_FOUND", "FORBIDDEN"],
                         shape["result_outcomes"])
        self.assertEqual(VIEW_COMPONENTS, shape["view_record_components"])
        self.assertEqual(
            "non-null view only for AVAILABLE",
            shape["result_payload_invariant"],
        )

        implementation = self.contract["implementation_state"]
        self.assertFalse(implementation["implementation_started"])
        self.assertFalse(implementation["production_source_added"])
        self.assertEqual([], implementation["main_source_files_added"])
        self.assertFalse(implementation["schema_or_index_delta_added"])
        successor_main_files = self.successor["implementation"]["main_source_files"]
        successor_main_hashes = self.successor["implementation"]["main_source_sha256"]
        for relative in implementation["future_main_source_files"]:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            matching = [
                name for name, successor_relative in successor_main_files.items()
                if successor_relative == relative
            ]
            self.assertEqual(1, len(matching), relative)
            current_hash = sha256(path)
            if self.read_successor is None:
                self.assertEqual(
                    successor_main_hashes[matching[0]], current_hash, relative
                )
            else:
                self.assertEqual(
                    self.read_successor["implementation"]
                    ["learning_and_personalbank_main_source_manifest"][relative],
                    current_hash,
                    relative,
                )

        api = (ROOT / "server/src/main/java/io/saksk/ti/personalbank/api/"
               "PersonalBankApplicationApi.java").read_text(encoding="utf-8")
        self.assertIn("findUsageStats", api)
        self.assertIn("PersonalBankUsageStatsResult", api)

        current_manifest = {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in sorted((ROOT / "server/src/main/java/io/saksk/ti/personalbank")
                               .rglob("*.java"))
        }
        unchanged = self.contract["unchanged_state"]
        self.assertNotEqual(unchanged["personalbank_main_source_manifest"],
                            current_manifest)
        if self.read_successor is None:
            self.assertEqual(
                self.successor["implementation"]["personalbank_main_source_manifest"],
                current_manifest,
            )
        else:
            accepted_manifest = self.read_successor["implementation"][
                "learning_and_personalbank_main_source_manifest"
            ]
            current_manifest = learning_and_personalbank_main_source_manifest()
            runtime = validate_tag_preflight_production_runtime_successor(
                ROOT,
                accepted_manifest,
                current_manifest,
                view="learning_personalbank_main",
            )
            self.assertEqual(40, len(accepted_manifest))
            self.assertEqual(54, len(current_manifest))
            self.assertEqual(14, len(runtime.added_files))
            self.assertEqual((), runtime.changed_files)
            self.assertEqual((), runtime.deleted_files)
        self.assertEqual(22, unchanged["implemented_public_application_method_count"])
        self.assertEqual(3, unchanged["personalbank_public_method_count"])
        self.assertEqual(23, unchanged["future_public_application_method_count"])
        self.assertEqual(4, unchanged["future_personalbank_public_method_count"])

    def test_05_route_openapi_and_effective_counts_have_zero_delta(self):
        with (ROOT / "docs/refactor/02-route-parity-matrix.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {
                f"{row['route_id']}|{row['methods']}|{row['path']}": row
                for row in csv.DictReader(handle)
                if row["route_id"] in {"d67a16965b08", "22aecd49a3c2"}
            }
        self.assertEqual(ROUTE_KEYS, set(rows))
        for row in rows.values():
            self.assertEqual("personalbank", row["target_module"])
            self.assertEqual("pending", row["migration_status"])
            self.assertIn("auth_required", row["decorators"])

        effective = self.effective["effective"]
        self.assertEqual(611, effective["expanded_operation_count"])
        self.assertEqual(11, effective["migration_status"]["migrated"])
        self.assertEqual(600, effective["migration_status"]["pending"])
        self.assertEqual(0, effective["production_cutover_operation_count"])

        raw_openapi_operations = sum(
            1
            for path_item in self.openapi["paths"].values()
            for method in path_item
            if method.lower() in HTTP_METHODS
        )
        self.assertEqual(610, raw_openapi_operations)

        route_state = self.contract["route_state"]
        self.assertEqual(611, route_state["expanded_http_method_count"])
        self.assertEqual(610, route_state["raw_openapi_operation_count"])
        self.assertEqual(11, route_state["migrated_route_count"])
        self.assertEqual(600, route_state["effective_pending_operation_count"])
        self.assertEqual(0, route_state["production_cutover_count"])
        self.assertEqual(0, route_state["route_delta_count"])
        self.assertEqual(0, route_state["openapi_delta_count"])

        self.assertEqual(ROUTE_KEYS, {
            f"{item['route_id']}|{item['method']}|{item['path']}"
            for item in route_state["operations"]
        })
        for item in route_state["operations"]:
            operation = self.openapi["paths"][item["openapi_path"]]["get"]
            self.assertEqual(OPENAPI_PATHS[item["route_id"]], item["openapi_path"])
            self.assertEqual("pending", operation["x-ti-migration"]["status"])
            self.assertEqual("inferred", operation["x-ti-contract-maturity"])
            self.assertEqual(
                "#/components/schemas/LegacyOpaquePayload",
                operation["responses"]["default"]["content"]["*/*"]
                ["schema"]["$ref"],
            )
            self.assertFalse(item["production_cutover"])

    def test_06_http_schema_and_cutover_remain_strictly_deferred(self):
        deferred = self.contract["http_boundary_deferred"]
        self.assertTrue(deferred["authentication_and_alias_divergence_captured"])
        self.assertTrue(deferred["status_envelope_and_failure_negotiation_captured"])
        self.assertTrue(deferred["session_last_active_side_effect_isolated"])
        self.assertFalse(deferred["controller_implementation_authorized"])
        self.assertFalse(deferred["security_matcher_authorized"])
        self.assertFalse(deferred["route_or_openapi_delta_authorized"])

        forbidden = self.contract["forbidden_scope"]
        self.assertTrue(all(value is False for value in forbidden.values()))
        self.assertFalse(self.plan["claim_limits"]["schema_change_authorized"])
        self.assertFalse(self.plan["claim_limits"]["index_change_authorized"])
        self.assertFalse(self.plan["data_set"]
                         ["production_or_test_schema_index_added"])
        self.assertTrue(all(
            "src/test/resources" in relative
            for relative in self.contract["implementation_state"]
            ["test_only_fixture_files"]
        ))

        gate = self.contract["entry_gate"]
        self.assertTrue(gate["preimplementation_boundary_verified"])
        self.assertTrue(gate["all_evidence_hashes_bound"])
        self.assertTrue(gate["implementation_authorized"])
        self.assertFalse(gate["http_migration_authorized"])
        self.assertFalse(gate["production_cutover_authorized"])
        self.assertEqual({
            "status": "passed",
            "command": (
                "PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/python -B "
                "-m unittest discover -s tools -p 'test_*.py'"
            ),
            "tests": 359,
            "failures": 0,
            "errors": 0,
            "passed": True,
        }, gate["full_source_tools"])
        self.assertEqual({
            "status": "passed",
            "command": "./infra/phase2/verify-in-maven-container.sh clean verify",
            "surefire_tests": 470,
            "failsafe_tests": 70,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "passed": True,
        }, gate["full_maven"])


if __name__ == "__main__":
    unittest.main()
