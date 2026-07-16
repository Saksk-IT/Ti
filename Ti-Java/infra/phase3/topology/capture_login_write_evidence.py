#!/usr/bin/env python3
"""Capture redacted, read-only evidence for the Phase 3 isolated login write comparison.

This program never sends HTTP.  The operator performs one login request outside this
process, in the declared serial order.  CAPTURE samples only guarded Docker,
PostgreSQL and Redis state.  SANITIZE_RESPONSE converts already-captured HTTP header
and body files into a small observation that contains no Cookie or Session value.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import email.utils
import hashlib
import hmac
import json
import os
import pathlib
import re
import stat
import sys
import time
import zlib
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from typing import Any, Mapping, Sequence

from rehearse_switch import DockerRunner, RehearsalError
from runtime_state_auditor import (
    EXTERNAL_POLICY,
    OBJECT_STORE_POLICY,
    QUEUE_POLICY,
    AuditScope,
    collect_volume,
    validate_runtime,
)
from topology_guard import GuardError, GuardedTopology, guard_env_file


AUDITOR_ID = "phase3-login-write-evidence-v1"
EVIDENCE_SCHEMA_VERSION = "1"
PROOF_SCHEMA_VERSION = "1"
OBSERVATION_SCHEMA_VERSION = "1"
OPERATION_ID = "identity.auth.login"
FIXTURE_IDENTITY_ID = 1
FIXTURE_SESSION_VERSION = 7
FIXED_REQUEST_ID = "phase3-login-write-001"
FIXED_REDIRECT = "/practice"
FIXTURE_PASSWORD_MATERIAL_SHA256 = (
    "sha256:35bf3c57d38ad279234ff7148845979530c47a250fc4fb77b106e0b14728bce6"
)
QUEUE_BOUNDARY_POLICY_SHA256 = (
    "sha256:72292cd44bf85870a7398c1cbcb10f5fcff7b4e17a75e7b981da08889399399e"
)
OBJECT_STORE_BOUNDARY_POLICY_SHA256 = (
    "sha256:bfdd689deb6a0c3f45aca1da5b1baf9e3d985197327e35a2a02e273ee3db839e"
)
EXTERNAL_SINK_BOUNDARY_POLICY_SHA256 = (
    "sha256:e1fc1f413780c4428da382a5d92cfa38c7a776c51537f0021879d8311b65d36c"
)
RESOURCE_FIELDS = ("database", "redis", "volume")
REDIS_EVIDENCE_FIELDS = (
    "business_fact_keys",
    "server_session_records",
    "rate_limit_attempt_recorded",
    "rebuildable_only",
    "unexpected_keys",
)
MAX_INPUT_BYTES = 1024 * 1024
MAX_HTTP_HEADER_BYTES = 128 * 1024
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
SAFE_RELATION = re.compile(r"[a-z][a-z0-9_]{0,62}\Z")
FORBIDDEN_SCOPE = re.compile(
    r"(?:^|[^a-z0-9])(?:prod(?:uction)?|live)(?:$|[^a-z0-9])", re.I
)


class EvidenceError(RuntimeError):
    """A capture input or sampled state violated the Phase 3 evidence boundary."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise EvidenceError("invalid command arguments; use --help")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return digest_bytes(canonical_bytes(value))


def configuration_only_boundary(
    policy: Mapping[str, Any], expected_policy_sha256: str, label: str
) -> Mapping[str, Any]:
    require(digest_json(policy) == expected_policy_sha256,
            f"{label} configuration policy drifted")
    require(policy.get("configured") is False,
            f"{label} configuration policy must remain disabled")
    return {
        "runtime_observation_performed": False,
        "configured": False,
        "boundary_policy_sha256": expected_policy_sha256,
    }


def validate_digest(value: Any, label: str) -> str:
    require(isinstance(value, str) and SHA256.fullmatch(value) is not None,
            f"{label} must be a sha256 digest")
    return value


def validate_identifier(value: Any, label: str) -> str:
    require(isinstance(value, str) and SAFE_ID.fullmatch(value) is not None,
            f"{label} is not a safe identifier")
    require(FORBIDDEN_SCOPE.search(value) is None, f"PRODUCTION_FORBIDDEN: {label}")
    return value


