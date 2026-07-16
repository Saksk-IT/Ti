#!/usr/bin/env python3
"""Capture deterministic PostgreSQL 18 plans for Phase 4A public-bank reads.

The capture uses the immutable PostgreSQL image below, a network-disabled
ephemeral container, the test-only 042 schema, and a scaled synthetic snapshot.
Runtime timing and cache-dependent buffer counts are deliberately removed from
the checked-in artifact; plan shape, actual rows/loops, predicates and index
choices remain as machine evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Iterable, Optional


DEFAULT_IMAGE = (
    "postgres:18.4-alpine@"
    "sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
DEFAULT_DATABASE = "phase4a_public_bank_plan"
DEFAULT_METRIC_COUNT = 50_000
DEFAULT_VIEWER_COUNT = 100_000
DEFAULT_BOARD_COUNT = 64
DEFAULT_PAGE_SIZE = 25
DEFAULT_PAGE_OFFSET = 100
FIXED_NOW_BJ = "2026-07-16 12:00:00"
FIXED_NOW_INSTANT = "2026-07-16 12:00:00+08:00"
DETAIL_IDENTITY_ID = 700_001
DETAIL_SOURCE_ID = 15_839
KEYWORD = "needle"
FIXTURE_KEYWORD_PREDICATE = """
(LOWER(m.name) LIKE '%needle%'
 OR LOWER(COALESCE(m.description, '')) LIKE '%needle%'
 OR LOWER(COALESCE(m.owner_label, '')) LIKE '%needle%')
""".strip()


BUFFER_KEYS = {
    "Shared Hit Blocks",
    "Shared Read Blocks",
    "Shared Dirtied Blocks",
    "Shared Written Blocks",
    "Local Hit Blocks",
    "Local Read Blocks",
    "Local Dirtied Blocks",
    "Local Written Blocks",
    "Temp Read Blocks",
    "Temp Written Blocks",
    "Exact Heap Blocks",
    "Lossy Heap Blocks",
    "Heap Fetches",
}

TIMING_KEYS = {
    "Planning Time",
    "Execution Time",
    "Actual Startup Time",
    "Actual Total Time",
    "I/O Read Time",
    "I/O Write Time",
    "Temp I/O Read Time",
    "Temp I/O Write Time",
}

MEMORY_KEYS = {
    "Peak Memory Usage",
    "Sort Space Used",
    "Average Peak Memory",
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture deterministic PG18 public-bank read query plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/refactor/phase4a/public-bank-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-public-bank-runtime-sql.json",
        help="Generated target artifact; refreshed from the Java adapter before every capture.",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--metric-count", type=int, default=DEFAULT_METRIC_COUNT)
    parser.add_argument("--viewer-count", type=int, default=DEFAULT_VIEWER_COUNT)
    parser.add_argument("--board-count", type=int, default=DEFAULT_BOARD_COUNT)
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.metric_count < DEFAULT_METRIC_COUNT:
        raise ValueError(f"--metric-count must be at least {DEFAULT_METRIC_COUNT}")
    if args.viewer_count < DEFAULT_VIEWER_COUNT:
        raise ValueError(f"--viewer-count must be at least {DEFAULT_VIEWER_COUNT}")
    if args.board_count < 32:
        raise ValueError("--board-count must be at least 32")
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")
    if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", args.image):
        raise ValueError("--image must be an immutable @sha256 PostgreSQL image reference")
    if args.metric_count <= DETAIL_SOURCE_ID:
        raise ValueError("--metric-count does not contain the fixed detail source")


def run(
    command: Iterable[str],
    *,
    input_text: Optional[str] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def export_runtime_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("--runtime-sql-manifest must stay under Ti-Java/server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = run(
        [
            str(verifier),
            "-Dtest=PublicBankRuntimeSqlManifestTest",
            f"-Dti.public-bank.sql-manifest-output={output}",
            "test",
        ],
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java runtime SQL export failed: {detail}")


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read Java runtime SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Java runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != "ti.phase4a.public-bank-runtime-sql":
        raise RuntimeError("Java runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("Java runtime SQL manifest schema version drifted")
    queries = manifest.get("queries")
    if not isinstance(queries, list) or manifest.get("query_count") != len(queries):
        raise RuntimeError("Java runtime SQL manifest query count is invalid")
    expected_ids = {
        "search-count-keyword",
        "search-page-latest",
        "search-page-latest-keyword",
        "boards-directory",
        "hot-top-five",
        "summary-rolling-seven-days",
        "detail-with-both-relation",
    }
    actual_ids = {
        query.get("query_id") for query in queries if isinstance(query, dict)
    }
    if actual_ids != expected_ids or len(queries) != len(expected_ids):
        raise RuntimeError(f"Java runtime SQL manifest query IDs drifted: {actual_ids}")
    for query in queries:
        if not isinstance(query.get("sql"), str) or not query["sql"].strip():
            raise RuntimeError(f"Runtime SQL is missing for {query.get('query_id')}")
        if not isinstance(query.get("parameters"), dict):
            raise RuntimeError(f"Runtime SQL parameters are invalid for {query['query_id']}")
    return manifest


def psql(container: str, sql: str) -> str:
    result = run(
        [
            "docker",
            "exec",
            "--interactive",
            container,
            "psql",
            "--username=postgres",
            f"--dbname={DEFAULT_DATABASE}",
            "--no-psqlrc",
            "--quiet",
            "--tuples-only",
            "--no-align",
            "--set=ON_ERROR_STOP=1",
        ],
        input_text=sql.rstrip() + "\n",
        check=False,
    )
    if result.returncode != 0:
        statement_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        raise RuntimeError(
            "PostgreSQL command failed "
            f"(exit={result.returncode}, sql_sha256={statement_hash}): "
            f"{result.stderr.strip()[-3000:]}"
        )
    return result.stdout.strip()


def psql_json(container: str, sql: str) -> Any:
    raw = psql(container, sql)
    if not raw:
        raise RuntimeError("PostgreSQL returned an empty JSON result")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"PostgreSQL returned invalid JSON: {raw[:1000]}") from exc


def wait_until_ready(container: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        ready = run(
            [
                "docker",
                "exec",
                container,
                "psql",
                "--username=postgres",
                f"--dbname={DEFAULT_DATABASE}",
                "--no-psqlrc",
                "--quiet",
                "--tuples-only",
                "--command=SELECT 1",
            ],
            check=False,
        )
        if ready.returncode == 0:
            return
        time.sleep(1)
    logs = run(["docker", "logs", container], check=False)
    raise RuntimeError(
        f"PostgreSQL did not become ready in {timeout_seconds}s: "
        f"{(logs.stdout + logs.stderr)[-3000:]}"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def setup_sql(args: argparse.Namespace, schema_sql: str) -> str:
    return f"""
