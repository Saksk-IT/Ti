#!/usr/bin/env python3
"""Capture deterministic dual-PostgreSQL plans for user-counts evidence SQL."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
import uuid

import capture_phase4b_personal_bank_usage_stats_query_plans as usage_base


base = usage_base.base
POSTGRES_IMAGES = usage_base.POSTGRES_IMAGES
DEFAULT_DATABASE = "phase4b_personal_bank_user_counts_plan"
DEFAULT_BANK_COUNT = 5_000
DEFAULT_QUESTION_COUNT = 150_000
DEFAULT_LARGE_TAG_PARAMETER_COUNT = 900
MAX_LARGE_TAG_PARAMETER_COUNT = 900
TARGET_BANK_ID = 7_101
TARGET_VIEWER_ID = 7_001
TARGET_Q_TYPE = "single_choice"
TARGET_TAG_IDS = (8_101, 8_102, 8_201)
GENERATED_USER_OFFSET = 100_000
GENERATED_BANK_OFFSET = 1_000_000
GENERATED_QUESTION_OFFSET = 10_000_000
GENERATED_FAVORITE_OFFSET = 20_000_000
GENERATED_MISTAKE_OFFSET = 30_000_000
FAVORITE_INTERVAL = 4
MISTAKE_INTERVAL = 6

MANIFEST_ID = "ti.phase4b.personal-bank-user-counts-preimplementation-sql"
SOURCE_CLASS = (
    "io.saksk.ti.personalbank.infrastructure.persistence."
    "PersonalBankUserCountsEvidenceSql"
)
QUERY_IDS = (
    "personal-bank-user-counts-bank-access",
    "personal-bank-user-counts-share-access",
    "personal-bank-user-counts-all-count",
    "personal-bank-user-counts-favorites-count",
    "personal-bank-user-counts-mistakes-count",
    "personal-bank-user-counts-all-types",
    "personal-bank-user-counts-favorites-types",
    "personal-bank-user-counts-mistakes-types",
)
STATISTICS_QUERY_IDS = QUERY_IDS[2:]
TYPE_QUERY_IDS = frozenset(QUERY_IDS[5:])
VIEWER_QUERY_IDS = frozenset((QUERY_IDS[1], QUERY_IDS[3], QUERY_IDS[4], QUERY_IDS[6], QUERY_IDS[7]))
EXPECTED_OPERATIONS = (
    "bank-access",
    "share-access",
    "all-count",
    "favorites-count",
    "mistakes-count",
    "all-types",
    "favorites-types",
    "mistakes-types",
)
EXPECTED_BASE_SQL = {
    QUERY_IDS[0]: "select * from user_question_banks where id = :bank_id",
    QUERY_IDS[1]: (
        "select bsr.*, bs.permission, bs.is_active, bs.expires_at "
        "from bank_share_records bsr join bank_shares bs on bsr.share_id = bs.id "
        "where bsr.user_id = :user_id and bsr.bank_id = :bank_id and bsr.status = 1"
    ),
    QUERY_IDS[2]: (
        "select count(*) as cnt from user_bank_questions q "
        "where q.bank_id = :bank_id"
    ),
    QUERY_IDS[3]: (
        "select count(*) as cnt from user_bank_questions q "
        "join user_bank_favorites f on q.id = f.question_id "
        "where q.bank_id = :bank_id and f.user_id = :uid"
    ),
    QUERY_IDS[4]: (
        "select count(*) as cnt from user_bank_questions q "
        "join user_bank_mistakes m on q.id = m.question_id "
        "where q.bank_id = :bank_id and m.user_id = :uid"
    ),
    QUERY_IDS[5]: (
        "select distinct q.type as p_type from user_bank_questions q "
        "where q.bank_id = :bank_id order by q.type"
    ),
    QUERY_IDS[6]: (
        "select distinct q.type as p_type from user_bank_questions q "
        "join user_bank_favorites f on q.id = f.question_id "
        "where q.bank_id = :bank_id and f.user_id = :uid order by q.type"
    ),
    QUERY_IDS[7]: (
        "select distinct q.type as p_type from user_bank_questions q "
        "join user_bank_mistakes m on q.id = m.question_id "
        "where q.bank_id = :bank_id and m.user_id = :uid order by q.type"
    ),
}
EXPECTED_SEQUENCES = {
    "all": [QUERY_IDS[2], QUERY_IDS[3], QUERY_IDS[4], QUERY_IDS[5]],
    "favorites": [QUERY_IDS[3], QUERY_IDS[3], QUERY_IDS[4], QUERY_IDS[6]],
    "mistakes": [QUERY_IDS[4], QUERY_IDS[3], QUERY_IDS[4], QUERY_IDS[7]],
}
EXPECTED_VARIANTS = (
    ("unfiltered", False, 0),
    ("q-type-only", True, 0),
    ("tag-1", False, 1),
    ("tag-3", False, 3),
    ("q-type+tag-3", True, 3),
)
FIXTURE_INPUTS = (
    "server/src/test/resources/db/phase3/030-auth-schema.sql",
    "server/src/test/resources/db/phase4b/062-personal-bank-share-list-schema.sql",
    "server/src/test/resources/db/phase4b/063-personal-bank-share-list-seed.sql",
    "server/src/test/resources/db/phase4b/064-personal-bank-all-shares-seed.sql",
    "server/src/test/resources/db/phase4b/065-personal-bank-usage-stats-schema.sql",
    "server/src/test/resources/db/phase4b/066-personal-bank-usage-stats-seed.sql",
    "server/src/test/resources/db/phase4b/067-personal-bank-user-counts-schema.sql",
    "server/src/test/resources/db/phase4b/068-personal-bank-user-counts-seed.sql",
)
TIMING_KEYS = usage_base.TIMING_KEYS
BUFFER_KEYS = usage_base.BUFFER_KEYS
SENSITIVE_KEY_FRAGMENTS = usage_base.SENSITIVE_KEY_FRAGMENTS


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Capture Java-exported PG16/PG18 user-counts query plans."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            root / "docs/refactor/phase4b/"
            "personal-bank-user-counts-query-plan-evidence.json"
        ),
    )
    parser.add_argument(
        "--sql-manifest",
        type=Path,
        default=(
            root / "server/target/"
            "phase4b-personal-bank-user-counts-evidence-sql.json"
        ),
    )
    parser.add_argument(
        "--bank-count", type=int, default=DEFAULT_BANK_COUNT
    )
    parser.add_argument(
        "--question-count", type=int, default=DEFAULT_QUESTION_COUNT
    )
    parser.add_argument(
        "--large-tag-parameter-count",
        type=int,
        default=DEFAULT_LARGE_TAG_PARAMETER_COUNT,
    )
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.bank_count < DEFAULT_BANK_COUNT:
        raise ValueError(f"--bank-count must be at least {DEFAULT_BANK_COUNT}")
    if args.question_count < DEFAULT_QUESTION_COUNT:
        raise ValueError(
            f"--question-count must be at least {DEFAULT_QUESTION_COUNT}"
        )
    if not 1 <= args.large_tag_parameter_count <= MAX_LARGE_TAG_PARAMETER_COUNT:
        raise ValueError(
            "--large-tag-parameter-count must be between 1 and "
            f"{MAX_LARGE_TAG_PARAMETER_COUNT}"
        )
    if args.startup_timeout_seconds <= 0:
        raise ValueError("--startup-timeout-seconds must be positive")
    for image in POSTGRES_IMAGES:
        if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", image["image"]):
            raise ValueError("PostgreSQL image must be an immutable digest reference")


def validate_paths(root: Path, output: Path, manifest: Path) -> None:
    root = root.resolve()
    output = output.resolve()
    manifest = manifest.resolve()
    evidence_dir = (root / "docs/refactor/phase4b").resolve()
    target_dir = (root / "server/target").resolve()
    if output == evidence_dir or evidence_dir not in output.parents:
        raise ValueError("user-counts plan output must stay under docs/refactor/phase4b")
    if manifest == target_dir or target_dir not in manifest.parents:
        raise ValueError("user-counts SQL manifest must stay under server/target")
    for relative in FIXTURE_INPUTS:
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or path.is_symlink():
            raise ValueError(f"user-counts fixture input is unsafe: {relative}")


def normalize_sql(sql: str) -> str:
    return base.normalize_sql(sql)


def expected_parameter_order(
    query_id: str,
    q_type_filter: bool,
    tag_parameter_count: int,
) -> list[str]:
    if query_id == QUERY_IDS[0]:
        return ["bank_id"]
    if query_id == QUERY_IDS[1]:
        return ["user_id", "bank_id"]
    order = ["bank_id"]
    if query_id in VIEWER_QUERY_IDS:
        order.append("uid")
    if q_type_filter:
        order.append("q_type_f")
    order.extend(f"tq_{index}" for index in range(tag_parameter_count))
    return order


def expected_parameter_types(order: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in order:
        if name in {"uid", "user_id"}:
            result[name] = "bigint"
        elif name == "q_type_f":
            result[name] = "text"
        else:
            result[name] = "integer"
    return result


def expected_sql(
    query_id: str,
    q_type_filter: bool = False,
    tag_parameter_count: int = 0,
) -> str:
    if query_id not in EXPECTED_BASE_SQL:
        raise RuntimeError(f"unexpected user-counts query id: {query_id}")
    if query_id in QUERY_IDS[:2]:
        if q_type_filter or tag_parameter_count:
            raise RuntimeError("access queries cannot receive statistics filters")
        return EXPECTED_BASE_SQL[query_id]
    sql = EXPECTED_BASE_SQL[query_id]
    order_suffix = " order by q.type" if query_id in TYPE_QUERY_IDS else ""
    if order_suffix:
        sql = sql.removesuffix(order_suffix)
    if q_type_filter:
        sql += " and q.type = :q_type_f"
    if tag_parameter_count:
        placeholders = ", ".join(
            f":tq_{index}" for index in range(tag_parameter_count)
        )
        sql += f" and q.id in ({placeholders})"
    return sql + order_suffix


def query_filter_shape(query: Mapping[str, Any]) -> tuple[bool, int]:
    order = query.get("parameter_order")
    if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
        raise RuntimeError("user-counts query parameter_order must be text list")
    q_type_filter = "q_type_f" in order
    tags = [name for name in order if name.startswith("tq_")]
    if tags != [f"tq_{index}" for index in range(len(tags))]:
        raise RuntimeError("user-counts tag parameter order is not contiguous")
    return q_type_filter, len(tags)


def validate_query(
    query: Mapping[str, Any],
    *,
    query_id: str,
    operation: str,
    ordinal: int,
    q_type_filter: bool,
    tag_parameter_count: int,
) -> None:
    expected_metadata = {
        "ordinal": ordinal,
        "query_id": query_id,
        "operation": operation,
        "parameter_order": expected_parameter_order(
            query_id, q_type_filter, tag_parameter_count
        ),
    }
    for key, value in expected_metadata.items():
        if query.get(key) != value:
            raise RuntimeError(f"{query_id} {key} drifted")
    parameters = query.get("parameters")
    expected_types = expected_parameter_types(expected_metadata["parameter_order"])
    if parameters != expected_types:
        raise RuntimeError(f"{query_id} parameter types drifted")
    sql = query.get("sql")
    if not isinstance(sql, str) or not sql.strip():
        raise RuntimeError(f"{query_id} SQL must be nonempty text")
    if ";" in sql or "--" in sql or "/*" in sql:
        raise RuntimeError(f"{query_id} SQL contains a separator or comment")
    if len(re.findall(r"\bselect\b", sql, re.IGNORECASE)) != 1:
        raise RuntimeError(f"{query_id} must contain exactly one SELECT")
    forbidden = base.FORBIDDEN_SQL.search(sql)
    if forbidden:
        raise RuntimeError(f"{query_id} contains forbidden token {forbidden.group(0)}")
    if re.search(r"\b(?:pg_temp|pg_catalog|information_schema)\b", sql, re.I):
        raise RuntimeError(f"{query_id} references a system schema")
    if normalize_sql(sql) != expected_sql(query_id, q_type_filter, tag_parameter_count):
        raise RuntimeError(f"{query_id} SQL shape drifted")
    occurrences = base.NAMED_PARAMETER.findall(sql)
    if occurrences != expected_metadata["parameter_order"]:
        raise RuntimeError(f"{query_id} bind occurrence order drifted")
    observed_shape = query_filter_shape(query)
    if observed_shape != (q_type_filter, tag_parameter_count):
        raise RuntimeError(f"{query_id} filter metadata drifted")


def export_sql_manifest(root: Path, output: Path) -> None:
    validate_paths(root, root / "docs/refactor/phase4b/placeholder.json", output)
    verifier = root / "infra/phase2/verify-in-maven-container.sh"
    result = base.run([
        str(verifier),
        "-q",
        "-DskipITs",
        "-Dtest=PersonalBankUserCountsEvidenceSqlManifestTest",
        f"-Dti.personal-bank-user-counts-evidence.sql-manifest-output={output.resolve()}",
        "test",
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"Java user-counts SQL export failed: {detail}")


def load_sql_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read Java user-counts SQL manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("user-counts SQL manifest root must be an object")
    expected_top = {
        "manifest_id": MANIFEST_ID,
        "schema_version": 1,
        "source_class": SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "baseline_route_owner": "personalbank",
        "production_owner_authorized": False,
        "implementation_authorized": False,
        "schema_or_index_delta_authorized": False,
        "cross_context_table_owner": "learning",
        "cross_context_table_owner_approval": "not-granted",
        "runtime_tag_ddl_or_legacy_migration_in_scope": False,
        "postgres_transaction_poisoning_sqlstate": "25P02",
        "q_type_parameter_type_evidence": {
            "parameter_name": "q_type_f",
            "manifest_parameters_field_scope": (
                "postgresql-explicit-prepare-declaration-for-query-plan-evidence"
            ),
            "manifest_prepare_type": "text",
            "jdbc_client_observation_scope": (
                "spring-jdbcclient-java-string-binding-in-compatibility-it"
            ),
            "jdbc_client_observed_pg_typeof": "character varying",
            "legacy_runtime_bind_type_claimed": False,
            "cross_scope_type_identity_claimed": False,
            "legacy_q_type_predicate_changed": False,
        },
        "jdbc_compatibility_evidence": {
            "integration_test": (
                "io.saksk.ti.integration."
                "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT"
            ),
            "postgres_versions": ["16.14", "18.4"],
            "initial_statement_failure_sqlstate": "42703",
            "poisoned_followup_sqlstate": "25P02",
            "rollback_recovery_required": True,
        },
        "access_query_count": 2,
        "statistics_query_count_per_nonempty_read": 4,
        "query_family_count": 8,
        "query_order": list(QUERY_IDS),
    }
    for key, value in expected_top.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"user-counts SQL manifest {key} drifted")

    queries = manifest.get("queries")
    if not isinstance(queries, list) or len(queries) != 8:
        raise RuntimeError("user-counts manifest must contain eight query families")
    for ordinal, (query, query_id, operation) in enumerate(
        zip(queries, QUERY_IDS, EXPECTED_OPERATIONS), start=1
    ):
        if not isinstance(query, dict):
            raise RuntimeError("user-counts query family must be an object")
        validate_query(
            query,
            query_id=query_id,
            operation=operation,
            ordinal=ordinal,
            q_type_filter=False,
            tag_parameter_count=0,
        )

    if manifest.get("statistics_sequences") != EXPECTED_SEQUENCES:
        raise RuntimeError("user-counts source sequence metadata drifted")
    variants = manifest.get("canonical_variants")
    if not isinstance(variants, list) or len(variants) != len(EXPECTED_VARIANTS):
        raise RuntimeError("user-counts canonical variants drifted")
    for variant, (variant_id, q_type_filter, tag_count) in zip(
        variants, EXPECTED_VARIANTS
    ):
        if not isinstance(variant, dict):
            raise RuntimeError("user-counts canonical variant must be an object")
        for key, value in {
            "variant_id": variant_id,
            "q_type_filter": q_type_filter,
            "tag_parameter_count": tag_count,
            "query_count": 6,
        }.items():
            if variant.get(key) != value:
                raise RuntimeError(f"user-counts variant {variant_id} {key} drifted")
        variant_queries = variant.get("queries")
        if not isinstance(variant_queries, list) or len(variant_queries) != 6:
            raise RuntimeError(f"user-counts variant {variant_id} query count drifted")
        for ordinal, (query, query_id, operation) in enumerate(
            zip(
                variant_queries,
                STATISTICS_QUERY_IDS,
                EXPECTED_OPERATIONS[2:],
            ),
            start=1,
        ):
            if not isinstance(query, dict):
                raise RuntimeError("user-counts variant query must be an object")
            validate_query(
                query,
                query_id=query_id,
                operation=operation,
                ordinal=ordinal,
                q_type_filter=q_type_filter,
                tag_parameter_count=tag_count,
            )

    if manifest.get("empty_resolved_tag_ids") != {
        "http_result": "zero-count-success",
        "statistics_query_count": 0,
        "dynamic_in_query_emitted": False,
    }:
        raise RuntimeError("user-counts empty resolved tag contract drifted")
    if manifest.get("raw_type_projection") != {
        "jdbc_type": "text",
        "nullable": True,
        "blank_and_unknown_values_preserved": True,
        "application_type_mapping_in_scope": False,
    }:
        raise RuntimeError("user-counts raw type projection drifted")
    if manifest.get("legacy_join_shape") != {
        "favorites_bank_id_predicate": False,
        "mistakes_bank_id_predicate": False,
    }:
        raise RuntimeError("user-counts legacy join shape drifted")
    large = manifest.get("large_tag_safety")
    expected_large_names = [f"tq_{index}" for index in range(900)]
    expected_large_predicate = "q.id IN (" + ", ".join(
        f":{name}" for name in expected_large_names
    ) + ")"
    expected_large = {
        "canonical_variant_id": "tag-900-boundary",
        "evidence_render_bound": 900,
        "evidence_renderer_overflow_rejected": True,
        "legacy_explicit_tag_id_limit_present": False,
        "legacy_explicit_tag_id_limit": None,
        "overflow_above_evidence_bound": "not-a-captured-legacy-rejection",
        "production_limit_strategy_authorized": False,
        "values_interpolated_into_sql": False,
        "full_query_plan_required": False,
        "predicate": expected_large_predicate,
        "parameter_order": expected_large_names,
        "parameter_names_unique": True,
    }
    if large != expected_large:
        raise RuntimeError("user-counts large-tag manifest safety drifted")
    return manifest


def variant_by_id(manifest: Mapping[str, Any], variant_id: str) -> dict[str, Any]:
    matches = [
        variant for variant in manifest["canonical_variants"]
        if variant.get("variant_id") == variant_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"user-counts canonical variant missing: {variant_id}")
    return matches[0]


def build_large_tag_queries(
    manifest: Mapping[str, Any],
    tag_parameter_count: int,
) -> list[dict[str, Any]]:
    if not 1 <= tag_parameter_count <= MAX_LARGE_TAG_PARAMETER_COUNT:
        raise ValueError(
            f"large tag parameter count must be between 1 and {MAX_LARGE_TAG_PARAMETER_COUNT}"
        )
    canonical = variant_by_id(manifest, "q-type+tag-3")
    expanded = []
    for ordinal, source in enumerate(canonical["queries"], start=1):
        query_id = str(source["query_id"])
        operation = str(source["operation"])
        order = expected_parameter_order(query_id, True, tag_parameter_count)
        query = {
            "ordinal": ordinal,
            "query_id": query_id,
            "operation": operation,
            "sql": expected_sql(query_id, True, tag_parameter_count),
            "parameter_order": order,
            "parameters": expected_parameter_types(order),
        }
        validate_query(
            query,
            query_id=query_id,
            operation=operation,
            ordinal=ordinal,
            q_type_filter=True,
            tag_parameter_count=tag_parameter_count,
        )
        expanded.append(query)
    return expanded


def manifest_tag_safety(
    manifest: Mapping[str, Any],
    large_tag_parameter_count: int,
) -> dict[str, Any]:
    tag_1 = variant_by_id(manifest, "tag-1")
    tag_3 = variant_by_id(manifest, "tag-3")
    combined = variant_by_id(manifest, "q-type+tag-3")
    large = build_large_tag_queries(manifest, large_tag_parameter_count)
    maximum_bind_count = max(len(query["parameter_order"]) for query in large)
    return {
        "exported_tag_1_variant_payload_sha256": base.sha256_json(tag_1),
        "exported_tag_3_variant_payload_sha256": base.sha256_json(tag_3),
        "exported_q_type_plus_tag_3_variant_payload_sha256": base.sha256_json(combined),
        "exported_tag_900_boundary_payload_sha256": base.sha256_json(
            manifest["large_tag_safety"]
        ),
        "large_probe_derivation": (
            "bounded deterministic full-query expansion of the validated Java-exported "
            "q-type+tag-3 family using the exported tag-900 predicate; not production SQL"
        ),
        "large_tag_parameter_count": large_tag_parameter_count,
        "maximum_allowed_large_tag_parameter_count": MAX_LARGE_TAG_PARAMETER_COUNT,
        "legacy_explicit_tag_id_limit_present": False,
        "overflow_above_evidence_bound": "not-a-captured-legacy-rejection",
        "production_limit_strategy_authorized": False,
        "full_query_plan_required": False,
        "large_query_count": len(large),
        "large_query_payload_sha256": base.sha256_json(large),
        "maximum_large_bind_count": maximum_bind_count,
        "contiguous_named_parameters": all(
            query_filter_shape(query) == (True, large_tag_parameter_count)
            for query in large
        ),
        "integer_tag_bind_types": all(
            all(
                query["parameters"][f"tq_{index}"] == "integer"
                for index in range(large_tag_parameter_count)
            )
            for query in large
        ),
        "sql_separators_comments_or_writes_present": False,
        "empty_resolved_tag_short_circuits_before_statistics_sql": True,
    }


def plan_queries(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    access = [dict(query) for query in manifest["queries"][:2]]
    unfiltered = [
        dict(query) for query in variant_by_id(manifest, "unfiltered")["queries"]
    ]
    full_filter = [
        dict(query) for query in variant_by_id(manifest, "q-type+tag-3")["queries"]
    ]
    for query in access:
        query["evidence_variant"] = "access-unfiltered"
    for query in unfiltered:
        query["evidence_variant"] = "unfiltered"
    for query in full_filter:
        query["evidence_variant"] = "q-type+tag-3"
    result = access + unfiltered + full_filter
    for ordinal, query in enumerate(result, start=1):
        query["observation_ordinal"] = ordinal
        query["family_ordinal"] = QUERY_IDS.index(query["query_id"]) + 1
        query["observation_id"] = (
            f"{query['evidence_variant']}::{query['query_id']}"
        )
    expected_order = [*QUERY_IDS[:2], *STATISTICS_QUERY_IDS, *STATISTICS_QUERY_IDS]
    if [query["query_id"] for query in result] != expected_order:
        raise RuntimeError("user-counts plan observation order drifted")
    return result


def parameter_values(tag_parameter_count: int) -> dict[str, Any]:
    values: dict[str, Any] = {
        "bank_id": TARGET_BANK_ID,
        "uid": TARGET_VIEWER_ID,
        "user_id": TARGET_VIEWER_ID,
        "q_type_f": TARGET_Q_TYPE,
    }
    for index in range(tag_parameter_count):
        if index < len(TARGET_TAG_IDS):
            value = TARGET_TAG_IDS[index]
        else:
            value = 90_000_000 + index
        values[f"tq_{index}"] = value
    return values


def positional_sql(
    sql: str,
    occurrence_names: list[str],
) -> str:
    observed = base.NAMED_PARAMETER.findall(sql)
    if observed != occurrence_names:
        raise RuntimeError("named parameter occurrence order drifted before PREPARE")
    position = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal position
        position += 1
        return f"${position}"

    result = base.NAMED_PARAMETER.sub(replace, sql)
    if position != len(occurrence_names) or base.NAMED_PARAMETER.search(result):
        raise RuntimeError("named parameter positional conversion drifted")
    return result


def sql_literal(name: str, value: Any) -> str:
    if name == "q_type_f":
        if value != TARGET_Q_TYPE:
            raise RuntimeError("unexpected q_type evidence value")
        return "'single_choice'"
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"unexpected numeric evidence value for {name}")
    return str(value)


def prepared_statement(
    query: Mapping[str, Any],
    *,
    explain: bool,
) -> tuple[str, dict[str, Any]]:
    query_id = str(query["query_id"])
    q_type_filter, tag_count = query_filter_shape(query)
    operation = str(query["operation"])
    expected_ordinal = int(query.get("ordinal", 0))
    family_ordinal = QUERY_IDS.index(query_id) + 1
    validate_query(
        query,
        query_id=query_id,
        operation=operation,
        ordinal=expected_ordinal,
        q_type_filter=q_type_filter,
        tag_parameter_count=tag_count,
    )
    order = list(query["parameter_order"])
    types = query["parameters"]
    values = parameter_values(tag_count)
    positional = positional_sql(str(query["sql"]), order)
    prepared_name = "phase4b_user_counts_" + re.sub(
        r"[^a-z0-9]+", "_", query_id.removeprefix("personal-bank-user-counts-")
    ).strip("_")
    type_list = ", ".join(types[name] for name in order)
    value_list = ", ".join(sql_literal(name, values[name]) for name in order)
    execution = f"EXECUTE {prepared_name}({value_list});"
    if explain:
        execution = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + execution
    statement = (
        "SET max_parallel_workers_per_gather = 0;\n"
        "SET jit = off;\n"
        "SET work_mem = '64MB';\n"
        f"PREPARE {prepared_name}({type_list}) AS\n{positional.strip()};\n"
        f"{execution}\n"
        f"DEALLOCATE {prepared_name};\n"
    )
    ordered_bindings = [
        {
            "position": index,
            "name": name,
            "postgres_type": types[name],
            "value": values[name],
        }
        for index, name in enumerate(order, start=1)
    ]
    return statement, {
        "mode": "postgresql-prepare-execute",
        "prepared_name": prepared_name,
        "family_ordinal": family_ordinal,
        "session_settings": {
            "max_parallel_workers_per_gather": "0",
            "jit": "off",
            "work_mem": "64MB",
        },
        "runtime_statement_count": 1,
        "bound_parameter_count": len(order),
        "occurrence_names": order,
        "postgres_types_in_order": [types[name] for name in order],
        "ordered_bindings": ordered_bindings,
        "positional_sql_sha256": base.sha256_text(positional),
    }


def literal_sql(query: Mapping[str, Any]) -> str:
    q_type_filter, tag_count = query_filter_shape(query)
    query_id = str(query["query_id"])
    validate_query(
        query,
        query_id=query_id,
        operation=str(query["operation"]),
        ordinal=int(query["ordinal"]),
        q_type_filter=q_type_filter,
        tag_parameter_count=tag_count,
    )
    values = parameter_values(tag_count)
    return base.NAMED_PARAMETER.sub(
        lambda match: sql_literal(match.group(1), values[match.group(1)]),
        str(query["sql"]),
    )


def fixture_paths(root: Path) -> list[Path]:
    return [(root / relative).resolve() for relative in FIXTURE_INPUTS]


def scale_fixture_sql(bank_count: int, question_count: int) -> str:
    return f"""
INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
)
SELECT {GENERATED_USER_OFFSET} + value,
       'phase4b-user-counts-user-' || value,
       'public-test-only-hash', false, 1, true,
       'phase4b-user-counts-user-' || value || '@test.invalid'
FROM generate_series(1, {bank_count}) AS value;

INSERT INTO user_question_banks (id, user_id, name, status)
SELECT {GENERATED_BANK_OFFSET} + value,
       {GENERATED_USER_OFFSET} + value,
       'phase4b-user-counts-bank-' || value,
       1
FROM generate_series(1, {bank_count}) AS value;

INSERT INTO user_bank_questions (
    id, bank_id, user_id, type, content
)
SELECT {GENERATED_QUESTION_OFFSET} + value,
       {TARGET_BANK_ID},
       {TARGET_VIEWER_ID},
       CASE value % 8
           WHEN 0 THEN 'single_choice'
           WHEN 1 THEN 'multi_choice'
           WHEN 2 THEN 'boolean'
           WHEN 3 THEN 'essay'
           WHEN 4 THEN 'fill'
           WHEN 5 THEN 'unexpected_type'
           WHEN 6 THEN ''
           ELSE NULL
       END,
       'phase4b-user-counts-question-' || value
FROM generate_series(1, {question_count}) AS value;

