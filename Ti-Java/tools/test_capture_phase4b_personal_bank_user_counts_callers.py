#!/usr/bin/env python3
"""Contract checks for fixed-commit personal-bank user-counts callers."""

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
EVIDENCE = TI_JAVA / "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_user_counts_callers as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
EVIDENCE_FILE_SHA256 = "bad7e19e44710f57841a2681f1b45bfcce85c67b46f1882d2f22f45da86961fc"
ATTESTATION_SHA256 = "1b650434114f6824ae65e20bc2ead275e651853c026387ddd3461690009dc3fb"
DOCUMENT_PAYLOAD_SHA256 = "0470c6d6a5daa33474f0c2b794cce7bebcbc86c763eec31f190864fd8d858669"
CAPTURE_TOOL_SHA256 = "293a84072ed42ad6719b797fe36eeb931e04db0b80468860c37a9c3f2e5a0abd"


class PersonalBankUserCountsCallerAttestationTest(unittest.TestCase):

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
            "ti.phase4b.personal-bank-user-counts-caller-attestation",
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

    def test_full_repository_scan_is_complete_bounded_and_classified(self) -> None:
        scan = self.document["full_repository_scan"]
        self.assertEqual(43, scan["match_count"])
        self.assertEqual(24, scan["matched_source_count"])
        self.assertEqual(["app", "miniprogram-1", "tests"], scan["matched_source_roots"])
        self.assertEqual(
            ["miniprogram-1/analyse-data.json"],
            scan["excluded_generated_inventory_files"],
        )
        self.assertEqual(scan["matches_sha256"], capture.sha256_json(scan["matches"]))
        collisions = set(scan["generic_get_user_counts_collision_sources"])
        self.assertEqual(5, scan["generic_get_user_counts_collision_source_count"])
        self.assertEqual(
            {
                "miniprogram-1/miniprogram/pages/practice/practice.js",
                "miniprogram-1/miniprogram/pages/practice/practice.ts",
                "miniprogram-1/miniprogram/pages/subject-detail-v2/subject-detail-v2.js",
                "miniprogram-1/miniprogram/pages/subject-detail-v2/subject-detail-v2.ts",
                "tests/test_home_personal_bank_stats.py",
            },
            collisions,
        )

    def test_shared_handler_aliases_filters_response_and_tag_side_effect_close(self) -> None:
        handler = self.document["handler_and_aliases"]
        self.assertEqual("one_registered_handler_serves_both_aliases", handler["state"])
        self.assertEqual(774, handler["relative_route"]["line"])
        self.assertEqual(775, handler["authentication"]["line"])
        self.assertEqual(776, handler["handler"]["line"])
        self.assertEqual(779, handler["access_check"]["lookup"]["line"])
        self.assertEqual(
            {"q_type", "q_type_all_normalization", "source", "tag"},
            set(handler["query_parameters"]),
        )
        self.assertEqual(
            {"total", "favorites", "mistakes", "types", "shuffle_options_available"},
            set(handler["response_fields"]),
        )
        self.assertEqual(
            "/user/banks/api/<int:bank_id>/user-counts",
            handler["web_alias_registration"]["composed_path"],
        )
        self.assertEqual(
            "/api/user/banks/api/<int:bank_id>/user-counts",
            handler["api_alias_registration"]["composed_path"],
        )
        tag_store = handler["tag_store_dependency"]
        self.assertEqual(794, tag_store["load"]["line"])
        self.assertEqual(122, tag_store["migration_write"]["line"])
        self.assertEqual(183, tag_store["commit"]["line"])
        self.assertIn("not guaranteed", tag_store["disposition"])

    def test_frozen_route_matrix_rows_are_closed_without_mutation(self) -> None:
        matrix = self.document["frozen_route_matrix"]
        self.assertEqual("both_frozen_rows_closed", matrix["state"])
        self.assertEqual(
            {"6858f6fa506f", "006913d0d956"},
            set(matrix["rows"]),
        )
        for route_id, row in matrix["rows"].items():
            self.assertEqual(route_id, row["route_id"])
            self.assertEqual("GET", row["methods"])
            self.assertEqual("personalbank", row["target_module"])
            self.assertEqual("pending", row["migration_status"])
            self.assertEqual(64, len(row["row_sha256"]))
        self.assertIn("seven downstream", matrix["static_scan_limit"])

    def test_web_template_is_one_active_direct_caller(self) -> None:
        web = self.document["callers"]["web_template"]
        self.assertEqual("active", web["state"])
        self.assertEqual("legacy-web-bank-practice-start-count", web["logical_caller_id"])
        self.assertEqual("/user/banks/api/<bank_id>/user-counts", web["actual_alias"])
        self.assertEqual([13, 4], [item["line"] for item in web["template_include_chain"]])
        self.assertEqual(723, web["direct_get"]["line"])
        self.assertEqual(
            {"source": 718, "q_type": 719, "tag": 720},
            {key: value["line"] for key, value in web["forwarded_parameters"].items()},
        )
        self.assertEqual(
            {"total": 728, "shuffle_options_available": 729},
            {key: value["line"] for key, value in web["consumed_fields"].items()},
        )
        self.assertEqual({26, 463, 543, 635}, {
            source["line"] for source in web["activation"].values()
        })
        self.assertEqual(1, web["direct_network_call_site_count"])

    def test_api_base_and_relative_endpoint_select_the_actual_api_alias(self) -> None:
        path = self.document["callers"]["legacy_miniprogram_path_derivation"]
        self.assertEqual(18, path["production_api_base"]["line"])
        self.assertEqual(44, path["custom_base_normalization"]["line"])
        self.assertEqual(188, path["development_api_base"]["line"])
        self.assertEqual(760, path["typescript_symbol"]["line"])
        self.assertEqual(764, path["relative_endpoint"]["line"])
        self.assertEqual(105, path["request_url_composition"]["base_lookup"]["line"])
        self.assertEqual(110, path["request_url_composition"]["concatenation"]["line"])
        self.assertEqual(115, path["request_url_composition"]["bearer_header"]["line"])
        self.assertEqual(
            "/api/user/banks/api/<bank_id>/user-counts",
            path["actual_alias"],
        )
        self.assertIn("ends in /api", path["result"])

    def test_all_seven_typescript_direct_call_sites_are_closed(self) -> None:
        callers = self.document["callers"]["legacy_miniprogram_typescript_direct_calls"]
        expected = {
            "reusable-exam-builder-per-type-count": 583,
            "bank-detail-bootstrap-summary": 411,
            "bank-detail-filtered-start-count": 1422,
            "exam-center-per-type-count": 764,
            "legacy-practice-setup-summary": 295,
            "review-center-filtered-start-count": 570,
            "bank-quiz-source-adapter": 493,
        }
        self.assertEqual(expected, {
            caller["caller_id"]: caller["direct_call"]["line"] for caller in callers
        })
        self.assertEqual(7, len(callers))
        self.assertEqual(6, len({caller["direct_call"]["source"] for caller in callers}))
        by_id = {caller["caller_id"]: caller for caller in callers}
        self.assertEqual(3, len(by_id["bank-detail-bootstrap-summary"]["consumed_fields"]))
        self.assertEqual(3, len(by_id["bank-detail-filtered-start-count"]["request_parameters"]))
        self.assertIn(
            "not implemented",
            by_id["bank-quiz-source-adapter"]["tag_forwarding"],
        )

    def test_subject_stats_is_an_indirect_adapter_consumer(self) -> None:
        consumer = self.document["callers"]["legacy_miniprogram_indirect_consumer"]
        self.assertEqual("active_for_bank_id_deep_link", consumer["state"])
        self.assertEqual("subject-stats-via-bank-quiz-source", consumer["consumer_id"])
        self.assertEqual(75, consumer["indirect_call"]["line"])
        self.assertEqual([79, 80], [item["line"] for item in consumer["consumed_fields"]])
        self.assertEqual(702, consumer["adapter_selection"]["line"])
        self.assertIn("not a second network", consumer["network_call_counting"])

    def test_generated_javascript_is_runtime_evidence_not_double_counted(self) -> None:
        generated = self.document["callers"]["legacy_miniprogram_generated_javascript"]
        self.assertEqual("generated_runtime_mirrors_of_typescript_callers", generated["state"])
        self.assertEqual(419, generated["compiled_endpoint"]["line"])
        self.assertEqual(
            [599, 392, 1526, 875, 373, 599, 458],
            [item["compiled_direct_call"]["line"] for item in generated["compiled_direct_calls"]],
        )
        self.assertEqual(108, generated["compiled_indirect_consumer"]["line"])
        self.assertEqual(8, len(generated["source_generated_pairs"]))
        self.assertTrue(all(
            "not counted twice" in pair["caller_counting"]
            for pair in generated["source_generated_pairs"]
        ))
        self.assertEqual(7, generated["compiled_direct_call_site_count"])
        self.assertEqual(0, generated["additional_independent_caller_count"])

    def test_controlled_miniprogram_copy_is_byte_equal_and_separate(self) -> None:
        controlled = self.document["callers"]["ti_java_controlled_miniprogram_copy"]
        self.assertEqual("active_controlled_migration_copy", controlled["state"])
        self.assertEqual("Ti-Java/miniprogram", controlled["scope"])
        self.assertEqual(25, controlled["byte_equal_file_count"])
        self.assertEqual(25, len(controlled["byte_equal_files"]))
        self.assertTrue(all(
            item["byte_equal"]
            and item["legacy_sha256"] == item["controlled_sha256"]
            for item in controlled["byte_equal_files"]
        ))
        self.assertEqual(7, controlled["typescript_direct_call_site_count"])
        self.assertEqual(7, len(controlled["typescript_direct_calls"]))
        self.assertEqual(75, controlled["typescript_indirect_consumer"]["line"])
        self.assertEqual(
            "/api/user/banks/api/<bank_id>/user-counts",
            controlled["path_derivation"]["actual_alias"],
        )
        self.assertEqual(0, controlled["generated_javascript_additional_independent_caller_count"])

    def test_legacy_tests_gaps_counting_and_closure_are_explicit(self) -> None:
        tests = self.document["callers"]["legacy_tests"]
        self.assertEqual("focused_success_only_web_alias_coverage", tests["state"])
        self.assertEqual(232, tests["test"]["line"])
        self.assertEqual([237, 243], [item["line"] for item in tests["request_sites"]])
        self.assertEqual([240, 241, 246, 247], [item["line"] for item in tests["assertions"]])
        self.assertEqual(2, tests["request_site_count"])
        self.assertIn("API alias and Bearer authentication", tests["known_gaps"])

        counting = self.document["caller_counting"]
        self.assertEqual(1, counting["legacy_web_direct_network_call_site_count"])
        self.assertEqual(7, counting["legacy_miniprogram_typescript_direct_call_site_count"])
        self.assertEqual(6, counting["legacy_miniprogram_typescript_direct_source_file_count"])
        self.assertEqual(1, counting["legacy_miniprogram_indirect_consumer_count"])
        self.assertEqual(2, counting["legacy_test_request_site_count"])
        self.assertEqual(0, counting["generated_javascript_additional_count"])
        self.assertTrue(all(self.document["closure"].values()))

    def test_source_and_controlled_copy_drift_fail_closed(self) -> None:
        with patch.object(capture, "read_legacy_blob", return_value=b"changed\n"):
            with self.assertRaisesRegex(AssertionError, "caller drifted"):
                capture.legacy_source_line(Path("/unused"), "fake.py", 1, "expected")
            with self.assertRaisesRegex(AssertionError, "baseline drifted"):
                capture.controlled_copy_attestation(REPOSITORY_ROOT)


if __name__ == "__main__":
    unittest.main()
