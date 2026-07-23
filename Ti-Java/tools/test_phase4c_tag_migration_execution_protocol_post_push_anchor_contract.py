#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C execution-protocol D2 post-push anchor."""

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
        build_phase4c_tag_migration_execution_protocol_post_push_anchor_contract
        as builder,
    )
    from tools import (
        phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance
        as acceptance,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import build_phase4c_tag_migration_execution_protocol_post_push_anchor_contract \
        as builder
    import phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance \
        as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class ExecutionProtocolPostPushAnchorContractTest(unittest.TestCase):
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

    def test_03_d0_is_exact_55_with_18_additions_and_37_modifications(self) -> None:
        checkpoint = self.contract["implementation_checkpoint"]
        artifacts = checkpoint["artifacts"]
        self.assertEqual(builder.D0_COMMIT, checkpoint["commit_oid"])
        self.assertEqual(builder.D0_PARENT, checkpoint["parent_oid"])
        self.assertEqual(55, checkpoint["changed_path_count"])
        self.assertEqual(18, checkpoint["added_count"])
        self.assertEqual(37, checkpoint["modified_count"])
        self.assertEqual(0, checkpoint["deleted_count"])
        self.assertEqual(builder.D0_CHANGES, artifacts)
        self.assertEqual(18, sum(
            item["change_type"] == "A" for item in artifacts.values()
        ))
        self.assertEqual(37, sum(
            item["change_type"] == "M" for item in artifacts.values()
        ))

    def test_04_d0_authority_is_exact_7_plus_48_with_37_overrides(self) -> None:
        anchor = self.contract["execution_protocol_authority_anchor"]
        controls = set(anchor["implementation_control_sources"])
        fixed = set(anchor["implementation_fixed_non_control_sources"])
        transitions = set(anchor["implementation_transition_sources"])
        self.assertEqual(set(builder.D0_CONTROL_SOURCES), controls)
        self.assertEqual(7, len(controls))
        self.assertEqual(48, len(fixed))
        self.assertFalse(controls & fixed)
        self.assertEqual(set(builder.D0_CHANGES), controls | fixed)
        self.assertEqual(37, len(transitions))
        self.assertEqual(
            transitions,
            {path for path, item in builder.D0_CHANGES.items()
             if item["change_type"] == "M"},
        )
        self.assertEqual(
            "b0d38af07b440adc413433c8307350fd135921117b42b0749d520ca26367e089",
            anchor["implementation_control_path_manifest_sha256"],
        )
        self.assertEqual(
            "f701ca15dc594369a43234f5b0615d6ad7d7e27a80e30c013002650084faefd7",
            anchor["implementation_fixed_manifest_sha256"],
        )
        self.assertEqual(
            "3a360d9e4c636b8c3e731bacd7d0598c75d73c1e77d18c013c7131569e16e6e3",
            anchor["implementation_transition_manifest_sha256"],
        )

    def test_05_all_37_overrides_bind_parent_and_successor_bytes(self) -> None:
        operator = json.loads(
            (ROOT / builder.EXECUTION_PROTOCOL_CONTRACT_RELATIVE).read_bytes()
        )
        overrides = operator["historical_source_successors"]["overrides"]
        artifacts = self.contract["implementation_checkpoint"]["artifacts"]
        self.assertEqual(37, len(overrides))
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

    def test_06_d1_is_exactly_two_additions_with_fixed_modes(self) -> None:
        checkpoint = self.contract["independent_acceptance_checkpoint"]
        artifacts = checkpoint["artifacts"]
        self.assertEqual(builder.D1_COMMIT, checkpoint["commit_oid"])
        self.assertEqual(builder.D0_COMMIT, checkpoint["parent_oid"])
        self.assertEqual(2, checkpoint["changed_path_count"])
        self.assertEqual(2, checkpoint["added_count"])
        self.assertEqual(0, checkpoint["modified_count"])
        self.assertEqual(0, checkpoint["deleted_count"])
        self.assertEqual(builder.D1_CHANGES, artifacts)
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

    def test_08_only_57_checkpoint_paths_are_accepted(self) -> None:
        expected = set(builder.D0_CHANGES) | set(builder.D1_CHANGES)
        self.assertEqual(57, len(expected))
        self.assertEqual(expected, set(acceptance.checkpoint_paths()))
        for relative in expected:
            with self.subTest(relative=relative):
                descriptor = (
                    builder.D0_CHANGES.get(relative)
                    or builder.D1_CHANGES[relative]
                )
                self.assertEqual(
                    descriptor["sha256"],
                    acceptance.accepted_sha256(ROOT, relative),
                )
        self.assertIsNone(acceptance.accepted_sha256(ROOT, "tools/unknown.py"))
        for relative in builder.CURRENT_CONTROL_SOURCES:
            self.assertIsNone(acceptance.accepted_sha256(ROOT, relative))

    def test_09_six_d2_controls_are_exact_and_self_excluded(self) -> None:
        current = self.contract["current_node_trust_boundary"]
        self.assertEqual(list(builder.CURRENT_CONTROL_SOURCES), current["control_sources"])
        self.assertEqual(6, current["control_source_count"])
        self.assertTrue(current["control_sources_excluded_from_self_authority"])
        self.assertFalse(current["control_sources_external_git_anchor_complete"])
        self.assertFalse(current["d2_commit_or_tree_identity_embedded"])
        anchored = set(builder.D0_CHANGES) | set(builder.D1_CHANGES)
        self.assertFalse(set(builder.CURRENT_CONTROL_SOURCES) & anchored)
        serialized = self.payload.decode("utf-8")
        for relative in builder.CURRENT_CONTROL_SOURCES:
            path = ROOT / relative
            if path.is_file():
                self.assertNotIn(
                    hashlib.sha256(path.read_bytes()).hexdigest(), serialized
                )

    def test_09b_transitive_node_c_predecessor_anchor_remains_fixed(self) -> None:
        transitive = self.contract["transitive_node_c_anchor"]
        predecessor = transitive["predecessor"]
        self.assertTrue(transitive["immutable"])
        self.assertEqual(
            "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936",
            predecessor["sha256"],
        )
        self.assertEqual(84_461, predecessor["byte_count"])
        self.assertEqual(
            "4c47d1ea220ae9e310338bbf23b74d87d477e20f",
            predecessor["fixed_commit_oid"],
        )
        self.assertEqual(
            "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64",
            predecessor["document_payload_sha256"],
        )
        self.assertTrue(predecessor["immutable"])

    def test_10_source_discovery_and_original_evidence_remain_conservative(self) -> None:
        verification = self.contract["independent_copy_verification"]
        source = verification["verification"]["source_discovery"]
        closure = verification["original_closure"]
        self.assertFalse(source["executed_inside_independent_copy"])
        self.assertEqual(0, source["claimed_independent_copy_test_count"])
        self.assertTrue(closure["fixed_d0_independent_copy_acceptance_closed"])
        self.assertEqual(builder.D0_COMMIT, closure["proves_only_commit"])
        self.assertFalse(closure["proves_d1_evidence_commit"])
        self.assertFalse(closure["proves_d2_anchor_commit"])
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
        self.assertFalse(self.contract["acceptance"]["d2_self_anchor_complete"])

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
            ("acceptance", "d2_self_anchor_complete", True),
        )
        for section, key, value in mutations:
            with self.subTest(section=section, key=key):
                changed = deepcopy(self.contract)
                changed[section][key] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed)
        relative = next(iter(builder.D0_CHANGES))
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
            "tools/build_phase4c_tag_migration_execution_protocol_post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_execution_protocol_post_push_anchor_successor_acceptance.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            for forbidden in (
                ".glob(", ".rglob(", "os.walk(", "git ls-files",
                '"rev-parse", "HEAD"', '"show", "HEAD"',
            ):
                self.assertNotIn(forbidden, source, (relative, forbidden))


if __name__ == "__main__":
    unittest.main()
