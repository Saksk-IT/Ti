#!/usr/bin/env python3
"""Capture deterministic PG16/PG18 plans for preimplementation all-shares SQL."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import io
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Optional
import uuid

import capture_phase4b_personal_bank_share_list_query_plans as base


POSTGRES_IMAGES = base.POSTGRES_IMAGES
DEFAULT_DATABASE = "phase4b_personal_bank_all_shares_plan"
DEFAULT_BANK_COUNT = 5_000
DEFAULT_SHARE_COUNT = 150_000
TARGET_VIEWER_ID = 4_201
OTHER_VIEWER_ID = 4_202
TARGET_NULL_INTERVAL = 5_000

MANIFEST_ID = "ti.phase4b.personal-bank-all-shares-preimplementation-sql"
SOURCE_CLASS = (
    "io.saksk.ti.personalbank.infrastructure.persistence."
    "PersonalBankAllSharesEvidenceSql"
)
QUERY_ID = "personal-bank-all-shares"
EXPECTED_SQL = (
    "select bs.id, bs.bank_id, bs.owner_id, bs.share_code, bs.share_token, "
    "bs.permission, bs.expires_at, bs.max_uses, bs.current_uses, bs.is_active, "
    "bs.created_at, b.name as bank_name from bank_shares bs "
    "join user_question_banks b on bs.bank_id = b.id "
    "where bs.owner_id = :viewer_id and b.status = 1 "
    "order by bs.created_at desc nulls first"
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported PG16/PG18 all-shares query plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            root / "docs/refactor/phase4b/"
            "personal-bank-all-shares-query-plan-evidence.json"
        ),
    )
    parser.add_argument(
        "--sql-manifest",
        type=Path,
        default=(
            root / "server/target/"
            "phase4b-personal-bank-all-shares-evidence-sql.json"
        ),
    )
    parser.add_argument("--bank-count", type=int, default=DEFAULT_BANK_COUNT)
    parser.add_argument("--share-count", type=int, default=DEFAULT_SHARE_COUNT)
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.bank_count < DEFAULT_BANK_COUNT:
        raise ValueError(f"--bank-count must be at least {DEFAULT_BANK_COUNT}")
    if args.share_count < DEFAULT_SHARE_COUNT:
        raise ValueError(f"--share-count must be at least {DEFAULT_SHARE_COUNT}")
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")
    for image in POSTGRES_IMAGES:
        if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", image["image"]):
            raise ValueError("PostgreSQL image must be an immutable digest reference")


def validate_query_sql(sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError("all-shares SQL is empty")
    if ";" in stripped or "--" in stripped or "/*" in stripped:
        raise RuntimeError("all-shares SQL contains a separator or comment")
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError("all-shares SQL must contain exactly one SELECT")
    forbidden = base.FORBIDDEN_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(f"all-shares SQL contains forbidden token {forbidden.group(0)}")
    normalized = base.normalize_sql(stripped)
    if normalized != EXPECTED_SQL:
        raise RuntimeError("all-shares SQL shape drifted")
    if normalized.count(" join ") != 1:
        raise RuntimeError("all-shares SQL must contain exactly one JOIN")
    if any(value in normalized for value in (
        "share_link", "share_base_url", "request.host", "bs.is_active =",
        "bs.expires_at <", "bs.expires_at >", "b.user_id =",
    )):
        raise RuntimeError("all-shares SQL crossed its database-fact boundary")


def export_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("all-shares SQL manifest must stay under server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = base.run([
        str(verifier),
        "-q",
        "-DskipITs",
        "-Dtest=PersonalBankAllSharesEvidenceSqlManifestTest",
        f"-Dti.personal-bank-all-shares-evidence.sql-manifest-output={output}",
        "test",
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java all-shares SQL export failed: {detail}")


def load_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java all-shares SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("all-shares SQL manifest root must be an object")
    expected_top = {
        "manifest_id": MANIFEST_ID,
        "schema_version": 1,
        "source_class": SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "sequential_execution_required": False,
        "join_authorized": True,
        "http_derived_fields_excluded": ["share_link"],
        "query_count": 1,
    }
    for key, value in expected_top.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"all-shares SQL manifest {key} drifted")
    queries = manifest.get("queries")
    if not isinstance(queries, list) or len(queries) != 1:
        raise RuntimeError("all-shares SQL manifest must contain one query")
    query = queries[0]
    expected_query = {
        "ordinal": 1,
        "query_id": QUERY_ID,
        "operation": "all-shares",
        "parameter_order": ["viewer_id"],
        "parameters": {"viewer_id": "bigint"},
    }
    if not isinstance(query, dict):
        raise RuntimeError("all-shares SQL query must be an object")
    for key, value in expected_query.items():
        if query.get(key) != value:
            raise RuntimeError(f"all-shares SQL query {key} drifted")
    sql = query.get("sql")
    if not isinstance(sql, str):
        raise RuntimeError("all-shares SQL must be text")
    validate_query_sql(sql)
    if base.NAMED_PARAMETER.findall(sql) != ["viewer_id"]:
        raise RuntimeError("all-shares SQL bind occurrence order drifted")
    return manifest


def prepared_explain_sql(query: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    sql = str(query["sql"])
    validate_query_sql(sql)
    positional = base.NAMED_PARAMETER.sub("$1", sql)
    statement = (
        "SET max_parallel_workers_per_gather = 0;\n"
        "SET jit = off;\n"
        "SET work_mem = '64MB';\n"
        "PREPARE phase4b_all_shares(bigint) AS\n"
        f"{positional.strip()};\n"
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON, TIMING FALSE, SUMMARY FALSE)\n"
        f"EXECUTE phase4b_all_shares({TARGET_VIEWER_ID});\n"
        "DEALLOCATE phase4b_all_shares;\n"
    )
    return statement, {
        "mode": "postgresql-prepare-execute",
        "prepared_name": "phase4b_all_shares",
        "session_settings": {
            "max_parallel_workers_per_gather": "0",
            "jit": "off",
            "work_mem": "64MB",
        },
        "runtime_statement_count": 1,
        "bound_parameter_count": 1,
        "occurrence_names": ["viewer_id"],
        "positional_sql_sha256": base.sha256_text(positional),
        "parameters": {
            "viewer_id": {
                "postgres_type": "bigint",
                "value": TARGET_VIEWER_ID,
            }
        },
    }


def fixture_sql(bank_count: int, share_count: int) -> str:
    return f"""
