#!/usr/bin/env python3
"""Tests for the Phase 4C durable-ledger/freeze design evidence node."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import (
    build_phase4c_tag_migration_durable_ledger_freeze_design_contract as builder,
)
from tools import (
    phase4c_tag_migration_durable_ledger_freeze_design_successor_acceptance
    as acceptance,
)


class Phase4cTagMigrationDurableLedgerFreezeDesignContractTest(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = builder.ROOT
        cls.contract = acceptance.load_contract(cls.root)

    def test_checked_in_contract_is_exact_deterministic_builder_output(self) -> None:
        document = builder.build_contract(self.root)
        payload = builder.serialized_contract(document)
        self.assertEqual(document, self.contract)
        self.assertEqual(acceptance.EXPECTED_CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(
            acceptance.EXPECTED_CONTRACT_SHA256,
            builder.sha256_bytes(payload),
        )
        self.assertEqual(
            acceptance.EXPECTED_DOCUMENT_PAYLOAD_SHA256,
            document["document_payload_sha256"],
        )

    def test_node_a_physical_payload_and_both_git_checkpoints_are_fixed(self) -> None:
        predecessor = self.contract["predecessor"]
        self.assertEqual(builder.PREDECESSOR_SHA256, predecessor["sha256"])
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            predecessor["document_payload_sha256"],
        )
        self.assertEqual(builder.PREDECESSOR_BYTE_COUNT, predecessor["byte_count"])
        authority = self.contract["node_a_git_authority"]
        self.assertEqual(
            builder.NODE_A_IMPLEMENTATION_CHECKPOINT,
            authority["implementation_checkpoint"],
        )
        self.assertEqual(
            builder.NODE_A_EXTERNAL_ANCHOR_CHECKPOINT,
            authority["external_anchor_checkpoint"],
        )
        self.assertEqual(
            "345deff63d2d3e867926f1e0d05d5e6d90885c4a",
            authority["external_anchor_checkpoint"]["commit_oid"],
        )
        self.assertEqual(6, len(
            authority["external_anchor_checkpoint"]["artifacts"]
        ))

    def test_explicit_git_replay_fixes_six_anchor_blobs_and_legacy_writers(self) -> None:
        builder.validate_node_a_external_anchor_git(self.root.parent)
        for snapshot in builder.LEGACY_WRITER_SNAPSHOTS.values():
            self.assertEqual("100644", snapshot["mode"])
            self.assertRegex(snapshot["git_blob_oid"], r"^[0-9a-f]{40}$")
            self.assertRegex(snapshot["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(snapshot["byte_count"], 0)

    def test_ordinary_build_and_load_work_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            predecessor = fixture / builder.PREDECESSOR_RELATIVE
            predecessor.parent.mkdir(parents=True)
            shutil.copy2(self.root / builder.PREDECESSOR_RELATIVE, predecessor)
            document = builder.build_contract(fixture)
            self.assertEqual(self.contract, document)
            output = fixture / builder.OUTPUT_RELATIVE
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root / builder.OUTPUT_RELATIVE, output)
            self.assertEqual(document, acceptance.load_contract(fixture))
            self.assertFalse((fixture / ".git").exists())

    def test_unknown_escape_symlink_and_tampered_predecessor_fail_closed(self) -> None:
        with self.assertRaisesRegex(AssertionError, "escapes fixed root"):
            builder.fixed_regular_file(self.root, "../outside")
        with self.assertRaisesRegex(AssertionError, "not a regular file"):
            builder.fixed_regular_file(self.root, "docs/unknown-node-b-source")
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            predecessor = fixture / builder.PREDECESSOR_RELATIVE
            predecessor.parent.mkdir(parents=True)
            predecessor.write_bytes(
                (self.root / builder.PREDECESSOR_RELATIVE).read_bytes() + b"\n"
            )
            with self.assertRaisesRegex(AssertionError, "anchor bytes drifted"):
                builder.build_contract(fixture)
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            target = fixture / "target.json"
            target.write_bytes((self.root / builder.PREDECESSOR_RELATIVE).read_bytes())
            predecessor = fixture / builder.PREDECESSOR_RELATIVE
            predecessor.parent.mkdir(parents=True)
            predecessor.symlink_to(target)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                builder.build_contract(fixture)

    def test_state_machine_cas_and_terminal_rules_are_exact(self) -> None:
        state = self.contract["durable_ledger_design"]["state_machine"]
        self.assertEqual(list(builder.STATES), state["states"])
        self.assertEqual(list(builder.TRANSITIONS), state["transitions"])
        self.assertEqual(["APPLIED", "BLOCKED"], state["terminal_states"])
        self.assertTrue(state["insert_requires_clean_planned_v0"])
        self.assertTrue(state["state_version_mapping_database_checked"])
        self.assertTrue(state["exactly_one_concurrent_winner"])
        self.assertTrue(state["freeze_and_restore_digests_immutable_after_first_freeze"])
        self.assertTrue(
            state["applied_transition_immediate_complete_disposition_guard"]
        )
        self.assertTrue(state["applied_transition_deferred_commit_guard"])
        self.assertFalse(state["zero_receipt_applied_transition_allowed"])
        self.assertFalse(
            state["unexplained_zero_target_applied_transition_allowed"]
        )
        self.assertTrue(state["all_empty_noop_with_explicit_receipts_allowed"])
        self.assertEqual(
            [
                "DIGEST_DRIFT",
                "RECEIPT_MISMATCH",
                "TARGET_MISMATCH",
                "IDENTITY_MISMATCH",
                "ILLEGAL_STATE",
            ],
            state["blocked_code_allowlist"],
        )

    def test_receipt_atomicity_replay_and_statement_audit_are_required(self) -> None:
        receipt = self.contract["durable_ledger_design"]["receipt_protocol"]
        for field in (
            "append_only",
            "receipt_inserted_before_target",
            "target_has_receipt_foreign_key",
            "receipt_source_row_has_source_foreign_key",
            "receipt_identity_and_digests_have_ledger_foreign_key",
            "receipt_freeze_restore_digests_have_ledger_foreign_key",
            "receipt_and_target_insert_require_applying",
            "deferred_commit_constraint_requires_applied",
            "deferred_commit_constraint_checks_target_count",
            "every_frozen_source_has_exactly_one_receipt",
            "empty_noop_requires_explicit_receipt",
            "empty_noop_requires_zero_target_rows",
            "material_disposition_requires_positive_target_rows",
            "receipt_target_and_applied_state_single_transaction",
            "receipt_first_replay",
            "exact_receipt_match_required",
            "zero_row_or_on_conflict_dml_attempt_detected_by_statement_audit",
        ):
            self.assertTrue(receipt[field], field)
        self.assertEqual(0, receipt["confirmed_replay_business_dml"])
        self.assertFalse(receipt["local_file_redis_or_user_progress_marker_allowed"])
        self.assertEqual(
            "all_test_fixture_source_rows", receipt["frozen_source_scope"]
        )

    def test_canonical_target_digest_is_database_and_java_derived(self) -> None:
        durable = self.contract["durable_ledger_design"]
        self.assertEqual("uuid", durable["migration_id_storage_type"])
        self.assertFalse(durable["arbitrary_text_migration_id_storable"])
        target = durable["target_fact_digest_protocol"]
        self.assertEqual(
            "ti:phase4c:tag-migration:canonical-target-facts:v1",
            target["domain_separator"],
        )
        self.assertEqual(
            ["distinct question_id", "tag_utf8"], target["canonical_inputs"]
        )
        self.assertFalse(
            target["caller_supplied_target_fact_digest_column_present"]
        )
        for field in (
            "postgresql_recomputes_digest_from_canonical_facts",
            "applied_transition_compares_canonical_digest_to_ledger",
            "applied_transition_compares_canonical_digest_to_all_receipts",
            "java_recovery_independently_recomputes_canonical_digest",
            "wrong_facts_cannot_be_masked_by_caller_digest",
            "wrong_facts_transition_to_blocked_target_mismatch",
        ):
            self.assertTrue(target[field], field)

    def test_domain_separated_recovery_identity_is_three_way_exact(self) -> None:
        identity = self.contract["durable_ledger_design"]["database_identity"]
        self.assertEqual(
            "ti:phase4c:tag-migration:run-identity:v1",
            identity["domain_separator"],
        )
        self.assertEqual(
            "ti:phase4c:tag-migration:cluster-database:v1",
            identity["cluster_database_identity_domain_separator"],
        )
        self.assertIn(
            "cluster_system_identifier",
            identity["cluster_database_identity_inputs"],
        )
        self.assertIn("database_oid", identity["cluster_database_identity_inputs"])
        self.assertEqual(
            [
                "backup_manifest_sha256",
                "migration_run_uuid",
                "cluster_database_identity_sha256",
            ],
            identity["run_identity_inputs"],
        )
        self.assertTrue(
            identity["ledger_receipt_and_fresh_recovery_identity_exact_match"]
        )
        self.assertFalse(
            identity["cluster_system_identifier_or_database_oid_stored_plain"]
        )

    def test_only_real_40001_40p01_are_bounded_to_three_attempts(self) -> None:
        retry = self.contract["retry_and_ambiguity_design"]
        self.assertEqual(["40001", "40P01"], retry["retryable_sqlstates"])
        self.assertEqual(3, retry["maximum_attempts"])
        self.assertEqual(2, retry["maximum_retries"])
        self.assertEqual(1, retry["non_retryable_sqlstate_attempts"])
        self.assertEqual(0, retry["non_retryable_sqlstate_retries"])
        self.assertTrue(retry["fresh_transaction_per_attempt"])
        self.assertTrue(retry["real_postgresql_40001_evidenced"])
        self.assertTrue(retry["real_postgresql_40P01_evidenced"])
        self.assertTrue(retry["real_postgresql_40001_traversed_retry_loop"])
        self.assertTrue(retry["real_postgresql_40P01_traversed_retry_loop"])
        self.assertFalse(retry["production_retry_implementation_present"])

    def test_ack_discard_fixture_does_not_claim_real_network_failure(self) -> None:
        retry = self.contract["retry_and_ambiguity_design"]
        self.assertTrue(retry["ack_discard_after_commit_fixture_evidenced"])
        self.assertFalse(retry["ack_discard_fixture_is_real_network_failure"])
        self.assertFalse(retry["real_network_commit_ack_loss_evidenced"])
        self.assertEqual(0, retry["ambiguous_commit_confirmation_business_dml"])
        self.assertIn("matching_one_time_migration_run_uuid",
                      retry["ambiguous_commit_confirmation_requires"])
        self.assertIn(
            "independently_recomputed_canonical_question_tag_digest",
            retry["ambiguous_commit_confirmation_requires"],
        )
        self.assertIn(
            "complete_disposition_receipt_set",
            retry["ambiguous_commit_confirmation_requires"],
        )

    def test_legacy_writers_make_all_three_production_freezes_false(self) -> None:
        freeze = self.contract["freeze_protocol_design"]
        self.assertFalse(freeze["legacy_writers_take_java_advisory_lock"])
        self.assertFalse(freeze["advisory_lock_alone_is_freeze_evidence"])
        self.assertFalse(freeze["production_source_write_freeze_evidenced"])
        self.assertFalse(freeze["production_target_write_freeze_evidenced"])
        self.assertFalse(
            freeze["production_membership_write_freeze_or_digest_recheck_evidenced"]
        )
        self.assertTrue(
            freeze["legacy_writer_snapshots"]["generic_progress_writer"]
            ["accepts_arbitrary_p_key_delete"]
        )

    def test_role_is_nologin_passwordless_and_exactly_restricted(self) -> None:
        acl = self.contract["acl_and_sensitive_material_design"]
        self.assertFalse(acl["fixture_role_login"])
        self.assertFalse(acl["fixture_role_password_or_connect_grant"])
        self.assertFalse(acl["fixture_role_direct_connect_grant"])
        self.assertTrue(acl["public_connect_revoked_in_disposable_database"])
        self.assertFalse(acl["fixture_role_effective_connect_privilege"])
        self.assertFalse(acl["fixture_role_superuser"])
        self.assertFalse(acl["fixture_role_bypassrls"])
        self.assertTrue(acl["fixture_uses_owner_connection_then_set_role"])
        self.assertTrue(acl["source_select_only"])
        self.assertTrue(acl["receipt_update_or_delete_rejected"])
        self.assertTrue(acl["statement_audit_not_visible_to_fixture_role"])
        self.assertTrue(acl["sensitive_canary_rejected_as_uuid_migration_id"])
        self.assertEqual("uuid", acl["mutation_audit_migration_id_storage_type"])

    def test_only_design_gate_is_new_and_route_stays_13_598_0(self) -> None:
        authorization = self.contract["authorization"]
        self.assertEqual(
            ["migration_durable_ledger_freeze_design_evidence_closed"],
            authorization["newly_closed_gates"],
        )
        self.assertTrue(authorization["migration_global_preflight_evidence_closed"])
        self.assertTrue(
            authorization[
                "migration_durable_ledger_freeze_design_evidence_closed"
            ]
        )
        for field in (
            "migration_design_closed",
            "production_durable_ledger_or_tombstone",
            "production_source_write_freeze_evidence_closed",
            "production_target_write_freeze_evidence_closed",
            "production_membership_write_freeze_or_digest_recheck_evidence_closed",
            "bounded_40001_40P01_retry_implemented",
            "operator_migration_implementation",
            "production_schema_or_index",
            "real_data_migration_execution",
            "production_cutover",
        ):
            self.assertFalse(authorization[field], field)
        self.assertEqual(builder.ROUTE_STATE, self.contract["route_state"])

    def test_eight_controls_are_exact_and_cannot_self_authorize(self) -> None:
        source = self.contract["source_authority"]
        self.assertEqual(8, source["control_source_count"])
        self.assertEqual(list(builder.CONTROL_SOURCES), source["control_sources"])
        self.assertEqual(
            [builder.PREDECESSOR_RELATIVE], source["fixed_source_allowlist"]
        )
        self.assertFalse(
            set(source["control_sources"]) & set(source["fixed_source_allowlist"])
        )
        self.assertTrue(source["control_sources_excluded_from_self_authority"])
        self.assertFalse(source["control_sources_external_git_anchor_complete"])
        self.assertFalse(source["dynamic_source_discovery"])
        self.assertFalse(source["live_head_or_ref_authority"])

    def test_builder_has_no_dynamic_scan_or_old_self_acceptance_dependency(self) -> None:
        source = inspect.getsource(builder)
        build_source = inspect.getsource(builder.build_contract)
        self.assertNotIn("rglob(", source)
        self.assertNotIn("os.walk", source)
        self.assertNotIn("glob(", source)
        self.assertNotIn("HEAD", build_source)
        self.assertNotIn("validate_node_a_external_anchor_git", build_source)
        self.assertNotIn(
            "phase4c_tag_migration_global_preflight_post_push_anchor_"
            "successor_acceptance",
            source,
        )

    def test_sql_fixture_contains_database_guards_but_no_credentials(self) -> None:
        schema = (self.root / (
            "server/src/test/resources/db/phase4c/"
            "074-legacy-personal-bank-tag-durable-ledger-freeze-design-schema.sql"
        )).read_text(encoding="utf-8")
        self.assertIn("NOLOGIN", schema)
        self.assertIn("NOBYPASSRLS", schema)
        self.assertNotIn("PASSWORD", schema)
        self.assertNotIn("GRANT CONNECT", schema)
        self.assertIn("REVOKE CONNECT ON DATABASE", schema)
        self.assertIn("migration_id uuid", schema)
        self.assertNotIn("target_fact_digest_sha256", schema)
        self.assertIn("canonical-target-facts:v1", schema)
        self.assertIn("validate_complete_dispositions", schema)
        self.assertIn("ledger_applied_commit_guard", schema)
        self.assertIn("DEFERRABLE INITIALLY DEFERRED", schema)
        self.assertIn("FOR EACH STATEMENT", schema)
        self.assertIn("requires APPLYING ledger", schema)
        self.assertIn("requires APPLIED ledger", schema)
        self.assertIn("target count mismatch at commit", schema)
        self.assertIn("migration receipts are append-only", schema)
        self.assertIn("SET search_path = pg_catalog, pg_temp", schema)
        self.assertNotIn("CREATE EXTENSION", schema)

    def test_java_it_is_dual_version_contract_parity_not_independent_acceptance(self) -> None:
        evidence = self.contract["evidence"]
        self.assertEqual(["16.14", "18.4"], evidence["postgresql_versions"])
        self.assertTrue(evidence["java_contract_parity_loaded_from_same_integration_test"])
        self.assertFalse(evidence["independent_java_acceptance_claimed"])
        java = (self.root / (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT.java"
        )).read_text(encoding="utf-8")
        self.assertIn("Phase2PostgresContainers.reference18()", java)
        self.assertIn("Phase2PostgresContainers.compatibility16()", java)
        self.assertIn("SetRoleDataSource(owner, OPERATOR)", java)
        self.assertNotIn("OPERATOR_PASSWORD", java)
        self.assertIn("pg_current_xact_id()::text", java)
        self.assertIn("pg_control_system()", java)
        self.assertIn("canonicalTargetDigest", java)
        self.assertIn("insertEmptyNoopReceipt", java)
        self.assertTrue(evidence["public_connect_effective_privilege_removed"])
        self.assertNotIn("List.of(leftError, rightError)", java)

    def test_sensitive_canary_is_confined_to_seed_and_java_probe(self) -> None:
        payload = builder.serialized_contract(self.contract)
        self.assertNotIn(b"NODEB_SENSITIVE_CANARY", payload)
        seed = (self.root / (
            "server/src/test/resources/db/phase4c/"
            "075-legacy-personal-bank-tag-durable-ledger-freeze-design-seed.sql"
        )).read_text(encoding="utf-8")
        self.assertIn("NODEB_SENSITIVE_CANARY_KEY_DO_NOT_PERSIST", seed)
        acl = self.contract["acl_and_sensitive_material_design"]
        self.assertTrue(acl["sensitive_canary_absent_from_contract_payload"])
        self.assertTrue(
            acl["sensitive_canary_absent_from_ledger_receipt_and_mutation_audit"]
        )

    def test_no_production_main_flyway_compose_openapi_or_route_delta_is_claimed(self) -> None:
        durable = self.contract["durable_ledger_design"]
        self.assertTrue(durable["fixture_only"])
        self.assertFalse(durable["production_relation_created"])
        self.assertFalse(durable["flyway_migration_created"])
        controls = self.contract["source_authority"]["control_sources"]
        self.assertFalse(any("server/src/main" in path for path in controls))
        self.assertFalse(any("compose" in path.lower() for path in controls))
        self.assertFalse(any("openapi" in path.lower() for path in controls))
        self.assertFalse(any("route" in path.lower() for path in controls))


if __name__ == "__main__":
    unittest.main()
