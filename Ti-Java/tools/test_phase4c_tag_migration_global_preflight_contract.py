#!/usr/bin/env python3
"""Tests for the append-only Phase 4C tag global-preflight contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import types
import unittest
from unittest import mock

try:
    from tools import build_phase4c_tag_migration_global_preflight_contract as builder
    from tools import build_phase4c_tag_migration_operator_core_contract as operator_builder
    from tools import phase4c_tag_migration_execution_protocol_successor_acceptance as node_d_acceptance
    from tools import phase4c_tag_migration_global_preflight_successor_acceptance as acceptance
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_global_preflight_contract",
        "tools.build_phase4c_tag_migration_operator_core_contract",
        "tools.phase4c_tag_migration_execution_protocol_successor_acceptance",
        "tools.phase4c_tag_migration_global_preflight_successor_acceptance",
    }:
        raise
    import build_phase4c_tag_migration_global_preflight_contract as builder
    import build_phase4c_tag_migration_operator_core_contract as operator_builder
    import phase4c_tag_migration_execution_protocol_successor_acceptance as node_d_acceptance
    import phase4c_tag_migration_global_preflight_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
NODE_D_PRODUCTION_ADDITIONS = (
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "Ed25519TagMigrationEvidenceVerifier.java",
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "LegacyPersonalBankTagMigrationExecutionProtocol.java",
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "TagMigrationPlanCandidate.java",
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "TagMigrationPlanCandidateFactory.java",
)


def node_d_runtime(current: dict[str, str], root: Path) -> dict[str, str]:
    successor = dict(current)
    for relative in NODE_D_PRODUCTION_ADDITIONS:
        successor[relative] = builder.sha256_bytes((root / relative).read_bytes())
    return dict(sorted(successor.items()))


class TagMigrationGlobalPreflightContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = acceptance.load(ROOT)

    def _minimal_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "Ti-Java"
        root.mkdir()
        for relative in acceptance.minimal_fixture_paths():
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return temporary, root

    def _semantic_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "Ti-Java"
        root.mkdir()
        for relative in acceptance.semantic_fixture_paths(ROOT):
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return temporary, root

    def test_01_contract_is_a_deterministic_physical_successor(self) -> None:
        built = builder.build_contract(ROOT)
        self.assertEqual(self.contract, built)
        self.assertEqual(
            acceptance.CONTRACT_SHA256,
            builder.sha256_bytes(builder.serialized(built)),
        )
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            built["document_payload_sha256"],
        )

    def test_02_fixed_composition_route_and_approved_bytes_are_authoritative(self) -> None:
        predecessors = self.contract["append_only_predecessors"]
        self.assertEqual(
            "ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b",
            predecessors["semantic_composition"]["sha256"],
        )
        self.assertEqual(
            "e5bc53bb8c011c5cf2f08447543aa3e5dd2a045b6226f064c6594a3639d7b5c9",
            predecessors["current_route_promotion"]["sha256"],
        )
        self.assertEqual(
            "921d6626ab11d59a9667e1942953807b0aa1a81c06c01094cc109312f9d6b300",
            predecessors["approved_differences"]["sha256"],
        )
        self.assertEqual(
            list(builder.MIGRATION_APPROVED_DIFFERENCE_IDS),
            predecessors["approved_differences"]["accepted_migration_ids"],
        )
        self.assertEqual(
            list(builder.CURRENT_APPROVED_DIFFERENCE_IDS),
            predecessors["approved_differences"]["current_physical_file_ids"],
        )

    def test_03_historical_outcomes_and_actual_dispositions_are_separate(self) -> None:
        aggregation = self.contract["global_preflight_protocol"]["aggregation"]
        self.assertEqual(
            list(builder.HISTORICAL_ROW_OUTCOMES),
            aggregation["historical_row_outcomes"],
        )
        self.assertEqual(
            builder.HISTORICAL_REPORTING_GROUPS,
            aggregation["historical_reporting_groups"],
        )
        self.assertEqual(12, len(aggregation["historical_row_outcomes"]))
        self.assertEqual(5, len(aggregation["historical_reporting_groups"]))
        grouped = [
            outcome
            for group in aggregation["historical_reporting_groups"].values()
            for outcome in group
        ]
        self.assertCountEqual(builder.HISTORICAL_ROW_OUTCOMES, grouped)
        self.assertTrue(aggregation["historical_vocabulary_is_apply_predecessor_only"])
        self.assertFalse(aggregation["dry_run_emits_migrated_or_transaction_failure_outcomes"])
        self.assertEqual(
            list(builder.PREFLIGHT_DISPOSITIONS),
            aggregation["preflight_dispositions"],
        )
        self.assertEqual(
            builder.PREFLIGHT_REPORTING_GROUPS,
            aggregation["preflight_reporting_groups"],
        )
        self.assertEqual(11, len(aggregation["preflight_dispositions"]))
        actual_grouped = [
            disposition
            for group in aggregation["preflight_reporting_groups"].values()
            for disposition in group
        ]
        self.assertCountEqual(builder.PREFLIGHT_DISPOSITIONS, actual_grouped)
        self.assertTrue(aggregation["global_all_or_block"])

    def test_04_only_global_preflight_evidence_is_newly_closed(self) -> None:
        authorization = self.contract["authorization"]
        self.assertEqual(
            ["migration_global_preflight_evidence_closed"],
            authorization["newly_closed_gates"],
        )
        self.assertTrue(authorization["migration_global_preflight_evidence_closed"])
        for field in (
            "migration_design_closed",
            "operator_migration_implementation",
            "production_schema_or_index",
            "real_data_migration_execution",
            "production_cutover",
            "route_or_openapi_delta",
            "http_security_or_rate_limit_delta",
            "client_gateway_or_proxy_change",
        ):
            self.assertFalse(authorization[field], field)

    def test_05_pg16_pg18_evidence_is_read_only_and_not_production(self) -> None:
        evidence = self.contract["evidence"]
        connection = self.contract["global_preflight_protocol"]["connection"]
        selection = self.contract["global_preflight_protocol"]["selection_and_parsing"]
        bounds = self.contract["global_preflight_protocol"]["source_sweep_bounds"]
        mutation = self.contract["global_preflight_protocol"]["mutation_safety"]
        self.assertEqual(["16.14", "18.4"], evidence["postgresql_versions"])
        self.assertTrue(evidence["mixed_fixture_global_blocker_aggregation"])
        self.assertEqual(16, evidence["mixed_fixture_candidate_count"])
        self.assertEqual(
            builder.MIXED_FIXTURE_REPORTING_GROUP_COUNTS,
            evidence["mixed_fixture_reporting_group_counts"],
        )
        self.assertTrue(evidence["session_lock_contention_and_release_after_connection_close"])
        self.assertTrue(evidence["dry_run_zero_mutation_fingerprints"])
        self.assertTrue(evidence["bounded_source_payload_and_sweep_limits_evidenced"])
        self.assertTrue(evidence["unicode_postgresql_text_losslessness_evidenced"])
        self.assertFalse(
            evidence["bounded_payload_or_unicode_hardening_authorizes_apply"]
        )
        self.assertEqual(1_048_576, selection["per_payload_utf8_byte_limit"])
        self.assertTrue(selection["oversized_payload_rejected_before_json_parsing"])
        self.assertTrue(selection["postgresql_text_lossless_required"])
        self.assertTrue(selection["nul_and_unpaired_surrogates_rejected"])
        self.assertTrue(selection["valid_surrogate_pairs_preserved"])
        self.assertTrue(selection["unicode_case_and_normalization_forms_preserved"])
        self.assertEqual(100_000, bounds["maximum_reserved_source_rows"])
        self.assertEqual(268_435_456, bounds["maximum_reserved_source_utf8_bytes"])
        self.assertEqual(16, bounds["source_fetch_size"])
        self.assertTrue(bounds["sql_octet_length_checked_before_payload_materialization"])
        self.assertFalse(bounds["oversized_payload_materialized"])
        self.assertFalse(bounds["oversized_payload_target_or_membership_read"])
        self.assertFalse(bounds["bounds_are_production_scale_evidence"])
        self.assertEqual(0, mutation["source_dml"])
        self.assertEqual(0, mutation["target_dml"])
        self.assertEqual(0, mutation["schema_or_index_ddl"])
        self.assertFalse(evidence["production_database_connected"])
        self.assertFalse(evidence["production_credentials_read"])
        self.assertFalse(evidence["production_data_read_or_mutated"])
        expected_global_failures = {
            "CONNECTION_ACQUISITION_FAILED",
            "CONNECTION_SETUP_FAILED",
            "ADVISORY_LOCK_ACQUISITION_FAILED",
            "CONNECTION_METADATA_READ_FAILED",
            "TRANSACTION_SETUP_FAILED",
            "SOURCE_SCAN_FAILED",
            "CLASSIFICATION_READ_FAILED",
            "READ_ONLY_COMMIT_FAILED",
            "READ_ONLY_ROLLBACK_FAILED",
            "ADVISORY_UNLOCK_REJECTED",
            "ADVISORY_UNLOCK_FAILED",
            "CONNECTION_CLOSE_FAILED",
        }
        actual_global_failures = connection["global_failure_codes"]
        self.assertEqual(12, len(actual_global_failures))
        self.assertEqual(12, len(set(actual_global_failures)))
        self.assertEqual(expected_global_failures, set(actual_global_failures))

    def test_06_durable_marker_and_apply_protocol_remain_fail_closed(self) -> None:
        fail_closed = self.contract["apply_fail_closed"]
        self.assertFalse(fail_closed["production_apply_authorized"])
        self.assertFalse(
            fail_closed["planner_cleanliness_eligibility_is_production_authorization"]
        )
        self.assertEqual(
            list(builder.APPLY_PREREQUISITE_BLOCKERS),
            fail_closed["planner_apply_prerequisite_blockers"],
        )
        self.assertFalse(fail_closed["durable_migration_ledger_or_tombstone_exists"])
        self.assertTrue(fail_closed["durable_marker_absence_blocks_apply"])
        self.assertFalse(fail_closed["source_write_freeze_evidenced"])
        self.assertFalse(
            fail_closed["target_write_freeze_or_common_version_protocol_evidenced"]
        )
        self.assertFalse(
            fail_closed["membership_write_freeze_or_digest_recheck_evidenced"]
        )
        self.assertFalse(fail_closed["bounded_40001_40P01_retry_implemented"])
        self.assertFalse(fail_closed["backup_and_rollback_evidence_exists"])
        self.assertFalse(fail_closed["real_apply_path_present"])

    def test_07_route_authority_remains_13_598_0(self) -> None:
        self.assertEqual({
            "total_operation_count": 611,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
        }, self.contract["route_state"])

    def test_08_hardened_main_sources_append_a_seventh_worm_successor(self) -> None:
        authority = self.contract["build_context_authority"]
        self.assertEqual(
            "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
            authority["old_worm_predecessor"]["sha256"],
        )
        self.assertTrue(authority["current_build_context_changed"])
        self.assertEqual(3, authority["new_main_source_count"])
        self.assertEqual(
            [builder.SOURCES[name] for name in builder.NEW_MAIN_SOURCE_NAMES],
            authority["new_main_sources"],
        )
        self.assertFalse(authority["spring_component_runner_scheduler_or_http_registration"])
        self.assertFalse(authority["apply_statement_or_operator_entrypoint_added"])
        self.assertEqual({
            **builder.SOURCES["tag_global_preflight_worm_successor"],
            "java_build_context_sha256": builder.TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256,
            "dockerfile_sha256": builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
            "predecessor_sha256": builder.TAG_GLOBAL_PREFLIGHT_WORM_PREDECESSOR_SHA256,
            "fixed_chain_node_count": 6,
            "immutable": True,
        }, authority["initial_worm_successor"])
        self.assertEqual({
            **builder.SOURCES["tag_global_preflight_hardening_worm_successor"],
            "java_build_context_sha256": (
                builder.TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256
            ),
            "dockerfile_sha256": builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
            "predecessor_sha256": (
                builder.TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_PREDECESSOR_SHA256
            ),
            "fixed_chain_node_count": 7,
            "immutable": True,
        }, authority["new_worm_successor"])
        self.assertTrue(authority["initial_worm_successor_appended"])
        self.assertTrue(authority["new_worm_successor_was_required"])
        self.assertFalse(authority["new_worm_successor_required"])
        self.assertTrue(authority["new_worm_successor_appended"])
        self.assertFalse(authority["old_tip_reused_as_current"])
        self.assertFalse(authority["initial_worm_tip_reused_as_current"])
        self.assertTrue(authority["new_build_context_worm_closed"])
        self.assertFalse(authority["historical_worm_chain_overwritten"])

    def test_09_builder_calls_only_the_fixed_chain_and_requires_the_exact_tip(
        self,
    ) -> None:
        initial = types.SimpleNamespace(
            label=builder.TAG_GLOBAL_PREFLIGHT_WORM_LABEL,
            relative_path=(
                builder.SOURCES["tag_global_preflight_worm_successor"]["source"]
            ),
            sha256=builder.SOURCES["tag_global_preflight_worm_successor"]["sha256"],
            build_context_sha256=builder.TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256,
            dockerfile_sha256=builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
            predecessor_sha256=builder.TAG_GLOBAL_PREFLIGHT_WORM_PREDECESSOR_SHA256,
        )
        exact_tip = types.SimpleNamespace(
            label=builder.TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_LABEL,
            relative_path=(
                builder.SOURCES[
                    "tag_global_preflight_hardening_worm_successor"
                ]["source"]
            ),
            sha256=builder.SOURCES[
                "tag_global_preflight_hardening_worm_successor"
            ]["sha256"],
            build_context_sha256=(
                builder.TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256
            ),
            dockerfile_sha256=builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
            predecessor_sha256=(
                builder.TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_PREDECESSOR_SHA256
            ),
        )
        validate_evidence_chain = mock.Mock(return_value=exact_tip)
        immutable_mirrors = (object(),)
        phase2_worm = types.SimpleNamespace(
            FIXED_EVIDENCE_CHAIN=(
                *((object(),) * 5),
                initial,
                exact_tip,
                object(),
                object(),
            ),
            FIXED_IMMUTABLE_MIRRORS=immutable_mirrors,
            validate_evidence_chain=validate_evidence_chain,
        )
        with mock.patch.object(
            builder,
            "_load_phase2_worm_validator",
            return_value=phase2_worm,
        ):
            self.assertEqual(self.contract, builder.build_contract(ROOT))
        validate_evidence_chain.assert_called_once_with(
            ROOT,
            builder.fixed_regular_file(ROOT, builder.PHASE2_DRIFT_MANIFEST_RELATIVE),
            builder.TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
            builder.TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256,
            chain=phase2_worm.FIXED_EVIDENCE_CHAIN[:7],
            immutable_mirrors=immutable_mirrors,
        )

        wrong_tip = types.SimpleNamespace(
            **{
                **vars(exact_tip),
                "predecessor_sha256": "0" * 64,
            }
        )
        phase2_worm.validate_evidence_chain = mock.Mock(return_value=wrong_tip)
        with mock.patch.object(
            builder,
            "_load_phase2_worm_validator",
            return_value=phase2_worm,
        ):
            with self.assertRaisesRegex(AssertionError, "fixed WORM chain tip drifted"):
                builder.build_contract(ROOT)

    def test_10_gitless_minimal_fixed_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_11_tamper_and_symlink_sources_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.SOURCES["global_preflight_seed"]["source"]
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed bytes drifted"):
                acceptance.load(root)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.SOURCES["global_preflight_pg_it"]["source"]
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.java"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)

    def test_12_authorization_mutation_and_worm_tamper_are_rejected(self) -> None:
        changed = deepcopy(self.contract)
        changed["authorization"]["operator_migration_implementation"] = True
        with self.assertRaisesRegex(AssertionError, "payload|authorization"):
            acceptance.validate(changed, ROOT)

        changed = deepcopy(self.contract)
        changed["apply_fail_closed"]["production_apply_authorized"] = True
        with self.assertRaisesRegex(AssertionError, "payload|apply"):
            acceptance.validate(changed, ROOT)

        changed = deepcopy(self.contract)
        changed["build_context_authority"]["new_build_context_worm_closed"] = False
        with self.assertRaisesRegex(AssertionError, "payload|WORM"):
            acceptance.validate(changed, ROOT)

    def test_13_unknown_control_and_dynamic_sources_are_rejected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "unknown or self-authority"):
            builder.validated_source(ROOT, "unknown")
        for control_source in builder.CONTROL_SOURCES:
            self.assertNotIn(
                control_source,
                {descriptor["source"] for descriptor in builder.SOURCES.values()},
            )
        source = (
            ROOT / "tools/build_phase4c_tag_migration_global_preflight_contract.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            ".glob(",
            ".rglob(",
            "git ls-files",
            "git rev-parse",
            '"HEAD"',
        ):
            self.assertNotIn(forbidden, source)

    def test_14_exact_source_successor_bridge_is_fixed_and_external_anchor_false(
        self,
    ) -> None:
        bridges = self.contract["source_successor_bridges"]
        self.assertEqual(len(builder.SOURCE_SUCCESSORS), bridges["path_count"])
        self.assertEqual(sorted(builder.SOURCE_SUCCESSORS), bridges["paths"])
        self.assertEqual(
            sorted(builder.TYPED_PHASE2_SOURCE_SUCCESSORS),
            bridges["typed_phase2_paths"],
        )
        self.assertEqual(
            sorted(builder.PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS),
            bridges["phase6_typed_bridge_paths"],
        )
        self.assertEqual(
            sorted(builder.PHASE6_DOCUMENT_SOURCE_SUCCESSORS),
            bridges["phase6_document_paths"],
        )
        self.assertEqual(
            sorted(builder.PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS),
            bridges["phase6_bootstrap_paths"],
        )
        self.assertEqual(
            sorted(builder.SEMANTIC_CONSUMER_SOURCE_SUCCESSORS),
            bridges["semantic_consumer_paths"],
        )
        self.assertEqual(
            sorted(builder.POST_PUSH_BRIDGE_SOURCE_SUCCESSORS),
            bridges["post_push_bridge_paths"],
        )
        self.assertEqual(
            sorted(builder.TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS),
            bridges["typed_normalization_bridge_paths"],
        )
        groups = (
            set(builder.TYPED_PHASE2_SOURCE_SUCCESSORS),
            set(builder.PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS),
            set(builder.PHASE6_DOCUMENT_SOURCE_SUCCESSORS),
            set(builder.PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS),
            set(builder.SEMANTIC_CONSUMER_SOURCE_SUCCESSORS),
            set(builder.POST_PUSH_BRIDGE_SOURCE_SUCCESSORS),
            set(builder.TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS),
        )
        for index, left in enumerate(groups):
            for right in groups[index + 1:]:
                self.assertFalse(left.intersection(right))
        self.assertEqual(
            set(builder.SOURCE_SUCCESSORS),
            set().union(*groups),
        )
        self.assertFalse(bridges["source_successor_external_git_anchor_complete"])
        self.assertFalse(
            self.contract["authorization"][
                "source_successor_external_git_anchor_complete"
            ]
        )
        self.assertFalse(
            self.contract["authorization"][
                "semantic_successor_external_git_anchor_complete"
            ]
        )
        self.assertFalse(
            self.contract["authorization"][
                "bootstrap_control_sources_external_git_anchor_complete"
            ]
        )
        source_authority = self.contract["source_authority"]
        self.assertEqual(11, source_authority["control_source_count"])
        self.assertFalse(
            source_authority["control_sources_external_git_anchor_complete"]
        )
        self.assertIn(
            "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
            source_authority["control_sources"],
        )
        self.assertIn(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
            source_authority["control_sources"],
        )
        self.assertIn(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java",
            source_authority["control_sources"],
        )
        for relative, transition in builder.SOURCE_SUCCESSORS.items():
            with self.subTest(relative=relative):
                actual = bridges["overrides"][relative]
                self.assertEqual(transition["accepted_sha256"],
                                 actual["accepted_sha256"])
                self.assertEqual(transition["successor_sha256"],
                                 actual["successor_sha256"])
                self.assertEqual(
                    builder.SOURCES[
                        builder.SOURCE_SUCCESSOR_SOURCE_NAMES[relative]
                    ],
                    actual["successor_authority"],
                )
                self.assertTrue(actual["transition_fixed_by_this_contract"])
                self.assertFalse(
                    actual["successor_external_git_anchor_complete"]
                )

    def test_15_source_successor_api_rejects_unknown_tamper_and_symlink(self) -> None:
        for relative, transition in builder.SOURCE_SUCCESSORS.items():
            with self.subTest(relative=relative):
                node_c = operator_builder.SOURCE_TRANSITIONS.get(relative)
                node_d = node_d_acceptance.source_transition(ROOT, relative)
                self.assertEqual(
                    transition["accepted_sha256"],
                    acceptance.accepted_sha256(relative),
                )
                self.assertEqual(
                    (
                        transition["successor_sha256"]
                        if node_c is None
                        else (
                            node_c["successor_sha256"]
                            if node_d is None
                            else node_d["successor_sha256"]
                        )
                    ),
                    acceptance.successor_sha256(ROOT, relative),
                )
                if node_c is not None:
                    self.assertEqual(
                        transition["successor_sha256"],
                        node_c["accepted_sha256"],
                    )
                if node_d is not None:
                    self.assertIsNotNone(node_c)
                    self.assertEqual(
                        node_c["successor_sha256"],
                        node_d["accepted_sha256"],
                    )
        self.assertIsNone(acceptance.accepted_sha256("tools/unknown.py"))
        self.assertIsNone(acceptance.successor_sha256(ROOT, "tools/unknown.py"))

        temporary, root = self._minimal_copy()
        with temporary:
            relative = "infra/phase2/README.md"
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                AssertionError,
                "fixed source bytes|fixed bytes|source-successor bytes",
            ):
                acceptance.successor_sha256(root, relative)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.py"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.successor_sha256(root, relative)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = (
                "tools/test_phase4c_personal_bank_user_counts_"
                "http_entry_contract.py"
            )
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                AssertionError,
                "fixed source bytes|fixed bytes|source-successor bytes",
            ):
                acceptance.successor_sha256(root, relative)

    def test_16_historical_acceptance_authorities_fix_both_bridge_layers(
        self,
    ) -> None:
        typed = builder._validated_json(ROOT, "typed_anchor_contract")
        typed_overrides = typed["historical_source_successors"]["overrides"]
        for relative, expected in builder.TYPED_PHASE2_SOURCE_SUCCESSORS.items():
            self.assertEqual(
                expected["accepted_sha256"],
                typed_overrides[relative]["successor_sha256"],
            )
            self.assertEqual(
                expected["accepted_byte_count"],
                typed_overrides[relative]["successor_byte_count"],
            )

        phase6 = builder._validated_json(
            ROOT, "phase6_source_successor_anchor_contract"
        )
        bridge_artifacts = phase6["typed_anchor_bridge_source_anchor"][
            "artifacts"
        ]
        for relative, expected in (
            builder.PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS.items()
        ):
            self.assertEqual(
                expected["accepted_sha256"], bridge_artifacts[relative]["sha256"]
            )
            self.assertEqual(
                expected["accepted_byte_count"],
                bridge_artifacts[relative]["byte_count"],
            )

    def test_17_bridge_overclaim_and_descriptor_tamper_are_rejected(self) -> None:
        changed = deepcopy(self.contract)
        changed["source_successor_bridges"][
            "source_successor_external_git_anchor_complete"
        ] = True
        with self.assertRaisesRegex(AssertionError, "payload|source-successor"):
            acceptance.validate(changed, ROOT)

        changed = deepcopy(self.contract)
        changed["source_successor_bridges"]["overrides"][
            "infra/phase2/README.md"
        ]["successor_sha256"] = "f" * 64
        with self.assertRaisesRegex(AssertionError, "payload|source-successor"):
            acceptance.validate(changed, ROOT)

    def test_18_builder_remains_one_way_and_fixture_is_literal(self) -> None:
        source = (
            ROOT / "tools/build_phase4c_tag_migration_global_preflight_contract.py"
        ).read_text(encoding="utf-8")
        self.assertIn("validate_evidence_chain", source)
        self.assertNotIn("validate_fixed_acceptance", source)
        self.assertNotIn(
            "from tools import "
            "phase4c_tag_migration_global_preflight_successor_acceptance",
            source,
        )
        self.assertNotIn(
            "importlib.import_module("
            "TAG_GLOBAL_PREFLIGHT_SUCCESSOR_MODULE",
            source,
        )
        fixtures = set(acceptance.minimal_fixture_paths())
        self.assertIn(acceptance.CONTRACT_RELATIVE, fixtures)
        self.assertTrue(set(builder.SOURCE_SUCCESSORS).issubset(fixtures))
        self.assertTrue(
            {descriptor["source"] for descriptor in builder.SOURCES.values()}
            .issubset(fixtures)
        )

    def test_19_fixed_semantic_successors_cover_runtime_main_and_worm_tip(
        self,
    ) -> None:
        historical = builder._validated_json(
            ROOT, "historical_target_execution_contract"
        )["production_surface"]["files"]
        current = dict(historical)
        current.update(builder.PRODUCTION_MANIFEST_ADDITIONS)
        runtime = acceptance.validate_production_runtime_successor(
            ROOT, historical, current
        )
        self.assertEqual(297, runtime.accepted_file_count)
        self.assertEqual(300, runtime.current_file_count)
        self.assertEqual(
            builder.SUCCESSOR_PRODUCTION_MANIFEST_SHA256,
            runtime.current_manifest_sha256,
        )
        self.assertEqual(3, len(runtime.added_files))
        self.assertEqual((), runtime.changed_files)
        self.assertEqual((), runtime.deleted_files)

        node_c_current = dict(current)
        node_c_current.update(operator_builder.PRODUCTION_RUNTIME_ADDITIONS)
        node_c_current.update(operator_builder.PRODUCTION_RUNTIME_CHANGES)
        node_d_current = node_d_runtime(node_c_current, ROOT)
        composed = acceptance.validate_production_runtime_successor(
            ROOT, historical, node_d_current
        )
        self.assertEqual(297, composed.accepted_file_count)
        self.assertEqual(311, composed.current_file_count)
        self.assertEqual(
            builder.sha256_bytes(
                builder.canonical_json(node_d_current).encode("utf-8")
            ),
            composed.current_manifest_sha256,
        )
        self.assertEqual(14, len(composed.added_files))
        self.assertEqual((), composed.changed_files)
        self.assertEqual((), composed.deleted_files)

        prefixes = (
            "server/src/main/java/io/saksk/ti/learning/",
            "server/src/main/java/io/saksk/ti/personalbank/",
        )
        historical_main = {
            relative: digest
            for relative, digest in historical.items()
            if relative.startswith(prefixes)
        }
        current_main = {
            relative: digest
            for relative, digest in current.items()
            if relative.startswith(prefixes)
        }
        main = acceptance.validate_production_runtime_successor(
            ROOT,
            historical_main,
            current_main,
            view="learning_personalbank_main",
        )
        self.assertEqual(40, main.accepted_file_count)
        self.assertEqual(43, main.current_file_count)
        self.assertEqual(
            builder.SUCCESSOR_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256,
            main.current_manifest_sha256,
        )
        node_c_current_main = {
            relative: digest
            for relative, digest in node_d_current.items()
            if relative.startswith(prefixes)
        }
        composed_main = acceptance.validate_production_runtime_successor(
            ROOT,
            historical_main,
            node_c_current_main,
            view="learning_personalbank_main",
        )
        self.assertEqual(40, composed_main.accepted_file_count)
        self.assertEqual(54, composed_main.current_file_count)
        self.assertEqual(
            builder.sha256_bytes(
                builder.canonical_json(node_c_current_main).encode("utf-8")
            ),
            composed_main.current_manifest_sha256,
        )

        worm = acceptance.validate_worm_successor(
            ROOT,
            builder.SOURCES["old_worm_predecessor"]["sha256"],
            builder.HISTORICAL_BUILD_CONTEXT_SHA256,
        )
        self.assertEqual(5, worm.accepted_chain_node_count)
        self.assertEqual(6, worm.first_successor_chain_node_count)
        self.assertEqual(9, worm.current_chain_node_count)
        self.assertNotEqual(
            operator_builder.CURRENT_BUILD_CONTEXT_SHA256,
            worm.current_build_context_sha256,
        )
        self.assertNotEqual(
            operator_builder.WORM_SHA256,
            worm.current_report_sha256,
        )
        semantic_fixtures = set(acceptance.semantic_fixture_paths(ROOT))
        self.assertIn(
            "infra/phase2/hash-java-build-context.sh", semantic_fixtures
        )
        self.assertTrue(
            set(builder.PRODUCTION_MANIFEST_ADDITIONS).issubset(
                semantic_fixtures
            )
        )
        self.assertIn("server/Dockerfile", semantic_fixtures)
        self.assertIn("server/pom.xml", semantic_fixtures)

        with self.assertRaisesRegex(AssertionError, "unknown production view"):
            acceptance.validate_production_runtime_successor(
                ROOT, historical, current, view="unknown"
            )
        changed = dict(current)
        changed[next(iter(changed))] = "f" * 64
        with self.assertRaisesRegex(AssertionError, "current production manifest"):
            acceptance.validate_production_runtime_successor(
                ROOT, historical, changed
            )
        with self.assertRaisesRegex(AssertionError, "WORM successor"):
            acceptance.validate_worm_successor(
                ROOT, "f" * 64, builder.HISTORICAL_BUILD_CONTEXT_SHA256
            )

    def test_20_gitless_semantic_fixture_executes_both_views_and_worm(
        self,
    ) -> None:
        temporary, root = self._semantic_copy()
        with temporary:
            self.assertFalse((Path(temporary.name) / ".git").exists())
            historical = builder._validated_json(
                root, "historical_target_execution_contract"
            )["production_surface"]["files"]
            current = dict(historical)
            current.update(builder.PRODUCTION_MANIFEST_ADDITIONS)
            current.update(operator_builder.PRODUCTION_RUNTIME_ADDITIONS)
            current.update(operator_builder.PRODUCTION_RUNTIME_CHANGES)
            current = node_d_runtime(current, root)
            runtime = acceptance.validate_production_runtime_successor(
                root, historical, current
            )
            self.assertEqual((297, 311), (
                runtime.accepted_file_count,
                runtime.current_file_count,
            ))

            prefixes = (
                "server/src/main/java/io/saksk/ti/learning/",
                "server/src/main/java/io/saksk/ti/personalbank/",
            )
            historical_main = {
                relative: digest
                for relative, digest in historical.items()
                if relative.startswith(prefixes)
            }
            current_main = {
                relative: digest
                for relative, digest in current.items()
                if relative.startswith(prefixes)
            }
            main = acceptance.validate_production_runtime_successor(
                root,
                historical_main,
                current_main,
                view="learning_personalbank_main",
            )
            self.assertEqual((40, 54), (
                main.accepted_file_count,
                main.current_file_count,
            ))
            worm = acceptance.validate_worm_successor(
                root,
                builder.SOURCES["old_worm_predecessor"]["sha256"],
                builder.HISTORICAL_BUILD_CONTEXT_SHA256,
            )
            self.assertEqual((5, 6, 9), (
                worm.accepted_chain_node_count,
                worm.first_successor_chain_node_count,
                worm.current_chain_node_count,
            ))

        temporary, root = self._semantic_copy()
        with temporary:
            (root / "infra/phase2/hash-java-build-context.sh").unlink()
            with self.assertRaises(FileNotFoundError):
                acceptance.validate_worm_successor(
                    root,
                    builder.SOURCES["old_worm_predecessor"]["sha256"],
                    builder.HISTORICAL_BUILD_CONTEXT_SHA256,
                )

        temporary, root = self._semantic_copy()
        with temporary:
            (root / "server/pom.xml").unlink()
            with self.assertRaisesRegex(
                AssertionError, "physical build-context successor drifted"
            ):
                acceptance.validate_worm_successor(
                    root,
                    builder.SOURCES["old_worm_predecessor"]["sha256"],
                    builder.HISTORICAL_BUILD_CONTEXT_SHA256,
                )

        temporary, root = self._semantic_copy()
        with temporary:
            candidates = (
                relative
                for relative in acceptance.semantic_fixture_paths(ROOT)
                if relative.startswith("server/src/main/java/")
                and relative not in builder.PRODUCTION_MANIFEST_ADDITIONS
                and relative not in {
                    descriptor["source"]
                    for descriptor in builder.SOURCES.values()
                }
            )
            tampered = root / next(candidates)
            tampered.write_bytes(tampered.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                AssertionError,
                (
                    "operator-core fixed source bytes drifted|"
                    "operator-core unreviewed physical source drift|"
                    "physical build-context successor drifted"
                ),
            ):
                acceptance.validate_worm_successor(
                    root,
                    builder.SOURCES["old_worm_predecessor"]["sha256"],
                    builder.HISTORICAL_BUILD_CONTEXT_SHA256,
                )


if __name__ == "__main__":
    unittest.main()
