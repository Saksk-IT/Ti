#!/usr/bin/env python3
"""Contract checks for pinned dual-alias personal-bank share-list goldens."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4b/golden-personal-bank-share-list-reads.json"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-share-list-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_share_list_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "3d5ad616c5dcb644f2247582ce3680345ac2683ffbee67167f98b02bc61061ff"
CASE_PAYLOAD_SHA256 = "f497b8100603deb5d842b814f4c79c27e2f3f02f629428cd3755e49cf36d2dc8"
DOCUMENT_PAYLOAD_SHA256 = "4ff264b57bcb42dcaaa23953a07d06dc0ab8224c16ce7f132a67ef662d0b6d97"
CAPTURE_TOOL_SHA256 = "f0cc13428ca3b4e5cef9845cfca5cb937f8b1ee1fece0b808f47839d1c45dca3"
CALLER_FILE_SHA256 = "16b4dfd9caab9612de954520a9cb0af9caca348477f0dd0dc28345ea38d729fd"
CALLER_ATTESTATION_SHA256 = "561123a3cdb5ec8fd546ea748a51eca2b12438e13ac3ebd30f4de362b5e741e6"


def expected_case_ids() -> set[str]:
    scenarios = (
        "auth-session-owner",
        "auth-bearer-owner",
        "auth-session-other",
        "auth-bearer-precedes-session",
        "auth-invalid-bearer-falls-back-session",
        "auth-anonymous",
        "data-empty",
        "data-query-parameters-ignored",
        "data-nullable-fields",
        "bank-zero",
        "bank-inactive",
        "bank-null-status",
        "bank-status-two",
        "bank-other-owner",
        "bank-missing",
        "bank-negative-path",
        "fault-owner-probe-default",
        "fault-owner-probe-json",
        "fault-share-list-default",
        "fault-share-list-json",
    )
    return {
        f"{scenario}-{route}"
        for route in capture.ROUTES
        for scenario in scenarios
    }


def response_shares(case: dict[str, object]) -> list[dict[str, object]]:
    return case["response"]["body"]["data"]["shares"]


class PersonalBankShareListGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_checked_in_hashes_case_set_redaction_and_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            GOLDEN_FILE_SHA256,
            hashlib.sha256(self.serialized_bytes).hexdigest(),
        )
        self.assertEqual(
            "ti.phase4b.personal-bank-share-list-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(40, document["case_count"])
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

    def test_route_source_archive_and_complete_caller_authority_are_attested(self) -> None:
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
            {"e817f8083d74", "c50102968322"},
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

    def test_dual_alias_authentication_and_bearer_session_precedence_are_fixed(self) -> None:
        expected_status = {
            "auth-session-owner-api-alias": 200,
            "auth-bearer-owner-api-alias": 200,
            "auth-bearer-precedes-session-api-alias": 200,
            "auth-invalid-bearer-falls-back-session-api-alias": 200,
            "auth-anonymous-api-alias": 401,
            "auth-session-owner-web-alias": 200,
            "auth-bearer-owner-web-alias": 302,
            "auth-bearer-precedes-session-web-alias": 302,
            "auth-invalid-bearer-falls-back-session-web-alias": 200,
            "auth-anonymous-web-alias": 302,
        }
        for case_id, status in expected_status.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(status, self.by_id[case_id]["response"]["status"])
        for case_id in (
            "auth-bearer-owner-web-alias",
            "auth-bearer-precedes-session-web-alias",
            "auth-anonymous-web-alias",
        ):
            self.assertEqual(["/login"], self.by_id[case_id]["response"]["headers"]["Location"])

    def test_raw_projection_filters_and_sqlite_observation_are_exact(self) -> None:
        expected_ids = [0, 98201, 98202, 98203, -2]
        expected_fields = {
            "id", "bank_id", "owner_id", "share_code", "share_token",
            "permission", "expires_at", "max_uses", "current_uses",
            "is_active", "created_at",
        }
        for route in capture.ROUTES:
            rows = response_shares(self.by_id[f"auth-session-owner-{route}"])
            self.assertEqual(expected_ids, [row["id"] for row in rows])
            self.assertTrue(all(set(row) == expected_fields for row in rows))
            self.assertEqual(0, rows[1]["is_active"])
            self.assertEqual(capture.ACTORS["other"], rows[2]["owner_id"])
            self.assertEqual("2020-01-01 00:00:00", rows[2]["expires_at"])
            self.assertEqual("unexpected-value", rows[3]["permission"])
            self.assertEqual(-2, rows[3]["current_uses"])
            self.assertIsNone(rows[-1]["created_at"])
        fixture = self.document["fixture"]
        self.assertEqual(5, fixture["returned_owner_bank_share_count"])
        self.assertEqual(2, fixture["cross_owner_returned_count"])
        self.assertEqual(1, fixture["inactive_returned_count"])
        self.assertEqual(1, fixture["expired_returned_count"])

    def test_query_parameters_zero_bank_nullable_fields_and_short_circuits_are_fixed(self) -> None:
        for route in capture.ROUTES:
            baseline = response_shares(self.by_id[f"auth-session-owner-{route}"])
            ignored = self.by_id[f"data-query-parameters-ignored-{route}"]
            self.assertEqual(
                [["active", "1"], ["sort", "asc"],
                 ["page", "2"], ["page", "3"]],
                ignored["request"]["query"],
            )
            self.assertEqual(baseline, response_shares(ignored))
            self.assertEqual([], response_shares(self.by_id[f"data-empty-{route}"]))
            self.assertEqual(
                [capture.SHARES["zero_bank"]],
                [row["id"] for row in response_shares(self.by_id[f"bank-zero-{route}"])],
            )
            nullable = response_shares(self.by_id[f"data-nullable-fields-{route}"])[0]
            for field in (
                "share_code", "share_token", "permission", "expires_at",
                "max_uses", "current_uses", "is_active", "created_at",
            ):
                self.assertIsNone(nullable[field])
            for prefix in (
                "auth-session-other", "bank-inactive", "bank-null-status",
                "bank-status-two", "bank-other-owner", "bank-missing",
            ):
                case = self.by_id[f"{prefix}-{route}"]
                self.assertEqual(404, case["response"]["status"])
                self.assertEqual(
                    ["personal_bank_owner_status_probe"],
                    case["observed_get_effects"]["sql"]["personal_bank_query_sequence"],
                )

    def test_ordered_query_and_independent_failure_boundaries_close(self) -> None:
        for route in capture.ROUTES:
            success = self.by_id[f"auth-session-owner-{route}"]["observed_get_effects"]["sql"]
            self.assertEqual(
                ["personal_bank_owner_status_probe", "personal_bank_share_list_select"],
                success["personal_bank_query_sequence"],
            )
            self.assertEqual(2, success["owner_status_probe_bind_count"])
            self.assertEqual(1, success["share_list_select_bind_count"])
            for suffix in ("default", "json"):
                first = self.by_id[f"fault-owner-probe-{suffix}-{route}"]
                second = self.by_id[f"fault-share-list-{suffix}-{route}"]
                self.assertEqual(
                    ["personal_bank_owner_status_probe"],
                    first["observed_get_effects"]["sql"]["personal_bank_query_sequence"],
                )
                self.assertEqual(
                    ["personal_bank_owner_status_probe", "personal_bank_share_list_select"],
                    second["observed_get_effects"]["sql"]["personal_bank_query_sequence"],
                )
                self.assertEqual(500, first["response"]["status"])
                self.assertEqual(500, second["response"]["status"])
                self.assertNotIn("synthetic personal-bank", first["response"]["body_text"])
                self.assertNotIn("synthetic personal-bank", second["response"]["body_text"])
            self.assertEqual(
                "json" if route == "api-alias" else "text",
                self.by_id[f"fault-owner-probe-default-{route}"]["response"]["body_kind"],
            )
            self.assertEqual(
                "json",
                self.by_id[f"fault-share-list-json-{route}"]["response"]["body_kind"],
            )

    def test_sql_ledgers_last_active_and_no_business_writes_close(self) -> None:
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
            self.assertEqual(expected_activity, effects["user_last_active_changed_user_ids"])
            self.assertEqual(len(expected_activity), sql["user_last_active_dml_attempts"])

    def test_sqlite_and_postgresql_dialect_claims_are_separate_and_fail_closed(self) -> None:
        dialect = self.document["dialect_observation"]
        self.assertIn("0/1", dialect["sqlite_capture"])
        self.assertIn("YYYY-MM-DD", dialect["sqlite_capture"])
        self.assertIn("NULL last", dialect["sqlite_capture"])
        self.assertIn("PostgreSQL 16.14 and 18.4", dialect["postgresql_target"])
        self.assertIn("NULL first", dialect["postgresql_target"])
        self.assertIn("DESC NULLS FIRST", dialect["migration_rule"])
        self.assertIn("must not add an id tie-breaker", dialect["migration_rule"])
        self.assertEqual(
            "legacy order is unspecified and must not be strengthened",
            dialect["equal_created_at"],
        )
        sequence = self.document["legacy_query_sequence"]
        self.assertFalse(sequence["join_authorized"])
        self.assertFalse(sequence["parallel_execution_authorized"])
        self.assertEqual([1, 2], [statement["ordinal"] for statement in sequence["statements"]])


if __name__ == "__main__":
    unittest.main()
