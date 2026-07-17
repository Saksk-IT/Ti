#!/usr/bin/env python3
"""Capture fixed-commit HTTP-boundary evidence for user-count aliases.

This tool is deliberately descriptive.  It executes the archived Flask stack
through its test client, but it does not authorize a Java controller, security
matcher, route delta, OpenAPI delta, or production cutover.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from importlib import metadata
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Optional
from urllib.parse import urlencode


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
CAPTURE_TEST = TOOLS_DIR / (
    "test_capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py"
)
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_user_counts_goldens as golden  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
FIXED_REQUEST_ID = "phase4c-personal-bank-user-counts-http-boundary-request"
ROUTES = golden.ROUTES
OWNER_BANK_ID = golden.BANKS["owner_active"]
ALLOWED_CORS_ORIGIN = "https://servicewechat.com"
REJECTED_CORS_ORIGIN = "https://untrusted.invalid"
CORS_PREFLIGHT_METHOD = "GET"
CORS_PREFLIGHT_HEADERS = "Content-Type, Authorization, X-Request-ID"
SELECTED_KEY_SOURCES = (
    "requirements.txt",
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/modules/user_bank/__init__.py",
    "app/modules/user_bank/routes/api_base.py",
    "app/modules/user_bank/routes/api_quiz.py",
)
HELPER_PATHS = (
    TOOLS_DIR / "capture_phase4a_public_bank_goldens.py",
    TOOLS_DIR / "capture_phase4b_personal_bank_share_list_goldens.py",
    TOOLS_DIR / "capture_phase4b_personal_bank_user_counts_goldens.py",
)


@dataclass(frozen=True)
class BoundaryCase:
    case_id: str
    category: str
    route: str
    method: str = "GET"
    bank_segment: str = str(OWNER_BANK_ID)
    session_actor: Optional[str] = "owner"
    bearer_actor: Optional[str] = None
    invalid_bearer: bool = False
    accept: str = "*/*"
    query: tuple[tuple[str, str], ...] = ()
    tag_fixture: str = "none"
    origin: Optional[str] = None
    access_control_request_method: Optional[str] = None
    access_control_request_headers: Optional[str] = None


def arabic_indic(value: int) -> str:
    return str(value).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def fullwidth_digits(value: int) -> str:
    return str(value).translate(str.maketrans("0123456789", "０１２３４５６７８９"))


def percent_encoded_ascii_digits(value: int) -> str:
    return "".join(f"%{ord(character):02X}" for character in str(value))


def build_case_specs() -> tuple[BoundaryCase, ...]:
    cases: list[BoundaryCase] = []
    for route in ROUTES:
        cases.extend((
            BoundaryCase(f"auth-session-{route}", "authentication", route),
            BoundaryCase(
                f"auth-bearer-{route}", "authentication", route,
                session_actor=None, bearer_actor="owner",
            ),
            BoundaryCase(
                f"auth-invalid-bearer-with-session-{route}",
                "authentication", route, invalid_bearer=True,
            ),
            BoundaryCase(
                f"auth-invalid-bearer-only-{route}",
                "authentication", route, session_actor=None,
                invalid_bearer=True,
            ),
            BoundaryCase(
                f"auth-anonymous-{route}", "authentication", route,
                session_actor=None,
            ),
        ))

        for name, segment in (
            ("zero", "0"),
            ("leading-zero", f"000{OWNER_BANK_ID}"),
            ("unicode-nd-arabic-indic", arabic_indic(OWNER_BANK_ID)),
            ("unicode-nd-fullwidth", fullwidth_digits(OWNER_BANK_ID)),
            ("negative", "-1"),
            ("nondigit", "not-a-bank"),
            ("encoded-ascii-digits", percent_encoded_ascii_digits(OWNER_BANK_ID)),
            ("encoded-slash", f"%2F{OWNER_BANK_ID}"),
            ("matrix", f"{OWNER_BANK_ID};role=owner"),
            ("int-overflow", "2147483648"),
            ("long-overflow", "9223372036854775808"),
        ):
            cases.append(BoundaryCase(
                f"path-{name}-{route}", "path", route,
                bank_segment=segment,
            ))

        cases.extend((
            BoundaryCase(
                f"query-duplicate-q-type-{route}", "query", route,
                query=(("q_type", "选择题"), ("q_type", "简答题")),
            ),
            BoundaryCase(
                f"query-duplicate-source-{route}", "query", route,
                query=(("source", "favorites"), ("source", "mistakes")),
            ),
            BoundaryCase(
                f"query-duplicate-tag-{route}", "query", route,
                query=(("tag", "all"), ("tag", "重点")),
                tag_fixture="normalized",
            ),
        ))

        for failure, segment in (
            ("404", "not-a-bank"),
            ("long-overflow-500", "9223372036854775808"),
        ):
            for media, accept in (
                ("html", "text/html"),
                ("json", "application/json"),
            ):
                cases.append(BoundaryCase(
                    f"negotiation-{failure}-{media}-{route}",
                    "negotiation", route, bank_segment=segment, accept=accept,
                ))

        for method in ("HEAD", "OPTIONS"):
            cases.extend((
                BoundaryCase(
                    f"method-{method.lower()}-session-{route}",
                    "method", route, method=method,
                ),
                BoundaryCase(
                    f"method-{method.lower()}-anonymous-{route}",
                    "method", route, method=method, session_actor=None,
                ),
            ))

        for disposition, origin in (
            ("allowed", ALLOWED_CORS_ORIGIN),
            ("rejected", REJECTED_CORS_ORIGIN),
        ):
            cases.extend((
                BoundaryCase(
                    f"cors-get-{disposition}-origin-{route}",
                    "cors", route, origin=origin,
                ),
                BoundaryCase(
                    f"cors-preflight-{disposition}-origin-{route}",
                    "cors", route, method="OPTIONS", session_actor=None,
                    origin=origin,
                    access_control_request_method=CORS_PREFLIGHT_METHOD,
                    access_control_request_headers=CORS_PREFLIGHT_HEADERS,
                ),
            ))
    return tuple(cases)


CASE_SPECS = build_case_specs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


canonical_json = golden.canonical_json
sha256_json = golden.sha256_json
document_payload_sha256 = golden.document_payload_sha256
render_document = golden.render_document


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def credential_mode(spec: BoundaryCase) -> str:
    if spec.invalid_bearer and spec.session_actor is not None:
        return "session+invalid_bearer"
    if spec.invalid_bearer:
        return "invalid_bearer_only"
    if spec.bearer_actor is not None and spec.session_actor is not None:
        return "session+valid_bearer"
    if spec.bearer_actor is not None:
        return "valid_bearer_only"
    if spec.session_actor is not None:
        return "session"
    return "anonymous"


def recorded_headers(spec: BoundaryCase) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer <redacted-invalid-synthetic-jwt>"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    if spec.origin is not None:
        result["Origin"] = spec.origin
    if spec.access_control_request_method is not None:
        result["Access-Control-Request-Method"] = spec.access_control_request_method
    if spec.access_control_request_headers is not None:
        result["Access-Control-Request-Headers"] = spec.access_control_request_headers
    return result


def live_headers(spec: BoundaryCase, tokens: dict[str, str]) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer synthetic-invalid-token"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer " + tokens[spec.bearer_actor]
    if spec.origin is not None:
        result["Origin"] = spec.origin
    if spec.access_control_request_method is not None:
        result["Access-Control-Request-Method"] = spec.access_control_request_method
    if spec.access_control_request_headers is not None:
        result["Access-Control-Request-Headers"] = spec.access_control_request_headers
    return result


def normalize_token_header(value: str) -> str:
    return ", ".join(sorted({part.strip() for part in value.split(",") if part.strip()}))


def normalized_response(response: Any) -> dict[str, Any]:
    raw = response.get_data()
    payload = response.get_json(silent=True)
    headers: dict[str, list[str]] = {}
    selected = {
        "access-control-allow-credentials", "access-control-allow-headers",
        "access-control-allow-methods", "access-control-allow-origin",
        "access-control-expose-headers", "access-control-max-age",
        "allow", "content-length", "content-type", "location", "set-cookie",
        "vary", "x-request-id", "x-ratelimit-limit", "x-ratelimit-remaining",
        "x-ratelimit-reset", "retry-after",
    }
    for name in sorted(set(response.headers.keys()), key=str.lower):
        if name.lower() not in selected:
            continue
        values = response.headers.getlist(name)
        if name.lower() == "set-cookie":
            values = ["<redacted-session-cookie>" for _value in values]
        elif name.lower() in {
            "access-control-allow-headers", "access-control-allow-methods",
            "access-control-expose-headers", "allow", "vary",
        }:
            values = [normalize_token_header(value) for value in values]
        elif name.lower() == "x-ratelimit-remaining":
            values = ["<dynamic-counter>" for _value in values]
        elif name.lower() == "x-ratelimit-reset":
            values = ["<dynamic-epoch-second>" for _value in values]
        elif name.lower() == "retry-after":
            values = ["<dynamic-positive-seconds>" for _value in values]
        headers[name] = values
    return {
        "status": response.status_code,
        "headers": headers,
        "body_kind": "json" if payload is not None else "text",
        "body": golden.normalized_value(payload) if payload is not None else raw.decode(
            "utf-8", errors="replace"
        ),
        "body_length_bytes": len(raw),
        "body_sha256": hashlib.sha256(raw).hexdigest(),
    }


def compact_sql_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    raw_attempts = ledger["raw_connection_execute_attempts"]
    return {
        "statement_count": ledger["statement_count"],
        "select_attempts": ledger["select_attempts"],
        "dml_attempts": ledger["dml_attempts"],
        "ddl_attempts": ledger["ddl_attempts"],
        "business_table_dml_attempt_count": ledger["business_table_dml_attempt_count"],
        "user_last_active_dml_attempts": ledger["user_last_active_dml_attempts"],
        "classification_attempts": dict(sorted(
            ledger["classification_attempts"].items()
        )),
        "personal_bank_query_sequence": ledger["personal_bank_query_sequence"],
        "raw_connection_execute_attempt_count": len(raw_attempts),
        "raw_connection_classifications": [
            item["classification"] for item in raw_attempts
        ],
        "statements_sha256": ledger["statements_sha256"],
        "raw_connection_execute_attempts_sha256": ledger[
            "raw_connection_execute_attempts_sha256"
        ],
    }


def request_target(spec: BoundaryCase) -> tuple[str, str, str]:
    route = ROUTES[spec.route]
    path = route["path_template"].format(bank_id=spec.bank_segment)
    query_string = urlencode(spec.query)
    return path, query_string, path + ("?" + query_string if query_string else "")


def install_request_observer(app: Any, active: dict[str, Any]) -> None:
    from flask import request

    def observe_before_request() -> None:
        slot = active.get("slot")
        if slot is None:
            return
        slot["flask"] = {
            "method": request.method,
            "path": request.path,
            "full_path": request.full_path,
            "endpoint": request.endpoint,
            "matched_rule": None if request.url_rule is None else str(request.url_rule),
            "view_args": golden.normalized_value(request.view_args or {}),
            "query_items": [list(item) for item in request.args.items(multi=True)],
            "origin": request.headers.get("Origin"),
            "access_control_request_method": request.headers.get(
                "Access-Control-Request-Method"
            ),
            "access_control_request_headers": request.headers.get(
                "Access-Control-Request-Headers"
            ),
        }

    app.before_request_funcs.setdefault(None, []).insert(0, observe_before_request)
    original_wsgi_app = app.wsgi_app

    def observe_wsgi(environ: dict[str, Any], start_response: Any) -> Any:
        slot = active.get("slot")
        if slot is not None:
            slot["wsgi"] = {
                "request_method": environ.get("REQUEST_METHOD"),
                "script_name": environ.get("SCRIPT_NAME", ""),
                "path_info": environ.get("PATH_INFO"),
                "query_string": environ.get("QUERY_STRING"),
                "raw_uri": environ.get("RAW_URI"),
                "request_uri": environ.get("REQUEST_URI"),
            }
        return original_wsgi_app(environ, start_response)

    app.wsgi_app = observe_wsgi


def route_map_attestation(app: Any) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    for alias, route in ROUTES.items():
        rules = [rule for rule in app.url_map.iter_rules() if rule.endpoint == route["legacy_handler"]]
        expected_rule = route["route_template"]
        matches = [rule for rule in rules if str(rule) == expected_rule]
        if len(matches) != 1:
            raise AssertionError(f"route-map rule missing or duplicated: {alias}")
        rule = matches[0]
        converter = rule._converters["bank_id"]
        selected.append({
            "alias": alias,
            "route_id": route["route_id"],
            "rule": str(rule),
            "endpoint": rule.endpoint,
            "methods": sorted(rule.methods or ()),
            "arguments": sorted(rule.arguments),
            "strict_slashes": rule.strict_slashes,
            "merge_slashes": rule.merge_slashes,
            "converter": {
                "class": f"{type(converter).__module__}.{type(converter).__name__}",
                "regex": converter.regex,
                "signed": getattr(converter, "signed", None),
                "min": getattr(converter, "min", None),
                "max": getattr(converter, "max", None),
                "fixed_digits": getattr(converter, "fixed_digits", None),
            },
        })
    return {
        "selected_rules": selected,
        "selected_rules_sha256": sha256_json(selected),
        "attestation_scope": (
            "runtime Flask/Werkzeug route map from the complete fixed-commit app archive"
        ),
    }


def combined_business_fingerprint(db: Any) -> dict[str, Any]:
    details = {
        table: golden.table_fingerprint(db, table)
        for table in golden.BUSINESS_TABLES
    }
    return {"sha256": sha256_json(details), "tables": details}


def capture_case(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
    active: dict[str, Any],
    spec: BoundaryCase,
) -> dict[str, Any]:
    golden.set_actor_session(client, spec.session_actor)
    golden.reset_limiters(client.application)
    with client.application.app_context():
        golden.reset_case_facts(db, spec.tag_fixture)
        before = combined_business_fingerprint(db)
        identity_before = golden.user_identity_fingerprint(db)
        raw_activity_before, _activity_before = golden.user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()

    path, query_string, target = request_target(spec)
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    observed: dict[str, Any] = {}
    active["slot"] = observed
    probe_spec = golden.CaseSpec(
        case_id=spec.case_id,
        route=spec.route,
        session_actor=spec.session_actor,
        bearer_actor=spec.bearer_actor,
        invalid_bearer=spec.invalid_bearer,
        accept=spec.accept,
        query=spec.query,
        tag_fixture=spec.tag_fixture,
    )
    try:
        with golden.sql_probe(engine, probe_spec) as sql:
            response = client.open(
                target,
                method=spec.method,
                headers=live_headers(spec, tokens),
                environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
                follow_redirects=False,
            )
    finally:
        active["slot"] = None

    with client.application.app_context():
        try:
            db.session.rollback()
        finally:
            db.session.remove()
        after = combined_business_fingerprint(db)
        identity_after = golden.user_identity_fingerprint(db)
        raw_activity_after, _activity_after = golden.user_activity_snapshot(db)
        db.session.remove()
    changed_activity_ids = sorted(
        user_id for user_id in raw_activity_before
        if raw_activity_before[user_id] != raw_activity_after[user_id]
    )
    route = ROUTES[spec.route]
    return {
        "case_id": spec.case_id,
        "category": spec.category,
        "alias": spec.route,
        "route_id": route["route_id"],
        "credential_mode": credential_mode(spec),
        "request": {
            "method": spec.method,
            "input_path": path,
            "input_bank_segment": spec.bank_segment,
            "query": [list(item) for item in spec.query],
            "query_string": query_string,
            "target": target,
            "headers": recorded_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "request_observation": observed,
        "response": normalized_response(response),
        "effects": {
            "sql": compact_sql_ledger(sql),
            "business_fingerprint_before_sha256": before["sha256"],
            "business_fingerprint_after_sha256": after["sha256"],
            "business_tables_unchanged": before == after,
            "users_identity_unchanged": identity_before == identity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
        },
    }


def response_counts(case: dict[str, Any]) -> dict[str, Any]:
    body = case["response"]["body"]
    if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
        raise AssertionError(f"{case['case_id']} does not contain a count envelope")
    return body["data"]


def response_header(case: dict[str, Any], name: str) -> list[str]:
    return case["response"]["headers"].get(name, [])


def cors_case_summary(case: dict[str, Any]) -> dict[str, Any]:
    sql = case["effects"]["sql"]
    sequence = sql["personal_bank_query_sequence"]
    preflight = case["request"]["method"] == "OPTIONS" and bool(
        case["request"]["headers"].get("Access-Control-Request-Method")
    )
    response = case["response"]
    terminal_auth = (
        preflight
        and not sequence
        and (
            response["status"] == 401
            or (
                response["status"] == 302
                and response_header(case, "Location") == ["/login"]
            )
        )
    )
    return {
        "case_id": case["case_id"],
        "alias": case["alias"],
        "request": {
            "method": case["request"]["method"],
            "origin": case["request"]["headers"].get("Origin"),
            "access_control_request_method": case["request"]["headers"].get(
                "Access-Control-Request-Method"
            ),
            "access_control_request_headers": case["request"]["headers"].get(
                "Access-Control-Request-Headers"
            ),
            "credential_mode": case["credential_mode"],
        },
        "response": {
            "status": response["status"],
            "access_control_allow_origin": response_header(
                case, "Access-Control-Allow-Origin"
            ),
            "access_control_allow_headers": response_header(
                case, "Access-Control-Allow-Headers"
            ),
            "access_control_allow_methods": response_header(
                case, "Access-Control-Allow-Methods"
            ),
            "access_control_allow_credentials": response_header(
                case, "Access-Control-Allow-Credentials"
            ),
            "vary": response_header(case, "Vary"),
        },
        "execution": {
            "flask_route_matched": bool(
                case["request_observation"]["flask"]["matched_rule"]
            ),
            "terminal_global_auth_response_observed": terminal_auth,
            "terminal_global_auth_response_basis": (
                "exact 401 envelope or /login redirect plus the fixed app/__init__.py "
                "before-request source; no handler business query observed"
                if terminal_auth else None
            ),
            "session_authority_select_attempts": sql[
                "classification_attempts"
            ].get("users_select", 0),
            "last_active_write_attempts": sql["user_last_active_dml_attempts"],
            "last_active_changed_user_ids": case["effects"][
                "user_last_active_changed_user_ids"
            ],
            "handler_business_query_observed": bool(sequence),
            "personal_bank_business_query_sequence": sequence,
            "business_table_dml_attempt_count": sql[
                "business_table_dml_attempt_count"
            ],
        },
    }


@contextmanager
def fixed_cors_environment() -> Any:
    previous = os.environ.get("CORS_ALLOWED_ORIGINS")
    os.environ["CORS_ALLOWED_ORIGINS"] = ""
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        else:
            os.environ["CORS_ALLOWED_ORIGINS"] = previous


def assert_capture_contract(cases: list[dict[str, Any]], route_map: dict[str, Any]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(cases) != len(CASE_SPECS) or len(by_id) != len(CASE_SPECS):
        raise AssertionError("boundary case set is missing or duplicated")
    if any(not case["effects"]["business_tables_unchanged"] for case in cases):
        raise AssertionError("HTTP boundary capture changed a business table")
    if any(not case["effects"]["users_identity_unchanged"] for case in cases):
        raise AssertionError("HTTP boundary capture changed identity facts")
    for rule in route_map["selected_rules"]:
        if rule["methods"] != ["GET", "HEAD", "OPTIONS"]:
            raise AssertionError(f"unexpected derived methods: {rule}")

    for route in ROUTES:
        expected_auth = {
            f"auth-session-{route}": 200,
            f"auth-bearer-{route}": 200 if route == "api-alias" else 302,
            f"auth-invalid-bearer-with-session-{route}": 200,
            f"auth-invalid-bearer-only-{route}": 401 if route == "api-alias" else 302,
            f"auth-anonymous-{route}": 401 if route == "api-alias" else 302,
        }
        for case_id, status in expected_auth.items():
            if by_id[case_id]["response"]["status"] != status:
                raise AssertionError(f"{case_id} authentication status drifted")

        path_status = {
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
        for name, status in path_status.items():
            case_id = f"path-{name}-{route}"
            if by_id[case_id]["response"]["status"] != status:
                raise AssertionError(
                    f"{case_id} path status drifted: "
                    f"{by_id[case_id]['response']['status']}"
                )

        q_type = response_counts(by_id[f"query-duplicate-q-type-{route}"])
        if (q_type["total"], q_type["favorites"], q_type["mistakes"]) != (2, 2, 0):
            raise AssertionError(f"duplicate q_type first-value behavior drifted: {route}")
        source = response_counts(by_id[f"query-duplicate-source-{route}"])
        if (source["total"], source["favorites"], source["mistakes"]) != (5, 5, 3):
            raise AssertionError(f"duplicate source first-value behavior drifted: {route}")
        if response_counts(by_id[f"query-duplicate-tag-{route}"]) != golden.BASE_COUNTS:
            raise AssertionError(f"duplicate tag first-value behavior drifted: {route}")

        for media in ("html", "json"):
            not_found = by_id[f"negotiation-404-{media}-{route}"]
            overflow = by_id[f"negotiation-long-overflow-500-{media}-{route}"]
            if not_found["response"]["status"] != 404:
                raise AssertionError("404 negotiation status drifted")
            if overflow["response"]["status"] != 500:
                raise AssertionError("overflow negotiation status drifted")
            expected_kind = "json" if route == "api-alias" or media == "json" else "text"
            if not_found["response"]["body_kind"] != expected_kind:
                raise AssertionError("404 negotiation media drifted")
            if overflow["response"]["body_kind"] != expected_kind:
                raise AssertionError("overflow negotiation media drifted")

        head = by_id[f"method-head-session-{route}"]
        if head["response"]["status"] != 200 or head["response"]["body_length_bytes"] != 0:
            raise AssertionError(f"authenticated HEAD drifted: {route}")
        options = by_id[f"method-options-session-{route}"]
        allow = options["response"]["headers"].get("Allow", [])
        if options["response"]["status"] != 200 or allow != ["GET, HEAD, OPTIONS"]:
            raise AssertionError(f"authenticated OPTIONS drifted: {route}")
        if options["effects"]["sql"]["personal_bank_query_sequence"]:
            raise AssertionError(f"automatic OPTIONS entered handler: {route}")
        expected_anon = 401 if route == "api-alias" else 302
        for method in ("head", "options"):
            if by_id[f"method-{method}-anonymous-{route}"]["response"]["status"] != expected_anon:
                raise AssertionError(f"anonymous {method} drifted: {route}")

        expected_sequence = [
            "personal_bank_user_counts_bank_access_probe",
            "personal_bank_user_counts_total_all",
            "personal_bank_user_counts_favorites_count",
            "personal_bank_user_counts_mistakes_count",
            "personal_bank_user_counts_types_all",
        ]
        for disposition in ("allowed", "rejected"):
            cors_get = by_id[f"cors-get-{disposition}-origin-{route}"]
            if cors_get["response"]["status"] != 200:
                raise AssertionError(f"CORS GET status drifted: {route}/{disposition}")
            if cors_get["effects"]["sql"]["personal_bank_query_sequence"] != expected_sequence:
                raise AssertionError(f"CORS GET handler sequence drifted: {route}/{disposition}")
            if cors_get["effects"]["user_last_active_changed_user_ids"] != [
                golden.ACTORS["owner"]
            ]:
                raise AssertionError(f"CORS GET Session activity drifted: {route}/{disposition}")

            preflight = by_id[f"cors-preflight-{disposition}-origin-{route}"]
            expected_preflight_status = 401 if route == "api-alias" else 302
            if preflight["response"]["status"] != expected_preflight_status:
                raise AssertionError(f"CORS preflight auth status drifted: {route}/{disposition}")
            if preflight["effects"]["sql"]["personal_bank_query_sequence"]:
                raise AssertionError(f"CORS preflight entered handler: {route}/{disposition}")
            if preflight["effects"]["user_last_active_changed_user_ids"]:
                raise AssertionError(f"CORS preflight changed activity: {route}/{disposition}")
            observed = preflight["request_observation"]["flask"]
            if (
                observed["origin"]
                != (ALLOWED_CORS_ORIGIN if disposition == "allowed" else REJECTED_CORS_ORIGIN)
                or observed["access_control_request_method"] != CORS_PREFLIGHT_METHOD
                or observed["access_control_request_headers"] != CORS_PREFLIGHT_HEADERS
            ):
                raise AssertionError(f"CORS preflight request headers drifted: {route}/{disposition}")

        api = route == "api-alias"
        allowed_get = by_id[f"cors-get-allowed-origin-{route}"]
        rejected_get = by_id[f"cors-get-rejected-origin-{route}"]
        allowed_preflight = by_id[f"cors-preflight-allowed-origin-{route}"]
        rejected_preflight = by_id[f"cors-preflight-rejected-origin-{route}"]
        expected_allowed_origin = [ALLOWED_CORS_ORIGIN] if api else []
        if response_header(allowed_get, "Access-Control-Allow-Origin") != expected_allowed_origin:
            raise AssertionError(f"CORS GET ACAO drifted: {route}")
        if response_header(rejected_get, "Access-Control-Allow-Origin"):
            raise AssertionError(f"rejected CORS GET emitted ACAO: {route}")
        if response_header(allowed_preflight, "Access-Control-Allow-Origin") != expected_allowed_origin:
            raise AssertionError(f"CORS preflight ACAO drifted: {route}")
        if response_header(rejected_preflight, "Access-Control-Allow-Origin"):
            raise AssertionError(f"rejected CORS preflight emitted ACAO: {route}")
        expected_allow_headers = ["Authorization, Content-Type"] if api else []
        expected_allow_methods = ["DELETE, GET, OPTIONS, POST, PUT"] if api else []
        if response_header(
            allowed_preflight, "Access-Control-Allow-Headers"
        ) != expected_allow_headers:
            raise AssertionError(f"CORS preflight ACAH drifted: {route}")
        if response_header(
            allowed_preflight, "Access-Control-Allow-Methods"
        ) != expected_allow_methods:
            raise AssertionError(f"CORS preflight ACAM drifted: {route}")
        for case in (allowed_get, rejected_get, allowed_preflight, rejected_preflight):
            if response_header(case, "Access-Control-Allow-Credentials"):
                raise AssertionError(f"CORS credentials header unexpectedly emitted: {case['case_id']}")


def source_attestation(archived: Any, legacy_root: Path) -> dict[str, Any]:
    complete = golden.key_source_attestation(archived, legacy_root)
    return {
        "complete_app_archive": archived.attestation,
        "frozen_route_matrix": golden.matrix_attestation(),
        "key_sources": {path: complete[path] for path in SELECTED_KEY_SOURCES},
    }


def tool_provenance() -> dict[str, Any]:
    if not CAPTURE_TEST.is_file():
        raise AssertionError(f"boundary capture test missing: {CAPTURE_TEST}")
    helpers = {
        path.relative_to(TI_JAVA).as_posix(): sha256_file(path)
        for path in HELPER_PATHS
    }
    return {
        "capture_tool": {
            "path": "tools/capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "capture_test": {
            "path": "tools/test_capture_phase4c_personal_bank_user_counts_http_boundary_evidence.py",
            "sha256": sha256_file(CAPTURE_TEST),
        },
        "phase4_helpers": helpers,
        "runtime_versions": {
            "flask": metadata.version("Flask"),
            "werkzeug": metadata.version("Werkzeug"),
            "sqlalchemy": metadata.version("SQLAlchemy"),
            "flask_sqlalchemy": metadata.version("Flask-SQLAlchemy"),
            "flask_cors": metadata.version("Flask-Cors"),
        },
        "execution_model": (
            "complete app/ archive from the immutable legacy commit; isolated import; "
            "Flask/Werkzeug test client; temporary SQLite; fixed synthetic identities; "
            "fixed Beijing application clock; disabled rate limiter; explicitly empty "
            "CORS_ALLOWED_ORIGINS so only fixed source defaults and testing-debug origins apply"
        ),
        "redaction": {
            "authorization": "all valid and invalid JWT values are deterministic placeholders",
            "session_cookie": "every Set-Cookie value is replaced by a placeholder",
            "password_email_openid": "not serialized",
            "dynamic_activity_time": "only changed synthetic actor IDs are serialized",
            "rate_limit_counters": "disabled; any incidental dynamic values are placeholders",
        },
    }


def capture_document(legacy_root: Path) -> dict[str, Any]:
    if golden.LEGACY_COMMIT != LEGACY_COMMIT:
        raise AssertionError("Phase4B fixed-commit authority drifted")
    with golden.pinned_source.archived_legacy_source(legacy_root) as archived:
        source = source_attestation(archived, legacy_root)
        with fixed_cors_environment(), tempfile.TemporaryDirectory(
            prefix="ti-java-phase4c-user-counts-http-boundary-"
        ) as data_dir:
            with golden.capture_environment(data_dir):
                with golden.pinned_source.archived_legacy_import_environment(archived.root):
                    import app as legacy_app
                    from app.core.extensions import db
                    from app.core.utils.jwt_utils import generate_jwt_token
                    from app.models.user import User
                    from app.modules.user_bank.routes import api_base, api_quiz

                    golden.pinned_source.assert_module_from_archive(legacy_app, archived.root)
                    golden.pinned_source.assert_module_from_archive(api_base, archived.root)
                    golden.pinned_source.assert_module_from_archive(api_quiz, archived.root)
                    previous_logging = logging.root.manager.disable
                    original_now_bj = api_base.now_bj
                    logging.disable(logging.CRITICAL)
                    legacy_app._start_background_tasks = lambda _app: None
                    api_base.now_bj = lambda: golden.FIXED_NOW_BJ
                    app = legacy_app.create_app("testing")
                    app.config.update(
                        JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                        LAST_ACTIVE_UPDATE_INTERVAL_SECONDS=60,
                        PROPAGATE_EXCEPTIONS=False,
                        RATELIMIT_ENABLED=False,
                        TESTING=True,
                    )
                    active: dict[str, Any] = {"slot": None}
                    install_request_observer(app, active)
                    try:
                        route_map = route_map_attestation(app)
                        with app.app_context():
                            db.create_all()
                            golden.seed_static_actors(db, User)
                            golden.reset_case_facts(db, "none")
                            fixture = combined_business_fingerprint(db)
                            tokens = {
                                actor: generate_jwt_token(
                                    user_id=user_id,
                                    openid="",
                                    session_version=11,
                                )
                                for actor, user_id in golden.ACTORS.items()
                            }
                            db.session.remove()
                        client = app.test_client()
                        cases = [
                            capture_case(client, db, legacy_app, tokens, active, spec)
                            for spec in CASE_SPECS
                        ]
                        assert_capture_contract(cases, route_map)
                    finally:
                        api_base.now_bj = original_now_bj
                        logging.disable(previous_logging)
                        with app.app_context():
                            db.session.remove()

        provenance = tool_provenance()
        cors_observations = [
            cors_case_summary(case) for case in cases if case["category"] == "cors"
        ]
        document: dict[str, Any] = {
            "contract_id": "ti.phase4c.personal-bank-user-counts-http-boundary-evidence",
            "schema_version": 1,
            "status": "fixed_legacy_observation_only_future_http_entry_gate_open",
            "captured_at": "2026-07-17",
            "legacy_commit": LEGACY_COMMIT,
            "scope": (
                "dual-alias-auth-path-parameter-negotiation-method-and-cors-boundary"
            ),
            "legacy_source_attestation": source,
            "runtime_route_map": route_map,
            "provenance": provenance,
            "cors_runtime_evidence": {
                "evidence_class": (
                    "in-process fixed-commit Flask-CORS response-hook observation only"
                ),
                "fixed_source_configuration": {
                    "source": "app/core/extensions.py",
                    "sha256": source["key_sources"]["app/core/extensions.py"]["sha256"],
                    "resource_pattern": "/api/*",
                    "source_default_origin": ALLOWED_CORS_ORIGIN,
                    "capture_extra_origins_environment": "explicitly empty",
                    "testing_debug_origins_also_configured_by_fixed_source": [
                        "http://localhost:5000",
                        "http://127.0.0.1:5000",
                        "http://localhost:3000",
                        "http://127.0.0.1:3000",
                    ],
                    "configured_methods": [
                        "GET", "POST", "PUT", "DELETE", "OPTIONS"
                    ],
                    "configured_allow_headers": [
                        "Content-Type", "Authorization"
                    ],
                    "configured_supports_credentials": False,
                },
                "selected_allowed_origin": ALLOWED_CORS_ORIGIN,
                "selected_rejected_origin": REJECTED_CORS_ORIGIN,
                "preflight_request": {
                    "access_control_request_method": CORS_PREFLIGHT_METHOD,
                    "access_control_request_headers": CORS_PREFLIGHT_HEADERS,
                },
                "observation_count": len(cors_observations),
                "observations_sha256": sha256_json(cors_observations),
                "observations": cors_observations,
                "interpretation_boundary": {
                    "server_headers_and_app_execution_observed": True,
                    "browser_cors_enforcement_observed": False,
                    "reverse_proxy_header_preservation_observed": False,
                    "future_allowed_origins_authorized": False,
                    "future_credentials_policy_authorized": False,
                    "future_preflight_auth_order_authorized": False,
                },
            },
            "route_state": {
                "operations": [
                    {
                        "alias": alias,
                        "route_id": route["route_id"],
                        "path": route["route_template"],
                        "legacy_handler": route["legacy_handler"],
                        "reviewed_http_owner": "learning",
                        "migration_status": "pending",
                        "production_cutover": False,
                    }
                    for alias, route in ROUTES.items()
                ],
                "controller_added_by_this_evidence": False,
                "security_matcher_added_by_this_evidence": False,
                "route_or_openapi_delta": False,
                "production_cutover": False,
            },
            "observation_and_target_separation": {
                "legacy_observations_are_descriptive_not_normative": True,
                "observed_legacy_stack": {
                    "authentication": (
                        "API alias accepts valid bearer-only; Web alias redirects bearer-only; "
                        "a malformed bearer falls back to a valid Session on both aliases; "
                        "anonymous and invalid-bearer-only are API 401 or Web /login redirect"
                    ),
                    "path_converter": (
                        "the pinned Werkzeug integer converter accepts leading zeroes, Unicode Nd "
                        "and percent-decoded ASCII digits; negative, nondigit and semicolon matrix "
                        "segments do not match; Python integers exceed Java int/long ranges"
                    ),
                    "duplicate_parameters": (
                        "request.args.get consumes the first q_type, source and tag value"
                    ),
                    "negotiation": (
                        "an /api-prefixed failure is JSON regardless of text/html; Web failures "
                        "are HTML unless Accept starts with application/json"
                    ),
                    "derived_methods": (
                        "GET registration derives HEAD and automatic OPTIONS; before-request "
                        "authentication still applies; authenticated HEAD enters GET behavior with "
                        "an empty response body while automatic OPTIONS does not enter the handler"
                    ),
                    "cors": (
                        "with an explicit allowed Origin, only the /api alias receives Flask-CORS "
                        "headers; rejected origins and the /user alias receive none. Session GETs "
                        "still authenticate and enter the handler regardless of Origin. Anonymous "
                        "preflights terminate at the global API 401 or Web /login redirect before "
                        "handler SQL; the allowed API preflight is nevertheless decorated with "
                        "ACAO, the configured methods, and only Authorization/Content-Type from the "
                        "three requested headers. No credentials header is emitted"
                    ),
                },
                "cors_policy_decision": {
                    "status": "not_proposed_or_authorized_by_this_evidence",
                    "open_dimensions": [
                        "future allowed and rejected origin set",
                        "whether either alias participates in cross-origin access",
                        "credential support and browser cookie behavior",
                        "preflight authentication/filter ordering and response status",
                        "allowed request headers including X-Request-ID",
                        "allowed methods, Vary behavior and ingress header preservation",
                    ],
                },
                "future_security_targets_and_open_decisions": [
                    {
                        "id": "authoritative-identity",
                        "kind": "required_target",
                        "requirement": (
                            "authenticate only an authoritative server Session or verified bearer; "
                            "never trust identity/role headers; preserve immediate session_version "
                            "and lock revocation"
                        ),
                        "source": "docs/refactor/adr/0005-authentication-transition.md",
                        "proved_by_this_capture": False,
                    },
                    {
                        "id": "invalid-bearer-with-session",
                        "kind": "entry_contract_decision_required",
                        "requirement": (
                            "explicitly accept or reject the observed malformed-bearer Session "
                            "fallback; do not inherit it accidentally from filter ordering"
                        ),
                        "proved_by_this_capture": False,
                    },
                    {
                        "id": "matrix-path",
                        "kind": "approved_security_target",
                        "requirement": (
                            "StrictHttpFirewall rejects semicolon ambiguity with safe 400 before "
                            "MVC/controller and business calls"
                        ),
                        "source": "docs/refactor/phase4a/approved-differences.md#P4A-CATALOG-009",
                        "proved_by_this_capture": False,
                    },
                    {
                        "id": "numeric-domain",
                        "kind": "entry_contract_decision_required",
                        "requirement": (
                            "define Unicode/leading-zero compatibility and int/long overflow status "
                            "before binding the Java int bank ID; malformed or overflow input must "
                            "not reach the learning application API"
                        ),
                        "proved_by_this_capture": False,
                    },
                    {
                        "id": "parameter-pollution",
                        "kind": "required_target",
                        "requirement": (
                            "preserve the fixed first-value q_type/source/tag rule unless an approved "
                            "difference replaces it; cover ordered duplicates in HTTP tests"
                        ),
                        "proved_by_this_capture": False,
                    },
                    {
                        "id": "head-options",
                        "kind": "required_target",
                        "requirement": (
                            "HEAD and OPTIONS must use the intended alias authorization policy; HEAD "
                            "must emit no body and OPTIONS must not invoke the learning use case"
                        ),
                        "proved_by_this_capture": False,
                    },
                    {
                        "id": "safe-error-negotiation",
                        "kind": "required_target",
                        "requirement": (
                            "fix API/Web media and status behavior for converter, authentication and "
                            "overflow failures without leaking exception, credential or SQL text"
                        ),
                        "proved_by_this_capture": False,
                    },
                ],
                "non_authorizations": [
                    "Java HTTP controller implementation",
                    "Spring Security or rate-limit implementation",
                    "future CORS origin/header/method/credentials policy",
                    "route or OpenAPI migration delta",
                    "production schema or index change",
                    "operator migration execution",
                    "production cutover",
                ],
            },
            "evidence_gaps": [
                {
                    "id": "socket-and-reverse-proxy-raw-target",
                    "gap": (
                        "Flask test_client supplies a synthetic WSGI environ; RAW_URI/REQUEST_URI "
                        "show Werkzeug test transport only, not an ingress/reverse-proxy byte path"
                    ),
                    "compensating_attestation": (
                        "fixed requirements source plus runtime converter/route-map attestation; "
                        "future socket/proxy HTTP tests remain required"
                    ),
                },
                {
                    "id": "browser-cors-enforcement-and-cookie-credentials",
                    "gap": (
                        "Flask test_client does not enforce the browser same-origin policy or "
                        "preflight decision and deliberately sends its synthetic Session cookie on "
                        "the Origin GET cases even though supports_credentials is false"
                    ),
                    "compensating_attestation": (
                        "the evidence reports only application response headers and server-side "
                        "execution; it does not claim that a browser exposes the response or sends "
                        "the same credentials"
                    ),
                },
                {
                    "id": "reverse-proxy-cors-header-preservation",
                    "gap": (
                        "no ingress or reverse proxy participates, so header injection, stripping, "
                        "merging, caching and Origin normalization outside Flask are not observed"
                    ),
                    "compensating_attestation": (
                        "the fixed Flask-CORS source hash and in-process response headers establish "
                        "only the archived application layer; proxy/runtime evidence remains open"
                    ),
                },
                {
                    "id": "future-java-filter-and-binding-order",
                    "gap": (
                        "the legacy capture cannot observe StrictHttpFirewall, Spring Security, MVC "
                        "PathPattern, Java numeric binding, controller advice or learning calls"
                    ),
                    "compensating_attestation": (
                        "fixed legacy source and both frozen route-map rows only establish the old "
                        "boundary; the future entry contract must add Java HTTP tests"
                    ),
                },
                {
                    "id": "production-database-and-network",
                    "gap": (
                        "temporary SQLite and an in-process client are used; no PostgreSQL, TLS, "
                        "gateway timeout or production rate limiter is observed"
                    ),
                    "compensating_attestation": (
                        "this evidence makes no claim for those layers and does not supersede their "
                        "existing Phase 3/4 contracts"
                    ),
                },
            ],
            "coverage": {
                "aliases": sorted(ROUTES),
                "credential_modes": sorted({credential_mode(spec) for spec in CASE_SPECS}),
                "path_dimensions": [
                    "zero", "leading-zero", "unicode-nd-arabic-indic",
                    "unicode-nd-fullwidth", "negative", "nondigit",
                    "encoded-ascii-digits", "encoded-slash", "matrix",
                    "int-overflow", "long-overflow",
                ],
                "duplicate_query_keys": ["q_type", "source", "tag"],
                "accept_values": ["text/html", "application/json"],
                "methods": ["GET", "HEAD", "OPTIONS"],
                "cors": {
                    "origins": [ALLOWED_CORS_ORIGIN, REJECTED_CORS_ORIGIN],
                    "get_aliases": sorted(ROUTES),
                    "preflight_aliases": sorted(ROUTES),
                    "access_control_request_method": CORS_PREFLIGHT_METHOD,
                    "access_control_request_headers": CORS_PREFLIGHT_HEADERS,
                },
                "category_case_counts": {
                    category: sum(spec.category == category for spec in CASE_SPECS)
                    for category in sorted({spec.category for spec in CASE_SPECS})
                },
            },
            "fixture": {
                "synthetic_owner_actor_id": golden.ACTORS["owner"],
                "synthetic_owner_bank_id": OWNER_BANK_ID,
                "business_table_count": len(golden.BUSINESS_TABLES),
                "business_fixture_sha256": fixture["sha256"],
            },
            "case_count": len(cases),
            "case_payload_sha256": sha256_json(cases),
            "cases": cases,
        }
        document["provenance"]["hashes"] = {
            "case_payload_sha256": document["case_payload_sha256"],
            "runtime_route_map_sha256": route_map["selected_rules_sha256"],
            "capture_tool_sha256": provenance["capture_tool"]["sha256"],
            "capture_test_sha256": provenance["capture_test"]["sha256"],
            "selected_key_sources_sha256": sha256_json(source["key_sources"]),
            "helper_manifest_sha256": sha256_json(provenance["phase4_helpers"]),
            "cors_observations_sha256": document["cors_runtime_evidence"][
                "observations_sha256"
            ],
        }
        document["document_payload_sha256"] = document_payload_sha256(document)
        return document


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        f"captured {document['case_count']} HTTP boundary cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
