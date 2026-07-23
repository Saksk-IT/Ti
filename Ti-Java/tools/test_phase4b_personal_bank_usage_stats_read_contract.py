#!/usr/bin/env python3
"""Fail-closed parity for the implemented Phase 4B usage-statistics read."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
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
CONTRACT_PATH = PHASE4B / "personal-bank-usage-stats-read-contract.json"
CONTRACT_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json"
)
ENTRY_PATH = PHASE4B / "personal-bank-usage-stats-entry-contract.json"
SHAPE_PATH = (
    PHASE4B / "personal-bank-usage-stats-application-api-shape.json"
)
GOLDEN_PATH = PHASE4B / "golden-personal-bank-usage-stats-reads.json"
PLAN_PATH = PHASE4B / "personal-bank-usage-stats-query-plan-evidence.json"
USER_COUNTS_ENTRY_PATH = (
    PHASE4B / "personal-bank-user-counts-entry-contract.json"
)
USER_COUNTS_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json"
)
USER_COUNTS_GOLDEN_PATH = (
    PHASE4B / "golden-personal-bank-user-counts-reads.json"
)
PHASE4C_COMPOSITION_PATH = (
    ROOT / "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)

QUERY_IDS = [
    "personal-bank-usage-stats-bank-probe",
    "personal-bank-usage-stats-shared-users",
    "personal-bank-usage-stats-public-users",
]
ADAPTER_FIELDS = [
    "SELECT_BANK",
    "SELECT_SHARED_USERS",
    "SELECT_PUBLIC_USER_IDS",
]
ROUTE_KEYS = {
    "d67a16965b08|GET|/api/user/banks/api/<int:bank_id>/usage-stats",
    "22aecd49a3c2|GET|/user/banks/api/<int:bank_id>/usage-stats",
}
OPENAPI_PATHS = {
    "d67a16965b08": "/api/user/banks/api/{bank_id}/usage-stats",
    "22aecd49a3c2": "/user/banks/api/{bank_id}/usage-stats",
}
FORBIDDEN_SCOPE_KEYS = {
    "controller_added",
    "security_matcher_added",
    "route_or_openapi_delta_added",
    "cache_or_rate_limit_added",
    "schema_or_index_added",
    "production_ddl_or_dml_added",
    "query_join_or_collapse_added",
    "parallel_query_execution_added",
    "http_status_or_envelope_implementation_added",
    "production_cutover",
}
USER_COUNTS_AUTHORIZATION_KEYS = {
    "direct_personalbank_implementation",
    "learning_composition_implementation",
    "http_implementation",
    "production_schema_delta",
    "production_index_delta",
    "production_cutover",
}
USER_COUNTS_CHANGE_BUDGET_KEYS = {
    "production_java_files_added",
    "production_java_files_modified",
    "http_controllers_added",
    "application_methods_added",
    "production_schema_files_added",
    "production_indexes_added",
    "route_delta_rows_added",
    "openapi_operations_migrated",
    "production_cutover_operations",
}
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
EVIDENCE_SOURCES = {
    "application_api_shape": (
        "docs/refactor/phase4b/"
        "personal-bank-usage-stats-application-api-shape.json"
    ),
    "golden": (
        "docs/refactor/phase4b/golden-personal-bank-usage-stats-reads.json"
    ),
    "preimplementation_sql": (
        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSql.java"
    ),
    "query_plan": (
        "docs/refactor/phase4b/"
        "personal-bank-usage-stats-query-plan-evidence.json"
    ),
}
MAIN_SOURCE_FILES = {
    "application_api": (
        "server/src/main/java/io/saksk/ti/personalbank/api/"
        "PersonalBankApplicationApi.java"
    ),
    "usage_stats_result": (
        "server/src/main/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsResult.java"
    ),
    "usage_stats_view": (
        "server/src/main/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsView.java"
    ),
    "application_service": (
        "server/src/main/java/io/saksk/ti/personalbank/application/"
        "PersonalBankQueryService.java"
    ),
    "query_port": (
        "server/src/main/java/io/saksk/ti/personalbank/application/port/"
        "PersonalBankUsageStatsQueryPort.java"
    ),
    "jdbc_adapter": (
        "server/src/main/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/JdbcPersonalBankUsageStatsQueryAdapter.java"
    ),
}
VERIFICATION_SOURCE_FILES = {
    "result_test": (
        "server/src/test/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsResultTest.java"
    ),
    "view_test": (
        "server/src/test/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsViewTest.java"
    ),
    "service_test": (
        "server/src/test/java/io/saksk/ti/personalbank/application/"
        "PersonalBankQueryServiceTest.java"
    ),
    "adapter_test": (
        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/JdbcPersonalBankUsageStatsQueryAdapterTest.java"
    ),
    "adapter_test_access": (
        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/JdbcPersonalBankUsageStatsQueryAdapterTestAccess.java"
    ),
    "sql_contract_test": (
        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsSqlContractTest.java"
    ),
    "runtime_sql_manifest_test": (
        "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsRuntimeSqlManifestTest.java"
    ),
    "jdbc_compatibility_test": (
        "server/src/test/java/io/saksk/ti/integration/"
        "Phase4bPersonalBankUsageStatsJdbcCompatibilityIT.java"
    ),
    "contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ),
    "public_boundary_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankPublicBoundaryNeutralityTest.java"
    ),
    "module_context_test": (
        "server/src/test/java/io/saksk/ti/personalbank/"
        "PersonalBankModuleContextTest.java"
    ),
    "module_contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "ModuleContractParityTest.java"
    ),
    "read_contract_test": (
        "tools/test_phase4b_personal_bank_usage_stats_read_contract.py"
    ),
    "entry_forward_handoff_test": (
        "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py"
    ),
    "all_shares_read_forward_handoff_test": (
        "tools/test_phase4b_personal_bank_all_shares_read_contract.py"
    ),
    "all_shares_entry_forward_handoff_test": (
        "tools/test_phase4b_personal_bank_all_shares_entry_contract.py"
    ),
    "all_shares_contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ),
    "share_read_contract_test": (
        "tools/test_phase4b_personal_bank_share_list_read_contract.py"
    ),
    "share_list_entry_forward_handoff_test": (
        "tools/test_phase4b_personal_bank_share_list_entry_contract.py"
    ),
    "share_list_contract_parity_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ),
    "category_acceptance_forward_handoff_test": (
        "tools/test_phase4b_personal_bank_category_acceptance.py"
    ),
    "category_golden_forward_handoff_test": (
        "tools/test_capture_phase4b_personal_bank_category_goldens.py"
    ),
    "category_contract_forward_handoff_test": (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankCategoryContractParityTest.java"
    ),
    "progress_forward_handoff": "docs/refactor/05-progress.md",
}
FORWARD_ADDITIONS = {
    "Ti-Java/docs/refactor/phase4b/golden-personal-bank-usage-stats-reads.json",
    (
        "Ti-Java/docs/refactor/phase4b/"
        "personal-bank-usage-stats-application-api-shape.json"
    ),
    "Ti-Java/docs/refactor/phase4b/personal-bank-usage-stats-callers.json",
    "Ti-Java/docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json",
    (
        "Ti-Java/docs/refactor/phase4b/"
        "personal-bank-usage-stats-query-plan-evidence.json"
    ),
    "Ti-Java/docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json",
    (
        "Ti-Java/server/src/main/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsResult.java"
    ),
    (
        "Ti-Java/server/src/main/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsView.java"
    ),
    (
        "Ti-Java/server/src/main/java/io/saksk/ti/personalbank/application/port/"
        "PersonalBankUsageStatsQueryPort.java"
    ),
    (
        "Ti-Java/server/src/main/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/JdbcPersonalBankUsageStatsQueryAdapter.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "Phase4bPersonalBankUsageStatsJdbcCompatibilityIT.java"
    ),
    "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/api/PersonalBankUsageStatsResultTest.java",
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/api/"
        "PersonalBankUsageStatsViewTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSql.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSqlContractTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSqlManifestTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/JdbcPersonalBankUsageStatsQueryAdapterTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/JdbcPersonalBankUsageStatsQueryAdapterTestAccess.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsRuntimeSqlManifestTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsSqlContractTest.java"
    ),
    (
        "Ti-Java/server/src/test/resources/db/phase4b/"
        "065-personal-bank-usage-stats-schema.sql"
    ),
    (
        "Ti-Java/server/src/test/resources/db/phase4b/"
        "066-personal-bank-usage-stats-seed.sql"
    ),
    "Ti-Java/tools/capture_phase4b_personal_bank_usage_stats_callers.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_usage_stats_goldens.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_usage_stats_query_plans.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_usage_stats_callers.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_usage_stats_goldens.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_usage_stats_query_plans.py",
    "Ti-Java/tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
    "Ti-Java/tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
    "Ti-Java/docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
    "Ti-Java/docs/refactor/phase4b/personal-bank-user-counts-callers.json",
    "Ti-Java/docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json",
    (
        "Ti-Java/docs/refactor/phase4b/"
        "personal-bank-user-counts-query-plan-evidence.json"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUserCountsEvidenceSql.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUserCountsEvidenceSqlContractTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUserCountsEvidenceSqlManifestTest.java"
    ),
    (
        "Ti-Java/server/src/test/resources/db/phase4b/"
        "067-personal-bank-user-counts-schema.sql"
    ),
    (
        "Ti-Java/server/src/test/resources/db/phase4b/"
        "068-personal-bank-user-counts-seed.sql"
    ),
    "Ti-Java/tools/capture_phase4b_personal_bank_user_counts_callers.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_user_counts_goldens.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_user_counts_query_plans.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_user_counts_callers.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_user_counts_goldens.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_user_counts_query_plans.py",
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


def payload_sha256(document: dict) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


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


class Phase4bPersonalBankUsageStatsReadContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._validation_session = acceptance_validation_session()
        cls._validation_session.__enter__()
        cls.addClassCleanup(cls._validation_session.__exit__, None, None, None)
        cls.read_successor = load_read_successor_contract(ROOT)
        capture_validated_read_successors(cls.read_successor)
        cls.contract = load_json(CONTRACT_PATH)
        cls.entry = load_json(ENTRY_PATH)
        cls.shape = load_json(SHAPE_PATH)
        cls.golden = load_json(GOLDEN_PATH)
        cls.plan = load_json(PLAN_PATH)
        cls.user_counts_entry = load_json(USER_COUNTS_ENTRY_PATH)
        cls.user_counts_golden = load_json(USER_COUNTS_GOLDEN_PATH)
        cls.openapi = load_json(ROOT / "contracts" / "openapi.json")

    def test_01_predecessor_evidence_and_payload_are_closed(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-read-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            contract["status"],
        )
        self.assertEqual(self.entry["legacy_commit"], contract["legacy_commit"])

        predecessor = contract["predecessor"]
        self.assertEqual(
            "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json",
            predecessor["source"],
        )
        self.assertEqual(sha256(ENTRY_PATH), predecessor["sha256"])
        self.assertEqual(
            "entry_gate_passed_implementation_not_started",
            self.entry["status"],
        )
        self.assertFalse(
            self.entry["implementation_state"]["implementation_started"]
        )

        self.assertEqual(set(EVIDENCE_SOURCES), set(contract["evidence"]))
        for name, relative in EVIDENCE_SOURCES.items():
            reference = contract["evidence"][name]
            self.assertEqual(relative, reference["source"], name)
            self.assertEqual(sha256(ROOT / relative), reference["sha256"], name)

        self.assertEqual(32, self.golden["case_count"])
        self.assertEqual(
            ["16.14", "18.4"],
            [engine["server_version"] for engine in self.plan["engines"]],
        )
        self.assertEqual(
            contract["document_payload_sha256"], payload_sha256(contract)
        )

    def test_02_shape_api_result_view_and_port_are_exact(self):
        shape = self.shape
        self.assertEqual(23, shape["implemented_public_application_method_count"])
        self.assertEqual(11, shape["migrated_route_count"])
        self.assertEqual(600, shape["pending_route_count"])
        self.assertEqual(0, shape["production_cutover_count"])
        personalbank = shape["personalbank"]
        self.assertEqual(
            ["listCategories", "findShares", "listOwnedShares", "findUsageStats"],
            [method["name"] for method in personalbank["methods"]],
        )
        self.assertEqual(
            ["d67a16965b08", "22aecd49a3c2"],
            personalbank["deferred_usage_stats_http_route_ids"],
        )
        self.assertEqual(
            ["PersonalBankUsageStatsResult", "PersonalBankUsageStatsView"],
            personalbank["implemented_types"][-2:],
        )

        application = self.contract["application_contract"]
        self.assertEqual(
            "io.saksk.ti.personalbank.api.PersonalBankApplicationApi",
            application["public_api"],
        )
        self.assertEqual(
            "PersonalBankUsageStatsResult findUsageStats("
            "AuthenticatedPersonalBankViewer viewer, int bankId)",
            application["method"],
        )
        self.assertTrue(application["transaction_read_only"])
        self.assertEqual("requireNonNull_before_port", application["null_viewer"])
        self.assertEqual(
            ["AVAILABLE", "NOT_FOUND", "FORBIDDEN"],
            application["result_outcomes"],
        )
        self.assertEqual(
            "non-null view only for AVAILABLE",
            application["result_payload_invariant"],
        )

        result = self.contract["result_contract"]
        self.assertEqual(
            "io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult",
            result["record"],
        )
        self.assertEqual(
            ["AVAILABLE", "NOT_FOUND", "FORBIDDEN"], result["outcomes"]
        )
        self.assertEqual(
            VIEW_COMPONENTS, self.contract["usage_stats_view_components"]
        )
        self.assertEqual(
            self.entry["expected_application_shape"]["view_record_components"],
            self.contract["usage_stats_view_components"],
        )

        port = self.contract["query_port_contract"]
        self.assertEqual(
            "io.saksk.ti.personalbank.application.port."
            "PersonalBankUsageStatsQueryPort",
            port["port"],
        )
        self.assertEqual(
            ["findBank", "listSharedUsers", "listPublicUserIds"],
            [method["name"] for method in port["methods"]],
        )

        sources = self.contract["implementation"]["main_source_files"]
        api = (ROOT / sources["application_api"]).read_text(encoding="utf-8")
        result_source = (ROOT / sources["usage_stats_result"]).read_text(
            encoding="utf-8"
        )
        view = (ROOT / sources["usage_stats_view"]).read_text(encoding="utf-8")
        query_port = (ROOT / sources["query_port"]).read_text(encoding="utf-8")
        self.assertIn("PersonalBankUsageStatsResult findUsageStats(", api)
        self.assertIn("enum Outcome", result_source)
        self.assertIn("AVAILABLE", result_source)
        self.assertIn("totalUsersExcludingOwner", view)
        self.assertIn("Optional<BankAccess> findBank(int bankId)", query_port)
        self.assertIn("List<SharedUserAccess> listSharedUsers(int bankId)", query_port)
        self.assertIn("List<Object> listPublicUserIds(int bankId)", query_port)
        for source in (api, result_source, view, query_port):
            self.assertNotIn("HttpServletRequest", source)
            self.assertNotIn("@RestController", source)

    def test_03_sql_time_count_and_failure_semantics_are_frozen(self):
        frozen = self.entry["frozen_internal_contract"]
        persistence = self.contract["persistence_contract"]
        self.assertEqual(3, persistence["query_count"])
        self.assertEqual(QUERY_IDS, persistence["query_order"])
        self.assertTrue(persistence["sequential_execution_required"])
        self.assertTrue(persistence["short_circuit_after_bank_probe"])
        self.assertEqual(
            "REQUIRES_NEW read-only transaction per shared/public query",
            persistence["optional_query_transaction_boundary"],
        )
        self.assertFalse(persistence["join_or_query_collapse_authorized"])
        self.assertFalse(persistence["parallel_execution_authorized"])
        self.assertEqual("integer", persistence["bank_id_jdbc_bind_type"])
        self.assertFalse(persistence["schema_or_index_delta"])

        queries = persistence["queries"]
        planned = self.plan["sql_contract"]["manifest"]["queries"]
        self.assertEqual(3, len(queries))
        self.assertEqual(3, len(planned))
        for index, (query, evidence_query, frozen_query) in enumerate(
            zip(queries, planned, frozen["query_sequence"], strict=True)
        ):
            self.assertEqual(QUERY_IDS[index], query["query_id"])
            self.assertEqual(ADAPTER_FIELDS[index], query["adapter_field"])
            self.assertEqual(evidence_query["sql"], query["sql"])
            self.assertEqual(frozen_query["sql"], query["sql"])
            self.assertEqual(["bank_id"], query["parameter_order"])
            self.assertEqual({"bank_id": "integer"}, query["parameters"])

        self.assertEqual(
            frozen["time_semantics"], self.contract["time_semantics"]
        )
        self.assertEqual(
            frozen["usage_count_semantics"],
            self.contract["usage_count_semantics"],
        )
        self.assertEqual(
            frozen["failure_semantics"], self.contract["failure_contract"]
        )
        self.assertEqual(0, self.golden["request_effect_scope"]["business_table_writes"])
        self.assertEqual(
            QUERY_IDS, self.plan["sql_contract"]["query_order"]
        )
        self.assertTrue(self.plan["cross_version_contract"]["passed"])

    def test_04_implementation_hashes_manifest_and_verification_are_closed(self):
        implementation = self.contract["implementation"]
        self.assertEqual(MAIN_SOURCE_FILES, implementation["main_source_files"])
        self.assertEqual(
            set(MAIN_SOURCE_FILES), set(implementation["main_source_sha256"])
        )
        for name, relative in MAIN_SOURCE_FILES.items():
            current_hash = sha256(ROOT / relative)
            if self.read_successor is None:
                self.assertEqual(
                    current_hash,
                    implementation["main_source_sha256"][name],
                    name,
                )
            else:
                self.assertEqual(
                    self.read_successor["implementation"]
                    ["learning_and_personalbank_main_source_manifest"][relative],
                    current_hash,
                    name,
                )

        self.assertEqual(
            VERIFICATION_SOURCE_FILES, implementation["verification_source_files"]
        )
        self.assertEqual(
            set(VERIFICATION_SOURCE_FILES),
            set(implementation["verification_source_sha256"]),
        )
        for name, relative in VERIFICATION_SOURCE_FILES.items():
            current_hash = sha256(ROOT / relative)
            phase4c_hash = phase4c_successor_hash(relative)
            if self.read_successor is not None:
                if phase4c_hash is None:
                    self.assertEqual(
                        current_hash,
                        implementation["verification_source_sha256"][name],
                        name,
                    )
                else:
                    self.assertEqual(current_hash, phase4c_hash, name)
            elif phase4c_hash is None:
                self.assertEqual(
                    current_hash,
                    implementation["verification_source_sha256"][name],
                    name,
                )
            else:
                self.assertEqual(current_hash, phase4c_hash, name)
                self.assertNotEqual(
                    current_hash,
                    implementation["verification_source_sha256"][name],
                    name,
                )

        current_manifest = {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in sorted(
                (
                    ROOT
                    / "server/src/main/java/io/saksk/ti/personalbank"
                ).rglob("*.java")
            )
        }
        if self.read_successor is None:
            self.assertEqual(
                current_manifest, implementation["personalbank_main_source_manifest"]
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

        verification = self.contract["verification"]
        self.assertEqual(30, verification["targeted_unit_tests"])
        self.assertEqual(2, verification["postgresql_adapter_tests"])
        self.assertEqual(
            ["16.14", "18.4"], verification["postgresql_versions"]
        )
        self.assertEqual(0, verification["targeted_failures"])
        self.assertEqual(0, verification["targeted_errors"])
        self.assertEqual(0, verification["targeted_skipped"])
        self.assertTrue(verification["targeted_passed"])
        self.assertEqual(
            {"tests": 364, "failures": 0, "errors": 0},
            verification["full_source_tools"],
        )
        self.assertEqual(
            {
                "surefire": 494,
                "failsafe": 72,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
            },
            verification["full_maven"],
        )

    def test_05_routes_forbidden_scope_and_forward_additions_are_closed(self):
        with (ROOT / "docs/refactor/02-route-parity-matrix.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {
                f"{row['route_id']}|{row['methods']}|{row['path']}": row
                for row in csv.DictReader(handle)
                if row["route_id"] in {"d67a16965b08", "22aecd49a3c2"}
            }
        self.assertEqual(ROUTE_KEYS, set(rows))
        for key, row in rows.items():
            self.assertEqual("personalbank", row["target_module"], key)
            self.assertEqual("pending", row["migration_status"], key)

        route_state = self.contract["route_state"]
        self.assertEqual(11, route_state["migrated_route_count"])
        self.assertEqual(600, route_state["pending_route_count"])
        self.assertEqual(0, route_state["production_cutover_count"])
        self.assertEqual(set(OPENAPI_PATHS), {
            operation["route_id"] for operation in route_state["operations"]
        })
        for operation in route_state["operations"]:
            route_id = operation["route_id"]
            self.assertEqual(OPENAPI_PATHS[route_id], operation["openapi_path"])
            self.assertEqual("pending", operation["migration_status"])
            self.assertEqual("inferred", operation["contract_maturity"])
            self.assertFalse(operation["production_cutover"])
            openapi_operation = self.openapi["paths"][
                operation["openapi_path"]
            ]["get"]
            self.assertEqual(
                f"legacy_{route_id}_get", openapi_operation["operationId"]
            )
            self.assertEqual(
                "pending", openapi_operation["x-ti-migration"]["status"]
            )
            self.assertEqual(
                "inferred", openapi_operation["x-ti-contract-maturity"]
            )
            self.assertEqual(
                "#/components/schemas/LegacyOpaquePayload",
                openapi_operation["responses"]["default"]["content"]["*/*"]
                ["schema"]["$ref"],
            )

        forbidden = self.contract["forbidden_scope"]
        self.assertEqual(FORBIDDEN_SCOPE_KEYS, set(forbidden))
        self.assertTrue(all(value is False for value in forbidden.values()))
        forward = self.contract["forward_handoff"]
        self.assertEqual(FORWARD_ADDITIONS, set(forward["forward_additions"]))
        self.assertEqual(49, len(forward["forward_additions"]))
        for repository_relative in forward["forward_additions"]:
            self.assertTrue(
                (ROOT.parent / repository_relative).is_file(), repository_relative
            )

    def test_06_user_counts_successor_closes_evidence_without_authorization(self):
        successor = self.user_counts_entry
        self.assertEqual(
            "ti.phase4b.personal-bank-user-counts-entry-contract",
            successor["contract_id"],
        )
        self.assertEqual(
            "evidence_closed_but_production_implementation_blocked_"
            "pending_learning_composition",
            successor["status"],
        )
        self.assertEqual(CONTRACT_RELATIVE, successor["predecessor"]["source"])
        self.assertEqual(
            sha256(CONTRACT_PATH), successor["predecessor"]["sha256"]
        )

        decision = successor["entry_decision"]
        self.assertTrue(decision["evidence_closed"])
        self.assertFalse(decision["implementation_authorized"])
        self.assertEqual("personalbank", decision["baseline_route_owner"])
        self.assertEqual("learning", decision["reviewed_use_case_owner"])
        self.assertEqual("learning", decision["reviewed_http_owner"])
        authorizations = decision["authorizations"]
        self.assertEqual(USER_COUNTS_AUTHORIZATION_KEYS, set(authorizations))
        self.assertTrue(all(value is False for value in authorizations.values()))

        boundary = successor["module_boundary_decision"]
        self.assertEqual(
            "learning_to_personalbank_api",
            boundary["required_composition_direction"],
        )
        self.assertEqual("learning", boundary["complete_use_case_owner"])
        self.assertEqual("personalbank::api", boundary["personalbank_call_surface"])
        self.assertEqual(
            [
                "user_bank_favorites",
                "user_bank_mistakes",
                "user_progress",
                "user_question_tag_items",
            ],
            boundary["personalbank_forbidden_learning_tables"],
        )

        prerequisites = successor["entry_prerequisites"]
        for evidence_name in (
            "caller_attestation",
            "fixed_commit_golden",
            "jdbc_and_query_plans",
        ):
            reference = prerequisites[evidence_name]
            evidence_path = ROOT / reference["evidence_source"]
            self.assertTrue(evidence_path.is_file(), evidence_name)
            self.assertEqual(
                sha256(evidence_path), reference["file_sha256"], evidence_name
            )
        self.assertEqual(
            59, prerequisites["fixed_commit_golden"]["case_count"]
        )
        self.assertTrue(prerequisites["fixed_commit_golden"]["passed"])
        self.assertTrue(prerequisites["jdbc_and_query_plans"]["passed"])
        self.assertEqual(59, self.user_counts_golden["case_count"])

        unchanged = successor["unchanged_state"]
        self.assertEqual(23, unchanged["implemented_public_application_method_count"])
        self.assertEqual(11, unchanged["migrated_route_count"])
        self.assertEqual(600, unchanged["pending_route_count"])
        self.assertEqual(0, unchanged["production_cutover_count"])

        acceptance = successor["acceptance"]
        self.assertTrue(acceptance["evidence_closed"])
        self.assertFalse(acceptance["implementation_authorized"])
        self.assertEqual(
            "pending_learning_composition_contract",
            acceptance["next_required_gate"],
        )
        self.assertFalse(acceptance["production_cutover"])

        change_budget = successor["change_budget"]
        self.assertEqual(USER_COUNTS_CHANGE_BUDGET_KEYS, set(change_budget))
        self.assertTrue(all(value == 0 for value in change_budget.values()))
        self.assertNotIn("PENDING", json.dumps(successor, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