def _private_regular_file(path: pathlib.Path, label: str, maximum: int = MAX_INPUT_BYTES) -> bytes:
    require(path.is_absolute(), f"{label} must be absolute")
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode), f"{label} must be a regular file")
        require(metadata.st_uid == os.getuid(), f"{label} owner mismatch")
        require(metadata.st_nlink == 1, f"{label} hard links are forbidden")
        require(stat.S_IMODE(metadata.st_mode) == 0o600, f"{label} must have mode 0600")
        require(metadata.st_size <= maximum, f"{label} exceeds its size bound")
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(descriptor, min(65536, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        require(len(raw) <= maximum, f"{label} exceeds its size bound")
        return bytes(raw)
    except OSError as exc:
        raise EvidenceError(f"{label} is not readable") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _strict_json(raw: bytes, label: str) -> Mapping[str, Any]:
    def unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_float=lambda value: (_ for _ in ()).throw(ValueError(value)),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise EvidenceError(f"{label} is not strict UTF-8 JSON") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def read_json(path: pathlib.Path, label: str) -> Mapping[str, Any]:
    return _strict_json(_private_regular_file(path, label), label)


def _validate_output_path(path: pathlib.Path, label: str) -> None:
    require(path.is_absolute(), f"{label} must be absolute")
    require(path.suffix == ".json", f"{label} must use .json")
    require(not path.exists(), f"{label} already exists; overwrite is forbidden")
    try:
        metadata = path.parent.lstat()
    except OSError as exc:
        raise EvidenceError(f"{label} parent is not accessible") from exc
    require(stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode),
            f"{label} parent must be a real directory")
    require(metadata.st_uid == os.getuid() and stat.S_IMODE(metadata.st_mode) & 0o077 == 0,
            f"{label} parent must be owner-only")


def write_json_atomic(path: pathlib.Path, value: Mapping[str, Any]) -> None:
    _validate_output_path(path, "output")
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise EvidenceError("output collision; overwrite is forbidden") from exc
    except OSError as exc:
        raise EvidenceError("could not atomically write output") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class CaptureScope:
    environment: str
    side: str
    phase: str
    logical_run_id: str
    fixture_id: str
    snapshot_id: str
    snapshot_digest: str
    capture_sequence: int
    topology: GuardedTopology
    peer_topology: GuardedTopology
    fingerprint: Mapping[str, str]
    resource_binding_sha256: str


def _side_value(topology: GuardedTopology, side: str, suffix: str) -> str:
    prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
    return topology.values[f"{prefix}_{suffix}"]


def validate_fingerprint(
    document: Mapping[str, Any], environment: str, side: str, topology: GuardedTopology
) -> Mapping[str, str]:
    require(set(document) == {"schema_version", "environment", "side", *RESOURCE_FIELDS},
            f"{side} fingerprint fields do not match schema v1")
    require(document["schema_version"] == "1" and document["environment"] == environment
            and document["side"] == side, f"{side} fingerprint scope mismatch")
    result: dict[str, str] = {}
    for field in RESOURCE_FIELDS:
        value = document[field]
        require(isinstance(value, str) and 1 <= len(value) <= 512 and value == value.strip(),
                f"{side} {field} fingerprint is invalid")
        require(FORBIDDEN_SCOPE.search(value) is None, "PRODUCTION_FORBIDDEN: fingerprint")
        result[field] = value
    expected = {
        "database": _side_value(topology, side, "DB_NAME"),
        "redis": _side_value(topology, side, "REDIS_VOLUME"),
        "volume": _side_value(topology, side, "APP_VOLUME"),
    }
    require(result == expected, f"{side} fingerprint does not identify the guarded resources")
    return result


def resource_binding(fingerprint: Mapping[str, str]) -> str:
    payload = b"ti-phase3-isolated-write-fingerprint-v1\0" + b"\0".join(
        fingerprint[field].encode("utf-8") for field in RESOURCE_FIELDS
    )
    return digest_bytes(payload)


def _legacy_observation_scope(topology: GuardedTopology) -> str:
    payload = b"ti-phase3-legacy-response-scope-v1\0" + b"\0".join(
        value.encode("utf-8") for value in (
            topology.project,
            topology.run_id,
            _side_value(topology, "legacy", "DB_NAME"),
            _side_value(topology, "legacy", "REDIS_VOLUME"),
            _side_value(topology, "legacy", "APP_VOLUME"),
        )
    )
    return digest_bytes(payload)


def validate_pair_resources(
    environment: str,
    legacy: GuardedTopology,
    java: GuardedTopology,
    fingerprints: Mapping[str, Mapping[str, str]],
) -> None:
    require(environment in {"local", "test"}, "local/test environment is required")
    require(legacy.env_file != java.env_file and legacy.project != java.project
            and legacy.run_id != java.run_id, "legacy and Java must be different guarded runs")
    require(legacy.environment == environment and java.environment == environment,
            "guarded environment mismatch")
    selected = (
        _side_value(legacy, "legacy", "DB_NAME"),
        _side_value(legacy, "legacy", "PG_VOLUME"),
        _side_value(legacy, "legacy", "REDIS_VOLUME"),
        _side_value(legacy, "legacy", "APP_VOLUME"),
        _side_value(java, "java", "DB_NAME"),
        _side_value(java, "java", "PG_VOLUME"),
        _side_value(java, "java", "REDIS_VOLUME"),
        _side_value(java, "java", "APP_VOLUME"),
    )
    require(len(selected) == len(set(selected)), "selected data resources are not independent")
    ports = (
        _side_value(legacy, "legacy", "API_PORT"),
        _side_value(legacy, "legacy", "POSTGRES_PORT"),
        _side_value(legacy, "legacy", "REDIS_PORT"),
        _side_value(java, "java", "API_PORT"),
        _side_value(java, "java", "POSTGRES_PORT"),
        _side_value(java, "java", "REDIS_PORT"),
    )
    require(len(ports) == len(set(ports)), "selected host ports are not independent")
    all_fingerprints = [
        fingerprints[side][field] for side in ("legacy", "java") for field in RESOURCE_FIELDS
    ]
    require(len(all_fingerprints) == len(set(all_fingerprints)),
            "all six comparator fingerprint values must differ")
    legacy_image = _side_value(legacy, "legacy", "IMAGE").rsplit("sha256:", 1)[1]
    java_image = _side_value(java, "java", "IMAGE").rsplit("sha256:", 1)[1]
    require(legacy_image != java_image, "selected application images must differ")


def _resolve_capture_scope(args: argparse.Namespace) -> CaptureScope:
    legacy = guard_env_file(args.legacy_env_file)
    java = guard_env_file(args.java_env_file)
    topologies = {"legacy": legacy, "java": java}
    fingerprint_documents = {
        "legacy": read_json(args.legacy_fingerprint, "legacy fingerprint"),
        "java": read_json(args.java_fingerprint, "Java fingerprint"),
    }
    fingerprints = {
        side: validate_fingerprint(fingerprint_documents[side], args.environment, side,
                                   topologies[side])
        for side in ("legacy", "java")
    }
    validate_pair_resources(args.environment, legacy, java, fingerprints)
    require(args.phase in {"before", "after"}, "capture phase must be before/after")
    require(1 <= args.capture_sequence <= 4, "capture sequence must be between 1 and 4")
    return CaptureScope(
        environment=args.environment,
        side=args.side,
        phase=args.phase,
        logical_run_id=validate_identifier(args.run_id, "run-id"),
        fixture_id=validate_identifier(args.fixture_id, "fixture-id"),
        snapshot_id=validate_identifier(args.snapshot_id, "snapshot-id"),
        snapshot_digest=validate_digest(args.snapshot_digest, "snapshot-digest"),
        capture_sequence=args.capture_sequence,
        topology=topologies[args.side],
        peer_topology=topologies["java" if args.side == "legacy" else "legacy"],
        fingerprint=fingerprints[args.side],
        resource_binding_sha256=resource_binding(fingerprints[args.side]),
    )


def _assert_selected_runtime(scope: CaptureScope) -> DockerRunner:
    selected_runner: DockerRunner | None = None
    for side, topology, peer in (
        (scope.side, scope.topology, scope.peer_topology),
        ("java" if scope.side == "legacy" else "legacy",
         scope.peer_topology, scope.topology),
    ):
        runner = DockerRunner(topology, {})
        audit_scope = AuditScope(
            environment=scope.environment,
            side=side,
            phase=scope.phase,
            topology=topology,
            peer_topology=peer,
        )
        runner.preflight_local_context()
        validate_runtime(audit_scope, runner)
        opposite = "java" if side == "legacy" else "legacy"
        for suffix in ("api", "postgres", "redis"):
            require(not runner.compose_ids(f"{opposite}-{suffix}", running_only=False),
                    "a guarded run contains an undeclared opposite-stack container")
        if side == scope.side:
            selected_runner = runner
    assert selected_runner is not None
    return selected_runner


PG_QUERY_SHELL = r'''set -eu
export PGPASSWORD="$(cat /run/secrets/db.audit.password)"
exec psql --no-psqlrc --quiet --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --username "$1" --dbname "$2" --command "$3"
'''

PG_SCHEMA_SHELL = r'''set -eu
export PGPASSWORD="$(cat /run/secrets/db.audit.password)"
exec pg_dump --dbname="$2" --username="$1" --schema-only --no-owner --no-acl \
  --encoding=UTF8 --quote-all-identifiers --no-sync --format=plain
'''


def _pg_capture(
    scope: CaptureScope, runner: DockerRunner, sql: str, label: str
) -> bytes:
    role = _side_value(scope.topology, scope.side, "DB_AUDIT")
    database = _side_value(scope.topology, scope.side, "DB_NAME")
    result = runner.compose(
        ["exec", "-T", f"{scope.side}-postgres", "sh", "-ec", PG_QUERY_SHELL,
         label, role, database, sql],
        capture=True,
    )
    return result.stdout


def _relation_inventory(scope: CaptureScope, runner: DockerRunner) -> list[tuple[str, str]]:
    sql = """
        SELECT COALESCE(json_agg(json_build_array(n.nspname, c.relname, c.relkind)
                                ORDER BY n.nspname, c.relname)::text, '[]')
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p', 'm', 'S')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname !~ '^pg_toast'
    """
    document = json.loads(_pg_capture(scope, runner, sql, "phase3-login-relations").decode(
        "utf-8", "strict").strip())
    require(isinstance(document, list) and 1 <= len(document) <= 10_000,
            "PostgreSQL relation inventory is invalid")
    relations: list[tuple[str, str]] = []
    for item in document:
        require(isinstance(item, list) and len(item) == 3
                and item[2] in {"r", "p", "m", "S"},
                "PostgreSQL relation inventory row is invalid")
        schema, name, kind = item
        require(schema == "public" and isinstance(name, str)
                and SAFE_RELATION.fullmatch(name) is not None,
                "only safe public relations are supported by the Phase 3 fixture auditor")
        relations.append((name, kind))
    require(len(relations) == len(set(relations)), "duplicate PostgreSQL relation inventory")
    require(any(name == "users" and kind in {"r", "p"} for name, kind in relations),
            "public.users fixture table is missing")
    return relations


def _quote_identifier(value: str) -> str:
    require(SAFE_RELATION.fullmatch(value) is not None, "unsafe PostgreSQL identifier")
    return '"' + value + '"'


def _sql_literal(value: str) -> str:
    require("\x00" not in value, "NUL is forbidden in SQL literal")
    return "'" + value.replace("'", "''") + "'"


def _business_state_sql(relations: Sequence[tuple[str, str]], mode: str) -> str:
    require(mode in {"transition", "projected"}, "unknown business digest mode")
    statements: list[str] = ["BEGIN TRANSACTION READ ONLY ISOLATION LEVEL REPEATABLE READ;"]
    for name, kind in relations:
        prefix = "public." + name
        relation = '"public".' + _quote_identifier(name)
        marker = _sql_literal(prefix + "\t#relation")
        row_prefix = _sql_literal(prefix + "\t")
        if kind == "S":
            expression = "jsonb_build_object('is_called', is_called, 'last_value', last_value)"
            source = relation
        else:
            expression = "to_jsonb(t)"
            if name == "users":
                projected = ["has_password_set"] if mode == "transition" else [
                    "password_hash", "has_password_set", "session_version", "last_active"
                ]
                pairs = ", ".join(
                    "'" + field + "', '__phase3_projected_" + field + "__'"
                    for field in projected
                )
                expression = (
                    "CASE WHEN t.\"id\" = 1 THEN to_jsonb(t) || jsonb_build_object("
                    + pairs + ") ELSE to_jsonb(t) END"
                )
            source = "ONLY " + relation + " AS t"
        statements.append(
            f"SELECT {marker} AS framed UNION ALL "
            f"SELECT {row_prefix} || row_data::text FROM "
            f"(SELECT {expression} AS row_data FROM {source}) AS rows ORDER BY framed;"
        )
    statements.append("COMMIT;")
    return "\n".join(statements)


def _business_digest(
    scope: CaptureScope, runner: DockerRunner, relations: Sequence[tuple[str, str]], mode: str
) -> str:
    role = _side_value(scope.topology, scope.side, "DB_AUDIT")
    database = _side_value(scope.topology, scope.side, "DB_NAME")
    sql = _business_state_sql(relations, mode)
    return runner.stream_sha256([
        "exec", "-T", f"{scope.side}-postgres", "sh", "-ec", PG_QUERY_SHELL,
        f"phase3-login-business-{mode}", role, database, sql,
    ])


def _schema_digest(scope: CaptureScope, runner: DockerRunner) -> str:
    role = _side_value(scope.topology, scope.side, "DB_AUDIT")
    database = _side_value(scope.topology, scope.side, "DB_NAME")
    return runner.stream_sha256([
        "exec", "-T", f"{scope.side}-postgres", "sh", "-ec", PG_SCHEMA_SHELL,
        "phase3-login-schema", role, database,
    ], normalize_pg_restore_sql=True)


def _fixture_state(scope: CaptureScope, runner: DockerRunner) -> Mapping[str, Any]:
    sql = """
        SELECT json_build_object(
          'fixture_count', count(*) FILTER (WHERE id = 1),
          'users_row_count', (SELECT count(*) FROM public.users),
          'password_material', max(password_hash) FILTER (WHERE id = 1),
          'has_password_set', bool_or(has_password_set) FILTER (WHERE id = 1),
          'session_version', max(session_version) FILTER (WHERE id = 1),
          'last_active', max(last_active) FILTER (WHERE id = 1),
          'invalid_constraints', (
            SELECT count(*) FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'public' AND NOT c.convalidated
          ),
          'large_objects', (SELECT count(*) FROM pg_largeobject_metadata)
        )::text
        FROM public.users
    """
    raw = _pg_capture(scope, runner, sql, "phase3-login-fixture").decode("utf-8", "strict").strip()
    value = json.loads(raw)
    require(isinstance(value, dict) and set(value) == {
        "fixture_count", "users_row_count", "password_material", "has_password_set",
        "session_version", "last_active", "invalid_constraints", "large_objects",
    }, "fixture query output is invalid")
    require(value["fixture_count"] == 1 and type(value["users_row_count"]) is int,
            "the id=1 fixture row must exist exactly once")
    require(value["large_objects"] == 0, "large objects are outside this bounded evidence contract")
    require(value["invalid_constraints"] == 0, "unvalidated PostgreSQL constraints are forbidden")
    password_material = value["password_material"]
    require(isinstance(password_material, str), "fixture password material is missing")
    material_digest = digest_bytes(password_material.encode("utf-8"))
    require(material_digest == FIXTURE_PASSWORD_MATERIAL_SHA256,
            "id=1 is not the committed public scrypt compatibility vector")
    require(password_material.startswith("scrypt:32768:8:1$")
            and password_material.count("$") == 2,
            "fixture password material is not Werkzeug target scrypt")
    require(value["session_version"] == FIXTURE_SESSION_VERSION,
            "fixture session_version must remain 7")
    require(value["last_active"] is None, "fixture last_active must remain null")
    return {
        "users_row_count": value["users_row_count"],
        "has_password_set": value["has_password_set"],
        "session_version": value["session_version"],
        "last_active_state": "null",
        "credential_material_sha256": material_digest,
        "format_family": "werkzeug-scrypt",
        "target_parameters": "32768:8:1",
        "verifies_fixture_password": True,
        "constraint_violations": 0,
    }


def collect_database(scope: CaptureScope, runner: DockerRunner) -> Mapping[str, Any]:
    relations = _relation_inventory(scope, runner)
    transition = _business_digest(scope, runner, relations, "transition")
    projected = _business_digest(scope, runner, relations, "projected")
    fixture = _fixture_state(scope, runner)
    transition_confirmation = _business_digest(scope, runner, relations, "transition")
    require(transition_confirmation == transition,
            "PostgreSQL changed during the read-only capture window")
    return {
        "schema_sha256": _schema_digest(scope, runner),
        "normalized_business_state_sha256": projected,
        "transition_guard_sha256": transition,
        **fixture,
    }


REDIS_CAPTURE_LUA = r'''
local side = ARGV[1]
local session_namespace = ARGV[2]
local phase = ARGV[3]
if side ~= 'legacy' and side ~= 'java' then return redis.error_reply('INVALID_SIDE') end
if phase ~= 'before' and phase ~= 'after' then return redis.error_reply('INVALID_PHASE') end

local function starts(value, prefix)
  return string.sub(value, 1, string.len(prefix)) == prefix
end
local function positive_counter(key)
  if redis.call('TYPE', key).ok ~= 'string' then return false end
  local value = redis.call('GET', key)
  local ttl = redis.call('PTTL', key)
  return value ~= false and string.match(value, '^[1-9][0-9]*$') ~= nil and ttl > 0
end
local function first_attempt_counter(key)
  return redis.call('TYPE', key).ok == 'string' and redis.call('GET', key) == '1' and
         redis.call('PTTL', key) > 0 and redis.call('PTTL', key) <= 120000
end
local function positive_ttl(key)
  return redis.call('PTTL', key) > 0
end
local function bounded_ttl(key, maximum)
  local ttl = redis.call('PTTL', key)
  return ttl > 0 and ttl <= maximum
end
local function private_ipv4(value)
  local a,b,c,d = string.match(value, '^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  if not a then return false end
  a=tonumber(a); b=tonumber(b); c=tonumber(c); d=tonumber(d)
  if a>255 or b>255 or c>255 or d>255 then return false end
  return a==10 or a==127 or (a==192 and b==168) or (a==172 and b>=16 and b<=31)
end
local function exact_hash_fields(key, expected)
  local fields = redis.call('HKEYS', key)
  if #fields ~= #expected then return false end
  local seen = {}
  for _,field in ipairs(fields) do seen[field] = true end
  for _,field in ipairs(expected) do if not seen[field] then return false end end
  return true
end

local keys = redis.call('KEYS', '*')
local session_records = 0
local anonymous_records = 0
local login_rate = 0
local csrf_rate = 0
local session_ids = {}
local anonymous_ids = {}
local target_identity_sets = {}
local target_identity_sequences = {}
local target_global = {sessions=false, sequence=false, owners=false}
local target_key_count = 0
local session_prefix = session_namespace .. ':sessions:'
local target_prefix = 'ti-java:identity:target-session-index:'

for _,key in ipairs(keys) do
  local kind = redis.call('TYPE', key).ok
  if side == 'legacy' then
    local ip, endpoint = string.match(
      key, '^LIMITS:LIMITER/ip:([^/]+)/auth%.auth_api%.(api_[a-z_]+)/5/1/minute$')
    if not ip or not private_ipv4(ip) or endpoint ~= 'api_login' or
       not first_attempt_counter(key) then
      return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
    end
    login_rate = login_rate + 1
  else
    local login = string.match(key, '^ti%-java:identity:login%-rate:global:[0-9]+$') ~= nil
    if not login then
      local category, pseudonym = string.match(
        key, '^ti%-java:identity:login%-rate:([a-z]+):([0-9a-f]+):[0-9]+$')
      login = (category == 'ip' or category == 'account') and
              pseudonym ~= nil and string.len(pseudonym) == 64
    end
    local csrf = string.match(
      key, '^ti%-java:identity:csrf%-issuance%-rate:global:[0-9]+$') ~= nil
    if not csrf then
      local pseudonym = string.match(
        key, '^ti%-java:identity:csrf%-issuance%-rate:ip:([0-9a-f]+):[0-9]+$')
      csrf = pseudonym ~= nil and string.len(pseudonym) == 64
    end
    if login then
      if not first_attempt_counter(key) then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      login_rate = login_rate + 1
    elseif csrf then
      if not first_attempt_counter(key) then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      csrf_rate = csrf_rate + 1
    elseif starts(key, session_prefix) then
      if kind ~= 'hash' or not positive_ttl(key) then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      local identity = string.sub(key, string.len(session_prefix) + 1)
      if not string.match(identity, '^[A-Za-z0-9._-]+$') or session_ids[identity] or
         anonymous_ids[identity] then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      local authenticated = {'creationTime','lastAccessedTime','maxInactiveInterval',
        'sessionAttr:identity_id','sessionAttr:session_version',
        'sessionAttr:authenticated_at','sessionAttr:remember'}
      local anonymous = {'creationTime','lastAccessedTime','maxInactiveInterval',
        'sessionAttr:anonymous_expires_at','sessionAttr:csrf_token'}
      if exact_hash_fields(key, authenticated) then
        if not bounded_ttl(key, 605100000) or
           redis.call('HGET', key, 'sessionAttr:identity_id') ~= 'l:1' or
           redis.call('HGET', key, 'sessionAttr:session_version') ~= 'i:7' or
           redis.call('HGET', key, 'sessionAttr:remember') ~= 'b:1' or
           redis.call('HGET', key, 'maxInactiveInterval') ~= 'i:604800' or
           not string.match(redis.call('HGET', key, 'sessionAttr:authenticated_at') or '',
                            '^l:[0-9]+$') then
          return redis.error_reply('INVALID_SERVER_SESSION_SEMANTICS')
        end
        session_ids[identity] = true
        session_records = session_records + 1
      elseif exact_hash_fields(key, anonymous) then
        local interval = string.match(
          redis.call('HGET', key, 'maxInactiveInterval') or '', '^i:([0-9]+)$')
        local expires_at = redis.call('HGET', key, 'sessionAttr:anonymous_expires_at') or ''
        local csrf_token = redis.call('HGET', key, 'sessionAttr:csrf_token') or ''
        if not interval or tonumber(interval) < 1 or tonumber(interval) > 600 or
           not bounded_ttl(key, 900000) or
           not string.match(expires_at, '^l:[0-9]+$') or
           not string.match(csrf_token, '^s:[A-Za-z0-9_-]+$') or
           string.len(csrf_token) ~= 45 then
          return redis.error_reply('INVALID_ANONYMOUS_SESSION_SEMANTICS')
        end
        anonymous_ids[identity] = true
        anonymous_records = anonymous_records + 1
      else
        return redis.error_reply('INVALID_SERVER_SESSION_SEMANTICS')
      end
    elseif key == target_prefix .. 'global:sessions' then
      if kind ~= 'zset' or not bounded_ttl(key, 604800000) then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      target_global.sessions = true
      target_key_count = target_key_count + 1
    elseif key == target_prefix .. 'global:sequence' then
      if not positive_counter(key) or redis.call('GET', key) ~= '1' or
         not bounded_ttl(key, 604800000) then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      target_global.sequence = true
      target_key_count = target_key_count + 1
    elseif key == target_prefix .. 'global:owners' then
      if kind ~= 'hash' or not bounded_ttl(key, 604800000) then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      target_global.owners = true
      target_key_count = target_key_count + 1
    else
      local identity, suffix = string.match(
        key, '^ti%-java:identity:target%-session%-index:{([0-9a-f]+)}:([a-z]+)$')
      if not identity or string.len(identity) ~= 64 or
         (suffix ~= 'sessions' and suffix ~= 'sequence') then
        return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
      end
      if suffix == 'sessions' then
        if kind ~= 'zset' or not bounded_ttl(key, 604800000) or
           target_identity_sets[identity] then
          return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
        end
        target_identity_sets[identity] = key
      else
        if not positive_counter(key) or redis.call('GET', key) ~= '1' or
           not bounded_ttl(key, 604800000) or
           target_identity_sequences[identity] then
          return redis.error_reply('UNKNOWN_REDIS_KEY_OR_TYPE')
        end
        target_identity_sequences[identity] = key
      end
      target_key_count = target_key_count + 1
    end
  end
end

if side == 'java' then
  if phase == 'before' then
    if #keys ~= 3 or session_records ~= 0 or anonymous_records ~= 1 or
       login_rate ~= 0 or csrf_rate ~= 2 or target_key_count ~= 0 or
       next(target_identity_sets) or next(target_identity_sequences) or
       target_global.sessions or target_global.sequence or
       target_global.owners then return redis.error_reply('ORPHAN_SESSION_STATE') end
  elseif phase == 'after' and #keys == 11 and session_records == 1 and
         anonymous_records == 0 and login_rate == 3 and csrf_rate == 2 and
         target_key_count == 5 then
    local registry_identity, identity_set_key = next(target_identity_sets)
    local sequence_identity, identity_sequence_key = next(target_identity_sequences)
    if not registry_identity or next(target_identity_sets, registry_identity) or
       sequence_identity ~= registry_identity or
       next(target_identity_sequences, sequence_identity) or
       not target_global.sessions or not target_global.sequence or not target_global.owners then
      return redis.error_reply('TARGET_SESSION_REGISTRY_INCOMPLETE')
    end
    local session_identity = next(session_ids)
    if redis.call('ZCARD', identity_set_key) ~= 1 or
       redis.call('ZRANGE', identity_set_key, 0, 0)[1] ~= session_identity or
       redis.call('ZCARD', target_prefix .. 'global:sessions') ~= 1 or
       redis.call('ZRANGE', target_prefix .. 'global:sessions', 0, 0)[1] ~= session_identity or
       redis.call('HLEN', target_prefix .. 'global:owners') ~= 1 or
       redis.call('HGET', target_prefix .. 'global:owners', session_identity) ~= registry_identity or
       redis.call('GET', identity_sequence_key) ~= '1' then
      return redis.error_reply('TARGET_SESSION_REGISTRY_BINDING_INVALID')
    end
  else
    return redis.error_reply('UNEXPECTED_AUTHENTICATED_OR_ANONYMOUS_SESSION_COUNT')
  end
else
  if phase == 'before' and (#keys ~= 0 or login_rate ~= 0) then
    return redis.error_reply('LEGACY_BEFORE_REDIS_NOT_EMPTY')
  end
  if phase == 'after' and (#keys ~= 1 or login_rate ~= 1) then
    return redis.error_reply('LEGACY_LOGIN_ATTEMPT_COUNT_INVALID')
  end
end

local authenticated_session_id = 'none'
if session_records == 1 then authenticated_session_id = next(session_ids) end
return {'phase3-login-redis-v1', tostring(#keys), tostring(session_records),
        tostring(anonymous_records), tostring(login_rate), '0', '0',
        authenticated_session_id}
'''

REDIS_CAPTURE_SHELL = r'''set -eu
export REDISCLI_AUTH="$(cat /run/secrets/redis.password)"
exec redis-cli --no-auth-warning --raw EVAL "$1" 0 "$2" "$3" "$4"
'''


def _target_session_binding(session_id: str) -> str:
    require(re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        session_id,
    ) is not None, "target Session id is not a canonical UUIDv4")
    return digest_bytes(
        b"ti-phase3-java-session-binding-v1\0" + session_id.encode("ascii")
    )


