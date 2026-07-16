#!/usr/bin/env python3
"""Capture deterministic PG18 evidence for the raw subject-inventory query.

The runtime SELECT is exported from the Java JDBC adapter for every capture.
This tool owns only a public synthetic fixture, exact-result checks, normalized
plan observations, and fail-closed evidence gates. It never keeps a second SQL
statement that can be executed in place of the Java runtime statement.
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
DEFAULT_DATABASE = "phase4a_subject_inventory_plan"
DEFAULT_SUBJECT_COUNT = 5_000
DEFAULT_QUESTION_COUNT = 150_000

MANIFEST_ID = "ti.phase4a.subject-inventory-runtime-sql"
ADAPTER_CLASS = (
    "io.saksk.ti.catalog.infrastructure.persistence."
    "JdbcSubjectInventoryQueryAdapter"
)
QUERY_ID = "subject-inventory-summaries"
OPERATION = "subject-inventory"
EXPECTED_COLUMNS = (
    "s.id as subject_id",
    "s.name as subject_name",
    "s.is_locked as subject_locked",
    "count(q.id) as question_count",
)
EXPECTED_NORMALIZED_SQL = (
    f"select {', '.join(EXPECTED_COLUMNS)} from subjects s "
    "left join questions q on s.id = q.subject_id "
    "group by s.id, s.name, s.is_locked order by s.id asc"
)

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
    "Group Key",
    "Sort Key",
}
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "secret",
    "authorization",
    "credential",
    "cookie",
    "private_key",
    "access_token",
    "refresh_token",
    "dsn",
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported Phase 4A subject-inventory plan evidence."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root
        / "docs/refactor/phase4a/subject-inventory-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-subject-inventory-runtime-sql.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--subject-count", type=int, default=DEFAULT_SUBJECT_COUNT
    )
    parser.add_argument(
        "--question-count", type=int, default=DEFAULT_QUESTION_COUNT
    )
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.subject_count < DEFAULT_SUBJECT_COUNT:
        raise ValueError(
            f"--subject-count must be at least {DEFAULT_SUBJECT_COUNT}"
        )
    if args.question_count < DEFAULT_QUESTION_COUNT:
        raise ValueError(
            f"--question-count must be at least {DEFAULT_QUESTION_COUNT}"
        )
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
            "-q",
            "-DskipITs",
            "-Dtest=SubjectInventoryRuntimeSqlManifestTest",
            f"-Dti.subject-inventory.sql-manifest-output={output}",
            "test",
        ],
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java runtime SQL export failed: {detail}")


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).lower()


def validate_runtime_sql(sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError("subject-inventory runtime SQL is empty")
    if ";" in stripped:
        raise RuntimeError("subject-inventory runtime SQL contains a separator")
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError("subject-inventory runtime SQL must contain one SELECT")
    forbidden = FORBIDDEN_RUNTIME_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(
            "subject-inventory runtime SQL contains forbidden token "
            f"{forbidden.group(0)}"
        )
    if re.search(r"\bpg_temp\b", stripped, re.IGNORECASE):
        raise RuntimeError("subject-inventory runtime SQL references pg_temp")
    if re.search(
        r"\bselect\s+(?:(?:[A-Za-z][A-Za-z0-9_]*)\.)?\*",
        stripped,
        re.IGNORECASE,
    ):
        raise RuntimeError("subject-inventory SQL must use four explicit columns")
    if NAMED_PARAMETER.search(stripped):
        raise RuntimeError("subject-inventory SQL must remain parameter-free")
    if normalize_sql(stripped) != EXPECTED_NORMALIZED_SQL:
        raise RuntimeError(
            "subject-inventory runtime SQL shape drifted: "
            f"{normalize_sql(stripped)}"
        )


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java runtime SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID:
        raise RuntimeError("subject-inventory runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("subject-inventory runtime SQL manifest schema drifted")
    if manifest.get("adapter_class") != ADAPTER_CLASS:
        raise RuntimeError("subject-inventory runtime adapter class drifted")
    queries = manifest.get("queries")
    if (
        not isinstance(queries, list)
        or manifest.get("query_count") != 1
        or len(queries) != 1
        or not isinstance(queries[0], dict)
    ):
        raise RuntimeError("subject-inventory manifest must contain one query")
    query = queries[0]
    if query.get("query_id") != QUERY_ID:
        raise RuntimeError("subject-inventory runtime query ID drifted")
    if query.get("operation") != OPERATION:
        raise RuntimeError("subject-inventory runtime operation drifted")
    if query.get("parameters") != {}:
        raise RuntimeError("subject-inventory runtime query must have zero parameters")
    if not isinstance(query.get("sql"), str):
        raise RuntimeError("subject-inventory runtime SQL must be text")
    validate_runtime_sql(query["sql"])
    return manifest


def fixture_shape(args: argparse.Namespace) -> dict[str, int]:
    assigned_subject_count = args.subject_count * 4 // 5
    generated_question_count = args.question_count - 3
    null_assignment_count = generated_question_count // 997 + 1
    orphan_assignment_count = 1
    assigned_question_count = (
        args.question_count - null_assignment_count - orphan_assignment_count
    )
    total_subject_count = args.subject_count + 2
    true_lock_count = args.subject_count // 20 + 1
    null_lock_count = (args.subject_count + 19) // 20 + 1
    false_lock_count = total_subject_count - true_lock_count - null_lock_count
    return {
        "positive_subject_count": args.subject_count,
        "total_subject_count": total_subject_count,
        "question_count": args.question_count,
        "assigned_subject_count": assigned_subject_count,
        "generated_question_count": generated_question_count,
        "null_assignment_count": null_assignment_count,
        "orphan_assignment_count": orphan_assignment_count,
        "assigned_question_count": assigned_question_count,
        "zero_question_subject_count": (
            args.subject_count - assigned_subject_count + 1
        ),
        "true_lock_count": true_lock_count,
        "false_lock_count": false_lock_count,
        "null_lock_count": null_lock_count,
        "empty_name_count": 1,
        "unicode_name_count": 1,
    }


def fixture_sql(args: argparse.Namespace) -> str:
    shape = fixture_shape(args)
    orphan_subject_id = args.subject_count + 1001
    orphan_question_id = args.question_count - 2
    return f"""
