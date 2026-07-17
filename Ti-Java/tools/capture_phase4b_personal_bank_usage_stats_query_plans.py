#!/usr/bin/env python3
"""Capture deterministic dual-PostgreSQL plans for usage-stats evidence SQL."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import io
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
import uuid

import capture_phase4b_personal_bank_share_list_query_plans as base


POSTGRES_IMAGES = base.POSTGRES_IMAGES
DEFAULT_DATABASE = "phase4b_personal_bank_usage_stats_plan"
DEFAULT_BANK_COUNT = 5_000
DEFAULT_SHARE_RECORD_COUNT = 150_000
DEFAULT_PUBLIC_USER_COUNT = 150_000
TARGET_BANK_ID = 7_101
TARGET_OWNER_ID = 7_001
GENERATED_USER_OFFSET = 100_000
GENERATED_BANK_OFFSET = 1_000_000
GENERATED_SHARE_OFFSET = 2_000_000
GENERATED_RECORD_OFFSET = 3_000_000
GENERATED_PUBLIC_OFFSET = 4_000_000
TARGET_RECORD_INTERVAL = 3
TARGET_PUBLIC_INTERVAL = 500

MANIFEST_ID = "ti.phase4b.personal-bank-usage-stats-preimplementation-sql"
SOURCE_CLASS = (
    "io.saksk.ti.personalbank.infrastructure.persistence."
    "PersonalBankUsageStatsEvidenceSql"
)
QUERY_IDS = (
    "personal-bank-usage-stats-bank-probe",
    "personal-bank-usage-stats-shared-users",
    "personal-bank-usage-stats-public-users",
)
EXPECTED_SQL = {
    QUERY_IDS[0]: (
        "select id, user_id, is_public, status from user_question_banks "
        "where id = :bank_id"
    ),
    QUERY_IDS[1]: (
        "select distinct bsr.user_id as user_id, bs.expires_at as expires_at "
        "from bank_share_records bsr join bank_shares bs on bsr.share_id = bs.id "
        "where bsr.bank_id = :bank_id and bsr.status = 1 and bs.is_active = true"
    ),
    QUERY_IDS[2]: (
        "select distinct user_id from public_bank_users where bank_id = :bank_id"
    ),
}
FIXTURE_INPUTS = (
    "server/src/test/resources/db/phase3/030-auth-schema.sql",
    "server/src/test/resources/db/phase4b/062-personal-bank-share-list-schema.sql",
    "server/src/test/resources/db/phase4b/063-personal-bank-share-list-seed.sql",
    "server/src/test/resources/db/phase4b/064-personal-bank-all-shares-seed.sql",
    "server/src/test/resources/db/phase4b/065-personal-bank-usage-stats-schema.sql",
    "server/src/test/resources/db/phase4b/066-personal-bank-usage-stats-seed.sql",
)
TIMING_KEYS = {
    "Planning Time", "Execution Time", "Actual Startup Time", "Actual Total Time",
    "I/O Read Time", "I/O Write Time", "Temp I/O Read Time", "Temp I/O Write Time",
}
BUFFER_KEYS = base.BUFFER_KEYS
MEMORY_KEYS = {
    "Peak Memory Usage", "Sort Space Used", "Average Peak Memory", "Hash Buckets",
    "Original Hash Buckets", "Hash Batches", "Original Hash Batches", "Disk Usage",
}
PLANNER_ESTIMATE_KEYS = {"Startup Cost", "Total Cost", "Plan Rows", "Plan Width"}
PLAN_EXPRESSION_KEYS = {
    "Filter", "Index Cond", "Hash Cond", "Join Filter", "Merge Cond",
    "Recheck Cond", "Group Key", "Sort Key",
}
SENSITIVE_KEY_FRAGMENTS = (
    "password", "secret", "authorization", "credential", "cookie", "private_key",
    "access_token", "refresh_token", "dsn",
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported PG16/PG18 usage-stats query plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            root / "docs/refactor/phase4b/"
            "personal-bank-usage-stats-query-plan-evidence.json"
        ),
    )
    parser.add_argument(
        "--sql-manifest",
        type=Path,
        default=(
            root / "server/target/"
            "phase4b-personal-bank-usage-stats-evidence-sql.json"
        ),
    )
    parser.add_argument("--bank-count", type=int, default=DEFAULT_BANK_COUNT)
    parser.add_argument(
        "--share-record-count", type=int, default=DEFAULT_SHARE_RECORD_COUNT
    )
    parser.add_argument(
        "--public-user-count", type=int, default=DEFAULT_PUBLIC_USER_COUNT
    )
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    floors = {
        "bank_count": DEFAULT_BANK_COUNT,
        "share_record_count": DEFAULT_SHARE_RECORD_COUNT,
        "public_user_count": DEFAULT_PUBLIC_USER_COUNT,
    }
    for field, minimum in floors.items():
        if int(getattr(args, field)) < minimum:
            raise ValueError(f"--{field.replace('_', '-')} must be at least {minimum}")
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")
    for image in POSTGRES_IMAGES:
        if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", image["image"]):
            raise ValueError("PostgreSQL image must be an immutable digest reference")


def validate_paths(root: Path, output: Path, manifest: Path) -> None:
    root = root.resolve()
    output = output.resolve()
    manifest = manifest.resolve()
    evidence_dir = (root / "docs/refactor/phase4b").resolve()
    target_dir = (root / "server/target").resolve()
    if output == evidence_dir or evidence_dir not in output.parents:
        raise ValueError("usage-stats plan output must stay under docs/refactor/phase4b")
    if manifest == target_dir or target_dir not in manifest.parents:
        raise ValueError("usage-stats SQL manifest must stay under server/target")
    for relative in FIXTURE_INPUTS:
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or path.is_symlink():
            raise ValueError(f"usage-stats fixture input is unsafe: {relative}")


def normalize_sql(sql: str) -> str:
    return base.normalize_sql(sql)


def validate_query_sql(query_id: str, sql: str) -> None:
    if query_id not in EXPECTED_SQL:
        raise RuntimeError(f"unexpected usage-stats query id: {query_id}")
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError(f"{query_id} SQL is empty")
    if ";" in stripped or "--" in stripped or "/*" in stripped:
        raise RuntimeError(f"{query_id} SQL contains a separator or comment")
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError(f"{query_id} must contain exactly one SELECT")
    forbidden = base.FORBIDDEN_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(f"{query_id} contains forbidden token {forbidden.group(0)}")
    if re.search(r"\b(?:pg_temp|pg_catalog|information_schema)\b", stripped, re.I):
        raise RuntimeError(f"{query_id} references a system schema")
    normalized = normalize_sql(stripped)
    if normalized != EXPECTED_SQL[query_id]:
        raise RuntimeError(f"{query_id} SQL shape drifted")
    expected_joins = 1 if query_id == QUERY_IDS[1] else 0
    if normalized.count(" join ") != expected_joins:
        raise RuntimeError(f"{query_id} JOIN count drifted")
    if base.NAMED_PARAMETER.findall(stripped) != ["bank_id"]:
        raise RuntimeError(f"{query_id} bind occurrence order drifted")


def export_sql_manifest(root: Path, output: Path) -> None:
    validate_paths(root, root / "docs/refactor/phase4b/placeholder.json", output)
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = base.run([
        str(verifier),
        "-q",
        "-DskipITs",
        "-Dtest=PersonalBankUsageStatsEvidenceSqlManifestTest",
        f"-Dti.personal-bank-usage-stats-evidence.sql-manifest-output={output.resolve()}",
        "test",
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java usage-stats SQL export failed: {detail}")


def load_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java usage-stats SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("usage-stats SQL manifest root must be an object")
    expected_top = {
        "manifest_id": MANIFEST_ID,
        "schema_version": 1,
        "source_class": SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "sequential_execution_required": True,
        "short_circuit_after_bank_probe": True,
        "shared_and_public_failure_boundaries": "independently_degrade_to_empty",
        "query_count": 3,
    }
    for key, value in expected_top.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"usage-stats SQL manifest {key} drifted")
    queries = manifest.get("queries")
    if not isinstance(queries, list) or len(queries) != 3:
        raise RuntimeError("usage-stats SQL manifest must contain exactly three queries")
    operations = ("bank-probe", "shared-users", "public-users")
    for ordinal, (query, query_id, operation) in enumerate(
        zip(queries, QUERY_IDS, operations), start=1
    ):
        if not isinstance(query, dict):
            raise RuntimeError("usage-stats SQL query must be an object")
        expected_query = {
            "ordinal": ordinal,
            "query_id": query_id,
            "operation": operation,
            "parameter_order": ["bank_id"],
            "parameters": {"bank_id": "integer"},
        }
        for key, value in expected_query.items():
            if query.get(key) != value:
                raise RuntimeError(f"{query_id} {key} drifted")
        sql = query.get("sql")
        if not isinstance(sql, str):
            raise RuntimeError(f"{query_id} SQL must be text")
        validate_query_sql(query_id, sql)
    return manifest


def prepared_explain_sql(query: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    query_id = str(query["query_id"])
    sql = str(query["sql"])
    validate_query_sql(query_id, sql)
    positional = base.NAMED_PARAMETER.sub("$1", sql)
    prepared_name = {
        QUERY_IDS[0]: "phase4b_usage_bank_probe",
        QUERY_IDS[1]: "phase4b_usage_shared_users",
        QUERY_IDS[2]: "phase4b_usage_public_users",
    }[query_id]
    statement = (
        "SET max_parallel_workers_per_gather = 0;\n"
        "SET jit = off;\n"
        "SET work_mem = '64MB';\n"
        f"PREPARE {prepared_name}(integer) AS\n{positional.strip()};\n"
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n"
        f"EXECUTE {prepared_name}({TARGET_BANK_ID});\n"
        f"DEALLOCATE {prepared_name};\n"
    )
    return statement, {
        "mode": "postgresql-prepare-execute",
        "prepared_name": prepared_name,
        "session_settings": {
            "max_parallel_workers_per_gather": "0",
            "jit": "off",
            "work_mem": "64MB",
        },
        "runtime_statement_count": 1,
        "bound_parameter_count": 1,
        "occurrence_names": ["bank_id"],
        "positional_sql_sha256": base.sha256_text(positional),
        "parameters": {
            "bank_id": {"postgres_type": "integer", "value": TARGET_BANK_ID}
        },
    }


def fixture_paths(root: Path) -> list[Path]:
    return [(root / relative).resolve() for relative in FIXTURE_INPUTS]


def scale_fixture_sql(
    bank_count: int,
    share_record_count: int,
    public_user_count: int,
) -> str:
    user_count = max(share_record_count, public_user_count)
    return f"""
INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
)
SELECT {GENERATED_USER_OFFSET} + value,
       'phase4b-usage-user-' || value,
       'public-test-only-hash', false, 1, true,
       'phase4b-usage-user-' || value || '@test.invalid'
FROM generate_series(1, {user_count}) AS value;

INSERT INTO user_question_banks (id, user_id, name, status)
SELECT {GENERATED_BANK_OFFSET} + value,
       {GENERATED_USER_OFFSET} + value,
       'phase4b-usage-bank-' || value,
       1
FROM generate_series(1, {bank_count}) AS value;

INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
)
SELECT {GENERATED_SHARE_OFFSET} + value,
       CASE WHEN value % {TARGET_RECORD_INTERVAL} = 0 THEN {TARGET_BANK_ID}
            ELSE {GENERATED_BANK_OFFSET} + ((value - 1) % {bank_count}) + 1 END,
       {TARGET_OWNER_ID},
       'USAGE-GCODE-' || value,
       'usage-generated-token-' || value,
       'read',
       CASE WHEN value % 31 = 0 THEN TIMESTAMP '2020-01-01 00:00:00'
            WHEN value % 37 = 0 THEN NULL
            ELSE TIMESTAMP '2099-01-01 00:00:00' END,
       NULL, 0,
       CASE WHEN value % 19 = 0 THEN false
            WHEN value % 23 = 0 THEN NULL
            ELSE true END,
       TIMESTAMP '2026-07-17 12:00:00' - (value % 3600) * INTERVAL '1 second'
