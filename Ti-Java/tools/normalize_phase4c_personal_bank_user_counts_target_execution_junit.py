#!/usr/bin/env python3
"""Normalize the Phase 4C user-counts target JUnit report without leaking it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TEST_CLASS = (
    "io.saksk.ti.integration."
    "LegacyPersonalBankUserCountsGoldenTargetExecutionIT"
)
REPORT_FILENAME = f"TEST-{TEST_CLASS}.xml"
DEFAULT_REPORT = ROOT / "server" / "target" / "failsafe-reports" / REPORT_FILENAME
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-target-execution-junit-manifest.json"
)
EVIDENCE_PATH = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-execution-evidence.json"
)

ARTIFACT_ID = (
    "ti.phase4c.personal-bank-user-counts-target-execution-junit-manifest"
)
SOURCE_COMMIT = "0531b3c9272f9743a374edcf5c8bbeb72643eb1b"
SOURCE_PARENT = "67dddb831bac8499e80f4af57c959e9c6b244519"
SOURCE_ROOT_TREE = "816e2a7376d147f4a4d1478586cd384edf2c2a8a"
TI_JAVA_TREE = "1d24e46d33c25170caddf6e25247a7b2945390e4"
EVIDENCE_SHA256 = (
    "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002"
)
EVIDENCE_CASE_PAYLOAD_SHA256 = (
    "75be10b21c2c006d978575dda314003536ac8920ecd6c6fbe64cfdd264d2b17f"
)
EVIDENCE_DOCUMENT_PAYLOAD_SHA256 = (
    "5ca521f808aa67ea4589d044d04a0037e448dc9d2a519e3b6af7d776b2cb89de"
)
GOLDEN_ORDERED_CASE_IDS_SHA256 = (
    "d8c9aa1c8fdcfd833f2d7bbba3e21adcc3e696954b8756ace69405428bbdfad8"
)
EXECUTION_ORDER_CASE_IDS_SHA256 = (
    "4f953b182d2c8fd4fecf2f47876b2b649f41209a6b338e1e9eec689eb910f649"
)
ORDERED_LOGICAL_LEAF_IDS_SHA256 = (
    "ef35ab8704312f3f5056e572cd2584c7f4b3431274f5ec5abb25561cc4f6956c"
)
ORDERED_XML_NAMES_SHA256 = (
    "e7b1582e0e6166ca34876c54e5a1fefb1e22eeda6cbeb430bbe50f1042b220c8"
)
RAW_PROJECTION_SHA256 = (
    "483c6a52d6cebbc8fd3b69cf31cbccfe5aca3c20a50577bf8324e0a376a127a1"
)

SOURCE_INPUTS = {
    "target_execution_contract": {
        "path": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-http-target-execution-contract.json"
        ),
        "sha256": (
            "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460"
        ),
    },
    "python_successor_bridge": {
        "path": "tools/phase4c_http_target_execution_successor_acceptance.py",
        "sha256": (
            "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c"
        ),
    },
    "java_successor_bridge": {
        "path": (
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
        ),
        "sha256": (
            "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15"
        ),
    },
    "target_execution_test": {
        "path": (
            "server/src/test/java/io/saksk/ti/integration/"
            "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java"
        ),
        "sha256": (
            "45b1a96fcc66a436551a8ce7604b304f2a479cece87c431a3a3c003da01d5ca1"
        ),
    },
    "target_execution_evidence": {
        "path": EVIDENCE_PATH.relative_to(ROOT).as_posix(),
        "sha256": EVIDENCE_SHA256,
        "case_payload_sha256": EVIDENCE_CASE_PAYLOAD_SHA256,
        "document_payload_sha256": EVIDENCE_DOCUMENT_PAYLOAD_SHA256,
    },
    "phase4b_golden": {
        "path": "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
        "sha256": (
            "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1"
        ),
        "ordered_case_ids_sha256": GOLDEN_ORDERED_CASE_IDS_SHA256,
    },
    "historical_mapping": {
        "path": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-golden-target-mapping-evidence.json"
        ),
        "sha256": (
            "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3"
        ),
    },
    "maven_runner": {
        "path": "infra/phase2/verify-in-maven-container.sh",
        "sha256": (
            "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e"
        ),
    },
    "maven_project": {
        "path": "server/pom.xml",
        "sha256": (
            "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b"
        ),
    },
    "maven_wrapper": {
        "path": "server/.mvn/wrapper/maven-wrapper.properties",
        "sha256": (
            "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab"
        ),
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
    r"\A<\?xml[ \t]+version=(?P<version_quote>['\"])1\.0(?P=version_quote)"
    r"[ \t]+encoding=(?P<encoding_quote>['\"])(?:UTF-8|utf-8)"
    r"(?P=encoding_quote)[ \t]*\?>"
)

FORBIDDEN_OUTPUT_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)\b(?:authorization|set-cookie|cookie|password|passwd|secret|token)"
        r"\s*[:=]\s*[^,}\s]+"
    ),
    re.compile(r"/(?:Users|home|root|private/tmp|var/folders)/"),
    re.compile(r"(?i)\b(?:jdbc|redis|postgres(?:ql)?)://[^\s\"']+"),
)


class NormalizationError(ValueError):
    """Raised when a report or its evidence is not the exact accepted shape."""


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
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _require_unique(values: list[str], label: str) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count != 1)
    if duplicates:
        raise NormalizationError(f"duplicate {label}: {duplicates}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NormalizationError(f"cannot load JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise NormalizationError(f"JSON root must be an object: {path}")
    return payload


def load_fixed_evidence(path: Path = EVIDENCE_PATH) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise NormalizationError(f"cannot read target-execution evidence: {path}") from exc
    if sha256_bytes(raw) != EVIDENCE_SHA256:
        raise NormalizationError("target-execution evidence physical SHA-256 drifted")
    evidence = _load_json(path)
    cases = evidence.get("cases")
    if not isinstance(cases, list):
        raise NormalizationError("target-execution evidence cases must be an array")
    if sha256_json(cases) != EVIDENCE_CASE_PAYLOAD_SHA256:
        raise NormalizationError("target-execution evidence case payload drifted")
    if evidence.get("document_payload_sha256") != EVIDENCE_DOCUMENT_PAYLOAD_SHA256:
        raise NormalizationError("target-execution evidence payload field drifted")
    if document_payload_sha256(evidence) != EVIDENCE_DOCUMENT_PAYLOAD_SHA256:
        raise NormalizationError("target-execution evidence document payload is invalid")
    return evidence


def build_leaf_plan(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    cases = evidence.get("cases")
    if not isinstance(cases, list) or len(cases) != 59:
        raise NormalizationError("target-execution evidence must contain 59 cases")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != 59 or any(not isinstance(case_id, str) for case_id in case_ids):
        raise NormalizationError("target-execution evidence has an invalid case id")
    _require_unique(case_ids, "logical case id")

    execution_groups = (
        (
            "non_fault_http",
            "EXECUTED_FULL_CONTEXT_HTTP",
            "executesAllFortySixNonFaultHttpCasesThroughTheRealTarget",
            46,
        ),
        (
            "postgres_abort_http",
            "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT",
            "executesAllElevenFaultCasesWithRealPostgresqlFailures",
            11,
        ),
    )
    plan: list[dict[str, Any]] = []
    supplementary = evidence.get("execution_harness", {}).get("supplementary_junit", {})
    supplementary_method = supplementary.get("method")
    if supplementary_method != (
            "realFlaskExchangeAndAuthoritativeTargetSessionBothReachApplicationJdbc"):
        raise NormalizationError("supplementary JUnit method drifted")
    plan.append({
        "ordinal": 1,
        "xml_name": supplementary_method,
        "logical_id": supplementary_method,
        "group": "supplementary_auth_probe",
        "leaf_type": "test",
        "factory_or_method": supplementary_method,
        "execution_disposition": None,
        "outcome": "passed",
    })

    ordinal = 2
    for group, disposition, factory, expected_count in execution_groups:
        selected = [case for case in cases if case.get("execution_disposition") == disposition]
        if len(selected) != expected_count:
            raise NormalizationError(f"unexpected {group} case count")
        for index, case in enumerate(selected, start=1):
            junit = case.get("junit")
            if not isinstance(junit, dict):
                raise NormalizationError(f"missing JUnit evidence: {case.get('case_id')}")
            if junit.get("class") != TEST_CLASS:
                raise NormalizationError(f"JUnit class drifted: {case.get('case_id')}")
            if junit.get("factory_or_method") != factory:
                raise NormalizationError(f"JUnit factory drifted: {case.get('case_id')}")
            if junit.get("leaf_type") != "dynamic_test":
                raise NormalizationError(f"JUnit leaf type drifted: {case.get('case_id')}")
            if junit.get("dynamic_test_name") != case.get("case_id"):
                raise NormalizationError(f"dynamic test name drifted: {case.get('case_id')}")
            if case.get("execution_ordinal") != ordinal - 1:
                raise NormalizationError(f"execution ordinal drifted: {case.get('case_id')}")
            if junit.get("disposition_leaf_ordinal") != ordinal:
                raise NormalizationError(f"JUnit ordinal drifted: {case.get('case_id')}")
            plan.append({
                "ordinal": ordinal,
                "xml_name": f"{factory}()[{index}]",
                "logical_id": case["case_id"],
                "group": group,
                "leaf_type": "dynamic_test",
                "factory_or_method": factory,
                "execution_disposition": disposition,
                "outcome": "passed",
            })
            ordinal += 1

    typed = sorted(
        (
            case for case in cases
            if case.get("execution_disposition") in {
                "EXECUTED_TYPED_REJECTION",
                "EXECUTED_TYPED_COLLAPSE",
            }
        ),
        key=lambda case: case.get("execution_ordinal", -1),
    )
    if len(typed) != 2:
        raise NormalizationError("unexpected typed PostgreSQL case count")
    for case in typed:
        junit = case.get("junit")
        if not isinstance(junit, dict):
            raise NormalizationError(f"missing typed JUnit evidence: {case.get('case_id')}")
        method = junit.get("factory_or_method")
        if (
            junit.get("class") != TEST_CLASS
            or junit.get("leaf_type") != "test"
            or not isinstance(method, str)
            or junit.get("dynamic_test_name") is not None
            or case.get("execution_ordinal") != ordinal - 1
            or junit.get("disposition_leaf_ordinal") != ordinal
        ):
            raise NormalizationError(f"typed JUnit evidence drifted: {case.get('case_id')}")
        plan.append({
            "ordinal": ordinal,
            "xml_name": method,
            "logical_id": case["case_id"],
            "group": "typed_postgresql",
            "leaf_type": "test",
            "factory_or_method": method,
            "execution_disposition": case["execution_disposition"],
            "outcome": "passed",
        })
        ordinal += 1

    if len(plan) != 60 or [leaf["ordinal"] for leaf in plan] != list(range(1, 61)):
        raise NormalizationError("normalized JUnit plan is not exactly 60 ordered leaves")
    _require_unique([leaf["logical_id"] for leaf in plan], "logical leaf id")
    _require_unique([leaf["xml_name"] for leaf in plan], "XML testcase name")

    execution_case_ids = [leaf["logical_id"] for leaf in plan[1:]]
    logical_ids = [leaf["logical_id"] for leaf in plan]
    xml_names = [leaf["xml_name"] for leaf in plan]
    if sha256_json(execution_case_ids) != EXECUTION_ORDER_CASE_IDS_SHA256:
        raise NormalizationError("execution-order case-id SHA-256 drifted")
    if sha256_json(logical_ids) != ORDERED_LOGICAL_LEAF_IDS_SHA256:
        raise NormalizationError("ordered logical-leaf SHA-256 drifted")
    if sha256_json(xml_names) != ORDERED_XML_NAMES_SHA256:
        raise NormalizationError("ordered XML-name SHA-256 drifted")
    return plan


def _parse_nonnegative_decimal(value: str | None, label: str) -> None:
    try:
        parsed = Decimal(value) if value is not None else Decimal("-1")
    except (InvalidOperation, ValueError) as exc:
        raise NormalizationError(f"invalid {label}") from exc
    if not parsed.is_finite() or parsed < 0:
        raise NormalizationError(f"invalid {label}")


def _parse_exact_count(value: str | None, expected: int, label: str) -> None:
    if value is None or not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise NormalizationError(f"invalid {label}")
    if int(value) != expected:
        raise NormalizationError(f"unexpected {label}: {value}")


def _parse_report(report: Path, plan: list[dict[str, Any]]) -> tuple[bytes, list[dict[str, str]]]:
    try:
        raw = report.read_bytes()
    except OSError as exc:
        raise NormalizationError(f"cannot read JUnit report: {report}") from exc
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise NormalizationError("JUnit report is empty or exceeds the size limit")
    if any(raw.startswith(bom) for bom in FORBIDDEN_BOMS):
        raise NormalizationError("XML byte-order marks are forbidden; strict UTF-8 is required")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise NormalizationError("JUnit XML must be strict UTF-8") from exc
    if "\ufeff" in text:
        raise NormalizationError("XML byte-order marks are forbidden; strict UTF-8 is required")
    upper_text = text.upper()
    if "<!DOCTYPE" in upper_text or "<!ENTITY" in upper_text:
        raise NormalizationError("DTD and entity declarations are forbidden")
    declaration = XML_DECLARATION.match(text)
    if declaration is None:
        raise NormalizationError(
            "JUnit XML must start with a legal UTF-8 XML 1.0 declaration"
        )
    remainder = text[declaration.end():]
    if "<!--" in remainder:
        raise NormalizationError("XML comments after the declaration are forbidden")
    if "<?" in remainder:
        raise NormalizationError(
            "XML processing instructions after the declaration are forbidden"
        )
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(
            insert_comments=True,
            insert_pis=True,
        ))
        root = ET.fromstring(text, parser=parser)
    except ET.ParseError as exc:
        raise NormalizationError("JUnit report is not well-formed XML") from exc
    if root.tag != "testsuite":
        raise NormalizationError("JUnit root must be one testsuite")
    if set(root.attrib) != EXPECTED_SUITE_ATTRIBUTES:
        raise NormalizationError("JUnit testsuite attributes drifted")
    if root.attrib.get(XSI_SCHEMA_ATTRIBUTE) != (
            "https://maven.apache.org/surefire/maven-failsafe-plugin/"
            "xsd/failsafe-test-report.xsd"):
        raise NormalizationError("JUnit Failsafe schema location drifted")
    if root.attrib.get("version") != "3.0.2" or root.attrib.get("name") != TEST_CLASS:
        raise NormalizationError("JUnit suite identity drifted")
    _parse_nonnegative_decimal(root.attrib.get("time"), "testsuite time")
    _parse_exact_count(root.attrib.get("tests"), 60, "testsuite tests")
    for field in ("failures", "errors", "skipped", "flakes"):
        _parse_exact_count(root.attrib.get(field), 0, f"testsuite {field}")

    children = list(root)
    if not children or children[0].tag != "properties":
        raise NormalizationError("JUnit properties node must be first")
    if sum(child.tag == "properties" for child in children) != 1:
        raise NormalizationError("JUnit must contain exactly one properties node")
    properties = children[0]
    if properties.attrib:
        raise NormalizationError("JUnit properties node has unexpected attributes")
    for prop in properties:
        if prop.tag != "property" or set(prop.attrib) - {"name", "value"}:
            raise NormalizationError("JUnit property shape drifted")
        if not prop.attrib.get("name") or list(prop):
            raise NormalizationError("JUnit property is malformed")

    testcase_nodes = children[1:]
    if any(child.tag != "testcase" for child in testcase_nodes):
        raise NormalizationError("JUnit testsuite contains an unknown child node")
    if len(testcase_nodes) != 60:
        raise NormalizationError("JUnit report must contain exactly 60 testcase nodes")

    projection: list[dict[str, str]] = []
    observed_names: list[str] = []
    for ordinal, (case, expected) in enumerate(zip(testcase_nodes, plan), start=1):
        if set(case.attrib) != EXPECTED_TESTCASE_ATTRIBUTES:
            raise NormalizationError(f"testcase attributes drifted at leaf {ordinal}")
        if case.attrib.get("classname") != TEST_CLASS:
            raise NormalizationError(f"testcase class drifted at leaf {ordinal}")
        if case.attrib.get("name") != expected["xml_name"]:
            raise NormalizationError(f"testcase name/order drifted at leaf {ordinal}")
        _parse_nonnegative_decimal(case.attrib.get("time"), f"testcase time at leaf {ordinal}")
        observed_names.append(case.attrib["name"])
        for child in case:
            if child.tag in {"failure", "error", "skipped", "flakyFailure", "rerunFailure"}:
                raise NormalizationError(
                    f"non-passing JUnit outcome at leaf {ordinal}: {child.tag}"
                )
            if child.tag not in {"system-out", "system-err"}:
                raise NormalizationError(f"unknown testcase child at leaf {ordinal}: {child.tag}")
            if child.attrib or list(child):
                raise NormalizationError(f"malformed discarded output at leaf {ordinal}")
        projection.append({
            "classname": TEST_CLASS,
            "name": case.attrib["name"],
            "outcome": "passed",
        })
    _require_unique(observed_names, "observed XML testcase name")
    if sha256_json(observed_names) != ORDERED_XML_NAMES_SHA256:
        raise NormalizationError("observed XML-name projection SHA-256 drifted")
    if sha256_json(projection) != RAW_PROJECTION_SHA256:
        raise NormalizationError("normalized raw JUnit projection SHA-256 drifted")
    return raw, projection


def _assert_confidential(document: dict[str, Any]) -> None:
    rendered = canonical_json(document)
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(rendered):
            raise NormalizationError(
                f"normalized manifest contains forbidden sensitive material: {pattern.pattern}"
            )


def normalize_report(
    report: Path,
    *,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fixed_evidence = load_fixed_evidence() if evidence is None else deepcopy(evidence)
    plan = build_leaf_plan(fixed_evidence)
    raw, projection = _parse_report(report, plan)
    groups = Counter(leaf["group"] for leaf in plan)
    dispositions = Counter(
        leaf["execution_disposition"]
        for leaf in plan
        if leaf["execution_disposition"] is not None
    )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": ARTIFACT_ID,
        "status": "passed_normalized_sensitive_runtime_output_removed",
        "scope": "phase4c-personal-bank-user-counts-target-execution-junit",
        "source_anchor": {
            "git_commit_sha1": SOURCE_COMMIT,
            "git_parent_sha1": SOURCE_PARENT,
            "git_root_tree_sha1": SOURCE_ROOT_TREE,
            "ti_java_tree_sha1": TI_JAVA_TREE,
            "remote_ref": "origin/main",
            "commit_was_pushed_before_capture": True,
            "head_equaled_origin_main_at_capture": True,
            "ti_java_tracked_clean_at_capture": True,
            "ti_java_untracked_file_count_at_capture": 0,
            "capture_state_is_declared_metadata": True,
            "normalizer_does_not_revalidate_mutable_remote_ref": True,
        },
        "source_inputs": deepcopy(SOURCE_INPUTS),
        "runner": {
            "report_format": "maven-failsafe-junit-xml",
            "report_schema_version": "3.0.2",
            "maven_image": (
                "maven:3.9.16-eclipse-temurin-25@sha256:"
                "7e461cec477077c1d9e50b13df8aef9018764410f4c4cd7c34803f10c4c99e4c"
            ),
            "postgresql_image": (
                "postgres:18.4-alpine@sha256:"
                "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
            ),
            "redis_image": (
                "redis:7.4.7-alpine@sha256:"
                "02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf"
            ),
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
            "canonical_json": (
                "utf8;ensure_ascii=false;sort_keys=true;separators=comma-colon"
            ),
            "suite_allowlist": [TEST_CLASS],
            "testcase_identity_source": (
                "fixed target-execution evidence plus Failsafe factory index"
            ),
            "discarded_elements": ["properties", "system-out", "system-err"],
            "discarded_attributes": [
                "testsuite@time",
                "testcase@time",
                "testsuite@xsi:noNamespaceSchemaLocation",
            ],
            "arbitrary_xml_text_copied": False,
            "failure_error_skip_or_flake_allowed": False,
            "unknown_xml_nodes_allowed": False,
            "duplicate_logical_or_xml_ids_allowed": False,
            "raw_report_hash_role": (
                "single_execution_binding_not_cross_run_stability"
            ),
        },
        "result": {
            "suite": TEST_CLASS,
            "totals": {
                "tests": 60,
                "passed": 60,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
                "flakes": 0,
            },
            "group_counts": dict(sorted(groups.items())),
            "disposition_counts": dict(sorted(dispositions.items())),
            "leaves": plan,
            "execution_order_case_ids_sha256": EXECUTION_ORDER_CASE_IDS_SHA256,
            "ordered_logical_leaf_ids_sha256": ORDERED_LOGICAL_LEAF_IDS_SHA256,
            "ordered_xml_names_sha256": ORDERED_XML_NAMES_SHA256,
            "raw_projection_sha256": sha256_json(projection),
            "leaf_payload_sha256": sha256_json(plan),
        },
        "confidentiality": {
            "properties_removed": True,
            "stdout_removed": True,
            "stderr_removed": True,
            "timings_removed": True,
            "absolute_paths_removed": True,
            "credentials_tokens_cookies_and_urls_removed": True,
            "sensitive_output_scan_passed": True,
            "repository_tamper_evident": False,
            "manifest_bytes_external_git_anchor_complete": False,
            "post_push_successor_anchor_required": True,
            "independently_signed_provenance": False,
            "claim_boundary": (
                "Inputs are fixed by pushed predecessor "
                "0531b3c9272f9743a374edcf5c8bbeb72643eb1b; this manifest's bytes "
                "still require a post-push successor anchor and are not an independently "
                "signed execution attestation"
            ),
        },
    }
    _assert_confidential(manifest)
    manifest["document_payload_sha256"] = document_payload_sha256(manifest)
    _assert_confidential(manifest)
    return manifest


def write_manifest(report: Path, output: Path) -> dict[str, Any]:
    if report.resolve() == output.resolve():
        raise NormalizationError("report and output paths must differ")
    manifest = normalize_report(report)
    payload = render_manifest(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize the fixed Phase 4C 60-leaf Failsafe report.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = write_manifest(args.report, args.output)
    print(
        canonical_json({
            "output": args.output.as_posix(),
            "raw_report_sha256": manifest["raw_report"]["sha256"],
            "document_payload_sha256": manifest["document_payload_sha256"],
            "leaf_payload_sha256": manifest["result"]["leaf_payload_sha256"],
        })
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
