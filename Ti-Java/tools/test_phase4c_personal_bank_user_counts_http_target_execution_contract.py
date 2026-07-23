#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C target-execution successor contract."""

from __future__ import annotations

from collections import Counter
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
        build_phase4c_personal_bank_user_counts_http_target_execution_contract
        as builder,
    )
    from tools import phase4c_http_target_execution_successor_acceptance as acceptance
except ModuleNotFoundError:  # Direct execution from tools/.
    import build_phase4c_personal_bank_user_counts_http_target_execution_contract as builder
    import phase4c_http_target_execution_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / acceptance.CONTRACT_RELATIVE
EVIDENCE_PATH = ROOT / builder.TARGET_EVIDENCE_RELATIVE
GOLDEN_PATH = ROOT / builder.GOLDEN_RELATIVE
MAPPING_PATH = ROOT / builder.PARTIAL_MAPPING_RELATIVE
TAG_PREFLIGHT_CURRENT_WORM_SHA256 = (
    "5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c"
)

REMOVED_UNUSED_SEED_SOURCE_KEYS = {
    "share_list_seed",
    "all_shares_seed",
    "usage_stats_seed",
    "user_counts_seed",
}
REQUIRED_ADDITIONAL_SOURCE_PATHS = {
    "phase2_minimal_reference_schema": (
        "server/src/test/resources/db/phase2/minimal-reference-schema.sql"
    ),
    "phase2_readonly_role": (
        "server/src/test/resources/db/phase2/020-test-readonly-role.sql"
    ),
    "server_pom": "server/pom.xml",
    "application_test_configuration": "server/src/main/resources/application-test.yml",
    "approved_differences": "docs/refactor/phase4c/approved-differences.md",
}
EXPECTED_SOURCE_KEYS = {
    "predecessor",
    "phase4c_read_predecessor",
    "phase4b_all_shares_entry_anchor",
    "phase4b_goldens",
    "historical_partial_mapping",
    "target_execution_evidence",
    "target_execution_it",
    "fault_injecting_data_source",
    "target_execution_seed",
    "phase3_authentication_it",
    "auth_schema",
    "share_list_schema",
    "usage_stats_schema",
    "user_counts_schema",
    "phase2_minimal_reference_schema",
    "phase2_readonly_role",
    "container_images",
    "postgres_containers",
    "network_it",
    "postgres_it",
    "redis_it",
    "server_pom",
    "application_test_configuration",
    "approved_differences",
    "openapi_overlay",
    "route_delta",
    "ownership_effective",
    "worm_tip",
    "phase2_build_context_hasher",
    "read_contract_builder",
    "contract_builder",
    "contract_test",
    "python_successor_bridge",
    "java_successor_bridge",
    "java_contract_parity_test",
    "project_readme",
    "progress",
    "phase4c_readme",
    "phase2_readme",
    "phase2_static_gate",
    "phase2_worm_validator",
    "phase2_worm_validator_test",
    "historical_python_implementation_successor_bridge",
    "historical_implementation_contract_test",
    "historical_java_implementation_successor_bridge",
    "historical_python_read_successor_bridge",
    "historical_java_read_successor_bridge",
    "historical_all_shares_entry_contract_test",
    "historical_share_list_read_contract_test",
    "historical_composition_contract_test",
    "historical_read_contract_test",
}


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise AssertionError(f"JSON source is not an object: {path}")
    return document


def validate_worm_successor(*args, **kwargs):
    try:
        from tools.phase4c_tag_migration_global_preflight_successor_acceptance import (
            validate_worm_successor as validate_successor,
        )
    except ModuleNotFoundError as error:  # Direct execution from tools/.
        if error.name not in {
            "tools",
            "tools.phase4c_tag_migration_global_preflight_successor_acceptance",
        }:
            raise
        from phase4c_tag_migration_global_preflight_successor_acceptance import (
            validate_worm_successor as validate_successor,
        )
    return validate_successor(*args, **kwargs)


