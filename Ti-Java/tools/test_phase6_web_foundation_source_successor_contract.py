#!/usr/bin/env python3
"""Fail-closed tests for the Phase 6 source-successor bootstrap."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest


try:
    from tools import build_phase6_web_foundation_source_successor_contract as builder
    from tools import phase6_web_foundation_source_successor_acceptance as acceptance
except ModuleNotFoundError:
    import build_phase6_web_foundation_source_successor_contract as builder
    import phase6_web_foundation_source_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class Phase6WebFoundationSourceSuccessorContractTest(unittest.TestCase):
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

    def test_01_builder_acceptance_and_canonical_contract_match(self) -> None:
        built = builder.build_contract(ROOT, repository_root=REPOSITORY_ROOT)
        self.assertEqual(self.contract, built)
        payload = builder.serialized_contract(built)
        self.assertEqual(acceptance.CONTRACT_SHA256,
                         builder.sha256_bytes(payload))
        self.assertEqual(acceptance.CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(acceptance.CONTRACT_PAYLOAD_SHA256,
                         built["document_payload_sha256"])

    def test_02_fixed_c563_checkpoint_replays(self) -> None:
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(107, checkpoint["changed_path_count"])
        self.assertEqual(102, checkpoint["web_changed_path_count"])
        self.assertEqual(builder.GIT_SERVER_TREE_OID,
                         checkpoint["parent_server_tree_oid"])

    def test_03_only_three_typed_anchor_paths_are_delegated(self) -> None:
        expected = {
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
        }
        self.assertEqual(expected, set(acceptance.SOURCE_PATHS))
        self.assertEqual(expected, set(
            self.contract["typed_anchor_delegation"]["delegated_paths"]
        ))
        self.assertTrue(self.contract["typed_anchor_delegation"]
                        ["delegation_allowlist_exact"])
        self.assertIsNone(acceptance.accepted_sha256("tools/unknown.py"))
        self.assertIsNone(acceptance.successor_sha256(ROOT, "tools/unknown.py"))

    def test_04_historical_and_current_hashes_are_distinct_and_fixed(self) -> None:
        for relative, descriptor in acceptance.SOURCE_SUCCESSORS.items():
            self.assertEqual(descriptor["accepted_sha256"],
                             acceptance.accepted_sha256(relative))
            self.assertNotEqual(descriptor["accepted_sha256"],
                                descriptor["successor_sha256"])
            self.assertEqual(descriptor["successor_sha256"],
                             acceptance.successor_sha256(ROOT, relative))
        phase4c = acceptance.SOURCE_SUCCESSORS[
            "docs/refactor/phase4c/README.md"
        ]
        self.assertFalse(phase4c["transition_is_direct_parent_delta"])
        self.assertTrue(phase4c["successor_snapshot_fixed_by_checkpoint_tree"])

    def test_05_gitless_minimal_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertEqual(self.contract,
                             builder.build_contract(root, repository_root=None))
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_06_each_successor_tamper_fails_closed(self) -> None:
        for relative in acceptance.SOURCE_PATHS:
            with self.subTest(relative=relative):
                temporary, root = self._minimal_copy()
                with temporary:
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\n")
                    with self.assertRaisesRegex(
                            AssertionError,
                            "anchor module is unavailable|fixed bytes drifted"):
                        acceptance.successor_sha256(root, relative)

    def test_07_fixed_authority_inputs_are_tamper_evident(self) -> None:
        for relative in (
            acceptance.TYPED_ANCHOR_RELATIVE,
            acceptance.PHASE6_ACCEPTANCE_RELATIVE,
            acceptance.ROUTE_STATUS_RELATIVE,
            acceptance.WORM_RELATIVE,
        ):
            with self.subTest(relative=relative):
                temporary, root = self._minimal_copy()
                with temporary:
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\n")
                    with self.assertRaisesRegex(AssertionError,
                                                "fixed bytes drifted"):
                        acceptance.load(root)

    def test_08_symlink_and_escape_paths_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = acceptance.SOURCE_PATHS[0]
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.md"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.successor_sha256(root, relative)
        with self.assertRaisesRegex(AssertionError, "escapes root"):
            acceptance._fixed_regular_file(ROOT, "../README.md")
        with self.assertRaisesRegex(AssertionError, "escapes root"):
            acceptance._fixed_regular_file(ROOT, "/tmp/README.md")

    def test_09_route_phase_and_cutover_overclaims_are_rejected(self) -> None:
        mutations = (
            ("effective_authority", "migrated_operation_count", 14),
            ("effective_authority", "pending_operation_count", 597),
            ("effective_authority", "production_cutover_operation_count", 1),
            ("phase6_foundation", "phase6_complete", True),
            ("authorization", "production_cutover", True),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                changed = deepcopy(self.contract)
                changed[section][field] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate(changed, ROOT)

    def test_10_java_build_context_excludes_web_and_reuses_five_node_worm(self) -> None:
        boundary = self.contract["java_build_context_boundary"]
        self.assertFalse(boundary["web_in_java_build_context"])
        self.assertTrue(boundary["server_tree_unchanged_from_parent"])
        self.assertFalse(boundary["new_worm_node_required"])
        self.assertEqual(acceptance.JAVA_BUILD_CONTEXT_SHA256,
                         boundary["java_build_context_sha256"])

    def test_11_current_control_sources_are_explicitly_self_excluded(self) -> None:
        trust = self.contract["current_node_trust_boundary"]
        self.assertEqual(list(acceptance.CONTROL_SOURCES),
                         trust["control_sources"])
        self.assertTrue(trust["control_sources_excluded_from_self_authority"])
        self.assertFalse(trust["control_sources_external_git_anchor_complete"])
        self.assertFalse(trust["independently_signed_provenance"])

    def test_12_dynamic_discovery_and_live_head_authority_are_forbidden(self) -> None:
        for relative in (
            "tools/build_phase6_web_foundation_source_successor_contract.py",
            "tools/phase6_web_foundation_source_successor_acceptance.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            for forbidden in (
                ".glob(", ".rglob(", "git ls-files", "source_contracts.keys()",
                'GIT_COMMIT_OID = "HEAD"',
            ):
                self.assertNotIn(forbidden, source)

    def test_13_contract_payload_is_canonical(self) -> None:
        payload = {key: value for key, value in self.contract.items()
                   if key != "document_payload_sha256"}
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            acceptance._sha256_bytes(
                acceptance._canonical_json(payload).encode("utf-8")
            ),
        )


if __name__ == "__main__":
    unittest.main()