FROM generate_series(1, {share_record_count}) AS value;

INSERT INTO bank_share_records (
    id, share_id, bank_id, user_id, status, last_access_at, access_count, created_at
)
SELECT {GENERATED_RECORD_OFFSET} + value,
       {GENERATED_SHARE_OFFSET} + value,
       CASE WHEN value % {TARGET_RECORD_INTERVAL} = 0 THEN {TARGET_BANK_ID}
            ELSE {GENERATED_BANK_OFFSET} + ((value - 1) % {bank_count}) + 1 END,
       {GENERATED_USER_OFFSET} + value,
       CASE WHEN value % 17 = 0 THEN 0
            WHEN value % 29 = 0 THEN NULL
            ELSE 1 END,
       TIMESTAMP '2026-07-17 12:00:00',
       value % 11,
       TIMESTAMP '2026-07-17 11:00:00'
FROM generate_series(1, {share_record_count}) AS value;

INSERT INTO public_bank_users (
    id, bank_id, user_id, last_access_at, access_count, created_at
)
SELECT {GENERATED_PUBLIC_OFFSET} + value,
       CASE WHEN value % {TARGET_PUBLIC_INTERVAL} = 0 THEN {TARGET_BANK_ID}
            ELSE {GENERATED_BANK_OFFSET} + ((value - 1) % {bank_count}) + 1 END,
       {GENERATED_USER_OFFSET} + value,
       TIMESTAMP '2026-07-17 12:00:00',
       value % 13,
       TIMESTAMP '2026-07-17 10:00:00'
FROM generate_series(1, {public_user_count}) AS value;

