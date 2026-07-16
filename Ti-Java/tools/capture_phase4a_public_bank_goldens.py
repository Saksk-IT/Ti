#!/usr/bin/env python3
"""Capture deterministic Phase 4A public-bank read goldens from legacy Flask."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import io
import json
import logging
import os
from pathlib import Path, PurePosixPath
import pkgutil
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Any, Iterator


sys.dont_write_bytecode = True

FIXED_NOW_BJ = datetime(2026, 7, 16, 12, 0, 0)
FIXED_REQUEST_ID = "phase4a-public-bank-golden-request"
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
ARCHIVE_PREFIX = "legacy-source"
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_FILE_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 64 * 1024 * 1024
KEY_SOURCE_FILES = (
    "app/__init__.py",
    "app/core/extensions.py",
    "app/core/utils/api_response.py",
    "app/modules/user_bank/routes/public.py",
    "app/modules/user_bank/services/plaza_metrics_service.py",
    "app/modules/user_bank/services/plaza_query_service.py",
)

SOURCE_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": (
        "id", "username", "password_hash", "is_admin", "is_locked",
        "session_version", "avatar", "last_active", "created_at", "email",
        "email_verified", "has_password_set", "openid",
    ),
    "plaza_boards": (
        "id", "slug", "name", "description", "icon", "sort_order",
        "is_active", "created_at", "updated_at",
    ),
    "subjects": (
        "id", "name", "description", "is_locked", "plaza_board_id",
        "is_plaza_featured", "plaza_featured_weight", "plaza_featured_at",
        "created_at",
    ),
    "questions": (
        "id", "subject_id", "type", "content", "options", "answer",
        "analysis", "tags", "difficulty", "source", "created_by",
        "updated_by", "created_at", "updated_at",
    ),
    "user_answers": (
        "id", "user_id", "question_id", "user_answer", "is_correct",
        "created_at",
    ),
    "public_subject_users": (
        "id", "subject_id", "user_id", "last_access_at", "access_count",
        "created_at",
    ),
    "user_question_banks": (
        "id", "user_id", "category_id", "name", "description", "cover_image",
        "is_public", "public_description", "allow_copy", "public_at",
        "question_count", "share_count", "public_use_count", "status",
        "plaza_board_id", "is_plaza_featured", "plaza_featured_weight",
        "plaza_featured_at", "join_mode", "join_note", "created_at",
        "updated_at",
    ),
    "user_bank_questions": (
        "id", "bank_id", "user_id", "type", "content", "options", "answer",
        "analysis", "tags", "difficulty", "source_type", "source_question_id",
        "sort_order", "created_at", "updated_at",
    ),
    "user_bank_answers": (
        "id", "user_id", "bank_id", "question_id", "user_answer",
        "is_correct", "created_at",
    ),
    "public_bank_users": (
        "id", "bank_id", "user_id", "last_access_at", "access_count",
        "created_at",
    ),
    "bank_shares": (
        "id", "bank_id", "owner_id", "share_code", "share_token",
        "permission", "expires_at", "max_uses", "current_uses", "is_active",
        "created_at",
    ),
    "bank_share_records": (
        "id", "share_id", "bank_id", "user_id", "status", "last_access_at",
        "access_count", "created_at",
    ),
}

METRIC_COLUMNS: tuple[str, ...] = (
    "source_type", "source_id", "name", "description", "cover_image",
    "owner_label", "question_count_total", "plaza_board_id", "is_featured",
    "featured_weight", "published_at", "last_activity_at", "join_count_total",
    "join_users_7d", "join_users_30d", "answer_count_7d", "answer_count_30d",
    "answer_users_7d", "answer_users_30d", "hot_score", "active_score",
    "recommended_score", "updated_at",
)

ROUTES = (
    {"route_id": "14642ebe7c1d", "path": "/api/public/banks"},
    {"route_id": "db1ac691d6fb", "path": "/api/public/banks/boards"},
    {"route_id": "8cfb837021af", "path": "/api/public/banks/card/<source_type>/<int:bank_id>"},
    {"route_id": "a473896ff467", "path": "/api/public/banks/hot"},
    {"route_id": "b7e49e77a026", "path": "/api/public/banks/list"},
    {"route_id": "f3644c1474f3", "path": "/api/public/banks/summary"},
    {"route_id": "37cd782b28dc", "path": "/api/public/banks/<int:bank_id>"},
)

_DATETIME_RE = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})(?:\.(?P<micro>\d{1,6}))?$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


class LegacySourceArchiveError(RuntimeError):
    """Raised when the pinned legacy source cannot be proven and extracted safely."""


@dataclass(frozen=True)
class ArchivedLegacySource:
    root: Path
    workspace: Path
    attestation: dict[str, Any]


def _run_read_only_git(legacy_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    command = [
        "git",
        "--no-optional-locks",
        "-C",
        str(legacy_root),
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exception:
        raise LegacySourceArchiveError(
            f"read-only git command failed: {arguments[0]}"
        ) from exception
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace")[-2000:].strip()
        raise LegacySourceArchiveError(
            f"read-only git command rejected {arguments[0]}: {detail}"
        )
    return result.stdout


def _read_git_text(legacy_root: Path, *arguments: str) -> str:
    return _run_read_only_git(legacy_root, *arguments).decode("utf-8").strip()


def _pinned_tree_entries(legacy_root: Path, commit: str) -> dict[str, dict[str, str]]:
    raw = _run_read_only_git(
        legacy_root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        commit,
        "--",
        "app",
    )
    entries: dict[str, dict[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exception:
            raise LegacySourceArchiveError("invalid git ls-tree record") from exception
        if object_type != "blob" or not path.startswith("app/"):
            raise LegacySourceArchiveError(f"unexpected app tree entry: {path}")
        if path in entries:
            raise LegacySourceArchiveError(f"duplicate app tree entry: {path}")
        entries[path] = {"mode": mode, "git_blob": object_id}
    if "app/__init__.py" not in entries:
        raise LegacySourceArchiveError("pinned commit does not contain a complete app package")
    return entries


def _git_blob_id(payload: bytes, object_format: str) -> str:
    try:
        digest = hashlib.new(object_format)
    except ValueError as exception:
        raise LegacySourceArchiveError(
            f"unsupported Git object format: {object_format}"
        ) from exception
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _validated_archive_member(member: tarfile.TarInfo, destination: Path) -> Path:
    raw_name = member.name
    if not raw_name or "\\" in raw_name or "\0" in raw_name:
        raise LegacySourceArchiveError(f"unsafe archive member name: {raw_name!r}")
    normalized_name = raw_name[:-1] if raw_name.endswith("/") else raw_name
    pure_path = PurePosixPath(normalized_name)
    if (
        pure_path.is_absolute()
        or any(part in {"", ".", ".."} for part in pure_path.parts)
        or pure_path.as_posix() != normalized_name
    ):
        raise LegacySourceArchiveError(f"unsafe archive member path: {raw_name!r}")
    parts = pure_path.parts
    if not parts or parts[0] != ARCHIVE_PREFIX:
        raise LegacySourceArchiveError(f"archive member escaped fixed prefix: {raw_name!r}")
    if len(parts) > 1 and parts[1] != "app":
        raise LegacySourceArchiveError(f"archive member escaped app scope: {raw_name!r}")
    if not member.isdir() and not member.isfile():
        raise LegacySourceArchiveError(f"archive links/devices are forbidden: {raw_name!r}")
    if member.size < 0:
        raise LegacySourceArchiveError(f"archive member has a negative size: {raw_name!r}")
    if member.isdir() and member.size != 0:
        raise LegacySourceArchiveError(f"archive directory has data: {raw_name!r}")
    if member.isfile() and member.size > MAX_ARCHIVE_FILE_BYTES:
        raise LegacySourceArchiveError(f"archive member is too large: {raw_name!r}")
    target = destination.joinpath(*parts)
    try:
        target.resolve().relative_to(destination.resolve())
    except ValueError as exception:
        raise LegacySourceArchiveError(
            f"archive member escaped extraction root: {raw_name!r}"
        ) from exception
    return target


def _safe_extract_app_archive(
    archive_bytes: bytes,
    destination: Path,
    object_format: str,
) -> tuple[int, dict[str, dict[str, Any]]]:
    if not archive_bytes or len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise LegacySourceArchiveError("git archive size is outside the allowed bounds")
    destination.mkdir(parents=True, exist_ok=False)
    evidence: dict[str, dict[str, Any]] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
            members = archive.getmembers()
            if not members or len(members) > MAX_ARCHIVE_MEMBERS:
                raise LegacySourceArchiveError("git archive member count is invalid")
            validated: list[tuple[tarfile.TarInfo, Path]] = []
            seen: set[str] = set()
            expanded_size = 0
            for member in members:
                target = _validated_archive_member(member, destination)
                normalized_name = member.name.removesuffix("/")
                if normalized_name in seen:
                    raise LegacySourceArchiveError(
                        f"duplicate archive member: {normalized_name!r}"
                    )
                seen.add(normalized_name)
                if member.isfile():
                    expanded_size += member.size
                    if expanded_size > MAX_ARCHIVE_EXPANDED_BYTES:
                        raise LegacySourceArchiveError("git archive expands beyond its size limit")
                validated.append((member, target))

            for member, target in validated:
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise LegacySourceArchiveError(
                        f"archive file could not be read: {member.name!r}"
                    )
                payload = extracted.read(MAX_ARCHIVE_FILE_BYTES + 1)
                if len(payload) != member.size:
                    raise LegacySourceArchiveError(
                        f"archive member size mismatch: {member.name!r}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with target.open("xb") as handle:
                        handle.write(payload)
                except FileExistsError as exception:
                    raise LegacySourceArchiveError(
                        f"archive member overwrote a path: {member.name!r}"
                    ) from exception
                relative = PurePosixPath(*PurePosixPath(member.name).parts[1:]).as_posix()
                evidence[relative] = {
                    "git_blob": _git_blob_id(payload, object_format),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
    except (tarfile.TarError, OSError) as exception:
        raise LegacySourceArchiveError("git archive could not be extracted safely") from exception
    return len(members), evidence


def _materialize_archived_legacy_source(
    legacy_root: Path,
    workspace: Path,
) -> ArchivedLegacySource:
    repository_root = Path(
        _read_git_text(legacy_root, "rev-parse", "--show-toplevel")
    ).resolve()
    _run_read_only_git(
        repository_root,
        "cat-file",
        "-e",
        f"{LEGACY_COMMIT}^{{commit}}",
    )
    archive_commit = _read_git_text(
        repository_root,
        "rev-parse",
        "--verify",
        f"{LEGACY_COMMIT}^{{commit}}",
    )
    if archive_commit != LEGACY_COMMIT:
        raise LegacySourceArchiveError(
            f"legacy commit resolved unexpectedly: {archive_commit}"
        )
    object_format = _read_git_text(
        repository_root,
        "rev-parse",
        "--show-object-format",
    )
    archive_tree = _read_git_text(
        repository_root,
        "rev-parse",
        f"{archive_commit}^{{tree}}",
    )
    expected_entries = _pinned_tree_entries(repository_root, archive_commit)
    archive_bytes = _run_read_only_git(
        repository_root,
        "archive",
        "--format=tar",
        f"--prefix={ARCHIVE_PREFIX}/",
        archive_commit,
        "--",
        "app",
    )
    extraction_root = workspace / "extracted"
    member_count, extracted_entries = _safe_extract_app_archive(
        archive_bytes,
        extraction_root,
        object_format,
    )
    if set(extracted_entries) != set(expected_entries):
        missing = sorted(set(expected_entries) - set(extracted_entries))[:5]
        unexpected = sorted(set(extracted_entries) - set(expected_entries))[:5]
        raise LegacySourceArchiveError(
            f"archive app tree mismatch: missing={missing}, unexpected={unexpected}"
        )
    mismatched_blobs = [
        path
        for path in sorted(expected_entries)
        if extracted_entries[path]["git_blob"] != expected_entries[path]["git_blob"]
    ]
    if mismatched_blobs:
        raise LegacySourceArchiveError(
            f"archive blob mismatch: {mismatched_blobs[:5]}"
        )
    missing_key_sources = sorted(set(KEY_SOURCE_FILES) - set(extracted_entries))
    if missing_key_sources:
        raise LegacySourceArchiveError(
            f"archive lacks key public-bank sources: {missing_key_sources}"
        )
    key_sources = {
        path: {
            "git_blob": expected_entries[path]["git_blob"],
            "sha256": extracted_entries[path]["sha256"],
            "size_bytes": extracted_entries[path]["size_bytes"],
        }
        for path in KEY_SOURCE_FILES
    }
    attestation = {
        "archive_commit": archive_commit,
        "archive_tree": archive_tree,
        "archive_scope": ["app/"],
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "commit_object_verified": True,
        "complete_app_tree_verified": True,
        "extracted_file_count": len(extracted_entries),
        "git_object_format": object_format,
        "key_sources": key_sources,
        "member_count": member_count,
        "source_transport": "git archive --format=tar (read-only, fixed commit)",
        "temporary_extraction_cleanup": "enforced and checked on context exit",
    }
    return ArchivedLegacySource(
        root=extraction_root / ARCHIVE_PREFIX,
        workspace=workspace,
        attestation=attestation,
    )


@contextmanager
def archived_legacy_source(legacy_root: Path) -> Iterator[ArchivedLegacySource]:
    workspace: Path | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="ti-java-phase4a-public-bank-source-"
        ) as temporary:
            workspace = Path(temporary)
            yield _materialize_archived_legacy_source(legacy_root.resolve(), workspace)
    finally:
        if workspace is not None and workspace.exists():
            raise LegacySourceArchiveError(
                f"temporary legacy source workspace was not removed: {workspace}"
            )


@contextmanager
def archived_legacy_import_environment(source_root: Path) -> Iterator[None]:
    loaded_app_modules = [
        name for name in sys.modules if name == "app" or name.startswith("app.")
    ]
    if loaded_app_modules:
        raise LegacySourceArchiveError(
            f"app modules were loaded before archive isolation: {loaded_app_modules[:5]}"
        )
    previous_directory = Path.cwd()
    source_path = str(source_root)
    sys.path.insert(0, source_path)
    try:
        os.chdir(source_root)
        yield
    finally:
        try:
            os.chdir(previous_directory)
        finally:
            if source_path in sys.path:
                sys.path.remove(source_path)
            for name in list(sys.modules):
                if name == "app" or name.startswith("app."):
                    del sys.modules[name]


def assert_module_from_archive(module: Any, source_root: Path) -> None:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise LegacySourceArchiveError(f"imported module lacks __file__: {module!r}")
    try:
        Path(module_file).resolve().relative_to((source_root / "app").resolve())
    except ValueError as exception:
        raise LegacySourceArchiveError(
            f"module was not imported from pinned archive: {module.__name__}"
        ) from exception


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    if isinstance(value, str):
        match = _DATETIME_RE.fullmatch(value.strip())
        if match:
            micro = (match.group("micro") or "").ljust(6, "0")
            if not micro or int(micro) == 0:
                return match.group("base").replace("T", " ")
        return value
    return value


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): normalize_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_value(child) for child in value]
    return normalize_scalar(value)


def normalize_vary(value: str) -> str:
    tokens = sorted({token.strip() for token in str(value).split(",") if token.strip()})
    return ", ".join(tokens)


def normalized_response(response: Any) -> dict[str, Any]:
    payload = response.get_json(silent=True)
    if payload is None:
        raw = response.get_data(as_text=True)
        payload = {"body_excerpt": raw[:1000], "truncated": len(raw) > 1000}

    headers: dict[str, str] = {}
    for name in (
        "Content-Type",
        "Vary",
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ):
        if name not in response.headers:
            continue
        if name == "Vary":
            headers[name] = normalize_vary(response.headers[name])
        elif name == "X-RateLimit-Remaining":
            headers[name] = "<dynamic-counter>"
        elif name == "X-RateLimit-Reset":
            headers[name] = "<dynamic-epoch-second>"
        elif name == "Retry-After":
            headers[name] = "<dynamic-positive-seconds>"
        else:
            headers[name] = response.headers[name]

    return {
        "status": response.status_code,
        "headers": headers,
        "body": normalize_value(payload),
    }


def select_rows(db: Any, table: str, columns: tuple[str, ...], order_by: str) -> list[dict[str, Any]]:
    from sqlalchemy import text

    rows = db.session.execute(
        text(f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order_by}")
    ).mappings().all()
    return [
        {column: normalize_value(row.get(column)) for column in columns}
        for row in rows
    ]


def metrics_snapshot(db: Any) -> list[dict[str, Any]]:
    return select_rows(
        db,
        "public_bank_plaza_metrics",
        METRIC_COLUMNS,
        "source_type, source_id",
    )


def database_fingerprint(db: Any) -> dict[str, Any]:
    table_details: dict[str, dict[str, Any]] = {}
    source_payload: dict[str, list[dict[str, Any]]] = {}
    for table, columns in SOURCE_TABLE_COLUMNS.items():
        rows = select_rows(db, table, columns, "id")
        source_payload[table] = rows
        table_details[table] = {
            "row_count": len(rows),
            "sha256": sha256_json(rows),
        }

    metric_rows = metrics_snapshot(db)
    table_details["public_bank_plaza_metrics"] = {
        "row_count": len(metric_rows),
        "sha256": sha256_json(metric_rows),
    }
    source_sha256 = sha256_json(source_payload)
    metrics_sha256 = sha256_json(metric_rows)
    return {
        "sha256": sha256_json({
            "source_sha256": source_sha256,
            "metrics_sha256": metrics_sha256,
        }),
        "source_sha256": source_sha256,
        "metrics_sha256": metrics_sha256,
        "tables": table_details,
    }


def fingerprint_now(app: Any, db: Any) -> dict[str, Any]:
    with app.app_context():
        result = database_fingerprint(db)
        db.session.rollback()
        return result


def changed_tables(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    names = sorted(set(before["tables"]) | set(after["tables"]))
    return [
        table
        for table in names
        if before["tables"].get(table) != after["tables"].get(table)
    ]


class DatabaseEffectProbe:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.write_statement_count = 0
        self.metrics_delete_count = 0
        self.metrics_insert_count = 0
        self.metrics_inserted_rows = 0
        self.commit_count = 0

    def before_cursor_execute(
        self,
        _conn: Any,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        executemany: bool,
    ) -> None:
        sql = " ".join(str(statement).split())
        upper = sql.upper()
        self.statements.append(classify_sql(upper))
        if upper.startswith(("INSERT ", "UPDATE ", "DELETE ")):
            self.write_statement_count += 1
        if upper.startswith("DELETE FROM PUBLIC_BANK_PLAZA_METRICS"):
            self.metrics_delete_count += 1
        if upper.startswith("INSERT INTO PUBLIC_BANK_PLAZA_METRICS"):
            self.metrics_insert_count += 1
            if executemany and isinstance(parameters, (list, tuple)):
                self.metrics_inserted_rows += len(parameters)
            else:
                self.metrics_inserted_rows += 1

    def on_commit(self, _conn: Any) -> None:
        self.commit_count += 1

    def summary(self) -> dict[str, Any]:
        return {
            "sql_statement_count": len(self.statements),
            "sql_operations": self.statements,
            "write_statement_count": self.write_statement_count,
            "metrics_delete_count": self.metrics_delete_count,
            "metrics_insert_count": self.metrics_insert_count,
            "metrics_inserted_rows": self.metrics_inserted_rows,
            "commit_count": self.commit_count,
        }


def classify_sql(upper: str) -> str:
    if upper.startswith("SELECT MAX(UPDATED_AT)") and "PUBLIC_BANK_PLAZA_METRICS" in upper:
        return "metrics_staleness_select"
    if upper.startswith("SELECT S.ID AS SOURCE_ID") and "FROM SUBJECTS S" in upper:
        return "metrics_build_system_select"
    if upper.startswith("SELECT B.ID AS SOURCE_ID") and "FROM USER_QUESTION_BANKS B" in upper:
        return "metrics_build_user_select"
    if upper.startswith("DELETE FROM PUBLIC_BANK_PLAZA_METRICS"):
        return "metrics_delete"
    if upper.startswith("INSERT INTO PUBLIC_BANK_PLAZA_METRICS"):
        return "metrics_insert_batch"
    if "AS TOTAL_BANKS" in upper and "FROM PUBLIC_BANK_PLAZA_METRICS" in upper:
        return "summary_select"
    if upper.startswith("WITH FILTERED AS") and "ACTIVE_USERS_7D" in upper:
        return "summary_active_users_select"
    if upper.startswith("SELECT COUNT(*) AS TOTAL FROM PUBLIC_BANK_PLAZA_METRICS"):
        return "list_count_select"
    if upper.startswith("SELECT M.SOURCE_TYPE") and "FROM PUBLIC_BANK_PLAZA_METRICS M" in upper:
        return "metric_items_select"
    if upper.startswith("SELECT B.ID") and "FROM PLAZA_BOARDS B" in upper:
        return "boards_select"
    if upper.startswith("SELECT BANK_ID") and "FROM PUBLIC_BANK_USERS" in upper:
        return "public_relation_select"
    if upper.startswith("SELECT DISTINCT BSR.BANK_ID"):
        return "shared_relation_select"
    if upper.startswith("SELECT SUBJECT_ID") and "FROM PUBLIC_SUBJECT_USERS" in upper:
        return "system_relation_select"
    if upper.startswith("SELECT M.SOURCE_TYPE") and "JOIN SUBJECTS S" in upper:
        return "system_detail_select"
    if upper.startswith("SELECT M.SOURCE_TYPE") and "FROM USER_QUESTION_BANKS B" in upper:
        return "user_detail_select"
    if upper.startswith("SELECT") or upper.startswith("WITH"):
        return "other_read"
    if upper.startswith("INSERT"):
        return "other_insert"
    if upper.startswith("UPDATE"):
        return "other_update"
    if upper.startswith("DELETE"):
        return "other_delete"
    return "other_sql"


def run_with_probe(engine: Any, callback: Any) -> tuple[Any, DatabaseEffectProbe]:
    from sqlalchemy import event

    probe = DatabaseEffectProbe()
    event.listen(engine, "before_cursor_execute", probe.before_cursor_execute)
    event.listen(engine, "commit", probe.on_commit)
    try:
        return callback(), probe
    finally:
        event.remove(engine, "before_cursor_execute", probe.before_cursor_execute)
        event.remove(engine, "commit", probe.on_commit)


def recorded_request_headers(authorization_label: str | None) -> dict[str, str]:
    headers = {"X-Request-ID": FIXED_REQUEST_ID}
    if authorization_label:
        headers["Authorization"] = authorization_label
    return headers


def live_request_headers(authorization: str | None) -> dict[str, str]:
    headers = {"X-Request-ID": FIXED_REQUEST_ID}
    if authorization:
        headers["Authorization"] = authorization
    return headers


def capture_warm_case(
    *,
    app: Any,
    db: Any,
    engine: Any,
    client: Any,
    case_index: int,
    case_id: str,
    actor: str,
    path: str,
    authorization: str | None = None,
    authorization_label: str | None = None,
) -> dict[str, Any]:
    before = fingerprint_now(app, db)

    def request_once() -> Any:
        return client.get(
            path,
            headers=live_request_headers(authorization),
            environ_overrides={"REMOTE_ADDR": f"127.20.0.{case_index + 1}"},
        )

    response, probe = run_with_probe(engine, request_once)
    after = fingerprint_now(app, db)
    effects = probe.summary()
    side_effect_free = (
        before["sha256"] == after["sha256"]
        and effects["write_statement_count"] == 0
        and effects["commit_count"] == 0
    )
    if not side_effect_free:
        raise AssertionError(f"warm GET mutated business state: {case_id}")

    return {
        "case_id": case_id,
        "phase": "warm",
        "actor": actor,
        "request": {
            "method": "GET",
            "path": path,
            "headers": recorded_request_headers(authorization_label),
        },
        "response": normalized_response(response),
        "database_evidence": {
            "fingerprint_before": before["sha256"],
            "fingerprint_after": after["sha256"],
            "side_effect_free": True,
            "effects": effects,
        },
    }


def deterministic_jwt(app: Any, *, user_id: int, openid: str, session_version: int) -> str:
    import jwt

    issued_at = datetime(2026, 7, 16, 0, 0, 0, tzinfo=timezone.utc)
    payload = {
        "user_id": user_id,
        "openid": openid,
        "session_version": session_version,
        "iat": issued_at,
        "exp": issued_at + timedelta(days=3650),
        "jti": f"phase4a-public-bank-{user_id}",
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    return token.decode("utf-8") if isinstance(token, bytes) else token


def seed_fixture(db: Any) -> dict[str, Any]:
    from app.models.plaza import PlazaBoard, PublicSubjectUser
    from app.models.quiz import UserAnswer
    from app.models.subject import Question, Subject
    from app.models.user import User
    from app.models.user_bank import (
        BankShare,
        BankShareRecord,
        PublicBankUser,
        UserBankAnswer,
        UserBankQuestion,
        UserQuestionBank,
    )

    created = datetime(2026, 7, 1, 8, 0, 0)
    identities = [
        User(
            id=5101,
            username="owner",
            password_hash="synthetic-fixed-password-hash",
            email="owner@phase4a.test",
            email_verified=True,
            has_password_set=True,
            openid="phase4a-openid-5101",
            session_version=11,
            avatar="/uploads/avatars/owner.png",
            created_at=created,
        ),
        User(
            id=5102,
            username="public_viewer",
            password_hash="synthetic-fixed-password-hash",
            email="public_viewer@phase4a.test",
            email_verified=True,
            has_password_set=True,
            openid="phase4a-openid-5102",
            session_version=12,
            avatar="/uploads/avatars/public.png",
            created_at=created,
        ),
        User(
            id=5103,
            username="shared_viewer",
            password_hash="synthetic-fixed-password-hash",
            email="shared_viewer@phase4a.test",
            email_verified=True,
            has_password_set=True,
            openid="phase4a-openid-5103",
            session_version=13,
            avatar="/uploads/avatars/shared.png",
            created_at=created,
        ),
        User(
            id=5104,
            username="both_viewer",
            password_hash="synthetic-fixed-password-hash",
            email="both_viewer@phase4a.test",
            email_verified=True,
            has_password_set=True,
            openid="phase4a-openid-5104",
            session_version=14,
            avatar="/uploads/avatars/both.png",
            created_at=created,
        ),
        User(
            id=5105,
            username="system_viewer",
            password_hash="synthetic-fixed-password-hash",
            email="system_viewer@phase4a.test",
            email_verified=True,
            has_password_set=True,
            openid="phase4a-openid-5105",
            session_version=15,
            avatar="/uploads/avatars/system.png",
            created_at=created,
        ),
        User(
            id=5106,
            username="needle_author",
            password_hash="synthetic-fixed-password-hash",
            email="needle_author@phase4a.test",
            email_verified=True,
            has_password_set=True,
            openid="phase4a-openid-5106",
            session_version=16,
            avatar="/uploads/avatars/needle-author.png",
            created_at=created,
        ),
    ]

    boards = [
        PlazaBoard(
            id=5201,
            slug="alpha",
            name="Alpha Board",
            description=None,
            sort_order=20,
            is_active=True,
            created_at=created,
            updated_at=created,
        ),
        PlazaBoard(
            id=5202,
            slug="beta",
            name="Beta Board",
            description="Beta fixture board",
            sort_order=10,
            is_active=True,
            created_at=created,
            updated_at=created,
        ),
        PlazaBoard(
            id=5203,
            slug="empty-active",
            name="Empty Active Board",
            description="No metrics belong here",
            sort_order=5,
            is_active=True,
            created_at=created,
            updated_at=created,
        ),
        PlazaBoard(
            id=5204,
            slug="inactive",
            name="Inactive Board",
            description="Hidden from board directory",
            sort_order=1,
            is_active=False,
            created_at=created,
            updated_at=created,
        ),
    ]
    db.session.add_all([*identities, *boards])
    db.session.flush()

    subjects = [
        Subject(
            id=5301,
            name="needle",
            description="Exact-name system fixture",
            is_locked=False,
            plaza_board_id=5201,
            is_plaza_featured=True,
            plaza_featured_weight=10,
            plaza_featured_at=datetime(2026, 7, 10, 10, 0, 0),
            created_at=datetime(2026, 7, 10, 10, 0, 0),
        ),
        Subject(
            id=5302,
            name="Needle Prefix System",
            description="System prefix fixture",
            is_locked=False,
            plaza_board_id=5202,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            created_at=datetime(2026, 7, 16, 9, 0, 0),
        ),
        Subject(
            id=5303,
            name="Wildcard Catalog",
            description="Inactive-board fixture",
            is_locked=False,
            plaza_board_id=5204,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            created_at=datetime(2026, 7, 15, 7, 0, 0),
        ),
        Subject(
            id=5304,
            name="Locked System",
            description="Must not enter public metrics",
            is_locked=True,
            plaza_board_id=5201,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            created_at=datetime(2026, 7, 16, 10, 0, 0),
        ),
    ]
    db.session.add_all(subjects)
    db.session.flush()

    questions = [
        Question(
            id=5501,
            subject_id=5301,
            type="single_choice",
            content="System needle question one",
            options="[]",
            answer="A",
            tags="[]",
            difficulty=1,
            source="phase4a-public-bank-golden",
            created_by=5101,
            updated_by=5101,
            created_at=datetime(2026, 7, 10, 10, 5, 0),
            updated_at=datetime(2026, 7, 10, 10, 5, 0),
        ),
        Question(
            id=5502,
            subject_id=5301,
            type="boolean",
            content="System needle question two",
            options="[]",
            answer="true",
            tags="[]",
            difficulty=2,
            source="phase4a-public-bank-golden",
            created_by=5101,
            updated_by=5101,
            created_at=datetime(2026, 7, 10, 10, 6, 0),
            updated_at=datetime(2026, 7, 10, 10, 6, 0),
        ),
        Question(
            id=5503,
            subject_id=5302,
            type="fill",
            content="Prefix question",
            options="[]",
            answer="needle",
            tags="[]",
            difficulty=1,
            source="phase4a-public-bank-golden",
            created_by=5101,
            updated_by=5101,
            created_at=datetime(2026, 7, 16, 9, 5, 0),
            updated_at=datetime(2026, 7, 16, 9, 5, 0),
        ),
        Question(
            id=5504,
            subject_id=5304,
            type="essay",
            content="Locked question",
            options="[]",
            answer="[]",
            tags="[]",
            difficulty=1,
            source="phase4a-public-bank-golden",
            created_by=5101,
            updated_by=5101,
            created_at=datetime(2026, 7, 16, 10, 5, 0),
            updated_at=datetime(2026, 7, 16, 10, 5, 0),
        ),
    ]
    db.session.add_all(questions)

    banks = [
        UserQuestionBank(
            id=5401,
            user_id=5101,
            name="Atlas Needle User",
            description="Owner private description",
            public_description="Public atlas card",
            cover_image="/uploads/bank_covers/atlas.png",
            is_public=True,
            allow_copy=False,
            public_at=datetime(2026, 7, 15, 8, 0, 0),
            question_count=9,
            share_count=2,
            public_use_count=3,
            status=1,
            plaza_board_id=5201,
            is_plaza_featured=True,
            plaza_featured_weight=5,
            plaza_featured_at=datetime(2026, 7, 15, 8, 0, 0),
            join_mode="approval",
            join_note="Synthetic approval required",
            created_at=datetime(2026, 7, 14, 8, 0, 0),
            updated_at=datetime(2026, 7, 15, 8, 0, 0),
        ),
        UserQuestionBank(
            id=5402,
            user_id=5101,
            name="Needle User Prefix",
            description="User prefix fixture",
            public_description="Prefix public card",
            cover_image=None,
            is_public=True,
            allow_copy=True,
            public_at=datetime(2026, 7, 16, 8, 0, 0),
            question_count=5,
            share_count=0,
            public_use_count=0,
            status=1,
            plaza_board_id=5202,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            join_mode="free",
            join_note=None,
            created_at=datetime(2026, 7, 15, 8, 0, 0),
            updated_at=datetime(2026, 7, 16, 8, 0, 0),
        ),
        UserQuestionBank(
            id=5403,
            user_id=5101,
            name="Description Match",
            description="Fallback description",
            public_description="needle guide from description",
            cover_image=None,
            is_public=True,
            allow_copy=True,
            public_at=datetime(2026, 7, 11, 7, 0, 0),
            question_count=12,
            share_count=0,
            public_use_count=0,
            status=1,
            plaza_board_id=5201,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            join_mode="member",
            join_note="Members later",
            created_at=datetime(2026, 7, 10, 7, 0, 0),
            updated_at=datetime(2026, 7, 12, 7, 0, 0),
        ),
        UserQuestionBank(
            id=5404,
            user_id=5106,
            name="Owner Match",
            description="Owner keyword fixture",
            public_description="Owner keyword public card",
            cover_image="/uploads/bank_covers/owner-match.png",
            is_public=True,
            allow_copy=True,
            public_at=datetime(2026, 7, 14, 6, 0, 0),
            question_count=3,
            share_count=0,
            public_use_count=0,
            status=1,
            plaza_board_id=None,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            join_mode="free",
            join_note=None,
            created_at=datetime(2026, 7, 13, 6, 0, 0),
            updated_at=datetime(2026, 7, 14, 6, 0, 0),
        ),
        UserQuestionBank(
            id=5405,
            user_id=5101,
            name="Private Bank",
            description="Excluded private fixture",
            public_description=None,
            cover_image=None,
            is_public=False,
            allow_copy=True,
            public_at=None,
            question_count=99,
            share_count=0,
            public_use_count=0,
            status=1,
            plaza_board_id=5201,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            join_mode="free",
            join_note=None,
            created_at=datetime(2026, 7, 16, 10, 0, 0),
            updated_at=datetime(2026, 7, 16, 10, 0, 0),
        ),
        UserQuestionBank(
            id=5406,
            user_id=5101,
            name="Deleted Public Bank",
            description="Excluded status fixture",
            public_description="Excluded",
            cover_image=None,
            is_public=True,
            allow_copy=True,
            public_at=datetime(2026, 7, 16, 10, 0, 0),
            question_count=88,
            share_count=0,
            public_use_count=0,
            status=0,
            plaza_board_id=5201,
            is_plaza_featured=False,
            plaza_featured_weight=0,
            join_mode="free",
            join_note=None,
            created_at=datetime(2026, 7, 16, 10, 0, 0),
            updated_at=datetime(2026, 7, 16, 10, 0, 0),
        ),
    ]
    db.session.add_all(banks)
    db.session.flush()

    bank_questions = [
        UserBankQuestion(
            id=5701,
            bank_id=5401,
            user_id=5101,
            type="single_choice",
            content="Atlas answer fixture",
            options="[]",
            answer="A",
            tags="[]",
            difficulty=1,
            source_type="custom",
            sort_order=1,
            created_at=datetime(2026, 7, 14, 8, 5, 0),
            updated_at=datetime(2026, 7, 14, 8, 5, 0),
        ),
        UserBankQuestion(
            id=5702,
            bank_id=5403,
            user_id=5101,
            type="boolean",
            content="Description answer fixture",
            options="[]",
            answer="true",
            tags="[]",
            difficulty=1,
            source_type="custom",
            sort_order=1,
            created_at=datetime(2026, 7, 11, 7, 5, 0),
            updated_at=datetime(2026, 7, 11, 7, 5, 0),
        ),
    ]
    db.session.add_all(bank_questions)

    db.session.add_all([
        UserAnswer(
            id=5601,
            user_id=5105,
            question_id=5501,
            user_answer="A",
            is_correct=True,
            created_at=datetime(2026, 7, 16, 10, 0, 0),
        ),
        UserAnswer(
            id=5602,
            user_id=5101,
            question_id=5502,
            user_answer="true",
            is_correct=True,
            created_at=datetime(2026, 7, 11, 10, 0, 0),
        ),
        PublicSubjectUser(
            id=5911,
            subject_id=5301,
            user_id=5105,
            last_access_at=datetime(2026, 7, 16, 9, 30, 0),
            access_count=2,
            created_at=datetime(2026, 7, 15, 9, 30, 0),
        ),
        PublicBankUser(
            id=5901,
            bank_id=5401,
            user_id=5102,
            last_access_at=datetime(2026, 7, 16, 11, 0, 0),
            access_count=3,
            created_at=datetime(2026, 7, 15, 11, 0, 0),
        ),
        PublicBankUser(
            id=5902,
            bank_id=5401,
            user_id=5104,
            last_access_at=datetime(2026, 7, 16, 8, 0, 0),
            access_count=2,
            created_at=datetime(2026, 7, 10, 8, 0, 0),
        ),
        UserBankAnswer(
            id=5801,
            user_id=5102,
            bank_id=5401,
            question_id=5701,
            user_answer="A",
            is_correct=True,
            created_at=datetime(2026, 7, 16, 10, 30, 0),
        ),
        UserBankAnswer(
            id=5802,
            user_id=5101,
            bank_id=5403,
            question_id=5702,
            user_answer="true",
            is_correct=True,
            created_at=datetime(2026, 7, 12, 7, 30, 0),
        ),
    ])

    share = BankShare(
        id=5921,
        bank_id=5401,
        owner_id=5101,
        share_code="phase4a-share-code",
        share_token="phase4a-share-token",
        permission="read",
        expires_at=datetime(2026, 7, 20, 12, 0, 0),
        max_uses=20,
        current_uses=2,
        is_active=True,
        created_at=datetime(2026, 7, 14, 12, 0, 0),
    )
    db.session.add(share)
    db.session.flush()
    db.session.add_all([
        BankShareRecord(
            id=5931,
            share_id=5921,
            bank_id=5401,
            user_id=5103,
            status=1,
            last_access_at=datetime(2026, 7, 16, 9, 0, 0),
            access_count=2,
            created_at=datetime(2026, 7, 15, 9, 0, 0),
        ),
        BankShareRecord(
            id=5932,
            share_id=5921,
            bank_id=5401,
            user_id=5104,
            status=1,
            last_access_at=datetime(2026, 7, 16, 8, 30, 0),
            access_count=2,
            created_at=datetime(2026, 7, 15, 8, 30, 0),
        ),
    ])
    db.session.commit()

    return {
        "fixed_now_bj": FIXED_NOW_BJ.isoformat(sep=" "),
        "identities": [
            {"id": 5101, "role": "owner", "username": "owner", "session_version": 11},
            {"id": 5102, "role": "public", "username": "public_viewer", "session_version": 12},
            {"id": 5103, "role": "shared", "username": "shared_viewer", "session_version": 13},
            {"id": 5104, "role": "both", "username": "both_viewer", "session_version": 14},
            {"id": 5105, "role": "system_joined", "username": "system_viewer", "session_version": 15},
            {"id": 5106, "role": "keyword_owner", "username": "needle_author", "session_version": 16},
        ],
        "boards": [
            {"id": 5201, "slug": "alpha", "sort_order": 20, "is_active": True},
            {"id": 5202, "slug": "beta", "sort_order": 10, "is_active": True},
            {"id": 5203, "slug": "empty-active", "sort_order": 5, "is_active": True},
            {"id": 5204, "slug": "inactive", "sort_order": 1, "is_active": False},
        ],
        "system_subjects": [
            {"id": 5301, "name": "needle", "board_id": 5201, "is_locked": False},
            {"id": 5302, "name": "Needle Prefix System", "board_id": 5202, "is_locked": False},
            {"id": 5303, "name": "Wildcard Catalog", "board_id": 5204, "is_locked": False},
            {"id": 5304, "name": "Locked System", "board_id": 5201, "is_locked": True},
        ],
        "user_banks": [
            {"id": 5401, "name": "Atlas Needle User", "owner_id": 5101, "board_id": 5201, "is_public": True, "status": 1},
            {"id": 5402, "name": "Needle User Prefix", "owner_id": 5101, "board_id": 5202, "is_public": True, "status": 1},
            {"id": 5403, "name": "Description Match", "owner_id": 5101, "board_id": 5201, "is_public": True, "status": 1},
            {"id": 5404, "name": "Owner Match", "owner_id": 5106, "board_id": None, "is_public": True, "status": 1},
            {"id": 5405, "name": "Private Bank", "owner_id": 5101, "board_id": 5201, "is_public": False, "status": 1},
            {"id": 5406, "name": "Deleted Public Bank", "owner_id": 5101, "board_id": 5201, "is_public": True, "status": 0},
        ],
        "relation_seeds": [
            {"actor_id": 5101, "target": "user:5401", "relation": "none", "is_owner": True},
            {"actor_id": 5102, "target": "user:5401", "relation": "public", "is_owner": False},
            {"actor_id": 5103, "target": "user:5401", "relation": "shared", "is_owner": False},
            {"actor_id": 5104, "target": "user:5401", "relation": "both", "is_owner": False},
            {"actor_id": 5105, "target": "system:5301", "relation": "public"},
        ],
        "answer_seeds": {
            "system_question_ids": [5501, 5502, 5503, 5504],
            "system_answer_ids": [5601, 5602],
            "user_bank_question_ids": [5701, 5702],
            "user_bank_answer_ids": [5801, 5802],
        },
        "visible_metric_keys": [
            "system:5301", "system:5302", "system:5303",
            "user_public:5401", "user_public:5402", "user_public:5403",
            "user_public:5404",
        ],
        "excluded_source_keys": ["system:5304", "user_public:5405", "user_public:5406"],
    }


def assert_case_contracts(cases: list[dict[str, Any]]) -> None:
    by_id = {case["case_id"]: case for case in cases}

    def body(case_id: str) -> dict[str, Any]:
        return by_id[case_id]["response"]["body"]

    if body("summary-anonymous")["data"] != {
        "active_users_7d": 4,
        "new_banks_7d": 2,
        "source_breakdown": {"system": 3, "user_public": 4},
        "total_banks": 7,
        "total_boards": 3,
        "total_questions": 32,
    }:
        raise AssertionError("summary fixture no longer freezes the legacy today-as-7d semantics")

    for tab in ("latest", "hot", "active", "featured", "questions"):
        if body(f"list-tab-{tab}")["data"]["tab"] != tab:
            raise AssertionError(f"list tab was not preserved: {tab}")
    available = body("list-tab-questions")["data"]["available_tabs"]
    if "questions" in available:
        raise AssertionError("legacy questions tab unexpectedly became advertised")

    rank_names = [item["name"] for item in body("list-keyword-rank")["data"]["items"]]
    if rank_names[:2] != ["needle", "Needle Prefix System"]:
        raise AssertionError(f"keyword exact/prefix order drifted: {rank_names}")
    if body("list-keyword-wildcard")["data"]["total"] != 7:
        raise AssertionError("legacy LIKE wildcard behavior drifted")

    relation_expectations = {
        "detail-user-owner": ("none", True),
        "detail-user-public": ("public", False),
        "detail-user-shared": ("shared", False),
        "detail-user-both": ("both", False),
    }
    for case_id, (joined_via, is_owner) in relation_expectations.items():
        data = body(case_id)["data"]
        if data["relation"]["joined_via"] != joined_via or data["is_owner"] is not is_owner:
            raise AssertionError(f"relation drifted: {case_id}")

    if body("detail-system-joined")["data"]["relation"]["joined_via"] != "public":
        raise AssertionError("system joined relation drifted")
    hot_items = body("hot-valid-jwt-relations-remain-anonymous")["data"]["items"]
    if any(item["relation"]["is_joined"] for item in hot_items):
        raise AssertionError("hot endpoint unexpectedly started using optional identity")
    if len(body("hot-huge-limit-clamp")["data"]["items"]) != 7:
        raise AssertionError("arbitrary-precision hot limit no longer clamps to ten")

    huge_list = body("list-huge-integer-clamps")["data"]
    if huge_list["page"] != 1 or huge_list["per_page"] != 50:
        raise AssertionError("arbitrary-precision list page/per_page clamps drifted")
    huge_legacy_list = body("legacy-list-huge-integer-clamps")["data"]
    if huge_legacy_list["page"] != 1 or len(huge_legacy_list["banks"]) != 7:
        raise AssertionError("arbitrary-precision legacy list clamps drifted")

    anonymous = body("list-anonymous-relation")
    invalid = body("list-invalid-jwt-relation")
    if anonymous != invalid:
        raise AssertionError("invalid optional JWT no longer falls back to anonymous")

    if by_id["detail-business-404"]["response"]["status"] != 404:
        raise AssertionError("business 404 was not captured")
    if "code" not in body("detail-business-404"):
        raise AssertionError("business 404 lost its legacy code field")
    if "code" in body("detail-converter-404"):
        raise AssertionError("converter 404 unexpectedly gained a code field")
    unicode_equivalents = {
        "detail-unicode-decimal-id": "detail-user-anonymous",
        "card-unicode-decimal-id": "card-system-joined",
    }
    for unicode_case, ascii_case in unicode_equivalents.items():
        response = by_id[unicode_case]["response"]
        if response["status"] != 200 or body(unicode_case) != body(ascii_case):
            raise AssertionError(
                f"Werkzeug Unicode decimal integer conversion drifted: {unicode_case}"
            )
        if response["headers"].get("X-RateLimit-Limit") != "10":
            raise AssertionError(f"Unicode path ID stopped consuming rate limit: {unicode_case}")
    for case_id in ("detail-arbitrary-precision-id", "card-arbitrary-precision-id"):
        response = by_id[case_id]["response"]
        if response["status"] != 500:
            raise AssertionError(f"arbitrary-precision path ID no longer reaches handler: {case_id}")
        if response["headers"]["Content-Type"] != "application/json":
            raise AssertionError(f"arbitrary-precision path error content type drifted: {case_id}")
        if "code" in response["body"] or response["body"].get("payload", object()) is not None:
            raise AssertionError(f"arbitrary-precision path error envelope drifted: {case_id}")
        if response["headers"].get("X-RateLimit-Limit") != "10":
            raise AssertionError(f"arbitrary-precision path ID stopped consuming rate limit: {case_id}")

    partial_user = body("partial-user-detail-id-zero")
    if partial_user["data"]["id"] != 0 or partial_user["data"]["detail_url"] != "/public/banks/card/user/0":
        raise AssertionError("partial user metric legacy id=0 behavior drifted")
    if by_id["partial-system-detail-404"]["response"]["status"] != 404:
        raise AssertionError("partial system metric legacy 404 behavior drifted")
    partial_ids = {
        (item["source_type"], item["id"])
        for item in body("partial-list-omits-sources")["data"]["items"]
    }
    if ("system", 5301) in partial_ids or ("user_public", 5401) in partial_ids:
        raise AssertionError("partial list unexpectedly self-healed missing metrics")


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    output = args.output.resolve()

    with (
        archived_legacy_source(legacy_root) as archived_source,
        tempfile.TemporaryDirectory(
            prefix="ti-java-phase4a-public-bank-golden-"
        ) as data_dir,
        archived_legacy_import_environment(archived_source.root),
    ):
        os.environ["DATA_DIR"] = data_dir
        os.environ["FLASK_ENV"] = "testing"
        os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
        os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
        os.environ.pop("REDIS_URL", None)

        import app as legacy_app
        from app.core.extensions import db
        import app.models as models_package
        from app.modules.user_bank.services import plaza_metrics_service, plaza_query_service
        from sqlalchemy import text

        for imported_module in (
            legacy_app,
            models_package,
            plaza_metrics_service,
            plaza_query_service,
        ):
            assert_module_from_archive(imported_module, archived_source.root)
        logging.disable(logging.CRITICAL)
        legacy_app._start_background_tasks = lambda _app: None
        for module_info in pkgutil.iter_modules(models_package.__path__):
            imported_model = importlib.import_module(f"app.models.{module_info.name}")
            assert_module_from_archive(imported_model, archived_source.root)

        plaza_metrics_service.now_bj = lambda: FIXED_NOW_BJ
        plaza_query_service.now_bj = lambda: FIXED_NOW_BJ

        app = legacy_app.create_app("testing")
        app.config.update(TESTING=True)

        try:
            with app.app_context():
                db.create_all()
                fixture_manifest = seed_fixture(db)
                engine = db.engine
            tokens = {
                role: deterministic_jwt(
                    app,
                    user_id=user_id,
                    openid=f"phase4a-openid-{user_id}",
                    session_version=session_version,
                )
                for role, user_id, session_version in (
                    ("owner", 5101, 11),
                    ("public", 5102, 12),
                    ("shared", 5103, 13),
                    ("both", 5104, 14),
                    ("system", 5105, 15),
                )
            }

            client = app.test_client()
            cold_before = fingerprint_now(app, db)

            def cold_request() -> Any:
                return client.get(
                    "/api/public/banks/summary",
                    headers={"X-Request-ID": FIXED_REQUEST_ID},
                    environ_overrides={"REMOTE_ADDR": "127.20.1.1"},
                )

            cold_response, cold_probe = run_with_probe(engine, cold_request)
            cold_after = fingerprint_now(app, db)
            cold_effects = cold_probe.summary()
            cold_changes = changed_tables(cold_before, cold_after)
            cold_observed = (
                cold_response.status_code == 200
                and cold_changes == ["public_bank_plaza_metrics"]
                and cold_before["source_sha256"] == cold_after["source_sha256"]
                and cold_before["tables"]["public_bank_plaza_metrics"]["row_count"] == 0
                and cold_after["tables"]["public_bank_plaza_metrics"]["row_count"] == 7
                and cold_effects["metrics_delete_count"] == 1
                and cold_effects["metrics_insert_count"] == 1
                and cold_effects["metrics_inserted_rows"] == 7
                and cold_effects["commit_count"] == 1
            )
            if not cold_observed:
                raise AssertionError({
                    "message": "cold GET did not prove the expected metrics transition",
                    "changed_tables": cold_changes,
                    "effects": cold_effects,
                })

            with app.app_context():
                warm_metrics = metrics_snapshot(db)
                db.session.rollback()

            cases: list[dict[str, Any]] = []

            def add(
                case_id: str,
                actor: str,
                path: str,
                role: str | None = None,
                invalid_jwt: bool = False,
            ) -> None:
                authorization = None
                authorization_label = None
                if role:
                    authorization = f"Bearer {tokens[role]}"
                    authorization_label = f"Bearer <redacted-synthetic-jwt:{role}>"
                elif invalid_jwt:
                    authorization = " ".join(("Bearer", "not-a-valid-phase4a-jwt"))
                    authorization_label = "Bearer <invalid-synthetic-jwt>"
                cases.append(capture_warm_case(
                    app=app,
                    db=db,
                    engine=engine,
                    client=client,
                    case_index=len(cases),
                    case_id=case_id,
                    actor=actor,
                    path=path,
                    authorization=authorization,
                    authorization_label=authorization_label,
                ))

            add("summary-anonymous", "anonymous", "/api/public/banks/summary")
            add("summary-board-keyword", "anonymous", "/api/public/banks/summary?board_id=5201&keyword=needle")
            add("boards-anonymous", "anonymous", "/api/public/banks/boards")
            add("boards-keyword", "anonymous", "/api/public/banks/boards?keyword=needle")
            add("hot-anonymous-limit-two", "anonymous", "/api/public/banks/hot?limit=2")
            add(
                "hot-valid-jwt-relations-remain-anonymous",
                "public",
                "/api/public/banks/hot?limit=3",
                role="public",
            )
            add("hot-negative-limit", "anonymous", "/api/public/banks/hot?limit=-7")
            add(
                "hot-huge-limit-clamp",
                "anonymous",
                "/api/public/banks/hot?limit=999999999999999999999999999999999999999999999999",
            )
            add("list-tab-latest", "anonymous", "/api/public/banks/list?tab=latest&page=1&per_page=3")
            add("list-tab-hot", "anonymous", "/api/public/banks/list?tab=hot&page=1&per_page=3")
            add("list-tab-active", "anonymous", "/api/public/banks/list?tab=active&page=1&per_page=3")
            add("list-tab-featured", "anonymous", "/api/public/banks/list?tab=featured&page=1&per_page=50")
            add("list-tab-questions", "anonymous", "/api/public/banks/list?tab=questions&page=1&per_page=3")
            add("list-pagination-page-two", "anonymous", "/api/public/banks/list?tab=latest&page=2&per_page=2")
            add(
                "list-malformed-parameters",
                "anonymous",
                "/api/public/banks/list?tab=UNKNOWN&board_id=0&page=broken&per_page=0",
            )
            add(
                "list-huge-integer-clamps",
                "anonymous",
                "/api/public/banks/list?page=-999999999999999999999999999999999999999999999999"
                "&per_page=999999999999999999999999999999999999999999999999",
            )
            add(
                "list-keyword-rank",
                "anonymous",
                "/api/public/banks/list?keyword=%20%20NeEdLe%20%20&per_page=50",
            )
            add(
                "list-keyword-wildcard",
                "anonymous",
                "/api/public/banks/list?keyword=%25&per_page=50",
            )
            add(
                "list-anonymous-relation",
                "anonymous",
                "/api/public/banks/list?keyword=Atlas%20Needle%20User&per_page=5",
            )
            add(
                "list-public-relation",
                "public",
                "/api/public/banks/list?keyword=Atlas%20Needle%20User&per_page=5",
                role="public",
            )
            add(
                "list-invalid-jwt-relation",
                "invalid_jwt",
                "/api/public/banks/list?keyword=Atlas%20Needle%20User&per_page=5",
                invalid_jwt=True,
            )
            add("legacy-list-newest", "anonymous", "/api/public/banks?page=1&per_page=3")
            add("legacy-list-popular-system", "anonymous", "/api/public/banks?sort=popular&type=system&per_page=50")
            add("legacy-list-questions-user", "anonymous", "/api/public/banks?sort=questions&type=user&per_page=50")
            add(
                "legacy-list-malformed-case-and-type",
                "anonymous",
                "/api/public/banks?sort=POPULAR&type=%20user%20&page=-4&per_page=999",
            )
            add(
                "legacy-list-huge-integer-clamps",
                "anonymous",
                "/api/public/banks?page=-999999999999999999999999999999999999999999999999"
                "&per_page=999999999999999999999999999999999999999999999999",
            )
            add("detail-user-anonymous", "anonymous", "/api/public/banks/5401?type=user")
            add("detail-user-owner", "owner", "/api/public/banks/5401?type=user", role="owner")
            add("detail-user-public", "public", "/api/public/banks/5401?type=user", role="public")
            add("detail-user-shared", "shared", "/api/public/banks/5401?type=user", role="shared")
            add("detail-user-both", "both", "/api/public/banks/5401?type=user", role="both")
            add("detail-system-joined", "system", "/api/public/banks/5301?type=%20system%20", role="system")
            add("card-user-public", "public", "/api/public/banks/card/user/5401", role="public")
            add("card-system-joined", "system", "/api/public/banks/card/system/5301", role="system")
            add("card-uppercase-system-falls-back-user", "anonymous", "/api/public/banks/card/SYSTEM/5401")
            add("detail-business-404", "anonymous", "/api/public/banks/999999?type=user")
            add("card-business-404", "anonymous", "/api/public/banks/card/system/999999")
            add(
                "detail-unicode-decimal-id",
                "anonymous",
                "/api/public/banks/٥٤٠١?type=user",
            )
            add(
                "card-unicode-decimal-id",
                "system",
                "/api/public/banks/card/system/５３０１",
                role="system",
            )
            add(
                "detail-arbitrary-precision-id",
                "anonymous",
                "/api/public/banks/999999999999999999999999999999999999999999999999"
                "?type=user",
            )
            add(
                "card-arbitrary-precision-id",
                "anonymous",
                "/api/public/banks/card/system/"
                "999999999999999999999999999999999999999999999999",
            )
            add("detail-converter-404", "anonymous", "/api/public/banks/-1")
            add("card-converter-404", "anonymous", "/api/public/banks/card/user/-1")

            full_warm_before_partial = fingerprint_now(app, db)
            if any(not case["database_evidence"]["side_effect_free"] for case in cases):
                raise AssertionError("at least one full warm case had a database side effect")

            partial_before = fingerprint_now(app, db)
            with app.app_context():
                db.session.execute(
                    text(
                        "DELETE FROM public_bank_plaza_metrics "
                        "WHERE (source_type = 'system' AND source_id = 5301) "
                        "OR (source_type = 'user_public' AND source_id = 5401)"
                    )
                )
                db.session.commit()
            partial_after_setup = fingerprint_now(app, db)
            partial_setup_changes = changed_tables(partial_before, partial_after_setup)
            if partial_setup_changes != ["public_bank_plaza_metrics"]:
                raise AssertionError(f"partial setup changed unexpected tables: {partial_setup_changes}")
            if partial_after_setup["tables"]["public_bank_plaza_metrics"]["row_count"] != 5:
                raise AssertionError("partial setup did not leave five fresh metric rows")

            partial_case_start = len(cases)
            add("partial-list-omits-sources", "anonymous", "/api/public/banks/list?per_page=50")
            add(
                "partial-user-detail-id-zero",
                "both",
                "/api/public/banks/card/user/5401",
                role="both",
            )
            add(
                "partial-system-detail-404",
                "system",
                "/api/public/banks/card/system/5301",
                role="system",
            )
            partial_cases = cases[partial_case_start:]
            partial_final = fingerprint_now(app, db)
            partial_side_effect_free = (
                partial_after_setup["sha256"] == partial_final["sha256"]
                and all(case["database_evidence"]["side_effect_free"] for case in partial_cases)
            )
            if not partial_side_effect_free:
                raise AssertionError("partial fresh snapshot GETs unexpectedly changed database state")

            assert_case_contracts(cases)
            full_warm_side_effect_free = (
                cold_after["sha256"] == full_warm_before_partial["sha256"]
                and all(case["database_evidence"]["side_effect_free"] for case in cases[:partial_case_start])
            )
            warm_side_effect_free = full_warm_side_effect_free and partial_side_effect_free
            if not warm_side_effect_free:
                raise AssertionError("warm public-bank GETs were not side-effect free")

            document = {
                "contract_id": "ti.phase4a.public-bank-read-goldens",
                "schema_version": 1,
                "captured_at": "2026-07-16",
                "legacy_commit": LEGACY_COMMIT,
                "legacy_source_attestation": archived_source.attestation,
                "capture_tool": "tools/capture_phase4a_public_bank_goldens.py",
                "isolation": (
                    "temporary fixed-commit Git archive plus SQLite database; "
                    "no working-tree imports or persistent local data"
                ),
                "fixed_now_bj": FIXED_NOW_BJ.isoformat(sep=" "),
                "coordination_mode": "metrics Redis unavailable by construction; deterministic process-local lock",
                "normalization": {
                    "request_id": f"fixed to {FIXED_REQUEST_ID}",
                    "authorization": "synthetic JWTs are redacted from recorded requests",
                    "dynamic_headers": [
                        "X-RateLimit-Remaining",
                        "X-RateLimit-Reset",
                        "Retry-After",
                    ],
                    "vary": "tokens sorted",
                    "sqlite_datetimes": "zero microseconds normalized to second precision",
                    "metrics_surrogate_id": "excluded from logical fingerprints and warm_metrics",
                },
                "covered_routes": list(ROUTES),
                "sort_tab_modes": ["latest", "hot", "active", "featured", "questions"],
                "case_count": len(cases),
                "cold_side_effects_observed": cold_observed,
                "warm_side_effect_free": warm_side_effect_free,
                "fixture_manifest": fixture_manifest,
                "cold_get_side_effects": {
                    "request": {
                        "method": "GET",
                        "path": "/api/public/banks/summary",
                        "headers": {"X-Request-ID": FIXED_REQUEST_ID},
                    },
                    "response": normalized_response(cold_response),
                    "fingerprint_before": cold_before,
                    "fingerprint_after": cold_after,
                    "changed_tables": cold_changes,
                    "source_tables_unchanged": cold_before["source_sha256"] == cold_after["source_sha256"],
                    "effects": cold_effects,
                    "observed": True,
                },
                "warm_full_snapshot": {
                    "case_count": partial_case_start,
                    "fingerprint_before": cold_after["sha256"],
                    "fingerprint_after": full_warm_before_partial["sha256"],
                    "side_effect_free": full_warm_side_effect_free,
                },
                "warm_metrics": warm_metrics,
                "partial_fresh_snapshot": {
                    "deleted_metric_keys": ["system:5301", "user_public:5401"],
                    "fingerprint_before_setup": partial_before,
                    "fingerprint_after_setup": partial_after_setup,
                    "setup_changed_tables": partial_setup_changes,
                    "remaining_metric_row_count": 5,
                    "case_ids": [case["case_id"] for case in partial_cases],
                    "fingerprint_after_gets": partial_final["sha256"],
                    "side_effect_free": partial_side_effect_free,
                },
                "cases": cases,
            }

            output.parent.mkdir(parents=True, exist_ok=True)
            rendered = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            output.write_text(rendered, encoding="utf-8")
            output_sha256 = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            print(json.dumps({
                "output": str(output),
                "sha256": output_sha256,
                "case_count": len(cases),
                "cold_side_effects_observed": True,
                "warm_side_effect_free": True,
                "warm_metric_rows": len(warm_metrics),
            }, ensure_ascii=False, sort_keys=True))
        finally:
            with app.app_context():
                db.session.remove()
                db.drop_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
