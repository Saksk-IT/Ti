"""Exact, Gitless reconciliation of the two fixed main histories.

This additive contract composes reviewed file versions. It never authorizes
unknown bytes, rewrites a predecessor, or grants route/cutover authority.
"""
import hashlib
import json
from pathlib import Path

CONTRACT = "docs/refactor/phase4c/learning-transaction-write-http-integration-successor-contract.json"
CONTRACT_SHA256 = "9e14033e117348746a07a6ea0250b2ace38c10fe0aa5062c3f021b15d7b0830d"
CONTRACT_ID = "ti.phase4c.learning-transaction-write-http-integration-successor-contract"


def fixed_file(root: Path, relative: str) -> Path:
    if (not relative or relative.startswith("/") or "\\" in relative
            or ":" in relative or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise AssertionError("integration path escapes root")
    cursor = root.resolve(strict=True)
    for part in relative.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError("integration path is a symlink")
    if not cursor.is_file():
        raise AssertionError("integration file is absent: " + relative)
    return cursor


def load(root: Path) -> dict:
    payload = fixed_file(root, CONTRACT).read_bytes()
    if hashlib.sha256(payload).hexdigest() != CONTRACT_SHA256:
        raise AssertionError("integration successor contract drifted")
    document = json.loads(payload)
    if document["contract_id"] != CONTRACT_ID:
        raise AssertionError("integration successor identity drifted")
    return document


def accepts(root: Path, relative: str, digest: str, count: int) -> bool:
    transition = load(root)["transitions"].get(relative)
    if transition is None or not any(
        item["sha256"] == digest and item["byte_count"] == count
        for item in transition["accepted"]
    ):
        return False
    payload = fixed_file(root, relative).read_bytes()
    expected = transition["current"]
    return len(payload) == expected["byte_count"] and hashlib.sha256(payload).hexdigest() == expected["sha256"]
