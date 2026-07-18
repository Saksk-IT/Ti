#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 6 source-successor bootstrap."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = (
    "docs/refactor/phase6/web-foundation-source-successor-contract.json"
)
CONTRACT_ID = "ti.phase6.web-foundation-source-successor-contract"
CONTRACT_STATUS = "bootstrap_complete_external_git_anchor_pending"
CONTRACT_SCOPE = "phase6-web-foundation-source-successor"
CONTRACT_CAPTURED_AT = "2026-07-19T01:20:00+08:00"
CONTRACT_SHA256 = (
    "be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073"
)
CONTRACT_PAYLOAD_SHA256 = (
    "93e2eccb5bd3cdcc95addac0d09bef26d25ae3676c1ffd1b9c10c337c1b1b693"
)
CONTRACT_BYTE_COUNT = 7_335

TYPED_ANCHOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-anchor-contract.json"
)
TYPED_ANCHOR_SHA256 = (
    "c713aa04a82f340ea04fdd5ae870bd5cfae82f099101431c664f047c2d5218ca"
)
TYPED_ANCHOR_PAYLOAD_SHA256 = (
    "430ef24103006265001ecd1f2f6aa5e4b24a886e82fcc1391cc516eba5dbde7c"
)
TYPED_ANCHOR_BYTE_COUNT = 43_737
PHASE6_ACCEPTANCE_RELATIVE = "docs/refactor/phase6/web-foundation-acceptance.json"
PHASE6_ACCEPTANCE_SHA256 = (
    "6289e15ec68a332566539df46e5b7b3143c3c58ed9c60b35c2d736ed762d8e1f"
)
PHASE6_ACCEPTANCE_BYTE_COUNT = 4_932
ROUTE_STATUS_RELATIVE = (
    "docs/refactor/phase4c/effective-route-parity-successor-status.json"
)
ROUTE_STATUS_SHA256 = (
    "c0e96472533d0bbe7d67ac1416a91f3e9a3bfcef8c27e1170b0e9939c46b358a"
)
ROUTE_STATUS_PAYLOAD_SHA256 = (
    "3788d541c027ba7f9c397afee1d006ea92da300845557ca35bdd513b920a0637"
)
ROUTE_STATUS_BYTE_COUNT = 5_340
HASHER_RELATIVE = "infra/phase2/hash-java-build-context.sh"
HASHER_SHA256 = (
    "e8e618ce08128e4fbf7b090b5b0709ed1d6bc5d1638f1f2838ff6d7409a0dea6"
)
HASHER_BYTE_COUNT = 1_011
DOCKERFILE_RELATIVE = "server/Dockerfile"
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
DOCKERFILE_BYTE_COUNT = 1_850
JAVA_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
WORM_SHA256 = (
    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
)
WORM_BYTE_COUNT = 1_442

GIT_COMMIT_OID = "c563ac655077e69306c34d163f63a4da50569e01"
GIT_PARENT_OID = "bd2ed3946487d27abffc81d966e7adfaab1fe433"
GIT_ROOT_TREE_OID = "37c0029466f358795c58c5418573fa11ef57bcc6"
GIT_TI_JAVA_TREE_OID = "f5d5c5f8248213863730e0355780b12512203696"
GIT_WEB_TREE_OID = "a75f69a8205a56843feb055656ddb015ec5b5215"
GIT_SERVER_TREE_OID = "57cda4d266fd1416853a6996e395c0fb2fb353eb"
GIT_RAW_DELTA_SHA256 = (
    "7c1621f8e44520ccb0f04a5250cd7003b5d5a8a0d5cf0db35549a10b6fa4ffd4"
)

SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "README.md": {
        "accepted_sha256": "524f03e89122b4d8a9af4ed805596a3b315a4859dac2777b0ab989ac25e82b47",
        "accepted_byte_count": 38_265,
        "successor_git_blob_oid": "a18ef8e66e1213b4e7ab47e20fb63278c264ba4e",
        "successor_sha256": "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
        "successor_byte_count": 40_323,
        "transition_is_direct_parent_delta": True,
        "successor_snapshot_fixed_by_checkpoint_tree": True,
    },
    "docs/refactor/05-progress.md": {
        "accepted_sha256": "62ff84e2cc3b525855f0a0eb07a1820c231ad50864956329d0da08a3d86b697c",
        "accepted_byte_count": 103_256,
        "successor_git_blob_oid": "74974ed6ca408e90846ab90b90e965d8fc9faa5b",
        "successor_sha256": "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
        "successor_byte_count": 105_423,
        "transition_is_direct_parent_delta": True,
        "successor_snapshot_fixed_by_checkpoint_tree": True,
    },
    "docs/refactor/phase4c/README.md": {
        "accepted_sha256": "dd0f41f78466636d09d3afa7669e507814aa78a04cb94d62bf7e96596c18e85a",
        "accepted_byte_count": 19_511,
        "successor_git_blob_oid": "8659b84a26ea0b7182c4e375bcb1a1ee185e58b6",
        "successor_sha256": "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
        "successor_byte_count": 23_309,
        "transition_is_direct_parent_delta": False,
        "successor_snapshot_fixed_by_checkpoint_tree": True,
    },
}
SOURCE_PATHS = tuple(sorted(SOURCE_SUCCESSORS))
ANCHOR_SUCCESSOR_MODULE = (
    "tools.phase6_web_foundation_source_successor_anchor_acceptance"
)
ANCHOR_SUCCESSOR_SCRIPT_MODULE = (
    "phase6_web_foundation_source_successor_anchor_acceptance"
)

