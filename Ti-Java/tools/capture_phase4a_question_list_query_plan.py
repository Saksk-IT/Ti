#!/usr/bin/env python3
"""Capture deterministic PG18 evidence for catalog question-summary lists.

The four SELECT statements are exported from the Java JDBC adapter before each
capture.  This tool owns only a public synthetic fixture, typed bindings,
result-order checks, plan normalization, and fail-closed evidence assertions.
It never keeps a handwritten copy of production runtime SQL.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
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
DEFAULT_DATABASE = "phase4a_question_list_plan"
DEFAULT_QUESTION_COUNT = 150_000
DEFAULT_SUBJECT_COUNT = 5_000
QUESTION_TYPES = (
    "single_choice",
    "multi_choice",
    "boolean",
    "fill",
    "essay",
)

MANIFEST_ID = "ti.phase4a.question-list-runtime-sql"
ADAPTER_CLASS = (
    "io.saksk.ti.catalog.infrastructure.persistence."
    "JdbcQuestionSummaryQueryAdapter"
)
OPERATION = "question-list"
EXPECTED_QUERY_ORDER = (
    "question-summaries-all",
    "question-summaries-by-subject",
    "question-summaries-by-type",
    "question-summaries-by-subject-and-type",
)
EXPECTED_PARAMETER_TYPES = {
    "question-summaries-all": {},
    "question-summaries-by-subject": {"subject_id": "integer"},
    "question-summaries-by-type": {"question_type": "text"},
    "question-summaries-by-subject-and-type": {
        "subject_id": "integer",
        "question_type": "text",
    },
}
EXPECTED_COLUMNS = (
    "q.id",
    "q.subject_id",
    "q.type",
    "q.content",
    "q.difficulty",
    "q.tags",
    "q.image_path",
    "q.created_by",
    "q.updated_at",
)
EXPECTED_NORMALIZED_SQL = {
    "question-summaries-all": (
        f"select {', '.join(EXPECTED_COLUMNS)} from questions q "
        "order by q.id desc"
    ),
    "question-summaries-by-subject": (
        f"select {', '.join(EXPECTED_COLUMNS)} from questions q "
        "where q.subject_id = :subject_id order by q.id desc"
    ),
    "question-summaries-by-type": (
        f"select {', '.join(EXPECTED_COLUMNS)} from questions q "
        "where q.type = :question_type order by q.id desc"
    ),
    "question-summaries-by-subject-and-type": (
        f"select {', '.join(EXPECTED_COLUMNS)} from questions q "
        "where q.subject_id = :subject_id and q.type = :question_type "
        "order by q.id desc"
    ),
}

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
PLANNER_ESTIMATE_KEYS = {
    "Startup Cost",
    "Total Cost",
    "Plan Rows",
    "Plan Width",
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
        description="Capture Java-exported Phase 4A question-list plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root
        / "docs/refactor/phase4a/question-list-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-question-list-runtime-sql.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--question-count", type=int, default=DEFAULT_QUESTION_COUNT
    )
    parser.add_argument(
        "--subject-count", type=int, default=DEFAULT_SUBJECT_COUNT
    )
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
            "-Dtest=QuestionListRuntimeSqlManifestTest",
            f"-Dti.question-list.sql-manifest-output={output}",
            "test",
        ],
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java runtime SQL export failed: {detail}")


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).lower()


def validate_runtime_sql(query_id: str, sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError(f"runtime SQL is empty for {query_id}")
    if query_id not in EXPECTED_NORMALIZED_SQL:
        raise RuntimeError(f"unknown question-list runtime query: {query_id}")
    if ";" in stripped:
        raise RuntimeError(
            f"runtime SQL contains a statement separator: {query_id}"
        )
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError(f"runtime SQL must contain exactly one SELECT: {query_id}")
    forbidden = FORBIDDEN_RUNTIME_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(
            f"runtime SQL contains forbidden token {forbidden.group(0)}: "
            f"{query_id}"
        )
    if re.search(r"\bpg_temp\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL references pg_temp: {query_id}")
    if re.search(r"\bjoin\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL must not join another relation: {query_id}")
    if re.search(
        r"\bselect\s+(?:(?:[A-Za-z][A-Za-z0-9_]*)\.)?\*",
        stripped,
        re.IGNORECASE,
    ):
        raise RuntimeError(
            f"runtime SQL must use nine explicit question columns: {query_id}"
        )
    actual = normalize_sql(stripped)
    expected = EXPECTED_NORMALIZED_SQL[query_id]
    if actual != expected:
        raise RuntimeError(
            f"runtime SQL shape drifted for {query_id}: {actual}"
        )


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java runtime SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID:
        raise RuntimeError("question-list runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("question-list runtime SQL manifest schema drifted")
    if manifest.get("adapter_class") != ADAPTER_CLASS:
        raise RuntimeError("question-list runtime SQL adapter class drifted")
    queries = manifest.get("queries")
    if (
        not isinstance(queries, list)
        or manifest.get("query_count") != 4
        or len(queries) != 4
    ):
        raise RuntimeError("question-list runtime SQL manifest must contain four queries")
    actual_order: list[str] = []
    for query in queries:
        if not isinstance(query, dict):
            raise RuntimeError("question-list runtime SQL query must be an object")
        query_id = query.get("query_id")
        if not isinstance(query_id, str) or query_id in actual_order:
            raise RuntimeError(f"invalid or duplicate runtime query ID: {query_id}")
        actual_order.append(query_id)
        if query.get("operation") != OPERATION:
            raise RuntimeError(f"runtime query operation drifted: {query_id}")
        sql = query.get("sql")
        parameters = query.get("parameters")
        if not isinstance(sql, str) or not isinstance(parameters, dict):
            raise RuntimeError(f"runtime query shape drifted: {query_id}")
        validate_runtime_sql(query_id, sql)
        expected_parameters = EXPECTED_PARAMETER_TYPES[query_id]
        if parameters != expected_parameters:
            raise RuntimeError(
                f"runtime parameter types drifted for {query_id}: {parameters}"
            )
        occurrences = NAMED_PARAMETER.findall(sql)
        if set(occurrences) != set(parameters) or len(occurrences) != len(parameters):
            raise RuntimeError(
                f"runtime SQL parameter surface drifted for {query_id}: "
                f"occurrences={occurrences} declared={sorted(parameters)}"
            )
    if tuple(actual_order) != EXPECTED_QUERY_ORDER:
        raise RuntimeError(f"runtime query order drifted: {actual_order}")
    return manifest


def manifest_queries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {query["query_id"]: query for query in manifest["queries"]}


def subject_for(question_id: int, subject_count: int) -> Optional[int]:
    if question_id == -1:
        return 1
    if question_id == 0:
        return None
    if question_id % 997 == 0:
        return None
    return ((question_id - 1) % subject_count) + 1


def question_type_for(question_id: int) -> str:
    if question_id == -1:
        return "essay"
    if question_id == 0:
        return "fill"
    return QUESTION_TYPES[(question_id - 1) % len(QUESTION_TYPES)]


def expected_result(
    question_count: int,
    subject_count: int,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    first_ascending: list[int] = []
    last_ascending: deque[int] = deque(maxlen=3)
    count = 0
    for question_id in range(-1, question_count - 1):
        subject_id = subject_for(question_id, subject_count)
        question_type = question_type_for(question_id)
        if "subject_id" in parameters and subject_id != parameters["subject_id"]:
            continue
        if (
            "question_type" in parameters
            and question_type != parameters["question_type"]
        ):
            continue
        count += 1
        if len(first_ascending) < 3:
            first_ascending.append(question_id)
        last_ascending.append(question_id)
    return {
        "row_count": count,
        "minimum_id": first_ascending[0] if count else None,
        "maximum_id": last_ascending[-1] if count else None,
        "first_ids_desc": list(reversed(last_ascending)),
        "last_ids_desc": list(reversed(first_ascending)),
    }


def observation_specs(args: argparse.Namespace) -> list[dict[str, Any]]:
    raw_specs = [
        ("all-questions", "question-summaries-all", {}),
        (
            "existing-subject",
            "question-summaries-by-subject",
            {"subject_id": 1},
        ),
        (
            "missing-subject",
            "question-summaries-by-subject",
            {"subject_id": args.subject_count + 1},
        ),
        (
            "negative-subject",
            "question-summaries-by-subject",
            {"subject_id": -1},
        ),
        (
            "common-question-type",
            "question-summaries-by-type",
            {"question_type": QUESTION_TYPES[0]},
        ),
        (
            "unknown-question-type",
            "question-summaries-by-type",
            {"question_type": "unknown_type"},
        ),
        (
            "empty-question-type",
            "question-summaries-by-type",
            {"question_type": ""},
        ),
        (
            "matching-subject-and-type",
            "question-summaries-by-subject-and-type",
            {"subject_id": 1, "question_type": QUESTION_TYPES[0]},
        ),
        (
            "mismatching-subject-and-type",
            "question-summaries-by-subject-and-type",
            {"subject_id": 1, "question_type": QUESTION_TYPES[2]},
        ),
    ]
    return [
        {
            "observation_id": observation_id,
            "runtime_query_id": query_id,
            "parameters": parameters,
            "expected": expected_result(
                args.question_count, args.subject_count, parameters
            ),
        }
        for observation_id, query_id, parameters in raw_specs
    ]


def bound_parameter(name: str, value: Any) -> dict[str, Any]:
    if name == "subject_id":
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < -2_147_483_648
            or value > 2_147_483_647
        ):
            raise RuntimeError("subject_id binding must fit a signed integer")
        return {
            "bind_kind": "jdbc-scalar",
            "postgres_type": "integer",
            "value": value,
        }
    if name == "question_type":
        if not isinstance(value, str):
            raise RuntimeError("question_type binding must be text")
        return {
            "bind_kind": "jdbc-scalar",
            "postgres_type": "text",
            "value": value,
        }
    raise RuntimeError(f"unsupported question-list parameter: {name}")


def postgres_literal(parameter: dict[str, Any]) -> str:
    value = parameter["value"]
    if parameter["postgres_type"] == "integer":
        return str(value)
    if parameter["postgres_type"] == "text":
        return "'" + value.replace("'", "''") + "'"
    raise RuntimeError(f"unsupported PostgreSQL parameter: {parameter}")


def prepared_execution_sql(
    observation_id: str,
    query: dict[str, Any],
    parameter_values: dict[str, Any],
    *,
    explain: bool,
) -> tuple[str, dict[str, Any]]:
    query_id = query["query_id"]
    sql = query["sql"]
    validate_runtime_sql(query_id, sql)
    if set(parameter_values) != set(query["parameters"]):
        raise RuntimeError(
            f"parameter values drifted for {query_id}: {sorted(parameter_values)}"
        )
    bound = {
        name: bound_parameter(name, value)
        for name, value in parameter_values.items()
    }
    occurrences: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in bound:
            raise RuntimeError(f"undeclared runtime parameter :{name}")
        occurrences.append(name)
        return f"${len(occurrences)}"

    positional_sql = NAMED_PARAMETER.sub(replace, sql)
    if len(occurrences) != len(bound) or set(occurrences) != set(bound):
        raise RuntimeError(f"question-list bind surface drifted: {occurrences}")
    positional_parameters = [bound[name] for name in occurrences]
    postgres_types = [item["postgres_type"] for item in positional_parameters]
    literals = [postgres_literal(item) for item in positional_parameters]
    statement_name = "ql_" + re.sub(
        r"[^a-z0-9_]", "_", observation_id.lower()
    )
    statement_name = statement_name[:44] + "_" + sha256_text(observation_id)[:8]
    prepare_types = f" ({','.join(postgres_types)})" if postgres_types else ""
    execute_values = f" ({','.join(literals)})" if literals else ""
    prefix = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" if explain else ""
    execution_sql = (
        f"PREPARE {statement_name}{prepare_types} AS\n{positional_sql};\n"
        f"{prefix}EXECUTE {statement_name}{execute_values};\n"
        f"DEALLOCATE {statement_name};"
    )
    return execution_sql, {
        "mode": "prepare-execute",
        "bound_parameter_count": len(occurrences),
        "named_parameter_count": len(bound),
        "occurrence_names": occurrences,
        "positional_sql_sha256": sha256_text(positional_sql),
        "parameters": bound,
    }


def psql(container: str, sql: str, *, field_separator: str = "|") -> str:
    result = run(
        [
            "docker",
            "exec",
            "--interactive",
            "--env=PGOPTIONS=-c max_parallel_workers_per_gather=0 -c work_mem=64MB",
            container,
            "psql",
            "--username=postgres",
            f"--dbname={DEFAULT_DATABASE}",
            "--no-psqlrc",
            "--quiet",
            "--tuples-only",
            "--no-align",
            f"--field-separator={field_separator}",
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
CREATE TABLE subjects (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE questions (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    subject_id integer,
    type text NOT NULL,
    content text NOT NULL,
    difficulty integer,
    tags text,
    image_path text,
    created_by integer,
    updated_at timestamp
);

INSERT INTO subjects (id, name)
SELECT n, 'Synthetic subject ' || n
FROM generate_series(1, {args.subject_count}) AS generated(n);

INSERT INTO questions (
    id, subject_id, type, content, difficulty, tags, image_path,
    created_by, updated_at
)
SELECT n,
       CASE
           WHEN n = -1 THEN 1
           WHEN n = 0 THEN NULL
           WHEN n % 997 = 0 THEN NULL
           ELSE ((n - 1) % {args.subject_count}) + 1
       END,
       CASE
           WHEN n = -1 THEN 'essay'
           WHEN n = 0 THEN 'fill'
           ELSE (ARRAY[
               'single_choice', 'multi_choice', 'boolean', 'fill', 'essay'
           ])[1 + ((n - 1) % 5)]
       END,
       'Synthetic question ' || n,
       CASE
           WHEN n = 0 OR n % 1009 = 0 THEN NULL
           WHEN n = -1 THEN 1
           ELSE 1 + ((n - 1) % 5)
       END,
       CASE
           WHEN n % 1013 = 0 THEN NULL
           WHEN n % 499 = 0 THEN 'raw-synthetic-tag'
           ELSE '["synthetic"]'
       END,
       CASE
           WHEN n % 1019 = 0 THEN '["/synthetic/question.png"]'
           WHEN n % 503 = 0 THEN '/synthetic/question.png'
           ELSE NULL
       END,
       CASE WHEN n % 3 = 0 THEN 100000 + (n % 1000) END,
       timestamp '2026-01-02 00:00:00' + (n * interval '1 second')
FROM generate_series(-1, {args.question_count - 2}) AS generated(n);

-- TEST-ONLY synthetic indexes. Their names mirror observed legacy migrations;
-- this fixture does not approve or create a production index.
CREATE INDEX ix_questions_subject_id ON questions (subject_id);
CREATE INDEX ix_questions_subject_type ON questions (subject_id, type);

-- Force full-table deterministic statistics for this bounded 150k fixture so
-- repeated captures do not straddle equivalent planner cost choices.
ALTER TABLE questions ALTER COLUMN subject_id SET STATISTICS 10000;
ALTER TABLE questions ALTER COLUMN type SET STATISTICS 10000;

VACUUM (ANALYZE) subjects;
VACUUM (ANALYZE) questions;
"""


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
        if (
            key in TIMING_KEYS
            or key in BUFFER_KEYS
            or key in MEMORY_KEYS
            or key in PLANNER_ESTIMATE_KEYS
        ):
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
            "Sort Key",
            "Sort Method",
            "Actual Rows",
            "Actual Loops",
            "Rows Removed by Filter",
            "Index Cond",
            "Filter",
            "Recheck Cond",
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


