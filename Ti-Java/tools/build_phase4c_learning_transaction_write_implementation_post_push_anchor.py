#!/usr/bin/env python3
"""Build the post-push anchor for the Phase 4C write implementation gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
PREDECESSOR = (
    TI_JAVA
    / "docs/refactor/phase4c/"
    "learning-transaction-write-implementation-contract.json"
)
BUILD_TEST = (
    TOOLS_DIR
    / "test_phase4c_learning_transaction_write_implementation_post_push_anchor.py"
)
DEFAULT_OUTPUT = (
    TI_JAVA
    / "docs/refactor/phase4c/"
    "learning-transaction-write-implementation-post-push-anchor.json"
)
sys.dont_write_bytecode = True


FIXED_COMMIT = "56df49730dc09d550e64d5b4087af5060cceab64"
FIXED_ROOT_TREE = "4c961bc64c9bc50b4715cca9e78bfb3719d84f71"
FIXED_PARENT = "22a1d81b14be61129427ca614a68ea12befde919"
PREDECESSOR_SHA256 = (
    "c4f4b2aed1836ffb2515ca6f13d0e5d822557e57be1a8befc7b696959a814cd3"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "56eca630a339aae9d19c232573d722d64de67a2e3e53068a5a6346e4a2d0b6f6"
)
PREDECESSOR_GIT_BLOB = "5d21164912376dbdc791e2ef00453218e0ae89f5"
PREDECESSOR_SIZE = 15_652


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def render_document(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def build_document() -> dict[str, Any]:
    payload = PREDECESSOR.read_bytes()
    predecessor = json.loads(payload)
    if len(payload) != PREDECESSOR_SIZE:
        raise AssertionError("implementation contract size drifted")
    if hashlib.sha256(payload).hexdigest() != PREDECESSOR_SHA256:
        raise AssertionError("implementation contract bytes drifted")
    if (
        predecessor["document_payload_sha256"]
        != PREDECESSOR_PAYLOAD_SHA256
    ):
        raise AssertionError("implementation contract payload drifted")
    if (
        predecessor["contract_id"]
        != "ti.phase4c.learning-transaction-write-implementation-contract"
    ):
        raise AssertionError("implementation contract identity drifted")
    if not predecessor["status"]["implementation_authorized"]:
        raise AssertionError("implementation contract authorization drifted")
    builder_payload = Path(__file__).read_bytes()
    test_payload = BUILD_TEST.read_bytes()
    document: dict[str, Any] = {
        "contract_id": (
            "ti.phase4c.learning-transaction-write-implementation-"
            "post-push-anchor"
        ),
        "schema_version": 1,
        "captured_at": "2026-07-23T20:25:00+08:00",
        "fixed_git_object": {
            "commit_oid": FIXED_COMMIT,
            "root_tree_oid": FIXED_ROOT_TREE,
            "parent_commit_oid": FIXED_PARENT,
            "branch": "main",
            "remote_ref": "refs/heads/main",
            "remote_observed_at_capture": FIXED_COMMIT,
            "commit_contains_predecessor_bytes": True,
        },
        "predecessor_contract": {
            "path": (
                "docs/refactor/phase4c/"
                "learning-transaction-write-implementation-contract.json"
            ),
            "sha256": PREDECESSOR_SHA256,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "git_blob_oid": PREDECESSOR_GIT_BLOB,
            "size_bytes": PREDECESSOR_SIZE,
        },
        "accepted_authorization": {
            "operation_count": predecessor["scope"]["operation_count"],
            "approved_difference_count": len(
                predecessor["approved_differences"]
            ),
            "transaction_write_implementation": True,
            "scoped_flyway_migrations": True,
            "openapi_draft": True,
            "route_matrix_delta": False,
            "production_schema_execution": False,
            "production_cutover": False,
            "other_phase4c_groups": False,
        },
        "route_state": {
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "anchor_is_not_route_migration": True,
        },
        "control_plane": {
            "fixed_commit_external_git_anchor_complete": True,
            "predecessor_physical_bytes_in_fixed_commit": True,
            "predecessor_git_blob_fixed": True,
            "self_signed": False,
            "live_worktree_is_not_authority": True,
        },
        "status": {
            "anchor_complete": True,
            "implementation_authorized": True,
            "implementation_complete": False,
            "route_migration_complete": False,
            "production_cutover": False,
            "next_gate": (
                "transaction-write schema, application, HTTP, Redis and "
                "PostgreSQL implementation evidence"
            ),
        },
        "provenance": {
            "builder": {
                "path": (
                    "tools/"
                    "build_phase4c_learning_transaction_write_"
                    "implementation_post_push_anchor.py"
                ),
                "sha256": hashlib.sha256(builder_payload).hexdigest(),
                "size_bytes": len(builder_payload),
            },
            "builder_test": {
                "path": (
                    "tools/"
                    "test_phase4c_learning_transaction_write_"
                    "implementation_post_push_anchor.py"
                ),
                "sha256": hashlib.sha256(test_payload).hexdigest(),
                "size_bytes": len(test_payload),
            },
            "secrets_embedded": False,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    args = parse_args()
    rendered = render_document(build_document())
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_bytes() != rendered:
            raise SystemExit(f"post-push anchor drifted: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
