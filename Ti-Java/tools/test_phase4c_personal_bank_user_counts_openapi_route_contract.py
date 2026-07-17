#!/usr/bin/env python3
"""Contract gates for the Phase 4C user-counts OpenAPI and route delta."""

from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "openapi/phase4c-personal-bank-user-counts.openapi.json"
ROUTE_DELTA_PATH = ROOT / "docs/refactor/phase4c/route-parity-delta.csv"

API_PATH = "/api/user/banks/api/{bank_id}/user-counts"
WEB_PATH = "/user/banks/api/{bank_id}/user-counts"
LEGACY_API_PATH = "/api/user/banks/api/<int:bank_id>/user-counts"
LEGACY_WEB_PATH = "/user/banks/api/<int:bank_id>/user-counts"
APPLICATION_API = (
    "io.saksk.ti.learning.api."
    "LearningApplicationApi#findPersonalBankUserCounts"
)
APPROVED_DIFFERENCES = [
    "P4C-LEARNING-007",
    "P4C-LEARNING-008",
    "P4C-LEARNING-009",
    "P4C-LEARNING-010",
    "P4C-LEARNING-011",
    "P4C-LEARNING-012",
]

REQUEST_ID_HEADER = {"X-Request-ID"}
REQUEST_VARY_HEADERS = {"X-Request-ID", "Vary"}
SECURITY_HEADERS = {
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
}
CANDIDATE_HEADERS = REQUEST_VARY_HEADERS | SECURITY_HEADERS
RATE_HEADERS = {
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "Retry-After",
}
SUCCESS_HEADERS = CANDIDATE_HEADERS | RATE_HEADERS
COMMON_RATE_LIMITED_HEADERS = CANDIDATE_HEADERS | {
    "Retry-After",
    "X-RateLimit-Reset",
}
API_SIMPLE_ACAO_STATUSES = {"200", "401", "429", "500", "503"}
GET_AND_HEAD_HEADERS = {
    API_PATH: {
        "200": SUCCESS_HEADERS,
        "400": REQUEST_ID_HEADER,
        "401": CANDIDATE_HEADERS | RATE_HEADERS,
        # The umbrella contains only headers common to the charged business denial
        # and the uncharged, empty CORS rejection; variants are checked separately.
        "403": CANDIDATE_HEADERS,
        "404": CANDIDATE_HEADERS,
        # Reset is synthesized for auth-exchange 429s and shared with route 429s.
        "429": COMMON_RATE_LIMITED_HEADERS,
        "500": CANDIDATE_HEADERS | RATE_HEADERS,
        "503": CANDIDATE_HEADERS,
    },
    WEB_PATH: {
        "200": SUCCESS_HEADERS,
        "302": CANDIDATE_HEADERS | RATE_HEADERS | {"Location"},
        "400": REQUEST_ID_HEADER,
        "403": CANDIDATE_HEADERS | RATE_HEADERS,
        "404": CANDIDATE_HEADERS,
        "429": COMMON_RATE_LIMITED_HEADERS,
        "500": CANDIDATE_HEADERS | RATE_HEADERS,
        "503": CANDIDATE_HEADERS,
    },
}
OPTIONS_HEADERS = {
    API_PATH: {
        "204": SECURITY_HEADERS | {
            "Allow",
            "X-Request-ID",
            "Vary",
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
        },
        "400": REQUEST_ID_HEADER,
        "403": CANDIDATE_HEADERS,
    },
    WEB_PATH: {
        "204": CANDIDATE_HEADERS | {"Allow"},
        "400": REQUEST_ID_HEADER,
    },
}

IMMUTABLE_OPENAPI = {
    "contracts/openapi.json": (
        "41e0ad0e1eca3ba8731242dea7a638cd348069aad1331382f5f1bf6d4a08d64e"
    ),
    "openapi/phase3-authentication.openapi.json": (
        "7b014165a027ae3dbdbf8597ca910db8ab153b0437156f6d0fdd07985f348fab"
    ),
    "openapi/phase4a-public-bank.openapi.json": (
        "1f163574d9fb5b25d58df4a4a75ffca6b74b874dfbf66551cf46408d67110a34"
    ),
    "openapi/phase4a-subject-directory.openapi.json": (
        "8344f0173f523939abae203430cf92455d6240404e3d8ffe7a002507cadd2169"
    ),
}