CREATE TABLE plaza_boards (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
);

{schema_sql}

INSERT INTO plaza_boards (
    id, slug, name, description, icon, sort_order,
    is_active, created_at, updated_at
)
SELECT board_id,
       'board-' || lpad(board_id::text, 3, '0'),
       'Scaled board ' || lpad(board_id::text, 3, '0'),
       CASE WHEN board_id % 5 = 0 THEN NULL
            ELSE 'Deterministic Phase 4A board ' || board_id::text END,
       NULL,
       (board_id * 17) % {args.board_count},
       board_id % 8 <> 0,
       TIMESTAMP '2026-07-01 08:00:00',
       TIMESTAMP '2026-07-16 12:00:00'
FROM generate_series(1, {args.board_count}) AS generated(board_id);

INSERT INTO public_bank_plaza_metrics (
    source_type, source_id, name, description, cover_image,
    owner_id, owner_label, owner_avatar, question_count_total,
    plaza_board_id, is_featured, featured_weight, published_at,
    last_activity_at, join_count_total, join_users_7d, join_users_30d,
    answer_count_7d, answer_count_30d, answer_users_7d,
    answer_users_30d, hot_score, active_score, recommended_score,
    join_mode, join_note, allow_copy, share_count,
    snapshot_generation, updated_at
)
SELECT CASE WHEN metric_id % 5 IN (0, 1) THEN 'system'
            ELSE 'user_public' END,
       metric_id,
       CASE
           WHEN metric_id % 1000 = 0 THEN 'needle'
           WHEN metric_id % 100 = 0
               THEN 'Needle prefix bank ' || metric_id::text
           WHEN metric_id % 25 = 0
               THEN 'Catalog contains needle ' || metric_id::text
           ELSE 'Scaled public bank ' || lpad(metric_id::text, 6, '0')
       END,
       CASE WHEN metric_id % 40 = 0
            THEN 'needle description fixture ' || metric_id::text
            ELSE 'Deterministic public-bank description ' || metric_id::text END,
       CASE WHEN metric_id % 11 = 0
            THEN '/uploads/query-plan/cover-' || metric_id::text || '.png'
            ELSE NULL END,
       CASE WHEN metric_id % 5 IN (0, 1)
            THEN NULL ELSE 900000 + (metric_id % 2000) END,
       CASE WHEN metric_id % 5 IN (0, 1) THEN '系统题库'
            WHEN metric_id % 50 = 0 THEN 'needle_owner'
            ELSE 'scaled_owner_' || (metric_id % 2000)::text END,
       CASE WHEN metric_id % 5 IN (0, 1) THEN NULL
            ELSE '/uploads/query-plan/avatar-'
                 || (metric_id % 2000)::text || '.png' END,
       metric_id % 500,
       CASE WHEN metric_id % 17 = 0 THEN NULL
            ELSE ((metric_id - 1) % {args.board_count}) + 1 END,
       metric_id % 20 = 0,
       metric_id % 100,
       TIMESTAMP '2026-07-16 12:00:00'
           - make_interval(days => (metric_id % 365)::integer,
                           mins => (metric_id % 1440)::integer),
       TIMESTAMP '2026-07-16 12:00:00'
           - make_interval(days => (metric_id % 90)::integer,
                           mins => (metric_id % 720)::integer),
       metric_id % 1000,
       metric_id % 300,
       metric_id % 700,
       metric_id % 400,
       metric_id % 900,
       metric_id % 250,
       metric_id % 600,
       (metric_id % 10000)::double precision / 100.0,
       (metric_id % 7000)::double precision / 100.0,
       (metric_id % 13000)::double precision / 100.0
           + CASE WHEN metric_id % 20 = 0 THEN 1000 ELSE 0 END,
       CASE WHEN metric_id % 5 IN (0, 1) THEN 'free'
            WHEN metric_id % 3 = 0 THEN 'approval'
            WHEN metric_id % 3 = 1 THEN 'member'
            ELSE 'free' END,
       CASE WHEN metric_id % 5 IN (0, 1) OR metric_id % 3 = 2 THEN ''
            ELSE 'Synthetic join note ' || metric_id::text END,
       metric_id % 5 NOT IN (0, 1) AND metric_id % 7 <> 0,
       CASE WHEN metric_id % 5 IN (0, 1) THEN 0 ELSE metric_id % 80 END,
       1,
       TIMESTAMP '2026-07-16 12:00:00'
