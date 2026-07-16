#!/usr/bin/env python3
"""Run the complete deterministic gate for Phase 1 architecture contracts."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFACTOR_ROOT = PROJECT_ROOT / "docs" / "refactor"
ADR_ROOT = REFACTOR_ROOT / "adr"

EXPECTED_ADRS = (
    "0001-java-25-and-spring-boot.md",
    "0002-modular-monolith.md",
    "0003-spring-mvc.md",
    "0004-database-coexistence.md",
    "0005-authentication-transition.md",
    "0006-api-contract.md",
    "0007-vue-web-migration.md",
    "0008-python-worker-boundary.md",
    "0009-reliable-events.md",
    "0010-module-dependency-dag.md",
)
REQUIRED_ADR_SECTIONS = (
    "## 上下文",
    "## 决策",
    "## 后果",
    "## 拒绝的方案",
    "## 实施与验证约束",
    "## 事实证据",
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SECRET_PATTERN = re.compile(
    r"(?:-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{12,}|"
    r"\bBearer\s+(?!synthetic-invalid-token\b)[A-Za-z0-9._~+/=-]{12,})",
    re.IGNORECASE,
)


def validate_adrs(errors: list[str]) -> None:
    actual = tuple(sorted(path.name for path in ADR_ROOT.glob("*.md")))
    if actual != EXPECTED_ADRS:
        errors.append(f"ADR set drifted: expected {EXPECTED_ADRS}, got {actual}")
        return

    for path in (ADR_ROOT / name for name in EXPECTED_ADRS):
        text = path.read_text(encoding="utf-8")
        if "- 状态：已接受" not in text:
            errors.append(f"{path.name}: status is not accepted")
        if "- 日期：2026-07-16" not in text:
            errors.append(f"{path.name}: decision date drifted")
        for section in REQUIRED_ADR_SECTIONS:
            if text.count(section) != 1:
                errors.append(f"{path.name}: section {section!r} must occur once")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b", text, re.IGNORECASE):
            errors.append(f"{path.name}: unresolved placeholder remains")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"{path.name}: broken relative link {raw_target!r}")


def validate_cross_document_contracts(errors: list[str]) -> None:
    architecture = (REFACTOR_ROOT / "01-target-architecture.md").read_text(encoding="utf-8")
    runbook = (REFACTOR_ROOT / "04-migration-runbook.md").read_text(encoding="utf-8")
    conventions = (REFACTOR_ROOT / "phase1" / "api-contract-conventions.md").read_text(
        encoding="utf-8"
    )
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    if "adrs/" in architecture:
        errors.append("target architecture still references stale adrs/ directory")
    for name in EXPECTED_ADRS:
        if f"adr/{name}" not in architecture:
            errors.append(f"target architecture index is missing adr/{name}")
    for token in (
        "OpenAPI 3.1.2",
        "phase1/module-contracts.json",
        "validate_phase1_boundaries.py",
    ):
        if token not in architecture:
            errors.append(f"target architecture is missing accepted marker {token!r}")

    for token in (
        "phase1/comparison-cutover-protocol.md",
        "validate_phase1_openapi.py",
        "validate_phase1_boundaries.py",
        "不授权执行生产操作",
    ):
        if token not in runbook:
            errors.append(f"migration runbook is missing Phase 1 marker {token!r}")

    for token in (
        "`success` 恒为 `true`",
        "`total_items`",
        "`legacyXRequestedWith`",
        "`csrfHeader` 与 `accessToken` 是目标 `/api/v1` 方案",
        "x-ti-contract-maturity",
    ):
        if token not in conventions:
            errors.append(f"API conventions are missing contract marker {token!r}")

    for token in (
        "阶段 0 事实基线与阶段 1 架构/契约已经固化",
        "generate_phase1_openapi.py",
        "validate_phase1_openapi.py",
        "validate_phase1_boundaries.py",
    ):
        if token not in readme:
            errors.append(f"README is missing Phase 1 marker {token!r}")


def validate_portability_and_secrets(errors: list[str]) -> None:
    roots = (
        PROJECT_ROOT / "contracts",
        ADR_ROOT,
        REFACTOR_ROOT / "phase1",
        PROJECT_ROOT / "tools",
    )
    for root in roots:
        for path in root.rglob("*"):
            if path.is_symlink():
                errors.append(f"symlink is forbidden in Phase 1 artifacts: {path.relative_to(PROJECT_ROOT)}")
                continue
            if not path.is_file() or path.suffix not in {".json", ".md", ".py"}:
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(
                r"/Users/[^/\s]+/(?:Documents|Desktop|Downloads|Library|\.codex)/",
                text,
            ) or re.search(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\", text):
                errors.append(f"machine absolute path found in {path.relative_to(PROJECT_ROOT)}")
            if SECRET_PATTERN.search(text):
                errors.append(f"possible secret material found in {path.relative_to(PROJECT_ROOT)}")


def run_gate(arguments: list[str], errors: list[str]) -> None:
    process = subprocess.run(
        [sys.executable, *arguments],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if process.stdout:
        print(process.stdout.rstrip())
    if process.returncode != 0:
        errors.append(f"command failed ({process.returncode}): {' '.join(arguments)}")


def main() -> int:
    errors: list[str] = []
    validate_adrs(errors)
    validate_cross_document_contracts(errors)
    validate_portability_and_secrets(errors)
    run_gate(["tools/validate_phase1_openapi.py"], errors)
    run_gate(["tools/validate_phase1_boundaries.py"], errors)
    run_gate(
        ["-m", "unittest", "discover", "-s", "tools", "-p", "test_*phase1*.py"],
        errors,
    )

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print(f"Phase 1 validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print("PASS phase 1 aggregate gate: 10 ADRs + OpenAPI + boundaries + negative tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
