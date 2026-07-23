#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C learning route-scope entry contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

try:
    from tools import build_phase4c_learning_route_scope_contract as builder
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import build_phase4c_learning_route_scope_contract as builder


ROOT = Path(__file__).resolve().parents[1]


class Phase4cLearningRouteScopeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = (ROOT / builder.OUTPUT_RELATIVE).read_bytes()
        cls.document = json.loads(cls.payload)

    def test_01_checked_in_contract_is_deterministic_and_gitless(self) -> None:
        with mock.patch(
            "subprocess.run",
            side_effect=AssertionError("ordinary route-scope build attempted Git"),
        ):
            first = builder.build_contract(ROOT)
            second = builder.build_contract(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(self.payload, builder.serialized_contract(first))
        self.assertEqual(
            first["document_payload_sha256"],
            builder.document_payload_sha256(first),
        )

    def test_02_predecessor_and_frozen_route_authority_are_exact(self) -> None:
        predecessor = self.document["predecessor"]
        matrix = self.document["frozen_route_authority"]
        self.assertEqual(builder.PREDECESSOR_SHA256, predecessor["sha256"])
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            predecessor["document_payload_sha256"],
        )
        self.assertEqual(builder.PREDECESSOR_BYTE_COUNT, predecessor["byte_count"])
        self.assertEqual(builder.MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(592, matrix["rule_count"])
        self.assertEqual(611, matrix["operation_count"])
        self.assertEqual(67, matrix["baseline_learning_operation_count"])

    def test_03_partition_is_exact_disjoint_and_totals_71(self) -> None:
        partition = self.document["phase4c_partition"]
        groups = self.document["ordered_learning_groups"]
        self.assertEqual(71, partition["total_operation_count"])
        self.assertEqual(21, partition["phase6_page_shell_operation_count"])
        self.assertEqual(3, partition["cross_domain_transfer_operation_count"])
        self.assertEqual(47, partition["learning_backend_operation_count"])
        self.assertEqual(2, partition["already_migrated_learning_operation_count"])
        self.assertEqual(45, partition["remaining_learning_operation_count"])
        self.assertEqual([9, 11, 9, 16], partition["ordered_remaining_group_counts"])
        self.assertEqual(
            {"migrated": 58, "pending": 553, "production_cutover": 0},
            partition["final_route_target"],
        )
        self.assertEqual(
            [9, 11, 9, 16],
            [
                len(groups["transaction_writes"]),
                len(groups["progress_and_tags"]),
                len(groups["selection_search_and_count"]),
                len(groups["statistics_and_data_center"]),
            ],
        )
        keys = [
            (item["route_id"], item["method"])
            for group in groups.values()
            for item in group
        ]
        self.assertEqual(45, len(keys))
        self.assertEqual(45, len(set(keys)))
        self.assertEqual(2, len(self.document["already_migrated"]))
        self.assertEqual(21, len(self.document["page_shells"]))
        self.assertEqual(3, len(self.document["cross_domain_transfers"]))

    def test_04_transaction_write_route_keys_are_exact(self) -> None:
        actual = [
            (item["route_id"], item["method"], item["path"])
            for item in self.document["ordered_learning_groups"][
                "transaction_writes"
            ]
        ]
        self.assertEqual([
            ("6d548bfd6830", "POST", "/api/favorite"),
            ("b52d3008d4d1", "POST", "/api/quiz/favorite"),
            ("87bb4fb340c8", "POST", "/api/record_result"),
            ("67dccafb3ea4", "POST", "/api/quiz/record_result"),
            ("bf3cb0c4f9ab", "POST", "/api/quiz/study/learn/record"),
            ("c797832c43db", "POST", "/api/quiz/study/review/record"),
            ("278e1eac5eb4", "POST", "/api/quiz/study/review/master"),
            ("59c9c7366ec3", "POST", "/api/user/checkin"),
            (
                "624b5ac217d0",
                "PUT",
                "/api/quiz/questions/<int:question_id>",
            ),
        ], actual)

    def test_05_cross_domain_transfers_are_ai_and_subjective_grading(self) -> None:
        actual = {
            (item["route_id"], item["path"]): item["effective_owner"]
            for item in self.document["cross_domain_transfers"]
        }
        self.assertEqual({
            ("1156cacff587", "/api/data/ai-advice"): "intelligence",
            ("c256dab89924", "/api/grade_subjective"): "assessment",
            ("7de6db064715", "/api/quiz/grade_subjective"): "assessment",
        }, actual)

    def test_06_answer_idempotency_and_transaction_are_persistent(self) -> None:
        semantics = self.document["transaction_write_semantics"][
            "answer_aliases"
        ]
        idempotency = semantics["target_optional_idempotency_key"]
        self.assertEqual("Idempotency-Key", idempotency["header"])
        self.assertEqual(
            "replay first committed response",
            idempotency["same_actor_same_key_same_payload"],
        )
        self.assertEqual(
            "409 conflict",
            idempotency["same_actor_same_key_different_payload"],
        )
        self.assertIn("never double count", idempotency["concurrent_same_key"])
        self.assertEqual(
            "PostgreSQL learning-owned durable receipt",
            idempotency["persistence"],
        )
        self.assertIn(
            "one learning transaction", semantics["target_atomicity"]
        )

    def test_07_question_edit_preserves_catalog_table_ownership(self) -> None:
        edit = self.document["transaction_write_semantics"]["question_edit"]
        boundary = self.document["module_boundary"]
        self.assertEqual("catalog", edit["persistent_owner"])
        self.assertEqual("learning -> catalog::api", edit["required_dependency"])
        self.assertTrue(boundary["learning_direct_catalog_table_write_forbidden"])
        self.assertTrue(boundary["cross_module_database_transaction_forbidden"])
        self.assertIn("questions", boundary["catalog_owned_tables"])
        self.assertNotIn("questions", boundary["learning_owned_tables"])

    def test_08_only_golden_capture_is_authorized(self) -> None:
        authorization = self.document["authorization"]
        self.assertTrue(authorization["route_scope_partition_closed"])
        self.assertTrue(authorization["transaction_write_golden_capture_authorized"])
        for field in (
            "transaction_write_implementation_authorized",
            "progress_and_tags_implementation_authorized",
            "selection_search_and_count_implementation_authorized",
            "statistics_and_data_center_implementation_authorized",
            "production_schema_or_index",
            "flyway_baseline_or_migration",
            "real_data_migration_execution",
            "legacy_runtime_permanently_disabled",
            "route_or_openapi_delta",
            "client_gateway_or_proxy_change",
            "production_cutover",
        ):
            self.assertFalse(authorization[field], field)
        self.assertEqual({
            "total_operation_count": 611,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "legacy_flask_remains_production_owner": True,
        }, self.document["route_state"])

    def test_09_builder_rejects_matrix_drift_and_missing_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "Ti-Java"
            fixture.mkdir()
            fixture_paths = {
                builder.MATRIX_RELATIVE,
                *builder.predecessor_acceptance.minimal_fixture_paths(),
            }
            for relative in fixture_paths:
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            matrix = fixture / builder.MATRIX_RELATIVE
            matrix.write_bytes(matrix.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "matrix drifted"):
                builder.build_contract(fixture)
            matrix.write_bytes((ROOT / builder.MATRIX_RELATIVE).read_bytes())
            (fixture / builder.PREDECESSOR_RELATIVE).unlink()
            with self.assertRaises((AssertionError, FileNotFoundError)):
                builder.build_contract(fixture)

    def test_10_control_plane_is_honest_bootstrap(self) -> None:
        control = self.document["control_plane"]
        self.assertTrue(control["bootstrap"])
        self.assertFalse(
            control["current_control_sources_external_git_anchor_complete"]
        )
        self.assertFalse(control["self_signed"])
        self.assertTrue(control["closes_no_business_implementation_gate"])
        self.assertEqual(
            hashlib.sha256(self.payload).hexdigest(),
            hashlib.sha256(
                builder.serialized_contract(builder.build_contract(ROOT))
            ).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