CREATE TABLE subjects (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    is_locked boolean DEFAULT false
);

CREATE TABLE questions (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    subject_id integer REFERENCES subjects(id) ON DELETE SET NULL,
    type text NOT NULL,
    content text NOT NULL
);

INSERT INTO subjects (id, name, is_locked) VALUES
    (-1, '', NULL),
    (0, '科目 🧪', true);

INSERT INTO subjects (id, name, is_locked)
SELECT n,
       'Synthetic subject ' || n,
       CASE
           WHEN n % 20 = 0 THEN true
           WHEN n % 20 = 1 THEN NULL
           ELSE false
       END
FROM generate_series(1, {args.subject_count}) AS generated(n);

INSERT INTO questions (id, subject_id, type, content) VALUES
    (-1, -1, 'essay', 'Signed negative subject assignment'),
    (0, NULL, 'fill', 'Explicit unassigned question');

INSERT INTO questions (id, subject_id, type, content)
SELECT n,
       CASE
           WHEN n % 997 = 0 THEN NULL
           ELSE ((n - 1) % {shape['assigned_subject_count']}) + 1
       END,
       (ARRAY['single_choice', 'multi_choice', 'boolean', 'fill', 'essay'])[
           1 + ((n - 1) % 5)
       ],
       'Synthetic inventory question ' || n
FROM generate_series(1, {shape['generated_question_count']}) AS generated(n);

-- Preserve a deterministic inconsistent legacy restore edge without weakening
-- the production-compatible foreign key for the rest of the fixture.
SET session_replication_role = replica;
INSERT INTO questions (id, subject_id, type, content) VALUES
    ({orphan_question_id}, {orphan_subject_id}, 'essay', 'Orphan assignment edge');
SET session_replication_role = DEFAULT;

-- TEST-ONLY synthetic indexes mirror observed legacy migrations. This plan
-- evidence neither approves nor creates a production index.
CREATE INDEX ix_questions_subject_id ON questions (subject_id);
CREATE INDEX ix_questions_subject_type ON questions (subject_id, type);

ALTER TABLE questions ALTER COLUMN subject_id SET STATISTICS 10000;

