#!/usr/bin/env python3
"""Generate the deterministic phase-1 OpenAPI 3.1 contract draft.

Only frozen artifacts under ``Ti-Java/`` are inputs.  The legacy repository is
represented by source evidence already captured in the route matrix and golden
samples; it is never imported or executed by this generator.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = PROJECT_ROOT / "docs" / "refactor" / "02-route-parity-matrix.csv"
DEFAULT_GOLDEN_DIR = PROJECT_ROOT / "docs" / "refactor" / "golden-samples"
DEFAULT_OVERRIDES = PROJECT_ROOT / "contracts" / "openapi-manual-overrides.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "contracts" / "openapi.json"

OPENAPI_VERSION = "3.1.2"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
HTTP_METHOD_ORDER = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
HTTP_METHOD_SET = set(HTTP_METHOD_ORDER)
FLASK_PARAMETER = re.compile(r"<(?:(?P<converter>[^:<>]+):)?(?P<name>[^<>]+)>")
TEMPLATE_PARAMETER = re.compile(r"\{([^{}]+)\}")


@dataclass(frozen=True)
class ExpandedRoute:
    row_index: int
    method: str
    row: dict[str, str]

    @property
    def route_id(self) -> str:
        return self.row["route_id"]

    @property
    def path(self) -> str:
        return self.row["path"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_matrix(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    required = {
        "route_id",
        "path",
        "methods",
        "endpoint",
        "legacy_module",
        "source",
        "registration_source",
        "registration_kind",
        "decorators",
        "inline_auth_signals",
        "auth_semantics",
        "client_surfaces",
        "client_references",
        "contract_source",
        "target_module",
        "migration_status",
        "compatibility_notes",
    }
    missing = required - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"route matrix missing columns: {sorted(missing)}")
    if not rows:
        raise ValueError("route matrix is empty")
    return rows


def split_methods(value: str) -> list[str]:
    methods = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not methods or len(methods) != len(set(methods)):
        raise ValueError(f"invalid route methods: {value!r}")
    unsupported = set(methods) - HTTP_METHOD_SET
    if unsupported:
        raise ValueError(f"unsupported route methods: {sorted(unsupported)}")
    return sorted(methods, key=HTTP_METHOD_ORDER.index)


def expand_routes(rows: list[dict[str, str]]) -> list[ExpandedRoute]:
    expanded: list[ExpandedRoute] = []
    for row_index, row in enumerate(rows):
        for method in split_methods(row["methods"]):
            expanded.append(ExpandedRoute(row_index=row_index, method=method, row=row))
    return expanded


def parse_json_list(value: str, field: str, route_id: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{route_id} has invalid {field}: {exc}") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError(f"{route_id} {field} must be a JSON string array")
    return parsed


def flask_to_openapi_path(path: str) -> str:
    return FLASK_PARAMETER.sub(lambda match: "{" + match.group("name") + "}", path)


def flask_path_skeleton(path: str) -> str:
    return FLASK_PARAMETER.sub("{}", path)


def flask_path_regex(path: str) -> re.Pattern[str]:
    chunks: list[str] = []
    cursor = 0
    for match in FLASK_PARAMETER.finditer(path):
        chunks.append(re.escape(path[cursor : match.start()]))
        converter = match.group("converter") or "string"
        if converter == "int":
            chunks.append(r"[0-9]+")
        elif converter == "path":
            chunks.append(r".+")
        else:
            chunks.append(r"[^/]+")
        cursor = match.end()
    chunks.append(re.escape(path[cursor:]))
    return re.compile("^" + "".join(chunks) + "$")


def path_parameters(path: str) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in FLASK_PARAMETER.finditer(path):
        name = match.group("name")
        converter = match.group("converter") or "string"
        if name in seen:
            raise ValueError(f"duplicate Flask path parameter {name!r} in {path}")
        seen.add(name)
        if converter == "int":
            schema: dict[str, Any] = {"type": "integer", "format": "int64", "minimum": 0}
        elif converter == "path":
            schema = {"type": "string", "minLength": 1}
        elif converter == "string":
            schema = {"type": "string", "minLength": 1, "pattern": "^[^/]+$"}
        else:
            schema = {"type": "string", "minLength": 1, "x-ti-schema-status": "unknown-converter"}
        parameter: dict[str, Any] = {
            "name": name,
            "in": "path",
            "required": True,
            "schema": schema,
            "x-ti-flask-converter": converter,
        }
        if converter == "path":
            parameter["x-ti-openapi-limitation"] = (
                "Flask path accepts embedded slashes; standard OpenAPI path variables cannot represent "
                "unescaped slash semantics portably."
            )
        parameters.append(parameter)
    return parameters


def schema_from_observation(value: Any) -> tuple[dict[str, Any], bool]:
    """Return a non-overclaiming schema and whether some shape remains unknown."""
    if value is None:
        return {"type": "null", "x-ti-schema-status": "observed-null-only"}, True
    if isinstance(value, bool):
        return {"type": "boolean"}, False
    if isinstance(value, int):
        return {"type": "integer"}, False
    if isinstance(value, float):
        return {
            "type": "number",
            "x-ti-precision-status": "observed-json-number; decimal precision not inferred",
        }, True
    if isinstance(value, str):
        return {"type": "string"}, False
    if isinstance(value, list):
        if not value:
            return {
                "type": "array",
                "items": {"$ref": "#/components/schemas/UnknownPayload"},
                "x-ti-schema-status": "items-unknown-empty-golden-array",
            }, True
        item_schemas: list[dict[str, Any]] = []
        partial = False
        for item in value:
            item_schema, item_partial = schema_from_observation(item)
            if item_schema not in item_schemas:
                item_schemas.append(item_schema)
            partial = partial or item_partial
        items = item_schemas[0] if len(item_schemas) == 1 else {"oneOf": item_schemas}
        return {"type": "array", "items": items, "x-ti-schema-status": "golden-observation"}, partial
    if isinstance(value, dict):
        properties: dict[str, Any] = {}
        partial = False
        for key in sorted(value):
            child_schema, child_partial = schema_from_observation(value[key])
            properties[key] = child_schema
            partial = partial or child_partial
        return {
            "type": "object",
            "properties": properties,
            "additionalProperties": True,
            "x-ti-observed-properties": sorted(value),
            "x-ti-schema-status": "golden-observation-not-requiredness-proof",
        }, partial
    raise TypeError(f"unsupported golden JSON value: {type(value).__name__}")


def normalize_media_type(value: str | None) -> str:
    if not value:
        return "application/octet-stream"
    return value.split(";", 1)[0].strip().lower() or "application/octet-stream"


def load_golden_samples(golden_dir: Path) -> tuple[dict[str, Any], list[tuple[str, dict[str, Any]]]]:
    manifest_path = golden_dir / "manifest.json"
    manifest = load_json(manifest_path)
    sample_names = manifest.get("samples")
    if not isinstance(sample_names, list) or not sample_names:
        raise ValueError("golden manifest samples must be a non-empty array")
    if len(sample_names) != len(set(sample_names)):
        raise ValueError("golden manifest contains duplicate samples")
    samples: list[tuple[str, dict[str, Any]]] = []
    for name in sample_names:
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError(f"unsafe golden sample name: {name!r}")
        sample = load_json(golden_dir / name)
        if not isinstance(sample, dict):
            raise ValueError(f"golden sample {name} must be an object")
        samples.append((name, sample))
    return manifest, samples


def validate_override_shape(overrides: dict[str, Any]) -> None:
    if overrides.get("schema_version") != 1:
        raise ValueError("manual override schema_version must be 1")
    required_arrays = (
        "collision_resolutions",
        "path_template_resolutions",
        "operation_overrides",
        "golden_contract_pins",
    )
    for name in required_arrays:
        if not isinstance(overrides.get(name), list):
            raise ValueError(f"manual override {name} must be an array")
    for name in ("collision_resolutions", "operation_overrides"):
        ids = [entry.get("id") for entry in overrides[name]]
        if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"manual override {name} IDs must be non-empty and unique")


def operation_key(route_id: str, method: str) -> tuple[str, str]:
    return route_id, method.upper()


def select_effective_routes(
    expanded: list[ExpandedRoute], overrides: dict[str, Any]
) -> tuple[list[ExpandedRoute], list[dict[str, Any]], set[str]]:
    resolutions: dict[tuple[str, str], dict[str, Any]] = {}
    resolution_ids: set[str] = set()
    for resolution in overrides["collision_resolutions"]:
        key = (resolution.get("path"), str(resolution.get("method", "")).upper())
        if key in resolutions:
            raise ValueError(f"duplicate collision resolution for {key}")
        resolutions[key] = resolution

    grouped: dict[tuple[str, str], list[ExpandedRoute]] = defaultdict(list)
    for route in expanded:
        grouped[(route.path, route.method)].append(route)

    effective: list[ExpandedRoute] = []
    shadowed: list[dict[str, Any]] = []
    for key in sorted(grouped):
        routes = grouped[key]
        if len(routes) == 1:
            effective.append(routes[0])
            continue
        resolution = resolutions.get(key)
        if resolution is None:
            raise ValueError(f"unresolved path/method collision: {key} -> {[r.route_id for r in routes]}")
        route_ids = {route.route_id for route in routes}
        winner = resolution.get("effective_route_id")
        losers = resolution.get("shadowed_route_ids")
        if winner not in route_ids or not isinstance(losers, list):
            raise ValueError(f"invalid collision resolution {resolution.get('id')}")
        if set(losers) != route_ids - {winner}:
            raise ValueError(f"collision resolution {resolution.get('id')} does not cover all shadowed routes")
        winner_route = next(route for route in routes if route.route_id == winner)
        effective.append(winner_route)
        shadowed.append(
            {
                "resolutionId": resolution["id"],
                "path": key[0],
                "method": key[1],
                "effective": legacy_metadata(winner_route),
                "shadowed": [
                    legacy_metadata(route)
                    for route in routes
                    if route.route_id in set(losers)
                ],
                "reason": resolution.get("reason", ""),
                "sources": resolution.get("sources", []),
            }
        )
        resolution_ids.add(resolution["id"])
    unused = set(resolutions) - {key for key, routes in grouped.items() if len(routes) > 1}
    if unused:
        raise ValueError(f"unused collision resolutions: {sorted(unused)}")
    return effective, shadowed, resolution_ids


def resolve_template_paths(
    effective: list[ExpandedRoute], overrides: dict[str, Any]
) -> tuple[dict[str, str], set[str]]:
    by_skeleton: dict[str, set[str]] = defaultdict(set)
    for route in effective:
        by_skeleton[flask_path_skeleton(route.path)].add(flask_to_openapi_path(route.path))

    resolution_by_skeleton: dict[str, dict[str, Any]] = {}
    for resolution in overrides["path_template_resolutions"]:
        resolution_id = resolution.get("id")
        skeleton = resolution.get("skeleton")
        if not isinstance(resolution_id, str) or not resolution_id or not isinstance(skeleton, str):
            raise ValueError("path template resolutions require id and skeleton")
        if skeleton in resolution_by_skeleton:
            raise ValueError(f"duplicate path template resolution for {skeleton}")
        resolution_by_skeleton[skeleton] = resolution

    mapping: dict[str, str] = {}
    used: set[str] = set()
    for skeleton, rendered_paths in sorted(by_skeleton.items()):
        if len(rendered_paths) == 1:
            rendered = next(iter(rendered_paths))
        else:
            resolution = resolution_by_skeleton.get(skeleton)
            if resolution is None:
                raise ValueError(
                    f"OpenAPI template hierarchy conflict for {skeleton}: {sorted(rendered_paths)}"
                )
            rendered = resolution.get("canonical_path")
            if rendered not in rendered_paths:
                raise ValueError(f"template resolution {resolution.get('id')} selects an unknown path")
            used.add(resolution["id"])
        for route in effective:
            if flask_path_skeleton(route.path) == skeleton:
                mapping[route.path] = rendered
    configured_ids = {entry["id"] for entry in overrides["path_template_resolutions"]}
    if configured_ids - used:
        raise ValueError(f"unused path template resolutions: {sorted(configured_ids - used)}")
    return mapping, used


def reject_normalized_operation_collisions(
    effective: list[ExpandedRoute], rendered_path_by_flask_path: dict[str, str]
) -> None:
    """Fail if distinct Flask converters collapse onto one OAS path/method.

    Such routes can both be reachable in Flask, while OpenAPI can expose only one
    operation at that path/method.  Silently selecting a winner would lose
    behavior, so phase 1 deliberately requires the inventory/design to be
    revisited before generation can continue.
    """
    grouped: dict[tuple[str, str], list[ExpandedRoute]] = defaultdict(list)
    for route in effective:
        grouped[(rendered_path_by_flask_path[route.path], route.method)].append(route)
    collisions = {
        key: routes
        for key, routes in grouped.items()
        if len(routes) > 1
    }
    if collisions:
        details = {
            f"{method} {path}": [
                {"routeId": route.route_id, "flaskPath": route.path}
                for route in routes
            ]
            for (path, method), routes in sorted(collisions.items())
        }
        raise ValueError(
            "unresolved Flask-converter normalization collision; OpenAPI cannot silently choose: "
            + json.dumps(details, ensure_ascii=False, sort_keys=True)
        )


def _redocly_paths_ambiguous(first: str, second: str) -> bool:
    """Mirror Redocly 2.39.0 no-ambiguous-paths comparison."""
    first_parts = first.split("/")
    second_parts = second.split("/")
    if len(first_parts) != len(second_parts):
        return False
    first_variables = 0
    second_variables = 0
    ambiguous = True
    for first_part, second_part in zip(first_parts, second_parts):
        first_variable = bool(re.fullmatch(r"\{.+?\}", first_part))
        second_variable = bool(re.fullmatch(r"\{.+?\}", second_part))
        if first_variable or second_variable:
            first_variables += int(first_variable)
            second_variables += int(second_variable)
        elif first_part != second_part:
            ambiguous = False
    return ambiguous and first_variables == second_variables


def lint_ambiguous_path_pairs(paths: dict[str, Any]) -> list[dict[str, str]]:
    seen: list[str] = []
    findings: list[dict[str, str]] = []
    for current in sorted(paths):
        prior = next((item for item in seen if _redocly_paths_ambiguous(item, current)), None)
        if prior is not None:
            findings.append({"first": prior, "second": current})
        seen.append(current)
    return findings


def _walk_values(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)


def lint_unused_components(
    paths: dict[str, Any], components: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    referenced = {
        value["$ref"]
        for value in _walk_values({"paths": paths, "components": components})
        if isinstance(value, dict) and isinstance(value.get("$ref"), str)
    }
    security_references: set[str] = set()
    for path_item in paths.values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for requirement in operation.get("security", []):
                if isinstance(requirement, dict):
                    security_references.update(requirement)
    unused: list[dict[str, str]] = []
    for component_type in sorted(components):
        for name in sorted(components[component_type]):
            if component_type == "securitySchemes":
                used = name in security_references
            else:
                used = f"#/components/{component_type}/{name}" in referenced
            if not used:
                unused.append({"componentType": component_type, "name": name})
    return unused


def known_lint_findings(
    paths: dict[str, Any], components: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    ambiguous = lint_ambiguous_path_pairs(paths)
    trailing = sorted(path for path in paths if path != "/" and path.endswith("/"))
    unused = lint_unused_components(paths, components)
    total = len(ambiguous) + len(trailing) + len(unused)
    return {
        "externalValidator": {
            "tool": "@redocly/cli",
            "version": "2.39.0",
            "profile": "minimal",
            "expectedErrors": 0,
            "expectedWarnings": total,
        },
        "categories": [
            {
                "ruleId": "no-ambiguous-paths",
                "count": len(ambiguous),
                "disposition": "accepted-legacy-compatibility",
                "reason": (
                    "These static/dynamic Flask path hierarchies are frozen legacy facts. Flask converter "
                    "precedence remains authoritative; changing paths would break compatibility."
                ),
                "evidence": ambiguous,
            },
            {
                "ruleId": "no-path-trailing-slash",
                "count": len(trailing),
                "disposition": "accepted-legacy-compatibility",
                "reason": (
                    "Trailing slash is part of each frozen compatibility path and cannot be normalized "
                    "before its clients and status/redirect behavior are migrated."
                ),
                "evidence": trailing,
            },
            {
                "ruleId": "no-unused-components",
                "count": len(unused),
                "disposition": "accepted-phase1-predeclaration",
                "reason": (
                    "Shared target and error components are declared before /api/v1 operations consume "
                    "them; target-only security schemes must remain unused by legacy operations."
                ),
                "evidence": unused,
            },
        ],
    }


def legacy_metadata(route: ExpandedRoute) -> dict[str, Any]:
    row = route.row
    return {
        "routeId": row["route_id"],
        "method": route.method,
        "flaskPath": row["path"],
        "endpoint": row["endpoint"],
        "legacyModule": row["legacy_module"],
        "source": row["source"],
        "registrationSource": row["registration_source"],
        "registrationKind": row["registration_kind"],
        "contractSource": row["contract_source"],
        "decorators": parse_json_list(row["decorators"], "decorators", row["route_id"]),
        "inlineAuthSignals": parse_json_list(
            row["inline_auth_signals"], "inline_auth_signals", row["route_id"]
        ),
        "clientSurfaces": row["client_surfaces"].split(";") if row["client_surfaces"] else [],
    }


def security_for(auth_semantics: list[str]) -> tuple[list[dict[str, list[str]]], str, list[str]]:
    joined = "|".join(auth_semantics)
    roles: list[str] = []
    if "notification_admin_role" in joined:
        roles = ["admin", "notification_admin"]
    elif "subject_admin_role" in joined:
        roles = ["admin", "subject_admin"]
    elif "admin_role" in joined or "admin_blueprint_hook" in joined:
        roles = ["admin"]

    if "record_token_or_bearer" in joined:
        security = [{"recordToken": []}, {"legacyBearerJwt": []}]
    elif "route_decorator:jwt" in joined:
        security = [{"legacyBearerJwt": []}]
    elif any(
        marker in joined
        for marker in (
            "route_decorator:session_or_jwt",
            "global_session_or_valid_jwt",
            "admin_blueprint_hook:session_or_jwt",
        )
    ):
        security = [{"legacySessionCookie": []}, {"legacyBearerJwt": []}]
    elif "route_decorator:session" in joined or "global_anonymous_login_redirect" in joined:
        security = [{"legacySessionCookie": []}]
    elif any(marker.startswith("global_anonymous_allow") for marker in auth_semantics):
        security = [{}]
    elif "global_anonymous_returns_401" in joined:
        security = [{"legacySessionCookie": []}, {"legacyBearerJwt": []}]
    else:
        security = [{}]

    csrf_markers = [marker for marker in auth_semantics if marker.startswith("global_write_csrf_for_")]
    if csrf_markers and {"legacySessionCookie": []} in security:
        security = [
            {"legacySessionCookie": [], "legacyXRequestedWith": []}
            if item == {"legacySessionCookie": []}
            else item
            for item in security
        ]
    return security, "derived-from-frozen-auth-semantics", roles


def unknown_response() -> dict[str, Any]:
    return {
        "description": "Legacy response shape and status set have not yet been inferred.",
        "x-ti-schema-status": "unknown",
        "content": {
            "*/*": {
                "schema": {"$ref": "#/components/schemas/LegacyOpaquePayload"}
            }
        },
    }


def base_operation(route: ExpandedRoute) -> dict[str, Any]:
    row = route.row
    auth_semantics = parse_json_list(row["auth_semantics"], "auth_semantics", route.route_id)
    security, security_confidence, roles = security_for(auth_semantics)
    parameters = path_parameters(route.path)
    operation: dict[str, Any] = {
        "operationId": f"legacy_{route.route_id}_{route.method.lower()}",
        "summary": f"Legacy {route.method} {row['path']}",
        "description": (
            "Phase-1 compatibility contract draft. Inventory identity is authoritative; "
            "unknown schemas remain explicit until golden or manually audited evidence is added."
        ),
        "tags": [row["target_module"]],
        "parameters": parameters,
        "responses": {"default": unknown_response()},
        "security": security,
        "x-ti-envelope": "legacy",
        "x-ti-contract-maturity": "inferred",
        "x-ti-legacy": legacy_metadata(route),
        "x-ti-auth-semantics": auth_semantics,
        "x-ti-security-confidence": security_confidence,
        "x-ti-migration": {
            "targetModule": row["target_module"],
            "status": row["migration_status"],
            "compatibilityNotes": row["compatibility_notes"],
        },
        "x-ti-contract": {
            "confidence": "route-inventory-only",
            "pathParameters": "converter-derived",
            "nonPathParameters": "unknown",
            "requestBodySchema": "unknown",
            "responseSchema": "unknown",
            "sourceEvidence": [row["contract_source"]],
            "unknownAspects": [
                "query-header-cookie-parameters",
                "request-body",
                "response-statuses-and-payloads",
            ],
        },
    }
    if roles:
        operation["x-ti-required-roles"] = roles
        operation["x-ti-role-mode"] = "any"
    return operation


def match_golden_route(
    sample_name: str,
    sample: dict[str, Any],
    effective: list[ExpandedRoute],
    pins: dict[str, dict[str, Any]],
) -> ExpandedRoute:
    request = sample.get("request")
    response = sample.get("response")
    if not isinstance(request, dict) or not isinstance(response, dict):
        raise ValueError(f"golden sample {sample_name} requires request and response objects")
    method = str(request.get("method", "")).upper()
    path = request.get("path")
    if method not in HTTP_METHOD_SET or not isinstance(path, str):
        raise ValueError(f"golden sample {sample_name} has invalid method/path")
    pin = pins.get(sample_name)
    if pin is None:
        raise ValueError(f"golden sample {sample_name} has no manual pin")
    candidates = [
        route
        for route in effective
        if route.method == method and flask_path_regex(route.path).fullmatch(path)
    ]
    pinned = [route for route in candidates if route.route_id == pin.get("route_id")]
    if len(pinned) != 1:
        raise ValueError(
            f"golden sample {sample_name} pin does not resolve uniquely: "
            f"{[(route.route_id, route.path) for route in candidates]}"
        )
    route = pinned[0]
    if pin.get("method") != method or pin.get("path") != path or pin.get("status") != response.get("status"):
        raise ValueError(f"golden sample {sample_name} drifted from its structured pin")
    return route


def attach_golden(
    operation: dict[str, Any], sample_name: str, sample: dict[str, Any]
) -> None:
    request = sample["request"]
    response = sample["response"]
    request_json = request.get("json")
    response_body = response.get("body")
    response_schema, response_partial = schema_from_observation(response_body)
    media_type = normalize_media_type((response.get("headers") or {}).get("Content-Type"))
    status = str(response["status"])
    operation["responses"][status] = {
        "description": f"Observed legacy response from {sample_name}; one sample is not exhaustive.",
        "content": {
            media_type: {
                "schema": response_schema,
                "example": response_body,
            }
        },
        "x-ti-schema-status": "golden-sample-partial" if response_partial else "golden-sample-observed",
        "x-ti-observed-content-type": (response.get("headers") or {}).get("Content-Type"),
    }
    if request_json is not None:
        request_schema, request_partial = schema_from_observation(request_json)
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": request_schema,
                    "example": request_json,
                }
            },
            "x-ti-schema-status": "golden-sample-partial" if request_partial else "golden-sample-observed",
        }
    headers = request.get("headers") or {}
    for header_name, header_value in sorted(headers.items()):
        operation["parameters"].append(
            {
                "name": header_name,
                "in": "header",
                "required": False,
                "schema": {"type": "string", "const": header_value},
                "example": header_value,
                "x-ti-schema-status": "golden-sample-observed",
            }
        )
    contract = operation["x-ti-contract"]
    contract["confidence"] = "golden-sample-observed"
    operation["x-ti-contract-maturity"] = "observed"
    contract["requestBodySchema"] = (
        "golden-sample-observed" if request_json is not None else "not-present-in-golden-request"
    )
    contract["responseSchema"] = (
        "golden-sample-partial" if response_partial else "golden-sample-observed"
    )
    contract["goldenSample"] = f"docs/refactor/golden-samples/{sample_name}"
    contract["sourceEvidence"].append(contract["goldenSample"])
    contract["unknownAspects"] = [
        "unobserved-query-header-cookie-parameters",
        "unobserved-statuses-and-payload-variants",
    ]


def apply_operation_override(
    operation: dict[str, Any], override: dict[str, Any], golden_example: Any | None
) -> None:
    if "parameters" in override:
        operation["parameters"].extend(copy.deepcopy(override["parameters"]))
        operation["x-ti-contract"]["nonPathParameters"] = "source-audited"
    if "request_body" in override:
        request_body = copy.deepcopy(override["request_body"])
        if golden_example is not None:
            media = request_body.get("content", {}).get("application/json")
            if isinstance(media, dict):
                media["example"] = golden_example
        request_body["x-ti-schema-status"] = "source-audited"
        operation["requestBody"] = request_body
        operation["x-ti-contract"]["requestBodySchema"] = "source-audited"
    for status, response in override.get("responses", {}).items():
        if status in operation["responses"] and status != "default":
            raise ValueError(f"override {override['id']} replaces an observed response {status}")
        operation["responses"][status] = copy.deepcopy(response)
    contract = operation["x-ti-contract"]
    current = contract["confidence"]
    contract["confidence"] = (
        f"{override['confidence']}+golden-sample" if current.startswith("golden-") else override["confidence"]
    )
    contract["manualOverrideId"] = override["id"]
    contract["sourceEvidence"].extend(override.get("sources", []))
    unknown = list(contract["unknownAspects"])
    if "request_body" in override:
        unknown = [item for item in unknown if "request-body" not in item]
    if "parameters" in override:
        unknown = [item for item in unknown if "query-header-cookie" not in item]
        unknown.append("unobserved-header-cookie-parameters")
    contract["unknownAspects"] = sorted(set(unknown))


def component_schemas() -> dict[str, Any]:
    return {
        "LegacyOpaquePayload": {
            "description": (
                "Compatibility placeholder for a legacy payload whose schema has not been proven. It "
                "intentionally places no JSON type constraints and cannot prove migration completeness."
            ),
            "x-ti-schema-status": "unknown",
            "x-ti-envelope": "legacy",
        },
        "UnknownPayload": {
            "description": (
                "Generic JSON value used only as a type parameter placeholder in target shared components. "
                "Concrete /api/v1 operations must replace it with an explicit schema."
            ),
            "x-ti-schema-status": "generic-requires-specialization",
        },
        "ApiStatus": {
            "type": "string",
            "enum": ["success", "error"],
            "description": "Common legacy status values; target /api/v1 envelopes use the boolean success discriminator.",
            "x-ti-enum-policy": "closed-wire-values; additions require a reviewed contract change",
        },
        "ErrorCode": {
            "type": "string",
            "pattern": "^[A-Z][A-Z0-9_]*$",
            "description": "Stable target error code; values are reviewed as part of each operation contract.",
            "x-ti-enum-policy": "closed per operation; additions require a reviewed contract change",
        },
        "LegacyErrorCode": {
            "oneOf": [
                {"type": "string", "minLength": 1},
                {"type": "integer"},
            ],
            "description": "Compatibility-only code shape. Exact values remain operation-specific evidence.",
            "x-ti-schema-status": "legacy-operation-specific",
        },
        "ApiEnvelope": {
            "type": "object",
            "required": ["success", "data", "meta"],
            "properties": {
                "success": {"type": "boolean", "const": True},
                "data": {"$ref": "#/components/schemas/UnknownPayload"},
                "meta": {"$ref": "#/components/schemas/ResponseMeta"},
            },
            "additionalProperties": False,
            "description": (
                "Canonical /api/v1 success envelope. Downloads and event streams are not wrapped. Legacy "
                "compatibility operations keep observed shapes until migration is approved."
            ),
        },
        "ErrorEnvelope": {
            "type": "object",
            "required": ["success", "error", "meta"],
            "properties": {
                "success": {"type": "boolean", "const": False},
                "error": {"$ref": "#/components/schemas/ErrorBody"},
                "meta": {"$ref": "#/components/schemas/ResponseMeta"},
            },
            "additionalProperties": False,
            "description": "Canonical /api/v1 error envelope; details is optional and must not expose secrets or stacks.",
        },
        "ErrorBody": {
            "type": "object",
            "required": ["code", "message"],
            "properties": {
                "code": {"$ref": "#/components/schemas/ErrorCode"},
                "message": {"type": "string", "minLength": 1},
                "details": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ErrorDetail"},
                },
            },
            "additionalProperties": False,
        },
        "ErrorDetail": {
            "type": "object",
            "required": ["code", "message"],
            "properties": {
                "field": {"$ref": "#/components/schemas/NullableString"},
                "code": {"$ref": "#/components/schemas/ErrorCode"},
                "message": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
            "description": "Sanitized validation detail; never contains stack traces, SQL, credentials, or upstream raw bodies.",
        },
        "LegacyErrorEnvelope": {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": {"type": "string", "minLength": 1},
                "code": {"$ref": "#/components/schemas/LegacyErrorCode"},
                "message": {"type": "string"},
                "msg": {"type": "string"},
                "data": {"$ref": "#/components/schemas/LegacyOpaquePayload"},
            },
            "additionalProperties": True,
            "description": "Compatibility-only error shape; each operation still needs observed status/payload evidence.",
            "x-ti-schema-status": "legacy-operation-specific",
        },
        "PaginationMeta": {
            "type": "object",
            "required": [
                "page",
                "page_size",
                "total_items",
                "total_pages",
                "has_next",
                "has_previous",
            ],
            "properties": {
                "page": {"type": "integer", "minimum": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "total_items": {"type": "integer", "minimum": 0},
                "total_pages": {"type": "integer", "minimum": 0},
                "has_next": {"type": "boolean"},
                "has_previous": {"type": "boolean"},
            },
            "additionalProperties": False,
            "x-ti-pagination-policy": (
                "one-based page; page_size defaults to 20 and is at most 100 unless an operation proves "
                "another bound; total_items counts the full filtered result"
            ),
        },
        "ResponseMeta": {
            "type": "object",
            "required": ["request_id"],
            "properties": {
                "request_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Must equal the authoritative X-Request-ID response header.",
                },
                "pagination": {"$ref": "#/components/schemas/PaginationMeta"},
            },
            "additionalProperties": False,
        },
        "PageEnvelope": {
            "type": "object",
            "required": ["success", "data", "meta"],
            "properties": {
                "success": {"type": "boolean", "const": True},
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/UnknownPayload"},
                    "description": "Concrete list operations must replace UnknownPayload with their item schema.",
                },
                "meta": {
                    "type": "object",
                    "required": ["request_id", "pagination"],
                    "properties": {
                        "request_id": {"type": "string", "minLength": 1},
                        "pagination": {"$ref": "#/components/schemas/PaginationMeta"},
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
            "description": "Canonical /api/v1 list envelope; pagination is always meta.pagination.",
        },
        "Instant": {
            "type": "string",
            "format": "date-time",
            "description": "RFC 3339 timestamp with an explicit offset; target serialization uses UTC Z.",
            "x-ti-time-policy": "UTC at API boundaries; preserve source timezone before conversion",
        },
        "LocalDate": {
            "type": "string",
            "format": "date",
            "description": "Calendar date without timezone conversion.",
        },
        "LocalDateTime": {
            "type": "string",
            "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,9})?$",
            "description": "Local wall-clock time without offset; only for domains whose timezone is separately fixed.",
        },
        "DecimalString": {
            "type": "string",
            "pattern": "^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?$",
            "description": "Canonical base-10 decimal string; binary floating point and exponent notation are forbidden.",
            "x-ti-java-type": "java.math.BigDecimal",
            "x-ti-scale-policy": "each concrete property must declare scale and rounding in its reviewed contract",
        },
        "MoneyDecimal": {
            "type": "string",
            "pattern": "^-?(?:0|[1-9][0-9]*)\\.[0-9]{2}$",
            "description": "Currency amount with exactly two fractional digits.",
            "x-ti-java-type": "java.math.BigDecimal",
            "x-ti-decimal-scale": 2,
            "x-ti-rounding-mode": "field-contract-required; never implicit",
        },
        "ScoreDecimal": {
            "allOf": [{"$ref": "#/components/schemas/DecimalString"}],
            "description": "Exact assessment score. The operation or field contract must declare its scale and rounding rule.",
            "x-ti-rounding-mode": "operation-specific; never implicit",
        },
        "NullableString": {
            "type": ["string", "null"],
            "description": "Explicit null means no value; omission means the producer did not include the field.",
            "x-ti-null-policy": "null and omitted are distinct wire states",
        },
        "NullableId": {
            "type": ["integer", "null"],
            "minimum": 1,
            "description": "Nullable positive database identifier; null is not equivalent to zero or omission.",
            "x-ti-null-policy": "null and omitted are distinct wire states",
        },
        "LoginRequest": {
            "type": "object",
            "required": ["username", "password"],
            "properties": {
                "username": {
                    "type": "string",
                    "minLength": 1,
                    "pattern": "^(?:.*@.*|1[3-9][0-9]{9})$",
                    "description": "Legacy identifier: any trimmed value containing @, or a mainland China mobile number.",
                },
                "password": {"type": "string", "minLength": 1, "writeOnly": True},
                "remember": {"type": "boolean", "default": False},
                "redirect": {"$ref": "#/components/schemas/NullableString"},
            },
            "additionalProperties": True,
            "x-ti-legacy-extra-fields": "Pydantic default behavior ignores unknown input fields",
            "x-ti-contract-source": [
                "app/modules/auth/schemas.py:48",
                "app/modules/auth/routes/api.py:68",
            ],
        },
        "RecordResultRequest": {
            "type": "object",
            "required": ["question_id", "is_correct"],
            "properties": {
                "question_id": {
                    "oneOf": [
                        {"type": "integer", "minimum": 1},
                        {"type": "string", "pattern": "^[1-9][0-9]*$"},
                    ]
                },
                "is_correct": {
                    "type": "boolean",
                    "x-ti-legacy-coercion": "handler applies Python truthiness to non-boolean input; clients must send boolean",
                },
                "clear_mistake_on_correct": {
                    "oneOf": [
                        {"type": "boolean"},
                        {"type": "integer"},
                        {"type": "string"},
                    ],
                    "default": True,
                    "x-ti-legacy-coercion": "false/0/no/off strings map to false; other values use boolean coercion",
                },
            },
            "additionalProperties": True,
            "x-ti-contract-source": ["app/modules/quiz/routes/api_components/core.py:85"],
        },
    }


def component_responses() -> dict[str, Any]:
    labels = {
        "BadRequest": "Request validation failed.",
        "Unauthorized": "Authentication is missing or invalid.",
        "Forbidden": "The authenticated principal lacks permission.",
        "NotFound": "The requested resource does not exist.",
        "Conflict": "The request conflicts with current state.",
        "TooManyRequests": "The legacy or target rate limit was exceeded.",
        "InternalError": "An internal error occurred; sensitive details are not returned.",
    }
    return {
        name: {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/LegacyErrorEnvelope"}
                }
            },
        }
        for name, description in labels.items()
    }


def security_schemes() -> dict[str, Any]:
    return {
        "legacySessionCookie": {
            "type": "apiKey",
            "in": "cookie",
            "name": "session",
            "description": "Legacy Flask signed session compatibility. Target Web sessions use hardened cookies.",
        },
        "legacyBearerJwt": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Legacy mini-program JWT compatibility, including session_version semantics.",
        },
        "recordToken": {
            "type": "apiKey",
            "in": "header",
            "name": "X-AI-Record-Token",
            "description": "Scoped legacy admin automation token; never include its value in this contract.",
        },
        "legacyXRequestedWith": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Requested-With",
            "description": "Legacy write gate expects XMLHttpRequest for session-authenticated writes; this is not authentication by itself.",
        },
        "csrfHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-CSRF-TOKEN",
            "description": "Target SPA CSRF token. It is combined with the target secure Session cookie, not used by legacy operations.",
        },
        "accessToken": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Target short-lived mini-program access token. No current compatibility operation references it.",
        },
    }


def generate_document(
    matrix_path: Path = DEFAULT_MATRIX,
    golden_dir: Path = DEFAULT_GOLDEN_DIR,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> dict[str, Any]:
    rows = load_matrix(matrix_path)
    expanded = expand_routes(rows)
    overrides = load_json(overrides_path)
    if not isinstance(overrides, dict):
        raise ValueError("manual overrides must be a JSON object")
    validate_override_shape(overrides)
    manifest, samples = load_golden_samples(golden_dir)

    effective, shadowed, used_collision_ids = select_effective_routes(expanded, overrides)
    rendered_path_by_flask_path, used_template_ids = resolve_template_paths(effective, overrides)
    reject_normalized_operation_collisions(effective, rendered_path_by_flask_path)

    operation_overrides: dict[tuple[str, str], dict[str, Any]] = {}
    for override in overrides["operation_overrides"]:
        key = operation_key(str(override.get("route_id", "")), str(override.get("method", "")))
        if key in operation_overrides:
            raise ValueError(f"duplicate operation override for {key}")
        if override.get("confidence") != "source-audited" or not override.get("sources"):
            raise ValueError(f"operation override {override.get('id')} lacks source-audited evidence")
        operation_overrides[key] = override

    pins: dict[str, dict[str, Any]] = {}
    for pin in overrides["golden_contract_pins"]:
        sample_name = pin.get("sample")
        if not isinstance(sample_name, str) or sample_name in pins:
            raise ValueError("golden pins require unique sample names")
        pins[sample_name] = pin
    if set(pins) != {name for name, _sample in samples}:
        raise ValueError("golden pins must exactly cover the manifest samples")

    operations: dict[tuple[str, str], dict[str, Any]] = {}
    route_by_key: dict[tuple[str, str], ExpandedRoute] = {}
    for route in effective:
        key = operation_key(route.route_id, route.method)
        if key in operations:
            raise ValueError(f"duplicate route identity {key}")
        operation = base_operation(route)
        target_path = rendered_path_by_flask_path[route.path]
        operation["x-ti-migration"].update(
            {
                "targetOperationId": operation["operationId"],
                "targetPath": target_path,
                "targetMethod": route.method,
            }
        )
        operations[key] = operation
        route_by_key[key] = route

    golden_by_key: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for sample_name, sample in samples:
        route = match_golden_route(sample_name, sample, effective, pins)
        key = operation_key(route.route_id, route.method)
        if key in golden_by_key:
            raise ValueError(f"multiple golden samples map to {key}")
        attach_golden(operations[key], sample_name, sample)
        golden_by_key[key] = (sample_name, sample)

    used_override_ids: set[str] = set()
    for key, override in operation_overrides.items():
        operation = operations.get(key)
        if operation is None:
            raise ValueError(f"operation override {override['id']} does not match an effective route")
        golden_example = None
        if key in golden_by_key:
            golden_example = golden_by_key[key][1]["request"].get("json")
        apply_operation_override(operation, override, golden_example)
        used_override_ids.add(override["id"])

    paths: dict[str, dict[str, Any]] = {}
    for key, operation in operations.items():
        route = route_by_key[key]
        rendered_path = rendered_path_by_flask_path[route.path]
        path_item = paths.setdefault(rendered_path, {})
        method_key = route.method.lower()
        if method_key in path_item:
            raise ValueError(f"OpenAPI operation collision at {route.method} {rendered_path}")
        path_item[method_key] = operation

    for collision in shadowed:
        winner = collision["effective"]
        key = operation_key(winner["routeId"], winner["method"])
        operations[key]["x-ti-shadowed-legacy-operations"] = collision["shadowed"]
        operations[key]["x-ti-collision-resolution"] = collision["resolutionId"]

    golden_hashes = {
        "manifest.json": sha256_file(golden_dir / "manifest.json"),
        **{name: sha256_file(golden_dir / name) for name, _sample in samples},
    }
    unknown_count = sum(
        operation["x-ti-contract"]["responseSchema"] == "unknown"
        for operation in operations.values()
    )
    maturity_counts = Counter(
        operation["x-ti-contract-maturity"] for operation in operations.values()
    )
    components = {
        "schemas": component_schemas(),
        "responses": component_responses(),
        "securitySchemes": security_schemes(),
    }
    document: dict[str, Any] = {
        "openapi": OPENAPI_VERSION,
        "jsonSchemaDialect": JSON_SCHEMA_DIALECT,
        "info": {
            "title": "Ti Legacy Compatibility API Contract",
            "version": "0.1.0-phase1",
            "description": (
                "Deterministic phase-1 draft generated from the frozen Flask route inventory, golden "
                "samples, and reviewed source overrides. Unknown schemas are deliberate and auditable."
            ),
        },
        "servers": [
            {
                "url": "/",
                "description": "Relative compatibility base; deployment host and port are environment-specific.",
            }
        ],
        "tags": [
            {"name": name, "description": f"Target modular-monolith boundary: {name}."}
            for name in sorted({row["target_module"] for row in rows})
        ],
        "paths": paths,
        "components": components,
        "x-ti-contract-policy": copy.deepcopy(overrides["policy"]),
        "x-ti-inputs": {
            "routeMatrix": {
                "path": "docs/refactor/02-route-parity-matrix.csv",
                "sha256": sha256_file(matrix_path),
            },
            "manualOverrides": {
                "path": "contracts/openapi-manual-overrides.json",
                "sha256": sha256_file(overrides_path),
            },
            "goldenSamples": {
                "directory": "docs/refactor/golden-samples",
                "sha256": golden_hashes,
                "legacyCommit": manifest.get("legacy_commit"),
                "capturedAt": manifest.get("captured_at"),
            },
        },
        "x-ti-inventory": {
            "routeRuleCount": len(rows),
            "expandedLegacyOperationCount": len(expanded),
            "renderedOpenApiOperationCount": len(operations),
            "openApiPathCount": len(paths),
            "shadowedLegacyOperationCount": sum(len(item["shadowed"]) for item in shadowed),
            "goldenOperationCount": len(golden_by_key),
            "sourceAuditedOverrideCount": len(used_override_ids),
            "unknownResponseSchemaOperationCount": unknown_count,
            "contractMaturityCounts": {
                maturity: maturity_counts.get(maturity, 0)
                for maturity in ("observed", "tested", "manual", "inferred", "unknown")
            },
            "legacyCoverage": {
                "renderedTargetOperations": len(operations),
                "shadowedLegacyOperations": sum(len(item["shadowed"]) for item in shadowed),
                "expandedLegacyOperations": len(expanded),
            },
        },
        "x-ti-shadowed-operations": shadowed,
        "x-ti-known-lint-findings": known_lint_findings(paths, components),
        "x-ti-generation": {
            "deterministic": True,
            "timeDependentFields": False,
            "generator": "tools/generate_phase1_openapi.py",
            "usedCollisionResolutionIds": sorted(used_collision_ids),
            "usedPathTemplateResolutionIds": sorted(used_template_ids),
            "usedOperationOverrideIds": sorted(used_override_ids),
        },
    }
    return document


def main() -> int:
    args = parse_args()
    document = generate_document(args.matrix, args.golden_dir, args.overrides)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(dump_json_bytes(document))
    inventory = document["x-ti-inventory"]
    print(
        "generated OpenAPI "
        f"{document['openapi']}: {inventory['routeRuleCount']} rules / "
        f"{inventory['expandedLegacyOperationCount']} legacy operations / "
        f"{inventory['renderedOpenApiOperationCount']} rendered operations -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
