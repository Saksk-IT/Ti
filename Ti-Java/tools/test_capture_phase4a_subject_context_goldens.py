#!/usr/bin/env python3
"""Contract checks for pinned dual-page subject-context golden evidence."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
GOLDEN = TI_JAVA / "docs/refactor/phase4a/golden-subject-context-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_subject_context_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "fe9d29a6e3731062f2b00b5b9e953cb940c93a13cb4a146a7617875b8413945d"
CASE_PAYLOAD_SHA256 = "fce72c233b1d9637e066d15803b55f4310a5452d6e9bf07f13367632c3a946c8"
DOCUMENT_PAYLOAD_SHA256 = "027179c2141c1b0a8510a9e50e511ea16b13aca32f58f6b33c4ff0519dc2e0e5"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
EXPECTED_SOURCE_SHA256 = {
    "app/__init__.py": "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
    "app/core/errors.py": "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
    "app/core/extensions.py": "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
    "app/core/utils/decorators.py": "6c301dc92868eb701764722f06224e614e0d0b0f82a4c4f6f406e7ded15cd653",
    "app/models/subject.py": "e0e2d38d702d986912efb16b1b57d7f4e30318c4e9d56c004d2b4107d5e67757",
    "app/models/user.py": "4e7c64b3acc98412a0a9ff861aa13aa5a9fba1ca2ebc4f8c07c97666cc9e7da5",
    "app/modules/admin/__init__.py": "06ff47e53bb93c5e484544ff3d63188fa913bfd47d26d8f43034cb60a7f2573d",
    "app/modules/admin/routes/pages.py": "653a5694b64358ff0310e8cb3ace0d25f5dbce4c0c1f6bee4149185e591233fa",
    "app/modules/admin/templates/admin/admin_base.html": (
        "b5f6650079efdc39d4e2d9d0829233beed0bdc5c347d04001f29fc40a18ffaaf"
    ),
    "app/modules/admin/templates/admin/subjects/questions.html": (
        "c787dc4341cd421c0398b12e9d68b0fe0034ca188189d7a1863ece84676d369c"
    ),
    "app/modules/admin/templates/admin/subjects/duplicate_check.html": (
        "1e39ac2812dfabbe7930ec0f60d49fa7120995eeb267178597893cc377efd879"
    ),
    "app/modules/admin/templates/admin/subjects/_question_list.html": (
        "95351a5bc100a721c70c29336fdec1caaa767fd68f38067abb14916587bbe147"
    ),
    "app/modules/admin/templates/admin/subjects/_question_form.html": (
        "db8aaa2e29de9a3e3d5f98307a3a437cafe0fc048453d8f7390015eaac38557a"
    ),
    "app/modules/admin/templates/admin/subjects/_question_scripts.html": (
        "db4c3443ecbaef95d25ae86a20ca3dd39dec9a44a1106865897dcb6717a37523"
    ),
    "app/modules/admin/templates/admin/subjects/_question_styles.html": (
        "4b99c90d8f620725cfbcbae6f606081067de046284b3de888cbe467ab0108369"
    ),
    "app/modules/admin/templates/admin/subjects/_scripts.html": (
        "25c127df0dce2b7559bf7c85b76f9a75d7d70d720eeba1a8e8f23bca34f4fd3b"
    ),
}
CASE_PREFIXES = (
    "auth-admin-session-found",
    "auth-subject-admin-session-found",
    "auth-ordinary-session-forbidden",
    "auth-notification-admin-session-forbidden",
    "auth-anonymous-redirect-login",
    "auth-admin-bearer-only-redirect-login",
    "auth-ordinary-session-plus-admin-bearer-redirect-login",
    "data-locked-subject-found",
    "data-empty-name-found",
    "data-unicode-html-name-found",
    "integer-zero-id-found",
    "integer-unicode-nd-id-found",
    "integer-leading-zero-id-found",
    "integer-missing-positive-id",
    "integer-long-max-missing",
    "integer-long-overflow-bind-failure",
    "integer-negative-route-miss",
    "fault-injected-db-failure-html",
    "fault-injected-db-failure-json",
)


class SubjectContextGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_checked_in_hashes_close_and_sensitive_values_are_redacted(self) -> None:
        document = self.document
        self.assertEqual(GOLDEN_FILE_SHA256, hashlib.sha256(self.serialized_bytes).hexdigest())
        self.assertEqual("ti.phase4a.subject-context-read-goldens", document["contract_id"])
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(38, document["case_count"])
        self.assertEqual(38, len(document["cases"]))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, document["document_payload_sha256"])
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, capture.document_payload_sha256(document))
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

    def test_complete_archive_matrix_key_sources_and_dynamic_callers_are_attested(self) -> None:
        recorded = self.document["legacy_source_attestation"]
        matrix = recorded["frozen_route_matrix"]
        self.assertEqual(MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(capture.matrix_attestation(), matrix)
        self.assertEqual(
            {"52ad8f899d66", "5548b24849ed"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        for row in matrix["selected_rows"]:
            self.assertEqual("GET", row["methods"])
            self.assertEqual("operations", row["target_module"])
            self.assertEqual("pending", row["migration_status"])

        workspace: Path | None = None
        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(archived.attestation, recorded["complete_app_archive"])
            observed_sources = capture.key_source_attestation(archived)
            self.assertEqual(observed_sources, recorded["subject_context_key_sources"])
            self.assertEqual(set(EXPECTED_SOURCE_SHA256), set(observed_sources))
            for path, expected_sha in EXPECTED_SOURCE_SHA256.items():
                with self.subTest(path=path):
                    self.assertEqual(expected_sha, observed_sources[path]["sha256"])
                    self.assertEqual(
                        expected_sha,
                        hashlib.sha256((archived.root / path).read_bytes()).hexdigest(),
                    )
            self.assertEqual(
                capture.dynamic_caller_attestation(archived),
                recorded["dynamic_template_callers"],
            )

        self.assertIsNotNone(workspace)
        self.assertFalse(workspace.exists())
        callers = recorded["dynamic_template_callers"]
        self.assertEqual(
            {
                ("app/modules/admin/templates/admin/subjects/_question_scripts.html", 788),
                ("app/modules/admin/templates/admin/subjects/_scripts.html", 789),
            },
            {(caller["path"], caller["line"]) for caller in callers},
        )
        self.assertEqual({"5548b24849ed"}, {caller["target_route_id"] for caller in callers})

    def test_routes_stay_operations_pending_without_http_or_cutover_delta(self) -> None:
        status = self.document["route_status"]
        self.assertEqual("catalog", status["target_internal_owner"])
        self.assertEqual("operations", status["http_owner"])
        self.assertEqual("pending", status["migration_status"])
        self.assertFalse(status["production_cutover"])
        self.assertFalse(status["controller_added"])
        self.assertFalse(status["openapi_delta"])
        self.assertFalse(status["route_delta"])
        self.assertEqual(list(capture.ROUTES.values()), status["routes"])

        primitive = self.document["catalog_internal_primitive"]
        self.assertEqual("subjects", primitive["table"])
        self.assertEqual(["id", "name"], primitive["selected_columns"])
        self.assertEqual(2, primitive["selected_column_count"])
        self.assertEqual(1, primitive["query_variant_count"])
        self.assertEqual(1, primitive["bind_count"])
        self.assertEqual(0, primitive["questions_query_count"])
        self.assertIsNone(primitive["pagination"])

    def test_exact_19_per_route_case_matrix_has_no_gap_or_duplicate(self) -> None:
        expected = {
            f"{prefix}-{route}"
            for route in capture.ROUTES
            for prefix in CASE_PREFIXES
        }
        self.assertEqual(38, len(capture.CASE_SPECS))
        self.assertEqual(expected, {spec.case_id for spec in capture.CASE_SPECS})
        self.assertEqual(expected, set(self.by_id))
        self.assertEqual(38, len(self.by_id))
        self.assertEqual({"questions-page": 19, "duplicate-check-page": 19}, dict(
            Counter(case["route_key"] for case in self.document["cases"])
        ))
        self.assertEqual({"auth": 14, "data": 6, "integer": 14, "fault": 4}, dict(
            Counter(case["category"] for case in self.document["cases"])
        ))
        self.assertEqual({
            "per_route": 19,
            "routes": 2,
            "categories_per_route": {"auth": 7, "data": 3, "integer": 7, "fault": 2},
        }, self.document["case_matrix"])
        self.assertEqual({
            "per_route": 19,
            "routes": 2,
            "categories_per_route": {"auth": 7, "data": 3, "integer": 7, "fault": 2},
        }, self.document["case_matrix"])
        for case in self.document["cases"]:
            self.assertEqual("GET", case["request"]["method"])
            self.assertEqual([], case["request"]["query"])
            self.assertEqual("", case["request"]["query_string"])

    def test_auth_status_body_location_query_stops_and_activity_are_frozen(self) -> None:
        for route in capture.ROUTES:
            for actor, user_id in (
                ("admin", capture.ACTORS["administrator"]),
                ("subject-admin", capture.ACTORS["subject_admin"]),
            ):
                case = self.by_id[f"auth-{actor}-session-found-{route}"]
                with self.subTest(route=route, actor=actor):
                    self.assertEqual((200, "text"), (
                        case["response"]["status"], case["response"]["body_kind"],
                    ))
                    self.assertEqual(1, case["observed_get_effects"]["sql"][
                        "subject_context_select_attempts"
                    ])
                    self.assertEqual(
                        [user_id],
                        case["observed_get_effects"]["user_last_active_changed_user_ids"],
                    )

            for actor, user_id in (
                ("ordinary", capture.ACTORS["ordinary"]),
                ("notification-admin", capture.ACTORS["notification_admin"]),
            ):
                case = self.by_id[f"auth-{actor}-session-forbidden-{route}"]
                with self.subTest(route=route, actor=actor):
                    self.assertEqual((403, "json"), (
                        case["response"]["status"], case["response"]["body_kind"],
                    ))
                    self.assertEqual("forbidden", case["response"]["body"]["status"])
                    self.assertEqual(
                        "需要管理员或科目管理员权限",
                        case["response"]["body"]["message"],
                    )
                    self.assertEqual(0, case["observed_get_effects"]["sql"][
                        "subject_context_select_attempts"
                    ])
                    self.assertEqual(
                        [user_id],
                        case["observed_get_effects"]["user_last_active_changed_user_ids"],
                    )

            for prefix in (
                "auth-anonymous-redirect-login",
                "auth-admin-bearer-only-redirect-login",
                "auth-ordinary-session-plus-admin-bearer-redirect-login",
            ):
                case = self.by_id[f"{prefix}-{route}"]
                with self.subTest(route=route, prefix=prefix):
                    self.assertEqual(302, case["response"]["status"])
                    self.assertEqual(["/login"], case["response"]["headers"]["Location"])
                    self.assertEqual(0, case["observed_get_effects"]["sql"]["statement_count"])
                    self.assertEqual(
                        [],
                        case["observed_get_effects"]["user_last_active_changed_user_ids"],
                    )

    def test_locked_empty_and_unicode_html_names_render_in_both_distinct_pages(self) -> None:
        escaped = "&lt;算法 &amp; &#34;数据&#34;&gt;・α／中文"
        for route in capture.ROUTES:
            locked = self.by_id[f"data-locked-subject-found-{route}"]["response"]["body"]
            empty = self.by_id[f"data-empty-name-found-{route}"]["response"]["body"]
            unicode_body = self.by_id[f"data-unicode-html-name-found-{route}"]["response"]["body"]
            with self.subTest(route=route):
                self.assertIn("锁定科目", locked)
                self.assertIn(escaped, unicode_body)
                self.assertNotIn('<算法 & "数据">', unicode_body)
                if route == "questions-page":
                    self.assertIn("<title>题集管理</title>", locked)
                    self.assertIn(
                        '<span class="subject-badge" id="subjectName"></span>',
                        empty,
                    )
                    self.assertIn("    const subjectId = 97201;", locked)
                else:
                    self.assertIn("<title>题目查重去重</title>", locked)
                    self.assertIn('<span class="subject-badge"></span>', empty)
                    self.assertIn("const subjectId = 97201;", locked)

    def test_integer_converter_direct_404_and_generic_404_boundaries_are_frozen(self) -> None:
        safe_error = {
            "message": "An unexpected server error occurred.",
            "payload": None,
            "request_id": capture.FIXED_REQUEST_ID,
            "status": "error",
            "status_code": 500,
        }
        for route in capture.ROUTES:
            zero = self.by_id[f"integer-zero-id-found-{route}"]
            unicode_id = self.by_id[f"integer-unicode-nd-id-found-{route}"]
            leading = self.by_id[f"integer-leading-zero-id-found-{route}"]
            normal = self.by_id[f"auth-admin-session-found-{route}"]
            self.assertEqual(200, zero["response"]["status"])
            self.assertEqual(0, zero["request"]["path_parameter"]["python_int_value"])
            self.assertEqual(capture.UNICODE_ND_NORMAL_ID, unicode_id["request"][
                "path_parameter"
            ]["raw_text"])
            self.assertEqual(capture.SUBJECTS["normal"], unicode_id["request"][
                "path_parameter"
            ]["python_int_value"])
            self.assertTrue(unicode_id["request"]["path_parameter"][
                "flask_int_converter_match"
            ])
            self.assertEqual(normal["response"]["body_sha256"], unicode_id["response"]["body_sha256"])
            self.assertEqual(normal["response"]["body_sha256"], leading["response"]["body_sha256"])

            matched_missing = (
                ("integer-missing-positive-id", capture.MISSING_SUBJECT_ID),
                ("integer-long-max-missing", int(capture.LONG_MAX)),
            )
            for prefix, expected_id in matched_missing:
                missing = self.by_id[f"{prefix}-{route}"]
                with self.subTest(route=route, prefix=prefix):
                    self.assertEqual((404, "text", "科目不存在"), (
                        missing["response"]["status"],
                        missing["response"]["body_kind"],
                        missing["response"]["body"],
                    ))
                    self.assertEqual(
                        ["text/html; charset=utf-8"],
                        missing["response"]["headers"]["Content-Type"],
                    )
                    self.assertTrue(missing["request"]["path_parameter"][
                        "flask_int_converter_match"
                    ])
                    self.assertEqual(expected_id, missing["request"]["path_parameter"][
                        "python_int_value"
                    ])
                    self.assertEqual(1, missing["observed_get_effects"]["sql"][
                        "subject_context_select_attempts"
                    ])

            overflow = self.by_id[f"integer-long-overflow-bind-failure-{route}"]
            self.assertEqual((500, "json", safe_error), (
                overflow["response"]["status"],
                overflow["response"]["body_kind"],
                overflow["response"]["body"],
            ))
            self.assertEqual(
                int(capture.LONG_OVERFLOW),
                overflow["request"]["path_parameter"]["python_int_value"],
            )
            self.assertEqual(1, overflow["observed_get_effects"]["sql"][
                "subject_context_select_attempts"
            ])

            route_miss = self.by_id[f"integer-negative-route-miss-{route}"]
            parameter = route_miss["request"]["path_parameter"]
            self.assertFalse(parameter["flask_int_converter_match"])
            self.assertEqual(-1, parameter["python_int_value"])
            self.assertEqual((404, "text"), (
                route_miss["response"]["status"],
                route_miss["response"]["body_kind"],
            ))
            self.assertIn("404 - 页面未找到", route_miss["response"]["body"])
            self.assertEqual(0, route_miss["observed_get_effects"]["sql"][
                "subject_context_select_attempts"
            ])
            self.assertEqual(
                [capture.ACTORS["administrator"]],
                route_miss["observed_get_effects"]["user_last_active_changed_user_ids"],
            )

    def test_html_and_json_database_faults_are_safe_and_attempt_exact_lookup(self) -> None:
        for route in capture.ROUTES:
            html = self.by_id[f"fault-injected-db-failure-html-{route}"]
            json_case = self.by_id[f"fault-injected-db-failure-json-{route}"]
            self.assertEqual((500, "text"), (
                html["response"]["status"], html["response"]["body_kind"],
            ))
            self.assertIn("500 - 服务器错误", html["response"]["body"])
            self.assertNotIn("synthetic", html["response"]["body"])
            self.assertEqual((500, "json"), (
                json_case["response"]["status"], json_case["response"]["body_kind"],
            ))
            self.assertEqual(
                "An unexpected server error occurred.",
                json_case["response"]["body"]["message"],
            )
            self.assertNotIn("synthetic", json_case["response"]["body_text"])
            for case in (html, json_case):
                self.assertEqual(1, case["observed_get_effects"]["sql"][
                    "subject_context_select_attempts"
                ])
                self.assertTrue(case["observed_get_effects"]["subjects_unchanged"])
                self.assertTrue(case["observed_get_effects"]["questions_unchanged"])

    def test_every_case_closes_response_sql_fingerprints_and_activity_ledger(self) -> None:
        fixture = self.document["fixture"]
        self.assertEqual(5, fixture["full_subjects_fingerprint"]["row_count"])
        self.assertEqual(5, fixture["full_questions_fingerprint"]["row_count"])
        for case in self.document["cases"]:
            with self.subTest(case_id=case["case_id"]):
                response = case["response"]
                raw = response["body_text"].encode("utf-8")
                self.assertEqual(len(raw), response["body_length_bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), response["body_sha256"])
                self.assertIn("Content-Type", response["headers"])
                if response["body_kind"] == "json":
                    self.assertEqual(response["body"], json.loads(response["body_text"]))
                for cookie in response["headers"].get("Set-Cookie", []):
                    self.assertEqual("<redacted-session-cookie>", cookie)

                effects = case["observed_get_effects"]
                self.assertTrue(effects["subjects_match_case_fixture"])
                self.assertTrue(effects["questions_match_case_fixture"])
                self.assertEqual(effects["subjects_before"], effects["subjects_after"])
                self.assertEqual(effects["questions_before"], effects["questions_after"])
                self.assertTrue(effects["subjects_unchanged"])
                self.assertTrue(effects["questions_unchanged"])
                self.assertTrue(effects["users_identity_unchanged"])
                self.assertEqual(9, effects["subjects_before"]["column_count"])
                self.assertEqual(15, effects["questions_before"]["column_count"])
                self.assertEqual(7, effects["users_identity_before"]["column_count"])
                self.assertEqual(4, effects["users_identity_before"]["row_count"])

                sql = effects["sql"]
                self.assertEqual(len(sql["statements"]), sql["statement_count"])
                self.assertEqual(capture.sha256_json(sql["statements"]), sql["statements_sha256"])
                self.assertEqual(sql["statement_count"], sql["classified_attempt_count"])
                self.assertEqual(0, sql["questions_select_attempts"])
                self.assertEqual(0, sql["subjects_dml_attempts"])
                self.assertEqual(0, sql["questions_dml_attempts"])
                self.assertEqual(0, sql["unexpected_dml_attempts"])
                self.assertEqual(0, sql["ddl_attempts"])

    def test_sql_classifiers_are_narrow_and_explicit(self) -> None:
        lookup = "SELECT id, name FROM subjects WHERE id=:sid"
        self.assertTrue(capture.is_subject_context_select(lookup))
        self.assertTrue(capture.is_subject_context_select(
            " SELECT id, name FROM subjects WHERE id = ? "
        ))
        self.assertFalse(capture.is_subject_context_select(
            "SELECT id, name, is_locked FROM subjects WHERE id=?"
        ))
        self.assertFalse(capture.is_subject_context_select(
            "SELECT id, name FROM subjects ORDER BY id"
        ))
        self.assertTrue(capture.reads_table(lookup, "subjects"))
        self.assertFalse(capture.reads_table(lookup, "questions"))
        self.assertTrue(capture.is_table_dml(
            "UPDATE subjects SET name=? WHERE id=?", "subjects"
        ))
        self.assertTrue(capture.is_user_last_active_dml(
            "UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE users.id=?"
        ))
        self.assertTrue(capture.is_ddl_statement("CREATE TABLE accidental (id int)"))
        self.assertFalse(capture.is_ddl_statement(lookup))

    def test_fresh_fixed_commit_recapture_is_byte_identical(self) -> None:
        fresh = capture.capture_document(REPOSITORY_ROOT)
        fresh_bytes = capture.render_document(fresh).encode("utf-8")
        self.assertEqual(self.serialized_bytes, fresh_bytes)
        self.assertEqual(GOLDEN_FILE_SHA256, hashlib.sha256(fresh_bytes).hexdigest())


if __name__ == "__main__":
    unittest.main()
