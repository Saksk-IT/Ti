#!/usr/bin/env python3
"""Build the fixed external Git anchor for the Phase 6 source successor."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase6/"
    "web-foundation-source-successor-anchor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE

CONTRACT_ID = "ti.phase6.web-foundation-source-successor-anchor-contract"
CAPTURED_AT = "2026-07-19T03:00:00+08:00"
STATUS = "source_successor_checkpoint_externally_anchored_phase6_incomplete"
SCOPE = "phase6-web-foundation-source-successor-external-anchor"

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

_CHECKPOINT_LIST = json.loads(r'''[{"byte_count":7335,"change_type":"A","git_blob_oid":"4e2e267bfcf443139916fdd409b3d6885458c57b","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/docs/refactor/phase6/web-foundation-source-successor-contract.json","sha256":"be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073","ti_java_relative_path":"docs/refactor/phase6/web-foundation-source-successor-contract.json"},{"byte_count":43848,"change_type":"M","git_blob_oid":"41fedbae3238f0fb2d839e705ad673b65be56ec0","mode":"100644","object_type":"blob","previous_git_blob_oid":"14a37c3cf9178f0f328d8ebb77bea7ed4ceaed36","previous_mode":"100644","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java","sha256":"b762441b9d0537240e231effbe5477b89713e7abc861ff9d5a614fc80008848c","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java"},{"byte_count":14962,"change_type":"M","git_blob_oid":"078eb34c6bc7bee1989697ca08f1c4ada0117a26","mode":"100644","object_type":"blob","previous_git_blob_oid":"201a87ace6f96552be458571efc1195daedb956b","previous_mode":"100644","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java","sha256":"f0f57fbd1c24e8f26878209eba298645c63bd962381d26d2505fb76ee495cda8","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java"},{"byte_count":29043,"change_type":"A","git_blob_oid":"c7094e9cbd6a90e57f16596421ada26abfd2734d","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAcceptance.java","sha256":"dbdb33fdcba228d45ee72a560dccc11baee489c3780864caa1e649e2e9aa489b","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAcceptance.java"},{"byte_count":11378,"change_type":"A","git_blob_oid":"d918f07417f6362e8ee07534762efe83cd5edcff","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java","sha256":"e17f062b1cd960289aa5a56cd3fc7b0aa65a649b16f48c7d802d51fab81a89ec","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java"},{"byte_count":45854,"change_type":"M","git_blob_oid":"f2cb5c04f9dc8e6563c45d63164648ffc9556643","mode":"100644","object_type":"blob","previous_git_blob_oid":"a1a07b4f2b8d8524862cb907807ffa09f226546f","previous_mode":"100644","repository_path":"Ti-Java/tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract.py","sha256":"1b0064f9ce37fd41156b9eb74574d11e022ef88e889fd9c965fa514a4d0eba23","ti_java_relative_path":"tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract.py"},{"byte_count":21526,"change_type":"A","git_blob_oid":"aa1785ab315e19eb6832e31c45f7ad821480dab7","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/build_phase6_web_foundation_source_successor_contract.py","sha256":"f9fc6c70ad12e98ceb4d1bf27bb448085807c91fc390c56e451b905403b263c6","ti_java_relative_path":"tools/build_phase6_web_foundation_source_successor_contract.py"},{"byte_count":41725,"change_type":"M","git_blob_oid":"3ea8170b0a9392b332f2794269c8f30a390b72ee","mode":"100644","object_type":"blob","previous_git_blob_oid":"795476b3231b5a26c4c9f4220681b446038cedec","previous_mode":"100644","repository_path":"Ti-Java/tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py","sha256":"cf434c2dc8e33c0b60d09646292fc358bc2df678bfe2f83d04edae79c7bd4aee","ti_java_relative_path":"tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py"},{"byte_count":18420,"change_type":"A","git_blob_oid":"779adedd4b894ede7b215371b7ae5f661fd71c1a","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/phase6_web_foundation_source_successor_acceptance.py","sha256":"1904fae55218791fdc7c66490bcff0d9d9702a4d769ceb919542670bb6e32974","ti_java_relative_path":"tools/phase6_web_foundation_source_successor_acceptance.py"},{"byte_count":11128,"change_type":"M","git_blob_oid":"3c7af81193452fc00a2d98458025431f4ca7ad73","mode":"100644","object_type":"blob","previous_git_blob_oid":"43683440f7c3b5befb7696bf3226f711996461c3","previous_mode":"100644","repository_path":"Ti-Java/tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract.py","sha256":"a96c4431b258b15d367250b668602fcb0ca04cab9555f13a4abfaa8914b0edec","ti_java_relative_path":"tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract.py"},{"byte_count":9084,"change_type":"A","git_blob_oid":"233930c91cd111c6d45e28141b0df876d26d98c9","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/test_phase6_web_foundation_source_successor_contract.py","sha256":"08058702a694a380e16a3a385293396f5f13f88b1cfb36209ffff16818c2a471","ti_java_relative_path":"tools/test_phase6_web_foundation_source_successor_contract.py"}]''')
CHECKPOINT_CHANGES = {
    item["ti_java_relative_path"]: item for item in _CHECKPOINT_LIST
}

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

DOCUMENT_ACCEPTED = {
    "README.md": {
        "sha256": "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
        "byte_count": 40_323,
        "git_blob_oid": "a18ef8e66e1213b4e7ab47e20fb63278c264ba4e",
    },
    "docs/refactor/05-progress.md": {
        "sha256": "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
        "byte_count": 105_423,
        "git_blob_oid": "74974ed6ca408e90846ab90b90e965d8fc9faa5b",
    },
    "docs/refactor/phase4c/README.md": {
        "sha256": "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
        "byte_count": 23_309,
        "git_blob_oid": "8659b84a26ea0b7182c4e375bcb1a1ee185e58b6",
    },
}
SOURCE_PATHS = tuple(sorted((*DOCUMENT_ACCEPTED, *PREDECESSOR_CONTROL_SOURCES)))

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
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java",
    "tools/build_phase6_web_foundation_source_successor_anchor_contract.py",
    "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
    "tools/test_phase6_web_foundation_source_successor_anchor_contract.py",
)

CHECKPOINT_CURRENT_TOTAL_BYTES = 254_303
CHECKPOINT_ADDED_TOTAL_BYTES = 96_786
CHECKPOINT_MODIFIED_CURRENT_BYTES = 157_517
CHECKPOINT_MODIFIED_PARENT_BYTES = 148_725
CHECKPOINT_NET_BYTE_INCREASE = 105_578


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


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


def validated_bytes(root: Path, relative: str, sha256: str,
                    byte_count: int) -> bytes:
    payload = fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(f"Phase6 anchor fixed bytes drifted: {relative}")
    return payload


def read_fixed_json(root: Path, relative: str, sha256: str,
                    byte_count: int) -> dict[str, Any]:
    value = json.loads(validated_bytes(root, relative, sha256, byte_count))
    if not isinstance(value, dict):
        raise AssertionError(f"Phase6 anchor JSON is not an object: {relative}")
    return value


def _accepted_descriptor(relative: str) -> dict[str, Any]:
    if relative in DOCUMENT_ACCEPTED:
        return DOCUMENT_ACCEPTED[relative]
    checkpoint = CHECKPOINT_CHANGES[relative]
    return {
        "sha256": checkpoint["sha256"],
        "byte_count": checkpoint["byte_count"],
        "git_blob_oid": checkpoint["git_blob_oid"],
    }


def _source_successor(root: Path, relative: str) -> dict[str, Any]:
    accepted = _accepted_descriptor(relative)
    payload = fixed_regular_file(root, relative).read_bytes()
    successor_sha = sha256_bytes(payload)
    return {
        "source": relative,
        "accepted_git_commit_oid": GIT_COMMIT_OID,
        "accepted_git_blob_oid": accepted["git_blob_oid"],
        "accepted_sha256": accepted["sha256"],
        "accepted_byte_count": accepted["byte_count"],
        "successor_sha256": successor_sha,
        "successor_byte_count": len(payload),
        "changed_after_checkpoint": successor_sha != accepted["sha256"],
        "current_successor_bytes_external_git_anchor_complete": False,
    }


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
    if sha256_bytes(raw) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("Phase6 anchor raw delta drifted")
    expected_raw = [
        f":{item['previous_mode']} {item['mode']} "
        f"{item['previous_git_blob_oid']} {item['git_blob_oid']} "
        f"{item['change_type']}\t{item['repository_path']}"
        for item in _CHECKPOINT_LIST
    ]
    if raw.decode("utf-8").splitlines() != expected_raw:
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
            or [parts[2] for parts in parsed_numstat]
            != [item["repository_path"] for item in _CHECKPOINT_LIST]):
        raise AssertionError("Phase6 anchor exact numstat drifted")
    current_total = 0
    added_total = 0
    modified_current = 0
    modified_parent = 0
    for item in _CHECKPOINT_LIST:
        payload = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (len(payload) != item["byte_count"]
                or sha256_bytes(payload) != item["sha256"]):
            raise AssertionError(
                f"Phase6 anchor Git blob drifted: {item['repository_path']}"
            )
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
    for relative in DOCUMENT_ACCEPTED:
        descriptor = DOCUMENT_ACCEPTED[relative]
        oid = _git_text(
            root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java/{relative}"
        )
        payload = _run_git(root, "cat-file", "blob", oid)
        if (oid != descriptor["git_blob_oid"]
                or len(payload) != descriptor["byte_count"]
                or sha256_bytes(payload) != descriptor["sha256"]):
            raise AssertionError(
                f"Phase6 anchor unchanged document drifted: {relative}"
            )


def _validate_inputs(root: Path) -> None:
    checkpoint_paths = tuple(CHECKPOINT_CHANGES)
    if (len(_CHECKPOINT_LIST) != 11
            or len(set(checkpoint_paths)) != 11
            or set(PREDECESSOR_CONTROL_SOURCES)
            & set(TYPED_ANCHOR_BRIDGE_SOURCES)
            or set(PREDECESSOR_CONTROL_SOURCES)
            | set(TYPED_ANCHOR_BRIDGE_SOURCES) != set(checkpoint_paths)
            or set(CURRENT_CONTROL_SOURCES) & set(SOURCE_PATHS)):
        raise AssertionError("Phase6 anchor fixed allowlists are inconsistent")
    predecessor = read_fixed_json(root, PREDECESSOR_RELATIVE,
                                  PREDECESSOR_SHA256,
                                  PREDECESSOR_BYTE_COUNT)
    if (predecessor.get("contract_id") != PREDECESSOR_ID
            or predecessor.get("status") != PREDECESSOR_STATUS
            or predecessor.get("document_payload_sha256")
            != PREDECESSOR_PAYLOAD_SHA256
            or document_payload_sha256(predecessor)
            != PREDECESSOR_PAYLOAD_SHA256):
        raise AssertionError("Phase6 anchor predecessor drifted")
    route = read_fixed_json(root, ROUTE_STATUS_RELATIVE, ROUTE_STATUS_SHA256,
                            ROUTE_STATUS_BYTE_COUNT)
    if (route.get("document_payload_sha256") != ROUTE_STATUS_PAYLOAD_SHA256
            or document_payload_sha256(route) != ROUTE_STATUS_PAYLOAD_SHA256
            or route.get("effective", {}).get("migration_status")
            != {"migrated": 13, "pending": 598}
            or route.get("effective", {}).get(
                "production_cutover_operation_count") != 0):
        raise AssertionError("Phase6 anchor route authority drifted")
    validated_bytes(root, HASHER_RELATIVE, HASHER_SHA256, HASHER_BYTE_COUNT)
    validated_bytes(root, DOCKERFILE_RELATIVE, DOCKERFILE_SHA256,
                    DOCKERFILE_BYTE_COUNT)
    worm = read_fixed_json(root, WORM_RELATIVE, WORM_SHA256, WORM_BYTE_COUNT)
    if (worm.get("java", {}).get("buildContextSha256")
            != JAVA_BUILD_CONTEXT_SHA256
            or worm.get("java", {}).get("dockerfileSha256")
            != DOCKERFILE_SHA256):
        raise AssertionError("Phase6 anchor WORM boundary drifted")
    for relative in SOURCE_PATHS:
        fixed_regular_file(root, relative)


def build_contract(ti_java_root: Path = ROOT, *,
                   repository_root: Path | None = None) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    _validate_inputs(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)
    control_artifacts = {
        relative: deepcopy(CHECKPOINT_CHANGES[relative])
        for relative in PREDECESSOR_CONTROL_SOURCES
    }
    bridge_artifacts = {
        relative: deepcopy(CHECKPOINT_CHANGES[relative])
        for relative in TYPED_ANCHOR_BRIDGE_SOURCES
    }
    successors = {relative: _source_successor(root, relative)
                  for relative in SOURCE_PATHS}
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": STATUS,
        "scope": SCOPE,
        "predecessor_source_successor": {
            "source": PREDECESSOR_RELATIVE,
            "contract_id": PREDECESSOR_ID,
            "status": PREDECESSOR_STATUS,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "immutable": True,
        },
        "git_checkpoint": {
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
            "artifacts": deepcopy(CHECKPOINT_CHANGES),
        },
        "predecessor_control_source_anchor": {
            "source_paths": list(PREDECESSOR_CONTROL_SOURCES),
            "source_count": len(PREDECESSOR_CONTROL_SOURCES),
            "source_allowlist_exact": True,
            "artifacts": control_artifacts,
            "predecessor_control_sources_external_git_anchor_complete": True,
        },
        "typed_anchor_bridge_source_anchor": {
            "source_paths": list(TYPED_ANCHOR_BRIDGE_SOURCES),
            "source_count": len(TYPED_ANCHOR_BRIDGE_SOURCES),
            "source_allowlist_exact": True,
            "artifacts": bridge_artifacts,
            "typed_anchor_bridge_sources_external_git_anchor_complete": True,
        },
        "source_successors": {
            "paths": list(SOURCE_PATHS),
            "path_count": len(SOURCE_PATHS),
            "path_allowlist_exact": True,
            "dynamic_source_discovery_forbidden": True,
            "overrides": successors,
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
            "server_src_main_tree_unchanged_from_parent": True,
            "web_tree_unchanged_from_parent": True,
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
            "predecessor_source_successor_checkpoint_external_git_anchor_complete": True,
            "current_successor_bytes_external_git_anchor_complete": False,
            "phase6_complete": False,
            "route_delta_created": False,
            "operator_authorized": False,
            "schema_or_index_change_authorized": False,
            "real_data_migration_authorized": False,
            "gateway_authorized": False,
            "production_cutover": False,
        },
        "current_node_trust_boundary": {
            "control_sources": list(CURRENT_CONTROL_SOURCES),
            "control_source_count": len(CURRENT_CONTROL_SOURCES),
            "control_source_allowlist_exact": True,
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "tamper_evident_scope": (
                "fixed_predecessor_commit_tree_delta_blobs_and_explicit_successors"
            ),
        },
        "acceptance": {
            "checkpoint_changed_path_count": 11,
            "predecessor_control_source_count": 6,
            "typed_anchor_bridge_source_count": 5,
            "source_successor_path_count": len(SOURCE_PATHS),
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "phase6_complete": False,
            "production_cutover": False,
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
        if arguments.output.read_bytes() != payload:
            raise AssertionError("Phase6 source-successor anchor contract drifted")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_bytes(payload)
    print(f"Phase6 source-successor anchor passed: {sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
