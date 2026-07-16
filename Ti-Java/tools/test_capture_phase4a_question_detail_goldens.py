#!/usr/bin/env python3
"""Contract checks for pinned dual-route question-detail golden evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
GOLDEN = TI_JAVA / "docs/refactor/phase4a/golden-question-detail-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_question_detail_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
CASE_PAYLOAD_SHA256 = "5f7fc1ba7f13cf790bb5c130d5b1d39933217dd3b62a3cb91e4551fe72f19e16"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
EXPECTED_SOURCE_SHA256 = {
    "app/__init__.py": "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
    "app/core/errors.py": "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
    "app/core/extensions.py": "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
    "app/core/utils/decorators.py": "6c301dc92868eb701764722f06224e614e0d0b0f82a4c4f6f406e7ded15cd653",
    "app/core/utils/image_helpers.py": "491864ba784c5b511121877129a5cdfee9e0a9422c698e69b5e27d0a2ca57110",
    "app/core/utils/portable_question_format.py": "229c3d5a4d26b68020ed7b8e305ffa0ebf902faf597e7e9584fc172b5add8112",
    "app/core/utils/pqf_rows.py": "776d4d1f1c79e71e534a540ba56cc650d0d386bb5a1a5575d3054788dc8bb8db",
    "app/models/subject.py": "e0e2d38d702d986912efb16b1b57d7f4e30318c4e9d56c004d2b4107d5e67757",
    "app/modules/admin/__init__.py": "06ff47e53bb93c5e484544ff3d63188fa913bfd47d26d8f43034cb60a7f2573d",
    "app/modules/admin/routes/api_components/questions.py": "da2408b27412a364ebad39a2c075ddbc7df9f977025af4629212a97535fa3e98",
    "app/modules/admin/routes/api_legacy.py": "f4d4ca3bd9cd0981360b514c93a19117f3c92f2f0fa59ee846b4fc20e3b3a5d1",
}


class QuestionDetailGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized = GOLDEN.read_text(encoding="utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_checked_in_contract_is_complete_self_consistent_and_redacted(self) -> None:
        document = self.document
        self.assertEqual("ti.phase4a.question-detail-read-goldens", document["contract_id"])
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(46, len(capture.CASE_SPECS))
        self.assertEqual(46, document["case_count"])
        self.assertEqual(46, len(document["cases"]))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual(capture.render_document(document), self.serialized)
        capture.assert_case_contracts(document["cases"])

        route_status = document["route_status"]
        self.assertEqual("catalog", route_status["target_internal_owner"])
        self.assertEqual("operations", route_status["http_owner"])
        self.assertEqual("pending", route_status["migration_status"])
        self.assertFalse(route_status["production_cutover"])
        self.assertEqual(
            {"8cb323acac12", "d7d727b88aea"},
            {route["route_id"] for route in route_status["routes"]},
        )
        self.assertEqual(15, document["catalog_internal_primitive"]["column_count"])
        self.assertEqual(list(capture.QUESTION_COLUMNS), document["catalog_internal_primitive"]["columns"])

        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("invalid-synthetic-token", self.serialized)
        self.assertNotRegex(self.serialized, r'Bearer (?!<redacted)[A-Za-z0-9_-]+')

    def test_complete_archive_key_sources_and_route_matrix_are_attested(self) -> None:
        recorded = self.document["legacy_source_attestation"]
        matrix = recorded["frozen_route_matrix"]
        self.assertEqual(MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(capture.matrix_attestation(), matrix)

        workspace: Path | None = None
        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(archived.attestation, recorded["complete_app_archive"])
            observed = capture.key_source_attestation(archived)
            self.assertEqual(observed, recorded["question_detail_key_sources"])
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

    def test_auth_stops_are_before_the_catalog_query(self) -> None:
        for route in capture.ROUTES:
            for actor in ("administrator", "subject-admin"):
                with self.subTest(route=route, actor=actor):
                    case = self.by_id[f"auth-{actor}-{route}"]
                    self.assertEqual(200, case["response"]["status"])
                    self.assertEqual(
                        1,
                        case["observed_get_effects"]["sql"]["question_detail_select_attempts"],
                    )

            ordinary = self.by_id[f"auth-ordinary-{route}"]
            self.assertEqual(403, ordinary["response"]["status"])
            self.assertEqual("forbidden", ordinary["response"]["body"]["status"])
            self.assertEqual(0, ordinary["observed_get_effects"]["sql"]["question_detail_select_attempts"])

            for scenario in ("anonymous", "bearer-only", "ordinary-session-plus-bearer"):
                with self.subTest(route=route, scenario=scenario):
                    case = self.by_id[f"auth-{scenario}-{route}"]
                    self.assertEqual(302, case["response"]["status"])
                    self.assertEqual("/login", case["response"]["headers"]["Location"][0])
                    self.assertEqual(0, case["observed_get_effects"]["sql"]["statement_count"])

    def test_normal_pqf_type_projections_lock_route_differences(self) -> None:
        expectations = {
            "single": ("选择题", "B"),
            "multi": ("多选题", "AC"),
            "boolean": ("判断题", "正确"),
            "fill": ("填空题", "一;;零;0"),
        }
        for fixture_name, (q_type, answer) in expectations.items():
            modern = self.by_id[f"data-{fixture_name}-modern"]["response"]["body"]
            legacy = self.by_id[f"data-{fixture_name}-legacy"]["response"]["body"]
            with self.subTest(fixture=fixture_name):
                self.assertEqual(q_type, modern["q_type"])
                self.assertEqual(q_type, legacy["q_type"])
                self.assertEqual(answer, modern["answer"])
                self.assertEqual(answer, legacy["answer"])
                self.assertIsInstance(modern["options"], str)
                self.assertIsInstance(legacy["options"], list)
                self.assertNotIn("portable_type", modern)
                self.assertEqual(modern["type"], legacy["portable_type"])

        boolean_legacy = self.by_id["data-boolean-legacy"]["response"]["body"]
        self.assertEqual(["正确", "错误"], boolean_legacy["options"])
        fill_modern = self.by_id["data-fill-modern"]["response"]["body"]
        fill_legacy = self.by_id["data-fill-legacy"]["response"]["body"]
        self.assertEqual("甲__乙__丙", fill_modern["content"])
        self.assertEqual([["零", "0"], ["一"]], fill_legacy["portable_answer"])

    def test_null_malformed_grouped_images_and_unknown_type_are_frozen(self) -> None:
        null_modern = self.by_id["data-essay-nulls-modern"]["response"]["body"]
        null_legacy = self.by_id["data-essay-nulls-legacy"]["response"]["body"]
        self.assertIsNone(null_modern["options"])
        self.assertIsNone(null_modern["difficulty"])
        self.assertEqual("", null_modern["tags"])
        self.assertEqual([], null_legacy["options"])
        self.assertEqual(1, null_legacy["difficulty"])
        self.assertEqual([], null_legacy["tags"])

        malformed_modern = self.by_id["data-malformed-json-modern"]["response"]["body"]
        malformed_legacy = self.by_id["data-malformed-json-legacy"]["response"]["body"]
        self.assertEqual("", malformed_modern["q_type"])
        self.assertEqual("[broken-options", malformed_modern["options"])
        self.assertEqual("[broken-tags", malformed_modern["tags"])
        self.assertEqual("选择题", malformed_legacy["q_type"])
        self.assertEqual([], malformed_legacy["options"])
        self.assertEqual([], malformed_legacy["tags"])

        grouped_modern = self.by_id["data-grouped-images-modern"]["response"]["body"]
        grouped_legacy = self.by_id["data-grouped-images-legacy"]["response"]["body"]
        self.assertTrue(grouped_modern["image_path"].startswith('["{'))
        self.assertEqual(
            {
                "content": ["questions/stem.png", "questions/extra.png"],
                "answer": ["questions/answer.png"],
                "explanation": ["questions/explain.png"],
            },
            grouped_legacy["question_image_groups"],
        )
        self.assertEqual("[\"questions/stem.png\"]", grouped_legacy["image_path"])

        for route in capture.ROUTES:
            unknown = self.by_id[f"data-unknown-type-{route}"]["response"]["body"]
            self.assertEqual("mystery_case", unknown["type"])
            self.assertEqual("简答题", unknown["q_type"])
            self.assertEqual("1", unknown["answer"])

    def test_id_parser_not_found_overflow_and_fault_negotiation_are_frozen(self) -> None:
        for route in capture.ROUTES:
            zero = self.by_id[f"id-zero-{route}"]
            unicode_digits = self.by_id[f"id-unicode-digits-{route}"]
            leading_zero = self.by_id[f"id-leading-zero-{route}"]
            self.assertEqual(0, zero["response"]["body"]["id"])
            self.assertEqual(8301, unicode_digits["response"]["body"]["id"])
            self.assertEqual(8301, unicode_digits["request"]["path_parameter"]["python_int_value"])
            self.assertEqual("٨٣٠١", unicode_digits["request"]["path_parameter"]["raw_text"])
            self.assertEqual(8301, leading_zero["response"]["body"]["id"])
            self.assertEqual("00008301", leading_zero["request"]["path_parameter"]["raw_text"])

            for edge in ("not-found", "huge-signed-64"):
                case = self.by_id[f"id-{edge}-{route}"]
                self.assertEqual(404, case["response"]["status"])
                self.assertEqual("not found", case["response"]["body"]["error"])
                self.assertEqual(1, case["observed_get_effects"]["sql"]["question_detail_select_attempts"])

            overflow = self.by_id[f"id-overflow-{route}"]
            self.assertEqual(500, overflow["response"]["status"])
            self.assertEqual("error", overflow["response"]["body"]["status"])
            self.assertEqual(1, overflow["observed_get_effects"]["sql"]["question_detail_select_attempts"])

            negative = self.by_id[f"id-negative-{route}"]
            self.assertEqual(404, negative["response"]["status"])
            self.assertEqual("text", negative["response"]["body_kind"])
            self.assertIn("404 - 页面未找到", negative["response"]["body"])
            self.assertEqual(0, negative["observed_get_effects"]["sql"]["question_detail_select_attempts"])

            html_fault = self.by_id[f"fault-html-{route}"]
            json_fault = self.by_id[f"fault-json-{route}"]
            self.assertEqual((500, "text"), (html_fault["response"]["status"], html_fault["response"]["body_kind"]))
            self.assertIn("500 - 服务器错误", html_fault["response"]["body"])
            self.assertEqual((500, "json"), (json_fault["response"]["status"], json_fault["response"]["body_kind"]))
            self.assertEqual("An unexpected server error occurred.", json_fault["response"]["body"]["message"])

    def test_every_case_has_complete_response_sql_and_15_column_fingerprints(self) -> None:
        fixture = self.document["fixture"]["questions_fingerprint"]
        self.assertEqual(15, fixture["column_count"])
        self.assertEqual(9, fixture["row_count"])
        self.assertEqual(list(capture.QUESTION_COLUMNS), fixture["columns"])
        for case in self.document["cases"]:
            with self.subTest(case_id=case["case_id"]):
                response = case["response"]
                raw = response["body_text"].encode("utf-8")
                self.assertEqual(len(raw), response["body_length_bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), response["body_sha256"])
                self.assertIn("Content-Type", response["headers"])
                for cookie in response["headers"].get("Set-Cookie", []):
                    self.assertEqual("<redacted-session-cookie>", cookie)
                if response["body_kind"] == "json":
                    self.assertEqual(response["body"], json.loads(response["body_text"]))

                effects = case["observed_get_effects"]
                self.assertEqual(fixture, effects["questions_before"])
                self.assertEqual(fixture, effects["questions_after"])
                self.assertTrue(effects["questions_unchanged"])
                sql = effects["sql"]
                self.assertEqual(len(sql["statements"]), sql["statement_count"])
                self.assertEqual(capture.sha256_json(sql["statements"]), sql["statements_sha256"])
                self.assertEqual(0, sql["dml_attempts"])
                self.assertEqual(0, sql["question_dml_attempts"])

    def test_sql_classifier_is_narrow_to_detail_select_and_question_dml(self) -> None:
        self.assertTrue(capture.is_question_detail_select(
            "SELECT * FROM questions WHERE id=:qid"
        ))
        self.assertTrue(capture.is_question_detail_select(
            "  SELECT  *  FROM questions WHERE id = ?  "
        ))
        self.assertFalse(capture.is_question_detail_select(
            "SELECT id FROM questions WHERE id=:qid"
        ))
        self.assertFalse(capture.is_question_detail_select(
            "SELECT * FROM users WHERE id=:qid"
        ))
        self.assertTrue(capture.is_question_dml("UPDATE questions SET type=? WHERE id=?"))
        self.assertFalse(capture.is_question_dml("UPDATE users SET last_active=? WHERE id=?"))


if __name__ == "__main__":
    unittest.main()