def parse_result_rows(raw: str, expected: dict[str, Any]) -> dict[str, Any]:
    lines = [line for line in raw.splitlines() if line]
    ids: list[int] = []
    for line in lines:
        fields = line.split("|")
        if len(fields) != len(EXPECTED_COLUMNS):
            raise AssertionError(
                f"runtime result column count drifted: {len(fields)}"
            )
        if not re.fullmatch(r"-?[0-9]+", fields[0]):
            raise AssertionError(f"runtime result ID is not an integer: {fields[0]}")
        ids.append(int(fields[0]))
    strictly_descending = all(
        previous > current for previous, current in zip(ids, ids[1:])
    )
    actual = {
        "row_count": len(ids),
        "minimum_id": ids[-1] if ids else None,
        "maximum_id": ids[0] if ids else None,
        "first_ids_desc": ids[:3],
        "last_ids_desc": ids[-3:],
        "strictly_descending_by_id": strictly_descending,
        "row_column_count": len(EXPECTED_COLUMNS),
        "canonical_psql_rows_sha256": sha256_text(raw),
    }
    for key in (
        "row_count",
        "minimum_id",
        "maximum_id",
        "first_ids_desc",
        "last_ids_desc",
    ):
        if actual[key] != expected[key]:
            raise AssertionError(
                f"runtime result boundary drifted for {key}: "
                f"actual={actual[key]} expected={expected[key]}"
            )
    if len(ids) > 1 and not strictly_descending:
        raise AssertionError("runtime results are not strictly ordered by id DESC")
    return actual


