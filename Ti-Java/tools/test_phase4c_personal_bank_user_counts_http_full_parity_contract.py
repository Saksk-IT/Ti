#!/usr/bin/env python3
"""Tests for the append-only Phase 4C full-parity bootstrap."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

try:
    from tools import build_phase4c_personal_bank_user_counts_http_full_parity_contract as builder
    from tools import phase4c_http_full_parity_successor_acceptance as acceptance
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_http_full_parity_contract as builder
    import phase4c_http_full_parity_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]


class FullParityContractTest(unittest.TestCase):
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
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            built["document_payload_sha256"],
        )
        serialized = builder.serialized_contract(built)
        self.assertEqual(acceptance.CONTRACT_SHA256, builder.sha256_bytes(serialized))
        self.assertEqual(acceptance.CONTRACT_BYTE_COUNT, len(serialized))

    def test_02_all_four_required_gates_are_closed(self) -> None:
        parity = self.contract["parity"]
        for field in (
            "pg16_pg18_termination_fingerprints_complete",
            "real_tomcat_complete_response_header_matrix_complete",
            "same_service_redis_outage_and_recovery_complete",
            "full_target_parity_closed",
        ):
            self.assertTrue(parity[field], field)

    def test_03_bootstrap_does_not_promote_routes(self) -> None:
        authorization = self.contract["authorization"]
        self.assertFalse(authorization["current_bootstrap_sources_external_git_anchor_complete"])
        self.assertFalse(authorization["route_migration_eligible"])
        self.assertFalse(authorization["two_legacy_get_routes_migrated"])
        self.assertFalse(authorization["production_cutover"])
        self.assertEqual(11, self.contract["route_state"]["migrated_operation_count"])
        self.assertEqual(600, self.contract["route_state"]["pending_operation_count"])

    def test_04_worker_objects_paths_and_handoffs_are_fixed(self) -> None:
        lanes = self.contract["worker_integration"]["lanes"]
        self.assertEqual(set(builder.WORKERS), set(lanes))
        self.assertEqual(builder.BASE_SHA, self.contract["worker_integration"]["base_sha"])
        for lane, expected in builder.WORKERS.items():
            self.assertEqual(expected["implementation_commit"], lanes[lane]["implementation_commit"])
            self.assertEqual(expected["handoff_commit"], lanes[lane]["handoff_commit"])
            self.assertEqual(list(expected["paths"]), lanes[lane]["integrated_paths"])
            self.assertFalse(lanes[lane]["central_authority_files_modified_by_worker"])
            self.assertFalse(lanes[lane]["handoff_file_integrated_into_main"])

    def test_05_exact_verification_totals_are_fixed(self) -> None:
        verification = self.contract["verification"]
        self.assertEqual(13, verification["targeted_failsafe_tests"])
        self.assertEqual(709, verification["full_surefire_tests"])
        self.assertEqual(167, verification["full_failsafe_tests"])
        self.assertEqual(0, verification["full_failures_errors_skipped"])
        self.assertEqual("07:02 min", verification["full_total_time"])

    def test_06_gitless_minimal_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_07_artifact_tamper_and_symlink_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = next(iter(builder.ARTIFACTS))
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed bytes drifted"):
                acceptance.load(root)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = next(iter(builder.ARTIFACTS))
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.java"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)

    def test_08_route_overclaim_is_rejected(self) -> None:
        changed = deepcopy(self.contract)
        changed["authorization"]["route_migration_eligible"] = True
        with self.assertRaisesRegex(AssertionError, "payload|route eligibility"):
            acceptance.validate(changed, ROOT)

    def test_09_current_control_sources_are_self_excluded(self) -> None:
        authority = self.contract["source_authority"]
        self.assertEqual(6, authority["control_source_count"])
        self.assertEqual(list(builder.CONTROL_SOURCES), authority["control_sources"])
        self.assertTrue(authority["excluded_from_self_authority"])
        self.assertFalse(authority["historical_contracts_and_worm_overwritten"])

    def test_10_builder_uses_no_dynamic_discovery_or_live_git(self) -> None:
        source = (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_http_full_parity_contract.py"
        ).read_text(encoding="utf-8")
        for forbidden in (".glob(", ".rglob(", "git ls-files", "git rev-parse", '"HEAD"'):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