VACUUM (ANALYZE) user_question_banks;
VACUUM (ANALYZE) bank_shares;
VACUUM (ANALYZE) bank_share_records;
VACUUM (ANALYZE) public_bank_users;
"""


def expected_shared_values(count: int) -> list[int]:
    return [
        value for value in range(1, count + 1)
        if value % TARGET_RECORD_INTERVAL == 0
        and value % 17 != 0
        and value % 29 != 0
        and value % 19 != 0
        and value % 23 != 0
    ]


def expected_public_values(count: int) -> list[int]:
    return [
        value for value in range(1, count + 1)
        if value % TARGET_PUBLIC_INTERVAL == 0
    ]


def literal_sql(query: Mapping[str, Any]) -> str:
    validate_query_sql(str(query["query_id"]), str(query["sql"]))
    return base.NAMED_PARAMETER.sub(str(TARGET_BANK_ID), str(query["sql"]))


def copy_rows(container: str, database: str, query: Mapping[str, Any]) -> list[list[str]]:
    copy_sql = (
        "COPY (\n" + literal_sql(query).strip()
        + "\n) TO STDOUT WITH (FORMAT csv, NULL '<NULL>');\n"
    )
    raw = base.execute_psql(container, database, copy_sql)
    return list(csv.reader(io.StringIO(raw))) if raw else []


def bank_probe_result(rows: list[list[str]]) -> dict[str, Any]:
    expected = [["7101", "7001", "f", "1"]]
    if rows != expected:
        raise RuntimeError(f"usage-stats bank probe result drifted: {rows}")
    return {
        "row_count": 1,
        "column_count": 4,
        "exact_rows": rows,
        "rows_sha256": base.sha256_json(rows),
    }


def shared_users_result(rows: list[list[str]], count: int) -> dict[str, Any]:
    if any(len(row) != 2 for row in rows):
        raise RuntimeError("usage-stats shared-users projection drifted")
    expected_values = expected_shared_values(count)
    expected_count = len(expected_values) + 7
    if len(rows) != expected_count:
        raise RuntimeError(
            f"shared-users row count drifted: expected={expected_count} observed={len(rows)}"
        )
    canonical = sorted(rows, key=lambda row: (int(row[0]), row[1]))
    edge_rows = [row for row in canonical if int(row[0]) <= 7_008]
    expected_edges = sorted([
        ["7001", "<NULL>"],
        ["7003", "2099-01-01 00:00:00"],
        ["7003", "<NULL>"],
        ["7004", "2020-01-01 00:00:00"],
        ["7005", "<NULL>"],
        ["7006", "<NULL>"],
        ["7007", "<NULL>"],
    ], key=lambda row: (int(row[0]), row[1]))
    if edge_rows != expected_edges:
        raise RuntimeError(f"shared-users fixed edge rows drifted: {edge_rows}")
    generated = [row for row in canonical if int(row[0]) > 7_008]
    expected_ids = [GENERATED_USER_OFFSET + value for value in expected_values]
    if [int(row[0]) for row in generated] != expected_ids:
        raise RuntimeError("shared-users generated identities drifted")
    expected_expiry = Counter()
    for value in expected_values:
        if value % 31 == 0:
            expected_expiry["past"] += 1
        elif value % 37 == 0:
            expected_expiry["null"] += 1
        else:
            expected_expiry["future"] += 1
    expected_expiry.update({"past": 1, "null": 5, "future": 1})
    actual_expiry = Counter()
    for _, raw in rows:
        if raw == "<NULL>":
            actual_expiry["null"] += 1
        elif datetime.fromisoformat(raw) < datetime(2026, 7, 17):
            actual_expiry["past"] += 1
        else:
            actual_expiry["future"] += 1
    if actual_expiry != expected_expiry:
        raise RuntimeError(
            f"shared-users expiry distribution drifted: {actual_expiry}"
        )
    return {
        "row_count": len(rows),
        "column_count": 2,
        "distinct_user_count": len({int(row[0]) for row in rows}),
        "pair_distinct_duplicate_user_count": sum(
            1 for amount in Counter(row[0] for row in rows).values() if amount > 1
        ),
        "expiry_value_counts": dict(sorted(actual_expiry.items())),
        "fixed_edge_rows": edge_rows,
        "minimum_generated_user_id": expected_ids[0] if expected_ids else None,
        "maximum_generated_user_id": expected_ids[-1] if expected_ids else None,
        "unordered_rows_sha256": base.sha256_json(canonical),
    }


def public_users_result(rows: list[list[str]], count: int) -> dict[str, Any]:
    if any(len(row) != 1 for row in rows):
        raise RuntimeError("usage-stats public-users projection drifted")
    values = sorted(int(row[0]) for row in rows)
    expected_generated = [
        GENERATED_USER_OFFSET + value for value in expected_public_values(count)
    ]
    expected = [7_001, 7_003, 7_006, 7_007, *expected_generated]
    if values != expected:
        raise RuntimeError("usage-stats public-users result drifted")
    return {
        "row_count": len(values),
        "column_count": 1,
        "distinct_user_count": len(set(values)),
        "fixed_edge_user_ids": values[:4],
        "minimum_generated_user_id": expected_generated[0] if expected_generated else None,
        "maximum_generated_user_id": expected_generated[-1] if expected_generated else None,
        "canonical_user_ids_sha256": base.sha256_json(values),
    }


def collect_numeric_fields(value: Any, names: set[str]) -> dict[str, float]:
    totals: Counter[str] = Counter()

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                if key in names and isinstance(child, (int, float)):
                    totals[key] += float(child)
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return dict(sorted(totals.items()))


def normalize_explain(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_explain(child) for child in value]
    if not isinstance(value, dict):
        return value
    normalized: dict[str, Any] = {}
    for key, child in value.items():
        if key in TIMING_KEYS | BUFFER_KEYS | MEMORY_KEYS | PLANNER_ESTIMATE_KEYS:
            continue
        if key in {"Workers", "JIT"}:
            continue
        if key in PLAN_EXPRESSION_KEYS and isinstance(child, (str, list)):
            serialized = json.dumps(child, ensure_ascii=False, sort_keys=True)
            normalized[key] = {
                "redacted": "planner expression omitted",
                "character_count": len(serialized),
                "sha256": base.sha256_text(serialized),
            }
            continue
        candidate = normalize_explain(child)
        if isinstance(child, (dict, list)) and candidate in ({}, []):
            continue
        normalized[key] = candidate
    return normalized


def walk_plan(node: Mapping[str, Any], depth: int = 0) -> Iterable[tuple[int, Mapping[str, Any]]]:
    yield depth, node
    for child in node.get("Plans", []):
        if isinstance(child, Mapping):
            yield from walk_plan(child, depth + 1)


def plan_summary(
    normalized_explain: list[dict[str, Any]],
    buffer_fields: Mapping[str, float],
    timing_fields: Mapping[str, float],
) -> dict[str, Any]:
    root = normalized_explain[0].get("Plan")
    if not isinstance(root, Mapping):
        raise RuntimeError("usage-stats EXPLAIN root lacks Plan")
    walked = list(walk_plan(root))
    nodes: list[dict[str, Any]] = []
    for depth, node in walked:
        summary: dict[str, Any] = {"depth": depth}
        for key in (
            "Node Type", "Parent Relationship", "Strategy", "Join Type",
            "Relation Name", "Alias", "Index Name", "Scan Direction", "Sort Method",
            "Actual Rows", "Actual Loops", "Rows Removed by Filter",
            "Rows Removed by Index Recheck", "Group Key", "Sort Key", "Hash Cond",
            "Join Filter", "Index Cond", "Filter", "Recheck Cond",
        ):
            if key in node:
                summary[key] = node[key]
        nodes.append(summary)
    relations = Counter(
        str(node["Relation Name"]) for node in nodes if "Relation Name" in node
    )
    node_types = Counter(str(node["Node Type"]) for node in nodes)
    return {
        "root_node_type": root.get("Node Type"),
        "root_actual_rows": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max((node["depth"] for node in nodes), default=0),
        "maximum_actual_loops": max(
            (int(node.get("Actual Loops", 0)) for node in nodes), default=0
        ),
        "node_types_preorder": [node.get("Node Type") for node in nodes],
        "node_type_counts": dict(sorted(node_types.items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "index_names": sorted({
            str(node["Index Name"]) for node in nodes if "Index Name" in node
        }),
        "buffer_fields_observed_before_normalization": sorted(buffer_fields),
        "timing_fields_observed_before_normalization": sorted(timing_fields),
        "temp_read_blocks_observed": buffer_fields.get("Temp Read Blocks", 0.0),
        "temp_written_blocks_observed": buffer_fields.get("Temp Written Blocks", 0.0),
        "nodes": nodes,
    }


def assert_plan_contract(
    query_id: str,
    summary: Mapping[str, Any],
    expected_rows: int,
) -> list[str]:
    if summary["root_actual_rows"] != expected_rows:
        raise RuntimeError(f"{query_id} plan row count drifted")
    if summary["root_actual_loops"] != 1:
        raise RuntimeError(f"{query_id} plan root did not execute exactly once")
    if summary["temp_read_blocks_observed"] != 0 \
            or summary["temp_written_blocks_observed"] != 0:
        raise RuntimeError(f"{query_id} plan used temporary blocks")
    if "Planning Time" not in summary["timing_fields_observed_before_normalization"] \
            or "Execution Time" not in summary["timing_fields_observed_before_normalization"]:
        raise RuntimeError(f"{query_id} raw EXPLAIN omitted top-level timing fields")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise RuntimeError(f"{query_id} raw EXPLAIN omitted BUFFERS fields")
    expected_relations = {
        QUERY_IDS[0]: {"user_question_banks": 1},
        QUERY_IDS[1]: {"bank_share_records": 1, "bank_shares": 1},
        QUERY_IDS[2]: {"public_bank_users": 1},
    }[query_id]
    if summary["relation_scan_occurrences"] != expected_relations:
        raise RuntimeError(f"{query_id} relation scan budget drifted")
    if query_id == QUERY_IDS[0] and "user_question_banks_pkey" not in summary["index_names"]:
        raise RuntimeError("usage-stats bank probe lost its primary-key lookup")
    if query_id == QUERY_IDS[1]:
        record_nodes = [
            node for node in summary["nodes"]
            if node.get("Relation Name") == "bank_share_records"
        ]
        if len(record_nodes) != 1 or record_nodes[0].get("Node Type") != "Seq Scan":
            raise RuntimeError("shared-users no-bank_id-index scan is no longer observable")
        if "bank_share_records" in " ".join(summary["index_names"]):
            raise RuntimeError("shared-users unexpectedly used a bank_share_records index")
    return [
        "exact-result-row-count",
        "root-executed-once",
        "required-relations-scanned",
        "raw-timing-and-buffer-fields-observed",
        "zero-temp-blocks",
    ]


def psql_json(container: str, database: str, sql: str) -> Any:
    raw = base.execute_psql(container, database, sql)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("usage-stats PostgreSQL JSON query could not be parsed") from exc


def data_set_metadata(container: str, database: str) -> dict[str, Any]:
    return psql_json(container, database, """