def assert_plan(
    spec: dict[str, Any],
    execution: dict[str, Any],
    result_summary: dict[str, Any],
    summary: dict[str, Any],
    temp_blocks: dict[str, float],
) -> list[str]:
    passed: list[str] = []
    expected_rows = spec["expected"]["row_count"]
    if result_summary["row_count"] != expected_rows:
        raise AssertionError("question-list result row count drifted")
    if summary["result_row_count"] != expected_rows:
        raise AssertionError(
            f"{spec['observation_id']} plan rows "
            f"{summary['result_row_count']}; expected {expected_rows}"
        )
    passed.append("expected-result-count-and-boundaries")
    if not result_summary["strictly_descending_by_id"] and expected_rows > 1:
        raise AssertionError("question-list ordering is not strictly id DESC")
    passed.append("strict-id-desc-runtime-order")
    if summary["root_actual_loops"] != 1 or summary["maximum_actual_loops"] != 1:
        raise AssertionError("question-list plan must execute every node once")
    passed.append("single-execution-no-row-driven-loop")
    if summary["node_count"] > 8 or summary["maximum_depth"] > 4:
        raise AssertionError("question-list plan exceeded node/depth bounds")
    passed.append("bounded-plan-shape")
    relations = summary["relation_scan_occurrences"]
    if relations != {"questions": 1}:
        raise AssertionError(
            "question-list crossed catalog relation budget or scanned questions "
            f"more than once: {relations}"
        )
    passed.append("questions-once-users-subjects-zero")
    if any(value != 0 for value in temp_blocks.values()):
        raise AssertionError(f"question-list plan spilled to TEMP: {temp_blocks}")
    passed.append("zero-temp-blocks")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise AssertionError("BUFFERS evidence was not emitted")
    passed.append("buffers-captured-before-normalization")
    expected_parameters = EXPECTED_PARAMETER_TYPES[spec["runtime_query_id"]]
    if (
        execution["bound_parameter_count"] != len(expected_parameters)
        or execution["named_parameter_count"] != len(expected_parameters)
        or set(execution["occurrence_names"]) != set(expected_parameters)
    ):
        raise AssertionError("question-list bind surface drifted")
    passed.append("one-select-fixed-bind-cardinality")
    return passed


