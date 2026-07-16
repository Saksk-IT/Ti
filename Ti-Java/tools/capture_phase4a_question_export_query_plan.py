#!/usr/bin/env python3
"""Capture deterministic PG18.4 evidence for question-export snapshots.

Both runtime SELECT statements are exported from the Java JDBC adapter before
every live capture.  This file keeps only validation constants plus a public
synthetic fixture, typed-bind execution, exact-result checks, plan
normalization, and fail-closed evidence assertions.  The exported manifest is
the sole executable source of production runtime SQL used by the capture.
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
DEFAULT_DATABASE = "phase4a_question_export_plan"
DEFAULT_QUESTION_COUNT = 150_000
DEFAULT_SUBJECT_COUNT = 5_000
NULL_MARKER = "<PG-NULL>"
QUESTION_TYPES = (
    "single_choice",
    "multi_choice",
    "boolean",
    "fill",
    "essay",
)

MANIFEST_ID = "ti.phase4a.question-export-runtime-sql"
ADAPTER_CLASS = (
    "io.saksk.ti.catalog.infrastructure.persistence."
    "JdbcQuestionExportQueryAdapter"
)
OPERATION = "question-export-snapshot"
EXPECTED_QUERY_ORDER = (
    "question-export-all",
    "question-export-by-subject",
)
EXPECTED_PARAMETER_TYPES = {
    "question-export-all": {},
    "question-export-by-subject": {"subject_id": "integer"},
}
EXPECTED_COLUMNS = (
    "q.id",
    "q.subject_id",
    "s.name as subject_name",
    "q.type",
    "q.content",
    "q.options",
    "q.answer",
    "q.analysis",
    "q.difficulty",
    "q.tags",
)
# Validation-only copies. Live execution always reads SQL from the Java export.
EXPECTED_NORMALIZED_SQL = {
    "question-export-all": (
        f"select {', '.join(EXPECTED_COLUMNS)} from questions q "
        "left join subjects s on q.subject_id = s.id order by q.id asc"
    ),
    "question-export-by-subject": (
        f"select {', '.join(EXPECTED_COLUMNS)} from questions q "
        "left join subjects s on q.subject_id = s.id "
        "where q.subject_id = :subject_id order by q.id asc"
    ),
}

NAMED_PARAMETER = re.compile(r"(?<!:):([A-Za-z][A-Za-z0-9_]*)")
FORBIDDEN_RUNTIME_SQL = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|copy|call|do|"
    r"vacuum|analyze|refresh|grant|revoke|temporary|temp|reindex|cluster|"
    r"comment|set|reset|show|lock)\b",
    re.IGNORECASE,
)
FORBIDDEN_QUERY_SHAPE = re.compile(
    r"\b(?:limit|offset|fetch|union|intersect|except|into)\b",
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
    "Hash Buckets",
    "Original Hash Buckets",
    "Hash Batches",
    "Original Hash Batches",
    "Disk Usage",
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
    "Sort Key",
}
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "secret",
    "authorization",
    "credential",
    "cookie",
    "private_key",
    "api_key",
    "access_token",
    "refresh_token",
    "dsn",
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported Phase 4A question-export plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root
        / "docs/refactor/phase4a/question-export-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-question-export-runtime-sql.json",
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
    if args.subject_count > 2_147_482_646:
        raise ValueError("--subject-count leaves no signed-integer orphan ID")
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


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(payload)


def export_runtime_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("runtime SQL manifest must stay under server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = run(
        [
            str(verifier),
            "-q",
            "-DskipITs",
            "-Dtest=QuestionExportRuntimeSqlManifestTest",
            f"-Dti.question-export.sql-manifest-output={output}",
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
        raise RuntimeError(f"question-export runtime SQL is empty: {query_id}")
    if query_id not in EXPECTED_NORMALIZED_SQL:
        raise RuntimeError(f"unknown question-export runtime query: {query_id}")
    if ";" in stripped:
        raise RuntimeError(
            f"question-export runtime SQL contains a separator: {query_id}"
        )
    if "--" in stripped or "/*" in stripped or "*/" in stripped:
        raise RuntimeError(
            f"question-export runtime SQL contains a comment: {query_id}"
        )
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError(
            f"question-export runtime SQL must contain one SELECT: {query_id}"
        )
    forbidden = FORBIDDEN_RUNTIME_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(
            "question-export runtime SQL contains forbidden token "
            f"{forbidden.group(0)}: {query_id}"
        )
    forbidden_shape = FORBIDDEN_QUERY_SHAPE.search(stripped)
    if forbidden_shape:
        raise RuntimeError(
            "question-export runtime SQL contains forbidden query shape "
            f"{forbidden_shape.group(0)}: {query_id}"
        )
    if re.search(r"\bpg_(?:temp|catalog)\b", stripped, re.IGNORECASE):
        raise RuntimeError(
            f"question-export runtime SQL references a PG system schema: {query_id}"
        )
    if re.search(
        r"\bselect\s+(?:distinct\s+)?(?:(?:[A-Za-z][A-Za-z0-9_]*)\.)?\*",
        stripped,
        re.IGNORECASE,
    ) or re.search(r"\b[A-Za-z][A-Za-z0-9_]*\.\*", stripped):
        raise RuntimeError(
            f"question-export SQL must use ten explicit columns: {query_id}"
        )
    if len(re.findall(r"\bjoin\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError(
            f"question-export SQL must contain exactly one join: {query_id}"
        )
    if len(re.findall(r"\bleft\s+join\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError(
            f"question-export SQL must retain its LEFT JOIN: {query_id}"
        )
    actual = normalize_sql(stripped)
    if actual != EXPECTED_NORMALIZED_SQL[query_id]:
        raise RuntimeError(
            f"question-export runtime SQL shape drifted for {query_id}: {actual}"
        )


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java runtime SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID:
        raise RuntimeError("question-export runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("question-export runtime SQL manifest schema drifted")
    if manifest.get("adapter_class") != ADAPTER_CLASS:
        raise RuntimeError("question-export runtime SQL adapter class drifted")
    queries = manifest.get("queries")
    if (
        not isinstance(queries, list)
        or manifest.get("query_count") != len(EXPECTED_QUERY_ORDER)
        or len(queries) != len(EXPECTED_QUERY_ORDER)
    ):
        raise RuntimeError("question-export manifest must contain exactly two queries")
    actual_order: list[str] = []
    for query in queries:
        if not isinstance(query, dict):
            raise RuntimeError("question-export runtime query must be an object")
        query_id = query.get("query_id")
        if not isinstance(query_id, str) or query_id in actual_order:
            raise RuntimeError(f"invalid or duplicate runtime query ID: {query_id}")
        actual_order.append(query_id)
        if query_id not in EXPECTED_PARAMETER_TYPES:
            raise RuntimeError(f"unexpected runtime query ID: {query_id}")
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
        if (
            len(occurrences) != len(parameters)
            or set(occurrences) != set(parameters)
        ):
            raise RuntimeError(
                f"runtime SQL parameter surface drifted for {query_id}: "
                f"occurrences={occurrences} declared={sorted(parameters)}"
            )
    if tuple(actual_order) != EXPECTED_QUERY_ORDER:
        raise RuntimeError(f"runtime query order drifted: {actual_order}")
    return manifest


def manifest_queries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {query["query_id"]: query for query in manifest["queries"]}


def orphan_subject_id(subject_count: int) -> int:
    return subject_count + 1_001


def subject_for(question_id: int, subject_count: int) -> Optional[int]:
    if question_id == -1:
        return -1
    if question_id == 0:
        return 0
    if question_id == 1:
        return None
    if question_id == 2:
        return orphan_subject_id(subject_count)
    return ((question_id - 3) % subject_count) + 1


def expected_result(
    question_count: int,
    subject_count: int,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    ids = [
        question_id
        for question_id in range(-1, question_count - 1)
        if "subject_id" not in parameters
        or subject_for(question_id, subject_count) == parameters["subject_id"]
    ]
    return {
        "row_count": len(ids),
        "minimum_id": ids[0] if ids else None,
        "middle_id": ids[len(ids) // 2] if ids else None,
        "maximum_id": ids[-1] if ids else None,
        "first_ids_asc": ids[:3],
        "last_ids_asc": ids[-3:],
    }


def observation_specs(args: argparse.Namespace) -> list[dict[str, Any]]:
    middle_subject = (args.subject_count + 1) // 2
    raw_specs = [
        ("all-questions", "question-export-all", {}),
        ("first-subject", "question-export-by-subject", {"subject_id": 1}),
        (
            "middle-subject",
            "question-export-by-subject",
            {"subject_id": middle_subject},
        ),
        (
            "last-subject",
            "question-export-by-subject",
            {"subject_id": args.subject_count},
        ),
        ("zero-subject", "question-export-by-subject", {"subject_id": 0}),
        ("negative-subject", "question-export-by-subject", {"subject_id": -1}),
        (
            "missing-subject-reference",
            "question-export-by-subject",
            {"subject_id": orphan_subject_id(args.subject_count)},
        ),
        (
            "integer-min-subject",
            "question-export-by-subject",
            {"subject_id": -2_147_483_648},
        ),
        (
            "integer-max-subject",
            "question-export-by-subject",
            {"subject_id": 2_147_483_647},
        ),
    ]
    specs: list[dict[str, Any]] = []
    for observation_id, query_id, parameters in raw_specs:
        expected = expected_result(
            args.question_count,
            args.subject_count,
            parameters,
        )
        if query_id == "question-export-all":
            # The pinned PG18.4 plan memoizes one subject PK lookup for every
            # distinct nullable/signed/orphan/positive subject key.
            subject_relation_loops = min(
                args.subject_count,
                args.question_count - 4,
            ) + 4
            maximum_actual_loops = args.question_count
        else:
            # A filtered outer join probes subjects once when an outer row
            # exists, and the child remains unexecuted for an empty result.
            subject_relation_loops = 1 if expected["row_count"] else 0
            maximum_actual_loops = max(1, expected["row_count"])
        specs.append(
            {
                "observation_id": observation_id,
                "runtime_query_id": query_id,
                "parameters": parameters,
                "expected": expected,
                "expected_plan_loops": {
                    "maximum_actual_loops": maximum_actual_loops,
                    "relation_scan_actual_loops": {
                        "questions": [1],
                        "subjects": [subject_relation_loops],
                    },
                },
            }
        )
    return specs


def bound_parameter(name: str, value: Any) -> dict[str, Any]:
    if name != "subject_id":
        raise RuntimeError(f"unsupported question-export parameter: {name}")
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


def postgres_literal(parameter: dict[str, Any]) -> str:
    if parameter.get("postgres_type") != "integer":
        raise RuntimeError(f"unsupported PostgreSQL parameter: {parameter}")
    value = parameter.get("value")
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"invalid PostgreSQL integer parameter: {parameter}")
    return str(value)


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
        raise RuntimeError(
            f"question-export bind surface drifted: {occurrences}"
        )
    positional_parameters = [bound[name] for name in occurrences]
    postgres_types = [item["postgres_type"] for item in positional_parameters]
    literals = [postgres_literal(item) for item in positional_parameters]
    statement_name = "qe_" + re.sub(
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
        "runtime_statement_count": 1,
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
            f"--pset=null={NULL_MARKER}",
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
    maximum_question_id = args.question_count - 2
    missing_subject = orphan_subject_id(args.subject_count)
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
    options text,
    answer text,
    analysis text,
    difficulty integer,
    tags text
);

INSERT INTO subjects (id, name) VALUES
    (-1, ''),
    (0, '科目 🧪');

INSERT INTO subjects (id, name)
SELECT n, 'Synthetic subject ' || n
FROM generate_series(1, {args.subject_count}) AS generated(n);

INSERT INTO questions (
    id, subject_id, type, content, options, answer, analysis, difficulty, tags
)
SELECT n,
       CASE
           WHEN n = -1 THEN -1
           WHEN n = 0 THEN 0
           WHEN n = 1 THEN NULL
           WHEN n = 2 THEN {missing_subject}
           ELSE ((n - 3) % {args.subject_count}) + 1
       END,
       CASE
           WHEN n = -1 THEN 'essay'
           WHEN n = 0 THEN 'fill'
           ELSE (ARRAY[
               'single_choice', 'multi_choice', 'boolean', 'fill', 'essay'
           ])[1 + ((n - 1) % 5)]
       END,
       CASE
           WHEN n = -1 THEN '公开合成汉字🙂题干'
           WHEN n = 0 THEN ''
           ELSE 'Synthetic export question ' || n
       END,
       CASE
           WHEN n = -1 THEN 'not-json:{{broken]'
           WHEN n = 0 THEN ''
           WHEN n % 1013 = 0 THEN NULL
           ELSE '["synthetic-option"]'
       END,
       CASE
           WHEN n = -1 THEN 'RAW<未闭合'
           WHEN n % 1019 = 0 THEN NULL
           ELSE 'synthetic-answer-' || n
       END,
       CASE
           WHEN n = -1 THEN '分析🙂 invalid-json:[}}'
           WHEN n % 1021 = 0 THEN NULL
           ELSE 'Synthetic analysis ' || n
       END,
       CASE
           WHEN n = 1 OR n % 1009 = 0 THEN NULL
           ELSE 1 + (abs(n) % 5)
       END,
       CASE
           WHEN n = -1 THEN 'raw-malformed-tags:{{]'
           WHEN n % 997 = 0 THEN NULL
           ELSE '["synthetic"]'
       END
FROM generate_series(-1, {maximum_question_id}) AS generated(n);

-- TEST-ONLY synthetic index used only to observe bounded PG18.4 choices.
-- Its presence is not approval of a production index or migration.
CREATE INDEX ix_questions_subject_id ON questions (subject_id);

ALTER TABLE questions ALTER COLUMN subject_id SET STATISTICS 10000;

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
        if key in PLAN_EXPRESSION_KEYS and isinstance(child, (str, list)):
            serialized = json.dumps(child, ensure_ascii=False, sort_keys=True)
            normalized[key] = {
                "redacted": "planner expression omitted",
                "character_count": len(serialized),
                "sha256": sha256_text(serialized),
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
            "Strategy",
            "Join Type",
            "Relation Name",
            "Alias",
            "Index Name",
            "Scan Direction",
            "Sort Method",
            "Actual Rows",
            "Actual Loops",
            "Rows Removed by Filter",
            "Rows Removed by Index Recheck",
            "Index Searches",
            "Sort Key",
            "Hash Cond",
            "Merge Cond",
            "Join Filter",
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
    node_types = Counter(str(node["Node Type"]) for node in nodes)
    relations = Counter(
        str(node["Relation Name"]) for node in nodes if "Relation Name" in node
    )
    loops = [int(node.get("Actual Loops", 0)) for node in nodes]
    relation_loops: dict[str, list[int]] = {}
    for node in nodes:
        if "Relation Name" in node:
            relation_loops.setdefault(str(node["Relation Name"]), []).append(
                int(node.get("Actual Loops", 0))
            )
    join_nodes = [
        {
            "node_type": node.get("Node Type"),
            "join_type": node.get("Join Type"),
            "actual_rows": node.get("Actual Rows"),
            "actual_loops": node.get("Actual Loops"),
        }
        for node in nodes
        if str(node.get("Node Type", "")).endswith("Join")
        or node.get("Node Type") == "Nested Loop"
    ]
    return {
        "root_node_type": root.get("Node Type"),
        "result_row_count": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max(node["depth"] for node in nodes),
        "maximum_actual_loops": max(loops, default=0),
        "maximum_relation_scan_actual_loops": max(
            (loop for values in relation_loops.values() for loop in values),
            default=0,
        ),
        "relation_scan_actual_loops": {
            key: values for key, values in sorted(relation_loops.items())
        },
        "node_type_counts": dict(sorted(node_types.items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "join_nodes": join_nodes,
        "index_names": sorted(
            {str(node["Index Name"]) for node in nodes if "Index Name" in node}
        ),
        "buffer_fields_observed_before_normalization": sorted(buffer_fields),
        "nodes": nodes,
    }


def _subject_name_state(value: str) -> str:
    if value == NULL_MARKER:
        return "null"
    if value == "":
        return "empty"
    if any(ord(character) > 127 for character in value):
        return "unicode"
    return "text"


def parse_result_rows(raw: str, expected: dict[str, Any]) -> dict[str, Any]:
    lines = raw.splitlines() if raw else []
    ids: list[int] = []
    null_subject_ids = 0
    null_subject_names = 0
    empty_subject_names = 0
    unicode_subject_names = 0
    unicode_payload_rows = 0
    malformed_payload_rows = 0
    edge_rows: dict[str, dict[str, Any]] = {}
    malformed_markers = (
        "not-json:{broken]",
        "RAW<未闭合",
        "invalid-json:[}",
        "raw-malformed-tags:{]",
    )
    for line in lines:
        fields = line.split("|")
        if len(fields) != len(EXPECTED_COLUMNS):
            raise AssertionError(
                f"question-export runtime result column count drifted: {len(fields)}"
            )
        if not re.fullmatch(r"-?[0-9]+", fields[0]):
            raise AssertionError(
                f"question-export runtime result ID is not integer: {fields[0]}"
            )
        if fields[1] != NULL_MARKER and not re.fullmatch(r"-?[0-9]+", fields[1]):
            raise AssertionError(
                f"question-export subject ID is not nullable integer: {fields[1]}"
            )
        question_id = int(fields[0])
        ids.append(question_id)
        null_subject_ids += int(fields[1] == NULL_MARKER)
        name_state = _subject_name_state(fields[2])
        null_subject_names += int(name_state == "null")
        empty_subject_names += int(name_state == "empty")
        unicode_subject_names += int(name_state == "unicode")
        payload = fields[3:]
        unicode_payload = any(
            any(ord(character) > 127 for character in field)
            for field in payload
            if field != NULL_MARKER
        )
        malformed_payload = any(
            marker in field for marker in malformed_markers for field in payload
        )
        unicode_payload_rows += int(unicode_payload)
        malformed_payload_rows += int(malformed_payload)
        if question_id in {-1, 0, 1, 2}:
            edge_rows[str(question_id)] = {
                "question_id": question_id,
                "subject_id": None
                if fields[1] == NULL_MARKER
                else int(fields[1]),
                "subject_name_state": name_state,
                "unicode_payload": unicode_payload,
                "raw_malformed_payload": malformed_payload,
                "row_sha256": sha256_text(line),
            }
    strictly_ascending = all(
        previous < current for previous, current in zip(ids, ids[1:])
    )
    actual = {
        "row_count": len(ids),
        "minimum_id": ids[0] if ids else None,
        "middle_id": ids[len(ids) // 2] if ids else None,
        "maximum_id": ids[-1] if ids else None,
        "first_ids_asc": ids[:3],
        "last_ids_asc": ids[-3:],
        "strictly_ascending_by_id": strictly_ascending,
        "row_column_count": len(EXPECTED_COLUMNS),
        "null_subject_id_rows": null_subject_ids,
        "null_subject_name_rows": null_subject_names,
        "empty_subject_name_rows": empty_subject_names,
        "unicode_subject_name_rows": unicode_subject_names,
        "unicode_payload_rows": unicode_payload_rows,
        "raw_malformed_payload_rows": malformed_payload_rows,
        "edge_rows": edge_rows,
        "canonical_psql_rows_sha256": sha256_text(raw),
    }
    for key in (
        "row_count",
        "minimum_id",
        "middle_id",
        "maximum_id",
        "first_ids_asc",
        "last_ids_asc",
    ):
        if actual[key] != expected[key]:
            raise AssertionError(
                f"question-export runtime result boundary drifted for {key}: "
                f"actual={actual[key]} expected={expected[key]}"
            )
    if len(ids) > 1 and not strictly_ascending:
        raise AssertionError(
            "question-export runtime results are not strictly ordered by id ASC"
        )
    return actual


def assert_plan(
    spec: dict[str, Any],
    execution: dict[str, Any],
    result_summary: dict[str, Any],
    summary: dict[str, Any],
    temp_blocks: dict[str, Optional[float]],
) -> list[str]:
    passed: list[str] = []
    expected_rows = spec["expected"]["row_count"]
    if result_summary["row_count"] != expected_rows:
        raise AssertionError("question-export result row count drifted")
    if result_summary["row_column_count"] != len(EXPECTED_COLUMNS):
        raise AssertionError("question-export result must retain ten columns")
    if not re.fullmatch(
        r"[0-9a-f]{64}", result_summary["canonical_psql_rows_sha256"]
    ):
        raise AssertionError("question-export result digest is missing")
    passed.append("ten-column-result-count-boundaries-and-digest")
    if summary["result_row_count"] != expected_rows:
        raise AssertionError(
            f"{spec['observation_id']} plan rows "
            f"{summary['result_row_count']}; expected {expected_rows}"
        )
    passed.append("plan-row-count-matches-runtime-result")
    if not result_summary["strictly_ascending_by_id"] and expected_rows > 1:
        raise AssertionError("question-export ordering is not strictly id ASC")
    passed.append("strict-id-asc-runtime-order")
    if summary["root_actual_loops"] != 1:
        raise AssertionError("question-export plan root must execute exactly once")
    expected_loops = spec.get("expected_plan_loops")
    if not isinstance(expected_loops, dict):
        raise AssertionError("question-export expected plan-loop contract is missing")
    if (
        summary["relation_scan_actual_loops"]
        != expected_loops.get("relation_scan_actual_loops")
    ):
        raise AssertionError(
            "question-export relation scan loops drifted: "
            f"{summary['relation_scan_actual_loops']}"
        )
    if summary["maximum_actual_loops"] != expected_loops.get(
        "maximum_actual_loops"
    ):
        raise AssertionError(
            "question-export helper-node loops drifted: "
            f"{summary['maximum_actual_loops']}"
        )
    passed.append("exact-pg184-root-helper-and-relation-loop-contract")
    if summary["node_count"] > 10 or summary["maximum_depth"] > 6:
        raise AssertionError("question-export plan exceeded node/depth bounds")
    passed.append("bounded-plan-shape")
    if summary["relation_scan_occurrences"] != {
        "questions": 1,
        "subjects": 1,
    }:
        raise AssertionError(
            "question-export relation budget drifted: "
            f"{summary['relation_scan_occurrences']}"
        )
    passed.append("questions-and-subjects-scanned-once-only")
    join_nodes = summary["join_nodes"]
    if len(join_nodes) != 1 or join_nodes[0].get("join_type") not in {
        "Left",
        "Right",
    }:
        raise AssertionError(
            "question-export plan must retain exactly one outer join"
        )
    passed.append("one-outer-join-left-right-planner-swap-allowed")
    for key in ("Temp Read Blocks", "Temp Written Blocks"):
        if temp_blocks.get(key) != 0:
            raise AssertionError(
                f"question-export plan used or omitted TEMP blocks: {temp_blocks}"
            )
    passed.append("zero-temp-blocks")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise AssertionError("question-export BUFFERS evidence was not emitted")
    passed.append("buffers-captured-before-normalization")
    expected_parameters = EXPECTED_PARAMETER_TYPES[spec["runtime_query_id"]]
    if (
        execution.get("runtime_statement_count") != 1
        or execution["bound_parameter_count"] != len(expected_parameters)
        or execution["named_parameter_count"] != len(expected_parameters)
        or set(execution["occurrence_names"]) != set(expected_parameters)
    ):
        raise AssertionError("question-export statement or bind surface drifted")
    passed.append("one-select-fixed-typed-bind-cardinality")
    required_question_index = (
        "questions_pkey"
        if spec["runtime_query_id"] == "question-export-all"
        else "ix_questions_subject_id"
    )
    if required_question_index not in summary["index_names"]:
        raise AssertionError(
            f"question-export expected synthetic index was not observed: "
            f"{required_question_index}"
        )
    passed.append("expected-test-only-question-index-observed")
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
        raise RuntimeError("unexpected question-export EXPLAIN JSON payload")
    raw_explain = payload[0]
    buffer_fields = collect_numeric_fields(raw_explain, BUFFER_KEYS)
    temp_blocks = {
        key: buffer_fields.get(key)
        for key in ("Temp Read Blocks", "Temp Written Blocks")
    }
    normalized = normalize_explain(raw_explain)
    summary = summarize_plan(normalized, buffer_fields)
    if result_execution != execution:
        raise AssertionError("result and EXPLAIN binding metadata drifted")
    checks = assert_plan(
        spec,
        execution,
        result_summary,
        summary,
        temp_blocks,
    )
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


def assert_environment_metadata(metadata: dict[str, Any]) -> None:
    if metadata.get("server_version_num") != "180004":
        raise AssertionError(
            f"question-export capture requires PostgreSQL 18.4: {metadata}"
        )
    if metadata.get("work_mem") != "64MB":
        raise AssertionError("question-export deterministic work_mem drifted")
    if metadata.get("max_parallel_workers_per_gather") != "0":
        raise AssertionError("question-export parallel-plan setting drifted")


def dataset_metadata(container: str) -> dict[str, Any]:
    return psql_json(
        container,
        """
