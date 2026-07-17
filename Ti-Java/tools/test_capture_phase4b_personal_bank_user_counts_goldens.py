#!/usr/bin/env python3
"""Contract checks for fixed-commit personal-bank user-count read goldens."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_user_counts_goldens as capture  # noqa: E402


class PersonalBankUserCountsGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_provenance_redaction_hashes_and_fixed_commit_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            "ti.phase4b.personal-bank-user-counts-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(capture.LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(len(capture.CASE_SPECS), document["case_count"])
        self.assertEqual(
            {spec.case_id for spec in capture.CASE_SPECS}, set(self.by_id)
        )
        self.assertEqual(
            document["case_payload_sha256"],
            capture.sha256_json(document["cases"]),
        )
        self.assertEqual(
            document["document_payload_sha256"],
            capture.document_payload_sha256(document),
        )
        self.assertEqual(capture.render_document(document), self.serialized)

        provenance = document["provenance"]
        capture_tool_sha = hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest()
        capture_test_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.assertEqual(capture_tool_sha, provenance["capture_tool"]["sha256"])
        self.assertEqual(capture_test_sha, provenance["capture_test"]["sha256"])
        self.assertEqual(capture_tool_sha, provenance["hashes"]["capture_tool_sha256"])
        self.assertEqual(capture_test_sha, provenance["hashes"]["capture_test_sha256"])
        self.assertEqual(
            document["case_payload_sha256"],
            provenance["hashes"]["case_payload_sha256"],
        )
        self.assertRegex(provenance["runtime_versions"]["sqlalchemy"], r"^2\.")

        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("@test.example.com", self.serialized)
        self.assertNotRegex(
            self.serialized, r"Bearer (?!<redacted)[A-Za-z0-9_-]+"
        )
        self.assertNotRegex(
            self.serialized,
            re.compile(r'"last_active":\s*"20\d\d-', re.MULTILINE),
        )
        for case in document["cases"]:
            for cookie in case["response"]["headers"].get("Set-Cookie", []):
                self.assertEqual("<redacted-session-cookie>", cookie)

        recaptured = capture.capture_document(REPOSITORY_ROOT)
        self.assertEqual(self.serialized, capture.render_document(recaptured))

    def test_complete_archive_routes_sources_and_caller_reference_are_fixed(self) -> None:
        source = self.document["legacy_source_attestation"]
        archive = source["complete_app_archive"]
        self.assertTrue(archive["complete_app_tree_verified"])
        self.assertEqual(capture.LEGACY_COMMIT, archive["archive_commit"])
        self.assertGreaterEqual(archive["extracted_file_count"], 600)
        self.assertEqual(set(capture.KEY_SOURCE_FILES), set(source["key_sources"]))
        self.assertEqual(
            "git show from verified fixed commit",
            source["key_sources"]["requirements.txt"]["transport"],
        )
        self.assertEqual(
            "git show from verified fixed commit",
            source["key_sources"]["tests/test_user_bank_quiz_record.py"]["transport"],
        )
        handler_sha = source["key_sources"][
            "app/modules/user_bank/routes/api_quiz.py"
        ]["sha256"]
        self.assertEqual(
            handler_sha,
            self.document["provenance"]["hashes"]["legacy_handler_source_sha256"],
        )
        matrix = source["frozen_route_matrix"]
        self.assertFalse(matrix["caller_inventory_complete"])
        self.assertEqual(
            {"6858f6fa506f", "006913d0d956"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["target_module"] == "personalbank"
            and row["migration_status"] == "pending"
            for row in matrix["selected_rows"]
        ))
        callers = source["caller_evidence"]
        self.assertEqual(
            "docs/refactor/phase4b/personal-bank-user-counts-callers.json",
            callers["path"],
        )
        if CALLERS.is_file():
            self.assertTrue(callers["present"])
            self.assertTrue(callers["caller_attestation_complete"])
            self.assertEqual(
                hashlib.sha256(CALLERS.read_bytes()).hexdigest(), callers["sha256"]
            )
        else:
            self.assertFalse(callers["present"])
            self.assertFalse(callers["caller_attestation_complete"])

    def test_dual_alias_authentication_precedence_and_activity_are_fixed(self) -> None:
        expected_status = {
            "auth-session-owner-api-alias": 200,
            "auth-bearer-owner-api-alias": 200,
            "auth-bearer-precedes-session-api-alias": 403,
            "auth-invalid-bearer-falls-back-session-api-alias": 200,
            "auth-state-invalid-bearer-does-not-fallback-session-api-alias": 401,
            "auth-anonymous-api-alias": 401,
            "auth-session-owner-web-alias": 200,
            "auth-bearer-owner-web-alias": 302,
            "auth-bearer-precedes-session-web-alias": 302,
            "auth-invalid-bearer-falls-back-session-web-alias": 200,
            "auth-state-invalid-bearer-does-not-fallback-session-web-alias": 302,
            "auth-anonymous-web-alias": 302,
        }
        for case_id, status in expected_status.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(status, self.by_id[case_id]["response"]["status"])
        self.assertEqual(
            403, self.by_id["auth-bearer-precedes-session-api-alias"]["response"]["body"]["code"]
        )
        self.assertEqual(
            [], self.by_id["auth-bearer-precedes-session-api-alias"]
            ["observed_get_effects"]["user_last_active_changed_user_ids"]
        )
        for route in capture.ROUTES:
            invalid = self.by_id[f"auth-invalid-bearer-falls-back-session-{route}"]
            self.assertEqual(
                [capture.ACTORS["owner"]],
                invalid["observed_get_effects"]["user_last_active_changed_user_ids"],
            )
        state_invalid = self.by_id[
            "auth-state-invalid-bearer-does-not-fallback-session-api-alias"
        ]
        self.assertEqual("unauthorized", state_invalid["response"]["body"]["status"])
        self.assertIn("会话已失效", state_invalid["response"]["body"]["message"])
        self.assertEqual(
            [], state_invalid["observed_get_effects"]["user_last_active_changed_user_ids"]
        )
        for case_id in (
            "auth-bearer-owner-web-alias",
            "auth-bearer-precedes-session-web-alias",
            "auth-state-invalid-bearer-does-not-fallback-session-web-alias",
            "auth-anonymous-web-alias",
        ):
            self.assertEqual(
                ["/login"], self.by_id[case_id]["response"]["headers"]["Location"]
            )

    def test_access_status_public_shared_expiry_and_fetchone_boundaries_are_fixed(self) -> None:
        for case_id in ("access-status-null-owner", "access-status-two-owner"):
            self.assertEqual(capture.EMPTY_COUNTS, capture.response_counts(self.by_id[case_id]))
        for route in capture.ROUTES:
            self.assertEqual(
                403, self.by_id[f"access-status-zero-{route}"]["response"]["status"]
            )
            self.assertEqual(
                capture.EMPTY_COUNTS,
                capture.response_counts(self.by_id[f"access-public-other-{route}"]),
            )
            self.assertEqual(
                403, self.by_id[f"access-missing-{route}"]["response"]["status"]
            )
        self.assertEqual(
            403, self.by_id["access-private-other-forbidden"]["response"]["status"]
        )
        for case_id in (
            "access-shared-future", "access-shared-null-expiry",
            "access-shared-empty-expiry", "access-shared-cross-bank-record",
        ):
            data = capture.response_counts(self.by_id[case_id])
            self.assertEqual((9, 0, 0), (
                data["total"], data["favorites"], data["mistakes"]
            ))
        for case_id in (
            "access-shared-equal-now-forbidden",
            "access-shared-expired-forbidden",
            "access-shared-inactive-forbidden",
            "access-shared-fetchone-first-row",
        ):
            self.assertEqual(403, self.by_id[case_id]["response"]["status"])
        self.assertEqual(
            400,
            self.by_id["access-shared-malformed-expiry-value-error"]["response"]["status"],
        )
        self.assertEqual(
            500,
            self.by_id["access-shared-aware-expiry-type-error"]["response"]["status"],
        )
        contract = self.document["access_contract"]
        self.assertEqual("denied", contract["equal_to_now"])
        self.assertEqual("accepted", contract["null_or_empty_expiry"])
        self.assertIn("fetchone without ORDER BY", contract["multiple_share_rows"])
        self.assertIn("grants access", contract["cross_bank_share_coherence"])
        self.assertFalse(contract["admin_bypass"])

    def test_filters_raw_mapping_duplicates_counts_and_shuffle_are_fixed(self) -> None:
        for route in capture.ROUTES:
            self.assertEqual(
                capture.BASE_COUNTS,
                capture.response_counts(self.by_id[f"auth-session-owner-{route}"]),
            )
            self.assertEqual(
                capture.EMPTY_COUNTS,
                capture.response_counts(self.by_id[f"data-empty-{route}"]),
            )
            favorite = capture.response_counts(
                self.by_id[f"filter-source-favorites-{route}"]
            )
            self.assertEqual((5, 5, 3), (
                favorite["total"], favorite["favorites"], favorite["mistakes"]
            ))
            self.assertEqual(
                ["判断题", "选择题", "选择题", "简答题"], favorite["types"]
            )
        self.assertEqual(
            {
                "total": 2, "favorites": 2, "mistakes": 0,
                "types": ["选择题"], "shuffle_options_available": True,
            },
            capture.response_counts(self.by_id["filter-q-type-choice"]),
        )
        self.assertEqual(
            capture.BASE_COUNTS,
            capture.response_counts(self.by_id["filter-q-type-all-uppercase"]),
        )
        self.assertEqual(
            capture.BASE_COUNTS,
            capture.response_counts(self.by_id["filter-source-case-sensitive-fallback"]),
        )
        self.assertEqual(
            capture.response_counts(self.by_id["filter-q-type-choice"]),
            capture.response_counts(self.by_id["filter-q-type-duplicate-first-wins"]),
        )
        self.assertEqual(
            capture.response_counts(self.by_id["filter-source-favorites-api-alias"]),
            capture.response_counts(self.by_id["filter-source-duplicate-first-wins"]),
        )
        duplicate_tag = self.by_id["filter-tag-duplicate-first-all-wins"]
        self.assertEqual(capture.BASE_COUNTS, capture.response_counts(duplicate_tag))
        self.assertEqual(0, duplicate_tag["observed_get_effects"]["sql"]["ddl_attempts"])
        self.assertEqual(
            [["q_type", "选择题"], ["q_type", "简答题"]],
            self.by_id["filter-q-type-duplicate-first-wins"]["request"]["query"],
        )
        self.assertEqual(
            [["source", "favorites"], ["source", "mistakes"]],
            self.by_id["filter-source-duplicate-first-wins"]["request"]["query"],
        )
        self.assertEqual(
            [["tag", "all"], ["tag", "重点"]],
            duplicate_tag["request"]["query"],
        )
        self.assertEqual(
            ["判断题", "简答题", "填空题", "多选题", "选择题", "选择题", "简答题"],
            capture.BASE_COUNTS["types"],
        )
        contract = self.document["legacy_query_contract"]
        self.assertTrue(contract["favorites_source_duplicate_query"])
        self.assertTrue(contract["mistakes_source_duplicate_query"])
        self.assertFalse(contract["types_post_mapping_deduplication"])
        self.assertIn("first value", contract["duplicate_query_key_resolution"])
        self.assertIsNone(contract["pagination"])
        self.assertIsNone(contract["time_window"])

    def test_exact_query_order_duplicate_count_and_bind_shapes_are_fixed(self) -> None:
        baseline = self.by_id["auth-session-owner-api-alias"]["observed_get_effects"]["sql"]
        self.assertEqual(
            [
                "personal_bank_user_counts_bank_access_probe",
                "personal_bank_user_counts_total_all",
                "personal_bank_user_counts_favorites_count",
                "personal_bank_user_counts_mistakes_count",
                "personal_bank_user_counts_types_all",
            ],
            baseline["personal_bank_query_sequence"],
        )
        favorite = self.by_id[
            "filter-source-favorites-api-alias"
        ]["observed_get_effects"]["sql"]
        self.assertEqual(2, favorite["classification_attempts"][
            "personal_bank_user_counts_favorites_count"
        ])
        self.assertEqual(
            [
                "personal_bank_user_counts_bank_access_probe",
                "personal_bank_user_counts_favorites_count",
                "personal_bank_user_counts_favorites_count",
                "personal_bank_user_counts_mistakes_count",
                "personal_bank_user_counts_types_favorites",
            ],
            favorite["personal_bank_query_sequence"],
        )
        choice = self.by_id["filter-q-type-choice"]["observed_get_effects"]["sql"]
        count_rows = [
            row for row in choice["statements"]
            if row["classification"] in capture.STATS_CLASSIFICATIONS
        ]
        self.assertEqual(4, len(count_rows))
        self.assertTrue(all(
            capture.BANKS["owner_active"] in row["parameters"] for row in count_rows
        ))
        self.assertTrue(all(
            "single_choice" in row["parameters"] for row in count_rows
        ))

    def test_tag_ddl_legacy_migration_attempt_and_sa2_failure_are_fixed(self) -> None:
        for route in capture.ROUTES:
            case = self.by_id[f"tag-normalized-sa2-empty-{route}"]
            self.assertEqual(capture.EMPTY_COUNTS, capture.response_counts(case))
            sql = case["observed_get_effects"]["sql"]
            self.assertEqual(3, sql["ddl_attempts"])
            self.assertEqual(
                ["raw_sa2_new_tag_presence_probe"],
                [row["classification"] for row in sql["raw_connection_execute_attempts"]],
            )
        legacy = self.by_id["tag-legacy-migration-sa2-empty"]
        self.assertEqual(capture.EMPTY_COUNTS, capture.response_counts(legacy))
        ledger = legacy["observed_get_effects"]["sql"]
        self.assertEqual(6, ledger["ddl_attempts"])
        self.assertEqual(
            [
                "raw_sa2_new_tag_presence_probe",
                "raw_sa2_legacy_tag_migration_delete",
            ],
            [row["classification"] for row in ledger["raw_connection_execute_attempts"]],
        )
        self.assertTrue(all(
            row["exception_type"] == "ArgumentError"
            and row["failed_before_cursor_execution"]
            for row in ledger["raw_connection_execute_attempts"]
        ))
        self.assertEqual(0, ledger["business_table_dml_attempt_count"])
        contract = self.document["tag_compatibility_contract"]
        self.assertIn("ArgumentError", contract["observed_failure"])
        self.assertIn("SQLite-only", contract["postgresql_additional_incompatibility"])
        self.assertFalse(contract["migration_commit_reached_in_observed_runtime"])
        self.assertEqual("not established by this evidence", contract["approved_java_behavior"])

    def test_sqlite_optional_fallback_and_postgresql_poison_simulation_are_distinct(self) -> None:
        sqlite_favorite = capture.response_counts(
            self.by_id["fault-favorites-sqlite-continues"]
        )
        poisoned_favorite = capture.response_counts(
            self.by_id["fault-favorites-postgresql-poison-simulation"]
        )
        sqlite_mistake = capture.response_counts(
            self.by_id["fault-mistakes-sqlite-continues"]
        )
        poisoned_mistake = capture.response_counts(
            self.by_id["fault-mistakes-postgresql-poison-simulation"]
        )
        self.assertEqual((0, 3, capture.BASE_COUNTS["types"]), (
            sqlite_favorite["favorites"], sqlite_favorite["mistakes"],
            sqlite_favorite["types"],
        ))
        self.assertEqual((0, 0, []), (
            poisoned_favorite["favorites"], poisoned_favorite["mistakes"],
            poisoned_favorite["types"],
        ))
        self.assertEqual((5, 0, capture.BASE_COUNTS["types"]), (
            sqlite_mistake["favorites"], sqlite_mistake["mistakes"],
            sqlite_mistake["types"],
        ))
        self.assertEqual((5, 0, []), (
            poisoned_mistake["favorites"], poisoned_mistake["mistakes"],
            poisoned_mistake["types"],
        ))
        poison_ledger = self.by_id[
            "fault-favorites-postgresql-poison-simulation"
        ]["observed_get_effects"]["sql"]
        self.assertTrue(poison_ledger["postgresql_poison_simulation"])
        self.assertEqual(
            [
                "synthetic_targeted_failure",
                "synthetic_postgresql_current_transaction_is_aborted",
                "synthetic_postgresql_current_transaction_is_aborted",
            ],
            [event["kind"] for event in poison_ledger["fault_events"]],
        )
        contract = self.document["failure_and_transaction_contract"]
        self.assertIn("not direct PostgreSQL", contract["postgresql_poison_simulation"])
        self.assertIn("16.14", contract["remaining_gate"])
        self.assertIn("18.4", contract["remaining_gate"])

    def test_error_negotiation_business_effects_and_deferred_http_scope_close(self) -> None:
        for route in capture.ROUTES:
            default = self.by_id[f"fault-total-default-{route}"]
            json_case = self.by_id[f"fault-total-json-{route}"]
            self.assertEqual(500, default["response"]["status"])
            self.assertEqual(500, json_case["response"]["status"])
            self.assertNotIn("synthetic user-counts", default["response"]["body_text"])
            self.assertNotIn("synthetic user-counts", json_case["response"]["body_text"])
            self.assertEqual("json", json_case["response"]["body_kind"])
            self.assertEqual(
                "json" if route == "api-alias" else "text",
                default["response"]["body_kind"],
            )
        for spec in capture.CASE_SPECS:
            case = self.by_id[spec.case_id]
            effects = case["observed_get_effects"]
            self.assertTrue(all(effects["business_tables_match_case_fixture"].values()))
            if not spec.tag_fixture == "legacy":
                self.assertTrue(all(effects["business_tables_unchanged"].values()))
            self.assertTrue(effects["users_identity_unchanged"])
        route_status = self.document["route_status"]
        self.assertEqual("pending", route_status["migration_status"])
        self.assertFalse(route_status["production_cutover"])
        self.assertFalse(route_status["controller_added"])
        self.assertFalse(route_status["openapi_delta"])
        self.assertFalse(route_status["route_delta"])
        self.assertEqual(
            capture.FIXED_NOW_BJ.isoformat(sep=" "),
            self.document["fixed_beijing_time"],
        )


if __name__ == "__main__":
    unittest.main()
