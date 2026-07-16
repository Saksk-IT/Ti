#!/usr/bin/env python3
"""Contract checks for pinned admin subject-inventory golden evidence."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4a/golden-subject-inventory-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_subject_inventory_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "6ce049b13741c2f095ca988fe4f02afc58951389ebdc9c40cf092555d9bb5d07"
CASE_PAYLOAD_SHA256 = "f1ae276b9922cc66b1e8d2c613f060d7f30a4700cfac41a4b8a05f54adcaf0f9"
DOCUMENT_PAYLOAD_SHA256 = "7573787ef73af757fd598a7290ab725b6994c4d41b67acaf722898c6e3137af8"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
EXPECTED_SOURCE_SHA256 = {
    "app/__init__.py": "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
    "app/core/errors.py": "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
    "app/core/extensions.py": "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
    "app/core/utils/decorators.py": "6c301dc92868eb701764722f06224e614e0d0b0f82a4c4f6f406e7ded15cd653",
    "app/models/subject.py": "e0e2d38d702d986912efb16b1b57d7f4e30318c4e9d56c004d2b4107d5e67757",
    "app/models/user.py": "4e7c64b3acc98412a0a9ff861aa13aa5a9fba1ca2ebc4f8c07c97666cc9e7da5",
    "app/modules/admin/__init__.py": "06ff47e53bb93c5e484544ff3d63188fa913bfd47d26d8f43034cb60a7f2573d",
    "app/modules/admin/routes/api.py": "f74226d3f7bbbd30b665ea6ef2395f2d5666721941a097baf6c72eeffc7710c7",
    "app/modules/admin/routes/api_bp.py": "8e260c59ba36eebab6548195d8c5ccd07b2c3bebaa242b8a49b12b94ec7dd152",
    "app/modules/admin/routes/api_components/subjects.py": "03eb7c9942727d3df5aa5ff9996415241fe08269b8e4691d3d2e9ea1767de708",
    "app/modules/admin/templates/admin/subjects/_question_scripts.html": "db4c3443ecbaef95d25ae86a20ca3dd39dec9a44a1106865897dcb6717a37523",
    "app/modules/admin/templates/admin/subjects/_scripts.html": "25c127df0dce2b7559bf7c85b76f9a75d7d70d720eeba1a8e8f23bca34f4fd3b",
    "app/modules/admin/templates/admin/subjects/legacy.html": "b9d205b3b0fe0abb0dc0777e74708157a75997700ecf213c287fa77a35dcb4c1",
}
EXPECTED_CASE_IDS = {
    "auth-administrator",
    "auth-subject-admin",
    "auth-ordinary",
    "auth-anonymous",
    "auth-bearer-only",
    "auth-ordinary-session-plus-admin-bearer",
    "data-empty-tables",
    "data-single-subject",
    "data-multi-subject-edges",
    "fault-html",
    "fault-json",
}


class SubjectInventoryGoldenContractTest(unittest.TestCase):

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
        self.assertEqual(
            "ti.phase4a.subject-inventory-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(11, document["case_count"])
        self.assertEqual(11, len(document["cases"]))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, document["document_payload_sha256"])
        self.assertEqual(
            DOCUMENT_PAYLOAD_SHA256,
            capture.document_payload_sha256(document),
        )
        self.assertEqual(capture.render_document(document), self.serialized)
        capture.assert_case_contracts(document["cases"])

        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("@test.example.com", self.serialized)
        self.assertNotRegex(self.serialized, r"Bearer (?!<redacted)[A-Za-z0-9_-]+")
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
        self.assertEqual(1, len(matrix["selected_rows"]))
        row = matrix["selected_rows"][0]
        self.assertEqual("6e1a36f5052d", row["route_id"])
        self.assertEqual("/admin/api/subjects", row["path"])
        self.assertEqual("GET", row["methods"])
        self.assertEqual("operations", row["target_module"])
        self.assertEqual("pending", row["migration_status"])

        workspace: Path | None = None
        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(archived.attestation, recorded["complete_app_archive"])
            observed = capture.key_source_attestation(archived)
            self.assertEqual(observed, recorded["subject_inventory_key_sources"])
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

    def test_route_stays_operations_pending_without_http_or_cutover_delta(self) -> None:
        route_status = self.document["route_status"]
        self.assertEqual("catalog", route_status["target_internal_owner"])
        self.assertEqual("operations", route_status["http_owner"])
        self.assertEqual("pending", route_status["migration_status"])
        self.assertFalse(route_status["production_cutover"])
        self.assertFalse(route_status["controller_added"])
        self.assertFalse(route_status["openapi_delta"])
        self.assertFalse(route_status["route_delta"])
        self.assertEqual(capture.ROUTE, route_status["route"])

        primitive = self.document["catalog_internal_primitive"]
        self.assertEqual(["subjects", "questions"], primitive["tables"])
        self.assertEqual(
            ["id", "name", "is_locked", "question_count"],
            primitive["selected_columns"],
        )
        self.assertEqual(4, primitive["selected_column_count"])
        self.assertEqual(1, primitive["query_variant_count"])
        self.assertEqual(0, primitive["bind_count"])
        self.assertEqual([], primitive["filters"])
        self.assertIsNone(primitive["pagination"])
        self.assertEqual("signed s.id ASC", primitive["ordering"])

    def test_exact_11_case_matrix_has_no_gap_or_duplicate(self) -> None:
        self.assertEqual(11, len(EXPECTED_CASE_IDS))
        self.assertEqual(EXPECTED_CASE_IDS, {spec.case_id for spec in capture.CASE_SPECS})
        self.assertEqual(EXPECTED_CASE_IDS, set(self.by_id))
        self.assertEqual(11, len(self.by_id))
        self.assertEqual(
            {"6e1a36f5052d"},
            {case["route_id"] for case in self.document["cases"]},
        )
        for case in self.document["cases"]:
            self.assertEqual("GET", case["request"]["method"])
            self.assertEqual("/admin/api/subjects", case["request"]["path"])
            self.assertEqual([], case["request"]["query"])
            self.assertEqual("", case["request"]["query_string"])

    def test_auth_status_location_content_type_body_and_query_stops_are_frozen(self) -> None:
        for case_id in ("auth-administrator", "auth-subject-admin"):
            with self.subTest(case_id=case_id):
                case = self.by_id[case_id]
                self.assertEqual(200, case["response"]["status"])
                self.assertEqual("json", case["response"]["body_kind"])
                self.assertEqual(
                    ["application/json"],
                    case["response"]["headers"]["Content-Type"],
                )
                self.assertNotIn("Location", case["response"]["headers"])
                self.assertEqual(
                    1,
                    case["observed_get_effects"]["sql"]["subject_inventory_select_attempts"],
                )

        ordinary = self.by_id["auth-ordinary"]
        self.assertEqual(403, ordinary["response"]["status"])
        self.assertEqual("forbidden", ordinary["response"]["body"]["status"])
        self.assertEqual(
            "需要管理员或科目管理员权限",
            ordinary["response"]["body"]["message"],
        )
        self.assertEqual(
            ["application/json; charset=utf-8"],
            ordinary["response"]["headers"]["Content-Type"],
        )
        self.assertEqual(
            0,
            ordinary["observed_get_effects"]["sql"]["subject_inventory_select_attempts"],
        )

        for case_id in (
            "auth-anonymous",
            "auth-bearer-only",
            "auth-ordinary-session-plus-admin-bearer",
        ):
            with self.subTest(case_id=case_id):
                case = self.by_id[case_id]
                response = case["response"]
                self.assertEqual(302, response["status"])
                self.assertEqual(["/login"], response["headers"]["Location"])
                self.assertEqual(
                    ["text/html; charset=utf-8"],
                    response["headers"]["Content-Type"],
                )
                self.assertIn("Redirecting", response["body"])
                self.assertEqual(
                    0,
                    case["observed_get_effects"]["sql"]["statement_count"],
                )

    def test_empty_single_multi_signed_ascending_and_count_edges_are_frozen(self) -> None:
        empty = self.by_id["data-empty-tables"]
        self.assertEqual([], empty["response"]["body"])
        self.assertEqual(0, empty["observed_get_effects"]["subjects_before"]["row_count"])
        self.assertEqual(0, empty["observed_get_effects"]["questions_before"]["row_count"])

        single = self.by_id["data-single-subject"]
        self.assertEqual(1, single["observed_get_effects"]["subjects_before"]["row_count"])
        self.assertEqual(4, single["observed_get_effects"]["questions_before"]["row_count"])
        self.assertEqual([{
            "id": -3,
            "is_locked": 1,
            "name": "单一科目・β",
            "question_count": 2,
        }], single["response"]["body"])

        multi = self.by_id["data-multi-subject-edges"]
        body = multi["response"]["body"]
        self.assertEqual([-9, 0, 95001, 95002], [item["id"] for item in body])
        self.assertEqual(
            sorted(item["id"] for item in body),
            [item["id"] for item in body],
        )
        self.assertEqual([1, 0, 2, 1], [item["question_count"] for item in body])
        self.assertEqual([0, None, 1, 0], [item["is_locked"] for item in body])
        self.assertEqual("", body[1]["name"])
        self.assertEqual("算法基础・α／中文", body[2]["name"])
        self.assertEqual(
            {"id", "name", "is_locked", "question_count"},
            set(body[0]),
        )
        for index in (0, 2, 3):
            self.assertIs(type(body[index]["is_locked"]), int)
        self.assertIsNone(body[1]["is_locked"])

        fixture = self.document["fixture"]
        self.assertEqual(4, fixture["full_subjects_fingerprint"]["row_count"])
        self.assertEqual(6, fixture["full_questions_fingerprint"]["row_count"])
        self.assertEqual({
            "assigned_question_count": 4,
            "null_subject_question_count": 1,
            "orphan_subject_question_count": 1,
            "response_question_count_sum": 4,
        }, fixture["full_association_facts"])
        self.assertEqual(4, sum(item["question_count"] for item in body))
        self.assertNotIn(capture.ORPHAN_SUBJECT_ID, [item["id"] for item in body])

    def test_every_case_closes_responses_sql_fingerprints_and_activity_side_effects(self) -> None:
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
                self.assertEqual(effects["subjects_before"], effects["subjects_after"])
                self.assertEqual(effects["questions_before"], effects["questions_after"])
                self.assertTrue(effects["subjects_match_case_fixture"])
                self.assertTrue(effects["questions_match_case_fixture"])
                self.assertTrue(effects["subjects_unchanged"])
                self.assertTrue(effects["questions_unchanged"])
                self.assertEqual(
                    effects["users_identity_before"],
                    effects["users_identity_after"],
                )
                self.assertTrue(effects["users_identity_unchanged"])
                self.assertEqual(9, effects["subjects_before"]["column_count"])
                self.assertEqual(15, effects["questions_before"]["column_count"])
                self.assertEqual(7, effects["users_identity_before"]["column_count"])
                self.assertEqual(3, effects["users_identity_before"]["row_count"])

                sql = effects["sql"]
                self.assertEqual(len(sql["statements"]), sql["statement_count"])
                self.assertEqual(capture.sha256_json(sql["statements"]), sql["statements_sha256"])
                self.assertEqual(sql["statement_count"], sql["classified_attempt_count"])
                self.assertEqual(0, sql["subjects_dml_attempts"])
                self.assertEqual(0, sql["questions_dml_attempts"])
                self.assertEqual(0, sql["ddl_attempts"])

                inventory = [
                    statement
                    for statement in sql["statements"]
                    if statement["classification"] == "subject_inventory_select"
                ]
                self.assertEqual(sql["subject_inventory_select_attempts"], len(inventory))
                for statement in inventory:
                    self.assertEqual([], statement["parameters"])
                    self.assertFalse(statement["executemany"])
                    self.assertTrue(capture.is_subject_inventory_select(statement["sql"]))
                self.assertEqual(
                    sql["subject_inventory_select_attempts"],
                    sql["subjects_select_attempts"],
                )
                self.assertEqual(
                    sql["subject_inventory_select_attempts"],
                    sql["questions_select_attempts"],
                )

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
        html = self.by_id["fault-html"]
        json_case = self.by_id["fault-json"]
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
                case["observed_get_effects"]["sql"]["subject_inventory_select_attempts"],
            )
            self.assertTrue(case["observed_get_effects"]["subjects_unchanged"])
            self.assertTrue(case["observed_get_effects"]["questions_unchanged"])

    def test_sql_classifier_is_narrow_and_explicit(self) -> None:
        inventory = (
            "SELECT s.id, s.name, s.is_locked, COUNT(q.id) as question_count "
            "FROM subjects s LEFT JOIN questions q ON s.id = q.subject_id "
            "GROUP BY s.id, s.name, s.is_locked ORDER BY s.id"
        )
        self.assertTrue(capture.is_subject_inventory_select(inventory))
        self.assertFalse(capture.is_subject_inventory_select(
            "SELECT id, name FROM subjects ORDER BY id"
        ))
        self.assertTrue(capture.reads_table(inventory, "subjects"))
        self.assertTrue(capture.reads_table(inventory, "questions"))
        self.assertFalse(capture.reads_table(inventory, "users"))
        self.assertTrue(capture.is_table_dml(
            "UPDATE subjects SET name=? WHERE id=?", "subjects"
        ))
        self.assertTrue(capture.is_table_dml(
            "DELETE FROM questions WHERE subject_id=?", "questions"
        ))
        self.assertFalse(capture.is_table_dml(
            "UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE users.id=?",
            "subjects",
        ))
        self.assertTrue(capture.is_user_last_active_dml(
            "UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE users.id=?"
        ))
        self.assertTrue(capture.is_ddl_statement("CREATE TABLE accidental (id int)"))
        self.assertFalse(capture.is_ddl_statement(inventory))

    def test_fresh_fixed_commit_recapture_is_byte_identical(self) -> None:
        fresh = capture.capture_document(REPOSITORY_ROOT)
        fresh_bytes = capture.render_document(fresh).encode("utf-8")
        self.assertEqual(self.serialized_bytes, fresh_bytes)
        self.assertEqual(GOLDEN_FILE_SHA256, hashlib.sha256(fresh_bytes).hexdigest())


if __name__ == "__main__":
    unittest.main()
