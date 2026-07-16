#!/usr/bin/env python3
"""Capture deterministic PostgreSQL 18 evidence for category-list runtime SQL."""

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
from typing import Any, Iterable, Mapping, Optional
import uuid


DEFAULT_IMAGE = (
    "postgres:18.4-alpine@"
    "sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
DEFAULT_DATABASE = "phase4b_personal_bank_category_plan"
DEFAULT_CATEGORY_COUNT = 5_000
DEFAULT_BANK_COUNT = 150_000
CURRENT_USER_ID = 9_001
OTHER_USER_ID = 9_002

MANIFEST_ID = "ti.phase4b.personal-bank-category-runtime-sql"
ADAPTER_CLASS = (
    "io.saksk.ti.personalbank.infrastructure.persistence."
    "JdbcPersonalBankCategoryQueryAdapter"
)
QUERY_ID = "personal-bank-category-list"
OPERATION = "personal-bank-category-list"
EXPECTED_COLUMNS = (
    "c.id as category_id",
    "c.user_id as category_user_id",
    "c.name as category_name",
    "c.description as category_description",
    "c.sort_order as category_sort_order",
    "c.created_at as category_created_at",
    "c.updated_at as category_updated_at",
    "count(b.id) as bank_count",
)
EXPECTED_NORMALIZED_SQL = (
    f"select {', '.join(EXPECTED_COLUMNS)} from user_bank_categories c "
    "left join user_question_banks b on b.category_id = c.id and b.status = 1 "
    "where c.user_id = :user_id "
    "group by c.id, c.user_id, c.name, c.description, c.sort_order, "
    "c.created_at, c.updated_at "
    "order by c.sort_order asc nulls last, c.id asc"
)
NAMED_PARAMETER = re.compile(r"(?<!:):([A-Za-z][A-Za-z0-9_]*)")
FORBIDDEN_SQL = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|copy|call|do|"
    r"vacuum|analyze|refresh|grant|revoke|temporary|temp|limit|offset|fetch)\b",
    re.IGNORECASE,
)
VOLATILE_PLAN_KEYS = {
    "Planning Time", "Execution Time", "Actual Startup Time", "Actual Total Time",
    "Startup Cost", "Total Cost", "Plan Rows", "Plan Width", "Peak Memory Usage",
    "Sort Space Used", "Average Peak Memory", "Hash Buckets", "Hash Batches",
    "Original Hash Buckets", "Original Hash Batches", "Disk Usage", "Workers",
    "JIT",
}
BUFFER_KEYS = {
    "Shared Hit Blocks", "Shared Read Blocks", "Shared Dirtied Blocks",
    "Shared Written Blocks", "Local Hit Blocks", "Local Read Blocks",
    "Local Dirtied Blocks", "Local Written Blocks", "Temp Read Blocks",
    "Temp Written Blocks", "Exact Heap Blocks", "Lossy Heap Blocks", "Heap Fetches",
}
SENSITIVE_KEY_FRAGMENTS = (
    "password", "secret", "authorization", "credential", "cookie",
    "private_key", "access_token", "refresh_token", "dsn",
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported Phase 4B category query-plan evidence."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/refactor/phase4b/personal-bank-category-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4b-personal-bank-category-runtime-sql.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--category-count", type=int, default=DEFAULT_CATEGORY_COUNT)
    parser.add_argument("--bank-count", type=int, default=DEFAULT_BANK_COUNT)
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.category_count < DEFAULT_CATEGORY_COUNT:
        raise ValueError(f"--category-count must be at least {DEFAULT_CATEGORY_COUNT}")
    if args.bank_count < DEFAULT_BANK_COUNT:
        raise ValueError(f"--bank-count must be at least {DEFAULT_BANK_COUNT}")
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


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).lower()


