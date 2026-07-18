#!/usr/bin/env python3
"""Tests for the fixed Phase 4C full-parity Git anchor."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

try:
    from tools import build_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract as builder
    from tools import phase4c_http_full_parity_anchor_successor_acceptance as acceptance
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract as builder
    import phase4c_http_full_parity_anchor_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class FullParityAnchorContractTest(unittest.TestCase):
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

    def test_01_builder_and_acceptance_match_canonical_contract(self) -> None:
        built = builder.build_contract(ROOT)
        self.assertEqual(self.contract, built)
        serialized = builder.serialized_contract(built)
        self.assertEqual(acceptance.CONTRACT_SHA256, builder.sha256_bytes(serialized))
        self.assertEqual(acceptance.CONTRACT_PAYLOAD_SHA256, built["document_payload_sha256"])
        self.assertEqual(acceptance.CONTRACT_BYTE_COUNT, len(serialized))

    def test_02_fixed_git_checkpoint_replay_passes(self) -> None:
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)

    def test_03_exact_commit_and_complete_delta_are_fixed(self) -> None:
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(builder.GIT_COMMIT_OID, checkpoint["commit_oid"])
        self.assertEqual(builder.GIT_PARENT_OID, checkpoint["parent_oid"])
        self.assertEqual(15, checkpoint["changed_path_count"])
        self.assertEqual(12, checkpoint["added_path_count"])
        self.assertEqual(3, checkpoint["modified_path_count"])
        self.assertEqual(list(builder.CHECKPOINT), checkpoint["exact_changed_paths"])

    def test_04_all_six_bootstrap_sources_are_externally_anchored(self) -> None:
        anchor = self.contract["full_parity_source_anchor"]
        self.assertEqual(6, anchor["source_count"])
        self.assertEqual(list(builder.BOOTSTRAP_SOURCES), anchor["source_paths"])
        self.assertTrue(anchor["predecessor_bootstrap_sources_external_git_anchor_complete"])
        self.assertTrue(anchor["current_anchor_sources_excluded_from_self_authority"])
        self.assertFalse(anchor["current_anchor_source_bytes_external_git_anchor_complete"])

    def test_05_route_is_eligible_but_not_yet_promoted(self) -> None:
        authorization = self.contract["authorization"]
        self.assertTrue(authorization[
            "full_parity_checkpoint_and_six_excluded_sources_external_git_anchor_complete"
        ])
        self.assertTrue(authorization["route_migration_eligible"])
        self.assertFalse(authorization["two_legacy_get_routes_migrated"])
        self.assertFalse(authorization["production_cutover"])
        self.assertEqual(11, self.contract["route_state"]["migrated_operation_count"])
        self.assertEqual(600, self.contract["route_state"]["pending_operation_count"])

    def test_06_gitless_minimal_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_07_bootstrap_source_tamper_and_symlink_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.BOOTSTRAP_SOURCES[1]
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed bytes drifted"):
                acceptance.load(root)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.BOOTSTRAP_SOURCES[1]
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.java"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)

    def test_08_route_and_cutover_overclaim_are_rejected(self) -> None:
        changed = deepcopy(self.contract)
        changed["authorization"]["route_migration_eligible"] = False
        with self.assertRaisesRegex(AssertionError, "payload|route eligibility"):
            acceptance.validate(changed, ROOT)
        changed = deepcopy(self.contract)
        changed["authorization"]["production_cutover"] = True
        with self.assertRaisesRegex(AssertionError, "payload|forbidden"):
            acceptance.validate(changed, ROOT)

    def test_09_current_anchor_controls_are_self_excluded(self) -> None:
        authority = self.contract["source_authority"]
        self.assertEqual(list(builder.CONTROL_SOURCES), authority["control_sources"])
        self.assertTrue(authority["excluded_from_self_authority"])
        self.assertFalse(authority["historical_contracts_and_worm_overwritten"])

    def test_10_builder_never_replays_head_or_discovers_paths(self) -> None:
        source = (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_http_full_parity_anchor_contract.py"
        ).read_text(encoding="utf-8")
        for forbidden in (".glob(", ".rglob(", 'GIT_COMMIT_OID = "HEAD"', "git ls-files"):
            self.assertNotIn(forbidden, source)
        self.assertIn(builder.GIT_COMMIT_OID, source)


if __name__ == "__main__":
    unittest.main()
