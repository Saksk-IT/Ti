#!/usr/bin/env python3
"""Fixed Git anchor for the transaction-write full-parity bootstrap.

Ordinary builds verify embedded fixed pre/post images without using Git or the
parent repository. Only the explicit replay command accesses fixed Git objects.
The current bridge and anchor controls cannot attest their own implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = "docs/refactor/phase4c/learning-transaction-write-http-full-parity-anchor-contract.json"
SNAPSHOT_PATH = "docs/refactor/phase4c/learning-transaction-write-http-full-parity-bootstrap-snapshot.json"
PROGRESS_PATH = "docs/refactor/05-progress.md"
BOOTSTRAP_PATH = "docs/refactor/phase4c/learning-transaction-write-http-full-parity-contract.json"
CONTRACT_ID = "ti.phase4c.learning-transaction-write-http-full-parity-anchor-contract"
CHECKPOINT = {'commit_oid': '6ed81347467a4155887300b7e4ae36589204af79',
 'parent_oid': 'b635d1db3b9d71698d9a40cc729a215d67a6906f',
 'root_tree_oid': '74115f3c94ccab64da81be5ae8c8109bb3ec0034',
 'authored_at': '2026-07-24T16:50:36+08:00',
 'committed_at': '2026-07-24T16:50:36+08:00',
 'subject': 'test(java): close transaction write full parity',
 'ti_java_tree_oid': 'f43ea25fe0d86855df0563f3cf5a3853b3791d01',
 'raw_delta_sha256': 'f1a209ae82d866315cf28ac30b7169a0731b00d1f8564157538f2326b6af6035',
 'changed_path_count': 8,
 'added_path_count': 6,
 'modified_path_count': 2,
 'artifacts': {'docs/refactor/phase4c/learning-transaction-write-http-full-parity-contract.json': {'change_type': 'A',
                                                                                                   'previous_mode': '000000',
                                                                                                   'mode': '100644',
                                                                                                   'previous_git_blob_oid': '0000000000000000000000000000000000000000',
                                                                                                   'git_blob_oid': 'b13b9d8dd770464f61a0f76d46a500239f5535bc',
                                                                                                   'sha256': '40b38a443d7f7d754cc42ce43fa854b0c3c18dc66f4920a2f07d451601d6d1db',
                                                                                                   'byte_count': 15604,
                                                                                                   'previous_sha256': None,
                                                                                                   'previous_byte_count': 0},
               'server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParityContractParityTest.java': {'change_type': 'A',
                                                                                                                                      'previous_mode': '000000',
                                                                                                                                      'mode': '100644',
                                                                                                                                      'previous_git_blob_oid': '0000000000000000000000000000000000000000',
                                                                                                                                      'git_blob_oid': '2c446524e99e6510e867ac3a1f7594025ab2016e',
                                                                                                                                      'sha256': '24f587dda5a78ce19003eb062b3279150cdc71c5c8f4751a977819aadd8eb5a1',
                                                                                                                                      'byte_count': 5313,
                                                                                                                                      'previous_sha256': None,
                                                                                                                                      'previous_byte_count': 0},
               'server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.java': {'change_type': 'A',
                                                                                                                                       'previous_mode': '000000',
                                                                                                                                       'mode': '100644',
                                                                                                                                       'previous_git_blob_oid': '0000000000000000000000000000000000000000',
                                                                                                                                       'git_blob_oid': '728c6bfd5b03b8c308a0c66d03a001abde0a6c9e',
                                                                                                                                       'sha256': 'b54f0e04ace4a101d06832fdb99f412a83ce0ee2c9a12aeded482c2c8ebdadbb',
                                                                                                                                       'byte_count': 25784,
                                                                                                                                       'previous_sha256': None,
                                                                                                                                       'previous_byte_count': 0},
               'server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java': {'change_type': 'M',
                                                                                                                              'previous_mode': '100644',
                                                                                                                              'mode': '100644',
                                                                                                                              'previous_git_blob_oid': '9a9f88ceaf7791c5b8060a4272161a130e08e6b6',
                                                                                                                              'git_blob_oid': '777841196e7c1eb28931ffcba902f86f8241731a',
                                                                                                                              'sha256': 'ba719c5ca08453c22696ff7a3e316936a937371830620a405fdcca424e6afb9a',
                                                                                                                              'byte_count': 53120,
                                                                                                                              'previous_sha256': '85b32075327dcbffd4790f760d2cd91714c183a4ccda509b5f71278cfdcd65d2',
                                                                                                                              'previous_byte_count': 51291},
               'tools/build_phase4c_learning_transaction_write_http_full_parity_contract.py': {'change_type': 'A',
                                                                                               'previous_mode': '000000',
                                                                                               'mode': '100644',
                                                                                               'previous_git_blob_oid': '0000000000000000000000000000000000000000',
                                                                                               'git_blob_oid': '93e1e37da95bca8252b0c19203397bb14910761d',
                                                                                               'sha256': 'e34df1686912e5eb40be9380f79420963ec3dd270053f4f1afc92b934f422c41',
                                                                                               'byte_count': 24262,
                                                                                               'previous_sha256': None,
                                                                                               'previous_byte_count': 0},
               'tools/phase4c_learning_transaction_write_http_full_parity_successor_acceptance.py': {'change_type': 'A',
                                                                                                     'previous_mode': '000000',
                                                                                                     'mode': '100644',
                                                                                                     'previous_git_blob_oid': '0000000000000000000000000000000000000000',
                                                                                                     'git_blob_oid': 'bf99128d2395632c4eb43e93f084420ed675623b',
                                                                                                     'sha256': '146ffdb8b82b33a9cab9a52eac4a0ce14a46254175bf7207ab4ab5c4a3bd4c95',
                                                                                                     'byte_count': 11098,
                                                                                                     'previous_sha256': None,
                                                                                                     'previous_byte_count': 0},
               'tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py': {'change_type': 'M',
                                                                                          'previous_mode': '100644',
                                                                                          'mode': '100644',
                                                                                          'previous_git_blob_oid': 'cfc7ca84573794864436f050995963ffa9486c79',
                                                                                          'git_blob_oid': '39ee69e0dbaf3a9d1429e0aed70166e550da6e22',
                                                                                          'sha256': '0119bedfa3e0298aa1f9019d8ec8e20995e0b49058a360763d209759a444929d',
                                                                                          'byte_count': 23894,
                                                                                          'previous_sha256': '434bb8ab22083dab4f63efb2b77ab0b86ebd55d2946726e0902579c458458789',
                                                                                          'previous_byte_count': 20338},
               'tools/test_phase4c_learning_transaction_write_http_full_parity_contract.py': {'change_type': 'A',
                                                                                              'previous_mode': '000000',
                                                                                              'mode': '100644',
                                                                                              'previous_git_blob_oid': '0000000000000000000000000000000000000000',
                                                                                              'git_blob_oid': '265bcb7add6f63fe7c1e34c1b954d34866baa7fa',
                                                                                              'sha256': 'b44fd3a871253e9a826379b09c1d4c4e3f6bd8353d83af2c3281f328b5bcc536',
                                                                                              'byte_count': 4957,
                                                                                              'previous_sha256': None,
                                                                                              'previous_byte_count': 0}}}
SNAPSHOT_SHA256 = '6696930a6cce0af544d67a2decd7d9309b7d550852b34bd1bb11f21580bef9a7'
SNAPSHOT_BYTE_COUNT = 246770
PROGRESS_TRANSITION = {'source': 'docs/refactor/05-progress.md',
 'accepted_sha256': '4720c1ef1f1dc9d0a7dd6ce8a4c9eb4b1fd4a55c40cd106158fd8060472212de',
 'accepted_byte_count': 122201,
 'successor_sha256': '44c294a91ccdac016cc72315e56b87dccc2fb9b129ba78cddc7dc2498b741ccc',
 'successor_byte_count': 124314}

# These four controls are unchanged since the anchored commit. The four other
# bootstrap controls receive the narrow progress bridge in this successor.
UNCHANGED_BOOTSTRAP_SOURCES = (
    BOOTSTRAP_PATH,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParityContractParityTest.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java",
    "tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py",
)
CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "tools/build_phase4c_learning_transaction_write_http_full_parity_anchor_contract.py",
    "tools/phase4c_learning_transaction_write_http_full_parity_anchor_successor_acceptance.py",
    "tools/test_phase4c_learning_transaction_write_http_full_parity_anchor_contract.py",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParityAnchorContractParityTest.java",
    "tools/build_phase4c_learning_transaction_write_http_full_parity_contract.py",
    "tools/phase4c_learning_transaction_write_http_full_parity_successor_acceptance.py",
    "tools/test_phase4c_learning_transaction_write_http_full_parity_contract.py",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.java",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_oid(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def payload_sha256(document: dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(
        {k: v for k, v in document.items() if k != "document_payload_sha256"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    value = PurePosixPath(relative)
    if (not relative or value.is_absolute() or "\\" in relative or ":" in relative
            or any(part in {"", ".", ".."} for part in relative.split("/"))):
        raise AssertionError(f"anchor path escapes root: {relative}")
    cursor = root.resolve(strict=True)
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"anchor path is a symlink: {relative}")
    if not cursor.is_file():
        raise AssertionError(f"anchor file is absent: {relative}")
    return cursor


def fixed_bytes(root: Path, relative: str, digest: str, count: int) -> bytes:
    payload = fixed_regular_file(root, relative).read_bytes()
    if len(payload) != count or sha256_bytes(payload) != digest:
        raise AssertionError(f"anchor fixed bytes drifted: {relative}")
    return payload


def read_snapshot(root: Path = ROOT) -> dict[str, Any]:
    snapshot = json.loads(fixed_bytes(root, SNAPSHOT_PATH, SNAPSHOT_SHA256, SNAPSHOT_BYTE_COUNT))
    if (set(snapshot) != {"commit_oid", "sources"}
            or snapshot["commit_oid"] != CHECKPOINT["commit_oid"]
            or set(snapshot["sources"]) != set(CHECKPOINT["artifacts"])):
        raise AssertionError("anchor snapshot path set drifted")
    for relative, descriptor in CHECKPOINT["artifacts"].items():
        images = snapshot["sources"][relative]
        for name, prefix in (("after", ""), ("before", "previous_")):
            image = images[name]
            if name == "before" and descriptor["change_type"] == "A":
                if image is not None or descriptor["previous_git_blob_oid"] != "0" * 40:
                    raise AssertionError(f"anchor added preimage drifted: {relative}")
                continue
            raw = image.encode("utf-8")
            if (len(raw) != descriptor[prefix + "byte_count"]
                    or sha256_bytes(raw) != descriptor[prefix + "sha256"]
                    or git_blob_oid(raw) != descriptor[prefix + "git_blob_oid"]):
                raise AssertionError(f"anchor snapshot blob drifted: {relative}")
    return snapshot


def fixed_inputs(root: Path) -> dict[str, dict[str, Any]]:
    """Derive only paths explicitly fixed by the immutable bootstrap/Node D JSON."""
    descriptor = CHECKPOINT["artifacts"][BOOTSTRAP_PATH]
    bootstrap = json.loads(fixed_bytes(root, BOOTSTRAP_PATH, descriptor["sha256"], descriptor["byte_count"]))
    inputs = {}
    for descriptor in bootstrap["predecessor"].values():
        if isinstance(descriptor, dict) and "source" in descriptor:
            inputs[descriptor["source"]] = descriptor
            fixed_bytes(root, descriptor["source"], descriptor["sha256"], descriptor["byte_count"])
    node_d = json.loads(fixed_regular_file(root, bootstrap["predecessor"]["node_d_contract"]["source"]).read_bytes())
    inputs.update(node_d["source_authority"]["fixed_non_control_sources"])
    for relative, transition in bootstrap["historical_source_successors"]["transitions"].items():
        inputs[relative] = {"sha256": transition["successor_sha256"], "byte_count": transition["successor_byte_count"]}
    inputs.update(bootstrap["fixed_evidence"]["artifacts"])
    inputs[PROGRESS_PATH] = {"sha256": PROGRESS_TRANSITION["successor_sha256"], "byte_count": PROGRESS_TRANSITION["successor_byte_count"]}
    for relative in UNCHANGED_BOOTSTRAP_SOURCES:
        inputs[relative] = CHECKPOINT["artifacts"][relative]
    return inputs


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    snapshot = read_snapshot(root)
    for relative, descriptor in fixed_inputs(root).items():
        fixed_bytes(root, relative, descriptor["sha256"], descriptor["byte_count"])
    bootstrap = json.loads(snapshot["sources"][BOOTSTRAP_PATH]["after"])
    if set(bootstrap["source_authority"]["control_sources"]) != set(CHECKPOINT["artifacts"]):
        raise AssertionError("anchor does not cover all bootstrap controls")
    document = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": "2026-09-13T00:00:00+08:00",
        "status": "bootstrap_externally_anchored_current_tree_verification_and_route_promotion_pending",
        "predecessor": {"source": BOOTSTRAP_PATH, "sha256": CHECKPOINT["artifacts"][BOOTSTRAP_PATH]["sha256"], "byte_count": 15604, "immutable": True},
        "git_checkpoint": {**CHECKPOINT, "exact_changed_paths": list(CHECKPOINT["artifacts"])},
        "bootstrap_sources": list(CHECKPOINT["artifacts"]),
        "bootstrap_snapshot": {"source": SNAPSHOT_PATH, "sha256": SNAPSHOT_SHA256, "byte_count": SNAPSHOT_BYTE_COUNT, "includes_modified_preimages": True},
        "unchanged_bootstrap_sources": list(UNCHANGED_BOOTSTRAP_SOURCES),
        "progress_successor": PROGRESS_TRANSITION,
        "parity": bootstrap["parity"],
        "authorization": {
            "bootstrap_control_sources_external_git_anchor_complete": True,
            "current_anchor_sources_external_git_anchor_complete": False,
            "route_migration_eligible": False,
            "nine_transaction_write_operations_migrated": False,
            "production_cutover": False,
            "production_schema_execution": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "next_gate": "current_tree_full_verification_then_append_only_route_promotion",
        },
        "route_state": bootstrap["route_state"],
        "source_authority": {
            "control_sources": list(CONTROL_SOURCES),
            "control_sources_excluded_from_self_authority": True,
            "ordinary_build_is_gitless": True,
            "live_head_main_or_origin_authority": False,
            "historical_contracts_or_worm_overwritten": False,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


def verify_fixed_git_checkpoints(repository_root: Path) -> None:
    """Explicit fixed-object replay; never used by ordinary build or tests."""
    def git(*args: str) -> bytes:
        return subprocess.run(["git", "-C", str(repository_root), *args], check=True, capture_output=True).stdout

    checkpoint = CHECKPOINT
    commit, parent = checkpoint["commit_oid"], checkpoint["parent_oid"]
    metadata = git("show", "-s", "--format=%H%n%P%n%T%n%aI%n%cI%n%s", commit).decode().splitlines()
    if metadata != [commit, parent, checkpoint["root_tree_oid"], checkpoint["authored_at"], checkpoint["committed_at"], checkpoint["subject"]]:
        raise AssertionError("anchor Git metadata drifted")
    if git("rev-parse", commit + ":Ti-Java").decode().strip() != checkpoint["ti_java_tree_oid"]:
        raise AssertionError("anchor Ti-Java tree drifted")
    raw = git("diff-tree", "--no-commit-id", "--no-renames", "--raw", "-r", "--abbrev=40", parent, commit)
    if sha256_bytes(raw) != checkpoint["raw_delta_sha256"]:
        raise AssertionError("anchor raw delta drifted")
    expected_lines = []
    for relative, descriptor in checkpoint["artifacts"].items():
        expected_lines.append(f":{descriptor['previous_mode']} {descriptor['mode']} {descriptor['previous_git_blob_oid']} {descriptor['git_blob_oid']} {descriptor['change_type']}\tTi-Java/{relative}\n")
        for prefix in ("", "previous_"):
            if prefix and descriptor["change_type"] == "A":
                continue
            payload = git("cat-file", "blob", descriptor[prefix + "git_blob_oid"])
            if (sha256_bytes(payload) != descriptor[prefix + "sha256"]
                    or len(payload) != descriptor[prefix + "byte_count"]):
                raise AssertionError(f"anchor Git blob drifted: {relative}")
    if raw != "".join(expected_lines).encode():
        raise AssertionError("anchor complete Git delta differs from descriptors")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repository-root", type=Path, help="explicit fixed Git replay; ordinary builds do not access Git")
    args = parser.parse_args()
    payload = serialized_contract(build_contract())
    if args.repository_root is not None:
        verify_fixed_git_checkpoints(args.repository_root)
    if args.check:
        if (ROOT / OUTPUT_RELATIVE).read_bytes() != payload:
            raise SystemExit("anchor contract drifted")
    else:
        (ROOT / OUTPUT_RELATIVE).write_bytes(payload)


if __name__ == "__main__":
    main()
