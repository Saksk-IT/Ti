#!/usr/bin/env python3
"""Terminal successor checks for the immutable Phase 4C HTTP contract."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

try:
    from tools import phase4c_http_implementation_successor_acceptance as acceptance
    from tools import phase4c_http_target_execution_successor_acceptance as target
except ModuleNotFoundError:  # Direct execution from tools/.
    import phase4c_http_implementation_successor_acceptance as acceptance
    import phase4c_http_target_execution_successor_acceptance as target


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / acceptance.CONTRACT_RELATIVE
OLD_BRIDGE_RELATIVE = (
    "tools/phase4c_http_implementation_successor_acceptance.py"
)
UNKNOWN_RELATIVE = acceptance.CONTRACT_RELATIVE


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def historical_contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise AssertionError("historical HTTP implementation contract must be an object")
    return document


class Phase4cHttpImplementationHistoricalBytesTest(unittest.TestCase):
    """Checks that do not require the terminal target contract to exist yet."""

    def test_historical_contract_bytes_payload_and_trust_are_fixed(self) -> None:
        self.assertTrue(CONTRACT_PATH.is_file())
        self.assertFalse(CONTRACT_PATH.is_symlink())
        self.assertEqual(acceptance.CONTRACT_SHA256, sha256(CONTRACT_PATH))

        contract = historical_contract()
        self.assertEqual(acceptance.CONTRACT_ID, contract["contract_id"])
        self.assertEqual(acceptance.CONTRACT_STATUS, contract["status"])
        self.assertEqual(acceptance.CONTRACT_SCOPE, contract["scope"])
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            acceptance.TRUST_PAYLOAD_SHA256,
            acceptance._trust_payload_sha256(contract),
        )
        self.assertEqual(
            contract["document_payload_sha256"],
            acceptance._payload_sha256(contract),
        )

    def test_target_successor_allowlist_is_exact_and_unknown_is_denied(self) -> None:
        expected = {
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "docs/refactor/phase4c/route-parity-delta.csv",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            OLD_BRIDGE_RELATIVE,
            "tools/phase4c_read_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
            (
                "tools/test_phase4c_personal_bank_user_counts_"
                "http_implementation_contract.py"
            ),
            (
                "server/src/test/java/io/saksk/ti/architecture/"
                "Phase4cHttpImplementationSuccessorAcceptance.java"
            ),
            (
                "server/src/test/java/io/saksk/ti/architecture/"
                "Phase4cReadSuccessorAcceptance.java"
            ),
        }
        self.assertEqual(expected, set(acceptance.TARGET_EXECUTION_SUCCESSOR_ALLOWLIST))
        self.assertTrue(expected < set(target.HISTORICAL_SOURCE_ACCEPTED_SHA256))
        for relative in expected:
            self.assertEqual(
                target.HISTORICAL_SOURCE_ACCEPTED_SHA256[relative],
                target.accepted_sha256(relative),
            )
        self.assertIsNone(target.accepted_sha256(UNKNOWN_RELATIVE))
        self.assertIsNone(target.successor_sha256(ROOT, UNKNOWN_RELATIVE))

    def test_old_bridge_cannot_self_authorize_or_authorize_unknown_path(self) -> None:
        contract = historical_contract()
        old_bridge_fixed = contract["source_contracts"][
            "python_successor_bridge"
        ]["sha256"]
        self.assertNotEqual(old_bridge_fixed, sha256(ROOT / OLD_BRIDGE_RELATIVE))

        with mock.patch.object(
            acceptance,
            "_target_execution_accepted_sha256",
            return_value=None,
        ), mock.patch.object(
            acceptance,
            "_target_execution_successor_sha256",
            return_value=sha256(ROOT / OLD_BRIDGE_RELATIVE),
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "target successor accepted hash drift",
            ):
                acceptance._validated_current_sha256(
                    ROOT,
                    OLD_BRIDGE_RELATIVE,
                    old_bridge_fixed,
                    label="negative self authorization",
                )

        with self.assertRaisesRegex(
            AssertionError,
            "tag-preflight successor does not accept negative unknown path",
        ):
            acceptance._validated_current_sha256(
                ROOT,
                UNKNOWN_RELATIVE,
                "0" * 64,
                label="negative unknown path",
            )

    def test_historical_checkpoint_stays_pending_and_keeps_fifth_worm(self) -> None:
        contract = historical_contract()
        route = contract["implementation"]["routes_and_openapi"]
        self.assertEqual(11, route["migrated_operation_count"])
        self.assertEqual(600, route["pending_operation_count"])
        self.assertEqual(0, route["production_cutover_operation_count"])
        self.assertFalse(route["route_migration_eligible"])
        self.assertTrue(all(
            item["migration_status"] == "pending"
            and item["production_cutover"] is False
            for item in route["routes"]
        ))

        worm = contract["worm_evidence"]
        self.assertEqual(5, worm["fixed_phase2_chain"]["node_count"])
        self.assertEqual(worm["sha256"], worm["fixed_phase2_chain"]["tip_sha256"])
        self.assertFalse(worm["production_cutover"])
        self.assertFalse(contract["authorization"]["full_target_parity_closed"])


class Phase4cHttpImplementationTerminalSuccessorTest(unittest.TestCase):
    """Full checks; these intentionally fail closed until target is terminal."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.target_contract = target.load_http_target_execution_successor_contract(ROOT)
        if cls.target_contract is None:
            raise AssertionError("Phase4C target-execution contract is required")
        cls.contract = acceptance.load_http_implementation_successor_contract(ROOT)
        if cls.contract is None:
            raise AssertionError("Phase4C HTTP implementation contract is required")

    def test_target_successor_exactly_carries_all_historical_paths(self) -> None:
        for relative in sorted(acceptance.TARGET_EXECUTION_SUCCESSOR_ALLOWLIST):
            self.assertEqual(
                target.HISTORICAL_SOURCE_ACCEPTED_SHA256[relative],
                target.accepted_sha256(relative),
            )
            self.assertEqual(
                sha256(ROOT / relative),
                target.successor_sha256(ROOT, relative),
            )

        old_reference = self.contract["source_contracts"][
            "python_successor_bridge"
        ]
        self.assertEqual(OLD_BRIDGE_RELATIVE, old_reference["source"])
        self.assertEqual(
            old_reference["sha256"],
            target.accepted_sha256(OLD_BRIDGE_RELATIVE),
        )
        self.assertEqual(
            sha256(ROOT / OLD_BRIDGE_RELATIVE),
            acceptance.fixed_source_sha256(ROOT, OLD_BRIDGE_RELATIVE),
        )

    def test_target_predecessor_is_the_fixed_historical_contract(self) -> None:
        predecessor = self.target_contract["predecessor"]
        self.assertEqual(acceptance.CONTRACT_RELATIVE, predecessor["source"])
        self.assertEqual(acceptance.CONTRACT_SHA256, predecessor["sha256"])
        self.assertEqual(
            acceptance.TRUST_PAYLOAD_SHA256,
            predecessor["trust_payload_sha256"],
        )
        self.assertTrue(predecessor["immutable"])

    def test_unknown_source_injection_remains_fail_closed(self) -> None:
        injected = copy.deepcopy(self.contract)
        injected["source_contracts"]["unreviewed"] = {
            "source": "tools/unreviewed.py",
            "sha256": "0" * 64,
        }
        injected["document_payload_sha256"] = acceptance._payload_sha256(injected)
        with self.assertRaisesRegex(AssertionError, "source contract set"):
            acceptance.validate_http_implementation_successor_contract(injected, ROOT)

    def test_historical_contract_cannot_add_its_own_bridge_to_history(self) -> None:
        injected = copy.deepcopy(self.contract)
        overrides = injected["historical_successor_acceptance"][
            "http_entry_source_overrides"
        ]
        overrides[OLD_BRIDGE_RELATIVE] = {
            "source": OLD_BRIDGE_RELATIVE,
            "accepted_sha256": self.contract["source_contracts"][
                "python_successor_bridge"
            ]["sha256"],
            "successor_sha256": sha256(ROOT / OLD_BRIDGE_RELATIVE),
        }
        injected["document_payload_sha256"] = acceptance._payload_sha256(injected)
        with self.assertRaisesRegex(AssertionError, "successor source set"):
            acceptance.validate_http_implementation_successor_contract(injected, ROOT)

    def test_rewriting_self_source_hash_cannot_bypass_historical_trust(self) -> None:
        injected = copy.deepcopy(self.contract)
        injected["source_contracts"]["python_successor_bridge"]["sha256"] = (
            sha256(ROOT / OLD_BRIDGE_RELATIVE)
        )
        injected["document_payload_sha256"] = acceptance._payload_sha256(injected)
        with self.assertRaisesRegex(AssertionError, "accepted hash drift"):
            acceptance.validate_http_implementation_successor_contract(injected, ROOT)


if __name__ == "__main__":
    unittest.main()
