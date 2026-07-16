#!/usr/bin/env python3
"""Capture deterministic PostgreSQL 18 plans for Phase 4A question counts.

The exact SELECT statements are exported from the Java JDBC adapter before
every capture. This tool owns only public synthetic fixture data, parameter
bindings, plan normalization, and bounded plan assertions.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
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
DEFAULT_DATABASE = "phase4a_question_count_plan"
DEFAULT_SUBJECT_COUNT = 5_000
DEFAULT_BASELINE_QUESTION_COUNT = 50_000
DEFAULT_LARGE_QUESTION_COUNT = 150_000
DEFAULT_LARGE_CANDIDATE_COUNT = 65_536

MANIFEST_ID = "ti.phase4a.question-count-runtime-sql"
ADAPTER_CLASS = (
    "io.saksk.ti.catalog.infrastructure.persistence."
    "JdbcQuestionCountQueryAdapter"
)
EXPECTED_QUERY_IDS = {
    "question-count-anonymous-all",
    "question-count-auth-unrestricted",
    "question-count-auth-restricted",
    "question-count-subject-type",
    "question-count-candidate-large",
}
EXPECTED_PARAMETER_NAMES = {
    "question-count-anonymous-all": set(),
    "question-count-auth-unrestricted": set(),
    "question-count-auth-restricted": {"excluded_subject_ids"},
    "question-count-subject-type": {"subject_name", "question_type"},
    "question-count-candidate-large": {"candidate_question_ids"},
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
        description="Capture Java-exported Phase 4A question-count plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root
        / "docs/refactor/phase4a/question-count-query-plan-evidence.json",
    )
    parser.add_argument(
        "--runtime-sql-manifest",
        type=Path,
        default=root / "server/target/phase4a-question-count-runtime-sql.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--subject-count", type=int, default=DEFAULT_SUBJECT_COUNT)
    parser.add_argument(
        "--baseline-question-count",
        type=int,
        default=DEFAULT_BASELINE_QUESTION_COUNT,
    )
    parser.add_argument(
        "--large-question-count",
        type=int,
        default=DEFAULT_LARGE_QUESTION_COUNT,
    )
    parser.add_argument(
        "--large-candidate-count",
        type=int,
        default=DEFAULT_LARGE_CANDIDATE_COUNT,
    )
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.subject_count < DEFAULT_SUBJECT_COUNT:
        raise ValueError(
            f"--subject-count must be at least {DEFAULT_SUBJECT_COUNT}"
        )
    if args.baseline_question_count < DEFAULT_BASELINE_QUESTION_COUNT:
        raise ValueError(
            "--baseline-question-count must be at least "
            f"{DEFAULT_BASELINE_QUESTION_COUNT}"
        )
    if args.large_question_count < 100_000:
        raise ValueError("--large-question-count must be at least 100000")
    if args.large_question_count <= args.baseline_question_count:
        raise ValueError("--large-question-count must exceed the baseline")
    if args.large_candidate_count < DEFAULT_LARGE_CANDIDATE_COUNT:
        raise ValueError(
            "--large-candidate-count must cross the 65535 bind boundary"
        )
    if args.large_candidate_count > args.large_question_count:
        raise ValueError("candidate count cannot exceed the large fixture")
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


def compact_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
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
            "-Dtest=QuestionCountRuntimeSqlManifestTest",
            f"-Dti.question-count.sql-manifest-output={output}",
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
        raise RuntimeError(f"runtime SQL contains a statement separator: {query_id}")
    if not re.match(r"^select\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL is not a SELECT: {query_id}")
    forbidden = FORBIDDEN_RUNTIME_SQL.search(stripped)
    if forbidden:
        raise RuntimeError(
            f"runtime SQL contains forbidden token {forbidden.group(0)}: {query_id}"
        )
    if re.search(r"\bpg_temp\b", stripped, re.IGNORECASE):
        raise RuntimeError(f"runtime SQL references pg_temp: {query_id}")


def load_runtime_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java runtime SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("runtime SQL manifest root must be an object")
    if manifest.get("manifest_id") != MANIFEST_ID:
        raise RuntimeError("question-count runtime SQL manifest ID drifted")
    if manifest.get("schema_version") != 1:
        raise RuntimeError("question-count runtime SQL manifest schema drifted")
    if manifest.get("adapter_class") != ADAPTER_CLASS:
        raise RuntimeError("question-count runtime SQL adapter class drifted")
    queries = manifest.get("queries")
    if not isinstance(queries, list) or manifest.get("query_count") != len(queries):
        raise RuntimeError("runtime SQL manifest query count is invalid")
    if len(queries) != len(EXPECTED_QUERY_IDS):
        raise RuntimeError("runtime SQL manifest must contain exactly five variants")

    actual_ids: set[str] = set()
    for query in queries:
        if not isinstance(query, dict):
            raise RuntimeError("runtime SQL manifest query must be an object")
        query_id = query.get("query_id")
        if not isinstance(query_id, str) or query_id in actual_ids:
            raise RuntimeError(f"invalid or duplicate runtime query ID: {query_id}")
        actual_ids.add(query_id)
        if query.get("operation") != "question-count":
            raise RuntimeError(f"runtime query operation drifted: {query_id}")
        sql = query.get("sql")
        parameters = query.get("parameters")
        if not isinstance(sql, str) or not isinstance(parameters, dict):
            raise RuntimeError(f"invalid SQL or parameters for {query_id}")
        validate_runtime_sql(query_id, sql)
        declared = set(parameters)
        referenced = set(NAMED_PARAMETER.findall(sql))
        if declared != referenced:
            raise RuntimeError(
                f"runtime SQL parameter drift for {query_id}: "
                f"declared={sorted(declared)} referenced={sorted(referenced)}"
            )
        expected_parameters = EXPECTED_PARAMETER_NAMES.get(query_id)
        if expected_parameters is None or declared != expected_parameters:
            raise RuntimeError(
                f"question-count parameters drifted for {query_id}: "
                f"declared={sorted(declared)}"
            )
        for name, parameter in parameters.items():
            if isinstance(parameter, str):
                continue
            if not isinstance(parameter, dict):
                raise RuntimeError(
                    f"parameter metadata is invalid: {query_id}:{name}"
                )
            materialize_manifest_array_parameter(parameter)

    if actual_ids != EXPECTED_QUERY_IDS:
        raise RuntimeError(f"runtime query IDs drifted: {sorted(actual_ids)}")
    candidate = manifest_queries(manifest)["question-count-candidate-large"]
    candidate_count = candidate["parameters"]["candidate_question_ids"].get(
        "element_count"
    )
    if not isinstance(candidate_count, int) or candidate_count < 100_000:
        raise RuntimeError(
            "question-count candidate manifest must contain at least 100000 IDs"
        )
    return manifest


def parameter_postgres_type(parameter: dict[str, Any]) -> str:
    explicit = parameter.get("postgres_type")
    if isinstance(explicit, str) and explicit.strip():
        candidate = explicit.strip().lower().replace(" ", "")
    else:
        jdbc_type = str(parameter.get("jdbc_type") or "").strip().lower()
        jdbc_type = jdbc_type.replace("-", "_").replace(" ", "_")
        mapping = {
            "text": "text",
            "varchar": "text",
            "string": "text",
            "integer": "integer",
            "int": "integer",
            "bigint": "bigint",
            "long": "bigint",
            "integer_array": "integer[]",
            "int_array": "integer[]",
            "bigint_array": "bigint[]",
            "long_array": "bigint[]",
        }
        candidate = mapping.get(jdbc_type, "")
        if not candidate and jdbc_type in {"array", "sql_array"}:
            element = str(
                parameter.get("element_type")
                or parameter.get("array_element_type")
                or ""
            ).strip().lower()
            candidate = {
                "integer": "integer[]",
                "int": "integer[]",
                "bigint": "bigint[]",
                "long": "bigint[]",
            }.get(element, "")
    if candidate not in {"text", "integer", "bigint", "integer[]", "bigint[]"}:
        raise RuntimeError(f"unsupported runtime SQL parameter type: {parameter}")
    return candidate


def decimal_lines_sha256(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def materialize_manifest_array_parameter(
    parameter: dict[str, Any],
) -> list[int]:
    postgres_type = parameter_postgres_type(parameter)
    if postgres_type not in {"integer[]", "bigint[]"}:
        raise RuntimeError(f"manifest generator must describe an array: {parameter}")
    if parameter.get("bind_kind") != "jdbc-sql-array":
        raise RuntimeError("array manifest bind_kind must be jdbc-sql-array")
    if parameter.get("canonical_encoding") != (
        "utf8-decimal-lines-with-final-newline"
    ):
        raise RuntimeError("array manifest canonical encoding drifted")
    generator = parameter.get("value_generator")
    if not isinstance(generator, dict) or generator.get("kind") != (
        "inclusive-integer-range"
    ):
        raise RuntimeError("array manifest value_generator drifted")
    start = generator.get("start")
    end = generator.get("end")
    step = generator.get("step")
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in (start, end, step)
    ):
        raise RuntimeError("array manifest generator bounds must be integers")
    if start <= 0 or end < start or step <= 0:
        raise RuntimeError("array manifest generator bounds are invalid")
    element_count = parameter.get("element_count")
    if (
        not isinstance(element_count, int)
        or isinstance(element_count, bool)
        or element_count <= 0
        or element_count > 1_000_000
    ):
        raise RuntimeError("array manifest element_count is outside safe bounds")
    if (end - start) % step != 0:
        raise RuntimeError("array manifest generator must reach its inclusive end")
    generated_count = ((end - start) // step) + 1
    if generated_count != element_count:
        raise RuntimeError(
            "array manifest element_count drifted: "
            f"expected={generated_count} actual={element_count}"
        )
    values = list(range(start, end + 1, step))
    expected_metadata = {
        "first": values[0],
        "last": values[-1],
        "min": min(values),
        "max": max(values),
        "sha256": decimal_lines_sha256(values),
    }
    for key, expected in expected_metadata.items():
        if parameter.get(key) != expected:
            raise RuntimeError(
                f"array manifest {key} drifted: "
                f"expected={expected} actual={parameter.get(key)}"
            )
    expected_element_type = postgres_type.removesuffix("[]")
    if parameter.get("element_type") != expected_element_type:
        raise RuntimeError("array manifest element_type drifted")
    return values


def postgres_parameter_literal(parameter: dict[str, Any]) -> str:
    postgres_type = parameter_postgres_type(parameter)
    value = parameter.get("value")
    if postgres_type in {"integer", "bigint"}:
        if not isinstance(value, int) or isinstance(value, bool):
            raise RuntimeError(f"invalid integer parameter: {parameter}")
        return str(value)
    if postgres_type == "text":
        if not isinstance(value, str):
            raise RuntimeError(f"invalid text parameter: {parameter}")
        return "'" + value.replace("'", "''") + "'"
    if not isinstance(value, (list, tuple)):
        raise RuntimeError(f"invalid array parameter: {parameter}")
    values: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise RuntimeError(f"array parameter requires positive integers: {parameter}")
        values.append(item)
    array_text = "{" + ",".join(str(item) for item in values) + "}"
    return f"'{array_text}'::{postgres_type}"


def parameter_summary(parameter: dict[str, Any]) -> dict[str, Any]:
    postgres_type = parameter_postgres_type(parameter)
    value = parameter.get("value")
    result: dict[str, Any] = {
        "bind_kind": parameter.get("bind_kind"),
        "postgres_type": postgres_type,
    }
    if postgres_type.endswith("[]"):
        if not isinstance(value, (list, tuple)):
            raise RuntimeError("array summary requires a sequence")
        values = list(value)
        result.update({
            "value_kind": "array",
            "element_count": len(values),
            "value_sha256": compact_json_sha256(values),
            "canonical_decimal_lines_sha256": decimal_lines_sha256(values),
            "first_values": values[:3],
            "last_values": values[-3:] if values else [],
        })
        if "value_generator" in parameter:
            result["manifest_contract"] = {
                "element_count": parameter.get("element_count"),
                "canonical_encoding": parameter.get("canonical_encoding"),
                "sha256": parameter.get("sha256"),
                "value_generator": parameter.get("value_generator"),
            }
            result["matches_manifest_value"] = (
                len(values) == parameter.get("element_count")
                and decimal_lines_sha256(values) == parameter.get("sha256")
            )
    else:
        result.update({"value_kind": "scalar", "value": value})
    return result


def bind_parameters(
    runtime_query: dict[str, Any], overrides: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    templates = runtime_query["parameters"]
    if set(templates) != set(overrides):
        raise RuntimeError(
            f"parameter override drift for {runtime_query['query_id']}: "
            f"templates={sorted(templates)} overrides={sorted(overrides)}"
        )
    bound: dict[str, dict[str, Any]] = {}
    for name, value in overrides.items():
        template = templates[name]
        if isinstance(template, str):
            metadata: dict[str, Any] = {
                "bind_kind": "jdbc-scalar",
                "postgres_type": "text",
            }
        elif isinstance(template, dict):
            metadata = deepcopy(template)
            if (
                parameter_postgres_type(metadata).endswith("[]")
                and "value_generator" in metadata
            ):
                materialize_manifest_array_parameter(metadata)
        else:
            raise RuntimeError(
                f"unsupported manifest parameter template: "
                f"{runtime_query['query_id']}:{name}"
            )
        metadata["value"] = value
        bound[name] = metadata
    return bound


def manifest_parameter_values(runtime_query: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, template in runtime_query["parameters"].items():
        if isinstance(template, str):
            values[name] = template
        elif isinstance(template, dict):
            values[name] = materialize_manifest_array_parameter(template)
        else:
            raise RuntimeError(
                f"unsupported manifest parameter value: "
                f"{runtime_query['query_id']}:{name}"
            )
    return values


def prepared_execution_sql(
    observation_id: str,
    sql: str,
    parameters: dict[str, dict[str, Any]],
    *,
    explain: bool,
) -> tuple[str, dict[str, Any]]:
    validate_runtime_sql(observation_id, sql)
    occurrences: list[tuple[str, dict[str, Any]]] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        parameter = parameters.get(name)
        if parameter is None:
            raise RuntimeError(f"undeclared runtime parameter :{name}")
        occurrences.append((name, parameter))
        return f"${len(occurrences)}"

    positional_sql = NAMED_PARAMETER.sub(replace, sql)
    used_names = {name for name, _ in occurrences}
    if used_names != set(parameters):
        raise RuntimeError(
            f"unused runtime parameters: {sorted(set(parameters) - used_names)}"
        )
    if not occurrences:
        statement = (
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + sql + ";"
            if explain
            else sql + ";"
        )
        return statement, {
            "mode": "direct",
            "bound_parameter_count": 0,
            "named_parameter_count": 0,
            "positional_sql_sha256": sha256_text(positional_sql),
            "parameters": {},
            "occurrence_names": [],
        }

    statement_name = "qc_" + re.sub(r"[^a-z0-9_]", "_", observation_id.lower())
    statement_name = statement_name[:48] + "_" + sha256_text(observation_id)[:8]
    types = ", ".join(parameter_postgres_type(item) for _, item in occurrences)
    literals = ", ".join(postgres_parameter_literal(item) for _, item in occurrences)
    execution = (
        f"PREPARE {statement_name} ({types}) AS\n{positional_sql};\n"
        + (
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n"
            if explain
            else ""
        )
        + f"EXECUTE {statement_name} ({literals});\n"
        + f"DEALLOCATE {statement_name};"
    )
    return execution, {
        "mode": "prepare-execute",
        "bound_parameter_count": len(occurrences),
        "named_parameter_count": len(parameters),
        "positional_sql_sha256": sha256_text(positional_sql),
        "parameters": {
            name: parameter_summary(parameter)
            for name, parameter in sorted(parameters.items())
        },
        "occurrence_names": [name for name, _ in occurrences],
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
        raise RuntimeError(f"PostgreSQL returned invalid JSON: {raw[:1000]}") from exc


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
        f"PostgreSQL did not become ready: {(logs.stdout + logs.stderr)[-3000:]}"
    )


def setup_sql(args: argparse.Namespace) -> str:
    return f"""
