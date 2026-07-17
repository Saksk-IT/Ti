#!/usr/bin/env python3
"""Capture fixed-commit caller evidence for the personal-bank all-shares read."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as pinned_source  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
ROUTES = (
    {
        "route_id": "a6fda3638fc3",
        "path": "/api/user/banks/api/shares/all",
        "surface": "external_api_compatibility_alias",
    },
    {
        "route_id": "0fdd3026f636",
        "path": "/user/banks/api/shares/all",
        "surface": "external_web_compatibility_alias",
    },
)
DIRECT_ALIAS_PATTERNS = tuple(route["path"] for route in ROUTES)
CAPABILITY_PATTERN = r"shares/all|getAllShares|allShares|shares_manage_all|manage/shares"
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
        f"{LEGACY_COMMIT}:{path}",
    )


def source_line(legacy_root: Path, path: str, line: int, contains: str) -> dict[str, Any]:
    payload = read_blob(legacy_root, path)
    lines = payload.decode("utf-8").splitlines()
    if line < 1 or line > len(lines):
        raise AssertionError(f"fixed-commit source line is out of range: {path}:{line}")
    text = lines[line - 1].strip()
    if contains not in text:
        raise AssertionError(
            f"fixed-commit caller drifted at {path}:{line}: "
            f"expected {contains!r}, got {text!r}"
        )
    return {
        "source": path,
        "line": line,
        "text": text,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_size_bytes": len(payload),
    }


def fixed_commit_grep(
    legacy_root: Path,
    patterns: tuple[str, ...],
    *,
    extended: bool,
    paths: tuple[str, ...] = (".",),
    exclusions: tuple[str, ...] = SCAN_EXCLUSIONS,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    arguments = ["grep", "-n", "-I", "-E" if extended else "-F"]
    for pattern in patterns:
        arguments.extend(("-e", pattern))
    arguments.extend((LEGACY_COMMIT, "--", *paths))
    arguments.extend(f":(exclude){path}" for path in exclusions)
    result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(legacy_root),
            *arguments,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
        env=environment,
    )
    if result.returncode not in (0, 1):
        detail = result.stderr.decode("utf-8", errors="replace")[-2000:].strip()
        raise AssertionError(f"fixed-commit git grep failed: {detail}")

    prefix = LEGACY_COMMIT + ":"
    matches: list[dict[str, Any]] = []
    for raw_line in result.stdout.decode("utf-8").splitlines():
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
    return {
        "command": "git grep -n -I with fixed strings or extended regex at the fixed commit",
        "match_mode": "extended_regex" if extended else "fixed_string",
        "patterns": list(patterns),
        "scope_paths": list(paths),
        "excluded_generated_inventory_files": list(exclusions),
        "match_count": len(matches),
        "matched_source_count": len({item["source"] for item in matches}),
        "matched_source_roots": sorted({item["source"].split("/", 1)[0] for item in matches}),
        "matches_sha256": sha256_json(matches),
        "matches": matches,
    }


def direct_caller_attestation(legacy_root: Path) -> dict[str, Any]:
    scan = fixed_commit_grep(
        legacy_root,
        DIRECT_ALIAS_PATTERNS,
        extended=False,
    )
    expected = [{
        "source": "app/modules/user_bank/templates/user_bank/manage/shares_manage_all.html",
        "line": 185,
        "text": "const res = await api('/user/banks/api/shares/all');",
    }]
    if scan["matches"] != expected:
        raise AssertionError(
            "fixed-commit all-shares direct caller set drifted: "
            f"expected {expected!r}, got {scan['matches']!r}"
        )

    caller = source_line(
        legacy_root,
        "app/modules/user_bank/templates/user_bank/manage/shares_manage_all.html",
        185,
        "api('/user/banks/api/shares/all')",
    )
    return {
        "state": "unique_direct_caller_in_dormant_template",
        "actual_alias": "/user/banks/api/shares/all",
        "full_repository_direct_alias_scan": scan,
        "direct_get": caller,
        "response_extraction": source_line(
            legacy_root,
            caller["source"],
            186,
            "allShares = res.data.shares || [];",
        ),
        "load_trigger": source_line(
            legacy_root,
            caller["source"],
            370,
            "loadShares();",
        ),
        "consumed_fields": {
            "bank_name": "client-side keyword filter and card title",
            "share_code": "keyword filter, display and copy action",
            "share_token": "client-side keyword filter",
            "is_active": "status filter, badge and revoke visibility",
            "permission": "permission filter",
            "created_at": "creation label",
            "expires_at": "expiry label",
            "used_count": (
                "usage display; this legacy client field name does not match the raw "
                "bank_shares.current_uses projection"
            ),
            "max_uses": "usage limit label",
            "share_link": "link display and copy action",
            "bank_id": "child share page, records and revoke actions",
            "id": "records and revoke actions",
        },
        "usage_count_field_mismatch": {
            "client_read": source_line(
                legacy_root,
                caller["source"],
                348,
                "s.used_count || 0",
            ),
            "server_raw_projection": source_line(
                legacy_root,
                "app/modules/user_bank/routes/api_shares.py",
                159,
                "SELECT bs.*",
            ),
            "legacy_server_column": "current_uses",
            "behavior": (
                "the dormant template reads used_count, while bs.* exposes current_uses; "
                "the display therefore falls back to zero unless an external layer adds used_count"
            ),
        },
    }


def page_tombstone_attestation(legacy_root: Path) -> dict[str, Any]:
    render_reference_scan = fixed_commit_grep(
        legacy_root,
        ("shares_manage_all.html",),
        extended=False,
    )
    if render_reference_scan["matches"]:
        raise AssertionError(
            "fixed-commit dormant all-shares template gained a render/include reference"
        )
    return {
        "state": "page_entry_retired_with_404",
        "route": source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            36,
            "@user_bank_pages_bp.route('/manage/shares')",
        ),
        "authentication": source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            37,
            "@login_required",
        ),
        "handler": source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            38,
            "def manage_shares():",
        ),
        "terminal_response": source_line(
            legacy_root,
            "app/modules/user_bank/routes/pages.py",
            40,
            'return "页面已下线", 404',
        ),
        "template_render_or_include_scan": render_reference_scan,
        "conclusion": (
            "the only direct caller remains in an orphan template; the registered page entry "
            "returns 404 and the fixed commit has no render/include reference to that template"
        ),
    }


def miniprogram_absence_attestation(legacy_root: Path) -> dict[str, Any]:
    scan = fixed_commit_grep(
        legacy_root,
        (CAPABILITY_PATTERN,),
        extended=True,
        paths=("miniprogram-1",),
    )
    if scan["matches"]:
        raise AssertionError(
            "fixed-commit all-shares capability unexpectedly gained a miniprogram caller"
        )
    return {
        "state": "no_miniprogram_caller",
        "full_miniprogram_text_scan": scan,
        "conclusion": (
            "no endpoint literal, wrapper symbol, template name or page-entry token for the "
            "all-shares capability exists in fixed-commit miniprogram text blobs"
        ),
    }


def external_compatibility_attestation(legacy_root: Path) -> dict[str, Any]:
    route_source = "app/modules/user_bank/routes/api_shares.py"
    registration_source = "app/modules/user_bank/__init__.py"
    return {
        "state": "both_http_aliases_remain_externally_registered",
        "relative_route": source_line(
            legacy_root,
            route_source,
            152,
            "@user_bank_api_bp.route('/shares/all', methods=['GET'])",
        ),
        "handler": source_line(
            legacy_root,
            route_source,
            154,
            "def get_all_shares():",
        ),
        "web_alias_registration": {
            "outer_prefix": source_line(
                legacy_root,
                registration_source,
                15,
                "url_prefix='/user/banks'",
            ),
            "nested_prefix": source_line(
                legacy_root,
                registration_source,
                17,
                "url_prefix='/api'",
            ),
            "application_registration": source_line(
                legacy_root,
                registration_source,
                18,
                "app.register_blueprint(user_bank_bp)",
            ),
            "composed_path": "/user/banks/api/shares/all",
            "route_id": "0fdd3026f636",
        },
        "api_alias_registration": {
            "outer_prefix": source_line(
                legacy_root,
                registration_source,
                23,
                "url_prefix='/api'",
            ),
            "nested_prefix": source_line(
                legacy_root,
                registration_source,
                24,
                "url_prefix='/user/banks/api'",
            ),
            "application_registration": source_line(
                legacy_root,
                registration_source,
                25,
                "app.register_blueprint(api_root_bp)",
            ),
            "composed_path": "/api/user/banks/api/shares/all",
            "route_id": "a6fda3638fc3",
        },
        "compatibility_boundary": (
            "caller dormancy does not authorize deleting either registered legacy GET alias; "
            "both remain external compatibility operations"
        ),
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

    capability_scan = fixed_commit_grep(
        legacy_root,
        (CAPABILITY_PATTERN,),
        extended=True,
    )
    if capability_scan["match_count"] != 6:
        raise AssertionError(
            "fixed-commit all-shares capability scan drifted: "
            f"expected 6 matches, got {capability_scan['match_count']}"
        )

    direct = direct_caller_attestation(legacy_root)
    tombstone = page_tombstone_attestation(legacy_root)
    miniprogram = miniprogram_absence_attestation(legacy_root)
    compatibility = external_compatibility_attestation(legacy_root)
    closure = {
        "fixed_commit_resolved": True,
        "full_repository_capability_scan_captured": True,
        "unique_direct_caller_closed": (
            direct["full_repository_direct_alias_scan"]["match_count"] == 1
        ),
        "unique_direct_caller_is_dormant": (
            direct["state"] == "unique_direct_caller_in_dormant_template"
        ),
        "page_entry_404_tombstone_closed": (
            tombstone["terminal_response"]["line"] == 40
        ),
        "template_render_or_include_absence_closed": (
            tombstone["template_render_or_include_scan"]["match_count"] == 0
        ),
        "miniprogram_caller_absence_closed": (
            miniprogram["full_miniprogram_text_scan"]["match_count"] == 0
        ),
        "web_external_compatibility_alias_closed": (
            compatibility["web_alias_registration"]["composed_path"]
            == "/user/banks/api/shares/all"
        ),
        "api_external_compatibility_alias_closed": (
            compatibility["api_alias_registration"]["composed_path"]
            == "/api/user/banks/api/shares/all"
        ),
        "caller_attestation_complete": True,
    }
    document: dict[str, Any] = {
        "contract_id": "ti.phase4b.personal-bank-all-shares-caller-attestation",
        "schema_version": 1,
        "captured_at": "2026-07-17",
        "legacy_commit": LEGACY_COMMIT,
        "routes": list(ROUTES),
        "full_repository_capability_scan": capability_scan,
        "callers": {
            "direct": direct,
            "page_entry": tombstone,
            "miniprogram": miniprogram,
        },
        "external_compatibility": compatibility,
        "frozen_route_matrix_disposition": {
            "matrix_is_immutable": True,
            "both_rows_report_not_found_static_scan": True,
            "fixed_commit_scan_proves_one_direct_web_caller": True,
            "caller_is_not_an_active_page_entry": True,
            "resolution": (
                "this additive fixed-commit attestation closes caller discovery without "
                "editing the frozen route matrix or the historical share-list evidence"
            ),
        },
        "closure": closure,
    }
    document["attestation_sha256"] = sha256_json({
        "routes": document["routes"],
        "full_repository_capability_scan": document["full_repository_capability_scan"],
        "callers": document["callers"],
        "external_compatibility": document["external_compatibility"],
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
        "captured personal-bank all-shares callers "
        f"matches={document['full_repository_capability_scan']['match_count']} "
        f"direct_callers={document['callers']['direct']['full_repository_direct_alias_scan']['match_count']} "
        f"attestation_sha256={document['attestation_sha256']} "
        f"document_sha256={document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
