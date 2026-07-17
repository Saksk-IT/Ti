#!/usr/bin/env python3
"""Contract checks for fixed-commit personal-bank all-shares goldens."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4b/golden-personal-bank-all-shares-reads.json"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-all-shares-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_all_shares_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "d7ce2c38f894a9eeb0b38b842c05b5f0a3947c37484a51959cfe61b0ee856e0b"
CASE_PAYLOAD_SHA256 = "86420e5da42d18e2165b722d9dd40cbdeedc669ee23c5f86591ce58b277a9cb0"
DOCUMENT_PAYLOAD_SHA256 = "e9f1b62c90f848bb0e9b4a90afa0a559de9cf9fcadf3cbf745314b8ebbb29b16"
CAPTURE_TOOL_SHA256 = "715ffb5903582ff0880647b6b436f3b0cff40d5090cc1916a54b7f4037fe0d53"
CALLER_FILE_SHA256 = "e20678ebb091db7840c37b42b9a592250a4f499ff772d775ed87a3b5e0942bbb"
CALLER_ATTESTATION_SHA256 = "1aa666fdd04e15e4509e8ee6c45d00ff4783141c9b767bd7a0fa7082e20d79d0"


def expected_case_ids() -> set[str]:
    return {
        "auth-session-mixed-api-alias",
        "auth-bearer-api-alias",
        "auth-bearer-precedes-session-api-alias",
        "auth-invalid-bearer-falls-back-session-api-alias",
        "auth-anonymous-api-alias",
        "auth-state-invalid-bearer-api-alias",
        "data-empty-api-alias",
        "data-query-parameters-ignored-api-alias",
        "data-configured-share-base-api-alias",
        "fault-default-api-alias",
        "fault-json-api-alias",
        "auth-session-mixed-web-alias",
        "auth-bearer-web-alias",
        "auth-bearer-precedes-session-web-alias",
        "auth-invalid-bearer-falls-back-session-web-alias",
        "auth-anonymous-web-alias",
        "data-empty-web-alias",
        "data-query-parameters-ignored-web-alias",
        "fault-default-web-alias",
        "fault-json-web-alias",
    }


def response_shares(case: dict[str, object]) -> list[dict[str, object]]:
    return case["response"]["body"]["data"]["shares"]


class PersonalBankAllSharesGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_checked_in_hashes_case_set_redaction_and_fixed_commit_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            GOLDEN_FILE_SHA256,
            hashlib.sha256(self.serialized_bytes).hexdigest(),
        )
        self.assertEqual(
            "ti.phase4b.personal-bank-all-shares-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(20, document["case_count"])
        self.assertEqual(expected_case_ids(), set(self.by_id))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, document["document_payload_sha256"])
        self.assertEqual(
            DOCUMENT_PAYLOAD_SHA256,
            capture.document_payload_sha256(document),
        )
        self.assertEqual(capture.render_document(document), self.serialized)
        capture.assert_case_contracts(document["cases"])
        self.assertEqual(
            CAPTURE_TOOL_SHA256,
            hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest(),
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

    def test_archive_routes_and_complete_caller_authority_are_attested(self) -> None:
        source = self.document["legacy_source_attestation"]
        archive = source["complete_app_archive"]
        self.assertTrue(archive["complete_app_tree_verified"])
        self.assertEqual(LEGACY_COMMIT, archive["archive_commit"])
        self.assertGreaterEqual(archive["extracted_file_count"], 600)
        self.assertEqual(set(capture.KEY_SOURCE_FILES), set(source["key_sources"]))
        self.assertEqual(
            "ea2074c97cd5f6840dd1f6e738404d41c08f4b3e3a0b8cb7f8886ec2a58e4993",
            source["key_sources"]["app/modules/user_bank/routes/api_shares.py"]["sha256"],
        )
        matrix = source["frozen_route_matrix"]
        self.assertFalse(matrix["caller_inventory_complete"])
        self.assertEqual(
            {"a6fda3638fc3", "0fdd3026f636"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["target_module"] == "personalbank"
            and row["migration_status"] == "pending"
            for row in matrix["selected_rows"]
        ))
        callers = source["complete_caller_attestation"]
        self.assertEqual(CALLER_FILE_SHA256, callers["sha256"])
        self.assertEqual(CALLER_FILE_SHA256, hashlib.sha256(CALLERS.read_bytes()).hexdigest())
        self.assertEqual(CALLER_ATTESTATION_SHA256, callers["attestation_sha256"])
        self.assertTrue(callers["caller_attestation_complete"])

    def test_dual_alias_authentication_precedence_and_state_validation_are_fixed(self) -> None:
        expected_status = {
            "auth-session-mixed-api-alias": 200,
            "auth-bearer-api-alias": 200,
            "auth-bearer-precedes-session-api-alias": 200,
            "auth-invalid-bearer-falls-back-session-api-alias": 200,
            "auth-anonymous-api-alias": 401,
            "auth-state-invalid-bearer-api-alias": 401,
            "auth-session-mixed-web-alias": 200,
            "auth-bearer-web-alias": 302,
            "auth-bearer-precedes-session-web-alias": 302,
            "auth-invalid-bearer-falls-back-session-web-alias": 200,
            "auth-anonymous-web-alias": 302,
        }
        for case_id, status in expected_status.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(status, self.by_id[case_id]["response"]["status"])
        for case_id in (
            "auth-bearer-web-alias",
            "auth-bearer-precedes-session-web-alias",
            "auth-anonymous-web-alias",
        ):
            self.assertEqual(["/login"], self.by_id[case_id]["response"]["headers"]["Location"])
        state_invalid = self.by_id["auth-state-invalid-bearer-api-alias"]
        self.assertEqual("unauthorized", state_invalid["response"]["body"]["status"])
        self.assertIn("会话已失效", state_invalid["response"]["body"]["message"])
        self.assertEqual(
            [capture.SHARES["other_owner"]],
            [row["id"] for row in response_shares(
                self.by_id["auth-bearer-precedes-session-api-alias"]
            )],
        )

    def test_single_join_sql_owner_status_filters_and_raw_projection_are_exact(self) -> None:
        expected_sql = (
            "SELECT BS.*, B.NAME AS BANK_NAME FROM BANK_SHARES BS "
            "JOIN USER_QUESTION_BANKS B ON BS.BANK_ID = B.ID "
            "WHERE BS.OWNER_ID = ? AND B.STATUS = 1 "
            "ORDER BY BS.CREATED_AT DESC"
        )
        baseline = self.by_id["auth-session-mixed-api-alias"]
        business = [
            item for item in baseline["observed_get_effects"]["sql"]["statements"]
            if item["classification"] == "personal_bank_all_shares_select"
        ]
        self.assertEqual(1, len(business))
        self.assertEqual(expected_sql, business[0]["sql"])
        self.assertEqual([capture.ACTORS["owner"]], business[0]["parameters"])

        expected_ids = [
            capture.SHARES["special_token_inactive_expired"],
            capture.SHARES["empty_token_cross_bank_owner"],
            capture.SHARES["ordinary"],
            capture.SHARES["null_created"],
        ]
        base_fields = {
            "id", "bank_id", "owner_id", "share_code", "share_token",
            "permission", "expires_at", "max_uses", "current_uses",
            "is_active", "created_at", "bank_name",
        }
        for route in capture.ROUTES:
            rows = response_shares(self.by_id[f"auth-session-mixed-{route}"])
            self.assertEqual(expected_ids, [row["id"] for row in rows])
            for row in rows:
                expected_fields = base_fields | ({"share_link"} if row["share_token"] else set())
                self.assertEqual(expected_fields, set(row))
            self.assertEqual(0, rows[0]["is_active"])
            self.assertEqual("2020-01-01 00:00:00", rows[0]["expires_at"])
            self.assertEqual(capture.BANKS["other_active"], rows[1]["bank_id"])
            self.assertEqual("", rows[1]["bank_name"])
            self.assertEqual("", rows[1]["share_token"])
            self.assertNotIn("share_link", rows[1])
            self.assertIsNone(rows[-1]["created_at"])
            excluded = {
                capture.SHARES["inactive_bank"],
                capture.SHARES["null_status_bank"],
                capture.SHARES["status_two_bank"],
                capture.SHARES["other_owner"],
            }
            self.assertTrue(excluded.isdisjoint({row["id"] for row in rows}))

    def test_host_fallback_configured_base_raw_token_empty_and_ignored_queries_close(self) -> None:
        fallback = (
            f"http://{capture.FALLBACK_HOST}/bank/join?token=raw&?/#+ token"
        )
        configured = (
            capture.CONFIGURED_SHARE_BASE_URL + "/bank/join?token=raw&?/#+ token"
        )
        for route in capture.ROUTES:
            baseline = response_shares(self.by_id[f"auth-session-mixed-{route}"])
            self.assertEqual(fallback, baseline[0]["share_link"])
            ignored = self.by_id[f"data-query-parameters-ignored-{route}"]
            self.assertEqual(
                [["active", "1"], ["sort", "asc"],
                 ["page", "2"], ["page", "3"]],
                ignored["request"]["query"],
            )
            self.assertEqual(baseline, response_shares(ignored))
            empty = self.by_id[f"data-empty-{route}"]
            self.assertEqual([], response_shares(empty))
            self.assertEqual(200, empty["response"]["status"])
            self.assertEqual("success", empty["response"]["body"]["status"])
        configured_rows = response_shares(
            self.by_id["data-configured-share-base-api-alias"]
        )
        self.assertEqual(configured, configured_rows[0]["share_link"])
        self.assertIn("//bank/join", configured_rows[0]["share_link"])

    def test_default_and_json_fault_media_safe_envelopes_and_sql_boundary_close(self) -> None:
        for route in capture.ROUTES:
            default = self.by_id[f"fault-default-{route}"]
            json_fault = self.by_id[f"fault-json-{route}"]
            self.assertEqual(500, default["response"]["status"])
            self.assertEqual(500, json_fault["response"]["status"])
            self.assertEqual(
                "json" if route == "api-alias" else "text",
                default["response"]["body_kind"],
            )
            self.assertEqual("json", json_fault["response"]["body_kind"])
            self.assertNotIn("synthetic personal-bank", default["response"]["body_text"])
            self.assertNotIn("synthetic personal-bank", json_fault["response"]["body_text"])
            for case in (default, json_fault):
                sql = case["observed_get_effects"]["sql"]
                self.assertEqual(1, sql["all_shares_select_attempts"])
                self.assertEqual(1, sql["all_shares_select_bind_count"])
                self.assertEqual(
                    ["personal_bank_all_shares_select"],
                    sql["personal_bank_query_sequence"],
                )
        self.assertEqual(
            "An unexpected server error occurred.",
            self.by_id["fault-default-api-alias"]["response"]["body"]["message"],
        )
        safe_json_500 = {
            "status": "error",
            "message": "An unexpected server error occurred.",
            "status_code": 500,
            "payload": None,
            "request_id": capture.FIXED_REQUEST_ID,
        }
        for case_id in (
            "fault-default-api-alias",
            "fault-json-api-alias",
            "fault-json-web-alias",
        ):
            self.assertEqual(safe_json_500, self.by_id[case_id]["response"]["body"])
        self.assertEqual(
            "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>",
            self.by_id["fault-default-web-alias"]["response"]["body"],
        )

    def test_ledgers_last_active_and_no_personal_bank_writes_close(self) -> None:
        for spec in capture.CASE_SPECS:
            effects = self.by_id[spec.case_id]["observed_get_effects"]
            sql = effects["sql"]
            self.assertTrue(effects["banks_unchanged"])
            self.assertTrue(effects["shares_unchanged"])
            self.assertTrue(effects["users_identity_unchanged"])
            self.assertEqual(0, sql["bank_table_dml_attempts"])
            self.assertEqual(0, sql["share_table_dml_attempts"])
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

    def test_dialect_and_scope_claims_remain_separate_and_fail_closed(self) -> None:
        dialect = self.document["dialect_observation"]
        self.assertIn("0/1", dialect["sqlite_capture"])
        self.assertIn("NULL last", dialect["sqlite_capture"])
        self.assertIn("NULL first", dialect["postgresql_target"])
        self.assertIn("do not invent an id tie-breaker", dialect["migration_rule"])
        query = self.document["legacy_query"]
        self.assertEqual(1, query["statement_count"])
        self.assertEqual(["uid"], query["binds"])
        self.assertIsNone(query["pagination"])
        self.assertIsNone(query["secondary_sort"])
        link = self.document["share_link_contract"]
        self.assertFalse(link["normalizes_configured_trailing_slash"])
        self.assertFalse(link["url_encodes_token"])
        self.assertTrue(link["falsey_token_omits_key"])


if __name__ == "__main__":
    unittest.main()
