#!/usr/bin/env python3
"""Contract checks for fixed-commit personal-bank usage-stats goldens."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4b/golden-personal-bank-usage-stats-reads.json"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-usage-stats-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_usage_stats_goldens as capture  # noqa: E402


class PersonalBankUsageStatsGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_provenance_hashes_redaction_and_fixed_commit_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(capture.LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(32, document["case_count"])
        self.assertEqual(
            {spec.case_id for spec in capture.CASE_SPECS},
            set(self.by_id),
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

        recaptured = capture.capture_document(REPOSITORY_ROOT)
        self.assertEqual(self.serialized, capture.render_document(recaptured))

    def test_complete_archive_routes_sources_and_caller_authority_are_fixed(self) -> None:
        source = self.document["legacy_source_attestation"]
        archive = source["complete_app_archive"]
        self.assertTrue(archive["complete_app_tree_verified"])
        self.assertEqual(capture.LEGACY_COMMIT, archive["archive_commit"])
        self.assertGreaterEqual(archive["extracted_file_count"], 600)
        self.assertEqual(set(capture.KEY_SOURCE_FILES), set(source["key_sources"]))
        handler_sha = source["key_sources"][
            "app/modules/user_bank/routes/api_shares.py"
        ]["sha256"]
        self.assertEqual(
            "ea2074c97cd5f6840dd1f6e738404d41c08f4b3e3a0b8cb7f8886ec2a58e4993",
            handler_sha,
        )
        self.assertEqual(
            handler_sha,
            self.document["provenance"]["hashes"]["legacy_handler_source_sha256"],
        )
        matrix = source["frozen_route_matrix"]
        self.assertFalse(matrix["caller_inventory_complete"])
        self.assertEqual(
            {"d67a16965b08", "22aecd49a3c2"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["target_module"] == "personalbank"
            and row["migration_status"] == "pending"
            for row in matrix["selected_rows"]
        ))
        callers = source["complete_caller_attestation"]
        self.assertEqual(
            hashlib.sha256(CALLERS.read_bytes()).hexdigest(),
            callers["sha256"],
        )
        self.assertEqual(
            callers["sha256"],
            self.document["provenance"]["hashes"]["caller_evidence_sha256"],
        )
        self.assertTrue(callers["caller_attestation_complete"])

    def test_dual_alias_authentication_precedence_and_no_fallback_are_fixed(self) -> None:
        expected_status = {
            "auth-session-owner-api-alias": 200,
            "auth-bearer-owner-api-alias": 200,
            "auth-bearer-precedes-session-api-alias": 403,
            "auth-state-invalid-bearer-does-not-fallback-session-api-alias": 401,
            "auth-anonymous-api-alias": 401,
            "auth-session-owner-web-alias": 200,
            "auth-bearer-owner-web-alias": 302,
            "auth-bearer-precedes-session-web-alias": 302,
            "auth-state-invalid-bearer-does-not-fallback-session-web-alias": 302,
            "auth-anonymous-web-alias": 302,
        }
        for case_id, status in expected_status.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(status, self.by_id[case_id]["response"]["status"])

        precedence = self.by_id["auth-bearer-precedes-session-api-alias"]
        self.assertEqual(403, precedence["response"]["body"]["code"])
        self.assertEqual([], precedence["observed_get_effects"]["user_last_active_changed_user_ids"])
        state_invalid = self.by_id[
            "auth-state-invalid-bearer-does-not-fallback-session-api-alias"
        ]
        self.assertEqual("unauthorized", state_invalid["response"]["body"]["status"])
        self.assertIn("会话已失效", state_invalid["response"]["body"]["message"])
        self.assertEqual([], state_invalid["observed_get_effects"]["user_last_active_changed_user_ids"])
        for case_id in (
            "auth-bearer-owner-web-alias",
            "auth-bearer-precedes-session-web-alias",
            "auth-state-invalid-bearer-does-not-fallback-session-web-alias",
            "auth-anonymous-web-alias",
        ):
            self.assertEqual(["/login"], self.by_id[case_id]["response"]["headers"]["Location"])

    def test_overlap_expiry_and_count_semantics_match_on_both_aliases(self) -> None:
        expected = {
            "bank_id": capture.BANKS["owner_active"],
            "is_public": False,
            "owner_id": capture.ACTORS["owner"],
            "owner_count": 1,
            "shared_users": 5,
            "public_users": 3,
            "total_users": 7,
            "total_users_excluding_owner": 6,
        }
        for route in capture.ROUTES:
            for case_id in (
                f"auth-session-owner-{route}",
                f"data-overlap-time-boundaries-{route}",
                f"data-query-parameters-ignored-{route}",
            ):
                self.assertEqual(expected, capture.response_stats(self.by_id[case_id]))
        self.assertEqual(expected, capture.response_stats(
            self.by_id["auth-bearer-owner-api-alias"]
        ))

        contract = self.document["usage_count_contract"]
        self.assertEqual("expires_at < now_bj()", contract["expired_when"])
        self.assertEqual("valid", contract["equal_to_now"])
        self.assertEqual("valid", contract["null_expiry"])
        self.assertEqual("valid", contract["empty_string_expiry_fixture"])
        self.assertEqual("expired", contract["truthy_malformed_expiry"])
        self.assertEqual("expired", contract["aware_vs_naive_comparison_error"])
        self.assertFalse(contract["shared_and_public_categories_mutually_subtracted"])
        self.assertEqual(1, contract["owner_count"])
        self.assertFalse(contract["is_public_null_serializes_as"])

    def test_falsey_expiry_and_signed_user_id_boundaries_are_explicit(self) -> None:
        shares = {row["id"]: row for row in capture.full_share_rows()}
        self.assertEqual("", shares[capture.SHARES["empty_expiry"]]["expires_at"])
        self.assertEqual(
            "malformed-expiry",
            shares[capture.SHARES["malformed_expiry"]]["expires_at"],
        )
        records = capture.full_record_rows()
        public = capture.full_public_rows()
        self.assertTrue(any(
            row["user_id"] == 0 and row["status"] == 1 for row in records
        ))
        self.assertTrue(any(
            row["user_id"] == capture.ACTORS["signed_negative"] for row in records
        ))
        self.assertTrue(any(row["user_id"] == 0 for row in public))
        self.assertTrue(any(
            row["user_id"] == capture.ACTORS["signed_negative"] for row in public
        ))
        contract = self.document["usage_count_contract"]
        self.assertIn("int(value or 0)", contract["user_id_conversion"])
        self.assertIn("ignored", contract["zero_user_id"])
        self.assertIn("counted", contract["negative_user_id"])
        boundaries = self.document["fixture"]["boundary_rows"]
        self.assertEqual(0, boundaries["zero_user_id_ignored_in_both_sources"])
        self.assertLess(boundaries["negative_user_id_counted_in_both_sources"], 0)

    def test_empty_missing_inactive_non_owner_and_ignored_queries_close(self) -> None:
        empty_expected = {
            "bank_id": capture.BANKS["owner_active"],
            "is_public": False,
            "owner_id": capture.ACTORS["owner"],
            "owner_count": 1,
            "shared_users": 0,
            "public_users": 0,
            "total_users": 1,
            "total_users_excluding_owner": 0,
        }
        for route in capture.ROUTES:
            self.assertEqual(empty_expected, capture.response_stats(
                self.by_id[f"data-owner-active-empty-{route}"]
            ))
            ignored = self.by_id[f"data-query-parameters-ignored-{route}"]
            self.assertEqual(
                [["scope", "all"], ["at", "past"], ["page", "2"], ["page", "3"]],
                ignored["request"]["query"],
            )
            missing = self.by_id[f"bank-missing-{route}"]
            inactive = self.by_id[f"bank-inactive-{route}"]
            forbidden = self.by_id[f"bank-non-owner-{route}"]
            self.assertEqual(404, missing["response"]["status"])
            self.assertEqual("题库不存在或已被删除", missing["response"]["body"]["message"])
            self.assertEqual(404, inactive["response"]["status"])
            self.assertEqual("题库不存在或已被删除", inactive["response"]["body"]["message"])
            self.assertEqual(403, forbidden["response"]["status"])
            self.assertEqual("无权查看（仅创建者可见）", forbidden["response"]["body"]["message"])
            for case in (missing, inactive, forbidden):
                sql = case["observed_get_effects"]["sql"]
                self.assertEqual(1, sql["bank_probe_attempts"])
                self.assertEqual(0, sql["shared_user_select_attempts"])
                self.assertEqual(0, sql["public_user_select_attempts"])

    def test_three_statement_sequence_and_single_bank_id_binds_are_fixed(self) -> None:
        expected_sequence = [
            "personal_bank_usage_bank_probe",
            "personal_bank_usage_shared_users_select",
            "personal_bank_usage_public_users_select",
        ]
        baseline = self.by_id["data-overlap-time-boundaries-api-alias"]
        sql = baseline["observed_get_effects"]["sql"]
        self.assertEqual(expected_sequence, sql["personal_bank_query_sequence"])
        self.assertEqual(1, sql["bank_probe_bind_count"])
        self.assertEqual(1, sql["shared_user_select_bind_count"])
        self.assertEqual(1, sql["public_user_select_bind_count"])
        business = [
            item for item in sql["statements"]
            if item["classification"] in expected_sequence
        ]
        self.assertEqual(3, len(business))
        self.assertTrue(capture.is_bank_probe(business[0]["sql"]))
        self.assertTrue(capture.is_shared_user_select(business[1]["sql"]))
        self.assertTrue(capture.is_public_user_select(business[2]["sql"]))
        self.assertEqual(
            [[capture.BANKS["owner_active"]]] * 3,
            [item["parameters"] for item in business],
        )

    def test_optional_query_failures_degrade_independently(self) -> None:
        for route in capture.ROUTES:
            shared = capture.response_stats(
                self.by_id[f"fault-shared-query-degrades-{route}"]
            )
            public = capture.response_stats(
                self.by_id[f"fault-public-query-degrades-{route}"]
            )
            both = capture.response_stats(
                self.by_id[f"fault-both-optional-queries-degrade-{route}"]
            )
            self.assertEqual((0, 3, 4, 3), (
                shared["shared_users"], shared["public_users"],
                shared["total_users"], shared["total_users_excluding_owner"],
            ))
            self.assertEqual((5, 0, 6, 5), (
                public["shared_users"], public["public_users"],
                public["total_users"], public["total_users_excluding_owner"],
            ))
            self.assertEqual((0, 0, 1, 0), (
                both["shared_users"], both["public_users"],
                both["total_users"], both["total_users_excluding_owner"],
            ))
            for case_id in (
                f"fault-shared-query-degrades-{route}",
                f"fault-public-query-degrades-{route}",
                f"fault-both-optional-queries-degrade-{route}",
            ):
                case = self.by_id[case_id]
                self.assertEqual(200, case["response"]["status"])
                self.assertEqual(
                    [
                        "personal_bank_usage_bank_probe",
                        "personal_bank_usage_shared_users_select",
                        "personal_bank_usage_public_users_select",
                    ],
                    case["observed_get_effects"]["sql"]["personal_bank_query_sequence"],
                )

    def test_bank_probe_fault_negotiation_and_safe_surfaces_are_fixed(self) -> None:
        safe_json = {
            "status": "error",
            "message": "An unexpected server error occurred.",
            "status_code": 500,
            "payload": None,
            "request_id": capture.FIXED_REQUEST_ID,
        }
        for case_id in (
            "fault-bank-probe-default-api-alias",
            "fault-bank-probe-json-api-alias",
            "fault-bank-probe-json-web-alias",
        ):
            case = self.by_id[case_id]
            self.assertEqual(500, case["response"]["status"])
            self.assertEqual("json", case["response"]["body_kind"])
            self.assertEqual(safe_json, case["response"]["body"])
            self.assertNotIn("synthetic personal-bank", case["response"]["body_text"])
        web = self.by_id["fault-bank-probe-default-web-alias"]
        self.assertEqual(500, web["response"]["status"])
        self.assertEqual("text", web["response"]["body_kind"])
        self.assertEqual(
            "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>",
            web["response"]["body"],
        )
        self.assertNotIn("synthetic personal-bank", web["response"]["body_text"])

    def test_four_business_tables_zero_write_and_last_active_scope_close(self) -> None:
        self.assertEqual(
            list(capture.BUSINESS_TABLES),
            self.document["request_effect_scope"]["business_tables"],
        )
        for spec in capture.CASE_SPECS:
            effects = self.by_id[spec.case_id]["observed_get_effects"]
            sql = effects["sql"]
            self.assertTrue(all(effects["business_tables_match_case_fixture"].values()))
            self.assertTrue(all(effects["business_tables_unchanged"].values()))
            self.assertEqual(
                {table: 0 for table in capture.BUSINESS_TABLES},
                sql["business_table_dml_attempts"],
            )
            self.assertEqual(0, sql["business_table_dml_attempt_count"])
            self.assertEqual(0, sql["ddl_attempts"])
            self.assertEqual(sql["classified_attempt_count"], sql["statement_count"])
            expected_activity = []
            if spec.session_actor is not None and spec.bearer_actor is None:
                expected_activity = [capture.ACTORS[spec.session_actor]]
            self.assertEqual(
                expected_activity,
                effects["user_last_active_changed_user_ids"],
            )
            self.assertEqual(len(expected_activity), sql["user_last_active_dml_attempts"])

    def test_fixed_beijing_clock_and_deferred_http_scope_remain_explicit(self) -> None:
        self.assertEqual(
            capture.FIXED_NOW_BJ.isoformat(sep=" "),
            self.document["fixed_beijing_time"],
        )
        route_status = self.document["route_status"]
        self.assertEqual("pending", route_status["migration_status"])
        self.assertFalse(route_status["production_cutover"])
        self.assertFalse(route_status["controller_added"])
        self.assertFalse(route_status["openapi_delta"])
        self.assertFalse(route_status["route_delta"])
        self.assertIn("fixed now_bj", self.document["isolation"])


if __name__ == "__main__":
    unittest.main()