INSERT INTO user_bank_favorites (
    id, user_id, bank_id, question_id
)
SELECT {GENERATED_FAVORITE_OFFSET} + value,
       {TARGET_VIEWER_ID},
       {TARGET_BANK_ID},
       {GENERATED_QUESTION_OFFSET} + value
FROM generate_series(1, {question_count}) AS value
WHERE value % {FAVORITE_INTERVAL} = 0;

INSERT INTO user_bank_mistakes (
    id, user_id, bank_id, question_id, wrong_count
)
SELECT {GENERATED_MISTAKE_OFFSET} + value,
       {TARGET_VIEWER_ID},
       {TARGET_BANK_ID},
       {GENERATED_QUESTION_OFFSET} + value,
       (value % 5) + 1
FROM generate_series(1, {question_count}) AS value
WHERE value % {MISTAKE_INTERVAL} = 0;

VACUUM (ANALYZE) user_question_banks;
VACUUM (ANALYZE) bank_shares;
VACUUM (ANALYZE) bank_share_records;
VACUUM (ANALYZE) user_bank_questions;
VACUUM (ANALYZE) user_bank_favorites;
VACUUM (ANALYZE) user_bank_mistakes;
VACUUM (ANALYZE) user_progress;
VACUUM (ANALYZE) user_question_tag_items;
"""


def copy_rows(
    container: str,
    database: str,
    query: Mapping[str, Any],
) -> list[list[str]]:
    copy_sql = (
        "COPY (\n" + literal_sql(query).strip()
        + "\n) TO STDOUT WITH (FORMAT csv, NULL '<NULL>');\n"
    )
    result = base.run([
        "docker", "exec", "-i", container,
        "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1",
        "-U", "postgres", "-d", database, "-A", "-t",
    ], input_text=copy_sql, check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-6000:]
        raise RuntimeError(f"PostgreSQL COPY failed: {detail}")
    rows = list(csv.reader(io.StringIO(result.stdout))) if result.stdout else []
    if query["query_id"] in TYPE_QUERY_IDS:
        rows = [[""] if row == [] else row for row in rows]
    return rows


def result_summary(
    query_id: str,
    rows: list[list[str]],
    evidence_variant: str,
    question_count: int,
) -> dict[str, Any]:
    full_filter_expected: dict[str, list[list[str]] | None] = {
        QUERY_IDS[0]: None,
        QUERY_IDS[1]: None,
        QUERY_IDS[2]: [["1"]],
        QUERY_IDS[3]: [["1"]],
        QUERY_IDS[4]: [["0"]],
        QUERY_IDS[5]: [[TARGET_Q_TYPE]],
        QUERY_IDS[6]: [[TARGET_Q_TYPE]],
        QUERY_IDS[7]: [],
    }
    raw_all_types = [
        [""], ["boolean"], ["essay"], ["fill"], ["multi_choice"],
        ["single_choice"], ["unexpected_type"], ["<NULL>"],
    ]
    unfiltered_expected: dict[str, list[list[str]]] = {
        QUERY_IDS[2]: [[str(question_count + 9)]],
        QUERY_IDS[3]: [[str(question_count // FAVORITE_INTERVAL + 4)]],
        QUERY_IDS[4]: [[str(question_count // MISTAKE_INTERVAL + 4)]],
        QUERY_IDS[5]: raw_all_types,
        QUERY_IDS[6]: [
            ["essay"], ["fill"], ["multi_choice"], ["single_choice"],
            ["<NULL>"],
        ],
        QUERY_IDS[7]: [
            [""], ["boolean"], ["fill"], ["multi_choice"],
            ["single_choice"], ["<NULL>"],
        ],
    }
    if evidence_variant == "access-unfiltered":
        expected = full_filter_expected[query_id]
    elif evidence_variant == "unfiltered":
        expected = unfiltered_expected[query_id]
    elif evidence_variant == "q-type+tag-3":
        expected = full_filter_expected[query_id]
    else:
        raise RuntimeError(f"unexpected user-counts evidence variant: {evidence_variant}")
    if query_id in QUERY_IDS[:2]:
        if len(rows) != 1:
            raise RuntimeError(f"{query_id} result row count drifted: {len(rows)}")
        minimum_columns = 20 if query_id == QUERY_IDS[0] else 10
        if len(rows[0]) < minimum_columns:
            raise RuntimeError(f"{query_id} projection width drifted")
    elif rows != expected:
        raise RuntimeError(
            f"{evidence_variant} {query_id} result drifted: {rows}"
        )
    canonical = sorted(rows)
    stable_projection = "all returned columns"
    if query_id == QUERY_IDS[0]:
        canonical = [[row[0], row[1], row[6], row[13]] for row in rows]
        if canonical != [["7101", "7001", "f", "1"]]:
            raise RuntimeError("bank access stable semantic projection drifted")
        stable_projection = "id,user_id,is_public,status"
    result: dict[str, Any] = {
        "row_count": len(rows),
        "column_count": len(rows[0]) if rows else (1 if query_id in TYPE_QUERY_IDS else 0),
        "canonical_rows_sha256": base.sha256_json(canonical),
        "cross_version_stable_projection": stable_projection,
        "evidence_variant": evidence_variant,
    }
    if query_id in QUERY_IDS[2:5]:
        result["count_value"] = int(rows[0][0])
    if query_id in TYPE_QUERY_IDS:
        result["raw_type_values"] = [row[0] for row in rows]
    return result


def collect_numeric_fields(value: Any, names: set[str]) -> dict[str, float]:
    return usage_base.collect_numeric_fields(value, names)


def normalize_explain(value: Any) -> Any:
    return usage_base.normalize_explain(value)


def walk_plan(
    node: Mapping[str, Any], depth: int = 0
) -> Iterable[tuple[int, Mapping[str, Any]]]:
    return usage_base.walk_plan(node, depth)


def plan_summary(
    normalized_explain: list[dict[str, Any]],
    buffer_fields: Mapping[str, float],
    timing_fields: Mapping[str, float],
) -> dict[str, Any]:
    return usage_base.plan_summary(normalized_explain, buffer_fields, timing_fields)


def assert_plan_contract(
    query_id: str,
    summary: Mapping[str, Any],
    expected_rows: int,
) -> list[str]:
    if summary["root_actual_rows"] != expected_rows:
        raise RuntimeError(f"{query_id} plan row count drifted")
    if summary["root_actual_loops"] != 1:
        raise RuntimeError(f"{query_id} plan root did not execute exactly once")
    if summary["temp_read_blocks_observed"] != 0 \
            or summary["temp_written_blocks_observed"] != 0:
        raise RuntimeError(f"{query_id} plan used temporary blocks")
    timings = summary["timing_fields_observed_before_normalization"]
    if "Planning Time" not in timings or "Execution Time" not in timings:
        raise RuntimeError(f"{query_id} raw EXPLAIN omitted top-level timing fields")
    if not summary["buffer_fields_observed_before_normalization"]:
        raise RuntimeError(f"{query_id} raw EXPLAIN omitted BUFFERS fields")
    expected_relations = {
        QUERY_IDS[0]: {"user_question_banks": 1},
        QUERY_IDS[1]: {"bank_share_records": 1, "bank_shares": 1},
        QUERY_IDS[2]: {"user_bank_questions": 1},
        QUERY_IDS[3]: {"user_bank_questions": 1, "user_bank_favorites": 1},
        QUERY_IDS[4]: {"user_bank_questions": 1, "user_bank_mistakes": 1},
        QUERY_IDS[5]: {"user_bank_questions": 1},
        QUERY_IDS[6]: {"user_bank_questions": 1, "user_bank_favorites": 1},
        QUERY_IDS[7]: {"user_bank_questions": 1, "user_bank_mistakes": 1},
    }[query_id]
    if summary["relation_scan_occurrences"] != expected_relations:
        raise RuntimeError(f"{query_id} relation scan budget drifted")
    if query_id == QUERY_IDS[0] \
            and "user_question_banks_pkey" not in summary["index_names"]:
        raise RuntimeError("user-counts bank access lost its primary-key lookup")
    return [
        "exact-result-row-count",
        "root-executed-once",
        "required-relations-scanned-once",
        "raw-timing-and-buffer-fields-observed",
        "zero-temp-blocks",
    ]


def psql_json(container: str, database: str, sql: str) -> Any:
    raw = base.execute_psql(container, database, sql)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("user-counts PostgreSQL JSON query could not be parsed") from exc


def data_set_metadata(container: str, database: str) -> dict[str, Any]:
    return psql_json(container, database, """
