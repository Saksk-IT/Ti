#!/usr/bin/env python3
"""Contract checks for the pinned question-type dual-route golden evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
GOLDEN = TI_JAVA / "docs/refactor/phase4a/golden-question-type-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_question_type_goldens as capture  # noqa: E402


EXPECTED_KEY_SOURCES = {
    "app/__init__.py": (
        "1f945e13969e2d4bebf8925e65f483f2a1d4cef3",
        "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
        43_489,
    ),
    "app/core/errors.py": (
        "28a07dd252a880a2c458b5a44d2a9ca6ef8e7392",
        "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
        5_616,
    ),
    "app/core/utils/decorators.py": (
        "07a31eca9ce85e7a60ad84e0888cbdb03f2d2251",
        "6c301dc92868eb701764722f06224e614e0d0b0f82a4c4f6f406e7ded15cd653",
        11_355,
    ),
    "app/core/utils/portable_question_format.py": (
        "afd112c33c117fb946280f5628c86246df7f1956",
        "229c3d5a4d26b68020ed7b8e305ffa0ebf902faf597e7e9584fc172b5add8112",
        15_274,
    ),
    "app/modules/admin/__init__.py": (
        "e7fe1ad8c197be6da2e5ab15e2c8af72768bb2db",
        "06ff47e53bb93c5e484544ff3d63188fa913bfd47d26d8f43034cb60a7f2573d",
        5_189,
    ),
    "app/modules/admin/routes/api_components/questions.py": (
        "22b573f9a74b14a4b021678559b31ef97e05b76b",
        "da2408b27412a364ebad39a2c075ddbc7df9f977025af4629212a97535fa3e98",
        28_706,
    ),
    "app/modules/admin/routes/api_legacy.py": (
        "2bf3b5f76fb493eb40f1087b51cd0efb93a56019",
        "f4d4ca3bd9cd0981360b514c93a19117f3c92f2f0fa59ee846b4fc20e3b3a5d1",
        53_339,
    ),
}


class QuestionTypeGoldenContractTest(unittest.TestCase):

    def test_checked_in_cases_cover_route_auth_data_and_fault_differences(self) -> None:
        document = json.loads(GOLDEN.read_text(encoding="utf-8"))

        self.assertEqual("ti.phase4a.question-type-read-goldens", document["contract_id"])
        self.assertEqual(capture.pinned_source.LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(22, document["case_count"])
        self.assertEqual(22, len(document["cases"]))
        self.assertEqual(
            "eecedd275bcc4545f96fc00962fbd3f78d81772e9f89d5fbbaa25d9fc2a35374",
            document["case_payload_sha256"],
        )
        self.assertEqual(
            document["case_payload_sha256"],
            capture.sha256_json(document["cases"]),
        )
        self.assertEqual("operations", document["route_status"]["http_owner"])
        self.assertEqual("pending", document["route_status"]["migration_status"])
        self.assertFalse(document["route_status"]["production_cutover"])
        self.assertEqual(
            {"e4cbe4d6bcc8", "3a346cb29186"},
            {route["route_id"] for route in document["route_status"]["routes"]},
        )
        capture.assert_case_contracts(document["cases"])

        self.assertTrue(all(
            case["catalog_effects"]["questions_unchanged"]
            and case["catalog_effects"]["question_write_statements"] == 0
            for case in document["cases"]
        ))
        serialized = GOLDEN.read_text(encoding="utf-8")
        self.assertNotIn("eyJ", serialized)
        self.assertNotIn("public-test-only-password-hash", serialized)

    def test_complete_pinned_archive_and_question_sources_are_attested(self) -> None:
        document = json.loads(GOLDEN.read_text(encoding="utf-8"))
        recorded = document["legacy_source_attestation"]
        workspace: Path | None = None

        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(archived.attestation, recorded["complete_app_archive"])
            observed = capture.key_source_attestation(archived)
            self.assertEqual(observed, recorded["question_type_key_sources"])
            self.assertEqual(set(EXPECTED_KEY_SOURCES), set(observed))
            for path, (git_blob, sha256, size_bytes) in EXPECTED_KEY_SOURCES.items():
                with self.subTest(path=path):
                    evidence = observed[path]
                    self.assertEqual(git_blob, evidence["git_blob"])
                    self.assertEqual(sha256, evidence["sha256"])
                    self.assertEqual(size_bytes, evidence["size_bytes"])
                    self.assertEqual(
                        sha256,
                        hashlib.sha256((archived.root / path).read_bytes()).hexdigest(),
                    )

        self.assertIsNotNone(workspace)
        self.assertFalse(workspace.exists())

    def test_sql_probe_matches_only_the_question_type_distinct_query(self) -> None:
        self.assertTrue(capture.is_question_type_select(
            "SELECT DISTINCT q.type AS question_type FROM questions q"))
        self.assertTrue(capture.is_question_type_select(
            "SELECT DISTINCT type AS p_type FROM questions"))
        self.assertFalse(capture.is_question_type_select(
            "SELECT type FROM questions"))
        self.assertFalse(capture.is_question_type_select(
            "SELECT DISTINCT name FROM subjects"))


if __name__ == "__main__":
    unittest.main()
