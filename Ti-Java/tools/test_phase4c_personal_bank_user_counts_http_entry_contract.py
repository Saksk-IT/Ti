#!/usr/bin/env python3
"""Fail-closed checks for the Phase 4C user-counts HTTP entry gate."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    from tools import build_phase4c_personal_bank_user_counts_http_entry_contract as builder
    from tools import phase4c_http_entry_successor_acceptance as acceptance
    from tools.phase4c_http_entry_successor_acceptance import (
        CONTRACT_ID,
        CONTRACT_STATUS,
        SUCCESSOR_SOURCES,
        load_http_entry_successor_contract,
        validate_http_entry_successor_contract,
    )
    from tools.phase4c_http_implementation_successor_acceptance import (
        load_http_implementation_successor_contract,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    import build_phase4c_personal_bank_user_counts_http_entry_contract as builder
    import phase4c_http_entry_successor_acceptance as acceptance
    from phase4c_http_entry_successor_acceptance import (
        CONTRACT_ID,
        CONTRACT_STATUS,
        SUCCESSOR_SOURCES,
        load_http_entry_successor_contract,
        validate_http_entry_successor_contract,
    )
    from phase4c_http_implementation_successor_acceptance import (
        load_http_implementation_successor_contract,
    )


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / (
    "docs/refactor/phase4c/personal-bank-user-counts-http-entry-contract.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_production_runtime_successor(*args, **kwargs):
    try:
        from tools.phase4c_tag_migration_global_preflight_successor_acceptance import (
            validate_production_runtime_successor as validate_successor,
        )
    except ModuleNotFoundError as error:  # Direct script execution from tools/.
        if error.name not in {
            "tools",
            "tools.phase4c_tag_migration_global_preflight_successor_acceptance",
        }:
            raise
        from phase4c_tag_migration_global_preflight_successor_acceptance import (
            validate_production_runtime_successor as validate_successor,
        )
    return validate_successor(*args, **kwargs)


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def document_payload_sha256(document: dict) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class Phase4cPersonalBankUserCountsHttpEntryContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_http_entry_successor_contract(ROOT)
        if cls.contract is None:
            raise AssertionError("Phase4C HTTP entry contract is required")
        cls.implementation = load_http_implementation_successor_contract(ROOT)
        if cls.implementation is None:
            raise AssertionError("Phase4C HTTP implementation successor is required")
        cls.predecessor = json.loads(
            (ROOT / builder.PREDECESSOR_RELATIVE).read_text(encoding="utf-8")
        )
        cls.boundary = json.loads(
            (ROOT / builder.BOUNDARY_RELATIVE).read_text(encoding="utf-8")
        )
        cls.rate = json.loads(
            (ROOT / builder.RATE_RELATIVE).read_text(encoding="utf-8")
        )

    def test_01_identity_predecessor_payload_sources_and_determinism_close(self) -> None:
        contract = self.contract
        self.assertEqual(CONTRACT_ID, contract["contract_id"])
        self.assertEqual(CONTRACT_STATUS, contract["status"])
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "phase4c-personal-bank-user-counts-http-entry-gate",
            contract["scope"],
        )
        self.assertEqual(
            builder.PREDECESSOR_SHA256,
            sha256(ROOT / builder.PREDECESSOR_RELATIVE),
        )
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            self.predecessor["document_payload_sha256"],
        )
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            document_payload_sha256(self.predecessor),
        )
        self.assertEqual(
            contract["document_payload_sha256"],
            document_payload_sha256(contract),
        )
        for name, reference in contract["source_contracts"].items():
            source = ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            self.assertEqual(
                sha256(source),
                acceptance._validated_terminal_sha256(
                    ROOT, reference["source"], reference["sha256"]
                ),
                name,
            )

    def test_02_current_production_surface_is_byte_identical_and_routes_stay_pending(self) -> None:
        current = self.contract["current_state"]
        surface = current["current_production_surface"]
        self.assertFalse(current["implementation_started"])
        for field in (
            "controller_present",
            "route_security_present",
            "route_rate_limiter_present",
            "route_cors_present",
            "openapi_overlay_present",
        ):
            self.assertFalse(current[field], field)
        self.assertEqual(27, surface["public_application_method_count"])
        self.assertEqual(
            self.predecessor["implementation"]["public_application_methods"],
            surface["public_application_methods"],
        )
        transition = self.implementation["implementation"][
            "production_runtime_transition"
        ]
        accepted_main = transition["learning_and_personalbank"]["files"]
        main = builder.read_builder.main_source_manifest()
        if main == accepted_main:
            self.assertEqual(40, len(main))
        else:
            successor = validate_production_runtime_successor(
                ROOT,
                accepted_main,
                main,
                view="learning_personalbank_main",
            )
            self.assertEqual(40, successor.accepted_file_count)
            self.assertEqual(50, successor.current_file_count)
            self.assertEqual([], list(successor.changed_files))
            self.assertEqual([], list(successor.deleted_files))
        self.assertEqual(
            builder.EXPECTED_MAIN_MANIFEST_SHA256,
            builder.sha256_json(accepted_main),
        )
        self.assertEqual(
            288, surface["production_runtime_file_count"]
        )
        self.assertEqual(
            builder.EXPECTED_RUNTIME_MANIFEST_SHA256,
            surface["production_runtime_manifest_sha256"],
        )
        self.assertEqual(5, surface["route_status_file_count"])
        self.assertEqual(
            builder.EXPECTED_ROUTE_MANIFEST_SHA256,
            surface["route_status_manifest_sha256"],
        )
        self.assertEqual(
            builder.EXPECTED_BUILD_CONTEXT_SHA256,
            surface["java_build_context_sha256"],
        )
        self.assertEqual(288, transition["predecessor"]["file_count"])
        self.assertEqual(297, transition["current"]["file_count"])
        self.assertEqual(
            builder.EXPECTED_RUNTIME_MANIFEST_SHA256,
            transition["predecessor"]["manifest_sha256"],
        )
        self.assertEqual(11, current["migrated_operation_count"])
        self.assertEqual(600, current["pending_operation_count"])
        self.assertEqual(0, current["production_cutover_operation_count"])
        self.assertEqual(builder.ROUTES, current["routes"])
        self.assertTrue(all(
            route_item["http_owner"] == "learning"
            and route_item["migration_status"] == "pending"
            and not route_item["production_cutover"]
            for route_item in current["routes"]
        ))

    def test_03_fixed_legacy_evidence_closes_http_cors_and_rate_observations(self) -> None:
        evidence = self.contract["evidence"]
        self.assertEqual(builder.LEGACY_COMMIT, evidence["legacy_commit"])
        self.assertEqual(59, evidence["phase4b_goldens"]["case_count"])
        self.assertEqual(
            builder.GOLDEN_CASE_PAYLOAD_SHA256,
            evidence["phase4b_goldens"]["case_payload_sha256"],
        )
        self.assertEqual(
            builder.CALLERS_ATTESTATION_SHA256,
            evidence["callers"]["attestation_sha256"],
        )
        self.assertTrue(evidence["callers"]["closed"])

        boundary = evidence["http_boundary"]
        self.assertEqual(builder.BOUNDARY_SHA256, boundary["sha256"])
        self.assertEqual(62, boundary["case_count"])
        self.assertEqual(
            builder.BOUNDARY_CASE_PAYLOAD_SHA256,
            boundary["case_payload_sha256"],
        )
        self.assertEqual(
            self.boundary["case_payload_sha256"], boundary["case_payload_sha256"]
        )
        self.assertEqual(
            self.boundary["document_payload_sha256"],
            boundary["document_payload_sha256"],
        )
        by_id = {case["case_id"]: case for case in self.boundary["cases"]}
        allowed = by_id["cors-preflight-allowed-origin-api-alias"]
        rejected = by_id["cors-preflight-rejected-origin-api-alias"]
        self.assertEqual(401, allowed["response"]["status"])
        self.assertEqual(
            ["https://servicewechat.com"],
            allowed["response"]["headers"]["Access-Control-Allow-Origin"],
        )
        self.assertEqual(
            ["Authorization, Content-Type"],
            allowed["response"]["headers"]["Access-Control-Allow-Headers"],
        )
        self.assertNotIn(
            "Access-Control-Allow-Origin", rejected["response"]["headers"]
        )
        self.assertEqual(0, len(allowed["effects"]["sql"][
            "personal_bank_query_sequence"]))

        rate = evidence["rate_limit"]
        self.assertEqual(builder.RATE_SHA256, rate["sha256"])
        self.assertEqual(
            builder.RATE_RUNTIME_EVIDENCE_PAYLOAD_SHA256,
            rate["runtime_evidence_payload_sha256"],
        )
        self.assertEqual(
            [
                {"count": 10, "unit": "second"},
                {"count": 500, "unit": "hour"},
                {"count": 5000, "unit": "day"},
            ],
            rate["base_windows"],
        )
        self.assertEqual(100, rate["production_default_multiplier"])
        self.assertEqual(
            "500000/day;50000/hour;1000/second",
            rate["production_default_effective_value"],
        )
        self.assertEqual("independent_per_registered_endpoint", rate["alias_buckets"])
        self.assertEqual(500, rate["redis_connection_refusal_status"])

    def test_04_authentication_is_authoritative_alias_specific_and_enumeration_resistant(self) -> None:
        authentication = self.contract["target_http_contract"]["authentication"]
        self.assertIn("valid legacy Bearer for this request only", authentication["api_alias"])
        self.assertNotIn(
            "valid legacy Bearer for this request only", authentication["web_alias"]
        )
        self.assertTrue(authentication["explicit_authorization_selects_bearer"])
        self.assertTrue(authentication["cookie_fallback_after_authorization_forbidden"])
        self.assertEqual("302 Location /login", authentication["web_any_authorization_result"])
        self.assertEqual(
            {
                "status": 401,
                "body": {
                    "status": "unauthorized",
                    "message": "请先登录",
                    "status_code": 401,
                    "request_id": "<request-id>",
                },
            },
            authentication["api_rejected_bearer_or_anonymous"],
        )
        self.assertIn("stale session_version", authentication[
            "enumeration_resistant_rejections"])
        self.assertEqual("P3-AUTH-006", authentication["inherited_difference"])
        self.assertEqual("P4C-LEARNING-007", authentication["stable_difference"])
        self.assertFalse(authentication["email_bind_required_parity_claimed"])
        ownership = self.contract["target_http_contract"]["ownership"]
        self.assertEqual("learning", ownership["http_owner"])
        self.assertTrue(ownership["client_supplied_viewer_id_forbidden"])

    def test_05_query_result_denial_and_failure_policy_remain_exact(self) -> None:
        target = self.contract["target_http_contract"]
        query = target["query_parameters"]
        self.assertEqual("first value wins", query["repeated_parameter_rule"])
        self.assertEqual("", query["q_type"]["default"])
        self.assertEqual("essay", query["q_type"]["unknown"])
        self.assertEqual(
            ["favorites", "mistakes"],
            query["source"]["special_exact_lowercase_values"],
        )
        self.assertEqual("all", query["tag"]["bypass_only_exact_lowercase"])
        result = target["application_result"]
        self.assertEqual(200, result["available_status"])
        self.assertEqual(
            {"status", "code", "data", "message", "request_id"},
            set(result["available_body_fields_exact"]),
        )
        self.assertEqual(403, result["denied_status"])
        self.assertEqual("无权访问此题库", result["denied_body"]["message"])
        self.assertEqual(["data", "payload"], result["denied_forbids_fields"])
        self.assertTrue(result["terminal_denial"])
        self.assertTrue(result["permission_recheck_before_zero_or_tag_return"])
        self.assertTrue(
            result["optional_field_fail_soft_only_for_infrastructure_or_query_failure"]
        )

    def test_06_path_head_options_and_negotiation_are_explicit(self) -> None:
        target = self.contract["target_http_contract"]
        path = target["path"]
        self.assertEqual(
            "io.saksk.ti.web.LegacyDecimalPathInteger", path["normalizer"]
        )
        self.assertEqual(403, path["zero"]["status"])
        self.assertFalse(path["zero"]["application_called"])
        self.assertEqual("1..2147483647", path["application_domain"])
        self.assertEqual(500, path["above_integer_max"]["status"])
        self.assertEqual(0, path["above_integer_max"]["business_sql"])
        self.assertEqual(404, path["converter_miss"]["status"])
        self.assertFalse(path["converter_miss"]["rate_limited"])
        self.assertEqual(400, path["encoded_slash_or_ambiguous_path"]["status"])
        self.assertEqual(400, path["semicolon_matrix"]["status"])

        methods = target["methods"]
        self.assertTrue(
            methods["head"]["same_status_auth_rate_application_and_sql_as_get"]
        )
        self.assertEqual(0, methods["head"]["body_bytes_for_every_status"])
        self.assertEqual(204, methods["bare_options"]["status"])
        self.assertEqual(["GET", "HEAD", "OPTIONS"], methods[
            "bare_options"]["allow"])
        for field in (
            "authentication", "rate_limited", "session_mutation", "application_called",
        ):
            self.assertFalse(methods["bare_options"][field], field)
        self.assertEqual(0, methods["bare_options"]["sql"])
        failure = target["failure_negotiation"]
        self.assertEqual(
            "application/json", failure["api_500"]["content_type"]
        )
        self.assertIn("服务器错误", failure["web_500_default_html"])
        self.assertTrue(failure["global_exception_handler_changes_forbidden"])

    def test_07_cors_rate_last_active_and_request_id_resolve_reviewed_differences(self) -> None:
        target = self.contract["target_http_contract"]
        cors = target["cors"]
        self.assertEqual("API alias only", cors["scope"])
        self.assertFalse(cors["web_alias_acao"])
        self.assertFalse(cors["wildcard_origin"])
        self.assertFalse(cors["credentials"])
        self.assertEqual(["GET", "HEAD", "OPTIONS"], cors["allowed_methods"])
        self.assertEqual(
            ["Content-Type", "Authorization", "X-Request-ID"],
            cors["allowed_headers"],
        )
        self.assertEqual(403, cors["disallowed_simple_api_request"]["status"])
        self.assertEqual(204, cors["valid_preflight"]["status"])
        self.assertEqual(403, cors["invalid_preflight"]["status"])
        for decision in (
            cors["disallowed_simple_api_request"],
            cors["valid_preflight"],
        ):
            self.assertFalse(decision["authentication"])
            self.assertFalse(decision["rate_limited"])
            self.assertFalse(decision["session_mutation"])
            self.assertFalse(decision["application_called"])
            self.assertEqual(0, decision["sql"])

        rate = target["rate_limit"]
        self.assertEqual(10, rate["base_limits"]["per_second"])
        self.assertEqual(100, rate["production_default_multiplier"])
        self.assertEqual(1000, rate["production_effective_defaults"]["per_second"])
        self.assertEqual("independent", rate["alias_buckets"])
        self.assertFalse(rate["raw_identity_or_address_in_redis"])
        self.assertEqual(429, rate["rate_limited_status"])
        self.assertEqual(503, rate["storage_failure"]["status"])
        self.assertTrue(rate["storage_failure"]["fail_closed"])
        self.assertFalse(rate["storage_failure"]["internal_details"])
        activity = target["identity_activity"]
        self.assertEqual(0, activity["users_last_active_dml"])
        self.assertEqual(["GET", "HEAD", "OPTIONS"], activity["methods"])
        request_id = target["request_id"]
        self.assertEqual(
            "io.saksk.ti.web.request.RequestId#from", request_id["source"]
        )
        self.assertTrue(request_id["body_and_response_header_must_match"])

    def test_08_future_allowlist_is_exact_and_forbidden_scope_stays_closed(self) -> None:
        future = self.contract["authorized_future_slice"]
        self.assertFalse(future["implementation_started"])
        self.assertEqual(builder.FUTURE_NEW_MAIN_SOURCES, future[
            "new_main_sources_exact"])
        self.assertEqual(builder.FUTURE_CHANGED_MAIN_SOURCES, future[
            "changed_main_sources_exact"])
        self.assertEqual(builder.FUTURE_CHANGED_RESOURCES, future[
            "changed_resources_exact"])
        self.assertEqual(builder.FUTURE_OPENAPI_OVERLAY, future[
            "new_openapi_overlay_exact"])
        self.assertEqual(2, future["required_route_delta_rows"])
        self.assertEqual(13, future["future_migrated_operation_count"])
        self.assertEqual(598, future["future_pending_operation_count"])
        self.assertEqual(0, future["production_cutover_operation_count"])
        self.assertEqual(builder.FORBIDDEN_FUTURE_MAIN_SOURCES, future[
            "forbidden_main_sources"])
        self.assertEqual(10, len(future["required_test_families"]))
        implementation_delta = self.implementation["implementation"][
            "production_runtime_transition"
        ]["exact_delta"]
        self.assertEqual(
            set(builder.FUTURE_NEW_MAIN_SOURCES),
            set(implementation_delta["added_files"]) - {
                builder.FUTURE_OPENAPI_OVERLAY
            },
        )
        for relative in builder.FUTURE_NEW_MAIN_SOURCES:
            self.assertTrue((ROOT / relative).is_file(), relative)

        checkpoint = self.implementation["acceptance"]
        self.assertFalse(checkpoint["route_migration_eligible"])
        self.assertEqual(11, checkpoint["migrated_operation_count"])
        self.assertEqual(600, checkpoint["pending_operation_count"])
        self.assertEqual(0, checkpoint["production_cutover_operation_count"])

        authorization = self.contract["authorization"]
        for field in (
            "future_controller", "future_route_specific_security",
            "future_route_specific_rate_limit", "future_route_specific_cors",
            "future_route_and_openapi_delta", "future_required_configuration",
        ):
            self.assertTrue(authorization[field], field)
        for field in (
            "current_http_implementation_started",
            "identity_api_or_global_auth_filter_change",
            "learning_or_personalbank_persistence_change",
            "production_schema_or_index", "operator_migration_implementation",
            "real_data_migration_execution", "migration_global_preflight_closed",
            "client_change", "gateway_or_proxy_change", "production_cutover",
        ):
            self.assertFalse(authorization[field], field)

    def test_09_successor_allowlist_is_exact_physical_and_rejects_tampering(self) -> None:
        history = self.contract["historical_successor_acceptance"]
        self.assertEqual(set(SUCCESSOR_SOURCES), set(history[
            "read_source_overrides"]))
        self.assertTrue(history["successor_allowlist_exact"])
        self.assertTrue(history["arbitrary_source_hash_lookup_forbidden"])
        self.assertTrue(history["bridge_self_authorization_forbidden"])
        self.assertNotIn(
            "tools/phase4c_http_entry_successor_acceptance.py",
            history["read_source_overrides"],
        )
        for relative, fixed in SUCCESSOR_SOURCES.items():
            reference = history["read_source_overrides"][relative]
            self.assertEqual(relative, reference["source"])
            self.assertEqual(fixed["accepted_sha256"], reference[
                "accepted_sha256"])
            self.assertEqual(fixed["successor_sha256"], reference[
                "successor_sha256"])
            self.assertEqual(
                sha256(ROOT / relative),
                acceptance._validated_terminal_sha256(
                    ROOT, relative, fixed["successor_sha256"]
                ),
            )

        tampered = copy.deepcopy(self.contract)
        tampered["historical_successor_acceptance"]["read_source_overrides"][
            "tools/unreviewed.py"
        ] = {
            "source": "tools/unreviewed.py",
            "accepted_sha256": "0" * 64,
            "successor_sha256": "0" * 64,
        }
        tampered["document_payload_sha256"] = document_payload_sha256(tampered)
        with self.assertRaisesRegex(AssertionError, "unexpected .* source set"):
            validate_http_entry_successor_contract(tampered, ROOT)

        overclaim = copy.deepcopy(self.contract)
        overclaim["current_state"]["controller_present"] = True
        overclaim["document_payload_sha256"] = document_payload_sha256(overclaim)
        with self.assertRaisesRegex(AssertionError, "overclaims current"):
            validate_http_entry_successor_contract(overclaim, ROOT)

        for label, mutate in (
            (
                "future allowlist",
                lambda document: document["authorized_future_slice"]
                ["new_main_sources_exact"].append(
                    "server/src/main/java/io/saksk/ti/identity/Unreviewed.java"
                ),
            ),
            (
                "CORS wildcard",
                lambda document: document["target_http_contract"]["cors"]
                .__setitem__("wildcard_origin", True),
            ),
            (
                "evidence payload",
                lambda document: document["evidence"]["http_boundary"]
                .__setitem__("case_count", 61),
            ),
            (
                "builder provenance",
                lambda document: document["source_contracts"]["contract_builder"]
                .__setitem__("sha256", "0" * 64),
            ),
        ):
            with self.subTest(label=label):
                changed = copy.deepcopy(self.contract)
                mutate(changed)
                changed["document_payload_sha256"] = document_payload_sha256(changed)
                with self.assertRaisesRegex(
                        AssertionError, "independent trust payload drifted"):
                    validate_http_entry_successor_contract(changed, ROOT)

    def test_10_differences_worm_and_acceptance_do_not_claim_cutover(self) -> None:
        expected_differences = {
            "P3-AUTH-006",
            *(f"P4C-LEARNING-{index:03d}" for index in range(1, 13)),
        }
        self.assertEqual(expected_differences, set(self.contract[
            "stable_differences"]))
        differences = (
            ROOT / "docs/refactor/phase4c/approved-differences.md"
        ).read_text(encoding="utf-8")
        for index in range(7, 13):
            self.assertIn(f"## P4C-LEARNING-{index:03d}", differences)
        worm = self.contract["worm_evidence"]
        self.assertEqual(builder.WORM_SHA256, sha256(ROOT / worm["source"]))
        self.assertFalse(worm["new_worm_required_for_current_gate"])
        self.assertTrue(worm["new_worm_required_after_future_production_change"])
        acceptance = self.contract["acceptance"]
        self.assertTrue(acceptance["entry_evidence_closed"])
        self.assertFalse(acceptance["current_http_implementation_started"])
        self.assertTrue(acceptance["future_exact_http_slice_authorized"])
        self.assertTrue(acceptance["routes_remain_pending"])
        self.assertTrue(acceptance["operator_and_real_migration_remain_blocked"])
        self.assertFalse(acceptance["production_cutover"])


class Phase4cHttpEntryFixedHandoffUnitTest(unittest.TestCase):

    def test_fixed_source_map_matches_immutable_http_entry_contract(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        recorded_paths = {
            name: reference["source"]
            for name, reference in contract["source_contracts"].items()
        }
        self.assertEqual(recorded_paths, acceptance.SOURCE_PATHS)
        self.assertEqual(32, len(acceptance.SOURCE_PATHS))

    def test_unchanged_source_does_not_delegate_to_implementation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ti-http-entry-handoff-") as temporary:
            root = Path(temporary)
            source = root / "fixed-source.txt"
            source.write_bytes(b"unchanged HTTP entry source\n")
            accepted = sha256(source)
            with (
                mock.patch.object(
                    acceptance, "implementation_accepted_sha256"
                ) as implementation_accepted,
                mock.patch.object(
                    acceptance, "implementation_successor_sha256"
                ) as implementation_successor,
            ):
                self.assertEqual(
                    accepted,
                    acceptance._validated_terminal_sha256(
                        root, "fixed-source.txt", accepted
                    ),
                )
            implementation_accepted.assert_not_called()
            implementation_successor.assert_not_called()

    def test_drift_requires_exact_implementation_handoff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ti-http-entry-handoff-") as temporary:
            root = Path(temporary)
            source = root / "fixed-source.txt"
            source.write_bytes(b"Phase4C HTTP implementation successor\n")
            physical = sha256(source)
            accepted = "a" * 64

            with (
                mock.patch.object(
                    acceptance,
                    "implementation_accepted_sha256",
                    return_value=accepted,
                ) as implementation_accepted,
                mock.patch.object(
                    acceptance,
                    "implementation_successor_sha256",
                    return_value=physical,
                ) as implementation_successor,
            ):
                self.assertEqual(
                    physical,
                    acceptance._validated_terminal_sha256(
                        root, "fixed-source.txt", accepted
                    ),
                )
                implementation_accepted.assert_called_once_with("fixed-source.txt")
                implementation_successor.assert_called_once_with(
                    root, "fixed-source.txt"
                )

            with mock.patch.object(
                acceptance,
                "implementation_accepted_sha256",
                return_value="b" * 64,
            ):
                with self.assertRaisesRegex(
                    AssertionError, "did not accept exact HTTP entry source"
                ):
                    acceptance._validated_terminal_sha256(
                        root, "fixed-source.txt", accepted
                    )

            with (
                mock.patch.object(
                    acceptance,
                    "implementation_accepted_sha256",
                    return_value=accepted,
                ),
                mock.patch.object(
                    acceptance,
                    "implementation_successor_sha256",
                    return_value="b" * 64,
                ),
            ):
                with self.assertRaisesRegex(
                    AssertionError, "implementation successor file hash drift"
                ):
                    acceptance._validated_terminal_sha256(
                        root, "fixed-source.txt", accepted
                    )

    def test_source_contracts_never_supply_followed_paths(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        source_contracts = contract["source_contracts"]
        with mock.patch.object(
            acceptance,
            "_validated_terminal_sha256",
            side_effect=lambda _root, _relative, accepted: accepted,
        ) as validate_terminal:
            acceptance._validate_source_contracts(ROOT, source_contracts)
        self.assertEqual(
            [
                mock.call(
                    ROOT,
                    relative,
                    source_contracts[name]["sha256"],
                )
                for name, relative in acceptance.SOURCE_PATHS.items()
            ],
            validate_terminal.call_args_list,
        )

        first_name = next(iter(acceptance.SOURCE_PATHS))
        tampered_path = copy.deepcopy(source_contracts)
        tampered_path[first_name]["source"] = "tools/unreviewed.py"
        with mock.patch.object(
            acceptance, "_validated_terminal_sha256"
        ) as validate_terminal:
            with self.assertRaisesRegex(
                AssertionError, "fixed HTTP entry source path drift"
            ):
                acceptance._validate_source_contracts(ROOT, tampered_path)
        validate_terminal.assert_not_called()

        tampered_shape = copy.deepcopy(source_contracts)
        tampered_shape[first_name]["unreviewed_path"] = "tools/unreviewed.py"
        with self.assertRaisesRegex(
            AssertionError, "source contract shape"
        ):
            acceptance._validate_source_contracts(ROOT, tampered_shape)

        tampered_set = copy.deepcopy(source_contracts)
        tampered_set["unreviewed"] = {
            "source": "tools/unreviewed.py",
            "sha256": "0" * 64,
        }
        with self.assertRaisesRegex(
            AssertionError, "unexpected HTTP entry source contract set"
        ):
            acceptance._validate_source_contracts(ROOT, tampered_set)

    def test_successor_lookup_returns_verified_terminal_hash(self) -> None:
        relative, fixed = next(iter(SUCCESSOR_SOURCES.items()))
        terminal = "c" * 64
        with (
            mock.patch.object(
                acceptance,
                "load_http_entry_successor_contract",
                return_value={},
            ),
            mock.patch.object(
                acceptance,
                "_validated_terminal_sha256",
                return_value=terminal,
            ) as validate_terminal,
        ):
            self.assertEqual(
                terminal,
                acceptance.successor_sha256(ROOT, relative),
            )
        validate_terminal.assert_called_once_with(
            ROOT.resolve(strict=True),
            relative,
            fixed["successor_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