def parse_redis_summary(raw: bytes) -> Mapping[str, Any]:
    try:
        lines = raw.decode("ascii").rstrip("\n").split("\n")
    except UnicodeDecodeError as exc:
        raise EvidenceError("Redis summary is not ASCII") from exc
    require(len(lines) == 8 and lines[0] == "phase3-login-redis-v1",
            "Redis summary schema mismatch")
    require(all(re.fullmatch(r"0|[1-9][0-9]{0,8}", item) for item in lines[1:7]),
            "Redis summary count is invalid")
    key_count, sessions, anonymous, login_rate, business, unexpected = map(
        int, lines[1:7]
    )
    session_id = lines[7]
    require(session_id == "none" or re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        session_id,
    ) is not None, "Redis authenticated Session id is invalid")
    require((sessions == 1) is (session_id != "none"),
            "Redis authenticated Session binding is incomplete")
    require(business == 0 and unexpected == 0, "Redis contains business or unknown state")
    require(sessions <= 1 and anonymous <= 1 and login_rate <= 3 and key_count <= 64,
            "Redis evidence exceeds the bounded login fixture")
    return {
        "business_fact_keys": business,
        "server_session_records": sessions,
        "rate_limit_attempt_recorded": login_rate > 0,
        "rebuildable_only": True,
        "unexpected_keys": unexpected,
        "target_session_binding_sha256": (
            "none" if session_id == "none" else _target_session_binding(session_id)
        ),
    }