def validate_runtime_sql(sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError("personal-bank category runtime SQL is empty")
    if ";" in stripped or "--" in stripped or "/*" in stripped:
        raise RuntimeError("runtime SQL contains a separator or comment")
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError("runtime SQL must contain exactly one SELECT")
    forbidden = FORBIDDEN_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(f"runtime SQL contains forbidden token {forbidden.group(0)}")
    if re.search(r"\b(?:pg_temp|pg_catalog)\b", stripped, re.IGNORECASE):
        raise RuntimeError("runtime SQL references a PostgreSQL system schema")
    if re.search(r"\bselect\s+(?:\w+\.)?\*", stripped, re.IGNORECASE):
        raise RuntimeError("runtime SQL must use eight explicit columns")
    if normalize_sql(stripped) != EXPECTED_NORMALIZED_SQL:
        raise RuntimeError("personal-bank category runtime SQL shape drifted")
    names = NAMED_PARAMETER.findall(stripped)
    if names != ["user_id"]:
        raise RuntimeError(f"runtime bind shape drifted: {names}")


def export_runtime_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("runtime SQL manifest must stay under server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = run([
        str(verifier),
        "-q",
        "-DskipITs",
        "-Dtest=PersonalBankCategoryRuntimeSqlManifestTest",
        f"-Dti.personal-bank-category.sql-manifest-output={output}",
        "test",
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java runtime SQL export failed: {detail}")


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java runtime SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID:
        raise RuntimeError("runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("runtime SQL manifest schema drifted")
    if manifest.get("adapter_class") != ADAPTER_CLASS:
        raise RuntimeError("runtime SQL adapter class drifted")
    queries = manifest.get("queries")
    if manifest.get("query_count") != 1 or not isinstance(queries, list) or len(queries) != 1:
        raise RuntimeError("runtime SQL manifest must contain exactly one query")
    query = queries[0]
    if not isinstance(query, dict):
        raise RuntimeError("runtime query must be an object")
    if query.get("query_id") != QUERY_ID or query.get("operation") != OPERATION:
        raise RuntimeError("runtime query identity drifted")
    if query.get("parameters") != {"user_id": "bigint"}:
        raise RuntimeError("runtime query parameter contract drifted")
    sql = query.get("sql")
    if not isinstance(sql, str):
        raise RuntimeError("runtime query SQL must be text")
    validate_runtime_sql(sql)
    return manifest


def prepared_sql(sql: str, user_id: int, *, explain: bool) -> tuple[str, dict[str, Any]]:
    validate_runtime_sql(sql)
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise RuntimeError("user_id must be a signed bigint")
    if not -(2**63) <= user_id <= 2**63 - 1:
        raise RuntimeError("user_id is outside signed bigint range")
    positional = NAMED_PARAMETER.sub("$1", sql)
    execution = f"EXECUTE phase4b_category_list({user_id})"
    statement = (
        "PREPARE phase4b_category_list(bigint) AS\n"
        + positional
        + ";\n"
        + ("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON, TIMING FALSE, SUMMARY FALSE)\n"
           if explain else "")
        + execution
        + ";\nDEALLOCATE phase4b_category_list;"
    )
    return statement, {
        "mode": "postgresql-prepare-execute",
        "runtime_statement_count": 1,
        "bound_parameter_count": 1,
        "named_parameter_count": 1,
        "occurrence_names": ["user_id"],
        "positional_sql_sha256": sha256_text(positional),
        "parameters": {
            "user_id": {
                "bind_kind": "postgresql-prepared-statement-parameter",
                "postgres_type": "bigint",
                "value": user_id,
            }
        },
    }


def fixture_sql(category_count: int, bank_count: int) -> str:
    return f"""
CREATE TABLE user_bank_categories (
    id integer PRIMARY KEY,
    user_id integer NOT NULL,
    name text NOT NULL,
    description text,
    sort_order integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    CONSTRAINT uq_user_bank_categories_user_name UNIQUE (user_id, name)
);
CREATE TABLE user_question_banks (
    id integer PRIMARY KEY,
    user_id integer NOT NULL,
    category_id integer REFERENCES user_bank_categories(id) ON DELETE SET NULL,
    name text NOT NULL,
    status integer
);

INSERT INTO user_bank_categories
    (id, user_id, name, description, sort_order, created_at, updated_at)
VALUES
    (-1, {CURRENT_USER_ID}, 'Negative category', 'signed identifier', -5,
     TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 09:00:00'),
    (0, {CURRENT_USER_ID}, '', '', 0,
     TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 09:00:00');

INSERT INTO user_bank_categories
    (id, user_id, name, description, sort_order, created_at, updated_at)
SELECT g,
       {CURRENT_USER_ID},
       CASE WHEN g = 1 THEN '高数・α／🧪' ELSE 'Category ' || g END,
       CASE WHEN g % 17 = 0 THEN NULL ELSE 'Description ' || g END,
       CASE WHEN g = {category_count} THEN NULL ELSE g % 50 END,
       CASE WHEN g % 19 = 0 THEN NULL ELSE TIMESTAMP '2026-07-17 08:00:00' END,
       CASE WHEN g % 23 = 0 THEN NULL ELSE TIMESTAMP '2026-07-17 09:00:00' END
FROM generate_series(1, {category_count}) AS g;

INSERT INTO user_bank_categories
    (id, user_id, name, description, sort_order, created_at, updated_at)
VALUES
    ({category_count + 1000}, {OTHER_USER_ID}, 'Other identity category',
     'must remain isolated', -100, TIMESTAMP '2026-07-17 08:00:00',
     TIMESTAMP '2026-07-17 09:00:00');

INSERT INTO user_question_banks (id, user_id, category_id, name, status)
SELECT CASE WHEN g = 1 THEN -1 WHEN g = 2 THEN 0 ELSE g - 2 END,
       CASE WHEN g % 7 = 0 THEN {OTHER_USER_ID} ELSE {CURRENT_USER_ID} END,
       CASE
           WHEN g = 1 THEN -1
           WHEN g = 2 THEN 0
           WHEN g = 3 THEN {category_count + 1000}
           ELSE ((g - 4) % {category_count * 4 // 5}) + 1
       END,
       'Bank ' || g,
       CASE
           WHEN g % 101 = 0 THEN 2
           WHEN g % 103 = 0 THEN NULL
           WHEN g % 10 = 0 THEN 0
           ELSE 1
       END
FROM generate_series(1, {bank_count}) AS g;

ALTER TABLE user_question_banks ALTER COLUMN category_id SET STATISTICS 10000;
VACUUM (ANALYZE) user_bank_categories;
VACUUM (ANALYZE) user_question_banks;
"""


def psql(container: str, sql: str, *, separator: str = "|") -> str:
    result = run([
        "docker", "exec", "--interactive",
        "--env=PGOPTIONS=-c max_parallel_workers_per_gather=0 -c work_mem=64MB",
        container,
        "psql", "--username=postgres", f"--dbname={DEFAULT_DATABASE}",
        "--no-psqlrc", "--quiet", "--tuples-only", "--no-align",
        f"--field-separator={separator}", "--pset=null=<NULL>",
        "--set=ON_ERROR_STOP=1",
    ], input_text=sql.rstrip() + "\n", check=False)
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
        raise RuntimeError(f"PostgreSQL returned invalid JSON: {raw[:1000]}") from exc


def wait_until_ready(container: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        ready = run([
            "docker", "exec", container, "pg_isready", "--username=postgres",
            f"--dbname={DEFAULT_DATABASE}",
        ], check=False)
        if ready.returncode == 0:
            return
        time.sleep(1)
    logs = run(["docker", "logs", container], check=False)
    raise RuntimeError("PostgreSQL did not become ready: " + (logs.stdout + logs.stderr)[-3000:])


def dataset_metadata(container: str) -> dict[str, Any]:
    return psql_json(container, f"""
SELECT json_build_object(
    'category_user_id_type', (SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        WHERE a.attrelid = 'user_bank_categories'::regclass
          AND a.attname = 'user_id' AND NOT a.attisdropped),
    'bank_user_id_type', (SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        WHERE a.attrelid = 'user_question_banks'::regclass
          AND a.attname = 'user_id' AND NOT a.attisdropped),
    'category_rows', (SELECT COUNT(*) FROM user_bank_categories),
    'current_user_category_rows', (SELECT COUNT(*) FROM user_bank_categories
        WHERE user_id = {CURRENT_USER_ID}),
    'other_user_category_rows', (SELECT COUNT(*) FROM user_bank_categories
        WHERE user_id = {OTHER_USER_ID}),
    'bank_rows', (SELECT COUNT(*) FROM user_question_banks),
    'status_one_bank_rows', (SELECT COUNT(*) FROM user_question_banks WHERE status = 1),
    'status_zero_bank_rows', (SELECT COUNT(*) FROM user_question_banks WHERE status = 0),
    'status_two_bank_rows', (SELECT COUNT(*) FROM user_question_banks WHERE status = 2),
    'status_null_bank_rows', (SELECT COUNT(*) FROM user_question_banks WHERE status IS NULL),
    'non_one_bank_rows', (SELECT COUNT(*) FROM user_question_banks WHERE status IS DISTINCT FROM 1),
    'cross_owner_active_associations', (SELECT COUNT(*)
        FROM user_question_banks b JOIN user_bank_categories c ON c.id = b.category_id
        WHERE c.user_id = {CURRENT_USER_ID} AND b.user_id <> c.user_id AND b.status = 1),
    'current_user_active_associations', (SELECT COUNT(*)
        FROM user_question_banks b JOIN user_bank_categories c ON c.id = b.category_id
        WHERE c.user_id = {CURRENT_USER_ID} AND b.status = 1),
    'zero_active_bank_categories', (SELECT COUNT(*) FROM user_bank_categories c
        WHERE c.user_id = {CURRENT_USER_ID} AND NOT EXISTS (
            SELECT 1 FROM user_question_banks b WHERE b.category_id = c.id AND b.status = 1)),
    'null_sort_categories', (SELECT COUNT(*) FROM user_bank_categories
        WHERE user_id = {CURRENT_USER_ID} AND sort_order IS NULL),
    'empty_name_categories', (SELECT COUNT(*) FROM user_bank_categories
        WHERE user_id = {CURRENT_USER_ID} AND name = ''),
    'unicode_name_categories', (SELECT COUNT(*) FROM user_bank_categories
        WHERE user_id = {CURRENT_USER_ID} AND name = '高数・α／🧪')
)::text;
""")


def expected_bank_status_counts(bank_count: int) -> dict[str, int]:
    counts = {"status_one_bank_rows": 0, "status_zero_bank_rows": 0,
              "status_two_bank_rows": 0, "status_null_bank_rows": 0}
    for row_id in range(1, bank_count + 1):
        if row_id % 101 == 0:
            key = "status_two_bank_rows"
        elif row_id % 103 == 0:
            key = "status_null_bank_rows"
        elif row_id % 10 == 0:
            key = "status_zero_bank_rows"
        else:
            key = "status_one_bank_rows"
        counts[key] += 1
    return counts


def current_user_category_ids_description(category_count: int) -> str:
    if isinstance(category_count, bool) or not isinstance(category_count, int):
        raise ValueError("category_count must be an integer")
    if category_count < 1:
        raise ValueError("category_count must be positive")
    return f"-1, 0 and inclusive 1..{category_count}"


def index_definitions(container: str) -> list[dict[str, str]]:
    value = psql_json(container, """
SELECT COALESCE(json_agg(json_build_object(
    'table', tablename, 'name', indexname, 'definition', indexdef
) ORDER BY tablename, indexname), '[]'::json)::text
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('user_bank_categories', 'user_question_banks');
""")
    if not isinstance(value, list):
        raise RuntimeError("index metadata must be a JSON array")
    return value


def runtime_sql_with_literal(sql: str, user_id: int) -> str:
    validate_runtime_sql(sql)
    return NAMED_PARAMETER.sub(f"{user_id}::bigint", sql)


def parse_result_rows(raw: str, category_count: int) -> dict[str, Any]:
    lines = raw.splitlines() if raw else []
    rows: list[dict[str, Any]] = []
    for line in lines:
        fields = line.split("\x1f")
        if len(fields) != 8:
            raise AssertionError(f"runtime row column count drifted: {fields}")
        rows.append({
            "id": int(fields[0]),
            "user_id": int(fields[1]),
            "name": fields[2],
            "description": None if fields[3] == "<NULL>" else fields[3],
            "sort_order": None if fields[4] == "<NULL>" else int(fields[4]),
            "created_at": None if fields[5] == "<NULL>" else fields[5],
            "updated_at": None if fields[6] == "<NULL>" else fields[6],
            "bank_count": int(fields[7]),
        })
    expected_rows = category_count + 2
    if len(rows) != expected_rows:
        raise AssertionError(f"expected {expected_rows} category rows, got {len(rows)}")
    if any(row["user_id"] != CURRENT_USER_ID for row in rows):
        raise AssertionError("category query leaked another identity")
    keys = [
        (row["sort_order"] is None, row["sort_order"] or 0, row["id"])
        for row in rows
    ]
    if keys != sorted(keys):
        raise AssertionError("category result order drifted")
    if rows[0]["id"] != -1 or rows[-1]["id"] != category_count:
        raise AssertionError("signed or NULLS LAST edge order drifted")
    return {
        "row_count": len(rows),
        "row_column_count": 8,
        "first_ids": [row["id"] for row in rows[:3]],
        "last_ids": [row["id"] for row in rows[-3:]],
        "first_id": rows[0]["id"],
        "last_id": rows[-1]["id"],
        "all_current_user": True,
        "strict_sort_order_asc_nulls_last_then_id_asc": True,
        "null_sort_rows": sum(row["sort_order"] is None for row in rows),
        "null_description_rows": sum(row["description"] is None for row in rows),
        "null_created_at_rows": sum(row["created_at"] is None for row in rows),
        "null_updated_at_rows": sum(row["updated_at"] is None for row in rows),
        "empty_name_rows": sum(row["name"] == "" for row in rows),
        "unicode_name_rows": sum(row["name"] == "高数・α／🧪" for row in rows),
        "zero_bank_count_rows": sum(row["bank_count"] == 0 for row in rows),
        "active_bank_count_sum": sum(row["bank_count"] for row in rows),
        "negative_category_bank_count": next(
            row["bank_count"] for row in rows if row["id"] == -1
        ),
        "zero_category_bank_count": next(
            row["bank_count"] for row in rows if row["id"] == 0
        ),
        "canonical_psql_rows_sha256": sha256_text(raw),
    }


def plan_nodes(root: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: Mapping[str, Any], depth: int) -> None:
        summary: dict[str, Any] = {"depth": depth}
        for key in (
            "Node Type", "Parent Relationship", "Strategy", "Join Type",
            "Relation Name", "Alias", "Index Name", "Scan Direction", "Sort Method",
            "Actual Rows", "Actual Loops", "Rows Removed by Filter", "Group Key", "Sort Key",
        ):
            if key in node:
                summary[key] = node[key]
        nodes.append(summary)
        for child in node.get("Plans", []):
            visit(child, depth + 1)

    visit(root, 0)
    return nodes


def collect_buffer_fields(value: Any) -> dict[str, float]:
    totals: Counter[str] = Counter()

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                if key in BUFFER_KEYS and isinstance(child, (int, float)):
                    totals[key] += float(child)
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return dict(sorted(totals.items()))


def summarize_plan(explain: Mapping[str, Any]) -> dict[str, Any]:
    root = explain["Plan"]
    nodes = plan_nodes(root)
    relation_nodes = [node for node in nodes if "Relation Name" in node]
    relations = Counter(str(node["Relation Name"]) for node in relation_nodes)
    loops = [int(node.get("Actual Loops", 0)) for node in nodes]
    relation_loops: dict[str, list[int]] = {}
    for node in relation_nodes:
        relation_loops.setdefault(str(node["Relation Name"]), []).append(
            int(node.get("Actual Loops", 0))
        )
    return {
        "root_node_type": root.get("Node Type"),
        "result_row_count": int(root.get("Actual Rows", 0)),
        "root_actual_loops": int(root.get("Actual Loops", 0)),
        "node_count": len(nodes),
        "maximum_depth": max(node["depth"] for node in nodes),
        "maximum_actual_loops": max(loops, default=0),
        "maximum_relation_scan_actual_loops": max(
            (loop for values in relation_loops.values() for loop in values), default=0
        ),
        "node_type_counts": dict(sorted(Counter(
            str(node["Node Type"]) for node in nodes
        ).items())),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "relation_scan_actual_loops": dict(sorted(relation_loops.items())),
        "index_names": sorted({
            str(node["Index Name"]) for node in nodes if "Index Name" in node
        }),
        "nodes": nodes,
    }


def assert_measurement(
    result: dict[str, Any],
    dataset: dict[str, Any],
    plan: dict[str, Any],
    buffers: dict[str, float],
    binding: dict[str, Any],
) -> list[str]:
    if result["row_count"] != dataset["current_user_category_rows"]:
        raise AssertionError("runtime result/category fixture count drifted")
    if result["active_bank_count_sum"] != dataset["current_user_active_associations"]:
        raise AssertionError("status=1 category aggregate drifted")
    if result["zero_bank_count_rows"] != dataset["zero_active_bank_categories"]:
        raise AssertionError("zero-count category preservation drifted")
    if result["null_sort_rows"] != 1 or result["empty_name_rows"] != 1:
        raise AssertionError("nullable/empty category edges drifted")
    if result["unicode_name_rows"] != 1:
        raise AssertionError("Unicode category edge drifted")
    if plan["result_row_count"] != result["row_count"] or plan["root_actual_loops"] != 1:
        raise AssertionError("plan root cardinality/loop drifted")
    if plan["relation_scan_occurrences"] != {
        "user_bank_categories": 1,
        "user_question_banks": 1,
    }:
        raise AssertionError(f"relation scan count drifted: {plan['relation_scan_occurrences']}")
    if plan["maximum_relation_scan_actual_loops"] != 1:
        raise AssertionError("relation scans gained repeated loops/N+1")
    if binding["bound_parameter_count"] != 1:
        raise AssertionError("runtime query must bind one bigint user_id")
    if buffers.get("Temp Read Blocks", 0) or buffers.get("Temp Written Blocks", 0):
        raise AssertionError("synthetic query plan spilled temporary blocks")
    return [
        "one runtime SELECT with one bigint user_id bind",
        "eight-column current-user projection returned every category",
        "status=1 only aggregate includes cross-owner category associations",
        "PostgreSQL ASC NULLS LAST then signed id ASC order preserved",
        "both relations scanned once with one root loop and no N+1",
        "zero temporary read/write blocks at the synthetic evidence scale",
    ]


def image_metadata(image: str) -> dict[str, Any]:
    raw = run(["docker", "image", "inspect", image]).stdout
    metadata = json.loads(raw)[0]
    digest = image.split("@", 1)[1]
    repo_digests = sorted(metadata.get("RepoDigests", []))
    if not any(value.endswith(digest) for value in repo_digests):
        raise AssertionError(f"resolved image lacks expected digest {digest}")
    return {
        "expected_digest": digest,
        "resolved_image_id": metadata.get("Id"),
        "resolved_repo_digests": repo_digests,
        "os": metadata.get("Os"),
        "architecture": metadata.get("Architecture"),
    }


def required_input_paths(root: Path, manifest_path: Path) -> dict[str, Path]:
    return {
        "adapter": root / (
            "server/src/main/java/io/saksk/ti/personalbank/infrastructure/persistence/"
            "JdbcPersonalBankCategoryQueryAdapter.java"
        ),
        "runtime_sql_manifest": manifest_path,
        "runtime_sql_exporter": root / (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/persistence/"
            "PersonalBankCategoryRuntimeSqlManifestTest.java"
        ),
        "postgres_compatibility_test": root / (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4bPersonalBankCategoryJdbcCompatibilityIT.java"
        ),
        "postgres_schema": root / (
            "server/src/test/resources/db/phase4b/"
            "060-personal-bank-category-schema.sql"
        ),
        "postgres_fixture": root / (
            "server/src/test/resources/db/phase4b/"
            "061-personal-bank-category-seed.sql"
        ),
        "capture_tool": Path(__file__).resolve(),
        "capture_tool_test": Path(__file__).with_name(
            "test_capture_phase4b_personal_bank_category_query_plan.py"
        ).resolve(),
    }


def assert_public_evidence(document: Any) -> None:
    ephemeral = re.compile(r"ti-phase4b-personal-bank-category-plan-[0-9a-f]{12}")

    def visit(value: Any, key: str = "") -> None:
        if any(fragment in key.lower() for fragment in SENSITIVE_KEY_FRAGMENTS):
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
            if ephemeral.search(value):
                raise AssertionError("ephemeral container identity leaked into evidence")

    visit(document)


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
    sql = query["sql"]
    validate_runtime_sql(sql)
    dataset = dataset_metadata(container)
    if dataset["category_rows"] != args.category_count + 3:
        raise AssertionError("category fixture cardinality drifted")
    if dataset["current_user_category_rows"] != args.category_count + 2:
        raise AssertionError("current-user fixture cardinality drifted")
    if dataset["bank_rows"] != args.bank_count:
        raise AssertionError("bank fixture cardinality drifted")
    expected_statuses = expected_bank_status_counts(args.bank_count)
    actual_statuses = {key: dataset[key] for key in expected_statuses}
    if actual_statuses != expected_statuses:
        raise AssertionError(
            f"bank status fixture distribution drifted: {actual_statuses}"
        )
    if sum(actual_statuses.values()) != dataset["bank_rows"]:
        raise AssertionError("bank status distribution does not close over all fixture rows")
    if (
        dataset["status_zero_bank_rows"]
        + dataset["status_two_bank_rows"]
        + dataset["status_null_bank_rows"]
        != dataset["non_one_bank_rows"]
    ):
        raise AssertionError("non-one bank status aggregate drifted")
    if dataset["category_user_id_type"] != "integer" \
            or dataset["bank_user_id_type"] != "integer":
        raise AssertionError("legacy personal-bank user_id columns must remain int4")

    raw_rows = psql(
        container,
        runtime_sql_with_literal(sql, CURRENT_USER_ID) + ";",
        separator="\x1f",
    )
    result = parse_result_rows(raw_rows, args.category_count)
    explain_sql, binding = prepared_sql(sql, CURRENT_USER_ID, explain=True)
    raw_explain = psql_json(container, explain_sql)
    if not isinstance(raw_explain, list) or len(raw_explain) != 1:
        raise RuntimeError("unexpected EXPLAIN JSON payload")
    buffers = collect_buffer_fields(raw_explain[0])
    plan = summarize_plan(raw_explain[0])
    assertions = assert_measurement(result, dataset, plan, buffers, binding)

    root = Path(__file__).resolve().parents[1]
    paths = required_input_paths(root, manifest_path)
    inputs: dict[str, Any] = {}
    for key, path in paths.items():
        inputs[key] = str(path.relative_to(root))
        inputs[f"{key}_sha256"] = sha256_file(path)
    runtime_sql_sha256 = sha256_text(sql)
    network_mode = run([
        "docker", "inspect", "--format={{.HostConfig.NetworkMode}}", container
    ]).stdout.strip()
    if network_mode != "none":
        raise AssertionError(f"evidence container network drifted: {network_mode}")

    document = {
        "evidence_id": "ti.phase4b.personal-bank-category-query-plan",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "scope": "personalbank-category-list-internal-read-capability",
        "route_migration_status": {
            "route_ids": ["19b37a262989", "e32aec766730"],
            "http_owner": "personalbank",
            "status": "pending",
            "production_cutover": False,
        },
        "environment": {
            "container_image": args.image,
            **image_metadata(args.image),
            "network": network_mode,
            "database": DEFAULT_DATABASE,
            "postgresql": {
                "server_version": psql(container, "SHOW server_version;"),
                "server_version_num": psql(container, "SHOW server_version_num;"),
                "max_parallel_workers_per_gather": 0,
                "work_mem": "64MB",
            },
        },
        "inputs": inputs,
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "positive_category_count": args.category_count,
                "signed_edge_category_count": 2,
                "other_identity_category_count": 1,
                "bank_count": args.bank_count,
                "current_user_id": CURRENT_USER_ID,
                "other_user_id": OTHER_USER_ID,
            },
            "actual": dataset,
            "schema_and_bind_boundary": {
                "user_bank_categories.user_id": "integer (int4)",
                "user_question_banks.user_id": "integer (int4)",
                "runtime_user_id_bind": "bigint (int8)",
                "compatibility_statement": (
                    "This PostgreSQL 18.4 PREPARE(bigint) capture proves its int8 parameter "
                    "compares to the synthetic legacy-shaped int4 owner columns at user_id "
                    "9001; it does not claim JDBC or PostgreSQL 16 execution"
                ),
                "hashed_compatibility_inputs_scope": (
                    "The PostgreSQL JDBC integration test, schema and fixture hashes identify "
                    "source provenance only; execution results belong to the read contract's "
                    "separately rerun verification record"
                ),
            },
            "distribution": {
                "current_user_category_ids": current_user_category_ids_description(
                    args.category_count
                ),
                "other_identity_category_id": args.category_count + 1000,
                "sort_order": (
                    "negative edge -5; zero and positive modulo 50 ties; final positive "
                    "category NULL to prove PostgreSQL NULLS LAST"
                ),
                "bank_status": (
                    "rows divisible by 101 use status=2, then rows divisible by 103 use NULL, "
                    "then remaining rows divisible by 10 use 0; only all other rows use 1"
                ),
                "bank_owner": (
                    "every seventh bank belongs to the other identity while category counts "
                    "remain association-based"
                ),
                "category_assignment": (
                    "two signed edges, one other-identity category, then round-robin over the "
                    "first 80 percent of positive current-user categories"
                ),
            },
            "statistics": (
                "user_question_banks.category_id statistics target 10000 and VACUUM (ANALYZE) "
                "completed for both relations"
            ),
            "index_definitions": index_definitions(container),
            "index_decision": (
                "observe only fixture primary/unique indexes matching legacy constraints; this "
                "evidence does not approve a production index"
            ),
        },
        "measurement": {
            "command": (
                "PREPARE(bigint) plus EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON, "
                "TIMING FALSE, SUMMARY FALSE) EXECUTE exact Java runtime SQL"
            ),
            "runs_per_query": 1,
            "query_count": 1,
            "sql_statement_count": 1,
            "growth_with_result_count": 0,
            "n_plus_one_forbidden": True,
            "observation": {
                "observation_id": "current-user-category-list",
                "runtime_query_id": QUERY_ID,
                "operation": OPERATION,
                "source": inputs["adapter"],
                "sql": sql,
                "sql_sha256": runtime_sql_sha256,
                "binding": binding,
                "runtime_result": result,
                "temp_blocks_observed": {
                    "Temp Read Blocks": buffers.get("Temp Read Blocks", 0),
                    "Temp Written Blocks": buffers.get("Temp Written Blocks", 0),
                },
                "buffer_fields_observed_before_normalization": sorted(buffers),
                "assertions_passed": assertions,
                "plan_summary": plan,
            },
        },
        "normalization": {
            "removed": [
                "planning and execution timing",
                "per-node actual timing",
                "cache-dependent buffer block counts",
                "planner estimates and costs",
                "runtime memory/hash counters",
                "container ID and ephemeral container name",
            ],
            "retained": [
                "plan node types/depth and actual rows/loops",
                "join/aggregate/sort strategy",
                "relation and index names",
                "which BUFFERS fields were emitted and zero temp-block assertion",
            ],
        },
        "interpretation": {
            "status": "observational_evidence_only",
            "statement": (
                "This isolated deterministic capture proves exact internal query semantics and "
                "bounded relation scans at the recorded scale. It is not a production latency "
                "SLA, capacity claim, HTTP parity claim or index recommendation."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/capture_phase4b_personal_bank_category_query_plan.py "
                "--output Ti-Java/docs/refactor/phase4b/"
                "personal-bank-category-query-plan-evidence.json"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": "ephemeral network-disabled container removed on every exit",
        },
    }
    if runtime_sql_sha256 != sha256_text(manifest["queries"][0]["sql"]):
        raise AssertionError("runtime SQL hash drifted after capture")
    for key, path in paths.items():
        if inputs[f"{key}_sha256"] != sha256_file(path):
            raise AssertionError(f"source drifted during capture: {key}")
    assert_public_evidence(document)
    return document


def cleanup_container(container: str) -> None:
    run(["docker", "rm", "--force", container], check=False)
    inspected = run(["docker", "inspect", container], check=False)
    if inspected.returncode == 0:
        raise RuntimeError(f"temporary query-plan container remains: {container}")
    detail = (inspected.stdout + "\n" + inspected.stderr).strip()
    if not re.search(r"\bno such (?:object|container)\b", detail, re.IGNORECASE):
        raise RuntimeError(
            "could not verify temporary query-plan container absence "
            f"(docker inspect exit={inspected.returncode}): {detail[-1000:]}"
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
    container = "ti-phase4b-personal-bank-category-plan-" + uuid.uuid4().hex[:12]
    started = False
    try:
        result = run([
            "docker", "run", "--detach", "--rm", "--name", container,
            "--network", "none", "--env", "POSTGRES_PASSWORD=postgres",
            "--env", f"POSTGRES_DB={DEFAULT_DATABASE}", args.image,
        ], check=False)
        if result.returncode != 0:
            raise RuntimeError(f"could not start PostgreSQL: {result.stderr.strip()[-3000:]}")
        started = True
        wait_until_ready(container, args.startup_timeout_seconds)
        psql(container, fixture_sql(args.category_count, args.bank_count))
        document = capture(args, container, manifest, manifest_path)
        write_json_atomic(args.output, document)
        print(
            "captured personal-bank category plan "
            f"sql_sha256={document['measurement']['observation']['sql_sha256']}"
        )
        return 0
    finally:
        if started:
            cleanup_container(container)


if __name__ == "__main__":
    raise SystemExit(main())
