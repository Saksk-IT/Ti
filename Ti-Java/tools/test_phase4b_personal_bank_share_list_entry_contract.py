#!/usr/bin/env python3
"""Fail-closed checks for the Phase 4B personal-bank share-list entry gate."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
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


TI_JAVA_ROOT = pathlib.Path(__file__).resolve().parents[1]
PHASE4B_ROOT = TI_JAVA_ROOT / "docs" / "refactor" / "phase4b"
CONTRACT_PATH = PHASE4B_ROOT / "personal-bank-share-list-entry-contract.json"
SUCCESSOR_PATH = PHASE4B_ROOT / "personal-bank-share-list-read-contract.json"
TERMINAL_PATH = PHASE4B_ROOT / "personal-bank-usage-stats-read-contract.json"

ROUTE_KEYS = {
    "e817f8083d74|GET|/api/user/banks/api/<int:bank_id>/shares",
    "c50102968322|GET|/user/banks/api/<int:bank_id>/shares",
}
PREREQUISITES = {
    "complete_caller_attestation",
    "capture_first_and_second_query_failure_boundaries",
    "verify_postgresql_16_14_and_18_4_jdbc_and_query_plans",
    "freeze_null_ordering_and_dialect_behavior",
}
QUERY_SEQUENCE = [
    "personal_bank_owner_status_probe",
    "personal_bank_share_list_select",
]
SELECTED_COLUMNS = [
    "id",
    "bank_id",
    "owner_id",
    "share_code",
    "share_token",
    "permission",
    "expires_at",
    "max_uses",
    "current_uses",
    "is_active",
    "created_at",
]
EXPECTED_SHARE_COMPONENTS = [
    {"name": "id", "java_type": "int", "nullable": False},
    {"name": "bankId", "java_type": "int", "nullable": False},
    {"name": "ownerId", "java_type": "long", "nullable": False},
    {"name": "shareCode", "java_type": "java.lang.String", "nullable": True},
    {"name": "shareToken", "java_type": "java.lang.String", "nullable": True},
    {"name": "permission", "java_type": "java.lang.String", "nullable": True},
    {
        "name": "expiresAt",
        "java_type": "java.time.LocalDateTime",
        "nullable": True,
    },
    {"name": "maxUses", "java_type": "java.lang.Integer", "nullable": True},
    {"name": "currentUses", "java_type": "java.lang.Integer", "nullable": True},
    {"name": "isActive", "java_type": "java.lang.Boolean", "nullable": True},
    {
        "name": "createdAt",
        "java_type": "java.time.LocalDateTime",
        "nullable": True,
    },
]
EXPECTED_MAIN_SOURCE_MANIFEST = {
    "server/src/main/java/io/saksk/ti/personalbank/api/AuthenticatedPersonalBankViewer.java":
        "a1d0fe3791ced4e45bbeb6ce254eda704bb3f81a49c4ba3cd068cc52db315760",
    "server/src/main/java/io/saksk/ti/personalbank/api/PersonalBankApplicationApi.java":
        "58435de470bda3ecdf4668f3968d201dde04d861f6989a379b6bb83ccc90f08c",
    "server/src/main/java/io/saksk/ti/personalbank/api/PersonalBankCategoryView.java":
        "70435695f616c48306ad1d0b622ad3243a9cb1ad5cca303cfd3b6329f339bab5",
    "server/src/main/java/io/saksk/ti/personalbank/api/package-info.java":
        "575e22a59276f7ef2f94eef87fceed201cb4428caa7270051d10019ea7ae2966",
    "server/src/main/java/io/saksk/ti/personalbank/application/PersonalBankQueryService.java":
        "c66fbf299d68b57fa0ca11f1135b203479b801b1ee3ced01dd7e20739ea99820",
    "server/src/main/java/io/saksk/ti/personalbank/application/port/PersonalBankCategoryQueryPort.java":
        "f611707567dc2e425ace5851802f61cdd9c9ff3fc518aebdb7c79d98a7b975ca",
    "server/src/main/java/io/saksk/ti/personalbank/infrastructure/persistence/JdbcPersonalBankCategoryQueryAdapter.java":
        "749a70cad4c83acdca9ef5a68ef31a48901e394718a95363ae910a0d2102a2ad",
    "server/src/main/java/io/saksk/ti/personalbank/package-info.java":
        "d5d53fe893de9d408a2e45ffb03597c57b72dad3f4ce765b5ab4d902f3d2699f",
}


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict) -> str:
    return sha256_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    })


_VALIDATED_READ_SUCCESSORS: dict[str, str] = {}


def capture_validated_read_successors(contract: dict | None) -> None:
    if contract is None:
        return
    history = contract["historical_successor_acceptance"]
    for section in ("python_sources", "java_sources", "auxiliary_sources"):
        for relative in history[section]:
            _VALIDATED_READ_SUCCESSORS[relative] = sha256(
                TI_JAVA_ROOT / relative
            )


def phase4c_successor_hash(relative: str) -> str | None:
    validated = _VALIDATED_READ_SUCCESSORS.get(relative)
    if validated is None:
        return successor_sha256(TI_JAVA_ROOT, relative)
    if sha256(TI_JAVA_ROOT / relative) != validated:
        raise AssertionError(f"validated read successor drifted: {relative}")
    return validated


def learning_and_personalbank_main_source_manifest() -> dict[str, str]:
    main_root = TI_JAVA_ROOT / "server/src/main/java/io/saksk/ti"
    paths = []
    for module in ("learning", "personalbank"):
        paths.extend((main_root / module).rglob("*.java"))
    return {
        path.relative_to(TI_JAVA_ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


class Phase4bPersonalBankShareListEntryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._validation_session = acceptance_validation_session()
        cls._validation_session.__enter__()
        cls.addClassCleanup(cls._validation_session.__exit__, None, None, None)
        cls.read_successor = load_read_successor_contract(TI_JAVA_ROOT)
        capture_validated_read_successors(cls.read_successor)
        cls.contract = load_json(CONTRACT_PATH)
        cls.category = load_json(
            PHASE4B_ROOT / "personal-bank-category-acceptance.json"
        )
        cls.shape = load_json(PHASE4B_ROOT / "application-api-shape-status.json")
        cls.callers = load_json(
            PHASE4B_ROOT / "personal-bank-share-list-callers.json"
        )
        cls.golden = load_json(
            PHASE4B_ROOT / "golden-personal-bank-share-list-reads.json"
        )
        cls.plan = load_json(
            PHASE4B_ROOT / "personal-bank-share-list-query-plan-evidence.json"
        )
        cls.openapi = load_json(TI_JAVA_ROOT / "contracts/openapi.json")
        cls.successor = load_json(SUCCESSOR_PATH)
        cls.terminal = load_json(TERMINAL_PATH)

    def test_01_predecessor_scope_and_all_source_hashes_are_closed(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-share-list-entry-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "entry_gate_passed_implementation_not_started", contract["status"]
        )
        self.assertEqual("700006dfdfa063deb4387be572911e782bcea0d9", contract["legacy_commit"])
        predecessor = contract["predecessor"]
        self.assertEqual("passed", predecessor["status"])
        self.assertTrue(predecessor["category_internal_read_closed"])
        self.assertEqual(
            sha256(TI_JAVA_ROOT / predecessor["source"]), predecessor["sha256"]
        )
        self.assertEqual(predecessor["sha256"], sha256(
            PHASE4B_ROOT / "personal-bank-category-acceptance.json"
        ))
        self.assertEqual("passed", self.category["status"])

        for name, reference in contract["source_contracts"].items():
            source = TI_JAVA_ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            if name == "application_api":
                successor_files = self.terminal["implementation"]["main_source_files"]
                successor_hashes = self.terminal["implementation"]["main_source_sha256"]
                self.assertEqual(reference["source"], successor_files[name])
                current_hash = sha256(source)
                if self.read_successor is None:
                    self.assertEqual(successor_hashes[name], current_hash, name)
                else:
                    self.assertEqual(
                        self.read_successor["implementation"]
                        ["learning_and_personalbank_main_source_manifest"]
                        [reference["source"]],
                        current_hash,
                        name,
                    )
                self.assertNotEqual(reference["sha256"], sha256(source), name)
            elif name in {
                "entry_contract_test",
                "category_acceptance_forward_handoff_test",
            }:
                successor_files = self.terminal["implementation"][
                    "verification_source_files"
                ]
                successor_hashes = self.terminal["implementation"][
                    "verification_source_sha256"
                ]
                successor_name = {
                    "entry_contract_test": "share_list_entry_forward_handoff_test",
                    "category_acceptance_forward_handoff_test":
                        "category_acceptance_forward_handoff_test",
                }[name]
                self.assertEqual(reference["source"], successor_files[successor_name])
                current_hash = sha256(source)
                if self.read_successor is None:
                    self.assertEqual(
                        successor_hashes[successor_name], current_hash, name
                    )
                else:
                    read_hash = phase4c_successor_hash(reference["source"])
                    if read_hash is None:
                        self.assertEqual(
                            successor_hashes[successor_name], current_hash, name
                        )
                    else:
                        self.assertEqual(read_hash, current_hash, name)
                self.assertNotEqual(reference["sha256"], sha256(source), name)
            else:
                self.assertEqual(reference["sha256"], sha256(source), name)

        self.assertEqual(
            "ti.phase4b.personal-bank-share-list-read-contract",
            self.successor["contract_id"],
        )
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            self.successor["status"],
        )
        self.assertEqual(
            CONTRACT_PATH.name, self.successor["predecessor"]["source"]
        )
        self.assertEqual(
            sha256(CONTRACT_PATH), self.successor["predecessor"]["sha256"]
        )
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-read-contract",
            self.terminal["contract_id"],
        )

        self.assertEqual(
            ROUTE_KEYS,
            set(contract["authorized_slice"]["only_operation_keys"]),
        )
        self.assertEqual(
            ROUTE_KEYS,
            set(self.category["authorized_next_slice"]["only_operation_keys"]),
        )
        self.assertEqual(
            PREREQUISITES,
            set(self.category["authorized_next_slice"]["required_before_implementation"]),
        )

    def test_02_caller_attestation_is_complete_and_additive(self):
        caller_gate = self.contract["entry_prerequisites"]["caller_attestation"]
        self.assertTrue(caller_gate["passed"])
        self.assertEqual(46, caller_gate["repository_match_count"])
        self.assertEqual(19, caller_gate["matched_source_count"])
        self.assertEqual(
            self.callers["attestation_sha256"], caller_gate["attestation_sha256"]
        )
        self.assertEqual(
            self.callers["document_payload_sha256"],
            caller_gate["document_payload_sha256"],
        )
        self.assertTrue(self.callers["closure"]["caller_attestation_complete"])
        self.assertTrue(all(self.callers["closure"].values()))
        self.assertTrue(self.callers["frozen_route_matrix_disposition"]["matrix_is_immutable"])
        self.assertTrue(
            self.callers["frozen_route_matrix_disposition"]
            ["matrix_rows_are_not_a_complete_caller_inventory"]
        )
        self.assertEqual("active", self.callers["callers"]["web"]["state"])
        self.assertEqual(
            "active",
            self.callers["callers"]["miniprogram"]["active_bank_detail"]["state"],
        )
        self.assertEqual(
            "dormant_external_entry_candidate",
            self.callers["callers"]["miniprogram"]
            ["dedicated_bank_share_page"]["state"],
        )
        self.assertEqual(
            {item["route_id"] for item in self.callers["routes"]},
            {key.split("|", 1)[0] for key in ROUTE_KEYS},
        )
        web = self.callers["callers"]["web"]
        self.assertEqual(293, web["optional_share_link_branch"]["guard"]["line"])
        self.assertIn(
            "must not be synthesized",
            web["optional_share_link_branch"]["server_contract"],
        )
        mini = self.callers["callers"]["miniprogram"]
        self.assertEqual(
            110,
            mini["path_derivation"]["request_url_composition"]
            ["concatenation"]["line"],
        )
        active = mini["active_bank_detail"]
        self.assertEqual(
            [2043, 2049, 2055, 2096, 2107],
            [
                active["compiled_runtime"][key]["line"]
                for key in (
                    "call",
                    "active_filter",
                    "token_picker_call",
                    "order_preserving_iteration",
                    "first_valid_return",
                )
            ],
        )
        self.assertEqual(
            {"id", "share_code", "current_uses", "expires_at",
             "expires_at_display", "is_active"},
            set(active["wxml_consumption"]["fields"]),
        )
        self.assertIn("first active non-expired", mini["ordering_dependency"])

    def test_03_goldens_freeze_two_queries_and_independent_failures(self):
        golden_gate = self.contract["entry_prerequisites"][
            "first_and_second_query_failure_boundaries"
        ]
        self.assertTrue(golden_gate["passed"])
        self.assertEqual(40, golden_gate["case_count"])
        self.assertEqual(40, self.golden["case_count"])
        self.assertEqual(40, len(self.golden["cases"]))
        self.assertEqual(
            {"e817f8083d74": 20, "c50102968322": 20},
            {
                route_id: sum(
                    case["route_id"] == route_id for case in self.golden["cases"]
                )
                for route_id in ("e817f8083d74", "c50102968322")
            },
        )
        self.assertEqual(
            golden_gate["case_payload_sha256"], self.golden["case_payload_sha256"]
        )
        self.assertEqual(
            golden_gate["document_payload_sha256"],
            self.golden["document_payload_sha256"],
        )
        self.assertEqual(SELECTED_COLUMNS, self.golden["response_contract"]["selected_columns"])
        self.assertEqual(11, self.golden["response_contract"]["selected_column_count"])
        self.assertIsNone(self.golden["response_contract"]["pagination"])
        sequence = self.golden["legacy_query_sequence"]
        self.assertEqual("owner_status_probe_then_share_list", sequence["shape"])
        self.assertFalse(sequence["join_authorized"])
        self.assertFalse(sequence["parallel_execution_authorized"])

        cases = {case["case_id"]: case for case in self.golden["cases"]}
        for alias in ("api-alias", "web-alias"):
            self.assertEqual(
                QUERY_SEQUENCE,
                cases[f"auth-session-owner-{alias}"]["observed_get_effects"]
                ["sql"]["personal_bank_query_sequence"],
            )
            self.assertEqual(
                QUERY_SEQUENCE,
                cases[f"bank-zero-{alias}"]["observed_get_effects"]
                ["sql"]["personal_bank_query_sequence"],
            )
            self.assertEqual(
                [QUERY_SEQUENCE[0]],
                cases[f"bank-missing-{alias}"]["observed_get_effects"]
                ["sql"]["personal_bank_query_sequence"],
            )
            self.assertEqual(
                [],
                cases[f"bank-negative-path-{alias}"]["observed_get_effects"]
                ["sql"]["personal_bank_query_sequence"],
            )
            self.assertEqual(
                [QUERY_SEQUENCE[0]],
                cases[f"fault-owner-probe-default-{alias}"]["observed_get_effects"]
                ["sql"]["personal_bank_query_sequence"],
            )
            self.assertEqual(
                QUERY_SEQUENCE,
                cases[f"fault-share-list-default-{alias}"]["observed_get_effects"]
                ["sql"]["personal_bank_query_sequence"],
            )

        owner_shares = (
            cases["auth-session-owner-api-alias"]["response"]
            ["body"]["data"]["shares"]
        )
        self.assertEqual(set(SELECTED_COLUMNS), set(owner_shares[0]))
        self.assertTrue(all("share_link" not in row for row in owner_shares))
        self.assertIn(0, {row["id"] for row in owner_shares})
        self.assertIn(-2, {row["id"] for row in owner_shares})
        self.assertTrue(any(row["owner_id"] == 98002 for row in owner_shares))
        self.assertTrue(any(row["is_active"] == 0 for row in owner_shares))
        self.assertTrue(any(row["expires_at"] == "2020-01-01 00:00:00"
                            for row in owner_shares))
        self.assertTrue(any(row["max_uses"] == -1 and row["current_uses"] == -2
                            for row in owner_shares))
        self.assertTrue(any(row["permission"] == "unexpected-value"
                            for row in owner_shares))
        nullable = (
            cases["data-nullable-fields-api-alias"]["response"]
            ["body"]["data"]["shares"][0]
        )
        for name in (
            "share_code",
            "share_token",
            "permission",
            "expires_at",
            "max_uses",
            "current_uses",
            "is_active",
            "created_at",
        ):
            self.assertIsNone(nullable[name], name)
        self.assertEqual(
            [],
            cases["data-empty-api-alias"]["response"]["body"]["data"]["shares"],
        )
        self.assertEqual(200, cases["data-empty-api-alias"]["response"]["status"])
        self.assertEqual(404, cases["bank-missing-api-alias"]["response"]["status"])

    def test_04_sql_jdbc_and_cross_version_plan_contracts_are_closed(self):
        sql_gate = self.contract["entry_prerequisites"]["jdbc_and_query_plans"]
        self.assertTrue(sql_gate["passed"])
        sql_contract = self.plan["sql_contract"]
        self.assertEqual(2, sql_contract["query_count"])
        self.assertTrue(sql_contract["sequential_execution_required"])
        self.assertFalse(sql_contract["join_authorized"])
        self.assertTrue(sql_contract["second_query_requires_first_query_row"])
        self.assertFalse(sql_contract["production_source_added"])
        queries = sql_contract["manifest"]["queries"]
        self.assertEqual([1, 2], [query["ordinal"] for query in queries])
        self.assertEqual(["bank_id", "viewer_id"], queries[0]["parameter_order"])
        self.assertEqual(
            {"bank_id": "integer", "viewer_id": "bigint"},
            queries[0]["parameters"],
        )
        self.assertEqual(["bank_id"], queries[1]["parameter_order"])
        self.assertIn("ORDER BY created_at DESC NULLS FIRST", queries[1]["sql"])
        self.assertNotRegex(queries[1]["sql"], r"(?i)\bid\s+(?:asc|desc)\b")
        self.assertNotRegex("\n".join(query["sql"] for query in queries), r"(?i)\bjoin\b")
        frozen_queries = self.contract["frozen_internal_contract"]["query_sequence"]
        self.assertEqual(2, len(frozen_queries))
        for frozen, manifest in zip(frozen_queries, queries, strict=True):
            self.assertEqual(manifest["ordinal"], frozen["ordinal"])
            self.assertEqual(manifest["query_id"], frozen["query_id"])
            self.assertEqual(manifest["sql"], frozen["sql"])
            self.assertEqual(manifest["parameter_order"], frozen["parameter_order"])
            self.assertEqual(manifest["parameters"], frozen["parameter_types"])

        self.assertEqual(
            self.plan["document_payload_sha256"],
            document_payload_sha256(self.plan),
        )
        self.assertEqual(
            self.plan["inputs"]["sql_manifest_payload_sha256"],
            sha256_json(sql_contract["manifest"]),
        )
        plan_inputs = {
            "evidence_sql": "evidence_sql",
            "sql_contract_test": "sql_contract_test",
            "sql_manifest_exporter": "sql_manifest_test",
            "jdbc_compatibility_test": "jdbc_compatibility_test",
            "schema": "postgres_schema",
            "seed": "postgres_fixture",
            "capture_tool": "query_plan_capture_tool",
            "capture_tool_test": "query_plan_capture_tool_test",
        }
        for input_name, source_name in plan_inputs.items():
            self.assertEqual(
                self.contract["source_contracts"][source_name]["sha256"],
                self.plan["inputs"][f"{input_name}_sha256"],
                input_name,
            )

        self.assertEqual(["16.14", "18.4"], [
            engine["server_version"] for engine in self.plan["engines"]
        ])
        for engine in self.plan["engines"]:
            self.assertEqual(2, len(engine["observations"]))
            probe, share_list = engine["observations"]
            self.assertEqual(
                "bigint",
                probe["binding"]["parameters"]["viewer_id"]["postgres_type"],
            )
            self.assertEqual("Index Scan", probe["plan_summary"]["root_node_type"])
            self.assertEqual(["user_question_banks_pkey"], probe["plan_summary"]["index_names"])
            self.assertEqual(
                {"user_question_banks": 1},
                probe["plan_summary"]["relation_scan_occurrences"],
            )
            self.assertEqual("Sort", share_list["plan_summary"]["root_node_type"])
            self.assertEqual(["Sort", "Seq Scan"], share_list["plan_summary"]["node_types_preorder"])
            self.assertEqual([], share_list["plan_summary"]["index_names"])
            self.assertEqual(
                {"bank_shares": 1},
                share_list["plan_summary"]["relation_scan_occurrences"],
            )
            for observation in (probe, share_list):
                summary = observation["plan_summary"]
                self.assertEqual(1, summary["maximum_actual_loops"])
                self.assertEqual(0, summary["temp_read_blocks"])
                self.assertEqual(0, summary["temp_written_blocks"])
            self.assertEqual(303, share_list["result"]["row_count"])
            self.assertEqual(11, share_list["result"]["column_count"])
            self.assertTrue(share_list["result"]["all_null_created_at_rows_are_leading"])
            self.assertTrue(share_list["result"]["non_null_created_at_descending"])
            self.assertEqual(
                "unordered_within_group",
                share_list["result"]["equal_created_at_order_contract"],
            )
            self.assertEqual(["<NULL>", "f", "t"], share_list["result"]["postgres_boolean_values"])
            self.assertTrue(share_list["result"]["cross_owner_rows_present"])
            self.assertTrue(share_list["result"]["inactive_rows_present"])
        limits = self.plan["claim_limits"]
        self.assertTrue(limits["observational_evidence_only"])
        self.assertFalse(limits["index_change_authorized"])
        self.assertFalse(limits["schema_change_authorized"])
        self.assertFalse(limits["http_parity_claimed"])
        self.assertFalse(limits["production_cutover_claimed"])
        verification = sql_gate["verification_record"]
        self.assertEqual("passed", verification["status"])
        self.assertEqual(5, verification["runner_totals"]["surefire"]["tests"])
        self.assertEqual(2, verification["runner_totals"]["failsafe"]["tests"])

    def test_05_expected_api_wrapper_and_raw_result_shape_are_frozen(self):
        expected = self.contract["expected_application_shape"]
        self.assertEqual("findShares", expected["method_name"])
        self.assertEqual(
            "java.util.Optional<io.saksk.ti.personalbank.api.PersonalBankShareListView>",
            expected["return_type"],
        )
        self.assertEqual(
            [
                "io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer",
                "int",
            ],
            expected["parameter_types"],
        )
        self.assertEqual(EXPECTED_SHARE_COMPONENTS, expected["share_record_components"])
        self.assertEqual(
            [{"name": "shares", "java_type":
              "java.util.List<io.saksk.ti.personalbank.api.PersonalBankShareView>"}],
            expected["list_record_components"],
        )
        distinction = expected["availability_distinction"]
        self.assertEqual("Optional.empty", distinction["owner_probe_no_row"])
        self.assertEqual(
            "Optional.of(PersonalBankShareListView with empty immutable shares)",
            distinction["owner_probe_row_and_no_shares"],
        )

        inputs = self.contract["frozen_internal_contract"]["input"]
        self.assertEqual("int", inputs["bank_id"]["java_type"])
        self.assertEqual("integer", inputs["bank_id"]["jdbc_bind_type"])
        self.assertTrue(inputs["bank_id"]["zero_supported"])
        self.assertFalse(inputs["bank_id"]["new_positive_validation_authorized"])
        self.assertEqual("long", inputs["viewer_id"]["java_type"])
        self.assertEqual("bigint", inputs["viewer_id"]["jdbc_bind_type"])
        self.assertEqual("integer", inputs["viewer_id"]["legacy_column_type"])
        self.assertEqual(
            "AuthenticatedPersonalBankViewer identityId must be positive",
            inputs["viewer_id"]["identity_invariant"],
        )
        semantics = self.contract["frozen_internal_contract"]["result_semantics"]
        for name, value in semantics.items():
            if name == "share_link":
                self.assertEqual("absent_and_must_not_be_synthesized", value)
            elif name == "equal_created_at_order":
                self.assertEqual("unordered_and_not_resorted_in_java", value)
            else:
                self.assertTrue(value, name)

    def test_06_shape_route_matrix_openapi_and_main_sources_are_unchanged(self):
        state = self.contract["unchanged_state"]
        self.assertEqual(11, self.shape["migrated_route_count"])
        self.assertEqual(11, self.shape["implemented_route_backed_operation_count"])
        self.assertEqual(20, self.shape["implemented_public_application_method_count"])
        self.assertEqual(11, state["migrated_route_count"])
        self.assertEqual(600, state["pending_route_count"])
        self.assertEqual(0, state["production_cutover_count"])
        personalbank = next(
            module for module in self.shape["modules"]
            if module["module_id"] == "personalbank"
        )
        self.assertEqual(1, len(personalbank["methods"]))
        self.assertEqual("listCategories", personalbank["methods"][0]["name"])
        self.assertEqual([], personalbank["implemented_route_ids"])
        self.assertFalse(personalbank["direct_http_operation"])

        actual_manifest = {
            path.relative_to(TI_JAVA_ROOT).as_posix(): sha256(path)
            for path in sorted((TI_JAVA_ROOT / "server/src/main/java/io/saksk/ti/personalbank")
                               .rglob("*.java"))
        }
        self.assertEqual(EXPECTED_MAIN_SOURCE_MANIFEST, state["personalbank_main_source_manifest"])
        self.assertFalse(self.contract["implementation_state"]["implementation_started"])
        self.assertEqual([], self.contract["implementation_state"]["main_source_files_added"])

        expected_current_manifest = self.terminal["implementation"][
            "personalbank_main_source_manifest"
        ]
        if self.read_successor is None:
            self.assertEqual(expected_current_manifest, actual_manifest)
        else:
            accepted_manifest = self.read_successor["implementation"][
                "learning_and_personalbank_main_source_manifest"
            ]
            current_manifest = learning_and_personalbank_main_source_manifest()
            runtime = validate_tag_preflight_production_runtime_successor(
                TI_JAVA_ROOT,
                accepted_manifest,
                current_manifest,
                view="learning_personalbank_main",
            )
            self.assertEqual(40, runtime.accepted_file_count)
            self.assertEqual(54, runtime.current_file_count)
            self.assertEqual(14, len(runtime.added_files))
            self.assertEqual((), runtime.changed_files)
            self.assertEqual((), runtime.deleted_files)

        with (TI_JAVA_ROOT / "docs/refactor/02-route-parity-matrix.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        selected = {
            f'{row["route_id"]}|{row["methods"]}|{row["path"]}': row
            for row in rows if row["route_id"] in {key.split("|", 1)[0] for key in ROUTE_KEYS}
        }
        self.assertEqual(ROUTE_KEYS, set(selected))
        self.assertTrue(all(row["migration_status"] == "pending" for row in selected.values()))
        self.assertTrue(all(row["target_module"] == "personalbank" for row in selected.values()))

        baseline = self.contract["openapi_baseline"]
        self.assertEqual("3.1.2", self.openapi["openapi"])
        self.assertTrue(baseline["baseline_is_immutable"])
        self.assertFalse(baseline["openapi_delta_authorized"])
        for expected in baseline["operations"]:
            operation = self.openapi["paths"][expected["path"]]["get"]
            self.assertEqual(expected["operation_id"], operation["operationId"])
            self.assertEqual(expected["route_id"], operation["x-ti-legacy"]["routeId"])
            self.assertEqual("inferred", operation["x-ti-contract-maturity"])
            self.assertEqual("pending", operation["x-ti-migration"]["status"])
            self.assertNotIn("x-ti-migration-status", operation)
            self.assertEqual({"default"}, set(operation["responses"]))
            response = operation["responses"]["default"]
            self.assertEqual("unknown", response["x-ti-schema-status"])
            self.assertEqual(
                "#/components/schemas/LegacyOpaquePayload",
                response["content"]["*/*"]["schema"]["$ref"],
            )
            self.assertEqual(expected["payload_sha256"], sha256_json(operation))
        opaque = self.openapi["components"]["schemas"]["LegacyOpaquePayload"]
        self.assertEqual("legacy", opaque["x-ti-envelope"])
        self.assertEqual("unknown", opaque["x-ti-schema-status"])
        self.assertNotIn("type", opaque)
        self.assertNotIn("properties", opaque)
        self.assertEqual(baseline["legacy_opaque_payload_sha256"], sha256_json(opaque))

    def test_07_entry_gate_only_authorizes_http_neutral_internal_implementation(self):
        contract = self.contract
        self.assertTrue(contract["entry_gate"]["passed"])
        self.assertTrue(all(
            gate["passed"] for gate in contract["entry_prerequisites"].values()
        ))
        self.assertEqual(PREREQUISITES, set(contract["entry_gate"]["completed_prerequisites"]))
        maven = contract["entry_gate"]["full_maven_verification"]
        self.assertTrue(maven["passed"])
        self.assertEqual(0, maven["exit_code"])
        self.assertEqual(429, maven["surefire"]["tests"])
        self.assertEqual(62, maven["failsafe"]["tests"])
        for runner in ("surefire", "failsafe"):
            self.assertEqual(0, maven[runner]["failures"])
            self.assertEqual(0, maven[runner]["errors"])
            self.assertEqual(0, maven[runner]["skipped"])
        authorization = contract["next_authorization"]
        self.assertEqual(
            "http_neutral_personal_bank_share_list_internal_implementation_and_parity_evidence",
            authorization["scope"],
        )
        self.assertTrue(authorization["authorized"])
        self.assertFalse(authorization["controller_authorized"])
        self.assertFalse(authorization["security_matcher_authorized"])
        self.assertFalse(authorization["route_openapi_delta_authorized"])
        self.assertFalse(authorization["production_cutover_authorized"])
        self.assertFalse(contract["route_state"]["aliases_migrated"])
        self.assertFalse(contract["route_state"]["production_cutover"])
        self.assertEqual(
            {
                "controller",
                "security_matcher",
                "route_delta",
                "openapi_delta",
                "create_share",
                "delete_share",
                "join_share",
                "share_records",
                "share_statistics",
                "cache",
                "rate_limit",
                "database_index",
                "database_schema",
                "query_join_or_parallelization",
                "stable_tie_breaker",
                "production_cutover",
            },
            set(authorization["forbidden_scope"]),
        )


if __name__ == "__main__":
    unittest.main()
