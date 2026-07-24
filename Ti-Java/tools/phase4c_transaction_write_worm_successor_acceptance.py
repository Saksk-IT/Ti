#!/usr/bin/env python3
"""Accept the fixed tenth WORM node for Phase 4C transaction writes."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tools import phase2_wormhole_successor_acceptance as predecessor
except ModuleNotFoundError:
    import phase2_wormhole_successor_acceptance as predecessor


TRANSACTION_WRITE_REPORT_PATH = (
    "docs/refactor/phase4c/"
    "learning-transaction-write-http-worm-evidence.json"
)
TRANSACTION_WRITE_REPORT_SHA256 = (
    "dd165106d7b3a73512acdbf89924b352e3f1ad027132b8a8519af957a47de599"
)
TRANSACTION_WRITE_BUILD_CONTEXT_SHA256 = (
    "5e4247d0a43405661cef27b91b4169273e8ad096bfa750b4ba4488ca6c247224"
)
TRANSACTION_WRITE_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
TRANSACTION_WRITE_SUCCESSOR = predecessor.EvidenceDescriptor(
    label="phase4c-learning-transaction-write-http",
    relative_path=TRANSACTION_WRITE_REPORT_PATH,
    sha256=TRANSACTION_WRITE_REPORT_SHA256,
    build_context_sha256=TRANSACTION_WRITE_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=TRANSACTION_WRITE_DOCKERFILE_SHA256,
    predecessor_sha256=predecessor.PHASE4C_TAG_EXECUTION_PROTOCOL_REPORT_SHA256,
)
FIXED_EVIDENCE_CHAIN = (
    *predecessor.FIXED_EVIDENCE_CHAIN,
    TRANSACTION_WRITE_SUCCESSOR,
)


def validate_fixed_chain(
    ti_java_root: Path,
    drift_manifest_path: Path,
    current_dockerfile_sha256: str,
    current_build_context_sha256: str,
) -> predecessor.EvidenceDescriptor:
    """Validate the historical nine nodes plus the fixed transaction-write node."""

    predecessor.validate_fixed_chain(
        ti_java_root,
        drift_manifest_path,
        predecessor.PHASE4C_TAG_EXECUTION_PROTOCOL_DOCKERFILE_SHA256,
        predecessor.PHASE4C_TAG_EXECUTION_PROTOCOL_BUILD_CONTEXT_SHA256,
    )
    return predecessor.validate_evidence_chain(
        ti_java_root,
        drift_manifest_path,
        current_dockerfile_sha256,
        current_build_context_sha256,
        chain=FIXED_EVIDENCE_CHAIN,
        immutable_mirrors=predecessor.FIXED_IMMUTABLE_MIRRORS,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the fixed Phase 4C transaction-write WORM successor."
    )
    parser.add_argument("--ti-java-root", type=Path, required=True)
    parser.add_argument("--drift-manifest", type=Path, required=True)
    parser.add_argument("--dockerfile-sha256", required=True)
    parser.add_argument("--build-context-sha256", required=True)
    args = parser.parse_args()
    try:
        tip = validate_fixed_chain(
            args.ti_java_root,
            args.drift_manifest,
            args.dockerfile_sha256,
            args.build_context_sha256,
        )
    except (predecessor.EvidenceValidationError, OSError) as error:
        raise SystemExit(
            f"Transaction-write WORM evidence invalid: {error}"
        ) from error
    print(f"Fixed transaction-write WORM successor passed: {tip.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
