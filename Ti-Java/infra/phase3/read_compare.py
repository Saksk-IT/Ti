#!/usr/bin/env python3
"""Fail-closed local/test READ_COMPARE runner for legacy and Java HTTP reads."""

import argparse
import copy
import datetime as dt
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


REPORT_SCHEMA_VERSION = "1.0.0"
INPUT_SCHEMA_VERSION = "1"
MAX_INPUT_BYTES = 1024 * 1024
MAX_DIFFERENCES = 500
FINGERPRINT_FIELDS = ("database", "redis", "volume")
AUDIT_STATE_FIELDS = (
    "database",
    "redis",
    "volume",
    "queue",
    "object_store",
    "external_writes",
)
SAFE_RESPONSE_HEADERS = (
    "cache-control",
    "content-encoding",
    "content-language",
    "etag",
    "last-modified",
    "vary",
    "x-content-type-options",
    "x-frame-options",
    "x-request-id",
)
DYNAMIC_RESPONSE_HEADERS = {"x-request-id"}
FORBIDDEN_REQUEST_HEADERS = {
    "connection",
    "content-length",
    "host",
    "proxy-authorization",
    "transfer-encoding",
}
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
HEADER_NAME_RE = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,128}\Z")
MEDIA_TYPE_TOKEN_RE = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
SHA256_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
PRODUCTION_MARKER_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:prod(?:uction)?|live)(?:$|[^a-z0-9])", re.IGNORECASE
)
SENSITIVE_KEY_RE = re.compile(
    r"^(?:authorization|proxy_authorization|cookie|set_cookie|token|access_token|"
    r"refresh_token|secret|password|passwd|openid|jwt|credential|api_key|apikey)$",
    re.IGNORECASE,
)
SENSITIVE_KEY_COMPONENT_RE = re.compile(
    r"(?:^|_)(?:authorization|cookie|token|secret|password|passwd|openid|jwt|"
    r"credential|api_key|apikey)(?:$|_)",
    re.IGNORECASE,
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
DYNAMIC_FIELD_RE = re.compile(
    r"^(?:request[_-]?id|trace[_-]?id|server[_-]?time|generated[_-]?at|"
    r"current[_-]?time)$",
    re.IGNORECASE,
)
JSON_NOT_PARSED = object()


class CompareError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CompareError("CLI_ARGUMENT_INVALID", "命令参数无效；请查看 --help。")


class DuplicateJsonKeyError(ValueError):
    pass


class InvalidJsonConstantError(ValueError):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_object(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    value: Dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise DuplicateJsonKeyError("duplicate JSON object key")
        value[key] = child
    return value


def reject_json_constant(value: str) -> None:
    raise InvalidJsonConstantError(value)


def strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        parse_int=Decimal,
        parse_float=Decimal,
        parse_constant=reject_json_constant,
        object_pairs_hook=strict_object,
    )


def has_unsafe_text_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 or 0xD800 <= ord(character) <= 0xDFFF for character in value)


def json_ready(value: Any) -> Any:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, Decimal):
        return {"type": "number", "value": str(value)}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, list):
        return {"type": "array", "value": [json_ready(item) for item in value]}
    if isinstance(value, dict):
        return {
            "type": "object",
            "value": {key: json_ready(value[key]) for key in sorted(value)},
        }
    raise CompareError("UNSUPPORTED_JSON", "响应包含不受支持的 JSON 值类型。")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        json_ready(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def contains_sensitive_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS)


def is_sensitive_key(value: str) -> bool:
    normalized = value.lower().replace("-", "_")
    return bool(
        SENSITIVE_KEY_RE.fullmatch(normalized)
        or SENSITIVE_KEY_COMPONENT_RE.search(normalized)
    )


def reject_production_marker(value: str, label: str) -> None:
    if PRODUCTION_MARKER_RE.search(value):
        raise CompareError("PRODUCTION_FORBIDDEN", f"{label} 含生产环境标识。")


def validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise CompareError("INVALID_IDENTIFIER", f"{label} 必须是非空安全标识。")
    reject_production_marker(value, label)
    return value