CONTROL_SOURCES = (
    CONTRACT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorContractParityTest.java",
    "tools/build_phase6_web_foundation_source_successor_contract.py",
    "tools/phase6_web_foundation_source_successor_acceptance.py",
    "tools/test_phase6_web_foundation_source_successor_contract.py",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _payload_sha256(document: dict[str, Any]) -> str:
    return _sha256_bytes(_canonical_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    }).encode("utf-8"))


def _fixed_regular_file(root: Path, relative: str) -> Path:
    value = Path(relative)
    if value.is_absolute() or not value.parts or any(
            part in ("", ".", "..") for part in value.parts):
        raise AssertionError(f"Phase6 source path escapes root: {relative}")
    candidate = root.joinpath(*value.parts)
    current = root
    for part in value.parts:
        current = current / part
        if current.is_symlink():
            raise AssertionError(f"Phase6 source path is a symlink: {relative}")
    if not candidate.is_file():
        raise AssertionError(f"Phase6 source path is not a regular file: {relative}")
    return candidate


def _validate_physical(root: Path, relative: str, sha256: str,
                       byte_count: int) -> bytes:
    payload = _fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or _sha256_bytes(payload) != sha256:
        raise AssertionError(f"Phase6 fixed bytes drifted: {relative}")
    return payload


def _read_json(root: Path, relative: str, sha256: str,
               byte_count: int) -> dict[str, Any]:
    document = json.loads(_validate_physical(root, relative, sha256, byte_count))
    if not isinstance(document, dict):
        raise AssertionError(f"Phase6 fixed JSON is not an object: {relative}")
    return document


def _load_anchor_successor() -> object:
    try:
        return importlib.import_module(ANCHOR_SUCCESSOR_MODULE)
    except ModuleNotFoundError:
        try:
            return importlib.import_module(ANCHOR_SUCCESSOR_SCRIPT_MODULE)
        except (ImportError, ModuleNotFoundError) as error:
            raise AssertionError(
                "fixed Phase6 source-successor anchor module is unavailable"
            ) from error
    except ImportError as error:
        raise AssertionError(
            "fixed Phase6 source-successor anchor module is unavailable"
        ) from error


def accepted_sha256(relative: str) -> str | None:
    descriptor = SOURCE_SUCCESSORS.get(relative)
    return None if descriptor is None else str(descriptor["accepted_sha256"])


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    descriptor = SOURCE_SUCCESSORS.get(relative)
    if descriptor is None:
        return None
    root = ti_java_root.resolve(strict=True)
    payload = _fixed_regular_file(root, relative).read_bytes()
    physical = _sha256_bytes(payload)
    if (physical == descriptor["successor_sha256"]
            and len(payload) == descriptor["successor_byte_count"]):
        return physical
    anchor = _load_anchor_successor()
    anchor_accepted = getattr(anchor, "accepted_sha256", None)
    anchor_successor = getattr(anchor, "successor_sha256", None)
    if not callable(anchor_accepted) or not callable(anchor_successor):
        raise AssertionError("fixed Phase6 source-successor anchor API drifted")
    if anchor_accepted(relative) != descriptor["successor_sha256"]:
        raise AssertionError("Phase6 source-successor anchor rejected bootstrap hash")
    if anchor_successor(root, relative) != physical:
        raise AssertionError("Phase6 source-successor anchor did not bind current bytes")
    return physical


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(sorted({
        CONTRACT_RELATIVE,
        TYPED_ANCHOR_RELATIVE,
        PHASE6_ACCEPTANCE_RELATIVE,
        ROUTE_STATUS_RELATIVE,
        HASHER_RELATIVE,
        DOCKERFILE_RELATIVE,
        WORM_RELATIVE,
        *SOURCE_PATHS,
    }))


