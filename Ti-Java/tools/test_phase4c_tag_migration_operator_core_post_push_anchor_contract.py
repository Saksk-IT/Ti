#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C operator-core C2 post-push anchor."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

try:
    from tools import (
        build_phase4c_tag_migration_operator_core_post_push_anchor_contract
        as builder,
    )
    from tools import (
        phase4c_tag_migration_operator_core_post_push_anchor_successor_acceptance
        as acceptance,
    )
    from tools import (
        phase4c_tag_migration_execution_protocol_successor_acceptance
        as execution_protocol_successor,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import build_phase4c_tag_migration_operator_core_post_push_anchor_contract \
        as builder
    import phase4c_tag_migration_operator_core_post_push_anchor_successor_acceptance \
        as acceptance
    import phase4c_tag_migration_execution_protocol_successor_acceptance \
        as execution_protocol_successor


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class OperatorCorePostPushAnchorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = (ROOT / builder.OUTPUT_RELATIVE).read_bytes()
        cls.contract = acceptance.load_contract(ROOT)

    @staticmethod
    def _fixture(temporary: Path) -> Path:
        fixture = temporary / "Ti-Java"
        fixture.mkdir()
        for relative in acceptance.minimal_fixture_paths():
            source = ROOT / relative
            target = fixture / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return fixture

    def test_01_checked_in_bytes_match_gitless_builder_and_acceptance(self) -> None:
        built = builder.build_contract(ROOT, repository_root=None)
        payload = builder.serialized_contract(built)
        self.assertEqual(self.contract, built)
        self.assertEqual(self.payload, payload)
        self.assertEqual(acceptance.EXPECTED_CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(
            acceptance.EXPECTED_CONTRACT_SHA256,
            hashlib.sha256(payload).hexdigest(),
        )
        self.assertEqual(
            acceptance.EXPECTED_DOCUMENT_PAYLOAD_SHA256,
            built["document_payload_sha256"],
        )

    def test_02_minimal_fixture_is_gitless_and_never_runs_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            self.assertFalse((Path(temporary) / ".git").exists())
            with mock.patch(
                "subprocess.run",
                side_effect=AssertionError("ordinary load attempted subprocess"),
            ):
                self.assertEqual(
                    self.contract,
                    builder.build_contract(fixture, repository_root=None),
                )
                self.assertEqual(self.contract, acceptance.load_contract(fixture))

    def test_03_c0_is_exact_56_with_22_additions_and_34_modifications(self) -> None:
        checkpoint = self.contract["implementation_checkpoint"]
        artifacts = checkpoint["artifacts"]
        self.assertEqual(builder.C0_COMMIT, checkpoint["commit_oid"])
        self.assertEqual(builder.C0_PARENT, checkpoint["parent_oid"])
        self.assertEqual(56, checkpoint["changed_path_count"])
        self.assertEqual(22, checkpoint["added_count"])
        self.assertEqual(34, checkpoint["modified_count"])
        self.assertEqual(0, checkpoint["deleted_count"])
        self.assertEqual(builder.C0_CHANGES, artifacts)
        self.assertEqual(22, sum(
            item["change_type"] == "A" for item in artifacts.values()
        ))
        self.assertEqual(34, sum(
            item["change_type"] == "M" for item in artifacts.values()
        ))

    def test_04_c0_authority_is_exact_7_plus_49_with_34_overrides(self) -> None:
        anchor = self.contract["operator_core_authority_anchor"]
        controls = set(anchor["implementation_control_sources"])
        fixed = set(anchor["implementation_fixed_non_control_sources"])
        transitions = set(anchor["implementation_transition_sources"])
        self.assertEqual(set(builder.C0_CONTROL_SOURCES), controls)
        self.assertEqual(7, len(controls))
        self.assertEqual(49, len(fixed))
        self.assertFalse(controls & fixed)
        self.assertEqual(set(builder.C0_CHANGES), controls | fixed)
        self.assertEqual(34, len(transitions))
        self.assertEqual(
            transitions,
            {path for path, item in builder.C0_CHANGES.items()
             if item["change_type"] == "M"},
        )
        self.assertEqual(
            "f9098c90c9ea2d75f3b5f2d08bb84ac075015c8f1b30160dd475d0d6d6e96f22",
            anchor["implementation_control_path_manifest_sha256"],
        )
        self.assertEqual(
            "a0b3742d34ff42cffe2b903644876bb2d6e4db55ffba9639125fa89376d0b376",
            anchor["implementation_fixed_manifest_sha256"],
        )
        self.assertEqual(
            "cd7f19edd049c676de69cd2572a45c6c6235dfc7a6ac1a57248c7e508dae5487",
            anchor["implementation_transition_manifest_sha256"],
        )

    def test_05_all_34_overrides_bind_parent_and_successor_bytes(self) -> None:
        operator = json.loads(
            (ROOT / builder.OPERATOR_CONTRACT_RELATIVE).read_bytes()
        )
        overrides = operator["historical_source_successors"]["overrides"]
        artifacts = self.contract["implementation_checkpoint"]["artifacts"]
        self.assertEqual(34, len(overrides))
        for relative, override in overrides.items():
            with self.subTest(relative=relative):
                item = artifacts[relative]
                self.assertEqual("M", item["change_type"])
                self.assertEqual(
                    override["accepted_sha256"], item["previous_sha256"]
                )
                self.assertEqual(
                    override["accepted_byte_count"],
                    item["previous_byte_count"],
                )
                self.assertEqual(override["successor_sha256"], item["sha256"])
                self.assertEqual(
                    override["successor_byte_count"], item["byte_count"]
                )

    def test_06_c1_is_exactly_two_additions_with_fixed_modes(self) -> None:
        checkpoint = self.contract["independent_acceptance_checkpoint"]
        artifacts = checkpoint["artifacts"]
        self.assertEqual(builder.C1_COMMIT, checkpoint["commit_oid"])
        self.assertEqual(builder.C0_COMMIT, checkpoint["parent_oid"])
        self.assertEqual(2, checkpoint["changed_path_count"])
        self.assertEqual(2, checkpoint["added_count"])
        self.assertEqual(0, checkpoint["modified_count"])
        self.assertEqual(0, checkpoint["deleted_count"])
        self.assertEqual(builder.C1_CHANGES, artifacts)
        self.assertEqual("100644", artifacts[builder.EVIDENCE_RELATIVE]["mode"])
        self.assertEqual("100755", artifacts[builder.RUNNER_RELATIVE]["mode"])

    def test_07_evidence_and_runner_cross_anchor_is_exact(self) -> None:
        evidence = self.contract["independent_acceptance_evidence"]
        runner = evidence["runner"]
        artifacts = self.contract["independent_acceptance_checkpoint"][
            "artifacts"
        ]
        self.assertEqual(
            artifacts[builder.EVIDENCE_RELATIVE]["sha256"], evidence["sha256"]
        )
        self.assertEqual(
            artifacts[builder.EVIDENCE_RELATIVE]["byte_count"],
            evidence["byte_count"],
        )
        self.assertEqual(
            artifacts[builder.RUNNER_RELATIVE]["sha256"], runner["sha256"]
        )
        self.assertEqual(
            artifacts[builder.RUNNER_RELATIVE]["byte_count"],
            runner["byte_count"],
        )
        self.assertEqual(
            artifacts[builder.RUNNER_RELATIVE]["mode"], runner["git_mode"]
        )
        self.assertFalse(evidence["raw_report_required_for_gitless_build"])
        self.assertFalse(runner["raw_report"]["tracked"])
        self.assertFalse(runner["raw_report"]["embedded"])

    def test_08_only_58_checkpoint_paths_are_accepted(self) -> None:
        expected = set(builder.C0_CHANGES) | set(builder.C1_CHANGES)
        self.assertEqual(58, len(expected))
        self.assertEqual(expected, set(acceptance.checkpoint_paths()))
        for relative in expected:
            with self.subTest(relative=relative):
                descriptor = (
                    builder.C0_CHANGES.get(relative)
                    or builder.C1_CHANGES[relative]
                )
                transition = execution_protocol_successor.source_transition(
                    ROOT, relative
                )
                if transition is None:
                    self.assertEqual(
                        descriptor["sha256"],
                        acceptance.accepted_sha256(ROOT, relative),
                    )
                else:
                    self.assertIsNone(
                        acceptance.accepted_sha256(ROOT, relative)
                    )
                    self.assertEqual(
                        descriptor["sha256"], transition["accepted_sha256"]
                    )
                    self.assertEqual(
                        descriptor["byte_count"],
                        transition["accepted_byte_count"],
                    )
        self.assertIsNone(acceptance.accepted_sha256(ROOT, "tools/unknown.py"))
        for relative in builder.CURRENT_CONTROL_SOURCES:
            self.assertIsNone(acceptance.accepted_sha256(ROOT, relative))

    def test_09_six_c2_controls_are_exact_and_self_excluded(self) -> None:
        current = self.contract["current_node_trust_boundary"]
        self.assertEqual(list(builder.CURRENT_CONTROL_SOURCES), current["control_sources"])
        self.assertEqual(6, current["control_source_count"])
        self.assertTrue(current["control_sources_excluded_from_self_authority"])
        self.assertFalse(current["control_sources_external_git_anchor_complete"])
        self.assertFalse(current["c2_commit_or_tree_identity_embedded"])
        anchored = set(builder.C0_CHANGES) | set(builder.C1_CHANGES)
        self.assertFalse(set(builder.CURRENT_CONTROL_SOURCES) & anchored)
        serialized = self.payload.decode("utf-8")
        for relative in builder.CURRENT_CONTROL_SOURCES:
            path = ROOT / relative
            if path.is_file():
                self.assertNotIn(
                    hashlib.sha256(path.read_bytes()).hexdigest(), serialized
                )

    def test_09b_transitive_node_b_predecessor_anchor_remains_fixed(self) -> None:
        transitive = self.contract["transitive_node_b_anchor"]
        predecessor = transitive["predecessor"]
        git = transitive["git_authority"]
        checkpoint = git["external_anchor_checkpoint"]
        self.assertTrue(transitive["immutable"])
        self.assertEqual(
            "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6",
            predecessor["sha256"],
        )
        self.assertEqual(15_550, predecessor["byte_count"])
        self.assertEqual(
            "bbeb08efcccb0b9974dfefa2044aab43e0675f6f",
            checkpoint["commit_oid"],
        )
        self.assertEqual(6, checkpoint["changed_path_count"])
        self.assertEqual(6, git["external_anchor_artifact_count"])
        self.assertEqual(6, len(git["external_anchor_artifacts"]))
        self.assertFalse(git["ordinary_build_and_load_require_git"])
        self.assertFalse(git["live_head_main_or_origin_authority"])

    def test_10_source_discovery_and_original_evidence_remain_conservative(self) -> None:
        verification = self.contract["independent_copy_verification"]
        source = verification["verification"]["source_discovery"]
        closure = verification["original_closure"]
        self.assertFalse(source["executed_inside_independent_copy"])
        self.assertEqual(0, source["claimed_independent_copy_test_count"])
        self.assertTrue(closure["fixed_c0_independent_copy_acceptance_closed"])
        self.assertEqual(builder.C0_COMMIT, closure["proves_only_commit"])
        self.assertFalse(closure["proves_c1_evidence_commit"])
        self.assertFalse(closure["proves_c2_anchor_commit"])
        self.assertFalse(closure["self_hash_embedded"])

    def test_11_route_and_production_boundaries_are_conservative(self) -> None:
        self.assertEqual(builder.ROUTE_STATE, self.contract["route_state"])
        authorization = self.contract["authorization"]
        for field in builder.PRODUCTION_FALSE_FIELDS:
            self.assertFalse(authorization[field], field)
        self.assertFalse(
            authorization["current_node_control_sources_external_git_anchor_complete"]
        )
        production = self.contract["production_and_worm_boundary"]
        for field in (
            "production_schema_or_index_added",
            "production_connection_or_credentials_used",
            "production_data_read_or_mutated",
            "production_operator_executed",
            "user_compose_or_production_docker_mutated",
        ):
            self.assertFalse(production[field], field)
        self.assertTrue(self.contract["acceptance"]["anchor_closes_no_functional_gate"])
        self.assertFalse(self.contract["acceptance"]["c2_self_anchor_complete"])

    def test_12_fixed_inputs_and_contract_tamper_fail_closed(self) -> None:
        for relative in acceptance.minimal_fixture_paths():
            with self.subTest(relative=relative):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._fixture(Path(temporary))
                    target = fixture / relative
                    target.write_bytes(target.read_bytes() + b"\n")
                    with self.assertRaises(AssertionError):
                        acceptance.load_contract(fixture)

    def test_13_runner_mode_and_symlink_escape_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            runner = fixture / builder.RUNNER_RELATIVE
            runner.chmod(0o644)
            with self.assertRaisesRegex(AssertionError, "runner identity"):
                acceptance.load_contract(fixture)
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            target = fixture / builder.EVIDENCE_RELATIVE
            real = target.with_suffix(".real")
            target.rename(real)
            target.symlink_to(real)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load_contract(fixture)

    def test_14_semantic_overclaims_and_artifact_tamper_fail_closed(self) -> None:
        mutations = (
            ("authorization", "production_schema_or_index", True),
            ("authorization", "production_cutover", True),
            ("route_state", "migrated_operation_count", 14),
            ("current_node_trust_boundary",
             "control_sources_external_git_anchor_complete", True),
            ("acceptance", "c2_self_anchor_complete", True),
        )
        for section, key, value in mutations:
            with self.subTest(section=section, key=key):
                changed = deepcopy(self.contract)
                changed[section][key] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed)
        relative = next(iter(builder.C0_CHANGES))
        for key, value in (
            ("sha256", "0" * 64),
            ("byte_count", 1),
            ("mode", "100755"),
            ("repository_path", "Ti-Java/tools/other.py"),
        ):
            with self.subTest(artifact_key=key):
                changed = deepcopy(self.contract)
                changed["implementation_checkpoint"]["artifacts"][relative][key] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed)

    def test_15_acceptance_replays_both_checkpoints_without_builder_replay(self) -> None:
        with mock.patch.object(
            builder,
            "validate_fixed_git_checkpoints",
            side_effect=AssertionError("builder replay must not be called"),
        ):
            acceptance.validate_fixed_git_checkpoints(REPOSITORY_ROOT)

    def test_16_fixed_git_replay_is_read_only_and_rejects_live_refs(self) -> None:
        for ref in ("HEAD", "main", "origin/main", "@", "--all"):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(AssertionError, "live"):
                    acceptance._run_fixed_git(REPOSITORY_ROOT, "show", ref)
        observed: list[tuple[tuple[object, ...], dict[str, object]]] = []
        real_run = acceptance.subprocess.run

        def recording_run(*args: object, **kwargs: object) -> object:
            observed.append((args, kwargs))
            return real_run(*args, **kwargs)

        with mock.patch.object(
            acceptance.subprocess, "run", side_effect=recording_run
        ):
            acceptance.validate_fixed_git_checkpoints(REPOSITORY_ROOT)
        self.assertTrue(observed)
        for args, kwargs in observed:
            command = tuple(args[0])
            self.assertEqual(("git", "--no-optional-locks"), command[:2])
            self.assertFalse(
                {"HEAD", "main", "origin/main", "add", "commit", "push",
                 "update-ref"} & set(command)
            )
            self.assertEqual(30, kwargs["timeout"])
            environment = kwargs["env"]
            self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
            self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])

    def test_17_no_dynamic_discovery_or_live_ref_primitive_is_present(self) -> None:
        for relative in (
            "tools/build_phase4c_tag_migration_operator_core_post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_operator_core_post_push_anchor_successor_acceptance.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            for forbidden in (
                ".glob(", ".rglob(", "os.walk(", "git ls-files",
                '"rev-parse", "HEAD"', '"show", "HEAD"',
            ):
                self.assertNotIn(forbidden, source, (relative, forbidden))


if __name__ == "__main__":
    unittest.main()