def collect_redis(scope: CaptureScope, runner: DockerRunner) -> Mapping[str, Any]:
    namespace = _side_value(scope.topology, "java", "SESSION_NAMESPACE")
    result = runner.compose(
        ["exec", "-T", f"{scope.side}-redis", "sh", "-ec", REDIS_CAPTURE_SHELL,
         "phase3-login-redis", REDIS_CAPTURE_LUA, scope.side, namespace, scope.phase],
        capture=True,
    )
    return parse_redis_summary(result.stdout)


def collect_application_volume(
    scope: CaptureScope, runner: DockerRunner
) -> Mapping[str, Any]:
    audit_scope = AuditScope(
        environment=scope.environment,
        side=scope.side,
        phase=scope.phase,
        topology=scope.topology,
        peer_topology=scope.peer_topology,
    )
    return collect_volume(audit_scope, runner)


def _parse_http_headers(raw: bytes) -> tuple[int, Mapping[str, list[str]]]:
    require(len(raw) <= MAX_HTTP_HEADER_BYTES, "HTTP header capture is too large")
    try:
        text = raw.decode("iso-8859-1")
    except UnicodeDecodeError as exc:
        raise EvidenceError("HTTP headers are invalid") from exc
    require("\x00" not in text, "HTTP headers contain NUL")
    normalized = text.replace("\r\n", "\n")
    require("\r" not in normalized, "HTTP headers use invalid line endings")
    blocks = [block for block in normalized.split("\n\n") if block.strip()]
    require(len(blocks) == 1, "exactly one non-redirect HTTP response is required")
    lines = blocks[0].split("\n")
    status_match = re.fullmatch(r"HTTP/(?:1\.[01]|2) ([1-5][0-9]{2})(?: [^\x00-\x1f\x7f]*)?", lines[0])
    require(status_match is not None, "HTTP status line is invalid")
    headers: dict[str, list[str]] = {}
    for line in lines[1:]:
        require(line and not line[:1].isspace() and ":" in line,
                "folded or malformed HTTP header is forbidden")
        name, value = line.split(":", 1)
        require(re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) is not None,
                "HTTP header name is invalid")
        value = value.strip(" \t")
        require(not any(ord(character) < 32 and character != "\t" or ord(character) == 127
                        for character in value), "HTTP header value contains controls")
        headers.setdefault(name.lower(), []).append(value)
    return int(status_match.group(1)), headers


