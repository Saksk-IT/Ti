#!/usr/bin/env python3
"""Fail-closed checks for the Phase 4B personal-bank all-shares entry gate."""

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
    )
    from tools.phase4c_http_target_execution_successor_acceptance import (
        fixed_source_sha256 as target_fixed_source_sha256,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase4c_read_successor_acceptance import (
        load_read_successor_contract,
        successor_sha256,
    )
    from phase4c_http_target_execution_successor_acceptance import (
        fixed_source_sha256 as target_fixed_source_sha256,
    )


TI_JAVA_ROOT = Path(__file__).resolve().parents[1]
PHASE4B_ROOT = TI_JAVA_ROOT / "docs" / "refactor" / "phase4b"
CONTRACT_PATH = PHASE4B_ROOT / "personal-bank-all-shares-entry-contract.json"
SUCCESSOR_PATH = PHASE4B_ROOT / "personal-bank-all-shares-read-contract.json"
USAGE_STATS_ENTRY_PATH = (
    PHASE4B_ROOT / "personal-bank-usage-stats-entry-contract.json"
)
USAGE_STATS_READ_PATH = (
    PHASE4B_ROOT / "personal-bank-usage-stats-read-contract.json"
)
USAGE_STATS_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json"
)
PHASE4C_COMPOSITION_PATH = (
    TI_JAVA_ROOT
    / "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)
PHASE3_AUTH_TIME_HANDOFF_NAME = "phase3_auth_time_forward_handoff_test"
PHASE3_AUTH_TIME_HISTORICAL_SHA256 = (
    "cbafdbd774ab13429c834b20c7a89eab63f10f35edfc20173181bbbdf0e2e85c"
)
TERMINAL_SOURCE_HANDOFFS = {
    "application_api": ("main_source", "application_api"),
    "share_list_read_forward_handoff_test": (
        "verification_source", "share_read_contract_test"
    ),
    "share_list_java_forward_handoff_test": (
        "verification_source", "share_list_contract_parity_test"
    ),
    "entry_contract_test": (
        "verification_source", "all_shares_entry_forward_handoff_test"
    ),
    "progress_forward_handoff": (
        "verification_source", "progress_forward_handoff"
    ),
}

ROUTE_KEYS = {
    "a6fda3638fc3|GET|/api/user/banks/api/shares/all",
    "0fdd3026f636|GET|/user/banks/api/shares/all",
}
SELECTED_FIELDS = [
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
    "bank_name",
]
EXPECTED_COMPONENTS = [
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


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def phase4c_successor_hash(relative: str) -> str | None:
    return successor_sha256(TI_JAVA_ROOT, relative)


def learning_and_personalbank_main_source_manifest() -> dict[str, str]:
    main_root = TI_JAVA_ROOT / "server/src/main/java/io/saksk/ti"
    paths = []
    for module in ("learning", "personalbank"):
        paths.extend((main_root / module).rglob("*.java"))
    return {
        path.relative_to(TI_JAVA_ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


class Phase4bPersonalBankAllSharesEntryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read_successor = load_read_successor_contract(TI_JAVA_ROOT)
        cls.contract = load_json(CONTRACT_PATH)
        cls.predecessor = load_json(
            PHASE4B_ROOT / "personal-bank-share-list-read-contract.json"
        )
        cls.callers = load_json(
            PHASE4B_ROOT / "personal-bank-all-shares-callers.json"
        )
        cls.golden = load_json(
            PHASE4B_ROOT / "golden-personal-bank-all-shares-reads.json"
        )
        cls.plan = load_json(
            PHASE4B_ROOT / "personal-bank-all-shares-query-plan-evidence.json"
        )
        cls.openapi = load_json(TI_JAVA_ROOT / "contracts" / "openapi.json")
        cls.successor = load_json(SUCCESSOR_PATH)
        cls.usage_stats_entry = load_json(USAGE_STATS_ENTRY_PATH)
        cls.terminal = load_json(USAGE_STATS_READ_PATH)

    def test_01_identity_predecessor_and_all_source_hashes_are_closed(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-entry-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "entry_gate_passed_implementation_not_started", contract["status"]
        )
        self.assertEqual(
            "700006dfdfa063deb4387be572911e782bcea0d9",
            contract["legacy_commit"],
        )
        predecessor = contract["predecessor"]
        self.assertEqual("passed", predecessor["status"])
        self.assertTrue(predecessor["share_list_internal_read_closed"])
        self.assertFalse(predecessor["share_list_http_aliases_migrated"])
        self.assertFalse(predecessor["production_cutover"])
        self.assertEqual(
            sha256(TI_JAVA_ROOT / predecessor["source"]),
            predecessor["sha256"],
        )
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            self.predecessor["status"],
        )
        self.assertTrue(self.predecessor["final_acceptance"]["passed"])

        for name, reference in contract["source_contracts"].items():
            source = TI_JAVA_ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            current_hash = sha256(source)
            if name == PHASE3_AUTH_TIME_HANDOFF_NAME:
                self.assertEqual(
                    PHASE3_AUTH_TIME_HISTORICAL_SHA256,
                    reference["sha256"],
                )
                self.assertEqual(
                    current_hash,
                    target_fixed_source_sha256(
                        TI_JAVA_ROOT, reference["source"]
                    ),
                )
                self.assertNotEqual(reference["sha256"], current_hash)
                continue
            handoff = TERMINAL_SOURCE_HANDOFFS.get(name)
            if handoff is None:
                self.assertEqual(reference["sha256"], current_hash, name)
                continue
            section, terminal_name = handoff
            files = self.terminal["implementation"][f"{section}_files"]
            hashes = self.terminal["implementation"][f"{section}_sha256"]
            self.assertEqual(reference["source"], files[terminal_name])
            phase4c_hash = phase4c_successor_hash(reference["source"])
            if self.read_successor is not None:
                if phase4c_hash is None:
                    self.assertEqual(hashes[terminal_name], current_hash, name)
                else:
                    self.assertEqual(phase4c_hash, current_hash, name)
            elif phase4c_hash is None:
                self.assertEqual(hashes[terminal_name], current_hash, name)
            else:
                self.assertEqual(phase4c_hash, current_hash, name)
                self.assertNotEqual(hashes[terminal_name], current_hash, name)
            self.assertNotEqual(reference["sha256"], current_hash, name)

        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-read-contract",
            self.successor["contract_id"],
        )
        self.assertEqual(
            CONTRACT_PATH.relative_to(TI_JAVA_ROOT).as_posix(),
            self.successor["predecessor"]["source"],
        )
        self.assertEqual(
            sha256(CONTRACT_PATH), self.successor["predecessor"]["sha256"]
        )
        self.assertEqual(
            SUCCESSOR_PATH.relative_to(TI_JAVA_ROOT).as_posix(),
            self.usage_stats_entry["predecessor"]["source"],
        )
        self.assertEqual(
            sha256(SUCCESSOR_PATH),
            self.usage_stats_entry["predecessor"]["sha256"],
        )
        self.assertEqual(
            USAGE_STATS_ENTRY_RELATIVE,
            self.terminal["predecessor"]["source"],
        )
        self.assertEqual(
            sha256(USAGE_STATS_ENTRY_PATH),
            self.terminal["predecessor"]["sha256"],
        )

        self.assertEqual(
            contract["document_payload_sha256"],
            document_payload_sha256(contract),
        )

    def test_02_only_the_two_pending_aliases_are_authorized(self):
        contract = self.contract
        self.assertEqual(
            ROUTE_KEYS,
            set(contract["authorized_slice"]["only_operation_keys"]),
        )
        self.assertTrue(
            contract["authorized_slice"]["http_neutral_internal_implementation_only"]
        )
        self.assertEqual(
            "single_joined_all_shares_select",
            contract["authorized_slice"]["legacy_query_shape_to_preserve"],
        )

        with (TI_JAVA_ROOT / "docs/refactor/02-route-parity-matrix.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {
                f"{row['route_id']}|{row['methods']}|{row['path']}": row
                for row in csv.DictReader(handle)
                if row["route_id"] in {"a6fda3638fc3", "0fdd3026f636"}
            }
        self.assertEqual(ROUTE_KEYS, set(rows))
        for row in rows.values():
            self.assertEqual("personalbank", row["target_module"])
            self.assertEqual("pending", row["migration_status"])
            self.assertIn("auth_required", row["decorators"])

        for path, route_id in (
            ("/api/user/banks/api/shares/all", "a6fda3638fc3"),
            ("/user/banks/api/shares/all", "0fdd3026f636"),
        ):
            operation = self.openapi["paths"][path]["get"]
            self.assertEqual(route_id, operation["x-ti-legacy"]["routeId"])
            self.assertEqual("pending", operation["x-ti-migration"]["status"])
            self.assertEqual("inferred", operation["x-ti-contract-maturity"])
            self.assertEqual(
                "#/components/schemas/LegacyOpaquePayload",
                operation["responses"]["default"]["content"]["*/*"]["schema"]["$ref"],
            )

        route_state = contract["route_state"]
        self.assertEqual(11, route_state["migrated_route_count"])
        self.assertEqual(600, route_state["pending_route_count"])
        self.assertEqual(0, route_state["production_cutover_count"])
        self.assertFalse(route_state["aliases_migrated"])
        self.assertFalse(route_state["controller_added"])
        self.assertFalse(route_state["security_matcher_added"])
        self.assertFalse(route_state["route_delta_added"])
        self.assertFalse(route_state["openapi_delta_added"])

    def test_03_caller_and_fixed_legacy_golden_evidence_are_complete(self):
        callers = self.callers
        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-caller-attestation",
            callers["contract_id"],
        )
        self.assertEqual(1, callers["callers"]["direct"][
            "full_repository_direct_alias_scan"
        ]["match_count"])
        direct = callers["callers"]["direct"]["direct_get"]
        self.assertEqual(
            "app/modules/user_bank/templates/user_bank/manage/shares_manage_all.html",
            direct["source"],
        )
        self.assertEqual(185, direct["line"])
        self.assertEqual(
            "page_entry_retired_with_404",
            callers["callers"]["page_entry"]["state"],
        )
        self.assertEqual(
            "return \"页面已下线\", 404",
            callers["callers"]["page_entry"]["terminal_response"]["text"],
        )
        self.assertEqual(
            0,
            callers["callers"]["miniprogram"]["full_miniprogram_text_scan"][
                "match_count"
            ],
        )
        self.assertTrue(callers["closure"]["caller_attestation_complete"])
        self.assertEqual(
            "both_http_aliases_remain_externally_registered",
            callers["external_compatibility"]["state"],
        )

        golden = self.golden
        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-read-goldens",
            golden["contract_id"],
        )
        self.assertEqual(20, golden["case_count"])
        self.assertEqual(
            golden["case_payload_sha256"], sha256_json(golden["cases"])
        )
        self.assertEqual(
            golden["document_payload_sha256"], document_payload_sha256(golden)
        )
        self.assertEqual(1, golden["legacy_query"]["statement_count"])
        self.assertEqual(["uid"], golden["legacy_query"]["binds"])
        self.assertEqual("ignored", golden["legacy_query"]["query_parameters"])
        self.assertEqual(SELECTED_FIELDS, golden["response_contract"]["raw_selected_columns"])
        self.assertIn("Python-truthy", golden["response_contract"]["conditional_field"])
        self.assertTrue(golden["failure_contract"]["injected_exception_redacted"])
        self.assertEqual(
            "unchanged", golden["request_effect_scope"]["personal_bank_business_tables"]
        )
        self.assertEqual(4, golden["fixture"]["owner_returned_count"])
        self.assertEqual(3, golden["fixture"]["excluded_bank_status_count"])
        self.assertEqual(1, golden["fixture"]["excluded_other_owner_count"])

        cases = {case["case_id"]: case for case in golden["cases"]}
        self.assertEqual(20, len(cases))
        self.assertEqual(
            200, cases["auth-session-mixed-api-alias"]["response"]["status"]
        )
        self.assertEqual(
            302, cases["auth-bearer-web-alias"]["response"]["status"]
        )
        self.assertEqual(
            401, cases["auth-anonymous-api-alias"]["response"]["status"]
        )
        self.assertEqual(
            302, cases["auth-anonymous-web-alias"]["response"]["status"]
        )
        self.assertEqual(
            "text", cases["fault-default-web-alias"]["response"]["body_kind"]
        )
        self.assertEqual(
            "json", cases["fault-json-web-alias"]["response"]["body_kind"]
        )

    def test_04_single_query_postgresql_contract_is_http_neutral(self):
        plan = self.plan
        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-query-plan-evidence",
            plan["contract_id"],
        )
        sql_contract = plan["sql_contract"]
        self.assertEqual(1, sql_contract["query_count"])
        self.assertTrue(sql_contract["join_authorized"])
        self.assertEqual(["share_link"], sql_contract["http_derived_fields_excluded"])
        self.assertFalse(sql_contract["production_source_added"])
        manifest = sql_contract["manifest"]
        self.assertFalse(manifest["sequential_execution_required"])
        query = manifest["queries"][0]
        self.assertEqual("personal-bank-all-shares", query["query_id"])
        self.assertEqual(["viewer_id"], query["parameter_order"])
        self.assertEqual({"viewer_id": "bigint"}, query["parameters"])
        normalized = " ".join(query["sql"].split()).lower()
        self.assertEqual(
            "select bs.id, bs.bank_id, bs.owner_id, bs.share_code, bs.share_token, "
            "bs.permission, bs.expires_at, bs.max_uses, bs.current_uses, bs.is_active, "
            "bs.created_at, b.name as bank_name from bank_shares bs "
            "join user_question_banks b on bs.bank_id = b.id "
            "where bs.owner_id = :viewer_id and b.status = 1 "
            "order by bs.created_at desc nulls first",
            normalized,
        )
        self.assertNotIn("share_link", normalized)
        self.assertNotIn("bs.is_active =", normalized)
        self.assertNotIn(" limit ", normalized)

        cross = plan["cross_version_contract"]
        self.assertEqual(["16.14", "18.4"], cross["observed_versions"])
        self.assertTrue(cross["single_query_observed_per_version"])
        self.assertFalse(cross["ordered_result_payload_equality_required"])
        self.assertTrue(cross["unordered_result_multisets_identical"])
        self.assertTrue(cross["seq_scan_join_and_sort_without_index"])
        self.assertTrue(cross["desc_nulls_first_verified"])
        self.assertFalse(cross["equal_timestamp_order_strengthened"])
        self.assertFalse(cross["http_derived_share_link_in_sql"])
        self.assertTrue(cross["passed"])
        self.assertEqual(
            {
                "max_parallel_workers_per_gather": "0",
                "jit": "off",
                "work_mem": "64MB",
            },
            plan["plan_capture_environment"]["session_settings"],
        )
        self.assertTrue(plan["plan_capture_environment"]["same_settings_for_all_engines"])

    def test_05_expected_internal_shape_is_exact_and_not_yet_implemented(self):
        shape = self.contract["expected_application_shape"]
        self.assertEqual(
            "io.saksk.ti.personalbank.api.PersonalBankApplicationApi",
            shape["public_api"],
        )
        self.assertEqual("listOwnedShares", shape["method_name"])
        self.assertEqual(
            "java.util.List<io.saksk.ti.personalbank.api.PersonalBankOwnedShareView>",
            shape["generic_return_type"],
        )
        self.assertEqual(
            ["io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer"],
            shape["parameter_types"],
        )
        self.assertEqual(EXPECTED_COMPONENTS, shape["record_components"])
        self.assertEqual("List.copyOf", shape["collection_immutability"])
        self.assertEqual("absent", shape["share_link"])

        implementation = self.contract["implementation_state"]
        self.assertFalse(implementation["implementation_started"])
        self.assertFalse(implementation["production_source_added"])
        successor_main_files = self.successor["implementation"]["main_source_files"]
        successor_main_hashes = self.successor["implementation"]["main_source_sha256"]
        for relative in implementation["future_main_source_files"]:
            path = TI_JAVA_ROOT / relative
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

        main_root = TI_JAVA_ROOT / "server/src/main/java/io/saksk/ti/personalbank"
        actual = {
            path.relative_to(TI_JAVA_ROOT).as_posix(): sha256(path)
            for path in sorted(main_root.rglob("*.java"))
        }
        self.assertNotEqual(
            self.contract["unchanged_state"]["personalbank_main_source_manifest"], actual
        )
        if self.read_successor is None:
            self.assertEqual(
                self.terminal["implementation"]["personalbank_main_source_manifest"],
                actual,
            )
        else:
            current_manifest = learning_and_personalbank_main_source_manifest()
            self.assertEqual(40, len(current_manifest))
            self.assertEqual(
                self.read_successor["implementation"]
                ["learning_and_personalbank_main_source_manifest"],
                current_manifest,
            )
        application_api = (
            TI_JAVA_ROOT
            / "server/src/main/java/io/saksk/ti/personalbank/api/"
            "PersonalBankApplicationApi.java"
        ).read_text(encoding="utf-8")
        self.assertIn("listOwnedShares", application_api)

    def test_06_scope_denials_and_entry_decision_fail_closed(self):
        frozen = self.contract["frozen_internal_contract"]
        self.assertEqual(SELECTED_FIELDS, frozen["selected_fields"])
        self.assertEqual(12, frozen["selected_field_count"])
        self.assertEqual("read-only", frozen["transaction"])
        self.assertEqual(1, frozen["query_count"])
        self.assertEqual("bigint", frozen["input"]["viewer_id"]["jdbc_bind_type"])
        self.assertFalse(frozen["java_secondary_sorting_authorized"])
        self.assertFalse(frozen["share_link_synthesis_authorized"])
        self.assertFalse(frozen["extra_filters_authorized"])
        self.assertFalse(frozen["pagination_authorized"])
        self.assertFalse(frozen["schema_or_index_delta_authorized"])

        forbidden = self.contract["forbidden_scope"]
        self.assertFalse(forbidden["controller_added"])
        self.assertFalse(forbidden["security_matcher_added"])
        self.assertFalse(forbidden["route_or_openapi_delta_added"])
        self.assertFalse(forbidden["schema_or_index_added"])
        self.assertFalse(forbidden["share_link_in_persistence_added"])
        self.assertFalse(forbidden["write_statistics_or_page_restore_added"])
        self.assertFalse(forbidden["production_cutover"])

        gate = self.contract["entry_gate"]
        self.assertEqual(
            {
                "complete_caller_attestation",
                "capture_single_query_auth_data_link_and_failure_boundaries",
                "verify_postgresql_16_14_and_18_4_jdbc_and_query_plans",
                "freeze_http_derived_share_link_boundary",
                "freeze_null_and_equal_timestamp_ordering",
            },
            set(gate["completed_prerequisites"]),
        )
        self.assertTrue(gate["all_evidence_hashes_bound"])
        self.assertTrue(gate["preimplementation_boundary_verified"])
        self.assertTrue(gate["implementation_authorized"])
        self.assertFalse(gate["http_migration_authorized"])
        self.assertFalse(gate["production_cutover_authorized"])


if __name__ == "__main__":
    unittest.main()
