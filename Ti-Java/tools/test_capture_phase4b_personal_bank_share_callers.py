#!/usr/bin/env python3
"""Contract checks for fixed-commit personal-bank share caller evidence."""

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
EVIDENCE = TI_JAVA / "docs/refactor/phase4b/personal-bank-share-list-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_share_callers as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
EVIDENCE_FILE_SHA256 = "16b4dfd9caab9612de954520a9cb0af9caca348477f0dd0dc28345ea38d729fd"
ATTESTATION_SHA256 = "561123a3cdb5ec8fd546ea748a51eca2b12438e13ac3ebd30f4de362b5e741e6"
DOCUMENT_PAYLOAD_SHA256 = "035ae8b4cab7367bcd01f786c8f7442c710905497947f12863e35c59a3d89eb6"
CAPTURE_TOOL_SHA256 = "0759f00efbe1829bfc1698e7525fbe6959d5deab90d195f2b54c36cd249a9ccc"


class PersonalBankShareCallerAttestationTest(unittest.TestCase):

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
            "ti.phase4b.personal-bank-share-list-caller-attestation",
            document["contract_id"],
        )
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

    def test_full_repository_scan_is_bounded_complete_and_method_aware(self) -> None:
        scan = self.document["full_repository_scan"]
        self.assertEqual(46, scan["match_count"])
        self.assertEqual(
            ["app", "miniprogram-1", "tests"],
            scan["matched_source_roots"],
        )
        self.assertEqual(
            ["miniprogram-1/analyse-data.json"],
            scan["excluded_generated_inventory_files"],
        )
        self.assertEqual(
            scan["matches_sha256"],
            capture.sha256_json(scan["matches"]),
        )
        self.assertTrue(any(
            item["source"].endswith("api_shares.py")
            and item["line"] == 29
            and "methods=['GET']" in item["text"]
            for item in scan["matches"]
        ))
        self.assertTrue(any(
            item["source"] == "tests/test_user_bank_shares.py"
            and item["line"] == 103
            for item in scan["matches"]
        ))
        tests = self.document["callers"]["backend_test_coverage"]
        self.assertEqual("no_direct_get_coverage", tests["state"])
        self.assertEqual(
            ["POST", "POST", "POST"],
            [item["method"] for item in tests["same_path_occurrences"]],
        )
        self.assertEqual("DELETE", tests["delete_occurrence"]["method"])

    def test_active_web_caller_and_orphan_templates_are_not_conflated(self) -> None:
        callers = self.document["callers"]
        web = callers["web"]
        self.assertEqual("active", web["state"])
        self.assertEqual(
            "/user/banks/api/<bank_id>/shares",
            web["actual_alias"],
        )
        self.assertEqual(220, web["direct_get"]["line"])
        self.assertEqual(785, web["render_reference"]["line"])
        self.assertEqual(160, web["private_bank_only_guard"]["line"])
        self.assertEqual(430, web["page_load_trigger"]["line"])
        self.assertEqual(293, web["optional_share_link_branch"]["guard"]["line"])
        self.assertEqual(298, web["optional_share_link_branch"]["copy_action"]["line"])
        self.assertIn(
            "must not be synthesized",
            web["optional_share_link_branch"]["server_contract"],
        )
        self.assertEqual(
            {"id", "share_code", "current_uses", "max_uses", "expires_at",
             "created_at", "is_active", "share_link"},
            set(web["consumed_fields"]),
        )

        dormant = callers["dormant_or_orphan_callers"]
        self.assertEqual(
            ["orphan_template", "orphan_partial"],
            [item["state"] for item in dormant],
        )
        self.assertTrue(all(
            item["render_or_include_references"] == [] for item in dormant
        ))
        self.assertEqual(9, dormant[1]["active_composition_proof"]["line"])
        self.assertIn("_07_share_basic", dormant[1]["active_composition_proof"]["text"])

    def test_miniprogram_alias_activation_order_dependency_and_dormant_page_close(self) -> None:
        mini = self.document["callers"]["miniprogram"]
        self.assertEqual(
            "/api/user/banks/api/<bank_id>/shares",
            mini["actual_alias"],
        )
        self.assertIn("/api base", mini["path_derivation"]["result"])
        composition = mini["path_derivation"]["request_url_composition"]
        self.assertEqual(105, composition["base_lookup"]["line"])
        self.assertEqual(110, composition["concatenation"]["line"])
        self.assertEqual(434, mini["path_derivation"]["compiled_relative_endpoint"]["line"])
        active = mini["active_bank_detail"]
        self.assertEqual("active", active["state"])
        self.assertEqual(1888, active["call"]["line"])
        self.assertEqual(542, active["share_tab_activation"]["line"])
        self.assertEqual(1955, active["wechat_share_prepare_trigger"]["line"])
        self.assertEqual(634, active["ordinary_tab_tap_observation"]["source"]["line"])
        self.assertIn(
            "does not itself call loadShares",
            active["ordinary_tab_tap_observation"]["behavior"],
        )
        self.assertEqual(2117, active["join_deep_link"]["source"]["line"])
        compiled = active["compiled_runtime"]
        self.assertEqual(
            [2043, 2049, 2055, 2096, 2107],
            [
                compiled["call"]["line"],
                compiled["active_filter"]["line"],
                compiled["token_picker_call"]["line"],
                compiled["order_preserving_iteration"]["line"],
                compiled["first_valid_return"]["line"],
            ],
        )
        self.assertIn("without sorting or reversing", compiled["ordering_contract"])
        self.assertEqual(
            {"id", "share_code", "current_uses", "expires_at",
             "expires_at_display", "is_active"},
            set(active["wxml_consumption"]["fields"]),
        )
        self.assertIn("first active non-expired", mini["ordering_dependency"])
        self.assertEqual(
            "dormant_external_entry_candidate",
            mini["dedicated_bank_share_page"]["state"],
        )
        self.assertEqual(51, mini["dedicated_bank_share_page"]["registration"]["line"])
        self.assertEqual(56, mini["dedicated_bank_share_page"]["call"]["line"])
        dedicated = mini["dedicated_bank_share_page"]
        dedicated_runtime = dedicated["compiled_runtime"]
        self.assertEqual(
            [86, 95, 108, 137, 146],
            [
                dedicated_runtime["call"]["line"],
                dedicated_runtime["active_filter"]["line"],
                dedicated_runtime["token_picker_call"]["line"],
                dedicated_runtime["order_preserving_iteration"]["line"],
                dedicated_runtime["first_valid_return"]["line"],
            ],
        )
        self.assertEqual(
            {"id", "share_code", "current_uses", "expires_at",
             "expires_at_display"},
            set(dedicated["wxml_consumption"]["fields"]),
        )

    def test_matrix_disposition_closure_and_source_drift_fail_closed(self) -> None:
        disposition = self.document["frozen_route_matrix_disposition"]
        self.assertTrue(disposition["matrix_is_immutable"])
        self.assertTrue(disposition["matrix_rows_are_not_a_complete_caller_inventory"])
        self.assertTrue(disposition["web_row_names_an_orphan_partial_instead_of_the_rendered_management_page"])
        self.assertTrue(all(self.document["closure"].values()))
        self.assertEqual(
            {"e817f8083d74", "c50102968322"},
            {route["route_id"] for route in self.document["routes"]},
        )

        with patch.object(capture, "read_blob", return_value=b"changed\n"):
            with self.assertRaisesRegex(AssertionError, "caller drifted"):
                capture.source_line(Path("/unused"), "fake.py", 1, "expected")


if __name__ == "__main__":
    unittest.main()