def capture_observation(
    container: str,
    query: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result_sql, result_execution = prepared_execution_sql(
        spec["observation_id"],
        query,
        spec["parameters"],
        explain=False,
    )
    raw_rows = psql(container, result_sql)
    result_summary = parse_result_rows(raw_rows, spec["expected"])

    explain_sql, execution = prepared_execution_sql(
        spec["observation_id"],
        query,
        spec["parameters"],
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
    if result_execution != execution:
        raise AssertionError("result and EXPLAIN binding metadata drifted")
    checks = assert_plan(spec, execution, result_summary, summary, temp_blocks)
    return {
        "observation_id": spec["observation_id"],
        "runtime_query_id": query["query_id"],
        "expected": spec["expected"],
        "runtime_result": result_summary,
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
    'questions', (SELECT COUNT(*) FROM questions),
    'subjects', (SELECT COUNT(*) FROM subjects),
    'minimum_question_id', (SELECT MIN(id) FROM questions),
    'maximum_question_id', (SELECT MAX(id) FROM questions),
    'distinct_assigned_subject_ids',
        (SELECT COUNT(DISTINCT subject_id) FROM questions),
    'distinct_question_types', (SELECT COUNT(DISTINCT type) FROM questions),
    'null_subject_rows',
        (SELECT COUNT(*) FROM questions WHERE subject_id IS NULL),
    'null_difficulty_rows',
        (SELECT COUNT(*) FROM questions WHERE difficulty IS NULL),
    'null_tags_rows',
        (SELECT COUNT(*) FROM questions WHERE tags IS NULL),
    'null_image_path_rows',
        (SELECT COUNT(*) FROM questions WHERE image_path IS NULL),
    'null_created_by_rows',
        (SELECT COUNT(*) FROM questions WHERE created_by IS NULL)
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
  AND tablename IN ('questions', 'subjects');
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
        "JdbcQuestionSummaryQueryAdapter.java",
        "runtime_sql_manifest": manifest_path,
        "runtime_sql_exporter": root
        / "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "QuestionListRuntimeSqlManifestTest.java",
        "capture_tool": Path(__file__).resolve(),
        "capture_tool_test": Path(__file__).with_name(
            "test_capture_phase4a_question_list_query_plan.py"
        ).resolve(),
    }


def input_evidence(root: Path, manifest_path: Path) -> dict[str, str]:
    paths = required_input_paths(root, manifest_path)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"question-list evidence inputs are missing: {missing}")
    evidence: dict[str, str] = {}
    for name, path in paths.items():
        evidence[name] = str(path.relative_to(root))
        evidence[f"{name}_sha256"] = sha256_file(path)
    return evidence


def assert_input_hash_closure(
    recorded: dict[str, str], paths: dict[str, Path]
) -> None:
    for name, path in paths.items():
        expected = recorded.get(f"{name}_sha256")
        actual = sha256_file(path)
        if expected != actual:
            raise AssertionError(
                f"question-list evidence source drifted: {name} "
                f"recorded={expected} actual={actual}"
            )


def assert_runtime_sql_hash_closure(
    recorded: dict[str, str], manifest: dict[str, Any]
) -> None:
    queries = manifest_queries(manifest)
    if set(recorded) != set(EXPECTED_QUERY_ORDER):
        raise AssertionError("question-list recorded runtime SQL hash keys drifted")
    for query_id in EXPECTED_QUERY_ORDER:
        actual = sha256_text(queries[query_id]["sql"])
        if recorded.get(query_id) != actual:
            raise AssertionError(
                f"question-list runtime SQL hash drifted: {query_id}"
            )


def assert_public_evidence(document: dict[str, Any]) -> None:
    serialized = json.dumps(document, ensure_ascii=False, sort_keys=True)
    forbidden_values = (
        "/Users/",
        "/private/",
        "POSTGRES_PASSWORD",
        "PUBLIC-TEST-ONLY",
        "ti-phase4a-question-list-plan-",
    )
    leaks = [value for value in forbidden_values if value in serialized]
    if leaks:
        raise AssertionError(f"question-list evidence leaked private values: {leaks}")

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower().replace("-", "_")
                if any(
                    marker in normalized
                    for marker in ("password", "secret", "api_key", "access_token")
                ):
                    raise AssertionError(
                        f"question-list evidence contains a sensitive key: {key}"
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)


def capture(
    args: argparse.Namespace,
    container: str,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    queries = manifest_queries(manifest)
    specs = observation_specs(args)
    observations = [
        capture_observation(container, queries[spec["runtime_query_id"]], spec)
        for spec in specs
    ]
    if len(observations) < 9:
        raise AssertionError("question-list capture requires at least nine observations")
    covered = {item["runtime_query_id"] for item in observations}
    if covered != set(EXPECTED_QUERY_ORDER):
        raise AssertionError(f"question-list runtime variant coverage drifted: {covered}")
    bind_counts = {
        query_id: sorted(
            {
                item["binding"]["bound_parameter_count"]
                for item in observations
                if item["runtime_query_id"] == query_id
            }
        )
        for query_id in EXPECTED_QUERY_ORDER
    }
    expected_bind_counts = {
        query_id: [len(EXPECTED_PARAMETER_TYPES[query_id])]
        for query_id in EXPECTED_QUERY_ORDER
    }
    if bind_counts != expected_bind_counts:
        raise AssertionError(f"question-list bind cardinality drifted: {bind_counts}")
    if {item["sql_statement_count"] for item in observations} != {1}:
        raise AssertionError("question-list SQL statement count drifted")

    dataset = dataset_metadata(container)
    expected_dataset = {
        "questions": args.question_count,
        "subjects": args.subject_count,
        "minimum_question_id": -1,
        "maximum_question_id": args.question_count - 2,
        "distinct_assigned_subject_ids": args.subject_count,
        "distinct_question_types": len(QUESTION_TYPES),
    }
    for key, expected in expected_dataset.items():
        if dataset.get(key) != expected:
            raise AssertionError(
                f"question-list fixture {key} drifted: {dataset.get(key)}"
            )
    for key in (
        "null_subject_rows",
        "null_difficulty_rows",
        "null_tags_rows",
        "null_image_path_rows",
        "null_created_by_rows",
    ):
        if not isinstance(dataset.get(key), int) or dataset[key] <= 0:
            raise AssertionError(f"question-list fixture lost sparse null data: {key}")

    indexes = index_definitions(container)
    index_names = {item["name"] for item in indexes}
    expected_indexes = {
        "subjects_pkey",
        "questions_pkey",
        "ix_questions_subject_id",
        "ix_questions_subject_type",
    }
    if index_names != expected_indexes:
        raise AssertionError(
            f"question-list synthetic fixture indexes drifted: {sorted(index_names)}"
        )

    root = Path(__file__).resolve().parents[1]
    fixture = fixture_sql(args)
    runtime_hashes = {
        query_id: sha256_text(queries[query_id]["sql"])
        for query_id in EXPECTED_QUERY_ORDER
    }
    inputs = input_evidence(root, manifest_path)
    document = {
        "evidence_id": "ti.phase4a.question-list-query-plan",
        "schema_version": 1,
        "captured_on": "2026-07-16",
        "scope": "catalog-owned-question-summary-list-internal-read-primitive",
        "runtime_sql_contract": {
            "source": "Java adapter runtime SQL manifest exported before capture",
            "manifest_id": manifest["manifest_id"],
            "manifest_schema_version": manifest["schema_version"],
            "adapter_class": manifest["adapter_class"],
            "query_ids_in_manifest_order": list(EXPECTED_QUERY_ORDER),
            "operation": OPERATION,
            "explicit_question_column_count": len(EXPECTED_COLUMNS),
            "explicit_question_columns": list(EXPECTED_COLUMNS),
            "fixed_order": "q.id DESC",
            "query_sql_sha256": runtime_hashes,
            "parameter_postgres_types": EXPECTED_PARAMETER_TYPES,
            "sql_statement_count_per_execution": 1,
            "relation_budget": {
                "questions": 1,
                "users": 0,
                "subjects": 0,
                "joins": 0,
            },
            "forbidden_runtime_effects": ["DML", "DDL", "TEMP"],
        },
        "environment": {
            "container_image": args.image,
            **image_metadata(args.image),
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment_metadata(container),
            "deterministic_session_settings": {
                "max_parallel_workers_per_gather": 0,
                "work_mem": "64MB",
            },
        },
        "inputs": {
            **inputs,
            "fixture_sql_sha256": sha256_text(fixture),
        },
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "question_count": args.question_count,
                "subject_count": args.subject_count,
                "question_id_range": [-1, args.question_count - 2],
                "question_types": list(QUESTION_TYPES),
                "type_distribution": "uniform by question ID modulo five",
                "raw_and_null_distribution": "fixed sparse public modulo rules",
            },
            "actual": dataset,
            "fixture_sql_sha256": sha256_text(fixture),
            "statistics": "VACUUM (ANALYZE) completed before capture",
            "deterministic_statistics": (
                "subject_id and type use test-only statistics target 10000 so the "
                "bounded fixture is analyzed in full"
            ),
            "index_definitions": indexes,
            "index_boundary": {
                "status": "test_only_synthetic_observation",
                "statement": (
                    "The fixture creates ix_questions_subject_id and "
                    "ix_questions_subject_type only to observe PG18.4 plan choices. "
                    "Their presence and use are not approval of a production index."
                ),
                "production_index_state": "unknown_not_asserted",
                "production_migration_added": False,
            },
        },
        "measurement": {
            "command": (
                "execute and EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) each exact "
                "Java runtime SELECT"
            ),
            "runs_per_observation": 1,
            "observation_count": len(observations),
            "runtime_query_count": len(EXPECTED_QUERY_ORDER),
            "sql_statement_count_per_execution": 1,
            "required_maximum_actual_loops": 1,
            "required_temp_blocks": 0,
            "observations": observations,
        },
        "cross_observation_assertions": {
            "status": "passed",
            "runtime_variant_coverage": list(EXPECTED_QUERY_ORDER),
            "bound_parameter_counts_by_runtime_query": bind_counts,
            "expected_bound_parameter_counts_by_runtime_query": expected_bind_counts,
            "bind_count_independent_of_result_row_count": True,
            "questions_relation_scans_per_observation": 1,
            "users_relation_scans_per_observation": 0,
            "subjects_relation_scans_per_observation": 0,
            "strict_id_desc_all_nontrivial_results": True,
            "zero_temp_blocks_all_observations": True,
        },
        "normalization": {
            "removed": [
                "planning and execution timing",
                "per-node actual timing",
                "cache-dependent buffer block counts",
                "runtime memory counters",
                "sample-dependent planner costs and row estimates",
                "parallel worker identities and counters",
                "container ID and container name",
            ],
            "redacted": [
                "planner filter and index expressions, retaining length and SHA-256"
            ],
            "retained": [
                "plan node types and depth",
                "actual rows and loops",
                "relation and observed index names",
                "scan direction and sort shape",
                "which BUFFERS fields were emitted",
            ],
        },
        "interpretation": {
            "status": "bounded_synthetic_plan_evidence_only",
            "statement": (
                "This isolated PostgreSQL 18.4 capture closes row counts, ID "
                "boundaries, strict descending order, fixed bind counts, one "
                "questions scan, zero users/subjects scans, and zero TEMP for the "
                "exact Java SQL. It is not a production latency, capacity, or "
                "index-approval claim."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/"
                "capture_phase4a_question_list_query_plan.py --output "
                "Ti-Java/docs/refactor/phase4a/"
                "question-list-query-plan-evidence.json"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": (
                "ephemeral network-disabled container removed on success or failure"
            ),
        },
    }
    assert_input_hash_closure(inputs, required_input_paths(root, manifest_path))
    assert_runtime_sql_hash_closure(runtime_hashes, manifest)
    assert_public_evidence(document)
    return document


def write_json_atomic(output: Path, document: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def cleanup_container(container: str) -> None:
    run(["docker", "rm", "--force", container], check=False)
    if run(["docker", "inspect", container], check=False).returncode == 0:
        raise RuntimeError(
            f"temporary PostgreSQL container was not removed: {container}"
        )


def main() -> int:
    args = parse_args()
    validate_args(args)
    if shutil.which("docker") is None:
        raise SystemExit("docker is required")
    root = Path(__file__).resolve().parents[1]
    manifest_path = args.runtime_sql_manifest.resolve()
    export_runtime_sql_manifest(root, manifest_path)
    manifest = load_runtime_sql_manifest(manifest_path)
    container = "ti-phase4a-question-list-plan-" + uuid.uuid4().hex[:12]
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
                "POSTGRES_PASSWORD=PUBLIC-TEST-ONLY-question-list",
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
        write_json_atomic(output, document)
        print(
            "captured question-list plans "
            f"observations={document['measurement']['observation_count']} "
            f"sha256={sha256_file(output)}"
        )
        return 0
    finally:
        if started:
            cleanup_container(container)


if __name__ == "__main__":
    raise SystemExit(main())
