#!/usr/bin/env python3
"""Capture deterministic PG16/PG18 plans for preimplementation share-list SQL."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Iterable, Mapping, Optional
import uuid


POSTGRES_IMAGES = (
    {
        "label": "PostgreSQL 16.14",
        "version": "16.14",
        "image": (
            "postgres:16.14-alpine@"
            "sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777"
        ),
    },
    {
        "label": "PostgreSQL 18.4",
        "version": "18.4",
        "image": (
            "postgres:18.4-alpine@"
            "sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
        ),
    },
)
DEFAULT_DATABASE = "phase4b_personal_bank_share_plan"
DEFAULT_BANK_COUNT = 5_000
DEFAULT_SHARE_COUNT = 150_000
TARGET_BANK_ID = 4_101
TARGET_VIEWER_ID = 4_201
OTHER_VIEWER_ID = 4_202
TARGET_SHARE_INTERVAL = 500
TARGET_NULL_INTERVAL = 5_000

MANIFEST_ID = "ti.phase4b.personal-bank-share-list-preimplementation-sql"
SOURCE_CLASS = (
    "io.saksk.ti.personalbank.infrastructure.persistence."
    "PersonalBankShareListEvidenceSql"
)
QUERY_IDS = (
    "personal-bank-share-owner-status-probe",
    "personal-bank-share-list",
)
NAMED_PARAMETER = re.compile(r"(?<!:):([A-Za-z][A-Za-z0-9_]*)")
FORBIDDEN_SQL = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|copy|call|do|"
    r"vacuum|analyze|refresh|grant|revoke|temporary|temp|limit|offset|fetch|"
    r"for\s+update)\b",
    re.IGNORECASE,
)
EXPECTED_PROBE = (
    "select id from user_question_banks where id = :bank_id "
    "and user_id = :viewer_id and status = 1"
)
EXPECTED_SHARE_LIST = (
    "select id, bank_id, owner_id, share_code, share_token, permission, "
    "expires_at, max_uses, current_uses, is_active, created_at "
    "from bank_shares where bank_id = :bank_id "
    "order by created_at desc nulls first"
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


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported PG16/PG18 share-list query plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/refactor/phase4b/personal-bank-share-list-query-plan-evidence.json",
    )
    parser.add_argument(
        "--sql-manifest",
        type=Path,
        default=root / "server/target/phase4b-personal-bank-share-list-evidence-sql.json",
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


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def document_payload_sha256(document: Mapping[str, Any]) -> str:
    return sha256_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    })


def render_document(document: Mapping[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).lower()


def validate_query_sql(query_id: str, sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise RuntimeError(f"{query_id} SQL is empty")
    if ";" in stripped or "--" in stripped or "/*" in stripped:
        raise RuntimeError(f"{query_id} SQL contains a separator or comment")
    if len(re.findall(r"\bselect\b", stripped, re.IGNORECASE)) != 1:
        raise RuntimeError(f"{query_id} must contain exactly one SELECT")
    forbidden = FORBIDDEN_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(f"{query_id} contains forbidden token {forbidden.group(0)}")
    if re.search(r"\b(?:pg_temp|pg_catalog)\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"{query_id} references a PostgreSQL system schema")
    normalized = normalize_sql(stripped)
    expected = EXPECTED_PROBE if query_id == QUERY_IDS[0] else EXPECTED_SHARE_LIST
    if normalized != expected:
        raise RuntimeError(f"{query_id} SQL shape drifted")
    if " join " in normalized:
        raise RuntimeError(f"{query_id} cannot contain JOIN")


def export_sql_manifest(root: Path, output: Path) -> None:
    target = (root / "server/target").resolve()
    output = output.resolve()
    if output == target or target not in output.parents:
        raise ValueError("share-list SQL manifest must stay under server/target")
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = run([
        str(verifier),
        "-q",
        "-DskipITs",
        "-Dtest=PersonalBankShareListEvidenceSqlManifestTest",
        f"-Dti.personal-bank-share-list-evidence.sql-manifest-output={output}",
        "test",
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java share-list SQL export failed: {detail}")


def load_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java share-list SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("share-list SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID or manifest.get("schema_version") != 1:
        raise RuntimeError("share-list SQL manifest identity drifted")
    if manifest.get("source_class") != SOURCE_CLASS:
        raise RuntimeError("share-list SQL source class drifted")
    if manifest.get("scope") != "test-only-preimplementation-evidence":
        raise RuntimeError("share-list SQL manifest overstates its scope")
    if manifest.get("sequential_execution_required") is not True:
        raise RuntimeError("share-list SQL manifest lost sequential execution")
    if manifest.get("join_authorized") is not False:
        raise RuntimeError("share-list SQL manifest authorized JOIN")
    queries = manifest.get("queries")
    if manifest.get("query_count") != 2 or not isinstance(queries, list) or len(queries) != 2:
        raise RuntimeError("share-list SQL manifest must contain exactly two queries")
    expected = (
        {
            "ordinal": 1,
            "query_id": QUERY_IDS[0],
            "operation": "owner-status-probe",
            "parameter_order": ["bank_id", "viewer_id"],
            "parameters": {"bank_id": "integer", "viewer_id": "bigint"},
        },
        {
            "ordinal": 2,
            "query_id": QUERY_IDS[1],
            "operation": "share-list",
            "parameter_order": ["bank_id"],
            "parameters": {"bank_id": "integer"},
        },
    )
    for query, contract in zip(queries, expected, strict=True):
        if not isinstance(query, dict):
            raise RuntimeError("share-list SQL query must be an object")
        for key, value in contract.items():
            if query.get(key) != value:
                raise RuntimeError(f"{contract['query_id']} {key} drifted")
        sql = query.get("sql")
        if not isinstance(sql, str):
            raise RuntimeError(f"{contract['query_id']} SQL must be text")
        validate_query_sql(contract["query_id"], sql)
        if NAMED_PARAMETER.findall(sql) != contract["parameter_order"]:
            raise RuntimeError(f"{contract['query_id']} bind occurrence order drifted")
    return manifest


def positional_sql(sql: str, parameter_order: list[str]) -> str:
    positions = {name: index + 1 for index, name in enumerate(parameter_order)}

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in positions:
            raise RuntimeError(f"unexpected named parameter: {name}")
        return f"${positions[name]}"

    return NAMED_PARAMETER.sub(replace, sql)


def prepared_explain_sql(query: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    query_id = str(query["query_id"])
    sql = str(query["sql"])
    parameter_order = list(query["parameter_order"])
    validate_query_sql(query_id, sql)
    positional = positional_sql(sql, parameter_order)
    values = {
        "bank_id": TARGET_BANK_ID,
        "viewer_id": TARGET_VIEWER_ID,
    }
    parameter_types = query.get("parameters")
    if not isinstance(parameter_types, Mapping):
        raise RuntimeError(f"{query_id} parameter types are missing")
    if set(parameter_types) != set(parameter_order):
        raise RuntimeError(f"{query_id} parameter type names drifted")
    if any(parameter_types[name] not in {"integer", "bigint"} for name in parameter_order):
        raise RuntimeError(f"{query_id} contains an unsupported parameter type")
    signature = ", ".join(str(parameter_types[name]) for name in parameter_order)
    arguments = ", ".join(str(values[name]) for name in parameter_order)
    prepared_name = "phase4b_share_probe" if query_id == QUERY_IDS[0] else "phase4b_share_list"
    statement = (
        "SET max_parallel_workers_per_gather = 0;\n"
        "SET jit = off;\n"
        "SET work_mem = '64MB';\n"
        f"PREPARE {prepared_name}({signature}) AS\n{positional.strip()};\n"
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON, TIMING FALSE, SUMMARY FALSE)\n"
        f"EXECUTE {prepared_name}({arguments});\n"
        f"DEALLOCATE {prepared_name};\n"
    )
    return statement, {
        "mode": "postgresql-prepare-execute",
        "prepared_name": prepared_name,
        "runtime_statement_count": 1,
        "bound_parameter_count": len(parameter_order),
        "occurrence_names": parameter_order,
        "positional_sql_sha256": sha256_text(positional),
        "parameters": {
            name: {
                "postgres_type": parameter_types[name],
                "value": values[name],
            }
            for name in parameter_order
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
INSERT INTO user_question_banks (id, user_id, status)
VALUES ({TARGET_BANK_ID}, {TARGET_VIEWER_ID}, 1),
       (0, {TARGET_VIEWER_ID}, 1),
       (4102, {TARGET_VIEWER_ID}, 0),
       (4103, {TARGET_VIEWER_ID}, NULL),
       (4104, {OTHER_VIEWER_ID}, 1);
INSERT INTO user_question_banks (id, user_id, status)
SELECT 10000 + value, {OTHER_VIEWER_ID}, 1
FROM generate_series(1, {bank_count}) AS value;
INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
) VALUES
    (-2, {TARGET_BANK_ID}, {OTHER_VIEWER_ID}, NULL, NULL, NULL, NULL,
     NULL, NULL, NULL, NULL),
    (-1, {TARGET_BANK_ID}, {TARGET_VIEWER_ID}, 'SPECIAL_OFF', 'special-off-token',
     'copy', TIMESTAMP '2020-01-01 00:00:00', 1, 99, false,
     TIMESTAMP '2026-07-17 11:00:00'),
    (0, {TARGET_BANK_ID}, {TARGET_VIEWER_ID}, 'SPECIAL_NEW', 'special-new-token',
     'read', NULL, NULL, 0, true, TIMESTAMP '2027-01-01 00:00:00');
INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
)
SELECT value,
       CASE WHEN value % {TARGET_SHARE_INTERVAL} = 0
            THEN {TARGET_BANK_ID}
            ELSE 10001 + (value % {bank_count}) END,
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


def execute_psql(container: str, database: str, sql: str) -> str:
    result = run([
        "docker", "exec", "-i", container,
        "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
        "-U", "postgres", "-d", database, "-A", "-t",
    ], input_text=sql, check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"PostgreSQL command failed: {detail}")
    return result.stdout.strip()


def wait_for_postgres(container: str, database: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = run([
            "docker", "exec", container,
            "pg_isready", "-U", "postgres", "-d", database,
        ], check=False)
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError("PostgreSQL container did not become ready")


def parse_explain(raw: str) -> list[dict[str, Any]]:
    start = raw.find("[")
    end = raw.rfind("]")
    if start < 0 or end < start:
        raise RuntimeError("EXPLAIN output does not contain JSON")
    try:
        parsed = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("EXPLAIN JSON could not be parsed") from exc
    if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
        raise RuntimeError("EXPLAIN JSON root shape drifted")
    return parsed


def walk_plan(node: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield node
    for child in node.get("Plans", []):
        if isinstance(child, Mapping):
            yield from walk_plan(child)


def plan_summary(explain: list[dict[str, Any]]) -> dict[str, Any]:
    root = explain[0].get("Plan")
    if not isinstance(root, Mapping):
        raise RuntimeError("EXPLAIN root lacks a Plan object")
    nodes = list(walk_plan(root))
    relations = Counter(
        str(node["Relation Name"])
        for node in nodes
        if "Relation Name" in node
    )
    indexes = [str(node["Index Name"]) for node in nodes if "Index Name" in node]
    return {
        "root_node_type": root.get("Node Type"),
        "root_actual_rows": root.get("Actual Rows"),
        "node_types_preorder": [node.get("Node Type") for node in nodes],
        "node_count": len(nodes),
        "relation_scan_occurrences": dict(sorted(relations.items())),
        "index_names": indexes,
        "maximum_actual_loops": max(int(node.get("Actual Loops", 0)) for node in nodes),
        "temp_read_blocks": sum(int(node.get("Temp Read Blocks", 0)) for node in nodes),
        "temp_written_blocks": sum(int(node.get("Temp Written Blocks", 0)) for node in nodes),
        "sort_methods": [str(node["Sort Method"]) for node in nodes if "Sort Method" in node],
        "sort_space_types": [
            str(node["Sort Space Type"]) for node in nodes if "Sort Space Type" in node
        ],
    }


def sanitized_plan(value: Any) -> Any:
    if isinstance(value, list):
        return [sanitized_plan(item) for item in value]
    if isinstance(value, dict):
        return {
            key: sanitized_plan(child)
            for key, child in value.items()
            if key not in VOLATILE_PLAN_KEYS and key not in BUFFER_KEYS
        }
    return value


def literal_sql(query: Mapping[str, Any]) -> str:
    sql = str(query["sql"])
    values = {
        "bank_id": TARGET_BANK_ID,
        "viewer_id": TARGET_VIEWER_ID,
    }
    return NAMED_PARAMETER.sub(lambda match: str(values[match.group(1)]), sql)


def probe_result(container: str, database: str, query: Mapping[str, Any]) -> dict[str, Any]:
    output = execute_psql(container, database, literal_sql(query))
    values = [] if not output else [int(line) for line in output.splitlines()]
    if values != [TARGET_BANK_ID]:
        raise RuntimeError(f"owner/status probe result drifted: {values}")
    return {
        "row_count": len(values),
        "ids": values,
        "rows_sha256": sha256_json(values),
    }


def share_result(
    container: str,
    database: str,
    query: Mapping[str, Any],
    share_count: int,
) -> dict[str, Any]:
    copy_sql = (
        "COPY (\n" + literal_sql(query).strip()
        + "\n) TO STDOUT WITH (FORMAT csv, NULL '<NULL>');\n"
    )
    raw = execute_psql(container, database, copy_sql)
    rows = list(csv.reader(io.StringIO(raw))) if raw else []
    expected_count = share_count // TARGET_SHARE_INTERVAL + 3
    if len(rows) != expected_count:
        raise RuntimeError(
            f"share-list row count drifted: expected={expected_count} observed={len(rows)}"
        )
    if any(len(row) != 11 for row in rows):
        raise RuntimeError("share-list COPY projection lost an explicit column")
    created = [row[10] for row in rows]
    null_count = sum(value == "<NULL>" for value in created)
    expected_null_count = share_count // TARGET_NULL_INTERVAL + 1
    if null_count != expected_null_count:
        raise RuntimeError("share-list NULL created_at fixture count drifted")
    if created[:null_count] != ["<NULL>"] * null_count:
        raise RuntimeError("PostgreSQL DESC NULLS FIRST behavior drifted")
    if any(value == "<NULL>" for value in created[null_count:]):
        raise RuntimeError("PostgreSQL NULL created_at escaped the leading group")
    non_null = [datetime.fromisoformat(value) for value in created[null_count:]]
    if any(left < right for left, right in zip(non_null, non_null[1:])):
        raise RuntimeError("share-list non-NULL timestamps are not descending")
    tie_groups = Counter(created[null_count:])
    if max(tie_groups.values(), default=0) < 2:
        raise RuntimeError("share-list fixture lost equal-created_at ambiguity")
    active_values = {row[9] for row in rows}
    if not {"t", "f", "<NULL>"}.issubset(active_values):
        raise RuntimeError("share-list fixture lost nullable PostgreSQL booleans")
    if not any(int(row[2]) == OTHER_VIEWER_ID for row in rows):
        raise RuntimeError("share-list fixture lost cross-owner rows")
    if not any(row[5] == "unexpected-value" for row in rows):
        raise RuntimeError("share-list fixture lost unconstrained permission rows")
    ids = [int(row[0]) for row in rows]
    return {
        "row_count": len(rows),
        "column_count": 11,
        "rows_sha256": sha256_json(rows),
        "leading_null_created_at_count": null_count,
        "all_null_created_at_rows_are_leading": True,
        "non_null_created_at_descending": True,
        "equal_created_at_group_count": sum(1 for count in tie_groups.values() if count > 1),
        "maximum_equal_created_at_group_size": max(tie_groups.values(), default=0),
        "equal_created_at_order_contract": "unordered_within_group",
        "postgres_boolean_values": sorted(active_values),
        "cross_owner_rows_present": True,
        "inactive_rows_present": True,
        "unconstrained_permission_rows_present": True,
        "first_ten_ids": ids[:10],
        "last_ten_ids": ids[-10:],
    }


def assert_plan_contract(query_id: str, summary: Mapping[str, Any], expected_rows: int) -> None:
    if summary["root_actual_rows"] != expected_rows:
        raise RuntimeError(f"{query_id} plan row count drifted")
    if summary["maximum_actual_loops"] != 1:
        raise RuntimeError(f"{query_id} plan executed a node more than once")
    if summary["temp_read_blocks"] != 0 or summary["temp_written_blocks"] != 0:
        raise RuntimeError(f"{query_id} plan used temporary blocks")
    if query_id == QUERY_IDS[0]:
        if summary["relation_scan_occurrences"] != {"user_question_banks": 1}:
            raise RuntimeError("owner/status probe relation plan drifted")
        if "user_question_banks_pkey" not in summary["index_names"]:
            raise RuntimeError("owner/status probe lost the primary-key lookup")
    else:
        if summary["relation_scan_occurrences"] != {"bank_shares": 1}:
            raise RuntimeError("share-list relation plan drifted")
        if summary["root_node_type"] != "Sort":
            raise RuntimeError("share-list plan lost the explicit Sort root")
        if summary["node_types_preorder"] != ["Sort", "Seq Scan"]:
            raise RuntimeError("share-list no-index plan shape drifted")
        if summary["index_names"]:
            raise RuntimeError("share-list unexpectedly acquired an index-backed plan")


def capture_engine(
    image: Mapping[str, str],
    manifest: Mapping[str, Any],
    fixture: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    container = f"ti-phase4b-share-plan-{uuid.uuid4().hex[:12]}"
    password = "public-test-only-password"
    run_result = run([
        "docker", "run", "-d", "--rm", "--name", container,
        "-e", f"POSTGRES_PASSWORD={password}",
        "-e", f"POSTGRES_DB={DEFAULT_DATABASE}",
        image["image"],
    ], check=False)
    if run_result.returncode != 0:
        detail = (run_result.stdout + "\n" + run_result.stderr).strip()[-4000:]
        raise RuntimeError(f"cannot start {image['label']}: {detail}")
    try:
        wait_for_postgres(container, DEFAULT_DATABASE, args.startup_timeout_seconds)
        execute_psql(container, DEFAULT_DATABASE, fixture)
        server_version = execute_psql(container, DEFAULT_DATABASE, "SHOW server_version;")
        server_version_num = execute_psql(
            container, DEFAULT_DATABASE, "SHOW server_version_num;"
        )
        if server_version != image["version"]:
            raise RuntimeError(
                f"{image['label']} server version drifted: {server_version}"
            )
        image_id = run([
            "docker", "image", "inspect", image["image"], "--format", "{{.Id}}",
        ]).stdout.strip()
        observations = []
        queries = manifest["queries"]
        for query in queries:
            statement, binding = prepared_explain_sql(query)
            raw_explain = parse_explain(execute_psql(container, DEFAULT_DATABASE, statement))
            summary = plan_summary(raw_explain)
            result = (
                probe_result(container, DEFAULT_DATABASE, query)
                if query["query_id"] == QUERY_IDS[0]
                else share_result(container, DEFAULT_DATABASE, query, args.share_count)
            )
            assert_plan_contract(query["query_id"], summary, result["row_count"])
            normalized = normalize_sql(query["sql"])
            observations.append({
                "ordinal": query["ordinal"],
                "query_id": query["query_id"],
                "operation": query["operation"],
                "sql": query["sql"],
                "sql_sha256": sha256_text(query["sql"]),
                "normalized_sql_sha256": sha256_text(normalized),
                "binding": binding,
                "result": result,
                "plan_summary": summary,
                "sanitized_explain": sanitized_plan(raw_explain),
            })
        return {
            "label": image["label"],
            "image": image["image"],
            "image_id": image_id,
            "server_version": server_version,
            "server_version_num": server_version_num,
            "observations": observations,
        }
    finally:
        run(["docker", "rm", "-f", "-v", container], check=False)


def tool_inputs(root: Path) -> dict[str, str]:
    paths = {
        "evidence_sql": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/persistence/"
            "PersonalBankShareListEvidenceSql.java"
        ),
        "sql_contract_test": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/persistence/"
            "PersonalBankShareListEvidenceSqlContractTest.java"
        ),
        "sql_manifest_exporter": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/persistence/"
            "PersonalBankShareListEvidenceSqlManifestTest.java"
        ),
        "jdbc_compatibility_test": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4bPersonalBankShareListEvidenceJdbcCompatibilityIT.java"
        ),
        "schema": "server/src/test/resources/db/phase4b/062-personal-bank-share-list-schema.sql",
        "seed": "server/src/test/resources/db/phase4b/063-personal-bank-share-list-seed.sql",
        "capture_tool": "tools/capture_phase4b_personal_bank_share_list_query_plans.py",
        "capture_tool_test": "tools/test_capture_phase4b_personal_bank_share_list_query_plans.py",
    }
    return {key + "_sha256": sha256_file(root / value) for key, value in paths.items()}


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
    expected_share_rows = args.share_count // TARGET_SHARE_INTERVAL + 3
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-share-list-query-plan-evidence",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "scope": "test-only preimplementation JDBC SQL and observational query-plan evidence",
        "inputs": {
            "sql_manifest_path": "server/target/phase4b-personal-bank-share-list-evidence-sql.json",
            "sql_manifest_sha256": sha256_file(manifest_path),
            "sql_manifest_payload_sha256": sha256_json(manifest),
            **tool_inputs(root),
        },
        "sql_contract": {
            "manifest": manifest,
            "query_order": list(QUERY_IDS),
            "query_count": 2,
            "sequential_execution_required": True,
            "join_authorized": False,
            "second_query_requires_first_query_row": True,
            "production_source_added": False,
        },
        "fixture": {
            "bank_count_argument": args.bank_count,
            "generated_bank_count": args.bank_count + 5,
            "share_count_argument": args.share_count,
            "generated_share_count": args.share_count + 3,
            "target_bank_id": TARGET_BANK_ID,
            "target_viewer_id": TARGET_VIEWER_ID,
            "target_share_interval": TARGET_SHARE_INTERVAL,
            "target_null_interval": TARGET_NULL_INTERVAL,
            "expected_target_share_count": expected_share_rows,
            "schema_has_bank_id_or_created_at_index": False,
            "fixture_sql_sha256": sha256_text(fixture),
        },
        "engines": engines,
        "cross_version_contract": {
            "required_versions": [image["version"] for image in POSTGRES_IMAGES],
            "observed_versions": [engine["server_version"] for engine in engines],
            "both_queries_observed_per_version": all(
                [observation["query_id"] for observation in engine["observations"]]
                == list(QUERY_IDS)
                for engine in engines
            ),
            "owner_probe_uses_primary_key": all(
                "user_question_banks_pkey"
                in engine["observations"][0]["plan_summary"]["index_names"]
                for engine in engines
            ),
            "share_list_uses_seq_scan_and_sort_without_index": all(
                engine["observations"][1]["plan_summary"]["node_types_preorder"]
                == ["Sort", "Seq Scan"]
                and not engine["observations"][1]["plan_summary"]["index_names"]
                for engine in engines
            ),
            "desc_nulls_first_verified": all(
                engine["observations"][1]["result"]["all_null_created_at_rows_are_leading"]
                for engine in engines
            ),
            "equal_timestamp_order_strengthened": False,
            "temporary_blocks_zero": all(
                observation["plan_summary"]["temp_read_blocks"] == 0
                and observation["plan_summary"]["temp_written_blocks"] == 0
                for engine in engines
                for observation in engine["observations"]
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
                "The no-index share-list plan documents the frozen legacy risk; it is not a "
                "performance acceptance target or authorization to add an index."
            ),
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    args = parse_args()
    document = capture_document(args)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        "captured personal-bank share-list PG16/PG18 plans "
        f"manifest_sha256={document['inputs']['sql_manifest_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
