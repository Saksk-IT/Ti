#!/usr/bin/env python3
"""Capture deterministic PG18 plan evidence for question detail by ID.

The runtime SQL is exported from the Java JDBC adapter before capture. This
tool owns only a public synthetic fixture, five fixed bigint bindings, plan
normalization, and fail-closed assertions. It never derives runtime SQL from a
second handwritten implementation.
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
import time
from typing import Any, Iterable, Optional
import uuid


DEFAULT_IMAGE = (
    "postgres:18.4-alpine@"
    "sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
DEFAULT_DATABASE = "phase4a_question_detail_plan"
DEFAULT_QUESTION_COUNT = 150_000
DEFAULT_SUBJECT_COUNT = 5_000
LONG_MAX_VALUE = 9_223_372_036_854_775_807

MANIFEST_ID = "ti.phase4a.question-detail-runtime-sql"
ADAPTER_CLASS = (
    "io.saksk.ti.catalog.infrastructure.persistence."
    "JdbcQuestionDetailQueryAdapter"
)
QUERY_ID = "question-detail-by-id"
OPERATION = "question-detail"
PARAMETER_NAME = "question_id"
ROUTE_IDS = ("8cb323acac12", "d7d727b88aea")

NAMED_PARAMETER = re.compile(r"(?<!:):([A-Za-z][A-Za-z0-9_]*)")
FORBIDDEN_RUNTIME_SQL = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|copy|call|do|"
    r"vacuum|analyze|refresh|grant|revoke|temporary|temp)\b",
    re.IGNORECASE,
)
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
MEMORY_KEYS = {
    "Peak Memory Usage",
    "Sort Space Used",
    "Average Peak Memory",
}
PLAN_EXPRESSION_KEYS = {
    "Filter",
    "Index Cond",
    "Hash Cond",
    "Join Filter",
    "Merge Cond",
    "Recheck Cond",
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported Phase 4A question-detail plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root
        / "docs/refactor/phase4a/question-detail-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-question-detail-runtime-sql.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--question-count", type=int, default=DEFAULT_QUESTION_COUNT
    )
    parser.add_argument("--subject-count", type=int, default=DEFAULT_SUBJECT_COUNT)
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.question_count < DEFAULT_QUESTION_COUNT:
        raise ValueError(
            f"--question-count must be at least {DEFAULT_QUESTION_COUNT}"
        )
    if args.subject_count < DEFAULT_SUBJECT_COUNT:
        raise ValueError(
            f"--subject-count must be at least {DEFAULT_SUBJECT_COUNT}"
        )
    if args.subject_count > args.question_count:
        raise ValueError("--subject-count cannot exceed --question-count")
    if args.question_count + 1 > LONG_MAX_VALUE:
        raise ValueError("--question-count exceeds the signed bigint fixture bound")
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")
    if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", args.image):
        raise ValueError("--image must be an immutable digest reference")


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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_runtime_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("runtime SQL manifest must stay under server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = run(
        [
            str(verifier),
            "-Dtest=QuestionDetailRuntimeSqlManifestTest",
            f"-Dti.question-detail.sql-manifest-output={output}",
            "test",
        ],
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java runtime SQL export failed: {detail}")


def validate_runtime_sql(query_id: str, sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError(f"runtime SQL is empty for {query_id}")
    if ";" in stripped:
        raise RuntimeError(
            f"runtime SQL contains a statement separator: {query_id}"
        )
    if not re.match(r"^select\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL is not one SELECT: {query_id}")
    forbidden = FORBIDDEN_RUNTIME_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(
            f"runtime SQL contains forbidden token {forbidden.group(0)}: "
            f"{query_id}"
        )
    if re.search(r"\bpg_temp\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL references pg_temp: {query_id}")
    if re.search(r"\bselect\s+(?:(?:[A-Za-z][A-Za-z0-9_]*)\.)?\*", stripped,
                 re.IGNORECASE):
        raise RuntimeError(
            f"runtime SQL must use an explicit question column list: {query_id}"
        )
    if not re.search(r"\bfrom\s+questions(?:\s+[A-Za-z][A-Za-z0-9_]*)?\b",
                     stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL must read questions: {query_id}")
    if re.search(r"\bjoin\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL must not join another relation: {query_id}")
    occurrences = NAMED_PARAMETER.findall(stripped)
    if occurrences != [PARAMETER_NAME]:
        raise RuntimeError(
            "runtime SQL must contain exactly one :question_id bind occurrence: "
            f"{query_id}:{occurrences}"
        )


def _normalized_parameter_type(parameter: Any) -> str:
    if isinstance(parameter, bool):
        return ""
    if isinstance(parameter, int):
        return "bigint"
    if isinstance(parameter, str):
        normalized = parameter.strip().lower().replace(" ", "_")
        if normalized in {"bigint", "long", "java_long", "jdbc_bigint"}:
            return "bigint"
        if re.fullmatch(r"[0-9]+", normalized):
            return "bigint"
        return ""
    if not isinstance(parameter, dict):
        return ""
    explicit = str(parameter.get("postgres_type") or "").strip().lower()
    jdbc = str(parameter.get("jdbc_type") or "").strip().lower()
    candidate = explicit or jdbc
    candidate = candidate.replace("-", "_").replace(" ", "_")
    return {
        "bigint": "bigint",
        "long": "bigint",
        "java_long": "bigint",
        "jdbc_bigint": "bigint",
    }.get(candidate, "")


def validate_parameter_template(parameter: Any) -> None:
    if _normalized_parameter_type(parameter) != "bigint":
        raise RuntimeError("question_id runtime parameter must be bigint")
    if isinstance(parameter, int):
        if parameter < 0 or parameter > LONG_MAX_VALUE:
            raise RuntimeError("question_id manifest example is outside bigint")
        return
    if isinstance(parameter, str):
        if re.fullmatch(r"[0-9]+", parameter.strip()):
            value = int(parameter.strip())
            if value > LONG_MAX_VALUE:
                raise RuntimeError("question_id manifest example is outside bigint")
        return
    if isinstance(parameter, dict):
        bind_kind = parameter.get("bind_kind")
        if bind_kind not in (None, "jdbc-scalar"):
            raise RuntimeError("question_id bind_kind must be jdbc-scalar")
        if "value" in parameter:
            raw_value = parameter["value"]
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, str)):
                raise RuntimeError("question_id manifest example must be an integer")
            try:
                value = int(raw_value)
            except ValueError as exc:
                raise RuntimeError(
                    "question_id manifest example must be an integer"
                ) from exc
            if value < 0 or value > LONG_MAX_VALUE:
                raise RuntimeError("question_id manifest example is outside bigint")


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"cannot read Java runtime SQL manifest: {path}"
        ) from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID:
        raise RuntimeError("question-detail runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("question-detail runtime SQL manifest schema drifted")
    if manifest.get("adapter_class") != ADAPTER_CLASS:
        raise RuntimeError("question-detail runtime SQL adapter class drifted")
    queries = manifest.get("queries")
    if (
        not isinstance(queries, list)
        or manifest.get("query_count") != 1
        or len(queries) != 1
        or not isinstance(queries[0], dict)
    ):
        raise RuntimeError(
            "question-detail runtime SQL manifest must contain one query"
        )
    query = queries[0]
    if query.get("query_id") != QUERY_ID:
        raise RuntimeError("question-detail runtime SQL query ID drifted")
    if query.get("operation") != OPERATION:
        raise RuntimeError("question-detail runtime SQL operation drifted")
    sql = query.get("sql")
    parameters = query.get("parameters")
    if not isinstance(sql, str) or not isinstance(parameters, dict):
        raise RuntimeError("question-detail runtime SQL query shape drifted")
    if set(parameters) != {PARAMETER_NAME}:
        raise RuntimeError(
            "question-detail runtime SQL must declare only question_id"
        )
    validate_runtime_sql(QUERY_ID, sql)
    validate_parameter_template(parameters[PARAMETER_NAME])
    return manifest


def runtime_query(manifest: dict[str, Any]) -> dict[str, Any]:
    return manifest["queries"][0]


def bound_parameter(question_id: int) -> dict[str, Any]:
    if (
        isinstance(question_id, bool)
        or not isinstance(question_id, int)
        or question_id < 0
        or question_id > LONG_MAX_VALUE
    ):
        raise RuntimeError("question_id binding must be a non-negative bigint")
    return {
        "bind_kind": "jdbc-scalar",
        "postgres_type": "bigint",
        "value": question_id,
    }


def prepared_execution_sql(
    observation_id: str,
    sql: str,
    question_id: int,
    *,
    explain: bool = True,
) -> tuple[str, dict[str, Any]]:
    validate_runtime_sql(observation_id, sql)
    occurrences: list[str] = []

    def replace(match: re.Match[str]) -> str:
        occurrences.append(match.group(1))
        return f"${len(occurrences)}"

    positional_sql = NAMED_PARAMETER.sub(replace, sql)
    if occurrences != [PARAMETER_NAME]:
        raise RuntimeError(
            f"question-detail bind surface drifted: {occurrences}"
        )
    parameter = bound_parameter(question_id)
    statement_name = "qd_" + re.sub(
        r"[^a-z0-9_]", "_", observation_id.lower()
    )
    statement_name = statement_name[:48] + "_" + sha256_text(observation_id)[:8]
    prefix = (
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" if explain else ""
    )
    execution_sql = (
        f"PREPARE {statement_name} (bigint) AS\n{positional_sql};\n"
        f"{prefix}EXECUTE {statement_name} ({question_id});\n"
        f"DEALLOCATE {statement_name};"
    )
    return execution_sql, {
        "mode": "prepare-execute",
        "bound_parameter_count": 1,
        "named_parameter_count": 1,
        "occurrence_names": occurrences,
        "positional_sql_sha256": sha256_text(positional_sql),
        "parameters": {PARAMETER_NAME: parameter},
    }


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
        raise RuntimeError(
            "PostgreSQL command failed "
            f"(exit={result.returncode}, sql_sha256={sha256_text(sql)}): "
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
        raise RuntimeError(
            f"PostgreSQL returned invalid JSON: {raw[:1000]}"
        ) from exc


def wait_until_ready(container: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        ready = run(
            [
                "docker",
                "exec",
                container,
                "pg_isready",
                "--username=postgres",
                f"--dbname={DEFAULT_DATABASE}",
            ],
            check=False,
        )
        if ready.returncode == 0:
            return
        time.sleep(1)
    logs = run(["docker", "logs", container], check=False)
    raise RuntimeError(
        "PostgreSQL did not become ready: "
        f"{(logs.stdout + logs.stderr)[-3000:]}"
    )


def fixture_sql(args: argparse.Namespace) -> str:
    return f"""