SELECT json_build_object(
    'users', (SELECT COUNT(*) FROM users),
    'user_question_banks', (SELECT COUNT(*) FROM user_question_banks),
    'bank_shares', (SELECT COUNT(*) FROM bank_shares),
    'bank_share_records', (SELECT COUNT(*) FROM bank_share_records),
    'public_bank_users', (SELECT COUNT(*) FROM public_bank_users),
    'target_bank_share_records', (
        SELECT COUNT(*) FROM bank_share_records WHERE bank_id = 7101
    ),
    'target_public_bank_users', (
        SELECT COUNT(*) FROM public_bank_users WHERE bank_id = 7101
    )
);
""")


def schema_fingerprint(container: str, database: str) -> str:
    raw = base.execute_psql(container, database, """
SELECT table_name || '|' || column_name || '|' || data_type || '|' || is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
SELECT tablename || '|' || indexname || '|' || indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
""")
    return base.sha256_text(raw)


def data_fingerprint(container: str, database: str) -> str:
    raw = base.execute_psql(container, database, """
SELECT 'user_question_banks', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(user_id::bigint), 0), COALESCE(SUM(status::bigint), 0)
FROM user_question_banks
UNION ALL
SELECT 'bank_shares', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(owner_id::bigint), 0)
FROM bank_shares
UNION ALL
SELECT 'bank_share_records', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(user_id::bigint), 0)
FROM bank_share_records
UNION ALL
SELECT 'public_bank_users', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(user_id::bigint), 0)
FROM public_bank_users
ORDER BY 1;
""")
    return base.sha256_text(raw)


def capture_engine(
    image: Mapping[str, str],
    manifest: Mapping[str, Any],
    args: argparse.Namespace,
    root: Path,
) -> dict[str, Any]:
    container = f"ti-phase4b-usage-plan-{uuid.uuid4().hex[:12]}"
    password = "public-test-only-password"
    result = base.run([
        "docker", "run", "-d", "--rm", "--network", "none", "--name", container,
        "-e", f"POSTGRES_PASSWORD={password}",
        "-e", f"POSTGRES_DB={DEFAULT_DATABASE}",
        image["image"],
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-4000:]
        raise RuntimeError(f"cannot start {image['label']}: {detail}")
    try:
        base.wait_for_postgres(container, DEFAULT_DATABASE, args.startup_timeout_seconds)
        for path in fixture_paths(root):
            base.execute_psql(container, DEFAULT_DATABASE, path.read_text(encoding="utf-8"))
        scale_sql = scale_fixture_sql(
            args.bank_count, args.share_record_count, args.public_user_count
        )
        base.execute_psql(container, DEFAULT_DATABASE, scale_sql)
        server_version = base.execute_psql(
            container, DEFAULT_DATABASE, "SHOW server_version;"
        )
        if server_version != image["version"]:
            raise RuntimeError(f"{image['label']} server version drifted: {server_version}")
        network_mode = base.run([
            "docker", "inspect", "--format={{.HostConfig.NetworkMode}}", container
        ]).stdout.strip()
        if network_mode != "none":
            raise RuntimeError(f"usage-stats evidence network drifted: {network_mode}")
        image_id = base.run([
            "docker", "image", "inspect", image["image"], "--format", "{{.Id}}"
        ]).stdout.strip()
        before_schema = schema_fingerprint(container, DEFAULT_DATABASE)
        before_data = data_fingerprint(container, DEFAULT_DATABASE)
        data_set = data_set_metadata(container, DEFAULT_DATABASE)
        observations = []
        for query in manifest["queries"]:
            query_id = str(query["query_id"])
            rows = copy_rows(container, DEFAULT_DATABASE, query)
            query_result = {
                QUERY_IDS[0]: lambda: bank_probe_result(rows),
                QUERY_IDS[1]: lambda: shared_users_result(rows, args.share_record_count),
                QUERY_IDS[2]: lambda: public_users_result(rows, args.public_user_count),
            }[query_id]()
            explain_statement, binding = prepared_explain_sql(query)
            raw_explain = base.parse_explain(
                base.execute_psql(container, DEFAULT_DATABASE, explain_statement)
            )
            buffers = collect_numeric_fields(raw_explain, BUFFER_KEYS)
            timings = collect_numeric_fields(raw_explain, TIMING_KEYS)
            normalized_explain = normalize_explain(raw_explain)
            summary = plan_summary(normalized_explain, buffers, timings)
            assertions = assert_plan_contract(query_id, summary, query_result["row_count"])
            observations.append({
                "ordinal": query["ordinal"],
                "query_id": query_id,
                "operation": query["operation"],
                "sql": query["sql"],
                "sql_sha256": base.sha256_text(query["sql"]),
                "normalized_sql_sha256": base.sha256_text(normalize_sql(query["sql"])),
                "binding": binding,
                "result": query_result,
                "assertions_passed": assertions,
                "plan_summary": summary,
                "normalized_explain_analyze": normalized_explain[0],
            })
        after_schema = schema_fingerprint(container, DEFAULT_DATABASE)
        after_data = data_fingerprint(container, DEFAULT_DATABASE)
        if before_schema != after_schema or before_data != after_data:
            raise RuntimeError("usage-stats plan capture mutated schema or business rows")
        return {
            "label": image["label"],
            "image": image["image"],
            "image_id": image_id,
            "network": network_mode,
            "server_version": server_version,
            "server_version_num": base.execute_psql(
                container, DEFAULT_DATABASE, "SHOW server_version_num;"
            ),
            "data_set": data_set,
            "schema_fingerprint_before_after_sha256": before_schema,
            "data_fingerprint_before_after_sha256": before_data,
            "read_only_capture_fingerprints_unchanged": True,
            "observations": observations,
        }
    finally:
        base.run(["docker", "rm", "-f", "-v", container], check=False)


def tool_inputs(root: Path, manifest_path: Path) -> dict[str, Any]:
    paths = {
        "evidence_sql": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUsageStatsEvidenceSql.java"
        ),
        "sql_contract_test": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUsageStatsEvidenceSqlContractTest.java"
        ),
        "sql_manifest_exporter": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUsageStatsEvidenceSqlManifestTest.java"
        ),
        "jdbc_compatibility_test": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT.java"
        ),
        "base_capture_support": (
            "tools/capture_phase4b_personal_bank_share_list_query_plans.py"
        ),
        "capture_tool": "tools/capture_phase4b_personal_bank_usage_stats_query_plans.py",
        "capture_tool_test": (
            "tools/test_capture_phase4b_personal_bank_usage_stats_query_plans.py"
        ),
    }
    for index, relative in enumerate(FIXTURE_INPUTS, start=1):
        paths[f"fixture_{index}"] = relative
    inputs: dict[str, Any] = {
        "sql_manifest_path": str(manifest_path.resolve().relative_to(root.resolve())),
        "sql_manifest_sha256": base.sha256_file(manifest_path),
    }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inputs["sql_manifest_payload_sha256"] = base.sha256_json(manifest)
    for key, relative in paths.items():
        path = (root / relative).resolve()
        inputs[key] = relative
        inputs[f"{key}_sha256"] = base.sha256_file(path)
    return inputs


def assert_redacted(document: Mapping[str, Any]) -> None:
    serialized = json.dumps(document, ensure_ascii=False, sort_keys=True)
    forbidden_values = (
        "public-test-only-password", "/Users/", "@test.invalid",
        "ti-phase4b-usage-plan-",
    )
    if any(value in serialized for value in forbidden_values):
        raise RuntimeError("usage-stats evidence leaked ephemeral or sensitive fixture data")

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                lowered = str(key).lower()
                if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                    raise RuntimeError(f"usage-stats evidence contains sensitive key: {key}")
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)


def capture_document(args: argparse.Namespace) -> dict[str, Any]:
    validate_args(args)
    root = Path(__file__).resolve().parents[1]
    manifest_path = args.sql_manifest.resolve()
    validate_paths(root, args.output, manifest_path)
    export_sql_manifest(root, manifest_path)
    manifest = load_sql_manifest(manifest_path)
    engines = [
        capture_engine(image, manifest, args, root)
        for image in POSTGRES_IMAGES
    ]
    query_result_hashes: dict[str, set[str]] = {query_id: set() for query_id in QUERY_IDS}
    for engine in engines:
        for observation in engine["observations"]:
            result = observation["result"]
            digest = (
                result.get("rows_sha256")
                or result.get("unordered_rows_sha256")
                or result.get("canonical_user_ids_sha256")
            )
            query_result_hashes[observation["query_id"]].add(str(digest))
    if any(len(values) != 1 for values in query_result_hashes.values()):
        raise RuntimeError("PostgreSQL versions returned different usage-stats results")
    scale_sql = scale_fixture_sql(
        args.bank_count, args.share_record_count, args.public_user_count
    )
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-usage-stats-query-plan-evidence",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "scope": "test-only preimplementation usage-stats SQL and plan evidence",
        "route_migration_status": {
            "route_ids": ["d67a16965b08", "22aecd49a3c2"],
            "http_owner": "personalbank",
            "status": "pending",
            "production_cutover": False,
        },
        "provenance": {
            "legacy_commit": "700006dfdfa063deb4387be572911e782bcea0d9",
            "legacy_source": "app/modules/user_bank/routes/api_shares.py:56-149",
            "runtime_dependency_on_legacy_source": False,
            "manifest_exported_by_maven_test": True,
            "query_input_kind": "Java test-only preimplementation evidence manifest",
        },
        "inputs": tool_inputs(root, manifest_path),
        "sql_contract": {
            "manifest": manifest,
            "query_order": list(QUERY_IDS),
            "query_count": 3,
            "sequential_execution_required": True,
            "short_circuit_after_bank_probe": True,
            "shared_and_public_failure_boundaries": "independently_degrade_to_empty",
            "query_payload_sha256": base.sha256_json(manifest["queries"]),
            "production_source_added": False,
        },
        "data_set": {
            "kind": "public deterministic repository fixtures plus synthetic scale rows",
            "repository_fixture_load_order": list(FIXTURE_INPUTS),
            "parameters": {
                "generated_bank_count": args.bank_count,
                "generated_share_record_count": args.share_record_count,
                "generated_public_user_count": args.public_user_count,
                "target_bank_id": TARGET_BANK_ID,
                "target_record_interval": TARGET_RECORD_INTERVAL,
                "target_public_interval": TARGET_PUBLIC_INTERVAL,
            },
            "scale_fixture_sql_sha256": base.sha256_text(scale_sql),
            "production_or_test_schema_index_added": False,
            "legacy_index_observation": (
                "bank_share_records has no bank_id-leading index; public_bank_users has the "
                "existing UNIQUE(bank_id,user_id) index created by fixture 065"
            ),
        },
        "engines": engines,
        "cross_version_contract": {
            "required_versions": [image["version"] for image in POSTGRES_IMAGES],
            "observed_versions": [engine["server_version"] for engine in engines],
            "three_queries_observed_in_order_per_version": all(
                [item["query_id"] for item in engine["observations"]] == list(QUERY_IDS)
                for engine in engines
            ),
            "exact_query_results_equal_across_versions": all(
                len(values) == 1 for values in query_result_hashes.values()
            ),
            "bank_probe_uses_primary_key": all(
                "user_question_banks_pkey"
                in engine["observations"][0]["plan_summary"]["index_names"]
                for engine in engines
            ),
            "shared_users_exposes_missing_bank_id_index": all(
                any(
                    node.get("Relation Name") == "bank_share_records"
                    and node.get("Node Type") == "Seq Scan"
                    for node in engine["observations"][1]["plan_summary"]["nodes"]
                )
                for engine in engines
            ),
            "temp_blocks_zero": all(
                item["plan_summary"]["temp_read_blocks_observed"] == 0
                and item["plan_summary"]["temp_written_blocks_observed"] == 0
                for engine in engines for item in engine["observations"]
            ),
            "read_only_capture_fingerprints_unchanged": all(
                engine["read_only_capture_fingerprints_unchanged"] for engine in engines
            ),
            "passed": True,
        },
        "normalization": {
            "removed": [
                "planning and execution timing values",
                "per-node actual timing values",
                "cache-dependent buffer block counts except TEMP zero assertions",
                "planner estimates and costs",
                "runtime memory, hash and worker counters",
                "container ID and ephemeral container name",
            ],
            "retained": [
                "exact result counts and canonical result hashes",
                "plan root and node types",
                "actual rows and loops",
                "relation and index names",
                "redacted hashes of planner expressions",
                "names of raw timing and BUFFERS fields observed before normalization",
                "TEMP read and write block zero values",
            ],
            "reason": (
                "Adjacent plan gates remove volatile timing, cost and cache counters so a "
                "fresh dual-version capture is byte-identical instead of presenting random "
                "latency as a stable contract."
            ),
        },
        "claim_limits": {
            "observational_evidence_only": True,
            "production_sla_claimed": False,
            "index_change_authorized": False,
            "schema_change_authorized": False,
            "http_parity_claimed": False,
            "production_cutover_claimed": False,
            "note": (
                "The scale fixture exposes the current bank_share_records scan and does not "
                "authorize an index, schema, HTTP, or production change."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/"
                "capture_phase4b_personal_bank_usage_stats_query_plans.py"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": "ephemeral network-disabled containers removed on all exits",
        },
    }
    assert_redacted(document)
    document["document_payload_sha256"] = base.document_payload_sha256(document)
    return document


def write_json_atomic(path: Path, document: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(base.render_document(document), encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    args = parse_args()
    document = capture_document(args)
    write_json_atomic(args.output, document)
    print(
        "captured personal-bank usage-stats PG16/PG18 plans "
        f"manifest_sha256={document['inputs']['sql_manifest_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
