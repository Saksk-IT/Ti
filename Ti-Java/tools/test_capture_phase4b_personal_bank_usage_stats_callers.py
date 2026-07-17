#!/usr/bin/env python3
"""Contract checks for fixed-commit personal-bank usage-stats callers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
EVIDENCE = TI_JAVA / "docs/refactor/phase4b/personal-bank-usage-stats-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_usage_stats_callers as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
EVIDENCE_FILE_SHA256 = "28bf3fb165d54f81e4e095284d4b7b6bcc14431c600ad52e544ef02b40a67529"
ATTESTATION_SHA256 = "3164e3202058b9396157a2f34003c2de5d6c6f8ff70c3d33071e358cb9c6d8b0"
DOCUMENT_PAYLOAD_SHA256 = "479042d6e9d7cc160aaf8ad7649a8b6e438b1f8b9efb4f10681788bcfcf9cf08"
CAPTURE_TOOL_SHA256 = "18bda810d1f16ed8e5cc1dba3e7ef3b9baf00369900bb6e2e72c03f17427eb43"


class PersonalBankUsageStatsCallerAttestationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized_bytes = EVIDENCE.read_bytes()
        cls.serialized = cls.serialized_bytes.decode("utf-8")
        cls.document = json.loads(cls.serialized)

    def test_checked_in_hashes_and_fixed_commit_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            EVIDENCE_FILE_SHA256,
            hashlib.sha256(self.serialized_bytes).hexdigest(),
        )
        self.assertEqual(
            "ti.phase4b.personal-bank-usage-stats-caller-attestation",
            document["contract_id"],
        )
        self.assertEqual(LEGACY_COMMIT, capture.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(ATTESTATION_SHA256, document["attestation_sha256"])
        self.assertEqual(DOCUMENT_PAYLOAD_SHA256, document["document_payload_sha256"])
        self.assertEqual(
            DOCUMENT_PAYLOAD_SHA256,
            capture.document_payload_sha256(document),
        )
        self.assertEqual(capture.render_document(document), self.serialized)
        self.assertEqual(
            CAPTURE_TOOL_SHA256,
            hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest(),
        )
        recaptured = capture.capture_document(REPOSITORY_ROOT)
        self.assertEqual(self.serialized, capture.render_document(recaptured))

    def test_full_repository_scan_is_complete_and_bounded(self) -> None:
        scan = self.document["full_repository_scan"]
        self.assertEqual(39, scan["match_count"])
        self.assertEqual(7, scan["matched_source_count"])
        self.assertEqual(["app", "miniprogram-1"], scan["matched_source_roots"])
        self.assertEqual(
            ["miniprogram-1/analyse-data.json"],
            scan["excluded_generated_inventory_files"],
        )
        self.assertEqual(scan["matches_sha256"], capture.sha256_json(scan["matches"]))
        self.assertEqual(
            {
                "app/modules/user_bank/routes/api_shares.py",
                "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.wxml",
                "miniprogram-1/miniprogram/utils/api-endpoints.js",
                "miniprogram-1/miniprogram/utils/api-endpoints.ts",
            },
            {item["source"] for item in scan["matches"]},
        )

    def test_both_aliases_resolve_to_one_authenticated_handler(self) -> None:
        handler = self.document["handler_and_aliases"]
        self.assertEqual(
            "one_registered_handler_serves_both_aliases",
            handler["state"],
        )
        self.assertEqual(56, handler["relative_route"]["line"])
        self.assertEqual(57, handler["authentication"]["line"])
        self.assertEqual(58, handler["handler"]["line"])
        self.assertEqual(
            {
                "bank_id",
                "is_public",
                "owner_id",
                "owner_count",
                "shared_users",
                "public_users",
                "total_users",
                "total_users_excluding_owner",
            },
            set(handler["response_fields"]),
        )
        self.assertEqual(
            "/user/banks/api/<int:bank_id>/usage-stats",
            handler["web_alias_registration"]["composed_path"],
        )
        self.assertEqual(
            "/api/user/banks/api/<int:bank_id>/usage-stats",
            handler["api_alias_registration"]["composed_path"],
        )
        self.assertEqual(
            {"d67a16965b08", "22aecd49a3c2"},
            {route["route_id"] for route in self.document["routes"]},
        )

    def test_web_template_caller_is_reachable_and_active(self) -> None:
        web = self.document["callers"]["web_template"]
        self.assertEqual("active", web["state"])
        self.assertEqual(
            "legacy-web-bank-share-management",
            web["logical_caller_id"],
        )
        self.assertEqual(
            "/user/banks/api/<bank_id>/usage-stats",
            web["actual_alias"],
        )
        self.assertEqual(769, web["page_route"]["line"])
        self.assertEqual(785, web["render_reference"]["line"])
        self.assertEqual([9, 357, 1043], [
            item["line"] for item in web["navigation_references"]
        ])
        self.assertEqual(232, web["direct_get"]["line"])
        self.assertEqual(234, web["consumed_field"]["line"])
        self.assertIn("total_users", web["consumed_field"]["text"])
        self.assertEqual(
            {"initial_page_load": 431, "after_revoke": 326, "after_create": 359},
            {key: value["line"] for key, value in web["activation"].items()},
        )
        self.assertIn("registered route", web["reason"])

    def test_legacy_typescript_caller_is_active_and_selects_api_alias(self) -> None:
        mini = self.document["callers"]["legacy_miniprogram_typescript"]
        self.assertEqual("active", mini["state"])
        self.assertEqual(
            "legacy-miniprogram-bank-detail",
            mini["logical_caller_id"],
        )
        self.assertEqual(
            "/api/user/banks/api/<bank_id>/usage-stats",
            mini["actual_alias"],
        )
        path = mini["path_derivation"]
        self.assertEqual(783, path["typescript_symbol"]["line"])
        self.assertEqual(784, path["relative_endpoint"]["line"])
        self.assertEqual(18, path["production_api_base"]["line"])
        self.assertEqual(105, path["request_url_composition"]["base_lookup"]["line"])
        self.assertEqual(110, path["request_url_composition"]["concatenation"]["line"])
        self.assertIn("selects the API alias", path["result"])
        self.assertEqual(83, mini["page_activation"]["subpackage_registration"]["line"])
        self.assertEqual(250, mini["page_activation"]["navigation_reference"]["line"])
        self.assertEqual(
            {322, 634, 701, 1972, 2099},
            {
                source["line"]
                for key, source in mini["page_activation"].items()
                if key not in {"subpackage_registration", "navigation_reference"}
            },
        )
        self.assertEqual(1991, mini["direct_call"]["line"])
        self.assertEqual(
            {
                "is_public",
                "owner_id",
                "owner_count",
                "shared_users",
                "public_users",
                "total_users",
                "total_users_excluding_owner",
            },
            set(mini["mapped_response_fields"]),
        )
        self.assertEqual(741, mini["rendered_field"]["line"])

    def test_generated_javascript_is_runtime_evidence_not_a_second_caller(self) -> None:
        generated = self.document["callers"]["legacy_miniprogram_generated_javascript"]
        self.assertEqual(
            "generated_runtime_mirror_of_typescript_caller",
            generated["state"],
        )
        self.assertEqual(437, generated["compiled_endpoint_symbol"]["line"])
        self.assertEqual(438, generated["compiled_relative_endpoint"]["line"])
        self.assertEqual(2185, generated["compiled_direct_call"]["line"])
        self.assertEqual(2196, generated["compiled_total_users_mapping"]["line"])
        self.assertEqual(2, len(generated["source_generated_pairs"]))
        self.assertTrue(all(
            "not counted as an independent" in pair["caller_counting"]
            for pair in generated["source_generated_pairs"]
        ))
        self.assertEqual(0, generated["additional_independent_caller_count"])

        counting = self.document["caller_counting"]
        self.assertEqual(2, counting["fixed_commit_legacy_logical_caller_count"])
        self.assertEqual(0, counting["generated_javascript_additional_count"])
        self.assertTrue(counting["both_legacy_caller_families_active"])

    def test_ti_java_controlled_copy_is_byte_equal_and_separately_counted(self) -> None:
        controlled = self.document["callers"]["ti_java_controlled_miniprogram_copy"]
        self.assertEqual("active_controlled_migration_copy", controlled["state"])
        self.assertEqual("Ti-Java/miniprogram", controlled["scope"])
        self.assertEqual(784, controlled["typescript_endpoint"]["line"])
        self.assertEqual(1991, controlled["typescript_direct_call"]["line"])
        self.assertEqual(438, controlled["generated_javascript_endpoint"]["line"])
        self.assertEqual(2185, controlled["generated_javascript_call"]["line"])
        self.assertEqual(741, controlled["rendered_field"]["line"])
        self.assertEqual(5, len(controlled["byte_equal_files"]))
        self.assertTrue(all(
            item["byte_equal"]
            and item["legacy_sha256"] == item["controlled_sha256"]
            for item in controlled["byte_equal_files"]
        ))
        self.assertEqual(
            0,
            controlled["generated_javascript_additional_independent_caller_count"],
        )
        self.assertIn(
            "not added to the fixed-commit legacy count",
            self.document["caller_counting"]["controlled_copy_counting"],
        )

    def test_matrix_disposition_closure_and_source_drift_fail_closed(self) -> None:
        disposition = self.document["frozen_route_matrix_disposition"]
        self.assertTrue(disposition["matrix_is_immutable"])
        self.assertTrue(disposition["matrix_static_scan_is_not_a_complete_caller_inventory"])
        self.assertTrue(disposition["dynamic_web_template_caller_is_closed_here"])
        self.assertTrue(all(self.document["closure"].values()))

        with patch.object(capture, "read_legacy_blob", return_value=b"changed\n"):
            with self.assertRaisesRegex(AssertionError, "caller drifted"):
                capture.legacy_source_line(Path("/unused"), "fake.py", 1, "expected")
            with self.assertRaisesRegex(AssertionError, "baseline drifted"):
                capture.controlled_copy_attestation(REPOSITORY_ROOT)


if __name__ == "__main__":
    unittest.main()
