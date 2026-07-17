#!/usr/bin/env python3
"""Capture deterministic caller evidence for personal-bank user-counts aliases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
CONTROLLED_MINIPROGRAM = TI_JAVA / "miniprogram"
ROUTE_MATRIX = TI_JAVA / "docs/refactor/02-route-parity-matrix.csv"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
ROUTES = (
    {
        "route_id": "6858f6fa506f",
        "path": "/api/user/banks/api/<int:bank_id>/user-counts",
        "surface": "miniprogram_compatibility_alias",
    },
    {
        "route_id": "006913d0d956",
        "path": "/user/banks/api/<int:bank_id>/user-counts",
        "surface": "web_compatibility_alias",
    },
)
SCAN_PATTERN = r"user-counts|getBankUserCounts|get_user_counts|getUserCounts"
SCAN_EXCLUSIONS = ("miniprogram-1/analyse-data.json",)

CONTROLLED_COPY_FILES = (
    "app.json",
    "utils/config.ts",
    "utils/config.js",
    "utils/api-client.ts",
    "utils/api-client.js",
    "utils/api-endpoints.ts",
    "utils/api-endpoints.js",
    "utils/quiz-source.ts",
    "utils/quiz-source.js",
    "components/v2-exam-builder/v2-exam-builder.ts",
    "components/v2-exam-builder/v2-exam-builder.js",
    "pages/bank-detail/bank-detail.ts",
    "pages/bank-detail/bank-detail.js",
    "pages/bank-detail/bank-detail.wxml",
    "pages/bank-detail/bank-detail.json",
    "pages/index-v2/index-v2.ts",
    "pages/index-v2/index-v2.js",
    "pages/index-v2/index-v2.wxml",
    "pages/index-v2/index-v2.json",
    "pages/practice-setup/practice-setup.ts",
    "pages/practice-setup/practice-setup.js",
    "pages/review-center-v2/review-center-v2.ts",
    "pages/review-center-v2/review-center-v2.js",
    "pages/subject-stats/subject-stats.ts",
    "pages/subject-stats/subject-stats.js",
)

TYPESCRIPT_DIRECT_CALLS = (
    (
        "reusable-exam-builder-per-type-count",
        "miniprogram-1/miniprogram/components/v2-exam-builder/v2-exam-builder.ts",
        583,
        "api.getBankUserCounts(bankId, { q_type: t, source: 'all' })",
    ),
    (
        "bank-detail-bootstrap-summary",
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        411,
        "api.getBankUserCounts(bankId, { source: 'all' })",
    ),
    (
        "bank-detail-filtered-start-count",
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        1422,
        "api.getBankUserCounts(bankId, params)",
    ),
    (
        "exam-center-per-type-count",
        "miniprogram-1/miniprogram/pages/index-v2/index-v2.ts",
        764,
        "api.getBankUserCounts(bankId, { q_type: t, source: 'all' })",
    ),
    (
        "legacy-practice-setup-summary",
        "miniprogram-1/miniprogram/pages/practice-setup/practice-setup.ts",
        295,
        "api.getBankUserCounts(bankId, params)",
    ),
    (
        "review-center-filtered-start-count",
        "miniprogram-1/miniprogram/pages/review-center-v2/review-center-v2.ts",
        570,
        "api.getBankUserCounts(bankId, params)",
    ),
    (
        "bank-quiz-source-adapter",
        "miniprogram-1/miniprogram/utils/quiz-source.ts",
        493,
        "api.getBankUserCounts(this.sourceId, apiParams)",
    ),
)

GENERATED_DIRECT_CALLS = (
    (
        "reusable-exam-builder-per-type-count",
        "miniprogram-1/miniprogram/components/v2-exam-builder/v2-exam-builder.js",
        599,
        "api_1.api.getBankUserCounts(bankId, { q_type: t, source: 'all' })",
    ),
    (
        "bank-detail-bootstrap-summary",
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
        392,
        "api_1.api.getBankUserCounts(bankId, { source: 'all' })",
    ),
    (
        "bank-detail-filtered-start-count",
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
        1526,
        "api_1.api.getBankUserCounts(bankId, params)",
    ),
    (
        "exam-center-per-type-count",
        "miniprogram-1/miniprogram/pages/index-v2/index-v2.js",
        875,
        "api_1.api.getBankUserCounts(bankId, { q_type: t, source: 'all' })",
    ),
    (
        "legacy-practice-setup-summary",
        "miniprogram-1/miniprogram/pages/practice-setup/practice-setup.js",
        373,
        "api_1.api.getBankUserCounts(bankId, params)",
    ),
    (
        "review-center-filtered-start-count",
        "miniprogram-1/miniprogram/pages/review-center-v2/review-center-v2.js",
        599,
        "api_1.api.getBankUserCounts(bankId, params)",
    ),
    (
        "bank-quiz-source-adapter",
        "miniprogram-1/miniprogram/utils/quiz-source.js",
        458,
        "api_1.api.getBankUserCounts(this.sourceId, apiParams)",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    })


def render_document(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def read_legacy_blob(legacy_root: Path, path: str) -> bytes:
    return pinned_source._run_read_only_git(
        legacy_root,
        "show",
        f"{LEGACY_COMMIT}:{path}",
    )


def _source_line(
    payload: bytes,
    *,
    source: str,
    line: int,
    contains: str,
) -> dict[str, Any]:
    lines = payload.decode("utf-8").splitlines()
    if line < 1 or line > len(lines):
        raise AssertionError(f"source line is out of range: {source}:{line}")
    text = lines[line - 1].strip()
    if contains not in text:
        raise AssertionError(
            f"user-counts caller drifted at {source}:{line}: "
            f"expected {contains!r}, got {text!r}"
        )
    return {
        "source": source,
        "line": line,
        "text": text,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_size_bytes": len(payload),
    }


def legacy_source_line(
    legacy_root: Path,
    path: str,
    line: int,
    contains: str,
) -> dict[str, Any]:
    return _source_line(
        read_legacy_blob(legacy_root, path),
        source=path,
        line=line,
        contains=contains,
    )


def controlled_source_line(path: str, line: int, contains: str) -> dict[str, Any]:
    source = TI_JAVA / path
    if not source.is_file():
        raise AssertionError(f"controlled miniprogram source is missing: {path}")
    return _source_line(
        source.read_bytes(),
        source=path,
        line=line,
        contains=contains,
    )


def full_repository_usage_scan(legacy_root: Path) -> dict[str, Any]:
    raw = pinned_source._run_read_only_git(
        legacy_root,
        "grep",
        "-n",
        "-I",
        "-E",
        SCAN_PATTERN,
        LEGACY_COMMIT,
        "--",
        ".",
        ":(exclude)miniprogram-1/analyse-data.json",
    ).decode("utf-8")
    prefix = LEGACY_COMMIT + ":"
    matches: list[dict[str, Any]] = []
    for raw_line in raw.splitlines():
        if not raw_line.startswith(prefix):
            raise AssertionError(f"unexpected fixed-commit git grep row: {raw_line!r}")
        match = re.fullmatch(r"(.+?):([0-9]+):(.*)", raw_line[len(prefix):])
        if match is None:
            raise AssertionError(f"unparseable fixed-commit git grep row: {raw_line!r}")
        matches.append({
            "source": match.group(1),
            "line": int(match.group(2)),
            "text": match.group(3).strip(),
        })
    matches.sort(key=lambda item: (item["source"], item["line"], item["text"]))
    sources = sorted({item["source"] for item in matches})
    generic_only_sources = sorted({
        "miniprogram-1/miniprogram/pages/practice/practice.js",
        "miniprogram-1/miniprogram/pages/practice/practice.ts",
        "miniprogram-1/miniprogram/pages/subject-detail-v2/subject-detail-v2.js",
        "miniprogram-1/miniprogram/pages/subject-detail-v2/subject-detail-v2.ts",
        "tests/test_home_personal_bank_stats.py",
    })
    if not matches:
        raise AssertionError("fixed-commit user-counts caller scan returned no matches")
    if not set(generic_only_sources).issubset(sources):
        raise AssertionError("generic getUserCounts collision classification drifted")
    return {
        "command": "git grep -n -I -E <pattern> <fixed-commit> -- . <exclusions>",
        "pattern": SCAN_PATTERN,
        "scope": "all executable, template, test and configuration text blobs at the fixed legacy commit",
        "excluded_generated_inventory_files": list(SCAN_EXCLUSIONS),
        "exclusion_reason": (
            "analyse-data.json is a generated one-line bundle inventory; embedded source text "
            "would duplicate real callers and inflate the attestation"
        ),
        "match_count": len(matches),
        "matched_source_count": len(sources),
        "matched_source_roots": sorted({source.split("/", 1)[0] for source in sources}),
        "generic_get_user_counts_collision_sources": generic_only_sources,
        "generic_get_user_counts_collision_source_count": len(generic_only_sources),
        "capability_or_mixed_source_count": len(sources) - len(generic_only_sources),
        "matches_sha256": sha256_json(matches),
        "matches": matches,
    }


def route_matrix_attestation() -> dict[str, Any]:
    if not ROUTE_MATRIX.is_file():
        raise AssertionError(f"route matrix is missing: {ROUTE_MATRIX}")
    with ROUTE_MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected: dict[str, dict[str, Any]] = {}
    for route in ROUTES:
        matches = [row for row in rows if row.get("route_id") == route["route_id"]]
        if len(matches) != 1:
            raise AssertionError(
                f"route matrix row count drifted for {route['route_id']}: {len(matches)}"
            )
        row = matches[0]
        if row["path"] != route["path"] or row["methods"] != "GET":
            raise AssertionError(f"route matrix identity drifted for {route['route_id']}")
        if row["migration_status"] != "pending" or row["target_module"] != "personalbank":
            raise AssertionError(f"route matrix disposition drifted for {route['route_id']}")
        client_references = json.loads(row["client_references"])
        selected[route["route_id"]] = {
            "route_id": row["route_id"],
            "path": row["path"],
            "methods": row["methods"],
            "endpoint": row["endpoint"],
            "registration_kind": row["registration_kind"],
            "auth_semantics": json.loads(row["auth_semantics"]),
            "client_surfaces": row["client_surfaces"].split(";"),
            "client_references": client_references,
            "target_module": row["target_module"],
            "migration_status": row["migration_status"],
            "row_sha256": sha256_json(row),
        }
    return {
        "state": "both_frozen_rows_closed",
        "matrix": "docs/refactor/02-route-parity-matrix.csv",
        "rows": selected,
        "static_scan_limit": (
            "the API row records the endpoint wrapper, while this additive caller attestation "
            "closes the seven downstream TypeScript invocation sites and one adapter consumer"
        ),
    }


def handler_and_alias_attestation(legacy_root: Path) -> dict[str, Any]:
    route_source = "app/modules/user_bank/routes/api_quiz.py"
    registration_source = "app/modules/user_bank/__init__.py"
    return {
        "state": "one_registered_handler_serves_both_aliases",
        "relative_route": legacy_source_line(
            legacy_root,
            route_source,
            774,
            "@user_bank_api_bp.route('/<int:bank_id>/user-counts', methods=['GET'])",
        ),
        "authentication": legacy_source_line(
            legacy_root, route_source, 775, "@auth_required"
        ),
        "handler": legacy_source_line(
            legacy_root, route_source, 776, "def get_user_counts(bank_id):"
        ),
        "access_check": {
            "lookup": legacy_source_line(
                legacy_root, route_source, 779, "check_bank_access(user_id, bank_id)"
            ),
            "forbidden": legacy_source_line(
                legacy_root, route_source, 782, "'无权访问此题库'"
            ),
        },
        "query_parameters": {
            "q_type": legacy_source_line(
                legacy_root, route_source, 784, "request.args.get('q_type', '').strip()"
            ),
            "q_type_all_normalization": legacy_source_line(
                legacy_root, route_source, 785, "if q_type.lower() == 'all':"
            ),
            "source": legacy_source_line(
                legacy_root, route_source, 787, "request.args.get('source', 'all').strip()"
            ),
            "tag": legacy_source_line(
                legacy_root, route_source, 788, "request.args.get('tag')"
            ),
        },
        "tag_store_dependency": {
            "load": legacy_source_line(
                legacy_root, route_source, 794, "_load_bank_tag_store(raw_conn, bank_id, user_id)"
            ),
            "legacy_fallback": legacy_source_line(
                legacy_root,
                "app/modules/user_bank/routes/api_tags.py",
                116,
                "fallback：读取旧格式，并尽力迁移到新表",
            ),
            "migration_write": legacy_source_line(
                legacy_root,
                "app/modules/user_bank/routes/api_tags.py",
                122,
                "_save_bank_tag_store(conn, bank_id, user_id",
            ),
            "commit": legacy_source_line(
                legacy_root,
                "app/modules/user_bank/routes/api_tags.py",
                183,
                "db.session.commit()",
            ),
            "disposition": "tag-filtered GET is not guaranteed to be side-effect free in legacy",
        },
        "response_fields": {
            field: legacy_source_line(legacy_root, route_source, line, f"'{field}'")
            for field, line in (
                ("total", 892),
                ("favorites", 893),
                ("mistakes", 894),
                ("types", 895),
                ("shuffle_options_available", 896),
            )
        },
        "web_alias_registration": {
            "outer_prefix": legacy_source_line(
                legacy_root, registration_source, 15, "url_prefix='/user/banks'"
            ),
            "nested_prefix": legacy_source_line(
                legacy_root, registration_source, 17, "url_prefix='/api'"
            ),
            "application_registration": legacy_source_line(
                legacy_root, registration_source, 18, "app.register_blueprint(user_bank_bp)"
            ),
            "composed_path": "/user/banks/api/<int:bank_id>/user-counts",
            "route_id": "006913d0d956",
        },
        "api_alias_registration": {
            "outer_prefix": legacy_source_line(
                legacy_root, registration_source, 23, "url_prefix='/api'"
            ),
            "nested_prefix": legacy_source_line(
                legacy_root, registration_source, 24, "url_prefix='/user/banks/api'"
            ),
            "application_registration": legacy_source_line(
                legacy_root, registration_source, 25, "app.register_blueprint(api_root_bp)"
            ),
            "composed_path": "/api/user/banks/api/<int:bank_id>/user-counts",
            "route_id": "6858f6fa506f",
        },
    }


def web_caller_attestation(legacy_root: Path) -> dict[str, Any]:
    template = "app/modules/user_bank/templates/user_bank/bank/bank_practice/body_end/_01_core.html"
    return {
        "state": "active",
        "logical_caller_id": "legacy-web-bank-practice-start-count",
        "actual_alias": "/user/banks/api/<bank_id>/user-counts",
        "page_route": legacy_source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            124,
            "@user_bank_pages_bp.route('/<int:bank_id>/practice')",
        ),
        "page_authentication": legacy_source_line(
            legacy_root, "app/modules/user_bank/routes/pages.py", 125, "@login_required"
        ),
        "render_reference": legacy_source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            241,
            "user_bank/bank/bank_practice.html",
        ),
        "template_include_chain": [
            legacy_source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/bank/bank_practice.html",
                13,
                "bank_practice/_body_end.html",
            ),
            legacy_source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/bank/bank_practice/_body_end.html",
                4,
                "body_end/_01_core.html",
            ),
        ],
        "bank_id_injection": legacy_source_line(
            legacy_root, template, 3, "const BANK_ID = {{ bank_id }};"
        ),
        "forwarded_parameters": {
            "source": legacy_source_line(legacy_root, template, 718, "params.set('source', source)"),
            "q_type": legacy_source_line(legacy_root, template, 719, "params.set('q_type', state.type)"),
            "tag": legacy_source_line(legacy_root, template, 720, "params.set('tag', state.tag)"),
        },
        "direct_get": legacy_source_line(
            legacy_root, template, 723, "/user-counts?` + params.toString()"
        ),
        "response_extraction": legacy_source_line(
            legacy_root, template, 727, "data && data.data ? data.data : {}"
        ),
        "consumed_fields": {
            "total": legacy_source_line(legacy_root, template, 728, "payload.total"),
            "shuffle_options_available": legacy_source_line(
                legacy_root, template, 729, "payload.shuffle_options_available"
            ),
        },
        "activation": {
            "bootstrap": legacy_source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/bank/bank_practice/body_end/_06_bootstrap.html",
                26,
                "queueStartCount();",
            ),
            "practice_tab": legacy_source_line(legacy_root, template, 463, "queueStartCount();"),
            "filter_chip": legacy_source_line(legacy_root, template, 543, "queueStartCount();"),
            "tag_delete": legacy_source_line(legacy_root, template, 635, "queueStartCount();"),
        },
        "failure_render": legacy_source_line(
            legacy_root, template, 736, "setStartCount('—', false)"
        ),
        "direct_network_call_site_count": 1,
    }


def miniprogram_path_derivation(legacy_root: Path) -> dict[str, Any]:
    endpoint = "miniprogram-1/miniprogram/utils/api-endpoints.ts"
    return {
        "production_api_base": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/config.ts",
            18,
            "https://saksk.top/api",
        ),
        "custom_base_normalization": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/config.ts",
            44,
            "${scheme}://${hostPort}/api",
        ),
        "development_api_base": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/config.ts",
            188,
            "http://${host}:${port}/api",
        ),
        "typescript_symbol": legacy_source_line(
            legacy_root, endpoint, 760, "getBankUserCounts: (bankId: number"
        ),
        "relative_endpoint": legacy_source_line(
            legacy_root, endpoint, 764, "/user-counts`, 'GET', params || {})"
        ),
        "request_url_composition": {
            "base_lookup": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/api-client.ts",
                105,
                "const apiBaseUrl = getApiBaseUrl();",
            ),
            "concatenation": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/api-client.ts",
                110,
                "url: `${apiBaseUrl}${url}`",
            ),
            "bearer_header": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/api-client.ts",
                115,
                "`Bearer ${tokenAtRequest}`",
            ),
            "data_unwrap": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/api-client.ts",
                127,
                "resolve(result.data as T)",
            ),
        },
        "actual_alias": "/api/user/banks/api/<bank_id>/user-counts",
        "result": "every supported API base ends in /api, so the relative endpoint selects the API alias",
    }


def miniprogram_direct_callers(legacy_root: Path) -> list[dict[str, Any]]:
    callers: list[dict[str, Any]] = []
    for caller_id, path, line, contains in TYPESCRIPT_DIRECT_CALLS:
        callers.append({
            "caller_id": caller_id,
            "direct_call": legacy_source_line(legacy_root, path, line, contains),
        })
    by_id = {caller["caller_id"]: caller for caller in callers}

    by_id["reusable-exam-builder-per-type-count"].update({
        "request_parameters": ["q_type=<available type>", "source=all"],
        "consumed_fields": [legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/components/v2-exam-builder/v2-exam-builder.ts",
            584,
            "res?.total",
        )],
        "activations": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.wxml",
                296,
                '<v2-exam-builder source="user_bank"',
            ),
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/index-v2/index-v2.wxml",
                84,
                "<v2-exam-builder",
            ),
        ],
        "fan_out": "one request per available question type via Promise.all",
    })
    by_id["bank-detail-bootstrap-summary"].update({
        "request_parameters": ["source=all"],
        "consumed_fields": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
                line,
                field,
            )
            for line, field in ((465, "countsData?.total"), (466, "countsData?.favorites"), (467, "countsData?.mistakes"))
        ],
        "activation": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
            313,
            "this.bootstrap();",
        ),
    })
    by_id["bank-detail-filtered-start-count"].update({
        "request_parameters": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
                line,
                contains,
            )
            for line, contains in (
                (1418, "source: this.data.practiceScope"),
                (1419, "params.q_type = this.data.qType"),
                (1420, "params.tag = this.data.tag"),
            )
        ],
        "consumed_fields": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
                1425,
                "data?.shuffle_options_available",
            ),
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
                1427,
                "data?.total",
            ),
        ],
        "activation": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
            1409,
            "this.loadStartCount()",
        ),
    })
    by_id["exam-center-per-type-count"].update({
        "request_parameters": ["q_type=<available type>", "source=all"],
        "consumed_fields": [legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/index-v2/index-v2.ts",
            765,
            "res?.total",
        )],
        "activation": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/index-v2/index-v2.ts",
            341,
            "this.reloadExamTypes()",
        ),
        "fan_out": "one request per available question type via Promise.all",
    })
    by_id["legacy-practice-setup-summary"].update({
        "request_parameters": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/practice-setup/practice-setup.ts",
                line,
                contains,
            )
            for line, contains in (
                (291, "params.q_type = selectedType"),
                (292, "params.source = selectedSource"),
                (293, "params.tag = selectedTag"),
            )
        ],
        "consumed_fields": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/practice-setup/practice-setup.ts",
                line,
                f"data.{field}",
            )
            for line, field in ((300, "total"), (301, "favorites"), (302, "mistakes"))
        ],
        "page_registration": legacy_source_line(
            legacy_root, "miniprogram-1/miniprogram/app.json", 41, "pages/practice-setup/practice-setup"
        ),
    })
    by_id["review-center-filtered-start-count"].update({
        "request_parameters": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/review-center-v2/review-center-v2.ts",
                line,
                contains,
            )
            for line, contains in (
                (566, "params.q_type = qType"),
                (568, "params.source = source"),
                (569, "params.tag = tag"),
            )
        ],
        "consumed_fields": [legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/review-center-v2/review-center-v2.ts",
            571,
            "res?.total",
        )],
        "activation": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/review-center-v2/review-center-v2.ts",
            429,
            "this.refreshStartCount();",
        ),
    })
    by_id["bank-quiz-source-adapter"].update({
        "request_parameters": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/quiz-source.ts",
                line,
                contains,
            )
            for line, contains in (
                (487, "apiParams.q_type = params.type"),
                (490, "apiParams.source = params.source"),
            )
        ],
        "tag_forwarding": "not implemented by FilterParams or this adapter",
        "consumed_fields": [
            legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/quiz-source.ts",
                line,
                f"data.{field}",
            )
            for line, field in ((496, "total"), (497, "favorites"), (498, "mistakes"))
        ],
    })
    return callers


def miniprogram_indirect_consumer(legacy_root: Path) -> dict[str, Any]:
    source = "miniprogram-1/miniprogram/pages/subject-stats/subject-stats.ts"
    return {
        "state": "active_for_bank_id_deep_link",
        "consumer_id": "subject-stats-via-bank-quiz-source",
        "page_registration": legacy_source_line(
            legacy_root, "miniprogram-1/miniprogram/app.json", 42, "pages/subject-stats/subject-stats"
        ),
        "source_factory": legacy_source_line(
            legacy_root, source, 33, "createSourceFromOptions(options)"
        ),
        "indirect_call": legacy_source_line(
            legacy_root, source, 75, "quizSource.getUserCounts()"
        ),
        "consumed_fields": [
            legacy_source_line(legacy_root, source, 79, "userCounts.mistakes"),
            legacy_source_line(legacy_root, source, 80, "userCounts.favorites"),
        ],
        "adapter_selection": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/quiz-source.ts",
            702,
            "new BankQuizSource(Number(bankId))",
        ),
        "network_call_counting": "indirect consumer of the adapter direct call; not a second network implementation",
    }


def generated_javascript_attestation(legacy_root: Path) -> dict[str, Any]:
    calls = [
        {
            "caller_id": caller_id,
            "compiled_direct_call": legacy_source_line(legacy_root, path, line, contains),
        }
        for caller_id, path, line, contains in GENERATED_DIRECT_CALLS
    ]
    source_generated_pairs = []
    for relative in (
        "utils/api-endpoints",
        "utils/quiz-source",
        "components/v2-exam-builder/v2-exam-builder",
        "pages/bank-detail/bank-detail",
        "pages/index-v2/index-v2",
        "pages/practice-setup/practice-setup",
        "pages/review-center-v2/review-center-v2",
        "pages/subject-stats/subject-stats",
    ):
        source = f"miniprogram-1/miniprogram/{relative}.ts"
        generated = f"miniprogram-1/miniprogram/{relative}.js"
        source_generated_pairs.append({
            "typescript_source": source,
            "typescript_sha256": hashlib.sha256(read_legacy_blob(legacy_root, source)).hexdigest(),
            "generated_javascript": generated,
            "generated_javascript_sha256": hashlib.sha256(read_legacy_blob(legacy_root, generated)).hexdigest(),
            "caller_counting": "generated JavaScript is runtime evidence and is not counted twice",
        })
    return {
        "state": "generated_runtime_mirrors_of_typescript_callers",
        "compiled_endpoint": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/api-endpoints.js",
            419,
            'getBankUserCounts: function (bankId, params)',
        ),
        "compiled_direct_calls": calls,
        "compiled_indirect_consumer": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/subject-stats/subject-stats.js",
            108,
            "quizSource.getUserCounts()",
        ),
        "source_generated_pairs": source_generated_pairs,
        "compiled_direct_call_site_count": len(calls),
        "additional_independent_caller_count": 0,
    }


def legacy_test_attestation(legacy_root: Path) -> dict[str, Any]:
    source = "tests/test_user_bank_quiz_record.py"
    return {
        "state": "focused_success_only_web_alias_coverage",
        "test": legacy_source_line(
            legacy_root, source, 232, "test_bank_user_counts_reports_shuffle_options_availability"
        ),
        "request_sites": [
            legacy_source_line(legacy_root, source, 237, "/user-counts"),
            legacy_source_line(legacy_root, source, 243, "/user-counts"),
        ],
        "assertions": [
            legacy_source_line(legacy_root, source, 240, 'choice_data["types"]'),
            legacy_source_line(legacy_root, source, 241, 'shuffle_options_available"] is True'),
            legacy_source_line(legacy_root, source, 246, 'mixed_data["types"]'),
            legacy_source_line(legacy_root, source, 247, 'shuffle_options_available"] is False'),
        ],
        "covered_alias": "/user/banks/api/<bank_id>/user-counts",
        "request_site_count": 2,
        "known_gaps": [
            "API alias and Bearer authentication",
            "anonymous and mixed-credential behavior",
            "owner, public, shared, expired-share, disabled-bank and missing-bank access",
            "source, q_type and tag filter combinations",
            "total, favorites and mistakes count semantics",
            "empty and nonstandard stored question types",
            "tag fallback migration and GET side effects",
            "partial SQL fallback and generic failure responses",
        ],
    }


def controlled_copy_attestation(legacy_root: Path) -> dict[str, Any]:
    if not CONTROLLED_MINIPROGRAM.is_dir():
        raise AssertionError(
            f"controlled miniprogram root is missing: {CONTROLLED_MINIPROGRAM}"
        )
    files = []
    for relative in CONTROLLED_COPY_FILES:
        legacy_path = f"miniprogram-1/miniprogram/{relative}"
        controlled_path = f"miniprogram/miniprogram/{relative}"
        legacy_payload = read_legacy_blob(legacy_root, legacy_path)
        local_source = TI_JAVA / controlled_path
        if not local_source.is_file():
            raise AssertionError(f"controlled miniprogram source is missing: {controlled_path}")
        controlled_payload = local_source.read_bytes()
        if controlled_payload != legacy_payload:
            raise AssertionError(
                "controlled miniprogram caller baseline drifted from the fixed legacy commit: "
                f"{controlled_path}"
            )
        files.append({
            "legacy_source": legacy_path,
            "controlled_source": controlled_path,
            "legacy_sha256": hashlib.sha256(legacy_payload).hexdigest(),
            "controlled_sha256": hashlib.sha256(controlled_payload).hexdigest(),
            "byte_equal": True,
        })

    direct_calls = [
        {
            "caller_id": caller_id,
            "direct_call": controlled_source_line(
                path.replace("miniprogram-1/", "miniprogram/", 1), line, contains
            ),
        }
        for caller_id, path, line, contains in TYPESCRIPT_DIRECT_CALLS
    ]
    return {
        "state": "active_controlled_migration_copy",
        "scope": "Ti-Java/miniprogram",
        "baseline_relationship": (
            "all caller, path-derivation, activation and generated-runtime files used by this "
            "attestation are byte-equal to the fixed legacy commit"
        ),
        "path_derivation": {
            "production_api_base": controlled_source_line(
                "miniprogram/miniprogram/utils/config.ts", 18, "https://saksk.top/api"
            ),
            "relative_endpoint": controlled_source_line(
                "miniprogram/miniprogram/utils/api-endpoints.ts",
                764,
                "/user-counts`, 'GET', params || {})",
            ),
            "request_concatenation": controlled_source_line(
                "miniprogram/miniprogram/utils/api-client.ts",
                110,
                "url: `${apiBaseUrl}${url}`",
            ),
            "actual_alias": "/api/user/banks/api/<bank_id>/user-counts",
        },
        "typescript_direct_calls": direct_calls,
        "typescript_indirect_consumer": controlled_source_line(
            "miniprogram/miniprogram/pages/subject-stats/subject-stats.ts",
            75,
            "quizSource.getUserCounts()",
        ),
        "generated_direct_calls": [
            {
                "caller_id": caller_id,
                "direct_call": controlled_source_line(
                    path.replace("miniprogram-1/", "miniprogram/", 1), line, contains
                ),
            }
            for caller_id, path, line, contains in GENERATED_DIRECT_CALLS
        ],
        "byte_equal_files": files,
        "byte_equal_file_count": len(files),
        "typescript_direct_call_site_count": len(direct_calls),
        "generated_javascript_additional_independent_caller_count": 0,
    }


def capture_document(legacy_root: Path) -> dict[str, Any]:
    if pinned_source.LEGACY_COMMIT != LEGACY_COMMIT:
        raise AssertionError(
            "shared fixed-commit authority drifted: "
            f"expected {LEGACY_COMMIT}, got {pinned_source.LEGACY_COMMIT}"
        )
    resolved = pinned_source._run_read_only_git(
        legacy_root,
        "rev-parse",
        "--verify",
        f"{LEGACY_COMMIT}^{{commit}}",
    ).decode("utf-8").strip()
    if resolved != LEGACY_COMMIT:
        raise AssertionError(f"legacy commit resolution drifted: {resolved}")

    scan = full_repository_usage_scan(legacy_root)
    if scan["match_count"] != 43 or scan["matched_source_count"] != 24:
        raise AssertionError(
            "fixed-commit user-counts capability scan drifted: "
            f"expected 43/24 matches/sources, got "
            f"{scan['match_count']}/{scan['matched_source_count']}"
        )
    matrix = route_matrix_attestation()
    handler = handler_and_alias_attestation(legacy_root)
    web = web_caller_attestation(legacy_root)
    path_derivation = miniprogram_path_derivation(legacy_root)
    direct_callers = miniprogram_direct_callers(legacy_root)
    indirect_consumer = miniprogram_indirect_consumer(legacy_root)
    generated = generated_javascript_attestation(legacy_root)
    tests = legacy_test_attestation(legacy_root)
    controlled = controlled_copy_attestation(legacy_root)
    caller_counting = {
        "legacy_web_direct_network_call_site_count": 1,
        "legacy_miniprogram_typescript_direct_call_site_count": len(direct_callers),
        "legacy_miniprogram_typescript_direct_source_file_count": len({
            caller["direct_call"]["source"] for caller in direct_callers
        }),
        "legacy_miniprogram_indirect_consumer_count": 1,
        "legacy_test_request_site_count": tests["request_site_count"],
        "generated_javascript_direct_call_site_count": generated["compiled_direct_call_site_count"],
        "generated_javascript_additional_count": 0,
        "controlled_copy_counting": (
            "separate migration-project counterpart; not added to fixed-commit legacy counts"
        ),
        "endpoint_wrapper_counting": "shared request factory; not counted as a downstream caller",
    }
    closure = {
        "fixed_commit_resolved": True,
        "full_repository_scan_captured": True,
        "generic_symbol_collisions_classified": scan["generic_get_user_counts_collision_source_count"] == 5,
        "frozen_route_matrix_rows_closed": matrix["state"] == "both_frozen_rows_closed",
        "shared_handler_closed": handler["handler"]["line"] == 776,
        "both_registered_aliases_closed": (
            handler["web_alias_registration"]["route_id"] == "006913d0d956"
            and handler["api_alias_registration"]["route_id"] == "6858f6fa506f"
        ),
        "active_web_direct_caller_closed": web["direct_network_call_site_count"] == 1,
        "seven_miniprogram_typescript_direct_calls_closed": len(direct_callers) == 7,
        "subject_stats_indirect_consumer_closed": indirect_consumer["indirect_call"]["line"] == 75,
        "api_base_actual_alias_closed": path_derivation["actual_alias"].startswith("/api/"),
        "typescript_generated_mirrors_closed": (
            generated["compiled_direct_call_site_count"] == 7
            and generated["additional_independent_caller_count"] == 0
        ),
        "focused_legacy_tests_closed": tests["request_site_count"] == 2,
        "controlled_miniprogram_copy_closed": all(
            item["byte_equal"] for item in controlled["byte_equal_files"]
        ),
        "generated_files_not_double_counted": (
            caller_counting["generated_javascript_additional_count"] == 0
        ),
        "caller_attestation_complete": True,
    }
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-user-counts-caller-attestation",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "legacy_commit": LEGACY_COMMIT,
        "routes": list(ROUTES),
        "full_repository_scan": scan,
        "frozen_route_matrix": matrix,
        "handler_and_aliases": handler,
        "callers": {
            "web_template": web,
            "legacy_miniprogram_path_derivation": path_derivation,
            "legacy_miniprogram_typescript_direct_calls": direct_callers,
            "legacy_miniprogram_indirect_consumer": indirect_consumer,
            "legacy_miniprogram_generated_javascript": generated,
            "legacy_tests": tests,
            "ti_java_controlled_miniprogram_copy": controlled,
        },
        "caller_counting": caller_counting,
        "frozen_route_matrix_disposition": {
            "matrix_is_immutable": True,
            "matrix_static_scan_is_not_a_complete_caller_inventory": True,
            "web_template_and_tests_already_named": True,
            "seven_miniprogram_downstream_invocations_closed_here": True,
            "subject_stats_adapter_consumer_closed_here": True,
            "resolution": (
                "this additive fixed-commit attestation closes active downstream callers without "
                "editing the route matrix, OpenAPI, production Java or migration contracts"
            ),
        },
        "closure": closure,
    }
    document["attestation_sha256"] = sha256_json({
        "routes": document["routes"],
        "full_repository_scan": document["full_repository_scan"],
        "frozen_route_matrix": document["frozen_route_matrix"],
        "handler_and_aliases": document["handler_and_aliases"],
        "callers": document["callers"],
        "caller_counting": document["caller_counting"],
        "frozen_route_matrix_disposition": document["frozen_route_matrix_disposition"],
        "closure": document["closure"],
    })
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    args = parse_args()
    document = capture_document(args.legacy_root.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_document(document), encoding="utf-8")
    print(
        "captured personal-bank user-counts callers "
        f"matches={document['full_repository_scan']['match_count']} "
        f"web_calls={document['caller_counting']['legacy_web_direct_network_call_site_count']} "
        f"miniprogram_direct_calls={document['caller_counting']['legacy_miniprogram_typescript_direct_call_site_count']} "
        f"attestation_sha256={document['attestation_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