FROM generate_series(1, {args.metric_count}) AS generated(metric_id);

WITH generated AS (
    SELECT viewer_number,
           ((viewer_number - 1) / 10)::bigint AS identity_offset,
           ((viewer_number - 1) % 10)::integer AS relation_slot
    FROM generate_series(1, {args.viewer_count}) AS numbered(viewer_number)
),
targeted AS (
    SELECT viewer_number,
           identity_offset,
           relation_slot,
           ((identity_offset * 97 + relation_slot * 7919)
               % {args.metric_count}) + 1 AS metric_id
    FROM generated
)
INSERT INTO public_bank_plaza_viewer_state (
    identity_id, source_type, source_id, has_public, has_shared,
    last_activity_at, snapshot_generation, updated_at
)
SELECT {DETAIL_IDENTITY_ID} + identity_offset,
       CASE WHEN metric_id % 5 IN (0, 1) THEN 'system'
            ELSE 'user_public' END,
       metric_id,
       relation_slot % 3 <> 1,
       relation_slot % 3 <> 0,
       TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
           - make_interval(
               days => ((identity_offset + relation_slot) % 45)::integer,
               mins => ((identity_offset * 7 + relation_slot * 13) % 1440)::integer
             ),
       1,
       TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
FROM targeted;

UPDATE public_bank_plaza_metrics
   SET projection_digest =
       '8f4d37eadf758a4e07e955d15f41a75069046f57634ed8fc99c74001a38d53b1';
UPDATE public_bank_plaza_viewer_state
   SET projection_digest =
       '8f4d37eadf758a4e07e955d15f41a75069046f57634ed8fc99c74001a38d53b1';

INSERT INTO public_bank_plaza_snapshot_state (
    snapshot_name, status, last_success_at, metrics_count,
    system_count, user_public_count, viewer_state_count,
    projection_digest, projector_schema_version, source_high_watermark,
    generation, updated_at
)
SELECT 'public-bank-plaza',
       'complete',
       TIMESTAMPTZ '2026-07-16 12:00:00+08:00',
       COUNT(*),
       COUNT(*) FILTER (WHERE source_type = 'system'),
       COUNT(*) FILTER (WHERE source_type = 'user_public'),
       (SELECT COUNT(*) FROM public_bank_plaza_viewer_state),
       '8f4d37eadf758a4e07e955d15f41a75069046f57634ed8fc99c74001a38d53b1',
       1,
       'synthetic-query-plan-fixture-v1',
       1,
       TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
FROM public_bank_plaza_metrics;

ALTER TABLE public_bank_plaza_metrics
    ALTER COLUMN source_type SET STATISTICS 10000,
    ALTER COLUMN source_id SET STATISTICS 10000,
    ALTER COLUMN name SET STATISTICS 10000,
    ALTER COLUMN description SET STATISTICS 10000,
    ALTER COLUMN owner_label SET STATISTICS 10000,
    ALTER COLUMN plaza_board_id SET STATISTICS 10000,
    ALTER COLUMN published_at SET STATISTICS 10000,
    ALTER COLUMN last_activity_at SET STATISTICS 10000,
    ALTER COLUMN hot_score SET STATISTICS 10000,
    ALTER COLUMN snapshot_generation SET STATISTICS 10000;

ALTER TABLE public_bank_plaza_viewer_state
    ALTER COLUMN identity_id SET STATISTICS 10000,
    ALTER COLUMN source_type SET STATISTICS 10000,
    ALTER COLUMN source_id SET STATISTICS 10000,
    ALTER COLUMN last_activity_at SET STATISTICS 10000,
    ALTER COLUMN snapshot_generation SET STATISTICS 10000;

