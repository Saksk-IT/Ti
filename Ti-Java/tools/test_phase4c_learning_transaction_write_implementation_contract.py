#!/usr/bin/env python3
"""Tests for the Phase 4C transaction-write implementation contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
CONTRACT = (
    TI_JAVA
    / "docs/refactor/phase4c/"
    "learning-transaction-write-implementation-contract.json"
)
sys.path.insert(0, str(TOOLS_DIR))

import build_phase4c_learning_transaction_write_implementation_contract as builder


class LearningTransactionWriteImplementationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = CONTRACT.read_bytes()
        cls.contract = json.loads(cls.payload)

    def test_identity_predecessor_and_payload_hash_close(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ti.phase4c.learning-transaction-write-implementation-contract",
            contract["contract_id"],
        )
        self.assertEqual(
            builder.document_payload_sha256(contract),
            contract["document_payload_sha256"],
        )
        predecessor = contract["predecessor"]
        self.assertEqual(
            builder.PREDECESSOR_COMMIT, predecessor["commit_oid"]
        )
        self.assertEqual(
            builder.PREDECESSOR_TREE, predecessor["root_tree_oid"]
        )
        self.assertEqual(
            builder.GOLDEN_SHA256,
            predecessor["golden_evidence"]["sha256"],
        )
        self.assertEqual(
            builder.CALLERS_SHA256,
            predecessor["caller_evidence"]["sha256"],
        )

    def test_nine_routes_and_three_approved_differences_are_exact(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(9, scope["operation_count"])
        self.assertEqual(
            {route_id for route_id, *_rest in builder.ROUTES},
            {route["route_id"] for route in scope["routes"]},
        )
        differences = self.contract["approved_differences"]
        self.assertEqual(3, len(differences))
        self.assertEqual(
            {"P4C-TW-AD-001", "P4C-TW-AD-002", "P4C-TW-AD-003"},
            {difference["difference_id"] for difference in differences},
        )
        self.assertTrue(all(difference["approved"] for difference in differences))

    def test_idempotency_and_transaction_contracts_close_races(self) -> None:
        idempotency = self.contract["idempotency_contract"]
        self.assertTrue(idempotency["optional"])
        self.assertEqual("HTTP 409", idempotency["same_actor_key_different_payload"])
        self.assertIn("one business commit", idempotency["concurrent_same_key"])
        self.assertIn("roll back together", idempotency["failed_transaction"])
        schema = self.contract["schema_authorization"]
        self.assertTrue(schema["authorized"])
        self.assertFalse(schema["production_execution_authorized"])
        self.assertEqual(
            {
                "learning_idempotency_receipts",
                "catalog_question_edit_commands",
            },
            {table["table"] for table in schema["tables"]},
        )
        self.assertIn(
            "no partial business or receipt rows",
            self.contract["transaction_contract"]["rollback"],
        )

    def test_module_ownership_keeps_question_edit_in_catalog(self) -> None:
        boundary = self.contract["module_boundary"]
        self.assertTrue(
            boundary["learning_direct_sql_to_catalog_tables_forbidden"]
        )
        self.assertTrue(
            boundary["catalog_direct_sql_to_learning_tables_forbidden"]
        )
        self.assertEqual(
            "learning HTTP -> catalog::api",
            boundary["question_edit_call_direction"],
        )
        self.assertEqual(
            "catalog", boundary["question_edit_idempotency_owner"]
        )

    def test_authorization_is_scoped_and_route_state_stays_honest(self) -> None:
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["transaction_write_implementation"])
        self.assertTrue(authorization["scoped_flyway_migrations"])
        self.assertTrue(authorization["approved_difference_implementation"])
        self.assertFalse(authorization["route_matrix_delta"])
        self.assertFalse(authorization["production_schema_execution"])
        self.assertFalse(authorization["production_cutover"])
        self.assertFalse(authorization["progress_and_tags_group"])
        route_state = self.contract["route_state"]
        self.assertEqual(13, route_state["migrated_operation_count_after_contract"])
        self.assertEqual(598, route_state["pending_operation_count_after_contract"])
        self.assertTrue(
            route_state["implementation_contract_is_not_route_migration"]
        )

    def test_provenance_and_fresh_build_are_byte_identical(self) -> None:
        provenance = self.contract["provenance"]
        self.assertEqual(
            hashlib.sha256(Path(builder.__file__).read_bytes()).hexdigest(),
            provenance["builder"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            provenance["builder_test"]["sha256"],
        )
        with tempfile.TemporaryDirectory(
            prefix="ti-phase4c-learning-write-implementation-contract-"
        ) as temporary:
            output = Path(temporary) / "contract.json"
            output.write_bytes(
                builder.render_document(builder.build_document())
            )
            self.assertEqual(self.payload, output.read_bytes())


if __name__ == "__main__":
    unittest.main()