CREATE TABLE questions (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    subject_id integer,
    type text NOT NULL,
    content text NOT NULL,
    options text DEFAULT '[]',
    answer text DEFAULT '[]',
    analysis text,
    tags text DEFAULT '[]',
    difficulty integer DEFAULT 1,
    image_path text,
    source text,
    created_by integer,
    updated_by integer,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO questions (
    id, subject_id, type, content, options, answer, analysis, tags,
    difficulty, image_path, source, created_by, updated_by, created_at,
    updated_at
)
SELECT n,
       ((n - 1) % {args.subject_count}) + 1,
       (ARRAY['single_choice', 'multi_choice', 'boolean', 'fill', 'essay'])[
           1 + ((n - 1) % 5)
       ],
       'Synthetic question ' || n,
       '["A. Alpha", "B. Beta"]',
       '[0]',
       'Synthetic analysis ' || n,
       '["synthetic"]',
       1 + ((n - 1) % 5),
       CASE WHEN n % 10 = 0 THEN '/synthetic/question-' || n || '.png' END,
       CASE WHEN n % 2 = 0 THEN 'synthetic-even' ELSE 'synthetic-odd' END,
       100000 + (n % 1000),
       CASE WHEN n % 3 = 0 THEN 200000 + (n % 1000) END,
       timestamp '2026-01-01 00:00:00' + (n * interval '1 second'),
       timestamp '2026-01-02 00:00:00' + (n * interval '1 second')
FROM generate_series(1, {args.question_count}) AS generated(n);

VACUUM (ANALYZE) questions;
"""


def observation_specs(args: argparse.Namespace) -> list[dict[str, Any]]:
    middle = max(1, args.question_count // 2)
    return [
        {
            "observation_id": "first-existing-question",
            "question_id": 1,
            "expected_rows": 1,
        },
        {
            "observation_id": "middle-existing-question",
            "question_id": middle,
            "expected_rows": 1,
        },
        {
            "observation_id": "last-existing-question",
            "question_id": args.question_count,
            "expected_rows": 1,
        },
        {
            "observation_id": "first-missing-question",
            "question_id": args.question_count + 1,
            "expected_rows": 0,
        },
        {
            "observation_id": "signed-bigint-maximum-missing-question",
            "question_id": LONG_MAX_VALUE,
            "expected_rows": 0,
        },
    ]


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
        if key in TIMING_KEYS or key in BUFFER_KEYS or key in MEMORY_KEYS:
            continue
        if key in {"Workers", "JIT"}:
            continue
        if key in PLAN_EXPRESSION_KEYS and isinstance(child, str):
            normalized[key] = {
                "redacted": "planner expression omitted",
                "character_count": len(child),
                "sha256": sha256_text(child),
            }
            continue
        candidate = normalize_explain(child)
        if isinstance(child, (dict, list)) and candidate in ({}, []):
            continue
        normalized[key] = candidate
    return normalized


def plan_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: dict[str, Any], depth: int) -> None:
        summary: dict[str, Any] = {"depth": depth}
        for key in (
            "Node Type",
            "Parent Relationship",
            "Relation Name",
            "Alias",
            "Index Name",
            "Scan Direction",
            "Actual Rows",
            "Actual Loops",
            "Rows Removed by Filter",
            "Plan Rows",
            "Index Cond",
            "Filter",
        ):
            if key in node:
                summary[key] = node[key]
        nodes.append(summary)
        for child in node.get("Plans", []):
            visit(child, depth + 1)

    visit(root, 0)
    return nodes


def summarize_plan(
    normalized_explain: dict[str, Any], buffer_fields: dict[str, float]
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
    loops = [int(node.get("Actual Loops", 0)) for node in nodes]
    return {
        "root_node_type": root.get("Node Type"),
        "result_row_count": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max(node["depth"] for node in nodes),
        "maximum_actual_loops": max(loops, default=0),
        "node_type_counts": dict(sorted(node_types.items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "index_names": indexes,
        "buffer_fields_observed_before_normalization": sorted(buffer_fields),
        "nodes": nodes,
    }


def assert_plan(
    spec: dict[str, Any],
    execution: dict[str, Any],
    summary: dict[str, Any],
    temp_blocks: dict[str, float],
) -> list[str]:
    passed: list[str] = []
    if summary["result_row_count"] != spec["expected_rows"]:
        raise AssertionError(
            f"{spec['observation_id']} returned "
            f"{summary['result_row_count']} rows; expected {spec['expected_rows']}"
        )
    passed.append("expected-found-or-missing-row-count")
    if summary["root_actual_loops"] != 1 or summary["maximum_actual_loops"] != 1:
        raise AssertionError("question-detail plan must execute every node once")
    passed.append("single-execution-no-row-driven-loop")
    if summary["node_count"] > 2 or summary["maximum_depth"] > 1:
        raise AssertionError("question-detail plan exceeded node/depth bounds")
    passed.append("bounded-plan-shape")
    if summary["relation_scan_occurrences"] != {"questions": 1}:
        raise AssertionError(
            "question-detail crossed catalog relation budget: "
            f"{summary['relation_scan_occurrences']}"
        )
    passed.append("one-catalog-questions-relation-scan")
    if "questions_pkey" not in summary["index_names"]:
        raise AssertionError("question-detail did not use questions_pkey")
    passed.append("questions-primary-key-index-observed")
    if "Seq Scan" in summary["node_type_counts"]:
        raise AssertionError("question-detail unexpectedly used a sequential scan")
    if not ({"Index Scan", "Index Only Scan"} & set(summary["node_type_counts"])):
        raise AssertionError("question-detail did not use an index scan")
    passed.append("selective-index-scan-only")
    if any(value != 0 for value in temp_blocks.values()):
        raise AssertionError(f"question-detail plan spilled to TEMP: {temp_blocks}")
    passed.append("zero-temp-blocks")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise AssertionError("BUFFERS evidence was not emitted")
    passed.append("buffers-captured-before-normalization")
    if (
        execution.get("bound_parameter_count") != 1
        or execution.get("named_parameter_count") != 1
        or execution.get("occurrence_names") != [PARAMETER_NAME]
    ):
        raise AssertionError("question-detail bind surface is not fixed at one")
    parameter = execution.get("parameters", {}).get(PARAMETER_NAME, {})
    if parameter.get("postgres_type") != "bigint":
        raise AssertionError("question-detail bind is not bigint")
    passed.append("one-bigint-bind-one-select-statement")
    return passed


def capture_observation(
    container: str,
    query: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    explain_sql, execution = prepared_execution_sql(
        spec["observation_id"],
        query["sql"],
        spec["question_id"],
        explain=True,
    )
    payload = psql_json(container, explain_sql)
    if not isinstance(payload, list) or len(payload) != 1 or "Plan" not in payload[0]:
        raise RuntimeError("unexpected EXPLAIN FORMAT JSON payload")
    raw_explain = payload[0]
    buffer_fields = collect_numeric_fields(raw_explain, BUFFER_KEYS)
    temp_blocks = {
        key: value
        for key, value in buffer_fields.items()
        if key in {"Temp Read Blocks", "Temp Written Blocks"}
    }
    normalized = normalize_explain(raw_explain)
    summary = summarize_plan(normalized, buffer_fields)
    checks = assert_plan(spec, execution, summary, temp_blocks)
    return {
        "observation_id": spec["observation_id"],
        "runtime_query_id": query["query_id"],
        "question_id": spec["question_id"],
        "expected_rows": spec["expected_rows"],
        "sql_statement_count": 1,
        "binding": execution,
        "temp_blocks_observed": temp_blocks,
        "assertions_passed": checks,
        "plan_summary": summary,
        "normalized_explain_analyze": normalized,
    }


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


def dataset_metadata(container: str) -> dict[str, Any]:
    return psql_json(
        container,
        """
SELECT json_build_object(
    'questions', COUNT(*),
    'minimum_question_id', MIN(id),
    'maximum_question_id', MAX(id),
    'distinct_subject_ids', COUNT(DISTINCT subject_id),
    'distinct_question_types', COUNT(DISTINCT type)
)
FROM questions;
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
        ) ORDER BY indexname
    ),
    '[]'::json
)
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'questions';
""",
    )


def image_metadata(image: str) -> dict[str, Any]:
    raw = run(["docker", "image", "inspect", image]).stdout
    metadata = json.loads(raw)[0]
    expected_digest = image.split("@", 1)[1]
    repo_digests = sorted(metadata.get("RepoDigests", []))
    if not any(value.endswith(expected_digest) for value in repo_digests):
        raise AssertionError(
            f"resolved image lacks expected digest {expected_digest}"
        )
    return {
        "expected_digest": expected_digest,
        "resolved_image_id": metadata.get("Id"),
        "resolved_repo_digests": repo_digests,
        "os": metadata.get("Os"),
        "architecture": metadata.get("Architecture"),
    }


def required_input_paths(root: Path, manifest_path: Path) -> dict[str, Path]:
    return {
        "adapter": root
        / "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "JdbcQuestionDetailQueryAdapter.java",
        "runtime_sql_manifest": manifest_path,
        "runtime_sql_exporter": root
        / "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "QuestionDetailRuntimeSqlManifestTest.java",
        "capture_tool": Path(__file__).resolve(),
        "capture_tool_test": Path(__file__).with_name(
            "test_capture_phase4a_question_detail_query_plan.py"
        ).resolve(),
    }


def capture(
    args: argparse.Namespace,
    container: str,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    query = runtime_query(manifest)
    specs = observation_specs(args)
    observations = [
        capture_observation(container, query, spec) for spec in specs
    ]
    if len(observations) != 5:
        raise AssertionError("question-detail capture must contain five observations")
    bind_counts = {
        item["binding"]["bound_parameter_count"] for item in observations
    }
    statement_counts = {item["sql_statement_count"] for item in observations}
    positional_hashes = {
        item["binding"]["positional_sql_sha256"] for item in observations
    }
    if bind_counts != {1} or statement_counts != {1} or len(positional_hashes) != 1:
        raise AssertionError(
            "question-detail observation bind/statement surface drifted"
        )
    observed_ids = {item["question_id"] for item in observations}
    expected_ids = {
        1,
        max(1, args.question_count // 2),
        args.question_count,
        args.question_count + 1,
        LONG_MAX_VALUE,
    }
    if observed_ids != expected_ids:
        raise AssertionError(
            f"question-detail observation IDs drifted: {sorted(observed_ids)}"
        )

    dataset = dataset_metadata(container)
    if dataset.get("questions") != args.question_count:
        raise AssertionError("question-detail fixture row count drifted")
    if dataset.get("minimum_question_id") != 1:
        raise AssertionError("question-detail fixture minimum ID drifted")
    if dataset.get("maximum_question_id") != args.question_count:
        raise AssertionError("question-detail fixture maximum ID drifted")
    if dataset.get("distinct_subject_ids") != args.subject_count:
        raise AssertionError("question-detail fixture subject distribution drifted")

    indexes = index_definitions(container)
    index_names = {item["name"] for item in indexes}
    if index_names != {"questions_pkey"}:
        raise AssertionError(
            f"question-detail fixture indexes drifted: {sorted(index_names)}"
        )

    root = Path(__file__).resolve().parents[1]
    inputs = required_input_paths(root, manifest_path)
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"question-detail evidence inputs are missing: {missing}")
    input_evidence: dict[str, str] = {}
    for name, path in inputs.items():
        input_evidence[name] = str(path.relative_to(root))
        input_evidence[f"{name}_sha256"] = sha256_file(path)

    fixture = fixture_sql(args)
    image = image_metadata(args.image)
    return {
        "evidence_id": "ti.phase4a.question-detail-query-plan",
        "schema_version": 1,
        "captured_on": "2026-07-16",
        "scope": "catalog-owned-question-detail-internal-read-primitive",
        "route_migration_status": {
            "route_ids": list(ROUTE_IDS),
            "http_owner": "operations",
            "status": "pending",
            "production_cutover": False,
        },
        "runtime_sql_contract": {
            "source": "Java adapter runtime SQL manifest exported before capture",
            "manifest_id": manifest["manifest_id"],
            "manifest_schema_version": manifest["schema_version"],
            "adapter_class": manifest["adapter_class"],
            "query_id": query["query_id"],
            "operation": query["operation"],
            "sql": query["sql"],
            "sql_sha256": sha256_text(query["sql"]),
            "parameter_names": [PARAMETER_NAME],
            "parameter_postgres_types": {PARAMETER_NAME: "bigint"},
            "sql_statement_count": 1,
            "forbidden_runtime_effects": ["DML", "DDL", "TEMP"],
        },
        "environment": {
            "container_image": args.image,
            **image,
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment_metadata(container),
        },
        "inputs": {
            **input_evidence,
            "fixture_sql_sha256": sha256_text(fixture),
        },
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "question_count": args.question_count,
                "subject_count": args.subject_count,
                "question_type_count": 5,
            },
            "actual": dataset,
            "fixture_sql_sha256": sha256_text(fixture),
            "statistics": "VACUUM (ANALYZE) questions completed before capture",
            "index_definitions": indexes,
            "index_decision": (
                "observe the existing questions primary key only; no new "
                "production index is introduced by this evidence"
            ),
        },
        "measurement": {
            "command": (
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) exact Java runtime SQL"
            ),
            "runs_per_observation": 1,
            "observation_count": len(observations),
            "runtime_query_count": 1,
            "sql_statement_count_per_observation": 1,
            "bound_parameter_count_per_observation": 1,
            "required_index": "questions_pkey",
            "required_maximum_actual_loops": 1,
            "observations": observations,
        },
        "normalization": {
            "removed": [
                "planning and execution timing",
                "per-node actual timing",
                "cache-dependent buffer block counts",
                "runtime memory counters",
                "parallel worker identities and counters",
                "container ID and container name",
            ],
            "redacted": [
                "planner filter and index expressions, retaining length and SHA-256"
            ],
            "retained": [
                "plan node types and depth",
                "actual rows and loops",
                "plan row estimates and costs",
                "relation and index names",
                "which BUFFERS fields were emitted",
            ],
        },
        "interpretation": {
            "status": "observational_evidence_only",
            "statement": (
                "This isolated PostgreSQL 18.4 synthetic capture proves five "
                "single-bind primary-key observations for the exact Java runtime "
                "SQL. It is not a production latency or capacity SLA."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/"
                "capture_phase4a_question_detail_query_plan.py --output "
                "Ti-Java/docs/refactor/phase4a/"
                "question-detail-query-plan-evidence.json"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": (
                "ephemeral network-disabled container removed on success or failure"
            ),
        },
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    if shutil.which("docker") is None:
        raise SystemExit("docker is required")
    root = Path(__file__).resolve().parents[1]
    manifest_path = args.runtime_sql_manifest.resolve()
    export_runtime_sql_manifest(root, manifest_path)
    manifest = load_runtime_sql_manifest(manifest_path)
    container = "ti-phase4a-question-detail-plan-" + uuid.uuid4().hex[:12]
    started = False
    try:
        result = run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                container,
                "--network",
                "none",
                "--env",
                "POSTGRES_PASSWORD=postgres",
                "--env",
                f"POSTGRES_DB={DEFAULT_DATABASE}",
                args.image,
            ],
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"could not start PostgreSQL: {result.stderr.strip()[-3000:]}"
            )
        started = True
        wait_until_ready(container, args.startup_timeout_seconds)
        psql(container, fixture_sql(args))
        document = capture(args, container, manifest, manifest_path)
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            "captured question-detail plans "
            f"observations={document['measurement']['observation_count']} "
            f"sql_sha256={document['runtime_sql_contract']['sql_sha256']}"
        )
        return 0
    finally:
        if started:
            run(["docker", "rm", "--force", container], check=False)
        if run(["docker", "inspect", container], check=False).returncode == 0:
            raise RuntimeError(
                f"temporary PostgreSQL container was not removed: {container}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
