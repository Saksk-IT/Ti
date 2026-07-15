#!/usr/bin/env python3
"""Run the protected legacy suite and reject failures outside the recorded allowlist."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = PROJECT_ROOT / "docs" / "refactor" / "legacy-test-baseline.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    baseline = load_json(args.baseline.resolve())
    if not (legacy_root / "app" / "__init__.py").is_file():
        raise SystemExit(f"Not a Ti legacy root: {legacy_root}")

    with tempfile.TemporaryDirectory(prefix="ti-java-legacy-suite-") as temporary:
        temporary_path = Path(temporary)
        junit = temporary_path / "pytest.xml"
        env = os.environ.copy()
        env.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "DATA_DIR": str(temporary_path / "data"),
                "RATELIMIT_STORAGE_URI": "memory://",
                "RATELIMIT_STORAGE_URL": "memory://",
            }
        )
        env.pop("REDIS_URL", None)
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={junit}",
        ]
        completed = subprocess.run(
            command,
            cwd=legacy_root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=900,
            check=False,
        )
        if not junit.is_file():
            print(completed.stdout[-5000:], file=sys.stderr)
            raise SystemExit("pytest did not produce JUnit XML")

        tree = ET.parse(junit)
        cases = list(tree.iter("testcase"))
        failures: list[dict[str, str]] = []
        errors = 0
        skipped = 0
        for case in cases:
            failure = case.find("failure")
            error = case.find("error")
            skip = case.find("skipped")
            if failure is not None:
                classname = case.attrib.get("classname", "")
                file_name = case.attrib.get("file", "")
                if not file_name and classname:
                    file_name = classname.replace(".", "/") + ".py"
                failures.append(
                    {
                        "file": file_name,
                        "classname": classname,
                        "test_name": case.attrib.get("name", ""),
                        "message": failure.attrib.get("message", ""),
                    }
                )
            if error is not None:
                errors += 1
            if skip is not None:
                skipped += 1

        warning_matches = re.findall(r"(?:^|\s)(\d+) warnings?(?:\s|,|$)", completed.stdout)
        warnings = int(warning_matches[-1]) if warning_matches else None
        core_counts = {
            "collected": len(cases),
            "passed": len(cases) - len(failures) - errors - skipped,
            "failed": len(failures),
            "skipped": skipped,
            "errors": errors,
        }
        counts = {**core_counts, "warnings": warnings}
        allowed_items = [
            item
            for item in baseline.get("allowed_failures", [])
            if isinstance(item, dict)
        ]
        allowed = {
            (str(item.get("file", "")), str(item.get("test_name", "")))
            for item in allowed_items
        }
        expected_message_fragments = {
            (str(item.get("file", "")), str(item.get("test_name", ""))): str(
                item.get("expected_message_fragment", "")
            )
            for item in allowed_items
        }
        actual_failures = {
            (item["file"], item["test_name"])
            for item in failures
        }
        signature_mismatches = [
            {
                "file": item["file"],
                "test_name": item["test_name"],
                "expected_message_fragment": expected_message_fragments.get(
                    (item["file"], item["test_name"]), ""
                ),
            }
            for item in failures
            if not expected_message_fragments.get((item["file"], item["test_name"]), "")
            or expected_message_fragments[(item["file"], item["test_name"])]
            not in item["message"]
        ]
        warning_range = baseline.get("warning_count_range")
        warnings_match = bool(
            isinstance(warnings, int)
            and isinstance(warning_range, list)
            and len(warning_range) == 2
            and all(isinstance(value, int) for value in warning_range)
            and warning_range[0] <= warnings <= warning_range[1]
        )
        result = {
            "command": command,
            "pytest_exit_code": completed.returncode,
            "counts": counts,
            "failures": failures,
            "expected_counts": baseline.get("expected"),
            "allowed_failure_ids": [list(item) for item in sorted(allowed)],
            "signature_mismatches": signature_mismatches,
            "matches_baseline": (
                completed.returncode == 1
                and core_counts == baseline.get("expected")
                and warnings_match
                and actual_failures == allowed
                and not signature_mismatches
            ),
        }
        if args.report is not None:
            report_path = args.report.resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["matches_baseline"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
