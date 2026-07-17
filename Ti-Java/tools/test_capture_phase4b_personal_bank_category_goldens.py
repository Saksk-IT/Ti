#!/usr/bin/env python3
"""Contract checks for pinned dual-alias personal-bank category goldens."""

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
GOLDEN = TI_JAVA / "docs/refactor/phase4b/golden-personal-bank-category-reads.json"
CONTRACT = TI_JAVA / "docs/refactor/phase4b/personal-bank-category-read-contract.json"
PLAN = TI_JAVA / "docs/refactor/phase4b/personal-bank-category-query-plan-evidence.json"
SHAPE = TI_JAVA / "docs/refactor/phase4b/application-api-shape-status.json"
PHASE4A_FINAL = TI_JAVA / "docs/refactor/phase4a/phase4a-final-acceptance.json"
SHARE_READ_CONTRACT = (
    TI_JAVA / "docs/refactor/phase4b/personal-bank-share-list-read-contract.json"
)
TERMINAL_READ_CONTRACT = (
    TI_JAVA / "docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json"
)
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_category_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
GOLDEN_FILE_SHA256 = "c81ad22b70e1e9e25eed96e2f06a475ba590eb7ae00b7a106c6bcedac3818515"
CASE_PAYLOAD_SHA256 = "66590670726216ad48cb5e5b2f858da16529c2a1ff976c70dbb92f2ca2e6e6cc"
DOCUMENT_PAYLOAD_SHA256 = "ef04369ba1ba04768bc75a88c254e1b1ae3af9f0cdefc16272d331ad9f5982fc"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
CALLER_ATTESTATION_SHA256 = "1496c5ccb93bed488ad5e6009fec926f50dd6fe817d3f0fc9b0977a5578d7add"
CAPTURE_TOOL_SHA256 = "6442f6aff7691b82c15343b64ab481c1b9783608c109490f259063ab69fc4d92"


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
        "fault-default",
        "fault-json",
    )
    return {
        f"{scenario}-{route}"
        for route in capture.ROUTES
        for scenario in scenarios
    }


def response_categories(case: dict[str, object]) -> list[dict[str, object]]:
    body = case["response"]["body"]
    return body["data"]["categories"]


class PersonalBankCategoryGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = GOLDEN.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.shape = json.loads(SHAPE.read_text(encoding="utf-8"))
        cls.share_read_contract = json.loads(
            SHARE_READ_CONTRACT.read_text(encoding="utf-8")
        )
        cls.terminal_read_contract = json.loads(
            TERMINAL_READ_CONTRACT.read_text(encoding="utf-8")
        )

    def test_checked_in_hashes_case_set_and_redaction_close(self) -> None:
        document = self.document
        self.assertEqual(
            GOLDEN_FILE_SHA256,
            hashlib.sha256(self.serialized_bytes).hexdigest(),
        )
        self.assertEqual(
            "ti.phase4b.personal-bank-category-read-goldens",
            document["contract_id"],
        )
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(22, document["case_count"])
        self.assertEqual(22, len(document["cases"]))
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
        self.assertNotRegex(
            self.serialized,
            re.compile(r'"X-RateLimit-Reset":\s*\[\s*"\d+', re.MULTILINE),
        )
        for case in document["cases"]:
            for cookie in case["response"]["headers"].get("Set-Cookie", []):
                self.assertEqual("<redacted-session-cookie>", cookie)

    def test_route_matrix_complete_archive_sources_and_dormant_caller_are_attested(self) -> None:
        source = self.document["legacy_source_attestation"]
        matrix = source["frozen_route_matrix"]
        self.assertEqual(MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(capture.matrix_attestation(), matrix)
        self.assertEqual(
            {"19b37a262989", "e32aec766730"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["target_module"] == "personalbank"
            and row["migration_status"] == "pending"
            for row in matrix["selected_rows"]
        ))
        self.assertEqual(
            "blueprint_compatibility_alias",
            next(row for row in matrix["selected_rows"]
                 if row["route_id"] == "19b37a262989")["registration_kind"],
        )

        archive = source["complete_app_archive"]
        self.assertTrue(archive["complete_app_tree_verified"])
        self.assertEqual(LEGACY_COMMIT, archive["archive_commit"])
        self.assertGreaterEqual(archive["extracted_file_count"], 600)
        self.assertEqual(set(capture.KEY_SOURCE_FILES), set(source["key_sources"]))

        caller = source["callers"]
        self.assertEqual(CALLER_ATTESTATION_SHA256, caller["attestation_sha256"])
        self.assertEqual("dormant", caller["caller_state"])
        self.assertEqual([], caller["api_alias_direct_occurrences"])
        self.assertEqual([], caller["template_render_references"])
        self.assertEqual(
            [("app/modules/user_bank/templates/user_bank/public/categories.html", 115)],
            [(item["source"], item["line"])
             for item in caller["direct_get_occurrences"]],
        )

    def test_machine_contract_closes_phase4a_shape_golden_plan_and_implementation(self) -> None:
        contract = self.contract
        evidence = contract["evidence"]
        self.assertEqual(
            "ti.phase4b.personal-bank-category-read-contract",
            contract["contract_id"],
        )
        self.assertEqual(
            "personalbank_internal_category_read_implemented_http_aliases_deferred",
            contract["status"],
        )
        self.assertEqual(LEGACY_COMMIT, contract["legacy_commit"])
        self.assertEqual(
            hashlib.sha256(PHASE4A_FINAL.read_bytes()).hexdigest(),
            evidence["phase4a_final_acceptance"]["sha256"],
        )
        self.assertEqual(
            "9eeec781af91c0994c750ea2641653183f36eb4492d4ff9bd6809679c723620f",
            evidence["phase4a_final_acceptance"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(SHAPE.read_bytes()).hexdigest(),
            evidence["application_api_shape"]["sha256"],
        )
        self.assertEqual(11, self.shape["migrated_route_count"])
        self.assertEqual(11, self.shape["implemented_route_backed_operation_count"])
        self.assertEqual(20, self.shape["implemented_public_application_method_count"])

        golden = evidence["golden"]
        self.assertEqual(GOLDEN_FILE_SHA256, golden["file_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, golden["case_payload_sha256"])
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, golden["document_payload_sha256"])
        self.assertEqual(CAPTURE_TOOL_SHA256, golden["capture_tool_sha256"])
        current_test_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        successor_test_hash = self.terminal_read_contract["implementation"][
            "verification_source_sha256"
        ]["category_golden_forward_handoff_test"]
        self.assertEqual(successor_test_hash, current_test_hash)
        self.assertNotEqual(
            successor_test_hash,
            self.share_read_contract["implementation"][
                "verification_source_sha256"
            ]["category_golden_forward_handoff_test"],
        )
        self.assertNotEqual(current_test_hash, golden["capture_tool_test_sha256"])

        plan = evidence["query_plan"]
        self.assertEqual(
            hashlib.sha256(PLAN.read_bytes()).hexdigest(),
            plan["file_sha256"],
        )
        self.assertEqual(
            self.plan["measurement"]["observation"]["sql_sha256"],
            plan["runtime_sql_sha256"],
        )
        for key, source in (
            ("adapter_sha256", "adapter_sha256"),
            ("runtime_sql_manifest_sha256", "runtime_sql_manifest_sha256"),
            ("runtime_sql_exporter_sha256", "runtime_sql_exporter_sha256"),
            ("capture_tool_sha256", "capture_tool_sha256"),
            ("capture_tool_test_sha256", "capture_tool_test_sha256"),
        ):
            self.assertEqual(self.plan["inputs"][source], plan[key])

        implementation = evidence["implementation"]
        for field, relative in implementation["source_files"].items():
            current_hash = hashlib.sha256((TI_JAVA / relative).read_bytes()).hexdigest()
            if field in {"application_api", "application_service"}:
                successor = self.terminal_read_contract["implementation"]
                self.assertEqual(relative, successor["main_source_files"][field])
                self.assertEqual(current_hash, successor["main_source_sha256"][field])
                self.assertNotEqual(current_hash, implementation["source_sha256"][field])
            else:
                self.assertEqual(current_hash, implementation["source_sha256"][field])

    def test_datetime_and_sqlite_dialect_limits_are_explicit_not_overclaimed(self) -> None:
        attestation = self.document["legacy_datetime_serializer_attestation"]
        self.assertEqual("Fri, 17 Jul 2026 08:00:00 GMT", attestation["output"])
        self.assertIn("model-type plus serializer", attestation["scope"])
        self.assertIn("not a PostgreSQL driver", attestation["scope"])
        dialect = self.document["dialect_observation"]
        self.assertIn("SQLite", dialect)
        self.assertIn("NULLS LAST", dialect)
        self.assertIn("YYYY-MM-DD HH:MM:SS", dialect)
        self.assertIn("full PostgreSQL-backed legacy HTTP gate remains deferred", dialect)

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
        self.assertEqual(
            [capture.CATEGORIES["negative"], capture.CATEGORIES["zero"],
             capture.CATEGORIES["unicode"], capture.CATEGORIES["empty_name"]],
            [row["id"] for row in response_categories(
                self.by_id["auth-bearer-precedes-session-api-alias"]
            )],
        )
        for case_id in (
            "auth-bearer-owner-web-alias",
            "auth-bearer-precedes-session-web-alias",
            "auth-anonymous-web-alias",
        ):
            self.assertEqual(["/login"], self.by_id[case_id]["response"]["headers"]["Location"])

    def test_current_identity_projection_order_and_status_one_counts_are_exact(self) -> None:
        expected = [
            (-2, 97001, "负主键分类", -5, 2),
            (0, 97001, "", 0, 1),
            (97101, 97001, "高数・α／🧪", 0, 0),
            (97102, 97001, "尾部分类", 9, 0),
        ]
        for route in capture.ROUTES:
            rows = response_categories(self.by_id[f"auth-session-owner-{route}"])
            actual = [
                (row["id"], row["user_id"], row["name"],
                 row["sort_order"], row["bank_count"])
                for row in rows
            ]
            self.assertEqual(expected, actual)
            self.assertEqual(
                [(97103, 1)],
                [(row["id"], row["bank_count"])
                 for row in response_categories(
                     self.by_id[f"auth-session-other-{route}"]
                 )],
            )
        fixture = self.document["fixture"]
        self.assertEqual(4, fixture["active_status_one_bank_count"])
        self.assertEqual(4, fixture["inactive_or_non_one_bank_count"])
        self.assertEqual(2, fixture["cross_owner_active_bank_count"])

    def test_query_parameters_are_ignored_and_nullable_fields_remain_present(self) -> None:
        for route in capture.ROUTES:
            baseline = response_categories(self.by_id[f"auth-session-owner-{route}"])
            ignored = self.by_id[f"data-query-parameters-ignored-{route}"]
            self.assertEqual(
                [
                    ["category_id", "999"], ["sort", "desc"],
                    ["page", "2"], ["page", "3"],
                ],
                ignored["request"]["query"],
            )
            self.assertEqual(baseline, response_categories(ignored))
            self.assertEqual([], response_categories(self.by_id[f"data-empty-{route}"]))
            nullable = response_categories(
                self.by_id[f"data-nullable-fields-{route}"]
            )[0]
            self.assertEqual(
                {"description": None, "sort_order": None,
                 "created_at": None, "updated_at": None},
                {key: nullable[key] for key in (
                    "description", "sort_order", "created_at", "updated_at"
                )},
            )
            self.assertEqual(0, nullable["bank_count"])

    def test_sql_ledgers_close_one_bind_and_zero_business_writes(self) -> None:
        for case in self.document["cases"]:
            effects = case["observed_get_effects"]
            sql = effects["sql"]
            self.assertTrue(effects["categories_unchanged"])
            self.assertTrue(effects["banks_unchanged"])
            self.assertTrue(effects["users_identity_unchanged"])
            self.assertEqual(0, sql["category_table_dml_attempts"])
            self.assertEqual(0, sql["bank_table_dml_attempts"])
            self.assertEqual(0, sql["ddl_attempts"])
            self.assertEqual(sql["classified_attempt_count"], sql["statement_count"])
            if sql["category_select_attempts"]:
                self.assertEqual(1, sql["category_select_attempts"])
                self.assertEqual(1, sql["category_select_bind_count"])
                selected = [statement for statement in sql["statements"]
                            if statement["classification"] == "personal_bank_category_select"]
                self.assertEqual(1, len(selected))
                self.assertIn("STATUS = 1", selected[0]["sql"])
                self.assertNotIn("USER_QUESTION_BANKS.USER_ID", selected[0]["sql"])

    def test_last_active_side_effect_is_separate_and_exact(self) -> None:
        for spec in capture.CASE_SPECS:
            effects = self.by_id[spec.case_id]["observed_get_effects"]
            expected = []
            if spec.session_actor is not None and spec.bearer_actor is None:
                expected = [capture.ACTORS[spec.session_actor]]
            self.assertEqual(expected, effects["user_last_active_changed_user_ids"])
            self.assertEqual(
                len(expected),
                effects["sql"]["user_last_active_dml_attempts"],
            )

    def test_fault_content_negotiation_is_safe_and_alias_specific(self) -> None:
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
            for case in (default, json_fault):
                self.assertNotIn(
                    "synthetic personal-bank",
                    case["response"]["body_text"],
                )
                self.assertEqual(1, case["observed_get_effects"]["sql"]["category_select_attempts"])

    def test_capture_tool_hash_and_fixed_commit_recapture_are_byte_identical(self) -> None:
        self.assertEqual(
            CAPTURE_TOOL_SHA256,
            hashlib.sha256((TOOLS_DIR / capture.__file__).read_bytes()).hexdigest()
            if not Path(capture.__file__).is_absolute()
            else hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest(),
        )
        recaptured = capture.capture_document(REPOSITORY_ROOT)
        self.assertEqual(self.serialized, capture.render_document(recaptured))


if __name__ == "__main__":
    unittest.main()
