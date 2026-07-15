#!/usr/bin/env python3
"""Validate the deterministic artifacts produced by refactor phase 0.

The validator deliberately depends only on the Python standard library and
resolves every input relative to ``Ti-Java/`` rather than the caller's current
working directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFACTOR_DIR = PROJECT_ROOT / "docs" / "refactor"
ROUTE_MATRIX = REFACTOR_DIR / "02-route-parity-matrix.csv"
DATA_MATRIX = REFACTOR_DIR / "03-data-ownership.csv"
INVENTORY_SUMMARY = REFACTOR_DIR / "phase0-inventory-summary.json"
PERFORMANCE_SAMPLE = REFACTOR_DIR / "legacy-performance-sample.json"
LEGACY_TEST_BASELINE = REFACTOR_DIR / "legacy-test-baseline.json"
MINIPROGRAM_TYPE_BASELINE = REFACTOR_DIR / "miniprogram-type-baseline.json"
SURFACE_INVENTORY = REFACTOR_DIR / "09-surface-inventory.json"
GOLDEN_DIR = REFACTOR_DIR / "golden-samples"
MINIPROGRAM_ROOT = PROJECT_ROOT / "miniprogram"

REQUIRED_DOCS = (
    "00-current-state.md",
    "01-target-architecture.md",
    "02-route-parity-matrix.csv",
    "03-data-ownership.csv",
    "04-migration-runbook.md",
    "05-progress.md",
)

ROUTE_FIELDS = (
    "route_id",
    "path",
    "methods",
    "endpoint",
    "legacy_module",
    "source",
    "registration_source",
    "registration_kind",
    "decorators",
    "inline_auth_signals",
    "auth_semantics",
    "client_surfaces",
    "client_references",
    "contract_source",
    "target_module",
    "migration_status",
    "compatibility_notes",
)
ROUTE_NONEMPTY_FIELDS = tuple(field for field in ROUTE_FIELDS if field != "client_references")

DATA_FIELDS = (
    "resource_kind",
    "resource_name",
    "legacy_owner",
    "legacy_source",
    "target_owner",
    "persistence_role",
    "constraints_or_pattern",
    "migration_status",
    "notes",
)

EXPECTED_GOLDEN_DOMAINS = {
    "identity",
    "catalog",
    "learning",
    "assessment",
    "community",
    "campus",
    "operations",
}

FORBIDDEN_MINIPROGRAM_NAMES = {
    ".cloudbase",
    ".git",
    ".cache",
    ".ds_store",
    "node_modules",
    "private",
    "log",
    "log.txt",
    "logs",
    "_archived",
    "analyse-data.json",
    "project.private.config.json",
}

SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "credentials",
    "password",
    "password_hash",
    "refresh_token",
    "secret",
    "set_cookie",
    "token",
}
NONDETERMINISTIC_KEYS = {
    "correlation_id",
    "request_id",
    "trace_id",
}
REDACTED_VALUE_MARKERS = ("redacted", "masked", "removed", "test-only")
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
)
SHA256_LINE = re.compile(r"^([0-9a-f]{64})  \./(.+)$")
MIGRATION_STATUS = re.compile(r"^[a-z][a-z0-9_-]*$")
HTTP_METHODS = {"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}
LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
SURFACE_INVENTORY_SHA256 = "3753bb174d95c28fb40d81f7217fdfcf64e8cfc98d8eb79501f5bb0db5ca4886"
ALLOWED_INLINE_AUTH_SIGNALS = {
    "current_user_resolution",
    "forbidden_response_signal",
    "jwt_or_authorization_reference",
    "session_reference",
    "unauthorized_response_signal",
}
ALLOWED_GLOBAL_AUTH_GATES = {
    "global_anonymous_allow_exact",
    "global_anonymous_allow_except_mode_favorites_or_mistakes_returns_401",
    "global_anonymous_allow_fast_path",
    "global_anonymous_allow_notification_route_inline_policy",
    "global_anonymous_allow_only_common_image_extension",
    "global_anonymous_allow_public_bank_prefix",
    "global_anonymous_allow_qr_file_prefix",
    "global_anonymous_allow_returns_zero_counts",
    "global_anonymous_allow_web_login_prefix",
    "global_anonymous_login_redirect",
    "global_anonymous_returns_401",
    "global_record_token_or_bearer_bypass_else_login_redirect",
    "global_session_or_valid_jwt_else_401",
    "global_session_or_valid_jwt_else_backup_error_401",
}
ALLOWED_ROUTE_AUTH = {
    "route_auth:none",
    "route_decorator:jwt",
    "route_decorator:record_token_or_bearer",
    "route_decorator:session",
    "route_decorator:session+admin_role",
    "route_decorator:session+notification_admin_role",
    "route_decorator:session+subject_admin_role",
    "route_decorator:session_or_jwt",
}
ADMIN_AUTH_HOOK = "admin_blueprint_hook:session_or_jwt_plus_role_if_global_gate_passes"
CSRF_AUTH_SEMANTIC = re.compile(
    r"^global_write_csrf_for_(?:DELETE|GET|PATCH|POST|PUT)(?:\+(?:DELETE|GET|PATCH|POST|PUT))*:valid_jwt_or_xhr_required$"
)


class ValidationReport:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passes: list[str] = []

    def error(self, section: str, message: str) -> None:
        self.errors.append(f"{section}: {message}")

    def passed(self, message: str) -> None:
        self.passes.append(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--legacy-root",
        required=True,
        type=Path,
        help="旧 Flask 仓库根目录；仅用于阶段 0 隔离重生成校验",
    )
    parser.add_argument(
        "--legacy-python",
        type=Path,
        help="旧项目 Python；默认使用 <legacy-root>/.venv/bin/python",
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(
    path: Path,
    expected_fields: tuple[str, ...],
    section: str,
    report: ValidationReport,
) -> list[dict[str, str]] | None:
    if not path.is_file():
        report.error(section, f"缺少文件 {display_path(path)}")
        return None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            actual_fields = tuple(reader.fieldnames or ())
            missing_fields = [field for field in expected_fields if field not in actual_fields]
            extra_fields = [field for field in actual_fields if field not in expected_fields]
            if missing_fields:
                report.error(section, f"缺少 CSV 字段: {', '.join(missing_fields)}")
            if extra_fields:
                report.error(section, f"存在未约定 CSV 字段: {', '.join(extra_fields)}")
            rows = list(reader)
    except (OSError, csv.Error, UnicodeError) as exc:
        report.error(section, f"无法读取 {display_path(path)}: {exc}")
        return None
    return rows


def validate_routes(report: ValidationReport) -> None:
    section = "路由矩阵"
    rows = read_csv(ROUTE_MATRIX, ROUTE_FIELDS, section, report)
    if rows is None:
        return

    if len(rows) != 592:
        report.error(section, f"应有 592 条路由，实际为 {len(rows)} 条")

    route_ids: dict[str, int] = {}
    parsed_decorators: dict[int, list[str]] = {}
    parsed_auth: dict[int, list[str]] = {}
    expanded_routes: dict[tuple[str, str], list[str]] = {}
    source_targets: dict[str, set[str]] = {}
    for line_number, row in enumerate(rows, start=2):
        for field in ROUTE_NONEMPTY_FIELDS:
            if not (row.get(field) or "").strip():
                report.error(section, f"第 {line_number} 行字段 {field} 为空")

        route_id = (row.get("route_id") or "").strip()
        if route_id:
            if not re.fullmatch(r"[0-9a-f]{12}", route_id):
                report.error(section, f"第 {line_number} 行 route_id 格式无效: {route_id!r}")
            previous = route_ids.get(route_id)
            if previous is not None:
                report.error(
                    section,
                    f"route_id {route_id!r} 重复，位于第 {previous}、{line_number} 行",
                )
            else:
                route_ids[route_id] = line_number

        methods = {
            method.strip() for method in (row.get("methods") or "").split(",") if method.strip()
        }
        invalid_methods = sorted(methods - HTTP_METHODS)
        if not methods or invalid_methods:
            report.error(
                section,
                f"第 {line_number} 行 HTTP 方法无效: {(row.get('methods') or '')!r}",
            )
        for method in methods:
            expanded_routes.setdefault((row.get("path", ""), method), []).append(
                row.get("endpoint", "")
            )

        try:
            decorators = json.loads(row.get("decorators") or "")
        except json.JSONDecodeError as exc:
            report.error(section, f"第 {line_number} 行 decorators 不是 JSON 数组: {exc}")
            decorators = []
        if not isinstance(decorators, list) or not all(isinstance(item, str) for item in decorators):
            report.error(section, f"第 {line_number} 行 decorators 必须是字符串 JSON 数组")
            decorators = []
        parsed_decorators[line_number] = decorators

        try:
            inline_signals = json.loads(row.get("inline_auth_signals") or "")
        except json.JSONDecodeError as exc:
            report.error(section, f"第 {line_number} 行 inline_auth_signals 不是 JSON 数组: {exc}")
            inline_signals = []
        if not isinstance(inline_signals, list) or not all(
            isinstance(item, str) for item in inline_signals
        ):
            report.error(section, f"第 {line_number} 行 inline_auth_signals 必须是字符串 JSON 数组")
            inline_signals = []
        unknown_inline = sorted(set(inline_signals) - ALLOWED_INLINE_AUTH_SIGNALS)
        if unknown_inline:
            report.error(
                section,
                f"第 {line_number} 行含未知函数内认证信号: {', '.join(unknown_inline)}",
            )

        try:
            auth = json.loads(row.get("auth_semantics") or "")
        except json.JSONDecodeError as exc:
            report.error(section, f"第 {line_number} 行 auth_semantics 不是 JSON 数组: {exc}")
            auth = []
        if not isinstance(auth, list) or not auth or not all(isinstance(item, str) for item in auth):
            report.error(section, f"第 {line_number} 行 auth_semantics 必须是非空字符串 JSON 数组")
            auth = []
        parsed_auth[line_number] = auth
        allowed_auth = ALLOWED_GLOBAL_AUTH_GATES | ALLOWED_ROUTE_AUTH | {ADMIN_AUTH_HOOK}
        unknown_auth = [
            item
            for item in auth
            if item not in allowed_auth and not CSRF_AUTH_SEMANTIC.fullmatch(item)
        ]
        if unknown_auth:
            report.error(
                section,
                f"第 {line_number} 行含未知或含混鉴权语义: {', '.join(unknown_auth)}",
            )
        gates = [item for item in auth if item in ALLOWED_GLOBAL_AUTH_GATES]
        route_auth = [item for item in auth if item in ALLOWED_ROUTE_AUTH]
        if len(gates) != 1:
            report.error(section, f"第 {line_number} 行必须且只能有一个全局认证门禁")
        if len(route_auth) != 1:
            report.error(section, f"第 {line_number} 行必须且只能有一个路由级认证事实")
        expects_admin_hook = (row.get("endpoint") or "").startswith("admin.")
        if (ADMIN_AUTH_HOOK in auth) != expects_admin_hook:
            report.error(section, f"第 {line_number} 行 Admin Blueprint hook 语义与 Endpoint 不一致")

        references = row.get("client_references") or ""
        surfaces = set((row.get("client_surfaces") or "").split(";"))
        if references == "not_found_static_scan":
            if surfaces != {"not_found_static_scan"}:
                report.error(section, f"第 {line_number} 行客户端来源与引用不一致")
        else:
            try:
                parsed_references = json.loads(references)
            except json.JSONDecodeError as exc:
                report.error(section, f"第 {line_number} 行 client_references 不是 JSON 对象: {exc}")
                parsed_references = {}
            if not isinstance(parsed_references, dict) or set(parsed_references) != surfaces:
                report.error(section, f"第 {line_number} 行 client_surfaces 与引用对象键不一致")

        source_targets.setdefault(row.get("source", ""), set()).add(row.get("target_module", ""))

        status = (row.get("migration_status") or "").strip()
        if status and (
            not MIGRATION_STATUS.fullmatch(status)
            or status in {"todo", "tbd", "unknown", "unidentified"}
        ):
            report.error(section, f"第 {line_number} 行迁移状态无效: {status!r}")

    expected_auth_counts = {
        "auth_required": 221,
        "admin_required": 100,
        "login_required": 51,
        "subject_admin_required": 28,
        "session_admin_required": 7,
        "notification_admin_required": 6,
        "jwt_required": 4,
        "_record_auth_required": 2,
    }

    def has_decorator(line_number: int, name: str) -> bool:
        return any(
            item.split("(", 1)[0].rsplit(".", 1)[-1].strip() == name
            for item in parsed_decorators.get(line_number, [])
        )

    for name, expected in expected_auth_counts.items():
        actual = sum(has_decorator(line_number, name) for line_number in range(2, len(rows) + 2))
        if actual != expected:
            report.error(section, f"鉴权装饰器 {name} 应覆盖 {expected} 条，实际为 {actual} 条")
    route_auth_names = tuple(expected_auth_counts)
    no_route_auth = sum(
        not any(has_decorator(line_number, name) for name in route_auth_names)
        for line_number in range(2, len(rows) + 2)
    )
    if no_route_auth != 180:
        report.error(section, f"无路由级鉴权装饰器应为 180 条，实际为 {no_route_auth} 条")

    decorator_to_semantic = {
        "auth_required": "route_decorator:session_or_jwt",
        "admin_required": "route_decorator:session+admin_role",
        "login_required": "route_decorator:session",
        "subject_admin_required": "route_decorator:session+subject_admin_role",
        "session_admin_required": "route_decorator:session+admin_role",
        "notification_admin_required": "route_decorator:session+notification_admin_role",
        "jwt_required": "route_decorator:jwt",
        "_record_auth_required": "route_decorator:record_token_or_bearer",
    }
    for line_number in range(2, len(rows) + 2):
        expected_semantics = {
            semantic
            for decorator, semantic in decorator_to_semantic.items()
            if has_decorator(line_number, decorator)
        }
        actual_semantics = set(parsed_auth.get(line_number, [])) & ALLOWED_ROUTE_AUTH
        if expected_semantics:
            if actual_semantics != expected_semantics:
                report.error(
                    section,
                    f"第 {line_number} 行路由装饰器与认证语义不一致: "
                    f"应为 {sorted(expected_semantics)}，实际为 {sorted(actual_semantics)}",
                )
        elif actual_semantics != {"route_auth:none"}:
            report.error(section, f"第 {line_number} 行无认证装饰器时必须标记 route_auth:none")

    mini_rows = sum(
        "miniprogram" in (row.get("client_surfaces") or "").split(";") for row in rows
    )
    if mini_rows != 102:
        report.error(section, f"应有 102 条注册规则被小程序调用，实际为 {mini_rows} 条")
    if sum(len((row.get("methods") or "").split(",")) for row in rows) != 611:
        report.error(section, "展开后的 path + method 契约必须为 611 个")
    collisions = {
        key: endpoints for key, endpoints in expanded_routes.items() if len(endpoints) > 1
    }
    if set(collisions) != {("/profile", "GET")} or len(collisions.get(("/profile", "GET"), [])) != 2:
        report.error(section, f"唯一 path/method 冲突应为 GET /profile，实际为 {collisions}")
    conflicting_sources = {
        source: targets for source, targets in source_targets.items() if len(targets) > 1
    }
    if conflicting_sources:
        report.error(section, f"同一处理函数出现多个目标模块: {conflicting_sources}")

    overview_rows = [
        row
        for row in rows
        if row.get("path") == "/user/banks/api/overview" and row.get("methods") == "GET"
    ]
    overview_reference = "static/js/my_bank_hub.js:107:fetch_literal"
    if len(overview_rows) != 1 or overview_reference not in overview_rows[0].get(
        "client_references", ""
    ):
        report.error(section, "GET /user/banks/api/overview 必须保留准确的 fetch 调用证据")
    dynamic_delete_rows = [
        row
        for row in rows
        if row.get("path") == "/user/banks/api/<int:bank_id>"
        and row.get("methods") == "DELETE"
    ]
    if any("my_bank_hub.js:107" in row.get("client_references", "") for row in dynamic_delete_rows):
        report.error(section, "GET overview 证据不得跨 fetch 调用误挂到动态 DELETE 路由")

    backup_paths = {
        "/admin/api/backups",
        "/admin/api/settings/backup",
        "/admin/api/settings/backup/test",
    }
    backup_rows = [row for row in rows if row.get("path") in backup_paths]
    if len(backup_rows) != 5 or any(
        "global_session_or_valid_jwt_else_backup_error_401"
        not in json.loads(row.get("auth_semantics") or "[]")
        for row in backup_rows
    ):
        report.error(section, "5 条备份管理规则必须记录专用 JSON 401 全局门禁")

    if (
        len(rows) == 592
        and len(route_ids) == 592
        and not any(error.startswith(f"{section}:") for error in report.errors)
    ):
        report.passed("路由矩阵：592 条路由、route_id 唯一且契约字段完整")


def validate_data_ownership(report: ValidationReport) -> None:
    section = "数据所有权"
    rows = read_csv(DATA_MATRIX, DATA_FIELDS, section, report)
    if rows is None:
        return

    resources: dict[tuple[str, str], int] = {}
    rows_by_resource: dict[tuple[str, str], dict[str, str]] = {}
    table_names: list[str] = []
    migration_index_names: list[str] = []
    target_owners: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        for field in DATA_FIELDS:
            if not (row.get(field) or "").strip():
                report.error(section, f"第 {line_number} 行字段 {field} 为空")

        kind = (row.get("resource_kind") or "").strip()
        name = (row.get("resource_name") or "").strip()
        resource = (kind, name)
        if kind and name:
            previous = resources.get(resource)
            if previous is not None:
                report.error(
                    section,
                    f"资源组合 {kind}/{name} 重复，位于第 {previous}、{line_number} 行",
                )
            else:
                resources[resource] = line_number
                rows_by_resource[resource] = row

        if kind == "table":
            table_names.append(name)
            match = re.search(
                r"(?:^|; )migration_indexes=([^;]+)",
                row.get("constraints_or_pattern", ""),
            )
            if match:
                migration_index_names.extend(match.group(1).split("|"))

        owner = (row.get("target_owner") or "").strip()
        if owner:
            target_owners.add(owner)

        status = (row.get("migration_status") or "").strip()
        if status and (
            not MIGRATION_STATUS.fullmatch(status)
            or status in {"todo", "tbd", "unknown", "unidentified"}
        ):
            report.error(section, f"第 {line_number} 行迁移状态无效: {status!r}")

    application_tables = [name for name in table_names if name != "alembic_version"]
    expected_kind_counts = {
        "table": 70,
        "db_kv_namespace": 15,
        "redis_key": 34,
        "queue": 2,
        "queue_task": 4,
        "scheduled_or_background_task": 6,
        "realtime_channel": 2,
        "object_prefix": 11,
        "external_api": 10,
    }
    actual_kind_counts: dict[str, int] = {}
    for row in rows:
        kind = (row.get("resource_kind") or "").strip()
        actual_kind_counts[kind] = actual_kind_counts.get(kind, 0) + 1
    if len(rows) != 154:
        report.error(section, f"应有 154 个数据/外部资源，实际为 {len(rows)} 个")
    if actual_kind_counts != expected_kind_counts:
        report.error(
            section,
            f"资源类型计数不闭环，应为 {expected_kind_counts}，实际为 {actual_kind_counts}",
        )
    if len(table_names) != 70:
        report.error(section, f"应有 70 条 table 资源，实际为 {len(table_names)} 条")
    if len(application_tables) != 69:
        report.error(section, f"应有 69 张应用表，实际为 {len(application_tables)} 张")
    if table_names.count("alembic_version") != 1:
        report.error(
            section,
            "必须且只能记录一次 Alembic 控制表 alembic_version",
        )
    if len(migration_index_names) != 59 or len(set(migration_index_names)) != 59:
        report.error(
            section,
            "表级 constraints_or_pattern 必须唯一枚举 59 个 Alembic 显式索引",
        )

    required_resources = {
        ("db_kv_namespace", "web_login_token:<token>"),
        ("db_kv_namespace", "bank_quiz_progress_<uid>_..."),
        ("db_kv_namespace", "last_practice_session"),
        ("db_kv_namespace", "user_settings_v1"),
        ("db_kv_namespace", "user_bank_duplicate_check:<bank_id>"),
        ("redis_key", "auth:user_state:<user_id>"),
        ("redis_key", "edu_schedule:upstream_slots"),
        ("queue", "RQ queue saksk"),
        ("queue", "RQ queue default"),
        ("realtime_channel", "sse:events"),
        ("object_prefix", "uploads/user_bank_question_images/"),
        ("external_api", "browser export extension: Chaoxing/PTA/Yuketang"),
    }
    missing_resources = sorted(required_resources - set(resources))
    if missing_resources:
        report.error(
            section,
            "缺少关键资源: " + ", ".join(f"{kind}/{name}" for kind, name in missing_resources),
        )

    expected_legacy_owners = {
        ("table", "interaction_notifications"): "forum",
        ("table", "plaza_boards"): "user_bank",
        ("table", "public_bank_plaza_metrics"): "user_bank",
        ("table", "public_subject_users"): "user_bank",
    }
    for resource, expected_owner in expected_legacy_owners.items():
        row = rows_by_resource.get(resource)
        if row is not None and row.get("legacy_owner") != expected_owner:
            report.error(
                section,
                f"{resource[1]} 的旧 owner 应为 {expected_owner!r}，实际为 {row.get('legacy_owner')!r}",
            )

    for name in ("question_tags_v1", "bank_<bank_id>_tags"):
        row = rows_by_resource.get(("db_kv_namespace", name))
        if row is not None and row.get("persistence_role") != "legacy_compatibility_state":
            report.error(section, f"{name} 必须标记为 legacy_compatibility_state")

    forum_posts = rows_by_resource.get(("table", "forum_posts"))
    if forum_posts is not None:
        constraints = forum_posts.get("constraints_or_pattern", "")
        source = forum_posts.get("legacy_source", "")
        if not all(
            marker in constraints
            for marker in ("columns=27", "physical_columns=28", "search_vector")
        ):
            report.error(section, "forum_posts 必须闭合 27 ORM 列与 28 物理列差异")
        if "d1e2f3a4b5c6_add_forum_fulltext_search.py" not in source:
            report.error(section, "forum_posts 必须引用 generated column 的 ALTER 迁移")

    if (
        len(resources) == len(rows)
        and len(table_names) == 70
        and len(application_tables) == 69
        and not any(error.startswith(f"{section}:") for error in report.errors)
    ):
        report.passed(
            f"数据所有权：69 张应用表 + alembic_version，{len(rows)} 个资源组合唯一，"
            f"覆盖 {len(target_owners)} 个目标 owner"
        )


def validate_inventory_summary(report: ValidationReport) -> None:
    section = "盘点摘要"
    summary = load_json(INVENTORY_SUMMARY, section, report)
    if not isinstance(summary, dict):
        if summary is not None:
            report.error(section, "phase0-inventory-summary.json 顶层必须是对象")
        return
    expected = {
        "registered_url_rules": 592,
        "route_identity_sha256": "781c3c4bcf524988ef97738780b1e0b0c203216bf83b8b12ba7c8ce84c5c08b5",
        "route_contract_sha256": "362c620798fbcb7ceed293cf8c46500e4bd382dce6afabc4b5e62f4ca629b7e8",
        "source_route_decorators": 538,
        "registered_decorator_rules": 528,
        "unregistered_route_decorators": 10,
        "route_registration_kinds": {
            "application_compatibility_alias": 9,
            "application_decorator": 1,
            "blueprint_compatibility_alias": 54,
            "blueprint_decorator": 527,
            "framework_static": 1,
        },
        "miniprogram_call_expressions": 116,
        "miniprogram_unique_calls": 113,
        "miniprogram_registered_rules": 102,
        "data_resources": 154,
        "data_resource_identity_sha256": "445dd5765bb14830d545033ce478f78cfc4f2f6fd70803408c7924fe68fa492d",
        "data_contract_sha256": "46f61947aa4b58fca9ee576ba0e6345d47229fa8b5c6a324aa19e48673f7e6df",
        "resource_kinds": {
            "db_kv_namespace": 15,
            "external_api": 10,
            "object_prefix": 11,
            "queue": 2,
            "queue_task": 4,
            "realtime_channel": 2,
            "redis_key": 34,
            "scheduled_or_background_task": 6,
            "table": 70,
        },
        "tables": 70,
        "application_tables": 69,
        "orm_application_columns": 615,
        "migration_only_application_columns": 1,
        "migration_tooling_columns": 1,
        "known_physical_columns": 617,
        "package_discovered_tables": 67,
        "all_model_modules_tables": 69,
        "alembic_head": "f5b6c7d8e9f0",
        "alembic_revisions": 22,
        "migration_explicit_indexes": 59,
        "external_resources": 84,
    }
    for key, expected_value in expected.items():
        actual = summary.get(key)
        if actual != expected_value:
            report.error(section, f"{key} 应为 {expected_value!r}，实际为 {actual!r}")
    expected_unregistered = {
        ("app/modules/admin/routes/api_components/popups.py:18", "/popups", ("GET",)),
        ("app/modules/admin/routes/api_components/popups.py:38", "/popups", ("POST",)),
        ("app/modules/admin/routes/api_components/popups.py:80", "/popups/<int:pid>", ("GET",)),
        ("app/modules/admin/routes/api_components/popups.py:100", "/popups/<int:pid>", ("PUT",)),
        ("app/modules/admin/routes/api_components/popups.py:162", "/popups/<int:pid>", ("DELETE",)),
        ("app/modules/admin/routes/api_components/popups.py:190", "/popups/stats", ("GET",)),
        ("app/modules/admin/routes/api_components/popups.py:214", "/popups/<int:pid>/stats", ("GET",)),
        ("app/modules/popups/routes/api.py:18", "/popups/active", ("GET",)),
        ("app/modules/popups/routes/api.py:45", "/popups/<int:popup_id>/dismiss", ("POST",)),
        ("app/modules/popups/routes/api.py:74", "/popups/<int:popup_id>/view", ("POST",)),
    }
    raw_unregistered = summary.get("unregistered_route_definitions")
    actual_unregistered: set[tuple[str, str, tuple[str, ...]]] = set()
    if isinstance(raw_unregistered, list):
        for item in raw_unregistered:
            if isinstance(item, dict) and isinstance(item.get("methods"), list):
                actual_unregistered.add(
                    (
                        str(item.get("source", "")),
                        str(item.get("declared_path", "")),
                        tuple(str(method) for method in item["methods"]),
                    )
                )
    if actual_unregistered != expected_unregistered:
        report.error(
            section,
            "10 个未注册 popup 定义与静态源码闭环不一致",
        )
    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("盘点摘要：路由、小程序、模型、Alembic、索引和资源计数闭环")


def validate_performance_sample(report: ValidationReport) -> None:
    section = "性能与 SQL 样本"
    sample = load_json(PERFORMANCE_SAMPLE, section, report)
    if not isinstance(sample, dict):
        if sample is not None:
            report.error(section, "legacy-performance-sample.json 顶层必须是对象")
        return
    safety = str(sample.get("safety", ""))
    if "No production" not in safety or "persistent local database" not in safety:
        report.error(section, "必须声明未访问生产或本地持久数据库")
    startup = sample.get("startup")
    if not isinstance(startup, dict):
        report.error(section, "缺少 startup 对象")
    else:
        for key in (
            "legacy_import_and_create_app_ms",
            "rss_before_import_mib",
            "rss_after_create_app_mib",
            "rss_delta_mib",
        ):
            value = startup.get(key)
            if not isinstance(value, (int, float)) or value < 0:
                report.error(section, f"startup.{key} 必须是非负数")
    environment = sample.get("environment")
    samples_per_endpoint = (
        environment.get("samples_per_endpoint") if isinstance(environment, dict) else None
    )
    if not isinstance(samples_per_endpoint, int) or samples_per_endpoint < 5:
        report.error(section, "每个入口必须至少记录 5 个性能样本")
    if not isinstance(environment, dict) or not str(environment.get("cache_state", "")).strip():
        report.error(section, "必须记录缓存预热/冷暖状态")
    requests = sample.get("requests")
    expected_paths = {
        "/api/ping",
        "/api/public/banks/summary",
        "/api/questions/count",
        "/hub",
    }
    if not isinstance(requests, dict) or set(requests) != expected_paths:
        report.error(section, "请求样本入口集合不完整")
    else:
        expected_sql_counts = {
            "/api/ping": 0,
            "/api/public/banks/summary": 7,
            "/api/questions/count": 1,
            "/hub": 2,
        }
        for path, measurement in requests.items():
            if not isinstance(measurement, dict):
                report.error(section, f"{path} 测量值必须是对象")
                continue
            statuses = measurement.get("statuses")
            samples = measurement.get("samples")
            if samples != samples_per_endpoint or not isinstance(statuses, list) or len(statuses) != samples or any(
                status != 200 for status in statuses
            ):
                report.error(section, f"{path} 状态样本必须全部为 HTTP 200")
            for key in (
                "latency_ms_median",
                "latency_ms_p95",
                "sql_count_min",
                "sql_count_max",
                "sql_duration_ms_median",
            ):
                value = measurement.get(key)
                if not isinstance(value, (int, float)) or value < 0:
                    report.error(section, f"{path}.{key} 必须是非负数")
            expected_sql = expected_sql_counts[path]
            if measurement.get("sql_count_min") != expected_sql or measurement.get(
                "sql_count_max"
            ) != expected_sql:
                report.error(section, f"{path} 的空夹具 SQL 次数应稳定为 {expected_sql}")
    limitations = sample.get("limitations")
    if not isinstance(limitations, list) or len(limitations) < 2:
        report.error(section, "必须记录至少两条性能样本限制")
    else:
        rendered_limitations = " ".join(str(item) for item in limitations).lower()
        if "sqlite" not in rendered_limitations or "phase-9" not in rendered_limitations:
            report.error(section, "限制必须明确 SQLite 空夹具和非阶段 9 验收基线")
    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("性能与 SQL 样本：隔离启动 RSS/耗时及 4 个入口 SQL 次数证据完整")


def validate_legacy_test_baseline(report: ValidationReport) -> None:
    section = "旧测试回归白名单"
    baseline = load_json(LEGACY_TEST_BASELINE, section, report)
    if not isinstance(baseline, dict):
        if baseline is not None:
            report.error(section, "legacy-test-baseline.json 顶层必须是对象")
        return
    expected_counts = {
        "collected": 659,
        "passed": 654,
        "failed": 2,
        "skipped": 3,
        "errors": 0,
    }
    if baseline.get("expected") != expected_counts:
        report.error(section, f"测试计数应为 {expected_counts}")
    if baseline.get("warning_count_range") != [364, 366]:
        report.error(section, "warning_count_range 应固定当前 364–366 波动窗口")
    failures = baseline.get("allowed_failures")
    actual_ids: set[tuple[str, str]] = set()
    if isinstance(failures, list):
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            actual_ids.add((str(failure.get("file", "")), str(failure.get("test_name", ""))))
            for field in (
                "classification",
                "expected_message_fragment",
                "isolated_result",
                "signature",
            ):
                if not str(failure.get(field, "")).strip():
                    report.error(section, f"失败项缺少 {field}")
    expected_ids = {
        (
            "tests/test_rate_limit_policy.py",
            "test_production_policy_expands_decorator_and_manual_limits",
        ),
        (
            "tests/test_user_bank_document_export.py",
            "test_export_pdf_returns_pdf_download",
        ),
    }
    if actual_ids != expected_ids:
        report.error(section, f"允许失败集合不一致: {sorted(actual_ids)}")
    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("旧测试回归白名单：659 项计数与 2 个允许失败 nodeid 已结构化固定")


def validate_miniprogram_type_baseline(report: ValidationReport) -> None:
    section = "小程序类型错误基线"
    baseline = load_json(MINIPROGRAM_TYPE_BASELINE, section, report)
    if not isinstance(baseline, dict):
        if baseline is not None:
            report.error(section, "miniprogram-type-baseline.json 顶层必须是对象")
        return
    legacy = baseline.get("legacy")
    controlled = baseline.get("controlled_copy")
    difference = baseline.get("intentional_difference")
    if baseline.get("typescript_exit_code") != 2:
        report.error(section, "TypeScript 既有退出码应为 2")
    if not isinstance(legacy, dict) or legacy.get("errors") != 392:
        report.error(section, "旧小程序错误数应为 392")
    if not isinstance(controlled, dict) or controlled.get("errors") != 386:
        report.error(section, "受控副本错误数应为 386")
    if (
        not isinstance(difference, dict)
        or difference.get("errors") != 6
        or difference.get("code") != "TS2393"
        or difference.get("source_prefix") != "_archived/"
    ):
        report.error(section, "6 个差异必须且只能来自已排除 _archived 的 TS2393")
    legacy_codes = set(legacy.get("codes", [])) if isinstance(legacy, dict) else set()
    controlled_codes = set(controlled.get("codes", [])) if isinstance(controlled, dict) else set()
    if legacy_codes - controlled_codes != {"TS2393"}:
        report.error(section, "受控副本与旧树的错误代码差异必须仅为 TS2393")
    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("小程序类型错误基线：旧树 392、受控副本 386，差异仅为 6 个归档 TS2393")


def normalized_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def is_redacted(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return any(marker in normalized for marker in REDACTED_VALUE_MARKERS)


def is_sensitive_key(key_name: str) -> bool:
    return key_name in SENSITIVE_KEYS or key_name.endswith(
        ("_api_key", "_cookie", "_password", "_secret", "_token")
    )


def find_sensitive_values(value: Any, location: str = "$") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = normalized_key(key)
            child_location = f"{location}.{key}"
            if key_name in NONDETERMINISTIC_KEYS:
                yield f"{child_location} 含动态请求标识，黄金样本不可确定复现"
            if is_sensitive_key(key_name) and not is_redacted(child):
                yield f"{child_location} 含未脱敏敏感值"
            yield from find_sensitive_values(child, child_location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from find_sensitive_values(child, f"{location}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                yield f"{location} 命中疑似密钥/凭据模式"
                break


def load_json(path: Path, section: str, report: ValidationReport) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.error(section, f"无法读取 {display_path(path)}: {exc}")
        return None


def validate_surface_inventory(report: ValidationReport) -> None:
    section = "页面与客户端入口"
    if not SURFACE_INVENTORY.is_file():
        report.error(section, f"缺少文件 {display_path(SURFACE_INVENTORY)}")
        return
    if sha256_file(SURFACE_INVENTORY) != SURFACE_INVENTORY_SHA256:
        report.error(section, "09-surface-inventory.json 的固定契约 SHA-256 不匹配")

    inventory = load_json(SURFACE_INVENTORY, section, report)
    if not isinstance(inventory, dict):
        if inventory is not None:
            report.error(section, "09-surface-inventory.json 顶层必须是对象")
        return
    if inventory.get("schema_version") != 1 or inventory.get("legacy_commit") != LEGACY_COMMIT:
        report.error(section, "清单必须固定 schema_version=1 与旧来源提交")
    if inventory.get("inputs") != {
        "legacy_baseline": ".",
        "miniprogram_controlled_copy": "Ti-Java/miniprogram",
        "miniprogram_original_source": "miniprogram-1",
    }:
        report.error(section, "页面清单输入边界必须是旧根与 Ti-Java 受控小程序副本")

    expected_summary = {
        "admin_runtime_entry_count": 181,
        "admin_source_only_entry_count": 7,
        "html_page_heuristic_count": 128,
        "html_partial_heuristic_count": 181,
        "html_template_count": 309,
        "journey_count": 14,
        "miniprogram_declared_page_count": 61,
        "miniprogram_main_page_count": 50,
        "miniprogram_source_only_page_count": 7,
        "miniprogram_subpackage_page_count": 11,
        "runtime_expanded_method_count": 611,
        "runtime_route_rule_count": 592,
        "runtime_route_template_mapping_status": {
            "candidate_literals_found": 12,
            "literal_found": 91,
            "no_render_template_call_found": 489,
        },
        "source_dynamic_render_template_call_count": 3,
        "source_literal_render_template_call_count": 101,
        "source_render_template_call_count": 104,
    }
    if inventory.get("summary") != expected_summary:
        report.error(section, "页面、路由、模板、小程序、后台与旅程摘要计数漂移")

    templates = inventory.get("templates")
    if not isinstance(templates, list) or len(templates) != 309:
        report.error(section, "templates 必须完整列出 309 个 HTML 模板")
    else:
        paths = [str(item.get("relative_path", "")) for item in templates if isinstance(item, dict)]
        classes = Counter(
            str(item.get("classification", "")) for item in templates if isinstance(item, dict)
        )
        if len(paths) != 309 or len(set(paths)) != 309 or any(
            not path.startswith("app/") or not path.endswith(".html") for path in paths
        ):
            report.error(section, "HTML 模板路径必须唯一、为 app/ 下相对路径且以 .html 结尾")
        if classes != {"page": 128, "partial": 181}:
            report.error(section, f"模板启发式分类应为 128 page + 181 partial，实际 {dict(classes)}")

    routes = inventory.get("runtime_routes")
    surface_contracts: set[tuple[str, frozenset[str], str]] = set()
    if not isinstance(routes, list) or len(routes) != 592:
        report.error(section, "runtime_routes 必须完整列出 592 条运行时规则")
    else:
        route_ids: list[str] = []
        expanded_methods = 0
        for route in routes:
            if not isinstance(route, dict) or not isinstance(route.get("methods"), list):
                report.error(section, "runtime_routes 中存在非结构化路由")
                continue
            methods = tuple(str(method) for method in route["methods"])
            route_ids.append(str(route.get("route_id", "")))
            expanded_methods += len(methods)
            surface_contracts.add(
                (str(route.get("path", "")), frozenset(methods), str(route.get("endpoint", "")))
            )
        if len(route_ids) != 592 or len(set(route_ids)) != 592 or expanded_methods != 611:
            report.error(section, "页面清单路由 ID 必须唯一，方法展开数必须为 611")

        try:
            with ROUTE_MATRIX.open("r", encoding="utf-8", newline="") as handle:
                matrix_rows = list(csv.DictReader(handle))
        except (OSError, UnicodeError, csv.Error) as exc:
            report.error(section, f"无法与路由矩阵交叉校验: {exc}")
        else:
            matrix_contracts = {
                (
                    str(row.get("path", "")),
                    frozenset(method for method in str(row.get("methods", "")).split(",") if method),
                    str(row.get("endpoint", "")),
                )
                for row in matrix_rows
            }
            if surface_contracts != matrix_contracts:
                report.error(section, "09 清单与 02 路由矩阵的 path/method/endpoint 集合不一致")

    render_calls = inventory.get("source_render_template_calls")
    if not isinstance(render_calls, list) or len(render_calls) != 104:
        report.error(section, "必须列出 104 个 Flask render_template 调用")
    elif Counter(str(call.get("resolution", "")) for call in render_calls if isinstance(call, dict)) != {
        "literal": 101,
        "dynamic": 3,
    }:
        report.error(section, "render_template 解析应为 101 literal + 3 dynamic")
    if inventory.get("unresolved_runtime_template_literals") != []:
        report.error(section, "运行时模板字面量必须全部解析")

    pages = inventory.get("miniprogram_pages")
    if not isinstance(pages, list) or len(pages) != 61:
        report.error(section, "miniprogram_pages 必须完整列出 61 个声明页面")
    else:
        full_paths: list[str] = []
        kinds: Counter[str] = Counter()
        for page in pages:
            if not isinstance(page, dict):
                report.error(section, "miniprogram_pages 中存在非对象条目")
                continue
            full_paths.append(str(page.get("full_path", "")))
            kinds[str(page.get("package_kind", ""))] += 1
            original_files = page.get("implementation_files")
            controlled_files = page.get("controlled_copy_files")
            if (
                not isinstance(original_files, list)
                or not isinstance(controlled_files, list)
                or not original_files
                or len(original_files) != len(controlled_files)
            ):
                report.error(section, f"小程序页面缺少受控实现文件: {page.get('full_path')}")
                continue
            for controlled in controlled_files:
                controlled_path = str(controlled)
                if not controlled_path.startswith("Ti-Java/miniprogram/") or not (
                    PROJECT_ROOT.parent / controlled_path
                ).is_file():
                    report.error(section, f"受控小程序证据路径无效: {controlled_path}")
        if len(full_paths) != 61 or len(set(full_paths)) != 61:
            report.error(section, "61 个小程序声明页面路径必须唯一")
        if kinds != {"main": 50, "subpackage": 11}:
            report.error(section, f"小程序页面应为 50 主包 + 11 分包，实际 {dict(kinds)}")

    source_only_pages = inventory.get("miniprogram_source_only_pages")
    expected_source_only_paths = {
        "pages/data-ai-v2/data-ai-v2",
        "pages/data-banks-v2/data-banks-v2",
        "pages/data-trend-v2/data-trend-v2",
        "pages/data-web-v2/data-web-v2",
        "pages/history-v2/history-v2",
        "pages/settings-hotkeys-v2/settings-hotkeys-v2",
        "pages/settings-v2/settings-v2",
    }
    if not isinstance(source_only_pages, list) or len(source_only_pages) != 7:
        report.error(section, "必须列出 7 套 app.json 未声明的完整小程序页源码")
    else:
        actual_source_only_paths = {
            str(page.get("full_path", "")) for page in source_only_pages if isinstance(page, dict)
        }
        if actual_source_only_paths != expected_source_only_paths:
            report.error(section, "7 套小程序 source-only 页面路径集合漂移")
        referenced_source_only = {
            "pages/data-ai-v2/data-ai-v2",
            "pages/data-banks-v2/data-banks-v2",
            "pages/data-trend-v2/data-trend-v2",
            "pages/history-v2/history-v2",
        }
        for page in source_only_pages:
            if not isinstance(page, dict):
                report.error(section, "miniprogram_source_only_pages 中存在非对象条目")
                continue
            controlled_files = page.get("controlled_copy_files")
            if (
                page.get("declaration_status") != "source_only_not_in_app_json"
                or not isinstance(controlled_files, list)
                or len(controlled_files) < 3
            ):
                report.error(section, f"source-only 页面证据不完整: {page.get('full_path')}")
                continue
            for controlled in controlled_files:
                controlled_path = str(controlled)
                if not controlled_path.startswith("Ti-Java/miniprogram/") or not (
                    PROJECT_ROOT.parent / controlled_path
                ).is_file():
                    report.error(section, f"source-only 受控路径无效: {controlled_path}")
            if page.get("full_path") in referenced_source_only and not page.get("source_references"):
                report.error(section, f"仍被导航源码引用的 source-only 页面缺证据: {page.get('full_path')}")

    admin = inventory.get("admin_entries")
    if not isinstance(admin, dict):
        report.error(section, "缺少结构化 admin_entries")
    else:
        expected_admin_counts = {
            "runtime_entry_count": 181,
            "runtime_web_entry_count": 30,
            "runtime_api_entry_count": 151,
            "source_declaration_count": 188,
            "source_only_declaration_count": 7,
        }
        for key, value in expected_admin_counts.items():
            if admin.get(key) != value:
                report.error(section, f"admin_entries.{key} 应为 {value}")
        runtime_entries = admin.get("runtime_entries")
        source_declarations = admin.get("source_declared_entries")
        source_only = admin.get("source_only_entries")
        if not isinstance(runtime_entries, list) or len(runtime_entries) != 181:
            report.error(section, "必须列出 181 个后台运行时入口")
        if not isinstance(source_declarations, list) or len(source_declarations) != 188:
            report.error(section, "必须列出 188 个后台源码声明")
        if (
            not isinstance(source_only, list)
            or len(source_only) != 7
            or any(item.get("registered") is not False for item in source_only if isinstance(item, dict))
        ):
            report.error(section, "必须显式保留 7 个未注册后台 popup 声明")

    expected_journeys = [
        "authentication",
        "home_and_catalog",
        "practice_and_answer",
        "learning_data",
        "exam",
        "personal_bank",
        "public_bank",
        "community",
        "chat",
        "campus",
        "coding",
        "notifications",
        "settings_and_profile",
        "administration",
    ]
    journeys = inventory.get("key_journeys")
    if (
        not isinstance(journeys, list)
        or [journey.get("journey_id") for journey in journeys if isinstance(journey, dict)]
        != expected_journeys
        or any(not isinstance(journey.get("evidence"), list) or len(journey["evidence"]) < 2 for journey in journeys if isinstance(journey, dict))
    ):
        report.error(section, "14 条关键旅程及其路由/小程序证据必须完整")

    for issue in find_sensitive_values(inventory):
        report.error(section, issue)
    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed(
            "页面与客户端入口：309 模板、592 路由、61+7 小程序页、181 后台入口与 14 旅程闭环"
        )


def validate_golden_samples(report: ValidationReport) -> None:
    section = "黄金样本"
    manifest_path = GOLDEN_DIR / "manifest.json"
    if not manifest_path.is_file():
        report.error(section, f"缺少文件 {display_path(manifest_path)}")
        return

    manifest = load_json(manifest_path, section, report)
    if not isinstance(manifest, dict):
        if manifest is not None:
            report.error(section, "manifest.json 顶层必须是对象")
        return

    sample_names = manifest.get("samples")
    if not isinstance(sample_names, list) or not all(
        isinstance(name, str) and name for name in sample_names
    ):
        report.error(section, "manifest.samples 必须是非空文件名数组")
        return
    if len(sample_names) != 7 or len(set(sample_names)) != 7:
        report.error(section, f"manifest 应唯一列出 7 个样本，实际为 {len(sample_names)} 个")
    if manifest.get("all_success") is not True:
        report.error(section, "manifest.all_success 必须为 true")
    if not str(manifest.get("isolation", "")).strip():
        report.error(section, "manifest.isolation 不能为空")
    if not str(manifest.get("redaction", "")).strip():
        report.error(section, "manifest.redaction 不能为空")

    actual_json_names = {
        path.name for path in GOLDEN_DIR.glob("*.json") if path.name != "manifest.json"
    }
    listed_names = set(sample_names)
    if listed_names != actual_json_names:
        missing = sorted(listed_names - actual_json_names)
        unlisted = sorted(actual_json_names - listed_names)
        if missing:
            report.error(section, f"manifest 中样本文件不存在: {', '.join(missing)}")
        if unlisted:
            report.error(section, f"存在 manifest 未列出的样本: {', '.join(unlisted)}")

    domains: set[str] = set()
    learning_contract_valid = False
    for name in sample_names:
        if Path(name).name != name or not name.endswith(".json"):
            report.error(section, f"manifest 样本名必须是目录内 JSON 文件名: {name!r}")
            continue
        path = GOLDEN_DIR / name
        if not path.is_file():
            continue
        sample = load_json(path, section, report)
        if not isinstance(sample, dict):
            if sample is not None:
                report.error(section, f"{name} 顶层必须是对象")
            continue

        domain = sample.get("domain")
        if not isinstance(domain, str) or not domain:
            report.error(section, f"{name} 缺少 domain")
        elif domain in domains:
            report.error(section, f"领域 {domain!r} 出现重复样本")
        else:
            domains.add(domain)

        if domain == "learning":
            request_contract = sample.get("request")
            postconditions = sample.get("postconditions")
            latest_answer = (
                postconditions.get("latest_answer")
                if isinstance(postconditions, dict)
                else None
            )
            learning_contract_valid = bool(
                isinstance(request_contract, dict)
                and request_contract.get("method") == "POST"
                and request_contract.get("path") == "/api/record_result"
                and isinstance(request_contract.get("json"), dict)
                and isinstance(postconditions, dict)
                and postconditions.get("user_answers_count") == 1
                and isinstance(latest_answer, dict)
                and latest_answer.get("is_correct") is True
                and latest_answer.get("user_answer") is None
                and postconditions.get("mistakes_count") == 0
            )
            if not learning_contract_valid:
                report.error(
                    section,
                    f"{name} 必须覆盖 POST /api/record_result 并证明正确答题落入 user_answers",
                )

        response = sample.get("response")
        status = response.get("status") if isinstance(response, dict) else None
        if status != 200:
            report.error(section, f"{name} 响应状态应为 200，实际为 {status!r}")

        for issue in find_sensitive_values(sample):
            report.error(section, f"{name}: {issue}")

    if domains != EXPECTED_GOLDEN_DOMAINS:
        missing_domains = sorted(EXPECTED_GOLDEN_DOMAINS - domains)
        extra_domains = sorted(domains - EXPECTED_GOLDEN_DOMAINS)
        if missing_domains:
            report.error(section, f"缺少领域样本: {', '.join(missing_domains)}")
        if extra_domains:
            report.error(section, f"存在未约定领域样本: {', '.join(extra_domains)}")

    if (
        len(sample_names) == 7
        and len(listed_names) == 7
        and listed_names == actual_json_names
        and domains == EXPECTED_GOLDEN_DOMAINS
        and learning_contract_valid
        and manifest.get("all_success") is True
        and not any(error.startswith(f"{section}:") for error in report.errors)
    ):
        report.passed(
            "黄金样本：7 个领域与 manifest 一致，真实答题写入已验证，全部 HTTP 200 且已脱敏"
        )


def iter_miniprogram_entries(root: Path) -> Iterable[Path]:
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_root)
        directory_names[:] = sorted(directory_names)
        for name in directory_names:
            yield current / name
        for name in sorted(file_names):
            yield current / name


def validate_miniprogram_tree(report: ValidationReport) -> None:
    section = "小程序快照"
    if not MINIPROGRAM_ROOT.is_dir():
        report.error(section, f"缺少目录 {display_path(MINIPROGRAM_ROOT)}")
        return
    if MINIPROGRAM_ROOT.is_symlink():
        report.error(section, f"小程序根目录不得是符号链接: {display_path(MINIPROGRAM_ROOT)}")

    for path in iter_miniprogram_entries(MINIPROGRAM_ROOT):
        relative = path.relative_to(MINIPROGRAM_ROOT).as_posix()
        name = path.name.lower()
        if path.is_symlink():
            report.error(section, f"禁止符号链接: {relative}")
        if (
            name in FORBIDDEN_MINIPROGRAM_NAMES
            or ".private." in name
            or (path.is_file() and name.endswith(".log"))
        ):
            report.error(section, f"包含禁止的本地/私密/生成项: {relative}")

    app_json_path = MINIPROGRAM_ROOT / "miniprogram" / "app.json"
    app_json = load_json(app_json_path, section, report)
    if isinstance(app_json, dict):
        pages = app_json.get("pages")
        subpackages = app_json.get("subPackages", app_json.get("subpackages"))
        if not isinstance(pages, list) or not all(isinstance(page, str) for page in pages):
            report.error(section, "miniprogram/app.json 的 pages 必须是字符串数组")
        elif not isinstance(subpackages, list):
            report.error(section, "miniprogram/app.json 的 subPackages 必须是数组")
        else:
            resolved_pages = list(pages)
            for index, package in enumerate(subpackages):
                if not isinstance(package, dict):
                    report.error(section, f"subPackages[{index}] 必须是对象")
                    continue
                root = package.get("root")
                package_pages = package.get("pages")
                if not isinstance(root, str) or not isinstance(package_pages, list) or not all(
                    isinstance(page, str) for page in package_pages
                ):
                    report.error(section, f"subPackages[{index}] 的 root/pages 格式无效")
                    continue
                resolved_pages.extend(
                    f"{root.rstrip('/')}/{page.lstrip('/')}" for page in package_pages
                )
            if len(resolved_pages) != 61:
                report.error(section, f"app.json 应声明 61 个页面，实际为 {len(resolved_pages)} 个")
            if len(set(resolved_pages)) != len(resolved_pages):
                report.error(section, "app.json 存在重复页面声明")
    elif app_json is not None:
        report.error(section, "miniprogram/app.json 顶层必须是对象")

    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("小程序快照：无私密/生成项和符号链接，app.json 唯一声明 61 个页面")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_source_manifest(report: ValidationReport) -> None:
    section = "源码清单"
    manifest_path = MINIPROGRAM_ROOT / "SOURCE-MANIFEST.sha256"
    if not manifest_path.is_file():
        report.error(section, f"缺少文件 {display_path(manifest_path)}")
        return

    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        report.error(section, f"无法读取 SOURCE-MANIFEST.sha256: {exc}")
        return

    listed: dict[str, str] = {}
    ordered_paths: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        match = SHA256_LINE.fullmatch(line)
        if match is None:
            report.error(section, f"第 {line_number} 行不是 '<sha256>  ./<path>' 格式")
            continue
        expected_hash, relative = match.groups()
        pure_path = PurePosixPath(relative)
        if pure_path.is_absolute() or ".." in pure_path.parts or relative in {"", "."}:
            report.error(section, f"第 {line_number} 行包含不安全路径: {relative!r}")
            continue
        if relative == "SOURCE-MANIFEST.sha256":
            report.error(section, "SOURCE-MANIFEST.sha256 不得把自身列入哈希清单")
            continue
        if relative in listed:
            report.error(section, f"清单路径重复: {relative}")
            continue
        listed[relative] = expected_hash
        ordered_paths.append(relative)

    if ordered_paths != sorted(ordered_paths):
        report.error(section, "清单路径必须按字典序排列，以保证确定性")

    actual_files: set[str] = set()
    for path in iter_miniprogram_entries(MINIPROGRAM_ROOT):
        if path.is_file() and not path.is_symlink() and path != manifest_path:
            actual_files.add(path.relative_to(MINIPROGRAM_ROOT).as_posix())

    listed_files = set(listed)
    missing = sorted(listed_files - actual_files)
    unlisted = sorted(actual_files - listed_files)
    if missing:
        report.error(section, f"清单列出的文件不存在: {', '.join(missing[:10])}")
    if unlisted:
        suffix = " ..." if len(unlisted) > 10 else ""
        report.error(section, f"存在未列入清单的文件: {', '.join(unlisted[:10])}{suffix}")

    for relative in sorted(listed_files & actual_files):
        path = MINIPROGRAM_ROOT / relative
        try:
            actual_hash = sha256_file(path)
        except OSError as exc:
            report.error(section, f"无法计算 {relative} 的 SHA-256: {exc}")
            continue
        if actual_hash != listed[relative]:
            report.error(
                section,
                f"SHA-256 不匹配: {relative}，期望 {listed[relative]}，实际 {actual_hash}",
            )

    if (
        listed_files == actual_files
        and len(listed) == len(lines)
        and ordered_paths == sorted(ordered_paths)
        and not any(error.startswith(f"{section}:") for error in report.errors)
    ):
        report.passed(f"源码清单：{len(listed)} 个文件均存在且 SHA-256 匹配")


def validate_miniprogram_source_commit(
    report: ValidationReport,
    legacy_root: Path,
) -> None:
    section = "小程序来源提交"
    command = [
        "git",
        "-C",
        str(legacy_root.resolve()),
        "archive",
        "--format=tar",
        LEGACY_COMMIT,
        "--",
        "miniprogram-1",
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        report.error(section, result.stderr.decode("utf-8", errors="replace")[-2000:])
        return

    forbidden_parts = {".cloudbase", "node_modules", "_archived", "private", "log", "logs"}
    forbidden_names = {"analyse-data.json", "log.txt", "project.private.config.json"}
    source_files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith("miniprogram-1/"):
                continue
            relative = member.name.removeprefix("miniprogram-1/")
            pure_path = PurePosixPath(relative)
            lowered_parts = {part.lower() for part in pure_path.parts}
            if (
                lowered_parts & forbidden_parts
                or pure_path.name.lower() in forbidden_names
                or pure_path.name.lower().endswith(".log")
            ):
                continue
            extracted = archive.extractfile(member)
            if extracted is not None:
                source_files[relative] = extracted.read()

    boundary_files = {".gitignore", "BASELINE.md", "SOURCE-MANIFEST.sha256"}
    controlled_files = {
        path.relative_to(MINIPROGRAM_ROOT).as_posix(): path
        for path in MINIPROGRAM_ROOT.rglob("*")
        if path.is_file() and not path.is_symlink()
        and path.relative_to(MINIPROGRAM_ROOT).as_posix() not in boundary_files
    }
    if set(source_files) != set(controlled_files):
        missing = sorted(set(source_files) - set(controlled_files))
        extra = sorted(set(controlled_files) - set(source_files))
        report.error(
            section,
            f"来源/受控文件集合不同，缺少={missing[:5]}，额外={extra[:5]}",
        )
    mismatches = [
        relative
        for relative in sorted(set(source_files) & set(controlled_files))
        if source_files[relative] != controlled_files[relative].read_bytes()
    ]
    if mismatches:
        report.error(section, f"与固定 Git blob 不一致: {', '.join(mismatches[:10])}")
    if (
        len(source_files) != 611
        or len(controlled_files) != 611
        or set(source_files) != set(controlled_files)
    ):
        report.error(
            section,
            f"过滤后的来源和受控文件都应为 611，实际 {len(source_files)}/{len(controlled_files)}",
        )
    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("小程序来源提交：611 个受控文件逐字节等于固定 Git blob")


def validate_required_docs(report: ValidationReport) -> None:
    section = "阶段文档"
    contents: dict[str, str] = {}
    for name in REQUIRED_DOCS:
        path = REFACTOR_DIR / name
        if not path.is_file():
            report.error(section, f"缺少必需文档 {name}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
            contents[name] = content
            if not content.strip():
                report.error(section, f"必需文档为空: {name}")
        except (OSError, UnicodeError) as exc:
            report.error(section, f"无法读取 {name}: {exc}")
    progress_sections = (
        "## 当前阶段",
        "## 本轮已完成",
        "## 验证命令与结果",
        "## 尚未迁移的路由与数据",
        "## 已知风险与未收口项",
        "## 下一项具体动作",
    )
    progress = contents.get("05-progress.md", "")
    for heading in progress_sections:
        if heading not in progress:
            report.error(section, f"05-progress.md 缺少必需章节 {heading}")
    if "最近通过的提交" not in progress:
        report.error(section, "05-progress.md 缺少最近通过的提交")

    current_state = contents.get("00-current-state.md", "")
    for fact in (
        "592 条 URL 规则",
        "611 个 `path + method`",
        "116 次请求表达式",
        "113 个唯一",
        "102 条注册 URL 规则",
        "617 个物理列",
        "154 个资源条目",
        "309 个 HTML 模板",
        "61 个 app.json 声明页面",
        "7 套完整但未声明的小程序页源码",
        "181 个后台运行时入口",
        "14 条关键旅程",
    ):
        if fact not in current_state:
            report.error(section, f"00-current-state.md 缺少当前事实: {fact}")

    architecture = contents.get("01-target-architecture.md", "")
    for marker in ("目标依赖 DAG", "PostgreSQL 是业务事实源", "ADR 索引"):
        if marker not in architecture:
            report.error(section, f"01-target-architecture.md 缺少架构标记: {marker}")
    runbook = contents.get("04-migration-runbook.md", "")
    for marker in ("单写者", "回滚", "完整性"):
        if marker not in runbook:
            report.error(section, f"04-migration-runbook.md 缺少迁移安全标记: {marker}")

    for boundary_file in (PROJECT_ROOT / "README.md", PROJECT_ROOT / "AGENTS.md"):
        if not boundary_file.is_file() or not boundary_file.read_text(encoding="utf-8").strip():
            report.error(section, f"缺少独立项目边界文件 {boundary_file.name}")

    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("阶段文档：00–05 结构、关键事实、架构与迁移安全标记完整")


def validate_regeneration(
    report: ValidationReport,
    legacy_root: Path,
    legacy_python: Path | None,
) -> None:
    section = "确定性重生成"
    legacy_root = legacy_root.resolve()
    if not (legacy_root / "app" / "__init__.py").is_file():
        report.error(section, f"不是旧 Flask 仓库根目录: {legacy_root}")
        return
    if legacy_python is not None:
        python = legacy_python.expanduser()
        if not python.is_absolute():
            python = Path.cwd() / python
        python = python.absolute()
    else:
        python = (legacy_root / ".venv" / "bin" / "python").absolute()
    if not python.is_file():
        report.error(section, f"找不到旧项目 Python: {python}")
        return

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("TI_BACKUP_SCHEDULER", None)
    commands: list[tuple[str, list[str]]] = []
    with tempfile.TemporaryDirectory(prefix="ti-java-phase0-regen-") as temporary:
        output = Path(temporary) / "refactor"
        golden = output / "golden-samples"
        output.mkdir(parents=True)
        commands.extend(
            [
                (
                    "inventory",
                    [
                        str(python),
                        str(PROJECT_ROOT / "tools" / "inventory_legacy.py"),
                        "--legacy-root",
                        str(legacy_root),
                        "--output-dir",
                        str(output),
                    ],
                ),
                (
                    "golden",
                    [
                        str(python),
                        str(PROJECT_ROOT / "tools" / "capture_golden_samples.py"),
                        "--legacy-root",
                        str(legacy_root),
                        "--output-dir",
                        str(golden),
                    ],
                ),
                (
                    "surfaces",
                    [
                        str(python),
                        str(PROJECT_ROOT / "tools" / "inventory_surfaces.py"),
                        "--legacy-root",
                        str(legacy_root),
                        "--miniprogram-root",
                        str(MINIPROGRAM_ROOT),
                        "--output",
                        str(output / "09-surface-inventory.json"),
                    ],
                ),
            ]
        )
        for name, command in commands:
            result = subprocess.run(
                command,
                cwd=legacy_root,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=False,
            )
            if result.returncode != 0:
                excerpt = result.stdout[-3000:]
                report.error(section, f"{name} 重生成失败（{result.returncode}）:\n{excerpt}")
                return

        comparisons = (
            (output / "02-route-parity-matrix.csv", ROUTE_MATRIX),
            (output / "03-data-ownership.csv", DATA_MATRIX),
            (output / "phase0-inventory-summary.json", INVENTORY_SUMMARY),
            (output / "09-surface-inventory.json", SURFACE_INVENTORY),
        )
        for generated, checked_in in comparisons:
            if generated.read_bytes() != checked_in.read_bytes():
                report.error(
                    section,
                    f"重生成结果与已保存文件不同: {display_path(checked_in)}",
                )

        generated_golden = {path.name: path for path in golden.glob("*.json")}
        checked_golden = {path.name: path for path in GOLDEN_DIR.glob("*.json")}
        if set(generated_golden) != set(checked_golden):
            report.error(section, "黄金样本重生成文件集合与已保存集合不同")
        for name in sorted(set(generated_golden) & set(checked_golden)):
            if generated_golden[name].read_bytes() != checked_golden[name].read_bytes():
                report.error(section, f"黄金样本重生成结果不同: {name}")

    if not any(error.startswith(f"{section}:") for error in report.errors):
        report.passed("确定性重生成：路由、数据、页面入口、摘要和 7 组黄金样本逐字节一致")


def main() -> int:
    args = parse_args()
    report = ValidationReport()
    validate_routes(report)
    validate_data_ownership(report)
    validate_inventory_summary(report)
    validate_performance_sample(report)
    validate_legacy_test_baseline(report)
    validate_miniprogram_type_baseline(report)
    validate_surface_inventory(report)
    validate_golden_samples(report)
    validate_miniprogram_tree(report)
    validate_source_manifest(report)
    validate_miniprogram_source_commit(report, args.legacy_root)
    validate_required_docs(report)
    validate_regeneration(report, args.legacy_root, args.legacy_python)

    for message in report.passes:
        print(f"[PASS] {message}")
    if report.errors:
        sys.stdout.flush()
        for message in report.errors:
            print(f"[FAIL] {message}", file=sys.stderr)
        print(
            f"阶段 0 校验失败：{len(report.passes)} 项通过，{len(report.errors)} 个问题。",
            file=sys.stderr,
        )
        return 1

    print(f"阶段 0 校验通过：{len(report.passes)} 项检查全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