ANALYZE plaza_boards;
ANALYZE public_bank_plaza_metrics;
ANALYZE public_bank_plaza_viewer_state;
ANALYZE public_bank_plaza_snapshot_state;
"""


NAMED_PARAMETER = re.compile(r"(?<!:):([A-Za-z][A-Za-z0-9_]*)")
POSTGRES_PARAMETER_TYPES = {
    "boolean": "boolean",
    "integer": "integer",
    "bigint": "bigint",
    "text": "text",
    "timestamp": "timestamp",
    "timestamptz": "timestamptz",
}


def postgres_parameter_literal(parameter: dict[str, Any]) -> str:
    jdbc_type = parameter.get("jdbc_type")
    value = parameter.get("value")
    if jdbc_type == "boolean" and isinstance(value, bool):
        return "true" if value else "false"
    if jdbc_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if jdbc_type == "bigint" and isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value):
        return value
    if jdbc_type in {"text", "timestamp", "timestamptz"} and isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise RuntimeError(f"Unsupported or invalid runtime SQL parameter: {parameter}")


def prepared_explain_sql(
    query_id: str,
    sql: str,
    parameters: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    if ";" in sql:
        raise RuntimeError(f"Runtime SQL contains a statement separator: {query_id}")
    if not parameters:
        if NAMED_PARAMETER.search(sql):
            raise RuntimeError(f"Runtime SQL has undeclared parameters: {query_id}")
        explain_sql = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + sql.rstrip() + ";"
        return explain_sql, {
            "mode": "direct",
            "parameter_occurrences": [],
            "prepared_sql_sha256": None,
        }

    occurrence_parameters: list[tuple[str, dict[str, Any]]] = []

    def replace_parameter(match: re.Match[str]) -> str:
        name = match.group(1)
        parameter = parameters.get(name)
        if not isinstance(parameter, dict):
            raise RuntimeError(
                f"Runtime SQL parameter :{name} is missing from manifest query {query_id}"
            )
        jdbc_type = parameter.get("jdbc_type")
        if jdbc_type not in POSTGRES_PARAMETER_TYPES:
            raise RuntimeError(
                f"Runtime SQL parameter :{name} has unsupported type {jdbc_type}"
            )
        occurrence_parameters.append((name, parameter))
        return f"${len(occurrence_parameters)}"

    positional_sql = NAMED_PARAMETER.sub(replace_parameter, sql)
    used_names = {name for name, _ in occurrence_parameters}
    unused_names = sorted(set(parameters) - used_names)
    if unused_names:
        raise RuntimeError(
            f"Runtime SQL manifest has unused parameters for {query_id}: {unused_names}"
        )
    statement_name = "phase4a_" + re.sub(r"[^a-z0-9_]", "_", query_id.lower())
    postgres_types = ", ".join(
        POSTGRES_PARAMETER_TYPES[parameter["jdbc_type"]]
        for _, parameter in occurrence_parameters
    )
    literals = ", ".join(
        postgres_parameter_literal(parameter)
        for _, parameter in occurrence_parameters
    )
    prepared_sql = (
        f"PREPARE {statement_name} ({postgres_types}) AS\n"
        + positional_sql.rstrip()
        + ";\n"
        + "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n"
        + f"EXECUTE {statement_name} ({literals});\n"
        + f"DEALLOCATE {statement_name};"
    )
    return prepared_sql, {
        "mode": "prepare-execute",
        "parameter_occurrences": [
            {
                "position": position,
                "name": name,
                "jdbc_type": parameter["jdbc_type"],
                "value": parameter["value"],
            }
            for position, (name, parameter) in enumerate(occurrence_parameters, start=1)
        ],
        "prepared_sql_sha256": sha256_text(positional_sql),
    }


def explain(
    container: str,
    query_id: str,
    sql: str,
    parameters: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    execution_sql, execution = prepared_explain_sql(query_id, sql, parameters)
    payload = psql_json(container, execution_sql)
    if not isinstance(payload, list) or len(payload) != 1 or "Plan" not in payload[0]:
        raise RuntimeError("unexpected EXPLAIN (FORMAT JSON) payload")
    return payload[0], execution


def collect_buffer_fields(value: Any) -> list[str]:
    fields: set[str] = set()

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                if key in BUFFER_KEYS:
                    fields.add(key)
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return sorted(fields)


def normalize_explain(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_explain(child) for child in value]
    if not isinstance(value, dict):
        return value
    normalized: dict[str, Any] = {}
    for key, child in value.items():
        if key in TIMING_KEYS or key in BUFFER_KEYS or key in MEMORY_KEYS:
            continue
        if key == "Workers":
            continue
        candidate = normalize_explain(child)
        if candidate == {} or candidate == [] and isinstance(child, (dict, list)):
            continue
        normalized[key] = candidate
    return normalized


def plan_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: dict[str, Any], depth: int) -> None:
        summary = {"depth": depth}
        for key in (
            "Node Type",
            "Parent Relationship",
            "Strategy",
            "Join Type",
            "Relation Name",
            "Alias",
            "Index Name",
            "Actual Rows",
            "Actual Loops",
            "Rows Removed by Filter",
            "Plan Rows",
            "Filter",
            "Index Cond",
            "Hash Cond",
            "Join Filter",
            "Sort Key",
            "Group Key",
        ):
            if key in node:
                summary[key] = node[key]
        nodes.append(summary)
        for child in node.get("Plans", []):
            visit(child, depth + 1)

    visit(root, 0)
    return nodes


def summarize_plan(
    normalized_explain: dict[str, Any],
    buffer_fields: list[str],
) -> dict[str, Any]:
    root = normalized_explain["Plan"]
    nodes = plan_nodes(root)
    relations = Counter(
        str(node["Relation Name"]) for node in nodes if "Relation Name" in node
    )
    indexes = sorted(
        {str(node["Index Name"]) for node in nodes if "Index Name" in node}
    )
    node_types = Counter(str(node["Node Type"]) for node in nodes)
    actual_loops = [int(node.get("Actual Loops", 0)) for node in nodes]
    return {
        "root_node_type": root.get("Node Type"),
        "result_row_count": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max(node["depth"] for node in nodes),
        "maximum_actual_loops": max(actual_loops, default=0),
        "node_type_counts": dict(sorted(node_types.items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "index_names": indexes,
        "buffer_fields_observed_before_normalization": buffer_fields,
        "nodes": nodes,
    }


def dataset_metadata(container: str, args: argparse.Namespace) -> dict[str, Any]:
    return psql_json(
        container,
        f"""