def _validate_contract_physical_bytes(root: Path) -> dict[str, Any]:
    document = _read_json(root, CONTRACT_RELATIVE, CONTRACT_SHA256,
                          CONTRACT_BYTE_COUNT)
    if (document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
            or _payload_sha256(document) != CONTRACT_PAYLOAD_SHA256):
        raise AssertionError("Phase6 source-successor contract payload drifted")
    return document


def validate(document: dict[str, Any], ti_java_root: Path) -> None:
    root = ti_java_root.resolve(strict=True)
    expected_keys = {
        "contract_id", "schema_version", "captured_at", "status", "scope",
        "predecessor_typed_anchor", "git_checkpoint", "phase6_foundation",
        "typed_anchor_delegation", "source_successors",
        "java_build_context_boundary", "effective_authority", "authorization",
        "current_node_trust_boundary", "document_payload_sha256",
    }
    if set(document) != expected_keys:
        raise AssertionError("Phase6 source-successor contract shape drifted")
    if (document.get("contract_id") != CONTRACT_ID
            or document.get("schema_version") != 1
            or document.get("captured_at") != CONTRACT_CAPTURED_AT
            or document.get("status") != CONTRACT_STATUS
            or document.get("scope") != CONTRACT_SCOPE
            or document.get("document_payload_sha256")
            != CONTRACT_PAYLOAD_SHA256
            or _payload_sha256(document) != CONTRACT_PAYLOAD_SHA256):
        raise AssertionError("Phase6 source-successor identity drifted")

    predecessor = document["predecessor_typed_anchor"]
    if (predecessor.get("source") != TYPED_ANCHOR_RELATIVE
            or predecessor.get("sha256") != TYPED_ANCHOR_SHA256
            or predecessor.get("byte_count") != TYPED_ANCHOR_BYTE_COUNT
            or predecessor.get("document_payload_sha256")
            != TYPED_ANCHOR_PAYLOAD_SHA256
            or predecessor.get("immutable") is not True):
        raise AssertionError("Phase6 typed-anchor predecessor descriptor drifted")
    typed = _read_json(root, TYPED_ANCHOR_RELATIVE, TYPED_ANCHOR_SHA256,
                       TYPED_ANCHOR_BYTE_COUNT)
    if (typed.get("contract_id")
            != "ti.phase4c.personal-bank-user-counts-http-typed-normalization-anchor-contract"
            or typed.get("document_payload_sha256")
            != TYPED_ANCHOR_PAYLOAD_SHA256
            or _payload_sha256(typed) != TYPED_ANCHOR_PAYLOAD_SHA256):
        raise AssertionError("Phase6 typed-anchor predecessor payload drifted")

    checkpoint = document["git_checkpoint"]
    if (checkpoint.get("commit_oid") != GIT_COMMIT_OID
            or checkpoint.get("parent_oid") != GIT_PARENT_OID
            or checkpoint.get("root_tree_oid") != GIT_ROOT_TREE_OID
            or checkpoint.get("ti_java_tree_oid") != GIT_TI_JAVA_TREE_OID
            or checkpoint.get("web_tree_oid") != GIT_WEB_TREE_OID
            or checkpoint.get("server_tree_oid") != GIT_SERVER_TREE_OID
            or checkpoint.get("parent_server_tree_oid") != GIT_SERVER_TREE_OID
            or checkpoint.get("raw_delta_sha256") != GIT_RAW_DELTA_SHA256
            or checkpoint.get("changed_path_count") != 107
            or checkpoint.get("web_changed_path_count") != 102
            or checkpoint.get("exact_raw_delta_fixed") is not True):
        raise AssertionError("Phase6 fixed Git checkpoint descriptor drifted")

    foundation = document["phase6_foundation"]
    phase6 = _read_json(root, PHASE6_ACCEPTANCE_RELATIVE,
                        PHASE6_ACCEPTANCE_SHA256,
                        PHASE6_ACCEPTANCE_BYTE_COUNT)
    if (foundation.get("source") != PHASE6_ACCEPTANCE_RELATIVE
            or foundation.get("sha256") != PHASE6_ACCEPTANCE_SHA256
            or foundation.get("foundation_complete") is not True
            or foundation.get("phase6_complete") is not False
            or foundation.get("web_file_count") != 102
            or foundation.get("web_byte_count") != 558_898
            or phase6.get("phase6_disposition", {}).get("foundation_complete")
            is not True
            or phase6.get("phase6_disposition", {}).get("phase6_complete")
            is not False):
        raise AssertionError("Phase6 foundation descriptor drifted")

    delegation = document["typed_anchor_delegation"]
    successors = document["source_successors"]
    if (delegation.get("delegated_paths") != list(SOURCE_PATHS)
            or delegation.get("delegated_path_count") != len(SOURCE_PATHS)
            or delegation.get("delegation_allowlist_exact") is not True
            or delegation.get("dynamic_source_discovery_forbidden") is not True
            or successors.get("paths") != list(SOURCE_PATHS)
            or successors.get("path_count") != len(SOURCE_PATHS)
            or successors.get("overrides") != SOURCE_SUCCESSORS):
        raise AssertionError("Phase6 source-successor allowlist drifted")
    for relative, descriptor in SOURCE_SUCCESSORS.items():
        physical = _fixed_regular_file(root, relative).read_bytes()
        physical_sha = _sha256_bytes(physical)
        if (physical_sha != descriptor["successor_sha256"]
                or len(physical) != descriptor["successor_byte_count"]):
            anchor = _load_anchor_successor()
            accepted = getattr(anchor, "accepted_sha256", None)
            terminal = getattr(anchor, "successor_sha256", None)
            if (not callable(accepted) or not callable(terminal)
                    or accepted(relative) != descriptor["successor_sha256"]
                    or terminal(root, relative) != physical_sha):
                raise AssertionError(
                    f"Phase6 source-successor physical bytes drifted: {relative}"
                )

    boundary = document["java_build_context_boundary"]
    _validate_physical(root, HASHER_RELATIVE, HASHER_SHA256, HASHER_BYTE_COUNT)
    _validate_physical(root, DOCKERFILE_RELATIVE, DOCKERFILE_SHA256,
                       DOCKERFILE_BYTE_COUNT)
    worm = _read_json(root, WORM_RELATIVE, WORM_SHA256, WORM_BYTE_COUNT)
    if (boundary.get("java_build_context_sha256")
            != JAVA_BUILD_CONTEXT_SHA256
            or boundary.get("web_in_java_build_context") is not False
            or boundary.get("server_tree_unchanged_from_parent") is not True
            or boundary.get("new_worm_node_required") is not False
            or worm.get("java", {}).get("buildContextSha256")
            != JAVA_BUILD_CONTEXT_SHA256):
        raise AssertionError("Phase6 Java build-context boundary drifted")

    authority = document["effective_authority"]
    route = _read_json(root, ROUTE_STATUS_RELATIVE, ROUTE_STATUS_SHA256,
                       ROUTE_STATUS_BYTE_COUNT)
    if (authority.get("migrated_operation_count") != 13
            or authority.get("pending_operation_count") != 598
            or authority.get("production_cutover_operation_count") != 0
            or authority.get("legacy_flask_remains_production_owner") is not True
            or route.get("document_payload_sha256")
            != ROUTE_STATUS_PAYLOAD_SHA256
            or _payload_sha256(route) != ROUTE_STATUS_PAYLOAD_SHA256):
        raise AssertionError("Phase6 effective authority drifted")

    if any(document["authorization"].values()):
        raise AssertionError("Phase6 source-successor overclaims authorization")
    trust = document["current_node_trust_boundary"]
    if (trust.get("control_sources") != list(CONTROL_SOURCES)
            or trust.get("control_source_count") != len(CONTROL_SOURCES)
            or trust.get("control_source_allowlist_exact") is not True
            or trust.get("control_sources_excluded_from_self_authority") is not True
            or trust.get("control_sources_external_git_anchor_complete") is not False
            or trust.get("independently_signed_provenance") is not False):
        raise AssertionError("Phase6 source-successor trust boundary drifted")


def load(ti_java_root: Path = ROOT) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    document = _validate_contract_physical_bytes(root)
    validate(document, root)
    return document


def validate_git_checkpoint(repository_root: Path) -> None:
    try:
        from tools import build_phase6_web_foundation_source_successor_contract as builder
    except ModuleNotFoundError:
        import build_phase6_web_foundation_source_successor_contract as builder
    if (builder.GIT_COMMIT_OID != GIT_COMMIT_OID
            or builder.GIT_RAW_DELTA_SHA256 != GIT_RAW_DELTA_SHA256):
        raise AssertionError("Phase6 builder Git authority drifted")
    builder.validate_git_checkpoint(repository_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    arguments = parser.parse_args()
    document = load(arguments.ti_java_root)
    if arguments.repository_root is not None:
        validate_git_checkpoint(arguments.repository_root)
    print("Phase6 Web-foundation source successor passed: "
          f"{document['document_payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