SELECT json_build_object(
    'users', (SELECT COUNT(*) FROM users),
    'user_question_banks', (SELECT COUNT(*) FROM user_question_banks),
    'bank_shares', (SELECT COUNT(*) FROM bank_shares),
    'bank_share_records', (SELECT COUNT(*) FROM bank_share_records),
    'public_bank_users', (SELECT COUNT(*) FROM public_bank_users),
    'user_bank_questions', (SELECT COUNT(*) FROM user_bank_questions),
    'user_bank_favorites', (SELECT COUNT(*) FROM user_bank_favorites),
    'user_bank_mistakes', (SELECT COUNT(*) FROM user_bank_mistakes),
    'user_progress', (SELECT COUNT(*) FROM user_progress),
    'user_question_tag_items', (SELECT COUNT(*) FROM user_question_tag_items),
    'target_bank_questions', (
        SELECT COUNT(*) FROM user_bank_questions WHERE bank_id = 7101
    ),
    'target_viewer_favorites', (
        SELECT COUNT(*) FROM user_bank_favorites WHERE user_id = 7001
    ),
    'target_viewer_mistakes', (
        SELECT COUNT(*) FROM user_bank_mistakes WHERE user_id = 7001
    )
);
""")


def schema_fingerprint(container: str, database: str) -> str:
    return usage_base.schema_fingerprint(container, database)


def data_fingerprint(container: str, database: str) -> str:
    raw = base.execute_psql(container, database, """
