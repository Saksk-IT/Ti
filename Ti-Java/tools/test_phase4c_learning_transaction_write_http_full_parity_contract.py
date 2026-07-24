#!/usr/bin/env python3
"""Tests for the transaction-write full-parity successor."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import build_phase4c_learning_transaction_write_http_full_parity_contract as builder
from tools import phase4c_learning_transaction_write_http_full_parity_successor_acceptance as acceptance
from tools import phase4c_tag_migration_execution_protocol_successor_acceptance as node_d


ROOT = Path(__file__).resolve().parents[1]


class Phase4cLearningTransactionWriteHttpFullParityContractTest(
    unittest.TestCase
):
    def test_01_builder_acceptance_and_contract_match(self) -> None:
        document = acceptance.load(ROOT)
        self.assertEqual(builder.build_contract(ROOT), document)
        self.assertEqual(
            builder.serialized_contract(document),
            (ROOT / builder.OUTPUT_RELATIVE).read_bytes(),
        )

    def test_02_fixed_git_checkpoints_replay(self) -> None:
        builder.verify_fixed_git_checkpoints(ROOT)

    def test_03_all_reviewed_transitions_are_exact(self) -> None:
        self.assertEqual(17, len(builder.SOURCE_TRANSITIONS))
        for relative, expected in builder.SOURCE_TRANSITIONS.items():
            actual = acceptance.source_transition(ROOT, relative)
            self.assertEqual({"source": relative, **expected}, actual)
            self.assertEqual(
                expected["accepted_sha256"],
                acceptance.accepted_sha256(relative),
            )
            self.assertEqual(
                expected["successor_sha256"],
                acceptance.successor_sha256(ROOT, relative),
            )
        self.assertIsNone(acceptance.source_transition(ROOT, "unknown"))
        self.assertIsNone(acceptance.successor_sha256(ROOT, "unknown"))

    def test_04_node_d_bridge_composes_current_bytes(self) -> None:
        document = node_d.load(ROOT)
        self.assertEqual(builder.node_d.CONTRACT_ID, document["contract_id"])
        for relative in (
            "docs/refactor/05-progress.md",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
        ):
            physical = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(physical, node_d.successor_sha256(ROOT, relative))

    def test_05_route_and_cutover_overclaims_fail_closed(self) -> None:
        document = acceptance.load(ROOT)
        mutations = (
            ("authorization", "route_migration_eligible"),
            ("authorization", "nine_transaction_write_operations_migrated"),
            ("authorization", "production_cutover"),
        )
        for section, field in mutations:
            tampered = copy.deepcopy(document)
            tampered[section][field] = True
            with self.assertRaises(AssertionError, msg=field):
                acceptance.validate(tampered, ROOT)

    def test_06_transition_tamper_fails_closed(self) -> None:
        relative = "docs/refactor/05-progress.md"
        paths = acceptance.minimal_fixture_paths()
        with tempfile.TemporaryDirectory() as temporary:
            isolated = Path(temporary) / "Ti-Java"
            for path in paths:
                source = ROOT / path
                target = isolated / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            with (isolated / relative).open("ab") as output:
                output.write(b"\n")
            with self.assertRaises(AssertionError):
                acceptance.load(isolated)

    def test_07_symlink_and_escape_paths_fail_closed(self) -> None:
        with self.assertRaises(AssertionError):
            builder.fixed_regular_file(ROOT, "../outside")
        with tempfile.TemporaryDirectory() as temporary:
            isolated = Path(temporary)
            target = isolated / "target"
            target.write_text("x", encoding="utf-8")
            link = isolated / "link"
            link.symlink_to(target)
            with self.assertRaises(AssertionError):
                builder.fixed_regular_file(isolated, "link")

    def test_08_payload_and_source_authority_are_canonical(self) -> None:
        payload = (ROOT / builder.OUTPUT_RELATIVE).read_bytes()
        document = json.loads(payload)
        self.assertEqual(
            acceptance.CONTRACT_SHA256, hashlib.sha256(payload).hexdigest()
        )
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            builder.payload_sha256(document),
        )
        self.assertEqual(
            list(builder.CONTROL_SOURCES),
            document["source_authority"]["control_sources"],
        )
        self.assertTrue(
            document["source_authority"][
                "control_sources_excluded_from_self_authority"
            ]
        )


if __name__ == "__main__":
    unittest.main()
