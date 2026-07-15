#!/usr/bin/env python3
"""Standard-library structural validator for the phase-1 OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

from generate_phase1_openapi import (
    DEFAULT_GOLDEN_DIR,
    DEFAULT_MATRIX,
    DEFAULT_OUTPUT,
    DEFAULT_OVERRIDES,
    HTTP_METHOD_ORDER,
    JSON_SCHEMA_DIALECT,
    OPENAPI_VERSION,
    TEMPLATE_PARAMETER,
    dump_json_bytes,
    expand_routes,
    generate_document,
    known_lint_findings,
    legacy_metadata,
    load_golden_samples,
    load_json,
    load_matrix,
    normalize_media_type,
    operation_key,
    reject_normalized_operation_collisions,
    resolve_template_paths,
    select_effective_routes,
    sha256_file,
)


MATURITY_VALUES = {"observed", "tested", "manual", "inferred", "unknown"}
REQUIRED_SECURITY_SCHEMES = {
    "legacySessionCookie",
    "legacyBearerJwt",
    "recordToken",
    "legacyXRequestedWith",
    "csrfHeader",
    "accessToken",
}
LEGACY_ONLY_SCHEMES = {
    "legacySessionCookie",
    "legacyBearerJwt",
    "recordToken",
    "legacyXRequestedWith",
}
TARGET_ONLY_SCHEMES = {"csrfHeader", "accessToken"}
FORBIDDEN_OLD_SCHEMES = {"legacyJwtBearer", "legacyRecordToken"}
EXPECTED_COMPONENT_SCHEMAS = {
    "ApiEnvelope",
    "ApiStatus",
    "DecimalString",
    "ErrorBody",
    "ErrorCode",
    "ErrorDetail",
    "ErrorEnvelope",
    "Instant",
    "LegacyErrorCode",
    "LegacyErrorEnvelope",
    "LegacyOpaquePayload",
    "LocalDate",
    "LocalDateTime",
    "LoginRequest",
    "MoneyDecimal",
    "NullableId",
    "NullableString",
    "PageEnvelope",
    "PaginationMeta",
    "RecordResultRequest",
    "ResponseMeta",
    "ScoreDecimal",
    "UnknownPayload",
}
SECRET_PATTERN = re.compile(
    r"(?:-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{12,}|\bBearer\s+[A-Za-z0-9._~+/=-]{12,})",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--openapi", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def iter_operations(document: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHOD_ORDER:
            operation = path_item.get(method.lower())
            if isinstance(operation, dict):
                yield path, method, operation


def walk(value: Any, pointer: str = "#") -> Iterator[tuple[str, Any]]:
    yield pointer, value
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from walk(child, f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{pointer}/{index}")


def resolve_pointer(document: Any, reference: str) -> Any:
    if not reference.startswith("#/"):
        raise KeyError("external references are not allowed")
    value = document
    for raw in reference[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[int(token)]
        else:
            value = value[token]
    return value


def check(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def expected_state(
    matrix_path: Path, golden_dir: Path, overrides_path: Path
) -> tuple[
    list[dict[str, str]],
    list[Any],
    list[Any],
    dict[str, str],
    dict[str, Any],
    dict[str, Any],
    list[tuple[str, dict[str, Any]]],
]:
    rows = load_matrix(matrix_path)
    expanded = expand_routes(rows)
    overrides = load_json(overrides_path)
    effective, _shadowed, _used_collision = select_effective_routes(expanded, overrides)
    rendered_paths, _used_templates = resolve_template_paths(effective, overrides)
    reject_normalized_operation_collisions(effective, rendered_paths)
    manifest, samples = load_golden_samples(golden_dir)
    return rows, expanded, effective, rendered_paths, overrides, manifest, samples


def validate_components(document: dict[str, Any], errors: list[str]) -> None:
    components = document.get("components")
    check(isinstance(components, dict), errors, "components must be an object")
    if not isinstance(components, dict):
        return
    schemas = components.get("schemas")
    responses = components.get("responses")
    security = components.get("securitySchemes")
    check(isinstance(schemas, dict), errors, "components.schemas must be an object")
    check(isinstance(responses, dict), errors, "components.responses must be an object")
    check(isinstance(security, dict), errors, "components.securitySchemes must be an object")
    if not isinstance(schemas, dict) or not isinstance(security, dict):
        return

    check(
        EXPECTED_COMPONENT_SCHEMAS <= set(schemas),
        errors,
        f"missing shared schemas: {sorted(EXPECTED_COMPONENT_SCHEMAS - set(schemas))}",
    )
    check(
        set(security) == REQUIRED_SECURITY_SCHEMES,
        errors,
        f"security schemes must be exactly {sorted(REQUIRED_SECURITY_SCHEMES)}, got {sorted(security)}",
    )
    check(not (FORBIDDEN_OLD_SCHEMES & set(security)), errors, "obsolete security scheme names remain")
    if set(security) == REQUIRED_SECURITY_SCHEMES:
        check(
            security["legacySessionCookie"].get("type") == "apiKey"
            and security["legacySessionCookie"].get("in") == "cookie"
            and security["legacySessionCookie"].get("name") == "session",
            errors,
            "legacySessionCookie must model the session cookie",
        )
        check(
            security["legacyBearerJwt"].get("type") == "http"
            and security["legacyBearerJwt"].get("scheme") == "bearer",
            errors,
            "legacyBearerJwt must model the compatibility Bearer JWT",
        )
        check(
            security["recordToken"].get("name") == "X-AI-Record-Token",
            errors,
            "recordToken header name drifted",
        )
        check(
            security["legacyXRequestedWith"].get("name") == "X-Requested-With",
            errors,
            "legacyXRequestedWith must preserve the real compatibility write gate",
        )
        check(
            security["csrfHeader"].get("name") == "X-CSRF-TOKEN",
            errors,
            "csrfHeader target scheme drifted",
        )
        check(
            security["accessToken"].get("type") == "http"
            and security["accessToken"].get("scheme") == "bearer",
            errors,
            "accessToken must be a target Bearer token",
        )

    if not EXPECTED_COMPONENT_SCHEMAS <= set(schemas):
        return
    api = schemas["ApiEnvelope"]
    check(api.get("required") == ["success", "data", "meta"], errors, "ApiEnvelope required fields drifted")
    check(api.get("properties", {}).get("success", {}).get("const") is True, errors, "ApiEnvelope.success must be true")
    check(
        api.get("properties", {}).get("meta", {}).get("$ref") == "#/components/schemas/ResponseMeta",
        errors,
        "ApiEnvelope metadata must use ResponseMeta",
    )
    error = schemas["ErrorEnvelope"]
    check(error.get("required") == ["success", "error", "meta"], errors, "ErrorEnvelope required fields drifted")
    check(error.get("properties", {}).get("success", {}).get("const") is False, errors, "ErrorEnvelope.success must be false")
    check(
        error.get("properties", {}).get("error", {}).get("$ref") == "#/components/schemas/ErrorBody",
        errors,
        "ErrorEnvelope.error must use ErrorBody",
    )
    meta = schemas["ResponseMeta"]
    check(meta.get("required") == ["request_id"], errors, "ResponseMeta must require request_id")
    pagination = schemas["PaginationMeta"]
    expected_page_fields = [
        "page",
        "page_size",
        "total_items",
        "total_pages",
        "has_next",
        "has_previous",
    ]
    check(pagination.get("required") == expected_page_fields, errors, "PaginationMeta required fields drifted")
    check(
        set(pagination.get("properties", {})) == set(expected_page_fields),
        errors,
        "PaginationMeta properties drifted",
    )
    page_size = pagination.get("properties", {}).get("page_size", {})
    check(
        page_size.get("default") == 20 and page_size.get("maximum") == 100,
        errors,
        "target page_size must default to 20 and cap at 100",
    )
    page_envelope = schemas["PageEnvelope"]
    check(
        page_envelope.get("properties", {}).get("meta", {}).get("required")
        == ["request_id", "pagination"],
        errors,
        "PageEnvelope pagination must live at meta.pagination",
    )
    check(
        schemas["Instant"].get("format") == "date-time"
        and "UTC" in schemas["Instant"].get("description", ""),
        errors,
        "Instant must be RFC3339 date-time with UTC policy",
    )
    check(schemas["LocalDate"].get("format") == "date", errors, "LocalDate must use the date format")
    check(
        schemas["DecimalString"].get("type") == "string"
        and schemas["DecimalString"].get("x-ti-java-type") == "java.math.BigDecimal",
        errors,
        "DecimalString must be a BigDecimal-backed decimal string",
    )
    check(
        schemas["MoneyDecimal"].get("type") == "string"
        and schemas["MoneyDecimal"].get("x-ti-decimal-scale") == 2,
        errors,
        "MoneyDecimal must be a scale-2 decimal string",
    )
    check(
        "operation-specific" in schemas["ScoreDecimal"].get("x-ti-rounding-mode", ""),
        errors,
        "ScoreDecimal must not invent a global rounding rule",
    )
    check(
        schemas["NullableString"].get("type") == ["string", "null"],
        errors,
        "NullableString must use OpenAPI 3.1 union types",
    )
    check(
        schemas["LegacyOpaquePayload"].get("x-ti-schema-status") == "unknown",
        errors,
        "LegacyOpaquePayload must remain explicitly unknown",
    )


def validate_document(
    document: dict[str, Any],
    matrix_path: Path = DEFAULT_MATRIX,
    golden_dir: Path = DEFAULT_GOLDEN_DIR,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> list[str]:
    errors: list[str] = []
    try:
        rows, expanded, effective, rendered_paths, overrides, manifest, samples = expected_state(
            matrix_path, golden_dir, overrides_path
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return [f"cannot load frozen inputs: {exc}"]

    check(document.get("openapi") == OPENAPI_VERSION, errors, f"openapi must be {OPENAPI_VERSION}")
    check(
        document.get("jsonSchemaDialect") == JSON_SCHEMA_DIALECT,
        errors,
        "jsonSchemaDialect must be JSON Schema 2020-12",
    )
    paths = document.get("paths")
    check(isinstance(paths, dict) and bool(paths), errors, "paths must be a non-empty object")
    if not isinstance(paths, dict):
        return errors
    for path, path_item in paths.items():
        check(isinstance(path, str) and path.startswith("/"), errors, f"invalid OpenAPI path key: {path!r}")
        check(isinstance(path_item, dict), errors, f"path item {path} must be an object")
        if isinstance(path_item, dict):
            unexpected = set(path_item) - {method.lower() for method in HTTP_METHOD_ORDER}
            check(not unexpected, errors, f"path item {path} has unsupported fields: {sorted(unexpected)}")

    skeleton_paths: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        skeleton_paths[TEMPLATE_PARAMETER.sub("{}", path)].add(path)
    conflicts = {key: value for key, value in skeleton_paths.items() if len(value) > 1}
    check(not conflicts, errors, f"OpenAPI contains ambiguous path template hierarchies: {conflicts}")

    actual_operations = list(iter_operations(document))
    operation_ids = [operation.get("operationId") for _path, _method, operation in actual_operations]
    check(
        all(isinstance(item, str) and item for item in operation_ids),
        errors,
        "every operation must have a non-empty operationId",
    )
    check(len(operation_ids) == len(set(operation_ids)), errors, "operationId values must be globally unique")

    expected_by_key = {operation_key(route.route_id, route.method): route for route in effective}
    expected_path_by_key = {
        operation_key(route.route_id, route.method): rendered_paths[route.path] for route in effective
    }
    actual_by_key: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    maturity_counter: Counter[str] = Counter()
    referenced_security: set[str] = set()
    for path, method, operation in actual_operations:
        legacy = operation.get("x-ti-legacy")
        if not isinstance(legacy, dict):
            errors.append(f"{method} {path} lacks x-ti-legacy")
            continue
        key = operation_key(str(legacy.get("routeId", "")), method)
        if key in actual_by_key:
            errors.append(f"duplicate rendered route identity {key}")
            continue
        actual_by_key[key] = (path, operation)
        route = expected_by_key.get(key)
        if route is None:
            errors.append(f"unexpected rendered route {key} at {method} {path}")
            continue
        check(path == expected_path_by_key[key], errors, f"{key} rendered at wrong path {path}")
        check(legacy == legacy_metadata(route), errors, f"{key} x-ti-legacy drifted from route matrix")
        check(
            operation.get("operationId") == f"legacy_{route.route_id}_{method.lower()}",
            errors,
            f"{key} operationId drifted",
        )
        check(operation.get("x-ti-envelope") == "legacy", errors, f"{key} must declare legacy envelope")
        maturity = operation.get("x-ti-contract-maturity")
        check(maturity in MATURITY_VALUES, errors, f"{key} has invalid contract maturity {maturity!r}")
        if maturity in MATURITY_VALUES:
            maturity_counter[maturity] += 1
        contract = operation.get("x-ti-contract")
        check(isinstance(contract, dict), errors, f"{key} lacks x-ti-contract")
        if isinstance(contract, dict):
            check(bool(contract.get("confidence")), errors, f"{key} lacks contract confidence")
            check(bool(contract.get("sourceEvidence")), errors, f"{key} lacks contract evidence")
            check(bool(contract.get("unknownAspects")), errors, f"{key} silently claims a complete contract")
            if maturity == "observed":
                check(bool(contract.get("goldenSample")), errors, f"{key} observed maturity lacks golden evidence")
            if maturity == "manual":
                check(bool(contract.get("manualOverrideId")), errors, f"{key} manual maturity lacks override")
                check(
                    any("test" in str(source).lower() for source in contract.get("sourceEvidence", [])),
                    errors,
                    f"{key} manual maturity lacks contract-test evidence",
                )
            if contract.get("responseSchema") == "unknown":
                default = operation.get("responses", {}).get("default", {})
                ref = (
                    default.get("content", {})
                    .get("*/*", {})
                    .get("schema", {})
                    .get("$ref")
                )
                check(default.get("x-ti-schema-status") == "unknown", errors, f"{key} unknown response is not marked")
                check(
                    ref == "#/components/schemas/LegacyOpaquePayload",
                    errors,
                    f"{key} unknown response does not use LegacyOpaquePayload",
                )

        migration = operation.get("x-ti-migration")
        check(
            migration
            == {
                "targetModule": route.row["target_module"],
                "status": route.row["migration_status"],
                "compatibilityNotes": route.row["compatibility_notes"],
                "targetOperationId": operation.get("operationId"),
                "targetPath": path,
                "targetMethod": method,
            },
            errors,
            f"{key} migration metadata drifted",
        )
        check(operation.get("tags") == [route.row["target_module"]], errors, f"{key} target tag drifted")
        try:
            expected_auth = json.loads(route.row["auth_semantics"])
        except json.JSONDecodeError:
            expected_auth = None
        check(operation.get("x-ti-auth-semantics") == expected_auth, errors, f"{key} auth semantics drifted")

        parameters = operation.get("parameters")
        check(isinstance(parameters, list), errors, f"{key} parameters must be an array")
        if isinstance(parameters, list):
            names = [(item.get("in"), item.get("name")) for item in parameters if isinstance(item, dict)]
            check(len(names) == len(set(names)), errors, f"{key} has duplicate parameters")
            template_names = TEMPLATE_PARAMETER.findall(path)
            path_parameters = [item for item in parameters if isinstance(item, dict) and item.get("in") == "path"]
            check(
                sorted(item.get("name") for item in path_parameters) == sorted(template_names),
                errors,
                f"{key} path template parameters are incomplete",
            )
            check(
                all(item.get("required") is True and isinstance(item.get("schema"), dict) for item in path_parameters),
                errors,
                f"{key} path parameters must be required and typed",
            )

        responses = operation.get("responses")
        check(isinstance(responses, dict) and bool(responses), errors, f"{key} must define responses")
        security = operation.get("security")
        check(isinstance(security, list) and bool(security), errors, f"{key} must explicitly define security")
        if isinstance(security, list):
            for requirement in security:
                check(isinstance(requirement, dict), errors, f"{key} has invalid security requirement")
                if isinstance(requirement, dict):
                    for scheme, scopes in requirement.items():
                        referenced_security.add(scheme)
                        check(isinstance(scopes, list), errors, f"{key} security scopes must be arrays")

    check(set(actual_by_key) == set(expected_by_key), errors, "rendered operations do not exactly cover effective routes")

    shadow_root = document.get("x-ti-shadowed-operations")
    check(isinstance(shadow_root, list), errors, "x-ti-shadowed-operations must be an array")
    shadowed_keys: set[tuple[str, str]] = set()
    if isinstance(shadow_root, list):
        for collision in shadow_root:
            if not isinstance(collision, dict):
                errors.append("invalid shadowed operation record")
                continue
            for shadow in collision.get("shadowed", []):
                if isinstance(shadow, dict):
                    shadowed_keys.add(operation_key(str(shadow.get("routeId", "")), str(shadow.get("method", ""))))
            effective_meta = collision.get("effective", {})
            effective_key = operation_key(
                str(effective_meta.get("routeId", "")), str(effective_meta.get("method", ""))
            )
            rendered = actual_by_key.get(effective_key)
            check(rendered is not None, errors, f"shadow winner {effective_key} is not rendered")
            if rendered is not None:
                check(
                    rendered[1].get("x-ti-collision-resolution") == collision.get("resolutionId"),
                    errors,
                    f"shadow winner {effective_key} lacks collision resolution",
                )
    expanded_keys = {operation_key(route.route_id, route.method) for route in expanded}
    check(
        set(actual_by_key) | shadowed_keys == expanded_keys,
        errors,
        "rendered plus shadowed operation identities do not cover all expanded legacy methods",
    )
    check(
        shadowed_keys == {("ddd38e139d39", "GET")}
        and ("1aae474aceca", "GET") in actual_by_key,
        errors,
        "GET /profile shadow resolution drifted",
    )

    defined_security = set(document.get("components", {}).get("securitySchemes", {}))
    check(referenced_security <= defined_security, errors, "an operation references an undefined security scheme")
    check(not (FORBIDDEN_OLD_SCHEMES & referenced_security), errors, "operations reference obsolete security scheme names")
    check(not (TARGET_ONLY_SCHEMES & referenced_security), errors, "legacy operations must not reference target-only security schemes")
    check(referenced_security <= LEGACY_ONLY_SCHEMES, errors, "legacy operations reference a non-legacy security scheme")

    pins = {pin["sample"]: pin for pin in overrides["golden_contract_pins"]}
    for sample_name, sample in samples:
        pin = pins.get(sample_name)
        if pin is None:
            errors.append(f"golden sample {sample_name} lacks a pin")
            continue
        key = operation_key(pin["route_id"], pin["method"])
        rendered = actual_by_key.get(key)
        if rendered is None:
            errors.append(f"golden sample {sample_name} operation {key} is not rendered")
            continue
        operation = rendered[1]
        response = operation.get("responses", {}).get(str(pin["status"]), {})
        media_type = normalize_media_type(sample["response"].get("headers", {}).get("Content-Type"))
        example = response.get("content", {}).get(media_type, {}).get("example")
        check(example == sample["response"].get("body"), errors, f"golden response {sample_name} drifted")
        check(operation.get("x-ti-contract-maturity") == "observed", errors, f"{sample_name} must be observed")
        request_json = sample["request"].get("json")
        if request_json is not None:
            body_example = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("example")
            )
            check(body_example == request_json, errors, f"golden request {sample_name} drifted")

    inventory = document.get("x-ti-inventory")
    check(isinstance(inventory, dict), errors, "x-ti-inventory must be an object")
    expected_maturity_counts = {value: maturity_counter.get(value, 0) for value in ("observed", "tested", "manual", "inferred", "unknown")}
    if isinstance(inventory, dict):
        check(inventory.get("routeRuleCount") == len(rows), errors, "route rule count drifted")
        check(inventory.get("expandedLegacyOperationCount") == len(expanded), errors, "expanded method count drifted")
        check(inventory.get("renderedOpenApiOperationCount") == len(effective), errors, "rendered operation count drifted")
        check(inventory.get("openApiPathCount") == len(paths), errors, "OpenAPI path count drifted")
        check(inventory.get("shadowedLegacyOperationCount") == len(shadowed_keys), errors, "shadowed count drifted")
        check(inventory.get("goldenOperationCount") == len(samples), errors, "golden operation count drifted")
        check(
            inventory.get("contractMaturityCounts") == expected_maturity_counts,
            errors,
            "contract maturity counts drifted",
        )
        check(
            inventory.get("legacyCoverage")
            == {
                "renderedTargetOperations": len(effective),
                "shadowedLegacyOperations": len(shadowed_keys),
                "expandedLegacyOperations": len(expanded),
            },
            errors,
            "legacy-to-target coverage equation drifted",
        )
        check(
            inventory.get("legacyCoverage", {}).get("renderedTargetOperations", 0)
            + inventory.get("legacyCoverage", {}).get("shadowedLegacyOperations", 0)
            == inventory.get("legacyCoverage", {}).get("expandedLegacyOperations", -1),
            errors,
            "legacy coverage must equal target operations plus explicit shadows",
        )
    check(
        maturity_counter == Counter({"inferred": len(effective) - len(samples), "observed": len(samples)}),
        errors,
        f"unexpected phase-1 maturity distribution: {dict(maturity_counter)}",
    )

    generation = document.get("x-ti-generation", {})
    operation_override_ids = sorted(entry["id"] for entry in overrides["operation_overrides"])
    collision_ids = sorted(entry["id"] for entry in overrides["collision_resolutions"])
    template_ids = sorted(entry["id"] for entry in overrides["path_template_resolutions"])
    check(generation.get("deterministic") is True, errors, "generation must be deterministic")
    check(generation.get("timeDependentFields") is False, errors, "time-dependent generation fields are forbidden")
    check(generation.get("usedOperationOverrideIds") == operation_override_ids, errors, "unused/missing operation override")
    check(generation.get("usedCollisionResolutionIds") == collision_ids, errors, "unused/missing collision resolution")
    check(generation.get("usedPathTemplateResolutionIds") == template_ids, errors, "unused/missing template resolution")

    inputs = document.get("x-ti-inputs", {})
    check(
        inputs.get("routeMatrix", {}).get("sha256") == sha256_file(matrix_path),
        errors,
        "route matrix input hash drifted",
    )
    check(
        inputs.get("manualOverrides", {}).get("sha256") == sha256_file(overrides_path),
        errors,
        "manual override input hash drifted",
    )
    check(
        inputs.get("goldenSamples", {}).get("legacyCommit") == manifest.get("legacy_commit"),
        errors,
        "golden legacy commit drifted",
    )

    validate_components(document, errors)

    components = document.get("components")
    if isinstance(components, dict):
        expected_lint = known_lint_findings(paths, components)
        check(
            document.get("x-ti-known-lint-findings") == expected_lint,
            errors,
            "known external lint findings do not match deterministic paths/components analysis",
        )
        categories = {
            item.get("ruleId"): item
            for item in expected_lint.get("categories", [])
            if isinstance(item, dict)
        }
        check(
            expected_lint.get("externalValidator", {}).get("expectedWarnings") == 48,
            errors,
            "Redocly minimal warning baseline must remain an explained set of 48",
        )
        check(
            categories.get("no-ambiguous-paths", {}).get("count") == 30,
            errors,
            "legacy ambiguous-path warning count drifted",
        )
        check(
            categories.get("no-path-trailing-slash", {}).get("count") == 4,
            errors,
            "legacy trailing-slash warning count drifted",
        )
        check(
            categories.get("no-unused-components", {}).get("count") == 14,
            errors,
            "phase-1 unused-component warning count drifted",
        )

    for pointer, value in walk(document):
        if isinstance(value, dict) and "nullable" in value:
            errors.append(f"OpenAPI 3.0 nullable keyword is forbidden at {pointer}")
        if isinstance(value, dict) and "$ref" in value:
            reference = value["$ref"]
            if not isinstance(reference, str):
                errors.append(f"non-string $ref at {pointer}")
            else:
                try:
                    resolve_pointer(document, reference)
                except (KeyError, IndexError, ValueError, TypeError):
                    errors.append(f"unresolved or external $ref {reference!r} at {pointer}")
        if isinstance(value, str):
            if SECRET_PATTERN.search(value):
                errors.append(f"possible secret material at {pointer}")
            if value.startswith("/Users/") or re.match(r"^[A-Za-z]:\\\\Users\\", value):
                errors.append(f"machine absolute path at {pointer}")
        if pointer.endswith("/example") and isinstance(value, str) and "password" in pointer.lower():
            check("redacted" in value.lower(), errors, f"password example is not redacted at {pointer}")

    return errors


def validate_determinism(
    openapi_path: Path,
    matrix_path: Path = DEFAULT_MATRIX,
    golden_dir: Path = DEFAULT_GOLDEN_DIR,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> list[str]:
    errors: list[str] = []
    try:
        first = dump_json_bytes(generate_document(matrix_path, golden_dir, overrides_path))
        second = dump_json_bytes(generate_document(matrix_path, golden_dir, overrides_path))
        actual = openapi_path.read_bytes()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return [f"deterministic regeneration failed: {exc}"]
    check(first == second, errors, "two in-memory regenerations are not byte-identical")
    check(actual == first, errors, "checked-in openapi.json differs from deterministic regeneration")
    return errors


def main() -> int:
    args = parse_args()
    try:
        document = load_json(args.openapi)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL phase 1 OpenAPI: cannot read {args.openapi}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(document, dict):
        print("FAIL phase 1 OpenAPI: root must be an object", file=sys.stderr)
        return 1
    errors = validate_document(document, args.matrix, args.golden_dir, args.overrides)
    errors.extend(validate_determinism(args.openapi, args.matrix, args.golden_dir, args.overrides))
    if errors:
        print(f"FAIL phase 1 OpenAPI ({len(errors)} errors):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    inventory = document["x-ti-inventory"]
    print(
        "PASS phase 1 OpenAPI: "
        f"{inventory['routeRuleCount']} rules / "
        f"{inventory['expandedLegacyOperationCount']} legacy operations / "
        f"{inventory['renderedOpenApiOperationCount']} rendered / "
        f"{inventory['shadowedLegacyOperationCount']} shadowed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
