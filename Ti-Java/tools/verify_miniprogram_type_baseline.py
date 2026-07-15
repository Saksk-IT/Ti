#!/usr/bin/env python3
"""Verify the exact pre-existing TypeScript error baseline for both mini-program trees."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = PROJECT_ROOT / "docs" / "refactor" / "miniprogram-type-baseline.json"
ERROR_PATTERN = re.compile(r"error (TS\d+):")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    return parser.parse_args()


def run_tsc(tsc: Path, project: Path) -> tuple[int, list[str]]:
    result = subprocess.run(
        [str(tsc), "-p", str(project / "tsconfig.json"), "--noEmit", "--pretty", "false"],
        cwd=project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    return result.returncode, [line for line in result.stdout.splitlines() if ERROR_PATTERN.search(line)]


def normalized_errors(lines: list[str], root: Path) -> Counter[str]:
    root_text = str(root.resolve())
    return Counter(line.replace(root_text, "<MINIPROGRAM>") for line in lines)


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    baseline: dict[str, Any] = json.loads(args.baseline.read_text(encoding="utf-8"))
    legacy = legacy_root / "miniprogram-1"
    controlled = PROJECT_ROOT / "miniprogram"
    tsc = legacy / "node_modules" / ".bin" / "tsc"
    if not tsc.is_file():
        raise SystemExit(f"TypeScript compiler not found: {tsc}")

    legacy_code, legacy_errors = run_tsc(tsc, legacy)
    controlled_code, controlled_errors = run_tsc(tsc, controlled)
    archived_errors = [line for line in legacy_errors if line.startswith("_archived/")]
    active_legacy_errors = [line for line in legacy_errors if not line.startswith("_archived/")]
    legacy_codes = sorted({match.group(1) for line in legacy_errors if (match := ERROR_PATTERN.search(line))})
    controlled_codes = sorted(
        {match.group(1) for line in controlled_errors if (match := ERROR_PATTERN.search(line))}
    )
    active_match = normalized_errors(active_legacy_errors, legacy) == normalized_errors(
        controlled_errors,
        controlled,
    )
    result = {
        "legacy": {"exit_code": legacy_code, "errors": len(legacy_errors), "codes": legacy_codes},
        "controlled_copy": {
            "exit_code": controlled_code,
            "errors": len(controlled_errors),
            "codes": controlled_codes,
        },
        "archived_only_errors": len(archived_errors),
        "active_error_multiset_matches": active_match,
    }
    expected_exit = baseline.get("typescript_exit_code")
    result["matches_baseline"] = bool(
        legacy_code == controlled_code == expected_exit
        and len(legacy_errors) == baseline.get("legacy", {}).get("errors")
        and legacy_codes == baseline.get("legacy", {}).get("codes")
        and len(controlled_errors) == baseline.get("controlled_copy", {}).get("errors")
        and controlled_codes == baseline.get("controlled_copy", {}).get("codes")
        and len(archived_errors) == baseline.get("intentional_difference", {}).get("errors")
        and all("TS2393" in line for line in archived_errors)
        and active_match
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["matches_baseline"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
