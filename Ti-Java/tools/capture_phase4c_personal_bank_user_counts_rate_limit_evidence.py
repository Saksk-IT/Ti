#!/usr/bin/env python3
"""Capture fixed-commit rate-limit evidence for personal-bank user counts.

The capture deliberately separates immutable legacy source facts, runtime
observations made through the real Flask routes, and an unimplemented target
proposal.  Production-effective limits are not inferred from the base config.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import contextmanager
import hashlib
from importlib import metadata
import json
import logging
from pathlib import Path
import platform
import re
import socket
import sys
import tempfile
from typing import Any, Callable, Iterator


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
CAPTURE_TEST = TOOLS_DIR / "test_capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_user_counts_goldens as counts  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
FIXED_CAPTURE_DATE = "2026-07-17"
MISSING_BANK_ID = 99999
OWNER_BANK_ID = counts.BANKS["owner_active"]
BASE_LIMITS = "5000 per day;500 per hour;10 per second"
PRODUCTION_DEFAULT_LIMITS = "500000/day;50000/hour;1000/second"
ROUTES = {
    "api-alias": {
        "route_id": "6858f6fa506f",
        "path": f"/api/user/banks/api/{MISSING_BANK_ID}/user-counts",
        "owner_bank_path": f"/api/user/banks/api/{OWNER_BANK_ID}/user-counts",
        "template": "/api/user/banks/api/<int:bank_id>/user-counts",
        "expected_endpoint": "user_bank_api_root.user_bank_api.get_user_counts",
    },
    "web-alias": {
        "route_id": "006913d0d956",
        "path": f"/user/banks/api/{MISSING_BANK_ID}/user-counts",
        "owner_bank_path": f"/user/banks/api/{OWNER_BANK_ID}/user-counts",
        "template": "/user/banks/api/<int:bank_id>/user-counts",
        "expected_endpoint": "user_bank.user_bank_api.get_user_counts",
    },
}
KEY_SOURCE_FILES = (
    "requirements.txt",
    ".env.example",
    "compose.prod.yml",
    "app/__init__.py",
    "app/core/config.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/rate_limit.py",
    "app/core/utils/rate_limit_policy.py",
    "app/modules/user_bank/__init__.py",
    "app/modules/user_bank/routes/api_base.py",
    "app/modules/user_bank/routes/api_quiz.py",
)
SUPPORT_FILES = (
    "capture_phase4a_public_bank_goldens.py",
    "capture_phase4b_personal_bank_category_goldens.py",
    "capture_phase4b_personal_bank_share_list_goldens.py",
    "capture_phase4b_personal_bank_user_counts_goldens.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return sha256_json(payload)


def render_document(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def read_fixed_blob(legacy_root: Path, archived: Any, path: str) -> bytes:
    archived_path = archived.root / path
    if archived_path.is_file():
        return archived_path.read_bytes()
    return counts.pinned_source._run_read_only_git(
        legacy_root,
        "show",
        f"{LEGACY_COMMIT}:{path}",
    )


def key_source_attestation(
    legacy_root: Path,
    archived: Any,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    object_format = archived.attestation["git_object_format"]
    attestations: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    for path in KEY_SOURCE_FILES:
        payload = read_fixed_blob(legacy_root, archived, path)
        sources[path] = payload.decode("utf-8")
        attestations[path] = {
            "git_blob": counts.pinned_source._git_blob_id(payload, object_format),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "transport": (
                "verified complete app/ archive"
                if path.startswith("app/")
                else "git show from verified fixed commit"
            ),
        }
    return attestations, sources


def _function_decorators(source: str, function_name: str) -> list[str]:
    tree = ast.parse(source)
    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(matches) != 1:
        raise AssertionError(f"fixed source must contain one {function_name} handler")
    return [ast.unparse(decorator) for decorator in matches[0].decorator_list]


def source_facts(sources: dict[str, str]) -> dict[str, Any]:
    config = sources["app/core/config.py"]
    extensions = sources["app/core/extensions.py"]
    rate_key = sources["app/core/utils/rate_limit.py"]
    policy = sources["app/core/utils/rate_limit_policy.py"]
    factory = sources["app/__init__.py"]
    module = sources["app/modules/user_bank/__init__.py"]
    handler = sources["app/modules/user_bank/routes/api_quiz.py"]
    compose = sources["compose.prod.yml"]
    requirements = sources["requirements.txt"]
    decorators = _function_decorators(handler, "get_user_counts")

    required_anchors = (
        (config, 'RATELIMIT_DEFAULT = "5000 per day;500 per hour;10 per second"'),
        (config, "RATELIMIT_HEADERS_ENABLED = True"),
        (config, "RATELIMIT_LIMIT_MULTIPLIER = production_rate_limit_multiplier()"),
        (config, "RATELIMIT_STORAGE_URI = REDIS_URL"),
        (extensions, "limiter = TiLimiter(key_func=user_or_ip_rate_key)"),
        (rate_key, 'return f"uid:{uid}"'),
        (rate_key, 'return f"ip:{_safe_client_ip()}"'),
        (policy, "_DEFAULT_PRODUCTION_MULTIPLIER = 100"),
        (factory, "RATELIMIT_STORAGE_URI 不能为 memory://"),
        (module, "api_root_bp.register_blueprint(user_bank_api_bp, url_prefix='/user/banks/api')"),
        (compose, 'RATELIMIT_DEFAULT: "${RATELIMIT_DEFAULT:-500000/day;50000/hour;1000/second}"'),
        (compose, "RATELIMIT_LIMIT_MULTIPLIER: ${RATELIMIT_LIMIT_MULTIPLIER:-100}"),
        (requirements, "Flask-Limiter==3.11.0"),
        (requirements, "limits==4.2"),
    )
    for source, anchor in required_anchors:
        if anchor not in source:
            raise AssertionError(f"fixed rate-limit source anchor drifted: {anchor}")
    expected_decorators = {
        "user_bank_api_bp.route('/<int:bank_id>/user-counts', methods=['GET'])",
        "auth_required",
    }
    if set(decorators) != expected_decorators:
        raise AssertionError(f"user-count handler decorators drifted: {decorators}")
    if any("limit" in decorator.lower() for decorator in decorators):
        raise AssertionError("user-count route unexpectedly gained a route limiter")

    return {
        "handler": {
            "source": "app/modules/user_bank/routes/api_quiz.py",
            "function": "get_user_counts",
            "decorators": decorators,
            "route_specific_limiter": False,
            "limiter_source": "application-wide RATELIMIT_DEFAULT",
        },
        "aliases": {
            "state": "one shared handler registered as two distinct Flask endpoints",
            "routes": ROUTES,
        },
        "base_configuration": {
            "value": BASE_LIMITS,
            "windows": [
                {"count": 10, "unit": "second"},
                {"count": 500, "unit": "hour"},
                {"count": 5000, "unit": "day"},
            ],
            "headers_enabled": True,
            "applies_to": "base Config and inherited development/testing config",
        },
        "production_configuration": {
            "default_multiplier": 100,
            "default_effective_value": PRODUCTION_DEFAULT_LIMITS,
            "compose_default_value": PRODUCTION_DEFAULT_LIMITS,
            "environment_override": "RATELIMIT_DEFAULT may replace the fallback",
            "base_values_are_not_fixed_commit_production_defaults": True,
            "redis_required": True,
            "memory_storage_rejected_when_not DEBUG or TESTING": True,
        },
        "key_resolution": {
            "priority": [
                "g.current_user_id",
                "Session user_id",
                "decoded optional Bearer JWT user_id",
                "request remote address",
            ],
            "authenticated_shape": "uid:<raw-user-id>",
            "anonymous_shape": "ip:<request-remote-address>",
            "raw_keys_captured": False,
            "proxy_note": (
                "get_remote_address reads request.remote_addr; production ProxyFix may rewrite it, "
                "but trusted-proxy behavior is outside this capture"
            ),
        },
        "library_pins": {
            "Flask-Limiter": "3.11.0",
            "limits": "4.2",
            "redis": ">=5.0.0,<6",
        },
    }


def limiter_runtime(app: Any) -> dict[str, Any]:
    installed = list(app.extensions.get("limiter", set()))
    if len(installed) != 1:
        raise AssertionError(f"expected one Flask limiter, observed {len(installed)}")
    limiter = installed[0]
    storage = getattr(limiter, "_storage", None)
    strategy = getattr(limiter, "_limiter", None)
    return {
        "configured_default": app.config.get("RATELIMIT_DEFAULT"),
        "headers_enabled": bool(app.config.get("RATELIMIT_HEADERS_ENABLED")),
        "storage_class": (
            f"{type(storage).__module__}.{type(storage).__name__}"
            if storage is not None else None
        ),
        "strategy_class": (
            f"{type(strategy).__module__}.{type(strategy).__name__}"
            if strategy is not None else None
        ),
    }


@contextmanager
def handler_probe(engine: Any) -> Iterator[dict[str, int]]:
    from sqlalchemy import event

    ledger = {"sql_statement_count": 0, "handler_bank_access_probe_count": 0}

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        _parameters: Any,
        _context: Any,
        _executemany: Any,
    ) -> None:
        normalized = counts.normalized_sql(statement)
        ledger["sql_statement_count"] += 1
        if (
            normalized.startswith("SELECT * FROM USER_QUESTION_BANKS")
            and "WHERE ID =" in normalized
            and "JOIN" not in normalized
        ):
            ledger["handler_bank_access_probe_count"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield ledger
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def recorded_response(response: Any) -> dict[str, Any]:
    normalized = counts.normalized_response(response)
    normalized["headers"] = {
        name: values
        for name, values in normalized["headers"].items()
        if name in {
            "Content-Type",
            "Content-Length",
            "Location",
            "Vary",
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        }
    }
    return normalized


def perform_request(
    client: Any,
    path: str,
    *,
    request_id: str,
    remote_address: str,
    accept: str = "application/json",
    bearer: str | None = None,
) -> Any:
    headers = {"Accept": accept, "X-Request-ID": request_id}
    if bearer is not None:
        headers["Authorization"] = "Bearer " + bearer
    return client.get(
        path,
        headers=headers,
        environ_overrides={"REMOTE_ADDR": remote_address},
        follow_redirects=False,
    )


def run_sequence(
    client: Any,
    engine: Any,
    *,
    path: str,
    attempts: int,
    request_id: str,
    remote_addresses: Callable[[int], str],
    accept: str = "application/json",
    bearer: str | None = None,
    sample_attempts: set[int] | None = None,
) -> dict[str, Any]:
    samples = sample_attempts or {1, attempts}
    statuses: list[int] = []
    captured: list[dict[str, Any]] = []
    with handler_probe(engine) as ledger:
        for attempt in range(1, attempts + 1):
            handler_before = ledger["handler_bank_access_probe_count"]
            sql_before = ledger["sql_statement_count"]
            response = perform_request(
                client,
                path,
                request_id=request_id,
                remote_address=remote_addresses(attempt),
                accept=accept,
                bearer=bearer,
            )
            statuses.append(response.status_code)
            if attempt in samples:
                captured.append({
                    "attempt": attempt,
                    "response": recorded_response(response),
                    "handler_bank_access_probe_delta": (
                        ledger["handler_bank_access_probe_count"] - handler_before
                    ),
                    "sql_statement_delta": ledger["sql_statement_count"] - sql_before,
                })
    return {
        "attempt_count": attempts,
        "status_counts": {
            str(status): count for status, count in sorted(Counter(statuses).items())
        },
        "status_sequence_sha256": sha256_json(statuses),
        "handler_bank_access_probe_count": ledger["handler_bank_access_probe_count"],
        "sql_statement_count": ledger["sql_statement_count"],
        "samples": captured,
    }


def _set_session_actor(client: Any, actor: str | None) -> None:
    counts.set_actor_session(client, actor)


def run_with_legacy_app(
    archive_root: Path,
    *,
    default_limit: str | None,
    storage_uri: str | None,
    seed_facts: bool,
    callback: Callable[[Any, Any, Any, dict[str, str]], dict[str, Any]],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="ti-java-phase4c-user-counts-rate-data-"
    ) as data_dir:
        with counts.capture_environment(data_dir):
            with counts.pinned_source.archived_legacy_import_environment(archive_root):
                import app as legacy_app
                from app.core.config import TestingConfig
                from app.core.extensions import db
                from app.core.utils.jwt_utils import generate_jwt_token
                from app.models.user import User

                counts.pinned_source.assert_module_from_archive(legacy_app, archive_root)
                if default_limit is not None:
                    TestingConfig.RATELIMIT_DEFAULT = default_limit
                if storage_uri is not None:
                    TestingConfig.RATELIMIT_STORAGE_URI = storage_uri
                    TestingConfig.RATELIMIT_STORAGE_URL = storage_uri
                previous_logging = logging.root.manager.disable
                logging.disable(logging.CRITICAL)
                legacy_app._start_background_tasks = lambda _app: None
                app = legacy_app.create_app("testing")
                app.config.update(
                    JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                    LAST_ACTIVE_UPDATE_INTERVAL_SECONDS=60,
                    PROPAGATE_EXCEPTIONS=False,
                    RATELIMIT_ENABLED=True,
                    TESTING=True,
                )
                try:
                    with app.app_context():
                        db.create_all()
                        counts.seed_static_actors(db, User)
                        if seed_facts:
                            counts.reset_case_facts(db, "none")
                        tokens = {
                            actor: generate_jwt_token(
                                user_id=counts.ACTORS[actor],
                                openid="",
                                session_version=11,
                            )
                            for actor in ("owner", "other")
                        }
                        engine = db.engine
                        db.session.remove()
                    client = app.test_client()
                    return callback(app, client, engine, tokens)
                finally:
                    with app.app_context():
                        db.session.remove()
                    logging.disable(previous_logging)


def capture_base_second_window(archive_root: Path) -> dict[str, Any]:
    def callback(app: Any, client: Any, engine: Any, _tokens: dict[str, str]) -> dict[str, Any]:
        _set_session_actor(client, "owner")
        counts.reset_limiters(app)
        sequence = run_sequence(
            client,
            engine,
            path=ROUTES["api-alias"]["path"],
            attempts=11,
            request_id="phase4c-user-counts-rate-10-second",
            remote_addresses=lambda attempt: f"198.51.100.{10 + attempt}",
            sample_attempts={1, 10, 11},
        )
        endpoints = {
            rule.rule: rule.endpoint
            for rule in app.url_map.iter_rules()
            if rule.rule in {route["template"] for route in ROUTES.values()}
        }
        return {
            "observation_kind": "fixed_commit_real_route_combined_base_config",
            "production_observation": False,
            "runtime": limiter_runtime(app),
            "registered_endpoints": endpoints,
            "route": "api-alias",
            "configured_limits": BASE_LIMITS,
            "isolated_window_override": None,
            "limit_under_test": "10 per second",
            "sequence": sequence,
        }

    return run_with_legacy_app(
        archive_root,
        default_limit=None,
        storage_uri=None,
        seed_facts=False,
        callback=callback,
    )


def capture_isolated_window(
    archive_root: Path,
    *,
    limit_value: str,
    limit: int,
    unit: str,
) -> dict[str, Any]:
    def callback(app: Any, client: Any, engine: Any, _tokens: dict[str, str]) -> dict[str, Any]:
        _set_session_actor(client, "owner")
        counts.reset_limiters(app)
        return {
            "observation_kind": "fixed_commit_real_route_single_window_diagnostic",
            "production_observation": False,
            "runtime": limiter_runtime(app),
            "route": "api-alias",
            "configured_limits": limit_value,
            "isolated_window_override": {
                "source_mutated": False,
                "runtime_config_override": f"RATELIMIT_DEFAULT={limit_value}",
                "purpose": (
                    "isolate this fixed-source clause because the combined 10/second "
                    "window otherwise masks a burst test of the longer window"
                ),
            },
            "limit_under_test": f"{limit} per {unit}",
            "sequence": run_sequence(
                client,
                engine,
                path=ROUTES["api-alias"]["path"],
                attempts=limit + 1,
                request_id=f"phase4c-user-counts-rate-{limit}-{unit}",
                remote_addresses=lambda _attempt: "198.51.100.70",
                sample_attempts={1, limit, limit + 1},
            ),
        }

    return run_with_legacy_app(
        archive_root,
        default_limit=limit_value,
        storage_uri=None,
        seed_facts=False,
        callback=callback,
    )


def capture_scope_and_identity(archive_root: Path) -> dict[str, Any]:
    diagnostic_limit = "10 per day"

    def callback(app: Any, client: Any, engine: Any, tokens: dict[str, str]) -> dict[str, Any]:
        api_path = ROUTES["api-alias"]["path"]
        web_path = ROUTES["web-alias"]["path"]

        _set_session_actor(client, "owner")
        counts.reset_limiters(app)
        api_first_ten = run_sequence(
            client,
            engine,
            path=api_path,
            attempts=10,
            request_id="phase4c-rate-alias-scope",
            remote_addresses=lambda _attempt: "198.51.100.80",
            sample_attempts={10},
        )
        web_first = perform_request(
            client,
            web_path,
            request_id="phase4c-rate-alias-scope",
            remote_address="198.51.100.80",
            accept="*/*",
        )
        api_breach = perform_request(
            client,
            api_path,
            request_id="phase4c-rate-alias-scope",
            remote_address="198.51.100.80",
        )
        web_tail = run_sequence(
            client,
            engine,
            path=web_path,
            attempts=10,
            request_id="phase4c-rate-alias-scope",
            remote_addresses=lambda _attempt: "198.51.100.80",
            accept="*/*",
            sample_attempts={9, 10},
        )

        counts.reset_limiters(app)
        _set_session_actor(client, "owner")
        web_json = run_sequence(
            client,
            engine,
            path=web_path,
            attempts=11,
            request_id="phase4c-rate-web-json",
            remote_addresses=lambda _attempt: "198.51.100.81",
            accept="application/json",
            sample_attempts={11},
        )

        counts.reset_limiters(app)
        _set_session_actor(client, "owner")
        session_ips = run_sequence(
            client,
            engine,
            path=api_path,
            attempts=11,
            request_id="phase4c-rate-session-across-ip",
            remote_addresses=lambda attempt: f"198.51.100.{90 + attempt}",
            sample_attempts={1, 10, 11},
        )

        counts.reset_limiters(app)
        _set_session_actor(client, None)
        anonymous_same_ip = run_sequence(
            client,
            engine,
            path=api_path,
            attempts=11,
            request_id="phase4c-rate-anonymous-ip",
            remote_addresses=lambda _attempt: "198.51.100.120",
            sample_attempts={1, 10, 11},
        )
        anonymous_other_ip = perform_request(
            client,
            api_path,
            request_id="phase4c-rate-anonymous-other-ip",
            remote_address="198.51.100.121",
        )

        counts.reset_limiters(app)
        _set_session_actor(client, "owner")
        owner_ten = run_sequence(
            client,
            engine,
            path=api_path,
            attempts=10,
            request_id="phase4c-rate-distinct-session",
            remote_addresses=lambda _attempt: "198.51.100.130",
            sample_attempts={10},
        )
        _set_session_actor(client, "other")
        other_first = perform_request(
            client,
            api_path,
            request_id="phase4c-rate-distinct-session",
            remote_address="198.51.100.130",
        )
        _set_session_actor(client, "owner")
        owner_breach = perform_request(
            client,
            api_path,
            request_id="phase4c-rate-distinct-session",
            remote_address="198.51.100.130",
        )

        counts.reset_limiters(app)
        _set_session_actor(client, "owner")
        conflict = run_sequence(
            client,
            engine,
            path=ROUTES["api-alias"]["owner_bank_path"],
            attempts=10,
            request_id="phase4c-rate-session-bearer-conflict",
            remote_addresses=lambda attempt: f"198.51.100.{140 + attempt}",
            bearer=tokens["other"],
            sample_attempts={1, 10},
        )
        session_after_conflict = perform_request(
            client,
            ROUTES["api-alias"]["owner_bank_path"],
            request_id="phase4c-rate-session-bearer-conflict",
            remote_address="198.51.100.151",
        )
        counts.reset_limiters(app)
        _set_session_actor(client, "owner")
        session_owner_baseline = perform_request(
            client,
            ROUTES["api-alias"]["owner_bank_path"],
            request_id="phase4c-rate-session-owner-baseline",
            remote_address="198.51.100.152",
        )

        counts.reset_limiters(app)
        _set_session_actor(client, None)
        bearer_ips = run_sequence(
            client,
            engine,
            path=ROUTES["api-alias"]["owner_bank_path"],
            attempts=11,
            request_id="phase4c-rate-bearer-across-ip",
            remote_addresses=lambda attempt: f"198.51.100.{160 + attempt}",
            bearer=tokens["owner"],
            sample_attempts={1, 10, 11},
        )

        return {
            "observation_kind": "fixed_commit_real_route_scope_and_key_diagnostic",
            "production_observation": False,
            "runtime": limiter_runtime(app),
            "isolated_window_override": {
                "source_mutated": False,
                "runtime_config_override": f"RATELIMIT_DEFAULT={diagnostic_limit}",
                "purpose": "avoid wall-clock rollover while proving endpoint and key scope",
            },
            "alias_buckets": {
                "result": "independent_per_registered_endpoint",
                "api_first_ten": api_first_ten,
                "web_attempt_one_after_api_exhaustion": recorded_response(web_first),
                "api_attempt_eleven": recorded_response(api_breach),
                "web_remaining_attempts_two_through_eleven": web_tail,
            },
            "response_negotiation": {
                "api_json_429": recorded_response(api_breach),
                "web_default_html_429": web_tail["samples"][-1]["response"],
                "web_accept_json_429": web_json["samples"][-1]["response"],
            },
            "key_behavior": {
                "same_session_across_remote_addresses": session_ips,
                "anonymous_same_remote_address": anonymous_same_ip,
                "anonymous_new_remote_address_after_breach": recorded_response(
                    anonymous_other_ip
                ),
                "distinct_sessions_same_remote_address": {
                    "owner_first_ten": owner_ten,
                    "other_first": recorded_response(other_first),
                    "owner_attempt_eleven": recorded_response(owner_breach),
                },
                "session_precedes_conflicting_bearer_for_limiter_key": {
                    "session_owner_plus_bearer_other_first_ten": conflict,
                    "session_owner_without_bearer_attempt_eleven": recorded_response(
                        session_after_conflict
                    ),
                    "session_owner_after_reset_baseline": recorded_response(
                        session_owner_baseline
                    ),
                    "interpretation": (
                        "the limiter charges the Session owner before auth_required selects the "
                        "conflicting Bearer actor for the handler"
                    ),
                },
                "bearer_only_same_actor_across_remote_addresses": bearer_ips,
            },
        }

    return run_with_legacy_app(
        archive_root,
        default_limit=diagnostic_limit,
        storage_uri=None,
        seed_facts=True,
        callback=callback,
    )


def capture_redis_storage_failure(archive_root: Path) -> dict[str, Any]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as guard:
        guard.bind(("127.0.0.1", 0))
        port = int(guard.getsockname()[1])
        storage_uri = (
            f"redis://127.0.0.1:{port}/15"
            "?socket_connect_timeout=0.05&socket_timeout=0.05"
        )

        def callback(
            app: Any,
            client: Any,
            engine: Any,
            _tokens: dict[str, str],
        ) -> dict[str, Any]:
            _set_session_actor(client, "owner")
            with handler_probe(engine) as ledger:
                response = perform_request(
                    client,
                    ROUTES["api-alias"]["path"],
                    request_id="phase4c-rate-redis-unavailable",
                    remote_address="198.51.100.200",
                )
            return {
                "observation_kind": "fixed_commit_real_redis_client_connection_refusal",
                "production_observation": False,
                "storage_endpoint": (
                    "redis://127.0.0.1:<bound-non-listening-port>/15"
                    "?socket_connect_timeout=<short>&socket_timeout=<short>"
                ),
                "mocked_storage": False,
                "live_redis_server_started_then_failed": False,
                "failure_mechanism": (
                    "real redis-py/limits client connection to a locally bound but "
                    "non-listening TCP port"
                ),
                "runtime": limiter_runtime(app),
                "response": recorded_response(response),
                "handler_bank_access_probe_count": ledger[
                    "handler_bank_access_probe_count"
                ],
                "sql_statement_count": ledger["sql_statement_count"],
                "observed_semantics": (
                    "request denied before handler with safe generic HTTP 500; no rate-limit "
                    "headers and no Redis exception text in the response"
                ),
            }

        return run_with_legacy_app(
            archive_root,
            default_limit=None,
            storage_uri=storage_uri,
            seed_facts=False,
            callback=callback,
        )


def tool_provenance() -> dict[str, Any]:
    if not CAPTURE_TEST.is_file():
        raise AssertionError(f"rate-limit capture test missing: {CAPTURE_TEST}")
    support = {
        f"tools/{name}": hashlib.sha256((TOOLS_DIR / name).read_bytes()).hexdigest()
        for name in SUPPORT_FILES
    }
    return {
        "capture_tool": {
            "path": "tools/capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py",
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "capture_test": {
            "path": "tools/test_capture_phase4c_personal_bank_user_counts_rate_limit_evidence.py",
            "sha256": hashlib.sha256(CAPTURE_TEST.read_bytes()).hexdigest(),
        },
        "support_sources": support,
        "runtime_versions": {
            "python": platform.python_version(),
            "Flask": metadata.version("Flask"),
            "Flask-Limiter": metadata.version("Flask-Limiter"),
            "limits": metadata.version("limits"),
            "redis": metadata.version("redis"),
            "SQLAlchemy": metadata.version("SQLAlchemy"),
            "Flask-SQLAlchemy": metadata.version("Flask-SQLAlchemy"),
        },
        "execution_model": (
            "complete app/ archive from the immutable git commit; isolated legacy imports; "
            "real Flask routes; temporary SQLite; synthetic identities; in-memory limits "
            "storage except the explicit real-client Redis refusal probe"
        ),
    }


def _sample(sequence: dict[str, Any], attempt: int) -> dict[str, Any]:
    matches = [item for item in sequence["samples"] if item["attempt"] == attempt]
    if len(matches) != 1:
        raise AssertionError(f"missing unique sample for attempt {attempt}")
    return matches[0]


def assert_evidence_contract(document: dict[str, Any], *, verify_hashes: bool = True) -> None:
    if document.get("contract_id") != (
        "ti.phase4c.personal-bank-user-counts-rate-limit-evidence"
    ):
        raise AssertionError("rate-limit evidence contract id drifted")
    if document.get("status") != (
        "fixed_legacy_observation_only_target_proposal_not_authorized"
    ):
        raise AssertionError("rate-limit evidence status drifted")
    if document.get("legacy_commit") != LEGACY_COMMIT:
        raise AssertionError("rate-limit evidence legacy commit drifted")
    facts = document["legacy_source_facts"]
    if facts["base_configuration"]["value"] != BASE_LIMITS:
        raise AssertionError("base rate-limit declaration drifted")
    if facts["production_configuration"]["default_effective_value"] != (
        PRODUCTION_DEFAULT_LIMITS
    ):
        raise AssertionError("production-effective default drifted")
    if not facts["production_configuration"][
        "base_values_are_not_fixed_commit_production_defaults"
    ]:
        raise AssertionError("base limits were misrepresented as production defaults")

    runtime = document["legacy_runtime_observations"]
    expected_windows = (
        (runtime["base_10_per_second"], 10, 403, "10"),
        (runtime["isolated_500_per_hour"], 500, 403, "500"),
        (runtime["isolated_5000_per_day"], 5000, 403, "5000"),
    )
    for observation, limit, allowed_status, header_limit in expected_windows:
        sequence = observation["sequence"]
        if sequence["attempt_count"] != limit + 1:
            raise AssertionError(f"{limit} window attempt count drifted")
        threshold = _sample(sequence, limit)
        breach = _sample(sequence, limit + 1)
        if threshold["response"]["status"] != allowed_status:
            raise AssertionError(f"{limit}th request must enter the handler")
        if threshold["handler_bank_access_probe_delta"] != 1:
            raise AssertionError(f"{limit}th request did not enter the handler")
        if breach["response"]["status"] != 429:
            raise AssertionError(f"{limit + 1}th request must be HTTP 429")
        if breach["handler_bank_access_probe_delta"] != 0:
            raise AssertionError(f"{limit + 1}th request reached the handler")
        headers = breach["response"]["headers"]
        if headers.get("X-RateLimit-Limit") != [header_limit]:
            raise AssertionError(f"{limit} breach header drifted")
        if headers.get("X-RateLimit-Remaining") != ["0"]:
            raise AssertionError(f"{limit} remaining header drifted")
        if headers.get("X-RateLimit-Reset") != ["<rate-limit-reset-epoch>"]:
            raise AssertionError(f"{limit} reset header was not redacted")
        if headers.get("Retry-After") != ["<dynamic-seconds>"]:
            raise AssertionError(f"{limit} retry header was not redacted")

    scope = runtime["scope_identity_and_negotiation"]
    aliases = scope["alias_buckets"]
    if aliases["result"] != "independent_per_registered_endpoint":
        raise AssertionError("dual aliases were not recorded as independent buckets")
    if aliases["web_attempt_one_after_api_exhaustion"]["status"] != 403:
        raise AssertionError("API alias exhaustion leaked into Web alias bucket")
    if aliases["api_attempt_eleven"]["status"] != 429:
        raise AssertionError("API alias did not reject its eleventh request")
    if aliases["web_remaining_attempts_two_through_eleven"]["samples"][-1][
        "response"
    ]["status"] != 429:
        raise AssertionError("Web alias did not reject its eleventh request")

    negotiated = scope["response_negotiation"]
    if negotiated["api_json_429"]["body_kind"] != "json":
        raise AssertionError("API alias 429 must be JSON")
    if negotiated["web_default_html_429"]["body_kind"] != "text":
        raise AssertionError("default Web alias 429 must be HTML text")
    if negotiated["web_accept_json_429"]["body_kind"] != "json":
        raise AssertionError("Accept JSON Web alias 429 must be JSON")
    for name in ("api_json_429", "web_accept_json_429"):
        body = negotiated[name]["body"]
        if body.get("status") != "error" or body.get("status_code") != 429:
            raise AssertionError(f"{name} envelope drifted")
        if "payload" not in body or body["payload"] is not None:
            raise AssertionError(f"{name} null payload drifted")

    keys = scope["key_behavior"]
    if _sample(keys["same_session_across_remote_addresses"], 11)["response"][
        "status"
    ] != 429:
        raise AssertionError("Session key incorrectly varied with remote address")
    if _sample(keys["anonymous_same_remote_address"], 11)["response"][
        "status"
    ] != 429:
        raise AssertionError("anonymous remote-address fallback was not limited")
    if keys["anonymous_new_remote_address_after_breach"]["status"] != 401:
        raise AssertionError("independent anonymous remote address inherited a bucket")
    distinct = keys["distinct_sessions_same_remote_address"]
    if distinct["other_first"]["status"] != 403:
        raise AssertionError("distinct Session actor inherited exhausted bucket")
    if distinct["owner_attempt_eleven"]["status"] != 429:
        raise AssertionError("original Session actor did not retain exhausted bucket")
    conflict = keys["session_precedes_conflicting_bearer_for_limiter_key"]
    if conflict["session_owner_plus_bearer_other_first_ten"]["status_counts"] != {
        "403": 10
    }:
        raise AssertionError("conflicting Bearer did not select the non-owner handler actor")
    if conflict["session_owner_without_bearer_attempt_eleven"]["status"] != 429:
        raise AssertionError("conflicting Bearer requests did not charge the Session bucket")
    if conflict["session_owner_after_reset_baseline"]["status"] != 200:
        raise AssertionError("Session owner baseline did not prove downstream actor contrast")
    if _sample(keys["bearer_only_same_actor_across_remote_addresses"], 11)[
        "response"
    ]["status"] != 429:
        raise AssertionError("Bearer-only identity incorrectly varied with remote address")

    redis_failure = runtime["redis_storage_failure"]
    if redis_failure["response"]["status"] != 500:
        raise AssertionError("legacy Redis failure observation must remain HTTP 500")
    if redis_failure["handler_bank_access_probe_count"] != 0:
        raise AssertionError("Redis failure reached the user-count handler")
    for header in (
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ):
        if header in redis_failure["response"]["headers"]:
            raise AssertionError("Redis failure unexpectedly emitted rate-limit headers")
    redis_body = redis_failure["response"]["body"]
    if redis_body != {
        "message": "An unexpected server error occurred.",
        "payload": None,
        "request_id": "phase4c-rate-redis-unavailable",
        "status": "error",
        "status_code": 500,
    }:
        raise AssertionError("legacy Redis failure envelope drifted")

    target = document["proposed_target_contract"]
    if target["status"] != "proposal_only_not_implemented_or_authorized":
        raise AssertionError("target proposal was misrepresented as implemented")
    if target["storage_failure"]["policy"] != "fail_closed":
        raise AssertionError("target proposal must fail closed")
    if target["storage_failure"]["proposed_status"] != 503:
        raise AssertionError("target proposal must distinguish outage from quota breach")
    if not document["remaining_authorization_gaps"]:
        raise AssertionError("rate-limit authorization gaps were hidden")

    serialized = render_document(document)
    forbidden = (
        "public-test-only-password-hash",
        "@test.example.com",
        "Bearer eyJ",
    )
    if any(value in serialized for value in forbidden):
        raise AssertionError("rate-limit evidence leaked a credential or synthetic identity")
    if re.search(r"redis://127\.0\.0\.1:\d+", serialized):
        raise AssertionError("rate-limit evidence leaked the ephemeral Redis probe port")
    if re.search(r'"X-RateLimit-Reset":\s*\[\s*"\d+', serialized):
        raise AssertionError("dynamic reset epoch was not redacted")
    if re.search(r'"Retry-After":\s*\[\s*"\d+', serialized):
        raise AssertionError("dynamic retry duration was not redacted")

    if verify_hashes:
        hashes = document["provenance"]["hashes"]
        if hashes["source_payload_sha256"] != sha256_json(
            document["legacy_source_attestation"]
        ):
            raise AssertionError("source payload hash drifted")
        if hashes["runtime_evidence_payload_sha256"] != sha256_json(runtime):
            raise AssertionError("runtime evidence payload hash drifted")
        if document.get("document_payload_sha256") != document_payload_sha256(
            document
        ):
            raise AssertionError("document payload hash drifted")


def capture_document(legacy_root: Path) -> dict[str, Any]:
    if counts.LEGACY_COMMIT != LEGACY_COMMIT:
        raise AssertionError("shared fixed-commit legacy authority drifted")
    with counts.pinned_source.archived_legacy_source(legacy_root) as archived:
        key_sources, source_text = key_source_attestation(
            legacy_root,
            archived,
        )
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "key_sources": key_sources,
        }
        runtime = {
            "base_10_per_second": capture_base_second_window(archived.root),
            "isolated_500_per_hour": capture_isolated_window(
                archived.root,
                limit_value="500 per hour",
                limit=500,
                unit="hour",
            ),
            "isolated_5000_per_day": capture_isolated_window(
                archived.root,
                limit_value="5000 per day",
                limit=5000,
                unit="day",
            ),
            "scope_identity_and_negotiation": capture_scope_and_identity(
                archived.root
            ),
            "redis_storage_failure": capture_redis_storage_failure(archived.root),
        }

    provenance = tool_provenance()
    document: dict[str, Any] = {
        "contract_id": "ti.phase4c.personal-bank-user-counts-rate-limit-evidence",
        "schema_version": 1,
        "captured_at": FIXED_CAPTURE_DATE,
        "status": "fixed_legacy_observation_only_target_proposal_not_authorized",
        "legacy_commit": LEGACY_COMMIT,
        "scope": "dual-alias personal-bank user-counts rate-limit pre-entry evidence",
        "classification": {
            "legacy_source_facts": "immutable fixed-commit source and deployment declarations",
            "legacy_runtime_observations": (
                "real fixed-commit Flask routes in isolated test applications; not deployed "
                "production traffic"
            ),
            "proposed_target_contract": (
                "design proposal only; not authorization, implementation, or cutover evidence"
            ),
        },
        "legacy_source_attestation": source_attestation,
        "legacy_source_facts": source_facts(source_text),
        "legacy_runtime_observations": runtime,
        "proposed_target_contract": {
            "status": "proposal_only_not_implemented_or_authorized",
            "budget": {
                "proposal": "10/second;500/hour;5000/day",
                "reason": "preserve the fixed base configuration named by the HTTP-entry brief",
                "unresolved_difference": (
                    "the fixed commit's default production deployment uses a 100x multiplier"
                ),
            },
            "key": {
                "proposal": (
                    "use the authenticated effective actor after authentication; use trusted "
                    "remote address only if an explicitly authorized anonymous path exists"
                ),
                "intentional_difference_requiring_approval": (
                    "do not preserve the legacy Session-before-conflicting-Bearer limiter mismatch"
                ),
                "raw_identity_in_redis": False,
                "pseudonymized_identity": True,
            },
            "alias_buckets": {
                "proposal": "independent",
                "reason": "preserve observed per-registered-endpoint Flask behavior",
            },
            "429": {
                "proposal": (
                    "preserve API JSON envelope, null payload, request_id, limit description, "
                    "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset and Retry-After"
                ),
                "web_content_negotiation": (
                    "requires explicit entry-contract choice because the legacy Web alias emits "
                    "HTML by default and JSON only for Accept application/json"
                ),
            },
            "storage_failure": {
                "policy": "fail_closed",
                "proposed_status": 503,
                "proposed_envelope": (
                    "safe stable service-unavailable JSON without Redis details or rate-limit "
                    "headers"
                ),
                "intentional_difference_requiring_approval": (
                    "legacy observed generic 500; proposed 503 distinguishes dependency outage "
                    "from both application failure and quota breach"
                ),
                "fail_open": "not proposed and not authorized",
            },
        },
        "remaining_authorization_gaps": [
            "choose base 10/500/5000 budgets or fixed-production default 1000/50000/500000 budgets",
            "approve effective authenticated actor instead of legacy Session-before-Bearer keying",
            "approve independent alias buckets or intentionally merge them",
            "approve legacy Web HTML/Accept negotiation or a JSON-only target surface",
            "approve proposed fail-closed 503 instead of the observed generic 500",
            "run a live Redis server interruption test if process-level recovery, multi-worker sharing, or post-recovery counter continuity is required",
            "separately authorize trusted-proxy/X-Forwarded-For behavior; this capture uses direct REMOTE_ADDR",
        ],
        "redis_gap": {
            "connection_refusal_closed": True,
            "real_redis_client_used": True,
            "mocked_storage": False,
            "live_server_started_then_interrupted": False,
            "what_is_not_proved": [
                "counter continuity after Redis restarts",
                "partial Lua/transaction failure",
                "multi-worker convergence",
                "network timeout duration under deployed settings",
            ],
        },
        "redaction": {
            "jwt": "never serialized",
            "session_cookie": "normalized placeholder when present",
            "raw_limiter_keys": "not captured because legacy keys contain raw user IDs/IPs",
            "redis_probe_port": "normalized placeholder",
            "reset_epoch": "normalized placeholder",
            "retry_after": "normalized placeholder",
            "credentials_and_synthetic_emails": "not serialized",
        },
        "provenance": {
            **provenance,
            "hashes": {
                "source_payload_sha256": sha256_json(source_attestation),
                "runtime_evidence_payload_sha256": sha256_json(runtime),
                "capture_tool_sha256": provenance["capture_tool"]["sha256"],
                "capture_test_sha256": provenance["capture_test"]["sha256"],
            },
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    assert_evidence_contract(document)
    return document


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        "captured personal-bank user-count rate-limit evidence "
        f"runtime_sha256={document['provenance']['hashes']['runtime_evidence_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