SELECT json_build_object(
    'boards', (SELECT COUNT(*) FROM plaza_boards),
    'active_boards', (SELECT COUNT(*) FROM plaza_boards WHERE is_active),
    'metrics', (SELECT COUNT(*) FROM public_bank_plaza_metrics),
    'system_metrics', (
        SELECT COUNT(*) FROM public_bank_plaza_metrics WHERE source_type = 'system'
    ),
    'user_public_metrics', (
        SELECT COUNT(*) FROM public_bank_plaza_metrics WHERE source_type = 'user_public'
    ),
    'keyword_metrics', (
        SELECT COUNT(*)
        FROM public_bank_plaza_metrics m
        WHERE {FIXTURE_KEYWORD_PREDICATE}
    ),
    'viewer_states', (SELECT COUNT(*) FROM public_bank_plaza_viewer_state),
    'distinct_viewers', (
        SELECT COUNT(DISTINCT identity_id) FROM public_bank_plaza_viewer_state
    ),
    'recent_active_viewers', (
        SELECT COUNT(DISTINCT identity_id)
        FROM public_bank_plaza_viewer_state
        WHERE last_activity_at >= TIMESTAMPTZ '2026-07-09 04:00:00+00:00'
    ),
    'detail_relation', (
        SELECT json_build_object(
            'identity_id', identity_id,
            'source_type', source_type,
            'source_id', source_id,
            'has_public', has_public,
            'has_shared', has_shared
        )
        FROM public_bank_plaza_viewer_state
        WHERE identity_id = {DETAIL_IDENTITY_ID}
          AND source_type = 'user_public'
          AND source_id = {DETAIL_SOURCE_ID}
    ),
    'snapshot_state', (
        SELECT json_build_object(
            'status', status,
            'metrics_count', metrics_count,
            'system_count', system_count,
            'user_public_count', user_public_count,
            'viewer_state_count', viewer_state_count,
            'generation', generation
        )
        FROM public_bank_plaza_snapshot_state
    )
);
""",
    )


def environment_metadata(container: str) -> dict[str, Any]:
    return psql_json(
        container,
        """
SELECT json_build_object(
    'server_version', current_setting('server_version'),
    'server_version_num', current_setting('server_version_num'),
    'block_size_bytes', current_setting('block_size'),
    'shared_buffers', current_setting('shared_buffers'),
    'work_mem', current_setting('work_mem'),
    'effective_cache_size', current_setting('effective_cache_size'),
    'random_page_cost', current_setting('random_page_cost'),
    'max_parallel_workers_per_gather',
        current_setting('max_parallel_workers_per_gather'),
    'jit', current_setting('jit')
);
""",
    )


def index_definitions(container: str) -> list[dict[str, str]]:
    return psql_json(
        container,
        """
SELECT COALESCE(
    json_agg(
        json_build_object(
            'table', tablename,
            'name', indexname,
            'definition', indexdef
        ) ORDER BY tablename, indexname
    ),
    '[]'::json
)
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
      'plaza_boards',
      'public_bank_plaza_metrics',
      'public_bank_plaza_viewer_state',
      'public_bank_plaza_snapshot_state'
  );
