#!/usr/bin/env python3
"""Tests for the transaction-write source/runtime successor."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from tools import build_phase4c_learning_transaction_write_http_source_successor_contract as builder
from tools import phase4c_learning_transaction_write_http_source_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]


class Phase4cLearningTransactionWriteHttpSourceSuccessorContractTest(
    unittest.TestCase
):
    def test_01_builder_acceptance_and_contract_match(self) -> None:
        document = acceptance.load(ROOT)
        self.assertEqual(builder.build_contract(ROOT), document)
        self.assertEqual(
            builder.serialized_contract(document),
            (ROOT / builder.OUTPUT_RELATIVE).read_bytes(),
        )

    def test_02_fixed_bootstrap_commit_replays(self) -> None:
        builder.verify_fixed_git_checkpoint(ROOT)

    def test_03_all_seventeen_source_transitions_compose(self) -> None:
        self.assertEqual(17, len(builder.predecessor.SOURCE_TRANSITIONS))
        for relative, expected in builder.predecessor.SOURCE_TRANSITIONS.items():
            current = dict(expected)
            if relative == "docs/refactor/05-progress.md":
                fixed = builder.integration.load(ROOT)["transitions"][relative]["current"]
                current.update(successor_sha256=fixed["sha256"], successor_byte_count=fixed["byte_count"])
            self.assertEqual(
                {"source": relative, **current},
                acceptance.source_transition(ROOT, relative),
            )
            self.assertEqual(
                current["successor_sha256"],
                acceptance.successor_sha256(ROOT, relative),
            )
        self.assertIsNone(acceptance.source_transition(ROOT, "unknown"))

    def test_04_runtime_successor_closes_both_views(self) -> None:
        _, accepted = builder.node_d.production_runtime_manifests(ROOT)
        current = builder.production_runtime_manifest(ROOT)
        full = acceptance.validate_production_runtime_successor(
            ROOT, accepted, current
        )
        self.assertEqual(311, full.accepted_file_count)
        self.assertEqual(395, full.current_file_count)
        self.assertEqual(84, len(full.added_files))
        self.assertEqual(10, len(full.changed_files))
        self.assertFalse(full.deleted_files)

        accepted_main = builder.learning_personalbank_main(accepted)
        current_main = builder.learning_personalbank_main(current)
        scoped = acceptance.validate_production_runtime_successor(
            ROOT,
            accepted_main,
            current_main,
            view="learning_personalbank_main",
        )
        self.assertEqual(54, scoped.accepted_file_count)
        self.assertEqual(105, scoped.current_file_count)

    def test_05_worm_successor_closes_node_nine_to_ten(self) -> None:
        result = acceptance.validate_worm_successor(
            ROOT,
            builder.WORM["accepted_report_sha256"],
            builder.WORM["accepted_build_context_sha256"],
        )
        self.assertEqual(9, result.accepted_chain_node_count)
        self.assertEqual(10, result.current_chain_node_count)
        self.assertEqual(
            builder.WORM["current_report_sha256"],
            result.current_report_sha256,
        )
        self.assertEqual(
            builder.WORM["current_build_context_sha256"],
            result.current_build_context_sha256,
        )

    def test_06_route_overclaims_fail_closed(self) -> None:
        document = acceptance.load(ROOT)
        for field in (
            "route_migration_eligible",
            "nine_transaction_write_operations_migrated",
            "route_delta",
            "production_cutover",
        ):
            tampered = copy.deepcopy(document)
            tampered["authorization"][field] = True
            with self.assertRaises(AssertionError, msg=field):
                acceptance.validate(tampered, ROOT)

    def test_07_control_sources_remain_self_excluded(self) -> None:
        authority = acceptance.load(ROOT)["source_authority"]
        self.assertEqual(len(builder.CONTROL_SOURCES), authority["control_source_count"])
        self.assertEqual(list(builder.CONTROL_SOURCES), authority["control_sources"])
        self.assertTrue(authority["control_sources_excluded_from_self_authority"])
        self.assertFalse(authority["live_head_main_or_origin_authority"])

    def test_08_contract_hashes_are_canonical(self) -> None:
        payload = (ROOT / builder.OUTPUT_RELATIVE).read_bytes()
        document = json.loads(payload)
        self.assertEqual(
            acceptance.CONTRACT_SHA256, hashlib.sha256(payload).hexdigest()
        )
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            builder.payload_sha256(document),
        )

    def test_09_node_d_transitions_compose_through_current_controls(self) -> None:
        composed = 0
        for relative in builder.CONTROL_SOURCES:
            accepted = builder.node_d.SOURCE_FILES.get(relative)
            if accepted is None:
                continue
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(
                {
                    "source": relative,
                    "accepted_sha256": accepted[0],
                    "accepted_byte_count": accepted[1],
                    "successor_sha256": builder.sha256_bytes(payload),
                    "successor_byte_count": len(payload),
                },
                acceptance.transition_from_node_d(
                    ROOT,
                    relative,
                    accepted[0],
                    accepted[1],
                ),
            )
            composed += 1
        self.assertEqual(24, composed)
        self.assertIsNone(
            acceptance.transition_from_node_d(
                ROOT,
                "unknown",
                "0" * 64,
                0,
            )
        )


if __name__ == "__main__":
    unittest.main()
