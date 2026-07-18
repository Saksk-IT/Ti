#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 6 source-successor Git anchor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = (
    "docs/refactor/phase6/"
    "web-foundation-source-successor-anchor-contract.json"
)
CONTRACT_ID = "ti.phase6.web-foundation-source-successor-anchor-contract"
CONTRACT_STATUS = (
    "source_successor_checkpoint_externally_anchored_phase6_incomplete"
)
CONTRACT_SCOPE = "phase6-web-foundation-source-successor-external-anchor"
CONTRACT_CAPTURED_AT = "2026-07-19T03:00:00+08:00"
CONTRACT_SHA256 = (
    "c91b924c027af0099dfec9d8ff36945635b128ba5822c8faca1f6fcfb2167da2"
)
CONTRACT_PAYLOAD_SHA256 = (
    "87d952b1ba4ca4336c067d8d68ffbe86101ea0263c854541674ac3dbd7feb4af"
)
CONTRACT_BYTE_COUNT = 29_658

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase6/web-foundation-source-successor-contract.json"
)
PREDECESSOR_ID = "ti.phase6.web-foundation-source-successor-contract"
PREDECESSOR_STATUS = "bootstrap_complete_external_git_anchor_pending"
PREDECESSOR_SHA256 = (
    "be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "93e2eccb5bd3cdcc95addac0d09bef26d25ae3676c1ffd1b9c10c337c1b1b693"
)
PREDECESSOR_BYTE_COUNT = 7_335

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "40a27ffdd83ecf240e17f4a5f69106906faaef35"
GIT_PARENT_OID = "c563ac655077e69306c34d163f63a4da50569e01"
GIT_ROOT_TREE_OID = "b83b6957736c594066cf18955b8e87b1c91f6b82"
GIT_TI_JAVA_TREE_OID = "d7c83c3439509ea51e5fa06f3310df91bf0fd5a4"
GIT_SERVER_TREE_OID = "275dbc7251889ca9fad02688fb4b418e52d2c68a"
GIT_WEB_TREE_OID = "a75f69a8205a56843feb055656ddb015ec5b5215"
GIT_SERVER_SRC_MAIN_TREE_OID = "7130e1d1fde766030689658cdd508794ab9a12d6"
GIT_AUTHORED_AT = "2026-07-19T02:41:02+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "test(java): bridge phase6 source successor"
GIT_RAW_DELTA_SHA256 = (
    "0e97aacf626cf528ab4303bc5c61cfc9e359edb66f1a9b227e866dc21c26d2cd"
)
GIT_INSERTED_LINE_COUNT = 2_297
GIT_DELETED_LINE_COUNT = 28
CHECKPOINT_PATHS = (
    "docs/refactor/phase6/web-foundation-source-successor-contract.json",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py",
    "tools/build_phase6_web_foundation_source_successor_contract.py",
    "tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py",
    "tools/phase6_web_foundation_source_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py",
    "tools/test_phase6_web_foundation_source_successor_contract.py",
)
CHECKPOINT_CURRENT_TOTAL_BYTES = 254_303
CHECKPOINT_ADDED_TOTAL_BYTES = 96_786
CHECKPOINT_MODIFIED_CURRENT_BYTES = 157_517
CHECKPOINT_MODIFIED_PARENT_BYTES = 148_725
CHECKPOINT_NET_BYTE_INCREASE = 105_578
PREDECESSOR_CONTROL_SOURCES = (
    PREDECESSOR_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorContractParityTest.java",
    "tools/build_phase6_web_foundation_source_successor_contract.py",
    "tools/phase6_web_foundation_source_successor_acceptance.py",
    "tools/test_phase6_web_foundation_source_successor_contract.py",
)
TYPED_ANCHOR_BRIDGE_SOURCES = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py",
    "tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py",
)

SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "README.md": {
        "accepted_sha256": "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
        "accepted_byte_count": 40_323,
        "accepted_git_blob_oid": "a18ef8e66e1213b4e7ab47e20fb63278c264ba4e",
        "successor_sha256": "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
        "successor_byte_count": 40_323,
        "changed_after_checkpoint": False,
    },
    "docs/refactor/05-progress.md": {
        "accepted_sha256": "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
        "accepted_byte_count": 105_423,
        "accepted_git_blob_oid": "74974ed6ca408e90846ab90b90e965d8fc9faa5b",
        "successor_sha256": "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
        "successor_byte_count": 105_423,
        "changed_after_checkpoint": False,
    },
    "docs/refactor/phase4c/README.md": {
        "accepted_sha256": "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
        "accepted_byte_count": 23_309,
        "accepted_git_blob_oid": "8659b84a26ea0b7182c4e375bcb1a1ee185e58b6",
        "successor_sha256": "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
        "successor_byte_count": 23_309,
        "changed_after_checkpoint": False,
    },
    PREDECESSOR_RELATIVE: {
        "accepted_sha256": PREDECESSOR_SHA256,
        "accepted_byte_count": PREDECESSOR_BYTE_COUNT,
        "accepted_git_blob_oid": "4e2e267bfcf443139916fdd409b3d6885458c57b",
        "successor_sha256": PREDECESSOR_SHA256,
        "successor_byte_count": PREDECESSOR_BYTE_COUNT,
        "changed_after_checkpoint": False,
    },
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAcceptance.java": {
        "accepted_sha256": "dbdb33fdcba228d45ee72a560dccc11baee489c3780864caa1e649e2e9aa489b",
        "accepted_byte_count": 29_043,
        "accepted_git_blob_oid": "c7094e9cbd6a90e57f16596421ada26abfd2734d",
        "successor_sha256": "288e85ace1a4fc3e2a74e03d4390533044678604fef71fe6707c3e840c2b5d85",
        "successor_byte_count": 29_642,
        "changed_after_checkpoint": True,
    },
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorContractParityTest.java": {
        "accepted_sha256": "e17f062b1cd960289aa5a56cd3fc7b0aa65a649b16f48c7d802d51fab81a89ec",
        "accepted_byte_count": 11_378,
        "accepted_git_blob_oid": "d918f07417f6362e8ee07534762efe83cd5edcff",
        "successor_sha256": "34d6b638cf40667a2c0b1ce1214cc04b8e149321f3137ea8d5d09ee44290d694",
        "successor_byte_count": 11_770,
        "changed_after_checkpoint": True,
    },
    "tools/build_phase6_web_foundation_source_successor_contract.py": {
        "accepted_sha256": "f9fc6c70ad12e98ceb4d1bf27bb448085807c91fc390c56e451b905403b263c6",
        "accepted_byte_count": 21_526,
        "accepted_git_blob_oid": "aa1785ab315e19eb6832e31c45f7ad821480dab7",
        "successor_sha256": "ed3a711cf9e0b15cb7facfcaa76a63ca2d6509eda84dc617afbfc8b033a1079a",
        "successor_byte_count": 22_788,
        "changed_after_checkpoint": True,
    },
    "tools/phase6_web_foundation_source_successor_acceptance.py": {
        "accepted_sha256": "1904fae55218791fdc7c66490bcff0d9d9702a4d769ceb919542670bb6e32974",
        "accepted_byte_count": 18_420,
        "accepted_git_blob_oid": "779adedd4b894ede7b215371b7ae5f661fd71c1a",
        "successor_sha256": "19190c0053c1313f5b481c5ce85db8d905e959f6ada10745848c7dcce4f57e59",
        "successor_byte_count": 19_222,
        "changed_after_checkpoint": True,
    },
    "tools/test_phase6_web_foundation_source_successor_contract.py": {
        "accepted_sha256": "08058702a694a380e16a3a385293396f5f13f88b1cfb36209ffff16818c2a471",
        "accepted_byte_count": 9_084,
        "accepted_git_blob_oid": "233930c91cd111c6d45e28141b0df876d26d98c9",
        "successor_sha256": "fb553e8d15c8b748dc62eb6517f775614132657a60b13716449ad1a72606685d",
        "successor_byte_count": 9_139,
        "changed_after_checkpoint": True,
    },
}
SOURCE_PATHS = tuple(sorted(SOURCE_SUCCESSORS))

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
CURRENT_CONTROL_SOURCES = (
    CONTRACT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java",
    "tools/build_phase6_web_foundation_source_successor_anchor_contract.py",
    "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
    "tools/test_phase6_web_foundation_source_successor_anchor_contract.py",
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
        raise AssertionError(f"Phase6 anchor path escapes root: {relative}")
    candidate = root.joinpath(*value.parts)
    cursor = root
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"Phase6 anchor path is a symlink: {relative}")
    if not candidate.is_file():
        raise AssertionError(f"Phase6 anchor path is not a regular file: {relative}")
    return candidate


