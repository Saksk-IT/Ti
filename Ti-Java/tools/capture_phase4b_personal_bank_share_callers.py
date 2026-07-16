#!/usr/bin/env python3
"""Capture deterministic fixed-commit caller evidence for personal-bank share reads."""

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
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


ROUTES = (
    {
        "route_id": "e817f8083d74",
        "path": "/api/user/banks/api/<int:bank_id>/shares",
        "surface": "miniprogram",
    },
    {
        "route_id": "c50102968322",
        "path": "/user/banks/api/<int:bank_id>/shares",
        "surface": "web",
    },
)
SCAN_PATTERN = r"getBankShares|/shares|bank_manage_shares|bank-share"
SCAN_EXCLUSIONS = ("miniprogram-1/analyse-data.json",)


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


def read_blob(legacy_root: Path, path: str) -> bytes:
    return pinned_source._run_read_only_git(
        legacy_root,
        "show",
        f"{pinned_source.LEGACY_COMMIT}:{path}",
    )


def source_line(legacy_root: Path, path: str, line: int, contains: str) -> dict[str, Any]:
    payload = read_blob(legacy_root, path)
    lines = payload.decode("utf-8").splitlines()
    if line < 1 or line > len(lines):
        raise AssertionError(f"fixed-commit source line is out of range: {path}:{line}")
    text = lines[line - 1].strip()
    if contains not in text:
        raise AssertionError(
            f"fixed-commit caller drifted at {path}:{line}: expected {contains!r}, got {text!r}"
        )
    return {
        "source": path,
        "line": line,
        "text": text,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_size_bytes": len(payload),
    }


def full_repository_share_scan(legacy_root: Path) -> dict[str, Any]:
    raw = pinned_source._run_read_only_git(
        legacy_root,
        "grep",
        "-n",
        "-I",
        "-E",
        SCAN_PATTERN,
        pinned_source.LEGACY_COMMIT,
        "--",
        ".",
        ":(exclude)miniprogram-1/analyse-data.json",
    ).decode("utf-8")
    matches: list[dict[str, Any]] = []
    prefix = pinned_source.LEGACY_COMMIT + ":"
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
        raise AssertionError("fixed-commit share caller scan unexpectedly returned no matches")
    source_roots = sorted({item["source"].split("/", 1)[0] for item in matches})
    return {
        "command": "git grep -n -I -E <pattern> <fixed-commit> -- . <exclusions>",
        "pattern": SCAN_PATTERN,
        "scope": "all executable, template, test and configuration text blobs at the fixed legacy commit",
        "excluded_generated_inventory_files": list(SCAN_EXCLUSIONS),
        "exclusion_reason": (
            "analyse-data.json is a one-line generated bundle inventory, not executable source; "
            "its embedded filenames would duplicate source matches and inflate the evidence"
        ),
        "match_count": len(matches),
        "matched_source_count": len({item["source"] for item in matches}),
        "matched_source_roots": source_roots,
        "matches_sha256": sha256_json(matches),
        "matches": matches,
    }


def web_caller_attestation(legacy_root: Path) -> dict[str, Any]:
    direct_get = source_line(
        legacy_root,
        "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
        220,
        "window.ubmApi(`/user/banks/api/${encodeURIComponent(bankId)}/shares`)",
    )
    render = source_line(
        legacy_root,
        "app/modules/user_bank/routes/pages.py",
        785,
        "user_bank/manage/bank_manage_shares.html",
    )
    page_route = source_line(
        legacy_root,
        "app/modules/user_bank/routes/pages.py",
        769,
        "@user_bank_pages_bp.route('/<int:bank_id>/shares')",
    )
    navigation = [
        source_line(
            legacy_root,
            "app/modules/user_bank/templates/user_bank/manage/_bank_manage_basebar.html",
            9,
            "href=\"/user/banks/{{ bank_id }}/shares\"",
        ),
        source_line(
            legacy_root,
            "app/modules/user_bank/templates/user_bank/manage/manage_base.html",
            357,
            "href=\"/user/banks/{{ bank_id }}/shares\"",
        ),
        source_line(
            legacy_root,
            "app/modules/user_bank/templates/user_bank/manage/banks.html",
            1043,
            "/user/banks/${bank.id}/shares",
        ),
    ]
    private_only_guard = source_line(
        legacy_root,
        "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
        160,
        "{% if not is_public %}",
    )
    page_load = source_line(
        legacy_root,
        "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
        430,
        "loadShares();",
    )
    optional_share_link_branch = {
        "guard": source_line(
            legacy_root,
            "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
            293,
            "if (s.share_link)",
        ),
        "copy_action": source_line(
            legacy_root,
            "app/modules/user_bank/templates/user_bank/manage/bank_manage_shares.html",
            298,
            "String(s.share_link)",
        ),
        "server_contract": (
            "optional client compatibility branch only; share_link is absent from the "
            "legacy eleven-column bank_shares projection and must not be synthesized"
        ),
    }
    required_fields = {
        "id": "revocation action",
        "share_code": "label and copy action",
        "current_uses": "usage label",
        "max_uses": "usage limit label",
        "expires_at": "expiry label",
        "created_at": "creation label",
        "is_active": "inactive badge and revocation visibility",
        "share_link": "optional copy-link branch; absent from the legacy raw table projection",
    }
    return {
        "state": "active",
        "actual_alias": "/user/banks/api/<bank_id>/shares",
        "page_route": page_route,
        "render_reference": render,
        "navigation_references": navigation,
        "private_bank_only_guard": private_only_guard,
        "page_load_trigger": page_load,
        "direct_get": direct_get,
        "optional_share_link_branch": optional_share_link_branch,
        "response_envelope": "code/status plus data.shares array",
        "consumed_fields": required_fields,
        "error_behavior": "load failure clears the list and renders the thrown message",
        "reason": (
            "the owner-only page route renders the direct caller, the private-bank script invokes "
            "it on page load, and multiple live management surfaces navigate to that page"
        ),
    }


