#!/usr/bin/env python3
"""Tests for the append-only Phase 4C route-promotion successor."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

try:
    from tools import build_phase4c_personal_bank_user_counts_route_promotion_contract as builder
    from tools import phase4c_http_route_promotion_successor_acceptance as acceptance
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_route_promotion_contract as builder
    import phase4c_http_route_promotion_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]


class RoutePromotionContractTest(unittest.TestCase):
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

    def test_01_builder_acceptance_and_effective_status_are_deterministic(self) -> None:
        built = builder.build_contract(ROOT)
        self.assertEqual(self.contract, built)
        self.assertEqual(
            acceptance.CONTRACT_SHA256,
            builder.sha256_bytes(builder.serialized(built)),
        )
        effective = builder.build_effective_status(ROOT)
        self.assertEqual(
            builder.EFFECTIVE_SHA256,
            builder.sha256_bytes(builder.serialized(effective)),
        )
        self.assertEqual(builder.EFFECTIVE_PAYLOAD_SHA256, effective["document_payload_sha256"])

    def test_02_only_the_two_get_operations_are_promoted(self) -> None:
        routes = self.contract["route_authority"]["promoted_routes"]
        self.assertEqual(list(builder.ROUTES), routes)
        self.assertEqual(2, len(routes))
        self.assertEqual({"GET"}, {route["method"] for route in routes})
        self.assertEqual({"learning"}, {route["target_module"] for route in routes})

    def test_03_effective_counts_are_13_598_0(self) -> None:
        self.assertEqual({
            "total_operation_count": 611,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
        }, self.contract["route_state"])
        effective = builder.build_effective_status(ROOT)["effective"]
        self.assertEqual({"pending": 598, "migrated": 13}, effective["migration_status"])
        self.assertEqual(13, len(effective["migrated_operations"]))
        self.assertEqual(0, effective["production_cutover_operation_count"])

    def test_04_historical_route_files_are_immutable_inputs(self) -> None:
        authority = self.contract["route_authority"]
        self.assertFalse(authority["historical_matrix_and_deltas_overwritten"])
        self.assertEqual(
            "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b",
            authority["sources"]["phase4c_pending_delta"]["sha256"],
        )
        self.assertEqual(
            "eef46dc120be7aff600f7f767120673451d21fa42389a777f24e7b4e4f011d07",
            authority["sources"]["successor_delta"]["sha256"],
        )

    def test_05_route_eligibility_does_not_authorize_cutover(self) -> None:
        authorization = self.contract["authorization"]
        self.assertTrue(self.contract["parity"]["route_migration_eligible"])
        self.assertTrue(authorization["two_legacy_get_routes_migrated"])
        self.assertFalse(authorization["derived_head_and_options_count_as_migrated"])
        self.assertFalse(authorization["production_cutover"])
        self.assertFalse(authorization["operator_migration_implementation"])
        self.assertFalse(authorization["production_schema_or_index"])
        self.assertFalse(authorization["real_data_migration_execution"])

    def test_06_gitless_minimal_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_07_delta_tamper_and_symlink_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.SOURCES["successor_delta"]["source"]
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed bytes drifted"):
                acceptance.load(root)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = builder.SOURCES["successor_delta"]["source"]
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.csv"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)

    def test_08_count_and_cutover_overclaims_are_rejected(self) -> None:
        changed = deepcopy(self.contract)
        changed["route_state"]["migrated_operation_count"] = 14
        with self.assertRaisesRegex(AssertionError, "payload|effective counts"):
            acceptance.validate(changed, ROOT)
        changed = deepcopy(self.contract)
        changed["authorization"]["production_cutover"] = True
        with self.assertRaisesRegex(AssertionError, "payload|forbidden"):
            acceptance.validate(changed, ROOT)

    def test_09_current_control_sources_are_self_excluded(self) -> None:
        authority = self.contract["source_authority"]
        self.assertEqual(list(builder.CONTROL_SOURCES), authority["control_sources"])
        self.assertTrue(authority["excluded_from_self_authority"])
        self.assertFalse(authority["historical_contracts_and_worm_overwritten"])

    def test_10_builder_uses_fixed_sources_without_dynamic_discovery(self) -> None:
        source = (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_route_promotion_contract.py"
        ).read_text(encoding="utf-8")
        for forbidden in (".glob(", ".rglob(", "git ls-files", "git rev-parse", '"HEAD"'):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
