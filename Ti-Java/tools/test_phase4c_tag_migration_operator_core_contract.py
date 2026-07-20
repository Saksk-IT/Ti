#!/usr/bin/env python3
"""Tests for the Phase 4C tag-migration operator-core evidence node."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from tools import build_phase4c_tag_migration_operator_core_contract as builder
from tools import phase4c_tag_migration_operator_core_successor_acceptance as acceptance


class Phase4cTagMigrationOperatorCoreContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = builder.ROOT
        cls.contract = acceptance.load(cls.root)

    def test_checked_in_contract_is_exact_deterministic_builder_output(self) -> None:
        document = builder.build_contract(self.root)
        payload = builder.serialized_contract(document)
        self.assertEqual(document, self.contract)
        self.assertEqual(acceptance.CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(acceptance.CONTRACT_SHA256, builder.sha256_bytes(payload))
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            document["document_payload_sha256"],
        )

    def test_fixed_predecessor_and_explicit_bb_anchor_replay_are_exact(self) -> None:
        predecessor = self.contract["predecessor"]
        self.assertEqual(builder.PREDECESSOR_SHA256, predecessor["sha256"])
        self.assertEqual(builder.PREDECESSOR_BYTE_COUNT, predecessor["byte_count"])
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            predecessor["document_payload_sha256"],
        )
        authority = self.contract["node_b_git_authority"]
        self.assertEqual(
            builder.NODE_B_ANCHOR_CHECKPOINT,
            authority["external_anchor_checkpoint"],
        )
        self.assertEqual(
            builder.NODE_B_ANCHOR_ARTIFACTS,
            authority["external_anchor_artifacts"],
        )
        builder.validate_node_b_anchor_git(self.root.parent)

    def test_ordinary_build_and_load_are_gitless_in_minimal_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            for relative in acceptance.minimal_fixture_paths():
                source = self.root / relative
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            self.assertFalse((fixture / ".git").exists())
            with mock.patch.object(
                builder.subprocess,
                "run",
                side_effect=AssertionError("ordinary load attempted subprocess"),
            ):
                self.assertEqual(self.contract, builder.build_contract(fixture))
                self.assertEqual(self.contract, acceptance.load(fixture))

    def test_unknown_escape_symlink_and_tampered_source_fail_closed(self) -> None:
        with self.assertRaisesRegex(AssertionError, "escapes fixed root"):
            builder.fixed_regular_file(self.root, "../outside")
        with self.assertRaisesRegex(AssertionError, "absent or escaped"):
            builder.fixed_regular_file(self.root, "docs/unknown-node-c-source")
        with self.assertRaisesRegex(AssertionError, "unknown or self-authority"):
            builder.validated_source(self.root, builder.OUTPUT_RELATIVE)
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            for relative in acceptance.minimal_fixture_paths():
                source = self.root / relative
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            changed = next(iter(builder.SOURCE_FILES))
            (fixture / changed).write_bytes((fixture / changed).read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed source bytes drifted"):
                builder.build_contract(fixture)
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            target = fixture / "target"
            target.write_bytes((self.root / builder.PREDECESSOR_RELATIVE).read_bytes())
            predecessor = fixture / builder.PREDECESSOR_RELATIVE
            predecessor.parent.mkdir(parents=True, exist_ok=True)
            predecessor.symlink_to(target)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                builder.load_predecessor(fixture)

    def test_exact_49_non_controls_7_controls_and_34_transitions(self) -> None:
        authority = self.contract["source_authority"]
        self.assertEqual(
            builder.FIXED_NON_CONTROL_SOURCE_COUNT,
            authority["fixed_non_control_source_count"],
        )
        self.assertEqual(builder.CONTROL_SOURCE_COUNT, authority["control_source_count"])
        self.assertEqual(
            builder.SOURCE_TRANSITION_COUNT,
            self.contract["historical_source_successors"]["override_count"],
        )
        self.assertEqual(set(builder.SOURCE_FILES), set(
            authority["fixed_non_control_sources"]
        ))
        self.assertEqual(list(builder.CONTROL_SOURCES), authority["control_sources"])
        self.assertFalse(set(builder.SOURCE_FILES) & set(builder.CONTROL_SOURCES))
        self.assertEqual(
            builder.SOURCE_TRANSITIONS,
            self.contract["historical_source_successors"]["overrides"],
        )
        self.assertFalse(authority["dynamic_source_discovery"])
        self.assertTrue(authority["ordinary_build_and_load_are_gitless"])
        self.assertFalse(authority["live_head_main_or_origin_authority"])

    def test_each_source_transition_api_is_exact_and_unknown_is_rejected(self) -> None:
        for relative, expected in builder.SOURCE_TRANSITIONS.items():
            self.assertEqual(expected, acceptance.source_transition(self.root, relative))
            self.assertEqual(
                expected["accepted_sha256"], acceptance.accepted_sha256(relative)
            )
            self.assertEqual(
                expected["successor_sha256"],
                acceptance.successor_sha256(self.root, relative),
            )
        self.assertIsNone(acceptance.source_transition(self.root, "unknown"))
        self.assertIsNone(acceptance.accepted_sha256("unknown"))
        self.assertIsNone(acceptance.successor_sha256(self.root, "unknown"))

    def test_full_runtime_successor_is_exact_300_to_307(self) -> None:
        accepted, current = builder.production_runtime_manifests(self.root)
        result = acceptance.validate_production_runtime_successor(
            self.root,
            accepted,
            current,
            view="full_runtime",
        )
        self.assertEqual(300, result.accepted_file_count)
        self.assertEqual(builder.ACCEPTED_PRODUCTION_MANIFEST_SHA256,
                         result.accepted_manifest_sha256)
        self.assertEqual(307, result.current_file_count)
        self.assertEqual(builder.CURRENT_PRODUCTION_MANIFEST_SHA256,
                         result.current_manifest_sha256)
        self.assertEqual(
            tuple(sorted(builder.PRODUCTION_RUNTIME_ADDITIONS.items())),
            result.added_files,
        )
        self.assertEqual(
            tuple(sorted(builder.PRODUCTION_RUNTIME_CHANGES.items())),
            result.changed_files,
        )
        self.assertEqual((), result.deleted_files)

    def test_learning_personalbank_runtime_successor_is_exact_43_to_50(self) -> None:
        accepted, current = builder.production_runtime_manifests(self.root)
        accepted_main = builder._learning_personalbank_main(accepted)
        current_main = builder._learning_personalbank_main(current)
        result = acceptance.validate_production_runtime_successor(
            self.root,
            accepted_main,
            current_main,
            view="learning_personalbank_main",
        )
        self.assertEqual(43, result.accepted_file_count)
        self.assertEqual(50, result.current_file_count)
        self.assertEqual(
            builder.ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256,
            result.accepted_manifest_sha256,
        )
        self.assertEqual(
            builder.CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256,
            result.current_manifest_sha256,
        )

    def test_runtime_missing_extra_digest_or_unknown_view_fail_closed(self) -> None:
        accepted, current = builder.production_runtime_manifests(self.root)
        missing = dict(current)
        missing.pop(next(iter(builder.PRODUCTION_RUNTIME_ADDITIONS)))
        with self.assertRaisesRegex(AssertionError, "current production manifest"):
            acceptance.validate_production_runtime_successor(
                self.root, accepted, missing, view="full_runtime"
            )
        changed = dict(current)
        changed[next(iter(changed))] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "current production manifest"):
            acceptance.validate_production_runtime_successor(
                self.root, accepted, changed, view="full_runtime"
            )
        extra = dict(current)
        extra["server/src/main/java/Unknown.java"] = "1" * 64
        with self.assertRaisesRegex(AssertionError, "current production manifest"):
            acceptance.validate_production_runtime_successor(
                self.root, accepted, extra, view="full_runtime"
            )
        with self.assertRaisesRegex(AssertionError, "unknown production view"):
            acceptance.validate_production_runtime_successor(
                self.root, accepted, current, view="unknown"
            )

    def test_worm_successor_is_exact_append_only_7_to_8(self) -> None:
        result = acceptance.validate_worm_successor(
            self.root,
            builder.WORM_PREDECESSOR_SHA256,
            builder.ACCEPTED_BUILD_CONTEXT_SHA256,
        )
        self.assertEqual(7, result.accepted_chain_node_count)
        self.assertEqual(8, result.current_chain_node_count)
        self.assertEqual(builder.WORM_PREDECESSOR_SHA256,
                         result.accepted_report_sha256)
        self.assertEqual(builder.WORM_SHA256, result.current_report_sha256)
        self.assertEqual(builder.ACCEPTED_BUILD_CONTEXT_SHA256,
                         result.accepted_build_context_sha256)
        self.assertEqual(builder.CURRENT_BUILD_CONTEXT_SHA256,
                         result.current_build_context_sha256)
        with self.assertRaisesRegex(AssertionError, "rejected WORM predecessor"):
            acceptance.validate_worm_successor(
                self.root, "0" * 64, builder.ACCEPTED_BUILD_CONTEXT_SHA256
            )

    def test_operator_core_is_explicit_bounded_and_has_three_receipts(self) -> None:
        operator = self.contract["operator_core_implementation"]
        self.assertTrue(operator["explicit_callable_only"])
        self.assertFalse(operator["spring_component_or_bean_registration"])
        self.assertFalse(operator["command_line_runner_scheduler_or_http_registration"])
        self.assertFalse(operator["production_data_source_wiring"])
        self.assertEqual(30_000, operator["statement_timeout_milliseconds"])
        self.assertEqual(5_000, operator["lock_timeout_milliseconds"])
        self.assertEqual(60_000, operator["idle_in_transaction_timeout_milliseconds"])
        self.assertEqual(1_048_576, operator["maximum_payload_bytes"])
        self.assertEqual(100_001, operator["maximum_source_rows"])
        self.assertEqual(84, operator["maximum_tag_utf8_bytes"])
        self.assertEqual(200_001, operator["maximum_target_facts"])
        receipts = operator["writer_stop_receipts"]
        self.assertEqual(
            {
                "source_writer_stop_receipt_sha256": "required_separate_digest",
                "target_writer_stop_receipt_sha256": "required_separate_digest",
                "membership_writer_stop_receipt_sha256": "required_separate_digest",
                "single_collapsed_receipt_allowed": False,
                "pairwise_distinct_required": True,
                "all_three_bound_to_ledger_receipts_and_recovery": True,
            },
            receipts,
        )

    def test_schema_acl_retry_receipt_and_recovery_gates_are_closed(self) -> None:
        schema = self.contract["schema_and_acl_verification"]
        self.assertEqual(["16.14", "18.4"], schema["postgresql_versions"])
        self.assertTrue(schema["exact_relation_column_type_nullability_default_identity_checks"])
        self.assertTrue(schema["owner_role_membership_and_effective_acl_closure"])
        self.assertTrue(schema["hostile_search_path_safe"])
        self.assertEqual(0, schema["schema_or_acl_mismatch_business_dml"])
        self.assertEqual(
            builder.EXPECTED_CATALOG_SHA256,
            schema["expected_catalog_sha256"],
        )
        retry = self.contract["bounded_retry_and_ambiguity_recovery"]
        self.assertEqual(["40001", "40P01"], retry["retryable_root_sqlstates"])
        self.assertEqual(3, retry["maximum_attempts"])
        self.assertEqual(2, retry["maximum_retries"])
        self.assertTrue(retry["fresh_connection_pid_and_txid_per_retry"])
        self.assertTrue(retry["deferred_commit_23503_nonretryable"])
        self.assertFalse(retry["real_network_commit_ack_loss_evidenced"])
        invariants = self.contract["source_target_receipt_invariants"]
        self.assertTrue(invariants["partial_receipts_must_be_strict_manifest_prefix"])
        self.assertTrue(invariants["sparse_or_out_of_order_partial_receipts_block"])
        self.assertEqual(0, invariants["exact_receipt_replay_business_dml"])
        self.assertEqual(0, invariants["users_last_active_dml"])

    def test_only_three_operator_gates_are_new_and_production_stays_closed(self) -> None:
        authorization = self.contract["authorization"]
        self.assertEqual(list(builder.NEWLY_CLOSED_GATES),
                         authorization["newly_closed_gates"])
        for field in (
            "migration_global_preflight_evidence_closed",
            "migration_durable_ledger_freeze_design_evidence_closed",
            "operator_core_evidence_closed",
            "bounded_40001_40P01_retry_implemented",
            "operator_migration_implementation",
        ):
            self.assertTrue(authorization[field], field)
        for field in (
            "migration_design_closed",
            "production_durable_ledger_or_tombstone",
            "production_source_write_freeze_evidence_closed",
            "production_target_write_freeze_evidence_closed",
            "production_membership_write_freeze_or_digest_recheck_evidence_closed",
            "production_connection_drain_evidence_closed",
            "production_schema_or_index",
            "flyway_baseline_or_migration",
            "backup_and_rollback_evidence_closed",
            "real_data_migration_execution",
            "legacy_runtime_permanently_disabled",
            "route_or_openapi_delta",
            "client_gateway_or_proxy_change",
            "production_cutover",
            "current_node_control_sources_external_git_anchor_complete",
        ):
            self.assertFalse(authorization[field], field)
        self.assertEqual(builder.ROUTE_STATE, self.contract["route_state"])

    def test_contract_excludes_raw_canary_and_production_or_route_claims(self) -> None:
        payload = builder.serialized_contract(self.contract)
        self.assertNotIn(b"NODEC_CANARY_RAW_TAG_7F21", payload)
        evidence = self.contract["evidence"]
        self.assertEqual(83, evidence["targeted_unit_test_count"])
        self.assertTrue(
            evidence[
                "sparse_partial_receipt_business_facts_and_existing_receipts_unchanged"
            ]
        )
        self.assertTrue(
            evidence[
                "sparse_partial_receipt_durable_block_run_and_single_audit_only"
            ]
        )
        self.assertNotIn(
            "sparse_partial_receipt_rejected_without_fingerprint_change",
            evidence,
        )
        self.assertFalse(evidence["production_database_connected"])
        self.assertFalse(evidence["production_credentials_read"])
        self.assertFalse(evidence["production_data_read_or_mutated"])
        self.assertFalse(evidence["production_operator_executed"])
        controls = self.contract["source_authority"]["control_sources"]
        self.assertFalse(any("compose" in path.lower() for path in controls))
        self.assertFalse(any("openapi" in path.lower() for path in controls))
        self.assertFalse(any("route-delta" in path.lower() for path in controls))

    def test_builder_has_no_dynamic_scan_or_ordinary_git_authority(self) -> None:
        source = inspect.getsource(builder)
        build_source = inspect.getsource(builder.build_contract)
        load_source = inspect.getsource(acceptance.load)
        self.assertNotIn("rglob(", source)
        self.assertNotIn("os.walk", source)
        self.assertNotIn("glob(", source)
        self.assertNotIn("validate_node_b_anchor_git", build_source)
        self.assertNotIn("_run_fixed_git", build_source)
        self.assertNotIn("subprocess", load_source)
        self.assertNotIn("HEAD", build_source)
        self.assertNotIn("origin/main", build_source)

    def test_contract_envelope_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            for relative in acceptance.minimal_fixture_paths():
                source = self.root / relative
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            contract = fixture / builder.OUTPUT_RELATIVE
            document = json.loads(contract.read_bytes())
            document["route_state"]["migrated_operation_count"] = 14
            contract.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "contract bytes drifted"):
                acceptance.load(fixture)


if __name__ == "__main__":
    unittest.main()