SELECT 'user_question_banks', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(user_id::bigint), 0), COALESCE(SUM(status::bigint), 0)
FROM user_question_banks
UNION ALL
SELECT 'bank_shares', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(owner_id::bigint), 0)
FROM bank_shares
UNION ALL
SELECT 'bank_share_records', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(user_id::bigint), 0)
FROM bank_share_records
UNION ALL
SELECT 'public_bank_users', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(user_id::bigint), 0)
FROM public_bank_users
UNION ALL
SELECT 'user_bank_questions', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(user_id::bigint), 0)
FROM user_bank_questions
UNION ALL
SELECT 'user_bank_favorites', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(question_id::bigint), 0)
FROM user_bank_favorites
UNION ALL
SELECT 'user_bank_mistakes', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(bank_id::bigint), 0), COALESCE(SUM(question_id::bigint), 0)
FROM user_bank_mistakes
UNION ALL
SELECT 'user_progress', COUNT(*), COALESCE(SUM(id::bigint), 0),
       COALESCE(SUM(user_id::bigint), 0), 0
FROM user_progress
UNION ALL
SELECT 'user_question_tag_items', COUNT(*),
       COALESCE(SUM(question_id::bigint), 0),
       COALESCE(SUM(scope_id::bigint), 0), COALESCE(SUM(user_id::bigint), 0)