VACUUM (ANALYZE) subjects;
VACUUM (ANALYZE) questions;
"""


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
            "Group Key",
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
    return {
        "root_node_type": root.get("Node Type"),
        "result_row_count": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max(node["depth"] for node in nodes),
        "maximum_actual_loops": max(loops, default=0),
        "node_type_counts": dict(sorted(node_types.items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "index_names": sorted(
            {str(node["Index Name"]) for node in nodes if "Index Name" in node}
        ),
        "buffer_fields_observed_before_normalization": sorted(buffer_fields),
        "nodes": nodes,
    }


def _lock_label(raw: str) -> str:
    if raw == "":
        return "null"
    if raw == "t":
        return "true"
    if raw == "f":
        return "false"
    raise AssertionError(f"unexpected PostgreSQL boolean text: {raw}")


def parse_result_rows(raw: str, positive_subject_count: int) -> dict[str, Any]:
    lines = raw.splitlines() if raw else []
    expected_ids = [-1, 0, *range(1, positive_subject_count + 1)]
    ids: list[int] = []
    lock_counts: Counter[str] = Counter()
    question_count_sum = 0
    zero_question_subjects = 0
    empty_names = 0
    unicode_names = 0
    edge_rows: dict[str, dict[str, Any]] = {}

    for index, line in enumerate(lines):
        fields = line.split("|")
        if len(fields) != len(EXPECTED_COLUMNS):
            raise AssertionError(
                f"runtime result column count drifted: {len(fields)}"
            )
        if not re.fullmatch(r"-?[0-9]+", fields[0]):
            raise AssertionError(f"subject ID is not an integer: {fields[0]}")
        if not re.fullmatch(r"[0-9]+", fields[3]):
            raise AssertionError(f"question count is not non-negative: {fields[3]}")
        subject_id = int(fields[0])
        name = fields[1]
        lock = _lock_label(fields[2])
        question_count = int(fields[3])
        ids.append(subject_id)
        lock_counts[lock] += 1
        question_count_sum += question_count
        zero_question_subjects += int(question_count == 0)
        empty_names += int(name == "")
        unicode_names += int(any(ord(character) > 127 for character in name))
        if subject_id in {-1, 0, positive_subject_count}:
            edge_rows[str(subject_id)] = {
                "id": subject_id,
                "name": name,
                "is_locked": None if lock == "null" else lock == "true",
                "question_count": question_count,
            }
        if index >= len(expected_ids) or subject_id != expected_ids[index]:
            raise AssertionError(
                "subject-inventory results are not the exact signed id ASC set"
            )

    if len(ids) != len(expected_ids):
        raise AssertionError(
            f"subject-inventory row count drifted: {len(ids)} != {len(expected_ids)}"
        )
    strictly_ascending = all(
        previous < current for previous, current in zip(ids, ids[1:])
    )
    if len(ids) > 1 and not strictly_ascending:
        raise AssertionError("subject-inventory results are not strictly id ASC")
    return {
        "row_count": len(ids),
        "minimum_id": ids[0] if ids else None,
        "maximum_id": ids[-1] if ids else None,
        "first_ids_asc": ids[:3],
        "last_ids_asc": ids[-3:],
        "strictly_ascending_by_id": strictly_ascending,
        "row_column_count": len(EXPECTED_COLUMNS),
        "lock_value_counts": dict(sorted(lock_counts.items())),
        "empty_name_count": empty_names,
        "unicode_name_count": unicode_names,
        "zero_question_subject_count": zero_question_subjects,
        "question_count_sum": question_count_sum,
        "edge_rows": edge_rows,
        "canonical_psql_rows_sha256": sha256_text(raw),
    }


def assert_runtime_result(
    result: dict[str, Any], shape: dict[str, int]
) -> list[str]:
    expected = {
        "row_count": shape["total_subject_count"],
        "minimum_id": -1,
        "maximum_id": shape["positive_subject_count"],
        "first_ids_asc": [-1, 0, 1],
        "last_ids_asc": [
            shape["positive_subject_count"] - 2,
            shape["positive_subject_count"] - 1,
            shape["positive_subject_count"],
        ],
        "strictly_ascending_by_id": True,
        "row_column_count": 4,
        "lock_value_counts": {
            "false": shape["false_lock_count"],
            "null": shape["null_lock_count"],
            "true": shape["true_lock_count"],
        },
        "empty_name_count": shape["empty_name_count"],
        "unicode_name_count": shape["unicode_name_count"],
        "zero_question_subject_count": shape["zero_question_subject_count"],
        "question_count_sum": shape["assigned_question_count"],
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise AssertionError(
                f"subject-inventory runtime result drifted for {key}: "
                f"{result.get(key)} != {value}"
            )
    negative = result["edge_rows"].get("-1")
    zero = result["edge_rows"].get("0")
    maximum = result["edge_rows"].get(str(shape["positive_subject_count"]))
    if negative != {
        "id": -1,
        "name": "",
        "is_locked": None,
        "question_count": 1,
    }:
        raise AssertionError("negative subject edge drifted")
    if zero != {
        "id": 0,
        "name": "科目 🧪",
        "is_locked": True,
        "question_count": 0,
    }:
        raise AssertionError("zero/unicode subject edge drifted")
    if not maximum or maximum["question_count"] != 0:
        raise AssertionError("maximum signed fixture subject must retain zero count")
    return [
        "four-column-exact-result-shape",
        "strict-signed-id-asc-runtime-order",
        "true-false-null-locks-preserved",
        "empty-and-unicode-names-preserved",
        "zero-question-subjects-preserved",
        "count-q-id-excludes-null-and-orphan-assignments",
    ]


def assert_plan(
    result: dict[str, Any],
    shape: dict[str, int],
    summary: dict[str, Any],
    temp_blocks: dict[str, float],
    binding: dict[str, Any],
) -> list[str]:
    passed = assert_runtime_result(result, shape)
    if summary["result_row_count"] != shape["total_subject_count"]:
        raise AssertionError("subject-inventory plan result row count drifted")
    passed.append("plan-row-count-matches-all-subjects")
    if summary["root_actual_loops"] != 1 or summary["maximum_actual_loops"] != 1:
        raise AssertionError("subject-inventory plan must execute every node once")
    passed.append("single-execution-no-row-driven-loop")
    if summary["node_count"] > 8 or summary["maximum_depth"] > 5:
        raise AssertionError("subject-inventory plan exceeded node/depth bounds")
    passed.append("bounded-plan-shape")
    if summary["relation_scan_occurrences"] != {
        "questions": 1,
        "subjects": 1,
    }:
        raise AssertionError(
            "subject-inventory relation budget drifted: "
            f"{summary['relation_scan_occurrences']}"
        )
    passed.append("subjects-and-questions-scanned-once-only")
    join_nodes = [
        node
        for node in summary["nodes"]
        if str(node.get("Node Type", "")).endswith("Join")
        or node.get("Node Type") == "Nested Loop"
    ]
    if len(join_nodes) != 1 or join_nodes[0].get("Join Type") not in {
        "Left",
        "Right",
    }:
        raise AssertionError(
            "subject-inventory plan must preserve one outer join; LEFT/RIGHT swap allowed"
        )
    passed.append("one-outer-join-left-right-planner-swap-allowed")
    if summary["node_type_counts"].get("Aggregate", 0) != 1:
        raise AssertionError("subject-inventory plan must contain one aggregate")
    passed.append("one-question-count-aggregate")
    for key in ("Temp Read Blocks", "Temp Written Blocks"):
        if key not in temp_blocks or temp_blocks[key] != 0:
            raise AssertionError(f"subject-inventory plan used TEMP blocks: {temp_blocks}")
    passed.append("zero-temp-blocks")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise AssertionError("subject-inventory BUFFERS evidence was not emitted")
    passed.append("buffers-captured-before-normalization")
    expected_binding = {
        "mode": "parameter-free",
        "bound_parameter_count": 0,
        "named_parameter_count": 0,
        "occurrence_names": [],
        "parameters": {},
    }
    if binding != expected_binding:
        raise AssertionError(f"subject-inventory bind surface drifted: {binding}")
    passed.append("one-select-zero-bind-fixed-cardinality")
    return passed


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
    'minimum_subject_id', (SELECT MIN(id) FROM subjects),
    'maximum_subject_id', (SELECT MAX(id) FROM subjects),
    'locked_subjects', (SELECT COUNT(*) FROM subjects WHERE is_locked IS true),
    'unlocked_subjects', (SELECT COUNT(*) FROM subjects WHERE is_locked IS false),
    'nullable_lock_subjects', (SELECT COUNT(*) FROM subjects WHERE is_locked IS NULL),
    'empty_name_subjects', (SELECT COUNT(*) FROM subjects WHERE name = ''),
    'unicode_name_subjects', (SELECT COUNT(*) FROM subjects WHERE name = '科目 🧪'),
    'zero_question_subjects', (
        SELECT COUNT(*) FROM subjects s
        WHERE NOT EXISTS (SELECT 1 FROM questions q WHERE q.subject_id = s.id)
    ),
    'null_question_assignments', (
        SELECT COUNT(*) FROM questions WHERE subject_id IS NULL
    ),
    'orphan_question_assignments', (
        SELECT COUNT(*)
        FROM questions q
        LEFT JOIN subjects s ON s.id = q.subject_id
        WHERE q.subject_id IS NOT NULL AND s.id IS NULL
    ),
    'assigned_question_count', (
        SELECT COUNT(q.id)
        FROM subjects s
        JOIN questions q ON q.subject_id = s.id
    )
);
""")