CREATE TABLE users (
    id integer PRIMARY KEY
);
CREATE TABLE user_question_banks (
    id integer PRIMARY KEY,
    user_id integer NOT NULL REFERENCES users(id),
    name text NOT NULL,
    status integer
);
CREATE TABLE bank_shares (
    id integer PRIMARY KEY,
    bank_id integer NOT NULL REFERENCES user_question_banks(id),
    owner_id integer NOT NULL REFERENCES users(id),
    share_code text UNIQUE,
    share_token text UNIQUE,
    permission text DEFAULT 'read',
    expires_at timestamp without time zone,
    max_uses integer,
    current_uses integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now()
);
INSERT INTO users (id) VALUES ({TARGET_VIEWER_ID}), ({OTHER_VIEWER_ID});
INSERT INTO user_question_banks (id, user_id, name, status) VALUES
    (4101, {TARGET_VIEWER_ID}, 'owner bank 高数・α／🧪', 1),
    (4102, {TARGET_VIEWER_ID}, 'inactive bank', 0),
    (4103, {TARGET_VIEWER_ID}, 'null status bank', NULL),
    (4104, {OTHER_VIEWER_ID}, '', 1);
INSERT INTO user_question_banks (id, user_id, name, status)
SELECT 10000 + value, {OTHER_VIEWER_ID}, 'generated-bank-' || value, 1
FROM generate_series(1, {bank_count}) AS value;
INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
) VALUES
    (-6, 4101, {TARGET_VIEWER_ID}, NULL, NULL, NULL, NULL,
     NULL, NULL, NULL, NULL),
    (-5, 4104, {TARGET_VIEWER_ID}, 'CROSSBANK', 'cross-bank-token', 'copy',
     TIMESTAMP '2020-01-01 00:00:00', 1, 99, false,
     TIMESTAMP '2026-07-17 13:00:00'),
    (-4, 4103, {TARGET_VIEWER_ID}, 'NULLBANK', 'null-bank-token', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 16:00:00'),
    (-3, 4101, {OTHER_VIEWER_ID}, 'OTHER', 'other-owner-token', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 17:00:00'),
    (-2, 4102, {TARGET_VIEWER_ID}, 'OFFBANK', 'off-bank-token', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 15:00:00'),
    (-1, 4101, {TARGET_VIEWER_ID}, 'INACTIVE', 'inactive-share-token',
     'unexpected-value', TIMESTAMP '2020-01-01 00:00:00', -1, -2, false,
     TIMESTAMP '2026-07-17 12:00:00'),
    (0, 4101, {TARGET_VIEWER_ID}, 'ACTIVE', 'active-share-token', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 14:00:00');
INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
)
SELECT value,
       10001 + (value % {bank_count}),
       CASE WHEN value % 777 = 0 THEN {OTHER_VIEWER_ID} ELSE {TARGET_VIEWER_ID} END,
       'GCODE-' || value,
       'gtoken-' || value,
       CASE WHEN value % 97 = 0 THEN 'unexpected-value' ELSE 'read' END,
       CASE WHEN value % 89 = 0 THEN TIMESTAMP '2020-01-01 00:00:00' ELSE NULL END,
       CASE WHEN value % 83 = 0 THEN -1 ELSE NULL END,
       CASE WHEN value % 79 = 0 THEN -2 ELSE value % 11 END,
       CASE WHEN value % 73 = 0 THEN NULL WHEN value % 71 = 0 THEN false ELSE true END,
       CASE WHEN value % {TARGET_NULL_INTERVAL} = 0 THEN NULL
            ELSE TIMESTAMP '2026-01-01 00:00:00' - (value % 30) * INTERVAL '1 second' END
FROM generate_series(1, {share_count}) AS value;
ANALYZE users;
ANALYZE user_question_banks;
ANALYZE bank_shares;
"""


def literal_sql(query: Mapping[str, Any]) -> str:
    validate_query_sql(str(query["sql"]))
    return base.NAMED_PARAMETER.sub(str(TARGET_VIEWER_ID), str(query["sql"]))


def expected_row_count(share_count: int) -> int:
    return share_count - share_count // 777 + 4


def expected_null_count(share_count: int) -> int:
    overlap = share_count // math.lcm(TARGET_NULL_INTERVAL, 777)
    return share_count // TARGET_NULL_INTERVAL - overlap + 1


def all_shares_result(
    container: str,
    database: str,
    query: Mapping[str, Any],
    share_count: int,
) -> dict[str, Any]:
    copy_sql = (
        "COPY (\n" + literal_sql(query).strip()
        + "\n) TO STDOUT WITH (FORMAT csv, NULL '<NULL>');\n"
    )
    raw = base.execute_psql(container, database, copy_sql)
    rows = list(csv.reader(io.StringIO(raw))) if raw else []
    if len(rows) != expected_row_count(share_count):
        raise RuntimeError("all-shares row count drifted")
    if any(len(row) != 12 for row in rows):
        raise RuntimeError("all-shares COPY projection lost an explicit database field")
    ids = [int(row[0]) for row in rows]
    if not {-6, -5, -1, 0}.issubset(ids) or {-4, -3, -2}.intersection(ids):
        raise RuntimeError("all-shares owner or active-bank filtering drifted")
    created = [row[10] for row in rows]
    null_count = sum(value == "<NULL>" for value in created)
    if null_count != expected_null_count(share_count):
        raise RuntimeError("all-shares NULL created_at fixture count drifted")
    if created[:null_count] != ["<NULL>"] * null_count:
        raise RuntimeError("PostgreSQL all-shares DESC NULLS FIRST behavior drifted")
    if any(value == "<NULL>" for value in created[null_count:]):
        raise RuntimeError("all-shares NULL created_at escaped the leading group")
    non_null = [datetime.fromisoformat(value) for value in created[null_count:]]
    if any(left < right for left, right in zip(non_null, non_null[1:])):
        raise RuntimeError("all-shares non-NULL timestamps are not descending")
    tie_groups = Counter(created[null_count:])
    if max(tie_groups.values(), default=0) < 2:
        raise RuntimeError("all-shares fixture lost equal-created_at ambiguity")
    active_values = {row[9] for row in rows}
    if not {"t", "f", "<NULL>"}.issubset(active_values):
        raise RuntimeError("all-shares fixture lost nullable PostgreSQL booleans")
    if "" not in {row[11] for row in rows}:
        raise RuntimeError("all-shares fixture lost cross-bank-owner empty bank name")
    if not any(row[5] == "unexpected-value" for row in rows):
        raise RuntimeError("all-shares fixture lost unconstrained permission rows")
    return {
        "row_count": len(rows),
        "column_count": 12,
        "rows_sha256": base.sha256_json(rows),
        "unordered_rows_sha256": base.sha256_json(sorted(rows)),
        "leading_null_created_at_count": null_count,
        "all_null_created_at_rows_are_leading": True,
        "non_null_created_at_descending": True,
        "equal_created_at_group_count": sum(
            1 for count in tie_groups.values() if count > 1
        ),
        "maximum_equal_created_at_group_size": max(tie_groups.values(), default=0),
        "equal_created_at_order_contract": "unordered_within_group",
        "postgres_boolean_values": sorted(active_values),
        "owner_filter_verified": True,
        "active_bank_filter_verified": True,
        "cross_bank_owner_row_present": True,
        "inactive_expired_overused_share_present": True,
        "unconstrained_permission_row_present": True,
        "http_derived_share_link_absent": True,
        "first_ten_ids": ids[:10],
        "last_ten_ids": ids[-10:],
    }


def assert_plan_contract(summary: Mapping[str, Any], expected_rows: int) -> None:
    if summary["root_actual_rows"] != expected_rows:
        raise RuntimeError("all-shares plan row count drifted")
    if summary["root_node_type"] != "Sort":
        raise RuntimeError("all-shares plan lost the explicit Sort root")
    if summary["maximum_actual_loops"] != 1:
        raise RuntimeError("all-shares plan executed a node more than once")
    if summary["temp_read_blocks"] != 0 or summary["temp_written_blocks"] != 0:
        raise RuntimeError("all-shares plan used temporary blocks")
    if summary["relation_scan_occurrences"] != {
        "bank_shares": 1,
        "user_question_banks": 1,
    }:
        raise RuntimeError("all-shares relation plan drifted")
    node_types = summary["node_types_preorder"]
    if not any(str(node).endswith("Join") for node in node_types):
        raise RuntimeError("all-shares plan lost its join")
    if node_types.count("Seq Scan") != 2:
        raise RuntimeError("all-shares no-index plan lost its two sequential scans")
    if summary["index_names"]:
        raise RuntimeError("all-shares unexpectedly acquired an index-backed plan")


def capture_engine(
    image: Mapping[str, str],
    manifest: Mapping[str, Any],
    fixture: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    container = f"ti-phase4b-all-shares-plan-{uuid.uuid4().hex[:12]}"
    password = "public-test-only-password"
    result = base.run([
        "docker", "run", "-d", "--rm", "--name", container,
        "-e", f"POSTGRES_PASSWORD={password}",
        "-e", f"POSTGRES_DB={DEFAULT_DATABASE}",
        image["image"],
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-4000:]
        raise RuntimeError(f"cannot start {image['label']}: {detail}")
    try:
        base.wait_for_postgres(container, DEFAULT_DATABASE, args.startup_timeout_seconds)
        base.execute_psql(container, DEFAULT_DATABASE, fixture)
        server_version = base.execute_psql(
            container, DEFAULT_DATABASE, "SHOW server_version;"
        )
        if server_version != image["version"]:
            raise RuntimeError(f"{image['label']} server version drifted: {server_version}")
        server_version_num = base.execute_psql(
            container, DEFAULT_DATABASE, "SHOW server_version_num;"
        )
        image_id = base.run([
            "docker", "image", "inspect", image["image"], "--format", "{{.Id}}",
        ]).stdout.strip()
        query = manifest["queries"][0]
        statement, binding = prepared_explain_sql(query)
        explain = base.parse_explain(
            base.execute_psql(container, DEFAULT_DATABASE, statement)
        )
        summary = base.plan_summary(explain)
        query_result = all_shares_result(
            container, DEFAULT_DATABASE, query, args.share_count
        )
        assert_plan_contract(summary, query_result["row_count"])
        normalized = base.normalize_sql(query["sql"])
        observation = {
            "ordinal": query["ordinal"],
            "query_id": query["query_id"],
            "operation": query["operation"],
            "sql": query["sql"],
            "sql_sha256": base.sha256_text(query["sql"]),
            "normalized_sql_sha256": base.sha256_text(normalized),
            "binding": binding,
            "result": query_result,
            "plan_summary": summary,
            "sanitized_explain": base.sanitized_plan(explain),
        }
        return {
            "label": image["label"],
            "image": image["image"],
            "image_id": image_id,
            "server_version": server_version,
            "server_version_num": server_version_num,
            "observations": [observation],
        }
    finally:
        base.run(["docker", "rm", "-f", "-v", container], check=False)


def tool_inputs(root: Path) -> dict[str, str]:
    paths = {
        "evidence_sql": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankAllSharesEvidenceSql.java"
        ),
        "sql_contract_test": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankAllSharesEvidenceSqlContractTest.java"
        ),
        "sql_manifest_exporter": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankAllSharesEvidenceSqlManifestTest.java"
        ),
        "jdbc_compatibility_test": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4bPersonalBankAllSharesEvidenceJdbcCompatibilityIT.java"
        ),
        "schema": "server/src/test/resources/db/phase4b/062-personal-bank-share-list-schema.sql",
        "predecessor_seed": (
            "server/src/test/resources/db/phase4b/063-personal-bank-share-list-seed.sql"
        ),
        "all_shares_seed": (
            "server/src/test/resources/db/phase4b/064-personal-bank-all-shares-seed.sql"
        ),
        "base_capture_support": (
            "tools/capture_phase4b_personal_bank_share_list_query_plans.py"
        ),
        "capture_tool": "tools/capture_phase4b_personal_bank_all_shares_query_plans.py",
        "capture_tool_test": (
            "tools/test_capture_phase4b_personal_bank_all_shares_query_plans.py"
        ),
    }
    return {
        key + "_sha256": base.sha256_file(root / value)
        for key, value in paths.items()
    }


def capture_document(args: argparse.Namespace) -> dict[str, Any]:
    validate_args(args)
    root = Path(__file__).resolve().parents[1]
    manifest_path = args.sql_manifest.resolve()
    export_sql_manifest(root, manifest_path)
    manifest = load_sql_manifest(manifest_path)
    fixture = fixture_sql(args.bank_count, args.share_count)
    engines = [
        capture_engine(image, manifest, fixture, args)
        for image in POSTGRES_IMAGES
    ]
    observations = [engine["observations"][0] for engine in engines]
    unordered_result_hashes = {
        item["result"]["unordered_rows_sha256"] for item in observations
    }
    if len(unordered_result_hashes) != 1:
        raise RuntimeError("PostgreSQL versions returned different all-shares row multisets")
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-all-shares-query-plan-evidence",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "scope": "test-only preimplementation JDBC SQL and query-plan evidence",
        "inputs": {
            "sql_manifest_path": (
                "server/target/phase4b-personal-bank-all-shares-evidence-sql.json"
            ),
            "sql_manifest_sha256": base.sha256_file(manifest_path),
            "sql_manifest_payload_sha256": base.sha256_json(manifest),
            **tool_inputs(root),
        },
        "sql_contract": {
            "manifest": manifest,
            "query_order": [QUERY_ID],
            "query_count": 1,
            "join_authorized": True,
            "http_derived_fields_excluded": ["share_link"],
            "production_source_added": False,
        },
        "fixture": {
            "bank_count_argument": args.bank_count,
            "generated_bank_count": args.bank_count + 4,
            "share_count_argument": args.share_count,
            "generated_share_count": args.share_count + 7,
            "target_viewer_id": TARGET_VIEWER_ID,
            "expected_result_count": expected_row_count(args.share_count),
            "target_null_interval": TARGET_NULL_INTERVAL,
            "schema_has_owner_id_or_created_at_index": False,
            "fixture_sql_sha256": base.sha256_text(fixture),
        },
        "plan_capture_environment": {
            "session_settings": observations[0]["binding"]["session_settings"],
            "same_settings_for_all_engines": all(
                item["binding"]["session_settings"]
                == observations[0]["binding"]["session_settings"]
                for item in observations
            ),
        },
        "engines": engines,
        "cross_version_contract": {
            "required_versions": [image["version"] for image in POSTGRES_IMAGES],
            "observed_versions": [engine["server_version"] for engine in engines],
            "single_query_observed_per_version": all(
                [item["query_id"] for item in engine["observations"]] == [QUERY_ID]
                for engine in engines
            ),
            "ordered_result_payloads_identical": len({
                item["result"]["rows_sha256"] for item in observations
            }) == 1,
            "ordered_result_payload_equality_required": False,
            "unordered_result_multisets_identical": True,
            "seq_scan_join_and_sort_without_index": all(
                item["plan_summary"]["root_node_type"] == "Sort"
                and item["plan_summary"]["node_types_preorder"].count("Seq Scan") == 2
                and not item["plan_summary"]["index_names"]
                for item in observations
            ),
            "desc_nulls_first_verified": all(
                item["result"]["all_null_created_at_rows_are_leading"]
                for item in observations
            ),
            "equal_timestamp_order_strengthened": False,
            "http_derived_share_link_in_sql": False,
            "temporary_blocks_zero": all(
                item["plan_summary"]["temp_read_blocks"] == 0
                and item["plan_summary"]["temp_written_blocks"] == 0
                for item in observations
            ),
            "passed": True,
        },
        "claim_limits": {
            "observational_evidence_only": True,
            "production_sla_claimed": False,
            "index_change_authorized": False,
            "schema_change_authorized": False,
            "http_parity_claimed": False,
            "production_cutover_claimed": False,
            "note": (
                "The no-index join plan freezes the legacy risk and does not authorize an "
                "index, schema, HTTP, or production change."
            ),
        },
    }
    document["document_payload_sha256"] = base.document_payload_sha256(document)
    return document


def main() -> int:
    args = parse_args()
    document = capture_document(args)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base.render_document(document), encoding="utf-8")
    print(
        "captured personal-bank all-shares PG16/PG18 plans "
        f"manifest_sha256={document['inputs']['sql_manifest_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