FROM user_question_tag_items
ORDER BY 1;
""")
    return base.sha256_text(raw)


def transaction_poisoning_probe(
    container: str,
    database: str,
    expected_recovery_count: int,
) -> dict[str, Any]:
    sql = """
\\set VERBOSITY sqlstate
BEGIN;
SELECT missing_user_counts_column FROM user_bank_questions;
SELECT COUNT(*) FROM user_bank_questions;
ROLLBACK;
SELECT COUNT(*) FROM user_bank_questions;
"""
    result = base.run([
        "docker", "exec", "-i", container,
        "psql", "-X", "-q", "-v", "ON_ERROR_STOP=0",
        "-U", "postgres", "-d", database, "-A", "-t",
    ], input_text=sql, check=False)
    sqlstates = re.findall(r"ERROR:\s*([0-9A-Z]{5})", result.stderr)
    stdout_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0:
        raise RuntimeError("user-counts transaction poisoning probe did not recover")
    if sqlstates != ["42703", "25P02"]:
        raise RuntimeError(f"user-counts transaction SQLSTATE drifted: {sqlstates}")
    if not stdout_lines or stdout_lines[-1] != str(expected_recovery_count):
        raise RuntimeError("user-counts rollback recovery result drifted")
    return {
        "initial_failure_sqlstate": "42703",
        "subsequent_statement_sqlstate": "25P02",
        "rollback_recovery_row_count": expected_recovery_count,
        "same_session_transaction": True,
        "rollback_restored_readability": True,
        "stderr_redacted_to_sqlstates": True,
    }


def execute_large_tag_probe(
    container: str,
    database: str,
    query: Mapping[str, Any],
) -> dict[str, Any]:
    statement, binding = prepared_statement(query, explain=False)
    raw = base.execute_psql(container, database, statement)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines or lines[-1] != "1":
        raise RuntimeError(f"large tag prepared execution result drifted: {lines}")
    return {
        "query_id": query["query_id"],
        "operation": query["operation"],
        "result_count": 1,
        "bound_parameter_count": binding["bound_parameter_count"],
        "occurrence_names_sha256": base.sha256_json(binding["occurrence_names"]),
        "postgres_types_in_order_sha256": base.sha256_json(
            binding["postgres_types_in_order"]
        ),
        "positional_sql_sha256": binding["positional_sql_sha256"],
        "prepare_execute_succeeded": True,
    }


def capture_engine(
    image: Mapping[str, str],
    manifest: Mapping[str, Any],
    args: argparse.Namespace,
    root: Path,
) -> dict[str, Any]:
    container = f"ti-phase4b-user-counts-plan-{uuid.uuid4().hex[:12]}"
    password = "public-test-only-password"
    result = base.run([
        "docker", "run", "-d", "--rm", "--network", "none", "--name", container,
        "-e", f"POSTGRES_PASSWORD={password}",
        "-e", f"POSTGRES_DB={DEFAULT_DATABASE}",
        image["image"],
    ], check=False)
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()[-4000:]
        raise RuntimeError(f"cannot start {image['label']}: {detail}")
    try:
        base.wait_for_postgres(
            container, DEFAULT_DATABASE, args.startup_timeout_seconds
        )
        for path in fixture_paths(root):
            base.execute_psql(
                container, DEFAULT_DATABASE, path.read_text(encoding="utf-8")
            )
        scale_sql = scale_fixture_sql(args.bank_count, args.question_count)
        base.execute_psql(container, DEFAULT_DATABASE, scale_sql)
        server_version = base.execute_psql(
            container, DEFAULT_DATABASE, "SHOW server_version;"
        )
        if server_version != image["version"]:
            raise RuntimeError(
                f"{image['label']} server version drifted: {server_version}"
            )
        network_mode = base.run([
            "docker", "inspect", "--format={{.HostConfig.NetworkMode}}", container
        ]).stdout.strip()
        if network_mode != "none":
            raise RuntimeError(f"user-counts evidence network drifted: {network_mode}")
        image_id = base.run([
            "docker", "image", "inspect", image["image"], "--format", "{{.Id}}"
        ]).stdout.strip()

        before_schema = schema_fingerprint(container, DEFAULT_DATABASE)
        before_data = data_fingerprint(container, DEFAULT_DATABASE)
        data_set = data_set_metadata(container, DEFAULT_DATABASE)
        observations = []
        for query in plan_queries(manifest):
            query_id = str(query["query_id"])
            rows = copy_rows(container, DEFAULT_DATABASE, query)
            query_result = result_summary(
                query_id,
                rows,
                str(query["evidence_variant"]),
                args.question_count,
            )
            explain_statement, binding = prepared_statement(query, explain=True)
            raw_explain = base.parse_explain(
                base.execute_psql(container, DEFAULT_DATABASE, explain_statement)
            )
            buffers = collect_numeric_fields(raw_explain, BUFFER_KEYS)
            timings = collect_numeric_fields(raw_explain, TIMING_KEYS)
            normalized_explain = normalize_explain(raw_explain)
            summary = plan_summary(normalized_explain, buffers, timings)
            assertions = assert_plan_contract(
                query_id, summary, query_result["row_count"]
            )
            observations.append({
                "observation_ordinal": query["observation_ordinal"],
                "observation_id": query["observation_id"],
                "family_ordinal": query["family_ordinal"],
                "query_id": query_id,
                "operation": query["operation"],
                "evidence_variant": query["evidence_variant"],
                "sql": query["sql"],
                "sql_sha256": base.sha256_text(query["sql"]),
                "normalized_sql_sha256": base.sha256_text(
                    normalize_sql(query["sql"])
                ),
                "binding": binding,
                "result": query_result,
                "assertions_passed": assertions,
                "plan_summary": summary,
                "normalized_explain_analyze": normalized_explain[0],
            })

        large_queries = build_large_tag_queries(
            manifest, args.large_tag_parameter_count
        )
        large_probe = execute_large_tag_probe(
            container, DEFAULT_DATABASE, large_queries[0]
        )
        poisoning = transaction_poisoning_probe(
            container,
            DEFAULT_DATABASE,
            int(data_set["user_bank_questions"]),
        )
        after_schema = schema_fingerprint(container, DEFAULT_DATABASE)
        after_data = data_fingerprint(container, DEFAULT_DATABASE)
        if before_schema != after_schema or before_data != after_data:
            raise RuntimeError(
                "user-counts plan capture mutated schema, indexes or business rows"
            )
        return {
            "label": image["label"],
            "image": image["image"],
            "image_id": image_id,
            "network": network_mode,
            "server_version": server_version,
            "server_version_num": base.execute_psql(
                container, DEFAULT_DATABASE, "SHOW server_version_num;"
            ),
            "data_set": data_set,
            "schema_fingerprint_before_after_sha256": before_schema,
            "data_fingerprint_before_after_sha256": before_data,
            "schema_index_and_data_fingerprints_unchanged": True,
            "observations": observations,
            "large_tag_prepare_execute_probe": large_probe,
            "transaction_poisoning_and_rollback_recovery": poisoning,
        }
    finally:
        base.run(["docker", "rm", "-f", "-v", container], check=False)


def tool_inputs(root: Path, manifest_path: Path) -> dict[str, Any]:
    paths = {
        "evidence_sql": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUserCountsEvidenceSql.java"
        ),
        "sql_contract_test": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUserCountsEvidenceSqlContractTest.java"
        ),
        "sql_manifest_exporter": (
            "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
            "persistence/PersonalBankUserCountsEvidenceSqlManifestTest.java"
        ),
        "jdbc_compatibility_test": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT.java"
        ),
        "legacy_semantic_golden": (
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json"
        ),
        "base_capture_support": (
            "tools/capture_phase4b_personal_bank_usage_stats_query_plans.py"
        ),
        "capture_tool": (
            "tools/capture_phase4b_personal_bank_user_counts_query_plans.py"
        ),
        "capture_tool_test": (
            "tools/test_capture_phase4b_personal_bank_user_counts_query_plans.py"
        ),
    }
    for index, relative in enumerate(FIXTURE_INPUTS, start=1):
        paths[f"fixture_{index}"] = relative
    inputs: dict[str, Any] = {
        "sql_manifest_path": str(manifest_path.resolve().relative_to(root.resolve())),
        "sql_manifest_sha256": base.sha256_file(manifest_path),
    }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inputs["sql_manifest_payload_sha256"] = base.sha256_json(manifest)
    for key, relative in paths.items():
        path = (root / relative).resolve()
        if not path.is_file() or path.is_symlink() or root.resolve() not in path.parents:
            raise RuntimeError(f"user-counts evidence input is unsafe: {relative}")
        inputs[key] = relative
        inputs[f"{key}_sha256"] = base.sha256_file(path)
    return inputs


def assert_redacted(document: Mapping[str, Any]) -> None:
    serialized = json.dumps(document, ensure_ascii=False, sort_keys=True)
    forbidden_values = (
        "public-test-only-password",
        "/Users/",
        "@test.invalid",
        "ti-phase4b-user-counts-plan-",
    )
    if any(value in serialized for value in forbidden_values):
        raise RuntimeError(
            "user-counts evidence leaked ephemeral or sensitive fixture data"
        )

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                lowered = str(key).lower()
                if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                    raise RuntimeError(
                        f"user-counts evidence contains sensitive key: {key}"
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)


def sequence_occurrence_metadata(manifest: Mapping[str, Any]) -> dict[str, Any]:
    sequences = manifest["statistics_sequences"]
    metadata: dict[str, Any] = {}
    for source, query_ids in sequences.items():
        counts = Counter(query_ids)
        repeated = {
            query_id: {
                "occurrence_count": amount,
                "one_based_positions": [
                    index for index, candidate in enumerate(query_ids, start=1)
                    if candidate == query_id
                ],
                "same_sql_family_reused": True,
            }
            for query_id, amount in sorted(counts.items())
            if amount > 1
        }
        metadata[source] = {
            "runtime_statement_count": 4,
            "query_ids_in_order": query_ids,
            "query_ids_in_order_sha256": base.sha256_json(query_ids),
            "repeated_query_families": repeated,
        }
    return metadata


def capture_document(args: argparse.Namespace) -> dict[str, Any]:
    validate_args(args)
    root = Path(__file__).resolve().parents[1]
    manifest_path = args.sql_manifest.resolve()
    validate_paths(root, args.output, manifest_path)
    export_sql_manifest(root, manifest_path)
    manifest = load_sql_manifest(manifest_path)
    tag_safety = manifest_tag_safety(
        manifest, args.large_tag_parameter_count
    )
    engines = [
        capture_engine(image, manifest, args, root)
        for image in POSTGRES_IMAGES
    ]

    expected_observations = plan_queries(manifest)
    expected_observation_ids = [
        query["observation_id"] for query in expected_observations
    ]
    result_hashes: dict[str, set[str]] = {
        observation_id: set() for observation_id in expected_observation_ids
    }
    for engine in engines:
        for observation in engine["observations"]:
            result_hashes[observation["observation_id"]].add(
                observation["result"]["canonical_rows_sha256"]
            )
    differing_results = {
        key: sorted(values)
        for key, values in result_hashes.items()
        if len(values) != 1
    }
    if differing_results:
        raise RuntimeError(
            "PostgreSQL versions returned different user-counts family results: "
            f"{differing_results}"
        )

    scale_sql = scale_fixture_sql(args.bank_count, args.question_count)
    source_sequences = sequence_occurrence_metadata(manifest)
    document: dict[str, Any] = {
        "contract_id": (
            "ti.phase4b.personal-bank-user-counts-query-plan-evidence"
        ),
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "scope": (
            "test-only preimplementation personal-bank user-counts SQL and plan evidence"
        ),
        "route_migration_status": {
            "route_ids": ["6858f6fa506f", "006913d0d956"],
            "baseline_target_module": "personalbank",
            "reviewed_use_case_owner": "learning",
            "reviewed_http_owner": "learning",
            "status": "pending",
            "production_cutover": False,
            "query_plan_disposition": (
                "baseline SQL observation only; it does not authorize personalbank "
                "or any other module to implement or own the reviewed HTTP use case"
            ),
        },
        "provenance": {
            "legacy_commit": "700006dfdfa063deb4387be572911e782bcea0d9",
            "legacy_sources": {
                "access_check": (
                    "app/modules/user_bank/routes/api_base.py:53:check_bank_access"
                ),
                "statistics_handler": (
                    "app/modules/user_bank/routes/api_quiz.py:776:get_user_counts"
                ),
            },
            "runtime_dependency_on_legacy_source": False,
            "manifest_exported_by_maven_test": True,
            "query_input_kind": (
                "Java test-only preimplementation evidence manifest"
            ),
        },
        "inputs": tool_inputs(root, manifest_path),
        "sql_contract": {
            "manifest": manifest,
            "plan_variants": ["access-unfiltered", "unfiltered", "q-type+tag-3"],
            "observation_count_per_version": 14,
            "unique_query_family_count": 8,
            "observation_ids_in_order": expected_observation_ids,
            "observation_ids_in_order_sha256": base.sha256_json(
                expected_observation_ids
            ),
            "access_query_count": 2,
            "statistics_family_count": 6,
            "statistics_plan_variant_count": 2,
            "statistics_runtime_statement_count_per_nonempty_source": 4,
            "query_family_payload_sha256": base.sha256_json(manifest["queries"]),
            "canonical_variant_payload_sha256": base.sha256_json(
                variant_by_id(manifest, "q-type+tag-3")
            ),
            "q_type_parameter_type_evidence": manifest[
                "q_type_parameter_type_evidence"
            ],
            "prepare_type_scope_conclusion": (
                "the manifest text type is an explicit PostgreSQL PREPARE declaration used "
                "only by this query-plan capture; JdbcClient binding of a Java String was "
                "separately observed as character varying, and cross-scope type identity "
                "or a legacy runtime bind type is not claimed"
            ),
            "source_sequences": source_sequences,
            "duplicate_sequence_conclusion": (
                "favorites reuses favorites-count at positions 1 and 2; mistakes reuses "
                "mistakes-count at positions 1 and 3; plans are captured once per family "
                "and runtime occurrence metadata preserves duplicate execution"
            ),
            "production_source_added": False,
        },
        "dynamic_tag_manifest_safety": tag_safety,
        "data_set": {
            "kind": (
                "public deterministic repository fixtures plus synthetic scale rows"
            ),
            "repository_fixture_load_order": list(FIXTURE_INPUTS),
            "parameters": {
                "generated_bank_count": args.bank_count,
                "generated_question_count": args.question_count,
                "generated_favorite_count": args.question_count // FAVORITE_INTERVAL,
                "generated_mistake_count": args.question_count // MISTAKE_INTERVAL,
                "target_bank_id": TARGET_BANK_ID,
                "target_viewer_id": TARGET_VIEWER_ID,
                "canonical_q_type": TARGET_Q_TYPE,
                "canonical_tag_question_ids": list(TARGET_TAG_IDS),
                "favorite_interval": FAVORITE_INTERVAL,
                "mistake_interval": MISTAKE_INTERVAL,
            },
            "scale_fixture_sql_sha256": base.sha256_text(scale_sql),
            "capture_schema_or_index_added": False,
            "fixture_index_observation": (
                "067 defines only its frozen test schema indexes; the capture adds no "
                "schema or index and fingerprints the complete public schema before/after"
            ),
        },
        "engines": engines,
        "cross_version_contract": {
            "required_versions": [image["version"] for image in POSTGRES_IMAGES],
            "observed_versions": [engine["server_version"] for engine in engines],
            "fourteen_observations_in_order_per_version": all(
                [item["observation_id"] for item in engine["observations"]]
                == expected_observation_ids
                for engine in engines
            ),
            "observation_count_per_version": 14,
            "unique_query_family_count": 8,
            "unfiltered_and_full_filter_statistics_plans_present": all(
                {
                    (item["query_id"], item["evidence_variant"])
                    for item in engine["observations"]
                    if item["query_id"] in STATISTICS_QUERY_IDS
                }
                == {
                    (query_id, variant)
                    for query_id in STATISTICS_QUERY_IDS
                    for variant in ("unfiltered", "q-type+tag-3")
                }
                for engine in engines
            ),
            "canonical_results_equal_across_versions": all(
                len(values) == 1 for values in result_hashes.values()
            ),
            "explicit_prepare_bind_order_and_declared_types_closed": all(
                [entry["name"] for entry in item["binding"]["ordered_bindings"]]
                == item["binding"]["occurrence_names"]
                and [entry["postgres_type"] for entry in item["binding"]["ordered_bindings"]]
                == item["binding"]["postgres_types_in_order"]
                for engine in engines for item in engine["observations"]
            ),
            "explicit_prepare_type_scope": (
                "postgresql-explicit-prepare-declaration-for-query-plan-evidence"
            ),
            "jdbc_client_runtime_type_equivalence_claimed": False,
            "large_tag_prepare_execute_succeeded": all(
                engine["large_tag_prepare_execute_probe"]["prepare_execute_succeeded"]
                for engine in engines
            ),
            "initial_failure_42703_then_25p02_observed": all(
                engine["transaction_poisoning_and_rollback_recovery"]
                ["initial_failure_sqlstate"] == "42703"
                and engine["transaction_poisoning_and_rollback_recovery"]
                ["subsequent_statement_sqlstate"] == "25P02"
                for engine in engines
            ),
            "rollback_recovery_observed": all(
                engine["transaction_poisoning_and_rollback_recovery"]
                ["rollback_restored_readability"]
                for engine in engines
            ),
            "temp_blocks_zero": all(
                item["plan_summary"]["temp_read_blocks_observed"] == 0
                and item["plan_summary"]["temp_written_blocks_observed"] == 0
                for engine in engines for item in engine["observations"]
            ),
            "schema_index_and_data_fingerprints_unchanged": all(
                engine["schema_index_and_data_fingerprints_unchanged"]
                for engine in engines
            ),
            "passed": True,
        },
        "transaction_failure_boundary": {
            "manifest_declared_sqlstate": manifest[
                "postgres_transaction_poisoning_sqlstate"
            ],
            "manifest_jdbc_compatibility_reference": manifest[
                "jdbc_compatibility_evidence"
            ],
            "legacy_semantic_golden_reference": {
                "path": (
                    "docs/refactor/phase4b/"
                    "golden-personal-bank-user-counts-reads.json"
                ),
                "json_pointer": "/failure_and_transaction_contract",
                "conclusion": (
                    "the golden simulation marked direct PG16/PG18 transaction-boundary "
                    "proof as a remaining gate"
                ),
            },
            "jdbc_test_reference": {
                "path": (
                    "server/src/test/java/io/saksk/ti/integration/"
                    "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT.java"
                ),
                "method": "assertTransactionPoisoningAndRollbackRecovery",
                "conclusion": (
                    "both container tests require 42703, then 25P02, then successful "
                    "read after rollback"
                ),
            },
            "query_plan_capture_independently_repeated_on_both_versions": True,
            "conclusion": (
                "catching an optional statistics statement inside one PostgreSQL "
                "transaction does not make later statements usable; rollback or an "
                "independent clean transaction boundary is required"
            ),
        },
        "normalization": {
            "removed": [
                "planning and execution timing values",
                "per-node actual timing values",
                "cache-dependent buffer block counts except TEMP zero assertions",
                "planner estimates and costs",
                "runtime memory, hash and worker counters",
                "container ID and ephemeral container name",
            ],
            "retained": [
                "exact result counts and canonical result hashes",
                "plan root and node types",
                "actual rows and loops",
                "relation and index names",
                "redacted hashes of planner expressions",
                "names of raw timing and BUFFERS fields observed before normalization",
                "TEMP read and write block zero values",
            ],
            "reason": (
                "volatile timing, cost and cache counters are removed so repeated dual-version "
                "capture is byte-identical while structural and exact-result evidence remains"
            ),
        },
        "claim_limits": {
            "observational_evidence_only": True,
            "production_sla_claimed": False,
            "index_change_authorized": False,
            "schema_change_authorized": False,
            "http_parity_claimed": False,
            "production_cutover_claimed": False,
            "large_tag_900_is_evidence_render_bound_not_legacy_limit": True,
            "production_tag_limit_strategy_authorized": False,
            "note": (
                "The scale and large-tag probes characterize frozen evidence only and do not "
                "authorize a schema, index, tag limit, HTTP, or production change."
            ),
        },
        "reproduction": {
            "working_directory": "repository root containing Ti-Java",
            "command": (
                "python3 Ti-Java/tools/"
                "capture_phase4b_personal_bank_user_counts_query_plans.py"
            ),
            "prerequisites": "Docker and the repository Maven verification image",
            "isolation": (
                "ephemeral network-disabled containers removed on all exits"
            ),
        },
    }
    assert_redacted(document)
    document["document_payload_sha256"] = base.document_payload_sha256(document)
    return document


def write_json_atomic(path: Path, document: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(base.render_document(document), encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    args = parse_args()
    document = capture_document(args)
    write_json_atomic(args.output, document)
    print(
        "captured personal-bank user-counts PG16/PG18 plans "
        f"manifest_sha256={document['inputs']['sql_manifest_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
