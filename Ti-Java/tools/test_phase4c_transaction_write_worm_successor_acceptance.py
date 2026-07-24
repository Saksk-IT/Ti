#!/usr/bin/env python3
"""Tests for the fixed transaction-write WORM successor."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from tools import phase4c_transaction_write_worm_successor_acceptance as acceptance
except ModuleNotFoundError:
    import phase4c_transaction_write_worm_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]


class TransactionWriteWormSuccessorAcceptanceTest(unittest.TestCase):
    def test_fixed_tenth_node_extends_the_ninth_without_rewriting_history(self) -> None:
        self.assertEqual(
            acceptance.predecessor.FIXED_EVIDENCE_CHAIN,
            acceptance.FIXED_EVIDENCE_CHAIN[:-1],
        )
        self.assertEqual(10, len(acceptance.FIXED_EVIDENCE_CHAIN))
        self.assertEqual(
            acceptance.predecessor.PHASE4C_TAG_EXECUTION_PROTOCOL_REPORT_SHA256,
            acceptance.TRANSACTION_WRITE_SUCCESSOR.predecessor_sha256,
        )
        self.assertEqual(
            acceptance.TRANSACTION_WRITE_REPORT_SHA256,
            acceptance.TRANSACTION_WRITE_SUCCESSOR.sha256,
        )

    def test_repository_fixed_chain_closes_on_current_build_context(self) -> None:
        tip = acceptance.validate_fixed_chain(
            ROOT,
            ROOT / "infra/phase2/reference-drift-manifest.json",
            acceptance.TRANSACTION_WRITE_DOCKERFILE_SHA256,
            acceptance.TRANSACTION_WRITE_BUILD_CONTEXT_SHA256,
        )
        self.assertEqual(acceptance.TRANSACTION_WRITE_SUCCESSOR, tip)

    def test_wrong_predecessor_or_current_build_context_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ti-p4c-write-worm-") as raw:
            root = Path(raw)
            with mock.patch.object(
                acceptance,
                "FIXED_EVIDENCE_CHAIN",
                (
                    *acceptance.predecessor.FIXED_EVIDENCE_CHAIN,
                    replace(
                        acceptance.TRANSACTION_WRITE_SUCCESSOR,
                        predecessor_sha256="0" * 64,
                    ),
                ),
            ), mock.patch.object(
                acceptance.predecessor,
                "validate_fixed_chain",
                return_value=acceptance.predecessor.FIXED_EVIDENCE_CHAIN[-1],
            ), mock.patch.object(
                acceptance.predecessor,
                "validate_evidence_chain",
                side_effect=acceptance.predecessor.EvidenceValidationError(
                    "broken predecessor"
                ),
            ):
                with self.assertRaisesRegex(
                    acceptance.predecessor.EvidenceValidationError,
                    "broken predecessor",
                ):
                    acceptance.validate_fixed_chain(
                        root,
                        root / "manifest.json",
                        acceptance.TRANSACTION_WRITE_DOCKERFILE_SHA256,
                        "f" * 64,
                    )


if __name__ == "__main__":
    unittest.main()
