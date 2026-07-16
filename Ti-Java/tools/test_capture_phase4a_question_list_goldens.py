#!/usr/bin/env python3
"""Contract checks for pinned dual-route question-list golden evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
GOLDEN = TI_JAVA / "docs/refactor/phase4a/golden-question-list-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_question_list_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "bc107912c61ee632457cb8563b29f9d69e99126d5c4be212d90dbdca40aac3b6"
CASE_PAYLOAD_SHA256 = "cba2ad0d1a9e1ae75476fcf7e15d9821a65151930713da58a7ec595fc83ed1bc"
DOCUMENT_PAYLOAD_SHA256 = "c01330ec53a610a5f497ab7395c8a31f45cba796dc0f70d12c11f8efe27b8460"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
EXPECTED_SOURCE_SHA256 = {
    "app/__init__.py": "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
    "app/core/errors.py": "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
    "app/core/extensions.py": "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
    "app/core/utils/decorators.py": "6c301dc92868eb701764722f06224e614e0d0b0f82a4c4f6f406e7ded15cd653",
    "app/core/utils/portable_question_format.py": "229c3d5a4d26b68020ed7b8e305ffa0ebf902faf597e7e9584fc172b5add8112",
    "app/models/subject.py": "e0e2d38d702d986912efb16b1b57d7f4e30318c4e9d56c004d2b4107d5e67757",
    "app/models/user.py": "4e7c64b3acc98412a0a9ff861aa13aa5a9fba1ca2ebc4f8c07c97666cc9e7da5",
    "app/modules/admin/__init__.py": "06ff47e53bb93c5e484544ff3d63188fa913bfd47d26d8f43034cb60a7f2573d",
    "app/modules/admin/routes/api_components/questions.py": "da2408b27412a364ebad39a2c075ddbc7df9f977025af4629212a97535fa3e98",
    "app/modules/admin/routes/api_legacy.py": "f4d4ca3bd9cd0981360b514c93a19117f3c92f2f0fa59ee846b4fc20e3b3a5d1",
}


def expected_case_ids() -> set[str]:
    scenarios = (
        "auth-administrator",
        "auth-subject-admin",
        "auth-ordinary",
        "auth-anonymous",
        "auth-bearer-only",
        "auth-ordinary-session-plus-bearer",
        "data-empty-table",
        "data-default-multi",
        "subject-exact",
        "subject-not-found",
        "subject-empty",
        "subject-zero",
        "subject-negative",
        "subject-blank",
        "subject-out-of-range",
        "subject-repeated-first-value",
        "type-default-all",
        "type-chinese-raw",
        "type-single-choice",
        "type-single-alias",
        "type-empty",
        "type-uppercase-all",
        "type-unknown",
        "fault-html",
        "fault-json",
    )
    return {
        f"{scenario}-{route}"
        for route in capture.ROUTES
        for scenario in scenarios
    }


class QuestionListGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_checked_in_golden_hashes_close_and_sensitive_values_are_redacted(self) -> None:
        document = self.document
        self.assertEqual(
            GOLDEN_FILE_SHA256,
            hashlib.sha256(self.serialized_bytes).hexdigest(),
        )
        self.assertEqual("ti.phase4a.question-list-read-goldens", document["contract_id"])
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(50, document["case_count"])
        self.assertEqual(50, len(document["cases"]))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, document["document_payload_sha256"])
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, capture.document_payload_sha256(document))
        self.assertEqual(capture.render_document(document), self.serialized)
        capture.assert_case_contracts(document["cases"])

        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("@test.example.com", self.serialized)
        self.assertNotRegex(self.serialized, r'Bearer (?!<redacted)[A-Za-z0-9_-]+')
        self.assertNotRegex(
            self.serialized,
            re.compile(r'"last_active":\s*"20\d\d-', re.MULTILINE),
        )
        for case in document["cases"]:
            for cookie in case["response"]["headers"].get("Set-Cookie", []):
                self.assertEqual("<redacted-session-cookie>", cookie)

    def test_complete_archive_key_sources_and_route_matrix_are_attested(self) -> None:
        recorded = self.document["legacy_source_attestation"]
        matrix = recorded["frozen_route_matrix"]
        self.assertEqual(MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(capture.matrix_attestation(), matrix)
        self.assertEqual(
            {"1437bc4bf41b", "6cd7322bea3b"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["target_module"] == "operations"
            for row in matrix["selected_rows"]
        ))
        self.assertTrue(all(
            row["migration_status"] == "pending"
            for row in matrix["selected_rows"]
        ))

        workspace: Path | None = None
        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(archived.attestation, recorded["complete_app_archive"])
            observed = capture.key_source_attestation(archived)
            self.assertEqual(observed, recorded["question_list_key_sources"])
            self.assertEqual(set(EXPECTED_SOURCE_SHA256), set(observed))
            for path, expected_sha256 in EXPECTED_SOURCE_SHA256.items():
                with self.subTest(path=path):
                    evidence = observed[path]
                    self.assertEqual(expected_sha256, evidence["sha256"])
                    self.assertEqual(
                        expected_sha256,
                        hashlib.sha256((archived.root / path).read_bytes()).hexdigest(),
                    )

        self.assertIsNotNone(workspace)
        self.assertFalse(workspace.exists())

    def test_exact_50_case_dual_route_matrix_has_no_gap_or_duplicate(self) -> None:
        expected = expected_case_ids()
        self.assertEqual(50, len(expected))
        self.assertEqual(expected, {spec.case_id for spec in capture.CASE_SPECS})
        self.assertEqual(expected, set(self.by_id))
        self.assertEqual(50, len(self.by_id))
        self.assertEqual(
            {"1437bc4bf41b", "6cd7322bea3b"},
            {case["route_id"] for case in self.document["cases"]},
        )
        for route in capture.ROUTES:
            self.assertEqual(
                25,
                sum(case["route"] == route for case in self.document["cases"]),
            )

    def test_auth_status_location_content_type_body_and_query_stops_are_frozen(self) -> None:
        for route in capture.ROUTES:
            for actor in ("administrator", "subject-admin"):
                with self.subTest(route=route, actor=actor):
                    case = self.by_id[f"auth-{actor}-{route}"]
                    response = case["response"]
                    self.assertEqual(200, response["status"])
                    self.assertEqual("json", response["body_kind"])
                    self.assertEqual(["application/json"], response["headers"]["Content-Type"])
                    self.assertNotIn("Location", response["headers"])
                    self.assertEqual(
                        1,
                        case["observed_get_effects"]["sql"]["question_collection_select_attempts"],
                    )

            ordinary = self.by_id[f"auth-ordinary-{route}"]
            self.assertEqual(403, ordinary["response"]["status"])
            self.assertEqual("forbidden", ordinary["response"]["body"]["status"])
            self.assertEqual(
                ["application/json; charset=utf-8"],
                ordinary["response"]["headers"]["Content-Type"],
            )
            self.assertNotIn("Location", ordinary["response"]["headers"])
            self.assertEqual(
                0,
                ordinary["observed_get_effects"]["sql"]["question_collection_select_attempts"],
            )

            for scenario in ("anonymous", "bearer-only", "ordinary-session-plus-bearer"):
                with self.subTest(route=route, scenario=scenario):
                    case = self.by_id[f"auth-{scenario}-{route}"]
                    response = case["response"]
                    self.assertEqual(302, response["status"])
                    self.assertEqual(["/login"], response["headers"]["Location"])
                    self.assertEqual(
                        ["text/html; charset=utf-8"], response["headers"]["Content-Type"],
                    )
                    self.assertIn("Redirecting", response["body"])
                    self.assertEqual(0, case["observed_get_effects"]["sql"]["statement_count"])

    def test_empty_default_strict_desc_and_negative_question_id_are_frozen(self) -> None:
        expected_desc = sorted(capture.QUESTIONS.values(), reverse=True)
        self.assertEqual(-7, capture.QUESTIONS["negative_id"])
        self.assertEqual(10, self.document["fixture"]["full_questions_fingerprint"]["row_count"])
        self.assertEqual(15, self.document["fixture"]["full_questions_fingerprint"]["column_count"])
        for route in capture.ROUTES:
            empty = self.by_id[f"data-empty-table-{route}"]
            self.assertEqual([], empty["response"]["body"])
            self.assertEqual(0, empty["observed_get_effects"]["questions_before"]["row_count"])

            default = self.by_id[f"data-default-multi-{route}"]
            observed = capture.response_ids(default)
            self.assertEqual(expected_desc, observed)
            self.assertEqual(-7, observed[-1])
            self.assertEqual(sorted(observed, reverse=True), observed)
            self.assertEqual(10, default["observed_get_effects"]["questions_before"]["row_count"])

    def test_subject_raw_truthiness_numeric_edges_and_first_value_are_frozen(self) -> None:
        primary = sorted((
            capture.QUESTIONS["negative_id"], capture.QUESTIONS["essay"],
            capture.QUESTIONS["raw_chinese_type"], capture.QUESTIONS["fill"],
            capture.QUESTIONS["nulls"], capture.QUESTIONS["malformed"],
            capture.QUESTIONS["valid"],
        ), reverse=True)
        all_ids = sorted(capture.QUESTIONS.values(), reverse=True)
        expected = {
            "exact": primary,
            "not-found": [],
            "empty": all_ids,
            "zero": [capture.QUESTIONS["zero_subject"]],
            "negative": [capture.QUESTIONS["negative_subject"]],
            "blank": [],
            "out-of-range": [],
            "repeated-first-value": primary,
        }
        for route in capture.ROUTES:
            for scenario, ids in expected.items():
                with self.subTest(route=route, scenario=scenario):
                    case = self.by_id[f"subject-{scenario}-{route}"]
                    self.assertEqual(ids, capture.response_ids(case))
                    self.assertEqual(
                        1,
                        case["observed_get_effects"]["sql"]["question_collection_select_attempts"],
                    )
            repeated = self.by_id[f"subject-repeated-first-value-{route}"]
            self.assertEqual(
                [
                    {"name": "subject_id", "value": str(capture.SUBJECTS["primary"])},
                    {"name": "subject_id", "value": str(capture.SUBJECTS["other"])},
                ],
                repeated["request"]["query"],
            )

    def test_type_normalization_preserves_modern_legacy_differences(self) -> None:
        single_choice = sorted((
            capture.QUESTIONS["negative_subject"], capture.QUESTIONS["malformed"],
            capture.QUESTIONS["valid"],
        ), reverse=True)
        essay = sorted((
            capture.QUESTIONS["negative_id"], capture.QUESTIONS["essay"],
            capture.QUESTIONS["nulls"],
        ), reverse=True)
        all_ids = sorted(capture.QUESTIONS.values(), reverse=True)
        for route in capture.ROUTES:
            self.assertEqual(
                all_ids,
                capture.response_ids(self.by_id[f"type-default-all-{route}"]),
            )
            self.assertEqual(
                single_choice,
                capture.response_ids(self.by_id[f"type-chinese-raw-{route}"]),
            )
            for scenario in ("single-choice", "single-alias"):
                expected = single_choice if route == "modern" else essay
                self.assertEqual(
                    expected,
                    capture.response_ids(self.by_id[f"type-{scenario}-{route}"]),
                )
            for scenario in ("empty", "uppercase-all", "unknown"):
                self.assertEqual(
                    essay,
                    capture.response_ids(self.by_id[f"type-{scenario}-{route}"]),
                )

    def test_projection_facts_cover_pqf_tags_images_and_creator_join_edges(self) -> None:
        modern = {
            item["id"]: item
            for item in self.by_id["data-default-multi-modern"]["response"]["body"]
        }
        legacy = {
            item["id"]: item
            for item in self.by_id["data-default-multi-legacy"]["response"]["body"]
        }
        self.assertEqual("甲__乙__丙", modern[capture.QUESTIONS["fill"]]["content"])
        self.assertEqual("甲{1}乙{0}丙", legacy[capture.QUESTIONS["fill"]]["content"])
        self.assertEqual("数学,核心", modern[capture.QUESTIONS["valid"]]["tags"])
        self.assertEqual(["数学", "核心"], legacy[capture.QUESTIONS["valid"]]["tags"])
        self.assertEqual("", modern[capture.QUESTIONS["nulls"]]["tags"])
        self.assertIsNone(legacy[capture.QUESTIONS["nulls"]]["tags"])

        for projection in (modern, legacy):
            self.assertEqual(
                "[broken-tags",
                projection[capture.QUESTIONS["malformed"]]["tags"],
            )
            self.assertEqual(
                '["not-json-image"]',
                projection[capture.QUESTIONS["malformed"]]["image_path"],
            )
            self.assertEqual("[]", projection[capture.QUESTIONS["nulls"]]["image_path"])
            self.assertEqual(
                '["/uploads/questions/list.png"]',
                projection[capture.QUESTIONS["valid"]]["image_path"],
            )
            self.assertEqual(
                "phase4a_list_administrator",
                projection[capture.QUESTIONS["valid"]]["created_by"],
            )
            self.assertIsNone(projection[capture.QUESTIONS["malformed"]]["created_by"])
            self.assertIsNone(projection[capture.QUESTIONS["nulls"]]["created_by"])

    def test_each_case_closes_response_sql_fingerprints_and_activity_side_effects(self) -> None:
        full_fixture = self.document["fixture"]["full_questions_fingerprint"]
        self.assertEqual(list(capture.QUESTION_COLUMNS), full_fixture["columns"])
        self.assertEqual(15, full_fixture["column_count"])
        self.assertEqual(10, full_fixture["row_count"])
        for case in self.document["cases"]:
            with self.subTest(case_id=case["case_id"]):
                response = case["response"]
                raw = response["body_text"].encode("utf-8")
                self.assertEqual(len(raw), response["body_length_bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), response["body_sha256"])
                self.assertIn("Content-Type", response["headers"])
                if response["body_kind"] == "json":
                    self.assertEqual(response["body"], json.loads(response["body_text"]))

                effects = case["observed_get_effects"]
                self.assertEqual(
                    15,
                    effects["questions_before"]["column_count"],
                )
                self.assertEqual(effects["questions_before"], effects["questions_after"])
                self.assertTrue(effects["questions_match_case_fixture"])
                self.assertTrue(effects["questions_unchanged"])
                self.assertEqual(
                    effects["users_identity_before"], effects["users_identity_after"]
                )
                self.assertEqual(7, effects["users_identity_before"]["column_count"])
                self.assertEqual(3, effects["users_identity_before"]["row_count"])

                sql = effects["sql"]
                self.assertEqual(len(sql["statements"]), sql["statement_count"])
                self.assertEqual(capture.sha256_json(sql["statements"]), sql["statements_sha256"])
                self.assertEqual(sql["statement_count"], sql["classified_attempt_count"])
                self.assertEqual(0, sql["question_dml_attempts"])
                self.assertEqual(0, sql["ddl_attempts"])

                has_session_activity = (
                    case["session_actor"] != "anonymous"
                    and case["bearer_actor"] == "none"
                )
                expected_changed = (
                    [capture.ACTORS[case["session_actor"]]] if has_session_activity else []
                )
                self.assertEqual(
                    expected_changed,
                    effects["user_last_active_changed_user_ids"],
                )
                self.assertEqual(
                    len(expected_changed),
                    sql["user_last_active_dml_attempts"],
                )
                self.assertEqual(
                    bool(expected_changed),
                    effects["surrounding_session_activity_write_observed"],
                )
                self.assertTrue(all(
                    item["last_active"] is None
                    for item in effects["user_last_active_before"]
                ))

    def test_fault_content_negotiation_and_attempted_select_are_frozen(self) -> None:
        for route in capture.ROUTES:
            html = self.by_id[f"fault-html-{route}"]
            json_case = self.by_id[f"fault-json-{route}"]
            self.assertEqual((500, "text"), (
                html["response"]["status"], html["response"]["body_kind"],
            ))
            self.assertEqual(
                ["text/html; charset=utf-8"],
                html["response"]["headers"]["Content-Type"],
            )
            self.assertIn("500 - 服务器错误", html["response"]["body"])
            self.assertEqual((500, "json"), (
                json_case["response"]["status"], json_case["response"]["body_kind"],
            ))
            self.assertEqual(
                "An unexpected server error occurred.",
                json_case["response"]["body"]["message"],
            )
            for case in (html, json_case):
                self.assertEqual(
                    1,
                    case["observed_get_effects"]["sql"]["question_collection_select_attempts"],
                )
                self.assertTrue(case["observed_get_effects"]["questions_unchanged"])

    def test_sql_classifier_is_narrow_and_explicit_for_select_dml_and_ddl(self) -> None:
        collection = (
            "SELECT q.id, q.subject_id, q.type, q.content, q.difficulty, q.tags, "
            "q.image_path, u.username as created_by, q.updated_at "
            "FROM questions q LEFT JOIN users u ON q.created_by = u.id "
            "WHERE 1=1 ORDER BY q.id DESC"
        )
        self.assertTrue(capture.is_question_collection_select(collection))
        self.assertFalse(capture.is_question_collection_select(
            "SELECT id FROM questions ORDER BY id DESC"
        ))
        self.assertTrue(capture.is_users_select(collection))
        self.assertTrue(capture.is_users_select("SELECT id FROM users WHERE id=?"))
        self.assertFalse(capture.is_users_select("SELECT id FROM subjects"))
        self.assertTrue(capture.is_question_dml("UPDATE questions SET type=? WHERE id=?"))
        self.assertFalse(capture.is_question_dml(
            "UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE users.id=?"
        ))
        self.assertTrue(capture.is_user_last_active_dml(
            "UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE users.id=?"
        ))
        self.assertTrue(capture.is_ddl_statement("CREATE TABLE accidental (id int)"))
        self.assertFalse(capture.is_ddl_statement("SELECT * FROM questions"))

    def test_fresh_fixed_commit_recapture_is_byte_identical(self) -> None:
        fresh = capture.capture_document(REPOSITORY_ROOT)
        fresh_bytes = capture.render_document(fresh).encode("utf-8")
        self.assertEqual(self.serialized_bytes, fresh_bytes)
        self.assertEqual(GOLDEN_FILE_SHA256, hashlib.sha256(fresh_bytes).hexdigest())


if __name__ == "__main__":
    unittest.main()
