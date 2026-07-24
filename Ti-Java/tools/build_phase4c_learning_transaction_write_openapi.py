#!/usr/bin/env python3
"""Build the Phase 4C transaction-write OpenAPI 3.1.2 overlay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "openapi/phase4c-learning-transaction-write.openapi.json"
)
EXECUTION_COMMIT = "dad308eab71dbe26bfa87ada78c29df3bd159ae0"

ROUTES = (
    {
        "route_id": "6d548bfd6830",
        "method": "post",
        "path": "/api/favorite",
        "owner": "learning",
        "group": "favorite",
        "rate": 30,
        "request": "FavoriteRequest",
        "success": "FavoriteSuccess",
        "summary": "Toggle a favorite through the Web compatibility alias",
        "application_api": (
            "io.saksk.ti.learning.api."
            "LearningWriteApplicationApi#toggleFavorite"
        ),
    },
    {
        "route_id": "b52d3008d4d1",
        "method": "post",
        "path": "/api/quiz/favorite",
        "owner": "learning",
        "group": "favorite",
        "rate": 30,
        "request": "FavoriteRequest",
        "success": "FavoriteSuccess",
        "summary": "Toggle a favorite through the quiz API alias",
        "application_api": (
            "io.saksk.ti.learning.api."
            "LearningWriteApplicationApi#toggleFavorite"
        ),
    },
    {
        "route_id": "87bb4fb340c8",
        "method": "post",
        "path": "/api/record_result",
        "owner": "learning",
        "group": "record-result",
        "rate": 60,
        "request": "RecordResultRequest",
        "success": "RecordResultSuccess",
        "summary": "Record a quiz result through the Web compatibility alias",
        "application_api": (
            "io.saksk.ti.learning.api."
            "RecordResultApplicationApi#recordResult"
        ),
    },
    {
        "route_id": "67dccafb3ea4",
        "method": "post",
        "path": "/api/quiz/record_result",
        "owner": "learning",
        "group": "record-result",
        "rate": 60,
        "request": "RecordResultRequest",
        "success": "RecordResultSuccess",
        "summary": "Record a quiz result through the quiz API alias",
        "application_api": (
            "io.saksk.ti.learning.api."
            "RecordResultApplicationApi#recordResult"
        ),
    },
    {
        "route_id": "bf3cb0c4f9ab",
        "method": "post",
        "path": "/api/quiz/study/learn/record",
        "owner": "learning",
        "group": "study-learn",
        "rate": 60,
        "request": "StudyLearnRequest",
        "success": "StudyLearnSuccess",
        "summary": "Record a learning attempt",
        "application_api": (
            "io.saksk.ti.learning.api."
            "StudyWriteApplicationApi#recordLearning"
        ),
    },
    {
        "route_id": "c797832c43db",
        "method": "post",
        "path": "/api/quiz/study/review/record",
        "owner": "learning",
        "group": "study-review-record",
        "rate": 60,
        "request": "StudyReviewRequest",
        "success": "StudyReviewSuccess",
        "summary": "Record a spaced-review rating",
        "application_api": (
            "io.saksk.ti.learning.api."
            "StudyWriteApplicationApi#recordReview"
        ),
    },
    {
        "route_id": "278e1eac5eb4",
        "method": "post",
        "path": "/api/quiz/study/review/master",
        "owner": "learning",
        "group": "study-review-master",
        "rate": 30,
        "request": "StudyMasterRequest",
        "success": "StudyMasterSuccess",
        "summary": "Set or clear the mastered review state",
        "application_api": (
            "io.saksk.ti.learning.api."
            "StudyWriteApplicationApi#setReviewMastered"
        ),
    },
    {
        "route_id": "59c9c7366ec3",
        "method": "post",
        "path": "/api/user/checkin",
        "owner": "learning",
        "group": "checkin",
        "rate": 10,
        "request": None,
        "success": "CheckinSuccess",
        "summary": "Create or replay today's user check-in",
        "application_api": (
            "io.saksk.ti.learning.api.CheckinApplicationApi#checkIn"
        ),
    },
    {
        "route_id": "624b5ac217d0",
        "method": "put",
        "path": "/api/quiz/questions/{questionId}",
        "owner": "catalog",
        "group": "question-edit",
        "rate": 10,
        "request": "QuestionEditRequest",
        "success": "QuestionEditSuccess",
        "summary": "Edit a catalog question as an authorized administrator",
        "application_api": (
            "io.saksk.ti.catalog.api."
            "QuestionEditApplicationApi#editQuestion"
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def schema_ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def response_ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/responses/{name}"}


def compatibility_properties(
    data: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "status": {"const": "success"},
        "data": data,
        "message": {"const": ""},
        "request_id": {"type": "string", "minLength": 1},
    }
    if extra:
        properties.update(extra)
    return {
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def question_id_request(
    extra: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "question_id": {
            "description": (
                "Legacy Python-style integer coercion is preserved; values that "
                "cannot become a signed 64-bit integer receive HTTP 400."
            )
        }
    }
    if extra:
        properties.update(extra)
    return {
        "type": "object",
        "properties": properties,
        "required": required or ["question_id"],
        "additionalProperties": True,
    }


def request_schemas() -> dict[str, Any]:
    scope = {
        "source": {
            "description": "Legacy scope selector; absent/false values default to public."
        },
        "subject": {
            "description": "Legacy subject selector; exact compatibility coercion applies."
        },
        "bank_id": {
            "description": "Optional signed 32-bit bank identifier after legacy coercion."
        },
    }
    return {
        "FavoriteRequest": question_id_request(),
        "RecordResultRequest": question_id_request(
            {
                "is_correct": {
                    "description": "Legacy Python truthiness is preserved."
                },
                "clear_mistake_on_correct": {
                    "description": (
                        "Optional legacy boolean; defaults to true and accepts "
                        "0/1, true/false, yes/no and on/off."
                    )
                },
            },
            ["question_id", "is_correct"],
        ),
        "StudyLearnRequest": question_id_request(
            {
                "is_correct": {
                    "description": "Required value interpreted with legacy truthiness."
                },
                **scope,
            },
            ["question_id", "is_correct"],
        ),
        "StudyReviewRequest": question_id_request(
            {
                "rating": {
                    "type": "string",
                    "enum": ["known", "fuzzy", "unknown"],
                },
                **scope,
            },
            ["question_id", "rating"],
        ),
        "StudyMasterRequest": question_id_request(
            {
                "is_mastered": {
                    "description": "Optional legacy boolean that defaults to true."
                },
                **scope,
            }
        ),
        "QuestionEditRequest": {
            "type": "object",
            "properties": {
                "content": {"type": ["string", "null"]},
                "q_type": {"type": ["string", "null"]},
                "answer": {"type": ["string", "null"]},
                "explanation": {"type": ["string", "null"]},
                "options": {
                    "description": (
                        "Optional JSON value or already-encoded string; catalog "
                        "validation owns the canonical option shape."
                    )
                },
            },
            "additionalProperties": True,
        },
    }


def success_schemas() -> dict[str, Any]:
    option = {
        "type": "object",
        "required": ["key", "value"],
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "additionalProperties": False,
    }
    return {
        "FavoriteSuccess": compatibility_properties({
            "type": "object",
            "required": ["is_favorite"],
            "properties": {"is_favorite": {"type": "boolean"}},
            "additionalProperties": False,
        }),
        "RecordResultSuccess": compatibility_properties(
            {
                "type": "object",
                "required": ["action"],
                "properties": {"action": {"type": "string"}},
                "additionalProperties": False,
            },
            extra={"action": {"type": "string"}},
        ),
        "StudyLearnSuccess": compatibility_properties({
            "type": "object",
            "required": ["streak", "is_learned", "next_due_at"],
            "properties": {
                "streak": {"type": "integer"},
                "is_learned": {"type": "integer", "enum": [0, 1]},
                "next_due_at": {
                    "type": ["string", "null"],
                    "pattern": (
                        "^[0-9]{4}-[0-9]{2}-[0-9]{2} "
                        "[0-9]{2}:[0-9]{2}:[0-9]{2}$"
                    ),
                },
            },
            "additionalProperties": False,
        }),
        "StudyReviewSuccess": compatibility_properties({
            "type": "object",
            "required": ["review_level", "next_due_at"],
            "properties": {
                "review_level": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 7,
                },
                "next_due_at": {
                    "type": "string",
                    "pattern": (
                        "^[0-9]{4}-[0-9]{2}-[0-9]{2} "
                        "[0-9]{2}:[0-9]{2}:[0-9]{2}$"
                    ),
                },
            },
            "additionalProperties": False,
        }),
        "StudyMasterSuccess": compatibility_properties({
            "type": "object",
            "required": ["is_mastered"],
            "properties": {
                "is_mastered": {"type": "integer", "enum": [0, 1]}
            },
            "additionalProperties": False,
        }),
        "CheckinSuccess": compatibility_properties({
            "type": "object",
            "required": [
                "today",
                "checked_in_today",
                "streak_days",
                "total_days",
                "just_checked_in",
                "checked_in_at",
                "checked_dates",
            ],
            "properties": {
                "today": {"type": "string", "format": "date"},
                "checked_in_today": {"type": "boolean"},
                "streak_days": {"type": "integer", "minimum": 0},
                "total_days": {"type": "integer", "minimum": 0},
                "just_checked_in": {"type": "boolean"},
                "checked_in_at": {"type": ["string", "null"]},
                "checked_dates": {
                    "type": "array",
                    "items": {"type": "string", "format": "date"},
                },
            },
            "additionalProperties": False,
        }),
        "QuestionEditSuccess": compatibility_properties({
            "type": "object",
            "required": [
                "id",
                "content",
                "q_type",
                "options",
                "answer",
                "explanation",
                "image_path",
                "subject",
                "is_fav",
                "is_mistake",
            ],
            "properties": {
                "id": {"type": "integer", "format": "int64", "minimum": 0},
                "content": {"type": "string"},
                "q_type": {"type": "string"},
                "options": {"type": "array", "items": option},
                "answer": {"type": "string"},
                "explanation": {"type": "string"},
                "image_path": {"type": ["string", "null"]},
                "subject": {"type": "string"},
                "is_fav": {"type": "integer", "enum": [0, 1]},
                "is_mistake": {"type": "integer", "enum": [0, 1]},
            },
            "additionalProperties": False,
        }),
    }


def common_headers() -> dict[str, Any]:
    return {
        "RequestId": {
            "description": "Stable request correlation identifier.",
            "schema": {"type": "string"},
        },
        "Vary": {
            "description": "Contains Origin and Cookie.",
            "schema": {"type": "string"},
        },
        "RateLimit": {
            "description": "Route-specific fixed-window request limit.",
            "schema": {"type": "integer", "minimum": 1},
        },
        "RateRemaining": {
            "description": "Requests remaining in the current fixed window.",
            "schema": {"type": "integer", "minimum": 0},
        },
        "RateReset": {
            "description": "Unix epoch second at which the current window resets.",
            "schema": {"type": "integer", "format": "int64"},
        },
        "RetryAfter": {
            "description": "Seconds until the current window resets.",
            "schema": {"type": "integer", "minimum": 1},
        },
    }


def response_headers(*, rate: bool) -> dict[str, Any]:
    result = {
        "X-Request-ID": {"$ref": "#/components/headers/RequestId"},
        "Vary": {"$ref": "#/components/headers/Vary"},
    }
    if rate:
        result.update({
            "X-RateLimit-Limit": {
                "$ref": "#/components/headers/RateLimit"
            },
            "X-RateLimit-Remaining": {
                "$ref": "#/components/headers/RateRemaining"
            },
            "X-RateLimit-Reset": {
                "$ref": "#/components/headers/RateReset"
            },
            "Retry-After": {
                "$ref": "#/components/headers/RetryAfter"
            },
        })
    return result


def responses() -> dict[str, Any]:
    error_content = {
        "application/json": {
            "schema": schema_ref("CompatibilityError")
        }
    }
    return {
        "BadRequest": {
            "description": "Malformed or compatibility-invalid request.",
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "AuthenticationRequired": {
            "description": "No accepted credential could authenticate the actor.",
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "Forbidden": {
            "description": (
                "Safety/authorization denial, or a bodyless CORS rejection "
                "before authentication."
            ),
            "headers": response_headers(rate=True),
            "content": error_content,
            "x-ti-bodyless-cors-variant": True,
        },
        "NotFound": {
            "description": "Question or identity was not found.",
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "Conflict": {
            "description": (
                "The idempotency key conflicts with the first request or its "
                "first transaction is still in progress."
            ),
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "RateLimited": {
            "description": "The route or authentication fixed window is exhausted.",
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "InternalFailure": {
            "description": "A compatibility-safe internal failure.",
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "ServiceUnavailable": {
            "description": "Authentication authority or Redis is unavailable.",
            "headers": response_headers(rate=True),
            "content": error_content,
        },
        "PreflightAccepted": {
            "description": "Allowed CORS preflight; no authentication or rate charge.",
            "headers": {
                "X-Request-ID": {
                    "$ref": "#/components/headers/RequestId"
                },
                "Vary": {"$ref": "#/components/headers/Vary"},
                "Access-Control-Allow-Origin": {
                    "schema": {"type": "string"}
                },
                "Access-Control-Allow-Methods": {
                    "schema": {"type": "string"}
                },
                "Access-Control-Allow-Headers": {
                    "schema": {"type": "string"}
                },
            },
        },
        "PreflightRejected": {
            "description": "Bodyless disallowed CORS preflight.",
            "headers": {
                "X-Request-ID": {
                    "$ref": "#/components/headers/RequestId"
                },
                "Vary": {"$ref": "#/components/headers/Vary"},
            },
        },
    }


def operation(route: dict[str, Any]) -> dict[str, Any]:
    route_id = route["route_id"]
    result: dict[str, Any] = {
        "operationId": f"legacy_{route_id}_{route['method']}",
        "summary": route["summary"],
        "tags": ["learning-transaction-write"],
        "security": [
            {"targetSession": []},
            {"legacyFlaskSession": []},
            {"legacyBearer": []},
        ],
        "parameters": [
            {"$ref": "#/components/parameters/IdempotencyKey"}
        ],
        "responses": {
            "200": {
                "description": "Compatibility success envelope.",
                "headers": response_headers(rate=True),
                "content": {
                    "application/json": {
                        "schema": schema_ref(route["success"])
                    }
                },
            },
            "400": response_ref("BadRequest"),
            "401": response_ref("AuthenticationRequired"),
            "403": response_ref("Forbidden"),
            "404": response_ref("NotFound"),
            "409": response_ref("Conflict"),
            "429": response_ref("RateLimited"),
            "500": response_ref("InternalFailure"),
            "503": response_ref("ServiceUnavailable"),
        },
        "x-ti-route-id": route_id,
        "x-ti-semantic-group": route["group"],
        "x-ti-application-api": route["application_api"],
        "x-ti-idempotency": {
            "optional": True,
            "maximumUtf8Bytes": 255,
            "blankIsAbsent": True,
            "sameActorKeySamePayload": "replay",
            "sameActorKeyDifferentPayloadStatus": 409,
            "businessAndReceiptTransaction": "atomic",
        },
        "x-ti-authentication": {
            "accepted": [
                "authoritative target Session",
                "successfully exchanged legacy Flask Session",
                "valid legacy Bearer",
            ],
            "sessionRequiresExactXRequestedWith": "XMLHttpRequest",
            "bearerBypassesSessionSafetyHeader": True,
            "anonymousChargedByIpBefore401": True,
        },
        "x-ti-rate-limit": {
            "algorithm": "Redis fixed minute window",
            "requestsPerMinute": route["rate"],
            "keyIsolation": "route + HMAC(identity or client address)",
            "failClosedStatus": 503,
        },
        "x-ti-cors": {
            "exactConfiguredOriginsOnly": True,
            "disallowedSimpleOrPreflightStatus": 403,
            "disallowedBodyBytes": 0,
        },
        "x-ti-migration": {
            "status": "pending",
            "targetModule": route["owner"],
            "countsAsMigratedOperation": False,
            "productionCutover": False,
        },
    }
    if route["request"] is not None:
        result["requestBody"] = {
            "required": False,
            "content": {
                "application/json": {
                    "schema": schema_ref(route["request"])
                }
            },
            "x-ti-absent-or-malformed-body": "route-compatible HTTP 400",
        }
    return result


def options_operation(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "operationId": f"legacy_{route['route_id']}_options_derived",
        "summary": "Terminate CORS preflight before authentication and rate limiting",
        "tags": ["learning-transaction-write"],
        "security": [],
        "responses": {
            "204": response_ref("PreflightAccepted"),
            "403": response_ref("PreflightRejected"),
        },
        "x-ti-route-id": route["route_id"],
        "x-ti-derived-from": (
            f"legacy_{route['route_id']}_{route['method']}"
        ),
        "x-ti-options-contract": {
            "expectedRequestedMethod": route["method"].upper(),
            "allowedMethods": [
                route["method"].upper(),
                "OPTIONS",
            ],
            "allowedRequestHeaders": [
                "Accept",
                "Authorization",
                "Content-Type",
                "Idempotency-Key",
                "X-Request-ID",
                "X-Requested-With",
            ],
            "authentication": False,
            "rateLimited": False,
            "applicationCalled": False,
            "sql": 0,
            "bodyBytesForEveryStatus": 0,
        },
        "x-ti-migration": {
            "status": "derived",
            "targetModule": route["owner"],
            "countsAsMigratedOperation": False,
            "productionCutover": False,
        },
    }


def build_document() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for route in ROUTES:
        path_item: dict[str, Any] = {
            route["method"]: operation(route),
            "options": options_operation(route),
        }
        if route["group"] == "question-edit":
            path_item["parameters"] = [
                {"$ref": "#/components/parameters/QuestionId"}
            ]
        paths[route["path"]] = path_item

    schemas = {
        **request_schemas(),
        **success_schemas(),
        "CompatibilityError": {
            "type": "object",
            "required": ["status", "message", "status_code", "request_id"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["error", "forbidden", "unauthorized"],
                },
                "message": {"type": "string"},
                "status_code": {
                    "type": "integer",
                    "enum": [400, 401, 403, 404, 409, 429, 500, 503],
                },
                "request_id": {"type": "string", "minLength": 1},
                "payload": {"type": "null"},
                "code": {"type": "string"},
                "data": {"type": "object"},
            },
            "additionalProperties": False,
        },
    }
    return {
        "openapi": "3.1.2",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Ti Phase 4C Learning Transaction-Write Compatibility Delta",
            "version": "0.4.0-phase4c-transaction-write",
            "description": (
                "Self-contained Java overlay for nine legacy transaction-write "
                "operations. Implementations and real execution evidence exist; "
                "operations remain pending until the fixed successor and route "
                "promotion gates close. Production cutover is disabled."
            ),
        },
        "servers": [{
            "url": "http://127.0.0.1:{port}",
            "description": "Phase 4C local/test Java runtime only",
            "variables": {"port": {"default": "18080"}},
        }],
        "tags": [{
            "name": "learning-transaction-write",
            "description": (
                "Learning-owned compatibility writes; question-edit delegates "
                "persistence to catalog::api."
            ),
        }],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "targetSession": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "TI_SESSION",
                },
                "legacyFlaskSession": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session",
                },
                "legacyBearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "legacy signed access token",
                },
            },
            "parameters": {
                "IdempotencyKey": {
                    "name": "Idempotency-Key",
                    "in": "header",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "maxLength": 255,
                    },
                    "x-ti-length-unit": "UTF-8 bytes",
                    "x-ti-blank-is-absent": True,
                },
                "QuestionId": {
                    "name": "questionId",
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "description": (
                        "Unicode Nd decimal segment normalized losslessly to a "
                        "non-negative signed 64-bit identifier."
                    ),
                    "x-ti-converter": "Unicode Nd decimal compatibility firewall",
                },
            },
            "headers": common_headers(),
            "responses": responses(),
            "schemas": schemas,
        },
        "x-ti-execution-checkpoint": {
            "commitOid": EXECUTION_COMMIT,
            "redisVersion": "7.4.7",
            "postgresVersions": ["16.14", "18.4"],
            "realTomcatRandomPort": True,
            "realCredentialChannels": [
                "target Session",
                "legacy Flask Session exchange",
                "legacy Bearer",
            ],
            "identityTableUpdateCount": 0,
            "usersLastActiveUnchanged": True,
        },
        "x-ti-route-accounting": {
            "frozenBaselineOperationCount": 611,
            "predecessorMigratedOperationCount": 13,
            "implementedPendingOperationCount": 9,
            "effectiveMigratedOperationCount": 13,
            "effectivePendingOperationCount": 598,
            "productionCutoverOperationCount": 0,
            "documentedDerivedOptionsCount": 9,
            "derivedMethodsCountAsMigratedOperations": False,
        },
        "x-ti-authorization-boundary": {
            "openapiOverlayCreated": True,
            "routePromotionAuthorized": False,
            "productionSchemaExecutionAuthorized": False,
            "gatewayOrProxyChangeAuthorized": False,
            "productionCutoverAuthorized": False,
        },
    }


def render_document(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def main() -> int:
    args = parse_args()
    rendered = render_document(build_document())
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_bytes() != rendered:
            raise SystemExit(f"transaction-write OpenAPI drifted: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
