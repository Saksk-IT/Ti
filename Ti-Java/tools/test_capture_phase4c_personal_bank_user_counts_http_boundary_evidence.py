#!/usr/bin/env python3
"""Contract checks for the fixed legacy user-count HTTP boundary evidence."""

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
EVIDENCE = TI_JAVA / (
    "docs/refactor/phase4c/personal-bank-user-counts-http-boundary-evidence.json"
)
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4c_personal_bank_user_counts_http_boundary_evidence as capture  # noqa: E402


class PersonalBankUserCountsHttpBoundaryEvidenceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized = EVIDENCE.read_text(encoding="utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_01_identity_payload_provenance_redaction_and_recapture_close(self) -> None:
        document = self.document
        self.assertEqual(
            "ti.phase4c.personal-bank-user-counts-http-boundary-evidence",
            document["contract_id"],
        )
        self.assertEqual(1, document["schema_version"])
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(capture.LEGACY_COMMIT, capture.golden.LEGACY_COMMIT)
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
        tool_sha = hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest()
        test_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.assertEqual(tool_sha, provenance["capture_tool"]["sha256"])
        self.assertEqual(test_sha, provenance["capture_test"]["sha256"])
        self.assertEqual(tool_sha, provenance["hashes"]["capture_tool_sha256"])
        self.assertEqual(test_sha, provenance["hashes"]["capture_test_sha256"])
        self.assertEqual(
            document["case_payload_sha256"],
            provenance["hashes"]["case_payload_sha256"],
        )
        self.assertEqual(
            document["runtime_route_map"]["selected_rules_sha256"],
            provenance["hashes"]["runtime_route_map_sha256"],
        )
        for name in (
            "flask", "werkzeug", "sqlalchemy", "flask_sqlalchemy", "flask_cors"
        ):
            self.assertRegex(provenance["runtime_versions"][name], r"^\d+\.\d+")

        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)
        self.assertNotIn("@test.example.com", self.serialized)
        self.assertNotRegex(
            self.serialized, r"Bearer (?!<redacted)[A-Za-z0-9_-]+"
        )
        self.assertNotRegex(
            self.serialized, re.compile(r'"last_active"\s*:', re.MULTILINE)
        )
        for case in document["cases"]:
            headers = case["response"]["headers"]
            for cookie in headers.get("Set-Cookie", []):
                self.assertEqual("<redacted-session-cookie>", cookie)

        recaptured = capture.capture_document(REPOSITORY_ROOT)
        self.assertEqual(self.serialized, capture.render_document(recaptured))

    def test_02_complete_archive_sources_matrix_and_runtime_route_map_are_fixed(self) -> None:
        source = self.document["legacy_source_attestation"]
        archive = source["complete_app_archive"]
        self.assertTrue(archive["complete_app_tree_verified"])
        self.assertEqual(capture.LEGACY_COMMIT, archive["archive_commit"])
        self.assertGreaterEqual(archive["extracted_file_count"], 600)
        self.assertEqual(set(capture.SELECTED_KEY_SOURCES), set(source["key_sources"]))
        self.assertEqual(
            "git show from verified fixed commit",
            source["key_sources"]["requirements.txt"]["transport"],
        )
        matrix = source["frozen_route_matrix"]
        self.assertEqual(
            {"6858f6fa506f", "006913d0d956"},
            {row["route_id"] for row in matrix["selected_rows"]},
        )
        self.assertTrue(all(
            row["migration_status"] == "pending"
            and row["methods"] == "GET"
            and row["decorators"] == '["auth_required"]'
            for row in matrix["selected_rows"]
        ))

        route_map = self.document["runtime_route_map"]
        self.assertEqual(
            route_map["selected_rules_sha256"],
            capture.sha256_json(route_map["selected_rules"]),
        )
        self.assertEqual(2, len(route_map["selected_rules"]))
        for rule in route_map["selected_rules"]:
            self.assertEqual(["GET", "HEAD", "OPTIONS"], rule["methods"])
            self.assertEqual(["bank_id"], rule["arguments"])
            self.assertEqual(
                "werkzeug.routing.converters.IntegerConverter",
                rule["converter"]["class"],
            )
            self.assertFalse(rule["converter"]["signed"])
            self.assertIsNone(rule["converter"]["min"])
            self.assertIsNone(rule["converter"]["max"])

        helpers = self.document["provenance"]["phase4_helpers"]
        self.assertEqual(
            {path.relative_to(capture.TI_JAVA).as_posix() for path in capture.HELPER_PATHS},
            set(helpers),
        )
        for relative, expected in helpers.items():
            self.assertEqual(
                expected,
                hashlib.sha256((capture.TI_JAVA / relative).read_bytes()).hexdigest(),
            )

    def test_03_both_aliases_authenticate_and_redirect_exactly_as_observed(self) -> None:
        for route in capture.ROUTES:
            expected = {
                f"auth-session-{route}": (200, "session"),
                f"auth-bearer-{route}": (
                    200 if route == "api-alias" else 302,
                    "valid_bearer_only",
                ),
                f"auth-invalid-bearer-with-session-{route}": (
                    200, "session+invalid_bearer"
                ),
                f"auth-invalid-bearer-only-{route}": (
                    401 if route == "api-alias" else 302,
                    "invalid_bearer_only",
                ),
                f"auth-anonymous-{route}": (
                    401 if route == "api-alias" else 302, "anonymous"
                ),
            }
            for case_id, (status, mode) in expected.items():
                with self.subTest(case_id=case_id):
                    case = self.by_id[case_id]
                    self.assertEqual(status, case["response"]["status"])
                    self.assertEqual(mode, case["credential_mode"])
                    self.assertEqual(
                        capture.ROUTES[route]["legacy_handler"],
                        case["request_observation"]["flask"]["endpoint"],
                    )
            for suffix in ("bearer", "invalid-bearer-only", "anonymous"):
                case = self.by_id[f"auth-{suffix}-web-alias"]
                if case["response"]["status"] == 302:
                    self.assertEqual(["/login"], case["response"]["headers"]["Location"])

        for route in capture.ROUTES:
            fallback = self.by_id[f"auth-invalid-bearer-with-session-{route}"]
            self.assertEqual(
                [capture.golden.ACTORS["owner"]],
                fallback["effects"]["user_last_active_changed_user_ids"],
            )
            bearer = self.by_id[f"auth-bearer-{route}"]
            self.assertEqual([], bearer["effects"]["user_last_active_changed_user_ids"])

    def test_04_path_converter_normalization_rejection_and_overflow_are_observed(self) -> None:
        expected_status = {
            "zero": 403,
            "leading-zero": 200,
            "unicode-nd-arabic-indic": 200,
            "unicode-nd-fullwidth": 200,
            "negative": 404,
            "nondigit": 404,
            "encoded-ascii-digits": 200,
            "encoded-slash": 308,
            "matrix": 404,
            "int-overflow": 403,
            "long-overflow": 500,
        }
        parsed = {
            "zero": 0,
            "leading-zero": capture.OWNER_BANK_ID,
            "unicode-nd-arabic-indic": capture.OWNER_BANK_ID,
            "unicode-nd-fullwidth": capture.OWNER_BANK_ID,
            "encoded-ascii-digits": capture.OWNER_BANK_ID,
            "int-overflow": 2147483648,
            "long-overflow": 9223372036854775808,
        }
        unmatched = {"negative", "nondigit", "encoded-slash", "matrix"}
        for route in capture.ROUTES:
            for name, status in expected_status.items():
                case_id = f"path-{name}-{route}"
                with self.subTest(case_id=case_id):
                    case = self.by_id[case_id]
                    self.assertEqual(status, case["response"]["status"])
                    flask = case["request_observation"]["flask"]
                    if name in parsed:
                        self.assertEqual(parsed[name], flask["view_args"]["bank_id"])
                        self.assertEqual(
                            capture.ROUTES[route]["legacy_handler"], flask["endpoint"]
                        )
                    if name in unmatched:
                        self.assertIsNone(flask["matched_rule"])
                        self.assertEqual([], case["effects"]["sql"][
                            "personal_bank_query_sequence"
                        ])

        encoded = self.by_id["path-encoded-ascii-digits-api-alias"]
        self.assertIn("%39", encoded["request"]["input_path"])
        self.assertEqual(
            str(capture.OWNER_BANK_ID),
            encoded["request_observation"]["wsgi"]["path_info"].rsplit("/", 2)[-2],
        )
        long_overflow = self.by_id["path-long-overflow-api-alias"]
        self.assertNotIn(
            "9223372036854775808", json.dumps(long_overflow["response"], ensure_ascii=False)
        )

    def test_05_duplicate_query_keys_are_ordered_and_first_value_wins(self) -> None:
        expected_query = {
            "q-type": [["q_type", "选择题"], ["q_type", "简答题"]],
            "source": [["source", "favorites"], ["source", "mistakes"]],
            "tag": [["tag", "all"], ["tag", "重点"]],
        }
        for route in capture.ROUTES:
            for name, query in expected_query.items():
                case = self.by_id[f"query-duplicate-{name}-{route}"]
                self.assertEqual(query, case["request"]["query"])
                self.assertEqual(
                    query, case["request_observation"]["flask"]["query_items"]
                )
            q_type = capture.response_counts(
                self.by_id[f"query-duplicate-q-type-{route}"]
            )
            self.assertEqual((2, 2, 0), (
                q_type["total"], q_type["favorites"], q_type["mistakes"]
            ))
            source = capture.response_counts(
                self.by_id[f"query-duplicate-source-{route}"]
            )
            self.assertEqual((5, 5, 3), (
                source["total"], source["favorites"], source["mistakes"]
            ))
            tag = self.by_id[f"query-duplicate-tag-{route}"]
            self.assertEqual(capture.golden.BASE_COUNTS, capture.response_counts(tag))
            self.assertEqual(0, tag["effects"]["sql"]["ddl_attempts"])
            self.assertEqual(
                0, tag["effects"]["sql"]["raw_connection_execute_attempt_count"]
            )

    def test_06_accept_negotiation_distinguishes_api_prefix_from_web(self) -> None:
        for route in capture.ROUTES:
            for failure, status in (("404", 404), ("long-overflow-500", 500)):
                for media in ("html", "json"):
                    case = self.by_id[f"negotiation-{failure}-{media}-{route}"]
                    self.assertEqual(status, case["response"]["status"])
                    expected = "json" if route == "api-alias" or media == "json" else "text"
                    self.assertEqual(expected, case["response"]["body_kind"])
                    content_type = case["response"]["headers"]["Content-Type"][0]
                    self.assertTrue(
                        content_type.startswith("application/json")
                        if expected == "json"
                        else content_type.startswith("text/html")
                    )
        for case in self.document["cases"]:
            response_text = json.dumps(case["response"], ensure_ascii=False)
            self.assertNotIn("Python int too large", response_text)
            self.assertNotIn("sqlalchemy", response_text.lower())
            self.assertNotIn("SELECT * FROM", response_text)

    def test_07_head_and_options_retain_auth_without_accidental_handler_entry(self) -> None:
        for route in capture.ROUTES:
            head = self.by_id[f"method-head-session-{route}"]
            self.assertEqual(200, head["response"]["status"])
            self.assertEqual(0, head["response"]["body_length_bytes"])
            self.assertEqual(
                [
                    "personal_bank_user_counts_bank_access_probe",
                    "personal_bank_user_counts_total_all",
                    "personal_bank_user_counts_favorites_count",
                    "personal_bank_user_counts_mistakes_count",
                    "personal_bank_user_counts_types_all",
                ],
                head["effects"]["sql"]["personal_bank_query_sequence"],
            )

            options = self.by_id[f"method-options-session-{route}"]
            self.assertEqual(200, options["response"]["status"])
            self.assertEqual(
                ["GET, HEAD, OPTIONS"], options["response"]["headers"]["Allow"]
            )
            self.assertEqual(
                [], options["effects"]["sql"]["personal_bank_query_sequence"]
            )

            anonymous_status = 401 if route == "api-alias" else 302
            for method in ("head", "options"):
                case = self.by_id[f"method-{method}-anonymous-{route}"]
                self.assertEqual(anonymous_status, case["response"]["status"])
                self.assertEqual(
                    [], case["effects"]["sql"]["personal_bank_query_sequence"]
                )

    def test_08_observations_targets_gaps_and_non_authorizations_stay_separate(self) -> None:
        separation = self.document["observation_and_target_separation"]
        self.assertTrue(separation["legacy_observations_are_descriptive_not_normative"])
        targets = {
            item["id"]: item
            for item in separation["future_security_targets_and_open_decisions"]
        }
        self.assertEqual(
            {
                "authoritative-identity", "invalid-bearer-with-session",
                "matrix-path", "numeric-domain", "parameter-pollution",
                "head-options", "safe-error-negotiation",
            },
            set(targets),
        )
        self.assertEqual(
            "entry_contract_decision_required",
            targets["invalid-bearer-with-session"]["kind"],
        )
        self.assertEqual(
            "approved_security_target", targets["matrix-path"]["kind"]
        )
        self.assertTrue(all(
            not item["proved_by_this_capture"] for item in targets.values()
        ))
        non_authorizations = set(separation["non_authorizations"])
        self.assertIn("Java HTTP controller implementation", non_authorizations)
        self.assertIn("Spring Security or rate-limit implementation", non_authorizations)
        self.assertIn(
            "future CORS origin/header/method/credentials policy", non_authorizations
        )
        self.assertIn("production cutover", non_authorizations)

        gaps = {item["id"]: item for item in self.document["evidence_gaps"]}
        self.assertEqual(
            {
                "socket-and-reverse-proxy-raw-target",
                "browser-cors-enforcement-and-cookie-credentials",
                "reverse-proxy-cors-header-preservation",
                "future-java-filter-and-binding-order",
                "production-database-and-network",
            },
            set(gaps),
        )
        self.assertIn("test_client", gaps[
            "socket-and-reverse-proxy-raw-target"
        ]["gap"])
        self.assertIn("route-map", gaps[
            "future-java-filter-and-binding-order"
        ]["compensating_attestation"])
        self.assertIn(
            "does not enforce the browser",
            gaps["browser-cors-enforcement-and-cookie-credentials"]["gap"],
        )
        self.assertIn(
            "no ingress or reverse proxy",
            gaps["reverse-proxy-cors-header-preservation"]["gap"],
        )

        state = self.document["route_state"]
        self.assertFalse(state["controller_added_by_this_evidence"])
        self.assertFalse(state["security_matcher_added_by_this_evidence"])
        self.assertFalse(state["route_or_openapi_delta"])
        self.assertFalse(state["production_cutover"])
        self.assertTrue(all(
            operation["reviewed_http_owner"] == "learning"
            and operation["migration_status"] == "pending"
            and not operation["production_cutover"]
            for operation in state["operations"]
        ))
        for case in self.document["cases"]:
            self.assertTrue(case["effects"]["business_tables_unchanged"])
            self.assertTrue(case["effects"]["users_identity_unchanged"])
            self.assertEqual(
                0, case["effects"]["sql"]["business_table_dml_attempt_count"]
            )

    def test_09_cors_headers_preflight_auth_and_handler_effects_are_observed(self) -> None:
        cors = self.document["cors_runtime_evidence"]
        config = cors["fixed_source_configuration"]
        self.assertEqual("app/core/extensions.py", config["source"])
        self.assertEqual(
            self.document["legacy_source_attestation"]["key_sources"]
            ["app/core/extensions.py"]["sha256"],
            config["sha256"],
        )
        self.assertEqual("/api/*", config["resource_pattern"])
        self.assertEqual(capture.ALLOWED_CORS_ORIGIN, config["source_default_origin"])
        self.assertEqual(
            ["Content-Type", "Authorization"], config["configured_allow_headers"]
        )
        self.assertFalse(config["configured_supports_credentials"])
        self.assertEqual(8, cors["observation_count"])
        self.assertEqual(
            cors["observations_sha256"],
            capture.sha256_json(cors["observations"]),
        )
        self.assertEqual(
            cors["observations_sha256"],
            self.document["provenance"]["hashes"]["cors_observations_sha256"],
        )
        summaries = {item["case_id"]: item for item in cors["observations"]}
        self.assertEqual(
            {case_id for case_id, case in self.by_id.items() if case["category"] == "cors"},
            set(summaries),
        )

        baseline_sequence = [
            "personal_bank_user_counts_bank_access_probe",
            "personal_bank_user_counts_total_all",
            "personal_bank_user_counts_favorites_count",
            "personal_bank_user_counts_mistakes_count",
            "personal_bank_user_counts_types_all",
        ]
        for route in capture.ROUTES:
            api = route == "api-alias"
            for disposition, origin in (
                ("allowed", capture.ALLOWED_CORS_ORIGIN),
                ("rejected", capture.REJECTED_CORS_ORIGIN),
            ):
                get_id = f"cors-get-{disposition}-origin-{route}"
                get_case = self.by_id[get_id]
                get_summary = summaries[get_id]
                self.assertEqual(200, get_case["response"]["status"])
                self.assertEqual(origin, get_case["request"]["headers"]["Origin"])
                self.assertEqual(
                    origin, get_case["request_observation"]["flask"]["origin"]
                )
                self.assertEqual("session", get_case["credential_mode"])
                self.assertTrue(get_summary["execution"]["flask_route_matched"])
                self.assertFalse(get_summary["execution"][
                    "terminal_global_auth_response_observed"
                ])
                self.assertEqual(
                    1, get_summary["execution"]["session_authority_select_attempts"]
                )
                self.assertEqual(1, get_summary["execution"]["last_active_write_attempts"])
                self.assertEqual(
                    [capture.golden.ACTORS["owner"]],
                    get_summary["execution"]["last_active_changed_user_ids"],
                )
                self.assertTrue(get_summary["execution"][
                    "handler_business_query_observed"
                ])
                self.assertEqual(
                    baseline_sequence,
                    get_summary["execution"]["personal_bank_business_query_sequence"],
                )
                self.assertEqual(
                    [capture.ALLOWED_CORS_ORIGIN]
                    if api and disposition == "allowed" else [],
                    get_summary["response"]["access_control_allow_origin"],
                )
                self.assertEqual(
                    ["Cookie, Origin"]
                    if api and disposition == "allowed" else ["Cookie"],
                    get_summary["response"]["vary"],
                )
                self.assertEqual(
                    [], get_summary["response"]["access_control_allow_credentials"]
                )

                preflight_id = f"cors-preflight-{disposition}-origin-{route}"
                preflight = self.by_id[preflight_id]
                preflight_summary = summaries[preflight_id]
                self.assertEqual(
                    401 if api else 302, preflight["response"]["status"]
                )
                self.assertEqual("anonymous", preflight["credential_mode"])
                self.assertEqual(
                    capture.CORS_PREFLIGHT_METHOD,
                    preflight["request_observation"]["flask"]
                    ["access_control_request_method"],
                )
                self.assertEqual(
                    capture.CORS_PREFLIGHT_HEADERS,
                    preflight["request_observation"]["flask"]
                    ["access_control_request_headers"],
                )
                self.assertTrue(preflight_summary["execution"]["flask_route_matched"])
                self.assertTrue(preflight_summary["execution"][
                    "terminal_global_auth_response_observed"
                ])
                self.assertEqual(
                    0, preflight_summary["execution"]["session_authority_select_attempts"]
                )
                self.assertEqual(
                    0, preflight_summary["execution"]["last_active_write_attempts"]
                )
                self.assertEqual(
                    [], preflight_summary["execution"]["last_active_changed_user_ids"]
                )
                self.assertFalse(preflight_summary["execution"][
                    "handler_business_query_observed"
                ])
                self.assertEqual(
                    [], preflight_summary["execution"]
                    ["personal_bank_business_query_sequence"],
                )
                self.assertEqual(
                    [capture.ALLOWED_CORS_ORIGIN]
                    if api and disposition == "allowed" else [],
                    preflight_summary["response"]["access_control_allow_origin"],
                )
                self.assertEqual(
                    ["Authorization, Content-Type"]
                    if api and disposition == "allowed" else [],
                    preflight_summary["response"]["access_control_allow_headers"],
                )
                self.assertNotIn(
                    "X-Request-ID",
                    ", ".join(preflight_summary["response"]
                              ["access_control_allow_headers"]),
                )
                self.assertEqual(
                    ["DELETE, GET, OPTIONS, POST, PUT"]
                    if api and disposition == "allowed" else [],
                    preflight_summary["response"]["access_control_allow_methods"],
                )
                self.assertEqual(
                    [], preflight_summary["response"]
                    ["access_control_allow_credentials"],
                )
                self.assertEqual(
                    ["Cookie, Origin"]
                    if api and disposition == "allowed" else ["Cookie"],
                    preflight_summary["response"]["vary"],
                )

        boundary = cors["interpretation_boundary"]
        self.assertTrue(boundary["server_headers_and_app_execution_observed"])
        self.assertFalse(boundary["browser_cors_enforcement_observed"])
        self.assertFalse(boundary["reverse_proxy_header_preservation_observed"])
        self.assertFalse(boundary["future_allowed_origins_authorized"])
        self.assertFalse(boundary["future_credentials_policy_authorized"])
        self.assertFalse(boundary["future_preflight_auth_order_authorized"])
        decision = self.document["observation_and_target_separation"]
        self.assertEqual(
            "not_proposed_or_authorized_by_this_evidence",
            decision["cors_policy_decision"]["status"],
        )


if __name__ == "__main__":
    unittest.main()
