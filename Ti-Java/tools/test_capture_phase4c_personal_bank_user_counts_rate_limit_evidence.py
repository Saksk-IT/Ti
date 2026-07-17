#!/usr/bin/env python3
"""Contract tests for Phase 4C personal-bank user-count rate-limit evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
EVIDENCE = (
    TI_JAVA
    / "docs/refactor/phase4c/personal-bank-user-counts-rate-limit-evidence.json"
)
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4c_personal_bank_user_counts_rate_limit_evidence as capture  # noqa: E402


class PersonalBankUserCountsRateLimitEvidenceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized = EVIDENCE.read_text(encoding="utf-8")
        cls.document = json.loads(cls.serialized)
        cls.runtime = cls.document["legacy_runtime_observations"]

    @staticmethod
    def sample(sequence: dict, attempt: int) -> dict:
        matches = [
            item for item in sequence["samples"]
            if item["attempt"] == attempt
        ]
        if len(matches) != 1:
            raise AssertionError(f"missing sample {attempt}")
        return matches[0]

    def test_fixed_commit_provenance_hashes_redaction_and_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            "ti.phase4c.personal-bank-user-counts-rate-limit-evidence",
            document["contract_id"],
        )
        self.assertEqual(
            "fixed_legacy_observation_only_target_proposal_not_authorized",
            document["status"],
        )
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        capture.assert_evidence_contract(document)
        self.assertEqual(capture.render_document(document), self.serialized)

        provenance = document["provenance"]
        self.assertEqual(
            hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest(),
            provenance["capture_tool"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            provenance["capture_test"]["sha256"],
        )
        for relative_path, expected_hash in provenance["support_sources"].items():
            self.assertEqual(
                hashlib.sha256((TI_JAVA / relative_path).read_bytes()).hexdigest(),
                expected_hash,
            )
        archive = document["legacy_source_attestation"]["complete_app_archive"]
        self.assertTrue(archive["commit_object_verified"])
        self.assertTrue(archive["complete_app_tree_verified"])
        self.assertEqual(capture.LEGACY_COMMIT, archive["archive_commit"])
        self.assertGreaterEqual(archive["extracted_file_count"], 600)
        self.assertEqual(
            set(capture.KEY_SOURCE_FILES),
            set(document["legacy_source_attestation"]["key_sources"]),
        )

        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("@test.example.com", self.serialized)
        self.assertNotIn("Bearer eyJ", self.serialized)
        self.assertNotRegex(self.serialized, r"redis://127\.0\.0\.1:\d+")
        self.assertNotRegex(
            self.serialized,
            re.compile(r'"X-RateLimit-Reset":\s*\[\s*"\d+', re.MULTILINE),
        )
        self.assertNotRegex(
            self.serialized,
            re.compile(r'"Retry-After":\s*\[\s*"\d+', re.MULTILINE),
        )

        recaptured = capture.capture_document(REPOSITORY_ROOT)
        self.assertEqual(self.serialized, capture.render_document(recaptured))

    def test_base_limits_and_production_effective_difference_are_not_conflated(self) -> None:
        facts = self.document["legacy_source_facts"]
        self.assertEqual(
            "5000 per day;500 per hour;10 per second",
            facts["base_configuration"]["value"],
        )
        self.assertEqual(
            [
                {"count": 10, "unit": "second"},
                {"count": 500, "unit": "hour"},
                {"count": 5000, "unit": "day"},
            ],
            facts["base_configuration"]["windows"],
        )
        production = facts["production_configuration"]
        self.assertEqual(100, production["default_multiplier"])
        self.assertEqual(
            "500000/day;50000/hour;1000/second",
            production["default_effective_value"],
        )
        self.assertTrue(production["base_values_are_not_fixed_commit_production_defaults"])
        self.assertTrue(production["redis_required"])
        self.assertTrue(production["memory_storage_rejected_when_not DEBUG or TESTING"])

        handler = facts["handler"]
        self.assertFalse(handler["route_specific_limiter"])
        self.assertEqual(
            "application-wide RATELIMIT_DEFAULT",
            handler["limiter_source"],
        )
        self.assertEqual(
            {
                "user_bank_api_bp.route('/<int:bank_id>/user-counts', methods=['GET'])",
                "auth_required",
            },
            set(handler["decorators"]),
        )

    def test_all_three_base_windows_allow_the_limit_and_reject_limit_plus_one(self) -> None:
        cases = (
            ("base_10_per_second", 10, "10", None),
            ("isolated_500_per_hour", 500, "500", "500 per hour"),
            ("isolated_5000_per_day", 5000, "5000", "5000 per day"),
        )
        for name, limit, header_limit, override in cases:
            with self.subTest(name=name):
                observation = self.runtime[name]
                sequence = observation["sequence"]
                self.assertEqual(limit + 1, sequence["attempt_count"])
                self.assertEqual(limit, sequence["status_counts"]["403"])
                self.assertEqual(1, sequence["status_counts"]["429"])
                threshold = self.sample(sequence, limit)
                breach = self.sample(sequence, limit + 1)
                self.assertEqual(403, threshold["response"]["status"])
                self.assertEqual(1, threshold["handler_bank_access_probe_delta"])
                self.assertEqual(429, breach["response"]["status"])
                self.assertEqual(0, breach["handler_bank_access_probe_delta"])
                self.assertEqual(
                    [header_limit],
                    breach["response"]["headers"]["X-RateLimit-Limit"],
                )
                self.assertEqual(
                    ["0"],
                    breach["response"]["headers"]["X-RateLimit-Remaining"],
                )
                if override is None:
                    self.assertIsNone(observation["isolated_window_override"])
                    self.assertEqual(
                        "fixed_commit_real_route_combined_base_config",
                        observation["observation_kind"],
                    )
                else:
                    diagnostic = observation["isolated_window_override"]
                    self.assertFalse(diagnostic["source_mutated"])
                    self.assertEqual(
                        f"RATELIMIT_DEFAULT={override}",
                        diagnostic["runtime_config_override"],
                    )
                self.assertFalse(observation["production_observation"])

    def test_alias_buckets_are_independent_and_429_negotiation_is_exact(self) -> None:
        scope = self.runtime["scope_identity_and_negotiation"]
        aliases = scope["alias_buckets"]
        self.assertEqual(
            "independent_per_registered_endpoint",
            aliases["result"],
        )
        self.assertEqual(
            403,
            aliases["web_attempt_one_after_api_exhaustion"]["status"],
        )
        self.assertEqual(429, aliases["api_attempt_eleven"]["status"])
        self.assertEqual(
            429,
            aliases["web_remaining_attempts_two_through_eleven"]
            ["samples"][-1]["response"]["status"],
        )

        negotiated = scope["response_negotiation"]
        api = negotiated["api_json_429"]
        web_html = negotiated["web_default_html_429"]
        web_json = negotiated["web_accept_json_429"]
        self.assertEqual("json", api["body_kind"])
        self.assertEqual("text", web_html["body_kind"])
        self.assertIn("429 - Too Many Requests", web_html["body"])
        self.assertEqual("json", web_json["body_kind"])
        for response in (api, web_html, web_json):
            self.assertEqual(["10"], response["headers"]["X-RateLimit-Limit"])
            self.assertEqual(["0"], response["headers"]["X-RateLimit-Remaining"])
            self.assertEqual(
                ["<rate-limit-reset-epoch>"],
                response["headers"]["X-RateLimit-Reset"],
            )
            self.assertEqual(
                ["<dynamic-seconds>"],
                response["headers"]["Retry-After"],
            )
        for response in (api, web_json):
            self.assertEqual("error", response["body"]["status"])
            self.assertEqual(429, response["body"]["status_code"])
            self.assertIn("payload", response["body"])
            self.assertIsNone(response["body"]["payload"])

    def test_session_bearer_and_remote_address_key_precedence_is_observed(self) -> None:
        keys = self.runtime["scope_identity_and_negotiation"]["key_behavior"]
        session = keys["same_session_across_remote_addresses"]
        self.assertEqual(429, self.sample(session, 11)["response"]["status"])

        anonymous = keys["anonymous_same_remote_address"]
        self.assertEqual(10, anonymous["status_counts"]["401"])
        self.assertEqual(1, anonymous["status_counts"]["429"])
        self.assertEqual(
            401,
            keys["anonymous_new_remote_address_after_breach"]["status"],
        )

        distinct = keys["distinct_sessions_same_remote_address"]
        self.assertEqual(403, distinct["other_first"]["status"])
        self.assertEqual(429, distinct["owner_attempt_eleven"]["status"])

        conflict = keys["session_precedes_conflicting_bearer_for_limiter_key"]
        self.assertEqual(
            {"403": 10},
            conflict["session_owner_plus_bearer_other_first_ten"]["status_counts"],
        )
        self.assertEqual(
            429,
            conflict["session_owner_without_bearer_attempt_eleven"]["status"],
        )
        self.assertEqual(
            200,
            conflict["session_owner_after_reset_baseline"]["status"],
        )
        bearer = keys["bearer_only_same_actor_across_remote_addresses"]
        self.assertEqual(10, bearer["status_counts"]["200"])
        self.assertEqual(1, bearer["status_counts"]["429"])

    def test_real_client_redis_refusal_is_legacy_500_and_target_503_is_only_a_proposal(self) -> None:
        failure = self.runtime["redis_storage_failure"]
        self.assertFalse(failure["mocked_storage"])
        self.assertFalse(failure["live_redis_server_started_then_failed"])
        self.assertEqual(500, failure["response"]["status"])
        self.assertEqual(0, failure["handler_bank_access_probe_count"])
        self.assertEqual(0, failure["sql_statement_count"])
        self.assertEqual(
            {
                "message": "An unexpected server error occurred.",
                "payload": None,
                "request_id": "phase4c-rate-redis-unavailable",
                "status": "error",
                "status_code": 500,
            },
            failure["response"]["body"],
        )
        for header in (
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ):
            self.assertNotIn(header, failure["response"]["headers"])

        gap = self.document["redis_gap"]
        self.assertTrue(gap["connection_refusal_closed"])
        self.assertTrue(gap["real_redis_client_used"])
        self.assertFalse(gap["live_server_started_then_interrupted"])
        self.assertIn(
            "counter continuity after Redis restarts",
            gap["what_is_not_proved"],
        )
        target = self.document["proposed_target_contract"]
        self.assertEqual(
            "proposal_only_not_implemented_or_authorized",
            target["status"],
        )
        self.assertEqual("fail_closed", target["storage_failure"]["policy"])
        self.assertEqual(503, target["storage_failure"]["proposed_status"])
        self.assertEqual(
            "not proposed and not authorized",
            target["storage_failure"]["fail_open"],
        )

    def test_negative_tamper_and_overclaim_cases_are_rejected(self) -> None:
        tampered_breach = copy.deepcopy(self.document)
        tampered_breach["legacy_runtime_observations"]["base_10_per_second"][
            "sequence"
        ]["samples"][-1]["response"]["status"] = 200
        with self.assertRaisesRegex(AssertionError, "must be HTTP 429"):
            capture.assert_evidence_contract(tampered_breach, verify_hashes=False)

        production_overclaim = copy.deepcopy(self.document)
        production_overclaim["legacy_source_facts"]["production_configuration"][
            "base_values_are_not_fixed_commit_production_defaults"
        ] = False
        with self.assertRaisesRegex(AssertionError, "misrepresented"):
            capture.assert_evidence_contract(production_overclaim, verify_hashes=False)

        implemented_overclaim = copy.deepcopy(self.document)
        implemented_overclaim["proposed_target_contract"]["status"] = "implemented"
        with self.assertRaisesRegex(AssertionError, "misrepresented as implemented"):
            capture.assert_evidence_contract(implemented_overclaim, verify_hashes=False)

        fail_open = copy.deepcopy(self.document)
        fail_open["proposed_target_contract"]["storage_failure"]["policy"] = "fail_open"
        with self.assertRaisesRegex(AssertionError, "must fail closed"):
            capture.assert_evidence_contract(fail_open, verify_hashes=False)


if __name__ == "__main__":
    unittest.main()