def assert_dataset_metadata(
    actual: dict[str, Any], shape: dict[str, int]
) -> None:
    expected = {
        "subjects": shape["total_subject_count"],
        "questions": shape["question_count"],
        "minimum_subject_id": -1,
        "maximum_subject_id": shape["positive_subject_count"],
        "locked_subjects": shape["true_lock_count"],
        "unlocked_subjects": shape["false_lock_count"],
        "nullable_lock_subjects": shape["null_lock_count"],
        "empty_name_subjects": shape["empty_name_count"],
        "unicode_name_subjects": shape["unicode_name_count"],
        "zero_question_subjects": shape["zero_question_subject_count"],
        "null_question_assignments": shape["null_assignment_count"],
        "orphan_question_assignments": shape["orphan_assignment_count"],
        "assigned_question_count": shape["assigned_question_count"],
    }
    if actual != expected:
        raise AssertionError(
            f"subject-inventory synthetic fixture drifted: {actual} != {expected}"
        )


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


def required_input_paths(root: Path, manifest_path: Path) -> dict[str, Path]:
    return {
        "adapter": root
        / "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "JdbcSubjectInventoryQueryAdapter.java",
        "runtime_sql_manifest": manifest_path,
        "runtime_sql_exporter": root
        / "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "SubjectInventoryRuntimeSqlManifestTest.java",
        "capture_tool": Path(__file__).resolve(),
        "capture_tool_test": Path(__file__).with_name(
            "test_capture_phase4a_subject_inventory_query_plan.py"
        ).resolve(),
    }


