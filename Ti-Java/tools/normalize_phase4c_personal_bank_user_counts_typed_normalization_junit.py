#!/usr/bin/env python3
"""Normalize the one-leaf Phase 4C typed-normalization Failsafe report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
import xml.etree.ElementTree as ET


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TEST_CLASS = (
    "io.saksk.ti.integration."
    "LegacyPersonalBankUserCountsTypedNormalizationIT"
)
TEST_METHOD = "executesAwareExpiryAsARealFullFilterChainHttpRead"
CASE_ID = "access-shared-aware-expiry-type-error"
REPORT_FILENAME = f"TEST-{TEST_CLASS}.xml"
DEFAULT_REPORT = ROOT / "server/target/failsafe-reports" / REPORT_FILENAME
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-typed-normalization-junit-manifest.json"
)

ARTIFACT_ID = (
    "ti.phase4c.personal-bank-user-counts-typed-normalization-junit-manifest"
)
PREDECESSOR_COMMIT = "c38defa703b358a280122a09019031c040c58ea7"
PREDECESSOR_PARENT = "1dae013e11c76ad858d6695f166a32631eb1525e"
PREDECESSOR_ROOT_TREE = "5ac75d896171039f34650c92829282d8a5e3c3f8"
PREDECESSOR_TI_JAVA_TREE = "07086dc62157018ec1c989832e5e63bfefbae0f0"

HISTORICAL_MANIFEST = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-target-execution-junit-manifest.json"
)
HISTORICAL_MANIFEST_SHA256 = (
    "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b"
)
HISTORICAL_MANIFEST_PAYLOAD_SHA256 = (
    "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c"
)
HISTORICAL_LEAF_PAYLOAD_SHA256 = (
    "77b0f4955931f2ad3206b7a1c0f9c9649b25a18c49bf1b259c452d169e5f0e04"
)
HISTORICAL_EVIDENCE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-execution-evidence.json"
)
HISTORICAL_EVIDENCE_SHA256 = (
    "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002"
)
GOLDEN = "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
GOLDEN_SHA256 = (
    "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1"
)
TEST_SOURCE = (
    "server/src/test/java/io/saksk/ti/integration/"
    "LegacyPersonalBankUserCountsTypedNormalizationIT.java"
)
TEST_SOURCE_SHA256 = (
    "f9bd7dbd51e65abe8f01e80d0d564b9dfdba6856f95c4b06ad21b3705a2f025f"
)
SEED_SOURCE = (
    "server/src/test/resources/db/phase4c/"
    "072-personal-bank-user-counts-typed-normalization-seed.sql"
)
SEED_SOURCE_SHA256 = (
    "089b795d6e6a3efdb1af86641701bd1bf9d30e2c1a94c65a0a32865bdfca29c6"
)
DIFFERENCE_SOURCE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-typed-normalization-approved-difference.md"
)
DIFFERENCE_SOURCE_SHA256 = (
    "3c6ecb59cae4e8a2f31e7dd0ed74bcca56e0cf61830339254523f3f824e652be"
)

POSTGRES_16_IMAGE = (
    "postgres:16.14-alpine@sha256:"
    "57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777"
)
POSTGRES_18_IMAGE = (
    "postgres:18.4-alpine@sha256:"
    "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
REDIS_7_IMAGE = (
    "redis:7.4.7-alpine@sha256:"
    "02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf"
)
RUNTIME_SCOPE = {
    "typed_cast_compatibility": {
        "postgresql_versions": ["16.14", "18.4"],
        "session_time_zones": ["UTC", "America/Los_Angeles"],
        "positive_offset_input": "2026-07-17T13:00:00+08:00",
        "negative_offset_input": "2026-07-17T13:00:00-05:00",
        "canonical_local_datetime": "2026-07-17T13:00:00",
        "cross_version_equal": True,
        "session_timezone_independent": True,
    },
    "full_filter_http": {
        "postgresql_version": "18.4",
        "redis_version": "7.4.7",
        "fixture_origin": (
            "java_string_bind_explicit_cast_insert_before_request_trace"
        ),
        "fixture_sql_literal_seeded": False,
        "fixture_dml_before_request_trace": True,
    },
}

SOURCE_INPUTS = {
    "historical_junit_manifest": {
        "path": HISTORICAL_MANIFEST,
        "sha256": HISTORICAL_MANIFEST_SHA256,
        "document_payload_sha256": HISTORICAL_MANIFEST_PAYLOAD_SHA256,
        "leaf_payload_sha256": HISTORICAL_LEAF_PAYLOAD_SHA256,
    },
    "historical_target_execution_evidence": {
        "path": HISTORICAL_EVIDENCE,
        "sha256": HISTORICAL_EVIDENCE_SHA256,
    },
    "phase4b_golden": {"path": GOLDEN, "sha256": GOLDEN_SHA256},
    "typed_normalization_test": {
        "path": TEST_SOURCE,
        "sha256": TEST_SOURCE_SHA256,
    },
    "typed_normalization_seed": {
        "path": SEED_SOURCE,
        "sha256": SEED_SOURCE_SHA256,
    },
    "typed_normalization_difference": {
        "path": DIFFERENCE_SOURCE,
        "sha256": DIFFERENCE_SOURCE_SHA256,
        "difference_id": "P4C-LEARNING-013",
    },
}

XSI_SCHEMA_ATTRIBUTE = (
    "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
)
EXPECTED_SUITE_ATTRIBUTES = {
    XSI_SCHEMA_ATTRIBUTE,
    "version",
    "name",
    "time",
    "tests",
    "errors",
    "skipped",
    "failures",
    "flakes",
}
EXPECTED_TESTCASE_ATTRIBUTES = {"name", "classname", "time"}
MAX_REPORT_BYTES = 5 * 1024 * 1024
FORBIDDEN_BOMS = (
    b"\xef\xbb\xbf",
    b"\xff\xfe\x00\x00",
    b"\x00\x00\xfe\xff",
    b"\xff\xfe",
    b"\xfe\xff",
)
XML_DECLARATION = re.compile(
    rb"\A<\?xml[ \t]+version=(?P<vq>['\"])1\.0(?P=vq)"
    rb"[ \t]+encoding=(?P<eq>['\"])(?:UTF-8|utf-8)(?P=eq)[ \t]*\?>"
)
FORBIDDEN_RENDERED = (
    re.compile(r"/(?:Users|home|root|private/tmp|var/folders)/"),
    re.compile(r"(?i)\b(?:authorization|cookie|password|secret|token)\s*[:=]"),
    re.compile(r"(?i)\b(?:jdbc|redis|postgres(?:ql)?)://"),
)


class NormalizationError(ValueError):
    """Raised when the raw report or fixed predecessor evidence drifts."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def render_manifest(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _fixed_file(relative: str, expected_sha256: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise NormalizationError(f"fixed source path escapes Ti-Java: {relative}")
    root = ROOT.resolve(strict=True)
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise NormalizationError(f"fixed source path contains symlink: {relative}")
    try:
        resolved = (root / candidate).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise NormalizationError(f"fixed source vanished: {relative}") from error
    if not resolved.is_file():
        raise NormalizationError(f"fixed source is not a regular file: {relative}")
    if sha256_bytes(resolved.read_bytes()) != expected_sha256:
        raise NormalizationError(f"fixed source hash drifted: {relative}")
    return resolved