SELECT json_build_object(
    'questions', (SELECT COUNT(*) FROM questions),
    'subjects', (SELECT COUNT(*) FROM subjects),
    'minimum_question_id', (SELECT MIN(id) FROM questions),
    'maximum_question_id', (SELECT MAX(id) FROM questions),
    'minimum_subject_id', (SELECT MIN(id) FROM subjects),
    'maximum_subject_id', (SELECT MAX(id) FROM subjects),
    'negative_subject_ids', (SELECT COUNT(*) FROM subjects WHERE id < 0),
    'zero_subject_ids', (SELECT COUNT(*) FROM subjects WHERE id = 0),
    'empty_subject_names', (SELECT COUNT(*) FROM subjects WHERE name = ''),
    'unicode_subject_names',
        (SELECT COUNT(*) FROM subjects WHERE name = '科目 🧪'),
    'null_question_subject_rows',
        (SELECT COUNT(*) FROM questions WHERE subject_id IS NULL),
    'orphan_question_subject_rows', (
        SELECT COUNT(*)
        FROM questions q
        LEFT JOIN subjects s ON s.id = q.subject_id
        WHERE q.subject_id IS NOT NULL AND s.id IS NULL
    ),
    'unicode_payload_rows',
        (SELECT COUNT(*) FROM questions WHERE content = '公开合成汉字🙂题干'),
    'raw_malformed_payload_rows', (
        SELECT COUNT(*)
        FROM questions
        WHERE options = 'not-json:{broken]'
          AND answer = 'RAW<未闭合'
          AND analysis = '分析🙂 invalid-json:[}'
          AND tags = 'raw-malformed-tags:{]'
    ),
    'nullable_options_rows',
        (SELECT COUNT(*) FROM questions WHERE options IS NULL),
    'nullable_answer_rows',
        (SELECT COUNT(*) FROM questions WHERE answer IS NULL),
    'nullable_analysis_rows',
        (SELECT COUNT(*) FROM questions WHERE analysis IS NULL),
    'nullable_difficulty_rows',
        (SELECT COUNT(*) FROM questions WHERE difficulty IS NULL),
    'nullable_tags_rows',
        (SELECT COUNT(*) FROM questions WHERE tags IS NULL)
);
""",
    )


def assert_dataset_metadata(
    metadata: dict[str, Any], args: argparse.Namespace
) -> None:
    expected = {
        "questions": args.question_count,
        "subjects": args.subject_count + 2,
        "minimum_question_id": -1,
        "maximum_question_id": args.question_count - 2,
        "minimum_subject_id": -1,
        "maximum_subject_id": args.subject_count,
        "negative_subject_ids": 1,
        "zero_subject_ids": 1,
        "empty_subject_names": 1,
        "unicode_subject_names": 1,
        "null_question_subject_rows": 1,
        "orphan_question_subject_rows": 1,
        "unicode_payload_rows": 1,
        "raw_malformed_payload_rows": 1,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise AssertionError(
                f"question-export synthetic fixture drifted for {key}: "
                f"{metadata.get(key)} != {value}"
            )
    for key in (
        "nullable_options_rows",
        "nullable_answer_rows",
        "nullable_analysis_rows",
        "nullable_difficulty_rows",
        "nullable_tags_rows",
    ):
        if not isinstance(metadata.get(key), int) or metadata[key] <= 0:
            raise AssertionError(
                f"question-export fixture lost nullable payloads: {key}"
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
        "JdbcQuestionExportQueryAdapter.java",
        "runtime_sql_manifest": manifest_path,
        "runtime_sql_exporter": root
        / "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "QuestionExportRuntimeSqlManifestTest.java",
        "capture_tool": Path(__file__).resolve(),
        "capture_tool_test": Path(__file__).with_name(
            "test_capture_phase4a_question_export_query_plan.py"
        ).resolve(),
    }


def input_evidence(root: Path, manifest_path: Path) -> dict[str, str]:
    paths = required_input_paths(root, manifest_path)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"question-export evidence inputs are missing: {missing}")
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
                f"question-export evidence source drifted: {name} "
                f"recorded={expected} actual={actual}"
            )


def assert_runtime_sql_hash_closure(
    recorded: dict[str, str], manifest: dict[str, Any]
) -> None:
    queries = manifest_queries(manifest)
    if set(recorded) != set(EXPECTED_QUERY_ORDER):
        raise AssertionError("question-export recorded SQL hash keys drifted")
    for query_id in EXPECTED_QUERY_ORDER:
        if recorded[query_id] != sha256_text(queries[query_id]["sql"]):
            raise AssertionError(
                f"question-export runtime SQL hash drifted: {query_id}"
            )


def add_attestation(document: dict[str, Any]) -> dict[str, Any]:
    if "attestation" in document:
        raise ValueError("question-export evidence is already attested")
    document["attestation"] = {
        "status": "passed",
        "algorithm": "sha256",
        "canonical_payload_excluding_attestation_sha256": canonical_json_sha256(
            document
        ),
        "closures": [
            "exact-java-runtime-sql-export",
            "manifest-schema-query-parameter-and-sql-shape",
            "public-synthetic-dataset-and-result-digests",
            "postgresql-18.4-immutable-image",
            "normalized-plans-relations-joins-loops-and-temp",
            "input-and-runtime-sql-post-capture-hashes",
        ],
    }
    return document


def assert_attestation(document: dict[str, Any]) -> None:
    attestation = document.get("attestation")
    if not isinstance(attestation, dict) or attestation.get("status") != "passed":
        raise AssertionError("question-export evidence attestation is missing")
    payload = {key: value for key, value in document.items() if key != "attestation"}
    actual = canonical_json_sha256(payload)
    if attestation.get("canonical_payload_excluding_attestation_sha256") != actual:
        raise AssertionError("question-export evidence attestation hash drifted")


def assert_public_evidence(document: Any) -> None:
    ephemeral_container = re.compile(
        r"ti-phase4a-question-export-plan-[0-9a-f]{12}"
    )

    def visit(value: Any, key: str = "") -> None:
        lowered = key.lower().replace("-", "_")
        if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
            raise AssertionError(f"sensitive evidence key is forbidden: {key}")
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str):
            if any(prefix in value for prefix in ("/Users/", "/private/", "/home/")):
                raise AssertionError("private absolute path leaked into evidence")
            if ephemeral_container.search(value):
                raise AssertionError("ephemeral container identity leaked into evidence")

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
    expected_observation_ids = {
        "all-questions",
        "first-subject",
        "middle-subject",
        "last-subject",
        "zero-subject",
        "negative-subject",
        "missing-subject-reference",
        "integer-min-subject",
        "integer-max-subject",
    }
    if {item["observation_id"] for item in observations} != expected_observation_ids:
        raise AssertionError("question-export observation boundary coverage drifted")
    covered = {item["runtime_query_id"] for item in observations}
    if covered != set(EXPECTED_QUERY_ORDER):
        raise AssertionError(
            f"question-export runtime variant coverage drifted: {covered}"
        )
    if {item["sql_statement_count"] for item in observations} != {1}:
        raise AssertionError("question-export SQL statement count drifted")
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
        raise AssertionError(
            f"question-export bind cardinality drifted: {bind_counts}"
        )

    all_result = next(
        item["runtime_result"]
        for item in observations
        if item["observation_id"] == "all-questions"
    )
    expected_edges = {
        "-1": {
            "subject_id": -1,
            "subject_name_state": "empty",
            "unicode_payload": True,
            "raw_malformed_payload": True,
        },
        "0": {
            "subject_id": 0,
            "subject_name_state": "unicode",
        },
        "1": {
            "subject_id": None,
            "subject_name_state": "null",
        },
        "2": {
            "subject_id": orphan_subject_id(args.subject_count),
            "subject_name_state": "null",
        },
    }
    for edge_id, expected_edge in expected_edges.items():
        actual_edge = all_result["edge_rows"].get(edge_id)
        if not actual_edge:
            raise AssertionError(f"question-export edge row is missing: {edge_id}")
        for key, value in expected_edge.items():
            if actual_edge.get(key) != value:
                raise AssertionError(
                    f"question-export edge row drifted: {edge_id}.{key}"
                )
    edge_counts = {
        "null_subject_id_rows": 1,
        "null_subject_name_rows": 2,
        "empty_subject_name_rows": 1,
        "unicode_subject_name_rows": 1,
        "unicode_payload_rows": 1,
        "raw_malformed_payload_rows": 1,
    }
    for key, value in edge_counts.items():
        if all_result.get(key) != value:
            raise AssertionError(
                f"question-export all-result edge count drifted: {key}"
            )

    dataset = dataset_metadata(container)
    assert_dataset_metadata(dataset, args)
    indexes = index_definitions(container)
    index_names = {item["name"] for item in indexes}
    if index_names != {
        "subjects_pkey",
        "questions_pkey",
        "ix_questions_subject_id",
    }:
        raise AssertionError(
            f"question-export synthetic fixture indexes drifted: {sorted(index_names)}"
        )
    postgres = environment_metadata(container)
    assert_environment_metadata(postgres)

    root = Path(__file__).resolve().parents[1]
    fixture = fixture_sql(args)
    runtime_hashes = {
        query_id: sha256_text(queries[query_id]["sql"])
        for query_id in EXPECTED_QUERY_ORDER
    }
    inputs = input_evidence(root, manifest_path)
    document = {
        "evidence_id": "ti.phase4a.question-export-query-plan",
        "schema_version": 1,
        "captured_on": "2026-07-17",
        "scope": "catalog-owned-question-export-snapshot-internal-read-primitive",
        "runtime_sql_contract": {
            "source": "Java adapter runtime SQL manifest exported before capture",
            "manifest_id": manifest["manifest_id"],
            "manifest_schema_version": manifest["schema_version"],
            "adapter_class": manifest["adapter_class"],
            "query_ids_in_manifest_order": list(EXPECTED_QUERY_ORDER),
            "operation": OPERATION,
            "explicit_column_count": len(EXPECTED_COLUMNS),
            "explicit_columns": list(EXPECTED_COLUMNS),
            "fixed_order": "q.id ASC",
            "join": "questions LEFT JOIN subjects on q.subject_id = s.id",
            "query_sql_sha256": runtime_hashes,
            "parameter_postgres_types": EXPECTED_PARAMETER_TYPES,
            "sql_statement_count_per_execution": 1,
            "relation_budget": {
                "questions": 1,
                "subjects": 1,
                "joins": 1,
                "other_relations": 0,
            },
            "forbidden_runtime_shapes": [
                "DML",
                "DDL",
                "TEMP",
                "extra joins",
                "wildcards",
                "LIMIT/OFFSET/FETCH",
                "statement separators",
            ],
        },
        "environment": {
            "container_image": args.image,
            **image_metadata(args.image),
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": postgres,
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
                "positive_subject_count": args.subject_count,
                "signed_edge_subject_count": 2,
                "total_subject_count": args.subject_count + 2,
                "question_id_range": [-1, args.question_count - 2],
                "positive_subject_id_range": [1, args.subject_count],
                "signed_subject_ids": [-1, 0],
                "orphan_subject_id": orphan_subject_id(args.subject_count),
                "question_types": list(QUESTION_TYPES),
                "raw_and_nullable_distribution": (
                    "fixed public edge rows plus sparse deterministic nulls"
                ),
            },
            "actual": dataset,
            "fixture_sql_sha256": sha256_text(fixture),
            "statistics": "VACUUM (ANALYZE) completed before capture",
            "deterministic_statistics": (
                "subject_id uses test-only statistics target 10000"
            ),
            "index_definitions": indexes,
            "index_boundary": {
                "status": "test_only_synthetic_observation",
                "statement": (
                    "ix_questions_subject_id exists only in the isolated fixture "
                    "to observe PG18.4 choices; it does not approve a production "
                    "index or migration."
                ),
                "production_index_state": "unknown_not_asserted",
                "production_migration_added": False,
            },
            "edge_attestation": {
                "negative_and_zero_ids": "present",
                "nullable_subject": "present",
                "missing_join_target": "present",
                "empty_subject_name": "present",
                "unicode_payload_and_name": "present",
                "raw_malformed_text_payloads": "present",
            },
        },
        "measurement": {
            "command": (
                "execute and EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) each exact "
                "Java runtime SELECT through PREPARE/EXECUTE"
            ),
            "runs_per_observation": 1,
            "observation_count": len(observations),
            "runtime_query_count": len(EXPECTED_QUERY_ORDER),
            "sql_statement_count_per_execution": 1,
            "required_root_actual_loops": 1,
            "required_question_relation_scan_actual_loops": 1,
            "subject_relation_loop_contract": (
                "exact distinct-key memoized probes for all rows; exact zero-or-one "
                "probe for filtered rows"
            ),
            "required_temp_blocks": 0,
            "observations": observations,
        },
        "cross_observation_assertions": {
            "status": "passed",
            "observation_boundary_coverage": sorted(expected_observation_ids),
            "runtime_variant_coverage": list(EXPECTED_QUERY_ORDER),
            "bound_parameter_counts_by_runtime_query": bind_counts,
            "expected_bound_parameter_counts_by_runtime_query": expected_bind_counts,
            "bind_count_independent_of_result_row_count": True,
            "questions_relation_scans_per_observation": 1,
            "subjects_relation_scans_per_observation": 1,
            "outer_joins_per_observation": 1,
            "strict_id_asc_all_nontrivial_results": True,
            "ten_columns_all_observations": True,
            "zero_temp_blocks_all_observations": True,
            "result_digest_all_observations": True,
        },
        "normalization": {
            "removed": [
                "planning and execution timing",
                "per-node actual timing",
                "cache-dependent buffer block counts",
                "runtime memory and hash counters",
                "sample-dependent planner costs and row estimates",
                "parallel worker identities and counters",
                "container ID and container name",
            ],
            "redacted": [
                "planner filter, join, sort, and index expressions with SHA-256 retained"
            ],
            "retained": [
                "plan node types and depth",
                "actual rows and loops",
                "relation, join type, and observed index names",
                "scan direction and sort shape",
                "which BUFFERS fields were emitted",
            ],
        },
        "interpretation": {
            "status": "bounded_synthetic_plan_evidence_only",
            "statement": (
                "This isolated PostgreSQL 18.4 capture closes ten-column row "
                "shape, result digests, signed and nullable edges, strict ascending "
                "order, typed binds, one outer join, one scan of each relation, "
                "bounded loops, and zero TEMP for the exact Java SQL. It is not a "
                "production latency, capacity, or index-approval claim."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/"
                "capture_phase4a_question_export_query_plan.py --output "
                "Ti-Java/docs/refactor/phase4a/"
                "question-export-query-plan-evidence.json"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": (
                "ephemeral network-disabled container removed on success or failure"
            ),
        },
    }
    assert_input_hash_closure(inputs, required_input_paths(root, manifest_path))
    assert_runtime_sql_hash_closure(runtime_hashes, manifest)
    add_attestation(document)
    assert_attestation(document)
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
    container = "ti-phase4a-question-export-plan-" + uuid.uuid4().hex[:12]
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
                "POSTGRES_HOST_AUTH_METHOD=trust",
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
            "captured question-export plans "
            f"observations={document['measurement']['observation_count']} "
            f"sha256={sha256_file(output)}"
        )
        return 0
    finally:
        if started:
            cleanup_container(container)


if __name__ == "__main__":
    raise SystemExit(main())
