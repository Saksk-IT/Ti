#!/usr/bin/env python3
"""Capture deterministic caller evidence for the personal-bank usage-stats read."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
CONTROLLED_MINIPROGRAM = TI_JAVA / "miniprogram"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
ROUTES = (
    {
        "route_id": "d67a16965b08",
        "path": "/api/user/banks/api/<int:bank_id>/usage-stats",
        "surface": "miniprogram_compatibility_alias",
    },
    {
        "route_id": "22aecd49a3c2",
        "path": "/user/banks/api/<int:bank_id>/usage-stats",
        "surface": "web_compatibility_alias",
    },
)
SCAN_PATTERN = r"usage-stats|getBankUsageStats|loadUsageStats|usageStats"
SCAN_EXCLUSIONS = ("miniprogram-1/analyse-data.json",)
CONTROLLED_COPY_PAIRS = (
    (
        "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        "miniprogram/miniprogram/utils/api-endpoints.ts",
    ),
    (
        "miniprogram-1/miniprogram/utils/api-endpoints.js",
        "miniprogram/miniprogram/utils/api-endpoints.js",
    ),
    (
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        "miniprogram/miniprogram/pages/bank-detail/bank-detail.ts",
    ),
    (
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
        "miniprogram/miniprogram/pages/bank-detail/bank-detail.js",
    ),
    (
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.wxml",
        "miniprogram/miniprogram/pages/bank-detail/bank-detail.wxml",
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
            f"usage-stats caller drifted at {source}:{line}: "
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
    if not matches:
        raise AssertionError("fixed-commit usage-stats caller scan returned no matches")
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
        "matched_source_count": len({item["source"] for item in matches}),
        "matched_source_roots": sorted({
            item["source"].split("/", 1)[0] for item in matches
        }),
        "matches_sha256": sha256_json(matches),
        "matches": matches,
    }


def handler_and_alias_attestation(legacy_root: Path) -> dict[str, Any]:
    route_source = "app/modules/user_bank/routes/api_shares.py"
    registration_source = "app/modules/user_bank/__init__.py"
    response_fields = {
        field: legacy_source_line(legacy_root, route_source, line, f"'{field}'")
        for field, line in (
            ("bank_id", 140),
            ("is_public", 141),
            ("owner_id", 142),
            ("owner_count", 143),
            ("shared_users", 144),
            ("public_users", 145),
            ("total_users", 146),
            ("total_users_excluding_owner", 147),
        )
    }
    return {
        "state": "one_registered_handler_serves_both_aliases",
        "relative_route": legacy_source_line(
            legacy_root,
            route_source,
            56,
            "@user_bank_api_bp.route('/<int:bank_id>/usage-stats', methods=['GET'])",
        ),
        "authentication": legacy_source_line(
            legacy_root,
            route_source,
            57,
            "@auth_required",
        ),
        "handler": legacy_source_line(
            legacy_root,
            route_source,
            58,
            "def get_bank_usage_stats(bank_id):",
        ),
        "response_fields": response_fields,
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
            "composed_path": "/user/banks/api/<int:bank_id>/usage-stats",
            "route_id": "22aecd49a3c2",
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
            "composed_path": "/api/user/banks/api/<int:bank_id>/usage-stats",
            "route_id": "d67a16965b08",
        },
    }


def web_caller_attestation(legacy_root: Path) -> dict[str, Any]:
    template = "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html"
    return {
        "state": "active",
        "logical_caller_id": "legacy-web-bank-share-management",
        "actual_alias": "/user/banks/api/<bank_id>/usage-stats",
        "page_route": legacy_source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            769,
            "@user_bank_pages_bp.route('/<int:bank_id>/shares')",
        ),
        "render_reference": legacy_source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            785,
            "user_bank/manage/bank_manage_shares.html",
        ),
        "navigation_references": [
            legacy_source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/manage/_bank_manage_basebar.html",
                9,
                'href="/user/banks/{{ bank_id }}/shares"',
            ),
            legacy_source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/manage/manage_base.html",
                357,
                'href="/user/banks/{{ bank_id }}/shares"',
            ),
            legacy_source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/manage/banks.html",
                1043,
                '/user/banks/${bank.id}/shares',
            ),
        ],
        "private_bank_guard": legacy_source_line(
            legacy_root, template, 160, "{% if not is_public %}"
        ),
        "function": legacy_source_line(
            legacy_root, template, 229, "async function loadUsageStats()"
        ),
        "direct_get": legacy_source_line(
            legacy_root, template, 232, "/usage-stats`"
        ),
        "response_extraction": legacy_source_line(
            legacy_root, template, 233, "const d = (res && res.data) ? res.data : (res || {});"
        ),
        "consumed_field": legacy_source_line(
            legacy_root, template, 234, "d.total_users"
        ),
        "render": legacy_source_line(
            legacy_root, template, 235, "可访问人数"
        ),
        "activation": {
            "initial_page_load": legacy_source_line(
                legacy_root, template, 431, "loadUsageStats();"
            ),
            "after_revoke": legacy_source_line(
                legacy_root, template, 326, "loadUsageStats();"
            ),
            "after_create": legacy_source_line(
                legacy_root, template, 359, "loadUsageStats();"
            ),
        },
        "failure_render": legacy_source_line(
            legacy_root, template, 237, "可访问人数：—"
        ),
        "reason": (
            "the owner-only share-management page is rendered from a registered route, is linked "
            "from live management surfaces, and invokes the Web alias on initial load and refreshes"
        ),
    }


def legacy_miniprogram_attestation(legacy_root: Path) -> dict[str, Any]:
    endpoint = "miniprogram-1/miniprogram/utils/api-endpoints.ts"
    page = "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts"
    response_fields = {
        field: legacy_source_line(legacy_root, page, line, f"data.{field}")
        for field, line in (
            ("is_public", 1995),
            ("owner_id", 1996),
            ("owner_count", 1997),
            ("shared_users", 1998),
            ("public_users", 1999),
            ("total_users", 2000),
            ("total_users_excluding_owner", 2001),
        )
    }
    return {
        "state": "active",
        "logical_caller_id": "legacy-miniprogram-bank-detail",
        "actual_alias": "/api/user/banks/api/<bank_id>/usage-stats",
        "path_derivation": {
            "production_api_base": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/utils/config.ts",
                18,
                "https://saksk.top/api",
            ),
            "typescript_symbol": legacy_source_line(
                legacy_root, endpoint, 783, "getBankUsageStats: (bankId: number) =>"
            ),
            "relative_endpoint": legacy_source_line(
                legacy_root, endpoint, 784, "/usage-stats`, 'GET')"
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
            },
            "result": "the /api base plus the relative /user/banks/api path selects the API alias",
        },
        "page_activation": {
            "subpackage_registration": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/app.json",
                83,
                '"root": "pages/bank-detail"',
            ),
            "navigation_reference": legacy_source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/my-banks-v2/my-banks-v2.ts",
                250,
                "/pages/bank-detail/bank-detail?id=${id}",
            ),
            "on_show_share_tab": legacy_source_line(
                legacy_root, page, 322, "this.loadUsageStats();"
            ),
            "tab_tap": legacy_source_line(
                legacy_root, page, 634, "this.loadUsageStats();"
            ),
            "go_share_tab": legacy_source_line(
                legacy_root, page, 701, "this.loadUsageStats();"
            ),
            "after_share_prepare": legacy_source_line(
                legacy_root, page, 1972, "this.loadUsageStats();"
            ),
            "after_revoke": legacy_source_line(
                legacy_root, page, 2099, "this.loadUsageStats();"
            ),
        },
        "load_function": legacy_source_line(
            legacy_root, page, 1983, "async loadUsageStats()"
        ),
        "owner_guard": legacy_source_line(
            legacy_root, page, 1986, "if (!this.data.canManageShare) return;"
        ),
        "direct_call": legacy_source_line(
            legacy_root, page, 1991, "api.getBankUsageStats(bankId)"
        ),
        "mapped_response_fields": response_fields,
        "rendered_field": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.wxml",
            741,
            "usageStats.total_users",
        ),
        "reason": (
            "the registered bank-detail page is reachable from the bank list and invokes the "
            "TypeScript endpoint for owner share-tab and share lifecycle flows"
        ),
    }


def generated_javascript_attestation(legacy_root: Path) -> dict[str, Any]:
    pairs = []
    for source, generated in (
        (
            "miniprogram-1/miniprogram/utils/api-endpoints.ts",
            "miniprogram-1/miniprogram/utils/api-endpoints.js",
        ),
        (
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
        ),
    ):
        pairs.append({
            "typescript_source": source,
            "typescript_sha256": hashlib.sha256(
                read_legacy_blob(legacy_root, source)
            ).hexdigest(),
            "generated_javascript": generated,
            "generated_javascript_sha256": hashlib.sha256(
                read_legacy_blob(legacy_root, generated)
            ).hexdigest(),
            "caller_counting": (
                "one logical caller family; generated JavaScript is executable evidence but is "
                "not counted as an independent source-authored caller"
            ),
        })
    return {
        "state": "generated_runtime_mirror_of_typescript_caller",
        "compiled_endpoint_symbol": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/api-endpoints.js",
            437,
            "getBankUsageStats: function (bankId)",
        ),
        "compiled_relative_endpoint": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/utils/api-endpoints.js",
            438,
            '"/usage-stats"), \'GET\')',
        ),
        "compiled_direct_call": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2185,
            "api_1.api.getBankUsageStats(bankId)",
        ),
        "compiled_total_users_mapping": legacy_source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2196,
            "data.total_users",
        ),
        "source_generated_pairs": pairs,
        "additional_independent_caller_count": 0,
    }


def controlled_copy_attestation(legacy_root: Path) -> dict[str, Any]:
    if not CONTROLLED_MINIPROGRAM.is_dir():
        raise AssertionError(
            f"controlled miniprogram root is missing: {CONTROLLED_MINIPROGRAM}"
        )
    files = []
    for legacy_path, controlled_path in CONTROLLED_COPY_PAIRS:
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
    return {
        "state": "active_controlled_migration_copy",
        "scope": "Ti-Java/miniprogram",
        "baseline_relationship": (
            "the independently maintained Ti-Java miniprogram copy retains the exact fixed-commit "
            "usage-stats caller bytes; it is attested separately from legacy caller counting"
        ),
        "typescript_endpoint": controlled_source_line(
            "miniprogram/miniprogram/utils/api-endpoints.ts",
            784,
            "/usage-stats`, 'GET')",
        ),
        "typescript_direct_call": controlled_source_line(
            "miniprogram/miniprogram/pages/bank-detail/bank-detail.ts",
            1991,
            "api.getBankUsageStats(bankId)",
        ),
        "generated_javascript_endpoint": controlled_source_line(
            "miniprogram/miniprogram/utils/api-endpoints.js",
            438,
            '"/usage-stats"), \'GET\')',
        ),
        "generated_javascript_call": controlled_source_line(
            "miniprogram/miniprogram/pages/bank-detail/bank-detail.js",
            2185,
            "api_1.api.getBankUsageStats(bankId)",
        ),
        "rendered_field": controlled_source_line(
            "miniprogram/miniprogram/pages/bank-detail/bank-detail.wxml",
            741,
            "usageStats.total_users",
        ),
        "byte_equal_files": files,
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
    if scan["match_count"] != 39:
        raise AssertionError(
            "fixed-commit usage-stats capability scan drifted: "
            f"expected 39 matches, got {scan['match_count']}"
        )
    handler = handler_and_alias_attestation(legacy_root)
    web = web_caller_attestation(legacy_root)
    miniprogram = legacy_miniprogram_attestation(legacy_root)
    generated = generated_javascript_attestation(legacy_root)
    controlled = controlled_copy_attestation(legacy_root)
    caller_counting = {
        "fixed_commit_legacy_logical_caller_count": 2,
        "fixed_commit_legacy_logical_callers": [
            web["logical_caller_id"],
            miniprogram["logical_caller_id"],
        ],
        "generated_javascript_additional_count": 0,
        "controlled_copy_counting": (
            "separate migration-project counterpart; not added to the fixed-commit legacy count"
        ),
        "both_legacy_caller_families_active": True,
    }
    closure = {
        "fixed_commit_resolved": True,
        "full_repository_scan_captured": True,
        "shared_handler_closed": handler["handler"]["line"] == 58,
        "both_registered_aliases_closed": (
            handler["web_alias_registration"]["route_id"] == "22aecd49a3c2"
            and handler["api_alias_registration"]["route_id"] == "d67a16965b08"
        ),
        "active_web_caller_closed": web["state"] == "active",
        "active_legacy_miniprogram_caller_closed": miniprogram["state"] == "active",
        "typescript_generated_mirror_closed": (
            generated["additional_independent_caller_count"] == 0
        ),
        "controlled_miniprogram_copy_closed": all(
            item["byte_equal"] for item in controlled["byte_equal_files"]
        ),
        "generated_files_not_double_counted": (
            caller_counting["generated_javascript_additional_count"] == 0
        ),
        "caller_attestation_complete": True,
    }
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-usage-stats-caller-attestation",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "legacy_commit": LEGACY_COMMIT,
        "routes": list(ROUTES),
        "full_repository_scan": scan,
        "handler_and_aliases": handler,
        "callers": {
            "web_template": web,
            "legacy_miniprogram_typescript": miniprogram,
            "legacy_miniprogram_generated_javascript": generated,
            "ti_java_controlled_miniprogram_copy": controlled,
        },
        "caller_counting": caller_counting,
        "frozen_route_matrix_disposition": {
            "matrix_is_immutable": True,
            "matrix_static_scan_is_not_a_complete_caller_inventory": True,
            "dynamic_web_template_caller_is_closed_here": True,
            "resolution": (
                "this additive fixed-commit attestation records active callers without editing "
                "the route matrix, OpenAPI, production Java or migration contracts"
            ),
        },
        "closure": closure,
    }
    document["attestation_sha256"] = sha256_json({
        "routes": document["routes"],
        "full_repository_scan": document["full_repository_scan"],
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
        "captured personal-bank usage-stats callers "
        f"matches={document['full_repository_scan']['match_count']} "
        f"legacy_logical_callers={document['caller_counting']['fixed_commit_legacy_logical_caller_count']} "
        f"attestation_sha256={document['attestation_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
