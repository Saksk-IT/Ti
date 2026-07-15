#!/usr/bin/env python3
"""Contract tests for deterministic phase-1 OpenAPI generation."""

from __future__ import annotations

import copy
import re
import unittest

from generate_phase1_openapi import (
    DEFAULT_GOLDEN_DIR,
    DEFAULT_MATRIX,
    DEFAULT_OUTPUT,
    DEFAULT_OVERRIDES,
    ExpandedRoute,
    dump_json_bytes,
    expand_routes,
    generate_document,
    load_json,
    load_matrix,
    reject_normalized_operation_collisions,
    resolve_template_paths,
    select_effective_routes,
)
from validate_phase1_openapi import iter_operations, validate_determinism, validate_document


class Phase1OpenApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_matrix(DEFAULT_MATRIX)
        cls.expanded = expand_routes(cls.rows)
        cls.overrides = load_json(DEFAULT_OVERRIDES)
        cls.document = load_json(DEFAULT_OUTPUT)
        cls.operations = list(iter_operations(cls.document))

    def test_checked_in_contract_is_deterministic_and_valid(self) -> None:
        self.assertEqual([], validate_document(self.document))
        self.assertEqual([], validate_determinism(DEFAULT_OUTPUT))
        first = dump_json_bytes(generate_document())
        second = dump_json_bytes(generate_document())
        self.assertEqual(first, second)
        self.assertEqual(DEFAULT_OUTPUT.read_bytes(), first)

    def test_all_legacy_methods_have_a_target_or_explicit_shadow(self) -> None:
        inventory = self.document["x-ti-inventory"]
        self.assertEqual(592, len(self.rows))
        self.assertEqual(611, len(self.expanded))
        self.assertEqual(610, len(self.operations))
        self.assertEqual(
            {
                "renderedTargetOperations": 610,
                "shadowedLegacyOperations": 1,
                "expandedLegacyOperations": 611,
            },
            inventory["legacyCoverage"],
        )
        collision = self.document["x-ti-shadowed-operations"]
        self.assertEqual(1, len(collision))
        self.assertEqual("GET", collision[0]["method"])
        self.assertEqual("/profile", collision[0]["path"])
        self.assertEqual("1aae474aceca", collision[0]["effective"]["routeId"])
        self.assertEqual(["ddd38e139d39"], [item["routeId"] for item in collision[0]["shadowed"]])
        profile = self.document["paths"]["/profile"]["get"]
        self.assertEqual("legacy_1aae474aceca_get", profile["operationId"])
        self.assertEqual("get-profile-registration-shadow", profile["x-ti-collision-resolution"])

    def test_every_operation_has_machine_readable_target_and_maturity(self) -> None:
        maturities: dict[str, int] = {}
        operation_ids: set[str] = set()
        for path, method, operation in self.operations:
            operation_id = operation["operationId"]
            self.assertNotIn(operation_id, operation_ids)
            operation_ids.add(operation_id)
            migration = operation["x-ti-migration"]
            self.assertEqual(operation_id, migration["targetOperationId"])
            self.assertEqual(path, migration["targetPath"])
            self.assertEqual(method, migration["targetMethod"])
            self.assertTrue(migration["targetModule"])
            self.assertEqual("legacy", operation["x-ti-envelope"])
            maturity = operation["x-ti-contract-maturity"]
            self.assertIn(maturity, {"observed", "tested", "manual", "inferred", "unknown"})
            maturities[maturity] = maturities.get(maturity, 0) + 1
            self.assertTrue(operation["x-ti-contract"]["sourceEvidence"])
            self.assertTrue(operation["x-ti-contract"]["unknownAspects"])
        self.assertEqual({"observed": 7, "inferred": 603}, maturities)

    def test_path_parameters_and_security_references_are_closed(self) -> None:
        schemes = set(self.document["components"]["securitySchemes"])
        self.assertEqual(
            {
                "legacySessionCookie",
                "legacyBearerJwt",
                "recordToken",
                "legacyXRequestedWith",
                "csrfHeader",
                "accessToken",
            },
            schemes,
        )
        referenced: set[str] = set()
        for path, _method, operation in self.operations:
            template_names = set(re.findall(r"\{([^{}]+)\}", path))
            path_parameters = {
                item["name"]: item
                for item in operation["parameters"]
                if item.get("in") == "path"
            }
            self.assertEqual(template_names, set(path_parameters))
            self.assertTrue(all(item["required"] is True for item in path_parameters.values()))
            for requirement in operation["security"]:
                referenced.update(requirement)
        self.assertLessEqual(referenced, schemes)
        self.assertFalse({"csrfHeader", "accessToken"} & referenced)
        record_result = self.document["paths"]["/api/record_result"]["post"]
        self.assertIn(
            {"legacySessionCookie": [], "legacyXRequestedWith": []},
            record_result["security"],
        )
        static_path = self.document["paths"]["/static/{filename}"]["get"]
        parameter = static_path["parameters"][0]
        self.assertEqual("path", parameter["x-ti-flask-converter"])
        self.assertIn("embedded slashes", parameter["x-ti-openapi-limitation"])

    def test_golden_samples_and_source_overrides_are_pinned(self) -> None:
        pins = self.overrides["golden_contract_pins"]
        self.assertEqual(7, len(pins))
        for pin in pins:
            sample = load_json(DEFAULT_GOLDEN_DIR / pin["sample"])
            rendered = next(
                operation
                for _path, method, operation in self.operations
                if method == pin["method"] and operation["x-ti-legacy"]["routeId"] == pin["route_id"]
            )
            self.assertEqual("observed", rendered["x-ti-contract-maturity"])
            media_type = sample["response"]["headers"]["Content-Type"].split(";", 1)[0]
            self.assertEqual(
                sample["response"]["body"],
                rendered["responses"][str(pin["status"])]["content"][media_type]["example"],
            )
        expected_override_ids = sorted(entry["id"] for entry in self.overrides["operation_overrides"])
        self.assertEqual(
            expected_override_ids,
            self.document["x-ti-generation"]["usedOperationOverrideIds"],
        )
        login = self.document["paths"]["/api/login"]["post"]
        self.assertEqual(
            "#/components/schemas/LoginRequest",
            login["requestBody"]["content"]["application/json"]["schema"]["$ref"],
        )
        self.assertEqual(
            "login-request-source-contract",
            login["x-ti-contract"]["manualOverrideId"],
        )

    def test_target_shared_components_match_accepted_conventions(self) -> None:
        schemas = self.document["components"]["schemas"]
        self.assertEqual(
            ["success", "data", "meta"],
            schemas["ApiEnvelope"]["required"],
        )
        self.assertEqual(True, schemas["ApiEnvelope"]["properties"]["success"]["const"])
        self.assertEqual(
            ["success", "error", "meta"],
            schemas["ErrorEnvelope"]["required"],
        )
        self.assertEqual(False, schemas["ErrorEnvelope"]["properties"]["success"]["const"])
        self.assertEqual(
            [
                "page",
                "page_size",
                "total_items",
                "total_pages",
                "has_next",
                "has_previous",
            ],
            schemas["PaginationMeta"]["required"],
        )
        self.assertEqual(
            ["request_id", "pagination"],
            schemas["PageEnvelope"]["properties"]["meta"]["required"],
        )
        self.assertEqual("java.math.BigDecimal", schemas["DecimalString"]["x-ti-java-type"])
        self.assertEqual(["string", "null"], schemas["NullableString"]["type"])

    def test_external_lint_warnings_are_deterministically_explained(self) -> None:
        findings = self.document["x-ti-known-lint-findings"]
        self.assertEqual(0, findings["externalValidator"]["expectedErrors"])
        self.assertEqual(48, findings["externalValidator"]["expectedWarnings"])
        categories = {item["ruleId"]: item for item in findings["categories"]}
        self.assertEqual(30, categories["no-ambiguous-paths"]["count"])
        self.assertEqual(30, len(categories["no-ambiguous-paths"]["evidence"]))
        self.assertEqual(4, categories["no-path-trailing-slash"]["count"])
        self.assertEqual(
            ["/admin/", "/admin/coding/", "/coding/", "/user/banks/"],
            categories["no-path-trailing-slash"]["evidence"],
        )
        self.assertEqual(14, categories["no-unused-components"]["count"])

    def test_validator_rejects_a_silently_untyped_response(self) -> None:
        mutated = copy.deepcopy(self.document)
        default = mutated["paths"]["/about"]["get"]["responses"]["default"]
        default.pop("x-ti-schema-status")
        errors = validate_document(mutated)
        self.assertTrue(any("unknown response is not marked" in error for error in errors), errors)

    def test_unresolved_route_and_template_conflicts_fail_closed(self) -> None:
        base_row = {
            "route_id": "one",
            "path": "/conflict/<int:id>",
        }
        same_path = [
            ExpandedRoute(0, "GET", base_row),
            ExpandedRoute(1, "GET", {"route_id": "two", "path": "/conflict/<int:id>"}),
        ]
        empty_overrides = {
            "collision_resolutions": [],
            "path_template_resolutions": [],
        }
        with self.assertRaisesRegex(ValueError, "unresolved path/method collision"):
            select_effective_routes(same_path, empty_overrides)

        different_templates = [
            ExpandedRoute(0, "GET", base_row),
            ExpandedRoute(1, "POST", {"route_id": "two", "path": "/conflict/<string:name>"}),
        ]
        with self.assertRaisesRegex(ValueError, "template hierarchy conflict"):
            resolve_template_paths(different_templates, empty_overrides)

        normalized_converter_collision = [
            ExpandedRoute(0, "GET", base_row),
            ExpandedRoute(1, "GET", {"route_id": "two", "path": "/conflict/<string:id>"}),
        ]
        normalized_mapping = {
            "/conflict/<int:id>": "/conflict/{id}",
            "/conflict/<string:id>": "/conflict/{id}",
        }
        with self.assertRaisesRegex(ValueError, "converter normalization collision"):
            reject_normalized_operation_collisions(
                normalized_converter_collision,
                normalized_mapping,
            )


if __name__ == "__main__":
    unittest.main()
