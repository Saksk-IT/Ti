#!/usr/bin/env python3
"""Contract checks for pinned dual-route question-export golden evidence."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4a/golden-question-export-reads.json"
CONTRACT = TI_JAVA / "docs/refactor/phase4a/question-export-read-contract.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_question_export_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "89ce148cb32d1ca26d2f9d617385ae86243cf264f6d33dede97018435d00530d"
CASE_PAYLOAD_SHA256 = "e1471ea32eb6e0e6ea5819f7df391a423ec3c036574205b801dab6fa09ba1584"
DOCUMENT_PAYLOAD_SHA256 = "6c818e96ff2fdc547920a532884c5e868628a06ad2ccca08ab514240dbdbcfea"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
CALLER_ATTESTATION_SHA256 = "699bdb17776a1ce9f1369c1aa10f1c20dc91bdc2fabb9559b777c83b468899c2"
CAPTURE_TOOL_SHA256 = "549ba5e988b7a91812895b0b0b692204e9a5e1165f7ec39d04d856e66e6bb534"
EXPECTED_SOURCE_SHA256 = {
    "app/__init__.py": "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
    "app/core/errors.py": "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
    "app/core/extensions.py": "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
    "app/core/utils/decorators.py": "6c301dc92868eb701764722f06224e614e0d0b0f82a4c4f6f406e7ded15cd653",
    "app/core/utils/json_helpers.py": "856147863f014f1805fab554d8acb2c8cfdabf7f4b46e4b0ed897055d27e4d78",
    "app/models/subject.py": "e0e2d38d702d986912efb16b1b57d7f4e30318c4e9d56c004d2b4107d5e67757",
    "app/models/user.py": "4e7c64b3acc98412a0a9ff861aa13aa5a9fba1ca2ebc4f8c07c97666cc9e7da5",
    "app/modules/admin/__init__.py": "06ff47e53bb93c5e484544ff3d63188fa913bfd47d26d8f43034cb60a7f2573d",
    "app/modules/admin/routes/api.py": "f74226d3f7bbbd30b665ea6ef2395f2d5666721941a097baf6c72eeffc7710c7",
    "app/modules/admin/routes/api_bp.py": "8e260c59ba36eebab6548195d8c5ccd07b2c3bebaa242b8a49b12b94ec7dd152",
    "app/modules/admin/routes/api_components/questions_io.py": "5ad1541301bd2e59ef6e81ba9b7dca9de4beff12b4ebc3b2f88f316bdf74a48d",
    "app/modules/admin/routes/api_legacy.py": "f4d4ca3bd9cd0981360b514c93a19117f3c92f2f0fa59ee846b4fc20e3b3a5d1",
    "app/modules/admin/templates/admin/subjects/questions.html": "c787dc4341cd421c0398b12e9d68b0fe0034ca188189d7a1863ece84676d369c",
    "app/modules/admin/templates/admin/subjects/_question_scripts.html": "db4c3443ecbaef95d25ae86a20ca3dd39dec9a44a1106865897dcb6717a37523",
    "app/modules/admin/templates/admin/subjects/_scripts.html": "25c127df0dce2b7559bf7c85b76f9a75d7d70d720eeba1a8e8f23bca34f4fd3b",
    "app/modules/admin/templates/admin/subjects/_styles.html": "210df628801fa3232b5d1226f9817fd287576d02a9c22d567c5c802003c9f15d",
}


def expected_case_ids() -> set[str]:
    scenarios = (
        "auth-administrator-session",
        "auth-subject-admin-session",
        "auth-ordinary-session-forbidden",
        "auth-notification-admin-session-forbidden",
        "auth-anonymous-redirect-login",
        "auth-administrator-bearer-only-redirect-login",
        "auth-ordinary-session-plus-administrator-bearer-redirect-login",
        "data-empty-table",
        "subject-missing-default",
        "subject-empty",
        "subject-blank",
        "subject-zero",
        "subject-negative",
        "subject-exact",
        "subject-exact-type-ignored",
        "subject-no-match",
        "subject-repeated-first-value",
        "subject-invalid",
        "subject-unicode-nd",
        "subject-int4-out-of-range",
        "fault-html",
        "fault-json",
    )
    return {
        f"{scenario}-{route}"
        for route in capture.ROUTES
        for scenario in scenarios
    }


class QuestionExportGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_checked_in_golden_hashes_close_and_sensitive_values_are_redacted(self) -> None:
        document = self.document
        self.assertEqual(
            GOLDEN_FILE_SHA256,
            hashlib.sha256(self.serialized_bytes).hexdigest(),
        )
        self.assertEqual(
            "ti.phase4a.question-export-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(44, document["case_count"])
        self.assertEqual(44, len(document["cases"]))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual(
            DOCUMENT_PAYLOAD_SHA256,
            document["document_payload_sha256"],
        )
        self.assertEqual(
            DOCUMENT_PAYLOAD_SHA256,
            capture.document_payload_sha256(document),
        )
        self.assertEqual(capture.render_document(document), self.serialized)
        capture.assert_case_contracts(document["cases"])

        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("@test.example.com", self.serialized)
        self.assertNotRegex(
            self.serialized,
            r"Bearer (?!<redacted)[A-Za-z0-9_-]+",
        )
        self.assertNotRegex(
            self.serialized,
            re.compile(r'"last_active":\s*"20\d\d-', re.MULTILINE),
        )
        for case in document["cases"]:
            for cookie in case["response"]["headers"].get("Set-Cookie", []):
                self.assertEqual("<redacted-session-cookie>", cookie)

    def test_machine_contract_closes_golden_and_java_operations_boundary(self) -> None:
        contract = self.contract
        golden = contract["evidence"]["golden"]
        self.assertEqual("ti.phase4a.question-export-read-contract", contract["contract_id"])
        self.assertEqual(
            "catalog_raw_snapshot_implemented_http_operations_deferred",
            contract["status"],
        )
        self.assertEqual(LEGACY_COMMIT, contract["legacy_commit"])
        self.assertEqual(GOLDEN_FILE_SHA256, golden["file_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, golden["case_payload_sha256"])
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, golden["document_payload_sha256"])
        self.assertEqual(CAPTURE_TOOL_SHA256, golden["capture_tool_sha256"])
        self.assertEqual(
            CAPTURE_TOOL_SHA256,
            hashlib.sha256(
                (TOOLS_DIR / "capture_phase4a_question_export_goldens.py").read_bytes()
            ).hexdigest(),
        )
        boundary = contract["module_boundary"]
        self.assertEqual(
            "List<QuestionExportRecordView> listQuestionExportRecords(QuestionExportQuery query)",
            boundary["method"],
        )
        self.assertEqual("Optional<Integer> subjectId", boundary["query_shape"])
        self.assertEqual(
            [
                "id", "subjectId", "subjectName", "type", "content",
                "optionsRaw", "answerRaw", "analysis", "difficulty", "tagsRaw",
            ],
            boundary["result_field_order"],
        )
        self.assertEqual("operations", boundary["http_operation_owner"])
        self.assertEqual("not_implemented", boundary["http_adapter_status"])
        operations = contract["route_status"]["operations"]
        self.assertEqual(
            {"4a33d8e15da5", "712a47789f1d"},
            {operation["route_id"] for operation in operations},
        )
        self.assertTrue(all(
            operation["target_module"] == "operations"
            and operation["migration_status"] == "pending"
            and operation["production_cutover"] is False
            for operation in operations
        ))
        self.assertIn(
            "PostgreSQL 16.14 and 18.4",
            contract["engine_boundary"]["required_phase4h_evidence"],
        )

    def test_complete_archive_key_sources_matrix_and_callers_are_attested(self) -> None:
        recorded = self.document["legacy_source_attestation"]
        matrix = recorded["frozen_route_matrix"]
        self.assertEqual(MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(capture.matrix_attestation(), matrix)
        self.assertEqual(
            {"4a33d8e15da5", "712a47789f1d"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["target_module"] == "operations"
            and row["migration_status"] == "pending"
            for row in matrix["selected_rows"]
        ))
        by_route = {row["route_id"]: row for row in matrix["selected_rows"]}
        self.assertEqual(
            '["subject_admin_required"]',
            by_route["4a33d8e15da5"]["decorators"],
        )
        self.assertEqual("[]", by_route["712a47789f1d"]["decorators"])

        callers = recorded["template_callers"]
        self.assertEqual(CALLER_ATTESTATION_SHA256, callers["attestation_sha256"])
        self.assertEqual(
            [("app/modules/admin/templates/admin/subjects/_scripts.html", 752),
             ("app/modules/admin/templates/admin/subjects/_scripts.html", 753)],
            [(item["source"], item["line"])
             for item in callers["direct_route_occurrences"]["modern"]],
        )
        self.assertEqual(
            [("app/modules/admin/templates/admin/subjects/_question_scripts.html", 751),
             ("app/modules/admin/templates/admin/subjects/_question_scripts.html", 752)],
            [(item["source"], item["line"])
             for item in callers["direct_route_occurrences"]["legacy"]],
        )
        self.assertEqual(
            "active",
            callers["reachability"]["active_legacy_chain"]["status"],
        )
        self.assertEqual(
            "dormant_in_frozen_archive",
            callers["reachability"]["modern_template"]["status"],
        )
        self.assertEqual(
            0,
            callers["reachability"]["modern_template"]["inbound_include_count"],
        )

        workspace: Path | None = None
        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(
                archived.attestation,
                recorded["complete_app_archive"],
            )
            observed = capture.key_source_attestation(archived)
            self.assertEqual(observed, recorded["question_export_key_sources"])
            self.assertEqual(set(EXPECTED_SOURCE_SHA256), set(observed))
            for path, expected_sha256 in EXPECTED_SOURCE_SHA256.items():
                with self.subTest(path=path):
                    evidence = observed[path]
                    self.assertEqual(expected_sha256, evidence["sha256"])
                    self.assertEqual(
                        expected_sha256,
                        hashlib.sha256((archived.root / path).read_bytes()).hexdigest(),
                    )
            self.assertEqual(callers, capture.template_caller_attestation(archived))

        self.assertIsNotNone(workspace)
        self.assertFalse(workspace.exists())

    def test_exact_44_case_dual_route_matrix_has_no_gap_or_duplicate(self) -> None:
        expected = expected_case_ids()
        self.assertEqual(44, len(expected))
        self.assertEqual(expected, {spec.case_id for spec in capture.CASE_SPECS})
        self.assertEqual(expected, set(self.by_id))
        self.assertEqual(44, len(self.by_id))
        self.assertEqual(
            {"4a33d8e15da5", "712a47789f1d"},
            {case["route_id"] for case in self.document["cases"]},
        )
        for route in capture.ROUTES:
            self.assertEqual(
                22,
                sum(case["route"] == route for case in self.document["cases"]),
            )

    def test_dual_route_auth_and_session_activity_boundaries_are_frozen(self) -> None:
        for route in capture.ROUTES:
            for actor, user_id in (
                ("administrator", capture.ACTORS["administrator"]),
                ("subject-admin", capture.ACTORS["subject_admin"]),
            ):
                case = self.by_id[f"auth-{actor}-session-{route}"]
                with self.subTest(route=route, actor=actor):
                    self.assertEqual((200, "json"), (
                        case["response"]["status"],
                        case["response"]["body_kind"],
                    ))
                    self.assertEqual(
                        1,
                        case["observed_get_effects"]["sql"]["export_select_attempts"],
                    )
                    self.assertEqual(
                        [user_id],
                        case["observed_get_effects"][
                            "user_last_active_changed_user_ids"
                        ],
                    )

            for actor, user_id in (
                ("ordinary", capture.ACTORS["ordinary"]),
                ("notification-admin", capture.ACTORS["notification_admin"]),
            ):
                case = self.by_id[f"auth-{actor}-session-forbidden-{route}"]
                with self.subTest(route=route, actor=actor):
                    self.assertEqual((403, "json", "forbidden", 403), (
                        case["response"]["status"],
                        case["response"]["body_kind"],
                        case["response"]["body"]["status"],
                        case["response"]["body"]["status_code"],
                    ))
                    self.assertEqual(
                        "需要管理员或科目管理员权限",
                        case["response"]["body"]["message"],
                    )
                    self.assertEqual(
                        0,
                        case["observed_get_effects"]["sql"]["export_select_attempts"],
                    )
                    self.assertEqual(
                        [user_id],
                        case["observed_get_effects"][
                            "user_last_active_changed_user_ids"
                        ],
                    )

            for prefix in (
                "auth-anonymous-redirect-login",
                "auth-administrator-bearer-only-redirect-login",
                "auth-ordinary-session-plus-administrator-bearer-redirect-login",
            ):
                case = self.by_id[f"{prefix}-{route}"]
                with self.subTest(route=route, prefix=prefix):
                    self.assertEqual(302, case["response"]["status"])
                    self.assertEqual(
                        ["/login"],
                        case["response"]["headers"]["Location"],
                    )
                    self.assertEqual(
                        0,
                        case["observed_get_effects"]["sql"]["statement_count"],
                    )
                    self.assertEqual(
                        [],
                        case["observed_get_effects"][
                            "user_last_active_changed_user_ids"
                        ],
                    )

    def test_modern_after_request_envelope_and_legacy_envelope_are_distinct(self) -> None:
        modern = self.by_id["subject-missing-default-modern"]["response"]
        legacy = self.by_id["subject-missing-default-legacy"]["response"]
        self.assertEqual(
            {"status", "meta", "count", "questions", "request_id", "message", "data"},
            set(modern["body"]),
        )
        self.assertEqual("success", modern["body"]["status"])
        self.assertEqual("", modern["body"]["message"])
        self.assertEqual(capture.FIXED_REQUEST_ID, modern["body"]["request_id"])
        self.assertEqual(
            {
                "meta": modern["body"]["meta"],
                "count": modern["body"]["count"],
                "questions": modern["body"]["questions"],
            },
            modern["body"]["data"],
        )
        self.assertEqual(
            {"meta", "count", "questions", "request_id"},
            set(legacy["body"]),
        )
        self.assertEqual(capture.FIXED_REQUEST_ID, legacy["body"]["request_id"])
        self.assertEqual(modern["body"]["meta"], legacy["body"]["meta"])
        self.assertEqual(modern["body"]["count"], legacy["body"]["count"])
        self.assertEqual(modern["body"]["questions"], legacy["body"]["questions"])

    def test_empty_multi_ascending_left_join_and_defaults_are_frozen(self) -> None:
        expected_ids = sorted(capture.QUESTIONS.values())
        self.assertEqual(-7, expected_ids[0])
        self.assertEqual(0, expected_ids[1])
        fixture = self.document["fixture"]["full_facts_fingerprint"]
        self.assertEqual((14, 15), (
            fixture["questions"]["row_count"],
            fixture["questions"]["column_count"],
        ))
        self.assertEqual((5, 9), (
            fixture["subjects"]["row_count"],
            fixture["subjects"]["column_count"],
        ))
        self.assertEqual(
            [capture.SUBJECTS["other"]],
            self.document["fixture"]["locked_subject_ids"],
        )
        self.assertEqual(
            [capture.SUBJECTS["other"]],
            [
                row["id"]
                for row in capture.subject_fixture_rows()
                if row["is_locked"]
            ],
        )
        for route in capture.ROUTES:
            empty = self.by_id[f"data-empty-table-{route}"]
            self.assertEqual((0, []), (
                empty["response"]["body"]["count"],
                capture.response_questions(empty),
            ))
            default = self.by_id[f"subject-missing-default-{route}"]
            self.assertEqual(expected_ids, capture.response_ids(default))
            self.assertEqual(
                {"scope": "question_center"},
                default["response"]["body"]["meta"],
            )
            items = {
                item["id"]: item
                for item in capture.response_questions(default)
            }
            nulls = items[capture.QUESTIONS["db_null"]]
            self.assertEqual(("", "", "", 1), (
                nulls["type"], nulls["content"],
                nulls["analysis"], nulls["difficulty"],
            ))
            self.assertEqual(1, items[capture.QUESTIONS["zero_id"]]["difficulty"])
            self.assertEqual(
                -2,
                items[capture.QUESTIONS["negative_subject"]]["difficulty"],
            )
            self.assertEqual(
                "导出证据・α／中文",
                items[capture.QUESTIONS["negative_id"]]["subject_name"],
            )
            for key in ("empty_subject_name", "orphan_subject", "null_subject"):
                self.assertEqual(
                    "默认科目",
                    items[capture.QUESTIONS[key]]["subject_name"],
                )
            locked_subject_item = items[capture.QUESTIONS["other_subject"]]
            self.assertEqual(
                (capture.SUBJECTS["other"], "其他科目"),
                (
                    locked_subject_item["subject_id"],
                    locked_subject_item["subject_name"],
                ),
            )

    def test_safe_load_null_empty_malformed_array_object_and_scalar_are_frozen(self) -> None:
        expected_array = {
            "options": ["甲", {"key": "B"}],
            "answer": [0, True, None],
            "tags": ["数学", ""],
        }
        expected_object = {
            "options": {"A": "甲"},
            "answer": {"value": "A"},
            "tags": {"topic": "代数"},
        }
        expected_scalar = {
            "options": "单值",
            "answer": 7,
            "tags": False,
        }
        for route in capture.ROUTES:
            items = {
                item["id"]: item
                for item in capture.response_questions(
                    self.by_id[f"subject-missing-default-{route}"]
                )
            }
            for field in ("options", "answer", "tags"):
                with self.subTest(route=route, field=field):
                    self.assertEqual([], items[capture.QUESTIONS["db_null"]][field])
                    self.assertIsNone(items[capture.QUESTIONS["json_null"]][field])
                    self.assertEqual([], items[capture.QUESTIONS["empty_raw"]][field])
                    self.assertEqual([], items[capture.QUESTIONS["malformed"]][field])
                    self.assertEqual(
                        expected_array[field],
                        items[capture.QUESTIONS["array"]][field],
                    )
                    self.assertEqual(
                        expected_object[field],
                        items[capture.QUESTIONS["object"]][field],
                    )
                    self.assertEqual(
                        expected_scalar[field],
                        items[capture.QUESTIONS["scalar"]][field],
                    )

    def test_raw_subject_first_value_and_sqlite_scoped_edges_are_frozen(self) -> None:
        all_ids = sorted(capture.QUESTIONS.values())
        primary_ids = sorted((
            capture.QUESTIONS["negative_id"],
            capture.QUESTIONS["db_null"],
            capture.QUESTIONS["json_null"],
            capture.QUESTIONS["empty_raw"],
            capture.QUESTIONS["malformed"],
            capture.QUESTIONS["array"],
            capture.QUESTIONS["object"],
            capture.QUESTIONS["scalar"],
        ))
        expected = {
            "missing-default": (all_ids, None),
            "empty": (all_ids, None),
            "blank": ([], " "),
            "zero": ([capture.QUESTIONS["zero_id"]], "0"),
            "negative": ([capture.QUESTIONS["negative_subject"]], "-1"),
            "exact": (primary_ids, str(capture.SUBJECTS["primary"])),
            "exact-type-ignored": (
                primary_ids,
                str(capture.SUBJECTS["primary"]),
            ),
            "no-match": ([], "999999"),
            "repeated-first-value": (primary_ids, str(capture.SUBJECTS["primary"])),
            "invalid": ([], "not-an-integer"),
            "unicode-nd": ([], capture.UNICODE_ND_PRIMARY),
            "int4-out-of-range": ([], capture.INT4_OUT_OF_RANGE),
        }
        for route in capture.ROUTES:
            for scenario, (ids, raw_meta) in expected.items():
                case = self.by_id[f"subject-{scenario}-{route}"]
                with self.subTest(route=route, scenario=scenario):
                    self.assertEqual(ids, capture.response_ids(case))
                    meta = case["response"]["body"]["meta"]
                    if raw_meta is None:
                        self.assertNotIn("subject_id", meta)
                    else:
                        self.assertEqual(raw_meta, meta["subject_id"])
                    self.assertEqual(
                        "SQLite from archived Flask testing configuration",
                        case["observed_get_effects"]["engine"],
                    )
                    self.assertEqual(
                        1,
                        case["observed_get_effects"]["sql"]["export_select_attempts"],
                    )
            type_ignored = self.by_id[f"subject-exact-type-ignored-{route}"]
            self.assertEqual(
                [
                    {"name": "subject_id", "value": str(capture.SUBJECTS["primary"])},
                    {"name": "type", "value": "definitely-not-matching"},
                ],
                type_ignored["request"]["query"],
            )
            self.assertEqual(
                {
                    "scope": "question_center",
                    "subject_id": str(capture.SUBJECTS["primary"]),
                },
                type_ignored["response"]["body"]["meta"],
            )
        self.assertIn(
            "not claimed as PostgreSQL behavior",
            self.document["engine_scope"]["non_claim"],
        )

    def test_accept_fault_sql_and_full_fact_fingerprints_are_frozen(self) -> None:
        safe_error = {
            "message": "An unexpected server error occurred.",
            "payload": None,
            "request_id": capture.FIXED_REQUEST_ID,
            "status": "error",
            "status_code": 500,
        }
        for route in capture.ROUTES:
            html = self.by_id[f"fault-html-{route}"]
            json_failure = self.by_id[f"fault-json-{route}"]
            self.assertEqual((500, "text"), (
                html["response"]["status"], html["response"]["body_kind"],
            ))
            self.assertEqual(
                "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>",
                html["response"]["body"],
            )
            self.assertEqual((500, "json", safe_error), (
                json_failure["response"]["status"],
                json_failure["response"]["body_kind"],
                json_failure["response"]["body"],
            ))
            for case in (html, json_failure):
                effects = case["observed_get_effects"]
                self.assertEqual(1, effects["sql"]["export_select_attempts"])
                self.assertEqual(0, effects["sql"]["fact_dml_attempts"])
                self.assertEqual(0, effects["sql"]["ddl_attempts"])
                self.assertTrue(effects["facts_unchanged"])
                self.assertEqual(
                    effects["facts_before"]["combined_sha256"],
                    effects["facts_after"]["combined_sha256"],
                )

        for case in self.document["cases"]:
            effects = case["observed_get_effects"]
            sql = effects["sql"]
            with self.subTest(case=case["case_id"]):
                self.assertTrue(effects["facts_match_case_fixture"])
                self.assertTrue(effects["facts_unchanged"])
                self.assertEqual(0, sql["fact_dml_attempts"])
                self.assertEqual(0, sql["ddl_attempts"])
                self.assertEqual(
                    sql["statement_count"], sql["classified_attempt_count"],
                )


if __name__ == "__main__":
    unittest.main()
