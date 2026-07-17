#!/usr/bin/env python3
"""Checks for fixed-commit personal-bank all-shares caller evidence."""

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
EVIDENCE = TI_JAVA / "docs/refactor/phase4b/personal-bank-all-shares-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_all_shares_callers as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
EVIDENCE_FILE_SHA256 = "e20678ebb091db7840c37b42b9a592250a4f499ff772d775ed87a3b5e0942bbb"
ATTESTATION_SHA256 = "1aa666fdd04e15e4509e8ee6c45d00ff4783141c9b767bd7a0fa7082e20d79d0"
DOCUMENT_PAYLOAD_SHA256 = "5da7eb9a7cc771fc4c5e22d1cc5413f955a7f46bb6d02283241876e3c99f2166"
CAPTURE_TOOL_SHA256 = "efc9b1d8a9c48ca99b88dead52353abbc512d7913fd1a47b26430bd6655d6ad0"


class PersonalBankAllSharesCallerAttestationTest(unittest.TestCase):

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
            "ti.phase4b.personal-bank-all-shares-caller-attestation",
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

    def test_full_scan_proves_exactly_one_direct_caller(self) -> None:
        scan = self.document["full_repository_capability_scan"]
        self.assertEqual(6, scan["match_count"])
        self.assertEqual(["app"], scan["matched_source_roots"])
        self.assertEqual(
            scan["matches_sha256"],
            capture.sha256_json(scan["matches"]),
        )

        direct = self.document["callers"]["direct"]
        direct_scan = direct["full_repository_direct_alias_scan"]
        self.assertEqual(1, direct_scan["match_count"])
        self.assertEqual(
            "app/modules/user_bank/templates/user_bank/manage/shares_manage_all.html",
            direct["direct_get"]["source"],
        )
        self.assertEqual(185, direct["direct_get"]["line"])
        self.assertEqual(186, direct["response_extraction"]["line"])
        self.assertEqual(370, direct["load_trigger"]["line"])
        self.assertEqual(
            "/user/banks/api/shares/all",
            direct["actual_alias"],
        )
        self.assertEqual(
            {"bank_name", "share_code", "share_token", "is_active", "permission",
             "created_at", "expires_at", "used_count", "max_uses", "share_link",
             "bank_id", "id"},
            set(direct["consumed_fields"]),
        )
        mismatch = direct["usage_count_field_mismatch"]
        self.assertEqual(348, mismatch["client_read"]["line"])
        self.assertEqual(159, mismatch["server_raw_projection"]["line"])
        self.assertEqual("current_uses", mismatch["legacy_server_column"])

    def test_page_entry_is_404_and_template_has_no_render_reference(self) -> None:
        page = self.document["callers"]["page_entry"]
        self.assertEqual("page_entry_retired_with_404", page["state"])
        self.assertEqual(36, page["route"]["line"])
        self.assertEqual(37, page["authentication"]["line"])
        self.assertEqual(38, page["handler"]["line"])
        self.assertEqual(40, page["terminal_response"]["line"])
        self.assertIn("404", page["terminal_response"]["text"])
        self.assertEqual(0, page["template_render_or_include_scan"]["match_count"])
        self.assertIn("orphan template", page["conclusion"])

    def test_no_miniprogram_caller_but_both_http_aliases_remain_compatible(self) -> None:
        miniprogram = self.document["callers"]["miniprogram"]
        self.assertEqual("no_miniprogram_caller", miniprogram["state"])
        mini_scan = miniprogram["full_miniprogram_text_scan"]
        self.assertEqual(["miniprogram-1"], mini_scan["scope_paths"])
        self.assertEqual(0, mini_scan["match_count"])

        compatibility = self.document["external_compatibility"]
        self.assertEqual(
            "both_http_aliases_remain_externally_registered",
            compatibility["state"],
        )
        self.assertEqual(152, compatibility["relative_route"]["line"])
        self.assertEqual(154, compatibility["handler"]["line"])
        self.assertEqual(
            "/user/banks/api/shares/all",
            compatibility["web_alias_registration"]["composed_path"],
        )
        self.assertEqual(
            "/api/user/banks/api/shares/all",
            compatibility["api_alias_registration"]["composed_path"],
        )
        self.assertEqual(
            {"a6fda3638fc3", "0fdd3026f636"},
            {route["route_id"] for route in self.document["routes"]},
        )
        self.assertIn("does not authorize deleting", compatibility["compatibility_boundary"])

    def test_matrix_disposition_closure_and_source_drift_fail_closed(self) -> None:
        disposition = self.document["frozen_route_matrix_disposition"]
        self.assertTrue(disposition["matrix_is_immutable"])
        self.assertTrue(disposition["both_rows_report_not_found_static_scan"])
        self.assertTrue(disposition["fixed_commit_scan_proves_one_direct_web_caller"])
        self.assertTrue(disposition["caller_is_not_an_active_page_entry"])
        self.assertTrue(all(self.document["closure"].values()))

        with patch.object(capture, "read_blob", return_value=b"changed\n"):
            with self.assertRaisesRegex(AssertionError, "caller drifted"):
                capture.source_line(Path("/unused"), "fake.py", 1, "expected")


if __name__ == "__main__":
    unittest.main()