def _read_fixed_json(relative: str, expected_sha256: str) -> dict[str, Any]:
    try:
        value = json.loads(
            _fixed_file(relative, expected_sha256).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NormalizationError(f"cannot read fixed JSON: {relative}") from error
    if not isinstance(value, dict):
        raise NormalizationError(f"fixed JSON is not an object: {relative}")
    return value


def validate_fixed_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    historical = _read_fixed_json(HISTORICAL_MANIFEST, HISTORICAL_MANIFEST_SHA256)
    if (
        historical.get("document_payload_sha256")
        != HISTORICAL_MANIFEST_PAYLOAD_SHA256
        or document_payload_sha256(historical)
        != HISTORICAL_MANIFEST_PAYLOAD_SHA256
        or historical.get("result", {}).get("leaf_payload_sha256")
        != HISTORICAL_LEAF_PAYLOAD_SHA256
        or historical.get("result", {}).get("totals", {}).get("tests") != 60
        or len(historical.get("result", {}).get("leaves", [])) != 60
    ):
        raise NormalizationError("historical JUnit manifest boundary drifted")
    old_aware = historical["result"]["leaves"][-1]
    if {
        "ordinal": old_aware.get("ordinal"),
        "logical_id": old_aware.get("logical_id"),
        "execution_disposition": old_aware.get("execution_disposition"),
        "outcome": old_aware.get("outcome"),
    } != {
        "ordinal": 60,
        "logical_id": CASE_ID,
        "execution_disposition": "EXECUTED_TYPED_COLLAPSE",
        "outcome": "passed",
    }:
        raise NormalizationError("historical aware leaf drifted")

    evidence = _read_fixed_json(HISTORICAL_EVIDENCE, HISTORICAL_EVIDENCE_SHA256)
    evidence_cases = {
        item.get("case_id"): item for item in evidence.get("cases", [])
    }
    aware = evidence_cases.get(CASE_ID, {})
    malformed = evidence_cases.get("access-shared-malformed-expiry-value-error", {})
    if (
        aware.get("execution_disposition") != "EXECUTED_TYPED_COLLAPSE"
        or malformed.get("execution_disposition") != "EXECUTED_TYPED_REJECTION"
        or malformed.get("typed_evidence", {}).get("sqlstate") != "22007"
    ):
        raise NormalizationError("historical typed dispositions drifted")

    golden = _read_fixed_json(GOLDEN, GOLDEN_SHA256)
    matches = [
        item for item in golden.get("cases", []) if item.get("case_id") == CASE_ID
    ]
    if len(matches) != 1:
        raise NormalizationError("aware golden case cardinality drifted")
    golden_case = matches[0]
    if {
        "route_id": golden_case.get("route_id"),
        "bank_id": golden_case.get("bank_id"),
        "session_actor": golden_case.get("session_actor"),
        "bearer_actor": golden_case.get("bearer_actor"),
        "source_status": golden_case.get("response", {}).get("status"),
        "path": golden_case.get("request", {}).get("path"),
        "accept": golden_case.get("request", {}).get("headers", {}).get("Accept"),
    } != {
        "route_id": "6858f6fa506f",
        "bank_id": 99551,
        "session_actor": "shared_aware",
        "bearer_actor": "none",
        "source_status": 500,
        "path": "/api/user/banks/api/99551/user-counts",
        "accept": "application/json",
    }:
        raise NormalizationError("aware golden case boundary drifted")

    for descriptor in SOURCE_INPUTS.values():
        _fixed_file(descriptor["path"], descriptor["sha256"])
    return historical, evidence, golden_case


def _parse_report(report: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = report.read_bytes()
    except OSError as error:
        raise NormalizationError("cannot read typed-normalization report") from error
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise NormalizationError("typed-normalization report size is invalid")
    if any(raw.startswith(bom) for bom in FORBIDDEN_BOMS):
        raise NormalizationError("byte-order marks are forbidden")
    declaration = XML_DECLARATION.match(raw)
    if declaration is None:
        raise NormalizationError("report requires a legal UTF-8 XML 1.0 declaration")
    tail = raw[declaration.end():]
    upper = tail.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise NormalizationError("DTD and entity input is forbidden")
    if b"<!--" in tail:
        raise NormalizationError("XML comments are forbidden")
    if b"<?" in tail:
        raise NormalizationError("XML processing instructions are forbidden")
    try:
        suite = ET.fromstring(raw)
    except ET.ParseError as error:
        raise NormalizationError("typed-normalization report is invalid XML") from error
    if suite.tag != "testsuite" or set(suite.attrib) != EXPECTED_SUITE_ATTRIBUTES:
        raise NormalizationError("unexpected testsuite shape")
    expected = {
        "version": "3.0.2",
        "name": TEST_CLASS,
        "tests": "1",
        "errors": "0",
        "skipped": "0",
        "failures": "0",
        "flakes": "0",
    }
    for key, value in expected.items():
        if suite.attrib.get(key) != value:
            raise NormalizationError(f"testsuite {key} drifted")
    children = list(suite)
    if any(child.tag not in {"properties", "testcase", "system-out", "system-err"}
           for child in children):
        raise NormalizationError("unknown testsuite child")
    testcases = [child for child in children if child.tag == "testcase"]
    if len(testcases) != 1:
        raise NormalizationError("typed-normalization testcase cardinality drifted")
    testcase = testcases[0]
    if set(testcase.attrib) != EXPECTED_TESTCASE_ATTRIBUTES:
        raise NormalizationError("unexpected testcase shape")
    if (
        testcase.attrib.get("name") != TEST_METHOD
        or testcase.attrib.get("classname") != TEST_CLASS
    ):
        raise NormalizationError("typed-normalization testcase identity drifted")
    if any(child.tag not in {"system-out", "system-err"} for child in testcase):
        raise NormalizationError("non-passing or unknown testcase child")
    projection = {
        "suite": TEST_CLASS,
        "tests": 1,
        "testcase": {"name": TEST_METHOD, "classname": TEST_CLASS},
        "outcome": "passed",
    }
    return raw, projection


def normalize_report(report: Path) -> dict[str, Any]:
    historical, _, golden_case = validate_fixed_sources()
    raw, projection = _parse_report(report)
    old_leaf = historical["result"]["leaves"][-1]
    new_leaf = {
        "physical_ordinal": 61,
        "logical_id": CASE_ID,
        "xml_name": TEST_METHOD,
        "suite": TEST_CLASS,
        "group": "non_fault_http",
        "execution_disposition": "EXECUTED_FULL_CONTEXT_HTTP",
        "target_status": 200,
        "business_jdbc_reached": True,
        "outcome": "passed",
    }
    override = {
        "case_id": CASE_ID,
        "difference_id": "P4C-LEARNING-013",
        "historical_execution_disposition": "EXECUTED_TYPED_COLLAPSE",
        "effective_execution_disposition": "EXECUTED_FULL_CONTEXT_HTTP",
        "historical_source_status": 500,
        "target_status": 200,
        "target_data": {
            "total": 9,
            "favorites": 0,
            "mistakes": 0,
            "types": ["判断题", "简答题", "填空题", "多选题", "选择题", "选择题", "简答题"],
            "shuffle_options_available": False,
        },
        "postgresql_projection": {
            "input_kind": "string_bind_explicit_cast",
            "input": "2026-07-17T13:00:00+08:00",
            "column_type": "timestamp without time zone",
            "canonical_local_datetime": "2026-07-17T13:00:00",
            "offset_provenance_erased": True,
            "fixture_share_id": 99661,
            "fixture_share_record_id": 99681,
            "cast_compatibility_versions": ["16.14", "18.4"],
            "cast_session_time_zones": ["UTC", "America/Los_Angeles"],
            "full_filter_http_version": "18.4",
            "http_fixture_origin": (
                "java_string_bind_explicit_cast_insert_before_request_trace"
            ),
            "http_fixture_sql_literal_seeded": False,
        },
        "request": {
            "route_id": golden_case["route_id"],
            "path": golden_case["request"]["path"],
            "accept": golden_case["request"]["headers"]["Accept"],
            "session_actor": golden_case["session_actor"],
            "bearer_actor": golden_case["bearer_actor"],
        },
        "proof_scope": (
            "Java String CAST compatibility on PostgreSQL 16.14 and 18.4 across "
            "UTC and America/Los_Angeles; full-production-filter-chain MockMvc "
            "HTTP on PostgreSQL 18.4 and Redis 7.4.7; not random-port Tomcat "
            "network evidence"
        ),
    }
    effective_summary = {
        "logical_disposition_count": 59,
        "http_disposition_count": 58,
        "typed_rejection_count": 1,
        "non_fault_http_count": 47,
        "postgres_abort_http_count": 11,
        "business_jdbc_http_count": 50,
        "pre_business_http_count": 8,
        "api_alias_http_count": 44,
        "web_alias_http_count": 14,
        "http_status_counts": {
            "200": 35,
            "302": 5,
            "401": 3,
            "403": 10,
            "500": 5,
        },
    }
    proof_payload = {
        "new_leaf": new_leaf,
        "superseded_historical_leaf": old_leaf,
        "effective_override": override,
        "effective_summary": effective_summary,
        "runtime_scope": RUNTIME_SCOPE,
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": ARTIFACT_ID,
        "status": "passed_aware_http_normalized_malformed_typed_rejection_retained",
        "scope": "phase4c-personal-bank-user-counts-typed-normalization-junit",
        "source_anchor": {
            "predecessor_commit_sha1": PREDECESSOR_COMMIT,
            "predecessor_parent_sha1": PREDECESSOR_PARENT,
            "predecessor_root_tree_sha1": PREDECESSOR_ROOT_TREE,
            "predecessor_ti_java_tree_sha1": PREDECESSOR_TI_JAVA_TREE,
            "new_evidence_was_executed_after_predecessor": True,
            "current_manifest_and_source_bytes_external_git_anchor_complete": False,
            "post_push_external_anchor_required": True,
        },
        "source_inputs": SOURCE_INPUTS,
        "runner": {
            "report_format": "maven-failsafe-junit-xml",
            "report_schema_version": "3.0.2",
            "java_release": 25,
            "maven_version": "3.9.16",
            "postgresql_images": {
                "16.14_cast_compatibility": POSTGRES_16_IMAGE,
                "18.4_cast_and_full_filter_http": POSTGRES_18_IMAGE,
            },
            "redis_image": REDIS_7_IMAGE,
            "test_class": TEST_CLASS,
        },
        "raw_report": {
            "expected_filename": REPORT_FILENAME,
            "sha256": sha256_bytes(raw),
            "byte_count": len(raw),
            "tracked": False,
            "committed": False,
            "content_embedded": False,
        },
        "normalization_policy": {
            "suite_and_testcase_allowlist_exact": True,
            "discarded_elements": ["properties", "system-out", "system-err"],
            "discarded_attributes": ["testsuite@time", "testcase@time"],
            "arbitrary_xml_text_copied": False,
            "failure_error_skip_or_flake_allowed": False,
            "raw_report_hash_role": "single_execution_binding_not_cross_run_stability",
        },
        "result": {
            "physical_evidence": {
                "historical_leaf_count": 60,
                "new_leaf_count": 1,
                "aggregate_leaf_count": 61,
                "passed": 61,
                "failed_error_skipped_or_flaky": 0,
            },
            "effective_evidence": {
                "logical_disposition_count": 59,
                "supplementary_authentication_leaf_count": 1,
                "selected_effective_proof_leaf_count": 60,
                "superseded_historical_representation_leaf_count": 1,
                "superseded_leaf_double_counted": False,
            },
            "effective_summary": effective_summary,
            "new_leaf": new_leaf,
            "superseded_historical_leaf": old_leaf,
            "effective_override": override,
            "runtime_scope": RUNTIME_SCOPE,
            "raw_projection_sha256": sha256_json(projection),
            "proof_payload_sha256": sha256_json(proof_payload),
        },
        "authorization": {
            "typed_normalization_execution_complete": True,
            "typed_parity_review_complete": False,
            "current_manifest_and_source_bytes_external_git_anchor_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "production_cutover": False,
        },
        "confidentiality": {
            "properties_removed": True,
            "stdout_removed": True,
            "stderr_removed": True,
            "timings_removed": True,
            "absolute_paths_removed": True,
            "credentials_tokens_cookies_and_urls_removed": True,
            "sensitive_output_scan_passed": True,
            "independently_signed_provenance": False,
        },
    }
    rendered = canonical_json(manifest)
    for pattern in FORBIDDEN_RENDERED:
        if pattern.search(rendered):
            raise NormalizationError("normalized manifest contains sensitive material")
    manifest["document_payload_sha256"] = document_payload_sha256(manifest)
    return manifest


def write_manifest(report: Path, output: Path) -> dict[str, Any]:
    if report.resolve() == output.resolve():
        raise NormalizationError("report and output paths must differ")
    manifest = normalize_report(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(render_manifest(manifest))
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize the fixed one-leaf typed-normalization report."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = write_manifest(args.report, args.output)
    print(canonical_json({
        "output": args.output.as_posix(),
        "raw_report_sha256": manifest["raw_report"]["sha256"],
        "document_payload_sha256": manifest["document_payload_sha256"],
        "proof_payload_sha256": manifest["result"]["proof_payload_sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
