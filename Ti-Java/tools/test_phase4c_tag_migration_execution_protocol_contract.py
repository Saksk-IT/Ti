#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C execution-protocol contract."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from tools import build_phase4c_tag_migration_execution_protocol_contract as builder
    from tools import phase4c_tag_migration_execution_protocol_successor_acceptance as successor
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_execution_protocol_contract",
        "tools.phase4c_tag_migration_execution_protocol_successor_acceptance",
    }:
        raise
    import build_phase4c_tag_migration_execution_protocol_contract as builder
    import phase4c_tag_migration_execution_protocol_successor_acceptance as successor


class Phase4cTagMigrationExecutionProtocolContractTest(unittest.TestCase):

    def test_fixed_partition_and_authorized_gate_names_are_exact(self) -> None:
        self.assertEqual(7, builder.CONTROL_SOURCE_COUNT)
        self.assertEqual(7, len(builder.CONTROL_SOURCES))
        self.assertEqual(11, builder.IMPLEMENTATION_SOURCE_COUNT)
        self.assertEqual(11, len(builder.IMPLEMENTATION_SOURCE_PATHS))
        self.assertEqual(37, builder.SOURCE_TRANSITION_COUNT)
        self.assertEqual(37, len(builder.SOURCE_TRANSITION_PATHS))
        self.assertEqual(48, builder.FIXED_NON_CONTROL_SOURCE_COUNT)
        self.assertEqual(
            set(builder.SOURCE_FILES),
            set(builder.IMPLEMENTATION_SOURCE_PATHS).union(
                builder.SOURCE_TRANSITION_PATHS
            ),
        )
        self.assertFalse(
            set(builder.SOURCE_FILES).intersection(builder.CONTROL_SOURCES)
        )
        self.assertEqual(
            (
                "migration_execution_protocol_implemented",
                "cryptographic_evidence_verifier_implemented",
                "local_test_backup_restore_execution_rehearsal_closed",
            ),
            builder.NEWLY_CLOSED_GATES,
        )

    def test_predecessor_is_the_fixed_c2_contract(self) -> None:
        document = builder.load_predecessor()
        self.assertEqual(builder.PREDECESSOR_ID, document["contract_id"])
        self.assertEqual(
            builder.PREDECESSOR_INDEPENDENT_ACCEPTANCE_COMMIT,
            document["independent_acceptance_checkpoint"]["commit_oid"],
        )
        self.assertEqual(builder.ROUTE_STATE, document["route_state"])
        self.assertEqual(
            "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936",
            builder.PREDECESSOR_SHA256,
        )
        self.assertEqual(
            "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64",
            builder.PREDECESSOR_PAYLOAD_SHA256,
        )
        self.assertEqual(84_461, builder.PREDECESSOR_BYTE_COUNT)

    def test_build_is_deterministic_and_ordinary_path_is_gitless(self) -> None:
        with mock.patch.object(
            builder.subprocess,
            "run",
            side_effect=AssertionError("ordinary build attempted a subprocess"),
        ):
            first = builder.build_contract()
            second = builder.build_contract()
        self.assertEqual(first, second)
        self.assertEqual(
            builder.document_payload_sha256(first),
            first["document_payload_sha256"],
        )
        self.assertEqual(
            builder.serialized_contract(first),
            builder.serialized_contract(second),
        )

    def test_checked_in_contract_matches_builder_and_fixed_envelope(self) -> None:
        document = successor.load()
        self.assertEqual(builder.build_contract(), document)
        payload = builder.fixed_regular_file(
            builder.ROOT, builder.OUTPUT_RELATIVE
        ).read_bytes()
        self.assertEqual(successor.CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(
            successor.CONTRACT_SHA256, builder.sha256_bytes(payload)
        )
        self.assertEqual(
            successor.CONTRACT_PAYLOAD_SHA256,
            document["document_payload_sha256"],
        )

    def test_contract_holds_exact_source_runtime_worm_and_route_boundaries(
        self,
    ) -> None:
        document = builder.build_contract()
        authority = document["source_authority"]
        self.assertEqual(48, authority["fixed_non_control_source_count"])
        self.assertEqual(11, authority["implementation_source_count"])
        self.assertEqual(37, authority["transition_source_count"])
        self.assertEqual(7, authority["control_source_count"])
        self.assertFalse(authority["dynamic_source_discovery"])
        self.assertTrue(authority["ordinary_build_and_load_are_gitless"])
        self.assertFalse(authority["live_head_main_or_origin_authority"])
        self.assertTrue(authority["fixed_c2_commit_replay_is_explicit_only"])

        transitions = document["historical_source_successors"]
        self.assertEqual(37, transitions["override_count"])
        self.assertEqual(builder.SOURCE_TRANSITIONS, transitions["overrides"])

        runtime = document["production_runtime_successor"]
        self.assertEqual(307, runtime["accepted_file_count"])
        self.assertEqual(311, runtime["current_file_count"])
        self.assertEqual("4A0M0D", runtime["exact_delta"])
        self.assertEqual(4, len(runtime["added_files"]))
        self.assertEqual({}, runtime["changed_files"])
        self.assertEqual([], runtime["deleted_files"])
        self.assertEqual(
            50, runtime["learning_personalbank_main"]["accepted_file_count"]
        )
        self.assertEqual(
            54, runtime["learning_personalbank_main"]["current_file_count"]
        )

        worm = document["worm_successor"]
        self.assertEqual(8, worm["accepted_chain_node_count"])
        self.assertEqual(9, worm["current_chain_node_count"])
        self.assertEqual(1, worm["appended_node_count"])
        self.assertFalse(worm["historical_nodes_rewritten"])
        self.assertEqual(builder.ROUTE_STATE, document["route_state"])

    def test_only_three_gates_close_and_production_authority_stays_false(
        self,
    ) -> None:
        authorization = builder.build_contract()["authorization"]
        self.assertEqual(
            list(builder.NEWLY_CLOSED_GATES),
            authorization["newly_closed_gates"],
        )
        for gate in builder.NEWLY_CLOSED_GATES:
            self.assertTrue(authorization[gate], gate)
        for gate in (
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
            "production_trust_roots_or_key_rotation_audit",
            "durable_evidence_nonce_journal",
            "operator_runtime_wiring",
            "legacy_runtime_permanently_disabled",
            "route_or_openapi_delta",
            "client_gateway_or_proxy_change",
            "production_cutover",
        ):
            self.assertFalse(authorization[gate], gate)

    def test_python_successor_api_propagates_exact_transition(self) -> None:
        relative = builder.SOURCE_TRANSITION_PATHS[0]
        transition = successor.source_transition(builder.ROOT, relative)
        self.assertEqual(builder.SOURCE_TRANSITIONS[relative], transition)
        document = successor.load(builder.ROOT)
        self.assertEqual(
            transition,
            successor.source_transition_from_validated_document(
                builder.ROOT, relative, document
            ),
        )
        self.assertIsNone(
            successor.source_transition_from_validated_document(
                builder.ROOT, "unknown", document
            )
        )
        self.assertEqual(
            transition["accepted_sha256"], successor.accepted_sha256(relative)
        )
        self.assertEqual(
            transition["successor_sha256"],
            successor.successor_sha256(builder.ROOT, relative),
        )
        self.assertEqual(
            tuple(builder.SOURCE_TRANSITION_PATHS), successor.successor_paths()
        )
        self.assertIsNone(successor.source_transition(builder.ROOT, "unknown"))
        self.assertIsNone(successor.accepted_sha256("unknown"))
        self.assertIsNone(successor.successor_sha256(builder.ROOT, "unknown"))
        calls = 0

        def factory() -> object:
            nonlocal calls
            calls += 1
            return object()

        with successor.validation_session():
            first = successor.validation_session_cached(
                "test-session-boundary", builder.ROOT, factory
            )
            second = successor.validation_session_cached(
                "test-session-boundary", builder.ROOT, factory
            )
            self.assertIs(first, second)
            self.assertEqual(1, calls)

        self.assertIsNot(
            first,
            successor.validation_session_cached(
                "test-session-boundary", builder.ROOT, factory
            ),
        )
        self.assertEqual(2, calls)

    def test_runtime_successor_api_accepts_only_exact_views(self) -> None:
        accepted, current = builder.production_runtime_manifests()
        full = successor.validate_production_runtime_successor(
            builder.ROOT, accepted, current
        )
        self.assertEqual("full_runtime", full.view)
        self.assertEqual(307, full.accepted_file_count)
        self.assertEqual(311, full.current_file_count)
        self.assertEqual(4, len(full.added_files))
        self.assertEqual((), full.changed_files)
        self.assertEqual((), full.deleted_files)

        accepted_main = builder._learning_personalbank_main(accepted)
        current_main = builder._learning_personalbank_main(current)
        scoped = successor.validate_production_runtime_successor(
            builder.ROOT,
            accepted_main,
            current_main,
            view="learning_personalbank_main",
        )
        self.assertEqual(50, scoped.accepted_file_count)
        self.assertEqual(54, scoped.current_file_count)

        tampered = dict(current)
        tampered.pop(next(iter(tampered)))
        with self.assertRaisesRegex(
            AssertionError, "rejected current runtime"
        ):
            successor.validate_production_runtime_successor(
                builder.ROOT, accepted, tampered
            )

    def test_worm_successor_api_binds_node_8_to_node_9(self) -> None:
        result = successor.validate_worm_successor(
            builder.ROOT,
            builder.WORM_PREDECESSOR_SHA256,
            builder.ACCEPTED_BUILD_CONTEXT_SHA256,
        )
        self.assertEqual(8, result.accepted_chain_node_count)
        self.assertEqual(9, result.current_chain_node_count)
        self.assertEqual(builder.WORM_SHA256, result.current_report_sha256)
        self.assertEqual(
            builder.CURRENT_BUILD_CONTEXT_SHA256,
            result.current_build_context_sha256,
        )
        with self.assertRaisesRegex(
            AssertionError, "rejected WORM predecessor"
        ):
            successor.validate_worm_successor(
                builder.ROOT,
                "0" * 64,
                builder.ACCEPTED_BUILD_CONTEXT_SHA256,
            )

    def test_fixed_path_loader_rejects_unknown_absolute_escape_and_symlink(
        self,
    ) -> None:
        for relative in ("", ".", "../escape", "/tmp/escape"):
            with self.assertRaises(AssertionError):
                builder.fixed_regular_file(builder.ROOT, relative)
        with self.assertRaisesRegex(AssertionError, "unknown or self-authority"):
            builder.validated_source(builder.ROOT, builder.CONTROL_SOURCES[0])
        with self.assertRaisesRegex(AssertionError, "unknown or self-authority"):
            builder.validated_source(builder.ROOT, "unknown")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.write_text("fixed", encoding="utf-8")
            (root / "link").symlink_to(real)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                builder.fixed_regular_file(root, "link")

    def test_refresh_and_git_replay_are_explicit_fixed_allowlist_only(self) -> None:
        source = inspect.getsource(builder.refreshed_fixed_map)
        for forbidden in (
            ".glob(",
            ".rglob(",
            "os.walk",
            "diff --name",
            "ls-files",
            "HEAD",
            "origin/main",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("IMPLEMENTATION_SOURCE_PATHS", source)
        self.assertIn("SOURCE_TRANSITION_PATHS", source)
        replay = inspect.getsource(builder.validate_predecessor_git)
        self.assertIn("PREDECESSOR_COMMIT", replay)
        self.assertNotIn("HEAD", replay)
        self.assertNotIn("origin/main", replay)

    def test_minimal_fixture_is_fixed_and_contains_every_physical_authority(
        self,
    ) -> None:
        fixture = successor.minimal_fixture_paths()
        self.assertEqual(len(fixture), len(set(fixture)))
        self.assertIn(builder.OUTPUT_RELATIVE, fixture)
        self.assertIn(builder.PREDECESSOR_RELATIVE, fixture)
        self.assertIn(builder.WORM_PREDECESSOR_RELATIVE, fixture)
        self.assertIn(builder.BUILD_CONTEXT_SCRIPT_RELATIVE, fixture)
        self.assertTrue(set(builder.SOURCE_FILES).issubset(fixture))
        self.assertFalse(set(builder.CONTROL_SOURCES[1:]).issubset(fixture))

    def test_contract_contains_no_secret_or_production_execution_claim(self) -> None:
        document = builder.build_contract()
        encoded = json.dumps(document, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "PRIVATE KEY",
            "BEGIN OPENSSH",
            "jdbc:postgresql://",
            "production_password",
            "executeAll",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            document["evidence"]["production_connection_or_credentials_used"]
        )
        self.assertFalse(document["evidence"]["production_data_read_or_mutated"])


if __name__ == "__main__":
    unittest.main()