def _canonical_content_type(headers: Mapping[str, list[str]]) -> str:
    values = headers.get("content-type", [])
    require(len(values) == 1, "exactly one Content-Type header is required")
    parts = [part.strip().lower() for part in values[0].split(";")]
    require(parts[0] == "application/json" and len(parts) == 2 and "=" in parts[1],
            "login response must be application/json with one charset")
    key, value = (item.strip().strip('"') for item in parts[1].split("=", 1))
    require(key == "charset" and value == "utf-8", "login response charset must be UTF-8")
    return "application/json;charset=utf-8"


def _legacy_response_epoch(headers: Mapping[str, list[str]]) -> int:
    values = headers.get("date", [])
    require(len(values) == 1, "legacy response must carry exactly one Date header")
    try:
        parsed = email.utils.parsedate_to_datetime(values[0])
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("legacy response Date header is invalid") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None
            and parsed.utcoffset().total_seconds() == 0,
            "legacy response Date header must use GMT")
    epoch = int(parsed.timestamp())
    require(1_577_836_800 <= epoch <= 4_102_444_800,
            "legacy response Date is outside the bounded evidence era")
    return epoch


def _urlsafe_decode(value: str, label: str) -> bytes:
    require(re.fullmatch(r"[A-Za-z0-9_-]+", value) is not None,
            f"{label} is not URL-safe base64")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError, TypeError) as exc:
        raise EvidenceError(f"{label} is not valid base64") from exc
    require(base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == value,
            f"{label} is not canonical base64")
    return decoded


