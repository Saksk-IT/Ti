#!/usr/bin/env python3
"""Build the Phase 4C user-counts typed-normalization successor contract."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-contract.json"
)
CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-typed-normalization-contract"
)
CONTRACT_STATUS = (
    "typed_normalization_executed_external_anchor_pending_routes_pending"
)
CONTRACT_SCOPE = "phase4c-personal-bank-user-counts-http-typed-normalization"
CAPTURED_AT = "2026-07-18T15:28:17+08:00"
NEXT_GATE = (
    "pg16_pg18_termination_identity_sql_nine_table_fingerprints_then_real_"
    "tomcat_complete_response_headers_then_same_service_redis_refusal_"
    "interruption_and_recovery_before_route_migration"
)

PREDECESSOR = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json"
)
PREDECESSOR_SHA256 = (
    "1aa86e7cd8fe4f6c6c808eee166ff0ed30f7e228e707941efde87323b9ae057a"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "b38abd80403536c7e6db2ec9b8a8920dc06e9f740ed9c065941e483a0b5a30e2"
)
PREDECESSOR_BYTE_COUNT = 32_763
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-"
    "post-push-anchor-contract"
)
PREDECESSOR_STATUS = (
    "target_execution_post_push_checkpoint_externally_anchored_"
    "typed_parity_pending_routes_pending"
)
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-"
    "post-push-external-anchor"
)
PREDECESSOR_CAPTURED_AT = "2026-07-18T14:04:12+08:00"

GIT_COMMIT = "c38defa703b358a280122a09019031c040c58ea7"
GIT_ROOT_TREE = "5ac75d896171039f34650c92829282d8a5e3c3f8"
GIT_PARENT = "1dae013e11c76ad858d6695f166a32631eb1525e"
GIT_TI_JAVA_TREE = "07086dc62157018ec1c989832e5e63bfefbae0f0"
GIT_AUTHORED_AT = "2026-07-18T15:06:30+08:00"
GIT_SUBJECT = "test(java): externally anchor user counts handoff"
GIT_RAW_DELTA_SHA256 = (
    "66bb02a32b94b858606b965b55c01cc1f09c7c6ded72ff7dcc639bb7c8284f72"
)
GIT_PATHS = (
    "Ti-Java/README.md",
    "Ti-Java/docs/refactor/05-progress.md",
    "Ti-Java/docs/refactor/phase4c/README.md",
    "Ti-Java/docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json",
    "Ti-Java/infra/phase2/README.md",
    "Ti-Java/infra/phase2/verify-static.sh",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java",
    "Ti-Java/tools/"
    "build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py",
    "Ti-Java/tools/"
    "build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py",
    "Ti-Java/tools/phase2_wormhole_successor_acceptance.py",
    "Ti-Java/tools/phase4c_http_target_execution_post_push_anchor_successor_acceptance.py",
    "Ti-Java/tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
    "Ti-Java/tools/test_phase2_wormhole_successor_acceptance.py",
    "Ti-Java/tools/"
    "test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py",
    "Ti-Java/tools/"
    "test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py",
)


def _git_source(
    relative: str,
    blob_oid: str,
    sha256: str,
    byte_count: int,
) -> dict[str, Any]:
    return {
        "ti_java_relative_path": relative,
        "repository_path": f"Ti-Java/{relative}",
        "git_blob_oid": blob_oid,
        "sha256": sha256,
        "byte_count": byte_count,
        "mode": "100644",
    }


ANCHORED_PREDECESSOR_SOURCES = {
    PREDECESSOR: _git_source(
        PREDECESSOR,
        "a010939ba208dd03387595ba191807eca5612ee8",
        PREDECESSOR_SHA256,
        PREDECESSOR_BYTE_COUNT,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java"
    ): _git_source(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
        "67ad65a5d482128549df3b5d012e5314cd5cb173",
        "0042ca6deb05498b2d363c81843d7ec39e3f2cb6af2d43376b24b1d24b03940a",
        54_058,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java"
    ): _git_source(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java",
        "c275b712c210a21560bb2a91238ca4500eb4b907",
        "4824d1aa3ecb5208277066731b16efe33eadf2748348071f04e43c6e5887b520",
        18_477,
    ),
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): _git_source(
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py",
        "70951075267e29b9cb354f7f03888b23adc504c9",
        "4f97c2fcdfd36ac943fce4a1e948d99bf52cb8418519602141d40614ce78af44",
        37_163,
    ),
    "tools/phase4c_http_target_execution_post_push_anchor_successor_acceptance.py":
        _git_source(
            "tools/phase4c_http_target_execution_post_push_anchor_"
            "successor_acceptance.py",
            "2a5ec91d4709d11709571805786a8c641dfeba04",
            "fe074402bcb58cfd3a681769050dd80174c584a082b462047d9684950b60e363",
            35_451,
        ),
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): _git_source(
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py",
        "368af3c122f52e35b66525f5e01362acbc956c20",
        "f51784ae1831b54e630150af2af12d3692397f3191d74314f3f0816b847cdfae",
        18_683,
    ),
}


def _local_source(sha256: str, byte_count: int) -> dict[str, Any]:
    return {"sha256": sha256, "byte_count": byte_count}


LOCAL_SOURCES = {
    "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json":
        _local_source(
            "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1",
            1_200_690,
        ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-golden-target-execution-evidence.json"
    ): _local_source(
        "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002",
        173_397,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-target-execution-junit-manifest.json"
    ): _local_source(
        "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b",
        33_246,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-typed-normalization-junit-manifest.json"
    ): _local_source(
        "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c",
        9_342,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-typed-normalization-approved-difference.md"
    ): _local_source(
        "3c6ecb59cae4e8a2f31e7dd0ed74bcca56e0cf61830339254523f3f824e652be",
        3_730,
    ),
    (
        "server/src/test/java/io/saksk/ti/integration/"
        "LegacyPersonalBankUserCountsTypedNormalizationIT.java"
    ): _local_source(
        "f9bd7dbd51e65abe8f01e80d0d564b9dfdba6856f95c4b06ad21b3705a2f025f",
        30_716,
    ),
    (
        "server/src/test/resources/db/phase4c/"
        "072-personal-bank-user-counts-typed-normalization-seed.sql"
    ): _local_source(
        "089b795d6e6a3efdb1af86641701bd1bf9d30e2c1a94c65a0a32865bdfca29c6",
        363,
    ),
    "tools/normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py":
        _local_source(
            "3ff33e3ef1ad3171ea2ca97f9b70fc49db1c3dd92d97a5d8c634497d78285acc",
            22_318,
        ),
    "tools/test_normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py":
        _local_source(
            "51b316b9370da51b3c4f93b601ffb600451494d2743c0f08fbe17335e8d8bdcd",
            10_366,
        ),
    "server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java":
        _local_source(
            "c3bcd6b78ed2606ddc1e7a685774b9d0c2969c93502b6983d5f8352e27c29f50",
            1_220,
        ),
    "server/src/test/java/io/saksk/ti/support/Phase2PostgresContainers.java":
        _local_source(
            "c5ecf36dc5e943f9baa34b61be65bf73cf4502b1e8bdccc0a012a8db55c29ffe",
            1_698,
        ),
    (
        "server/src/test/java/io/saksk/ti/support/"
        "Phase4cUserCountsFaultInjectingDataSource.java"
    ): _local_source(
        "83f381e0766ebeb0c71aa3b8f3f024d9af1a0099776b2d8923082947d6116dae",
        20_783,
    ),
    "server/src/test/resources/db/phase3/030-auth-schema.sql": _local_source(
        "9f9546be5f32bd1babcb9a4711c2cc9b3641e4c22ff051738ba9d735a150c87e",
        934,
    ),
    "server/src/test/resources/db/phase4b/062-personal-bank-share-list-schema.sql":
        _local_source(
            "d0e51e7cd16d0275611a82c984a52538beb14b10b19c50925646dd48a4d1c29d",
            1_654,
        ),
    "server/src/test/resources/db/phase4b/065-personal-bank-usage-stats-schema.sql":
        _local_source(
            "90d94b6c90c09586908e3108626ddbace04a83b56ed2018a55709ccdc7a2f684",
            1_291,
        ),
    "server/src/test/resources/db/phase4b/067-personal-bank-user-counts-schema.sql":
        _local_source(
            "32367c8795654e0ae2f5e2f1d6d4e42fb70e354f745a7f06894e28ac4a45f934",
            2_951,
        ),
    (
        "server/src/test/resources/db/phase4c/"
        "071-personal-bank-user-counts-golden-target-seed.sql"
    ): _local_source(
        "5fbdc1da8e15072995baffba15b3a430b1ddd93e4788237a44bc3a5965e7556e",
        9_672,
    ),
    "server/pom.xml": _local_source(
        "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b",
        9_582,
    ),
    "server/.mvn/wrapper/maven-wrapper.properties": _local_source(
        "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab",
        446,
    ),
    "infra/phase2/verify-in-maven-container.sh": _local_source(
        "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e",
        3_131,
    ),
    "server/Dockerfile": _local_source(
        "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499",
        1_850,
    ),
    "openapi/phase4c-personal-bank-user-counts.openapi.json": _local_source(
        "076957f391fd9aed65861d0633ad4b21d88b391df5217b10e2105b88b56605c9",
        87_401,
    ),
    "docs/refactor/phase4c/route-parity-delta.csv": _local_source(
        "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b",
        2_230,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-http-implementation-worm-evidence.json"
    ): _local_source(
        "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
        1_442,
    ),
}

HISTORICAL_EVIDENCE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-golden-target-execution-evidence.json"
)
HISTORICAL_MANIFEST = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-target-execution-junit-manifest.json"
)
TYPED_MANIFEST = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-typed-normalization-junit-manifest.json"
)
WORM = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
CURRENT_NODE_SOURCES = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-contract.json",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py",
)


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


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed typed-normalization path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"fixed typed-normalization path contains symlink: {relative}"
            )
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed typed-normalization path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(
            f"fixed typed-normalization path is not a regular file: {relative}"
        )
    return resolved


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        document = json.loads(
            fixed_regular_file(root, relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"cannot read fixed JSON: {relative}") from error
    if not isinstance(document, dict):
        raise AssertionError(f"fixed JSON is not an object: {relative}")
    return document


def validate_local_sources(root: Path) -> None:
    for relative, descriptor in LOCAL_SOURCES.items():
        payload = fixed_regular_file(root, relative).read_bytes()
        if (
            len(payload) != descriptor["byte_count"]
            or sha256_bytes(payload) != descriptor["sha256"]
        ):
            raise AssertionError(f"typed-normalization source drifted: {relative}")

    predecessor_raw = fixed_regular_file(root, PREDECESSOR).read_bytes()
    predecessor = _read_json(root, PREDECESSOR)
    if (
        len(predecessor_raw) != PREDECESSOR_BYTE_COUNT
        or sha256_bytes(predecessor_raw) != PREDECESSOR_SHA256
        or predecessor.get("contract_id") != PREDECESSOR_ID
        or predecessor.get("status") != PREDECESSOR_STATUS
        or predecessor.get("scope") != PREDECESSOR_SCOPE
        or predecessor.get("captured_at") != PREDECESSOR_CAPTURED_AT
        or predecessor.get("document_payload_sha256")
        != PREDECESSOR_PAYLOAD_SHA256
        or document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256
        or predecessor.get("post_push_source_anchor", {}).get(
            "current_anchor_source_bytes_external_git_anchor_complete"
        ) is not False
        or predecessor.get("authorization", {}).get("route_migration_eligible")
        is not False
    ):
        raise AssertionError("typed-normalization predecessor boundary drifted")

    manifest = _read_json(root, TYPED_MANIFEST)
    if (
        manifest.get("document_payload_sha256")
        != "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236"
        or document_payload_sha256(manifest)
        != manifest.get("document_payload_sha256")
        or manifest.get("result", {}).get("proof_payload_sha256")
        != "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047"
        or manifest.get("raw_report", {}).get("sha256")
        != "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b"
        or manifest.get("raw_report", {}).get("byte_count") != 51_169
        or manifest.get("result", {}).get("runtime_scope") != {
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
    ):
        raise AssertionError("typed-normalization JUnit manifest drifted")

    historical = _read_json(root, HISTORICAL_MANIFEST)
    if (
        historical.get("document_payload_sha256")
        != "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c"
        or len(historical.get("result", {}).get("leaves", [])) != 60
    ):
        raise AssertionError("historical JUnit manifest drifted")

    worm = _read_json(root, WORM)
    if (
        worm.get("java", {}).get("buildContextSha256")
        != "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
        or worm.get("java", {}).get("dockerfileSha256")
        != "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
        or worm.get("restore", {}).get("canonicalSchemaDumpSha256")
        != "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
        or worm.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("typed-normalization WORM boundary drifted")


def _compact_ledger(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    cases = evidence.get("cases", [])
    if not isinstance(cases, list) or len(cases) != 59:
        raise AssertionError("historical target case count drifted")
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_id = case.get("case_id")
        aware = case_id == "access-shared-aware-expiry-type-error"
        disposition = (
            "EXECUTED_FULL_CONTEXT_HTTP"
            if aware else case.get("execution_disposition")
        )
        http_execution = True if aware else case.get("http_execution")
        target_status = 200 if aware else case.get("target_status")
        business_jdbc = (
            True
            if aware
            else bool(case.get("sql_boundary", {}).get("business_jdbc_reached", False))
        )
        proof = (
            {
                "manifest": TYPED_MANIFEST,
                "suite_leaf_ordinal": 1,
                "xml_name": "executesAwareExpiryAsARealFullFilterChainHttpRead",
                "replaces_historical_leaf_ordinal": 60,
            }
            if aware
            else {
                "manifest": HISTORICAL_MANIFEST,
                "suite_leaf_ordinal": case.get("junit", {}).get(
                    "disposition_leaf_ordinal"
                ),
                "xml_name": (
                    case.get("junit", {}).get("dynamic_test_name")
                    or case.get("junit", {}).get("factory_or_method")
                ),
            }
        )
        rows.append({
            "canonical_case_ordinal": case.get("canonical_case_ordinal"),
            "execution_ordinal": case.get("execution_ordinal"),
            "case_id": case_id,
            "route_id": case.get("route_id"),
            "alias": case.get("alias"),
            "execution_disposition": disposition,
            "http_execution": http_execution,
            "target_status": target_status,
            "business_jdbc_reached": business_jdbc,
            "proof": proof,
        })
    rows.sort(key=lambda row: row["canonical_case_ordinal"])
    if [row["canonical_case_ordinal"] for row in rows] != list(range(1, 60)):
        raise AssertionError("canonical case ordinals drifted")
    case_ids = [row["case_id"] for row in rows]
    if len(set(case_ids)) != 59:
        raise AssertionError("duplicate logical case id")
    return rows


def _summarize_ledger(rows: list[dict[str, Any]]) -> dict[str, Any]:
    http_rows = [row for row in rows if row["http_execution"]]
    dispositions = Counter(row["execution_disposition"] for row in rows)
    statuses = Counter(str(row["target_status"]) for row in http_rows)
    aliases = Counter(row["alias"] for row in http_rows)
    business = sum(bool(row["business_jdbc_reached"]) for row in http_rows)
    summary = {
        "logical_disposition_count": len(rows),
        "http_execution_count": len(http_rows),
        "business_jdbc_reached_http_count": business,
        "pre_business_jdbc_termination_http_count": len(http_rows) - business,
        "non_fault_http_execution_count": dispositions[
            "EXECUTED_FULL_CONTEXT_HTTP"
        ],
        "postgres_abort_http_execution_count": dispositions[
            "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT"
        ],
        "typed_rejection_count": dispositions["EXECUTED_TYPED_REJECTION"],
        "api_alias_http_execution_count": aliases["api"],
        "web_alias_http_execution_count": aliases["web"],
        "http_status_counts": dict(sorted(statuses.items())),
        "execution_disposition_counts": dict(sorted(dispositions.items())),
        "bound_only_case_count": 0,
        "mocked_application_result_case_count": 0,
    }
    expected = {
        "logical_disposition_count": 59,
        "http_execution_count": 58,
        "business_jdbc_reached_http_count": 50,
        "pre_business_jdbc_termination_http_count": 8,
        "non_fault_http_execution_count": 47,
        "postgres_abort_http_execution_count": 11,
        "typed_rejection_count": 1,
        "api_alias_http_execution_count": 44,
        "web_alias_http_execution_count": 14,
        "http_status_counts": {
            "200": 35,
            "302": 5,
            "401": 3,
            "403": 10,
            "500": 5,
        },
        "execution_disposition_counts": {
            "EXECUTED_FULL_CONTEXT_HTTP": 47,
            "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT": 11,
            "EXECUTED_TYPED_REJECTION": 1,
        },
        "bound_only_case_count": 0,
        "mocked_application_result_case_count": 0,
    }
    if summary != expected:
        raise AssertionError(f"typed-normalization ledger summary drifted: {summary}")
    return summary


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    validate_local_sources(root)
    evidence = _read_json(root, HISTORICAL_EVIDENCE)
    ledger = _compact_ledger(evidence)
    summary = _summarize_ledger(ledger)
    aware = next(
        row for row in ledger
        if row["case_id"] == "access-shared-aware-expiry-type-error"
    )
    malformed = next(
        row for row in ledger
        if row["case_id"] == "access-shared-malformed-expiry-value-error"
    )
    old_malformed = next(
        case for case in evidence["cases"]
        if case["case_id"] == "access-shared-malformed-expiry-value-error"
    )
    source_descriptors = {
        relative: {"path": relative, **deepcopy(descriptor)}
        for relative, descriptor in sorted(LOCAL_SOURCES.items())
    }
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
        "predecessor": {
            "source": PREDECESSOR,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "contract_id": PREDECESSOR_ID,
            "status": PREDECESSOR_STATUS,
            "scope": PREDECESSOR_SCOPE,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "immutable": True,
        },
        "predecessor_external_git_anchor": {
            "object_format": "sha1",
            "commit_oid": GIT_COMMIT,
            "root_tree_oid": GIT_ROOT_TREE,
            "parent_oid": GIT_PARENT,
            "ti_java_tree_oid": GIT_TI_JAVA_TREE,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_AUTHORED_AT,
            "subject": GIT_SUBJECT,
            "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
            "exact_changed_paths": list(GIT_PATHS),
            "changed_path_count": 18,
            "added_path_count": 6,
            "modified_path_count": 12,
            "deleted_path_count": 0,
            "non_ti_java_path_count": 0,
            "inserted_line_count": 4_544,
            "deleted_line_count": 40,
            "anchored_source_count": 6,
            "anchored_source_total_bytes": 196_595,
            "anchored_sources": deepcopy(ANCHORED_PREDECESSOR_SOURCES),
            "predecessor_current_anchor_sources_external_git_anchor_complete": True,
            "mutable_ref_is_validation_authority": False,
            "ordinary_contract_load_requires_git": False,
            "explicit_git_replay_supported": True,
        },
        "source_contracts": source_descriptors,
        "junit_execution": {
            "historical_manifest": HISTORICAL_MANIFEST,
            "typed_normalization_manifest": TYPED_MANIFEST,
            "historical_physical_leaf_count": 60,
            "new_physical_leaf_count": 1,
            "aggregate_physical_leaf_count": 61,
            "selected_effective_proof_leaf_count": 60,
            "logical_disposition_leaf_count": 59,
            "supplementary_authentication_leaf_count": 1,
            "superseded_historical_representation_leaf_count": 1,
            "replacement_leaf_count": 1,
            "superseded_leaf_double_counted": False,
            "new_raw_report_sha256": (
                "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b"
            ),
            "new_raw_report_byte_count": 51_169,
            "new_manifest_document_payload_sha256": (
                "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236"
            ),
            "new_manifest_proof_payload_sha256": (
                "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047"
            ),
            "failed_error_skipped_or_flaky_leaf_count": 0,
        },
        "typed_normalization": {
            "difference_id": "P4C-LEARNING-013",
            "difference_document": (
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-typed-normalization-approved-difference.md"
            ),
            "behavior_difference_decision": (
                "documented_local_adr_pending_current_node_external_git_anchor"
            ),
            "case_id": aware["case_id"],
            "source_status": 500,
            "historical_disposition": "EXECUTED_TYPED_COLLAPSE",
            "effective_disposition": aware["execution_disposition"],
            "target_status": aware["target_status"],
            "business_jdbc_reached": aware["business_jdbc_reached"],
            "input_kind": "string_bind_explicit_cast",
            "input": "2026-07-17T13:00:00+08:00",
            "negative_offset_input": "2026-07-17T13:00:00-05:00",
            "postgresql_type": "timestamp without time zone",
            "canonical_local_datetime": "2026-07-17T13:00:00",
            "offset_provenance_erased": True,
            "cast_compatibility_versions": ["16.14", "18.4"],
            "cast_session_time_zones": ["UTC", "America/Los_Angeles"],
            "cross_version_equal": True,
            "session_timezone_independent": True,
            "full_filter_http_version": "18.4",
            "http_fixture_origin": (
                "java_string_bind_explicit_cast_insert_before_request_trace"
            ),
            "http_fixture_sql_literal_seeded": False,
            "fixture_share_id": 99_661,
            "fixture_share_record_id": 99_681,
            "target_data": {
                "total": 9,
                "favorites": 0,
                "mistakes": 0,
                "types": [
                    "判断题", "简答题", "填空题", "多选题",
                    "选择题", "选择题", "简答题",
                ],
                "shuffle_options_available": False,
            },
            "proof_scope": (
                "Java String CAST compatibility on PostgreSQL 16.14 and 18.4 "
                "across UTC and America/Los_Angeles; full production filter "
                "chain MockMvc HTTP on PostgreSQL 18.4 and Redis 7.4.7; not "
                "random-port Tomcat network evidence"
            ),
            "request_interval_assertions": {
                "authority_users_sql_count": 1,
                "bank_access_sql_count": 5,
                "share_access_sql_count": 5,
                "favorite_membership_sql_count": 1,
                "mistake_membership_sql_count": 1,
                "question_summary_sql_count": 2,
                "tag_membership_sql_count": 0,
                "write_dml_count": 0,
                "users_last_active_write_dml_count": 0,
                "schema_mutation_count": 0,
                "nine_table_fingerprint_unchanged": True,
                "hmac_route_rate_key_count": 3,
                "each_route_rate_key_value": 1,
            },
            "fixture_and_session_exchange_occur_before_request_trace": True,
            "whole_test_lifecycle_zero_dml_claimed": False,
        },
        "malformed_typed_rejection": {
            "case_id": malformed["case_id"],
            "execution_disposition": malformed["execution_disposition"],
            "http_execution": malformed["http_execution"],
            "target_status": malformed["target_status"],
            "sqlstate": old_malformed["typed_evidence"]["sqlstate"],
            "persisted_bank_share_row_count": old_malformed[
                "typed_evidence"
            ]["persisted_bank_share_row_count"],
            "no_row_http_forbidden_from_claiming_malformed_semantics": True,
        },
        "disposition_ledger": {
            "ordered_by": "canonical_case_ordinal",
            "ordered_case_ids_sha256": sha256_json(
                [row["case_id"] for row in ledger]
            ),
            "ledger_payload_sha256": sha256_json(ledger),
            "case_id_set_equal_to_historical_predecessor": True,
            "single_effective_override_case_id": (
                "access-shared-aware-expiry-type-error"
            ),
            "summary": summary,
            "rows": ledger,
        },
        "worm_evidence": {
            "source": WORM,
            "sha256": LOCAL_SOURCES[WORM]["sha256"],
            "fixed_chain_node_count": 5,
            "predecessor_sha256": (
                "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
            ),
            "java_build_context_sha256": (
                "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
            ),
            "dockerfile_sha256": LOCAL_SOURCES["server/Dockerfile"]["sha256"],
            "canonical_schema_dump_sha256": (
                "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
            ),
            "new_worm_report_created": False,
            "reused": True,
        },
        "production_surface": {
            "production_source_changed": False,
            "production_build_context_changed": False,
            "production_schema_or_index_changed": False,
            "operator_changed": False,
            "client_changed": False,
            "gateway_or_proxy_changed": False,
            "openapi_sha256": LOCAL_SOURCES[
                "openapi/phase4c-personal-bank-user-counts.openapi.json"
            ]["sha256"],
            "route_delta_sha256": LOCAL_SOURCES[
                "docs/refactor/phase4c/route-parity-delta.csv"
            ]["sha256"],
        },
        "authorization": {
            "typed_execution_normalization_complete": True,
            "behavior_difference_adr_documented": True,
            "current_node_sources_external_git_anchor_complete": False,
            "typed_parity_review_complete": False,
            "pg16_pg18_termination_fingerprints_complete": False,
            "real_tomcat_complete_response_header_matrix_complete": False,
            "same_service_redis_outage_and_recovery_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "two_legacy_get_routes_migrated": False,
            "derived_head_and_options_count_as_migrated": False,
            "production_cutover": False,
        },
        "acceptance": {
            **summary,
            "junit_physical_leaf_count": 61,
            "junit_selected_effective_leaf_count": 60,
            "implemented_pending_get_count": 2,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "route_migration_eligible": False,
            "typed_parity_review_complete": False,
            "full_target_parity_closed": False,
            "production_cutover": False,
            "next_gate": NEXT_GATE,
        },
        "current_node_trust_boundary": {
            "source_paths": sorted(CURRENT_NODE_SOURCES),
            "source_path_allowlist_exact": True,
            "source_count": 6,
            "sources_excluded_from_self_authority": True,
            "source_bytes_external_git_anchor_complete": False,
            "post_push_external_anchor_required": True,
            "dynamic_source_discovery_forbidden": True,
            "independently_signed_provenance": False,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repository_root), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssertionError(f"read-only Git command failed: {arguments[0]}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
        raise AssertionError(f"read-only Git command rejected: {detail}")
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    top = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise AssertionError("typed-normalization repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != "sha1":
        raise AssertionError("typed-normalization Git object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT) != "commit":
        raise AssertionError("typed-normalization predecessor anchor is not a commit")
    facts = _git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", GIT_COMMIT
    ).splitlines()
    if facts != [
        GIT_ROOT_TREE,
        GIT_PARENT,
        GIT_AUTHORED_AT,
        GIT_AUTHORED_AT,
        GIT_SUBJECT,
    ]:
        raise AssertionError("typed-normalization Git commit identity drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT}:Ti-Java") != GIT_TI_JAVA_TREE:
        raise AssertionError("typed-normalization Ti-Java subtree drifted")
    raw_delta = _run_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        GIT_COMMIT,
    )
    if sha256_bytes(raw_delta) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("typed-normalization exact Git delta drifted")
    paths = tuple(
        line.split("\t", 1)[1]
        for line in raw_delta.decode("utf-8").splitlines()
    )
    if paths != GIT_PATHS:
        raise AssertionError("typed-normalization changed-path allowlist drifted")
    statuses = [line.split("\t", 1)[0].rsplit(" ", 1)[-1] for line in
                raw_delta.decode("utf-8").splitlines()]
    if Counter(statuses) != Counter({"A": 6, "M": 12}):
        raise AssertionError("typed-normalization Git change types drifted")
    for descriptor in ANCHORED_PREDECESSOR_SOURCES.values():
        repository_path = descriptor["repository_path"]
        line = _git_text(root, "ls-tree", GIT_COMMIT, "--", repository_path)
        parts = line.split(None, 3)
        if len(parts) != 4 or parts[:3] != [
            descriptor["mode"], "blob", descriptor["git_blob_oid"]
        ]:
            raise AssertionError(f"anchored tree entry drifted: {repository_path}")
        payload = _run_git(root, "cat-file", "blob", descriptor["git_blob_oid"])
        if (
            len(payload) != descriptor["byte_count"]
            or sha256_bytes(payload) != descriptor["sha256"]
        ):
            raise AssertionError(f"anchored source bytes drifted: {repository_path}")


def write_contract(output: Path, root: Path = ROOT) -> dict[str, Any]:
    document = build_contract(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(serialized_contract(document))
    return document


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the fixed Phase 4C typed-normalization successor contract."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repository-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    document = build_contract(ROOT)
    payload = serialized_contract(document)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            raise AssertionError("typed-normalization checked contract drifted")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    if args.repository_root is not None:
        validate_git_checkpoint(args.repository_root)
    print(canonical_json({
        "output": args.output.as_posix(),
        "document_payload_sha256": document["document_payload_sha256"],
        "ledger_payload_sha256": document["disposition_ledger"]
        ["ledger_payload_sha256"],
        "http_execution_count": document["acceptance"]["http_execution_count"],
        "typed_rejection_count": document["acceptance"]["typed_rejection_count"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