def miniprogram_caller_attestation(legacy_root: Path) -> dict[str, Any]:
    endpoint = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        780,
        "request(`/user/banks/api/${bankId}/shares`, 'GET')",
    )
    production_base = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/utils/config.ts",
        18,
        "https://saksk.top/api",
    )
    request_base_lookup = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/utils/api-client.ts",
        105,
        "const apiBaseUrl = getApiBaseUrl();",
    )
    request_url_concatenation = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/utils/api-client.ts",
        110,
        "url: `${apiBaseUrl}${url}`",
    )
    compiled_endpoint = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/utils/api-endpoints.js",
        434,
        '"/user/banks/api/".concat(bankId, "/shares")',
    )
    detail_call = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        1888,
        "api.getBankShares(bankId)",
    )
    detail_activation = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        542,
        "tab === 'share' && canManageShare",
    )
    detail_navigation = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/my-banks-v2/my-banks-v2.ts",
        250,
        "/pages/bank-detail/bank-detail?id=${id}",
    )
    detail_registration = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/app.json",
        83,
        "\"root\": \"pages/bank-detail\"",
    )
    dedicated_registration = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/app.json",
        51,
        "\"pages/bank-share/bank-share\"",
    )
    dedicated_call = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/bank-share/bank-share.ts",
        56,
        "api.getBankShares(this.data.bankId)",
    )
    ordinary_tab_behavior = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        634,
        "this.loadUsageStats();",
    )
    wechat_prepare_trigger = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        1955,
        "await this.loadShares();",
    )
    join_deep_link = source_line(
        legacy_root,
        "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
        2117,
        "/pages/bank-join/bank-join?token=",
    )
    detail_compiled_runtime = {
        "call": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2043,
            "api_1.api.getBankShares(bankId)",
        ),
        "active_filter": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2049,
            "s.is_active",
        ),
        "token_picker_call": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2055,
            "this.pickShareTokenFromShares(shares)",
        ),
        "order_preserving_iteration": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2096,
            "list_1 = list",
        ),
        "first_valid_return": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
            2107,
            "return token;",
        ),
        "ordering_contract": (
            "the compiled runtime filters in response order, iterates without sorting or "
            "reversing, and returns the first active non-expired token"
        ),
    }
    detail_wxml_consumption = {
        "fields": [
            "id",
            "share_code",
            "current_uses",
            "expires_at",
            "expires_at_display",
            "is_active",
        ],
        "sources": [
            source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.wxml",
                line,
                contains,
            )
            for line, contains in (
                (767, 'wx:key="id"'),
                (770, "item.share_code"),
                (774, "item.current_uses"),
                (775, "item.expires_at_display"),
                (780, "item.share_code"),
                (783, "item.is_active"),
            )
        ],
    }
    dedicated_compiled_runtime = {
        "call": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-share/bank-share.js",
            86,
            "api_1.api.getBankShares(this.data.bankId)",
        ),
        "active_filter": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-share/bank-share.js",
            95,
            "s.is_active",
        ),
        "token_picker_call": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-share/bank-share.js",
            108,
            "this.pickShareTokenFromShares(shares)",
        ),
        "order_preserving_iteration": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-share/bank-share.js",
            137,
            "list_1 = list",
        ),
        "first_valid_return": source_line(
            legacy_root,
            "miniprogram-1/miniprogram/pages/bank-share/bank-share.js",
            146,
            "return token;",
        ),
        "ordering_contract": (
            "the compiled runtime filters in response order, iterates without sorting or "
            "reversing, and returns the first active non-expired token"
        ),
    }
    dedicated_wxml_consumption = {
        "fields": [
            "id",
            "share_code",
            "current_uses",
            "expires_at",
            "expires_at_display",
        ],
        "sources": [
            source_line(
                legacy_root,
                "miniprogram-1/miniprogram/pages/bank-share/bank-share.wxml",
                line,
                contains,
            )
            for line, contains in (
                (41, 'wx:key="id"'),
                (44, "item.share_code"),
                (48, "item.current_uses"),
                (49, "item.expires_at_display"),
                (54, "item.share_code"),
                (57, "item.id"),
            )
        ],
    }
    required_fields = {
        "id": "list key and revoke action",
        "share_code": "display and copy action",
        "share_token": "first active non-expired WeChat share candidate",
        "expires_at": "display and client-side expiry filtering",
        "current_uses": "usage label",
        "is_active": "client-side list filter and revoke visibility",
    }
    return {
        "actual_alias": "/api/user/banks/api/<bank_id>/shares",
        "path_derivation": {
            "production_api_base": production_base,
            "relative_endpoint": endpoint,
            "compiled_relative_endpoint": compiled_endpoint,
            "request_url_composition": {
                "base_lookup": request_base_lookup,
                "concatenation": request_url_concatenation,
            },
            "result": "the /api base plus /user/banks/api/... selects the compatibility alias",
        },
        "active_bank_detail": {
            "state": "active",
            "subpackage_registration": detail_registration,
            "navigation_reference": detail_navigation,
            "share_tab_activation": detail_activation,
            "call": detail_call,
            "compiled_runtime": detail_compiled_runtime,
            "wxml_consumption": detail_wxml_consumption,
            "wechat_share_prepare_trigger": wechat_prepare_trigger,
            "ordinary_tab_tap_observation": {
                "source": ordinary_tab_behavior,
                "behavior": (
                    "an ordinary share-tab tap loads usage stats only; it does not itself call "
                    "loadShares, while initial tab=share, WeChat preparation, create and revoke "
                    "flows can call or refresh the list"
                ),
            },
            "join_deep_link": {
                "source": join_deep_link,
                "relationship": (
                    "consumes a share_token selected from the list but does not call either GET alias"
                ),
            },
        },
        "dedicated_bank_share_page": {
            "state": "dormant_external_entry_candidate",
            "registration": dedicated_registration,
            "call": dedicated_call,
            "compiled_runtime": dedicated_compiled_runtime,
            "wxml_consumption": dedicated_wxml_consumption,
            "reason": (
                "the page is registered and executable for a direct external entry, but the "
                "fixed-commit repository scan contains no internal navigation to it"
            ),
        },
        "response_envelope": (
            "the shared request client unwraps successful result.data before page code reads shares"
        ),
        "consumed_fields": required_fields,
        "client_filter": "both pages remove rows whose is_active value is falsy",
        "ordering_dependency": (
            "pickShareTokenFromShares selects the first active non-expired share_token, so the "
            "server order remains observable"
        ),
    }


