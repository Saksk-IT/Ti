#!/usr/bin/env python3
"""Build the fixed Phase 6 Web-foundation source-successor bootstrap.

The ordinary build is Gitless and accepts only an explicit file allowlist.
Optional Git replay fixes the immutable c563ac6 commit, its trees and raw
delta.  This bootstrap deliberately excludes its own control sources until a
later post-push external Git anchor binds them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase6/web-foundation-source-successor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE

CONTRACT_ID = "ti.phase6.web-foundation-source-successor-contract"
CAPTURED_AT = "2026-07-19T01:20:00+08:00"
STATUS = "bootstrap_complete_external_git_anchor_pending"
SCOPE = "phase6-web-foundation-source-successor"

TYPED_ANCHOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-anchor-contract.json"
)
TYPED_ANCHOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-typed-normalization-anchor-contract"
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
PHASE6_ACCEPTANCE_GIT_BLOB_OID = "4508d911a8f9fc4cf694608988a0aae7fceb6105"

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

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "c563ac655077e69306c34d163f63a4da50569e01"
GIT_PARENT_OID = "bd2ed3946487d27abffc81d966e7adfaab1fe433"
GIT_ROOT_TREE_OID = "37c0029466f358795c58c5418573fa11ef57bcc6"
GIT_TI_JAVA_TREE_OID = "f5d5c5f8248213863730e0355780b12512203696"
GIT_WEB_TREE_OID = "a75f69a8205a56843feb055656ddb015ec5b5215"
GIT_SERVER_TREE_OID = "57cda4d266fd1416853a6996e395c0fb2fb353eb"
GIT_AUTHORED_AT = "2026-07-19T00:40:39+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "feat(web): integrate Phase 6 public bank foundation"
GIT_RAW_DELTA_SHA256 = (
    "7c1621f8e44520ccb0f04a5250cd7003b5d5a8a0d5cf0db35549a10b6fa4ffd4"
)
GIT_CHANGED_PATH_COUNT = 107
GIT_ADDED_COUNT = 105
GIT_MODIFIED_COUNT = 2
GIT_INSERTED_LINES = 18_384
GIT_DELETED_LINES = 4
GIT_CURRENT_TOTAL_BYTES = 718_109
GIT_ADDED_TOTAL_BYTES = 572_363
GIT_MODIFIED_CURRENT_BYTES = 145_746
GIT_MODIFIED_PARENT_BYTES = 143_265
GIT_NET_BYTE_INCREASE = 574_844
GIT_WEB_CHANGED_PATH_COUNT = 102
GIT_NON_WEB_CHANGED_PATHS = (
    "Ti-Java/README.md",
    "Ti-Java/docs/refactor/05-progress.md",
    "Ti-Java/docs/refactor/phase6/README.md",
    "Ti-Java/docs/refactor/phase6/verify_web_foundation_acceptance.py",
    "Ti-Java/docs/refactor/phase6/web-foundation-acceptance.json",
)

WEB_FILE_COUNT = 102
WEB_BYTE_COUNT = 558_898
WEB_MANIFEST_SHA256 = (
    "e92634ecb328edecce27fea97ec8d9e2ceb5fdc9e7a1aa8e74f378e5ea407752"
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

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorContractParityTest.java",
    "tools/build_phase6_web_foundation_source_successor_contract.py",
    "tools/phase6_web_foundation_source_successor_acceptance.py",
    "tools/test_phase6_web_foundation_source_successor_contract.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def document_payload_sha256(document: dict[str, Any]) -> str:
    payload = {key: value for key, value in document.items()
               if key != "document_payload_sha256"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    candidate_relative = Path(relative)
    if candidate_relative.is_absolute() or not candidate_relative.parts:
        raise AssertionError(f"Phase6 source path is not relative: {relative}")
    if any(part in ("", ".", "..") for part in candidate_relative.parts):
        raise AssertionError(f"Phase6 source path escapes root: {relative}")
    candidate = root.joinpath(*candidate_relative.parts)
    current = root
    for part in candidate_relative.parts:
        current = current / part
        if current.is_symlink():
            raise AssertionError(f"Phase6 source path is a symlink: {relative}")
    if not candidate.is_file():
        raise AssertionError(f"Phase6 source path is not a regular file: {relative}")
    if candidate.resolve(strict=True).parent != candidate.parent.resolve(strict=True):
        raise AssertionError(f"Phase6 source path resolution drifted: {relative}")
    return candidate


def validated_bytes(root: Path, relative: str, sha256: str,
                    byte_count: int) -> bytes:
    payload = fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(f"Phase6 fixed bytes drifted: {relative}")
    return payload


def read_fixed_json(root: Path, relative: str, sha256: str,
                    byte_count: int) -> dict[str, Any]:
    value = json.loads(validated_bytes(root, relative, sha256, byte_count))
    if not isinstance(value, dict):
        raise AssertionError(f"Phase6 fixed JSON is not an object: {relative}")
    return value


def _validate_fixed_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    typed = read_fixed_json(root, TYPED_ANCHOR_RELATIVE,
                            TYPED_ANCHOR_SHA256, TYPED_ANCHOR_BYTE_COUNT)
    if (typed.get("contract_id") != TYPED_ANCHOR_ID
            or typed.get("document_payload_sha256") != TYPED_ANCHOR_PAYLOAD_SHA256
            or document_payload_sha256(typed) != TYPED_ANCHOR_PAYLOAD_SHA256):
        raise AssertionError("Phase6 typed-anchor predecessor drifted")

    phase6 = read_fixed_json(root, PHASE6_ACCEPTANCE_RELATIVE,
                             PHASE6_ACCEPTANCE_SHA256,
                             PHASE6_ACCEPTANCE_BYTE_COUNT)
    if (phase6.get("contract_id") != "phase6-web-foundation-acceptance-v1"
            or phase6.get("status") != "complete"
            or phase6.get("phase6_disposition", {}).get("foundation_complete") is not True
            or phase6.get("phase6_disposition", {}).get("phase6_complete") is not False
            or phase6.get("phase6_disposition", {}).get(
                "gateway_or_production_cutover_authorized") is not False
            or phase6.get("web_content", {}).get("file_count") != WEB_FILE_COUNT
            or phase6.get("web_content", {}).get("byte_count") != WEB_BYTE_COUNT
            or phase6.get("web_content", {}).get("manifest_sha256")
            != WEB_MANIFEST_SHA256):
        raise AssertionError("Phase6 Web-foundation acceptance drifted")

    route = read_fixed_json(root, ROUTE_STATUS_RELATIVE, ROUTE_STATUS_SHA256,
                            ROUTE_STATUS_BYTE_COUNT)
    if (route.get("document_payload_sha256") != ROUTE_STATUS_PAYLOAD_SHA256
            or document_payload_sha256(route) != ROUTE_STATUS_PAYLOAD_SHA256
            or route.get("effective", {}).get("migration_status")
            != {"migrated": 13, "pending": 598}
            or route.get("effective", {}).get(
                "production_cutover_operation_count") != 0):
        raise AssertionError("Phase6 effective route authority drifted")

    validated_bytes(root, HASHER_RELATIVE, HASHER_SHA256, HASHER_BYTE_COUNT)
    validated_bytes(root, DOCKERFILE_RELATIVE, DOCKERFILE_SHA256,
                    DOCKERFILE_BYTE_COUNT)
    worm = read_fixed_json(root, WORM_RELATIVE, WORM_SHA256, WORM_BYTE_COUNT)
    if (worm.get("java", {}).get("dockerfileSha256") != DOCKERFILE_SHA256
            or worm.get("java", {}).get("buildContextSha256")
            != JAVA_BUILD_CONTEXT_SHA256):
        raise AssertionError("Phase6 fixed WORM Java boundary drifted")

    for relative, descriptor in SOURCE_SUCCESSORS.items():
        validated_bytes(root, relative, descriptor["successor_sha256"],
                        descriptor["successor_byte_count"])
    return phase6, route


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
                        "GIT_PAGER": "cat", "LC_ALL": "C"})
    result = subprocess.run(("git", *arguments), cwd=repository_root,
                            env=environment, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("Phase6 repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("Phase6 Git object format drifted")
    facts = _git_text(root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s",
                      GIT_COMMIT_OID).splitlines()
    if facts != [GIT_ROOT_TREE_OID, GIT_PARENT_OID, GIT_AUTHORED_AT,
                 GIT_COMMITTED_AT, GIT_SUBJECT]:
        raise AssertionError("Phase6 Git checkpoint identity drifted")
    expected_trees = {
        "Ti-Java": GIT_TI_JAVA_TREE_OID,
        "Ti-Java/web": GIT_WEB_TREE_OID,
        "Ti-Java/server": GIT_SERVER_TREE_OID,
    }
    for relative, expected in expected_trees.items():
        if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:{relative}") != expected:
            raise AssertionError(f"Phase6 checkpoint tree drifted: {relative}")
    if (_git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/server")
            != GIT_SERVER_TREE_OID):
        raise AssertionError("Phase6 server tree changed across Web integration")

    raw = _run_git(root, "diff-tree", "--no-commit-id", "--raw",
                   "--abbrev=40", "-r", GIT_COMMIT_OID)
    if sha256_bytes(raw) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("Phase6 raw delta digest drifted")
    names = _git_text(root, "diff-tree", "--no-commit-id", "--name-status",
                      "-r", GIT_COMMIT_OID).splitlines()
    if len(names) != GIT_CHANGED_PATH_COUNT:
        raise AssertionError("Phase6 changed-path count drifted")
    parsed = [(line.split("\t", 1)[0], line.split("\t", 1)[1])
              for line in names]
    if (sum(status == "A" for status, _ in parsed) != GIT_ADDED_COUNT
            or sum(status == "M" for status, _ in parsed) != GIT_MODIFIED_COUNT
            or [path for _, path in parsed if not path.startswith("Ti-Java/web/")]
            != list(GIT_NON_WEB_CHANGED_PATHS)
            or sum(path.startswith("Ti-Java/web/") for _, path in parsed)
            != GIT_WEB_CHANGED_PATH_COUNT):
        raise AssertionError("Phase6 exact checkpoint scope drifted")

    for relative, descriptor in SOURCE_SUCCESSORS.items():
        repository_path = f"Ti-Java/{relative}"
        oid = _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:{repository_path}")
        if oid != descriptor["successor_git_blob_oid"]:
            raise AssertionError(f"Phase6 successor Git blob drifted: {relative}")
        payload = _run_git(root, "cat-file", "blob", oid)
        if (len(payload) != descriptor["successor_byte_count"]
                or sha256_bytes(payload) != descriptor["successor_sha256"]):
            raise AssertionError(f"Phase6 successor Git payload drifted: {relative}")
    if (_git_text(root, "rev-parse",
                  f"{GIT_COMMIT_OID}:Ti-Java/{PHASE6_ACCEPTANCE_RELATIVE}")
            != PHASE6_ACCEPTANCE_GIT_BLOB_OID):
        raise AssertionError("Phase6 acceptance Git blob drifted")


def build_contract(ti_java_root: Path = ROOT, *,
                   repository_root: Path | None = None) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    _validate_fixed_inputs(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": STATUS,
        "scope": SCOPE,
        "predecessor_typed_anchor": {
            "source": TYPED_ANCHOR_RELATIVE,
            "contract_id": TYPED_ANCHOR_ID,
            "sha256": TYPED_ANCHOR_SHA256,
            "byte_count": TYPED_ANCHOR_BYTE_COUNT,
            "document_payload_sha256": TYPED_ANCHOR_PAYLOAD_SHA256,
            "immutable": True,
        },
        "git_checkpoint": {
            "object_format": GIT_OBJECT_FORMAT,
            "commit_oid": GIT_COMMIT_OID,
            "parent_oid": GIT_PARENT_OID,
            "root_tree_oid": GIT_ROOT_TREE_OID,
            "ti_java_tree_oid": GIT_TI_JAVA_TREE_OID,
            "web_tree_oid": GIT_WEB_TREE_OID,
            "server_tree_oid": GIT_SERVER_TREE_OID,
            "parent_server_tree_oid": GIT_SERVER_TREE_OID,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_COMMITTED_AT,
            "subject": GIT_SUBJECT,
            "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
            "changed_path_count": GIT_CHANGED_PATH_COUNT,
            "added_count": GIT_ADDED_COUNT,
            "modified_count": GIT_MODIFIED_COUNT,
            "deleted_count": 0,
            "inserted_line_count": GIT_INSERTED_LINES,
            "deleted_line_count": GIT_DELETED_LINES,
            "current_total_bytes": GIT_CURRENT_TOTAL_BYTES,
            "added_total_bytes": GIT_ADDED_TOTAL_BYTES,
            "modified_current_bytes": GIT_MODIFIED_CURRENT_BYTES,
            "modified_parent_bytes": GIT_MODIFIED_PARENT_BYTES,
            "net_byte_increase": GIT_NET_BYTE_INCREASE,
            "web_changed_path_count": GIT_WEB_CHANGED_PATH_COUNT,
            "non_web_changed_paths": list(GIT_NON_WEB_CHANGED_PATHS),
            "exact_raw_delta_fixed": True,
        },
        "phase6_foundation": {
            "source": PHASE6_ACCEPTANCE_RELATIVE,
            "sha256": PHASE6_ACCEPTANCE_SHA256,
            "byte_count": PHASE6_ACCEPTANCE_BYTE_COUNT,
            "git_blob_oid": PHASE6_ACCEPTANCE_GIT_BLOB_OID,
            "contract_id": "phase6-web-foundation-acceptance-v1",
            "foundation_complete": True,
            "phase6_complete": False,
            "web_file_count": WEB_FILE_COUNT,
            "web_byte_count": WEB_BYTE_COUNT,
            "web_manifest_sha256": WEB_MANIFEST_SHA256,
        },
        "typed_anchor_delegation": {
            "delegated_paths": sorted(SOURCE_SUCCESSORS),
            "delegated_path_count": len(SOURCE_SUCCESSORS),
            "delegation_allowlist_exact": True,
            "dynamic_source_discovery_forbidden": True,
            "unknown_path_rejected": True,
        },
        "source_successors": {
            "path_count": len(SOURCE_SUCCESSORS),
            "paths": sorted(SOURCE_SUCCESSORS),
            "overrides": {key: SOURCE_SUCCESSORS[key]
                          for key in sorted(SOURCE_SUCCESSORS)},
        },
        "java_build_context_boundary": {
            "hasher_source": HASHER_RELATIVE,
            "hasher_sha256": HASHER_SHA256,
            "hasher_byte_count": HASHER_BYTE_COUNT,
            "dockerfile_source": DOCKERFILE_RELATIVE,
            "dockerfile_sha256": DOCKERFILE_SHA256,
            "dockerfile_byte_count": DOCKERFILE_BYTE_COUNT,
            "java_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
            "worm_source": WORM_RELATIVE,
            "worm_sha256": WORM_SHA256,
            "worm_byte_count": WORM_BYTE_COUNT,
            "web_in_java_build_context": False,
            "server_tree_unchanged_from_parent": True,
            "new_worm_node_required": False,
        },
        "effective_authority": {
            "source": ROUTE_STATUS_RELATIVE,
            "sha256": ROUTE_STATUS_SHA256,
            "byte_count": ROUTE_STATUS_BYTE_COUNT,
            "document_payload_sha256": ROUTE_STATUS_PAYLOAD_SHA256,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "legacy_flask_remains_production_owner": True,
        },
        "authorization": {
            "route_delta_created": False,
            "operator_authorized": False,
            "schema_or_index_change_authorized": False,
            "real_data_migration_authorized": False,
            "gateway_authorized": False,
            "production_cutover": False,
        },
        "current_node_trust_boundary": {
            "control_sources": list(CONTROL_SOURCES),
            "control_source_count": len(CONTROL_SOURCES),
            "control_source_allowlist_exact": True,
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "next_gate": "fixed_post_push_external_git_anchor",
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    document = build_contract(arguments.ti_java_root,
                              repository_root=arguments.repository_root)
    payload = serialized_contract(document)
    if arguments.check:
        current = fixed_regular_file(arguments.ti_java_root.resolve(strict=True),
                                     str(arguments.output.resolve().relative_to(
                                         arguments.ti_java_root.resolve())))
        if current.read_bytes() != payload:
            raise AssertionError("Phase6 source-successor contract drifted")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_bytes(payload)
    print(f"Phase6 source-successor contract passed: {sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