def _java_cookie_session_binding(value: str) -> str:
    require(re.fullmatch(r"[A-Za-z0-9+/]{48}", value) is not None,
            "Java target Session cookie is not canonical standard Base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceError("Java target Session cookie is not valid Base64") from exc
    require(base64.b64encode(decoded).decode("ascii") == value,
            "Java target Session cookie is not canonical Base64")
    try:
        session_id = decoded.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EvidenceError("Java target Session cookie is not an ASCII Session id") from exc
    return _target_session_binding(session_id)


def verify_flask_session_cookie(
    cookie: str, secret: bytes, now: int | None = None
) -> Mapping[str, Any]:
    """Verify Flask's cookie-session signer and the exact public id=1 scalar snapshot."""
    require(32 <= len(secret) <= 128 and b"\x00" not in secret,
            "legacy Flask secret is invalid")
    require(20 <= len(cookie) <= 4096 and cookie.count(".") in {2, 3},
            "legacy Flask Session cookie structure is invalid")
    try:
        signed_value, encoded_signature = cookie.rsplit(".", 1)
        payload_and_timestamp, encoded_timestamp = signed_value.rsplit(".", 1)
    except ValueError as exc:
        raise EvidenceError("legacy Flask Session cookie structure is invalid") from exc
    derived = hmac.new(secret, b"cookie-session", hashlib.sha1).digest()
    expected = hmac.new(derived, signed_value.encode("ascii"), hashlib.sha1).digest()
    signature = _urlsafe_decode(encoded_signature, "Flask Session signature")
    require(hmac.compare_digest(signature, expected), "legacy Flask Session signature mismatch")

    timestamp_raw = _urlsafe_decode(encoded_timestamp, "Flask Session timestamp")
    require(1 <= len(timestamp_raw) <= 8, "legacy Flask Session timestamp is invalid")
    issued_at = int.from_bytes(timestamp_raw, "big")
    current = int(time.time()) if now is None else now
    require(current - 300 <= issued_at <= current + 30,
            "legacy Flask Session timestamp is outside the capture window")

    compressed = payload_and_timestamp.startswith(".")
    encoded_payload = payload_and_timestamp[1:] if compressed else payload_and_timestamp
    payload = _urlsafe_decode(encoded_payload, "Flask Session payload")
    if compressed:
        try:
            payload = zlib.decompress(payload)
        except zlib.error as exc:
            raise EvidenceError("legacy Flask Session compression is invalid") from exc
    require(len(payload) <= 8192, "legacy Flask Session payload is too large")
    session = _strict_json(payload, "legacy Flask Session payload")
    expected_keys = {
        "_permanent", "user_id", "username", "is_admin", "is_subject_admin",
        "is_notification_admin", "session_version", "remember",
    }
    require(set(session) == expected_keys, "legacy Flask Session fields drifted")
    require(session == {
        "_permanent": True,
        "user_id": FIXTURE_IDENTITY_ID,
        "username": "phase3-fixture",
        "is_admin": False,
        "is_subject_admin": False,
        "is_notification_admin": False,
        "session_version": FIXTURE_SESSION_VERSION,
        "remember": True,
    }, "legacy Flask Session scalar authority does not match the id=1 fixture")
    return {
        "signed_snapshot_verified": True,
        "identity_id": FIXTURE_IDENTITY_ID,
        "session_version": FIXTURE_SESSION_VERSION,
        "remember": True,
        "credential_material_count": 0,
    }


def _cookie_semantics(
    side: str,
    headers: Mapping[str, list[str]],
    remember: bool,
    flask_secret: bytes | None,
    legacy_response_epoch: int | None,
) -> Mapping[str, Any]:
    cookies: dict[str, list[tuple[str, Mapping[str, str]]]] = {}
    for line in headers.get("set-cookie", []):
        parsed = SimpleCookie()
        try:
            parsed.load(line)
        except CookieError as exc:
            raise EvidenceError("Set-Cookie is invalid") from exc
        require(len(parsed) == 1, "each Set-Cookie line must contain one cookie")
        name, morsel = next(iter(parsed.items()))
        if name in cookies:
            require(side == "java" and name == "ti_phase3_java_csrf"
                    and len(cookies[name]) == 1,
                    "duplicate Set-Cookie name is forbidden")
        cookies.setdefault(name, []).append(
            (morsel.value, {key.lower(): morsel[key] for key in morsel.keys()})
        )
    primary = "session" if side == "legacy" else "ti_phase3_java_session"
    if side == "legacy":
        require(set(cookies) == {"session"} and len(cookies["session"]) == 1,
                "legacy response cookie set does not match the isolated runtime")
    else:
        require(set(cookies) == {
            "ti_phase3_java_session", "ti_phase3_java_csrf", "session"
        } and len(cookies["ti_phase3_java_session"]) == 1
          and len(cookies["session"]) == 1
          and len(cookies["ti_phase3_java_csrf"]) == 2,
                "Java response cookie set does not match the isolated runtime")
    value, attributes = cookies[primary][0]
    require(bool(value) and len(value) <= 4096, "authenticated Session cookie is missing")
    require(attributes.get("httponly", "") is True or attributes.get("httponly", "") == True,
            "authenticated Session cookie must be HttpOnly")
    require(attributes.get("path") == "/", "authenticated Session cookie path must be /")
    same_site = str(attributes.get("samesite", ""))
    if side == "legacy":
        require(same_site == "",
                "legacy authenticated Session cookie SameSite contract drifted")
    else:
        require(same_site.lower() == "lax",
                "Java authenticated Session cookie SameSite must be Lax")
    persistent = bool(attributes.get("expires"))
    max_age = attributes.get("max-age")
    if max_age:
        require(re.fullmatch(r"[1-9][0-9]*", str(max_age)) is not None,
                "authenticated Session Max-Age must be positive")
        persistent = True
    if side == "java":
        require(str(max_age) == "604800",
                "Java target Session cookie lifetime is invalid")
        target_session_binding_sha256 = _java_cookie_session_binding(value)
    else:
        require(bool(attributes.get("expires")),
                "legacy remembered Session must carry an Expires attribute")
        target_session_binding_sha256 = "none"
    require(persistent == remember, "Session persistence does not match remember")
    if side == "java":
        legacy_value, legacy_attributes = cookies["session"][0]
        require(legacy_value == ""
                and str(legacy_attributes.get("max-age", "")) == "0"
                and bool(legacy_attributes.get("expires"))
                and legacy_attributes.get("path") == "/"
                and str(legacy_attributes.get("samesite", "")).lower() == "lax"
                and bool(legacy_attributes.get("httponly")),
                "legacy Session cookie must be explicitly cleared")
        csrf_issued, csrf_cleared = cookies["ti_phase3_java_csrf"]
        issued_value, issued_attributes = csrf_issued
        cleared_value, cleared_attributes = csrf_cleared
        require(re.fullmatch(r"[A-Za-z0-9_-]{43}", issued_value) is not None
                and issued_attributes.get("path") == "/"
                and str(issued_attributes.get("samesite", "")).lower() == "lax"
                and not issued_attributes.get("httponly")
                and not issued_attributes.get("max-age")
                and not issued_attributes.get("expires"),
                "Java CSRF mirror cookie must be issued before authentication")
        require(cleared_value == ""
                and str(cleared_attributes.get("max-age", "")) == "0"
                and bool(cleared_attributes.get("expires"))
                and cleared_attributes.get("path") == "/"
                and str(cleared_attributes.get("samesite", "")).lower() == "lax"
                and not cleared_attributes.get("httponly"),
                "Java CSRF mirror cookie must be cleared after authentication")
    signed_snapshot_verified = False
    if side == "legacy":
        require(flask_secret is not None, "legacy response sanitization requires guarded secret")
        require(legacy_response_epoch is not None,
                "legacy response sanitization requires its response Date")
        verify_flask_session_cookie(value, flask_secret, now=legacy_response_epoch)
        signed_snapshot_verified = True
    else:
        require(flask_secret is None, "Java response must not receive a Flask secret")
        require(legacy_response_epoch is None,
                "Java response must not receive a legacy response timestamp")
    return {
        "authenticated_session_issued": True,
        "persistent_remember_cookie": persistent,
        "legacy_signed_snapshot_verified": signed_snapshot_verified,
        "target_session_binding_sha256": target_session_binding_sha256,
    }


def sanitize_response(
    side: str,
    header_raw: bytes,
    body_raw: bytes,
    flask_secret: bytes | None = None,
    legacy_runtime_binding_sha256: str | None = None,
) -> Mapping[str, Any]:
    require(side in {"legacy", "java"}, "response side must be legacy/java")
    status, headers = _parse_http_headers(header_raw)
    require(status == 200, "only a successful login response is admissible")
    request_ids = headers.get("x-request-id", [])
    require(request_ids == [FIXED_REQUEST_ID], "response X-Request-ID does not match fixture")
    content_type = _canonical_content_type(headers)
    require(len(body_raw) <= MAX_INPUT_BYTES, "response body is too large")
    body = _strict_json(body_raw, "response body")
    stable_keys = {"status", "redirect", "remember", "needs_password_set"}
    require(set(body) == stable_keys | {"message", "data", "request_id"},
            f"{side} login response key set drifted")
    require(body["message"] == "" and body["request_id"] == FIXED_REQUEST_ID,
            f"{side} compatibility envelope request id/message is invalid")
    require(isinstance(body["data"], dict) and set(body["data"]) == {
        "redirect", "remember", "needs_password_set"
    } and body["data"] == {key: body[key] for key in (
        "redirect", "remember", "needs_password_set"
    )}, f"{side} compatibility data projection is invalid")
    require(body["status"] == "success" and body["redirect"] == FIXED_REDIRECT
            and body["remember"] is True and body["needs_password_set"] is False,
            "login response semantics do not match the id=1 remember fixture")
    legacy_response_epoch = _legacy_response_epoch(headers) if side == "legacy" else None
    if side == "legacy":
        validate_digest(legacy_runtime_binding_sha256, "legacy response runtime binding")
    else:
        require(legacy_runtime_binding_sha256 is None,
                "Java response must not receive a legacy runtime binding")
    cookie = _cookie_semantics(
        side, headers, True, flask_secret, legacy_response_epoch
    )
    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "operation_id": OPERATION_ID,
        "side": side,
        "status": status,
        "content_type": content_type,
        "normalized_body_sha256": digest_json(body),
        "authenticated_session_issued": cookie["authenticated_session_issued"],
        "remember_applied": cookie["persistent_remember_cookie"],
        "legacy_signed_snapshot_verified": cookie["legacy_signed_snapshot_verified"],
        "target_session_binding_sha256": cookie["target_session_binding_sha256"],
        "legacy_runtime_binding_sha256": (
            legacy_runtime_binding_sha256 if side == "legacy" else "none"
        ),
        "raw_headers_persisted": False,
        "raw_body_persisted": False,
        "raw_cookie_or_session_id_persisted": False,
    }


