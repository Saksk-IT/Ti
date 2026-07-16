#!/usr/bin/env python3
"""Capture normalized PG18 plan evidence for the exact Java question-type SQL."""

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
DEFAULT_DATABASE = "phase4a_question_type_plan"
DEFAULT_QUESTION_COUNT = 50_000
DEFAULT_SUBJECT_COUNT = 5_000
RAW_TYPES = (
    "single_choice",
    " SINGLE ",
    "multi_choice",
    "multiple",
    "BOOLEAN",
    "true_false",
    " fill ",
    "fill-in-the-blank",
    "essay",
    "short_answer",
    "unknown",
    "   ",
)

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
MEMORY_KEYS = {"Peak Memory Usage", "Sort Space Used", "Average Peak Memory"}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/refactor/phase4a/question-type-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-question-type-runtime-sql.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--question-count", type=int, default=DEFAULT_QUESTION_COUNT)
    parser.add_argument("--subject-count", type=int, default=DEFAULT_SUBJECT_COUNT)
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.question_count < DEFAULT_QUESTION_COUNT:
        raise ValueError(f"--question-count must be at least {DEFAULT_QUESTION_COUNT}")
    if args.subject_count < DEFAULT_SUBJECT_COUNT:
        raise ValueError(f"--subject-count must be at least {DEFAULT_SUBJECT_COUNT}")
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")
    if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", args.image):
        raise ValueError("--image must be an immutable @sha256 PostgreSQL image reference")


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


