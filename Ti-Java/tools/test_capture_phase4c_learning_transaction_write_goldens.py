#!/usr/bin/env python3
"""Contract tests for Phase 4C transaction-write golden evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
EVIDENCE = (
    TI_JAVA
    / "docs/refactor/phase4c/learning-transaction-write-golden-evidence.json"
)
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4c_learning_transaction_write_goldens as capture


class LearningTransactionWriteGoldenEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = EVIDENCE.read_bytes()
        cls.document = json.loads(cls.payload.decode("utf-8"))

    def test_identity_predecessors_and_payload_hash_close(self) -> None:
        document = self.document
        self.assertEqual(
            "ti.phase4c.learning-transaction-write-golden-execution",
            document["contract_id"],
        )
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(
            capture.document_payload_sha256(document),
            document["document_payload_sha256"],
        )
        source = document["source_authority"]
        self.assertEqual(
            capture.EXPECTED_ENTRY_CONTRACT_SHA256,
            source["entry_contract"]["sha256"],
        )
        self.assertEqual(
            capture.EXPECTED_CALLER_EVIDENCE_SHA256,
            source["caller_evidence"]["sha256"],
        )
        self.assertTrue(
            source["complete_app_archive"]["complete_app_tree_verified"]
        )

    def test_real_route_auth_csrf_and_rate_matrices_are_complete(self) -> None:
        auth = self.document["authentication_csrf_matrix"]
        self.assertTrue(auth["complete"])
        self.assertEqual(len(capture.OPERATIONS), auth["operation_count"])
        self.assertEqual(len(capture.OPERATIONS) * 5, auth["case_count"])
        self.assertEqual(
            capture.sha256_json(auth["cases"]), auth["cases_sha256"]
        )
        for case in auth["cases"]:
            self.assertFalse(case["database"]["changed_tables"])
            self.assertTrue(case["database"]["identity_unchanged"])
        rate = self.document["rate_limit_matrix"]
        self.assertTrue(rate["complete"])
        self.assertEqual(len(capture.OPERATIONS), rate["operation_count"])
        self.assertEqual(
            capture.sha256_json(rate["cases"]), rate["cases_sha256"]
        )

    def test_request_response_database_and_transaction_evidence_is_real(self) -> None:
        parity = self.document["request_response_database_parity"]
        self.assertTrue(parity["complete"])
        self.assertEqual(
            capture.sha256_json(parity["cases"]), parity["cases_sha256"]
        )
        by_id = {case["case_id"]: case for case in parity["cases"]}
        self.assertEqual(
            ["favorites"],
            by_id["favorite-web-alias-add"]["database"]["changed_tables"],
        )
        self.assertEqual(
            ["favorites"],
            by_id["favorite-quiz-api-add"]["database"]["changed_tables"],
        )
        self.assertEqual(
            200,
            by_id["question-edit-successful-noop"]["response"]["status"],
        )
        self.assertFalse(
            by_id["question-edit-successful-noop"]["database"][
                "changed_tables"
            ]
        )
        self.assertTrue(
            by_id["study-learn-runtime-failure"]["execution"][
                "raw_connection_execute_attempts"
            ]
        )

    def test_duplicate_concurrent_and_rollback_retry_boundaries_close(self) -> None:
        duplicate = self.document["duplicate_request_outcomes"]
        concurrent = self.document["concurrent_request_outcomes"]
        rollback = self.document["rollback_retry_matrix"]
        self.assertTrue(duplicate["complete"])
        self.assertTrue(concurrent["complete"])
        self.assertTrue(rollback["complete"])
        self.assertEqual(7, duplicate["semantic_group_count"])
        self.assertEqual(7, concurrent["semantic_group_count"])
        self.assertEqual(7, rollback["semantic_group_count"])
        favorite = next(
            case
            for case in concurrent["cases"]
            if case["semantic_group"] == "favorite"
        )
        record = next(
            case
            for case in concurrent["cases"]
            if case["semantic_group"] == "record-result"
        )
        self.assertEqual({"200": 1, "500": 1}, favorite["status_histogram"])
        self.assertEqual({"500": 2}, record["status_histogram"])
        self.assertTrue(
            all(
                case.get("failure_rolled_back_all_business_changes", True)
                for case in rollback["cases"]
            )
        )

    def test_legacy_defects_and_honest_authorization_state_are_explicit(self) -> None:
        defects = self.document["legacy_defects_observed"]
        self.assertEqual(
            {
                "study-raw-connection-sqlalchemy2",
                "checkin-datetime-string-bind",
                "question-edit-swallowed-portable-update",
            },
            {defect["defect_id"] for defect in defects},
        )
        self.assertTrue(
            all(defect["approved_difference_required"] for defect in defects)
        )
        closure = self.document["closure"]
        for key in (
            "complete_fixed_commit_app_archive",
            "active_caller_attestation",
            "authentication_csrf_rate_matrix",
            "request_response_parity",
            "isolated_database_before_after_fingerprints",
            "sql_and_transaction_trace",
            "duplicate_and_concurrent_outcomes",
            "rollback_and_retry_boundaries",
            "golden_execution_complete",
        ):
            self.assertTrue(closure[key], key)
        self.assertFalse(closure["implementation_authorized"])
        self.assertFalse(closure["route_delta_authorized"])
        self.assertEqual("pending", closure["migration_status"])
        self.assertFalse(closure["production_cutover"])

    def test_provenance_and_fresh_fixed_commit_recapture_are_byte_identical(self) -> None:
        provenance = self.document["provenance"]
        self.assertEqual(
            hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest(),
            provenance["capture_tool"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            provenance["capture_test"]["sha256"],
        )
        with tempfile.TemporaryDirectory(
            prefix="ti-phase4c-learning-write-golden-test-"
        ) as temporary:
            output = Path(temporary) / "golden.json"
            output.write_bytes(capture.render_document(
                capture.capture_document(REPOSITORY_ROOT)
            ))
            self.assertEqual(self.payload, output.read_bytes())


if __name__ == "__main__":
    unittest.main()
