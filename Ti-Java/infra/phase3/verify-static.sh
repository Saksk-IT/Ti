#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
TI_JAVA_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
COMPARATOR="$SCRIPT_DIR/read_compare.py"
TEST_FILE="$SCRIPT_DIR/test_read_compare.py"
WRITE_COMPARATOR="$SCRIPT_DIR/isolated_write_compare.py"
WRITE_TEST_FILE="$SCRIPT_DIR/test_isolated_write_compare.py"
RULES_FILE="$SCRIPT_DIR/normalization-rules.v1.json"
SCHEMA_FILE="$TI_JAVA_DIR/docs/refactor/phase3/read-compare-report.schema.json"

command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 is required" >&2
    exit 1
}

python3 -m py_compile "$COMPARATOR" "$TEST_FILE" "$WRITE_COMPARATOR" "$WRITE_TEST_FILE"

python3 - "$COMPARATOR" "$RULES_FILE" "$SCHEMA_FILE" <<'PY'
import json
import pathlib
import re
import sys

comparator_path, rules_path, schema_path = map(pathlib.Path, sys.argv[1:])
source = comparator_path.read_text(encoding="utf-8")
rules = json.loads(rules_path.read_text(encoding="utf-8"))
schema = json.loads(schema_path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise SystemExit(f"Phase 3 READ_COMPARE static gate failed: {message}")


require(rules == {
    "schema_version": "1",
    "ruleset_version": "phase3-read-normalization-v1",
    "operations": {
        "88d7dc05cdbb": {
            "ignore_json_pointers": [],
            "unordered_array_json_pointers": [],
            "ignore_response_headers": [],
        },
    },
}, "committed normalization allowlist must contain only the exact Phase 3 GET rule")
require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
        "report schema draft")
require(schema.get("additionalProperties") is False, "report schema top-level closure")
required = set(schema.get("required", []))
for field in (
    "operation",
    "environment",
    "request",
    "environment_fingerprints",
    "responses",
    "normalization",
    "side_effects",
    "differences",
    "sensitive_data_policy",
):
    require(field in required, f"report schema missing {field}")
require(schema["properties"]["operation"].get("const") == "READ_COMPARE",
        "report operation marker")
require(schema["properties"]["environment"].get("enum") == ["local", "test"],
        "report environment allowlist")
require(schema["properties"]["request"]["properties"]["method"].get("enum") ==
        ["GET", "HEAD"], "schema method allowlist")
require(schema["properties"]["request"]["properties"]["request_headers_persisted"].get("const")
        is False, "request header persistence prohibition")
require("canonical_content_type" in schema["$defs"]["responseSummary"]["required"],
        "canonical Content-Type response summary")
require("content_type_canonical_equal" in schema["properties"]["raw_comparison"]["required"],
        "canonical Content-Type equality conclusion")
policy = schema["properties"]["sensitive_data_policy"]["properties"]
require(policy["raw_request_headers_persisted"].get("const") is False,
        "raw request headers must be prohibited")
require(policy["raw_response_body_persisted"].get("const") is False,
        "raw response bodies must be prohibited")
require(schema["$defs"]["difference"]["properties"]["kind"].get("enum") == [
    "value",
    "missing",
    "type",
    "array_order",
    "array_length",
    "invalid_json",
    "json_representation",
    "body_bytes",
], "difference kind contract")

for marker in (
    '"READ_COMPARE"',
    'args.method not in ("GET", "HEAD")',
    'NoRedirectHandler',
    'urllib.request.ProxyHandler({})',
    'NON_LOOPBACK_ORIGIN',
    'SAME_ORIGIN_FORBIDDEN',
    'PRODUCTION_FORBIDDEN',
    'SHARED_ENVIRONMENT_FINGERPRINT',
    'SENSITIVE_OUTPUT_BLOCKED',
    'STALE_NORMALIZATION_RULE',
    'canonical_content_type',
    'os.link(temporary_name, target)',
    'request_headers_persisted": False',
    'raw_response_body_persisted": False',
):
    require(marker in source, f"comparator safety marker {marker}")
require("urllib.request.urlretrieve" not in source, "redirect-capable convenience fetch is forbidden")
require("shell=True" not in source, "auditor commands must never use a shell")
require("resolve().parent.parent.parent" not in source, "parent repository discovery is forbidden")
require(re.search(r"SAFE_RESPONSE_HEADERS\s*=", source) is not None,
        "selected response header allowlist")
PY

python3 - "$WRITE_COMPARATOR" <<'PY'
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise SystemExit(f"Phase 3 ISOLATED_WRITE_COMPARE static gate failed: {message}")


for marker in (
    '"ISOLATED_WRITE_COMPARE"',
    'OPERATION_ID = "identity.auth.login"',
    'HTTP_METHOD = "POST"',
    'HTTP_PATH = "/api/login"',
    '"dispatch": "external-serial-only"',
    '"writes_issued_by_comparator": 0',
    '"network_capability_present": False',
    'SHARED_ENVIRONMENT_FINGERPRINT',
    'EVIDENCE_RESOURCE_MISMATCH',
    'NON_SERIAL_EVIDENCE',
    'P3-AUTH-002',
    'os.link(temporary_name, target)',
    '"raw_password_hash_persisted": False',
    '"raw_cookie_or_session_id_persisted": False',
):
    require(marker in source, f"offline write comparator safety marker {marker}")

for forbidden in (
    "import socket",
    "import urllib",
    "import http.client",
    "import requests",
    "import subprocess",
    "shell=True",
    "resolve().parent.parent.parent",
):
    require(forbidden not in source, f"offline write comparator forbidden capability {forbidden}")
PY

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ti-phase3-verify.XXXXXX")
cleanup() {
    rm -rf -- "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

(
    cd "$TEMP_DIR"
    python3 "$TEST_FILE"
    python3 "$WRITE_TEST_FILE"
)

echo "Phase 3 READ_COMPARE and ISOLATED_WRITE_COMPARE static/unit gates passed"
