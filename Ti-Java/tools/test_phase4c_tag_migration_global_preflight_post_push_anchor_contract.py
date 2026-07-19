#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C tag-preflight Node A Git anchor."""

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
        build_phase4c_tag_migration_global_preflight_post_push_anchor_contract
        as builder,
    )
    from tools import (
        phase4c_tag_migration_global_preflight_post_push_anchor_successor_acceptance
        as acceptance,
    )
except ModuleNotFoundError:
    import build_phase4c_tag_migration_global_preflight_post_push_anchor_contract \
        as builder
    import phase4c_tag_migration_global_preflight_post_push_anchor_successor_acceptance \
        as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class Phase4cTagMigrationGlobalPreflightPostPushAnchorContractTest(
        unittest.TestCase):

    def setUp(self) -> None:
        self.contract = acceptance.load(ROOT)

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "Ti-Java"
        root.mkdir()
        for relative in acceptance.minimal_fixture_paths():
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return temporary, root

    def test_01_builder_acceptance_and_checked_in_bytes_match(self) -> None:
        built = builder.build_contract(ROOT, repository_root=None)
        self.assertEqual(self.contract, built)
        payload = builder.serialized_contract(built)
        self.assertEqual(acceptance.CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(acceptance.CONTRACT_SHA256,
                         hashlib.sha256(payload).hexdigest())
        self.assertEqual(acceptance.CONTRACT_PAYLOAD_SHA256,
                         built["document_payload_sha256"])
        self.assertEqual(payload, (ROOT / acceptance.CONTRACT_RELATIVE).read_bytes())

    def test_02_both_independent_git_replays_fix_commit_and_blobs(self) -> None:
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        predecessor = builder._read_fixed_predecessor(ROOT)
        builder.validate_node_a_fixed_sources_at_checkpoint(
            REPOSITORY_ROOT, predecessor
        )
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)

    def test_03_exact_63_path_checkpoint_and_tree_facts_are_fixed(self) -> None:
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual("256d5b347e2e5266eef084221807337427ceb16f",
                         checkpoint["commit_oid"])
        self.assertEqual("08328c3fe18e074f581bb9e782ee4ae86cf46c53",
                         checkpoint["parent_oid"])
        self.assertEqual("efcd304e85f597ac22840110630d9fc0ae9a8fb0",
                         checkpoint["root_tree_oid"])
        self.assertEqual("e47d851f451fdf045d2c456065ae6913c69229d2",
                         checkpoint["ti_java_tree_oid"])
        self.assertEqual("0adfaa0bf6e0edeba2aceebce6c267421e3b8144",
                         checkpoint["server_tree_oid"])
        self.assertEqual("21fe4902d57a11998502e63041b5a56fb039a090",
                         checkpoint["server_src_main_tree_oid"])
        self.assertEqual("a75f69a8205a56843feb055656ddb015ec5b5215",
                         checkpoint["web_tree_oid"])
        self.assertEqual(63, checkpoint["changed_path_count"])
        self.assertEqual(17, checkpoint["added_count"])
        self.assertEqual(46, checkpoint["modified_count"])
        self.assertEqual(0, checkpoint["deleted_count"])
        self.assertEqual(63, len(checkpoint["artifacts"]))
        self.assertEqual(set(builder.CHECKPOINT_PATHS),
                         set(checkpoint["artifacts"]))

    def test_04_node_a_authority_sets_and_partition_are_exact(self) -> None:
        node = self.contract["node_a_authority_anchor"]
        transitions = set(node["source_successor_paths"])
        semantic = set(node["semantic_consumer_paths"])
        fixed = set(node["fixed_source_paths"])
        controls = set(node["control_sources"])
        delta = set(self.contract["git_checkpoint"]["artifacts"])
        self.assertEqual(42, len(transitions))
        self.assertEqual(26, len(semantic))
        self.assertEqual(72, len(fixed))
        self.assertEqual(11, len(controls))
        self.assertLess(semantic, transitions)
        self.assertFalse(controls & transitions)
        self.assertFalse(controls & fixed)
        self.assertEqual(delta, controls | (delta & fixed))
        self.assertEqual(52, len(delta & fixed))
        self.assertEqual(20, len(fixed - delta))
        partition = node["delta_partition"]
        self.assertEqual(42, partition["changed_fixed_modified_count"])
        self.assertEqual(1_697_108,
                         partition["transition_accepted_total_bytes"])
        self.assertEqual(1_777_881,
                         partition["transition_current_total_bytes"])
        self.assertEqual(1_137_011,
                         partition["semantic_accepted_total_bytes"])
        self.assertEqual(1_179_001,
                         partition["semantic_current_total_bytes"])
        self.assertTrue(partition["exact_disjoint_partition"])

    def test_05_all_42_parent_to_current_transitions_match_predecessor(self) -> None:
        predecessor = json.loads(
            (ROOT / acceptance.PREDECESSOR_RELATIVE).read_bytes()
        )
        overrides = predecessor["source_successor_bridges"]["overrides"]
        artifacts = self.contract["git_checkpoint"]["artifacts"]
        for relative in self.contract["node_a_authority_anchor"][
                "source_successor_paths"]:
            with self.subTest(relative=relative):
                artifact = artifacts[relative]
                override = overrides[relative]
                self.assertEqual("M", artifact["change_type"])
                self.assertEqual(override["successor_sha256"],
                                 artifact["sha256"])
                self.assertEqual(override["successor_byte_count"],
                                 artifact["byte_count"])

    def test_06_six_current_controls_are_exact_and_self_excluded(self) -> None:
        trust = self.contract["current_node_trust_boundary"]
        self.assertEqual(list(acceptance.CURRENT_CONTROL_SOURCES),
                         trust["control_sources"])
        self.assertEqual(6, trust["control_source_count"])
        self.assertTrue(trust["control_sources_excluded_from_self_authority"])
        self.assertFalse(trust["control_sources_external_git_anchor_complete"])
        authority_paths = set(
            self.contract["node_a_authority_anchor"]["source_successor_paths"]
        ) | set(self.contract["node_a_authority_anchor"]["fixed_source_paths"]) \
            | set(self.contract["node_a_authority_anchor"]["control_sources"])
        self.assertFalse(set(acceptance.CURRENT_CONTROL_SOURCES) & authority_paths)
        serialized = builder.serialized_contract(self.contract).decode("utf-8")
        for relative in acceptance.CURRENT_CONTROL_SOURCES:
            with self.subTest(relative=relative):
                physical = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
                self.assertNotIn(physical, serialized)

    def test_07_gitless_minimal_fixture_builds_and_loads_without_subprocess(
            self) -> None:
        temporary, root = self._fixture()
        with temporary, mock.patch(
                "subprocess.run",
                side_effect=AssertionError("ordinary path attempted Git")):
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertEqual(self.contract,
                             builder.build_contract(root, repository_root=None))
        self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_08_fixed_contract_and_predecessor_tamper_fail_closed(self) -> None:
        for relative in acceptance.minimal_fixture_paths():
            with self.subTest(relative=relative):
                temporary, root = self._fixture()
                with temporary:
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\n")
                    with self.assertRaisesRegex(AssertionError, "fixed bytes"):
                        acceptance.load(root)

    def test_09_symlink_escape_and_unknown_paths_fail_closed(self) -> None:
        temporary, root = self._fixture()
        with temporary:
            relative = acceptance.PREDECESSOR_RELATIVE
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.json"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)
        for relative in ("../README.md", "/tmp/README.md"):
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(AssertionError, "escapes root"):
                    acceptance._fixed_regular_file(ROOT, relative)
        self.assertIsNone(acceptance.accepted_sha256("tools/unknown.py"))

    def test_10_overclaims_and_manifest_mutations_fail_closed(self) -> None:
        mutations = (
            ("authorization", "migration_design_closed", True),
            ("authorization", "operator_migration_implementation", True),
            ("authorization", "production_schema_or_index", True),
            ("authorization", "real_data_migration_execution", True),
            ("authorization", "production_cutover", True),
            ("route_state", "migrated_operation_count", 14),
            ("node_a_authority_anchor", "fixed_source_count", 71),
        )
        for section, key, value in mutations:
            with self.subTest(section=section, key=key):
                mutated = deepcopy(self.contract)
                mutated[section][key] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate(mutated, ROOT)

    def test_11_artifact_metadata_tamper_fails_closed(self) -> None:
        relative = next(iter(
            self.contract["git_checkpoint"]["artifacts"]
        ))
        for key, value in (
            ("sha256", "0" * 64),
            ("byte_count", 1),
            ("mode", "100755"),
            ("repository_path", "Ti-Java/tools/other.py"),
        ):
            with self.subTest(key=key):
                mutated = deepcopy(self.contract)
                mutated["git_checkpoint"]["artifacts"][relative][key] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate(mutated, ROOT)

    def test_12_git_replay_is_read_only_fixed_and_bounded(self) -> None:
        observed: list[tuple[tuple[object, ...], dict[str, object]]] = []
        real_run = acceptance.subprocess.run

        def recording_run(*args: object, **kwargs: object) -> object:
            observed.append((args, kwargs))
            return real_run(*args, **kwargs)

        with mock.patch.object(acceptance.subprocess, "run",
                               side_effect=recording_run):
            acceptance.validate_git_checkpoint(REPOSITORY_ROOT)
        self.assertTrue(observed)
        for args, kwargs in observed:
            command = tuple(args[0])
            self.assertEqual("git", command[0])
            self.assertEqual("--no-optional-locks", command[1])
            self.assertNotIn("HEAD", command)
            self.assertNotIn("origin/main", command)
            self.assertFalse({"add", "commit", "push", "update-ref"} & set(command))
            self.assertEqual(30, kwargs["timeout"])
            environment = kwargs["env"]
            self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
            self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])

    def test_13_no_dynamic_discovery_primitive_is_present(self) -> None:
        for relative in (
            "tools/build_phase4c_tag_migration_global_preflight_"
            "post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
            "post_push_anchor_successor_acceptance.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertNotIn(".glob(", source)
                self.assertNotIn(".rglob(", source)
                self.assertNotIn("ls-files", source)
                self.assertNotIn('"rev-parse", "HEAD"', source)
                self.assertNotIn('"show", "HEAD"', source)
                self.assertNotIn('"origin/main"', source.replace(
                    '"origin/main", ', ""
                ))


if __name__ == "__main__":
    unittest.main()
