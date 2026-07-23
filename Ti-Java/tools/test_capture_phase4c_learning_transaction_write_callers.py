#!/usr/bin/env python3
"""Contract tests for Phase 4C transaction-write caller evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4c_learning_transaction_write_callers as capture


TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
EVIDENCE = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-callers.json"
)


class LearningTransactionWriteCallerEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = EVIDENCE.read_bytes()
        cls.document = json.loads(cls.payload.decode("utf-8"))

    def test_identity_predecessor_and_payload_hash_close(self) -> None:
        document = self.document
        self.assertEqual(
            "ti.phase4c.learning-transaction-write-caller-attestation",
            document["contract_id"],
        )
        self.assertEqual(1, document["schema_version"])
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(
            capture.document_payload_sha256(document),
            document["document_payload_sha256"],
        )
        self.assertEqual(
            capture.EXPECTED_ENTRY_CONTRACT_SHA256,
            document["predecessor"]["sha256"],
        )
        self.assertEqual(
            capture.EXPECTED_ROUTE_MATRIX_SHA256,
            document["route_matrix"]["sha256"],
        )

    def test_every_operation_has_an_active_caller(self) -> None:
        attestation = self.document["caller_attestation"]
        self.assertTrue(attestation["active_caller_attestation_complete"])
        self.assertEqual(len(capture.CALLERS), attestation["caller_count"])
        self.assertEqual(len(capture.ROUTE_IDS), attestation["route_count"])
        self.assertEqual(
            set(capture.ROUTE_IDS),
            set(attestation["callers_by_route"]),
        )
        self.assertTrue(
            all(attestation["callers_by_route"].values()),
            attestation["callers_by_route"],
        )
        self.assertEqual(
            capture.sha256_json(attestation["callers"]),
            attestation["caller_set_sha256"],
        )

    def test_caller_lines_and_transport_anchors_are_fixed_commit_bytes(self) -> None:
        for caller in self.document["caller_attestation"]["callers"]:
            source = caller["source_attestation"]
            payload = capture.read_fixed_blob(REPOSITORY_ROOT, source["source"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                source["source_sha256"],
            )
            self.assertEqual(len(payload), source["source_size_bytes"])
        transport = self.document["transport_attestation"]
        self.assertTrue(transport["all_callers_have_transport"])
        self.assertTrue(transport["web_session_write_has_xhr_marker"])
        self.assertTrue(transport["miniprogram_write_has_bearer_transport"])
        self.assertEqual(len(capture.TRANSPORTS), transport["transport_count"])

    def test_fixed_commit_usage_scan_is_reproducible_and_not_empty(self) -> None:
        observed = capture.full_fixed_commit_scan(REPOSITORY_ROOT)
        recorded = self.document["full_fixed_commit_usage_scan"]
        self.assertEqual(observed, recorded)
        self.assertGreater(recorded["match_count"], len(capture.CALLERS))
        self.assertEqual(
            capture.sha256_json(recorded["matches"]),
            recorded["matches_sha256"],
        )

    def test_catalog_ownership_and_honest_gate_are_explicit(self) -> None:
        ownership = self.document["ownership_boundary"]
        self.assertEqual(
            ["624b5ac217d0"], ownership["catalog_owned_route_ids"]
        )
        self.assertEqual(
            "learning -> catalog::api",
            ownership["question_edit_dependency"],
        )
        self.assertTrue(
            ownership["learning_direct_question_table_write_forbidden"]
        )
        closure = self.document["closure"]
        self.assertTrue(closure["caller_attestation_complete"])
        self.assertFalse(closure["golden_execution_complete"])
        self.assertFalse(closure["implementation_authorized"])
        self.assertFalse(closure["route_delta_authorized"])
        self.assertEqual("pending", closure["migration_status"])
        self.assertFalse(closure["production_cutover"])

    def test_tool_provenance_and_fresh_recapture_are_byte_identical(self) -> None:
        provenance = self.document["provenance"]
        tool = Path(capture.__file__).resolve()
        test = Path(__file__).resolve()
        self.assertEqual(
            hashlib.sha256(tool.read_bytes()).hexdigest(),
            provenance["capture_tool"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(test.read_bytes()).hexdigest(),
            provenance["capture_test"]["sha256"],
        )
        with tempfile.TemporaryDirectory(
            prefix="ti-phase4c-learning-write-callers-"
        ) as temporary:
            output = Path(temporary) / "evidence.json"
            rendered = capture.render_document(
                capture.capture_document(REPOSITORY_ROOT)
            )
            output.write_bytes(rendered)
            self.assertEqual(self.payload, output.read_bytes())


if __name__ == "__main__":
    unittest.main()
