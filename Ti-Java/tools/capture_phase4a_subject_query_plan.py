#!/usr/bin/env python3
"""Capture PostgreSQL 18 query-plan evidence for Phase 4A subject reads.

The script starts an isolated, network-disabled PostgreSQL container, builds a
scaled synthetic data set, captures JSON EXPLAIN ANALYZE output for the exact
catalog and identity SQL used by the Java adapters, then removes the container.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_IMAGE = "postgres:18"
DEFAULT_DATABASE = "phase4a_query_plan"
DEFAULT_SUBJECT_COUNT = 5_000
DEFAULT_QUESTION_COUNT = 50_000
DEFAULT_USER_COUNT = 200
DEFAULT_RESTRICTIONS_PER_USER = 250
DEFAULT_IDENTITY_ID = 4_101
FIRST_USER_ID = 4_101
ADMINISTRATOR_ID = 4_102

CATALOG_SQL = """
SELECT s.id AS subject_id,
       s.name AS subject_name,
       COUNT(q.id) AS question_count
FROM subjects s
LEFT JOIN questions q ON q.subject_id = s.id
WHERE s.is_locked = false OR s.is_locked IS NULL
GROUP BY s.id, s.name
ORDER BY s.id ASC
""".strip()

IDENTITY_SQL_TEMPLATE = """
SELECT u.is_admin AS administrator,
       us.subject_id AS restricted_subject_id
FROM users u
LEFT JOIN user_subjects us ON us.user_id = u.id
WHERE u.id = {identity_id}
ORDER BY us.subject_id ASC NULLS FIRST
""".strip()


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture scaled PostgreSQL 18 plans for Phase 4A subject reads."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "docs/refactor/phase4a/subject-query-plan.json",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--subject-count", type=int, default=DEFAULT_SUBJECT_COUNT)
    parser.add_argument("--question-count", type=int, default=DEFAULT_QUESTION_COUNT)
    parser.add_argument("--user-count", type=int, default=DEFAULT_USER_COUNT)
    parser.add_argument(
        "--restrictions-per-user",
        type=int,
        default=DEFAULT_RESTRICTIONS_PER_USER,
    )
    parser.add_argument("--identity-id", type=int, default=DEFAULT_IDENTITY_ID)
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.subject_count < 3_000:
        raise ValueError("--subject-count must be at least 3000")
    if args.question_count < 20_000:
        raise ValueError("--question-count must be at least 20000")
    if args.user_count < 2:
        raise ValueError("--user-count must be at least 2")
    if not 1 <= args.restrictions_per_user <= args.subject_count:
        raise ValueError("--restrictions-per-user must be between 1 and subject-count")
    if args.user_count * args.restrictions_per_user < 10_000:
        raise ValueError("the generated data set must contain at least 10000 restrictions")
    last_user_id = FIRST_USER_ID + args.user_count - 1
    if not FIRST_USER_ID <= args.identity_id <= last_user_id:
        raise ValueError(
            f"--identity-id must be within generated users {FIRST_USER_ID}..{last_user_id}"
        )
    if args.identity_id == ADMINISTRATOR_ID:
        raise ValueError("--identity-id must select an ordinary user, not the administrator")
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")


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
            f"{result.stderr.strip()[-2000:]}"
        )
    return result.stdout.strip()


def psql_json(container: str, sql: str) -> Any:
    output = psql(container, sql)
    if not output:
        raise RuntimeError("PostgreSQL returned an empty JSON result")
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"PostgreSQL returned invalid JSON: {output[:500]}") from exc


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
        f"PostgreSQL did not become ready in {timeout_seconds}s:\n{logs.stderr[-2000:]}"
    )


def setup_sql(args: argparse.Namespace) -> str:
    question_subject_count = max(1, args.subject_count * 4 // 5)
    last_user_id = FIRST_USER_ID + args.user_count - 1
    return f"""
CREATE TABLE plaza_boards (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
);

CREATE TABLE subjects (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text,
    is_locked boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    plaza_board_id integer REFERENCES plaza_boards(id) ON DELETE SET NULL,
    is_plaza_featured boolean DEFAULT false NOT NULL,
    plaza_featured_weight integer DEFAULT 0 NOT NULL,
    plaza_featured_at timestamp without time zone
);

