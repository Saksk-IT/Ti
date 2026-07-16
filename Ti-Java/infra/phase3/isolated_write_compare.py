#!/usr/bin/env python3
"""Offline, fail-closed Phase 3 comparator for isolated POST /api/login evidence."""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


INPUT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_VERSION = "1.0.0"
OPERATION_ID = "identity.auth.login"
HTTP_METHOD = "POST"
HTTP_PATH = "/api/login"
QUEUE_BOUNDARY_POLICY_SHA256 = (
    "sha256:72292cd44bf85870a7398c1cbcb10f5fcff7b4e17a75e7b981da08889399399e"
)
OBJECT_STORE_BOUNDARY_POLICY_SHA256 = (
    "sha256:bfdd689deb6a0c3f45aca1da5b1baf9e3d985197327e35a2a02e273ee3db839e"
)
EXTERNAL_SINK_BOUNDARY_POLICY_SHA256 = (
    "sha256:e1fc1f413780c4428da382a5d92cfa38c7a776c51537f0021879d8311b65d36c"
)
MAX_INPUT_BYTES = 1024 * 1024
MAX_DIFFERENCES = 200
FINGERPRINT_FIELDS = ("database", "redis", "volume")
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
PRODUCTION_MARKER_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:prod(?:uction)?|live)(?:$|[^a-z0-9])", re.IGNORECASE
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(r"\b(?:sk-|gh[pousr]_)[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"\b(?:password|passwd|token|secret|openid|session|cookie)\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
)


class CompareError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class DuplicateJsonKeyError(ValueError):
    pass


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CompareError("CLI_ARGUMENT_INVALID", "命令参数无效；请查看 --help。")


def reject_json_constant(value: str) -> None:
    raise ValueError(value)


def strict_object(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    value: Dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise DuplicateJsonKeyError(key)
        value[key] = child
    return value


def strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        parse_float=lambda value: (_ for _ in ()).throw(ValueError(value)),
        parse_constant=reject_json_constant,
        object_pairs_hook=strict_object,
    )


def has_unsafe_text_character(value: str) -> bool:
    return any(
        ord(character) < 32
        or ord(character) == 127
        or 0xD800 <= ord(character) <= 0xDFFF
        for character in value
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def contains_sensitive_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS)


def reject_production_marker(value: str, label: str) -> None:
    if PRODUCTION_MARKER_RE.search(value):
        raise CompareError("PRODUCTION_FORBIDDEN", f"{label} 含生产环境标识。")


def validate_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise CompareError("INVALID_IDENTIFIER", f"{label} 必须是非空安全标识。")
    reject_production_marker(value, label)
    return value


def validate_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CompareError("INVALID_DIGEST", f"{label} 必须是 sha256 digest。")
    return value