""",
    )


def query_specs(runtime_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    relation_budget = {
        "plaza_boards": 1,
        "public_bank_plaza_metrics": 4,
        "public_bank_plaza_snapshot_state": 1,
        "public_bank_plaza_viewer_state": 3,
    }
    boundary_indexes = [
        "ix_public_bank_plaza_snapshot_boundary",
        "ix_public_bank_plaza_viewer_snapshot_boundary",
    ]
    expected_parameters = {
        "search-count-keyword": {
            "keyword": {"jdbc_type": "text", "value": "%needle%"},
        },
        "search-page-latest": {
            "limit": {"jdbc_type": "integer", "value": DEFAULT_PAGE_SIZE},
            "offset": {"jdbc_type": "bigint", "value": str(DEFAULT_PAGE_OFFSET)},
            "viewerId": {"jdbc_type": "bigint", "value": str(DETAIL_IDENTITY_ID)},
            "viewerPresent": {"jdbc_type": "boolean", "value": True},
        },
        "search-page-latest-keyword": {
            "keyword": {"jdbc_type": "text", "value": "%needle%"},
            "keywordExact": {"jdbc_type": "text", "value": KEYWORD},
            "keywordPrefix": {"jdbc_type": "text", "value": "needle%"},
            "limit": {"jdbc_type": "integer", "value": DEFAULT_PAGE_SIZE},
            "offset": {"jdbc_type": "bigint", "value": str(DEFAULT_PAGE_OFFSET)},
            "viewerId": {"jdbc_type": "bigint", "value": str(DETAIL_IDENTITY_ID)},
            "viewerPresent": {"jdbc_type": "boolean", "value": True},
        },
        "boards-directory": {},
        "hot-top-five": {
            "limit": {"jdbc_type": "integer", "value": 5},
        },
        "summary-rolling-seven-days": {
            "activityCutoff7d": {
                "jdbc_type": "timestamptz",
                "value": "2026-07-09T04:00Z",
            },
            "publishedCutoff7d": {
                "jdbc_type": "timestamp",
                "value": "2026-07-09T12:00",
            },
        },
        "detail-with-both-relation": {
            "detailId": {"jdbc_type": "bigint", "value": str(DETAIL_SOURCE_ID)},
            "detailSource": {"jdbc_type": "text", "value": "user_public"},
            "viewerId": {"jdbc_type": "bigint", "value": str(DETAIL_IDENTITY_ID)},
            "viewerPresent": {"jdbc_type": "boolean", "value": True},
        },
    }
    static_specs = [
        {
            "query_id": "search-count-keyword",
            "operation": "search-count",
            "expected_rows": 1,
            "required_indexes": boundary_indexes,
            "relation_scan_budget": relation_budget,
        },
        {
            "query_id": "search-page-latest",
            "operation": "search-page",
            "expected_rows": DEFAULT_PAGE_SIZE,
            "required_indexes": boundary_indexes + ["ix_public_bank_plaza_latest"],
            "relation_scan_budget": relation_budget,
        },
        {
            "query_id": "search-page-latest-keyword",
            "operation": "search-page",
            "expected_rows": DEFAULT_PAGE_SIZE,
            "required_indexes": boundary_indexes,
            "relation_scan_budget": relation_budget,
        },
        {
            "query_id": "boards-directory",
            "operation": "boards",
            "expected_rows": DEFAULT_BOARD_COUNT - DEFAULT_BOARD_COUNT // 8,
            "required_indexes": boundary_indexes,
            "relation_scan_budget": relation_budget,
        },
        {
            "query_id": "hot-top-five",
            "operation": "hot",
            "expected_rows": 5,
            "required_indexes": boundary_indexes + ["ix_public_bank_plaza_hot"],
            "relation_scan_budget": relation_budget,
        },
        {
            "query_id": "summary-rolling-seven-days",
            "operation": "summary",
            "expected_rows": 1,
            "required_indexes": boundary_indexes
            + ["ix_public_bank_plaza_viewer_activity"],
            "relation_scan_budget": relation_budget,
        },
        {
            "query_id": "detail-with-both-relation",
            "operation": "detail",
            "expected_rows": 1,
            "required_indexes": [
                *boundary_indexes,
                "uq_public_bank_plaza_metric_source",
                "pk_public_bank_plaza_viewer_state",
            ],
            "relation_scan_budget": relation_budget,
        },
    ]
    runtime_queries = {
        query["query_id"]: query for query in runtime_manifest["queries"]
    }
    specs: list[dict[str, Any]] = []
    for static_spec in static_specs:
        query_id = static_spec["query_id"]
        runtime_query = runtime_queries[query_id]
        if runtime_query.get("operation") != static_spec["operation"]:
            raise RuntimeError(f"Runtime SQL operation drifted for {query_id}")
        if runtime_query["parameters"] != expected_parameters[query_id]:
            raise RuntimeError(
                f"Runtime SQL fixture parameters drifted for {query_id}: "
                f"{runtime_query['parameters']}"
            )
        specs.append({
            **static_spec,
            "sql": runtime_query["sql"],
            "parameters": runtime_query["parameters"],
        })
    return specs


def assert_plan(
    spec: dict[str, Any],
    summary: dict[str, Any],
) -> list[str]:
    passed: list[str] = []
    if summary["result_row_count"] != spec["expected_rows"]:
        raise AssertionError(
            f"{spec['query_id']} returned {summary['result_row_count']} rows; "
            f"expected {spec['expected_rows']}"
        )
    passed.append("expected-result-row-count")
    if summary["root_actual_loops"] != 1:
        raise AssertionError(f"{spec['query_id']} root loop count is not one")
    passed.append("single-root-execution")
    if summary["node_count"] > 64 or summary["maximum_depth"] > 16:
        raise AssertionError(
            f"{spec['query_id']} plan is outside node/depth bounds: "
            f"{summary['node_count']}/{summary['maximum_depth']}"
        )
    passed.append("bounded-plan-nodes")
    for relation, occurrences in summary["relation_scan_occurrences"].items():
        budget = spec["relation_scan_budget"].get(relation, 0)
        if occurrences > budget:
            raise AssertionError(
                f"{spec['query_id']} scans {relation} {occurrences} times; budget {budget}"
            )
    passed.append("fixed-relation-scan-budget")
    missing = sorted(
        set(spec["required_indexes"]) - set(summary["index_names"])
    )
    if missing:
        raise AssertionError(f"{spec['query_id']} missed critical indexes: {missing}")
    if spec["required_indexes"]:
        passed.append("critical-index-observed")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise AssertionError(f"{spec['query_id']} did not expose BUFFERS fields")
    passed.append("buffers-captured-before-normalization")
    return passed


def capture(
    args: argparse.Namespace,
    container: str,
    image_id: str,
    schema_sql: str,
    schema_path: Path,
    runtime_manifest: dict[str, Any],
    runtime_manifest_path: Path,
) -> dict[str, Any]:
    dataset = dataset_metadata(container, args)
    if dataset["metrics"] != args.metric_count:
        raise AssertionError("metric fixture row count drifted")
    if dataset["viewer_states"] != args.viewer_count:
        raise AssertionError("viewer fixture row count drifted")
    if dataset["detail_relation"] != {
        "identity_id": DETAIL_IDENTITY_ID,
        "source_type": "user_public",
        "source_id": DETAIL_SOURCE_ID,
        "has_public": True,
        "has_shared": True,
    }:
        raise AssertionError(f"detail relation fixture drifted: {dataset['detail_relation']}")

    indexes = index_definitions(container)
    defined_index_names = {entry["name"] for entry in indexes}
    required_defined = {
        "ix_public_bank_plaza_latest",
        "ix_public_bank_plaza_hot",
        "ix_public_bank_plaza_active",
        "ix_public_bank_plaza_featured",
        "ix_public_bank_plaza_questions",
        "ix_public_bank_plaza_board",
        "ix_public_bank_plaza_viewer_activity",
        "ix_public_bank_plaza_snapshot_boundary",
        "ix_public_bank_plaza_viewer_snapshot_boundary",
        "uq_public_bank_plaza_metric_source",
        "pk_public_bank_plaza_viewer_state",
    }
    missing_definitions = sorted(required_defined - defined_index_names)
    if missing_definitions:
        raise AssertionError(f"042-equivalent indexes missing: {missing_definitions}")

    queries: list[dict[str, Any]] = []
    observed_indexes: set[str] = set()
    for spec in query_specs(runtime_manifest):
        raw_explain, execution = explain(
            container,
            spec["query_id"],
            spec["sql"],
            spec["parameters"],
        )
        buffer_fields = collect_buffer_fields(raw_explain)
        normalized = normalize_explain(raw_explain)
        summary = summarize_plan(normalized, buffer_fields)
        checks = assert_plan(spec, summary)
        observed_indexes.update(summary["index_names"])
        queries.append({
            "query_id": spec["query_id"],
            "operation": spec["operation"],
            "source": (
                "server/src/main/java/io/saksk/ti/catalog/infrastructure/"
                "persistence/JdbcPublicBankSnapshotQueryAdapter.java"
            ),
            "parameters": spec["parameters"],
            "sql": spec["sql"],
            "sql_sha256": sha256_text(spec["sql"]),
            "bound_explain_execution": execution,
            "sql_statement_count": 1,
            "assertions_passed": checks,
            "plan_summary": summary,
            "normalized_explain_analyze": normalized,
        })

    globally_required_observed = {
        "ix_public_bank_plaza_latest",
        "ix_public_bank_plaza_hot",
        "ix_public_bank_plaza_viewer_activity",
        "ix_public_bank_plaza_snapshot_boundary",
        "ix_public_bank_plaza_viewer_snapshot_boundary",
        "uq_public_bank_plaza_metric_source",
        "pk_public_bank_plaza_viewer_state",
    }
    globally_missing = sorted(globally_required_observed - observed_indexes)
    if globally_missing:
        raise AssertionError(f"critical indexes were never selected: {globally_missing}")

    image_metadata_raw = run(["docker", "image", "inspect", args.image]).stdout
    image_metadata = json.loads(image_metadata_raw)[0]
    expected_digest = args.image.split("@", 1)[1]
    repo_digests = sorted(image_metadata.get("RepoDigests", []))
    if not any(value.endswith(expected_digest) for value in repo_digests):
        raise AssertionError(
            f"resolved image does not expose expected digest {expected_digest}"
        )

    tool_path = Path(__file__).resolve()
    adapter_path = (
        tool_path.parents[1]
        / "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "JdbcPublicBankSnapshotQueryAdapter.java"
    )
    exporter_path = (
        tool_path.parents[1]
        / "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "PublicBankRuntimeSqlManifestTest.java"
    )
    return {
        "evidence_id": "ti.phase4a.public-bank-query-plan",
        "schema_version": 1,
        "captured_at": "2026-07-16",
        "scope": "phase4a-public-bank-read-model-large-fixture",
        "environment": {
            "container_image": args.image,
            "expected_image_digest": expected_digest,
            "resolved_image_id": image_id,
            "resolved_repo_digests": repo_digests,
            "container_os": image_metadata.get("Os"),
            "container_architecture": image_metadata.get("Architecture"),
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment_metadata(container),
        },
        "inputs": {
            "schema": str(schema_path.relative_to(tool_path.parents[1])),
            "schema_sha256": sha256_text(schema_sql),
            "adapter": str(adapter_path.relative_to(tool_path.parents[1])),
            "adapter_sha256": sha256_text(adapter_path.read_text(encoding="utf-8")),
            "runtime_sql_manifest": str(
                runtime_manifest_path.relative_to(tool_path.parents[1])
            ),
            "runtime_sql_manifest_sha256": sha256_text(
                runtime_manifest_path.read_text(encoding="utf-8")
            ),
            "runtime_sql_exporter": str(exporter_path.relative_to(tool_path.parents[1])),
            "runtime_sql_exporter_sha256": sha256_text(
                exporter_path.read_text(encoding="utf-8")
            ),
            "capture_tool_sha256": sha256_text(tool_path.read_text(encoding="utf-8")),
        },
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "metric_count": args.metric_count,
                "viewer_count": args.viewer_count,
                "board_count": args.board_count,
                "snapshot_generation": 1,
                "fixed_now_bj": FIXED_NOW_BJ,
                "fixed_now_instant": FIXED_NOW_INSTANT,
                "detail_identity_id": DETAIL_IDENTITY_ID,
                "detail_source_id": DETAIL_SOURCE_ID,
            },
            "actual_row_counts_and_distribution": dataset,
            "distribution": {
                "source_type": "metric_id modulo 5 gives 40 percent system and 60 percent user_public",
                "keyword": "exact, prefix, name-contains, description and owner-label matches",
                "viewer": "ten unique metric relations per identity with deterministic public/shared flags",
                "activity": "viewer activity is spread deterministically across 45 days",
            },
            "statistics": (
                "ANALYZE completed after setting statistics target 10000 on all predicate, "
                "join and ordering columns; the bounded fixture is fully sampled"
            ),
            "index_definitions": indexes,
        },
        "measurement": {
            "command": (
                "PREPARE exact Java runtime SQL with typed positional parameters; "
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) EXECUTE"
            ),
            "runs_per_query": 1,
            "query_count": len(queries),
            "operation_statement_budget": {
                "search": 2,
                "boards": 1,
                "hot": 1,
                "summary": 1,
                "detail": 1,
            },
            "queries": queries,
        },
        "normalization": {
            "removed": [
                "planning and execution timing",
                "per-node actual timing",
                "cache-dependent buffer block counts",
                "runtime memory counters",
                "parallel worker identities and counters",
                "container id and container name",
            ],
            "retained": [
                "plan node types and depth",
                "actual rows and loops",
                "plan row estimates and costs",
                "filters, joins, sort and group keys",
                "relation and index names",
                "which BUFFERS fields were emitted",
            ],
        },
        "assertions": {
            "status": "passed",
            "data_scale": {
                "metrics_at_least_50000": dataset["metrics"] >= 50_000,
                "viewer_rows_at_least_100000": dataset["viewer_states"] >= 100_000,
            },
            "fixed_sql_budget_no_n_plus_one": True,
            "query_node_bound": 64,
            "query_depth_bound": 16,
            "critical_indexes_defined": sorted(required_defined),
            "critical_indexes_observed": sorted(globally_required_observed),
            "relation_scan_occurrence_budgets_checked": True,
            "all_root_executions_once": True,
        },
        "interpretation": {
            "status": "observational_evidence_only",
            "statement": (
                "The plans describe one isolated deterministic PostgreSQL 18 synthetic "
                "fixture. Runtime timing and cache counters are intentionally excluded. "
                "Every measured statement is exported from the Java runtime adapter and "
                "executed through typed PostgreSQL parameters. No latency SLA, production "
                "capacity claim or cross-host benchmark is inferred."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/capture_phase4a_public_bank_query_plans.py "
                "--output Ti-Java/docs/refactor/phase4a/public-bank-query-plan-evidence.json"
            ),
            "prerequisite": "Docker with access to the pinned PostgreSQL image digest",
            "isolation": "ephemeral network-disabled container; removed on success or failure",
        },
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    if shutil.which("docker") is None:
        raise SystemExit("docker is required")

    root = Path(__file__).resolve().parents[1]
    runtime_manifest_path = args.runtime_sql_manifest.resolve()
    export_runtime_sql_manifest(root, runtime_manifest_path)
    runtime_manifest = load_runtime_sql_manifest(runtime_manifest_path)
    schema_path = root / "server/src/test/resources/db/phase4a/042-public-bank-snapshot-schema.sql"
    if not schema_path.is_file():
        raise SystemExit(f"missing Phase 4A snapshot schema: {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    for required in (
        "public_bank_plaza_metrics",
        "public_bank_plaza_viewer_state",
        "public_bank_plaza_snapshot_state",
        "metrics_count",
    ):
        if required not in schema_sql:
            raise SystemExit(f"042 schema is missing required token: {required}")

    container = f"ti-phase4a-public-bank-plan-{uuid.uuid4().hex[:12]}"
    started = False
    try:
        start = run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--network=none",
                f"--name={container}",
                "--env=POSTGRES_PASSWORD=PUBLIC-TEST-ONLY-phase4a",
                f"--env=POSTGRES_DB={DEFAULT_DATABASE}",
                args.image,
                "-c",
                "max_parallel_workers_per_gather=0",
                "-c",
                "jit=off",
            ],
            check=False,
        )
        if start.returncode != 0:
            raise RuntimeError(f"failed to start PostgreSQL container: {start.stderr.strip()}")
        started = True
        wait_until_ready(container, args.startup_timeout_seconds)
        psql(container, setup_sql(args, schema_sql))
        image_id = run(
            ["docker", "inspect", "--format={{.Image}}", container]
        ).stdout.strip()
        evidence = capture(
            args,
            container,
            image_id,
            schema_sql,
            schema_path,
            runtime_manifest,
            runtime_manifest_path,
        )

        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(
            evidence,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(output)
        print(json.dumps({
            "output": str(output),
            "sha256": sha256_text(rendered),
            "metric_count": args.metric_count,
            "viewer_count": args.viewer_count,
            "query_count": evidence["measurement"]["query_count"],
            "assertions": evidence["assertions"]["status"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        if started:
            run(["docker", "rm", "--force", container], check=False)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (
        AssertionError,
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        ValueError,
    ) as exc:
        raise SystemExit(str(exc)) from exc