CREATE TABLE users (
    id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    username varchar(128) NOT NULL UNIQUE,
    password_hash text NOT NULL,
    is_admin boolean NOT NULL DEFAULT false,
    is_locked boolean NOT NULL DEFAULT false,
    session_version integer NOT NULL DEFAULT 0,
    is_subject_admin boolean NOT NULL DEFAULT false,
    is_notification_admin boolean NOT NULL DEFAULT false,
    has_password_set boolean NOT NULL DEFAULT false,
    email text,
    phone varchar(20) UNIQUE,
    openid text,
    last_active timestamp without time zone
);
CREATE INDEX users_email_idx ON users (email);

CREATE TABLE questions (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
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

CREATE TABLE user_subjects (
    id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id integer NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    restricted_at timestamp without time zone DEFAULT now(),
    restricted_by bigint REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_user_subjects_user_subject UNIQUE (user_id, subject_id)
);
CREATE INDEX ix_user_subjects_user_id ON user_subjects (user_id);

INSERT INTO subjects (id, name, description, is_locked, created_at)
SELECT subject_id,
       'Scaled subject ' || lpad(subject_id::text, 5, '0'),
       'Phase 4A public synthetic query-plan fixture',
       CASE
           WHEN subject_id % 20 = 0 THEN true
           WHEN subject_id % 20 = 1 THEN NULL
           ELSE false
       END,
       TIMESTAMP '2026-07-16 00:00:00'
FROM generate_series(1, {args.subject_count}) AS generated(subject_id);

INSERT INTO users (
    id,
    username,
    password_hash,
    is_admin,
    is_locked,
    session_version,
    has_password_set,
    email
)
SELECT identity_id,
       'scaled-user-' || identity_id::text,
       'PUBLIC-TEST-ONLY',
       identity_id = {ADMINISTRATOR_ID},
       false,
       1,
       true,
       'scaled-user-' || identity_id::text || '@test.example.com'
FROM generate_series({FIRST_USER_ID}, {last_user_id}) AS generated(identity_id);

INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    options,
    answer,
    tags,
    difficulty,
    created_by,
    updated_by,
    created_at,
    updated_at
)
SELECT question_id,
       ((question_id - 1) % {question_subject_count}) + 1,
       CASE question_id % 4
           WHEN 0 THEN 'single_choice'
           WHEN 1 THEN 'boolean'
           WHEN 2 THEN 'fill'
           ELSE 'essay'
       END,
       'Scaled question ' || question_id::text,
       '[]',
       '[]',
       '[]',
       (question_id % 5) + 1,
       {ADMINISTRATOR_ID},
       {ADMINISTRATOR_ID},
       TIMESTAMP '2026-07-16 01:00:00',
       TIMESTAMP '2026-07-16 01:00:00'
FROM generate_series(1, {args.question_count}) AS generated(question_id);

INSERT INTO user_subjects (user_id, subject_id, restricted_at, restricted_by)
SELECT users.id,
       (((users.id - {FIRST_USER_ID}) * 251 + restriction_number - 1)
           % {args.subject_count}) + 1,
       TIMESTAMP '2026-07-16 02:00:00',
       {ADMINISTRATOR_ID}
FROM users
CROSS JOIN generate_series(1, {args.restrictions_per_user})
    AS restrictions(restriction_number);

