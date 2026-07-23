#!/usr/bin/env python3
"""Tests for the Phase 4C write implementation post-push anchor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
ANCHOR = (
    TI_JAVA
    / "docs/refactor/phase4c/"
    "learning-transaction-write-implementation-post-push-anchor.json"
)
sys.path.insert(0, str(TOOLS_DIR))

import build_phase4c_learning_transaction_write_implementation_post_push_anchor as builder


class LearningTransactionWriteImplementationPostPushAnchorTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = ANCHOR.read_bytes()
        cls.anchor = json.loads(cls.payload)

    def test_fixed_git_object_and_predecessor_bytes_close(self) -> None:
        fixed = self.anchor["fixed_git_object"]
        predecessor = self.anchor["predecessor_contract"]
        self.assertEqual(builder.FIXED_COMMIT, fixed["commit_oid"])
        self.assertEqual(builder.FIXED_ROOT_TREE, fixed["root_tree_oid"])
        self.assertEqual(builder.FIXED_PARENT, fixed["parent_commit_oid"])
        self.assertEqual(builder.FIXED_COMMIT, fixed["remote_observed_at_capture"])
        self.assertEqual(builder.PREDECESSOR_SHA256, predecessor["sha256"])
        self.assertEqual(
            builder.PREDECESSOR_GIT_BLOB, predecessor["git_blob_oid"]
        )
        self.assertTrue(fixed["commit_contains_predecessor_bytes"])

    def test_payload_hash_and_control_plane_close(self) -> None:
        self.assertEqual(
            builder.document_payload_sha256(self.anchor),
            self.anchor["document_payload_sha256"],
        )
        control = self.anchor["control_plane"]
        self.assertTrue(control["fixed_commit_external_git_anchor_complete"])
        self.assertTrue(control["predecessor_physical_bytes_in_fixed_commit"])
        self.assertTrue(control["predecessor_git_blob_fixed"])
        self.assertFalse(control["self_signed"])
        self.assertTrue(control["live_worktree_is_not_authority"])

    def test_authorization_and_route_state_remain_scoped(self) -> None:
        accepted = self.anchor["accepted_authorization"]
        self.assertEqual(9, accepted["operation_count"])
        self.assertEqual(3, accepted["approved_difference_count"])
        self.assertTrue(accepted["transaction_write_implementation"])
        self.assertTrue(accepted["scoped_flyway_migrations"])
        self.assertFalse(accepted["route_matrix_delta"])
        self.assertFalse(accepted["production_schema_execution"])
        self.assertFalse(accepted["production_cutover"])
        self.assertFalse(accepted["other_phase4c_groups"])
        route = self.anchor["route_state"]
        self.assertEqual(13, route["migrated_operation_count"])
        self.assertEqual(598, route["pending_operation_count"])
        self.assertTrue(route["anchor_is_not_route_migration"])

    def test_provenance_and_fresh_build_are_byte_identical(self) -> None:
        provenance = self.anchor["provenance"]
        self.assertEqual(
            hashlib.sha256(Path(builder.__file__).read_bytes()).hexdigest(),
            provenance["builder"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            provenance["builder_test"]["sha256"],
        )
        with tempfile.TemporaryDirectory(
            prefix="ti-phase4c-learning-write-post-push-anchor-"
        ) as temporary:
            output = Path(temporary) / "anchor.json"
            output.write_bytes(
                builder.render_document(builder.build_document())
            )
            self.assertEqual(self.payload, output.read_bytes())


if __name__ == "__main__":
    unittest.main()