def dormant_and_generated_attestation(legacy_root: Path) -> dict[str, Any]:
    dormant = [
        {
            "state": "orphan_template",
            "direct_get": source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/manage/shares.html",
                210,
                "api(`/user/banks/api/${bankId}/shares`)",
            ),
            "render_or_include_references": [],
        },
        {
            "state": "orphan_partial",
            "direct_get": source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/bank/bank_practice/body_end/_09_share_manage.html",
                139,
                "fetch(`/user/banks/api/${BANK_ID}/shares`",
            ),
            "render_or_include_references": [],
            "active_composition_proof": source_line(
                legacy_root,
                "app/modules/user_bank/templates/user_bank/bank/bank_practice/_body_end.html",
                9,
                "_07_share_basic.html",
            ),
            "reason": "the active composition includes _07_share_basic and never includes _09_share_manage",
        },
    ]
    generated_mirrors = [
        {
            "source": "miniprogram-1/miniprogram/utils/api-endpoints.ts",
            "generated": "miniprogram-1/miniprogram/utils/api-endpoints.js",
        },
        {
            "source": "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.ts",
            "generated": "miniprogram-1/miniprogram/pages/bank-detail/bank-detail.js",
        },
        {
            "source": "miniprogram-1/miniprogram/pages/bank-share/bank-share.ts",
            "generated": "miniprogram-1/miniprogram/pages/bank-share/bank-share.js",
        },
    ]
    for pair in generated_mirrors:
        pair["source_sha256"] = hashlib.sha256(
            read_blob(legacy_root, pair["source"])
        ).hexdigest()
        pair["generated_sha256"] = hashlib.sha256(
            read_blob(legacy_root, pair["generated"])
        ).hexdigest()
        pair["caller_counting"] = "one logical caller; generated JavaScript is not counted twice"
    backend_tests = {
        "state": "no_direct_get_coverage",
        "source": "tests/test_user_bank_shares.py",
        "same_path_occurrences": [
            {
                "method": "POST",
                "source": source_line(
                    legacy_root,
                    "tests/test_user_bank_shares.py",
                    line,
                    "f\"/api/user/banks/api/{bank_id}/shares\"",
                ),
            }
            for line in (103, 129, 168)
        ],
        "delete_occurrence": {
            "method": "DELETE",
            "source": source_line(
                legacy_root,
                "tests/test_user_bank_shares.py",
                190,
                "/shares/{share_id}",
            ),
        },
        "reason": "same-path POST and child-path DELETE coverage must not be counted as GET coverage",
    }
    return {
        "dormant_or_orphan_callers": dormant,
        "generated_mirrors": generated_mirrors,
        "backend_test_coverage": backend_tests,
    }


