#!/usr/bin/env python3
"""Contract gates for the Phase 4C transaction-write OpenAPI overlay."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi/phase4c-learning-transaction-write.openapi.json"

try:
    from tools import build_phase4c_learning_transaction_write_openapi as builder
except ModuleNotFoundError:
    import build_phase4c_learning_transaction_write_openapi as builder


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


def resolve_ref(document: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise AssertionError(f"external OpenAPI reference is forbidden: {reference}")
    value: Any = document
    for token in reference[2:].split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    return value


class LearningTransactionWriteOpenApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = OPENAPI.read_bytes()
        cls.document = json.loads(cls.payload)

    def test_01_document_is_openapi_312_and_deterministic(self) -> None:
        self.assertEqual("3.1.2", self.document["openapi"])
        self.assertEqual(
            "https://json-schema.org/draft/2020-12/schema",
            self.document["jsonSchemaDialect"],
        )
        self.assertEqual(
            self.payload,
            builder.render_document(builder.build_document()),
        )
        with tempfile.TemporaryDirectory(prefix="ti-phase4c-write-openapi-") as raw:
            output = Path(raw) / "openapi.json"
            output.write_bytes(builder.render_document(builder.build_document()))
            self.assertEqual(self.payload, output.read_bytes())

    def test_02_exact_nine_counted_operations_and_nine_derived_options(self) -> None:
        self.assertEqual(
            {route["path"] for route in builder.ROUTES},
            set(self.document["paths"]),
        )
        counted = []
        derived = []
        for route in builder.ROUTES:
            path_item = self.document["paths"][route["path"]]
            expected = {route["method"], "options"}
            if route["group"] == "question-edit":
                expected.add("parameters")
            self.assertEqual(expected, set(path_item))
            counted.append(path_item[route["method"]])
            derived.append(path_item["options"])
        self.assertEqual(9, len(counted))
        self.assertEqual(9, len(derived))
        self.assertEqual(
            {route["route_id"] for route in builder.ROUTES},
            {operation["x-ti-route-id"] for operation in counted},
        )
        self.assertTrue(all(
            operation["x-ti-migration"]["status"] == "pending"
            and not operation["x-ti-migration"]["countsAsMigratedOperation"]
            for operation in counted
        ))
        self.assertTrue(all(
            operation["x-ti-migration"]["status"] == "derived"
            and not operation["x-ti-migration"]["countsAsMigratedOperation"]
            for operation in derived
        ))

    def test_03_all_local_references_resolve(self) -> None:
        references = list(iter_refs(self.document))
        self.assertGreater(len(references), 100)
        for reference in references:
            with self.subTest(reference=reference):
                self.assertIsNotNone(resolve_ref(self.document, reference))

    def test_04_real_auth_safety_and_rate_contract_is_route_exact(self) -> None:
        security = [
            {"targetSession": []},
            {"legacyFlaskSession": []},
            {"legacyBearer": []},
        ]
        for route in builder.ROUTES:
            operation = self.document["paths"][route["path"]][route["method"]]
            with self.subTest(route_id=route["route_id"]):
                self.assertEqual(security, operation["security"])
                authentication = operation["x-ti-authentication"]
                self.assertEqual(
                    "XMLHttpRequest",
                    authentication["sessionRequiresExactXRequestedWith"],
                )
                self.assertTrue(authentication["bearerBypassesSessionSafetyHeader"])
                self.assertTrue(authentication["anonymousChargedByIpBefore401"])
                rate = operation["x-ti-rate-limit"]
                self.assertEqual(route["rate"], rate["requestsPerMinute"])
                self.assertEqual(503, rate["failClosedStatus"])
                self.assertIn("HMAC", rate["keyIsolation"])

    def test_05_idempotency_and_error_surface_are_closed(self) -> None:
        expected_responses = {
            "200", "400", "401", "403", "404", "409", "429", "500", "503"
        }
        for route in builder.ROUTES:
            operation = self.document["paths"][route["path"]][route["method"]]
            with self.subTest(route_id=route["route_id"]):
                self.assertEqual(expected_responses, set(operation["responses"]))
                idempotency = operation["x-ti-idempotency"]
                self.assertTrue(idempotency["optional"])
                self.assertEqual(255, idempotency["maximumUtf8Bytes"])
                self.assertTrue(idempotency["blankIsAbsent"])
                self.assertEqual(
                    "atomic",
                    idempotency["businessAndReceiptTransaction"],
                )
        parameter = self.document["components"]["parameters"]["IdempotencyKey"]
        self.assertFalse(parameter["required"])
        self.assertEqual("UTF-8 bytes", parameter["x-ti-length-unit"])
        error = self.document["components"]["schemas"]["CompatibilityError"]
        self.assertEqual(
            {"status", "message", "status_code", "request_id"},
            set(error["required"]),
        )
        self.assertIn("payload", error["properties"])

    def test_06_success_envelopes_and_question_edit_owner_are_not_generic(self) -> None:
        schemas = self.document["components"]["schemas"]
        success_names = {route["success"] for route in builder.ROUTES}
        self.assertEqual(7, len(success_names))
        for name in success_names:
            with self.subTest(schema=name):
                schema = schemas[name]
                self.assertEqual(
                    {"status", "data", "message", "request_id"}
                    | ({"action"} if name == "RecordResultSuccess" else set()),
                    set(schema["required"]),
                )
                self.assertFalse(schema["additionalProperties"])
        question_edit = next(
            route for route in builder.ROUTES
            if route["route_id"] == "624b5ac217d0"
        )
        operation = self.document["paths"][question_edit["path"]]["put"]
        self.assertEqual("catalog", operation["x-ti-migration"]["targetModule"])
        self.assertIn("catalog.api", operation["x-ti-application-api"])
        self.assertEqual(
            [{"$ref": "#/components/parameters/QuestionId"}],
            self.document["paths"][question_edit["path"]]["parameters"],
        )

    def test_07_preflight_is_bodyless_uncharged_and_method_exact(self) -> None:
        for route in builder.ROUTES:
            options = self.document["paths"][route["path"]]["options"]
            contract = options["x-ti-options-contract"]
            with self.subTest(route_id=route["route_id"]):
                self.assertEqual([], options["security"])
                self.assertEqual(
                    ["204", "403"],
                    list(options["responses"]),
                )
                self.assertEqual(
                    route["method"].upper(),
                    contract["expectedRequestedMethod"],
                )
                self.assertFalse(contract["authentication"])
                self.assertFalse(contract["rateLimited"])
                self.assertFalse(contract["applicationCalled"])
                self.assertEqual(0, contract["sql"])
                self.assertEqual(0, contract["bodyBytesForEveryStatus"])

    def test_08_execution_checkpoint_and_route_accounting_are_honest(self) -> None:
        checkpoint = self.document["x-ti-execution-checkpoint"]
        self.assertEqual(builder.EXECUTION_COMMIT, checkpoint["commitOid"])
        self.assertEqual(["16.14", "18.4"], checkpoint["postgresVersions"])
        self.assertEqual("7.4.7", checkpoint["redisVersion"])
        self.assertTrue(checkpoint["realTomcatRandomPort"])
        self.assertEqual(0, checkpoint["identityTableUpdateCount"])
        accounting = self.document["x-ti-route-accounting"]
        self.assertEqual(611, accounting["frozenBaselineOperationCount"])
        self.assertEqual(13, accounting["effectiveMigratedOperationCount"])
        self.assertEqual(598, accounting["effectivePendingOperationCount"])
        self.assertEqual(9, accounting["implementedPendingOperationCount"])
        self.assertFalse(accounting["derivedMethodsCountAsMigratedOperations"])
        authorization = self.document["x-ti-authorization-boundary"]
        self.assertTrue(authorization["openapiOverlayCreated"])
        self.assertFalse(authorization["routePromotionAuthorized"])
        self.assertFalse(authorization["productionCutoverAuthorized"])


if __name__ == "__main__":
    unittest.main()