def validate_observation(
    path: pathlib.Path,
    side: str,
    expected_legacy_runtime_binding_sha256: str | None = None,
) -> Mapping[str, Any]:
    value = read_json(path, "sanitized response observation")
    expected = {
        "schema_version", "operation_id", "side", "status", "content_type",
        "normalized_body_sha256", "authenticated_session_issued", "remember_applied",
        "legacy_signed_snapshot_verified", "target_session_binding_sha256",
        "legacy_runtime_binding_sha256",
        "raw_headers_persisted", "raw_body_persisted", "raw_cookie_or_session_id_persisted",
    }
    require(set(value) == expected and value["schema_version"] == OBSERVATION_SCHEMA_VERSION
            and value["operation_id"] == OPERATION_ID and value["side"] == side,
            "response observation scope or fields are invalid")
    require(value["status"] == 200 and value["content_type"] == "application/json;charset=utf-8"
            and value["authenticated_session_issued"] is True
            and value["remember_applied"] is True,
            "response observation does not prove a successful remembered login")
    require(value["raw_headers_persisted"] is False and value["raw_body_persisted"] is False
            and value["raw_cookie_or_session_id_persisted"] is False,
            "response observation declares forbidden raw persistence")
    validate_digest(value["normalized_body_sha256"], "normalized response body")
    if side == "legacy":
        require(value["target_session_binding_sha256"] == "none",
                "legacy response must not declare a Redis Session binding")
        require(expected_legacy_runtime_binding_sha256 is not None
                and value["legacy_runtime_binding_sha256"]
                == expected_legacy_runtime_binding_sha256,
                "legacy response observation belongs to another guarded runtime")
    else:
        validate_digest(value["target_session_binding_sha256"], "target Session binding")
        require(expected_legacy_runtime_binding_sha256 is None
                and value["legacy_runtime_binding_sha256"] == "none",
                "Java response must not declare a legacy runtime binding")
    require(value["legacy_signed_snapshot_verified"] is (side == "legacy"),
            "legacy signed Session verification marker is invalid")
    return value


def _principal_binding(scope: CaptureScope, session_version: int) -> str:
    key = bytes.fromhex(scope.snapshot_digest.removeprefix("sha256:"))
    payload = (scope.fixture_id + "\0identity:1\0session-version:"
               + str(session_version)).encode("utf-8")
    return "sha256:" + hmac.new(key, payload, hashlib.sha256).hexdigest()


def _proof_scope(scope: CaptureScope) -> Mapping[str, Any]:
    return {
        "environment": scope.environment,
        "logical_run_id": scope.logical_run_id,
        "side": scope.side,
        "fixture_id": scope.fixture_id,
        "snapshot_id": scope.snapshot_id,
        "snapshot_digest": scope.snapshot_digest,
        "resource_binding_sha256": scope.resource_binding_sha256,
        "guarded_run_sha256": digest_bytes(scope.topology.run_id.encode("utf-8")),
        "guarded_project_sha256": digest_bytes(scope.topology.project.encode("utf-8")),
    }


def build_before_proof(
    scope: CaptureScope,
    database: Mapping[str, Any],
    volume: Mapping[str, Any],
) -> Mapping[str, Any]:
    require(database["has_password_set"] is False,
            "before capture requires has_password_set=false")
    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "proof_type": "phase3-login-private-before-v1",
        **_proof_scope(scope),
        "capture_sequence": scope.capture_sequence,
        "schema_sha256": database["schema_sha256"],
        "transition_guard_sha256": database["transition_guard_sha256"],
        "normalized_business_state_sha256": database["normalized_business_state_sha256"],
        "users_row_count": database["users_row_count"],
        "credential_material_sha256": database["credential_material_sha256"],
        "has_password_set": False,
        "session_version": database["session_version"],
        "last_active_state": database["last_active_state"],
        "constraint_violations": database["constraint_violations"],
        "application_volume_manifest_sha256": volume["normalized_manifest_sha256"],
        "application_volume_policy_sha256": volume["exclusion_policy_sha256"],
        "application_volume_included_entry_count": volume["included_entry_count"],
        "application_volume_excluded_rotated_file_count": volume[
            "excluded_rotated_file_count"
        ],
        "raw_password_hash_persisted": False,
        "raw_cookie_or_session_id_persisted": False,
    }


def validate_after_against_proof(
    scope: CaptureScope,
    proof: Mapping[str, Any],
    database: Mapping[str, Any],
    volume: Mapping[str, Any],
) -> None:
    expected_fields = {
        "schema_version", "proof_type", *_proof_scope(scope).keys(), "capture_sequence",
        "schema_sha256", "transition_guard_sha256", "normalized_business_state_sha256",
        "users_row_count", "credential_material_sha256", "has_password_set",
        "session_version", "last_active_state", "constraint_violations",
        "application_volume_manifest_sha256", "application_volume_policy_sha256",
        "application_volume_included_entry_count",
        "application_volume_excluded_rotated_file_count",
        "raw_password_hash_persisted", "raw_cookie_or_session_id_persisted",
    }
    require(set(proof) == expected_fields and proof["schema_version"] == PROOF_SCHEMA_VERSION
            and proof["proof_type"] == "phase3-login-private-before-v1",
            "private before proof schema mismatch")
    for key, expected in _proof_scope(scope).items():
        require(proof[key] == expected, "private before proof scope mismatch")
    require(proof["capture_sequence"] + 1 == scope.capture_sequence,
            "after capture must immediately follow its private before proof")
    require(proof["has_password_set"] is False and database["has_password_set"] is True,
            "the only allowed fixture transition is has_password_set false-to-true")
    require(proof["raw_password_hash_persisted"] is False
            and proof["raw_cookie_or_session_id_persisted"] is False,
            "private proof declares forbidden raw persistence")
    equal_fields = (
        "schema_sha256", "transition_guard_sha256", "normalized_business_state_sha256",
        "users_row_count", "credential_material_sha256", "session_version",
        "last_active_state", "constraint_violations",
    )
    require(all(proof[field] == database[field] for field in equal_fields),
            "database changed outside the sole has_password_set false-to-true transition")
    volume_fields = {
        "application_volume_manifest_sha256": "normalized_manifest_sha256",
        "application_volume_policy_sha256": "exclusion_policy_sha256",
        "application_volume_included_entry_count": "included_entry_count",
        "application_volume_excluded_rotated_file_count": "excluded_rotated_file_count",
    }
    require(all(proof[proof_field] == volume[volume_field]
                for proof_field, volume_field in volume_fields.items()),
            "application volume changed during the isolated login operation")


def _response_for_phase(
    scope: CaptureScope, observation: Mapping[str, Any] | None
) -> Mapping[str, Any]:
    if scope.phase == "before":
        require(observation is None, "before capture cannot include a response observation")
        return {
            "observed": False,
            "status": 0,
            "content_type": "none",
            "normalized_body_sha256": "none",
            "authenticated_session_issued": False,
            "remember_applied": False,
        }
    require(observation is not None, "after capture requires a sanitized response observation")
    return {
        "observed": True,
        "status": observation["status"],
        "content_type": observation["content_type"],
        "normalized_body_sha256": observation["normalized_body_sha256"],
        "authenticated_session_issued": observation["authenticated_session_issued"],
        "remember_applied": observation["remember_applied"],
    }