def read_limited_file(path_text: str, label: str) -> bytes:
    path = pathlib.Path(path_text)
    descriptor: Optional[int] = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(str(path), flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CompareError("INPUT_NOT_FILE", f"{label} 必须指向普通文件。")
        if metadata.st_size > MAX_INPUT_BYTES:
            raise CompareError("INPUT_TOO_LARGE", f"{label} 超出 1 MiB 限制。")
        chunks = bytearray()
        while len(chunks) <= MAX_INPUT_BYTES:
            chunk = os.read(descriptor, min(65536, MAX_INPUT_BYTES + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > MAX_INPUT_BYTES:
            raise CompareError("INPUT_TOO_LARGE", f"{label} 超出 1 MiB 限制。")
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


def read_json_file(path_text: str, label: str) -> Dict[str, Any]:
    raw = read_limited_file(path_text, label)
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKeyError,
        InvalidJsonConstantError,
        RecursionError,
    ) as error:
        raise CompareError("INVALID_JSON_INPUT", f"{label}不是有效 UTF-8 JSON。") from error
    if not isinstance(value, dict):
        raise CompareError("INVALID_JSON_INPUT", f"{label}顶层必须是对象。")
    return value


def expect_exact_keys(document: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    if set(document) != set(expected):
        raise CompareError("UNKNOWN_INPUT_FIELD", f"{label}字段集合不符合版本化契约。")


def validate_origin(origin: str, label: str) -> Tuple[str, Tuple[str, int]]:
    if not isinstance(origin, str) or len(origin) > 256:
        raise CompareError("INVALID_ORIGIN", f"{label}不是有效回环 HTTP origin。")
    reject_production_marker(origin, label)
    try:
        parsed = urllib.parse.urlsplit(origin)
        port = parsed.port
    except ValueError as error:
        raise CompareError("INVALID_ORIGIN", f"{label}端口无效。") from error
    if parsed.scheme != "http" or parsed.username is not None or parsed.password is not None:
        raise CompareError("INVALID_ORIGIN", f"{label}仅允许无 userinfo 的 HTTP origin。")
    if (
        parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or port is None
        or port == 0
    ):
        raise CompareError("INVALID_ORIGIN", f"{label}必须是带显式端口的纯 origin。")
    hostname = (parsed.hostname or "").lower()
    if hostname == "localhost":
        normalized_host = "localhost"
    else:
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError as error:
            raise CompareError("NON_LOOPBACK_ORIGIN", f"{label}仅允许回环地址。") from error
        if not address.is_loopback:
            raise CompareError("NON_LOOPBACK_ORIGIN", f"{label}仅允许回环地址。")
        normalized_host = address.compressed
    display_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    canonical = f"http://{display_host}:{port}"
    # All accepted hosts are loopback. Sharing a port can silently target one runtime
    # through localhost/127.0.0.1 aliases, so use a stricter-than-RFC origin key.
    return canonical, ("loopback", port)


def validate_request_path(path: str) -> str:
    if not isinstance(path, str) or len(path) > 2048 or has_unsafe_text_character(path):
        raise CompareError("INVALID_REQUEST_PATH", "请求路径无效。")
    parsed = urllib.parse.urlsplit(path)
    if parsed.scheme or parsed.netloc or parsed.fragment or not parsed.path.startswith("/"):
        raise CompareError("INVALID_REQUEST_PATH", "请求路径必须是无 fragment 的 origin-relative 路径。")
    if parsed.path.startswith("//"):
        raise CompareError("INVALID_REQUEST_PATH", "请求路径不能覆盖 origin。")
    decoded_segments = [urllib.parse.unquote(segment) for segment in parsed.path.split("/")]
    if any(segment == ".." for segment in decoded_segments):
        raise CompareError("INVALID_REQUEST_PATH", "请求路径不能包含父级段。")
    if any(PRODUCTION_MARKER_RE.fullmatch(segment) for segment in decoded_segments if segment):
        raise CompareError("PRODUCTION_FORBIDDEN", "请求路径含生产环境标识。")
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        if is_sensitive_key(key):
            raise CompareError("SENSITIVE_QUERY_FORBIDDEN", "敏感参数只能经请求头文件传入。")
        reject_production_marker(value, "查询参数")
    return path


def validate_request_headers(path_text: Optional[str]) -> Dict[str, str]:
    if path_text is None:
        return {}
    document = read_json_file(path_text, "请求头文件")
    headers: Dict[str, str] = {}
    for name, value in document.items():
        if not isinstance(name, str) or not HEADER_NAME_RE.fullmatch(name):
            raise CompareError("INVALID_REQUEST_HEADER", "请求头名称无效。")
        lowered = name.lower()
        if lowered in FORBIDDEN_REQUEST_HEADERS:
            raise CompareError("FORBIDDEN_REQUEST_HEADER", "请求头文件包含比较器保留头。")
        if not isinstance(value, str) or len(value) > 8192 or has_unsafe_text_character(value):
            raise CompareError("INVALID_REQUEST_HEADER", "请求头值无效。")
        headers[name] = value
    return headers


def validate_report_target(path_text: str) -> None:
    if (
        not isinstance(path_text, str)
        or not path_text
        or len(path_text) > 4096
        or has_unsafe_text_character(path_text)
    ):
        raise CompareError("INVALID_REPORT_PATH", "报告路径无效。")
    target = pathlib.Path(path_text)
    if target.suffix.lower() != ".json":
        raise CompareError("INVALID_REPORT_PATH", "报告文件必须使用 .json 后缀。")
    try:
        if target.exists():
            raise CompareError("REPORT_EXISTS", "报告路径已存在；每次运行必须使用新文件。")
        if not target.parent.is_dir():
            raise CompareError("REPORT_DIRECTORY_MISSING", "报告父目录必须预先存在。")
    except CompareError:
        raise
    except OSError as error:
        raise CompareError("INVALID_REPORT_PATH", "报告路径不可访问。") from error


def validate_fingerprint(path_text: str, environment: str, side: str) -> Dict[str, str]:
    document = read_json_file(path_text, f"{side} 环境指纹")
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
    return result


def assert_independent_fingerprints(legacy: Mapping[str, str], java: Mapping[str, str]) -> None:
    all_values = list(legacy.values()) + list(java.values())
    if len(set(all_values)) != len(all_values):
        raise CompareError(
            "SHARED_ENVIRONMENT_FINGERPRINT",
            "两边数据库、Redis、卷指纹必须全部非空且彼此不同。",
        )


def parse_json_pointer(pointer: str, label: str) -> List[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/") or len(pointer) > 512:
        raise CompareError("INVALID_NORMALIZATION_POINTER", f"{label}必须是非根 JSON Pointer。")
    if re.search(r"~(?![01])", pointer):
        raise CompareError("INVALID_NORMALIZATION_POINTER", f"{label}含无效转义。")
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]
    if not tokens or any(token in ("", "*", "**") for token in tokens):
        raise CompareError("BROAD_NORMALIZATION_FORBIDDEN", f"{label}不能使用空段或通配符。")
    if any(is_sensitive_key(token) for token in tokens):
        raise CompareError("SENSITIVE_NORMALIZATION_FORBIDDEN", f"{label}不能隐藏敏感字段。")
    return tokens


def validate_pointer_list(values: Any, label: str, ignored: bool) -> List[Tuple[str, List[str]]]:
    if not isinstance(values, list) or len(values) > 64:
        raise CompareError("INVALID_NORMALIZATION_RULE", f"{label}必须是无重复的有界数组。")
    if any(not isinstance(pointer, str) for pointer in values) or len(set(values)) != len(values):
        raise CompareError("INVALID_NORMALIZATION_RULE", f"{label}必须是无重复的有界数组。")
    result: List[Tuple[str, List[str]]] = []
    for pointer in values:
        tokens = parse_json_pointer(pointer, label)
        if ignored:
            if tokens[-1].isdigit() or not DYNAMIC_FIELD_RE.fullmatch(tokens[-1]):
                raise CompareError(
                    "BROAD_NORMALIZATION_FORBIDDEN",
                    "动态字段忽略规则只能指向已批准的易变标量字段名。",
                )
        result.append((pointer, tokens))
    return result


def load_normalization_rules(path_text: str, operation_id: str) -> Dict[str, Any]:
    raw = read_limited_file(path_text, "规范化规则")
    try:
        document = strict_json_loads(raw.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKeyError,
        InvalidJsonConstantError,
        RecursionError,
    ) as error:
        raise CompareError("INVALID_JSON_INPUT", "规范化规则不是有效 UTF-8 JSON。") from error
    if not isinstance(document, dict):
        raise CompareError("INVALID_NORMALIZATION_RULE", "规范化规则顶层必须是对象。")
    expect_exact_keys(
        document,
        ("schema_version", "ruleset_version", "operations"),
        "规范化规则",
    )
    if document["schema_version"] != INPUT_SCHEMA_VERSION:
        raise CompareError("UNSUPPORTED_INPUT_VERSION", "规范化规则版本不受支持。")
    ruleset_version = validate_identifier(document["ruleset_version"], "规则集版本")
    operations = document["operations"]
    if not isinstance(operations, dict):
        raise CompareError("INVALID_NORMALIZATION_RULE", "operations 必须是对象。")
    for registered_id in operations:
        validate_identifier(registered_id, "规则 operation")
    if operation_id not in operations:
        raise CompareError("OPERATION_NOT_ALLOWLISTED", "operation 未进入版本化规范化白名单。")
    operation = operations[operation_id]
    if not isinstance(operation, dict):
        raise CompareError("INVALID_NORMALIZATION_RULE", "operation 规则必须是对象。")
    expect_exact_keys(
        operation,
        (
            "ignore_json_pointers",
            "unordered_array_json_pointers",
            "ignore_response_headers",
        ),
        "operation 规范化规则",
    )
    ignored = validate_pointer_list(operation["ignore_json_pointers"], "ignore_json_pointers", True)
    unordered = validate_pointer_list(
        operation["unordered_array_json_pointers"],
        "unordered_array_json_pointers",
        False,
    )
    if {pointer for pointer, _ in ignored} & {pointer for pointer, _ in unordered}:
        raise CompareError("INVALID_NORMALIZATION_RULE", "同一 JSON Pointer 不能同时忽略并排序。")
    ignored_headers = operation["ignore_response_headers"]
    if (
        not isinstance(ignored_headers, list)
        or len(ignored_headers) > len(DYNAMIC_RESPONSE_HEADERS)
        or any(not isinstance(name, str) for name in ignored_headers)
        or len(set(ignored_headers)) != len(ignored_headers)
        or any(name not in DYNAMIC_RESPONSE_HEADERS for name in ignored_headers)
    ):
        raise CompareError(
            "BROAD_NORMALIZATION_FORBIDDEN",
            "响应头忽略规则只能使用已批准的小写动态安全头。",
        )
    return {
        "ruleset_version": ruleset_version,
        "ruleset_sha256": sha256_bytes(raw),
        "ignored": ignored,
        "unordered": unordered,
        "ignored_headers": ignored_headers,
    }


def navigate(root: Any, tokens: Sequence[str]) -> Tuple[bool, Any, Optional[Any], Optional[str]]:
    current = root
    parent: Optional[Any] = None
    final: Optional[str] = None
    for token in tokens:
        parent = current
        final = token
        if isinstance(current, dict):
            if token not in current:
                return False, None, None, None
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return False, None, None, None
            current = current[index]
        else:
            return False, None, None, None
    return True, current, parent, final


def normalize_json(value: Any, rules: Mapping[str, Any]) -> Tuple[Any, Dict[str, int]]:
    normalized = copy.deepcopy(value)
    stats = {
        "ignored_declared": len(rules["ignored"]),
        "ignored_applied": 0,
        "unordered_declared": len(rules["unordered"]),
        "unordered_applied": 0,
    }
    for _, tokens in rules["ignored"]:
        found, _, parent, final = navigate(normalized, tokens)
        if found:
            if not isinstance(parent, dict) or final is None:
                raise CompareError("INVALID_NORMALIZATION_TARGET", "动态字段忽略目标必须是对象字段。")
            del parent[final]
            stats["ignored_applied"] += 1
    for _, tokens in rules["unordered"]:
        found, target, _, _ = navigate(normalized, tokens)
        if found:
            if not isinstance(target, list):
                raise CompareError("INVALID_NORMALIZATION_TARGET", "无序数组规则命中了非数组值。")
            target.sort(key=canonical_bytes)
            stats["unordered_applied"] += 1
    return normalized, stats


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Decimal):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unsupported"


def value_descriptor(value: Any, missing: bool = False) -> Dict[str, Any]:
    if missing:
        return {"type": "missing"}
    encoded = canonical_bytes(value)
    return {
        "type": json_type(value),
        "sha256": sha256_bytes(encoded),
        "size": len(encoded),
    }


def sanitize_pointer(tokens: Sequence[str]) -> str:
    safe_tokens = []
    for token in tokens:
        if is_sensitive_key(token):
            safe_tokens.append(f"$sensitive-{sha256_bytes(token.encode('utf-8'))[:12]}")
        elif len(token) > 128 or has_unsafe_text_character(token):
            safe_tokens.append(
                f"$key-{sha256_bytes(token.encode('utf-8', 'surrogatepass'))[:12]}"
            )
        else:
            safe_tokens.append(token.replace("~", "~0").replace("/", "~1"))
    pointer = "" if not safe_tokens else "/" + "/".join(safe_tokens)
    if len(pointer) > 2048:
        return "/$path-" + sha256_bytes(pointer.encode("utf-8"))
    return pointer


def append_difference(
    differences: List[Dict[str, Any]],
    scope: str,
    kind: str,
    tokens: Sequence[str],
    legacy: Any,
    java: Any,
    legacy_missing: bool = False,
    java_missing: bool = False,
) -> None:
    if len(differences) >= MAX_DIFFERENCES:
        return
    differences.append(
        {
            "scope": scope,
            "kind": kind,
            "path": sanitize_pointer(tokens),
            "legacy": value_descriptor(legacy, legacy_missing),
            "java": value_descriptor(java, java_missing),
        }
    )


def compare_json(
    legacy: Any,
    java: Any,
    differences: List[Dict[str, Any]],
    tokens: Optional[List[str]] = None,
) -> None:
    if len(differences) >= MAX_DIFFERENCES:
        return
    path = [] if tokens is None else tokens
    legacy_type = json_type(legacy)
    java_type = json_type(java)
    if legacy_type != java_type:
        append_difference(differences, "body", "type", path, legacy, java)
        return
    if isinstance(legacy, dict):
        for key in sorted(set(legacy) | set(java)):
            if key not in legacy:
                append_difference(
                    differences,
                    "body",
                    "missing",
                    path + [key],
                    None,
                    java[key],
                    legacy_missing=True,
                )
            elif key not in java:
                append_difference(
                    differences,
                    "body",
                    "missing",
                    path + [key],
                    legacy[key],
                    None,
                    java_missing=True,
                )
            else:
                compare_json(legacy[key], java[key], differences, path + [key])
        return
    if isinstance(legacy, list):
        legacy_items = [canonical_bytes(item) for item in legacy]
        java_items = [canonical_bytes(item) for item in java]
        if legacy_items == java_items:
            return
        if len(legacy) == len(java) and sorted(legacy_items) == sorted(java_items):
            append_difference(differences, "body", "array_order", path, legacy, java)
            return
        if len(legacy) != len(java):
            append_difference(differences, "body", "array_length", path, legacy, java)
        for index in range(min(len(legacy), len(java))):
            compare_json(legacy[index], java[index], differences, path + [str(index)])
        return
    if isinstance(legacy, Decimal):
        equal = str(legacy) == str(java)
    else:
        equal = legacy == java
    if not equal:
        append_difference(differences, "body", "value", path, legacy, java)


def validate_safe_text(value: str, label: str, limit: int = 1024) -> str:
    if not isinstance(value, str) or len(value) > limit or has_unsafe_text_character(value):
        raise CompareError("UNSAFE_RESPONSE_METADATA", f"{label}格式不安全。")
    if contains_sensitive_value(value):
        raise CompareError("SENSITIVE_OUTPUT_BLOCKED", f"{label}疑似包含敏感数据。")
    return value


def canonical_content_type(value: str) -> str:
    """Parse Content-Type strictly and canonicalize only protocol-insignificant syntax."""
    if not value:
        return ""
    length = len(value)
    cursor = 0

    def skip_ows() -> None:
        nonlocal cursor
        while cursor < length and value[cursor] in " \t":
            cursor += 1

    def token(label: str) -> str:
        nonlocal cursor
        match = MEDIA_TYPE_TOKEN_RE.match(value, cursor)
        if match is None:
            raise CompareError("INVALID_CONTENT_TYPE", f"Content-Type {label}格式无效。")
        cursor = match.end()
        return match.group(0)

    def parameter_value() -> str:
        nonlocal cursor
        if cursor >= length:
            raise CompareError("INVALID_CONTENT_TYPE", "Content-Type 参数缺少值。")
        if value[cursor] != '"':
            return token("参数值")
        cursor += 1
        decoded: List[str] = []
        while cursor < length:
            character = value[cursor]
            cursor += 1
            if character == '"':
                return "".join(decoded)
            if character == "\\":
                if cursor >= length:
                    break
                escaped = value[cursor]
                cursor += 1
                if escaped not in "\t " and not (0x21 <= ord(escaped) <= 0x7E):
                    raise CompareError("INVALID_CONTENT_TYPE", "Content-Type quoted-pair 无效。")
                decoded.append(escaped)
                continue
            codepoint = ord(character)
            if (
                character in "\t "
                or codepoint == 0x21
                or 0x23 <= codepoint <= 0x5B
                or 0x5D <= codepoint <= 0x7E
                or codepoint >= 0x80
            ):
                decoded.append(character)
                continue
            raise CompareError("INVALID_CONTENT_TYPE", "Content-Type quoted-string 无效。")
        raise CompareError("INVALID_CONTENT_TYPE", "Content-Type quoted-string 未闭合。")

    skip_ows()
    media_type = token("type").lower()
    if cursor >= length or value[cursor] != "/":
        raise CompareError("INVALID_CONTENT_TYPE", "Content-Type 缺少 subtype。")
    cursor += 1
    media_subtype = token("subtype").lower()
    parameters: Dict[str, str] = {}
    while True:
        skip_ows()
        if cursor == length:
            break
        if value[cursor] != ";":
            raise CompareError("INVALID_CONTENT_TYPE", "Content-Type 参数分隔符无效。")
        cursor += 1
        skip_ows()
        name = token("参数名").lower()
        if name in parameters:
            raise CompareError("INVALID_CONTENT_TYPE", "Content-Type 含重复参数。")
        if cursor >= length or value[cursor] != "=":
            raise CompareError("INVALID_CONTENT_TYPE", "Content-Type 参数缺少等号。")
        cursor += 1
        parameter = parameter_value()
        parameters[name] = parameter.lower() if name == "charset" else parameter

    canonical = f"{media_type}/{media_subtype}"
    for name in sorted(parameters):
        parameter = parameters[name]
        encoded = (
            parameter
            if MEDIA_TYPE_TOKEN_RE.fullmatch(parameter)
            else json.dumps(parameter, ensure_ascii=True, separators=(",", ":"))
        )
        canonical += f";{name}={encoded}"
    return canonical


def selected_headers(headers: Any) -> Dict[str, List[str]]:
    selected: Dict[str, List[str]] = {}
    for name in SAFE_RESPONSE_HEADERS:
        values = headers.get_all(name) or []
        if values:
            selected[name] = [validate_safe_text(value, "响应头") for value in values]
    return selected


def parse_response_json(body: bytes, content_type: str, method: str) -> Tuple[bool, Any, bool]:
    media_type = content_type.split(";", 1)[0].strip().lower()
    declared_json = media_type == "application/json" or media_type.endswith("+json")
    if not declared_json or method == "HEAD":
        return declared_json, JSON_NOT_PARSED, False
    if not body:
        return True, JSON_NOT_PARSED, True
    try:
        parsed = strict_json_loads(body.decode("utf-8-sig"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKeyError,
        InvalidJsonConstantError,
        RecursionError,
    ):
        return True, JSON_NOT_PARSED, True
    return True, parsed, False


def fetch_response(
    origin: str,
    path: str,
    method: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
    max_body_bytes: int,
) -> Dict[str, Any]:
    target = origin + path
    request_headers = dict(headers)
    request_headers.setdefault("Accept-Encoding", "identity")
    request_headers.setdefault("User-Agent", "Ti-Java-READ_COMPARE/1")
    request = urllib.request.Request(target, method=method, headers=request_headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())
    started = time.monotonic()
    try:
        response = opener.open(request, timeout=timeout_seconds)
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            raise CompareError("REDIRECT_FORBIDDEN", "比较端点返回重定向；请求未跟随。") from error
        response = error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise CompareError("HTTP_REQUEST_FAILED", "本地比较端点请求失败。") from error
    try:
        status_code = int(response.getcode())
        if not 100 <= status_code <= 599:
            raise CompareError("INVALID_HTTP_STATUS", "比较端点返回无效 HTTP 状态码。")
        if 300 <= status_code < 400:
            raise CompareError("REDIRECT_FORBIDDEN", "比较端点返回重定向；请求未跟随。")
        body = response.read(max_body_bytes + 1)
        if len(body) > max_body_bytes:
            raise CompareError("RESPONSE_TOO_LARGE", "响应正文超过显式字节限制。")
        content_type = validate_safe_text(response.headers.get("Content-Type", ""), "Content-Type", 512)
        canonical_type = canonical_content_type(content_type)
        safe_headers = selected_headers(response.headers)
    finally:
        response.close()
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    declared_json, parsed_json, invalid_json = parse_response_json(body, canonical_type, method)
    return {
        "status": status_code,
        "content_type": content_type,
        "canonical_content_type": canonical_type,
        "headers": safe_headers,
        "body": body,
        "duration_ms": duration_ms,
        "declared_json": declared_json,
        "parsed_json": parsed_json,
        "invalid_json": invalid_json,
    }


def validate_audit_state(state: Any) -> None:
    if not isinstance(state, dict) or not state:
        raise CompareError("INVALID_AUDIT_EVIDENCE", "审计 state 必须是非空对象。")
    missing = set(AUDIT_STATE_FIELDS) - set(state)
    if missing:
        raise CompareError("INVALID_AUDIT_EVIDENCE", "审计 state 缺少必需副作用域。")

    def visit(value: Any, key: Optional[str] = None) -> None:
        if key is not None:
            if not IDENTIFIER_RE.fullmatch(key) or is_sensitive_key(key):
                raise CompareError("SENSITIVE_AUDIT_EVIDENCE", "审计证据含非法或敏感字段名。")
            reject_production_marker(key, "审计字段")
        if isinstance(value, dict):
            if not value:
                raise CompareError("INVALID_AUDIT_EVIDENCE", "审计证据不能含空对象。")
            for child_key, child_value in value.items():
                if not isinstance(child_key, str):
                    raise CompareError("INVALID_AUDIT_EVIDENCE", "审计证据字段名必须是字符串。")
                visit(child_value, child_key)
        elif isinstance(value, list):
            if not value:
                raise CompareError("INVALID_AUDIT_EVIDENCE", "审计证据不能含空数组。")
            for child in value:
                visit(child)
        elif value is None or isinstance(value, float):
            raise CompareError("INVALID_AUDIT_EVIDENCE", "审计证据不允许 null 或浮点值。")
        elif isinstance(value, str):
            if (
                not value
                or len(value) > 2048
                or has_unsafe_text_character(value)
                or contains_sensitive_value(value)
            ):
                raise CompareError("SENSITIVE_AUDIT_EVIDENCE", "审计证据含空值或疑似敏感值。")
            reject_production_marker(value, "审计证据")
        elif not isinstance(value, (bool, int, Decimal)):
            raise CompareError("INVALID_AUDIT_EVIDENCE", "审计证据含不支持的值类型。")

    visit(state)


def validate_audit_document(
    document: Mapping[str, Any], environment: str, side: str, phase: str
) -> Dict[str, Any]:
    expect_exact_keys(
        document,
        ("schema_version", "environment", "side", "phase", "auditor", "state"),
        "副作用审计证据",
    )
    if document["schema_version"] != INPUT_SCHEMA_VERSION:
        raise CompareError("UNSUPPORTED_INPUT_VERSION", "副作用审计证据版本不受支持。")
    if (
        document["environment"] != environment
        or document["side"] != side
        or document["phase"] != phase
    ):
        raise CompareError("AUDIT_SCOPE_MISMATCH", "副作用审计证据作用域不匹配。")
    auditor = validate_identifier(document["auditor"], "auditor")
    validate_audit_state(document["state"])
    return {"auditor": auditor, "state": document["state"]}


def load_audit_file(
    path_text: str, environment: str, side: str, phase: str
) -> Dict[str, Any]:
    return validate_audit_document(
        read_json_file(path_text, "副作用审计证据"), environment, side, phase
    )


def validate_auditor_command(command_text: str) -> pathlib.Path:
    command = pathlib.Path(command_text)
    if not command.is_absolute():
        raise CompareError("AUDITOR_COMMAND_INVALID", "auditor 命令必须是绝对路径。")
    try:
        mode = command.lstat().st_mode
    except OSError as error:
        raise CompareError("AUDITOR_COMMAND_INVALID", "auditor 命令不可访问。") from error
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode) or not os.access(str(command), os.X_OK):
        raise CompareError("AUDITOR_COMMAND_INVALID", "auditor 命令必须是可执行普通文件。")
    return command


def run_auditor(
    command_text: str,
    environment: str,
    side: str,
    phase: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    command = validate_auditor_command(command_text)
    environment_vars = os.environ.copy()
    environment_vars.update(
        {
            "TI_READ_COMPARE_ENVIRONMENT": environment,
            "TI_READ_COMPARE_SIDE": side,
            "TI_READ_COMPARE_PHASE": phase,
        }
    )
    try:
        completed = subprocess.run(
            [str(command)],
            check=False,
            capture_output=True,
            env=environment_vars,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CompareError("AUDITOR_COMMAND_FAILED", "独立 auditor 命令执行失败。") from error
    if completed.returncode != 0 or len(completed.stdout) > MAX_INPUT_BYTES:
        raise CompareError("AUDITOR_COMMAND_FAILED", "独立 auditor 命令返回失败或输出过大。")
    try:
        document = strict_json_loads(completed.stdout.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKeyError,
        InvalidJsonConstantError,
        RecursionError,
    ) as error:
        raise CompareError("AUDITOR_COMMAND_INVALID", "独立 auditor 输出不是有效 UTF-8 JSON。") from error
    if not isinstance(document, dict):
        raise CompareError("AUDITOR_COMMAND_INVALID", "独立 auditor 输出顶层必须是对象。")
    return validate_audit_document(document, environment, side, phase)


def evidence_mode(args: argparse.Namespace) -> str:
    file_values = (
        args.legacy_before_evidence,
        args.legacy_after_evidence,
        args.java_before_evidence,
        args.java_after_evidence,
    )
    command_values = (args.legacy_auditor_command, args.java_auditor_command)
    files_used = any(value is not None for value in file_values)
    commands_used = any(value is not None for value in command_values)
    if files_used and commands_used:
        raise CompareError("AUDIT_SOURCE_CONFLICT", "副作用证据不能混用文件与命令模式。")
    if files_used:
        if not all(value is not None for value in file_values):
            raise CompareError("AUDIT_SOURCE_INCOMPLETE", "文件模式必须提供两边 before/after 四份证据。")
        return "file"
    if commands_used:
        if not all(value is not None for value in command_values):
            raise CompareError("AUDIT_SOURCE_INCOMPLETE", "命令模式必须提供两边 auditor 命令。")
        return "command"
    raise CompareError("AUDIT_SOURCE_REQUIRED", "必须显式提供独立副作用审计证据。")


def audit_snapshot_sha(state: Any) -> str:
    return sha256_bytes(canonical_bytes(state))


def compare_audit_pair(
    side: str,
    source_kind: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    differences: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if before["auditor"] != after["auditor"]:
        raise CompareError("AUDITOR_IDENTITY_CHANGED", "before/after 必须由同一 auditor 生成。")
    before_sha = audit_snapshot_sha(before["state"])
    after_sha = audit_snapshot_sha(after["state"])
    changed = before_sha != after_sha
    if changed:
        local_differences: List[Dict[str, Any]] = []
        compare_json(before["state"], after["state"], local_differences)
        for difference in local_differences:
            if len(differences) >= MAX_DIFFERENCES:
                break
            difference["scope"] = "side_effect"
            difference["path"] = f"/{side}" + difference["path"]
            differences.append(difference)
    return {
        "auditor": before["auditor"],
        "source_kind": source_kind,
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "changed": changed,
    }


def response_summary(response: Mapping[str, Any], normalized: Any) -> Dict[str, Any]:
    body = response["body"]
    summary: Dict[str, Any] = {
        "status": response["status"],
        "content_type": response["content_type"],
        "canonical_content_type": response["canonical_content_type"],
        "selected_headers": response["headers"],
        "body_sha256": sha256_bytes(body),
        "body_size": len(body),
        "duration_ms": response["duration_ms"],
        "declared_json": response["declared_json"],
        "valid_json": (
            response["declared_json"]
            and not response["invalid_json"]
            and response["parsed_json"] is not JSON_NOT_PARSED
        ),
    }
    if normalized is not JSON_NOT_PARSED:
        encoded = canonical_bytes(normalized)
        summary["normalized_body_sha256"] = sha256_bytes(encoded)
        summary["normalized_body_size"] = len(encoded)
    return summary


def compare_response_metadata(
    legacy: Mapping[str, Any],
    java: Mapping[str, Any],
    ignored_headers: Sequence[str],
    differences: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    if legacy["status"] != java["status"]:
        append_difference(differences, "status", "value", [], Decimal(legacy["status"]), Decimal(java["status"]))
    if legacy["canonical_content_type"] != java["canonical_content_type"]:
        append_difference(
            differences,
            "content_type",
            "value",
            [],
            legacy["content_type"],
            java["content_type"],
        )
    legacy_headers = legacy["headers"]
    java_headers = java["headers"]
    header_stats = {
        "legacy": {
            "headers_ignored_declared": len(ignored_headers),
            "headers_ignored_applied": 0,
        },
        "java": {
            "headers_ignored_declared": len(ignored_headers),
            "headers_ignored_applied": 0,
        },
    }
    for name in ignored_headers:
        legacy_present = name in legacy_headers
        java_present = name in java_headers
        if not legacy_present and not java_present:
            raise CompareError("STALE_NORMALIZATION_RULE", "动态响应头规则未命中任一响应。")
        if legacy_present and java_present:
            header_stats["legacy"]["headers_ignored_applied"] += 1
            header_stats["java"]["headers_ignored_applied"] += 1
    for name in sorted(set(legacy_headers) | set(java_headers)):
        if name in ignored_headers and name in legacy_headers and name in java_headers:
            continue
        if name not in legacy_headers:
            append_difference(
                differences, "header", "missing", [name], None, java_headers[name], legacy_missing=True
            )
        elif name not in java_headers:
            append_difference(
                differences, "header", "missing", [name], legacy_headers[name], None, java_missing=True
            )
        elif legacy_headers[name] != java_headers[name]:
            append_difference(
                differences, "header", "value", [name], legacy_headers[name], java_headers[name]
            )
    return header_stats


def normalize_and_compare_bodies(
    legacy: Mapping[str, Any],
    java: Mapping[str, Any],
    rules: Mapping[str, Any],
    differences: List[Dict[str, Any]],
) -> Tuple[Any, Any, Dict[str, Dict[str, int]]]:
    empty_stats = {
        "ignored_declared": len(rules["ignored"]),
        "ignored_applied": 0,
        "unordered_declared": len(rules["unordered"]),
        "unordered_applied": 0,
    }
    stats = {"legacy": dict(empty_stats), "java": dict(empty_stats)}
    if legacy["invalid_json"] or java["invalid_json"]:
        append_difference(
            differences,
            "body",
            "invalid_json",
            [],
            "invalid-json" if legacy["invalid_json"] else "valid-json",
            "invalid-json" if java["invalid_json"] else "valid-json",
        )
        return JSON_NOT_PARSED, JSON_NOT_PARSED, stats
    legacy_json = legacy["parsed_json"]
    java_json = java["parsed_json"]
    legacy_available = legacy_json is not JSON_NOT_PARSED
    java_available = java_json is not JSON_NOT_PARSED
    if legacy_available != java_available:
        append_difference(
            differences,
            "body",
            "json_representation",
            [],
            legacy_json if legacy_available else sha256_bytes(legacy["body"]),
            java_json if java_available else sha256_bytes(java["body"]),
        )
        return JSON_NOT_PARSED, JSON_NOT_PARSED, stats
    if not legacy_available and not java_available:
        if rules["ignored"] or rules["unordered"]:
            raise CompareError("NORMALIZATION_REQUIRES_JSON", "JSON 规范化规则不能用于非 JSON 响应。")
        if legacy["body"] != java["body"]:
            append_difference(
                differences,
                "body",
                "body_bytes",
                [],
                sha256_bytes(legacy["body"]),
                sha256_bytes(java["body"]),
            )
        return JSON_NOT_PARSED, JSON_NOT_PARSED, stats
    active_ignored = []
    for _, tokens in rules["ignored"]:
        # Dynamic values may differ, but field presence remains part of the contract.
        legacy_found, _, _, _ = navigate(legacy_json, tokens)
        java_found, _, _, _ = navigate(java_json, tokens)
        if not legacy_found and not java_found:
            raise CompareError("STALE_NORMALIZATION_RULE", "动态字段忽略规则未命中任一响应。")
        if legacy_found and java_found:
            active_ignored.append(("", tokens))
    effective_rules = dict(rules)
    effective_rules["ignored"] = active_ignored
    legacy_normalized, stats["legacy"] = normalize_json(legacy_json, effective_rules)
    java_normalized, stats["java"] = normalize_json(java_json, effective_rules)
    stats["legacy"]["ignored_declared"] = len(rules["ignored"])
    stats["java"]["ignored_declared"] = len(rules["ignored"])
    for index, (_, _) in enumerate(rules["unordered"]):
        legacy_found, _, _, _ = navigate(legacy_json, rules["unordered"][index][1])
        java_found, _, _, _ = navigate(java_json, rules["unordered"][index][1])
        if not legacy_found and not java_found:
            raise CompareError("STALE_NORMALIZATION_RULE", "无序数组规则未命中任一响应。")
    compare_json(legacy_normalized, java_normalized, differences)
    return legacy_normalized, java_normalized, stats


def fingerprint_report(fingerprint: Mapping[str, str]) -> Dict[str, str]:
    return {f"{field}_sha256": sha256_bytes(fingerprint[field].encode("utf-8")) for field in FINGERPRINT_FIELDS}


def ensure_report_safe(report: Mapping[str, Any]) -> None:
    def visit(value: Any, key: Optional[str] = None) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, child_key)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str):
            if contains_sensitive_value(value):
                raise CompareError("SENSITIVE_OUTPUT_BLOCKED", "最终报告敏感扫描失败。")

    visit(report)


def validate_report_shape(report: Mapping[str, Any]) -> None:
    required = {
        "report_schema_version",
        "operation",
        "generated_at",
        "environment",
        "outcome",
        "operation_id",
        "fixture_id",
        "request",
        "provenance",
        "environment_fingerprints",
        "responses",
        "raw_comparison",
        "normalization",
        "side_effects",
        "differences",
        "difference_count",
        "differences_truncated",
        "sensitive_data_policy",
    }
    if set(report) != required:
        raise CompareError("INTERNAL_REPORT_INVALID", "内部报告字段与 JSON Schema 不一致。")
    if report["operation"] != "READ_COMPARE" or report["outcome"] not in ("pass", "fail"):
        raise CompareError("INTERNAL_REPORT_INVALID", "内部报告枚举无效。")


def write_report_atomic(path_text: str, report: Mapping[str, Any]) -> None:
    target = pathlib.Path(path_text)
    if target.exists():
        raise CompareError("REPORT_EXISTS", "报告路径已存在；每次运行必须使用新文件。")
    parent = target.parent
    if not parent.is_dir():
        raise CompareError("REPORT_DIRECTORY_MISSING", "报告父目录必须预先存在。")
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    temporary_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".read-compare-", suffix=".tmp", dir=str(parent), delete=False
        ) as handle:
            temporary_name = handle.name
            os.chmod(temporary_name, 0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # Hard-linking a fully fsynced temporary inode exposes the report atomically
        # and fails if another process created the target after the initial check.
        os.link(temporary_name, target)
    except FileExistsError as error:
        raise CompareError("REPORT_EXISTS", "报告路径已存在；每次运行必须使用新文件。") from error
    except OSError as error:
        raise CompareError("REPORT_WRITE_FAILED", "无法原子写入报告。") from error
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description="Ti-Java 本地/测试只读 HTTP 结构化比较器（拒绝生产环境）"
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    command = subparsers.add_parser("READ_COMPARE", help="比较两个隔离回环运行时的 GET/HEAD")
    command.add_argument("--environment", required=True, choices=("local", "test"))
    command.add_argument("--operation-id", required=True)
    command.add_argument("--fixture-id", required=True)
    command.add_argument("--snapshot-id", required=True)
    command.add_argument("--legacy-artifact-digest", required=True)
    command.add_argument("--java-artifact-digest", required=True)
    command.add_argument("--legacy-origin", required=True)
    command.add_argument("--java-origin", required=True)
    command.add_argument("--path", required=True)
    command.add_argument(
        "--method",
        default="GET",
        metavar="{GET,HEAD}",
        help="仅允许 GET 或 HEAD（默认 GET）",
    )
    command.add_argument("--request-headers-file")
    command.add_argument("--legacy-fingerprint", required=True)
    command.add_argument("--java-fingerprint", required=True)
    command.add_argument("--normalization-rules", required=True)
    command.add_argument("--legacy-before-evidence")
    command.add_argument("--legacy-after-evidence")
    command.add_argument("--java-before-evidence")
    command.add_argument("--java-after-evidence")
    command.add_argument("--legacy-auditor-command")
    command.add_argument("--java-auditor-command")
    command.add_argument("--timeout-seconds", type=float, default=5.0)
    command.add_argument("--auditor-timeout-seconds", type=float, default=10.0)
    command.add_argument("--max-body-bytes", type=int, default=2 * 1024 * 1024)
    command.add_argument("--report", required=True)
    return parser


def execute(args: argparse.Namespace) -> int:
    if args.method not in ("GET", "HEAD"):
        raise CompareError("METHOD_FORBIDDEN", "READ_COMPARE 只允许 GET 或 HEAD。")
    if not (0 < args.timeout_seconds <= 60) or not (0 < args.auditor_timeout_seconds <= 60):
        raise CompareError("INVALID_TIMEOUT", "超时必须位于 0 到 60 秒之间。")
    if not (0 < args.max_body_bytes <= 16 * 1024 * 1024):
        raise CompareError("INVALID_BODY_LIMIT", "正文限制必须位于 1 到 16 MiB 之间。")

    for path_value in (
        args.request_headers_file,
        args.legacy_fingerprint,
        args.java_fingerprint,
        args.normalization_rules,
        args.legacy_before_evidence,
        args.legacy_after_evidence,
        args.java_before_evidence,
        args.java_after_evidence,
        args.legacy_auditor_command,
        args.java_auditor_command,
        args.report,
    ):
        if path_value is not None:
            reject_production_marker(path_value, "输入或输出路径")
    validate_report_target(args.report)

    operation_id = validate_identifier(args.operation_id, "operation-id")
    fixture_id = validate_identifier(args.fixture_id, "fixture-id")
    snapshot_id = validate_identifier(args.snapshot_id, "snapshot-id")
    if not SHA256_DIGEST_RE.fullmatch(args.legacy_artifact_digest or ""):
        raise CompareError("INVALID_ARTIFACT_DIGEST", "legacy 制品必须使用 sha256 digest。")
    if not SHA256_DIGEST_RE.fullmatch(args.java_artifact_digest or ""):
        raise CompareError("INVALID_ARTIFACT_DIGEST", "Java 制品必须使用 sha256 digest。")
    if args.legacy_artifact_digest == args.java_artifact_digest:
        raise CompareError("SHARED_ARTIFACT_DIGEST", "两个运行时制品 digest 必须不同。")

    legacy_origin, legacy_origin_key = validate_origin(args.legacy_origin, "legacy-origin")
    java_origin, java_origin_key = validate_origin(args.java_origin, "java-origin")
    if legacy_origin_key == java_origin_key:
        raise CompareError("SAME_ORIGIN_FORBIDDEN", "两个回环运行时必须使用不同 origin/端口。")
    request_path = validate_request_path(args.path)
    request_headers = validate_request_headers(args.request_headers_file)

    legacy_fingerprint = validate_fingerprint(
        args.legacy_fingerprint, args.environment, "legacy"
    )
    java_fingerprint = validate_fingerprint(args.java_fingerprint, args.environment, "java")
    assert_independent_fingerprints(legacy_fingerprint, java_fingerprint)
    rules = load_normalization_rules(args.normalization_rules, operation_id)
    source_kind = evidence_mode(args)

    if source_kind == "file":
        legacy_before = load_audit_file(
            args.legacy_before_evidence, args.environment, "legacy", "before"
        )
        java_before = load_audit_file(
            args.java_before_evidence, args.environment, "java", "before"
        )
        legacy_response = fetch_response(
            legacy_origin,
            request_path,
            args.method,
            request_headers,
            args.timeout_seconds,
            args.max_body_bytes,
        )
        legacy_after = load_audit_file(
            args.legacy_after_evidence, args.environment, "legacy", "after"
        )
        java_response = fetch_response(
            java_origin,
            request_path,
            args.method,
            request_headers,
            args.timeout_seconds,
            args.max_body_bytes,
        )
        java_after = load_audit_file(
            args.java_after_evidence, args.environment, "java", "after"
        )
    else:
        validate_auditor_command(args.legacy_auditor_command)
        validate_auditor_command(args.java_auditor_command)
        legacy_before = run_auditor(
            args.legacy_auditor_command,
            args.environment,
            "legacy",
            "before",
            args.auditor_timeout_seconds,
        )
        java_before = run_auditor(
            args.java_auditor_command,
            args.environment,
            "java",
            "before",
            args.auditor_timeout_seconds,
        )
        legacy_response = fetch_response(
            legacy_origin,
            request_path,
            args.method,
            request_headers,
            args.timeout_seconds,
            args.max_body_bytes,
        )
        legacy_after = run_auditor(
            args.legacy_auditor_command,
            args.environment,
            "legacy",
            "after",
            args.auditor_timeout_seconds,
        )
        java_response = fetch_response(
            java_origin,
            request_path,
            args.method,
            request_headers,
            args.timeout_seconds,
            args.max_body_bytes,
        )
        java_after = run_auditor(
            args.java_auditor_command,
            args.environment,
            "java",
            "after",
            args.auditor_timeout_seconds,
        )

    differences: List[Dict[str, Any]] = []
    header_normalization_stats = compare_response_metadata(
        legacy_response,
        java_response,
        rules["ignored_headers"],
        differences,
    )
    legacy_normalized, java_normalized, normalization_stats = normalize_and_compare_bodies(
        legacy_response, java_response, rules, differences
    )
    for side in ("legacy", "java"):
        normalization_stats[side].update(header_normalization_stats[side])
    side_effects = {
        "legacy": compare_audit_pair(
            "legacy", source_kind, legacy_before, legacy_after, differences
        ),
        "java": compare_audit_pair("java", source_kind, java_before, java_after, differences),
    }
    differences_truncated = len(differences) >= MAX_DIFFERENCES
    report: Dict[str, Any] = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "operation": "READ_COMPARE",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "environment": args.environment,
        "outcome": "pass" if not differences else "fail",
        "operation_id": operation_id,
        "fixture_id": fixture_id,
        "request": {
            "method": args.method,
            "legacy_origin": legacy_origin,
            "java_origin": java_origin,
            "path_sha256": sha256_bytes(request_path.encode("utf-8")),
            "request_headers_persisted": False,
        },
        "provenance": {
            "snapshot_id": snapshot_id,
            "legacy_artifact_digest": args.legacy_artifact_digest,
            "java_artifact_digest": args.java_artifact_digest,
        },
        "environment_fingerprints": {
            "legacy": fingerprint_report(legacy_fingerprint),
            "java": fingerprint_report(java_fingerprint),
        },
        "responses": {
            "legacy": response_summary(legacy_response, legacy_normalized),
            "java": response_summary(java_response, java_normalized),
        },
        "raw_comparison": {
            "status_equal": legacy_response["status"] == java_response["status"],
            "content_type_equal": legacy_response["content_type"] == java_response["content_type"],
            "content_type_canonical_equal": (
                legacy_response["canonical_content_type"]
                == java_response["canonical_content_type"]
            ),
            "selected_headers_equal": legacy_response["headers"] == java_response["headers"],
            "body_sha256_equal": legacy_response["body"] == java_response["body"],
        },
        "normalization": {
            "ruleset_version": rules["ruleset_version"],
            "ruleset_sha256": rules["ruleset_sha256"],
            "operation_allowlisted": True,
            "legacy": normalization_stats["legacy"],
            "java": normalization_stats["java"],
        },
        "side_effects": side_effects,
        "differences": differences,
        "difference_count": len(differences),
        "differences_truncated": differences_truncated,
        "sensitive_data_policy": {
            "raw_request_headers_persisted": False,
            "raw_response_body_persisted": False,
            "difference_values_are_hashes": True,
            "sensitive_json_pointer_tokens_redacted": True,
            "report_scan_passed": True,
        },
    }
    validate_report_shape(report)
    ensure_report_safe(report)
    write_report_atomic(args.report, report)
    json.dump(
        {
            "operation": "READ_COMPARE",
            "outcome": report["outcome"],
            "difference_count": report["difference_count"],
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