def _validate_physical(root: Path, relative: str, sha256: str,
                       byte_count: int) -> bytes:
    payload = _fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or _sha256_bytes(payload) != sha256:
        raise AssertionError(f"Phase6 anchor fixed bytes drifted: {relative}")
    return payload


def _read_json(root: Path, relative: str, sha256: str,
               byte_count: int) -> dict[str, Any]:
    value = json.loads(_validate_physical(root, relative, sha256, byte_count))
    if not isinstance(value, dict):
        raise AssertionError(f"Phase6 anchor JSON is not an object: {relative}")
    return value


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
    if (physical != descriptor["successor_sha256"]
            or len(payload) != descriptor["successor_byte_count"]):
        raise AssertionError(f"Phase6 anchor successor bytes drifted: {relative}")
    return physical


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(sorted({
        CONTRACT_RELATIVE,
        PREDECESSOR_RELATIVE,
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
        raise AssertionError("Phase6 anchor contract payload drifted")
    return document


def _validate_artifact_group(section: dict[str, Any], expected_paths: tuple[str, ...],
                             completion_field: str) -> None:
    if (section.get("source_paths") != list(expected_paths)
            or section.get("source_count") != len(expected_paths)
            or section.get("source_allowlist_exact") is not True
            or section.get(completion_field) is not True
            or set(section.get("artifacts", {})) != set(expected_paths)):
        raise AssertionError("Phase6 anchor fixed artifact group drifted")
    for relative in expected_paths:
        artifact = section["artifacts"][relative]
        if (artifact.get("ti_java_relative_path") != relative
                or artifact.get("repository_path") != f"Ti-Java/{relative}"
                or artifact.get("object_type") != "blob"
                or artifact.get("mode") != "100644"
                or artifact.get("change_type") not in {"A", "M"}
                or len(str(artifact.get("git_blob_oid", ""))) != 40
                or len(str(artifact.get("sha256", ""))) != 64
                or not isinstance(artifact.get("byte_count"), int)):
            raise AssertionError(f"Phase6 anchor artifact drifted: {relative}")


def validate(document: dict[str, Any], ti_java_root: Path) -> None:
    root = ti_java_root.resolve(strict=True)
    if set(document) != {
            "contract_id", "schema_version", "captured_at", "status", "scope",
            "predecessor_source_successor", "git_checkpoint",
            "predecessor_control_source_anchor",
            "typed_anchor_bridge_source_anchor", "source_successors",
            "java_build_context_boundary", "effective_authority",
            "authorization", "current_node_trust_boundary", "acceptance",
            "document_payload_sha256"}:
        raise AssertionError("Phase6 anchor contract shape drifted")
    if (document.get("contract_id") != CONTRACT_ID
            or document.get("schema_version") != 1
            or document.get("captured_at") != CONTRACT_CAPTURED_AT
            or document.get("status") != CONTRACT_STATUS
            or document.get("scope") != CONTRACT_SCOPE
            or document.get("document_payload_sha256")
            != CONTRACT_PAYLOAD_SHA256
            or _payload_sha256(document) != CONTRACT_PAYLOAD_SHA256):
        raise AssertionError("Phase6 anchor contract identity drifted")

    predecessor = document["predecessor_source_successor"]
    expected_predecessor = {
        "source": PREDECESSOR_RELATIVE,
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "sha256": PREDECESSOR_SHA256,
        "byte_count": PREDECESSOR_BYTE_COUNT,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "immutable": True,
    }
    if predecessor != expected_predecessor:
        raise AssertionError("Phase6 anchor predecessor descriptor drifted")
    predecessor_document = _read_json(
        root, PREDECESSOR_RELATIVE, PREDECESSOR_SHA256,
        PREDECESSOR_BYTE_COUNT)
    if (predecessor_document.get("contract_id") != PREDECESSOR_ID
            or predecessor_document.get("status") != PREDECESSOR_STATUS
            or predecessor_document.get("document_payload_sha256")
            != PREDECESSOR_PAYLOAD_SHA256
            or _payload_sha256(predecessor_document)
            != PREDECESSOR_PAYLOAD_SHA256):
        raise AssertionError("Phase6 anchor predecessor payload drifted")

    checkpoint = document["git_checkpoint"]
    expected_checkpoint = {
        "object_format": GIT_OBJECT_FORMAT,
        "commit_oid": GIT_COMMIT_OID,
        "parent_oid": GIT_PARENT_OID,
        "root_tree_oid": GIT_ROOT_TREE_OID,
        "ti_java_tree_oid": GIT_TI_JAVA_TREE_OID,
        "server_tree_oid": GIT_SERVER_TREE_OID,
        "web_tree_oid": GIT_WEB_TREE_OID,
        "server_src_main_tree_oid": GIT_SERVER_SRC_MAIN_TREE_OID,
        "authored_at": GIT_AUTHORED_AT,
        "committed_at": GIT_COMMITTED_AT,
        "subject": GIT_SUBJECT,
        "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
        "changed_path_count": 11,
        "added_count": 6,
        "modified_count": 5,
        "deleted_count": 0,
        "inserted_line_count": GIT_INSERTED_LINE_COUNT,
        "deleted_line_count": GIT_DELETED_LINE_COUNT,
        "current_total_bytes": CHECKPOINT_CURRENT_TOTAL_BYTES,
        "added_total_bytes": CHECKPOINT_ADDED_TOTAL_BYTES,
        "modified_current_bytes": CHECKPOINT_MODIFIED_CURRENT_BYTES,
        "modified_parent_bytes": CHECKPOINT_MODIFIED_PARENT_BYTES,
        "net_byte_increase": CHECKPOINT_NET_BYTE_INCREASE,
        "exact_eleven_path_delta": True,
    }
    for key, expected in expected_checkpoint.items():
        if checkpoint.get(key) != expected:
            raise AssertionError(f"Phase6 anchor checkpoint drifted: {key}")
    if set(checkpoint.get("artifacts", {})) != set(CHECKPOINT_PATHS):
        raise AssertionError("Phase6 anchor exact eleven-path set drifted")

    _validate_artifact_group(
        document["predecessor_control_source_anchor"],
        PREDECESSOR_CONTROL_SOURCES,
        "predecessor_control_sources_external_git_anchor_complete")
    _validate_artifact_group(
        document["typed_anchor_bridge_source_anchor"],
        TYPED_ANCHOR_BRIDGE_SOURCES,
        "typed_anchor_bridge_sources_external_git_anchor_complete")

    successors = document["source_successors"]
    if (successors.get("paths") != list(SOURCE_PATHS)
            or successors.get("path_count") != len(SOURCE_PATHS)
            or successors.get("path_allowlist_exact") is not True
            or successors.get("dynamic_source_discovery_forbidden") is not True
            or set(successors.get("overrides", {})) != set(SOURCE_PATHS)):
        raise AssertionError("Phase6 anchor successor allowlist drifted")
    for relative, expected in SOURCE_SUCCESSORS.items():
        actual = successors["overrides"][relative]
        if (actual.get("source") != relative
                or actual.get("accepted_git_commit_oid") != GIT_COMMIT_OID
                or actual.get("accepted_git_blob_oid")
                != expected["accepted_git_blob_oid"]
                or actual.get("accepted_sha256") != expected["accepted_sha256"]
                or actual.get("accepted_byte_count")
                != expected["accepted_byte_count"]
                or actual.get("successor_sha256")
                != expected["successor_sha256"]
                or actual.get("successor_byte_count")
                != expected["successor_byte_count"]
                or actual.get("changed_after_checkpoint")
                is not expected["changed_after_checkpoint"]
                or actual.get("current_successor_bytes_external_git_anchor_complete")
                is not False):
            raise AssertionError(f"Phase6 anchor successor drifted: {relative}")
        successor_sha256(root, relative)

    boundary = document["java_build_context_boundary"]
    if boundary != {
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
            "server_src_main_tree_unchanged_from_parent": True,
            "web_tree_unchanged_from_parent": True,
            "new_worm_node_required": False}:
        raise AssertionError("Phase6 anchor Java boundary drifted")
    _validate_physical(root, HASHER_RELATIVE, HASHER_SHA256,
                       HASHER_BYTE_COUNT)
    _validate_physical(root, DOCKERFILE_RELATIVE, DOCKERFILE_SHA256,
                       DOCKERFILE_BYTE_COUNT)
    worm = _read_json(root, WORM_RELATIVE, WORM_SHA256, WORM_BYTE_COUNT)
    if (worm.get("java", {}).get("buildContextSha256")
            != JAVA_BUILD_CONTEXT_SHA256
            or worm.get("java", {}).get("dockerfileSha256")
            != DOCKERFILE_SHA256):
        raise AssertionError("Phase6 anchor WORM boundary drifted")

    authority = document["effective_authority"]
    if authority != {
            "source": ROUTE_STATUS_RELATIVE,
            "sha256": ROUTE_STATUS_SHA256,
            "byte_count": ROUTE_STATUS_BYTE_COUNT,
            "document_payload_sha256": ROUTE_STATUS_PAYLOAD_SHA256,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "legacy_flask_remains_production_owner": True}:
        raise AssertionError("Phase6 anchor route descriptor drifted")
    route = _read_json(root, ROUTE_STATUS_RELATIVE, ROUTE_STATUS_SHA256,
                       ROUTE_STATUS_BYTE_COUNT)
    if (route.get("document_payload_sha256") != ROUTE_STATUS_PAYLOAD_SHA256
            or _payload_sha256(route) != ROUTE_STATUS_PAYLOAD_SHA256
            or route.get("effective", {}).get("migration_status")
            != {"migrated": 13, "pending": 598}
            or route.get("effective", {}).get(
                "production_cutover_operation_count") != 0):
        raise AssertionError("Phase6 anchor effective route drifted")

    authorization = document["authorization"]
    if (authorization.get(
            "predecessor_source_successor_checkpoint_external_git_anchor_complete")
            is not True
            or authorization.get(
                "current_successor_bytes_external_git_anchor_complete") is not False
            or set(authorization) != {
                "predecessor_source_successor_checkpoint_external_git_anchor_complete",
                "current_successor_bytes_external_git_anchor_complete",
                "phase6_complete", "route_delta_created", "operator_authorized",
                "schema_or_index_change_authorized",
                "real_data_migration_authorized", "gateway_authorized",
                "production_cutover"}
            or any(authorization[key] is not False for key in authorization
                   if key != (
                       "predecessor_source_successor_checkpoint_"
                       "external_git_anchor_complete"))):
        raise AssertionError("Phase6 anchor authorization overclaim")

    trust = document["current_node_trust_boundary"]
    if (trust.get("control_sources") != list(CURRENT_CONTROL_SOURCES)
            or trust.get("control_source_count") != 6
            or trust.get("control_source_allowlist_exact") is not True
            or trust.get("control_sources_excluded_from_self_authority") is not True
            or trust.get("control_sources_external_git_anchor_complete") is not False
            or trust.get("independently_signed_provenance") is not False):
        raise AssertionError("Phase6 anchor trust boundary drifted")

    acceptance = document["acceptance"]
    if acceptance != {
            "checkpoint_changed_path_count": 11,
            "predecessor_control_source_count": 6,
            "typed_anchor_bridge_source_count": 5,
            "source_successor_path_count": 9,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "phase6_complete": False,
            "production_cutover": False}:
        raise AssertionError("Phase6 anchor acceptance summary drifted")


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
                        "GIT_PAGER": "cat", "LC_ALL": "C"})
    completed = subprocess.run(("git", *arguments), cwd=repository_root,
                               env=environment, check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("Phase6 anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("Phase6 anchor Git object format drifted")
    if (_git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit"
            or _git_text(root, "rev-parse", "--verify",
                         f"{GIT_COMMIT_OID}^{{commit}}") != GIT_COMMIT_OID):
        raise AssertionError("Phase6 anchor Git commit object drifted")
    facts = _git_text(root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s",
                      GIT_COMMIT_OID).splitlines()
    if facts != [GIT_ROOT_TREE_OID, GIT_PARENT_OID, GIT_AUTHORED_AT,
                 GIT_COMMITTED_AT, GIT_SUBJECT]:
        raise AssertionError("Phase6 anchor Git checkpoint identity drifted")
    for relative, expected in {
        "Ti-Java": GIT_TI_JAVA_TREE_OID,
        "Ti-Java/server": GIT_SERVER_TREE_OID,
        "Ti-Java/web": GIT_WEB_TREE_OID,
        "Ti-Java/server/src/main": GIT_SERVER_SRC_MAIN_TREE_OID,
    }.items():
        if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:{relative}") != expected:
            raise AssertionError(f"Phase6 anchor tree drifted: {relative}")
    if (_git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/web")
            != GIT_WEB_TREE_OID
            or _git_text(root, "rev-parse",
                         f"{GIT_PARENT_OID}:Ti-Java/server/src/main")
            != GIT_SERVER_SRC_MAIN_TREE_OID):
        raise AssertionError("Phase6 anchor production tree boundary drifted")
    raw = _run_git(root, "diff-tree", "--no-commit-id", "--raw",
                   "--abbrev=40", "-r", GIT_COMMIT_OID)
    if _sha256_bytes(raw) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("Phase6 anchor raw delta drifted")
    actual_paths = tuple(
        line.split("\t", 1)[1].removeprefix("Ti-Java/")
        for line in raw.decode("utf-8").splitlines()
    )
    if actual_paths != CHECKPOINT_PATHS:
        raise AssertionError("Phase6 anchor exact eleven-path delta drifted")
    numstat = _git_text(root, "diff-tree", "--no-commit-id", "--numstat",
                        "-r", GIT_COMMIT_OID).splitlines()
    parsed_numstat = [line.split("\t", 2) for line in numstat]
    if (len(parsed_numstat) != 11
            or any(len(parts) != 3 or not parts[0].isdigit()
                   or not parts[1].isdigit() for parts in parsed_numstat)
            or sum(int(parts[0]) for parts in parsed_numstat)
            != GIT_INSERTED_LINE_COUNT
            or sum(int(parts[1]) for parts in parsed_numstat)
            != GIT_DELETED_LINE_COUNT
            or tuple(parts[2].removeprefix("Ti-Java/")
                     for parts in parsed_numstat) != CHECKPOINT_PATHS):
        raise AssertionError("Phase6 anchor exact numstat drifted")
    contract = _validate_contract_physical_bytes(root / "Ti-Java")
    artifacts = contract["git_checkpoint"]["artifacts"]
    current_total = 0
    added_total = 0
    modified_current = 0
    modified_parent = 0
    for relative in CHECKPOINT_PATHS:
        item = artifacts[relative]
        payload = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (len(payload) != item["byte_count"]
                or _sha256_bytes(payload) != item["sha256"]):
            raise AssertionError(f"Phase6 anchor Git blob drifted: {relative}")
        current_total += len(payload)
        if item["change_type"] == "A":
            added_total += len(payload)
        else:
            modified_current += len(payload)
            previous = _run_git(
                root, "cat-file", "blob", item["previous_git_blob_oid"]
            )
            modified_parent += len(previous)
    if (current_total != CHECKPOINT_CURRENT_TOTAL_BYTES
            or added_total != CHECKPOINT_ADDED_TOTAL_BYTES
            or modified_current != CHECKPOINT_MODIFIED_CURRENT_BYTES
            or modified_parent != CHECKPOINT_MODIFIED_PARENT_BYTES
            or current_total - modified_parent
            != CHECKPOINT_NET_BYTE_INCREASE):
        raise AssertionError("Phase6 anchor checkpoint byte aggregates drifted")
    for relative in (
            "README.md", "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md"):
        descriptor = SOURCE_SUCCESSORS[relative]
        oid = _git_text(
            root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java/{relative}"
        )
        payload = _run_git(root, "cat-file", "blob", oid)
        if (oid != descriptor["accepted_git_blob_oid"]
                or len(payload) != descriptor["accepted_byte_count"]
                or _sha256_bytes(payload) != descriptor["accepted_sha256"]):
            raise AssertionError(
                f"Phase6 anchor unchanged document drifted: {relative}"
            )


def load(ti_java_root: Path = ROOT) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    document = _validate_contract_physical_bytes(root)
    validate(document, root)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    arguments = parser.parse_args()
    document = load(arguments.ti_java_root)
    if arguments.repository_root is not None:
        validate_git_checkpoint(arguments.repository_root)
    print(
        "Phase6 source-successor anchor acceptance passed: "
        f"{document['document_payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