VACUUM (ANALYZE) subjects;
VACUUM (ANALYZE) questions;
VACUUM (ANALYZE) users;
VACUUM (ANALYZE) user_subjects;
"""


def plan_nodes(root: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []

    def visit(node: Dict[str, Any], depth: int) -> None:
        selected_keys = (
            "Node Type",
            "Strategy",
            "Join Type",
            "Relation Name",
            "Alias",
            "Index Name",
            "Actual Startup Time",
            "Actual Total Time",
            "Actual Rows",
            "Actual Loops",
            "Rows Removed by Filter",
            "Filter",
            "Index Cond",
            "Hash Cond",
            "Sort Key",
            "Group Key",
        )
        summary = {"depth": depth}
        summary.update({key: node[key] for key in selected_keys if key in node})
        nodes.append(summary)
        for child in node.get("Plans", []):
            visit(child, depth + 1)

    visit(root, 0)
    return nodes


def summarize_plan(explain: Dict[str, Any], result_row_count: int) -> Dict[str, Any]:
    root = explain["Plan"]
    nodes = plan_nodes(root)
    node_types = Counter(node["Node Type"] for node in nodes)
    index_names = sorted(
        {str(node["Index Name"]) for node in nodes if "Index Name" in node}
    )
    relation_names = sorted(
        {str(node["Relation Name"]) for node in nodes if "Relation Name" in node}
    )
    buffer_keys = (
        "Shared Hit Blocks",
        "Shared Read Blocks",
        "Shared Dirtied Blocks",
        "Shared Written Blocks",
        "Local Hit Blocks",
        "Local Read Blocks",
        "Temp Read Blocks",
        "Temp Written Blocks",
    )
    return {
        "result_row_count": result_row_count,
        "planning_time_ms": explain.get("Planning Time"),
        "actual_execution_time_ms": explain.get("Execution Time"),
        "root": {
            "node_type": root.get("Node Type"),
            "plan_rows": root.get("Plan Rows"),
            "actual_rows": root.get("Actual Rows"),
            "actual_loops": root.get("Actual Loops"),
            "actual_startup_time_ms": root.get("Actual Startup Time"),
            "actual_total_time_ms": root.get("Actual Total Time"),
        },
        "node_type_counts": dict(sorted(node_types.items())),
        "index_names": index_names,
        "relation_names": relation_names,
        "root_buffers": {
            key: root[key]
            for key in buffer_keys
            if key in root
        },
        "nodes": nodes,
    }


def explain(container: str, sql: str) -> Dict[str, Any]:
    payload = psql_json(
        container,
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + sql + ";",
    )
    if not isinstance(payload, list) or len(payload) != 1 or "Plan" not in payload[0]:
        raise RuntimeError("unexpected EXPLAIN (FORMAT JSON) payload")
    return payload[0]


def scalar_count(container: str, sql: str) -> int:
    output = psql(container, f"SELECT COUNT(*) FROM ({sql}) AS measured_result;")
    return int(output)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def capture(args: argparse.Namespace, container: str, image_id: str) -> Dict[str, Any]:
    identity_sql = IDENTITY_SQL_TEMPLATE.format(identity_id=args.identity_id)
    dataset = psql_json(
        container,
        f"""
SELECT json_build_object(
    'subjects', (SELECT COUNT(*) FROM subjects),
    'visible_subjects', (
        SELECT COUNT(*) FROM subjects
        WHERE is_locked = false OR is_locked IS NULL
    ),
    'locked_subjects', (SELECT COUNT(*) FROM subjects WHERE is_locked = true),
    'nullable_lock_subjects', (SELECT COUNT(*) FROM subjects WHERE is_locked IS NULL),
    'questions', (SELECT COUNT(*) FROM questions),
    'subjects_with_questions', (
        SELECT COUNT(DISTINCT subject_id) FROM questions WHERE subject_id IS NOT NULL
    ),
    'visible_subjects_with_zero_questions', (
        SELECT COUNT(*)
        FROM subjects s
        WHERE (s.is_locked = false OR s.is_locked IS NULL)
          AND NOT EXISTS (SELECT 1 FROM questions q WHERE q.subject_id = s.id)
    ),
    'users', (SELECT COUNT(*) FROM users),
    'restriction_relations', (SELECT COUNT(*) FROM user_subjects),
    'selected_identity_id', {args.identity_id},
    'selected_identity_restrictions', (
        SELECT COUNT(*) FROM user_subjects WHERE user_id = {args.identity_id}
    )
);
""",
    )
    environment = psql_json(
        container,
        """
SELECT json_build_object(
    'version', version(),
    'server_version', current_setting('server_version'),
    'server_version_num', current_setting('server_version_num'),
    'block_size_bytes', current_setting('block_size'),
    'shared_buffers', current_setting('shared_buffers'),
    'work_mem', current_setting('work_mem'),
    'effective_cache_size', current_setting('effective_cache_size'),
    'random_page_cost', current_setting('random_page_cost'),
    'effective_io_concurrency', current_setting('effective_io_concurrency'),
    'max_parallel_workers_per_gather', current_setting('max_parallel_workers_per_gather'),
    'jit', current_setting('jit')
);
""",
    )
    index_definitions = psql_json(
        container,
        """