ALTER DATABASE {DEFAULT_DATABASE} SET max_parallel_workers_per_gather = 0;
ALTER DATABASE {DEFAULT_DATABASE} SET jit = off;

CREATE TABLE subjects (
    id integer PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text,
    is_locked boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);

CREATE TABLE questions (
    id integer PRIMARY KEY,
    subject_id integer REFERENCES subjects(id) ON DELETE SET NULL,
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
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

CREATE INDEX ix_questions_subject_id ON questions (subject_id);
CREATE INDEX ix_questions_subject_type ON questions (subject_id, type);

ALTER TABLE subjects ALTER COLUMN name SET STATISTICS 10000;
ALTER TABLE subjects ALTER COLUMN is_locked SET STATISTICS 10000;
ALTER TABLE questions ALTER COLUMN subject_id SET STATISTICS 10000;
ALTER TABLE questions ALTER COLUMN type SET STATISTICS 10000;

INSERT INTO subjects (id, name, description, is_locked, created_at)
SELECT subject_id,
       'Subject ' || lpad(subject_id::text, 5, '0'),
       'PUBLIC TEST ONLY question-count plan fixture',
       CASE WHEN subject_id % 20 = 0 THEN true
            WHEN subject_id % 20 = 1 THEN NULL
            ELSE false END,
       TIMESTAMP '2026-07-16 00:00:00'
FROM generate_series(1, {args.subject_count}) AS generated(subject_id);

{question_insert_sql(1, args.baseline_question_count, args.subject_count)}

VACUUM (ANALYZE) subjects;
VACUUM (ANALYZE) questions;
"""


def question_insert_sql(start: int, end: int, subject_count: int) -> str:
    return f"""
INSERT INTO questions (
    id, subject_id, type, content, options, answer, tags, difficulty,
    created_at, updated_at
)
SELECT question_id,
       CASE WHEN question_id % 1000 = 0 THEN NULL
            ELSE ((question_id - 1) % {subject_count}) + 1 END,
       (ARRAY['single_choice', 'multi_choice', 'boolean', 'fill', 'essay'])[
           1 + (question_id % 5)
       ],
       'Synthetic question ' || question_id::text,
       '[]',
       '[]',
       '[]',
       (question_id % 5) + 1,
       TIMESTAMP '2026-07-16 01:00:00',
       TIMESTAMP '2026-07-16 01:00:00'
FROM generate_series({start}, {end}) AS generated(question_id);
""".strip()


def extend_to_large_sql(args: argparse.Namespace) -> str:
    return (
        question_insert_sql(
            args.baseline_question_count + 1,
            args.large_question_count,
            args.subject_count,
        )
        + "\nVACUUM (ANALYZE) questions;"
    )


def fixture_subject_id(question_id: int, subject_count: int) -> Optional[int]:
    if question_id % 1000 == 0:
        return None
    return ((question_id - 1) % subject_count) + 1


def fixture_question_type(question_id: int) -> str:
    return ["single_choice", "multi_choice", "boolean", "fill", "essay"][
        question_id % 5
    ]


def expected_count(
    question_count: int,
    subject_count: int,
    *,
    require_existing_subject: bool,
    subject_name: Optional[str] = None,
    question_type: Optional[str] = None,
    excluded_subject_ids: Iterable[int] = (),
    candidate_question_ids: Optional[Iterable[int]] = None,
) -> int:
    excluded = set(excluded_subject_ids)
    candidates = (
        range(1, question_count + 1)
        if candidate_question_ids is None
        else candidate_question_ids
    )
    total = 0
    for question_id in candidates:
        if question_id < 1 or question_id > question_count:
            continue
        subject_id = fixture_subject_id(question_id, subject_count)
        if require_existing_subject and subject_id is None:
            continue
        if subject_id is not None and subject_id % 20 == 0:
            continue
        if subject_id in excluded:
            continue
        if subject_name is not None:
            expected_subject = (
                None if subject_id is None else f"Subject {subject_id:05d}"
            )
            if expected_subject != subject_name:
                continue
        if question_type is not None and fixture_question_type(question_id) != question_type:
            continue
        total += 1
    return total


def manifest_queries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {query["query_id"]: query for query in manifest["queries"]}


def query_specs(
    manifest: dict[str, Any], args: argparse.Namespace, *, large: bool
) -> list[dict[str, Any]]:
    queries = manifest_queries(manifest)
    if not large:
        restricted_parameters = manifest_parameter_values(
            queries["question-count-auth-restricted"]
        )
        candidate_parameters = manifest_parameter_values(
            queries["question-count-candidate-large"]
        )
        excluded_ids = restricted_parameters["excluded_subject_ids"]
        candidate_ids = candidate_parameters["candidate_question_ids"]
        return [
            {
                "observation_id": (
                    f"anonymous-all-baseline-{args.baseline_question_count}"
                ),
                "runtime_query": queries["question-count-anonymous-all"],
                "parameters": {},
                "expected_count": expected_count(
                    args.baseline_question_count,
                    args.subject_count,
                    require_existing_subject=False,
                ),
                "fixture_question_count": args.baseline_question_count,
                "required_index_groups": [],
            },
            {
                "observation_id": (
                    "authenticated-unrestricted-baseline-"
                    f"{args.baseline_question_count}"
                ),
                "runtime_query": queries["question-count-auth-unrestricted"],
                "parameters": {},
                "expected_count": expected_count(
                    args.baseline_question_count,
                    args.subject_count,
                    require_existing_subject=True,
                ),
                "fixture_question_count": args.baseline_question_count,
                "required_index_groups": [],
            },
            {
                "observation_id": (
                    "authenticated-restricted-baseline-"
                    f"{args.baseline_question_count}"
                ),
                "runtime_query": queries["question-count-auth-restricted"],
                "parameters": restricted_parameters,
                "expected_count": expected_count(
                    args.baseline_question_count,
                    args.subject_count,
                    require_existing_subject=True,
                    excluded_subject_ids=excluded_ids,
                ),
                "fixture_question_count": args.baseline_question_count,
                "required_index_groups": [],
            },
            {
                "observation_id": (
                    f"subject-type-baseline-{args.baseline_question_count}"
                ),
                "runtime_query": queries["question-count-subject-type"],
                "parameters": {
                    "subject_name": "Subject 00002",
                    "question_type": "boolean",
                },
                "expected_count": expected_count(
                    args.baseline_question_count,
                    args.subject_count,
                    require_existing_subject=True,
                    subject_name="Subject 00002",
                    question_type="boolean",
                ),
                "fixture_question_count": args.baseline_question_count,
                "required_index_groups": [
                    {"subjects_name_key"},
                    {"ix_questions_subject_type", "questions_pkey"},
                ],
            },
            {
                "observation_id": (
                    f"candidate-manifest-{len(candidate_ids)}-baseline-"
                    f"{args.baseline_question_count}"
                ),
                "runtime_query": queries["question-count-candidate-large"],
                "parameters": candidate_parameters,
                "expected_count": expected_count(
                    args.baseline_question_count,
                    args.subject_count,
                    require_existing_subject=False,
                    candidate_question_ids=candidate_ids,
                ),
                "fixture_question_count": args.baseline_question_count,
                "required_index_groups": [],
            },
        ]

    manifest_parameters = manifest_parameter_values(
        queries["question-count-candidate-large"]
    )
    manifest_candidate_ids = manifest_parameters["candidate_question_ids"]
    boundary_candidate_ids = list(range(1, args.large_candidate_count + 1))
    return [
        {
            "observation_id": (
                f"candidate-manifest-{len(manifest_candidate_ids)}-large-"
                f"{args.large_question_count}"
            ),
            "runtime_query": queries["question-count-candidate-large"],
            "parameters": manifest_parameters,
            "expected_count": expected_count(
                args.large_question_count,
                args.subject_count,
                require_existing_subject=False,
                candidate_question_ids=manifest_candidate_ids,
            ),
            "fixture_question_count": args.large_question_count,
            "required_index_groups": [],
        },
        {
            "observation_id": (
                f"candidate-boundary-{len(boundary_candidate_ids)}-large-"
                f"{args.large_question_count}"
            ),
            "runtime_query": queries["question-count-candidate-large"],
            "parameters": {
                "candidate_question_ids": boundary_candidate_ids,
            },
            "expected_count": expected_count(
                args.large_question_count,
                args.subject_count,
                require_existing_subject=False,
                candidate_question_ids=boundary_candidate_ids,
            ),
            "fixture_question_count": args.large_question_count,
            "required_index_groups": [],
        }
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
    scalar_count: int,
    summary: dict[str, Any],
    temp_blocks: dict[str, float],
) -> list[str]:
    passed: list[str] = []
    if scalar_count != spec["expected_count"]:
        raise AssertionError(
            f"{spec['observation_id']} count {scalar_count}; "
            f"expected {spec['expected_count']}"
        )
    passed.append("expected-scalar-count")
    if summary["result_row_count"] != 1 or summary["root_actual_loops"] != 1:
        raise AssertionError("count plan must return one row in one root execution")
    passed.append("single-result-single-root-execution")
    if summary["node_count"] > 20 or summary["maximum_depth"] > 8:
        raise AssertionError("question-count plan exceeded node/depth bounds")
    passed.append("bounded-plan-shape")
    if summary["maximum_actual_loops"] > 1:
        raise AssertionError("question-count plan introduced repeated node execution")
    passed.append("no-row-driven-node-loop")
    relations = summary["relation_scan_occurrences"]
    if relations.get("questions") != 1 or relations.get("subjects") != 1:
        raise AssertionError(f"question-count relation scan drifted: {relations}")
    if set(relations) - {"questions", "subjects"}:
        raise AssertionError(f"question-count crossed data owners: {relations}")
    passed.append("catalog-only-fixed-relation-scan-budget")
    if any(value != 0 for value in temp_blocks.values()):
        raise AssertionError(f"question-count plan spilled to TEMP: {temp_blocks}")
    passed.append("no-temp-blocks")
    for group in spec["required_index_groups"]:
        if not set(group).intersection(summary["index_names"]):
            raise AssertionError(
                f"{spec['observation_id']} missed required index group {sorted(group)}"
            )
    if spec["required_index_groups"]:
        passed.append("selective-filter-index-observed")
    if execution["bound_parameter_count"] != len(execution["occurrence_names"]):
        raise AssertionError("bound parameter metadata is inconsistent")
    passed.append("single-select-constant-bind-surface")
    return passed


def capture_observation(
    container: str, spec: dict[str, Any]
) -> dict[str, Any]:
    runtime_query = spec["runtime_query"]
    parameters = bind_parameters(runtime_query, spec["parameters"])
    scalar_sql, scalar_execution = prepared_execution_sql(
        spec["observation_id"], runtime_query["sql"], parameters, explain=False
    )
    scalar_raw = psql(container, scalar_sql)
    scalar_lines = [line.strip() for line in scalar_raw.splitlines() if line.strip()]
    if len(scalar_lines) != 1 or not re.fullmatch(r"-?[0-9]+", scalar_lines[0]):
        raise RuntimeError(f"unexpected scalar count output: {scalar_raw[:1000]}")
    scalar_count = int(scalar_lines[0])

    explain_sql, execution = prepared_execution_sql(
        spec["observation_id"], runtime_query["sql"], parameters, explain=True
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
    checks = assert_plan(spec, execution, scalar_count, summary, temp_blocks)
    if scalar_execution != execution:
        raise AssertionError("scalar and EXPLAIN binding metadata drifted")

    return {
        "observation_id": spec["observation_id"],
        "runtime_query_id": runtime_query["query_id"],
        "source": (
            "server/src/main/java/io/saksk/ti/catalog/infrastructure/"
            "persistence/JdbcQuestionCountQueryAdapter.java"
        ),
        "fixture_question_count": spec["fixture_question_count"],
        "sql": runtime_query["sql"],
        "sql_sha256": sha256_text(runtime_query["sql"]),
        "sql_statement_count": 1,
        "scalar_count": scalar_count,
        "expected_scalar_count": spec["expected_count"],
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
    'max_parallel_workers_per_gather',
        current_setting('max_parallel_workers_per_gather'),
    'jit', current_setting('jit'),
    'work_mem', current_setting('work_mem')
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
  AND tablename IN ('subjects', 'questions');
""",
    )


