#!/usr/bin/env python3
"""Fail-closed Gitless acceptance of the fixed transaction bootstrap anchor."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from tools import build_phase4c_learning_transaction_write_http_full_parity_anchor_contract as builder
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    import build_phase4c_learning_transaction_write_http_full_parity_anchor_contract as builder

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "956ce6f59bb42df821aa77c6350f4214e62bacfa4a079e347fc2e506a088adc8"
CONTRACT_BYTE_COUNT = 10681
CONTRACT_PAYLOAD_SHA256 = "e960beb57ea8c62148404c6af63b524b0a9bdfabac669cbe22e45f34057ff5c6"


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    if (document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
            or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
            or document != builder.build_contract(root)):
        raise AssertionError("anchor deterministic rebuild drifted")


def load(root: Path = ROOT) -> dict[str, Any]:
    payload = builder.fixed_bytes(root, CONTRACT_RELATIVE, CONTRACT_SHA256, CONTRACT_BYTE_COUNT)
    document = json.loads(payload)
    validate(document, root)
    return document


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(dict.fromkeys((CONTRACT_RELATIVE, builder.SNAPSHOT_PATH,
                               "docs/refactor/phase4c/learning-transaction-write-http-integration-successor-contract.json",
                               *builder.fixed_inputs(ROOT))))


def progress_successor(root: Path, relative: str, accepted_sha256: str,
                       accepted_byte_count: int) -> dict[str, Any] | None:
    if relative != builder.PROGRESS_PATH:
        return None
    transition = builder.PROGRESS_TRANSITION
    if (accepted_sha256, accepted_byte_count) != (
            transition["accepted_sha256"], transition["accepted_byte_count"]):
        raise AssertionError("anchor progress predecessor drifted")
    # load only verifies fixed files and never calls the predecessor loader.
    load(root)
    return dict(transition)


if __name__ == "__main__":
    print(json.dumps({"accepted": True, "contract_id": load()["contract_id"]}))