SELECT COALESCE(json_agg(indexdef ORDER BY tablename, indexname), '[]'::json)
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('subjects', 'questions', 'users', 'user_subjects');
""",
    )
    image_metadata_raw = run(["docker", "image", "inspect", image_id]).stdout
    image_metadata = json.loads(image_metadata_raw)[0]

    catalog_explain = explain(container, CATALOG_SQL)
    catalog_rows = scalar_count(container, CATALOG_SQL)
    identity_explain = explain(container, identity_sql)
    identity_rows = scalar_count(container, identity_sql)

    queries = [
        {
            "query_id": "catalog-unlocked-subjects-with-question-counts",
            "source": "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/JdbcSubjectCatalogQueryAdapter.java",
            "parameters": {},
            "sql": CATALOG_SQL,
            "sql_sha256": sha256_text(CATALOG_SQL),
            "plan_summary": summarize_plan(catalog_explain, catalog_rows),
            "explain_analyze": catalog_explain,
        },
        {
            "query_id": "identity-subject-access",
            "source": "server/src/main/java/io/saksk/ti/identity/infrastructure/persistence/JdbcSubjectAccessReadAdapter.java",
            "parameters": {"identity_id": args.identity_id, "administrator": False},
            "sql": identity_sql,
            "sql_sha256": sha256_text(identity_sql),
            "plan_summary": summarize_plan(identity_explain, identity_rows),
            "explain_analyze": identity_explain,
        },
    ]
    return {
        "evidence_id": "ti.phase4a.subject-query-plan",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "protected-subject-directory-business-queries",
        "scope_note": (
            "This artifact covers the two SELECTs owned by the catalog business use case. "
            "The separate authentication-authority SELECT is covered by request-level "
            "integration evidence, making three SELECTs on the normal successful HTTP path."
        ),
        "environment": {
            "container_image": args.image,
            "container_image_id": image_id,
            "container_image_digest": image_metadata.get("RepoDigests", []),
            "container_os": image_metadata.get("Os"),
            "container_architecture": image_metadata.get("Architecture"),
            "network": "none",
            "database": DEFAULT_DATABASE,
            "postgresql": environment,
        },
        "data_set": {
            "kind": "public deterministic synthetic fixture",
            "parameters": {
                "subject_count": args.subject_count,
                "question_count": args.question_count,
                "question_subject_count": args.subject_count * 4 // 5,
                "user_count": args.user_count,
                "restrictions_per_user": args.restrictions_per_user,
                "identity_id": args.identity_id,
            },
            "actual_row_counts": dataset,
            "distribution": {
                "locked_subject": "subject_id % 20 = 0",
                "nullable_is_locked": "subject_id % 20 = 1",
                "question_subject": "round-robin over the first 80 percent of subjects",
                "restriction_subject": "deterministic rotating unique subject IDs per user",
            },
            "index_definitions": index_definitions,
            "statistics": "VACUUM (ANALYZE) completed for all four queried tables before capture",
        },
        "measurement": {
            "command": "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)",
            "runs_per_query": 1,
            "cache_state": "not controlled; capture follows fixture loading and VACUUM (ANALYZE)",
            "queries": queries,
        },
        "interpretation": {
            "status": "observational_evidence_only",
            "statement": (
                "The recorded plans and execution times describe one isolated synthetic "
                "PostgreSQL 18 run. No hard latency threshold, production capacity claim, "
                "or pass/fail performance conclusion is inferred from this artifact."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/capture_phase4a_subject_query_plan.py "
                "--output Ti-Java/docs/refactor/phase4a/subject-query-plan.json"
            ),
            "prerequisite": "Docker with access to the postgres:18 image",
            "isolation": "ephemeral network-disabled container; removed on success or failure",
        },
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    if shutil.which("docker") is None:
        raise SystemExit("docker is required")

    container = f"ti-phase4a-subject-plan-{uuid.uuid4().hex[:12]}"
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
            ]
        )
        started = True
        container_id = start.stdout.strip()
        wait_until_ready(container, args.startup_timeout_seconds)
        psql(container, setup_sql(args))
        image_id = run(
            ["docker", "inspect", "--format={{.Image}}", container]
        ).stdout.strip()
        evidence = capture(args, container, image_id)

        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
        print(f"wrote {output}")
        print(f"container {container_id[:12]} removed after capture")
        return 0
    finally:
        if started:
            run(["docker", "rm", "--force", container], check=False)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