IMMUTABLE_ROUTE_INPUTS = {
    "docs/refactor/02-route-parity-matrix.csv": (
        "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
    ),
    "docs/refactor/phase3/route-parity-delta.csv": (
        "8576d9e3311538af7cc5f47bbe1cefe78c3b65f007fae54aa6c06500c03ea323"
    ),
    "docs/refactor/phase4a/route-parity-delta.csv": (
        "0d82f1f1d58d4a2ff124f5e3ec7bb183b35811dcbabb26271d1ba246579afff8"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def security_names(operation: dict[str, Any]) -> list[str]:
    return [next(iter(item)) for item in operation["security"]]


def resolve_local_ref(document: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise AssertionError(f"external reference is not allowed: {reference}")
    value: Any = document
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    return value


def optional_headers(response: dict[str, Any]) -> set[str]:
    return set(response.get("x-ti-optional-headers", []))


def iter_refs(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                yield child
            else:
                yield from iter_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_refs(child)


class Phase4cPersonalBankUserCountsOpenApiRouteContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.openapi = load_json(OPENAPI_PATH)
        cls.route_delta = load_csv(ROUTE_DELTA_PATH)

    def test_01_phase1_phase3_and_phase4a_sources_remain_byte_immutable(self):
        for relative, expected in {
            **IMMUTABLE_OPENAPI,
            **IMMUTABLE_ROUTE_INPUTS,
        }.items():
            with self.subTest(relative=relative):
                self.assertEqual(expected, sha256(ROOT / relative))

    def test_02_overlay_has_exact_paths_methods_and_resolvable_local_refs(self):
        document = self.openapi
        self.assertEqual("3.1.2", document["openapi"])
        self.assertEqual({API_PATH, WEB_PATH}, set(document["paths"]))
        for path, path_item in document["paths"].items():
            with self.subTest(path=path):
                self.assertEqual(
                    {"parameters", "get", "head", "options"},
                    set(path_item),
                )
                self.assertEqual(
                    [{"$ref": "#/components/parameters/BankId"}],
                    path_item["parameters"],
                )
        for reference in iter_refs(document):
            with self.subTest(reference=reference):
                self.assertIsNotNone(resolve_local_ref(document, reference))

    def test_03_two_legacy_get_implementations_remain_pending_parity(self):
        expected = {
            API_PATH: ("6858f6fa506f", "legacy_6858f6fa506f_get", "api"),
            WEB_PATH: ("006913d0d956", "legacy_006913d0d956_get", "web"),
        }
        counted = []
        derived = []
        for path, (route_id, operation_id, alias) in expected.items():
            get = self.openapi["paths"][path]["get"]
            self.assertEqual(operation_id, get["operationId"])
            self.assertEqual(route_id, get["x-ti-route-id"])
            self.assertEqual(alias, get["x-ti-alias"])
            self.assertEqual(APPLICATION_API, get["x-ti-application-api"])
            self.assertEqual(APPROVED_DIFFERENCES, get["x-ti-approved-differences"])
            self.assertEqual(
                {
                    "status": "pending",
                    "targetModule": "learning",
                    "countsAsMigratedOperation": False,
                    "productionCutover": False,
                },
                get["x-ti-migration"],
            )
            counted.append(get)
            for method in ("head", "options"):
                operation = self.openapi["paths"][path][method]
                self.assertEqual(route_id, operation["x-ti-route-id"])
                self.assertEqual(alias, operation["x-ti-alias"])
                self.assertEqual(
                    {
                        "status": "derived",
                        "targetModule": "learning",
                        "countsAsMigratedOperation": False,
                        "productionCutover": False,
                    },
                    operation["x-ti-migration"],
                )
                derived.append(operation)
        self.assertEqual(2, len(counted))
        self.assertEqual(4, len(derived))
        accounting = self.openapi["x-ti-route-accounting"]
        self.assertEqual(611, accounting["frozenBaselineOperationCount"])
        self.assertEqual(11, accounting["predecessorMigratedOperationCount"])
        self.assertEqual(0, accounting["phase4cLegacyGetDeltaCount"])
        self.assertEqual(2, accounting["phase4cImplementedPendingGetCount"])
        self.assertEqual(11, accounting["effectiveMigratedOperationCount"])
        self.assertEqual(600, accounting["effectivePendingOperationCount"])
        self.assertEqual(0, accounting["productionCutoverOperationCount"])
        self.assertEqual(["GET"], accounting["countedMethods"])
        self.assertEqual(["HEAD", "OPTIONS"], accounting["documentedDerivedMethods"])
        self.assertFalse(accounting["derivedMethodsCountAsMigratedOperations"])

    def test_04_authentication_is_alias_specific_and_fail_closed(self):
        api = self.openapi["paths"][API_PATH]["get"]
        web = self.openapi["paths"][WEB_PATH]["get"]
        self.assertEqual(
            ["targetSession", "legacyFlaskSession", "legacyBearer"],
            security_names(api),
        )
        self.assertEqual(
            ["targetSession", "legacyFlaskSession"],
            security_names(web),
        )
        self.assertTrue(api["x-ti-authentication"]["explicitAuthorizationSelectsBearer"])
        self.assertFalse(api["x-ti-authentication"]["cookieFallbackAfterAuthorization"])
        self.assertEqual(401, api["x-ti-authentication"]["rejectedOrAnonymousStatus"])
        self.assertFalse(web["x-ti-authentication"]["bearerAccepted"])
        self.assertEqual(302, web["x-ti-authentication"]["anyAuthorizationStatus"])
        self.assertEqual("/login", web["x-ti-authentication"]["anyAuthorizationLocation"])
        unauthorized = self.openapi["components"]["schemas"]["ApiUnauthorized"]
        self.assertEqual(
            {"status", "message", "status_code", "request_id"},
            set(unauthorized["required"]),
        )
        self.assertEqual(
            "请先登录", unauthorized["properties"]["message"]["const"]
        )
        self.assertEqual(401, unauthorized["properties"]["status_code"]["const"])

    def test_05_query_parameters_freeze_first_value_and_normalization(self):
        parameters = self.openapi["components"]["parameters"]
        for name in ("QType", "Source", "Tag"):
            with self.subTest(parameter=name):
                self.assertEqual(
                    "first value wins",
                    parameters[name]["x-ti-repeated-value-rule"],
                )
        self.assertEqual("", parameters["QType"]["schema"]["default"])
        self.assertTrue(parameters["QType"]["x-ti-coercion"]["trim"])
        self.assertTrue(parameters["QType"]["x-ti-coercion"]["allCaseInsensitive"])
        self.assertEqual("essay", parameters["QType"]["x-ti-coercion"]["unknown"])
        self.assertEqual("all", parameters["Source"]["schema"]["default"])
        self.assertEqual(
            ["favorites", "mistakes"],
            parameters["Source"]["x-ti-coercion"]["specialExactLowercase"],
        )
        self.assertEqual("all", parameters["Source"]["x-ti-coercion"]["other"])
        self.assertEqual("", parameters["Tag"]["schema"]["default"])
        self.assertEqual(
            "all",
            parameters["Tag"]["x-ti-coercion"]["bypassOnlyExactLowercase"],
        )

    def test_06_unicode_nd_zero_overflow_and_firewall_contract_are_explicit(self):
        bank_id = self.openapi["components"]["parameters"]["BankId"]
        self.assertEqual("string", bank_id["schema"]["type"])
        self.assertEqual(r"^\p{Nd}+$", bank_id["schema"]["pattern"])
        coercion = bank_id["x-ti-coercion"]
        self.assertTrue(coercion["strictPercentDecodeOnce"])
        self.assertEqual("Nd", coercion["acceptedCodePointCategory"])
        self.assertEqual(
            {
                "status": 403,
                "authenticated": True,
                "rateLimited": True,
                "applicationCalled": False,
            },
            coercion["zero"],
        )
        self.assertEqual("1..2147483647", coercion["applicationRange"])
        self.assertEqual(500, coercion["aboveIntegerMaximum"]["status"])
        self.assertTrue(coercion["aboveIntegerMaximum"]["authenticated"])
        self.assertTrue(coercion["aboveIntegerMaximum"]["rateLimited"])
        self.assertFalse(coercion["aboveIntegerMaximum"]["applicationCalled"])
        self.assertEqual(0, coercion["aboveIntegerMaximum"]["businessSql"])
        self.assertEqual(404, coercion["converterMiss"]["status"])
        self.assertFalse(coercion["converterMiss"]["rateLimited"])
        self.assertEqual(400, coercion["encodedSlashOrSemicolon"]["status"])
        self.assertFalse(coercion["encodedSlashOrSemicolon"]["rateLimited"])

    def test_07_success_denial_and_status_matrix_are_exact(self):
        success = self.openapi["components"]["schemas"]["UserCountsSuccess"]
        data = self.openapi["components"]["schemas"]["UserCountsData"]
        denied = self.openapi["components"]["schemas"]["Forbidden"]
        self.assertEqual(
            {"status", "code", "data", "message", "request_id"},
            set(success["required"]),
        )
        self.assertEqual(
            {"total", "favorites", "mistakes", "types", "shuffle_options_available"},
            set(data["required"]),
        )
        self.assertEqual(
            {"status", "code", "message", "status_code", "request_id"},
            set(denied["required"]),
        )
        self.assertEqual("无权访问此题库", denied["properties"]["message"]["const"])
        self.assertEqual(["data", "payload"], denied["x-ti-forbidden-fields"])
        api_statuses = set(self.openapi["paths"][API_PATH]["get"]["responses"])
        web_statuses = set(self.openapi["paths"][WEB_PATH]["get"]["responses"])
        self.assertEqual(
            {"200", "400", "401", "403", "404", "429", "500", "503"},
            api_statuses,
        )
        self.assertEqual(
            {"200", "302", "400", "403", "404", "429", "500", "503"},
            web_statuses,
        )
        self.assertEqual(
            {"200", "302", "400", "401", "403", "404", "429", "500", "503"},
            api_statuses | web_statuses,
        )

    def test_08_head_is_get_equivalent_and_every_response_has_zero_body(self):
        for path in (API_PATH, WEB_PATH):
            get = self.openapi["paths"][path]["get"]
            head = self.openapi["paths"][path]["head"]
            with self.subTest(path=path):
                self.assertEqual(set(get["responses"]), set(head["responses"]))
                self.assertEqual(get["security"], head["security"])
                self.assertEqual(get["x-ti-vary-tokens"], head["x-ti-vary-tokens"])
                contract = head["x-ti-head-contract"]
                self.assertTrue(
                    contract[
                        "sameRawPathAuthenticationActorRateApplicationSqlStatusAndSemanticHeadersAsGet"
                    ]
                )
                self.assertEqual(0, contract["bodyBytesForEveryStatus"])
                for status, expected_headers in GET_AND_HEAD_HEADERS[path].items():
                    get_response = resolve_local_ref(
                        self.openapi,
                        get["responses"][status]["$ref"],
                    )
                    head_response = resolve_local_ref(
                        self.openapi,
                        head["responses"][status]["$ref"],
                    )
                    with self.subTest(path=path, status=status):
                        self.assertEqual(
                            expected_headers,
                            set(get_response.get("headers", {})),
                        )
                        self.assertEqual(
                            expected_headers,
                            set(head_response.get("headers", {})),
                        )
                        self.assertEqual(
                            get_response.get("headers", {}),
                            head_response.get("headers", {}),
                        )
                        expected_optional = (
                            {"Access-Control-Allow-Origin"}
                            if path == API_PATH
                            and status in API_SIMPLE_ACAO_STATUSES
                            else set()
                        )
                        self.assertEqual(
                            expected_optional,
                            optional_headers(get_response),
                        )
                        self.assertEqual(
                            expected_optional,
                            optional_headers(head_response),
                        )
                        self.assertEqual(0, head_response["x-ti-body-bytes"])
                        self.assertNotIn("content", head_response)

    def test_09_options_and_api_only_cors_are_pre_authentication_and_zero_side_effect(self):
        cors = self.openapi["x-ti-cors-contract"]
        self.assertEqual("API alias only", cors["scope"])
        self.assertEqual(
            [
                "https://servicewechat.com",
                "explicit configured origins",
                "development-profile localhost/127.0.0.1 ports 5000 and 3000",
            ],
            cors["allowedOrigins"],
        )
        self.assertFalse(cors["wildcardOrigin"])
        self.assertFalse(cors["credentials"])
        self.assertEqual(["GET", "HEAD", "OPTIONS"], cors["allowedMethods"])
        self.assertEqual(
            ["Content-Type", "Authorization", "X-Request-ID"],
            cors["allowedHeaders"],
        )
        self.assertFalse(cors["webAliasCors"])
        for path in (API_PATH, WEB_PATH):
            options = self.openapi["paths"][path]["options"]
            with self.subTest(path=path):
                self.assertEqual([], options["security"])
                contract = options["x-ti-options-contract"]
                self.assertEqual(204, contract["bareOptionsStatus"])
                self.assertEqual(0, contract["bodyBytesForEveryStatus"])
                self.assertEqual(["GET", "HEAD", "OPTIONS"], contract["allow"])
                for key in (
                    "authentication",
                    "rateLimited",
                    "sessionMutation",
                    "applicationCalled",
                ):
                    self.assertFalse(contract[key])
                self.assertEqual(0, contract["sql"])
                self.assertEqual(
                    set(OPTIONS_HEADERS[path]),
                    set(options["responses"]),
                )
                for status, expected_headers in OPTIONS_HEADERS[path].items():
                    response_ref = options["responses"][status]
                    response = resolve_local_ref(self.openapi, response_ref["$ref"])
                    with self.subTest(path=path, status=status):
                        self.assertEqual(
                            expected_headers,
                            set(response.get("headers", {})),
                        )
                        self.assertEqual(0, response["x-ti-body-bytes"])
                        self.assertNotIn("content", response)
        self.assertEqual(
            {"204", "400", "403"},
            set(self.openapi["paths"][API_PATH]["options"]["responses"]),
        )
        self.assertEqual(
            {"204", "400"},
            set(self.openapi["paths"][WEB_PATH]["options"]["responses"]),
        )
        firewall_components = {
            "PathFirewallRejected",
            "HeadFirewallRejected",
            "OptionsFirewallRejected",
        }
        for name, response in self.openapi["components"]["responses"].items():
            response_headers = set(response.get("headers", {}))
            with self.subTest(security_header_writer_candidate=name):
                if name in firewall_components:
                    self.assertTrue(SECURITY_HEADERS.isdisjoint(response_headers))
                else:
                    self.assertTrue(SECURITY_HEADERS <= response_headers)

    def test_10_rate_limit_is_actor_bound_alias_local_and_fail_closed(self):
        rate = self.openapi["x-ti-rate-limit-contract"]
        self.assertEqual(
            {"perSecond": 10, "perHour": 500, "perDay": 5000},
            rate["baseLimits"],
        )
        self.assertEqual(1, rate["developmentDefaultMultiplier"])
        self.assertEqual(100, rate["productionDefaultMultiplier"])
        self.assertEqual(
            {"perSecond": 1000, "perHour": 50000, "perDay": 500000},
            rate["productionEffectiveDefaults"],
        )
        self.assertTrue(rate["aliasBucketsIndependent"])
        self.assertTrue(rate["publicBankBucketsIndependent"])
        self.assertIn("TargetAuthenticatedPrincipal", rate["actor"])
        self.assertIn("HMAC-SHA-256", rate["keying"])
        self.assertIn("independent secret", rate["keying"])
        self.assertFalse(rate["rawIdentityAddressCookieOrBearerInRedis"])
        self.assertEqual(429, rate["rateLimitedStatus"])
        self.assertEqual(
            [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Retry-After",
            ],
            rate["userCountRouteDecisionHeaders"],
        )
        exchange = rate["authenticationExchange429"]
        self.assertTrue(exchange["beforeUserCountRouteLimiter"])
        self.assertEqual(
            ["Retry-After", "X-RateLimit-Reset"],
            exchange["guaranteedRateHeaders"],
        )
        self.assertEqual(
            ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
            exchange["optionalAttemptWindowHeaders"],
        )
        self.assertEqual([], exchange["notPromised"])
        self.assertIn("503", rate["storageFailure"])
        responses = self.openapi["components"]["responses"]

        for component in (
            "ApiAuthenticationRequired",
            "WebLoginRedirect",
            "ApiBusinessForbidden",
            "WebForbidden",
            "ApiInternalFailure",
            "WebInternalFailure",
        ):
            with self.subTest(charged_component=component):
                self.assertTrue(
                    RATE_HEADERS <= set(responses[component]["headers"]),
                )

        api_forbidden = responses["ApiForbidden"]
        self.assertEqual(CANDIDATE_HEADERS, set(api_forbidden["headers"]))
        self.assertEqual(
            "#/components/responses/ApiBusinessForbidden",
            api_forbidden["x-ti-variants"]["businessOrZero"]["$ref"],
        )
        self.assertEqual(
            "#/components/responses/ApiCorsForbidden",
            api_forbidden["x-ti-variants"]["disallowedOrigin"]["$ref"],
        )
        api_business_forbidden = responses["ApiBusinessForbidden"]
        self.assertEqual(
            CANDIDATE_HEADERS | RATE_HEADERS,
            set(api_business_forbidden["headers"]),
        )
        self.assertEqual(
            {"Access-Control-Allow-Origin"},
            optional_headers(api_business_forbidden),
        )
        api_cors_forbidden = responses["ApiCorsForbidden"]
        self.assertEqual(CANDIDATE_HEADERS, set(api_cors_forbidden["headers"]))
        self.assertEqual(set(), optional_headers(api_cors_forbidden))
        self.assertEqual([], api_cors_forbidden["x-ti-rate-limit-headers"])
        self.assertEqual(0, api_cors_forbidden["x-ti-body-bytes"])
        self.assertNotIn("content", api_cors_forbidden)
        for component in ("HeadApiBusinessForbidden", "HeadApiCorsForbidden"):
            with self.subTest(head_forbidden_variant=component):
                head_variant = responses[component]
                get_variant = resolve_local_ref(
                    self.openapi,
                    head_variant["x-ti-get-response"],
                )
                self.assertEqual(
                    set(get_variant["headers"]),
                    set(head_variant["headers"]),
                )
                self.assertEqual(
                    optional_headers(get_variant),
                    optional_headers(head_variant),
                )
                self.assertEqual(0, head_variant["x-ti-body-bytes"])
                self.assertNotIn("content", head_variant)

        for alias in ("Api", "Web"):
            umbrella = responses[f"{alias}RateLimited"]
            self.assertEqual(
                COMMON_RATE_LIMITED_HEADERS,
                set(umbrella["headers"]),
            )
            self.assertEqual(
                {"Access-Control-Allow-Origin"} if alias == "Api" else set(),
                optional_headers(umbrella),
            )
            self.assertEqual(
                f"#/components/responses/{alias}UserCountRouteRateLimited",
                umbrella["x-ti-variants"]["userCountRouteLimiter"]["$ref"],
            )
            self.assertEqual(
                f"#/components/responses/{alias}AuthenticationExchangeRateLimited",
                umbrella["x-ti-variants"]["authenticationExchange"]["$ref"],
            )

            route_limited = responses[f"{alias}UserCountRouteRateLimited"]
            self.assertEqual(
                CANDIDATE_HEADERS | RATE_HEADERS,
                set(route_limited["headers"]),
            )
            self.assertEqual(
                {"Access-Control-Allow-Origin"} if alias == "Api" else set(),
                optional_headers(route_limited),
            )

            exchange_limited = responses[
                f"{alias}AuthenticationExchangeRateLimited"
            ]
            self.assertEqual(
                COMMON_RATE_LIMITED_HEADERS,
                set(exchange_limited["headers"]),
            )
            self.assertEqual(
                {
                    "X-RateLimit-Limit",
                    "X-RateLimit-Remaining",
                    *({"Access-Control-Allow-Origin"} if alias == "Api" else set()),
                },
                optional_headers(exchange_limited),
            )
            self.assertEqual([], exchange_limited["x-ti-not-promised-headers"])

            for variant in (
                f"Head{alias}UserCountRouteRateLimited",
                f"Head{alias}AuthenticationExchangeRateLimited",
            ):
                with self.subTest(head_variant=variant):
                    head_variant = responses[variant]
                    get_variant = resolve_local_ref(
                        self.openapi,
                        head_variant["x-ti-get-response"],
                    )
                    self.assertEqual(
                        set(get_variant["headers"]),
                        set(head_variant["headers"]),
                    )
                    self.assertEqual(
                        optional_headers(get_variant),
                        optional_headers(head_variant),
                    )
                    self.assertEqual(0, head_variant["x-ti-body-bytes"])
                    self.assertNotIn("content", head_variant)

        for alias in ("Api", "Web"):
            unavailable = responses[f"{alias}ServiceUnavailable"]
            self.assertFalse(set(unavailable["headers"]) & RATE_HEADERS)
            self.assertTrue(SECURITY_HEADERS <= set(unavailable["headers"]))

        for component in (
            "ApiConverterNotFound",
            "HeadConverterNotFound",
            "ApiCorsForbidden",
            "HeadApiCorsForbidden",
        ):
            with self.subTest(no_cors_on_early_or_rejected_response=component):
                self.assertEqual(set(), optional_headers(responses[component]))

    def test_11_route_delta_keeps_11_migrated_600_pending_and_zero_cutover(self):
        self.assertEqual(2, len(self.route_delta))
        expected_rows = {
            ("6858f6fa506f", LEGACY_API_PATH, "GET"),
            ("006913d0d956", LEGACY_WEB_PATH, "GET"),
        }
        self.assertEqual(
            expected_rows,
            {(row["route_id"], row["path"], row["method"]) for row in self.route_delta},
        )
        for row in self.route_delta:
            with self.subTest(route_id=row["route_id"]):
                self.assertEqual("personalbank", row["base_target_module"])
                self.assertEqual("learning", row["phase4c_target_module"])
                self.assertEqual("pending", row["base_migration_status"])
                self.assertEqual("pending", row["phase4c_migration_status"])
                self.assertEqual(APPLICATION_API, row["application_api"])
                self.assertEqual(
                    APPROVED_DIFFERENCES,
                    row["approved_difference_ids"].split(";"),
                )
                self.assertEqual("false", row["production_cutover"])

        operations: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in load_csv(ROOT / "docs/refactor/02-route-parity-matrix.csv"):
            for method in row["methods"].split(","):
                key = (row["route_id"], row["path"], method)
                self.assertNotIn(key, operations)
                operations[key] = {
                    "status": row["migration_status"],
                    "target_module": row["target_module"],
                    "production_cutover": False,
                }
        self.assertEqual(611, len(operations))

        delta_specs = [
            (
                "docs/refactor/phase3/route-parity-delta.csv",
                "phase3_migration_status",
                "phase3_target_module",
            ),
            (
                "docs/refactor/phase4a/route-parity-delta.csv",
                "phase4a_migration_status",
                "phase4a_target_module",
            ),
            (
                "docs/refactor/phase4c/route-parity-delta.csv",
                "phase4c_migration_status",
                "phase4c_target_module",
            ),
        ]
        applied: set[tuple[str, str, str]] = set()
        for relative, status_field, module_field in delta_specs:
            for row in load_csv(ROOT / relative):
                key = (row["route_id"], row["path"], row["method"])
                self.assertIn(key, operations, f"unknown delta key: {key}")
                self.assertNotIn(key, applied, f"duplicate delta key: {key}")
                applied.add(key)
                operations[key] = {
                    "status": row[status_field],
                    "target_module": row[module_field],
                    "production_cutover": row["production_cutover"] == "true",
                }
        self.assertEqual(13, len(applied))
        self.assertEqual(
            11,
            sum(item["status"] == "migrated" for item in operations.values()),
        )
        self.assertEqual(
            600,
            sum(item["status"] == "pending" for item in operations.values()),
        )
        self.assertEqual(
            0,
            sum(item["production_cutover"] for item in operations.values()),
        )
        for key in expected_rows:
            self.assertEqual("learning", operations[key]["target_module"])

    def test_12_evidence_hashes_and_http_difference_set_are_current(self):
        self.assertEqual(APPROVED_DIFFERENCES, self.openapi["x-ti-approved-differences"])
        evidence = self.openapi["x-ti-evidence"]
        for item in evidence.values():
            if not isinstance(item, dict) or "path" not in item:
                continue
            with self.subTest(path=item["path"]):
                self.assertEqual(item["sha256"], sha256(ROOT / item["path"]))
        self.assertEqual(["16.14", "18.4"], evidence["postgresCompatibility"])
        side_effects = self.openapi["x-ti-side-effect-contract"]
        self.assertEqual(0, side_effects["usersLastActiveDml"])
        self.assertEqual(["GET", "HEAD", "OPTIONS"], side_effects["methods"])
        self.assertEqual(0, side_effects["businessWrites"])


if __name__ == "__main__":
    unittest.main()
