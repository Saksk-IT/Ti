#!/usr/bin/env python3
"""Capture fixed-commit goldens for the dual-alias personal-bank user counts read."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import contextmanager
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterator, Optional
from urllib.parse import urlencode


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
CALLERS = TI_JAVA / "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
CAPTURE_TEST = TOOLS_DIR / "test_capture_phase4b_personal_bank_user_counts_goldens.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_share_list_goldens as shared  # noqa: E402


pinned_source = shared.pinned_source
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
FIXED_REQUEST_ID = "phase4b-personal-bank-user-counts-golden-request"
FIXED_NOW_BJ = datetime(2026, 7, 17, 12, 0, 0)
ROUTES = {
    "api-alias": {
        "route_id": "6858f6fa506f",
        "path_template": "/api/user/banks/api/{bank_id}/user-counts",
        "route_template": "/api/user/banks/api/<int:bank_id>/user-counts",
        "legacy_handler": "user_bank_api_root.user_bank_api.get_user_counts",
        "registration_kind": "blueprint_compatibility_alias",
    },
    "web-alias": {
        "route_id": "006913d0d956",
        "path_template": "/user/banks/api/{bank_id}/user-counts",
        "route_template": "/user/banks/api/<int:bank_id>/user-counts",
        "legacy_handler": "user_bank.user_bank_api.get_user_counts",
        "registration_kind": "blueprint_decorator",
    },
}
KEY_SOURCE_FILES = (
    "requirements.txt",
    "app/__init__.py",
    "app/core/errors.py",
    "app/core/extensions.py",
    "app/core/utils/decorators.py",
    "app/core/utils/jwt_utils.py",
    "app/core/utils/portable_question_format.py",
    "app/core/utils/time_utils.py",
    "app/core/utils/user_question_tags.py",
    "app/models/system.py",
    "app/models/user.py",
    "app/models/user_bank.py",
    "app/modules/user_bank/__init__.py",
    "app/modules/user_bank/routes/api.py",
    "app/modules/user_bank/routes/api_base.py",
    "app/modules/user_bank/routes/api_quiz.py",
    "app/modules/user_bank/routes/api_tags.py",
    "tests/test_user_bank_quiz_record.py",
)
ACTORS = {
    "owner": 99451,
    "other": 99452,
    "shared_future": 99453,
    "shared_null": 99454,
    "shared_equal": 99455,
    "shared_expired": 99456,
    "shared_inactive": 99457,
    "shared_malformed": 99458,
    "shared_multi": 99459,
    "shared_mismatch": 99460,
    "shared_empty": 99461,
    "shared_aware": 99462,
    "revoked": 99463,
}
BANKS = {
    "owner_active": 99551,
    "inactive": 99552,
    "null_status": 99553,
    "status_two": 99554,
    "public_other": 99555,
    "private_other": 99556,
    "empty": 99557,
    "missing": 99999,
}
SHARES = {
    "future": 99651,
    "null_expiry": 99652,
    "equal_now": 99653,
    "expired": 99654,
    "inactive": 99655,
    "malformed": 99656,
    "multi_expired": 99657,
    "multi_future": 99658,
    "mismatched_bank": 99659,
    "empty_expiry": 99660,
    "aware_expiry": 99661,
}
RECORDS = {
    "future": 99671,
    "null_expiry": 99672,
    "equal_now": 99673,
    "expired": 99674,
    "inactive": 99675,
    "malformed": 99676,
    "multi_expired": 99677,
    "multi_future": 99678,
    "mismatched_bank": 99679,
    "empty_expiry": 99680,
    "aware_expiry": 99681,
}
QUESTIONS = {
    "single_a": 99701,
    "multi": 99702,
    "boolean": 99703,
    "fill": 99704,
    "essay": 99705,
    "unknown": 99706,
    "single_alias": 99707,
    "empty_type": 99708,
    "single_b": 99709,
}
BUSINESS_TABLES = (
    "user_question_banks",
    "bank_shares",
    "bank_share_records",
    "user_bank_questions",
    "user_bank_favorites",
    "user_bank_mistakes",
    "user_question_tag_items",
    "user_progress",
)
STATS_CLASSIFICATIONS = frozenset({
    "personal_bank_user_counts_total_all",
    "personal_bank_user_counts_favorites_count",
    "personal_bank_user_counts_mistakes_count",
    "personal_bank_user_counts_types_all",
    "personal_bank_user_counts_types_favorites",
    "personal_bank_user_counts_types_mistakes",
})


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    route: str = "api-alias"
    bank: str = "owner_active"
    session_actor: Optional[str] = "owner"
    bearer_actor: Optional[str] = None
    invalid_bearer: bool = False
    accept: str = "*/*"
    query: tuple[tuple[str, str], ...] = ()
    tag_fixture: str = "none"
    fail_stage: Optional[str] = None
    fail_occurrence: int = 1
    poison_after_failure: bool = False
    expected_status: int = 200


def build_case_specs() -> tuple[CaseSpec, ...]:
    specs: list[CaseSpec] = []
    for route in ROUTES:
        api = route == "api-alias"
        specs.extend((
            CaseSpec(f"auth-session-owner-{route}", route=route),
            CaseSpec(
                f"auth-bearer-owner-{route}", route=route,
                session_actor=None, bearer_actor="owner",
                expected_status=200 if api else 302,
            ),
            CaseSpec(
                f"auth-bearer-precedes-session-{route}", route=route,
                session_actor="owner", bearer_actor="other",
                expected_status=403 if api else 302,
            ),
            CaseSpec(
                f"auth-invalid-bearer-falls-back-session-{route}", route=route,
                invalid_bearer=True,
            ),
            CaseSpec(
                f"auth-state-invalid-bearer-does-not-fallback-session-{route}",
                route=route, session_actor="owner", bearer_actor="revoked",
                expected_status=401 if api else 302,
            ),
            CaseSpec(
                f"auth-anonymous-{route}", route=route, session_actor=None,
                expected_status=401 if api else 302,
            ),
            CaseSpec(f"data-empty-{route}", route=route, bank="empty"),
            CaseSpec(
                f"access-status-zero-{route}", route=route, bank="inactive",
                expected_status=403,
            ),
            CaseSpec(
                f"access-missing-{route}", route=route, bank="missing",
                expected_status=403,
            ),
            CaseSpec(
                f"access-public-other-{route}", route=route,
                bank="public_other", session_actor="other",
            ),
            CaseSpec(
                f"filter-source-favorites-{route}", route=route,
                query=(("source", "favorites"),),
            ),
            CaseSpec(
                f"tag-normalized-sa2-empty-{route}", route=route,
                query=(("tag", "重点"),), tag_fixture="normalized",
            ),
            CaseSpec(
                f"fault-total-default-{route}", route=route,
                fail_stage="personal_bank_user_counts_total_all",
                expected_status=500,
            ),
            CaseSpec(
                f"fault-total-json-{route}", route=route,
                accept="application/json, text/plain;q=0.5",
                fail_stage="personal_bank_user_counts_total_all",
                expected_status=500,
            ),
        ))
    specs.extend((
        CaseSpec("access-status-null-owner", bank="null_status"),
        CaseSpec("access-status-two-owner", bank="status_two"),
        CaseSpec(
            "access-private-other-forbidden", bank="private_other",
            session_actor="owner", expected_status=403,
        ),
        CaseSpec("access-shared-future", session_actor="shared_future"),
        CaseSpec("access-shared-null-expiry", session_actor="shared_null"),
        CaseSpec(
            "access-shared-equal-now-forbidden", session_actor="shared_equal",
            expected_status=403,
        ),
        CaseSpec(
            "access-shared-expired-forbidden", session_actor="shared_expired",
            expected_status=403,
        ),
        CaseSpec(
            "access-shared-inactive-forbidden", session_actor="shared_inactive",
            expected_status=403,
        ),
        CaseSpec(
            "access-shared-malformed-expiry-value-error",
            session_actor="shared_malformed", accept="application/json",
            expected_status=400,
        ),
        CaseSpec(
            "access-shared-aware-expiry-type-error",
            session_actor="shared_aware", accept="application/json",
            expected_status=500,
        ),
        CaseSpec("access-shared-empty-expiry", session_actor="shared_empty"),
        CaseSpec(
            "access-shared-fetchone-first-row", session_actor="shared_multi",
            expected_status=403,
        ),
        CaseSpec("access-shared-cross-bank-record", session_actor="shared_mismatch"),
        CaseSpec(
            "filter-q-type-choice", query=(("q_type", " 选择题 "),),
        ),
        CaseSpec("filter-q-type-all-uppercase", query=(("q_type", "ALL"),)),
        CaseSpec("filter-q-type-unknown-maps-essay", query=(("q_type", "mystery"),)),
        CaseSpec("filter-source-mistakes", query=(("source", "mistakes"),)),
        CaseSpec("filter-source-case-sensitive-fallback", query=(("source", "Favorites"),)),
        CaseSpec(
            "filter-q-type-duplicate-first-wins",
            query=(("q_type", "选择题"), ("q_type", "简答题")),
        ),
        CaseSpec(
            "filter-source-duplicate-first-wins",
            query=(("source", "favorites"), ("source", "mistakes")),
        ),
        CaseSpec("tag-all-bypasses-store", query=(("tag", "all"),)),
        CaseSpec(
            "filter-tag-duplicate-first-all-wins",
            query=(("tag", "all"), ("tag", "重点")),
            tag_fixture="normalized",
        ),
        CaseSpec(
            "tag-case-sensitive-all-enters-store", query=(("tag", "All"),),
            tag_fixture="normalized",
        ),
        CaseSpec(
            "tag-legacy-migration-sa2-empty", query=(("tag", "旧标签"),),
            tag_fixture="legacy",
        ),
        CaseSpec(
            "fault-favorites-sqlite-continues",
            fail_stage="personal_bank_user_counts_favorites_count",
        ),
        CaseSpec(
            "fault-favorites-postgresql-poison-simulation",
            fail_stage="personal_bank_user_counts_favorites_count",
            poison_after_failure=True,
        ),
        CaseSpec(
            "fault-mistakes-sqlite-continues",
            fail_stage="personal_bank_user_counts_mistakes_count",
        ),
        CaseSpec(
            "fault-mistakes-postgresql-poison-simulation",
            fail_stage="personal_bank_user_counts_mistakes_count",
            poison_after_failure=True,
        ),
        CaseSpec(
            "fault-types-degrades",
            fail_stage="personal_bank_user_counts_types_all",
        ),
        CaseSpec(
            "fault-source-favorites-second-count-postgresql-poison-simulation",
            query=(("source", "favorites"),),
            fail_stage="personal_bank_user_counts_favorites_count",
            fail_occurrence=2,
            poison_after_failure=True,
        ),
        CaseSpec(
            "fault-share-access-hard-failure", session_actor="shared_future",
            fail_stage="personal_bank_user_counts_share_access_probe",
            accept="application/json", expected_status=500,
        ),
    ))
    return tuple(specs)


CASE_SPECS = build_case_specs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


canonical_json = shared.canonical_json
sha256_json = shared.sha256_json
document_payload_sha256 = shared.document_payload_sha256
render_document = shared.render_document
normalized_value = shared.normalized_value
normalized_sql = shared.normalized_sql
is_select_statement = shared.is_select_statement
is_dml_statement = shared.is_dml_statement
is_ddl_statement = shared.is_ddl_statement
reads_table = shared.reads_table
is_table_dml = shared.is_table_dml
is_user_last_active_dml = shared.is_user_last_active_dml
reset_limiters = shared.reset_limiters
normalized_response = shared.normalized_response
capture_environment = shared.capture_environment


def bind_count(parameters: Any) -> int:
    if isinstance(parameters, Mapping):
        return len(parameters)
    if isinstance(parameters, (list, tuple)):
        return len(parameters)
    return 0 if parameters is None else 1


def classify_sql(statement: Any) -> str:
    sql = normalized_sql(statement)
    if (
        sql.startswith("SELECT * FROM USER_QUESTION_BANKS")
        and "WHERE ID =" in sql and "JOIN" not in sql
    ):
        return "personal_bank_user_counts_bank_access_probe"
    if (
        sql.startswith("SELECT BSR.*, BS.PERMISSION, BS.IS_ACTIVE, BS.EXPIRES_AT")
        and "FROM BANK_SHARE_RECORDS BSR" in sql
        and "JOIN BANK_SHARES BS ON BSR.SHARE_ID = BS.ID" in sql
    ):
        return "personal_bank_user_counts_share_access_probe"
    if sql.startswith("SELECT COUNT(*) AS CNT FROM USER_BANK_QUESTIONS Q"):
        if "JOIN USER_BANK_FAVORITES F" in sql:
            return "personal_bank_user_counts_favorites_count"
        if "JOIN USER_BANK_MISTAKES M" in sql:
            return "personal_bank_user_counts_mistakes_count"
        return "personal_bank_user_counts_total_all"
    if sql.startswith("SELECT DISTINCT Q.TYPE AS P_TYPE FROM USER_BANK_QUESTIONS Q"):
        if "JOIN USER_BANK_FAVORITES F" in sql:
            return "personal_bank_user_counts_types_favorites"
        if "JOIN USER_BANK_MISTAKES M" in sql:
            return "personal_bank_user_counts_types_mistakes"
        return "personal_bank_user_counts_types_all"
    if (
        sql.startswith("SELECT DATA FROM USER_PROGRESS")
        and "WHERE USER_ID =" in sql and "P_KEY =" in sql
    ):
        return "personal_bank_user_counts_legacy_tag_store_select"
    if is_user_last_active_dml(statement):
        return "user_last_active_dml"
    if is_ddl_statement(statement) and "USER_QUESTION_TAG_ITEMS" in sql:
        return "personal_bank_user_counts_tag_schema_ddl"
    if any(is_table_dml(statement, table) for table in BUSINESS_TABLES):
        return "personal_bank_user_counts_business_dml"
    if reads_table(statement, "users"):
        return "users_select"
    if is_select_statement(statement):
        return "select"
    if is_dml_statement(statement):
        return "dml"
    if is_ddl_statement(statement):
        return "ddl"
    return "other"


def classify_raw_connection_sql(statement: str) -> str:
    sql = normalized_sql(statement)
    if sql.startswith("SELECT 1 FROM USER_QUESTION_TAG_ITEMS"):
        return "raw_sa2_new_tag_presence_probe"
    if sql.startswith("SELECT QUESTION_ID, TAG FROM USER_QUESTION_TAG_ITEMS"):
        return "raw_sa2_new_tag_rows_select"
    if sql.startswith("DELETE FROM USER_QUESTION_TAG_ITEMS"):
        return "raw_sa2_legacy_tag_migration_delete"
    if sql.startswith("INSERT OR IGNORE INTO USER_QUESTION_TAG_ITEMS"):
        return "raw_sa2_legacy_tag_migration_insert"
    return "raw_sa2_connection_execute"


@contextmanager
def sql_probe(engine: Any, spec: CaseSpec) -> Iterator[dict[str, Any]]:
    from sqlalchemy import event
    from sqlalchemy.engine import Connection

    ledger: dict[str, Any] = {
        "statements": [],
        "raw_connection_execute_attempts": [],
        "select_attempts": 0,
        "dml_attempts": 0,
        "ddl_attempts": 0,
        "other_attempts": 0,
        "classification_attempts": {},
        "classification_bind_counts": {},
        "business_table_dml_attempts": {table: 0 for table in BUSINESS_TABLES},
        "user_last_active_dml_attempts": 0,
        "fault_events": [],
        "postgresql_poison_simulation": bool(spec.poison_after_failure),
    }
    stage_occurrences: dict[str, int] = {}
    poisoned = False

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: Any,
        parameters: Any,
        _context: Any,
        executemany: Any,
    ) -> None:
        nonlocal poisoned
        classification = classify_sql(statement)
        select = is_select_statement(statement)
        dml = is_dml_statement(statement)
        ddl = is_ddl_statement(statement)
        stage_occurrences[classification] = stage_occurrences.get(classification, 0) + 1
        ledger["classification_attempts"][classification] = (
            ledger["classification_attempts"].get(classification, 0) + 1
        )
        ledger["classification_bind_counts"][classification] = (
            ledger["classification_bind_counts"].get(classification, 0)
            + bind_count(parameters)
        )
        ledger["statements"].append({
            "sql": normalized_sql(statement),
            "parameters": normalized_value(parameters),
            "executemany": bool(executemany),
            "classification": classification,
            "occurrence": stage_occurrences[classification],
        })
        ledger["select_attempts"] += int(select)
        ledger["dml_attempts"] += int(dml)
        ledger["ddl_attempts"] += int(ddl)
        ledger["other_attempts"] += int(not select and not dml and not ddl)
        ledger["user_last_active_dml_attempts"] += int(
            classification == "user_last_active_dml"
        )
        for table in BUSINESS_TABLES:
            ledger["business_table_dml_attempts"][table] += int(
                is_table_dml(statement, table)
            )

        if poisoned and classification in STATS_CLASSIFICATIONS:
            ledger["fault_events"].append({
                "classification": classification,
                "occurrence": stage_occurrences[classification],
                "kind": "synthetic_postgresql_current_transaction_is_aborted",
            })
            raise RuntimeError("synthetic PostgreSQL current transaction is aborted")
        if (
            spec.fail_stage == classification
            and stage_occurrences[classification] == spec.fail_occurrence
        ):
            ledger["fault_events"].append({
                "classification": classification,
                "occurrence": stage_occurrences[classification],
                "kind": "synthetic_targeted_failure",
            })
            poisoned = bool(spec.poison_after_failure)
            raise RuntimeError(f"synthetic user-counts failure at {classification}")

    original_connection_execute = Connection.execute

    def instrumented_connection_execute(
        connection: Any,
        statement: Any,
        *multiparams: Any,
        **params: Any,
    ) -> Any:
        if isinstance(statement, str):
            item: dict[str, Any] = {
                "sql": normalized_sql(statement),
                "classification": classify_raw_connection_sql(statement),
                "positional_argument_count": len(multiparams),
                "keyword_argument_names": sorted(params),
            }
            ledger["raw_connection_execute_attempts"].append(item)
            try:
                return original_connection_execute(
                    connection, statement, *multiparams, **params
                )
            except Exception as error:
                item["exception_type"] = type(error).__name__
                item["failed_before_cursor_execution"] = True
                raise
        return original_connection_execute(connection, statement, *multiparams, **params)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    Connection.execute = instrumented_connection_execute
    try:
        yield ledger
    finally:
        Connection.execute = original_connection_execute
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        ledger["statement_count"] = len(ledger["statements"])
        ledger["classified_attempt_count"] = (
            ledger["select_attempts"] + ledger["dml_attempts"]
            + ledger["ddl_attempts"] + ledger["other_attempts"]
        )
        ledger["business_table_dml_attempt_count"] = sum(
            ledger["business_table_dml_attempts"].values()
        )
        ledger["personal_bank_query_sequence"] = [
            item["classification"] for item in ledger["statements"]
            if item["classification"].startswith("personal_bank_user_counts_")
            and item["classification"] not in {
                "personal_bank_user_counts_tag_schema_ddl",
                "personal_bank_user_counts_business_dml",
            }
        ]
        ledger["statements_sha256"] = sha256_json(ledger["statements"])
        ledger["raw_connection_execute_attempts_sha256"] = sha256_json(
            ledger["raw_connection_execute_attempts"]
        )


def table_fingerprint(db: Any, table: str) -> dict[str, Any]:
    from sqlalchemy import inspect, text

    columns = [column["name"] for column in inspect(db.engine).get_columns(table)]
    primary_key = inspect(db.engine).get_pk_constraint(table).get("constrained_columns") or []
    ordering = primary_key or columns
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY {', '.join(ordering)}"
    )).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "columns": columns,
        "column_count": len(columns),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def user_identity_fingerprint(db: Any) -> dict[str, Any]:
    from sqlalchemy import text

    columns = (
        "id", "username", "is_admin", "is_subject_admin",
        "is_notification_admin", "is_locked", "session_version",
    )
    binds = ", ".join(f":{actor}" for actor in ACTORS)
    rows = db.session.execute(text(
        f"SELECT {', '.join(columns)} FROM users WHERE id IN ({binds}) ORDER BY id"
    ), ACTORS).fetchall()
    normalized = [[normalized_value(value) for value in row] for row in rows]
    return {
        "columns": list(columns),
        "column_count": len(columns),
        "row_count": len(normalized),
        "rows_sha256": sha256_json(normalized),
    }


def user_activity_snapshot(db: Any) -> tuple[dict[int, Any], list[dict[str, Any]]]:
    from sqlalchemy import text

    binds = ", ".join(f":{actor}" for actor in ACTORS)
    rows = db.session.execute(text(
        f"SELECT id, last_active FROM users WHERE id IN ({binds}) ORDER BY id"
    ), ACTORS).fetchall()
    raw = {int(row[0]): row[1] for row in rows}
    recorded = [
        {
            "user_id": user_id,
            "last_active": None if value is None else "<database-current-timestamp>",
        }
        for user_id, value in sorted(raw.items())
    ]
    return raw, recorded


def matrix_attestation() -> dict[str, Any]:
    payload = MATRIX.read_bytes()
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
    route_ids = {route["route_id"] for route in ROUTES.values()}
    selected = [row for row in rows if row["route_id"] in route_ids]
    if len(selected) != 2:
        raise AssertionError("personal-bank user-count routes are missing or duplicated")
    return {
        "path": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "selected_rows_sha256": sha256_json(selected),
        "selected_rows": selected,
        "caller_inventory_complete": False,
        "caller_authority": "personal-bank-user-counts-callers.json",
    }


def key_source_attestation(
    archived: Any,
    legacy_root: Path,
) -> dict[str, dict[str, Any]]:
    object_format = archived.attestation["git_object_format"]
    result: dict[str, dict[str, Any]] = {}
    for path in KEY_SOURCE_FILES:
        archived_path = archived.root / path
        if archived_path.is_file():
            payload = archived_path.read_bytes()
            transport = "verified complete app/ archive"
        else:
            payload = pinned_source._run_read_only_git(
                legacy_root,
                "show",
                f"{LEGACY_COMMIT}:{path}",
            )
            transport = "git show from verified fixed commit"
        result[path] = {
            "git_blob": pinned_source._git_blob_id(payload, object_format),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "transport": transport,
        }
    return result


def caller_evidence_reference() -> dict[str, Any]:
    relative_path = "docs/refactor/phase4b/personal-bank-user-counts-callers.json"
    if not CALLERS.is_file():
        return {
            "path": relative_path,
            "present": False,
            "caller_attestation_complete": False,
            "state": "awaiting_parallel_caller_capture",
        }
    payload = CALLERS.read_bytes()
    document = json.loads(payload.decode("utf-8"))
    route_ids = {route["route_id"] for route in document.get("routes", [])}
    if route_ids != {route["route_id"] for route in ROUTES.values()}:
        raise AssertionError("user-count caller evidence route set drifted")
    closure = document.get("closure", {})
    complete = bool(closure.get("caller_attestation_complete"))
    if not complete:
        raise AssertionError("user-count caller evidence exists but is not closed")
    return {
        "path": relative_path,
        "present": True,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "attestation_sha256": document.get("attestation_sha256"),
        "document_payload_sha256": document.get("document_payload_sha256"),
        "caller_attestation_complete": True,
    }


def tool_provenance() -> dict[str, Any]:
    capture_tool = Path(__file__).resolve()
    if not CAPTURE_TEST.is_file():
        raise AssertionError(f"user-count golden test missing: {CAPTURE_TEST}")
    return {
        "capture_tool": {
            "path": "tools/capture_phase4b_personal_bank_user_counts_goldens.py",
            "sha256": hashlib.sha256(capture_tool.read_bytes()).hexdigest(),
        },
        "capture_test": {
            "path": "tools/test_capture_phase4b_personal_bank_user_counts_goldens.py",
            "sha256": hashlib.sha256(CAPTURE_TEST.read_bytes()).hexdigest(),
        },
        "runtime_versions": {
            "sqlalchemy": metadata.version("SQLAlchemy"),
            "flask_sqlalchemy": metadata.version("Flask-SQLAlchemy"),
        },
        "execution_model": (
            "complete app/ tree archived from the immutable commit, isolated import, "
            "temporary SQLite, synthetic actors and a fixed naive Beijing clock"
        ),
    }


def bank_rows() -> list[dict[str, Any]]:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    values = (
        ("owner_active", "owner", False, 1),
        ("inactive", "owner", True, 0),
        ("null_status", "owner", False, None),
        ("status_two", "owner", False, 2),
        ("public_other", "other", True, 1),
        ("private_other", "other", False, 1),
        ("empty", "owner", False, 1),
    )
    return [
        {
            "id": BANKS[bank],
            "user_id": ACTORS[owner],
            "name": f"user counts {bank} 高数・α／🧪",
            "is_public": public,
            "status": status,
            "question_count": 0 if bank == "empty" else len(QUESTIONS),
            "created_at": fixed,
            "updated_at": fixed,
        }
        for bank, owner, public, status in values
    ]


def share_rows() -> list[dict[str, Any]]:
    values = (
        ("future", "owner_active", "read", "2026-07-17 13:00:00", True),
        ("null_expiry", "owner_active", "copy", None, True),
        ("equal_now", "owner_active", None, "2026-07-17 12:00:00", True),
        ("expired", "owner_active", "read", "2026-07-17 11:59:59", True),
        ("inactive", "owner_active", "read", "2027-01-01 00:00:00", False),
        ("malformed", "owner_active", "unexpected", "malformed-expiry", True),
        ("multi_expired", "owner_active", "read", "2026-07-17 11:00:00", True),
        ("multi_future", "owner_active", "copy", "2026-07-17 14:00:00", True),
        ("mismatched_bank", "private_other", None, None, True),
        ("empty_expiry", "owner_active", "read", "", True),
        ("aware_expiry", "owner_active", "read", "2026-07-17T13:00:00+08:00", True),
    )
    return [
        {
            "id": SHARES[key],
            "bank_id": BANKS[bank],
            "owner_id": ACTORS["owner"],
            "share_code": f"C{index:05d}",
            "share_token": f"user-count-token-{index:04d}",
            "permission": permission,
            "expires_at": expires_at,
            "max_uses": None,
            "current_uses": index,
            "is_active": active,
            "created_at": datetime(2026, 7, 17, 8, index, 0),
        }
        for index, (key, bank, permission, expires_at, active)
        in enumerate(values, start=1)
    ]


def record_rows() -> list[dict[str, Any]]:
    values = (
        ("future", "future", "shared_future"),
        ("null_expiry", "null_expiry", "shared_null"),
        ("equal_now", "equal_now", "shared_equal"),
        ("expired", "expired", "shared_expired"),
        ("inactive", "inactive", "shared_inactive"),
        ("malformed", "malformed", "shared_malformed"),
        ("multi_expired", "multi_expired", "shared_multi"),
        ("multi_future", "multi_future", "shared_multi"),
        ("mismatched_bank", "mismatched_bank", "shared_mismatch"),
        ("empty_expiry", "empty_expiry", "shared_empty"),
        ("aware_expiry", "aware_expiry", "shared_aware"),
    )
    return [
        {
            "id": RECORDS[record],
            "share_id": SHARES[share],
            "bank_id": BANKS["owner_active"],
            "user_id": ACTORS[actor],
            "status": 1,
            "last_access_at": datetime(2026, 7, 17, 9, index, 0),
            "access_count": index,
            "created_at": datetime(2026, 7, 17, 8, index, 0),
        }
        for index, (record, share, actor) in enumerate(values, start=1)
    ]


def question_rows() -> list[dict[str, Any]]:
    types = (
        ("single_a", "single_choice"),
        ("multi", "multi_choice"),
        ("boolean", "boolean"),
        ("fill", "fill"),
        ("essay", "essay"),
        ("unknown", "unknown_type"),
        ("single_alias", "single"),
        ("empty_type", ""),
        ("single_b", "single_choice"),
    )
    return [
        {
            "id": QUESTIONS[key],
            "bank_id": BANKS["owner_active"],
            "user_id": ACTORS["owner"],
            "type": q_type,
            "content": f"counts question {index}",
            "options": "[]",
            "answer": "[]",
            "analysis": None,
            "tags": "[]",
            "difficulty": 1,
            "source_type": "custom",
            "sort_order": index,
            "created_at": datetime(2026, 7, 17, 8, index, 0),
            "updated_at": datetime(2026, 7, 17, 8, index, 0),
        }
        for index, (key, q_type) in enumerate(types, start=1)
    ]


def favorite_rows() -> list[dict[str, Any]]:
    assignments = (
        (1, "owner", "single_a", "owner_active"),
        (2, "owner", "boolean", "owner_active"),
        (3, "owner", "unknown", "owner_active"),
        (4, "owner", "single_alias", "owner_active"),
        # The legacy query ignores f.bank_id and counts by the joined question bank.
        (5, "owner", "single_b", "private_other"),
        (6, "other", "multi", "owner_active"),
    )
    return [
        {
            "id": 99800 + row_id,
            "user_id": ACTORS[actor],
            "bank_id": BANKS[bank],
            "question_id": QUESTIONS[question],
            "created_at": datetime(2026, 7, 17, 10, row_id, 0),
        }
        for row_id, actor, question, bank in assignments
    ]


def mistake_rows() -> list[dict[str, Any]]:
    assignments = (
        (1, "multi"),
        (2, "boolean"),
        (3, "essay"),
    )
    return [
        {
            "id": 99900 + row_id,
            "user_id": ACTORS["owner"],
            "bank_id": BANKS["owner_active"],
            "question_id": QUESTIONS[question],
            "wrong_count": row_id,
            "created_at": datetime(2026, 7, 17, 11, row_id, 0),
            "updated_at": datetime(2026, 7, 17, 11, row_id, 0),
        }
        for row_id, question in assignments
    ]


def _insert_rows(db: Any, table: str, rows: list[dict[str, Any]]) -> None:
    from sqlalchemy import text

    if not rows:
        return
    columns = tuple(rows[0])
    db.session.execute(text(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
        f"({', '.join(':' + column for column in columns)})"
    ), rows)


def seed_static_actors(db: Any, User: Any) -> None:
    fixed = datetime(2026, 7, 17, 8, 0, 0)
    for actor, user_id in ACTORS.items():
        db.session.add(User(
            id=user_id,
            username=f"phase4b_counts_{actor}",
            email=f"phase4b_counts_{actor}@test.example.com",
            password_hash="public-test-only-password-hash",
            has_password_set=True,
            email_verified=True,
            is_admin=False,
            is_subject_admin=False,
            is_notification_admin=False,
            is_locked=False,
            session_version=12 if actor == "revoked" else 11,
            created_at=fixed,
            last_active=None,
        ))
    db.session.commit()


def reset_case_facts(db: Any, tag_fixture: str) -> dict[str, Any]:
    from sqlalchemy import text

    db.session.rollback()
    for table in BUSINESS_TABLES:
        db.session.execute(text(f"DELETE FROM {table}"))
    _insert_rows(db, "user_question_banks", bank_rows())
    _insert_rows(db, "bank_shares", share_rows())
    _insert_rows(db, "bank_share_records", record_rows())
    _insert_rows(db, "user_bank_questions", question_rows())
    _insert_rows(db, "user_bank_favorites", favorite_rows())
    _insert_rows(db, "user_bank_mistakes", mistake_rows())
    if tag_fixture == "normalized":
        _insert_rows(db, "user_question_tag_items", [
            {
                "user_id": ACTORS["owner"], "scope": "user_bank",
                "scope_id": BANKS["owner_active"], "question_id": 0,
                "tag": "重点", "created_at": FIXED_NOW_BJ,
                "updated_at": FIXED_NOW_BJ,
            },
            {
                "user_id": ACTORS["owner"], "scope": "user_bank",
                "scope_id": BANKS["owner_active"],
                "question_id": QUESTIONS["single_a"], "tag": "重点",
                "created_at": FIXED_NOW_BJ, "updated_at": FIXED_NOW_BJ,
            },
        ])
    elif tag_fixture == "legacy":
        _insert_rows(db, "user_progress", [{
            "id": 99951,
            "user_id": ACTORS["owner"],
            "p_key": f"bank_{BANKS['owner_active']}_tags",
            "data": json.dumps({
                "tags": ["旧标签"],
                "question_tags": {
                    str(QUESTIONS["single_a"]): ["旧标签"],
                    str(QUESTIONS["multi"]): ["旧标签"],
                },
            }, ensure_ascii=False),
            "created_at": FIXED_NOW_BJ,
            "updated_at": FIXED_NOW_BJ,
        }])
    elif tag_fixture != "none":
        raise AssertionError(f"unknown tag fixture: {tag_fixture}")
    actor_binds = ", ".join(f":{actor}" for actor in ACTORS)
    db.session.execute(text(
        f"UPDATE users SET last_active = NULL WHERE id IN ({actor_binds})"
    ), ACTORS)
    db.session.commit()
    return {table: table_fingerprint(db, table) for table in BUSINESS_TABLES}


def set_actor_session(client: Any, actor: Optional[str]) -> None:
    with client.session_transaction() as session:
        session.clear()
        if actor is None:
            return
        session.update({
            "user_id": ACTORS[actor],
            "username": f"phase4b_counts_{actor}",
            "session_version": 11,
            "is_admin": False,
            "is_subject_admin": False,
            "is_notification_admin": False,
        })


def credential_mode(spec: CaseSpec) -> str:
    if spec.bearer_actor == "revoked" and spec.session_actor is not None:
        return "session+state_invalid_bearer"
    if spec.invalid_bearer and spec.session_actor is not None:
        return "session+invalid_bearer"
    if spec.bearer_actor is not None and spec.session_actor is not None:
        return "session+valid_bearer"
    if spec.bearer_actor is not None:
        return "valid_bearer_only"
    if spec.session_actor is not None:
        return "session"
    return "none"


def recorded_request_headers(spec: CaseSpec) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer <redacted-invalid-synthetic-jwt>"
    elif spec.bearer_actor == "revoked":
        result["Authorization"] = "Bearer <redacted-state-invalid-synthetic-jwt>"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer <redacted-valid-synthetic-jwt>"
    return result


def live_request_headers(spec: CaseSpec, tokens: dict[str, str]) -> dict[str, str]:
    result = {"Accept": spec.accept, "X-Request-ID": FIXED_REQUEST_ID}
    if spec.invalid_bearer:
        result["Authorization"] = "Bearer synthetic-invalid-token"
    elif spec.bearer_actor is not None:
        result["Authorization"] = "Bearer " + tokens[spec.bearer_actor]
    return result


def capture_case(
    client: Any,
    db: Any,
    legacy_app: Any,
    tokens: dict[str, str],
    spec: CaseSpec,
) -> dict[str, Any]:
    set_actor_session(client, spec.session_actor)
    reset_limiters(client.application)
    with client.application.app_context():
        expected = reset_case_facts(db, spec.tag_fixture)
        before = {table: table_fingerprint(db, table) for table in BUSINESS_TABLES}
        identity_before = user_identity_fingerprint(db)
        raw_activity_before, activity_before = user_activity_snapshot(db)
        engine = db.engine
        db.session.remove()
    with legacy_app._LAST_ACTIVE_LOCK:
        legacy_app._LAST_ACTIVE_TS.clear()
    digest = hashlib.sha256(spec.case_id.encode("utf-8")).digest()
    route = ROUTES[spec.route]
    bank_id = BANKS[spec.bank]
    path = route["path_template"].format(bank_id=bank_id)
    query_string = urlencode(spec.query)
    target = path + ("?" + query_string if query_string else "")
    with sql_probe(engine, spec) as sql:
        response = client.get(
            target,
            headers=live_request_headers(spec, tokens),
            environ_overrides={"REMOTE_ADDR": f"198.51.{digest[0]}.{digest[1]}"},
            follow_redirects=False,
        )
    with client.application.app_context():
        try:
            db.session.rollback()
        finally:
            db.session.remove()
        after = {table: table_fingerprint(db, table) for table in BUSINESS_TABLES}
        identity_after = user_identity_fingerprint(db)
        raw_activity_after, activity_after = user_activity_snapshot(db)
        db.session.remove()
    changed_activity_ids = sorted(
        user_id for user_id in raw_activity_before
        if raw_activity_before[user_id] != raw_activity_after[user_id]
    )
    return {
        "case_id": spec.case_id,
        "route_id": route["route_id"],
        "bank_fixture": spec.bank,
        "bank_id": bank_id,
        "session_actor": spec.session_actor or "anonymous",
        "bearer_actor": spec.bearer_actor or (
            "invalid" if spec.invalid_bearer else "none"
        ),
        "credential_mode": credential_mode(spec),
        "tag_fixture": spec.tag_fixture,
        "fault_injection": {
            "stage": spec.fail_stage,
            "occurrence": spec.fail_occurrence,
            "postgresql_poison_after_failure": spec.poison_after_failure,
        },
        "request": {
            "method": "GET",
            "path": path,
            "route_template": route["route_template"],
            "query": [list(item) for item in spec.query],
            "query_string": query_string,
            "headers": recorded_request_headers(spec),
            "remote_address": f"198.51.{digest[0]}.{digest[1]}",
        },
        "response": normalized_response(response),
        "observed_get_effects": {
            "sql": sql,
            "business_tables_before": before,
            "business_tables_after": after,
            "business_tables_match_case_fixture": {
                table: before[table] == expected[table] for table in BUSINESS_TABLES
            },
            "business_tables_unchanged": {
                table: before[table] == after[table] for table in BUSINESS_TABLES
            },
            "users_identity_before": identity_before,
            "users_identity_after": identity_after,
            "users_identity_unchanged": identity_before == identity_after,
            "user_last_active_before": activity_before,
            "user_last_active_after": activity_after,
            "user_last_active_changed_user_ids": changed_activity_ids,
            "surrounding_session_activity_write_observed": bool(changed_activity_ids),
        },
    }


def response_counts(case: dict[str, Any]) -> dict[str, Any]:
    body = case["response"]["body"]
    if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
        raise AssertionError(f"{case['case_id']} user-count envelope drifted")
    return body["data"]


BASE_COUNTS = {
    "total": 9,
    "favorites": 5,
    "mistakes": 3,
    "types": ["判断题", "简答题", "填空题", "多选题", "选择题", "选择题", "简答题"],
    "shuffle_options_available": False,
}
EMPTY_COUNTS = {
    "total": 0,
    "favorites": 0,
    "mistakes": 0,
    "types": [],
    "shuffle_options_available": False,
}


def assert_safe_500(case: dict[str, Any], *, json_expected: bool) -> None:
    if case["response"]["status"] != 500:
        raise AssertionError(f"{case['case_id']} must be HTTP 500")
    if "synthetic user-counts" in case["response"]["body_text"]:
        raise AssertionError(f"{case['case_id']} leaked fault injection")
    if json_expected:
        expected = {
            "status": "error",
            "message": "An unexpected server error occurred.",
            "status_code": 500,
            "payload": None,
            "request_id": FIXED_REQUEST_ID,
        }
        if case["response"]["body"] != expected:
            raise AssertionError(f"{case['case_id']} safe JSON 500 drifted")
    elif case["response"]["body"] != (
        "<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>"
    ):
        raise AssertionError(f"{case['case_id']} safe HTML 500 drifted")


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}
    if len(cases) != len(CASE_SPECS) or len(by_id) != len(CASE_SPECS):
        raise AssertionError("user-count golden case set is missing or duplicated")
    for spec in CASE_SPECS:
        case = by_id[spec.case_id]
        if case["response"]["status"] != spec.expected_status:
            raise AssertionError(
                f"{spec.case_id} status drifted: expected={spec.expected_status} "
                f"observed={case['response']['status']} body={case['response']['body']}"
            )
        effects = case["observed_get_effects"]
        sql = effects["sql"]
        if not all(effects["business_tables_match_case_fixture"].values()):
            raise AssertionError(f"{spec.case_id} fixture isolation drifted")
        if not effects["users_identity_unchanged"]:
            raise AssertionError(f"{spec.case_id} changed identity facts")
        if sql["classified_attempt_count"] != sql["statement_count"]:
            raise AssertionError(f"{spec.case_id} SQL classification did not close")
        expected_activity: list[int] = []
        if spec.session_actor is not None and spec.bearer_actor is None:
            expected_activity = [ACTORS[spec.session_actor]]
        if effects["user_last_active_changed_user_ids"] != expected_activity:
            raise AssertionError(
                f"{spec.case_id} last_active drifted: expected={expected_activity} "
                f"observed={effects['user_last_active_changed_user_ids']}"
            )
        if sql["user_last_active_dml_attempts"] != len(expected_activity):
            raise AssertionError(f"{spec.case_id} last_active SQL ledger drifted")

    for route in ROUTES:
        if response_counts(by_id[f"auth-session-owner-{route}"]) != BASE_COUNTS:
            raise AssertionError(f"auth-session-owner-{route} base counts drifted")
        if response_counts(by_id[f"data-empty-{route}"]) != EMPTY_COUNTS:
            raise AssertionError(f"data-empty-{route} drifted")
        if response_counts(by_id[f"access-public-other-{route}"]) != EMPTY_COUNTS:
            raise AssertionError(f"access-public-other-{route} drifted")
        if by_id[f"access-missing-{route}"]["response"]["status"] != 403:
            raise AssertionError(f"access-missing-{route} drifted")
        favorites = {
            "total": 5,
            "favorites": 5,
            "mistakes": 3,
            "types": ["判断题", "选择题", "选择题", "简答题"],
            "shuffle_options_available": False,
        }
        if response_counts(by_id[f"filter-source-favorites-{route}"]) != favorites:
            raise AssertionError(f"filter-source-favorites-{route} drifted")
        if response_counts(by_id[f"tag-normalized-sa2-empty-{route}"]) != EMPTY_COUNTS:
            raise AssertionError(f"tag-normalized-sa2-empty-{route} drifted")
        default = by_id[f"fault-total-default-{route}"]
        json_case = by_id[f"fault-total-json-{route}"]
        assert_safe_500(default, json_expected=route == "api-alias")
        assert_safe_500(json_case, json_expected=True)

    for case_id in (
        "filter-q-type-all-uppercase", "filter-source-case-sensitive-fallback",
        "tag-all-bypasses-store", "filter-tag-duplicate-first-all-wins",
        "auth-invalid-bearer-falls-back-session-api-alias",
        "auth-invalid-bearer-falls-back-session-web-alias",
    ):
        if response_counts(by_id[case_id]) != BASE_COUNTS:
            raise AssertionError(f"{case_id} base counts drifted")

    for case_id in ("access-status-null-owner", "access-status-two-owner"):
        if response_counts(by_id[case_id]) != EMPTY_COUNTS:
            raise AssertionError(f"{case_id} status-ignored access drifted")

    for case_id in (
        "access-shared-future", "access-shared-null-expiry",
        "access-shared-empty-expiry", "access-shared-cross-bank-record",
    ):
        result = response_counts(by_id[case_id])
        if (result["total"], result["favorites"], result["mistakes"]) != (9, 0, 0):
            raise AssertionError(f"{case_id} shared-reader counts drifted")

    choice = response_counts(by_id["filter-q-type-choice"])
    if choice != {
        "total": 2, "favorites": 2, "mistakes": 0,
        "types": ["选择题"], "shuffle_options_available": True,
    }:
        raise AssertionError("choice q_type contract drifted")
    if response_counts(by_id["filter-q-type-duplicate-first-wins"]) != choice:
        raise AssertionError("duplicate q_type first-value contract drifted")
    essay = response_counts(by_id["filter-q-type-unknown-maps-essay"])
    if essay != {
        "total": 1, "favorites": 0, "mistakes": 1,
        "types": ["简答题"], "shuffle_options_available": False,
    }:
        raise AssertionError("unknown q_type essay fallback drifted")
    mistakes = response_counts(by_id["filter-source-mistakes"])
    if mistakes != {
        "total": 3, "favorites": 5, "mistakes": 3,
        "types": ["判断题", "简答题", "多选题"],
        "shuffle_options_available": False,
    }:
        raise AssertionError("mistakes source contract drifted")
    if response_counts(by_id["filter-source-duplicate-first-wins"]) != response_counts(
        by_id["filter-source-favorites-api-alias"]
    ):
        raise AssertionError("duplicate source first-value contract drifted")
    duplicate_tag = by_id["filter-tag-duplicate-first-all-wins"]
    if duplicate_tag["observed_get_effects"]["sql"]["ddl_attempts"] != 0:
        raise AssertionError("duplicate tag did not use first all sentinel")
    for case_id, expected_query in {
        "filter-q-type-duplicate-first-wins": [
            ["q_type", "选择题"], ["q_type", "简答题"],
        ],
        "filter-source-duplicate-first-wins": [
            ["source", "favorites"], ["source", "mistakes"],
        ],
        "filter-tag-duplicate-first-all-wins": [
            ["tag", "all"], ["tag", "重点"],
        ],
    }.items():
        if by_id[case_id]["request"]["query"] != expected_query:
            raise AssertionError(f"{case_id} duplicate query evidence drifted")

    for case_id in (
        "tag-case-sensitive-all-enters-store", "tag-legacy-migration-sa2-empty",
    ):
        if response_counts(by_id[case_id]) != EMPTY_COUNTS:
            raise AssertionError(f"{case_id} SA2 tag fallback drifted")
    normalized_raw = by_id["tag-normalized-sa2-empty-api-alias"][
        "observed_get_effects"
    ]["sql"]["raw_connection_execute_attempts"]
    if [row["classification"] for row in normalized_raw] != [
        "raw_sa2_new_tag_presence_probe"
    ]:
        raise AssertionError("normalized tag raw SA2 failure drifted")
    legacy_raw = by_id["tag-legacy-migration-sa2-empty"][
        "observed_get_effects"
    ]["sql"]["raw_connection_execute_attempts"]
    if [row["classification"] for row in legacy_raw] != [
        "raw_sa2_new_tag_presence_probe",
        "raw_sa2_legacy_tag_migration_delete",
    ]:
        raise AssertionError("legacy tag migration attempt drifted")
    if not all(row.get("exception_type") == "ArgumentError"
               for row in normalized_raw + legacy_raw):
        raise AssertionError("SA2 raw-string exception type drifted")

    sqlite_favorites = response_counts(by_id["fault-favorites-sqlite-continues"])
    poison_favorites = response_counts(
        by_id["fault-favorites-postgresql-poison-simulation"]
    )
    sqlite_mistakes = response_counts(by_id["fault-mistakes-sqlite-continues"])
    poison_mistakes = response_counts(
        by_id["fault-mistakes-postgresql-poison-simulation"]
    )
    if sqlite_favorites != {**BASE_COUNTS, "favorites": 0}:
        raise AssertionError("SQLite favorite fallback contract drifted")
    if poison_favorites != {
        "total": 9, "favorites": 0, "mistakes": 0,
        "types": [], "shuffle_options_available": False,
    }:
        raise AssertionError("PostgreSQL favorite poisoning simulation drifted")
    if sqlite_mistakes != {**BASE_COUNTS, "mistakes": 0}:
        raise AssertionError("SQLite mistake fallback contract drifted")
    if poison_mistakes != {
        "total": 9, "favorites": 5, "mistakes": 0,
        "types": [], "shuffle_options_available": False,
    }:
        raise AssertionError("PostgreSQL mistake poisoning simulation drifted")
    if response_counts(by_id["fault-types-degrades"]) != {
        "total": 9, "favorites": 5, "mistakes": 3,
        "types": [], "shuffle_options_available": False,
    }:
        raise AssertionError("types fallback drifted")
    if response_counts(by_id[
        "fault-source-favorites-second-count-postgresql-poison-simulation"
    ]) != {
        "total": 5, "favorites": 0, "mistakes": 0,
        "types": [], "shuffle_options_available": False,
    }:
        raise AssertionError("duplicate favorite-count poisoning simulation drifted")

    baseline_sequence = by_id["auth-session-owner-api-alias"][
        "observed_get_effects"
    ]["sql"]["personal_bank_query_sequence"]
    if baseline_sequence != [
        "personal_bank_user_counts_bank_access_probe",
        "personal_bank_user_counts_total_all",
        "personal_bank_user_counts_favorites_count",
        "personal_bank_user_counts_mistakes_count",
        "personal_bank_user_counts_types_all",
    ]:
        raise AssertionError("baseline five-stage query sequence drifted")
    favorite_sequence = by_id["filter-source-favorites-api-alias"][
        "observed_get_effects"
    ]["sql"]["personal_bank_query_sequence"]
    if favorite_sequence != [
        "personal_bank_user_counts_bank_access_probe",
        "personal_bank_user_counts_favorites_count",
        "personal_bank_user_counts_favorites_count",
        "personal_bank_user_counts_mistakes_count",
        "personal_bank_user_counts_types_favorites",
    ]:
        raise AssertionError("favorite duplicate query sequence drifted")

    if by_id["auth-anonymous-api-alias"]["response"]["body_kind"] != "json":
        raise AssertionError("anonymous API alias must return JSON 401")
    state_invalid = by_id[
        "auth-state-invalid-bearer-does-not-fallback-session-api-alias"
    ]
    state_invalid_body = state_invalid["response"]["body"]
    if (
        state_invalid_body.get("status") != "unauthorized"
        or "会话已失效" not in state_invalid_body.get("message", "")
    ):
        raise AssertionError("state-invalid bearer must not fall back to Session")
    for case_id in (
        "auth-bearer-owner-web-alias", "auth-bearer-precedes-session-web-alias",
        "auth-state-invalid-bearer-does-not-fallback-session-web-alias",
        "auth-anonymous-web-alias",
    ):
        if by_id[case_id]["response"]["headers"].get("Location") != ["/login"]:
            raise AssertionError(f"{case_id} must redirect to /login")

    malformed = by_id["access-shared-malformed-expiry-value-error"]
    if malformed["response"]["body"].get("message") != "请求参数无效":
        raise AssertionError("malformed share expiry ValueError contract drifted")
    assert_safe_500(
        by_id["access-shared-aware-expiry-type-error"], json_expected=True
    )
    assert_safe_500(by_id["fault-share-access-hard-failure"], json_expected=True)


def capture_document(legacy_root: Path) -> dict[str, Any]:
    if pinned_source.LEGACY_COMMIT != LEGACY_COMMIT:
        raise AssertionError("shared fixed-commit authority drifted")
    with pinned_source.archived_legacy_source(legacy_root) as archived:
        caller_reference = caller_evidence_reference()
        source_attestation = {
            "complete_app_archive": archived.attestation,
            "frozen_route_matrix": matrix_attestation(),
            "key_sources": key_source_attestation(archived, legacy_root),
            "caller_evidence": caller_reference,
        }
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4b-personal-bank-user-counts-data-"
        ) as data_dir:
            with capture_environment(data_dir):
                with pinned_source.archived_legacy_import_environment(archived.root):
                    import app as legacy_app
                    from app.core.extensions import db
                    from app.core.utils.jwt_utils import generate_jwt_token
                    from app.models.user import User
                    from app.modules.user_bank.routes import api_base, api_quiz

                    pinned_source.assert_module_from_archive(legacy_app, archived.root)
                    pinned_source.assert_module_from_archive(api_base, archived.root)
                    pinned_source.assert_module_from_archive(api_quiz, archived.root)
                    previous_logging = logging.root.manager.disable
                    original_now_bj = api_base.now_bj
                    logging.disable(logging.CRITICAL)
                    legacy_app._start_background_tasks = lambda _app: None
                    api_base.now_bj = lambda: FIXED_NOW_BJ
                    app = legacy_app.create_app("testing")
                    app.config.update(
                        JWT_USER_STATE_CACHE_TTL_SECONDS=0,
                        LAST_ACTIVE_UPDATE_INTERVAL_SECONDS=60,
                        PROPAGATE_EXCEPTIONS=False,
                        RATELIMIT_ENABLED=False,
                        TESTING=True,
                    )
                    try:
                        with app.app_context():
                            db.create_all()
                            seed_static_actors(db, User)
                            full_fixture = reset_case_facts(db, "none")
                            tokens = {
                                actor: generate_jwt_token(
                                    user_id=user_id,
                                    openid="",
                                    session_version=11,
                                )
                                for actor, user_id in ACTORS.items()
                            }
                            db.session.remove()
                        client = app.test_client()
                        cases = [
                            capture_case(client, db, legacy_app, tokens, spec)
                            for spec in CASE_SPECS
                        ]
                        assert_case_contracts(cases)
                    finally:
                        api_base.now_bj = original_now_bj
                        logging.disable(previous_logging)
                        with app.app_context():
                            db.session.remove()

        provenance = tool_provenance()
        document: dict[str, Any] = {
            "contract_id": "ti.phase4b.personal-bank-user-counts-read-goldens",
            "schema_version": 1,
            "captured_at": "2026-07-17",
            "legacy_commit": LEGACY_COMMIT,
            "fixed_beijing_time": FIXED_NOW_BJ.isoformat(sep=" "),
            "legacy_source_attestation": source_attestation,
            "provenance": {
                **provenance,
                "hashes": {
                    "legacy_handler_source_sha256": source_attestation[
                        "key_sources"
                    ]["app/modules/user_bank/routes/api_quiz.py"]["sha256"],
                    "legacy_access_source_sha256": source_attestation[
                        "key_sources"
                    ]["app/modules/user_bank/routes/api_base.py"]["sha256"],
                    "legacy_tag_source_sha256": source_attestation[
                        "key_sources"
                    ]["app/modules/user_bank/routes/api_tags.py"]["sha256"],
                    "caller_evidence_sha256": caller_reference.get("sha256"),
                    "case_payload_sha256": sha256_json(cases),
                    "capture_tool_sha256": provenance["capture_tool"]["sha256"],
                    "capture_test_sha256": provenance["capture_test"]["sha256"],
                },
            },
            "route_status": {
                "target_internal_owner": "personalbank",
                "http_owner": "personalbank",
                "migration_status": "pending",
                "production_cutover": False,
                "routes": ROUTES,
                "controller_added": False,
                "openapi_delta": False,
                "route_delta": False,
            },
            "legacy_query_contract": {
                "access_order": [
                    "SELECT * FROM user_question_banks WHERE id = :bank_id",
                    "conditional SELECT bsr.*, bs.permission, bs.is_active, bs.expires_at "
                    "FROM bank_share_records bsr JOIN bank_shares bs ON bsr.share_id = bs.id "
                    "WHERE bsr.user_id = :user_id AND bsr.bank_id = :bank_id "
                    "AND bsr.status = 1; fetchone without ORDER BY",
                ],
                "statistics_order": [
                    "total selected by exact source favorites/mistakes else all",
                    "favorites count for current viewer regardless of source",
                    "mistakes count for current viewer regardless of source",
                    "DISTINCT raw q.type ordered by raw q.type then mapped to Chinese",
                ],
                "favorites_source_duplicate_query": True,
                "mistakes_source_duplicate_query": True,
                "count_aggregate": "COUNT(*) returns PostgreSQL bigint; no DISTINCT",
                "pagination": None,
                "time_window": None,
                "types_order": "raw stored q.type ASC before display mapping",
                "types_post_mapping_deduplication": False,
                "duplicate_query_key_resolution": (
                    "request.args.get consumes the first value for q_type, source, and tag; "
                    "ordered duplicate-key fixtures are captured"
                ),
                "relation_bank_id_semantics": (
                    "favorite/mistake bank_id is not filtered; q.bank_id is authoritative"
                ),
                "bind_types": {
                    "bank_id": "Python int to legacy INTEGER",
                    "uid": "normal Session/JWT path Python int to legacy INTEGER",
                    "q_type_f": "Python str to TEXT",
                    "tag_question_ids": "int() values expanded as tq_N INTEGER binds",
                },
            },
            "access_contract": {
                "bank_missing_or_status_zero": "403 no access",
                "status_null_or_nonzero": "not rejected by status gate",
                "owner": "short-circuits before public/share checks",
                "public": "any authenticated identity can read",
                "shared": (
                    "one arbitrary fetchone row must have truthy is_active and NULL/falsey "
                    "expiry or a strictly future expiry"
                ),
                "share_permission": "returned but ignored by user-counts",
                "expiry_clock": "fixed naive Beijing local datetime",
                "expiry_comparison": "datetime.fromisoformat(str(expires_at)) > now_bj()",
                "equal_to_now": "denied",
                "null_or_empty_expiry": "accepted",
                "malformed_expiry": "ValueError routed to safe 400",
                "offset_aware_expiry": "aware/naive TypeError routed to safe 500",
                "multiple_share_rows": (
                    "fetchone without ORDER BY is intentionally recorded as non-portable; "
                    "the SQLite fixture observes the lower inserted expired row"
                ),
                "cross_bank_share_coherence": (
                    "bs.bank_id is not compared with bsr.bank_id; the mismatch fixture grants access"
                ),
                "admin_bypass": False,
            },
            "filter_and_count_contract": {
                "q_type": (
                    "trim; case-insensitive all means no filter; every other non-empty value "
                    "passes through any_type_to_portable_type and unknown values become essay"
                ),
                "source": (
                    "trim; only case-sensitive exact favorites and mistakes are special; "
                    "all other values use the all branch"
                ),
                "tag": (
                    "trim; empty or exact lowercase all bypasses tag loading; membership and "
                    "the All sentinel are otherwise case-sensitive"
                ),
                "raw_type_mapping": {
                    "empty_or_null": "counted when unfiltered but omitted from types",
                    "unknown": "mapped to 简答题",
                    "alias_collapse": "may create duplicate Chinese entries after SQL DISTINCT",
                },
                "shuffle_options_available": (
                    "types must be non-empty and every mapped entry must be 选择题 or 多选题"
                ),
                "baseline": BASE_COUNTS,
                "empty": EMPTY_COUNTS,
            },
            "tag_compatibility_contract": {
                "source_intent": (
                    "ensure normalized tag table/indexes, read normalized rows first, otherwise "
                    "read user_progress and best-effort migrate then commit"
                ),
                "get_ddl_attempts": (
                    "CREATE TABLE IF NOT EXISTS plus two CREATE INDEX IF NOT EXISTS statements"
                ),
                "legacy_migration_intent": (
                    "DELETE then INSERT OR IGNORE normalized rows followed by db.session.commit"
                ),
                "observed_sqlalchemy_runtime": provenance["runtime_versions"]["sqlalchemy"],
                "observed_failure": (
                    "api_tags passes raw str with qmark placeholders to SQLAlchemy Connection.execute; "
                    "with positional tuple parameters, SQLAlchemy 2 raises ArgumentError before "
                    "cursor execution (before it reaches raw-string executability validation)"
                ),
                "postgresql_additional_incompatibility": "INSERT OR IGNORE is SQLite-only syntax",
                "observed_normalized_fixture_result": "HTTP 200 zero counts",
                "observed_legacy_fixture_result": (
                    "HTTP 200 zero counts after presence probe and migration DELETE attempts fail"
                ),
                "migration_commit_reached_in_observed_runtime": False,
                "approved_java_behavior": "not established by this evidence",
            },
            "failure_and_transaction_contract": {
                "access_and_total": "uncaught and negotiated by the global error handler",
                "favorites": "broad catch -> zero",
                "mistakes": "broad catch -> zero",
                "types": "broad catch -> empty list and shuffle false",
                "sqlite_observation": (
                    "a synthetic optional statement failure does not poison later SQLite statements"
                ),
                "postgresql_poison_simulation": (
                    "after the first synthetic statement failure, subsequent statistics statements "
                    "raise current-transaction-is-aborted; this is a deterministic semantic model, "
                    "not direct PostgreSQL 16/18 runtime proof"
                ),
                "remaining_gate": (
                    "direct PostgreSQL 16.14 and 18.4 adapter evidence must independently prove "
                    "the chosen transaction boundaries"
                ),
                "fault_text_redacted": True,
            },
            "authentication_contract": {
                "session": "accepted on both aliases and may commit users.last_active",
                "api_bearer": "accepted and precedes Session identity",
                "invalid_bearer": "falls back to a valid Session",
                "state_invalid_bearer": (
                    "a signature-valid bearer with stale session_version does not fall back "
                    "to a valid Session"
                ),
                "web_bearer_only": "global Web gate redirects to /login before route entry",
                "anonymous_api": "JSON 401",
                "anonymous_web": "redirect /login",
                "valid_bearer_last_active": "does not write Session activity",
            },
            "request_effect_scope": {
                "business_tables": list(BUSINESS_TABLES),
                "normal_statistics_business_dml": 0,
                "tag_path": "DDL attempts and source-intended legacy migration/commit",
                "observed_tag_runtime_business_dml": 0,
                "surrounding_session_side_effect": (
                    "users.last_active may be committed before handler entry, including later 403/500"
                ),
            },
            "legacy_test_coverage": {
                "source": "tests/test_user_bank_quiz_record.py",
                "covered": (
                    "owner Session, unfiltered single+multi true gate and single+boolean false gate"
                ),
                "not_covered": (
                    "dual aliases, JWT, access variants, counts, q_type/source/tag, raw aliases, "
                    "faults, GET side effects and PostgreSQL transaction poisoning"
                ),
            },
            "isolation": (
                "complete app/ tree from fixed read-only git archive; temporary SQLite; "
                "in-memory limiter; synthetic identities; fixed api_base.now_bj; no current "
                "worktree legacy import"
            ),
            "redaction": (
                "JWT, password hash, Session cookie values and database-current last_active "
                "timestamps are omitted or represented by deterministic placeholders"
            ),
            "fixture": {
                "actors": ACTORS,
                "banks": BANKS,
                "shares": SHARES,
                "records": RECORDS,
                "questions": QUESTIONS,
                "full_table_fingerprints": full_fixture,
                "question_row_count": len(question_rows()),
                "owner_favorite_count": 5,
                "owner_mistake_count": 3,
            },
            "case_count": len(cases),
            "case_payload_sha256": sha256_json(cases),
            "cases": cases,
        }
        document["document_payload_sha256"] = document_payload_sha256(document)
        return document


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        f"captured {document['case_count']} personal-bank user-count cases "
        f"cases_sha256={document['case_payload_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
