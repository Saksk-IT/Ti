#!/usr/bin/env python3
"""Fail-closed parity checks for the Phase 4C HTTP implementation contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

try:
    from tools import (
        build_phase4c_personal_bank_user_counts_http_implementation_contract
        as builder,
    )
    from tools import phase4c_http_implementation_successor_acceptance as acceptance
except ModuleNotFoundError:  # Direct execution from tools/.
    import build_phase4c_personal_bank_user_counts_http_implementation_contract as builder
    import phase4c_http_implementation_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / acceptance.CONTRACT_RELATIVE


class Phase4cHttpImplementationMissingEvidenceTest(unittest.TestCase):

    def test_builder_fails_closed_when_the_required_future_worm_is_missing(self) -> None:
        missing = (
            "docs/refactor/phase4c/"
            "deliberately-missing-http-implementation-worm-evidence.json"
        )
        with mock.patch.object(builder, "WORM_RELATIVE", missing):
            with self.assertRaisesRegex(FileNotFoundError, "required Phase4C HTTP"):
                builder.validate_worm("0" * 64)


class Phase4cHttpImplementationPendingCheckpointShapeTest(unittest.TestCase):

    def test_fixed_maps_and_pending_route_semantics_match_the_successor(self) -> None:
        self.assertEqual(44, len(builder.SOURCE_PATHS))
        self.assertEqual(builder.SOURCE_PATHS, acceptance.SOURCE_PATHS)
        self.assertEqual(14, len(builder.HTTP_ENTRY_SOURCE_ACCEPTED_SHA256))
        self.assertEqual(
            builder.HTTP_ENTRY_SOURCE_ACCEPTED_SHA256,
            acceptance.HTTP_ENTRY_SOURCE_ACCEPTED_SHA256,
        )
        self.assertEqual(1, len(builder.READ_TERMINAL_SOURCE_ACCEPTED_SHA256))
        self.assertEqual(
            builder.READ_TERMINAL_SOURCE_ACCEPTED_SHA256,
            acceptance.READ_TERMINAL_SOURCE_ACCEPTED_SHA256,
        )
        self.assertEqual(
            "implementation_present_parity_incomplete_routes_pending",
            builder.CONTRACT_STATUS,
        )
        self.assertTrue(all(
            route["migration_status"] == "pending"
            and route["production_cutover"] is False
            for route in builder.ROUTES
        ))


class Phase4cPersonalBankUserCountsHttpImplementationContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = acceptance.load_http_implementation_successor_contract(ROOT)
        if cls.contract is None:
            raise AssertionError("Phase4C HTTP implementation contract is required")
        cls.predecessor = json.loads(
            (ROOT / builder.PREDECESSOR_RELATIVE).read_text(encoding="utf-8")
        )

    def test_01_identity_predecessor_payload_trust_and_determinism_close(self) -> None:
        contract = self.contract
        self.assertEqual(acceptance.CONTRACT_ID, contract["contract_id"])
        self.assertEqual(acceptance.CONTRACT_STATUS, contract["status"])
        self.assertEqual(acceptance.CONTRACT_SCOPE, contract["scope"])
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            builder.PREDECESSOR_SHA256,
            builder.sha256(ROOT / builder.PREDECESSOR_RELATIVE),
        )
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            builder.document_payload_sha256(self.predecessor),
        )
        self.assertEqual(
            contract["document_payload_sha256"],
            builder.document_payload_sha256(contract),
        )
        self.assertEqual(
            acceptance.TRUST_PAYLOAD_SHA256,
            builder.trust_payload_sha256(contract),
        )

        with tempfile.TemporaryDirectory(prefix="ti-phase4c-http-implementation-") as tmp:
            generated = Path(tmp) / "contract.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / (
                        "tools/build_phase4c_personal_bank_user_counts_"
                        "http_implementation_contract.py"
                    )),
                    "--output",
                    str(generated),
                ],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(CONTRACT_PATH.read_bytes(), generated.read_bytes())

    def test_02_runtime_delta_is_exact_and_deletion_free(self) -> None:
        transition = self.contract["implementation"][
            "production_runtime_transition"
        ]
        self.assertEqual(
            {
                "file_count": 288,
                "manifest_sha256": builder.EXPECTED_PREDECESSOR_RUNTIME_MANIFEST_SHA256,
            },
            transition["predecessor"],
        )
        current = transition["current"]
        self.assertEqual(297, current["file_count"])
        self.assertEqual(
            builder.read_builder.production_runtime_manifest(),
            current["files"],
        )
        self.assertEqual(
            builder.sha256_json(current["files"]), current["manifest_sha256"]
        )

        delta = transition["exact_delta"]
        self.assertEqual(
            set(builder.EXPECTED_ADDED_RUNTIME_PATHS), set(delta["added_files"])
        )
        self.assertEqual(
            set(builder.EXPECTED_CHANGED_RUNTIME_PATHS), set(delta["changed_files"])
        )
        self.assertEqual(9, delta["added_file_count"])
        self.assertEqual(8, delta["new_main_source_count"])
        self.assertEqual(1, delta["new_openapi_file_count"])
        self.assertEqual(6, delta["changed_file_count"])
        self.assertEqual(2, delta["changed_main_source_count"])
        self.assertEqual(4, delta["changed_configuration_file_count"])
        self.assertEqual([], delta["deleted_files"])
        self.assertEqual(0, delta["deleted_file_count"])

    def test_03_module_api_and_forbidden_main_surfaces_remain_unchanged(self) -> None:
        transition = self.contract["implementation"][
            "production_runtime_transition"
        ]
        modules = transition["learning_and_personalbank"]
        self.assertEqual(40, modules["file_count"])
        self.assertEqual(builder.EXPECTED_MAIN_MANIFEST_SHA256, modules[
            "manifest_sha256"])
        self.assertEqual(builder.read_builder.main_source_manifest(), modules["files"])
        self.assertTrue(modules["unchanged_from_read_predecessor"])

        api = transition["public_application_api"]
        self.assertEqual(27, api["method_count"])
        self.assertEqual(builder.EXPECTED_PUBLIC_APPLICATION_METHODS_SHA256, api[
            "methods_sha256"])
        self.assertEqual(builder.read_builder.public_application_methods(), api["methods"])
        self.assertTrue(api["unchanged_from_http_entry_predecessor"])

        forbidden = transition["forbidden_main_sources"]
        self.assertTrue(forbidden["unchanged"])
        self.assertEqual(
            set(builder.EXPECTED_FORBIDDEN_UNCHANGED_MAIN_PATHS),
            set(forbidden["files"]),
        )

    def test_04_two_implemented_get_routes_remain_in_11_600_0(self) -> None:
        route = self.contract["implementation"]["routes_and_openapi"]
        self.assertEqual(2, route["implemented_pending_get_count"])
        self.assertEqual(11, route["migrated_operation_count"])
        self.assertEqual(600, route["pending_operation_count"])
        self.assertEqual(0, route["production_cutover_operation_count"])
        self.assertFalse(route["route_migration_eligible"])
        self.assertEqual(["GET"], route["counted_methods"])
        self.assertEqual(["HEAD", "OPTIONS"], route["derived_methods"])
        self.assertEqual(
            {"6858f6fa506f", "006913d0d956"},
            {item["route_id"] for item in route["routes"]},
        )
        self.assertTrue(all(
            item["method"] == "GET"
            and item["target_module"] == "learning"
            and item["migration_status"] == "pending"
            and not item["production_cutover"]
            for item in route["routes"]
        ))

    def test_05_new_rate_limit_namespace_has_one_learning_owner(self) -> None:
        ownership = self.contract["data_ownership"]
        self.assertEqual(159, ownership["predecessor"]["resource_count"])
        self.assertTrue(ownership["predecessor"]["immutable"])
        self.assertEqual(1, ownership["delta"]["new_resource_count"])
        effective = ownership["effective"]
        self.assertEqual(160, effective["resource_count"])
        self.assertEqual(160, effective["resources_with_exactly_one_owner"])
        self.assertTrue(self.contract["acceptance"][
            "new_rate_limit_resource_has_one_learning_owner"
        ])
        self.assertEqual(160, self.contract["acceptance"][
            "effective_resource_count"
        ])
        self.assertEqual(
            builder.OWNERSHIP_EFFECTIVE_MANIFEST_SHA256,
            effective["canonical_owner_manifest_sha256"],
        )
        self.assertTrue(effective["canonical_owner_manifest_recomputed"])
        predecessor = json.loads(
            (ROOT / builder.OWNERSHIP_PREDECESSOR_RELATIVE).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            builder.OWNERSHIP_EFFECTIVE_MANIFEST_SHA256,
            builder.sha256_json(
                builder.recompute_effective_owner_manifest(predecessor)
            ),
        )
        self.assertEqual([{
            "resource_kind": "redis_key",
            "resource_name": builder.OWNERSHIP_RESOURCE_NAME,
            "owner": "learning",
            "persistence_role": "runtime_rate_limit",
            "business_fact": False,
            "production_cutover": False,
        }], effective["new_resources"])
        self.assertEqual(
            effective["document_payload_sha256"],
            builder.document_payload_sha256(json.loads(
                (ROOT / builder.OWNERSHIP_EFFECTIVE_RELATIVE).read_text(
                    encoding="utf-8"
                )
            )),
        )

    def test_06_network_postgres_redis_and_partial_59_case_ledger_are_bound(self) -> None:
        evidence = self.contract["verification_evidence"]
        network = evidence["real_network_tomcat"]
        self.assertEqual(
            "random-port Tomcat with java.net.http.HttpClient", network["transport"]
        )
        self.assertFalse(network["mock_mvc"])
        postgres = evidence["postgresql_16_14_and_18_4"]
        self.assertEqual(["16.14", "18.4"], postgres["versions"])
        self.assertTrue(postgres["http_sql_fingerprint_parity"])
        self.assertTrue(postgres["read_only"])
        redis = evidence["redis_7"]
        self.assertTrue(redis["real_lua"])
        self.assertTrue(redis["atomic_concurrency_and_ttl"])
        self.assertTrue(redis["alias_isolation"])

        golden = evidence["phase4b_59_case_mapping"]
        self.assertEqual("PARTIAL_EXECUTION_MAPPING_LEDGER", golden[
            "claim_classification"])
        self.assertFalse(golden["full_target_parity_closed"])
        self.assertFalse(golden["cutover_evidence"])
        self.assertFalse(golden["route_migration_eligible"])
        self.assertEqual(59, golden["case_count"])
        self.assertEqual(48, golden["mockmvc_case_count"])
        self.assertEqual(11, golden["bound_only_case_count"])
        self.assertEqual("P4C-LEARNING-006", golden["inherited_difference_id"])
        self.assertEqual(
            [
                "access-shared-fetchone-first-row",
                "access-shared-cross-bank-record",
            ],
            golden["inherited_case_ids"],
        )
        self.assertEqual(
            [f"P4C-LEARNING-{index:03d}" for index in range(7, 13)],
            golden["http_difference_ids"],
        )

        source = json.loads(
            (ROOT / builder.GOLDEN_TARGET_RELATIVE).read_text(encoding="utf-8")
        )
        goldens = json.loads(
            (ROOT / builder.GOLDEN_RELATIVE).read_text(encoding="utf-8")
        )
        self.assertEqual(
            [item["case_id"] for item in goldens["cases"]],
            [item["case_id"] for item in source["cases"]],
        )
        for item in source["cases"]:
            self.assertEqual(
                len(item["http_slice_difference_ids"]),
                len(set(item["http_slice_difference_ids"])),
            )
            self.assertLessEqual(
                set(item["http_slice_difference_ids"]),
                set(golden["http_difference_ids"]),
            )
            if "inherited_predecessor_difference_id" in item:
                self.assertEqual(
                    "P4C-LEARNING-006",
                    item["inherited_predecessor_difference_id"],
                )
            self.assertNotIn("P4C-LEARNING-006", item[
                "http_slice_difference_ids"])

        adapter = evidence["http_adapter_security"]
        self.assertTrue(adapter["mock_mvc"])
        self.assertFalse(adapter["full_authentication_filter_chain"])
        self.assertEqual(
            [
                "TargetSessionAuthenticationFilter",
                "TargetSessionReconciliationFilter",
            ],
            adapter["excluded_filters"],
        )

    def test_07_worm_and_authorization_do_not_claim_schema_migration_or_cutover(self) -> None:
        worm = self.contract["worm_evidence"]
        self.assertEqual(builder.WORM_RELATIVE, worm["source"])
        self.assertEqual(builder.sha256(ROOT / worm["source"]), worm["sha256"])
        self.assertEqual(
            self.contract["implementation"]["java_build_context_sha256"],
            worm["java_build_context_sha256"],
        )
        self.assertTrue(worm["read_role_closed"])
        self.assertEqual("validate", worm["hibernate_schema_mode"])
        fixed_chain = worm["fixed_phase2_chain"]
        self.assertEqual(5, fixed_chain["node_count"])
        self.assertEqual(worm["sha256"], fixed_chain["tip_sha256"])
        self.assertEqual(
            builder.phase2_worm.PHASE4C_READ_ACCESS_REPORT_SHA256,
            fixed_chain["predecessor_sha256"],
        )
        for field in (
            "production_schema_or_index_changed",
            "operator_migration_executed",
            "real_data_migration_executed",
            "production_cutover",
        ):
            self.assertFalse(worm[field], field)

        authorization = self.contract["authorization"]
        self.assertTrue(authorization["implementation_present"])
        self.assertNotIn("http_implementation_complete", authorization)
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
            self.assertFalse(authorization[field], field)

        acceptance_checkpoint = self.contract["acceptance"]
        self.assertTrue(acceptance_checkpoint["implementation_present"])
        self.assertFalse(acceptance_checkpoint["full_target_parity_closed"])
        self.assertFalse(acceptance_checkpoint["route_migration_eligible"])
        self.assertEqual(2, acceptance_checkpoint["implemented_pending_get_count"])
        self.assertEqual(11, acceptance_checkpoint["migrated_operation_count"])
        self.assertEqual(600, acceptance_checkpoint["pending_operation_count"])
        self.assertEqual(
            "close_59_case_target_execution_and_full_authentication_chain_"
            "before_route_migration",
            acceptance_checkpoint["next_gate"],
        )

    def test_08_successor_allowlist_is_fixed_and_bridge_cannot_self_authorize(self) -> None:
        history = self.contract["historical_successor_acceptance"]
        overrides = history["http_entry_source_overrides"]
        self.assertEqual(set(acceptance.HTTP_ENTRY_SOURCE_ACCEPTED_SHA256), set(overrides))
        self.assertNotIn(
            "tools/phase4c_http_implementation_successor_acceptance.py", overrides
        )
        self.assertNotIn(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpImplementationSuccessorAcceptance.java",
            overrides,
        )
        for relative, accepted in acceptance.HTTP_ENTRY_SOURCE_ACCEPTED_SHA256.items():
            self.assertEqual(accepted, overrides[relative]["accepted_sha256"])
            self.assertEqual(relative, overrides[relative]["source"])
            self.assertEqual(
                builder.sha256(ROOT / relative), overrides[relative]["successor_sha256"]
            )

        injected = copy.deepcopy(self.contract)
        injected["source_contracts"]["unreviewed"] = {
            "source": "tools/unreviewed.py",
            "sha256": "0" * 64,
        }
        injected["document_payload_sha256"] = builder.document_payload_sha256(injected)
        with self.assertRaisesRegex(AssertionError, "source contract set"):
            acceptance.validate_http_implementation_successor_contract(injected, ROOT)

        overclaim = copy.deepcopy(self.contract)
        overclaim["authorization"]["production_cutover"] = True
        overclaim["document_payload_sha256"] = builder.document_payload_sha256(overclaim)
        with self.assertRaisesRegex(AssertionError, "overclaims authorization"):
            acceptance.validate_http_implementation_successor_contract(overclaim, ROOT)


if __name__ == "__main__":
    unittest.main()
