#!/usr/bin/env python3
"""Fail-closed parity for the implemented Phase 4B personal-bank all-shares read."""

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
CONTRACT_PATH = PHASE4B / "personal-bank-all-shares-read-contract.json"
CONTRACT_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-all-shares-read-contract.json"
)
USAGE_STATS_ENTRY_PATH = PHASE4B / "personal-bank-usage-stats-entry-contract.json"
USAGE_STATS_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json"
)
USAGE_STATS_READ_PATH = PHASE4B / "personal-bank-usage-stats-read-contract.json"
PHASE4C_COMPOSITION_PATH = (
    ROOT / "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)
ROUTE_KEYS = {
    "a6fda3638fc3|GET|/api/user/banks/api/shares/all",
    "0fdd3026f636|GET|/user/banks/api/shares/all",
}
USAGE_STATS_ROUTE_KEYS = {
    "d67a16965b08|GET|/api/user/banks/api/<int:bank_id>/usage-stats",
    "22aecd49a3c2|GET|/user/banks/api/<int:bank_id>/usage-stats",
}
USAGE_STATS_READ_HANDOFFS = {
    "service_test": "service_test",
    "contract_parity_test": "all_shares_contract_parity_test",
    "public_boundary_test": "public_boundary_test",
    "module_contract_parity_test": "module_contract_parity_test",
    "read_contract_test": "all_shares_read_forward_handoff_test",
    "entry_forward_handoff_test": "all_shares_entry_forward_handoff_test",
    "share_read_contract_test": "share_read_contract_test",
    "share_list_contract_parity_test": "share_list_contract_parity_test",
    "share_list_entry_forward_handoff_test":
        "share_list_entry_forward_handoff_test",
    "category_acceptance_forward_handoff_test":
        "category_acceptance_forward_handoff_test",
    "category_golden_forward_handoff_test":
        "category_golden_forward_handoff_test",
    "category_contract_forward_handoff_test":
        "category_contract_forward_handoff_test",
    "progress_forward_handoff": "progress_forward_handoff",
}
COMPONENTS = [
    {"name": "id", "java_type": "int", "nullable": False},
    {"name": "bankId", "java_type": "int", "nullable": False},
    {"name": "ownerId", "java_type": "long", "nullable": False},
    {"name": "shareCode", "java_type": "java.lang.String", "nullable": True},
    {"name": "shareToken", "java_type": "java.lang.String", "nullable": True},
    {"name": "permission", "java_type": "java.lang.String", "nullable": True},
    {"name": "expiresAt", "java_type": "java.time.LocalDateTime", "nullable": True},
    {"name": "maxUses", "java_type": "java.lang.Integer", "nullable": True},
    {"name": "currentUses", "java_type": "java.lang.Integer", "nullable": True},
    {"name": "isActive", "java_type": "java.lang.Boolean", "nullable": True},
    {"name": "createdAt", "java_type": "java.time.LocalDateTime", "nullable": True},
    {"name": "bankName", "java_type": "java.lang.String", "nullable": False},
]


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
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


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


class Phase4bPersonalBankAllSharesReadContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._validation_session = acceptance_validation_session()
        cls._validation_session.__enter__()
        cls.addClassCleanup(cls._validation_session.__exit__, None, None, None)
        cls.read_successor = load_read_successor_contract(ROOT)
        capture_validated_read_successors(cls.read_successor)
        cls.contract = load_json(CONTRACT_PATH)
        cls.entry = load_json(
            PHASE4B / "personal-bank-all-shares-entry-contract.json"
        )
        cls.shape = load_json(
            PHASE4B / "personal-bank-all-shares-application-api-shape.json"
        )
        cls.golden = load_json(
            PHASE4B / "golden-personal-bank-all-shares-reads.json"
        )
        cls.plan = load_json(
            PHASE4B / "personal-bank-all-shares-query-plan-evidence.json"
        )
        cls.usage_stats_entry = load_json(USAGE_STATS_ENTRY_PATH)
        cls.usage_stats_read = load_json(USAGE_STATS_READ_PATH)
        cls.openapi = load_json(ROOT / "contracts" / "openapi.json")

    def test_01_predecessor_evidence_sources_and_payload_are_closed(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-read-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            contract["status"],
        )
        predecessor = contract["predecessor"]
        self.assertEqual(
            "docs/refactor/phase4b/personal-bank-all-shares-entry-contract.json",
            predecessor["source"],
        )
        self.assertEqual(sha256(ROOT / predecessor["source"]), predecessor["sha256"])
        self.assertEqual(
            "entry_gate_passed_implementation_not_started", self.entry["status"]
        )
        self.assertFalse(self.entry["implementation_state"]["implementation_started"])

        for name, reference in contract["evidence"].items():
            self.assertEqual(
                reference["sha256"], sha256(ROOT / reference["source"]), name
            )
        for section in ("main_source", "verification_source"):
            files = contract["implementation"][f"{section}_files"]
            hashes = contract["implementation"][f"{section}_sha256"]
            self.assertEqual(set(files), set(hashes))
            for name, relative in files.items():
                current_hash = sha256(ROOT / relative)
                handoff_name = None
                if section == "main_source" and name in {
                        "application_api", "application_service"
                }:
                    handoff_name = name
                elif section == "verification_source":
                    handoff_name = USAGE_STATS_READ_HANDOFFS.get(name)
                if handoff_name is None:
                    self.assertEqual(hashes[name], current_hash, name)
                else:
                    successor_files = self.usage_stats_read["implementation"][
                        f"{section}_files"
                    ]
                    successor_hashes = self.usage_stats_read["implementation"][
                        f"{section}_sha256"
                    ]
                    self.assertEqual(relative, successor_files[handoff_name])
                    phase4c_hash = phase4c_successor_hash(relative)
                    if self.read_successor is not None:
                        if phase4c_hash is None:
                            self.assertEqual(
                                current_hash, successor_hashes[handoff_name], name
                            )
                        else:
                            self.assertEqual(current_hash, phase4c_hash, name)
                    elif phase4c_hash is None:
                        self.assertEqual(
                            current_hash, successor_hashes[handoff_name], name
                        )
                    else:
                        self.assertEqual(current_hash, phase4c_hash, name)
                        self.assertNotEqual(
                            current_hash, successor_hashes[handoff_name], name
                        )
                    self.assertNotEqual(hashes[name], current_hash, name)
        self.assertEqual(
            contract["document_payload_sha256"], payload_sha256(contract)
        )
        if self.read_successor is not None:
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
            self.assertEqual(40, runtime.accepted_file_count)
            self.assertEqual(54, runtime.current_file_count)
            self.assertEqual(14, len(runtime.added_files))
            self.assertEqual((), runtime.changed_files)
            self.assertEqual((), runtime.deleted_files)

    def test_02_shape_api_dto_and_service_are_exactly_http_neutral(self):
        shape = self.shape
        self.assertEqual(22, shape["implemented_public_application_method_count"])
        self.assertEqual(11, shape["migrated_route_count"])
        self.assertEqual(600, shape["pending_route_count"])
        self.assertEqual(0, shape["production_cutover_count"])
        personalbank = shape["personalbank"]
        self.assertEqual(
            ["listCategories", "findShares", "listOwnedShares"],
            [method["name"] for method in personalbank["methods"]],
        )
        self.assertEqual(
            ["a6fda3638fc3", "0fdd3026f636"],
            personalbank["deferred_all_shares_http_route_ids"],
        )

        application = self.contract["application_contract"]
        self.assertEqual(
            "List<PersonalBankOwnedShareView> listOwnedShares("
            "AuthenticatedPersonalBankViewer viewer)",
            application["method"],
        )
        self.assertEqual(COMPONENTS, self.contract["owned_share_record_components"])
        self.assertEqual("List.copyOf", application["collection_immutability"])
        self.assertEqual("requireNonNull_before_port", application["null_viewer"])
        self.assertEqual("propagate", application["persistence_failure"])
        self.assertFalse(application["share_link_present"])

        api = (ROOT / self.contract["implementation"]["main_source_files"]
               ["application_api"]).read_text(encoding="utf-8")
        service = (ROOT / self.contract["implementation"]["main_source_files"]
                   ["application_service"]).read_text(encoding="utf-8")
        dto = (ROOT / self.contract["implementation"]["main_source_files"]
               ["owned_share_view"]).read_text(encoding="utf-8")
        self.assertIn("List<PersonalBankOwnedShareView> listOwnedShares(", api)
        self.assertIn("@Transactional(readOnly = true)", service)
        self.assertIn("Objects.requireNonNull(viewer, \"viewer\")", service)
        self.assertIn("List.copyOf(ownedShares.listOwnedShares", service)
        self.assertIn("Objects.requireNonNull(bankName, \"bankName\")", dto)
        for source in (api, service, dto):
            self.assertNotIn("shareLink", source)
            self.assertNotIn("HttpServletRequest", source)
            self.assertNotIn("@RestController", source)

    def test_03_port_adapter_and_single_runtime_sql_preserve_the_frozen_query(self):
        persistence = self.contract["persistence_contract"]
        self.assertEqual(1, persistence["query_count"])
        self.assertEqual("bigint", persistence["viewer_jdbc_bind_type"])
        self.assertEqual(
            self.entry["frozen_internal_contract"]["query"]["sql"],
            persistence["sql"],
        )
        self.assertFalse(persistence["java_secondary_sorting"])
        self.assertFalse(persistence["share_link_synthesis"])
        self.assertFalse(persistence["extra_filters"])
        self.assertFalse(persistence["pagination"])
        self.assertFalse(persistence["schema_or_index_delta"])

        adapter = (ROOT / self.contract["implementation"]["main_source_files"]
                   ["jdbc_adapter"]).read_text(encoding="utf-8")
        port = (ROOT / self.contract["implementation"]["main_source_files"]
                ["query_port"]).read_text(encoding="utf-8")
        self.assertIn(
            "List<PersonalBankOwnedShareView> listOwnedShares(long viewerId)", port
        )
        self.assertIn(
            '.param("viewer_id", viewerId, Types.BIGINT)', adapter
        )
        self.assertIn('row.getObject("is_active", Boolean.class)', adapter)
        self.assertNotIn("getBoolean", adapter)
        self.assertNotIn("Math.toIntExact", adapter)
        self.assertNotIn("(int) viewerId", adapter)

    def test_04_runtime_data_plan_and_failure_semantics_remain_bound(self):
        self.assertEqual(20, self.golden["case_count"])
        self.assertEqual(1, self.golden["legacy_query"]["statement_count"])
        self.assertEqual(["uid"], self.golden["legacy_query"]["binds"])
        self.assertEqual(
            "unchanged",
            self.golden["request_effect_scope"]["personal_bank_business_tables"],
        )
        self.assertEqual(
            ["16.14", "18.4"],
            [engine["server_version"] for engine in self.plan["engines"]],
        )
        self.assertEqual(149_811, self.plan["fixture"]["expected_result_count"])
        for engine in self.plan["engines"]:
            self.assertTrue(all(
                observation["binding"]["runtime_statement_count"] == 1
                and observation["result"]["row_count"] == 149_811
                and observation["plan_summary"]["maximum_actual_loops"] == 1
                and observation["plan_summary"]["temp_read_blocks"] == 0
                and observation["plan_summary"]["temp_written_blocks"] == 0
                for observation in engine["observations"]
            ))
        verification = self.contract["verification"]
        self.assertEqual(2, verification["postgresql_adapter_tests"])
        self.assertTrue(verification["targeted_passed"])
        self.assertEqual(
            {"tests": 317, "failures": 0, "errors": 0},
            verification["full_source_tools"],
        )
        self.assertEqual(
            {
                "surefire": 465,
                "failsafe": 68,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
            },
            verification["full_maven"],
        )

    def test_05_routes_openapi_and_forbidden_scope_remain_unchanged(self):
        with (ROOT / "docs/refactor/02-route-parity-matrix.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {
                f"{row['route_id']}|{row['methods']}|{row['path']}": row
                for row in csv.DictReader(handle)
                if row["route_id"] in {"a6fda3638fc3", "0fdd3026f636"}
            }
        self.assertEqual(ROUTE_KEYS, set(rows))
        for key, row in rows.items():
            self.assertEqual("pending", row["migration_status"], key)
            self.assertEqual("personalbank", row["target_module"], key)

        route_state = self.contract["route_state"]
        self.assertEqual(11, route_state["migrated_route_count"])
        self.assertEqual(600, route_state["pending_route_count"])
        self.assertEqual(0, route_state["production_cutover_count"])
        self.assertEqual(ROUTE_KEYS, {
            f"{item['route_id']}|GET|{item['path']}"
            for item in route_state["operations"]
        })
        for item in route_state["operations"]:
            operation = self.openapi["paths"][item["path"]]["get"]
            self.assertEqual("pending", operation["x-ti-migration"]["status"])
            self.assertEqual("inferred", operation["x-ti-contract-maturity"])
            self.assertEqual(
                "#/components/schemas/LegacyOpaquePayload",
                operation["responses"]["default"]["content"]["*/*"]
                ["schema"]["$ref"],
            )
        self.assertTrue(all(
            value is False for value in self.contract["forbidden_scope"].values()
        ))

    def test_06_usage_stats_entry_and_read_form_the_authorized_successor_chain(self):
        successor = self.usage_stats_entry
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-entry-contract",
            successor["contract_id"],
        )
        self.assertEqual(
            "entry_gate_passed_implementation_not_started", successor["status"]
        )
        self.assertEqual(CONTRACT_RELATIVE, successor["predecessor"]["source"])
        self.assertEqual(
            sha256(CONTRACT_PATH), successor["predecessor"]["sha256"]
        )
        self.assertEqual(
            USAGE_STATS_ROUTE_KEYS,
            set(successor["authorized_slice"]["only_operation_keys"]),
        )
        self.assertTrue(successor["entry_gate"]["implementation_authorized"])
        self.assertFalse(successor["entry_gate"]["http_migration_authorized"])
        self.assertFalse(successor["entry_gate"]["production_cutover_authorized"])
        self.assertFalse(
            successor["implementation_state"]["implementation_started"]
        )
        self.assertFalse(successor["implementation_state"]["production_source_added"])

        unchanged = successor["unchanged_state"]
        self.assertEqual(22, unchanged["implemented_public_application_method_count"])
        self.assertEqual(3, unchanged["personalbank_public_method_count"])
        self.assertEqual(11, unchanged["implemented_route_backed_operation_count"])
        self.assertEqual(11, unchanged["migrated_route_count"])
        self.assertEqual(600, unchanged["effective_pending_operation_count"])
        self.assertEqual(0, unchanged["production_cutover_count"])

        terminal = self.usage_stats_read
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-read-contract",
            terminal["contract_id"],
        )
        self.assertEqual(USAGE_STATS_ENTRY_RELATIVE,
                         terminal["predecessor"]["source"])
        self.assertEqual(sha256(USAGE_STATS_ENTRY_PATH),
                         terminal["predecessor"]["sha256"])
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            terminal["status"],
        )
        self.assertEqual(11, terminal["route_state"]["migrated_route_count"])
        self.assertEqual(600, terminal["route_state"]["pending_route_count"])
        self.assertEqual(0, terminal["route_state"]["production_cutover_count"])


if __name__ == "__main__":
    unittest.main()