def target_fault_occurrence(case_id: str) -> int:
    if "share-access" in case_id or "total" in case_id:
        return 1
    if "favorites" in case_id or "source-favorites" in case_id:
        return 2
    if "mistakes" in case_id:
        return 3
    if "types" in case_id:
        return 4
    raise AssertionError(f"unclassified target fault case: {case_id}")


class Phase4cTargetExecutionFixedRootsTest(unittest.TestCase):

    def test_01_builder_and_bootstrap_acceptance_constants_match(self) -> None:
        for name in (
            "CONTRACT_ID",
            "CONTRACT_STATUS",
            "CONTRACT_SCOPE",
            "PREDECESSOR_RELATIVE",
            "PREDECESSOR_ID",
            "PREDECESSOR_STATUS",
            "PREDECESSOR_SCOPE",
            "PREDECESSOR_SHA256",
            "PREDECESSOR_PAYLOAD_SHA256",
            "PREDECESSOR_TRUST_PAYLOAD_SHA256",
            "SOURCE_CHECKPOINT_COMMIT",
            "SOURCE_CHECKPOINT_COMMITTED_AT",
            "SOURCE_CHECKPOINT_SUBJECT",
            "BRIDGE_PROVENANCE_SENTINEL",
            "BRIDGE_SOURCE_KEYS",
            "NEXT_GATE",
        ):
            self.assertEqual(getattr(builder, name), getattr(acceptance, name), name)
        self.assertEqual(builder.CAPTURED_AT, acceptance.CONTRACT_CAPTURED_AT)
        self.assertEqual(
            builder.TARGET_EVIDENCE_RELATIVE,
            acceptance.TARGET_EXECUTION_EVIDENCE_RELATIVE,
        )
        self.assertEqual(
            builder.TARGET_EVIDENCE_SHA256,
            acceptance.TARGET_EXECUTION_EVIDENCE_SHA256,
        )
        self.assertEqual(
            builder.TARGET_EVIDENCE_CASE_PAYLOAD_SHA256,
            acceptance.TARGET_EXECUTION_CASE_PAYLOAD_SHA256,
        )
        self.assertEqual(
            builder.TARGET_EVIDENCE_DOCUMENT_PAYLOAD_SHA256,
            acceptance.TARGET_EXECUTION_EVIDENCE_PAYLOAD_SHA256,
        )
        self.assertEqual(builder.WORM_SHA256, acceptance.WORM_SHA256)
        self.assertEqual(
            builder.JAVA_BUILD_CONTEXT_SHA256,
            acceptance.JAVA_BUILD_CONTEXT_SHA256,
        )
        self.assertEqual(
            builder.EXPECTED_RUNTIME_FILE_COUNT,
            acceptance.PRODUCTION_FILE_COUNT,
        )
        self.assertEqual(
            builder.EXPECTED_RUNTIME_MANIFEST_SHA256,
            acceptance.PRODUCTION_MANIFEST_SHA256,
        )

    def test_02_source_paths_are_exact_and_follow_real_container_inputs(self) -> None:
        self.assertEqual(EXPECTED_SOURCE_KEYS, set(builder.SOURCE_PATHS))
        self.assertEqual(builder.SOURCE_PATHS, acceptance.SOURCE_PATHS)
        self.assertTrue(
            REMOVED_UNUSED_SEED_SOURCE_KEYS.isdisjoint(builder.SOURCE_PATHS)
        )
        for name, relative in REQUIRED_ADDITIONAL_SOURCE_PATHS.items():
            self.assertEqual(relative, builder.SOURCE_PATHS.get(name), name)
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertEqual(
            builder.SOURCE_PATHS["target_execution_seed"],
            "server/src/test/resources/db/phase4c/"
            "071-personal-bank-user-counts-golden-target-seed.sql",
        )

    def test_03_historical_allowlist_is_exact_and_predecessor_anchored(self) -> None:
        expected_paths = set(acceptance.HISTORICAL_SOURCE_ACCEPTED_SHA256)
        self.assertEqual(18, len(expected_paths))
        self.assertEqual(expected_paths, set(builder.HISTORICAL_SUCCESSOR_ALLOWLIST))

        predecessor = builder.validate_predecessor()
        history = builder.validate_historical_successor_acceptance(predecessor)
        self.assertEqual(
            sorted(expected_paths),
            history["successor_allowlist"],
        )
        self.assertEqual(
            expected_paths,
            set(history["anchored_source_overrides"]),
        )
        for relative, accepted in acceptance.HISTORICAL_SOURCE_ACCEPTED_SHA256.items():
            reference = history["anchored_source_overrides"][relative]
            self.assertEqual(accepted, reference["accepted_sha256"], relative)
            self.assertEqual(
                acceptance.HISTORICAL_SOURCE_ACCEPTED_PROVENANCE[relative],
                reference["accepted_hash_provenance"],
                relative,
            )
        for field in (
            "successor_allowlist_exact",
            "accepted_hashes_independently_located",
            "predecessor_rewrite_forbidden",
            "arbitrary_source_hash_lookup_forbidden",
            "current_bridges_excluded_from_historical_accepted_hash_allowlist",
        ):
            self.assertIs(history[field], True, field)

    def test_04_predecessor_physical_payload_and_trust_roots_are_fixed(self) -> None:
        predecessor_path = ROOT / builder.PREDECESSOR_RELATIVE
        predecessor = read_json(predecessor_path)
        self.assertEqual(builder.PREDECESSOR_SHA256, builder.sha256(predecessor_path))
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            predecessor["document_payload_sha256"],
        )
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            builder.document_payload_sha256(predecessor),
        )
        self.assertEqual(
            builder.PREDECESSOR_TRUST_PAYLOAD_SHA256,
            builder.trust_payload_sha256(predecessor),
        )
        self.assertEqual(
            builder.PREDECESSOR_TRUST_PAYLOAD_SHA256,
            acceptance._bridge_normalized_payload_sha256(predecessor),
        )

    def test_05_physical_runtime_routes_ownership_and_worm_close(self) -> None:
        predecessor = builder.validate_predecessor()
        runtime = builder.validate_production_surface(predecessor)
        self.assertEqual(297, runtime["file_count"])
        self.assertEqual(builder.EXPECTED_RUNTIME_MANIFEST_SHA256, runtime[
            "manifest_sha256"])
        self.assertEqual(297, len(runtime["files"]))
        self.assertTrue(runtime["unchanged_from_predecessor"])

        routes = builder.validate_routes_and_openapi(predecessor)
        self.assertEqual(11, routes["migrated_operation_count"])
        self.assertEqual(600, routes["pending_operation_count"])
        self.assertEqual(0, routes["production_cutover_operation_count"])
        self.assertFalse(routes["route_migration_eligible"])
        self.assertTrue(all(
            route["method"] == "GET"
            and route["migration_status"] == "pending"
            and route["production_cutover"] is False
            for route in routes["routes"]
        ))

        ownership = builder.validate_data_ownership()
        self.assertEqual(160, ownership["resource_count"])
        self.assertEqual(160, ownership["resources_with_exactly_one_owner"])
        worm = builder.validate_worm()
        self.assertEqual(builder.WORM_SHA256, worm["sha256"])
        self.assertEqual(builder.JAVA_BUILD_CONTEXT_SHA256, worm[
            "java_build_context_sha256"])
        self.assertFalse(worm["new_worm"])
        physical_build_context = builder.java_build_context_sha256()
        if physical_build_context == builder.JAVA_BUILD_CONTEXT_SHA256:
            self.assertEqual(
                builder.JAVA_BUILD_CONTEXT_SHA256,
                physical_build_context,
            )
        else:
            successor = validate_worm_successor(
                ROOT,
                builder.WORM_SHA256,
                builder.JAVA_BUILD_CONTEXT_SHA256,
            )
            self.assertEqual(builder.WORM_SHA256, successor.accepted_report_sha256)
            self.assertEqual(
                builder.JAVA_BUILD_CONTEXT_SHA256,
                successor.accepted_build_context_sha256,
            )
            self.assertEqual(5, successor.accepted_chain_node_count)
            self.assertEqual(
                TAG_PREFLIGHT_CURRENT_WORM_SHA256,
                successor.current_report_sha256,
            )
            self.assertEqual(
                physical_build_context,
                successor.current_build_context_sha256,
            )
            self.assertEqual(9, successor.current_chain_node_count)
        fixed_chain = predecessor["worm_evidence"]["fixed_phase2_chain"]
        self.assertEqual(5, fixed_chain["node_count"])
        self.assertEqual(builder.WORM_SHA256, fixed_chain["tip_sha256"])

    def test_06_unknown_successor_paths_never_receive_hash_authority(self) -> None:
        unknown = "tools/not-reviewed-target-execution-successor.py"
        self.assertNotIn(unknown, builder.HISTORICAL_SUCCESSOR_ALLOWLIST)
        self.assertIsNone(acceptance.accepted_sha256(unknown))
        self.assertIsNone(acceptance.successor_sha256(ROOT, unknown))
        self.assertIsNone(acceptance.accepted_sha256("../outside-Ti-Java"))
        self.assertIsNone(acceptance.successor_sha256(ROOT, "../outside-Ti-Java"))
        for relative in (
            builder.SOURCE_PATHS["phase3_authentication_it"],
            builder.SOURCE_PATHS["historical_all_shares_entry_contract_test"],
            builder.SOURCE_PATHS["historical_share_list_read_contract_test"],
        ):
            self.assertEqual(
                builder.sha256(ROOT / relative),
                acceptance.fixed_source_sha256(ROOT, relative),
            )
        self.assertIsNone(acceptance.fixed_source_sha256(ROOT, unknown))
        for bridge_key in builder.BRIDGE_SOURCE_KEYS:
            relative = builder.SOURCE_PATHS[bridge_key]
            self.assertIsNone(acceptance.accepted_sha256(relative))
            self.assertIsNone(acceptance.successor_sha256(ROOT, relative))


class Phase4cTargetExecutionEvidenceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = read_json(EVIDENCE_PATH)
        cls.golden = read_json(GOLDEN_PATH)
        cls.mapping = read_json(MAPPING_PATH)
        cls.golden_cases = cls.golden["cases"]
        cls.mapping_cases = cls.mapping["cases"]
        cls.evidence_cases = cls.evidence["cases"]
        cls.mapping_by_id = {
            item["case_id"]: item for item in cls.mapping_cases
        }

    def test_01_all_59_cases_preserve_order_and_four_dispositions(self) -> None:
        golden_ids = [item["case_id"] for item in self.golden_cases]
        self.assertEqual(59, len(golden_ids))
        self.assertEqual(59, len(set(golden_ids)))
        self.assertEqual(
            golden_ids,
            [item["case_id"] for item in self.mapping_cases],
        )
        self.assertEqual(
            golden_ids,
            [item["case_id"] for item in self.evidence_cases],
        )
        self.assertEqual(
            builder.GOLDEN_ORDERED_CASE_IDS_SHA256,
            builder.sha256_json(golden_ids),
        )
        self.assertEqual(
            builder.TARGET_EVIDENCE_CASE_PAYLOAD_SHA256,
            builder.sha256_json(self.evidence_cases),
        )
        dispositions = Counter(
            item["execution_disposition"] for item in self.evidence_cases
        )
        self.assertEqual(builder.EXPECTED_DISPOSITION_COUNTS, dict(dispositions))
        execution_order = [
            item["case_id"] for item in self.evidence_cases
            if item["execution_disposition"] == "EXECUTED_FULL_CONTEXT_HTTP"
        ] + [
            item["case_id"] for item in self.evidence_cases
            if item["execution_disposition"]
            == "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT"
        ] + [builder.TYPED_REJECTION_CASE_ID, builder.TYPED_COLLAPSE_CASE_ID]
        execution_ordinal_by_id = {
            case_id: ordinal
            for ordinal, case_id in enumerate(execution_order, start=1)
        }
        self.assertEqual(59, len(execution_ordinal_by_id))
        for canonical_ordinal, item in enumerate(self.evidence_cases, start=1):
            execution_ordinal = execution_ordinal_by_id[item["case_id"]]
            self.assertEqual(canonical_ordinal, item["canonical_case_ordinal"])
            self.assertEqual(execution_ordinal, item["execution_ordinal"])
            self.assertEqual(
                execution_ordinal + 1,
                item["junit"]["disposition_leaf_ordinal"],
            )
        summary = self.evidence["summary"]
        self.assertEqual(
            builder.EXPECTED_DISPOSITION_COUNTS,
            summary["execution_disposition_counts"],
        )
        self.assertEqual(59, summary["case_count"])
        self.assertEqual(49, summary["business_jdbc_reached_http_count"])
        self.assertEqual(8, summary[
            "pre_business_jdbc_termination_http_count"])
        self.assertEqual({"302": 5, "401": 3}, summary[
            "pre_business_jdbc_termination_status_counts"])
        self.assertEqual(60, summary["junit_leaf_test_count"])
        self.assertEqual(59, 60 - summary["supplementary_junit_test_count"])

    def test_02_status_alias_and_mapping_differences_are_exact(self) -> None:
        statuses: Counter[str] = Counter()
        aliases: Counter[str] = Counter()
        compared_fields = (
            "http_slice_difference_ids",
            "inherited_predecessor_difference_id",
            "target_data_source_case",
            "tracking_note",
        )
        self.assertEqual(len(self.golden_cases), len(self.evidence_cases))
        for source_case, evidence_case in zip(
                self.golden_cases, self.evidence_cases):
            case_id = source_case["case_id"]
            mapping_case = self.mapping_by_id[case_id]
            expected_alias = (
                "api"
                if source_case["request"]["path"].startswith("/api/")
                else "web"
            )
            self.assertEqual(expected_alias, evidence_case["alias"], case_id)
            self.assertEqual(mapping_case.get("target_status"), evidence_case.get(
                "target_status"), case_id)
            for field in compared_fields:
                self.assertEqual(field in mapping_case, field in evidence_case, (
                    case_id, field, "presence"))
                if field in mapping_case:
                    self.assertEqual(
                        mapping_case[field], evidence_case[field], (case_id, field)
                    )
            if evidence_case["target_status"] is not None:
                statuses[str(evidence_case["target_status"])] += 1
                aliases[expected_alias] += 1
        self.assertEqual(builder.EXPECTED_HTTP_STATUS_COUNTS, dict(statuses))
        self.assertEqual(Counter({"api": 43, "web": 14}), aliases)

    def test_03_all_11_faults_bind_real_postgresql_abort_and_rollback(self) -> None:
        faults = [
            item for item in self.evidence_cases
            if item["execution_disposition"]
            == "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT"
        ]
        self.assertEqual(11, len(faults))
        for item in faults:
            case_id = item["case_id"]
            fault = item["fault_evidence"]
            occurrence = target_fault_occurrence(case_id)
            family = "SHARE_ACCESS" if "share-access" in case_id else (
                "QUESTION_SUMMARY")
            self.assertEqual(family, fault["family"], case_id)
            self.assertEqual(occurrence, fault["occurrence"], case_id)
            self.assertEqual("42703", fault["initial_sqlstate"], case_id)
            self.assertEqual("25P02", fault[
                "poisoned_transaction_sqlstate"], case_id)
            self.assertTrue(fault["fault_connection_read_only"], case_id)
            self.assertTrue(fault[
                "rollback_after_fault_on_same_connection"], case_id)
            self.assertTrue(fault[
                "failed_family_occurrence_has_no_success_record"], case_id)
            self.assertEqual(
                item["target_status"] == 200
                and family == "QUESTION_SUMMARY"
                and occurrence < 4,
                fault[
                    "later_same_family_success_after_rollback_on_different_"
                    "connection_required"
                ],
                case_id,
            )

    def test_04_two_typed_dispositions_are_non_http_and_fully_bound(self) -> None:
        by_id = {item["case_id"]: item for item in self.evidence_cases}
        rejection = by_id[builder.TYPED_REJECTION_CASE_ID]
        collapse = by_id[builder.TYPED_COLLAPSE_CASE_ID]
        self.assertEqual("EXECUTED_TYPED_REJECTION", rejection[
            "execution_disposition"])
        self.assertIs(rejection["http_execution"], False)
        self.assertIsNone(rejection["target_status"])
        self.assertEqual("22007", rejection["typed_evidence"]["sqlstate"])
        self.assertEqual(0, rejection["typed_evidence"][
            "persisted_bank_share_row_count"])
        self.assertTrue(rejection["typed_evidence"][
            "bank_shares_total_unchanged"])
        self.assertTrue(rejection["typed_evidence"][
            "bank_share_records_total_unchanged"])

        self.assertEqual("EXECUTED_TYPED_COLLAPSE", collapse[
            "execution_disposition"])
        self.assertIs(collapse["http_execution"], False)
        self.assertIsNone(collapse["target_status"])
        typed = collapse["typed_evidence"]
        self.assertTrue(typed["both_inputs_equal_after_projection"])
        self.assertTrue(typed["source_offset_provenance_erased"])
        self.assertTrue(typed["approved_null_expiry_is_sql_null"])
        self.assertTrue(typed["bank_shares_total_unchanged"])
        self.assertTrue(typed["bank_share_records_total_unchanged"])

    def test_05_source_checkpoint_artifact_hashes_are_physical(self) -> None:
        checkpoint = self.evidence["source_checkpoint"]
        self.assertEqual(builder.SOURCE_CHECKPOINT_COMMIT, checkpoint["commit"])
        self.assertEqual(
            builder.SOURCE_CHECKPOINT_COMMITTED_AT,
            checkpoint["committed_at"],
        )
        self.assertEqual(builder.SOURCE_CHECKPOINT_SUBJECT, checkpoint["subject"])
        artifacts = checkpoint["artifacts"]
        expected = {
            "target_execution_test": builder.SOURCE_PATHS["target_execution_it"],
            "fault_injecting_data_source": builder.SOURCE_PATHS[
                "fault_injecting_data_source"],
            "postgresql_seed": builder.SOURCE_PATHS["target_execution_seed"],
        }
        self.assertEqual(set(expected), set(artifacts))
        for name, relative in expected.items():
            self.assertEqual(relative, artifacts[name]["path"], name)
            self.assertEqual(
                builder.sha256(ROOT / relative), artifacts[name]["sha256"], name
            )

    def _assert_mutated_evidence_rejected(self, mutate) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutate(mutated)
        case_payload = builder.sha256_json(mutated["cases"])
        mutated["document_payload_sha256"] = builder.document_payload_sha256(mutated)
        original_load_json = builder.load_json

        def load_mutated(path: Path):
            if Path(path).resolve() == EVIDENCE_PATH.resolve():
                return copy.deepcopy(mutated)
            return original_load_json(path)

        with mock.patch.object(builder, "load_json", side_effect=load_mutated), \
                mock.patch.object(
                    builder,
                    "TARGET_EVIDENCE_CASE_PAYLOAD_SHA256",
                    case_payload,
                ), mock.patch.object(
                    builder,
                    "TARGET_EVIDENCE_DOCUMENT_PAYLOAD_SHA256",
                    mutated["document_payload_sha256"],
                ):
            with self.assertRaises(ValueError):
                builder.validate_target_execution_evidence()

    def test_06_case_omission_reorder_status_and_binding_mutations_are_rejected(self) -> None:
        mutations = {
            "case omission": lambda document: document["cases"].pop(),
            "case reorder": lambda document: document["cases"].__setitem__(
                slice(0, 2), list(reversed(document["cases"][:2]))
            ),
            "target status": lambda document: document["cases"][0].__setitem__(
                "target_status", 201
            ),
            "business JDBC reach": lambda document: document["cases"][0][
                "sql_boundary"].__setitem__("business_jdbc_reached", False),
            "business JDBC summary": lambda document: document["summary"].__setitem__(
                "business_jdbc_reached_http_count", 57
            ),
            "difference": lambda document: document["cases"][0][
                "http_slice_difference_ids"].append("P4C-UNREVIEWED"),
            "inherited difference": lambda document: next(
                item for item in document["cases"]
                if "inherited_predecessor_difference_id" in item
            ).__setitem__("inherited_predecessor_difference_id", "P4C-UNREVIEWED"),
            "target data source": lambda document: next(
                item for item in document["cases"]
                if "target_data_source_case" in item
            ).__setitem__("target_data_source_case", "unreviewed-source-case"),
            "tracking note": lambda document: next(
                item for item in document["cases"] if "tracking_note" in item
            ).__setitem__("tracking_note", "parity is complete"),
            "fault occurrence": lambda document: next(
                item for item in document["cases"] if "fault_evidence" in item
            )["fault_evidence"].__setitem__("occurrence", 99),
            "typed SQLSTATE": lambda document: next(
                item for item in document["cases"]
                if item["case_id"] == builder.TYPED_REJECTION_CASE_ID
            )["typed_evidence"].__setitem__("sqlstate", "00000"),
            "source checkpoint": lambda document: document["source_checkpoint"][
                "artifacts"]["target_execution_test"].__setitem__(
                    "sha256", "0" * 64
                ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self._assert_mutated_evidence_rejected(mutation)

    def test_07_evidence_parity_route_and_cutover_overclaims_are_rejected(self) -> None:
        mutations = {
            "full parity": lambda document: document["claim"].__setitem__(
                "full_target_parity_closed", True
            ),
            "route migration": lambda document: document["claim"].__setitem__(
                "route_migration_eligible", True
            ),
            "cutover": lambda document: document["claim"].__setitem__(
                "cutover_evidence", True
            ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self._assert_mutated_evidence_rejected(mutation)


class Phase4cTargetExecutionCheckedInContractTest(unittest.TestCase):

    def setUp(self) -> None:
        if not CONTRACT_PATH.is_file():
            self.fail("checked-in Phase4C target-execution contract is required")
        self.contract = read_json(CONTRACT_PATH)

    def test_01_checked_in_contract_is_accepted_and_byte_deterministic(self) -> None:
        acceptance.validate_http_target_execution_successor_contract(
            self.contract, ROOT
        )
        built = builder.build_contract()
        expected_bytes = (
            json.dumps(built, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        self.assertEqual(expected_bytes, CONTRACT_PATH.read_bytes())

        with tempfile.TemporaryDirectory(prefix="ti-phase4c-target-execution-") as tmp:
            generated = Path(tmp) / "contract.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / (
                        "tools/build_phase4c_personal_bank_user_counts_"
                        "http_target_execution_contract.py"
                    )),
                    "--output",
                    str(generated),
                ],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(CONTRACT_PATH.read_bytes(), generated.read_bytes())

    def test_02_contract_closes_counts_but_not_typed_parity_or_routes(self) -> None:
        acceptance_checkpoint = self.contract["acceptance"]
        self.assertTrue(acceptance_checkpoint[
            "all_59_target_dispositions_executed"])
        self.assertFalse(acceptance_checkpoint["typed_parity_review_complete"])
        self.assertEqual(59, acceptance_checkpoint["case_count"])
        self.assertEqual(57, acceptance_checkpoint["http_execution_count"])
        self.assertEqual(49, acceptance_checkpoint[
            "business_jdbc_reached_http_count"])
        self.assertEqual(8, acceptance_checkpoint[
            "pre_business_jdbc_termination_http_count"])
        self.assertEqual({"302": 5, "401": 3}, acceptance_checkpoint[
            "pre_business_jdbc_termination_status_counts"])
        self.assertEqual(2, acceptance_checkpoint[
            "typed_postgresql_disposition_count"])
        self.assertEqual(60, acceptance_checkpoint["junit_leaf_test_count"])
        self.assertEqual(11, acceptance_checkpoint["migrated_operation_count"])
        self.assertEqual(600, acceptance_checkpoint["pending_operation_count"])
        self.assertEqual(0, acceptance_checkpoint[
            "production_cutover_operation_count"])
        self.assertFalse(acceptance_checkpoint["full_target_parity_closed"])
        self.assertFalse(acceptance_checkpoint["route_migration_eligible"])
        self.assertFalse(acceptance_checkpoint[
            "external_bridge_bytes_anchor_complete"])
        self.assertTrue(acceptance_checkpoint[
            "post_push_external_git_anchor_required_before_route_migration"])
        self.assertFalse(acceptance_checkpoint["production_cutover"])

        bridge = self.contract["bridge_provenance"]
        self.assertEqual(
            "bootstrap_pending_post_push_external_git_anchor",
            bridge["state"],
        )
        self.assertEqual(sorted(builder.BRIDGE_SOURCE_KEYS), bridge[
            "normalized_source_keys"])
        self.assertFalse(bridge["external_bridge_bytes_anchor_complete"])
        self.assertTrue(bridge[
            "post_push_external_git_anchor_required_before_route_promotion"])

        ownership = self.contract["data_ownership"]
        ownership_counts = ownership.get("effective", ownership)
        self.assertEqual(160, ownership_counts["resource_count"])
        self.assertEqual(160, ownership_counts[
            "resources_with_exactly_one_owner"])
        worm = self.contract["worm_evidence"]
        self.assertEqual(builder.WORM_SHA256, worm["sha256"])
        self.assertEqual(builder.JAVA_BUILD_CONTEXT_SHA256, worm[
            "java_build_context_sha256"])
        self.assertFalse(worm["new_worm"])
        self.assertFalse(worm["new_worm_report_created"])
        self.assertTrue(worm["production_build_context_unchanged"])

    def test_03_bridge_hash_normalization_is_explicit_and_non_bridge_hashes_bind(
            self) -> None:
        original = builder.trust_payload_sha256(self.contract)
        bridge_mutation = copy.deepcopy(self.contract)
        bridge_mutation["source_contracts"][
            "python_successor_bridge"]["sha256"] = "0" * 64
        self.assertEqual(original, builder.trust_payload_sha256(bridge_mutation))

        non_bridge_mutation = copy.deepcopy(self.contract)
        non_bridge_mutation["source_contracts"]["route_delta"]["sha256"] = "0" * 64
        self.assertNotEqual(
            original,
            builder.trust_payload_sha256(non_bridge_mutation),
        )

    def _assert_contract_mutation_rejected(self, mutate) -> None:
        mutated = copy.deepcopy(self.contract)
        mutate(mutated)
        mutated["document_payload_sha256"] = builder.document_payload_sha256(mutated)
        with self.assertRaises(AssertionError):
            acceptance.validate_http_target_execution_successor_contract(mutated, ROOT)

    def test_04_unknown_sources_status_and_claim_overreach_are_rejected(self) -> None:
        mutations = {
            "unknown source": lambda contract: contract["source_contracts"].__setitem__(
                "unreviewed", {
                    "source": "tools/unreviewed.py",
                    "sha256": "0" * 64,
                }
            ),
            "status overclaim": lambda contract: contract.__setitem__(
                "status", "target_parity_complete_routes_migrated"
            ),
            "full parity": lambda contract: contract["authorization"].__setitem__(
                "full_target_parity_closed", True
            ),
            "route migration": lambda contract: contract[
                "authorization"].__setitem__("route_migration_eligible", True),
            "external bridge anchor overclaim": lambda contract: contract[
                "authorization"].__setitem__(
                    "external_bridge_bytes_anchor_complete", True
                ),
            "bootstrap blocker removed": lambda contract: contract[
                "authorization"].__setitem__(
                    "route_promotion_blocked_by_bridge_bootstrap", False
                ),
            "post-push anchor removed": lambda contract: contract[
                "acceptance"].__setitem__(
                    "post_push_external_git_anchor_required_before_route_migration",
                    False,
                ),
            "cutover": lambda contract: contract["authorization"].__setitem__(
                "production_cutover", True
            ),
            "arbitrary successor": lambda contract: contract[
                "historical_successor_acceptance"][
                    "anchored_source_overrides"
                ].__setitem__(
                    "tools/unreviewed.py",
                    {
                        "source": "tools/unreviewed.py",
                        "accepted_sha256": "0" * 64,
                        "successor_sha256": "1" * 64,
                    },
                ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self._assert_contract_mutation_rejected(mutation)


if __name__ == "__main__":
    unittest.main()