def build_evidence(
    scope: CaptureScope,
    database: Mapping[str, Any],
    redis: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
    application_volume_unchanged: bool,
) -> Mapping[str, Any]:
    before = scope.phase == "before"
    require(application_volume_unchanged is True,
            "persistent file write count requires an unchanged application-volume proof")
    if before:
        require(database["has_password_set"] is False, "before fixture state is not false")
        require(redis["server_session_records"] == 0,
                "before capture may not contain an authenticated server Session")
        require(redis["rate_limit_attempt_recorded"] is False
                and redis["target_session_binding_sha256"] == "none",
                "before Redis state already contains login attempt or target binding")
    else:
        require(database["has_password_set"] is True, "after fixture state is not true")
        expected_sessions = 0 if scope.side == "legacy" else 1
        require(redis["server_session_records"] == expected_sessions,
                "after server Session count does not match runtime semantics")
        require(redis["rate_limit_attempt_recorded"] is True,
                "after Redis state does not prove one login limiter attempt")
        require(observation is not None and observation["legacy_signed_snapshot_verified"]
                is (scope.side == "legacy"),
                "legacy authority profile requires an independently verified signed snapshot")
        require(observation["target_session_binding_sha256"]
                == redis["target_session_binding_sha256"],
                "response cookie does not bind to the authenticated Redis Session")
        require((scope.side == "legacy")
                is (redis["target_session_binding_sha256"] == "none"),
                "target Session binding does not match runtime storage profile")
    public_redis = {field: redis[field] for field in REDIS_EVIDENCE_FIELDS}
    session = {
        "authenticated": not before,
        "principal_binding_hmac_sha256": (
            "none" if before else _principal_binding(scope, database["session_version"])
        ),
        "session_version": "none" if before else database["session_version"],
        "remember": not before,
        "storage_profile": "none" if before else (
            "signed-client-cookie" if scope.side == "legacy" else "server-redis"
        ),
        "authority_profile": "none" if before else (
            "signed-login-snapshot" if scope.side == "legacy" else "postgresql-per-request"
        ),
        "credential_material_count": 0,
    }
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "environment": scope.environment,
        "run_id": scope.logical_run_id,
        "side": scope.side,
        "phase": scope.phase,
        "capture_sequence": scope.capture_sequence,
        "operation_id": OPERATION_ID,
        "fixture_id": scope.fixture_id,
        "snapshot_id": scope.snapshot_id,
        "snapshot_digest": scope.snapshot_digest,
        "resource_binding_sha256": scope.resource_binding_sha256,
        "auditor": AUDITOR_ID,
        "request_count": 0 if before else 1,
        "response": _response_for_phase(scope, observation),
        "state": {
            "database": {
                "schema_sha256": database["schema_sha256"],
                "normalized_business_state_sha256": database[
                    "normalized_business_state_sha256"
                ],
                "users_row_count": database["users_row_count"],
                "credential": {
                    "format_family": database["format_family"],
                    "target_parameters": database["target_parameters"],
                    "verifies_fixture_password": database["verifies_fixture_password"],
                    "has_password_set": database["has_password_set"],
                    "session_version": database["session_version"],
                    "last_active_state": database["last_active_state"],
                },
                "constraint_violations": database["constraint_violations"],
                "unexpected_row_changes": 0,
            },
            "session": session,
            "redis": public_redis,
            "external": {
                "persistent_file_writes": 0,
                "queue": configuration_only_boundary(
                    QUEUE_POLICY, QUEUE_BOUNDARY_POLICY_SHA256, "queue"
                ),
                "object_store": configuration_only_boundary(
                    OBJECT_STORE_POLICY,
                    OBJECT_STORE_BOUNDARY_POLICY_SHA256,
                    "object store",
                ),
                "external_sink": configuration_only_boundary(
                    EXTERNAL_POLICY,
                    EXTERNAL_SINK_BOUNDARY_POLICY_SHA256,
                    "external sink",
                ),
            },
        },
    }


def _execute_sanitize(args: argparse.Namespace) -> int:
    header_raw = _private_regular_file(args.headers_file, "response headers",
                                       MAX_HTTP_HEADER_BYTES)
    body_raw = _private_regular_file(args.body_file, "response body")
    flask_secret: bytes | None = None
    legacy_runtime_binding_sha256: str | None = None
    if args.side == "legacy":
        require(args.legacy_env_file is not None,
                "legacy SANITIZE_RESPONSE requires --legacy-env-file")
        topology = guard_env_file(args.legacy_env_file)
        require(topology.environment in {"local", "test"}, "local/test environment is required")
        secret_path = pathlib.Path(topology.values["TI_PHASE3_LEGACY_FLASK_SECRET_FILE"])
        flask_secret = _private_regular_file(secret_path, "legacy Flask secret", 256).rstrip(b"\r\n")
        legacy_runtime_binding_sha256 = _legacy_observation_scope(topology)
    else:
        require(args.legacy_env_file is None,
                "Java SANITIZE_RESPONSE must not receive --legacy-env-file")
    observation = sanitize_response(
        args.side,
        header_raw,
        body_raw,
        flask_secret,
        legacy_runtime_binding_sha256,
    )
    write_json_atomic(args.output, observation)
    print(json.dumps({
        "operation": "SANITIZE_RESPONSE",
        "side": args.side,
        "outcome": "pass",
        "raw_cookie_or_session_id_persisted": False,
    }, separators=(",", ":")))
    return 0


def _execute_capture(args: argparse.Namespace) -> int:
    scope = _resolve_capture_scope(args)
    _validate_output_path(args.evidence, "evidence output")
    if scope.phase == "before":
        require(args.observation is None, "before capture forbids --observation")
        _validate_output_path(args.before_proof, "private before proof")
    else:
        require(args.observation is not None, "after capture requires --observation")
    runner = _assert_selected_runtime(scope)
    database = collect_database(scope, runner)
    redis = collect_redis(scope, runner)
    volume = collect_application_volume(scope, runner)
    observation = None if args.observation is None else validate_observation(
        args.observation,
        scope.side,
        _legacy_observation_scope(scope.topology) if scope.side == "legacy" else None,
    )
    if scope.phase == "before":
        proof = build_before_proof(scope, database, volume)
        evidence = build_evidence(scope, database, redis, None, True)
        write_json_atomic(args.before_proof, proof)
    else:
        proof = read_json(args.before_proof, "private before proof")
        validate_after_against_proof(scope, proof, database, volume)
        evidence = build_evidence(scope, database, redis, observation, True)
    write_json_atomic(args.evidence, evidence)
    print(json.dumps({
        "operation": "CAPTURE_LOGIN_WRITE_EVIDENCE",
        "side": scope.side,
        "phase": scope.phase,
        "capture_sequence": scope.capture_sequence,
        "outcome": "pass",
        "writes_issued_by_collector": 0,
        "raw_password_hash_persisted": False,
        "raw_cookie_or_session_id_persisted": False,
    }, separators=(",", ":")))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    sanitize = commands.add_parser("SANITIZE_RESPONSE")
    sanitize.add_argument("--side", required=True, choices=("legacy", "java"))
    sanitize.add_argument("--headers-file", required=True, type=pathlib.Path)
    sanitize.add_argument("--body-file", required=True, type=pathlib.Path)
    sanitize.add_argument("--legacy-env-file", type=pathlib.Path)
    sanitize.add_argument("--output", required=True, type=pathlib.Path)

    capture = commands.add_parser("CAPTURE")
    capture.add_argument("--environment", required=True, choices=("local", "test"))
    capture.add_argument("--side", required=True, choices=("legacy", "java"))
    capture.add_argument("--phase", required=True, choices=("before", "after"))
    capture.add_argument("--capture-sequence", required=True, type=int)
    capture.add_argument("--run-id", required=True)
    capture.add_argument("--fixture-id", required=True)
    capture.add_argument("--snapshot-id", required=True)
    capture.add_argument("--snapshot-digest", required=True)
    capture.add_argument("--legacy-env-file", required=True, type=pathlib.Path)
    capture.add_argument("--java-env-file", required=True, type=pathlib.Path)
    capture.add_argument("--legacy-fingerprint", required=True, type=pathlib.Path)
    capture.add_argument("--java-fingerprint", required=True, type=pathlib.Path)
    capture.add_argument("--evidence", required=True, type=pathlib.Path)
    capture.add_argument("--before-proof", required=True, type=pathlib.Path)
    capture.add_argument("--observation", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.operation == "SANITIZE_RESPONSE":
            return _execute_sanitize(args)
        return _execute_capture(args)
    except (EvidenceError, GuardError, RehearsalError, OSError, UnicodeError, ValueError,
            json.JSONDecodeError) as exc:
        print(json.dumps({
            "operation": "CAPTURE_LOGIN_WRITE_EVIDENCE",
            "outcome": "rejected",
            "error": str(exc),
        }, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