def capture(
    args: argparse.Namespace,
    container: str,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    baseline = [
        capture_observation(container, spec)
        for spec in query_specs(manifest, args, large=False)
    ]
    psql(container, extend_to_large_sql(args))
    large = [
        capture_observation(container, spec)
        for spec in query_specs(manifest, args, large=True)
    ]
    observations = baseline + large

    candidate_observations = [
        item
        for item in observations
        if item["runtime_query_id"]
        == "question-count-candidate-large"
    ]
    bind_counts = {
        item["binding"]["bound_parameter_count"]
        for item in candidate_observations
    }
    named_counts = {
        item["binding"]["named_parameter_count"]
        for item in candidate_observations
    }
    if bind_counts != {1} or named_counts != {1}:
        raise AssertionError(
            f"candidate bind surface is not constant one array parameter: "
            f"bound={bind_counts} named={named_counts}"
        )
    candidate_counts = {
        item["binding"]["parameters"]["candidate_question_ids"]["element_count"]
        for item in candidate_observations
    }
    if args.large_candidate_count not in candidate_counts:
        raise AssertionError("large candidate boundary was not captured")
    manifest_candidate_count = manifest_queries(manifest)[
        "question-count-candidate-large"
    ]["parameters"]["candidate_question_ids"]["element_count"]
    if manifest_candidate_count < 100_000:
        raise AssertionError("Java manifest large candidate must contain at least 100000 IDs")
    if manifest_candidate_count not in candidate_counts:
        raise AssertionError("Java manifest candidate array was not executed")
    baseline_runtime_ids = {
        item["runtime_query_id"] for item in baseline
    }
    if baseline_runtime_ids != EXPECTED_QUERY_IDS:
        raise AssertionError(
            f"baseline runtime variant coverage drifted: {sorted(baseline_runtime_ids)}"
        )
    parameter_counts = {
        query_id: sorted({
            item["binding"]["bound_parameter_count"]
            for item in observations
            if item["runtime_query_id"] == query_id
        })
        for query_id in sorted(EXPECTED_QUERY_IDS)
    }
    expected_parameter_counts = {
        query_id: [len(EXPECTED_PARAMETER_NAMES[query_id])]
        for query_id in sorted(EXPECTED_QUERY_IDS)
    }
    if parameter_counts != expected_parameter_counts:
        raise AssertionError(
            f"runtime bind cardinality drifted: {parameter_counts}"
        )

    image_metadata = json.loads(
        run(["docker", "image", "inspect", args.image]).stdout
    )[0]
    expected_digest = args.image.split("@", 1)[1]
    repo_digests = sorted(image_metadata.get("RepoDigests", []))
    if not any(value.endswith(expected_digest) for value in repo_digests):
        raise AssertionError("resolved PostgreSQL image digest drifted")

    indexes = index_definitions(container)
    index_names = {item["name"] for item in indexes}
    required_indexes = {
        "subjects_pkey",
        "subjects_name_key",
        "questions_pkey",
        "ix_questions_subject_id",
        "ix_questions_subject_type",
    }
    if not required_indexes.issubset(index_names):
        raise AssertionError(
            f"question-count fixture indexes drifted: {sorted(index_names)}"
        )

    root = Path(__file__).resolve().parents[1]
    tool_path = Path(__file__).resolve()
    adapter_path = root / (
        "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "JdbcQuestionCountQueryAdapter.java"
    )
    exporter_path = root / (
        "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
        "QuestionCountRuntimeSqlManifestTest.java"
    )
    manifest_text = manifest_path.read_text(encoding="utf-8")
    return {
        "evidence_id": "ti.phase4a.question-count-query-plan",
        "schema_version": 1,
        "captured_on": "2026-07-16",
        "scope": "catalog-owned-question-count-primitives",
        "runtime_sql_contract": {
            "source": "Java adapter runtime SQL manifest exported before capture",
            "manifest_id": manifest["manifest_id"],
            "manifest_schema_version": manifest["schema_version"],
            "manifest_sha256": sha256_text(manifest_text),
            "adapter_class": manifest.get("adapter_class"),
            "query_ids": sorted(EXPECTED_QUERY_IDS),
            "forbidden_runtime_effects": [
                "DML",
                "DDL",
                "TEMP objects",
                "multiple SQL statements",
            ],
        },
        "inputs": {
            "adapter": str(adapter_path.relative_to(root)),
            "adapter_sha256": sha256_text(adapter_path.read_text(encoding="utf-8")),
            "runtime_sql_manifest": str(manifest_path.relative_to(root)),
            "runtime_sql_manifest_sha256": sha256_text(manifest_text),
            "runtime_sql_exporter": str(exporter_path.relative_to(root)),
            "runtime_sql_exporter_sha256": sha256_text(
                exporter_path.read_text(encoding="utf-8")
            ),
            "capture_tool_sha256": sha256_text(tool_path.read_text(encoding="utf-8")),
        },
        "environment": {
            "container_image": args.image,
            "container_image_id": image_metadata.get("Id"),
            "container_image_digest": repo_digests,
            "container_os": image_metadata.get("Os"),
            "container_architecture": image_metadata.get("Architecture"),
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment_metadata(container),
        },
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "subject_count": args.subject_count,
            "baseline_question_count": args.baseline_question_count,
            "large_question_count": args.large_question_count,
            "large_candidate_count": args.large_candidate_count,
            "large_candidate_boundary": "65536 IDs in one bigint[] bind, above 65535",
            "unassigned_distribution": "question_id % 1000 = 0",
            "locked_distribution": "subject_id % 20 = 0",
            "nullable_lock_distribution": "subject_id % 20 = 1",
            "index_definitions": indexes,
            "statistics": "VACUUM (ANALYZE) completed after each fixture stage",
        },
        "measurement": {
            "command": "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)",
            "timing_retained": False,
            "plan_expression_values_retained": False,
            "runs_per_observation": 1,
            "observations": observations,
        },
        "cross_observation_assertions": {
            "status": "passed",
            "runtime_variant_count": len(EXPECTED_QUERY_IDS),
            "baseline_runtime_variant_coverage": sorted(baseline_runtime_ids),
            "bound_parameter_counts_by_runtime_query": parameter_counts,
            "candidate_named_parameter_count": 1,
            "candidate_bound_parameter_count": 1,
            "candidate_element_counts": sorted(candidate_counts),
            "sql_statement_count_per_observation": 1,
            "n_plus_one": False,
            "runtime_dml_ddl_temp": False,
        },
        "interpretation": {
            "status": "bounded_synthetic_plan_evidence_only",
            "statement": (
                "The artifact fixes exact Java runtime SQL hashes, constant array-bind "
                "cardinality, catalog-only relation scan budgets, result counts, plan "
                "shape bounds, and absence of TEMP spill. Timing and buffer values are "
                "observed only and are not production latency or capacity claims."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/capture_phase4a_question_count_query_plans.py "
                "--output Ti-Java/docs/refactor/phase4a/"
                "question-count-query-plan-evidence.json"
            ),
            "isolation": "ephemeral network-disabled container; removed in finally",
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

    container = f"ti-phase4a-question-count-plan-{uuid.uuid4().hex[:12]}"
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
                "--env=POSTGRES_PASSWORD=PUBLIC-TEST-ONLY-question-count",
                f"--env=POSTGRES_DB={DEFAULT_DATABASE}",
                args.image,
            ]
        )
        started = True
        wait_until_ready(container, args.startup_timeout_seconds)
        psql(container, setup_sql(args))
        evidence = capture(args, container, manifest, manifest_path)

        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
        print(f"wrote {output}")
        print(f"sha256 {sha256_text(output.read_text(encoding='utf-8'))}")
        return 0
    finally:
        if started:
            run(["docker", "rm", "--force", container], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