def assert_runtime_sql_hash_closure(
    recorded_hash: str, manifest: dict[str, Any]
) -> None:
    current = sha256_text(manifest["queries"][0]["sql"])
    if current != recorded_hash:
        raise AssertionError("subject-inventory runtime SQL hash drifted after capture")


def assert_input_hash_closure(
    recorded: dict[str, Any], paths: dict[str, Path]
) -> None:
    for key, path in paths.items():
        field = f"{key}_sha256"
        if recorded.get(field) != sha256_file(path):
            raise AssertionError(f"subject-inventory source drifted: {key}")


def assert_public_evidence(document: Any) -> None:
    ephemeral_container = re.compile(
        r"ti-phase4a-subject-inventory-plan-[0-9a-f]{12}"
    )

    def visit(value: Any, key: str = "") -> None:
        lowered = key.lower()
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


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def capture(
    args: argparse.Namespace,
    container: str,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    query = manifest["queries"][0]
    validate_runtime_sql(query["sql"])
    shape = fixture_shape(args)
    dataset = dataset_metadata(container)
    assert_dataset_metadata(dataset, shape)

    raw_rows = psql(container, query["sql"])
    result = parse_result_rows(raw_rows, args.subject_count)

    raw_explain = psql_json(
        container,
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + query["sql"] + ";",
    )
    if not isinstance(raw_explain, list) or len(raw_explain) != 1:
        raise RuntimeError("unexpected subject-inventory EXPLAIN JSON payload")
    buffer_fields = collect_numeric_fields(raw_explain[0], BUFFER_KEYS)
    temp_blocks = {
        key: buffer_fields.get(key)
        for key in ("Temp Read Blocks", "Temp Written Blocks")
    }
    normalized = normalize_explain(raw_explain[0])
    summary = summarize_plan(normalized, buffer_fields)
    binding = {
        "mode": "parameter-free",
        "bound_parameter_count": 0,
        "named_parameter_count": 0,
        "occurrence_names": [],
        "parameters": {},
    }
    assertions = assert_plan(result, shape, summary, temp_blocks, binding)

    root = Path(__file__).resolve().parents[1]
    paths = required_input_paths(root, manifest_path)
    inputs: dict[str, Any] = {}
    for key, path in paths.items():
        inputs[key] = str(path.relative_to(root))
        inputs[f"{key}_sha256"] = sha256_file(path)
    runtime_sql_sha256 = sha256_text(query["sql"])

    document = {
        "evidence_id": "ti.phase4a.subject-inventory-query-plan",
        "schema_version": 1,
        "captured_at": "2026-07-16",
        "scope": "catalog-subject-inventory-internal-read-capability",
        "route_migration_status": {
            "route_ids": ["6e1a36f5052d"],
            "http_owner": "operations",
            "status": "pending",
            "production_cutover": False,
        },
        "environment": {
            "container_image": args.image,
            **image_metadata(args.image),
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment_metadata(container),
        },
        "inputs": inputs,
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "positive_subject_count": args.subject_count,
                "signed_edge_subject_count": 2,
                "total_subject_count": shape["total_subject_count"],
                "question_count": args.question_count,
                "assigned_positive_subject_count": shape[
                    "assigned_subject_count"
                ],
            },
            "actual": dataset,
            "distribution": {
                "subject_ids": "-1, 0, and the inclusive range 1..5000",
                "locked": "positive subject_id divisible by 20, plus subject 0",
                "nullable_lock": "positive subject_id congruent to 1 mod 20, plus -1",
                "question_subject": (
                    "round-robin over the first 80 percent of positive subjects; "
                    "every 997th generated question and id 0 are unassigned"
                ),
                "orphan_assignment": "one explicit test-only restored inconsistency",
                "names": "one exact empty string and one public Unicode synthetic name",
            },
            "statistics": (
                "questions.subject_id statistics target 10000; VACUUM (ANALYZE) "
                "completed for both relations before capture"
            ),
            "index_definitions": index_definitions(container),
            "index_decision": (
                "observe existing primary, subject_id and subject_id+type indexes only; "
                "this synthetic evidence does not approve a production index"
            ),
        },
        "measurement": {
            "command": "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) exact Java runtime SQL",
            "runs_per_query": 1,
            "query_count": 1,
            "sql_statement_count": 1,
            "growth_with_result_count": 0,
            "n_plus_one_forbidden": True,
            "observation": {
                "observation_id": "all-subject-inventory",
                "runtime_query_id": query["query_id"],
                "operation": query["operation"],
                "source": inputs["adapter"],
                "sql": query["sql"],
                "sql_sha256": runtime_sql_sha256,
                "binding": binding,
                "runtime_result": result,
                "temp_blocks_observed": temp_blocks,
                "assertions_passed": assertions,
                "plan_summary": summary,
                "normalized_explain_analyze": normalized,
            },
        },
        "normalization": {
            "removed": [
                "planning and execution timing",
                "per-node actual timing",
                "cache-dependent buffer block counts",
                "planner estimates and costs",
                "runtime memory, hash and worker counters",
                "container ID and ephemeral container name",
            ],
            "retained": [
                "plan node types and depth",
                "actual rows and loops",
                "outer join and aggregate strategy",
                "relation and index names",
                "redacted hashes of planner expressions",
                "which BUFFERS fields were emitted",
            ],
        },
        "interpretation": {
            "status": "observational_evidence_only",
            "statement": (
                "This isolated synthetic capture proves one bounded execution, exact "
                "signed-id ordering, LEFT-join inventory semantics and no N+1. It is "
                "not a production latency SLA, capacity claim or index recommendation."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/"
                "capture_phase4a_subject_inventory_query_plan.py --output "
                "Ti-Java/docs/refactor/phase4a/"
                "subject-inventory-query-plan-evidence.json"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": "ephemeral network-disabled container removed on all exits",
        },
    }
    assert_runtime_sql_hash_closure(runtime_sql_sha256, manifest)
    assert_input_hash_closure(inputs, paths)
    assert_public_evidence(document)
    return document


def cleanup_container(container: str) -> None:
    run(["docker", "rm", "--force", container], check=False)
    if run(["docker", "inspect", container], check=False).returncode == 0:
        raise RuntimeError(
            f"temporary subject-inventory PostgreSQL container remains: {container}"
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
    container = "ti-phase4a-subject-inventory-plan-" + uuid.uuid4().hex[:12]
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
        write_json_atomic(args.output, document)
        print(
            "captured subject-inventory plan "
            f"sql_sha256={document['measurement']['observation']['sql_sha256']}"
        )
        return 0
    finally:
        if started:
            cleanup_container(container)


if __name__ == "__main__":
    raise SystemExit(main())