def export_runtime_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("--runtime-sql-manifest must stay under Ti-Java/server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = run([
        str(verifier),
        "-Dtest=QuestionTypeRuntimeSqlManifestTest",
        f"-Dti.question-type.sql-manifest-output={output}",
        "test",
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java runtime SQL export failed: {detail}")


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        raise RuntimeError(f"Cannot read Java runtime SQL manifest: {path}") from exception
    if manifest.get("manifest_id") != "ti.phase4a.question-type-runtime-sql":
        raise RuntimeError("Java runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1 or manifest.get("query_count") != 1:
        raise RuntimeError("Java runtime SQL manifest shape drifted")
    queries = manifest.get("queries")
    if not isinstance(queries, list) or len(queries) != 1:
        raise RuntimeError("Java runtime SQL manifest query list drifted")
    query = queries[0]
    if query.get("query_id") != "question-types-distinct":
        raise RuntimeError("Java runtime SQL manifest query ID drifted")
    if query.get("operation") != "question-types" or query.get("parameters") != {}:
        raise RuntimeError("Java runtime SQL manifest operation or parameters drifted")
    sql = query.get("sql")
    if not isinstance(sql, str) or not sql.strip() or ";" in sql:
        raise RuntimeError("Java runtime SQL manifest SQL is unsafe or empty")
    return manifest


def psql(container: str, sql: str) -> str:
    result = run([
        "docker", "exec", "--interactive", container,
        "psql", "--username=postgres", f"--dbname={DEFAULT_DATABASE}",
        "--no-psqlrc", "--quiet", "--tuples-only", "--no-align",
        "--set=ON_ERROR_STOP=1",
    ], input_text=sql.rstrip() + "\n", check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "PostgreSQL command failed "
            f"(sql_sha256={sha256_text(sql)}): {result.stderr.strip()[-3000:]}"
        )
    return result.stdout.strip()


def psql_json(container: str, sql: str) -> Any:
    output = psql(container, sql)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exception:
        raise RuntimeError(f"PostgreSQL returned invalid JSON: {output[:500]}") from exception


def wait_until_ready(container: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        ready = run([
            "docker", "exec", container, "pg_isready",
            "--username=postgres", f"--dbname={DEFAULT_DATABASE}",
        ], check=False)
        if ready.returncode == 0:
            return
        time.sleep(1)
    logs = run(["docker", "logs", container], check=False)
    raise RuntimeError(
        f"PostgreSQL did not become ready: {(logs.stdout + logs.stderr)[-3000:]}"
    )


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def fixture_sql(args: argparse.Namespace) -> str:
    type_array = ", ".join(sql_literal(value) for value in RAW_TYPES)
    return f"""
CREATE TABLE subjects (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE questions (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    subject_id integer REFERENCES subjects(id) ON DELETE SET NULL,
    type text NOT NULL,
    content text NOT NULL
);

CREATE INDEX ix_questions_subject_id ON questions (subject_id);
CREATE INDEX ix_questions_subject_type ON questions (subject_id, type);
ALTER TABLE questions ALTER COLUMN type SET STATISTICS 10000;

INSERT INTO subjects (id, name)
SELECT n, 'Synthetic subject ' || lpad(n::text, 5, '0')
FROM generate_series(1, {args.subject_count}) AS generated(n);

INSERT INTO questions (subject_id, type, content)
SELECT ((n - 1) % {args.subject_count}) + 1,
       (ARRAY[{type_array}])[1 + (n % {len(RAW_TYPES)})],
       'Synthetic question ' || n
FROM generate_series(1, {args.question_count}) AS generated(n);

VACUUM (ANALYZE) subjects;
VACUUM (ANALYZE) questions;
"""


def legacy_label(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "single": "single_choice",
        "single_choice": "single_choice",
        "singlechoice": "single_choice",
        "multi": "multi_choice",
        "multiple": "multi_choice",
        "multi_choice": "multi_choice",
        "multichoice": "multi_choice",
        "boolean": "boolean",
        "bool": "boolean",
        "judge": "boolean",
        "true_false": "boolean",
        "truefalse": "boolean",
        "fill": "fill",
        "fill_in_the_blank": "fill",
        "fill-in-the-blank": "fill",
        "fillblank": "fill",
        "fill_in_the_blank_question": "fill",
        "essay": "essay",
        "short_answer": "essay",
        "shortanswer": "essay",
    }
    normalized = aliases.get(normalized, normalized)
    return {
        "single_choice": "选择题",
        "multi_choice": "多选题",
        "boolean": "判断题",
        "fill": "填空题",
    }.get(normalized, "简答题")


def collect_buffer_fields(value: Any) -> list[str]:
    observed: set[str] = set()

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                if key in BUFFER_KEYS:
                    observed.add(key)
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return sorted(observed)


def normalize_explain(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_explain(child) for child in value]
    if not isinstance(value, dict):
        return value
    normalized: dict[str, Any] = {}
    for key, child in value.items():
        if key in TIMING_KEYS or key in BUFFER_KEYS or key in MEMORY_KEYS or key == "Workers":
            continue
        candidate = normalize_explain(child)
        if isinstance(child, (dict, list)) and candidate in ({}, []):
            continue
        normalized[key] = candidate
    return normalized


def plan_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: dict[str, Any], depth: int) -> None:
        summary = {"depth": depth}
        for key in (
            "Node Type", "Parent Relationship", "Strategy", "Relation Name", "Alias",
            "Index Name", "Actual Rows", "Actual Loops", "Rows Removed by Filter",
            "Plan Rows", "Group Key", "Sort Key",
        ):
            if key in node:
                summary[key] = node[key]
        nodes.append(summary)
        for child in node.get("Plans", []):
            visit(child, depth + 1)

    visit(root, 0)
    return nodes


def summarize_plan(explain: dict[str, Any], buffer_fields: list[str]) -> dict[str, Any]:
    root = explain["Plan"]
    nodes = plan_nodes(root)
    node_types = Counter(str(node["Node Type"]) for node in nodes)
    relations = Counter(
        str(node["Relation Name"]) for node in nodes if "Relation Name" in node)
    return {
        "root_node_type": root.get("Node Type"),
        "result_row_count": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max(node["depth"] for node in nodes),
        "maximum_actual_loops": max(int(node.get("Actual Loops", 0)) for node in nodes),
        "node_type_counts": dict(sorted(node_types.items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "index_names": sorted(
            {str(node["Index Name"]) for node in nodes if "Index Name" in node}),
        "buffer_fields_observed_before_normalization": buffer_fields,
        "nodes": nodes,
    }


def assert_plan(summary: dict[str, Any]) -> list[str]:
    checks: list[str] = []
    if summary["result_row_count"] != len(RAW_TYPES):
        raise AssertionError("raw distinct result count drifted")
    checks.append("twelve-raw-distinct-values")
    if summary["root_actual_loops"] != 1 or summary["maximum_actual_loops"] != 1:
        raise AssertionError("query plan executed a node more than once")
    checks.append("single-execution-no-n-plus-one")
    if summary["relation_scan_occurrences"] != {"questions": 1}:
        raise AssertionError("questions relation scan count drifted")
    checks.append("one-questions-relation-scan")
    if summary["node_count"] > 4 or summary["maximum_depth"] > 2:
        raise AssertionError("query plan exceeds bounded node/depth budget")
    checks.append("bounded-plan-shape")
    if "Nested Loop" in summary["node_type_counts"]:
        raise AssertionError("question-type query unexpectedly introduced a nested loop")
    checks.append("no-nested-loop")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise AssertionError("BUFFERS evidence was not emitted")
    checks.append("buffers-captured-before-normalization")
    return checks


def environment_metadata(container: str) -> dict[str, Any]:
    return psql_json(container, """
SELECT json_build_object(
    'server_version', current_setting('server_version'),
    'server_version_num', current_setting('server_version_num'),
    'block_size_bytes', current_setting('block_size'),
    'shared_buffers', current_setting('shared_buffers'),
    'work_mem', current_setting('work_mem'),
    'effective_cache_size', current_setting('effective_cache_size'),
    'random_page_cost', current_setting('random_page_cost'),
    'max_parallel_workers_per_gather', current_setting('max_parallel_workers_per_gather'),
    'jit', current_setting('jit')
);
""")


def dataset_metadata(container: str) -> dict[str, Any]:
    return psql_json(container, """
SELECT json_build_object(
    'subjects', (SELECT COUNT(*) FROM subjects),
    'questions', (SELECT COUNT(*) FROM questions),
    'raw_distinct_types', (SELECT COUNT(DISTINCT type) FROM questions),
    'minimum_rows_per_type', (
        SELECT MIN(type_count) FROM (SELECT COUNT(*) type_count FROM questions GROUP BY type) t
    ),
    'maximum_rows_per_type', (
        SELECT MAX(type_count) FROM (SELECT COUNT(*) type_count FROM questions GROUP BY type) t
    )
);
""")


def index_definitions(container: str) -> list[dict[str, str]]:
    return psql_json(container, """
SELECT COALESCE(
    json_agg(json_build_object(
        'table', tablename,
        'name', indexname,
        'definition', indexdef
    ) ORDER BY tablename, indexname),
    '[]'::json
)
FROM pg_indexes
WHERE schemaname = 'public' AND tablename IN ('subjects', 'questions');
""")


def image_metadata(image: str) -> dict[str, Any]:
    raw = run(["docker", "image", "inspect", image]).stdout
    metadata = json.loads(raw)[0]
    expected_digest = image.split("@", 1)[1]
    repo_digests = sorted(metadata.get("RepoDigests", []))
    if not any(value.endswith(expected_digest) for value in repo_digests):
        raise AssertionError(f"resolved image lacks expected digest {expected_digest}")
    return {
        "expected_digest": expected_digest,
        "resolved_image_id": metadata.get("Id"),
        "resolved_repo_digests": repo_digests,
        "os": metadata.get("Os"),
        "architecture": metadata.get("Architecture"),
    }


def capture(
    args: argparse.Namespace,
    container: str,
    runtime_manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    query = runtime_manifest["queries"][0]
    raw_explain = psql_json(
        container,
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + query["sql"] + ";",
    )
    if not isinstance(raw_explain, list) or len(raw_explain) != 1:
        raise RuntimeError("unexpected EXPLAIN JSON payload")
    buffer_fields = collect_buffer_fields(raw_explain[0])
    normalized = normalize_explain(raw_explain[0])
    summary = summarize_plan(normalized, buffer_fields)
    checks = assert_plan(summary)
    dataset = dataset_metadata(container)
    if dataset["questions"] != args.question_count:
        raise AssertionError("question fixture row count drifted")
    if dataset["subjects"] != args.subject_count:
        raise AssertionError("subject fixture row count drifted")
    if dataset["raw_distinct_types"] != len(RAW_TYPES):
        raise AssertionError("question fixture distinct type count drifted")

    normalized_labels = sorted({legacy_label(value) for value in RAW_TYPES})
    expected_labels = ["判断题", "填空题", "多选题", "简答题", "选择题"]
    if normalized_labels != expected_labels:
        raise AssertionError(f"legacy label projection drifted: {normalized_labels}")

    root = Path(__file__).resolve().parents[1]
    tool_path = Path(__file__).resolve()
    adapter_path = root / (
        "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "JdbcQuestionTypeQueryAdapter.java"
    )
    exporter_path = root / (
        "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "QuestionTypeRuntimeSqlManifestTest.java"
    )
    image = image_metadata(args.image)
    return {
        "evidence_id": "ti.phase4a.question-type-query-plan",
        "schema_version": 1,
        "captured_at": "2026-07-16",
        "scope": "catalog-question-metadata-internal-read-capability",
        "route_migration_status": {
            "route_ids": ["e4cbe4d6bcc8", "3a346cb29186"],
            "http_owner": "operations",
            "status": "pending",
            "production_cutover": False,
        },
        "environment": {
            "container_image": args.image,
            **image,
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment_metadata(container),
        },
        "inputs": {
            "adapter": str(adapter_path.relative_to(root)),
            "adapter_sha256": sha256_text(adapter_path.read_text(encoding="utf-8")),
            "runtime_sql_manifest": str(manifest_path.relative_to(root)),
            "runtime_sql_manifest_sha256": sha256_text(
                manifest_path.read_text(encoding="utf-8")),
            "runtime_sql_exporter": str(exporter_path.relative_to(root)),
            "runtime_sql_exporter_sha256": sha256_text(
                exporter_path.read_text(encoding="utf-8")),
            "capture_tool_sha256": sha256_text(tool_path.read_text(encoding="utf-8")),
        },
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "subject_count": args.subject_count,
                "question_count": args.question_count,
                "raw_type_values": list(RAW_TYPES),
            },
            "actual": dataset,
            "legacy_normalized_labels": normalized_labels,
            "statistics": (
                "questions.type statistics target 10000 forces a full sample for this bounded "
                "fixture; VACUUM (ANALYZE) completed before capture"
            ),
            "index_definitions": index_definitions(container),
            "index_decision": (
                "observe existing subject_id and subject_id+type indexes only; "
                "no production type-only index is introduced by this evidence"
            ),
        },
        "measurement": {
            "command": "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) exact Java runtime SQL",
            "runs_per_query": 1,
            "query_count": 1,
            "sql_statement_count": 1,
            "growth_with_result_count": 0,
            "n_plus_one_forbidden": True,
            "query": {
                "query_id": query["query_id"],
                "operation": query["operation"],
                "source": str(adapter_path.relative_to(root)),
                "parameters": query["parameters"],
                "sql": query["sql"],
                "sql_sha256": sha256_text(query["sql"]),
                "assertions_passed": checks,
                "plan_summary": summary,
                "normalized_explain_analyze": normalized,
            },
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
            "retained": [
                "plan node types and depth",
                "actual rows and loops",
                "plan row estimates and costs",
                "group and sort keys",
                "relation and index names",
                "which BUFFERS fields were emitted",
            ],
        },
        "interpretation": {
            "status": "observational_evidence_only",
            "statement": (
                "This isolated synthetic capture proves one bounded SQL execution and no N+1. "
                "It is not a production latency SLA or an index recommendation."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/capture_phase4a_question_type_query_plan.py "
                "--output Ti-Java/docs/refactor/phase4a/question-type-query-plan-evidence.json"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": "ephemeral network-disabled container removed on success or failure",
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
    runtime_manifest = load_runtime_sql_manifest(manifest_path)
    container = "ti-phase4a-question-type-plan-" + uuid.uuid4().hex[:12]
    started = False
    try:
        result = run([
            "docker", "run", "--detach", "--rm", "--name", container,
            "--network", "none",
            "--env", "POSTGRES_PASSWORD=postgres",
            "--env", f"POSTGRES_DB={DEFAULT_DATABASE}",
            args.image,
        ], check=False)
        if result.returncode != 0:
            raise RuntimeError(f"could not start PostgreSQL: {result.stderr.strip()[-3000:]}")
        started = True
        wait_until_ready(container, args.startup_timeout_seconds)
        psql(container, fixture_sql(args))
        document = capture(args, container, runtime_manifest, manifest_path)
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.resolve().write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            "captured question-type plan "
            f"sql_sha256={document['measurement']['query']['sql_sha256']}"
        )
        return 0
    finally:
        if started:
            run(["docker", "rm", "--force", container], check=False)
        if run(["docker", "inspect", container], check=False).returncode == 0:
            raise RuntimeError(f"temporary PostgreSQL container was not removed: {container}")


if __name__ == "__main__":
    raise SystemExit(main())