def validate_count(value: Any, label: str, maximum: int = 10_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise CompareError("INVALID_EVIDENCE_VALUE", f"{label} 必须是有界非负整数。")
    return value


def expect_exact_keys(document: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    if set(document) != set(expected):
        raise CompareError("UNKNOWN_INPUT_FIELD", f"{label}字段集合不符合版本化契约。")


def read_limited_file(path_text: str, label: str) -> bytes:
    descriptor: Optional[int] = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path_text, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CompareError("INPUT_NOT_FILE", f"{label}必须是普通文件。")
        if metadata.st_size > MAX_INPUT_BYTES:
            raise CompareError("INPUT_TOO_LARGE", f"{label}超出 1 MiB 限制。")
        chunks = bytearray()
        while len(chunks) <= MAX_INPUT_BYTES:
            chunk = os.read(descriptor, min(65536, MAX_INPUT_BYTES + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > MAX_INPUT_BYTES:
            raise CompareError("INPUT_TOO_LARGE", f"{label}超出 1 MiB 限制。")
        return bytes(chunks)
    except CompareError:
        raise
    except OSError as error:
        raise CompareError("INPUT_UNREADABLE", f"无法读取{label}。") from error
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def read_json_file(path_text: str, label: str) -> Tuple[Dict[str, Any], bytes]:
    raw = read_limited_file(path_text, label)
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateJsonKeyError, ValueError, RecursionError) as error:
        raise CompareError("INVALID_JSON_INPUT", f"{label}不是有效 UTF-8 JSON。") from error
    if not isinstance(value, dict):
        raise CompareError("INVALID_JSON_INPUT", f"{label}顶层必须是对象。")
    return value, raw


def validate_report_target(path_text: str) -> None:
    if (
        not path_text
        or len(path_text) > 4096
        or has_unsafe_text_character(path_text)
        or pathlib.Path(path_text).suffix.lower() != ".json"
    ):
        raise CompareError("INVALID_REPORT_PATH", "报告路径必须是安全的 .json 文件。")
    target = pathlib.Path(path_text)
    try:
        if target.exists():
            raise CompareError("REPORT_EXISTS", "报告路径已存在；禁止覆盖证据。")
        if not target.parent.is_dir():
            raise CompareError("REPORT_DIRECTORY_MISSING", "报告父目录必须预先存在。")
    except CompareError:
        raise
    except OSError as error:
        raise CompareError("INVALID_REPORT_PATH", "报告路径不可访问。") from error


def validate_fingerprint(path_text: str, environment: str, side: str) -> Tuple[Dict[str, str], bytes]:
    document, raw = read_json_file(path_text, f"{side} 环境指纹")
    expect_exact_keys(
        document,
        ("schema_version", "environment", "side") + FINGERPRINT_FIELDS,
        f"{side} 环境指纹",
    )
    if document["schema_version"] != INPUT_SCHEMA_VERSION:
        raise CompareError("UNSUPPORTED_INPUT_VERSION", "环境指纹版本不受支持。")
    if document["environment"] != environment or document["side"] != side:
        raise CompareError("FINGERPRINT_SCOPE_MISMATCH", "环境指纹作用域不匹配。")
    result: Dict[str, str] = {}
    for field in FINGERPRINT_FIELDS:
        value = document[field]
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 512
            or has_unsafe_text_character(value)
        ):
            raise CompareError("EMPTY_FINGERPRINT", "数据库、Redis 和卷指纹均不能为空。")
        reject_production_marker(value, "环境指纹")
        if contains_sensitive_value(value):
            raise CompareError("SENSITIVE_FINGERPRINT", "环境指纹疑似包含敏感值。")
        result[field] = value
    return result, raw


def assert_independent_fingerprints(legacy: Mapping[str, str], java: Mapping[str, str]) -> None:
    values = list(legacy.values()) + list(java.values())
    if len(set(values)) != len(values):
        raise CompareError(
            "SHARED_ENVIRONMENT_FINGERPRINT",
            "两边数据库、Redis、卷指纹必须全部非空且六个值彼此不同。",
        )


def resource_binding(fingerprint: Mapping[str, str]) -> str:
    payload = b"ti-phase3-isolated-write-fingerprint-v1\0" + b"\0".join(
        fingerprint[field].encode("utf-8") for field in FINGERPRINT_FIELDS
    )
    return sha256_bytes(payload)


def validate_content_type(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 128 or has_unsafe_text_character(value):
        raise CompareError("INVALID_EVIDENCE_VALUE", "response.content_type 无效。")
    parts = [part.strip().lower() for part in value.split(";")]
    if parts[0] != "application/json":
        raise CompareError("INVALID_EVIDENCE_VALUE", "登录响应必须声明 application/json。")
    parameters: Dict[str, str] = {}
    for part in parts[1:]:
        if not part or "=" not in part:
            raise CompareError("INVALID_EVIDENCE_VALUE", "登录响应 Content-Type 参数无效。")
        key, parameter_value = (item.strip() for item in part.split("=", 1))
        if key in parameters:
            raise CompareError("INVALID_EVIDENCE_VALUE", "登录响应 Content-Type 参数重复。")
        parameters[key] = parameter_value.strip('"')
    if parameters != {"charset": "utf-8"}:
        raise CompareError("INVALID_EVIDENCE_VALUE", "登录响应必须明确使用 UTF-8。")
    return "application/json;charset=utf-8"


def validate_response(value: Any, phase: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "response 必须是对象。")
    expect_exact_keys(
        value,
        (
            "observed",
            "status",
            "content_type",
            "normalized_body_sha256",
            "authenticated_session_issued",
            "remember_applied",
        ),
        "response",
    )
    if not isinstance(value["observed"], bool):
        raise CompareError("INVALID_EVIDENCE_VALUE", "response.observed 必须是布尔值。")
    status = validate_count(value["status"], "response.status", 599)
    if not isinstance(value["authenticated_session_issued"], bool) or not isinstance(
        value["remember_applied"], bool
    ):
        raise CompareError("INVALID_EVIDENCE_VALUE", "响应 Session 标志必须是布尔值。")
    if phase == "before":
        if value != {
            "observed": False,
            "status": 0,
            "content_type": "none",
            "normalized_body_sha256": "none",
            "authenticated_session_issued": False,
            "remember_applied": False,
        }:
            raise CompareError("INVALID_EVIDENCE_PHASE", "before 证据不能包含写响应。")
        return dict(value)
    if not value["observed"] or status == 0:
        raise CompareError("INVALID_EVIDENCE_PHASE", "after 证据必须包含一次已观察响应。")
    return {
        "observed": True,
        "status": status,
        "content_type": validate_content_type(value["content_type"]),
        "normalized_body_sha256": validate_digest(
            value["normalized_body_sha256"], "response.normalized_body_sha256"
        ),
        "authenticated_session_issued": value["authenticated_session_issued"],
        "remember_applied": value["remember_applied"],
    }


def validate_credential(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "database.credential 必须是对象。")
    expect_exact_keys(
        value,
        (
            "format_family",
            "target_parameters",
            "verifies_fixture_password",
            "has_password_set",
            "session_version",
            "last_active_state",
        ),
        "database.credential",
    )
    if value["format_family"] not in ("werkzeug-scrypt", "werkzeug-pbkdf2"):
        raise CompareError("INVALID_EVIDENCE_VALUE", "凭据格式族不在批准范围。")
    if value["target_parameters"] not in ("32768:8:1", "not-target"):
        raise CompareError("INVALID_EVIDENCE_VALUE", "凭据参数摘要无效。")
    if not isinstance(value["verifies_fixture_password"], bool) or not isinstance(
        value["has_password_set"], bool
    ):
        raise CompareError("INVALID_EVIDENCE_VALUE", "凭据语义标志必须是布尔值。")
    if value["last_active_state"] not in ("null", "present"):
        raise CompareError("INVALID_EVIDENCE_VALUE", "last_active_state 无效。")
    return {
        **value,
        "session_version": validate_count(
            value["session_version"], "database.credential.session_version", 2_147_483_647
        ),
    }


def validate_database(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "state.database 必须是对象。")
    expect_exact_keys(
        value,
        (
            "schema_sha256",
            "normalized_business_state_sha256",
            "users_row_count",
            "credential",
            "constraint_violations",
            "unexpected_row_changes",
        ),
        "state.database",
    )
    return {
        "schema_sha256": validate_digest(value["schema_sha256"], "database.schema_sha256"),
        "normalized_business_state_sha256": validate_digest(
            value["normalized_business_state_sha256"],
            "database.normalized_business_state_sha256",
        ),
        "users_row_count": validate_count(value["users_row_count"], "database.users_row_count"),
        "credential": validate_credential(value["credential"]),
        "constraint_violations": validate_count(
            value["constraint_violations"], "database.constraint_violations"
        ),
        "unexpected_row_changes": validate_count(
            value["unexpected_row_changes"], "database.unexpected_row_changes"
        ),
    }


def validate_session(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "state.session 必须是对象。")
    expect_exact_keys(
        value,
        (
            "authenticated",
            "principal_binding_hmac_sha256",
            "session_version",
            "remember",
            "storage_profile",
            "authority_profile",
            "credential_material_count",
        ),
        "state.session",
    )
    if not isinstance(value["authenticated"], bool) or not isinstance(value["remember"], bool):
        raise CompareError("INVALID_EVIDENCE_VALUE", "Session 状态必须是布尔值。")
    if value["storage_profile"] not in ("none", "signed-client-cookie", "server-redis"):
        raise CompareError("INVALID_EVIDENCE_VALUE", "Session 存储类型无效。")
    if value["authority_profile"] not in (
        "none",
        "signed-login-snapshot",
        "postgresql-per-request",
    ):
        raise CompareError("INVALID_EVIDENCE_VALUE", "Session authority 类型无效。")
    binding = value["principal_binding_hmac_sha256"]
    version = value["session_version"]
    if value["authenticated"]:
        validate_digest(binding, "session.principal_binding_hmac_sha256")
        version = validate_count(version, "session.session_version", 2_147_483_647)
    elif binding != "none" or version != "none" or value["remember"]:
        raise CompareError("INVALID_EVIDENCE_VALUE", "未认证 Session 不能携带身份绑定。")
    return {
        **value,
        "session_version": version,
        "credential_material_count": validate_count(
            value["credential_material_count"], "session.credential_material_count"
        ),
    }


def validate_redis(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "state.redis 必须是对象。")
    expect_exact_keys(
        value,
        (
            "business_fact_keys",
            "server_session_records",
            "rate_limit_attempt_recorded",
            "rebuildable_only",
            "unexpected_keys",
        ),
        "state.redis",
    )
    if not isinstance(value["rate_limit_attempt_recorded"], bool) or not isinstance(
        value["rebuildable_only"], bool
    ):
        raise CompareError("INVALID_EVIDENCE_VALUE", "Redis 语义标志必须是布尔值。")
    return {
        "business_fact_keys": validate_count(value["business_fact_keys"], "redis.business_fact_keys"),
        "server_session_records": validate_count(
            value["server_session_records"], "redis.server_session_records"
        ),
        "rate_limit_attempt_recorded": value["rate_limit_attempt_recorded"],
        "rebuildable_only": value["rebuildable_only"],
        "unexpected_keys": validate_count(value["unexpected_keys"], "redis.unexpected_keys"),
    }


def validate_configuration_only_boundary(
    value: Any, label: str, expected_policy_sha256: str
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", f"{label} 必须是对象。")
    expect_exact_keys(
        value,
        ("runtime_observation_performed", "configured", "boundary_policy_sha256"),
        label,
    )
    if value["runtime_observation_performed"] is not False or value["configured"] is not False:
        raise CompareError(
            "INVALID_EVIDENCE_VALUE",
            f"{label} 只能声明未执行运行态观测且未配置写入端点。",
        )
    policy_sha256 = validate_digest(
        value["boundary_policy_sha256"], f"{label}.boundary_policy_sha256"
    )
    if policy_sha256 != expected_policy_sha256:
        raise CompareError("INVALID_EVIDENCE_VALUE", f"{label} 策略摘要不匹配。")
    return {
        "runtime_observation_performed": False,
        "configured": False,
        "boundary_policy_sha256": expected_policy_sha256,
    }


def validate_external(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "state.external 必须是对象。")
    expect_exact_keys(
        value,
        ("persistent_file_writes", "queue", "object_store", "external_sink"),
        "state.external",
    )
    return {
        "persistent_file_writes": validate_count(
            value["persistent_file_writes"], "external.persistent_file_writes"
        ),
        "queue": validate_configuration_only_boundary(
            value["queue"], "external.queue", QUEUE_BOUNDARY_POLICY_SHA256
        ),
        "object_store": validate_configuration_only_boundary(
            value["object_store"],
            "external.object_store",
            OBJECT_STORE_BOUNDARY_POLICY_SHA256,
        ),
        "external_sink": validate_configuration_only_boundary(
            value["external_sink"],
            "external.external_sink",
            EXTERNAL_SINK_BOUNDARY_POLICY_SHA256,
        ),
    }


def validate_state(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CompareError("INVALID_EVIDENCE_VALUE", "state 必须是对象。")
    expect_exact_keys(value, ("database", "session", "redis", "external"), "state")
    return {
        "database": validate_database(value["database"]),
        "session": validate_session(value["session"]),
        "redis": validate_redis(value["redis"]),
        "external": validate_external(value["external"]),
    }


def validate_evidence(
    path_text: str,
    environment: str,
    run_id: str,
    fixture_id: str,
    snapshot_id: str,
    snapshot_digest: str,
    side: str,
    phase: str,
    expected_sequence: int,
    expected_resource_binding: str,
) -> Tuple[Dict[str, Any], bytes]:
    document, raw = read_json_file(path_text, f"{side} {phase} 写状态证据")
    expect_exact_keys(
        document,
        (
            "schema_version",
            "environment",
            "run_id",
            "side",
            "phase",
            "capture_sequence",
            "operation_id",
            "fixture_id",
            "snapshot_id",
            "snapshot_digest",
            "resource_binding_sha256",
            "auditor",
            "request_count",
            "response",
            "state",
        ),
        f"{side} {phase} 写状态证据",
    )
    if document["schema_version"] != INPUT_SCHEMA_VERSION:
        raise CompareError("UNSUPPORTED_INPUT_VERSION", "写状态证据版本不受支持。")
    scope = (
        document["environment"],
        document["run_id"],
        document["side"],
        document["phase"],
        document["operation_id"],
        document["fixture_id"],
        document["snapshot_id"],
        document["snapshot_digest"],
    )
    expected_scope = (
        environment,
        run_id,
        side,
        phase,
        OPERATION_ID,
        fixture_id,
        snapshot_id,
        snapshot_digest,
    )
    if scope != expected_scope:
        raise CompareError("EVIDENCE_SCOPE_MISMATCH", "写状态证据作用域不匹配。")
    if document["resource_binding_sha256"] != expected_resource_binding:
        raise CompareError("EVIDENCE_RESOURCE_MISMATCH", "证据未绑定到声明的独立资源指纹。")
    if document["capture_sequence"] != expected_sequence:
        raise CompareError("NON_SERIAL_EVIDENCE", "采样序号不符合声明的完整串行执行顺序。")
    expected_request_count = 0 if phase == "before" else 1
    if document["request_count"] != expected_request_count:
        raise CompareError("INVALID_REQUEST_COUNT", "每边必须恰好执行一次登录写请求。")
    auditor = validate_identifier(document["auditor"], "auditor")
    return {
        "auditor": auditor,
        "response": validate_response(document["response"], phase),
        "state": validate_state(document["state"]),
    }, raw


def value_summary(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        kind = "boolean"
    elif isinstance(value, int):
        kind = "integer"
    elif isinstance(value, str):
        kind = "string"
    elif isinstance(value, list):
        kind = "array"
    elif isinstance(value, dict):
        kind = "object"
    else:
        kind = type(value).__name__
    encoded = canonical_bytes(value)
    return {"type": kind, "sha256": sha256_bytes(encoded), "encoded_size": len(encoded)}


def append_difference(
    differences: List[Dict[str, Any]],
    scope: str,
    kind: str,
    path: Sequence[str],
    legacy: Any,
    java: Any,
) -> None:
    if len(differences) >= MAX_DIFFERENCES:
        return
    differences.append(
        {
            "scope": scope,
            "kind": kind,
            "path": "/" + "/".join(path),
            "legacy": value_summary(legacy),
            "java": value_summary(java),
        }
    )


def compare_values(
    legacy: Any,
    java: Any,
    differences: List[Dict[str, Any]],
    scope: str,
    path: Tuple[str, ...] = (),
) -> None:
    if type(legacy) is not type(java):
        append_difference(differences, scope, "type", path, legacy, java)
        return
    if isinstance(legacy, dict):
        for key in sorted(legacy):
            compare_values(legacy[key], java[key], differences, scope, path + (key,))
        return
    if legacy != java:
        append_difference(differences, scope, "value", path, legacy, java)


def invariant_difference(
    differences: List[Dict[str, Any]], side: str, path: Sequence[str], actual: Any, expected: Any
) -> None:
    append_difference(differences, "invariant", "value", (side, *path), actual, expected)


def normalized_session(session: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "authenticated": session["authenticated"],
        "principal_binding_hmac_sha256": session["principal_binding_hmac_sha256"],
        "session_version": session["session_version"],
        "remember": session["remember"],
        "credential_material_count": session["credential_material_count"],
    }


def normalized_redis(redis: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "business_fact_keys": redis["business_fact_keys"],
        "rate_limit_attempt_recorded": redis["rate_limit_attempt_recorded"],
        "rebuildable_only": redis["rebuildable_only"],
        "unexpected_keys": redis["unexpected_keys"],
    }


def enforce_side_invariants(
    side: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    differences: List[Dict[str, Any]],
) -> None:
    before_state = before["state"]
    after_state = after["state"]
    before_database = before_state["database"]
    after_database = after_state["database"]
    before_session = before_state["session"]
    after_session = after_state["session"]
    before_redis = before_state["redis"]
    after_redis = after_state["redis"]

    required_equal = (
        "schema_sha256",
        "normalized_business_state_sha256",
        "users_row_count",
    )
    for field in required_equal:
        if before_database[field] != after_database[field]:
            invariant_difference(
                differences, side, ("database", field), after_database[field], before_database[field]
            )
    before_credential = before_database["credential"]
    after_credential = after_database["credential"]
    for field in (
        "format_family",
        "target_parameters",
        "verifies_fixture_password",
        "session_version",
        "last_active_state",
    ):
        if before_credential[field] != after_credential[field]:
            invariant_difference(
                differences,
                side,
                ("database", "credential", field),
                after_credential[field],
                before_credential[field],
            )
    for phase_name, state in (("before", before_state), ("after", after_state)):
        expected_zero = {
            ("database", "constraint_violations"): state["database"]["constraint_violations"],
            ("database", "unexpected_row_changes"): state["database"]["unexpected_row_changes"],
            ("redis", "business_fact_keys"): state["redis"]["business_fact_keys"],
            ("redis", "unexpected_keys"): state["redis"]["unexpected_keys"],
        }
        expected_zero[("external", "persistent_file_writes")] = state["external"][
            "persistent_file_writes"
        ]
        for path, actual in expected_zero.items():
            if actual != 0:
                invariant_difference(differences, side, (phase_name, *path), actual, 0)
        if state["redis"]["rebuildable_only"] is not True:
            invariant_difference(
                differences,
                side,
                (phase_name, "redis", "rebuildable_only"),
                state["redis"]["rebuildable_only"],
                True,
            )

    expected_before_session = {
        "authenticated": False,
        "principal_binding_hmac_sha256": "none",
        "session_version": "none",
        "remember": False,
        "storage_profile": "none",
        "authority_profile": "none",
        "credential_material_count": 0,
    }
    if before_session != expected_before_session:
        compare_values(
            before_session,
            expected_before_session,
            differences,
            "invariant",
            (side, "before", "session"),
        )

    response = after["response"]
    expected_storage = "signed-client-cookie" if side == "legacy" else "server-redis"
    expected_authority = "signed-login-snapshot" if side == "legacy" else "postgresql-per-request"
    expected_server_sessions = 0 if side == "legacy" else 1
    checks = (
        (("response", "status"), response["status"], 200),
        (
            ("response", "authenticated_session_issued"),
            response["authenticated_session_issued"],
            True,
        ),
        (("session", "authenticated"), after_session["authenticated"], True),
        (("session", "storage_profile"), after_session["storage_profile"], expected_storage),
        (("session", "authority_profile"), after_session["authority_profile"], expected_authority),
        (("session", "credential_material_count"), after_session["credential_material_count"], 0),
        (
            ("redis", "server_session_records"),
            after_redis["server_session_records"],
            expected_server_sessions,
        ),
        (
            ("redis", "rate_limit_attempt_recorded"),
            after_redis["rate_limit_attempt_recorded"],
            True,
        ),
        (
            ("database", "before", "credential", "format_family"),
            before_credential["format_family"],
            "werkzeug-scrypt",
        ),
        (
            ("database", "before", "credential", "target_parameters"),
            before_credential["target_parameters"],
            "32768:8:1",
        ),
        (
            ("database", "before", "credential", "verifies_fixture_password"),
            before_credential["verifies_fixture_password"],
            True,
        ),
        (
            ("database", "before", "credential", "has_password_set"),
            before_credential["has_password_set"],
            False,
        ),
        (
            ("database", "before", "credential", "last_active_state"),
            before_credential["last_active_state"],
            "null",
        ),
        (
            ("database", "credential", "format_family"),
            after_credential["format_family"],
            "werkzeug-scrypt",
        ),
        (
            ("database", "credential", "target_parameters"),
            after_credential["target_parameters"],
            "32768:8:1",
        ),
        (
            ("database", "credential", "verifies_fixture_password"),
            after_credential["verifies_fixture_password"],
            True,
        ),
        (
            ("database", "credential", "has_password_set"),
            after_credential["has_password_set"],
            True,
        ),
        (
            ("database", "credential", "last_active_state"),
            after_credential["last_active_state"],
            "null",
        ),
    )
    for path, actual, expected in checks:
        if actual != expected:
            invariant_difference(differences, side, path, actual, expected)
    if after_session["remember"] != response["remember_applied"]:
        invariant_difference(
            differences,
            side,
            ("session", "remember"),
            after_session["remember"],
            response["remember_applied"],
        )
    if after_session["session_version"] != after_credential["session_version"]:
        invariant_difference(
            differences,
            side,
            ("session", "session_version"),
            after_session["session_version"],
            after_credential["session_version"],
        )


def fingerprint_report(fingerprint: Mapping[str, str]) -> Dict[str, str]:
    return {
        f"{field}_sha256": sha256_bytes(fingerprint[field].encode("utf-8"))
        for field in FINGERPRINT_FIELDS
    }


def safe_state_summary(evidence: Mapping[str, Any], raw: bytes) -> Dict[str, str]:
    state = evidence["state"]
    return {
        "evidence_file_sha256": sha256_bytes(raw),
        "auditor_sha256": sha256_bytes(evidence["auditor"].encode("utf-8")),
        "database_sha256": sha256_bytes(canonical_bytes(state["database"])),
        "session_sha256": sha256_bytes(canonical_bytes(normalized_session(state["session"]))),
        "redis_sha256": sha256_bytes(canonical_bytes(normalized_redis(state["redis"]))),
        "external_boundary_sha256": sha256_bytes(canonical_bytes(state["external"])),
        "response_sha256": sha256_bytes(canonical_bytes(evidence["response"])),
    }


def ensure_report_safe(report: Mapping[str, Any]) -> None:
    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and contains_sensitive_value(value):
            raise CompareError("SENSITIVE_OUTPUT_BLOCKED", "最终报告敏感扫描失败。")

    visit(report)


def write_report_atomic(path_text: str, report: Mapping[str, Any]) -> None:
    target = pathlib.Path(path_text)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    temporary_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".isolated-write-compare-", suffix=".tmp", dir=str(target.parent), delete=False
        ) as handle:
            temporary_name = handle.name
            os.chmod(temporary_name, 0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_name, target)
    except FileExistsError as error:
        raise CompareError("REPORT_EXISTS", "报告路径已存在；禁止覆盖证据。") from error
    except OSError as error:
        raise CompareError("REPORT_WRITE_FAILED", "无法原子写入报告。") from error
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass


def expected_sequences(order: str) -> Dict[Tuple[str, str], int]:
    sides = ("legacy", "java") if order == "legacy-then-java" else ("java", "legacy")
    capture_points = tuple(
        (side, phase) for side in sides for phase in ("before", "after")
    )
    return {capture_point: sequence for sequence, capture_point in enumerate(capture_points, 1)}


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description="Ti-Java 本地/测试隔离登录写终态离线比较器（不发送 HTTP）"
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    command = subparsers.add_parser(
        "ISOLATED_WRITE_COMPARE", help="离线比较两套独立资源上的 POST /api/login 证据"
    )
    command.add_argument("--environment", required=True, choices=("local", "test"))
    command.add_argument("--operation-id", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("--fixture-id", required=True)
    command.add_argument("--snapshot-id", required=True)
    command.add_argument("--snapshot-digest", required=True)
    command.add_argument("--legacy-artifact-digest", required=True)
    command.add_argument("--java-artifact-digest", required=True)
    command.add_argument(
        "--execution-order", required=True, choices=("legacy-then-java", "java-then-legacy")
    )
    command.add_argument("--legacy-fingerprint", required=True)
    command.add_argument("--java-fingerprint", required=True)
    command.add_argument("--legacy-before-evidence", required=True)
    command.add_argument("--legacy-after-evidence", required=True)
    command.add_argument("--java-before-evidence", required=True)
    command.add_argument("--java-after-evidence", required=True)
    command.add_argument("--report", required=True)
    return parser


def execute(args: argparse.Namespace) -> int:
    if args.operation_id != OPERATION_ID:
        raise CompareError("OPERATION_FORBIDDEN", "该版本只允许 identity.auth.login。")
    for path_value in (
        args.legacy_fingerprint,
        args.java_fingerprint,
        args.legacy_before_evidence,
        args.legacy_after_evidence,
        args.java_before_evidence,
        args.java_after_evidence,
        args.report,
    ):
        reject_production_marker(path_value, "输入或输出路径")
    validate_report_target(args.report)
    run_id = validate_identifier(args.run_id, "run-id")
    fixture_id = validate_identifier(args.fixture_id, "fixture-id")
    snapshot_id = validate_identifier(args.snapshot_id, "snapshot-id")
    snapshot_digest = validate_digest(args.snapshot_digest, "snapshot-digest")
    legacy_artifact = validate_digest(args.legacy_artifact_digest, "legacy-artifact-digest")
    java_artifact = validate_digest(args.java_artifact_digest, "java-artifact-digest")
    if legacy_artifact == java_artifact:
        raise CompareError("SHARED_ARTIFACT_DIGEST", "两个运行时制品 digest 必须不同。")

    legacy_fingerprint, legacy_fingerprint_raw = validate_fingerprint(
        args.legacy_fingerprint, args.environment, "legacy"
    )
    java_fingerprint, java_fingerprint_raw = validate_fingerprint(
        args.java_fingerprint, args.environment, "java"
    )
    assert_independent_fingerprints(legacy_fingerprint, java_fingerprint)
    fingerprints = {"legacy": legacy_fingerprint, "java": java_fingerprint}
    sequences = expected_sequences(args.execution_order)
    evidence_paths = {
        ("legacy", "before"): args.legacy_before_evidence,
        ("legacy", "after"): args.legacy_after_evidence,
        ("java", "before"): args.java_before_evidence,
        ("java", "after"): args.java_after_evidence,
    }
    evidence: Dict[Tuple[str, str], Dict[str, Any]] = {}
    evidence_raw: Dict[Tuple[str, str], bytes] = {}
    for side, phase in evidence_paths:
        document, raw = validate_evidence(
            evidence_paths[(side, phase)],
            args.environment,
            run_id,
            fixture_id,
            snapshot_id,
            snapshot_digest,
            side,
            phase,
            sequences[(side, phase)],
            resource_binding(fingerprints[side]),
        )
        evidence[(side, phase)] = document
        evidence_raw[(side, phase)] = raw

    differences: List[Dict[str, Any]] = []
    legacy_before = evidence[("legacy", "before")]
    legacy_after = evidence[("legacy", "after")]
    java_before = evidence[("java", "before")]
    java_after = evidence[("java", "after")]

    compare_values(
        legacy_before["state"]["database"],
        java_before["state"]["database"],
        differences,
        "initial_database",
    )
    compare_values(
        legacy_after["state"]["database"],
        java_after["state"]["database"],
        differences,
        "final_database",
    )
    compare_values(legacy_after["response"], java_after["response"], differences, "response")
    compare_values(
        normalized_session(legacy_after["state"]["session"]),
        normalized_session(java_after["state"]["session"]),
        differences,
        "session",
    )
    compare_values(
        normalized_redis(legacy_after["state"]["redis"]),
        normalized_redis(java_after["state"]["redis"]),
        differences,
        "redis",
    )
    compare_values(
        legacy_after["state"]["external"],
        java_after["state"]["external"],
        differences,
        "external",
    )
    enforce_side_invariants("legacy", legacy_before, legacy_after, differences)
    enforce_side_invariants("java", java_before, java_after, differences)

    difference_count = len(differences)
    summaries = {
        side: {
            phase: safe_state_summary(
                evidence[(side, phase)], evidence_raw[(side, phase)]
            )
            for phase in ("before", "after")
        }
        for side in ("legacy", "java")
    }
    scope_counts = {
        scope: sum(1 for difference in differences if difference["scope"] == scope)
        for scope in (
            "initial_database",
            "final_database",
            "response",
            "session",
            "redis",
            "external",
            "invariant",
        )
    }
    report: Dict[str, Any] = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "operation": "ISOLATED_WRITE_COMPARE",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "environment": args.environment,
        "outcome": "pass" if not differences else "fail",
        "run_id": run_id,
        "operation_id": OPERATION_ID,
        "fixture_id": fixture_id,
        "request": {
            "method": HTTP_METHOD,
            "path": HTTP_PATH,
            "dispatch": "external-serial-only",
            "writes_issued_by_comparator": 0,
            "raw_request_persisted": False,
        },
        "provenance": {
            "snapshot_id": snapshot_id,
            "snapshot_digest": snapshot_digest,
            "legacy_artifact_digest": legacy_artifact,
            "java_artifact_digest": java_artifact,
        },
        "execution": {
            "declared_order": args.execution_order,
            "capture_sequence": [
                f"{side}:{phase}"
                for side, phase in sorted(sequences, key=lambda item: sequences[item])
            ],
            "serial_evidence_validated": True,
            "independent_resources_validated": True,
            "network_capability_present": False,
            "shared_write_target_detected": False,
        },
        "environment_fingerprints": {
            "legacy": fingerprint_report(legacy_fingerprint),
            "java": fingerprint_report(java_fingerprint),
            "legacy_file_sha256": sha256_bytes(legacy_fingerprint_raw),
            "java_file_sha256": sha256_bytes(java_fingerprint_raw),
        },
        "state_summaries": summaries,
        "normalization": {
            "version": "phase3-auth-login-final-state-v1",
            "database": "exact non-projected state digest plus explicit fixture credential fields",
            "projected_fixture_fields": [
                "users.password_hash",
                "users.has_password_set",
                "users.session_version",
                "users.last_active",
            ],
            "allowed_fixture_transition": "has_password_set:false-to-true-only",
            "session": "identity-version-remember semantics; storage profile excluded by P3-AUTH-002",
            "redis": "business/rebuildable/rate-limit semantics; server session count is side invariant",
            "external": (
                "persistent file writes are manifest-observed; queue, object store, and external "
                "sink are configuration-only boundaries without runtime write counts"
            ),
            "raw_password_hash_persisted": False,
            "raw_cookie_persisted": False,
        },
        "approved_implementation_differences": [
            {
                "id": "P3-AUTH-002",
                "scope": "session-storage-and-authority-profile",
                "legacy_profile": "signed-client-cookie",
                "java_profile": "server-redis-postgresql-authority",
            }
        ],
        "checks": {
            "same_snapshot_initial_database": scope_counts["initial_database"] == 0,
            "final_business_database_equivalent": scope_counts["final_database"] == 0,
            "response_contract_equivalent": scope_counts["response"] == 0,
            "session_semantics_equivalent": scope_counts["session"] == 0,
            "redis_semantics_equivalent": scope_counts["redis"] == 0,
            "file_and_external_configuration_boundaries_equivalent": (
                scope_counts["external"] == 0
            ),
            "per_side_invariants_satisfied": scope_counts["invariant"] == 0,
        },
        "differences": differences,
        "difference_count": difference_count,
        "differences_truncated": difference_count >= MAX_DIFFERENCES,
        "sensitive_data_policy": {
            "raw_request_persisted": False,
            "raw_response_persisted": False,
            "raw_password_hash_persisted": False,
            "raw_cookie_or_session_id_persisted": False,
            "difference_values_are_hashes": True,
            "report_scan_passed": True,
        },
    }
    ensure_report_safe(report)
    write_report_atomic(args.report, report)
    json.dump(
        {
            "operation": "ISOLATED_WRITE_COMPARE",
            "outcome": report["outcome"],
            "difference_count": difference_count,
            "report_written": True,
        },
        sys.stdout,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    sys.stdout.write("\n")
    return 0 if report["outcome"] == "pass" else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return execute(args)
    except CompareError as error:
        json.dump(
            {"error": {"code": error.code, "message": error.message}},
            sys.stderr,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sys.stderr.write("\n")
        return 2
    except (MemoryError, RecursionError):
        json.dump(
            {"error": {"code": "RESOURCE_LIMIT", "message": "输入超过安全资源限制。"}},
            sys.stderr,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sys.stderr.write("\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