def capture_document(legacy_root: Path) -> dict[str, Any]:
    resolved = pinned_source._run_read_only_git(
        legacy_root,
        "rev-parse",
        "--verify",
        f"{pinned_source.LEGACY_COMMIT}^{{commit}}",
    ).decode("utf-8").strip()
    if resolved != pinned_source.LEGACY_COMMIT:
        raise AssertionError(f"legacy commit resolution drifted: {resolved}")

    scan = full_repository_share_scan(legacy_root)
    web = web_caller_attestation(legacy_root)
    miniprogram = miniprogram_caller_attestation(legacy_root)
    residual = dormant_and_generated_attestation(legacy_root)
    closure = {
        "fixed_commit_resolved": True,
        "full_repository_scan_captured": True,
        "active_web_caller_closed": web["state"] == "active",
        "active_miniprogram_caller_closed": (
            miniprogram["active_bank_detail"]["state"] == "active"
        ),
        "deep_link_capable_page_closed": (
            miniprogram["dedicated_bank_share_page"]["state"]
            == "dormant_external_entry_candidate"
        ),
        "dormant_and_generated_sources_classified": True,
        "request_url_composition_closed": (
            miniprogram["path_derivation"]["request_url_composition"]
            ["concatenation"]["line"] == 110
        ),
        "compiled_runtime_behavior_closed": (
            miniprogram["active_bank_detail"]["compiled_runtime"]
            ["first_valid_return"]["line"] == 2107
            and miniprogram["dedicated_bank_share_page"]["compiled_runtime"]
            ["first_valid_return"]["line"] == 146
        ),
        "wxml_consumption_closed": bool(
            miniprogram["active_bank_detail"]["wxml_consumption"]["sources"]
            and miniprogram["dedicated_bank_share_page"]["wxml_consumption"]["sources"]
        ),
        "optional_share_link_branch_closed": (
            web["optional_share_link_branch"]["guard"]["line"] == 293
        ),
        "caller_attestation_complete": True,
    }
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-share-list-caller-attestation",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "legacy_commit": pinned_source.LEGACY_COMMIT,
        "routes": list(ROUTES),
        "full_repository_scan": scan,
        "callers": {
            "web": web,
            "miniprogram": miniprogram,
            **residual,
        },
        "frozen_route_matrix_disposition": {
            "matrix_is_immutable": True,
            "matrix_rows_are_not_a_complete_caller_inventory": True,
            "api_row_only_names_the_miniprogram_endpoint_definition": True,
            "web_row_names_an_orphan_partial_instead_of_the_rendered_management_page": True,
            "resolution": "this fixed-commit attestation is the additive Phase 4B caller authority",
        },
        "closure": closure,
    }
    document["attestation_sha256"] = sha256_json({
        "routes": document["routes"],
        "full_repository_scan": document["full_repository_scan"],
        "callers": document["callers"],
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
        "captured personal-bank share callers "
        f"matches={document['full_repository_scan']['match_count']} "
        f"attestation_sha256={document['attestation_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
